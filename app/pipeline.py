"""
Guardian Drive AI - System Pipeline Controller
Orchestrates capture, vision analysis, temporal behavior, risk & state,
alerts, and emergency dispatch.
Emits Qt signals to keep GUI decoupled and 100% responsive.
"""
from __future__ import annotations

import time
import threading
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from app.alerts.alert_manager import AlertManager
from app.alerts.hazard_simulator import HazardSimulator
from app.behavior.behavior_engine import BehaviorEngine
from app.behavior.risk_engine import RiskEngine
from app.behavior.state_engine import StateEngine
from app.camera.camera_manager import CameraManager
from app.config.settings import Settings
from app.emergency.clip_manager import ClipManager
from app.emergency.emergency_manager import EmergencyManager
from app.emergency.location_provider import WindowsLocationProvider
from app.emergency.notification_provider import SimulatorNotificationProvider
from app.models import (
    AlertEvent,
    AlertLevel,
    CameraStatus,
    DriverState,
    FaceFeatures,
    GuiStatus,
    RiskAssessment,
    SimulationScenario,
)
from app.simulation.simulator import ScenarioSimulator
from app.storage.repositories import AlertRepository, DriverRepository
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger
from app.utils.platform_utils import prevent_system_sleep
from app.vision.face_analyzer import FaceAnalyzer
from app.camera.camera_health import compute_frame_quality
from app.vision.frame_processor import _apply_night_mode, _classify_head_direction

_log = get_logger(__name__)


class PipelineController(QObject):
    """
    Core pipeline controller running analysis in a background thread.
    Communicates with Qt via signals.
    """

    status_updated = Signal(GuiStatus)
    frame_ready = Signal(QImage)
    emergency_triggered = Signal(str, bool)  # (summary, is_simulated)

    def __init__(self, settings: Settings, db: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self._cfg = settings
        self._db = db

        # Repositories
        self._alert_repo = AlertRepository(db)
        self._driver_repo = DriverRepository(db)

        # Vision & Camera
        self._camera_mgr = CameraManager(settings=settings)
        self._face_analyzer = FaceAnalyzer()

        # Behavior & Decision
        self._behavior_engine = BehaviorEngine(settings=settings)
        self._risk_engine = RiskEngine(settings=settings)
        self._state_engine = StateEngine(settings=settings)

        # Alerts & Hazard
        self._hazard_sim = HazardSimulator(on_state_change=self._on_hazard_state_change)
        self._alert_mgr = AlertManager(
            settings=settings,
            on_alert_message=self._on_alert_message,
            on_emergency=self._on_emergency_callback,
        )

        # Emergency & Clips
        self._clip_mgr = ClipManager(settings=settings)
        self._emergency_mgr = EmergencyManager(
            settings=settings,
            db_repo=self._alert_repo,
            notification_provider=SimulatorNotificationProvider(),
            location_provider=WindowsLocationProvider(),
            clip_manager=self._clip_mgr,
            on_status_update=self._on_emergency_status_update,
        )

        # Simulation
        self._simulator = ScenarioSimulator()

        # Thread state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Cached GUI status state
        self._simulated = False
        self._current_alert_msg = ""
        self._current_alert_level = AlertLevel.NONE
        self._hazard_active = False
        self._emergency_status = ""
        self._last_fps = 0.0
        self._last_recorded_level = AlertLevel.NONE
        self._active_alert_event_id: Optional[str] = None

    def start_monitoring(self) -> None:
        """Starts real camera monitoring."""
        with self._lock:
            if self._running:
                return
            self._simulated = False
            self._reset_engines()
            self._running = True
            self._camera_mgr.start()
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="PipelineThread")
            self._thread.start()
            prevent_system_sleep(True)
        _log.info("Monitoring pipeline started")

    def stop_monitoring(self) -> None:
        """Stops camera monitoring."""
        with self._lock:
            if not self._running:
                return
            self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._camera_mgr.stop()
        self._hazard_sim.deactivate()
        self._alert_mgr.reset()
        prevent_system_sleep(False)
        self._emit_idle_status()
        _log.info("Monitoring pipeline stopped")

    def start_simulation(self, scenario: SimulationScenario) -> None:
        """Starts monitoring in simulation mode with a predefined scenario."""
        with self._lock:
            if self._running:
                self._running = False
            if self._thread:
                self._thread.join(timeout=1.0)

            self._simulated = True
            self._reset_engines()
            self._simulator.start(scenario)
            self._running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="SimPipelineThread")
            self._thread.start()
            prevent_system_sleep(True)
        _log.info("Simulation pipeline started: %s", scenario.value)

    def stop_simulation(self) -> None:
        """Stops simulation mode."""
        self._simulator.stop()
        self.stop_monitoring()

    def _on_hazard_state_change(self, is_on: bool) -> None:
        self._hazard_active = is_on

    def _on_alert_message(self, msg: str, level: AlertLevel, hazard: bool) -> None:
        self._current_alert_msg = msg
        self._current_alert_level = level
        if hazard and not self._hazard_sim.is_active:
            self._hazard_sim.activate()
        elif not hazard and self._hazard_sim.is_active:
            self._hazard_sim.deactivate()

    def _on_emergency_callback(self, assessment: RiskAssessment) -> None:
        now_ts = time.monotonic()
        self._emergency_mgr.trigger(assessment, trigger_ts=now_ts, simulated=self._simulated)
        self.emergency_triggered.emit(
            f"Condition: {assessment.driver_state.value} | emergency workflow started",
            self._simulated,
        )

    def _on_emergency_status_update(self, status: str) -> None:
        self._emergency_status = status

    def _worker_loop(self) -> None:
        frame_count = 0
        fps_timer = time.monotonic()

        while self._running:
            tick_start = time.monotonic()
            frame_bgr: Optional[np.ndarray] = None
            features: FaceFeatures

            if self._simulated:
                features = self._simulator.get_features()
                frame_bgr = self._simulator.generate_synthetic_frame(features)
                cam_status = CameraStatus.OK if features.face_detected else CameraStatus.LOW_QUALITY
            else:
                frame_bgr = self._camera_mgr.read_frame()
                cam_status = self._camera_mgr.get_status()

                if frame_bgr is not None:
                    processed_frame = frame_bgr
                    brightness, blur, quality = compute_frame_quality(processed_frame)
                    if self._cfg.night_mode == "on" or (self._cfg.night_mode == "auto" and brightness < 60):
                        processed_frame = _apply_night_mode(processed_frame)
                    if self._cfg.camera_mirror:
                        processed_frame = cv2.flip(processed_frame, 1)
                    if self._cfg.lightweight_mode:
                        h, w = processed_frame.shape[:2]
                        scale = float(self._cfg.get_value("vision", "lightweight_scale", default=0.5))
                        processed_frame = cv2.resize(processed_frame, (max(1, int(w * scale)), max(1, int(h * scale))))
                    features, annotated_frame = self._face_analyzer.analyze_and_annotate(
                        processed_frame, time.monotonic()
                    )
                    features.frame_brightness = brightness
                    features.frame_blur_score = blur
                    if features.face_detected:
                        features.head_direction = _classify_head_direction(
                            features.head_yaw, features.head_pitch, self._cfg
                        )
                    if quality == CameraStatus.LOW_QUALITY and cam_status == CameraStatus.OK:
                        cam_status = quality
                    frame_bgr = annotated_frame
                else:
                    features = FaceFeatures(face_detected=False, confidence=0.0, timestamp=time.monotonic())

            # Temporal behavior analysis
            behavior_signals = self._behavior_engine.update(features)

            # Heuristic Risk computation
            risk_score = self._risk_engine.compute(behavior_signals, features.confidence)

            # State Engine (Hysteresis, Persistence & Alert Escalation)
            final_assessment = self._state_engine.update(behavior_signals, risk_score, features)

            self._record_alert_transition(final_assessment, behavior_signals)


            # Alert Manager (Audio, Voice, Hazard flasher)
            self._alert_mgr.update(final_assessment)

            # Rolling video buffer
            if frame_bgr is not None:
                self._clip_mgr.add_frame(frame_bgr, time.monotonic())

            # FPS calculation
            frame_count += 1
            now = time.monotonic()
            if now - fps_timer >= 1.0:
                self._last_fps = frame_count / (now - fps_timer)
                frame_count = 0
                fps_timer = now

            # Emit GUI Status
            gui_status = GuiStatus(
                monitoring_active=True,
                camera_status=cam_status,
                driver_state=final_assessment.driver_state,
                alert_level=final_assessment.alert_level,
                alert_message=self._current_alert_msg,
                hazard_simulation_active=self._hazard_active,
                emergency_status=self._emergency_status,
                fps=self._last_fps,
                simulated=self._simulated,
            )
            self.status_updated.emit(gui_status)

            # Emit Video Frame to Qt GUI
            if frame_bgr is not None:
                rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
                self.frame_ready.emit(q_img)

            # Regulate frame rate to ~30 FPS
            elapsed = time.monotonic() - tick_start
            sleep_time = max(0.005, 0.033 - elapsed)
            time.sleep(sleep_time)

    def _reset_engines(self) -> None:
        self._behavior_engine.reset()
        self._risk_engine.reset()
        self._state_engine.reset()
        self._alert_mgr.reset()
        self._last_recorded_level = AlertLevel.NONE
        self._active_alert_event_id = None

    def _record_alert_transition(self, assessment: RiskAssessment, signals) -> None:
        """Persist local Level 1/2 metadata and queue event-only clip capture."""
        level = assessment.alert_level
        if level == self._last_recorded_level:
            return
        self._last_recorded_level = level
        if level == AlertLevel.NONE:
            if self._active_alert_event_id:
                self._alert_repo.resolve_alert(self._active_alert_event_id)
                self._active_alert_event_id = None
            return
        if level not in (AlertLevel.LEVEL1, AlertLevel.LEVEL2):
            return
        from app.utils.time_utils import generate_event_id
        if level == AlertLevel.LEVEL2 and self._active_alert_event_id:
            clip_path = self._clip_mgr.save_clip(self._active_alert_event_id, level, assessment.timestamp) or ""
            self._alert_repo.update_alert_level(
                self._active_alert_event_id, level, assessment.driver_state, clip_path
            )
            return
        event = AlertEvent(
            alert_level=level,
            driver_state=assessment.driver_state,
            trigger_summary=(f"eye_closure={signals.eye_closure_duration_s:.1f}s; "
                             f"head_away={signals.head_away_duration_s:.1f}s; "
                             f"yawns={signals.yawn_count_60s}"),
            simulated=self._simulated,
        )
        event.event_id = generate_event_id()
        event.clip_path = self._clip_mgr.save_clip(event.event_id, level, assessment.timestamp) or ""
        self._alert_repo.record_alert(event)
        self._active_alert_event_id = event.event_id

    def _emit_idle_status(self) -> None:
        idle_status = GuiStatus(
            monitoring_active=False,
            camera_status=CameraStatus.NOT_STARTED,
            driver_state=DriverState.UNKNOWN,
            alert_level=AlertLevel.NONE,
            alert_message="Monitoring Paused",
            hazard_simulation_active=False,
            emergency_status="",
            fps=0.0,
            simulated=False,
        )
        self.status_updated.emit(idle_status)

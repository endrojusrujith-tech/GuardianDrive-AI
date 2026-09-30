"""
Guardian Drive AI - Scenario Simulator
Generates deterministic synthetic FaceFeatures and preview frames for testing and demo.
Allows running entire driver-monitoring pipelines without physical webcam.
"""
from __future__ import annotations

import time
import numpy as np
import cv2
from typing import Optional, Tuple

from app.models import EyeState, FaceFeatures, HeadDirection, SimulationScenario
from app.simulation.scenarios import SCENARIOS, ScenarioStep
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class ScenarioSimulator:
    """
    Simulates driver behavior over time based on pre-defined test scenarios.
    """

    def __init__(self, scenario: SimulationScenario = SimulationScenario.NORMAL_DRIVING) -> None:
        self.scenario = scenario
        self._start_time = 0.0
        self._active = False
        self._current_step_idx = 0

    def start(self, scenario: Optional[SimulationScenario] = None) -> None:
        if scenario:
            self.scenario = scenario
        self._start_time = time.monotonic()
        self._active = True
        _log.info("Started simulator with scenario: %s", self.scenario.value)

    def stop(self) -> None:
        self._active = False
        _log.info("Stopped simulator")

    @property
    def is_active(self) -> bool:
        return self._active

    def get_features(self, current_time: Optional[float] = None) -> FaceFeatures:
        """Returns synthetic FaceFeatures corresponding to the current elapsed time."""
        if not self._active:
            now = current_time or time.monotonic()
            return FaceFeatures(face_detected=False, confidence=0.0, timestamp=now)

        now = current_time or time.monotonic()
        elapsed = now - self._start_time

        steps = SCENARIOS.get(self.scenario, SCENARIOS[SimulationScenario.NORMAL_DRIVING])

        accumulated = 0.0
        active_step = steps[-1]
        for step in steps:
            accumulated += step.duration_s
            if elapsed <= accumulated:
                active_step = step
                break

        eye_state = EyeState.OPEN if active_step.ear >= 0.20 else EyeState.CLOSED
        if not active_step.face_detected:
            eye_state = EyeState.UNKNOWN

        features = FaceFeatures(
            face_detected=active_step.face_detected,
            face_count=active_step.face_count,
            confidence=active_step.confidence,
            face_center_x=0.5 + (active_step.head_yaw / 90.0) * 0.2,
            face_center_y=0.5 + (active_step.head_pitch / 90.0) * 0.2,
            face_width_ratio=0.35 if active_step.face_detected else 0.0,
            ear_left=active_step.ear,
            ear_right=active_step.ear,
            ear_avg=active_step.ear,
            eye_state=eye_state,
            head_yaw=active_step.head_yaw,
            head_pitch=active_step.head_pitch,
            head_direction=active_step.head_dir,
            mar=active_step.mar,
            yawn_detected=active_step.yawn_detected,
            phone_detected=active_step.phone_detected,
            phone_confidence=active_step.phone_conf,
            frame_brightness=active_step.brightness,
            frame_blur_score=active_step.blur,
            timestamp=now,
        )
        return features

    def generate_synthetic_frame(self, features: FaceFeatures, width: int = 640, height: int = 480) -> np.ndarray:
        """
        Renders a clean synthetic dashboard / simulated camera frame with face indicator,
        pose direction, eyes, and simulation telemetry overlay.
        """
        frame = np.full((height, width, 3), 32, dtype=np.uint8)

        # Simulation watermark banner
        cv2.rectangle(frame, (0, 0), (width, 36), (20, 24, 82), -1)
        banner_text = f"SIMULATION ACTIVE: {self.scenario.value.upper()}"
        cv2.putText(frame, banner_text, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2)

        if not features.face_detected:
            cv2.putText(
                frame,
                "NO FACE DETECTED (SIMULATED)",
                (width // 4, height // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            return frame

        # Draw simulated driver head / face circle
        cx = int(features.face_center_x * width)
        cy = int(features.face_center_y * height)
        radius = int(width * 0.16)

        face_color = (180, 210, 180)
        cv2.circle(frame, (cx, cy), radius, face_color, 2)

        # Eyes
        eye_y = cy - int(radius * 0.25)
        left_eye_x = cx - int(radius * 0.4)
        right_eye_x = cx + int(radius * 0.4)
        eye_r = int(radius * 0.15)

        if features.eye_state == EyeState.OPEN:
            cv2.circle(frame, (left_eye_x, eye_y), eye_r, (0, 255, 0), -1)
            cv2.circle(frame, (right_eye_x, eye_y), eye_r, (0, 255, 0), -1)
        else:
            # Closed eye horizontal line
            cv2.line(frame, (left_eye_x - eye_r, eye_y), (left_eye_x + eye_r, eye_y), (0, 0, 255), 3)
            cv2.line(frame, (right_eye_x - eye_r, eye_y), (right_eye_x + eye_r, eye_y), (0, 0, 255), 3)

        # Mouth / Yawn
        mouth_y = cy + int(radius * 0.45)
        if features.yawn_detected or features.mar > 0.5:
            cv2.ellipse(frame, (cx, mouth_y), (int(radius * 0.25), int(radius * 0.35)), 0, 0, 360, (0, 165, 255), -1)
        else:
            cv2.line(frame, (cx - int(radius * 0.25), mouth_y), (cx + int(radius * 0.25), mouth_y), (200, 200, 200), 2)

        # Phone indicator
        if features.phone_detected:
            px = cx + int(radius * 0.7)
            py = cy - int(radius * 0.3)
            cv2.rectangle(frame, (px, py), (px + 45, py + 80), (255, 100, 0), -1)
            cv2.putText(frame, "PHONE", (px - 5, py + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 100, 0), 1)

        # Telemetry text on bottom
        telemetry = f"EAR: {features.ear_avg:.2f} | MAR: {features.mar:.2f} | Yaw: {features.head_yaw:+.1f} deg | Pitch: {features.head_pitch:+.1f} deg"
        cv2.putText(frame, telemetry, (15, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

        return frame

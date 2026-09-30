"""
Guardian Drive AI - Monitoring View
Main dashboard screen:
  - Live video preview (webcam feed or simulation)
  - Driver State indicator (NORMAL, DISTRACTED, DROWSY, CRITICAL, UNKNOWN)
  - Camera Status indicator (OK, LOW_QUALITY, RECONNECTING, FAILED, NOT_STARTED)
  - Monitoring Status indicator (ACTIVE / PAUSED)
  - Alert Banner & Hazard Flasher indicator
  - Start/Stop monitoring controls
  - Simulation scenario selector & trigger
  - Note: NO internal risk score is shown on this screen (per project rules).
"""
from __future__ import annotations

from typing import Optional, Callable
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QGroupBox,
)

from app.models import (
    AlertLevel,
    CameraStatus,
    DriverState,
    GuiStatus,
    SimulationScenario,
)
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class VideoLabel(QLabel):
    """Subclass of QLabel that maintains aspect ratio when displaying frames."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px;")
        self.setMinimumSize(480, 360)
        self._pixmap: Optional[QPixmap] = None

    def set_frame(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._pixmap and not self._pixmap.isNull():
            self.setPixmap(self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class MonitoringView(QWidget):
    """Main live driver monitoring dashboard."""

    start_requested = Signal()
    stop_requested = Signal()
    simulation_requested = Signal(SimulationScenario)
    stop_simulation_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Top Indicator Bar ───────────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        # 1. Monitoring Status Card
        self.mon_card = self._create_status_card("MONITORING", "PAUSED", "#64748b")
        top_bar.addWidget(self.mon_card["container"])

        # 2. Driver State Card
        self.state_card = self._create_status_card("DRIVER STATE", "UNKNOWN", "#3b82f6")
        top_bar.addWidget(self.state_card["container"])

        # 3. Camera Status Card
        self.cam_card = self._create_status_card("CAMERA", "NOT_STARTED", "#64748b")
        top_bar.addWidget(self.cam_card["container"])

        # 4. Hazard Simulator Card
        self.hazard_card = self._create_status_card("HAZARD LIGHTS", "OFF", "#334155")
        top_bar.addWidget(self.hazard_card["container"])

        main_layout.addLayout(top_bar)

        # ── Alert Banner ────────────────────────────────────────────────────
        self.alert_banner = QLabel("SYSTEM READY - DRIVER ATTENTION MONITORING")
        self.alert_banner.setAlignment(Qt.AlignCenter)
        self.alert_banner.setFixedHeight(38)
        self.alert_banner.setStyleSheet("""
            background-color: #1e293b;
            color: #94a3b8;
            font-size: 14px;
            font-weight: bold;
            border-radius: 6px;
            padding: 4px 12px;
        """)
        main_layout.addWidget(self.alert_banner)

        # ── Video Viewport ──────────────────────────────────────────────────
        self.video_label = VideoLabel()
        self.video_label.setText("Camera Feed Inactive\nClick 'Start Monitoring' or 'Run Simulation' below.")
        main_layout.addWidget(self.video_label, stretch=1)

        # ── Bottom Control Panel ────────────────────────────────────────────
        ctrl_box = QGroupBox("System Controls")
        ctrl_box.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #94a3b8;
                border: 1px solid #1e293b;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 12px;
            }
        """)
        ctrl_layout = QHBoxLayout(ctrl_box)
        ctrl_layout.setSpacing(12)

        # Start / Stop Monitoring
        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 20px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.start_btn.clicked.connect(self._on_toggle_monitoring)
        ctrl_layout.addWidget(self.start_btn)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #334155;")
        ctrl_layout.addWidget(line)

        # Simulation selector
        sim_lbl = QLabel("Scenario:")
        sim_lbl.setStyleSheet("color: #cbd5e1; font-weight: 500;")
        ctrl_layout.addWidget(sim_lbl)

        self.scenario_combo = QComboBox()
        self.scenario_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 180px;
            }
        """)
        for s in SimulationScenario:
            self.scenario_combo.addItem(s.value.replace("_", " ").title(), s)
        ctrl_layout.addWidget(self.scenario_combo)

        self.sim_btn = QPushButton("Run Simulation")
        self.sim_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: #0f172a;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #d97706; }
        """)
        self.sim_btn.clicked.connect(self._on_toggle_simulation)
        ctrl_layout.addWidget(self.sim_btn)

        ctrl_layout.addStretch()

        # Live FPS
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        ctrl_layout.addWidget(self.fps_label)

        main_layout.addWidget(ctrl_box)

        self._monitoring_active = False
        self._simulation_active = False

    def _create_status_card(self, title: str, default_val: str, color: str) -> dict:
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(6, 4, 6, 4)
        vbox.setSpacing(2)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        t_lbl.setAlignment(Qt.AlignCenter)
        vbox.addWidget(t_lbl)

        v_lbl = QLabel(default_val)
        v_lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        v_lbl.setAlignment(Qt.AlignCenter)
        vbox.addWidget(v_lbl)

        return {"container": container, "title": t_lbl, "value": v_lbl}

    def _on_toggle_monitoring(self) -> None:
        if not self._monitoring_active:
            self.start_requested.emit()
        else:
            self.stop_requested.emit()

    def _on_toggle_simulation(self) -> None:
        if not self._simulation_active:
            scen = self.scenario_combo.currentData()
            self.simulation_requested.emit(scen)
        else:
            self.stop_simulation_requested.emit()

    @Slot(GuiStatus)
    def update_status(self, status: GuiStatus) -> None:
        """Called whenever the vision/monitoring worker delivers a status update."""
        self._monitoring_active = status.monitoring_active
        self._simulation_active = status.simulated

        # Update Start/Stop button
        if self._monitoring_active and not self._simulation_active:
            self.start_btn.setText("Stop Monitoring")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444; color: white; font-weight: bold;
                    font-size: 13px; padding: 8px 20px; border-radius: 4px;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
        else:
            self.start_btn.setText("Start Monitoring")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981; color: white; font-weight: bold;
                    font-size: 13px; padding: 8px 20px; border-radius: 4px;
                }
                QPushButton:hover { background-color: #059669; }
            """)

        # Update Simulation button
        if self._simulation_active:
            self.sim_btn.setText("Stop Simulation")
            self.sim_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444; color: white; font-weight: bold;
                    font-size: 13px; padding: 8px 18px; border-radius: 4px;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
        else:
            self.sim_btn.setText("Run Simulation")
            self.sim_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b; color: #0f172a; font-weight: bold;
                    font-size: 13px; padding: 8px 18px; border-radius: 4px;
                }
                QPushButton:hover { background-color: #d97706; }
            """)

        # 1. Monitoring Status Card
        if status.simulated:
            self.mon_card["value"].setText("SIMULATED")
            self.mon_card["value"].setStyleSheet("color: #f59e0b; font-size: 14px; font-weight: bold;")
        elif status.monitoring_active:
            self.mon_card["value"].setText("ACTIVE")
            self.mon_card["value"].setStyleSheet("color: #10b981; font-size: 14px; font-weight: bold;")
        else:
            self.mon_card["value"].setText("PAUSED")
            self.mon_card["value"].setStyleSheet("color: #64748b; font-size: 14px; font-weight: bold;")

        # 2. Driver State Card
        d_state = status.driver_state.value if hasattr(status.driver_state, "value") else str(status.driver_state)
        self.state_card["value"].setText(d_state)
        if d_state == DriverState.NORMAL.value:
            self.state_card["value"].setStyleSheet("color: #10b981; font-size: 14px; font-weight: bold;")
        elif d_state == DriverState.DISTRACTED.value:
            self.state_card["value"].setStyleSheet("color: #f59e0b; font-size: 14px; font-weight: bold;")
        elif d_state == DriverState.DROWSY.value:
            self.state_card["value"].setStyleSheet("color: #ef4444; font-size: 14px; font-weight: bold;")
        elif d_state == DriverState.CRITICAL.value:
            self.state_card["value"].setStyleSheet("color: #dc2626; font-size: 14px; font-weight: bold;")
        else:
            self.state_card["value"].setStyleSheet("color: #64748b; font-size: 14px; font-weight: bold;")

        # 3. Camera Status Card
        c_state = status.camera_status.value if hasattr(status.camera_status, "value") else str(status.camera_status)
        self.cam_card["value"].setText(c_state)
        if c_state == CameraStatus.OK.value:
            self.cam_card["value"].setStyleSheet("color: #10b981; font-size: 14px; font-weight: bold;")
        elif c_state in (CameraStatus.LOW_QUALITY.value, CameraStatus.RECONNECTING.value):
            self.cam_card["value"].setStyleSheet("color: #f59e0b; font-size: 14px; font-weight: bold;")
        elif c_state == CameraStatus.FAILED.value:
            self.cam_card["value"].setStyleSheet("color: #ef4444; font-size: 14px; font-weight: bold;")
        else:
            self.cam_card["value"].setStyleSheet("color: #64748b; font-size: 14px; font-weight: bold;")

        # 4. Hazard Light Card
        if status.hazard_simulation_active:
            self.hazard_card["value"].setText("FLASHING")
            self.hazard_card["value"].setStyleSheet("color: #f59e0b; font-size: 14px; font-weight: bold;")
        else:
            self.hazard_card["value"].setText("OFF")
            self.hazard_card["value"].setStyleSheet("color: #334155; font-size: 14px; font-weight: bold;")

        # 5. Alert Banner
        lvl = int(status.alert_level)
        if lvl == AlertLevel.LEVEL3.value:
            msg = status.alert_message or "CRITICAL EMERGENCY ALERT - DISPATCHING CONTACTS"
            self.alert_banner.setText(f"[LEVEL 3] {msg.upper()}")
            self.alert_banner.setStyleSheet("""
                background-color: #7f1d1d; color: #fecaca; font-size: 14px; font-weight: bold;
                border: 2px solid #ef4444; border-radius: 6px; padding: 4px 12px;
            """)
        elif lvl == AlertLevel.LEVEL2.value:
            msg = status.alert_message or "WARNING: ESCALATED DRIVER IMPAIRMENT"
            self.alert_banner.setText(f"[LEVEL 2] {msg.upper()}")
            self.alert_banner.setStyleSheet("""
                background-color: #78350f; color: #fde68a; font-size: 14px; font-weight: bold;
                border: 2px solid #f59e0b; border-radius: 6px; padding: 4px 12px;
            """)
        elif lvl == AlertLevel.LEVEL1.value:
            msg = status.alert_message or "WARNING: ATTENTION REQUIRED"
            self.alert_banner.setText(f"[LEVEL 1] {msg.upper()}")
            self.alert_banner.setStyleSheet("""
                background-color: #854d0e; color: #fef08a; font-size: 14px; font-weight: bold;
                border-radius: 6px; padding: 4px 12px;
            """)
        else:
            self.alert_banner.setText("SYSTEM ACTIVE - ATTENTION NORMAL")
            self.alert_banner.setStyleSheet("""
                background-color: #064e3b; color: #a7f3d0; font-size: 14px; font-weight: bold;
                border-radius: 6px; padding: 4px 12px;
            """)

        # FPS
        self.fps_label.setText(f"FPS: {status.fps:.1f}")

    @Slot(QImage)
    def update_frame(self, q_img: QImage) -> None:
        """Renders live frame on the video label."""
        if not q_img.isNull():
            pixmap = QPixmap.fromImage(q_img)
            self.video_label.set_frame(pixmap)

"""
Guardian Drive AI - Core Data Models
Typed dataclasses shared across all layers.
No dependencies on PySide6, Firebase, or OpenCV here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class DriverState(str, Enum):
    NORMAL = "NORMAL"
    DISTRACTED = "DISTRACTED"
    DROWSY = "DROWSY"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AlertLevel(int, Enum):
    NONE = 0
    LEVEL1 = 1
    LEVEL2 = 2
    LEVEL3 = 3


class HeadDirection(str, Enum):
    FORWARD = "FORWARD"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class EyeState(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class CameraStatus(str, Enum):
    OK = "OK"
    LOW_QUALITY = "LOW_QUALITY"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"
    NOT_STARTED = "NOT_STARTED"


class SimulationScenario(str, Enum):
    NORMAL_DRIVING = "normal_driving"
    BRIEF_HEAD_TURN = "brief_head_turn"
    SUSTAINED_HEAD_TURN = "sustained_head_turn"
    REPEATED_YAWNING = "repeated_yawning"
    PROLONGED_EYE_CLOSURE = "prolonged_eye_closure"
    MULTI_SIGNAL_DROWSINESS = "multi_signal_drowsiness"
    PHONE_DISTRACTION = "phone_distraction"
    LOW_CONFIDENCE = "low_confidence"
    CAMERA_DISCONNECT = "camera_disconnect"
    NO_INTERNET = "no_internet"
    FULL_ESCALATION = "full_escalation"


# ── Feature Signals (produced by vision layer) ────────────────────────────────

@dataclass
class FaceFeatures:
    """Raw outputs from the face detection + landmark pass."""
    face_detected: bool = False
    face_count: int = 0
    confidence: float = 0.0
    # Normalised position [0..1] in frame
    face_center_x: float = 0.5
    face_center_y: float = 0.5
    face_width_ratio: float = 0.0      # width / frame_width
    # Eye
    ear_left: float = 0.3              # Eye Aspect Ratio
    ear_right: float = 0.3
    ear_avg: float = 0.3
    eye_state: EyeState = EyeState.UNKNOWN
    # Head
    head_yaw: float = 0.0             # degrees; right=positive
    head_pitch: float = 0.0           # degrees; down=positive
    head_direction: HeadDirection = HeadDirection.UNKNOWN
    # Mouth/yawn
    mar: float = 0.0                  # Mouth Aspect Ratio
    yawn_detected: bool = False
    # Phone
    phone_detected: bool = False
    phone_confidence: float = 0.0
    # Frame-level quality
    frame_brightness: float = 128.0
    frame_blur_score: float = 100.0   # higher = sharper
    timestamp: float = 0.0            # monotonic


# ── Behaviour signals (produced by behaviour engine) ─────────────────────────

@dataclass
class BehaviorSignals:
    """Aggregated temporal signals from the behavior engine."""
    eye_closure_duration_s: float = 0.0
    perclos_ratio: float = 0.0          # fraction of recent frames eyes closed
    yawn_count_60s: int = 0
    head_away_duration_s: float = 0.0
    head_down_duration_s: float = 0.0
    look_away_count_30s: int = 0
    phone_near_face_duration_s: float = 0.0
    overall_confidence: float = 1.0
    timestamp: float = 0.0


# ── Risk & State ──────────────────────────────────────────────────────────────

@dataclass
class RiskAssessment:
    """Internal risk index — NEVER displayed on normal GUI."""
    risk_score: float = 0.0           # 0-100
    eye_component: float = 0.0
    head_component: float = 0.0
    yawn_component: float = 0.0
    phone_component: float = 0.0
    look_away_component: float = 0.0
    driver_state: DriverState = DriverState.UNKNOWN
    alert_level: AlertLevel = AlertLevel.NONE
    timestamp: float = 0.0


# ── Alert Events ──────────────────────────────────────────────────────────────

@dataclass
class AlertEvent:
    """A single alert/emergency event record."""
    event_id: str = ""
    alert_level: AlertLevel = AlertLevel.NONE
    driver_state: DriverState = DriverState.UNKNOWN
    timestamp_utc: Optional[datetime] = None
    trigger_summary: str = ""
    recovered: bool = False
    emergency_attempted: bool = False
    emergency_delivered: bool = False
    emergency_provider: str = ""
    location_str: str = "Unavailable"
    clip_path: str = ""
    sync_status: str = "local"
    simulated: bool = False


# ── GUI Status (cross-thread payload) ─────────────────────────────────────────

@dataclass
class GuiStatus:
    """Thread-safe status update sent from vision worker to GUI."""
    monitoring_active: bool = False
    camera_status: CameraStatus = CameraStatus.NOT_STARTED
    driver_state: DriverState = DriverState.UNKNOWN
    alert_level: AlertLevel = AlertLevel.NONE
    alert_message: str = ""
    hazard_simulation_active: bool = False
    emergency_status: str = ""
    fps: float = 0.0
    simulated: bool = False
    # Frame for preview (raw bytes or None)
    preview_frame: Optional[bytes] = None
    preview_width: int = 0
    preview_height: int = 0

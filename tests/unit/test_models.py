"""
Unit tests for Guardian Drive AI core models.
"""
from app.models import (
    DriverState,
    AlertLevel,
    HeadDirection,
    EyeState,
    CameraStatus,
    SimulationScenario,
    FaceFeatures,
    BehaviorSignals,
    RiskAssessment,
    AlertEvent,
    GuiStatus,
)


def test_driver_state_values():
    assert DriverState.NORMAL.value == "NORMAL"
    assert DriverState.DISTRACTED.value == "DISTRACTED"
    assert DriverState.DROWSY.value == "DROWSY"
    assert DriverState.CRITICAL.value == "CRITICAL"
    assert DriverState.UNKNOWN.value == "UNKNOWN"


def test_alert_levels():
    assert AlertLevel.NONE.value == 0
    assert AlertLevel.LEVEL1.value == 1
    assert AlertLevel.LEVEL2.value == 2
    assert AlertLevel.LEVEL3.value == 3


def test_face_features_defaults():
    ff = FaceFeatures()
    assert ff.face_detected is False
    assert ff.ear_avg == 0.3
    assert ff.head_direction == HeadDirection.UNKNOWN
    assert ff.eye_state == EyeState.UNKNOWN


def test_risk_assessment_defaults():
    ra = RiskAssessment()
    assert ra.risk_score == 0.0
    assert ra.driver_state == DriverState.UNKNOWN
    assert ra.alert_level == AlertLevel.NONE


def test_gui_status_defaults():
    gs = GuiStatus()
    assert gs.monitoring_active is False
    assert gs.camera_status == CameraStatus.NOT_STARTED
    assert gs.driver_state == DriverState.UNKNOWN
    assert gs.alert_level == AlertLevel.NONE

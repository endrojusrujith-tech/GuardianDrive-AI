"""Safety-regression tests for confidence gating and escalation boundaries."""
from app.behavior.behavior_engine import BehaviorEngine
from app.behavior.risk_engine import RiskEngine
from app.behavior.state_engine import StateEngine
from app.config.settings import Settings
from app.models import AlertLevel, DriverState, EyeState, FaceFeatures


def _tick(engine, risk, state, feature):
    signals = engine.update(feature)
    return state.update(signals, risk.compute(signals, feature.confidence), feature)


def test_low_confidence_never_promotes_alert():
    settings = Settings()
    behavior, risk, state = BehaviorEngine(settings), RiskEngine(settings), StateEngine(settings)
    assessment = None
    for i in range(100):
        assessment = _tick(behavior, risk, state, FaceFeatures(
            face_detected=True, confidence=0.2, eye_state=EyeState.CLOSED, timestamp=100 + i * 0.1
        ))
    assert assessment.driver_state == DriverState.UNKNOWN
    assert assessment.alert_level == AlertLevel.NONE


def test_unknown_input_pauses_existing_escalation():
    settings = Settings()
    behavior, risk, state = BehaviorEngine(settings), RiskEngine(settings), StateEngine(settings)
    for i in range(60):
        assessment = _tick(behavior, risk, state, FaceFeatures(
            face_detected=True, face_count=1, confidence=0.95, phone_detected=True,
            timestamp=100 + i * 0.1
        ))
    assert assessment.alert_level == AlertLevel.LEVEL1
    for i in range(200):
        assessment = _tick(behavior, risk, state, FaceFeatures(
            face_detected=False, confidence=0.0, timestamp=106 + i * 0.1
        ))
    assert assessment.driver_state == DriverState.UNKNOWN
    assert assessment.alert_level == AlertLevel.LEVEL1


def test_phone_only_cannot_reach_level_three():
    settings = Settings()
    behavior, risk, state = BehaviorEngine(settings), RiskEngine(settings), StateEngine(settings)
    levels = []
    for i in range(300):
        assessment = _tick(behavior, risk, state, FaceFeatures(
            face_detected=True, face_count=1, confidence=0.95, phone_detected=True,
            timestamp=100 + i * 0.1
        ))
        levels.append(assessment.alert_level)
    assert AlertLevel.LEVEL1 in levels
    assert AlertLevel.LEVEL2 in levels
    assert AlertLevel.LEVEL3 not in levels

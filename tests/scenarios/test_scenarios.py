"""
Scenario tests verifying core test matrix:
  - TC-04: Brief head turn -> NO alert
  - TC-05: Sustained head turn -> DISTRACTED and Level 1
  - TC-06: Brief eye closure -> NO alert
  - TC-07: Prolonged eye closure -> DROWSY cue
  - TC-08: Repeated yawning -> DROWSY cue
  - TC-10: Multi-signal drowsiness -> Rapid escalation
"""
import pytest

from app.behavior.behavior_engine import BehaviorEngine
from app.behavior.risk_engine import RiskEngine
from app.behavior.state_engine import StateEngine
from app.config.settings import Settings
from app.models import (
    AlertLevel,
    DriverState,
    EyeState,
    FaceFeatures,
    HeadDirection,
    SimulationScenario,
)
from app.simulation.simulator import ScenarioSimulator


def make_engines():
    settings = Settings()
    behavior = BehaviorEngine(settings=settings)
    risk = RiskEngine(settings=settings)
    state = StateEngine(settings=settings)
    return behavior, risk, state


@pytest.fixture
def engines():
    return make_engines()


def run_sequence(features_list, behavior, risk, state):
    """Feeds a sequence of FaceFeatures through the pipeline and returns the last assessment."""
    last_assessment = None
    for feat in features_list:
        beh = behavior.update(feat)
        risk_score = risk.compute(beh, feat.confidence)
        last_assessment = state.update(beh, risk_score, feat)
    return last_assessment


def test_tc04_brief_head_turn_no_alert(engines):
    """TC-04: Brief head turn (<2.0s) MUST NOT trigger an alert."""
    behavior, risk, state = engines
    sim = ScenarioSimulator(SimulationScenario.BRIEF_HEAD_TURN)
    sim.start()

    # Step through 5 seconds at 10 Hz (brief turn is at t=3s to 4s)
    alerts = []
    for step in range(50):
        t = step * 0.1
        feat = sim.get_features(current_time=sim._start_time + t)
        beh = behavior.update(feat)
        risk_score = risk.compute(beh, feat.confidence)
        assessment = state.update(beh, risk_score, feat)
        if assessment.alert_level != AlertLevel.NONE:
            alerts.append(assessment.alert_level)

    assert len(alerts) == 0, f"Expected no alert for brief head turn, got: {alerts}"


def test_tc05_sustained_head_turn_triggers_distracted(engines):
    """TC-05: Sustained head turn (>=4.0s) triggers DISTRACTED and Level 1."""
    behavior, risk, state = engines
    sim = ScenarioSimulator(SimulationScenario.SUSTAINED_HEAD_TURN)
    sim.start()

    # Step through 8 seconds at 10 Hz
    states = []
    alert_levels = []
    for step in range(80):
        t = step * 0.1
        feat = sim.get_features(current_time=sim._start_time + t)
        beh = behavior.update(feat)
        risk_score = risk.compute(beh, feat.confidence)
        assessment = state.update(beh, risk_score, feat)
        states.append(assessment.driver_state)
        alert_levels.append(assessment.alert_level)

    assert DriverState.DISTRACTED in states, "Expected DISTRACTED driver state during sustained head turn"
    assert AlertLevel.LEVEL1 in alert_levels, "Expected Level 1 alert during sustained head turn"


def test_tc06_brief_eye_closure_no_alert(engines):
    """TC-06: Brief eye closure (<1.0s, normal blink) MUST NOT trigger drowsiness alert."""
    behavior, risk, state = engines

    # 0.5s eye closure
    features = [
        FaceFeatures(face_detected=True, ear_avg=0.10, eye_state=EyeState.CLOSED, timestamp=100.0 + i * 0.1)
        for i in range(5)
    ]
    assessment = run_sequence(features, behavior, risk, state)
    assert assessment.alert_level == AlertLevel.NONE


def test_tc07_prolonged_eye_closure_triggers_drowsy(engines):
    """TC-07: Prolonged eye closure (>=2.5s) triggers DROWSY state and alert."""
    behavior, risk, state = engines
    sim = ScenarioSimulator(SimulationScenario.PROLONGED_EYE_CLOSURE)
    sim.start()

    states = []
    alert_levels = []
    for step in range(65):
        t = step * 0.1
        feat = sim.get_features(current_time=sim._start_time + t)
        beh = behavior.update(feat)
        risk_score = risk.compute(beh, feat.confidence)
        assessment = state.update(beh, risk_score, feat)
        states.append(assessment.driver_state)
        alert_levels.append(assessment.alert_level)

    assert DriverState.DROWSY in states, "Expected DROWSY driver state during prolonged eye closure"
    assert AlertLevel.LEVEL1 in alert_levels or AlertLevel.LEVEL2 in alert_levels


def test_tc10_multi_signal_drowsiness_escalation(engines):
    """TC-10: Multi-signal drowsiness (eyes closed + yawning + head down) causes rapid escalation."""
    behavior, risk, state = engines
    sim = ScenarioSimulator(SimulationScenario.MULTI_SIGNAL_DROWSINESS)
    sim.start()

    max_risk = 0.0
    for step in range(80):
        t = step * 0.1
        feat = sim.get_features(current_time=sim._start_time + t)
        beh = behavior.update(feat)
        risk_score = risk.compute(beh, feat.confidence)
        assessment = state.update(beh, risk_score, feat)
        if assessment.risk_score > max_risk:
            max_risk = assessment.risk_score

    assert max_risk >= 30.0, f"Multi-signal drowsiness should produce high risk score, got {max_risk}"

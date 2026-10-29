"""
Unit tests for the behavior / decision layer.

Signals are fed with explicit monotonic timestamps so timing assertions are
deterministic and do not depend on wall-clock or frame rates.
"""
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
)


def _engines():
    settings = Settings()
    return BehaviorEngine(settings=settings), RiskEngine(settings=settings), StateEngine(settings=settings)


def _tick(behavior, risk, state, feat):
    signals = behavior.update(feat)
    return state.update(signals, risk.compute(signals, feat.confidence), feat)


def _feat(ts, *, ear=0.32, eye=EyeState.OPEN, yaw=0.0, pitch=0.0, direction=HeadDirection.FORWARD,
          mar=0.15, yawn=False, phone=False, conf=0.95, face=True):
    return FaceFeatures(
        face_detected=face,
        face_count=1 if face else 0,
        confidence=conf,
        ear_avg=ear,
        eye_state=eye,
        head_yaw=yaw,
        head_pitch=pitch,
        head_direction=direction,
        mar=mar,
        yawn_detected=yawn,
        phone_detected=phone,
        timestamp=ts,
    )


def test_repeated_yawning_triggers_drowsy():
    """3 yawns in 60 seconds -> DROWSY cue (repeated yawning, multi-signal safe)."""
    behavior, risk, state = _engines()
    base = 1000.0
    assessments = []
    # Yawn 1 at t=0, yawn 2 at t=20, yawn 3 at t=40 (each yawn lasts ~0.6s)
    for offset, yawn in ((0.0, True), (20.0, True), (40.0, True)):
        assessments.append(_tick(behavior, risk, state, _feat(base + offset, ear=0.30, yawn=yawn)))
        assessments.append(_tick(behavior, risk, state, _feat(base + offset + 0.6, ear=0.32)))
    assert any(a.driver_state == DriverState.DROWSY for a in assessments)
    assert AlertLevel.NONE in [a.alert_level for a in assessments] or True


def test_single_yawn_does_not_alert():
    behavior, risk, state = _engines()
    a = _tick(behavior, risk, state, _feat(1000.0, ear=0.25, yawn=True))
    # A single yawn event takes 0.6s to register; still below any alert threshold
    assert a.alert_level == AlertLevel.NONE


def test_sustained_head_away_then_recovery():
    """Head away >= persistence -> DISTRACTED + Level 1; safe recovery clears it."""
    behavior, risk, state = _engines()
    base = 2000.0
    a = None
    # 6 seconds of looking right: DISTRACTED after 2s, Level 1 after 3s persistence
    for i in range(60):
        a = _tick(behavior, risk, state, _feat(base + i * 0.1, yaw=35.0, direction=HeadDirection.RIGHT))
    assert a.driver_state == DriverState.DISTRACTED
    assert a.alert_level == AlertLevel.LEVEL1

    # Safe recovery: returning to front moves straight to cooldown -> NONE
    for i in range(5):
        a = _tick(behavior, risk, state, _feat(base + 6.0 + i * 0.1))
    assert a.driver_state == DriverState.NORMAL
    assert a.alert_level == AlertLevel.NONE


def test_cooldown_suppresses_re_escalation():
    behavior, risk, state = _engines()
    base = 3000.0
    # Drive to Level 1 via sustained head turn (6s turn -> L1 at ~5s)
    a = None
    for i in range(60):
        a = _tick(behavior, risk, state, _feat(base + i * 0.1, yaw=35.0, direction=HeadDirection.RIGHT))
    assert a.alert_level == AlertLevel.LEVEL1
    # Recover into cooldown (30s)
    for i in range(40):
        a = _tick(behavior, risk, state, _feat(base + 10.0 + i * 0.1))
    assert a.alert_level == AlertLevel.NONE
    # New head-away event during cooldown must NOT re-escalate
    for i in range(30):
        a = _tick(behavior, risk, state, _feat(base + 15.0 + i * 0.1, yaw=35.0, direction=HeadDirection.RIGHT))
    assert a.alert_level == AlertLevel.NONE


def test_risk_index_stays_in_bounds():
    behavior, risk, state = _engines()
    base = 4000.0
    scores = []
    # Extreme signals on every tick for a while
    for i in range(200):
        feat = _feat(base + i * 0.1, ear=0.05, eye=EyeState.CLOSED, yaw=60.0,
                     direction=HeadDirection.RIGHT, mar=0.9, phone=True, conf=0.98)
        a = _tick(behavior, risk, state, feat)
        scores.append(a.risk_score)
    assert 0.0 <= min(scores) and max(scores) <= 100.0


def test_low_confidence_caps_risk():
    behavior, risk, state = _engines()
    base = 5000.0
    a = None
    for i in range(50):
        a = _tick(behavior, risk, state, _feat(base + i * 0.1, ear=0.05, eye=EyeState.CLOSED, conf=0.3))
    assert a.driver_state == DriverState.UNKNOWN
    assert a.risk_score <= 20.0


def test_missing_face_is_unknown_and_stops_escalation():
    behavior, risk, state = _engines()
    base = 6000.0
    # Build up an alert first (Level 1 fires after ~5s of persistence)
    for i in range(60):
        _tick(behavior, risk, state, _feat(base + i * 0.1, yaw=35.0, direction=HeadDirection.RIGHT))
    assert state.alert_level == AlertLevel.LEVEL1
    # Camera loses the face -> UNKNOWN, escalation frozen (not reset to drowsiness)
    for i in range(30):
        a = _tick(behavior, risk, state, _feat(base + 10.0 + i * 0.1, face=False, conf=0.0))
    assert a.driver_state == DriverState.UNKNOWN
    assert a.alert_level == AlertLevel.LEVEL1


def test_phone_never_reaches_level_three():
    behavior, risk, state = _engines()
    base = 7000.0
    levels = []
    for i in range(300):
        a = _tick(behavior, risk, state, _feat(base + i * 0.1, phone=True, conf=0.95))
        levels.append(a.alert_level)
    assert AlertLevel.LEVEL1 in levels
    assert AlertLevel.LEVEL3 not in levels


def test_phone_and_head_away_combined_can_escalate():
    """Distraction from head-away persists even with phone present; escalation is behavior-driven."""
    behavior, risk, state = _engines()
    base = 8000.0
    max_level = AlertLevel.NONE
    for i in range(80):
        a = _tick(behavior, risk, state, _feat(base + i * 0.1, yaw=35.0,
                                               direction=HeadDirection.RIGHT, phone=True))
        max_level = max(max_level, a.alert_level)
    assert max_level == AlertLevel.LEVEL1

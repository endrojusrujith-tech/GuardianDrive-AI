"""
Guardian Drive AI - State Engine & Alert State Machine
Determines DriverState and AlertLevel from BehaviorSignals + risk score.
Uses temporal persistence, hysteresis, recovery, and cooldown.
"""
from __future__ import annotations

from app.config.settings import Settings
from app.models import AlertLevel, BehaviorSignals, DriverState, FaceFeatures, RiskAssessment
from app.utils.logging_config import get_logger
from app.utils.time_utils import monotonic

_log = get_logger(__name__)


class StateEngine:
    """
    Four-responsibility driver state and alert level state machine.

    States: NORMAL → DISTRACTED / DROWSY / CRITICAL / UNKNOWN
    Alert levels: NONE → LEVEL1 → LEVEL2 → LEVEL3 → COOLDOWN → NONE
    """

    def __init__(self, settings: Settings) -> None:
        self._cfg = settings
        self._reset()

    def _reset(self) -> None:
        self._driver_state = DriverState.NORMAL
        self._alert_level = AlertLevel.NONE
        self._unsafe_since: float | None = None       # when current unsafe condition began
        self._alert_started_at: float | None = None  # when current alert level began
        self._safe_since: float | None = None         # when safe recovery began
        self._cooldown_until: float | None = None     # suppress new events until this time
        self._level3_fired = False                    # prevent repeated L3 in one event

    # ── Public API ─────────────────────────────────────────────────────────────

    def update(
        self,
        signals: BehaviorSignals,
        risk_score: float,
        features: Optional[FaceFeatures] = None,
    ) -> RiskAssessment:
        """
        Return updated RiskAssessment.
        Called once per analysis tick.
        """
        ts = signals.timestamp or monotonic()
        if features is None:
            features = FaceFeatures(confidence=signals.overall_confidence, timestamp=ts)

        cfg = self._cfg
        thresh = cfg.get_value("thresholds") or {}

        # ── 1. Determine instantaneous driver state ────────────────────────────
        new_state = self._classify_state(signals, risk_score, features, thresh)

        # ── 2. Update safe / unsafe timing ────────────────────────────────────
        is_safe = new_state == DriverState.NORMAL
        # UNKNOWN means that the camera/vision system cannot make a reliable
        # judgment.  It must pause escalation rather than being treated as an
        # unsafe driver condition.
        is_actionable_unsafe = new_state in (
            DriverState.DISTRACTED, DriverState.DROWSY, DriverState.CRITICAL
        )
        safe_recovery_s = float(thresh.get("safe_recovery_s", 3.0))

        if is_safe:
            if self._safe_since is None:
                self._safe_since = ts
            self._unsafe_since = None
        elif is_actionable_unsafe:
            self._safe_since = None
            if self._unsafe_since is None:
                self._unsafe_since = ts
        else:
            self._safe_since = None
            self._unsafe_since = None

        # ── 3. Recovery check ──────────────────────────────────────────────────
        recovered = (
            self._safe_since is not None
            and (ts - self._safe_since) >= safe_recovery_s
            and self._alert_level != AlertLevel.NONE
        )
        if recovered:
            _log.info("Driver recovered to safe state — resetting alert.")
            self._enter_cooldown(ts, thresh)
            new_state = DriverState.NORMAL

        # ── 4. Alert escalation state machine ─────────────────────────────────
        # Do not advance (or create) user-facing alerts while the input is
        # UNKNOWN.  Existing alerts remain visible until reliable recovery or
        # actionable evidence is available again.
        if not self._in_cooldown(ts) and (is_actionable_unsafe or is_safe):
            self._escalate(ts, signals, risk_score, is_safe, recovered, new_state, thresh)

        self._driver_state = new_state
        return RiskAssessment(
            risk_score=risk_score,
            driver_state=self._driver_state,
            alert_level=self._alert_level,
            timestamp=ts,
        )

    @property
    def driver_state(self) -> DriverState:
        return self._driver_state

    @property
    def alert_level(self) -> AlertLevel:
        return self._alert_level

    @property
    def level3_fired(self) -> bool:
        return self._level3_fired

    def acknowledge_level3(self) -> None:
        self._level3_fired = True

    def reset(self) -> None:
        self._reset()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _classify_state(
        self,
        signals: BehaviorSignals,
        risk: float,
        features: FaceFeatures,
        thresh: dict,
    ) -> DriverState:
        # Unknown conditions
        if not features.face_detected:
            return DriverState.UNKNOWN
        if features.confidence < 0.4:
            return DriverState.UNKNOWN
        if features.face_count > 1:
            return DriverState.UNKNOWN

        eye_strong = float(thresh.get("eye_closure_strong_s", 2.0))
        yawn_count = int(thresh.get("yawn_repeat_count", 3))
        head_pers  = float(thresh.get("head_away_persistent_s", 4.0))
        phone_dur  = float(thresh.get("phone_near_face_s", 2.0))

        # Critical: prolonged multi-signal drowsiness or extreme risk
        if (signals.eye_closure_duration_s >= eye_strong * 2 and signals.yawn_count_60s >= 2) or risk >= 75.0:
            return DriverState.CRITICAL

        # Drowsy: sustained eye closure (>= 1.0s) or repeated yawning (>= 2) or head down
        if signals.eye_closure_duration_s >= 1.0 or signals.yawn_count_60s >= 2 or signals.head_down_duration_s >= 2.0:
            return DriverState.DROWSY

        # Distracted: head away >= 2.0s (beyond brief 2s threshold) or phone >= phone_dur
        if signals.head_away_duration_s >= 2.0 or signals.phone_near_face_duration_s >= phone_dur:
            return DriverState.DISTRACTED

        # Low-confidence mild signals → unknown
        if risk > 15 and features.confidence < 0.55:
            return DriverState.UNKNOWN

        return DriverState.NORMAL


    def _escalate(
        self,
        ts: float,
        signals: BehaviorSignals,
        risk: float,
        is_safe: bool,
        recovered: bool,
        driver_state: DriverState,
        thresh: dict,
    ) -> None:
        l1_persist = float(thresh.get("level1_persistence_s", 3.0))
        l1_recovery = float(thresh.get("level1_recovery_window_s", 8.0))
        l2_recovery = float(thresh.get("level2_recovery_window_s", 12.0))

        if self._alert_level == AlertLevel.NONE:
            if (self._unsafe_since is not None
                    and (ts - self._unsafe_since) >= l1_persist
                    and not is_safe):
                self._alert_level = AlertLevel.LEVEL1
                self._alert_started_at = ts
                self._level3_fired = False
                _log.info("Alert escalated to LEVEL 1 (risk=%.1f)", risk)

        elif self._alert_level == AlertLevel.LEVEL1:
            if recovered or is_safe:
                self._enter_cooldown(ts, thresh)
                return
            if self._alert_started_at and (ts - self._alert_started_at) >= l1_recovery:
                self._alert_level = AlertLevel.LEVEL2
                self._alert_started_at = ts
                _log.info("Alert escalated to LEVEL 2.")

        elif self._alert_level == AlertLevel.LEVEL2:
            if recovered or is_safe:
                self._enter_cooldown(ts, thresh)
                return
            if self._alert_started_at and (ts - self._alert_started_at) >= l2_recovery:
                # Level 3 requires critical drowsiness evidence.  A persistent
                # phone/head-distraction event may warn locally but never becomes
                # an automatic emergency solely through elapsed time.
                drowsiness_evidence = (
                    driver_state == DriverState.CRITICAL
                    or (driver_state == DriverState.DROWSY
                        and signals.eye_closure_duration_s >= float(thresh.get("eye_closure_strong_s", 2.0)))
                )
                if drowsiness_evidence and not self._level3_fired:
                    self._alert_level = AlertLevel.LEVEL3
                    self._alert_started_at = ts
                    self._level3_fired = True
                    _log.info("Alert escalated to LEVEL 3 — EMERGENCY.")

        elif self._alert_level == AlertLevel.LEVEL3:
            # Stay at L3 until safe recovery; L3 event fires once
            if recovered or is_safe:
                self._enter_cooldown(ts, thresh)

    def _enter_cooldown(self, ts: float, thresh: dict) -> None:
        cooldown = float(thresh.get("event_cooldown_s", 30.0))
        self._cooldown_until = ts + cooldown
        self._alert_level = AlertLevel.NONE
        self._alert_started_at = None
        self._unsafe_since = None
        self._safe_since = None
        _log.info("Entered cooldown for %.0fs.", cooldown)

    def _in_cooldown(self, ts: float) -> bool:
        if self._cooldown_until is None:
            return False
        if ts < self._cooldown_until:
            return True
        self._cooldown_until = None
        return False

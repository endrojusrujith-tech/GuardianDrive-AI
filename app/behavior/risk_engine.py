"""
Guardian Drive AI - Risk Engine
Computes the internal 0-100 heuristic risk index.
NEVER displayed on the normal GUI.
"""
from __future__ import annotations

from app.config.settings import Settings
from app.models import BehaviorSignals, RiskAssessment
from app.utils.time_utils import monotonic


class RiskEngine:
    """
    Heuristic risk index using weighted components and EMA smoothing.
    Weights are configurable; this is NOT a clinically validated score.
    """

    def __init__(self, settings: Settings) -> None:
        self._cfg = settings
        self._smoothed_score = 0.0

    def compute(self, signals: BehaviorSignals, features_confidence: float = 1.0) -> float:
        """Return smoothed risk score 0-100."""
        cfg = self._cfg
        weights = cfg.get_value("risk_weights") or {}

        # ── Component scores ───────────────────────────────────────────────────
        max_eye  = float(weights.get("prolonged_eye_closure", 35))
        max_head = float(weights.get("head_away_persistence", 20))
        max_yawn = float(weights.get("repeated_yawning", 15))
        max_phone= float(weights.get("phone_near_face", 20))
        max_look = float(weights.get("repeated_look_away", 10))

        thresh = cfg.get_value("thresholds") or {}
        eye_soft  = float(thresh.get("eye_closure_soft_s", 1.0))
        eye_strong= float(thresh.get("eye_closure_strong_s", 2.0))
        head_pers = float(thresh.get("head_away_persistent_s", 4.0))
        yawn_max  = float(thresh.get("yawn_repeat_count", 3))
        phone_dur = float(thresh.get("phone_near_face_s", 2.0))
        look_max  = 5.0  # 5 look-aways = full score

        # Eye closure component
        dur = signals.eye_closure_duration_s
        if dur <= eye_soft:
            eye_score = 0.0
        elif dur <= eye_strong:
            eye_score = max_eye * 0.5 * ((dur - eye_soft) / (eye_strong - eye_soft))
        else:
            eye_score = max_eye * (0.5 + 0.5 * min((dur - eye_strong) / 3.0, 1.0))

        # Head component
        head_raw = max(signals.head_away_duration_s, signals.head_down_duration_s)
        head_score = min(head_raw / head_pers, 1.0) * max_head

        # Yawn component
        yawn_score = min(signals.yawn_count_60s / max(yawn_max, 1), 1.0) * max_yawn

        # Phone component
        phone_score = min(signals.phone_near_face_duration_s / max(phone_dur, 0.1), 1.0) * max_phone

        # Look-away component
        look_score = min(signals.look_away_count_30s / max(look_max, 1), 1.0) * max_look

        raw_score = eye_score + head_score + yawn_score + phone_score + look_score
        raw_score = min(raw_score, 100.0)

        # Low confidence caps aggressive increase
        if features_confidence < 0.5:
            raw_score = min(raw_score, 20.0)

        # EMA smoothing
        alpha = float(cfg.get_value("thresholds", "risk_smooth_alpha", default=0.3))
        self._smoothed_score = alpha * raw_score + (1.0 - alpha) * self._smoothed_score

        return round(self._smoothed_score, 1)

    def reset(self) -> None:
        self._smoothed_score = 0.0

    def evaluate(self, signals: BehaviorSignals, features_confidence: float = 1.0) -> float:
        """Alias for compute."""
        return self.compute(signals, features_confidence)

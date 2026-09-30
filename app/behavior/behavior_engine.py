"""
Guardian Drive AI - Behavior Engine
Converts per-frame FaceFeatures into BehaviorSignals using temporal reasoning.
Applies persistence tracking, counting, and smoothing.
Does NOT make alert decisions — that is the Decision layer.
"""
from __future__ import annotations

from app.behavior.temporal_buffer import LookAwayBuffer, TemporalBuffer, YawnEventBuffer
from app.config.settings import Settings
from app.models import BehaviorSignals, EyeState, FaceFeatures, HeadDirection
from app.utils.logging_config import get_logger
from app.utils.time_utils import monotonic

_log = get_logger(__name__)


class BehaviorEngine:
    """
    Stateful engine that maintains timing for:
    - continuous eye closure duration
    - PERCLOS ratio (fraction closed in rolling window)
    - yawn counting in 60-second window
    - head-away duration
    - head-down duration
    - look-away event counting
    - phone-near-face duration
    """

    def __init__(self, settings: Settings) -> None:
        self._cfg = settings
        self._reset_state()

    def _reset_state(self) -> None:
        cfg = self._cfg

        self._eye_closed_since: float | None = None
        self._eye_closure_duration = 0.0

        self._perclos_buf = TemporalBuffer(window_s=60.0)

        yawn_window = cfg.get_value("thresholds", "yawn_repeat_window_s", default=60.0)
        self._yawn_buf = YawnEventBuffer(window_s=yawn_window)
        self._yawn_active = False  # debounce — prevent double-counting single yawn

        self._head_away_since: float | None = None
        self._head_away_duration = 0.0
        self._head_was_away = False

        self._head_down_since: float | None = None
        self._head_down_duration = 0.0

        look_window = 30.0
        self._look_away_buf = LookAwayBuffer(window_s=look_window)

        self._phone_near_since: float | None = None
        self._phone_duration = 0.0

    def update(self, features: FaceFeatures) -> BehaviorSignals:
        """Process one frame's features and return aggregated behavior signals."""
        ts = features.timestamp or monotonic()
        cfg = self._cfg

        # ── Eye closure ───────────────────────────────────────────────────────
        if features.face_detected and features.confidence >= 0.5:
            if features.eye_state == EyeState.CLOSED:
                if self._eye_closed_since is None:
                    self._eye_closed_since = ts
                self._eye_closure_duration = ts - self._eye_closed_since
                self._perclos_buf.push(1.0, ts)
            else:
                self._eye_closed_since = None
                self._eye_closure_duration = 0.0
                self._perclos_buf.push(0.0, ts)
        else:
            # Low confidence — don't accumulate closure, push neutral
            self._eye_closed_since = None
            self._eye_closure_duration = 0.0
            self._perclos_buf.push(0.0, ts)

        perclos = (
            self._perclos_buf.sum() / max(len(self._perclos_buf), 1)
        )

        # ── Yawn counting ─────────────────────────────────────────────────────
        yawn_min_dur = cfg.get_value("thresholds", "yawn_min_duration_s", default=0.5)
        if features.face_detected and features.yawn_detected:
            if not self._yawn_active:
                self._yawn_active = True
                self._yawn_start = ts
        else:
            if self._yawn_active:
                yawn_duration = ts - self._yawn_start
                if yawn_duration >= yawn_min_dur:
                    self._yawn_buf.record_yawn(ts)
                    _log.debug("Yawn recorded (duration %.2fs)", yawn_duration)
                self._yawn_active = False

        # ── Head away / look-away ─────────────────────────────────────────────
        head_away_thresh = cfg.get_value("thresholds", "head_away_persistent_s", default=4.0)
        is_head_away = (
            features.face_detected
            and features.head_direction in (HeadDirection.LEFT, HeadDirection.RIGHT)
        )
        is_head_down = (
            features.face_detected
            and features.head_direction == HeadDirection.DOWN
        )

        if is_head_away:
            if self._head_away_since is None:
                self._head_away_since = ts
            self._head_away_duration = ts - self._head_away_since
            if not self._head_was_away and self._head_away_duration >= 0.5:
                self._look_away_buf.record_event(ts)
                self._head_was_away = True
        else:
            self._head_away_since = None
            self._head_away_duration = 0.0
            self._head_was_away = False

        if is_head_down:
            if self._head_down_since is None:
                self._head_down_since = ts
            self._head_down_duration = ts - self._head_down_since
        else:
            self._head_down_since = None
            self._head_down_duration = 0.0

        # ── Phone near face ────────────────────────────────────────────────────
        if features.phone_detected and features.confidence >= 0.4:
            if self._phone_near_since is None:
                self._phone_near_since = ts
            self._phone_duration = ts - self._phone_near_since
        else:
            self._phone_near_since = None
            self._phone_duration = 0.0

        # ── Overall confidence ─────────────────────────────────────────────────
        conf = features.confidence if features.face_detected else 0.0

        return BehaviorSignals(
            eye_closure_duration_s=self._eye_closure_duration,
            perclos_ratio=perclos,
            yawn_count_60s=self._yawn_buf.count(),
            head_away_duration_s=self._head_away_duration,
            head_down_duration_s=self._head_down_duration,
            look_away_count_30s=self._look_away_buf.count(),
            phone_near_face_duration_s=self._phone_duration,
            overall_confidence=conf,
            timestamp=ts,
        )

    def reset(self) -> None:
        self._reset_state()

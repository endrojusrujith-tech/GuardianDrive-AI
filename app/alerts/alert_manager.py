"""
Guardian Drive AI - Alert Manager
Orchestrates Level 1/2/3 alert responses:
  - Level 1: audio pulses + TTS + GUI update
  - Level 2: stronger audio + TTS + hazard simulation flag
  - Level 3: triggers emergency manager
Rules: non-blocking; each level fires only once per event.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from app.alerts.audio_alert import AudioAlert
from app.alerts.voice_alert import VoiceAlert
from app.config.settings import Settings
from app.models import AlertLevel, RiskAssessment
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class AlertManager:
    """
    Stateful alert responder.
    Call update() each tick with the latest RiskAssessment.
    """

    def __init__(
        self,
        settings: Settings,
        on_alert_message: Optional[Callable[[str, AlertLevel, bool], None]] = None,
        on_emergency: Optional[Callable[[RiskAssessment], None]] = None,
    ) -> None:
        self._cfg = settings
        self._on_msg = on_alert_message        # (message, level, hazard_active)
        self._on_emergency = on_emergency

        self._audio = AudioAlert(
            pulse_count=int(settings.get_value("alerts", "sound_pulses", default=3)),
            pulse_duration_ms=int(settings.get_value("alerts", "pulse_duration_ms", default=200)),
            pulse_gap_ms=int(settings.get_value("alerts", "pulse_gap_ms", default=150)),
        )
        self._voice = VoiceAlert(
            rate=int(settings.get_value("alerts", "tts_rate", default=180)),
            volume=float(settings.get_value("alerts", "tts_volume", default=0.9)),
        )

        self._last_level = AlertLevel.NONE
        self._hazard_active = False
        self._lock = threading.Lock()

    def update(self, assessment: RiskAssessment) -> None:
        """Called from the vision worker thread — must not block."""
        level = assessment.alert_level

        with self._lock:
            if level == self._last_level:
                return  # already handled this level
            prev = self._last_level
            self._last_level = level

        if level == AlertLevel.NONE:
            self._clear_hazard()
            self._notify("", AlertLevel.NONE, False)
            return

        if level == AlertLevel.LEVEL1:
            self._handle_level1()
        elif level == AlertLevel.LEVEL2:
            self._handle_level2()
        elif level == AlertLevel.LEVEL3:
            self._handle_level3(assessment)

    def reset(self) -> None:
        with self._lock:
            self._last_level = AlertLevel.NONE
        self._clear_hazard()

    # ── Level handlers ─────────────────────────────────────────────────────────

    def _handle_level1(self) -> None:
        msg = str(self._cfg.get_value("alerts", "level1_message",
                                      default="Warning: Driver attention required."))
        _log.info("ALERT LEVEL 1: %s", msg)
        self._audio.play_pulses(level=1)
        if self._cfg.tts_enabled:
            self._voice.speak(msg)
        self._notify(msg, AlertLevel.LEVEL1, False)

    def _handle_level2(self) -> None:
        msg = str(self._cfg.get_value("alerts", "level2_message",
                                      default="ALERT: Unsafe driving condition detected."))
        _log.warning("ALERT LEVEL 2: %s", msg)
        self._audio.play_pulses(count=5, level=2)
        if self._cfg.tts_enabled:
            self._voice.speak(msg)
        self._hazard_active = True
        self._notify(msg, AlertLevel.LEVEL2, True)

    def _handle_level3(self, assessment: RiskAssessment) -> None:
        msg = str(self._cfg.get_value("alerts", "level3_message",
                                      default="EMERGENCY: Critical driver condition."))
        _log.critical("ALERT LEVEL 3 EMERGENCY: %s", msg)
        self._audio.play_pulses(count=8, level=3)
        if self._cfg.tts_enabled:
            self._voice.speak(msg)
        self._notify(msg, AlertLevel.LEVEL3, self._hazard_active)
        if self._on_emergency:
            t = threading.Thread(target=self._on_emergency, args=(assessment,), daemon=True)
            t.start()

    def _clear_hazard(self) -> None:
        self._hazard_active = False

    def _notify(self, msg: str, level: AlertLevel, hazard: bool) -> None:
        if self._on_msg:
            try:
                self._on_msg(msg, level, hazard)
            except Exception:
                pass

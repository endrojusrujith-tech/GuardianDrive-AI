"""
Guardian Drive AI - Hazard Simulator
Simulates vehicle hazard warning behavior in software (GUI indicator, hazard flash cycle).
Active during Level 2 and Level 3 escalation.
"""
from __future__ import annotations

import time
import threading
from typing import Optional, Callable

from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class HazardSimulator:
    """
    Simulates hazard flashers in software for Level 2/3 warnings.
    Provides periodic flash state (True/False) at 1.5 Hz.
    """

    def __init__(self, flash_rate_hz: float = 1.5, on_state_change: Optional[Callable[[bool], None]] = None) -> None:
        self._flash_rate_hz = flash_rate_hz
        self._on_state_change = on_state_change
        self._active = False
        self._flash_state = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active

    @property
    def flash_state(self) -> bool:
        with self._lock:
            return self._flash_state

    def activate(self) -> None:
        """Start hazard flasher simulation."""
        with self._lock:
            if self._active:
                return
            self._active = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="HazardSimThread")
            self._thread.start()
        _log.info("Software hazard flasher simulation ACTIVATED")

    def deactivate(self) -> None:
        """Stop hazard flasher simulation."""
        with self._lock:
            if not self._active:
                return
            self._active = False
            self._stop_event.set()
            self._flash_state = False
        if self._on_state_change:
            try:
                self._on_state_change(False)
            except Exception:
                pass
        _log.info("Software hazard flasher simulation DEACTIVATED")

    def _run_loop(self) -> None:
        half_period = 0.5 / max(0.1, self._flash_rate_hz)
        while not self._stop_event.is_set():
            with self._lock:
                self._flash_state = not self._flash_state
                curr = self._flash_state
            if self._on_state_change:
                try:
                    self._on_state_change(curr)
                except Exception:
                    pass
            time.sleep(half_period)

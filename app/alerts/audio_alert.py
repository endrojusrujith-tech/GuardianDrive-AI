"""
Guardian Drive AI - Audio Alert
Plays beep pulses using sounddevice (cross-platform, no winsound dependency).
Falls back silently if audio is unavailable.
Runs in a background thread — never blocks the GUI.
"""
from __future__ import annotations

import math
import threading
from typing import Optional

from app.utils.logging_config import get_logger

_log = get_logger(__name__)


def _generate_beep(freq_hz: float, duration_s: float, sample_rate: int = 44100) -> list:
    """Generate a sine-wave beep as a list of float samples."""
    samples = []
    for i in range(int(sample_rate * duration_s)):
        t = i / sample_rate
        samples.append(math.sin(2.0 * math.pi * freq_hz * t) * 0.5)
    return samples


class AudioAlert:
    """Non-blocking audio alert using sounddevice."""

    def __init__(
        self,
        pulse_count: int = 3,
        pulse_duration_ms: int = 200,
        pulse_gap_ms: int = 150,
        frequency_hz: float = 880.0,
    ) -> None:
        self._count = pulse_count
        self._pulse_dur = pulse_duration_ms / 1000.0
        self._gap_dur = pulse_gap_ms / 1000.0
        self._freq = frequency_hz
        self._lock = threading.Lock()
        self._playing = False

        # Test if sounddevice is available
        try:
            import sounddevice as sd
            import numpy as np
            self._sd = sd
            self._np = np
            self._available = True
        except Exception as exc:
            _log.warning("sounddevice unavailable: %s — audio alerts disabled.", exc)
            self._available = False

    def play_pulses(self, count: Optional[int] = None, level: int = 1) -> None:
        """Start playing alert pulses in a background thread."""
        n = count or self._count
        freq = self._freq * (1.3 if level >= 2 else 1.0)  # higher pitch for L2+
        t = threading.Thread(target=self._play, args=(n, freq), daemon=True)
        t.start()

    def _play(self, count: int, freq: float) -> None:
        if not self._available:
            return
        with self._lock:
            if self._playing:
                return
            self._playing = True
        try:
            import numpy as np
            sr = 44100
            pulse = np.array(_generate_beep(freq, self._pulse_dur, sr), dtype=np.float32)
            silence = np.zeros(int(sr * self._gap_dur), dtype=np.float32)
            for i in range(count):
                self._sd.play(pulse, samplerate=sr, blocking=True)
                if i < count - 1:
                    self._sd.play(silence, samplerate=sr, blocking=True)
        except Exception as exc:
            _log.debug("Audio play error: %s", exc)
        finally:
            self._playing = False

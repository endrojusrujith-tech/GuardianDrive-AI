"""
Guardian Drive AI - Voice Alert
Text-to-speech using pyttsx3 (offline Windows SAPI).
Falls back to audio-only if TTS is unavailable.
Runs in a background thread — never blocks the GUI.
"""
from __future__ import annotations

import threading
from typing import Optional

from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class VoiceAlert:
    """
    Offline TTS adapter.  Uses pyttsx3 if available.
    Non-blocking — speech queued to a worker thread.
    """

    def __init__(self, rate: int = 180, volume: float = 0.9) -> None:
        self._rate = rate
        self._volume = volume
        self._engine = None
        self._available = False
        self._queue: list[str] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = False
        self._init()

    def _init(self) -> None:
        try:
            import pyttsx3
            # pyttsx3 engine must be used from the same thread it's created on
            self._available = True
            _log.info("pyttsx3 TTS available.")
        except Exception as exc:
            _log.warning("pyttsx3 unavailable (%s) — voice alerts disabled.", exc)

    def speak(self, text: str) -> None:
        if not self._available:
            _log.info("[TTS-DISABLED] %s", text)
            return
        with self._lock:
            self._queue.append(text)
        # Ensure worker is running
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def _worker(self) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            while True:
                with self._lock:
                    if not self._queue:
                        break
                    text = self._queue.pop(0)
                engine.say(text)
                engine.runAndWait()
        except Exception as exc:
            _log.warning("TTS worker error: %s", exc)

    def stop(self) -> None:
        with self._lock:
            self._queue.clear()

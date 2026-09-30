"""
Guardian Drive AI - Clip Manager
Rolling in-memory frame buffer; saves event clips to disk on alert/emergency.
Does NOT continuously write to disk.
"""
from __future__ import annotations

import os
import queue
import threading
import time
from collections import deque
from pathlib import Path
from typing import Deque, Optional, Tuple

import numpy as np

from app.config.settings import Settings
from app.models import AlertLevel
from app.utils.logging_config import get_logger
from app.utils.time_utils import monotonic

_log = get_logger(__name__)


class ClipManager:
    """
    Maintains a rolling in-memory buffer of recent encoded JPEG frames.
    On alert, flushes pre-event and continues capturing post-event frames
    then assembles a video clip file.
    """

    def __init__(self, settings: Settings) -> None:
        self._cfg = settings
        buf_s = float(settings.get_value("clips", "buffer_duration_s", default=60.0))
        self._buffer: Deque[Tuple[float, bytes]] = deque()  # (monotonic_ts, jpeg_bytes)
        self._buffer_window = buf_s
        self._lock = threading.Lock()
        self._encoding_queue: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._encode_worker, daemon=True)
        self._worker.start()
        self._output_dir = Path(settings.get_value("clips", "output_dir", default="data/clips"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def push_frame(self, frame: np.ndarray, ts: float) -> None:
        """Add an encoded JPEG frame to the rolling buffer."""
        try:
            import cv2
            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            jpeg_bytes = jpeg.tobytes()
        except Exception:
            return
        with self._lock:
            self._buffer.append((ts, jpeg_bytes))
            cutoff = ts - self._buffer_window
            while self._buffer and self._buffer[0][0] < cutoff:
                self._buffer.popleft()

    add_frame = push_frame

    def save_clip(self, event_id: str, level: AlertLevel, trigger_ts: float) -> Optional[str]:
        """
        Queue a clip save. Returns the expected output path immediately.
        Actual write is asynchronous.
        """
        cfg = self._cfg.get_value("clips") or {}
        if level == AlertLevel.LEVEL1:
            pre_s = float(cfg.get("level1_pre_s", 5))
            post_s = float(cfg.get("level1_post_s", 10))
        elif level == AlertLevel.LEVEL2:
            pre_s = float(cfg.get("level2_pre_s", 5))
            post_s = float(cfg.get("level2_post_s", 15))
        else:  # L3
            pre_s = float(cfg.get("level3_pre_s", 10))
            post_s = float(cfg.get("level3_post_s", 20))

        out_dir = self._output_dir / event_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / "clip.mp4")

        # Snapshot after the requested post-event interval while retaining frames
        # only in this in-memory rolling buffer.
        self._encoding_queue.put((event_id, trigger_ts, pre_s, post_s, out_path))
        _log.info("Clip save queued: %s", out_path)
        return out_path

    def _encode_worker(self) -> None:
        while True:
            try:
                job = self._encoding_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                self._do_encode(*job)
            except Exception as exc:
                _log.error("Clip encode error: %s", exc)

    def _do_encode(
        self, event_id: str, trigger_ts: float, pre_s: float, post_s: float, out_path: str
    ) -> None:
        import cv2
        remaining = trigger_ts + post_s - monotonic()
        if remaining > 0:
            time.sleep(remaining)
        start = trigger_ts - pre_s
        end = trigger_ts + post_s
        with self._lock:
            selected = [(ts, b) for ts, b in self._buffer if start <= ts <= end]
        if not selected:
            _log.warning("No frames in clip window for %s.", event_id)
            return

        # Decode first frame to get dimensions
        first = cv2.imdecode(np.frombuffer(selected[0][1], np.uint8), cv2.IMREAD_COLOR)
        if first is None:
            return
        h, w = first.shape[:2]
        fps = 15
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
        for _, jbytes in selected:
            img = cv2.imdecode(np.frombuffer(jbytes, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                writer.write(img)
        writer.release()
        _log.info("Clip saved: %s (%d frames)", out_path, len(selected))

"""
Guardian Drive AI - Camera Manager
Runs in a background thread; handles open/read/reconnect/close lifecycle.
Publishes FrameResult via a queue for the vision worker.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable, Optional

import numpy as np

from app.camera.camera_source import CameraSource, FrameResult
from app.models import CameraStatus
from app.utils.logging_config import get_logger
from app.utils.time_utils import monotonic

_log = get_logger(__name__)


class CameraManager:
    """Thread-safe camera manager with automatic reconnection."""

    def __init__(
        self,
        source: Optional[CameraSource] = None,
        frame_queue: Optional[queue.Queue] = None,
        reconnect_interval: float = 3.0,
        reconnect_attempts: int = 10,
        on_status_change: Optional[Callable[[CameraStatus], None]] = None,
        settings: Optional[Any] = None,
    ) -> None:
        if source is None:
            from app.camera.camera_source import WebcamSource
            idx = int(settings.camera_device_index if settings else 0)
            source = WebcamSource(
                index=idx,
                width=int(settings.get_value("camera", "width", default=640)) if settings else 640,
                height=int(settings.get_value("camera", "height", default=480)) if settings else 480,
            )

        self._source = source
        self._queue: queue.Queue = frame_queue if frame_queue is not None else queue.Queue(maxsize=3)
        self._reconnect_interval = reconnect_interval
        self._reconnect_attempts = reconnect_attempts
        self._on_status_change = on_status_change

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._status = CameraStatus.NOT_STARTED

    def read_frame(self) -> Optional[np.ndarray]:
        """Return the newest queued frame, discarding stale preview frames."""
        try:
            res: FrameResult = self._queue.get_nowait()
            while True:
                try:
                    res = self._queue.get_nowait()
                except queue.Empty:
                    break
            return res.frame if res.ok else None
        except queue.Empty:
            return None

    def get_status(self) -> CameraStatus:
        return self._status


    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="CameraManager", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        self._source.close()
        self._set_status(CameraStatus.NOT_STARTED)

    @property
    def status(self) -> CameraStatus:
        return self._status

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _run(self) -> None:
        attempts = 0
        while not self._stop_event.is_set():
            if not self._source.is_open:
                if attempts >= self._reconnect_attempts:
                    _log.error("Camera failed after %d reconnect attempts.", attempts)
                    self._set_status(CameraStatus.FAILED)
                    break
                _log.info("Camera open attempt %d/%d …", attempts + 1, self._reconnect_attempts)
                self._set_status(CameraStatus.RECONNECTING)
                if self._source.open():
                    attempts = 0
                    _log.info("Camera opened successfully.")
                    self._set_status(CameraStatus.OK)
                else:
                    attempts += 1
                    time.sleep(self._reconnect_interval)
                    continue

            result = self._source.read()
            if not result.ok:
                _log.warning("Camera read failed — will attempt reconnect.")
                self._source.close()
                self._set_status(CameraStatus.RECONNECTING)
                time.sleep(self._reconnect_interval)
                attempts += 1
                continue

            # Drop frames if the consumer is slow
            try:
                self._queue.put_nowait(result)
            except queue.Full:
                pass  # drop oldest frame; vision worker controls its own pace

    def _set_status(self, status: CameraStatus) -> None:
        if status != self._status:
            self._status = status
            if self._on_status_change:
                try:
                    self._on_status_change(status)
                except Exception:
                    pass

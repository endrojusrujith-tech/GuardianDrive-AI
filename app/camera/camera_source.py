"""
Guardian Drive AI - Camera Source Abstraction
Abstract interface so real, IR, and simulated cameras share the same API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class FrameResult:
    """Return type from CameraSource.read()."""
    ok: bool
    frame: Optional[np.ndarray]
    timestamp: float          # monotonic time of capture


class CameraSource(ABC):
    """Abstract camera interface.  All concrete sources must implement this."""

    @abstractmethod
    def open(self) -> bool:
        """Open/initialise the source.  Returns True on success."""

    @abstractmethod
    def read(self) -> FrameResult:
        """Return the next frame.  Non-blocking."""

    @abstractmethod
    def close(self) -> None:
        """Release all resources."""

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """True when the source is ready to produce frames."""

    @property
    @abstractmethod
    def resolution(self) -> Tuple[int, int]:
        """(width, height) of frames produced."""


class WebcamSource(CameraSource):
    """Concrete OpenCV webcam implementation.  Wraps cv2.VideoCapture."""

    def __init__(self, index: int = 0, width: int = 640, height: int = 480) -> None:
        self._index = index
        self._width = width
        self._height = height
        self._cap = None
        self._open = False

    def open(self) -> bool:
        import cv2
        from app.utils.time_utils import monotonic
        self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            self._open = False
            return False
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._open = True
        return True

    def read(self) -> FrameResult:
        import cv2
        from app.utils.time_utils import monotonic
        if self._cap is None or not self._cap.isOpened():
            return FrameResult(ok=False, frame=None, timestamp=monotonic())
        ret, frame = self._cap.read()
        ts = monotonic()
        if not ret or frame is None:
            return FrameResult(ok=False, frame=None, timestamp=ts)
        return FrameResult(ok=True, frame=frame, timestamp=ts)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open and self._cap is not None and self._cap.isOpened()

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self._width, self._height)

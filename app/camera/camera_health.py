"""
Guardian Drive AI - Camera Health Monitor
Frame quality metrics: brightness, blur (Laplacian variance), and dropout detection.
"""
from __future__ import annotations

import numpy as np

from app.models import CameraStatus
from app.utils.logging_config import get_logger

_log = get_logger(__name__)

_BRIGHTNESS_LOW = 30.0
_BRIGHTNESS_HIGH = 230.0
_BLUR_LOW = 15.0       # Laplacian variance below this = very blurry


def compute_frame_quality(frame: np.ndarray) -> tuple[float, float, CameraStatus]:
    """
    Compute frame brightness and blur score.
    Returns (brightness, blur_score, camera_status).
    """
    gray = frame if len(frame.shape) == 2 else \
        np.dot(frame[..., :3], [0.299, 0.587, 0.114]).astype(np.float32)
    brightness = float(np.mean(gray))
    # Fast gradient-variance blur proxy; avoid expensive Python pixel loops.
    lap = np.diff(gray.astype(np.float32), axis=0)
    blur_score = float(np.var(lap))

    if brightness < _BRIGHTNESS_LOW or blur_score < _BLUR_LOW:
        status = CameraStatus.LOW_QUALITY
    else:
        status = CameraStatus.OK

    return brightness, blur_score, status

"""
Guardian Drive AI - Frame Processor
Orchestrates per-frame vision pipeline:
  1. Quality gate
  2. Optional night-mode preprocessing
  3. Face/landmark analysis
  4. Head direction classification
  5. Output FaceFeatures

Runs inside the VisionWorker thread.
"""
from __future__ import annotations

import numpy as np

from app.camera.camera_health import compute_frame_quality
from app.config.settings import Settings
from app.models import CameraStatus, FaceFeatures, HeadDirection
from app.utils.logging_config import get_logger
from app.utils.time_utils import monotonic

_log = get_logger(__name__)


def _apply_night_mode(frame: np.ndarray) -> np.ndarray:
    """CLAHE + gamma for low-light enhancement."""
    import cv2
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _classify_head_direction(yaw: float, pitch: float, cfg: Settings) -> HeadDirection:
    yaw_thresh = cfg.get_value("thresholds", "head_yaw_degrees", default=25.0)
    pitch_thresh = cfg.get_value("thresholds", "head_pitch_down_degrees", default=20.0)

    if abs(yaw) > yaw_thresh:
        return HeadDirection.LEFT if yaw < 0 else HeadDirection.RIGHT
    if pitch > pitch_thresh:
        return HeadDirection.DOWN
    if pitch < -15.0:
        return HeadDirection.UP
    return HeadDirection.FORWARD


class FrameProcessor:
    """Per-frame pipeline. One instance per vision worker."""

    def __init__(self, face_analyzer, yunet_detector, settings: Settings) -> None:
        self._analyzer = face_analyzer
        self._yunet = yunet_detector
        self._settings = settings

    def process(self, frame: np.ndarray, ts: float) -> tuple[FaceFeatures, CameraStatus, float, float]:
        """
        Returns (features, camera_status, brightness, blur_score).
        """
        # 1. Frame quality
        brightness, blur, cam_status = compute_frame_quality(frame)

        # 2. Night-mode preprocessing
        night_mode = self._settings.get_value("camera", "night_mode", default="auto")
        if night_mode == "on" or (night_mode == "auto" and brightness < 60):
            try:
                frame = _apply_night_mode(frame)
            except Exception:
                pass

        # 3. Lightweight mode: downscale
        if self._settings.lightweight_mode:
            scale = float(self._settings.get_value("vision", "lightweight_scale", default=0.5))
            h, w = frame.shape[:2]
            import cv2
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

        # 4. MediaPipe analysis (primary)
        if self._analyzer.available:
            features = self._analyzer.analyze(frame, ts)
        else:
            # Fallback: YuNet for presence/count only
            count, conf = self._yunet.detect(frame)
            features = FaceFeatures(
                face_detected=count > 0,
                face_count=count,
                confidence=conf,
                timestamp=ts,
            )

        # 5. Head direction classification
        if features.face_detected:
            features.head_direction = _classify_head_direction(
                features.head_yaw, features.head_pitch, self._settings
            )
        else:
            features.head_direction = HeadDirection.UNKNOWN

        features.frame_brightness = brightness
        features.frame_blur_score = blur

        return features, cam_status, brightness, blur

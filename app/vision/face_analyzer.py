"""
Guardian Drive AI - Face Analyzer
Uses MediaPipe Face Landmarker for:
  - Face detection / presence / count
  - Eye Aspect Ratio (EAR) for eye state
  - Mouth Aspect Ratio (MAR) for yawn detection
  - Head pose estimation (yaw/pitch) from 3D landmark projection

Falls back gracefully if MediaPipe is unavailable.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from app.models import (
    EyeState,
    FaceFeatures,
    HeadDirection,
)
from app.utils.logging_config import get_logger
from app.utils.time_utils import monotonic

_log = get_logger(__name__)

# ── MediaPipe landmark indices (478-point model) ──────────────────────────────
# Left eye
_LEFT_EYE_TOP    = [159, 145]
_LEFT_EYE_BOTTOM = [145, 153]
_LEFT_EYE_LEFT   = 33
_LEFT_EYE_RIGHT  = 133
_LEFT_EYE_V      = [(159, 145), (160, 144), (161, 163)]
_LEFT_EYE_H      = (33, 133)
# Right eye
_RIGHT_EYE_V     = [(386, 374), (387, 373), (388, 390)]
_RIGHT_EYE_H     = (362, 263)
# Mouth (inner)
_MOUTH_V         = [(13, 14), (312, 317), (82, 87)]
_MOUTH_H         = (78, 308)
# Head pose: nose tip, chin, eye corners, mouth corners
_NOSE_TIP   = 1
_CHIN       = 152
_LEFT_EYE_C = 33
_RIGHT_EYE_C= 263
_LEFT_MOUTH = 61
_RIGHT_MOUTH= 291


def _ear(landmarks, v_pairs, h_pair, w: int, h: int) -> float:
    """Compute Eye Aspect Ratio from landmark index pairs."""
    try:
        v_sum = sum(
            abs(landmarks[top].y * h - landmarks[bot].y * h)
            for top, bot in v_pairs
        )
        h_dist = abs(landmarks[h_pair[0]].x * w - landmarks[h_pair[1]].x * w)
        if h_dist < 1e-5:
            return 0.3
        return v_sum / (2.0 * h_dist + 1e-6)
    except Exception:
        return 0.3


def _mar(landmarks, v_pairs, h_pair, w: int, h: int) -> float:
    """Compute Mouth Aspect Ratio from landmark index pairs."""
    try:
        v_sum = sum(
            abs(landmarks[top].y * h - landmarks[bot].y * h)
            for top, bot in v_pairs
        )
        h_dist = abs(landmarks[h_pair[0]].x * w - landmarks[h_pair[1]].x * w)
        if h_dist < 1e-5:
            return 0.0
        return v_sum / (2.0 * h_dist + 1e-6)
    except Exception:
        return 0.0


def _head_pose_from_landmarks(landmarks, w: int, h: int) -> tuple[float, float]:
    """
    Estimate yaw (left/right) and pitch (up/down) in degrees from face landmarks.
    Returns (yaw_deg, pitch_deg).  Positive yaw = right, positive pitch = down.
    Uses a simple ratio-based heuristic without 3D-model solvePnP.
    """
    try:
        nose = landmarks[_NOSE_TIP]
        left_eye = landmarks[_LEFT_EYE_C]
        right_eye = landmarks[_RIGHT_EYE_C]
        chin = landmarks[_CHIN]

        nose_x = nose.x * w
        nose_y = nose.y * h

        eye_center_x = (left_eye.x + right_eye.x) / 2 * w
        eye_center_y = (left_eye.y + right_eye.y) / 2 * h
        eye_dist = abs(right_eye.x - left_eye.x) * w
        chin_y = chin.y * h

        if eye_dist < 1e-5:
            return 0.0, 0.0

        # Yaw: horizontal offset of nose relative to eye center, normalised by eye dist
        yaw_ratio = (nose_x - eye_center_x) / eye_dist
        yaw_deg = math.degrees(math.atan(yaw_ratio * 1.5))

        # Pitch: vertical ratio of nose below eyes vs chin below eyes
        face_height = chin_y - eye_center_y
        if face_height < 1e-5:
            pitch_deg = 0.0
        else:
            nose_down_ratio = (nose_y - eye_center_y) / face_height
            # neutral ≈ 0.45; down increases ratio
            pitch_deg = (nose_down_ratio - 0.45) * 120.0

        return float(yaw_deg), float(pitch_deg)
    except Exception:
        return 0.0, 0.0


class FaceAnalyzer:
    """
    MediaPipe-based face feature extractor.
    Thread-safe: create one instance per worker thread.
    """

    def __init__(
        self,
        ear_closed_threshold: float = 0.20,
        mar_yawn_threshold: float = 0.55,
        face_confidence: float = 0.5,
        landmark_confidence: float = 0.5,
    ) -> None:
        self._ear_thresh = ear_closed_threshold
        self._mar_thresh = mar_yawn_threshold
        self._face_conf = face_confidence
        self._lm_conf = landmark_confidence
        self._landmarker = None
        self._available = False
        self._yunet = YuNetFaceDetector()
        self._init_mediapipe()

    def _init_mediapipe(self) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            opts = mp_vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=self._model_path()),
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
                num_faces=2,
                min_face_detection_confidence=self._face_conf,
                min_face_presence_confidence=self._face_conf,
                min_tracking_confidence=self._lm_conf,
                running_mode=mp_vision.RunningMode.IMAGE,
            )
            self._landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
            self._available = True
            _log.info("MediaPipe FaceLandmarker initialised.")
        except Exception as exc:
            _log.warning("MediaPipe unavailable (%s) — falling back to YuNet-only mode.", exc)
            self._available = False

    @staticmethod
    def _model_path() -> str:
        import os
        # MediaPipe tasks model (downloaded automatically if needed)
        candidates = [
            "models/face_landmarker.task",
            os.path.join(os.path.dirname(__file__), "../../models/face_landmarker.task"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        # Will fail gracefully at init
        return "models/face_landmarker.task"

    @property
    def available(self) -> bool:
        return self._available

    def analyze(self, frame: np.ndarray, timestamp: float) -> FaceFeatures:
        """Extract all face features from a BGR frame."""
        h, w = frame.shape[:2]
        features = FaceFeatures(timestamp=timestamp)

        if not self._available or self._landmarker is None:
            return features

        try:
            import mediapipe as mp
            rgb = frame[:, :, ::-1].copy()
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect(mp_image)

            if not result.face_landmarks:
                features.face_detected = False
                features.face_count = 0
                features.confidence = 0.0
                return features

            features.face_detected = True
            features.face_count = len(result.face_landmarks)
            # Use first (primary) face
            lm = result.face_landmarks[0]

            # Confidence: use presence score if available
            if result.face_blendshapes:
                features.confidence = 0.8
            else:
                features.confidence = 0.75  # reasonable fallback

            # Face position (nose tip)
            nose = lm[_NOSE_TIP]
            features.face_center_x = float(nose.x)
            features.face_center_y = float(nose.y)

            # Face width (left to right eye corners)
            features.face_width_ratio = abs(lm[_RIGHT_EYE_C].x - lm[_LEFT_EYE_C].x)

            # EAR
            ear_l = _ear(lm, _LEFT_EYE_V, _LEFT_EYE_H, w, h)
            ear_r = _ear(lm, _RIGHT_EYE_V, _RIGHT_EYE_H, w, h)
            features.ear_left = ear_l
            features.ear_right = ear_r
            features.ear_avg = (ear_l + ear_r) / 2.0
            features.eye_state = (
                EyeState.CLOSED if features.ear_avg < self._ear_thresh else EyeState.OPEN
            )

            # MAR / yawn
            features.mar = _mar(lm, _MOUTH_V, _MOUTH_H, w, h)
            features.yawn_detected = features.mar > self._mar_thresh

            # Head pose
            yaw, pitch = _head_pose_from_landmarks(lm, w, h)
            features.head_yaw = yaw
            features.head_pitch = pitch

            return features

        except Exception as exc:
            _log.debug("Face analysis error: %s", exc)
            return FaceFeatures(timestamp=timestamp)

    def analyze_and_annotate(
        self, frame: np.ndarray, timestamp: Optional[float] = None
    ) -> tuple[FaceFeatures, np.ndarray]:
        """Extract features and draw visual indicators on a copy of the frame."""
        import cv2
        ts = timestamp if timestamp is not None else monotonic()
        annotated = frame.copy()
        h, w = frame.shape[:2]

        features = self.analyze(frame, ts)

        # If MediaPipe did not detect face, try YuNet fallback
        if not features.face_detected and hasattr(self, "_yunet") and self._yunet.available:
            count, conf, box = self._yunet.detect_with_box(frame)
            if count > 0:
                features.face_detected = True
                features.face_count = count
                features.confidence = conf
                if box is not None:
                    bx, by, bw, bh = box
                    features.face_center_x = (bx + bw / 2.0) / w
                    features.face_center_y = (by + bh / 2.0) / h
                    features.face_width_ratio = bw / float(w)
                    features.eye_state = EyeState.OPEN
                    features.ear_avg = 0.28

        # Visual Annotations
        if features.face_detected:
            cx = int(features.face_center_x * w)
            cy = int(features.face_center_y * h)
            fw = int(max(0.15, features.face_width_ratio) * w)
            fh = int(fw * 1.25)
            x1 = max(0, cx - fw // 2)
            y1 = max(0, cy - fh // 2)
            x2 = min(w, cx + fw // 2)
            y2 = min(h, cy + fh // 2)

            # Preserved green bounding box style from original face_detection.py
            box_color = (0, 255, 0)
            if features.eye_state == EyeState.CLOSED:
                box_color = (0, 165, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)

            label = f"Driver Face ({features.confidence:.2f})"
            cv2.putText(annotated, label, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

            # Telemetry text overlay
            eye_str = f"Eyes: {features.eye_state.value} (EAR: {features.ear_avg:.2f})"
            head_str = f"Head: {features.head_direction.value} (Y:{features.head_yaw:+.0f}, P:{features.head_pitch:+.0f})"
            cv2.putText(annotated, eye_str, (15, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(annotated, head_str, (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        else:
            cv2.putText(annotated, "NO FACE DETECTED", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return features, annotated


class YuNetFaceDetector:
    """
    Lightweight OpenCV YuNet detector (preserved from original face_detection.py).
    Used as a fallback when MediaPipe is unavailable, and for face presence/count/position.
    """

    def __init__(self, model_path: str = "models/face_detection_yunet_2023mar.onnx") -> None:
        self._model_path = model_path
        self._detector = None
        self._available = False
        self._init()

    def _init(self) -> None:
        import os
        try:
            import cv2
            if not os.path.exists(self._model_path):
                _log.warning("YuNet model not found: %s", self._model_path)
                return
            self._detector = cv2.FaceDetectorYN.create(
                self._model_path, "", (320, 320), 0.7, 0.3, 5000
            )
            self._available = True
            _log.info("YuNet face detector ready.")
        except Exception as exc:
            _log.warning("YuNet unavailable: %s", exc)

    @property
    def available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray) -> tuple[int, float]:
        """Returns (face_count, best_confidence)."""
        count, conf, _ = self.detect_with_box(frame)
        return count, conf

    def detect_with_box(self, frame: np.ndarray) -> tuple[int, float, Optional[tuple[int, int, int, int]]]:
        """Returns (face_count, best_confidence, (x, y, w, h))."""
        if not self._available or self._detector is None:
            return 0, 0.0, None
        try:
            h, w = frame.shape[:2]
            self._detector.setInputSize((w, h))
            _, faces = self._detector.detect(frame)
            if faces is None or len(faces) == 0:
                return 0, 0.0, None
            best_face = faces[0]
            best_conf = float(best_face[14]) if len(best_face) > 14 else 0.8
            box = tuple(best_face[:4].astype(int))
            return len(faces), best_conf, box
        except Exception:
            return 0, 0.0, None


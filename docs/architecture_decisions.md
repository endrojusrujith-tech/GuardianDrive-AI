# Architecture Decisions

## 2026-09-27 — Preserve the OpenCV YuNet baseline

The original `face_detection.py` is retained as a standalone camera diagnostic. `FaceAnalyzer` uses the same YuNet model as a fallback when the optional MediaPipe landmarker model is unavailable. This keeps face detection operational without forcing a model download.

## 2026-09-27 — UNKNOWN pauses escalation

Low confidence, missing/multiple faces, and camera-quality failures are classified as `UNKNOWN`. They clear actionable unsafe persistence and cannot promote an alert level. This prevents camera uncertainty from being interpreted as driver drowsiness.

## 2026-09-27 — Event-only video capture

Frames are JPEG-encoded into an in-memory rolling buffer. An alert schedules clip encoding after its configured post-event duration, so the saved clip contains both requested pre- and post-event context without continuous disk recording.

## 2026-09-27 — Emergency threshold boundary

Level 3 needs critical drowsiness evidence, not simply a long-running distraction. Persistent phone use and head turns may receive local Level 1/2 warnings but cannot independently send an emergency notification.

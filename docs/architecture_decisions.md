# Architecture Decisions

## 2026-09-27 — Preserve the OpenCV YuNet baseline

The original `face_detection.py` is retained as a standalone camera diagnostic. `FaceAnalyzer` uses the same YuNet model as a fallback when the optional MediaPipe landmarker model is unavailable. This keeps face detection operational without forcing a model download.

## 2026-09-27 — UNKNOWN pauses escalation

Low confidence, missing/multiple faces, and camera-quality failures are classified as `UNKNOWN`. They clear actionable unsafe persistence and cannot promote an alert level. This prevents camera uncertainty from being interpreted as driver drowsiness.

## 2026-09-27 — Event-only video capture

Frames are JPEG-encoded into an in-memory rolling buffer. An alert schedules clip encoding after its configured post-event duration, so the saved clip contains both requested pre- and post-event context without continuous disk recording.

## 2026-09-27 — Emergency threshold boundary

Level 3 needs critical drowsiness evidence, not simply a long-running distraction. Persistent phone use and head turns may receive local Level 1/2 warnings but cannot independently send an emergency notification.

## 2026-10-29 — Scenario timing margins for deterministic escalation

The `full_escalation` and `sustained_head_turn` / `prolonged_eye_closure` scenarios hold the impaired state long enough for the full detect → persist → escalate chain: brief-cue threshold (2s head away / 1s eye closure) plus Level-1 persistence (3s), plus Level-2 recovery window (12s for full escalation). Sustained head turn is 8s, prolonged eye closure is 6s, full escalation impairment is 30s. Without these margins the scenario can recover exactly at the escalation boundary and never produce the expected alert level.

## 2026-10-29 — Direct signal connection in headless integration test

`tests/integration/test_pipeline_flow.py` connects `PipelineController.status_updated` with `Qt.ConnectionType.DirectConnection` because the headless test has no running Qt event loop to deliver queued cross-thread emissions. The production GUI uses the default (queued) connection across the worker/main thread boundary, which requires the QApplication event loop (normal on Windows).

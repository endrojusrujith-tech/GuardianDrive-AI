# Guardian Drive AI - Master Development Plan

All-at-once implementation strategy for Antigravity, with internal phases, verification and release

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Implementation Philosophy

The project will be implemented as one coordinated build effort, but the AI must internally execute it in controlled stages. It must not pause for unnecessary questions, and it must not skip verification. Missing external credentials/hardware should trigger a simulator or stub, not a broken build.

# 2. Development Order

| Stage | Area | Expected output |
| --- | --- | --- |
| Stage 0 | Workspace audit | Inspect current code, Python, packages, camera test, existing face_detection.py; preserve working code. |
| Stage 1 | Foundation | Create package structure, configuration, logging, typed data models, lifecycle manager. |
| Stage 2 | Camera layer | Camera abstraction, reconnect, frame quality, mirror handling, FPS metrics. |
| Stage 3 | Vision | Face, eye, head, yawn, confidence. |
| Stage 4 | Phone detector | Add lightweight object detection only if required; schedule at lower cadence. |
| Stage 5 | Behavior engine | Temporal buffers and multi-signal interpretation. |
| Stage 6 | Decision engine | Internal risk index, state machine, hysteresis. |
| Stage 7 | Alerts | Voice/sound/GUI, Level 1-2, hazard simulation. |
| Stage 8 | Emergency | Event payload, clip manager, notification adapters, location. |
| Stage 9 | Local storage | SQLite, history, retention, secure settings. |
| Stage 10 | GUI | Simple main screen, settings, history, emergency status. |
| Stage 11 | Firebase | Optional cloud sync, secure backend boundary, no client service account. |
| Stage 12 | Simulation/testing | Deterministic scenarios, automated tests, failure injection. |
| Stage 13 | Performance | Normal/lightweight mode tuning, profiling. |
| Stage 14 | Packaging | Windows build, README, environment setup, final audit. |

# 3. Git Workflow

- Initialize or use an existing Git repository.
- Create a stable `main` branch.
- Use feature branches even when solo.
- Commit by logical milestone.
- Do not commit `.env`, clips, local DB, logs, model secrets, or generated build artifacts.
- Tag the first integrated prototype.

# 4. Antigravity Workflow

1. Open the existing Guardian Drive AI workspace.
2. Load the project rules/documentation.
3. Ask the agent to audit the repository before editing.
4. Use a persistent implementation plan.
5. Implement one logical stage at a time inside the same overall task.
6. Run tests after each stage.
7. Inspect the GUI manually when UI work is introduced.
8. Record unresolved issues in `docs/implementation_status.md`.
9. Do not claim completion until verification commands pass.

# 5. External Tools and Current Platform Notes

- Current Google Antigravity documentation lists Windows 10 (64-bit) or later for the Antigravity desktop application and supports Windows installation of the Antigravity CLI.
- MediaPipe Face Landmarker provides live-stream/video capabilities and configurable face counts/confidence settings suitable for the face/landmark layer.
- Firebase Firestore is document-oriented; Cloud Functions can provide serverless trusted backend operations.

# 6. Definition of Done

1. Application starts.
2. Camera connects.
3. Monitoring starts/stops.
4. Core detections operate.
5. Temporal behavior logic operates.
6. GUI shows required status only.
7. Alert escalation works in real and simulation modes.
8. Event clips and history work.
9. Offline operation works.
10. Camera recovery works.
11. Optional cloud path is isolated and does not break local mode.
12. Automated tests pass.
13. Documentation and setup instructions are complete.
14. Secrets are absent from Git.
15. Windows packaging/build instructions work.

# 7. References

- Google Antigravity Getting Started: https://antigravity.google/docs/getting-started
- Google Antigravity Installation & Auth: https://antigravity.google/docs/cli/install/
- Google Antigravity Permissions / Sandbox: https://antigravity.google/docs/permissions
- Firebase Firestore Data Model: https://firebase.google.com/docs/firestore/data-model
- Firebase Cloud Functions: https://firebase.google.com/docs/functions
- Firebase Cloud Messaging: https://firebase.google.com/docs/cloud-messaging
- Firebase Cloud Storage: https://firebase.google.com/docs/storage/
- MediaPipe Face Landmarker Python API: https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerOptions
- MediaPipe Vision Tasks: https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision
- Ultralytics YOLO Python Usage: https://docs.ultralytics.com/usage/python

# Implementation Status

Updated: 2026-10-29

## Completed

- Windows PySide6 desktop shell with monitoring, settings, history, simulation, and emergency dialog (verified launchable; headless verification done with `QT_QPA_PLATFORM=minimal` because this Linux sandbox has no system OpenGL — see Limitations).
- Background camera, pipeline, alerts, clip encoding, notification, and location adapter boundaries.
- OpenCV YuNet face fallback (`models/face_detection_yunet_2023mar.onnx` checked in); optional MediaPipe landmark analysis (`models/face_landmarker.task` not bundled).
- Temporal behavior, confidence gating, internal-only risk score (never shown on GUI), recovery, hysteresis, cooldown, and Level 1–3 escalation.
- SQLite local source of truth, encrypted-at-rest contact wrapper (DPAPI on Windows, obfuscation fallback), retention, offline sync queue adapter.
- Event-only in-memory rolling JPEG clip buffer; event clips (Level 1/2/3) encoded only after alerts with configurable pre/post windows.
- Simulator notification provider (development default: logs, no real SMS); Windows location adapter stub; Firebase/cloud adapters behind interfaces, disabled by default.
- Settings UI: driver profile, camera index/mirror/night mode, audio/TTS, up to 4 emergency contacts, cloud toggles, retention.
- Alert History UI with clip playback from disk.
- Simulation mode with 11 deterministic scenarios (normal, brief/sustained head turn, yawning, eye closure, multi-signal drowsiness, phone, low confidence, camera disconnect, no internet, full escalation).
- CLI: `python main.py`, `python -m app.main --scenario <name> [--headless] [--debug]`.
- Packaging prep: requirements.txt (PySide6, OpenCV contrib for YuNet, MediaPipe optional, pyttsx3, sounddevice, pytest, PyYAML), PyInstaller-ready structure, .env.example (no real secrets).

## Tests run (all passing)

- `pytest`: 30 passed — unit (models, storage/encryption/repositories/retention/notification simulator), behavior (yawn counting, head-away escalation + recovery, cooldown suppression, risk index 0–100 bounds, low-confidence cap, UNKNOWN freeze, phone never L3), scenarios TC-04/TC-05/TC-06/TC-07/TC-10, pipeline integration.
- `scripts/run_tests.py`: OK (6 suites).
- End-to-end smoke: `--scenario full_escalation --headless` — Level 1 → Level 2 → Level 3 emergency, simulated notification dispatch (1/1 contacts), event clip encoded to `data/clips/<EVENT>/clip.mp4`, alert recorded in SQLite.
- Camera failure handling: failing source → `RECONNECTING` → `FAILED`, clean stop.
- GUI smoke: `MainWindow` (3 tabs) renders, status updates flow through signals, clean shutdown.

## Known limitations

- This Linux verification sandbox has no system OpenGL/EGL/libxkbcommon/libdbus, so PySide6 cannot import normally here. Local verification used `QT_QPA_PLATFORM=minimal` plus no-op stub shared libraries for libGL/libEGL/libxkbcommon/libdbus built under /tmp (NOT shipped with the product, not in the repository). On Windows (the target platform), PySide6 and OpenCV work natively.
- MediaPipe Face Landmarker task model is intentionally not bundled; without it the YuNet fallback supplies face presence/count/position only (no EAR/MAR/head-pose landmarks).
- TTS (pyttsx3) and audio (sounddevice/PortAudio) are unavailable in this sandbox and degrade gracefully to silent/log-only; on Windows they work if the runtime is present.
- Windows location API and Firebase are stubs pending explicit platform credentials/deployment configuration.
- No continuous video to disk; clips are event-only. Clip encoding depends on the local OpenCV video backend (mp4v).
- Prototype: not safety-certified, no guaranteed emergency delivery — see README and docs/06_Privacy_and_Security.md.

## Next action

None — baseline build complete. Commit `arena/2d0d0bb9-guardiandrive-ai` and run the release gate (`python -m pytest -q` + `python scripts/run_tests.py`) before tagging.

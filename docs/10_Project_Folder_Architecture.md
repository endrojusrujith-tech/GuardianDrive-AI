# Guardian Drive AI - Project Folder & Code Architecture

Recommended repository layout and responsibilities

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Repository Tree

```text
guardian-drive-ai/
|-- app/
|   |-- main.py
|   |-- config/
|   |   |-- settings.py
|   |   |-- defaults.yaml
|   |   |-- thresholds.yaml
|   |-- camera/
|   |   |-- camera_manager.py
|   |   |-- camera_source.py
|   |   |-- frame_processor.py
|   |   |-- camera_health.py
|   |-- vision/
|   |   |-- face_detector.py
|   |   |-- face_landmarker.py
|   |   |-- eye_analyzer.py
|   |   |-- head_pose.py
|   |   |-- yawn_analyzer.py
|   |   |-- phone_detector.py
|   |   |-- confidence.py
|   |-- behavior/
|   |   |-- temporal_buffer.py
|   |   |-- behavior_engine.py
|   |   |-- state_engine.py
|   |   |-- risk_engine.py
|   |-- alerts/
|   |   |-- alert_manager.py
|   |   |-- audio_alert.py
|   |   |-- voice_alert.py
|   |   |-- hazard_simulator.py
|   |-- emergency/
|   |   |-- emergency_manager.py
|   |   |-- sms_provider.py
|   |   |-- location_provider.py
|   |   |-- notification_provider.py
|   |   |-- clip_manager.py
|   |-- storage/
|   |   |-- sqlite_db.py
|   |   |-- repositories.py
|   |   |-- retention.py
|   |   |-- encryption.py
|   |-- cloud/
|   |   |-- firebase_adapter.py
|   |   |-- sync_queue.py
|   |   |-- cloud_storage.py
|   |-- gui/
|   |   |-- main_window.py
|   |   |-- monitoring_view.py
|   |   |-- settings_view.py
|   |   |-- history_view.py
|   |   |-- dialogs.py
|   |-- simulation/
|   |   |-- simulator.py
|   |   |-- scenarios.py
|   |-- utils/
|       |-- logging_config.py
|       |-- time_utils.py
|       |-- platform_utils.py
|
|-- models/
|-- tests/
|   |-- unit/
|   |-- integration/
|   |-- scenarios/
|   |-- fixtures/
|-- data/
|   |-- clips/
|   |-- snapshots/
|   |-- local/
|-- docs/
|-- scripts/
|-- logs/
|-- .env.example
|-- .gitignore
|-- README.md
|-- requirements.txt
|-- pyproject.toml
|-- PROJECT_RULES.md
|-- MASTER_PROMPT.md
```

# 2. Module Responsibilities

| Area | Responsibility |
| --- | --- |
| app/camera | Capture and camera-health abstraction |
| app/vision | Computer-vision feature extraction |
| app/behavior | Temporal analysis and behavior classification |
| app/alerts | Local alert delivery and hazard simulation |
| app/emergency | Emergency event lifecycle and provider orchestration |
| app/storage | SQLite, retention and secure local storage |
| app/cloud | Firebase and sync adapters |
| app/gui | PySide6 windows/views/widgets |
| app/simulation | Deterministic simulation scenarios |
| app/utils | Logging, time, OS utilities |
| models | Downloaded/configured inference models only; never secrets |
| tests | Automated tests and fixtures |
| scripts | Setup/build/diagnostic scripts |
| docs | Project documentation and AI instructions |

# 3. Dependency Direction

```text
gui -> application services
application -> domain/behavior interfaces
vision -> camera/frame abstractions
alerts/emergency -> interfaces
providers -> adapter contracts
storage -> repository interfaces

Avoid circular imports. Keep domain logic independent of PySide6/Firebase.
```

# 4. Configuration

- Use environment variables for secrets.
- Use YAML/JSON/TOML for thresholds and non-secret settings.
- Keep default thresholds versioned.
- Make lightweight-mode parameters configurable.

# 5. Logging

- Structured logs with levels INFO/WARNING/ERROR.
- Event IDs for correlation.
- Rotating file logs.
- No sensitive data in log messages.

# 6. Packaging

- requirements.txt or pyproject.toml for dependencies.
- `.env.example` for optional integrations.
- PyInstaller spec file later.
- Version string stored in one source of truth.

# 7. Existing Work Preservation

> **Note:** The AI agent must inspect the existing workspace before restructuring. Existing face-detection work should be preserved or migrated deliberately. Do not delete working files simply to fit the proposed tree.

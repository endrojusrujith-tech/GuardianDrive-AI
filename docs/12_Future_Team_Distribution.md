# Guardian Drive AI - Future 3-Person Module Distribution

Optional team plan; current development remains solo

**Version:** 1.0  
**Date:** 2026-09-25

> **Note:** Current execution is SOLO by decision. This document is retained only so the project can be split later without changing architecture.

# 1. Person 1 - Computer Vision

- Camera + frame pipeline
- Face detection/landmarks
- Eye analysis
- Head pose
- Yawning
- Phone detection
- Confidence/low-light pipeline
- Vision unit tests

# 2. Person 2 - Intelligence + Alerts

- Temporal buffers
- Behavior engine
- Risk index
- Driver state engine
- Alert manager
- Recovery/cooldown
- Simulation scenarios
- Alert unit/integration tests

# 3. Person 3 - Application + Cloud

- PySide6 GUI
- SQLite repositories
- Settings/history
- Firebase adapter
- Cloud Functions integration
- Notification/SMS adapter
- Location provider
- Packaging/build

# 4. Integration Contract

- All modules communicate through typed interfaces/data models.
- No direct imports across unrelated layers.
- Each person works on a branch.
- Pull requests include tests.
- Integration branch verifies the end-to-end simulation before merging.

# 5. Solo Development Translation

As a solo developer, implement in the same architectural order but keep the module boundaries. This makes later collaboration possible without a major refactor.

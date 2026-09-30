# Guardian Drive AI - Project Requirements Specification (SRS)

Requirements, scope, functional and non-functional requirements, assumptions, acceptance criteria

**Version:** 1.0  
**Date:** 2026-09-25

# Document Control

| Item | Value |
| --- | --- |
| Project | Guardian Drive AI |
| Version | 1.0 |
| Date | 2026-09-25 |
| Initial platform | Windows laptop/PC |
| Future platform | Vehicle computer |
| Development mode | Solo development; future team split documented separately |
| Status | Requirements frozen for implementation |

# 1. Purpose

Guardian Drive AI is a driver-monitoring application intended to observe driver attention and drowsiness-related visual signals through a camera, interpret those signals over time, and escalate local alerts when unsafe conditions persist. The first implementation is a Windows desktop prototype. Future versions may integrate night-vision/IR cameras, GPS, a vehicle computer, and vehicle interfaces.

> **Note:** Prototype boundary: Guardian Drive AI is a college/research prototype and must not be represented as a safety-certified automotive system. The application must not claim to replace a human driver, certified ADAS, or emergency services.

# 2. Product Goals

- Detect relevant visual driver-state signals in real time.
- Reduce false alerts by using time windows, temporal smoothing, confidence gating, and multi-signal reasoning.
- Provide a simple GUI that shows only actionable status information.
- Escalate warnings in three levels without requiring vehicle hardware in the first version.
- Capture limited event clips rather than continuously storing video.
- Continue local monitoring when internet/Firebase is unavailable.
- Keep camera, location, SMS, cloud, and vehicle interfaces modular for future migration.

# 3. Scope

- In scope: face presence/count/position, head direction, eye state, blink/closure, yawning, phone-near-face, temporal behavior analysis, internal risk index, driver states, alerts, clip buffering, local history, settings, simulation mode, optional cloud integration.
- Out of scope for the first release: actual vehicle control, real hazard-light actuation, embedded hardware deployment, autonomous driving, crash prediction, continuous cloud video surveillance, medical diagnosis.

# 4. User Experience Requirements

- Application starts to a simple main GUI. Monitoring begins only after the user selects Start Monitoring.
- Live camera view is shown during monitoring, with a hide/minimize option.
- Risk score is never displayed on the normal GUI.
- Main status areas: Monitoring state, Driver state, Camera health, current alert message.
- Settings provide driver information, camera, contacts, sound/voice, retention, night mode, and notification preferences.
- Alert history is available as a separate view.
- Simulation mode is available for demonstrations and deterministic testing.

# 5. Functional Requirements

| ID | Requirement | Description |
| --- | --- | --- |
| FR-01 | Camera input | Open a selectable camera source and expose a camera abstraction layer. |
| FR-02 | Face detection | Detect face presence, face count, and face position. |
| FR-03 | Head pose | Estimate forward/left/right/up/down orientation and duration. |
| FR-04 | Eye monitoring | Estimate eye open/closed state, blink events, prolonged closure, and closure duration. |
| FR-05 | Yawning | Detect mouth opening/yawn events and repeated yawning over time. |
| FR-06 | Phone detection | Detect a phone near the driver's face using an object detector only if needed. |
| FR-07 | Temporal reasoning | Use rolling time windows and persistence rules; do not trigger alerts from single frames. |
| FR-08 | Confidence gating | Use detection confidence and camera-quality checks; allow UNKNOWN state. |
| FR-09 | Driver state | Maintain NORMAL/ATTENTIVE, DISTRACTED, DROWSY, CRITICAL, UNKNOWN states. |
| FR-10 | Risk index | Compute an internal 0-100 heuristic risk index; never show it on main GUI. |
| FR-11 | Alert Level 1 | Voice + sound + GUI warning; initial level uses three sound pulses. |
| FR-12 | Alert Level 2 | Escalated local alert and software hazard-light simulation; no physical hardware. |
| FR-13 | Alert Level 3 | Create emergency event and send through pluggable notification/SMS adapter when configured. |
| FR-14 | Contacts | Support four emergency contacts. |
| FR-15 | Location | Support optional location provider now and future GPS provider. |
| FR-16 | Event clips | Use a rolling buffer and save only alert/emergency clips. |
| FR-17 | History | Store alert/event history locally in SQLite. |
| FR-18 | Offline | Local monitoring and alerts continue without internet. |
| FR-19 | Recovery | Detect camera disconnect, show a safe error, and attempt reconnection. |
| FR-20 | Simulation | Provide deterministic scenarios for all states and alert escalation. |
| FR-21 | Night support | Provide configurable low-light enhancement and camera abstraction for future IR camera. |
| FR-22 | Display orientation | Default camera preview to non-mirrored user-facing orientation, with a mirror toggle; detection logic must remain consistent. |

# 6. Non-Functional Requirements

| ID | Area | Requirement |
| --- | --- | --- |
| NFR-01 | Real-time | Target approximately 10-20 processed FPS on a reasonably modern Windows laptop; automatically enter lightweight mode on constrained hardware. |
| NFR-02 | Responsiveness | Target low alert latency; avoid blocking the GUI thread with vision, cloud, SMS, or video encoding work. |
| NFR-03 | Reliability | Core monitoring continues when cloud services fail. |
| NFR-04 | Privacy | No continuous permanent video recording. Event-based retention only. |
| NFR-05 | Security | Never commit secrets; do not ship Firebase service-account credentials inside the desktop client. |
| NFR-06 | Maintainability | Separate detection, interpretation, decision, and response layers. |
| NFR-07 | Portability | Use hardware/provider interfaces so the same core logic can move to a vehicle computer. |
| NFR-08 | Testability | Thresholds and behavior scenarios must be configuration-driven and unit-testable. |
| NFR-09 | Accessibility | Critical alerts must be available as sound and visual messages; voice is primary Level 1 feedback. |

# 7. Constraints and Assumptions

- First release runs on Windows 10 64-bit or later on supported hardware.
- Camera availability and lighting can vary significantly.
- Night vision hardware is not present initially.
- SMS and cloud credentials may be absent during development, so adapters and simulation are required.
- Thresholds are prototype defaults and must be tuned with controlled testing rather than treated as scientifically calibrated values.

# 8. Acceptance Criteria

1. Application launches without crashing and presents a simple GUI.
2. Start/Stop monitoring works without freezing the GUI.
3. Face, eye, head, yawn, and phone-near-face signals can be observed or simulated.
4. Brief head turns do not immediately cause escalation.
5. Sustained unsafe patterns trigger Level 1 and escalate only when persistence rules are met.
6. Alert recovery cancels escalation when the driver returns to a safe state for the configured recovery period.
7. Camera disconnect is handled without application crash.
8. Internet failure does not stop local monitoring.
9. Alert clips and history entries are created according to retention rules.
10. Simulation mode can demonstrate the complete Level 1 -> Level 2 -> Level 3 path.

# 9. Future Expansion

- Vehicle computer deployment
- IR/night-vision camera
- External GPS
- Real hazard/vehicle interface
- Mobile emergency-contact app
- Additional object and behavior models
- Hardware-accelerated inference

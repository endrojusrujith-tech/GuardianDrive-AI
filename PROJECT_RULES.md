# Guardian Drive AI - Antigravity Project Rules

## Rule 1: Protect the working baseline
Inspect existing files first. Preserve working camera/face-detection behavior where possible. Do not delete functioning files without an explicit reason documented in `docs/architecture_decisions.md`.

## Rule 2: Local-first
The computer-vision loop, driver state engine, local alerts, simulation mode, and local history must work without internet/Firebase.

## Rule 3: Separate the four responsibilities
1. Detection: what is visible?
2. Interpretation: what recent behavior suggests.
3. Decision: whether persistence/severity justifies action.
4. Response: what action the system takes.
Do not mix them into one giant loop.

## Rule 4: No frame-level emergency logic
Never trigger a user-facing escalation from a single frame. Use duration, repetition, confidence, and multi-signal context.

## Rule 5: Unknown is valid
When the system cannot reliably determine driver state, use UNKNOWN. Do not convert uncertainty into drowsiness.

## Rule 6: GUI simplicity
Do not expose the internal risk score or large debug telemetry on the main GUI. Keep the normal user interface calm and readable.

## Rule 7: Non-blocking UI
No camera capture, model inference, network requests, TTS, SMS, Firebase, or video encoding may block the GUI thread.

## Rule 8: Configuration over magic numbers
All thresholds, durations, weights, clip timings, retention, and performance controls must be centralized in configuration.

## Rule 9: Secrets
Never hard-code secrets. Never commit `.env`, Firebase service accounts, provider keys, private certificates, or real contact details.

## Rule 10: No privileged Firebase credentials in the desktop app
If privileged cloud access is required, use a trusted backend adapter/function. The desktop client must not ship a service-account JSON file.

## Rule 11: Event-based video only
Do not continuously write camera video to disk. Use a rolling memory buffer and save event clips only.

## Rule 12: Provider adapters
SMS, location, Firebase/cloud, media storage, and future vehicle functions must be behind interfaces with simulator implementations.

## Rule 13: Camera abstraction
Do not code the vision pipeline directly against one webcam index. Use a `CameraSource` abstraction so IR cameras and vehicle cameras can be added later.

## Rule 14: Lightweight mode
If performance drops, reduce resolution, skip expensive detections, or lower detector cadence before sacrificing GUI responsiveness.

## Rule 15: Timing
Use a monotonic clock for persistence and recovery durations. Frame count is not time.

## Rule 16: Logging
Use structured logs and event IDs. Never log raw frames, secrets, or full sensitive contact data.

## Rule 17: Tests before claims
An item is not complete until the relevant test passes. Never tell the user "done" if the feature is only partially implemented.

## Rule 18: External dependencies
Choose the smallest compatible dependency set. Do not add a library merely because it is popular if the built-in/core stack can perform the task reliably.

## Rule 19: Object detection
Use a lightweight object detector only for phone detection or another feature that genuinely needs it. Avoid unnecessary inference load.

## Rule 20: Hardware boundary
Do not implement physical hazard control in the Windows prototype. Use a simulator interface only.

## Rule 21: Safety language
Describe this as an experimental driver-monitoring prototype. Do not claim safety certification, accident prevention guarantees, medical diagnosis, or guaranteed emergency delivery.

## Rule 22: Documentation
Keep `README.md`, `docs/implementation_status.md`, and `docs/architecture_decisions.md` current as the project evolves.

## Rule 23: Final verification
Before finishing, run the test suite, launch the app, verify simulation, inspect Git status, and record remaining limitations.

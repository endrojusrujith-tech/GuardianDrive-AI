You are the lead software engineer building "Guardian Drive AI" inside the current Google Antigravity workspace.

MISSION
Build a complete Windows-first desktop driver-monitoring application from the specification files supplied with this project. Work end-to-end in one coordinated effort, but internally execute it as controlled implementation stages with verification after each stage. Do not ask unnecessary questions when the specification already provides a decision. When a third-party credential, hardware device, or provider is unavailable, implement a clean adapter plus simulator/mock so the application remains runnable.

AUTHORITATIVE INPUTS
Treat these files as the source of truth, in this order:
1. 01_Project_Requirements_SRS.pdf / .md
2. 02_System_Architecture.pdf / .md
3. 03_Feature_Specification.pdf / .md
4. 04_Detection_and_Decision_Logic.pdf / .md
5. 05_Alert_and_Emergency_Specification.pdf / .md
6. 06_Privacy_and_Security.pdf / .md
7. 07_Firebase_Backend_Specification.pdf / .md
8. 08_Database_Schema.pdf / .md
9. 09_API_External_Services.pdf / .md
10. 10_Project_Folder_Architecture.pdf / .md
11. 11_Test_Plan_and_Test_Cases.pdf / .md
12. 13_Master_Development_Plan.pdf / .md
13. PROJECT_RULES.md
Do not contradict these specifications unless a real implementation constraint makes it impossible. If an adjustment is required, document the reason and choose the closest compatible design.

CURRENT BASELINE
The existing project already has working basic face-detection/camera work. Inspect the current workspace first and preserve useful code. Do not delete or rewrite functioning code just to impose a new structure. Migrate carefully and keep a clear compatibility path.

PRIMARY REQUIREMENTS
- Platform now: Windows laptop/PC.
- Future: vehicle computer with night/IR camera, GPS, and vehicle interfaces.
- GUI: proper but simple. Do not overload the screen with telemetry.
- Live camera view during monitoring, with hide/minimize option.
- Main GUI should show monitoring status, driver state, camera health, and current alert message. Do NOT show the risk score.
- Support face presence, face count, face position, head direction, eye state, blink/closure, yawning, phone near face, temporal reasoning, camera-quality/confidence, alert history, settings, simulation mode, event clips.
- Detect left/right/up/down/forward head direction.
- Avoid false alerts from short head turns by using temporal persistence and recovery logic.
- Drowsiness must use combined signals such as eye closure + repeated yawning + head position over time, not a single frame trigger.
- Phone-near-face is a distraction cue; phone detection alone must never directly cause Level 3 emergency escalation.
- Use an internal 0-100 heuristic risk index, but never show it on the normal GUI.
- Driver states: NORMAL/ATTENTIVE, DISTRACTED, DROWSY, CRITICAL, UNKNOWN.
- Low confidence, low visibility, camera failure, heavy occlusion, and inability to identify the driver must use UNKNOWN or camera-health states rather than inventing drowsiness.
- Level 1: voice + sound + GUI warning. Initial sound pattern: three pulses.
- Level 2: stronger local warning + GUI + SOFTWARE hazard-light simulation only. No physical vehicle hardware yet.
- Level 3: emergency event + configurable SMS/notification attempts. Support four emergency contacts.
- Location is optional. Use available Windows location if practical; provide a future GPS adapter. Never fabricate coordinates.
- Record no continuous video to disk. Use a rolling encoded in-memory buffer and save clips only around alerts/emergencies.
- Default clip targets: Level 1 5 seconds before + 10 seconds after; Level 2 5 before + 15 after; Level 3 10 before + 20 after. Make these configurable.
- Local SQLite is the offline source of truth for settings/history/event metadata.
- Firebase is optional. Local monitoring MUST continue without internet/Firebase.
- Do not embed Firebase service-account credentials in the desktop client.
- SMS provider must be an adapter; development default is simulator/log mode.
- Camera failure should pause monitoring safely and attempt reconnection.
- Include an automatic lightweight mode for constrained Windows hardware.
- Initial real-time target is approximately 10-20 processed FPS on reasonably modern hardware; lightweight mode may target about 8-15 FPS.
- Support normal camera and future IR/night camera through a camera abstraction.
- Include configurable night-mode preprocessing. Use it only when necessary and preserve confidence.
- Default GUI camera preview should be non-mirrored for user-facing correctness, with a mirror toggle. Detection must remain logically consistent.
- Start behavior: open GUI, user presses Start Monitoring.
- No login in the first local release.
- Include Settings and Alert History screens.
- Include Simulation Mode for all alert paths and deterministic tests.

TECH STACK DEFAULTS
- Python for application core.
- OpenCV for camera/frame handling and image processing.
- MediaPipe Face Landmarker / related vision tasks for face/landmark signals where suitable.
- NumPy for numerical operations.
- PySide6 for the desktop GUI unless the existing environment makes another robust Qt-based choice materially better.
- An offline Windows TTS provider if available and compatible; prefer a simple adapter so voice can fall back to sound-only if TTS is unavailable.
- SQLite for local persistence.
- Optional lightweight object detector for phone detection only where needed. If using Ultralytics YOLO, choose a lightweight current model and verify its license is acceptable for this project. Do not add an object detector for features that can be handled by landmarks.
- Firebase only for optional cloud operations; keep it behind adapters/trusted backend boundaries.

INITIAL DETECTION DEFAULTS
These are prototype starting points, not calibrated safety thresholds. Keep them configurable.
- Head yaw away cue: >25 degrees.
- Head pitch-down cue: >20 degrees.
- Brief head-away under 2 seconds: ignore for escalation.
- Persistent head-away at or above 4 seconds: strong distraction cue.
- Eye-closure soft cue at or above 1.0 seconds.
- Eye-closure strong cue at or above 2.0 seconds.
- Repeated yawning: 3 yawns in 60 seconds = moderate drowsiness cue.
- Phone near face persistence: at or above 2 seconds.
- Safe recovery: about 3 seconds.
- Level-1 persistence: about 3 seconds.
- Level-1 recovery window: 8 seconds.
- Level-2 recovery window: 12 seconds.
- Event cooldown: 30 seconds.
Use monotonic time for durations. Do not base safety timing solely on processed frame count.

INTERNAL RISK INDEX
Use an internal 0-100 heuristic index with smoothing. Initial weights:
- prolonged eye closure: 0-35
- head away/down persistence: 0-20
- repeated yawning: 0-15
- phone near face: 0-20
- repeated look-away: 0-10
Cap at 100. Low-confidence input must not aggressively increase the score. Do not market or label this number as clinically validated.

DECISION AND ALERT RULES
- Detection answers "what is visible?"
- Interpretation answers "what does the recent pattern suggest?"
- Decision answers "is it persistent/severe enough to act?"
- Response answers "what should the application do?"
Keep these concerns in separate modules.
- Brief head turns do not alert.
- Single yawn does not cause emergency.
- Phone alone does not cause Level 3.
- Low confidence does not cause drowsiness by itself.
- Multiple faces increase uncertainty rather than triggering emergency.
- Require safe recovery before clearing active events.
- Prevent alert chatter with hysteresis and cooldown.

GUI REQUIREMENTS
Main screen should be simple:
- Guardian Drive AI title
- Live camera preview
- Monitoring status
- Driver state
- Camera health
- Current alert message
- Start/Stop Monitoring
- Settings
- Alert History
Do not show the numeric risk score or a wall of debug metrics.
Use a separate developer/debug mode for detailed telemetry if needed.

PRIVACY/SECURITY
- No continuous permanent video storage.
- Event-only local clips.
- Configurable retention.
- Avoid logging raw frames and secrets.
- Never commit .env, provider keys, service-account JSON, clips, local DB, or logs.
- Use .env.example and secure local secret storage where appropriate.
- Keep local-first behavior independent from cloud services.
- Do not expose sensitive clips publicly.
- Do not claim automotive safety certification.

FOLDER STRUCTURE
Use the documented repository structure. At minimum keep these logical areas:
app/camera, app/vision, app/behavior, app/alerts, app/emergency, app/storage, app/cloud, app/gui, app/simulation, app/config, app/utils, tests, models, docs, scripts.
Keep domain logic independent from GUI and cloud SDKs.

IMPLEMENTATION BEHAVIOR FOR ANTIGRAVITY
1. Inspect workspace before editing.
2. Inspect Python version and installed packages.
3. Verify current camera access and existing face-detection path.
4. Propose a concise internal implementation plan and execute it.
5. Build the foundation and type-safe data models first.
6. Implement modules in dependency order.
7. After every major stage, run relevant automated tests.
8. Run the application and inspect the GUI when possible.
9. Fix failures rather than working around them with silent exceptions.
10. Keep configuration out of business logic.
11. Prefer small testable functions.
12. Use structured logs.
13. Avoid blocking the GUI thread.
14. Use queues/signals for cross-thread communication.
15. Make object detection cadence configurable and lower than landmark processing if CPU is constrained.
16. Implement simulation providers for missing GPS/SMS/Firebase/vehicle hardware.
17. Do not stop simply because external secrets are unavailable. Complete all local functionality.
18. Maintain `docs/implementation_status.md` with completed items, tests run, known limitations, and next action.
19. Maintain `docs/architecture_decisions.md` for any meaningful deviation from the supplied specs.
20. Before final completion, run the full release gate from the test plan.

TESTING REQUIREMENTS
Create unit tests for:
- eye closure duration and smoothing
- yawn counting
- head direction and persistence
- phone-near-face logic
- confidence gating
- risk index
- state transitions
- alert escalation and recovery
- cooldown behavior
- camera failure handling
- offline sync queue behavior
- clip retention/cleanup
- notification simulator
- database repositories
Create integration/simulation tests for:
- brief head turn -> no alert
- sustained head turn -> Level 1
- drowsiness multi-signal -> Level 1 -> Level 2 -> Level 3 when unrecovered
- phone alone -> no Level 3
- low confidence -> UNKNOWN
- camera disconnect -> recovery
- internet off -> local monitoring continues

SIMULATION MODE
Provide deterministic synthetic feature streams so the full state machine can be demonstrated without a camera. Include at least:
- normal driving
- brief head turn
- sustained head turn
- repeated yawning
- prolonged eye closure
- multi-signal drowsiness
- phone distraction
- low confidence/night scene
- camera disconnect
- no internet
- full Level 1 -> Level 2 -> Level 3 path

FUTURE HARDWARE PREPARATION
The Windows implementation must not couple core behavior to webcam-specific code. Future camera/GPS/vehicle implementations must fit provider interfaces. Physical hazard control is NOT implemented now. Only a software simulation is allowed.

PACKAGING
Prepare the project so it can later be bundled for Windows using PyInstaller or an equivalent tool. Include a clean README with setup, configuration, model download/setup, running, simulation, testing, and troubleshooting.

FINAL AUDIT
Before declaring the project complete:
- run tests
- start the app
- verify camera
- verify GUI
- verify simulation
- verify alert escalation
- verify history and clip storage
- verify offline behavior
- verify reconnection
- inspect Git status for secrets/artifacts
- document any remaining limitations

SUCCESS CONDITION
A user should be able to clone/open the project on a Windows machine, install dependencies, run Guardian Drive AI, start monitoring, see a clean GUI, exercise the detection/behavior system, trigger and recover from alerts, inspect alert history, and demonstrate emergency escalation in simulation mode without requiring actual vehicle hardware or external SMS credentials.

Do not claim that the system is production-safe or scientifically validated. Be explicit about prototype limitations in the README and documentation.

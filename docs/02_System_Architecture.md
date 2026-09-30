# Guardian Drive AI - System Architecture

Layered architecture, components, interfaces, runtime and deployment

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Architecture Principles

- Local-first operation
- Modular interfaces
- Separation of detection, interpretation, decision, and response
- Non-blocking GUI
- Configuration over hard-coded thresholds
- Graceful degradation
- Event-driven cloud/notification integration

# 2. High-Level Architecture

```text
GUARDIAN DRIVE AI
=================
Windows PC/Laptop (now)
    |
    v
Camera Abstraction
    |
    v
Frame Processing + Quality Gate
    |
    +--> Face / Landmark Analysis
    |       +--> Face presence / count / position
    |       +--> Eye state / blink / closure
    |       +--> Head pose / gaze proxy
    |       +--> Yawning
    |
    +--> Object Detection (only when needed)
    |       +--> Phone near face
    |
    v
Temporal Feature Buffer
    |
    v
Behavior Interpretation
    |
    v
Internal Risk Index (0-100; NOT shown on GUI)
    |
    v
Driver State Engine
    |
    +--> ATTENTIVE / NORMAL
    +--> DISTRACTED
    +--> DROWSY
    +--> CRITICAL
    +--> UNKNOWN
    |
    v
Alert Manager
    |
    +--> Level 1: voice + sound + GUI warning
    +--> Level 2: stronger local alert + software hazard simulation
    +--> Level 3: emergency notification workflow
    |
    +--> Clip Manager (rolling buffer, event-only saving)
    +--> Local SQLite alert history
    |
    v
Optional Cloud Adapter
    |
    +--> Firebase sync / functions / storage (only as required)
    +--> SMS provider adapter
    +--> Location provider adapter
    |
    v
Future Vehicle Integration
    +--> IR / night camera
    +--> GPS
    +--> vehicle computer
    +--> hazard / other vehicle interfaces
```

# 3. Logical Layers

| Layer | Components | Responsibility |
| --- | --- | --- |
| Presentation | PySide6 GUI | Simple monitoring, settings, history, alerts |
| Application orchestration | Monitoring controller | Start/stop, lifecycle, state propagation |
| Vision | OpenCV + MediaPipe + optional object detector | Face, eye, head, yawn, phone signals |
| Behavior | Temporal buffer + behavior engine | Duration, repetition, combinations, smoothing |
| Decision | Risk engine + state engine | Internal risk index and alert eligibility |
| Response | Alert manager + emergency manager | Voice, sound, GUI, simulation, notifications |
| Storage | SQLite + event clip manager | Local history, configuration, event artifacts |
| Integration | Provider adapters | Firebase, SMS, location, future hardware |
| Infrastructure | Logging, configuration, update checks | Operational support |

# 4. Runtime Pipeline

1. Capture frame
2. Check camera/frame quality
3. Apply optional low-light preprocessing
4. Run face/landmark analysis
5. Run optional phone detector on a reduced cadence
6. Compute feature signals
7. Update temporal buffers
8. Calculate behavior signals and internal risk index
9. Update driver state
10. Pass decision to Alert Manager
11. Update GUI asynchronously
12. Write local history/event clip as required
13. Queue cloud/notification work asynchronously

# 5. Concurrency Model

- Main GUI thread: UI only.
- Vision worker: camera capture and frame analysis.
- Inference scheduler: optional lower-frequency YOLO/object detection.
- Alert worker: audio/voice.
- Clip worker: encode and write event clips.
- Cloud worker: sync queue, Firebase, notifications.
- All workers communicate through thread-safe signals/queues; no network or video encoding in GUI thread.

# 6. Hardware Abstraction

CameraSource, LocationProvider, NotificationProvider, SMSProvider, StorageProvider, and VehicleInterface should be abstract interfaces. The Windows prototype should use concrete local implementations and stubs/simulators where external hardware is absent.

# 7. Offline-First Design

```text
Internet available -> local operation + queued cloud sync
Internet unavailable -> local operation + local queue
Connection restored -> retry queue with backoff
Permanent failure -> retain local history and mark sync error
```

# 8. Failure Boundaries

| Failure | Required behavior |
| --- | --- |
| Camera failure | Monitoring paused safely; reconnect attempts; GUI shows camera unavailable. |
| Low lighting | Reduce confidence; optionally enable low-light enhancement; use UNKNOWN when uncertain. |
| Object detector unavailable | Phone feature disabled/unknown; core monitoring continues. |
| Firebase unavailable | No impact on local detection/alerts. |
| SMS provider unavailable | Log emergency event, show notification failure, retry according to policy; do not crash. |
| Disk full | Stop clip saving, preserve monitoring if possible, show storage warning. |
| GUI failure risk | Vision and alert layers should fail safe; main process should log exceptions. |

# 9. Deployment

- Development: Python source in Git repository.
- Prototype run: python -m app.main or configured entrypoint.
- Packaging later: PyInstaller or equivalent Windows bundle.
- Future embedded: replace camera/hardware providers and optimize inference without changing behavior/state interfaces.

# 10. Architecture Verification

1. Run unit tests for each layer.
2. Run simulation scenarios.
3. Run real camera integration.
4. Test internet-off and camera-disconnect cases.
5. Profile CPU/RAM/FPS in normal and lightweight modes.
6. Verify that external providers can be stubbed in tests.

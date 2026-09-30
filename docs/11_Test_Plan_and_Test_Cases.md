# Guardian Drive AI - Test Plan & Test Cases

Unit, integration, system, performance, false-alert and failure tests

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Test Strategy

- Unit test feature calculators and state logic.
- Integration test camera -> vision -> behavior -> alert flow.
- Scenario test alert escalation and recovery.
- Failure-injection test camera/network/storage/provider failures.
- Performance test normal and lightweight modes.
- Manual usability tests for GUI and simulation.

# 2. Core Test Matrix

| ID | Scenario | Stimulus | Expected |
| --- | --- | --- | --- |
| TC-01 | Face detected | Known face in good lighting | Face state valid |
| TC-02 | No face | Camera open but no visible face | UNKNOWN after persistence, no false emergency |
| TC-03 | Multiple faces | Passenger present | Multiple-face signal/uncertainty, no automatic emergency |
| TC-04 | Brief head turn | Left/right < 2 s | No alert |
| TC-05 | Sustained head turn | > 4 s | Distraction cue and Level 1 when persistence reached |
| TC-06 | Brief eye closure | < 1 s | No drowsiness alert |
| TC-07 | Prolonged eye closure | > 2 s | Strong drowsiness cue |
| TC-08 | Repeated yawning | 3 in 60 s | Moderate drowsiness cue |
| TC-09 | Phone near face | > 2 s | Distraction cue; no automatic Level 3 |
| TC-10 | Multi-signal drowsiness | eyes + yawns + head down | DROWSY/CRITICAL depending persistence |
| TC-11 | Recovery | Safe state for 3 s | Cancel escalation |
| TC-12 | No recovery | Unsafe after Level 1 window | Level 2 |
| TC-13 | Critical persistence | Unsafe after Level 2 window | Level 3 event |
| TC-14 | Camera disconnect | Unplug/disable source | Safe pause + reconnect attempts |
| TC-15 | Internet off | Disable network | Local monitoring continues |
| TC-16 | Disk full | Block clip directory | Monitoring continues; clip error logged |
| TC-17 | Low light | Dark scene | Confidence drop/UNKNOWN when insufficient |
| TC-18 | Simulation | Run all scenarios | Deterministic expected outcomes |

# 3. False Alert Tests

- Turn head briefly in both directions repeatedly.
- Look at passenger for a short moment.
- Blink normally.
- Yawn once.
- Move face because of posture adjustment.
- Occlude face briefly with hand.
- Have a passenger visible.
- Switch camera exposure between bright/dark.

# 4. Performance Targets

| Metric | Target | Acceptance |
| --- | --- | --- |
| Normal mode | 10-20 processed FPS target where hardware allows | Stable GUI, no sustained backlog. |
| Lightweight mode | 8-15 processed FPS target | Lower resolution/inference cadence; core features remain available. |
| Alert latency | Low single-digit seconds subject to persistence thresholds | Must respect decision windows. |
| GUI responsiveness | No blocking > 100 ms caused by external operations | Use worker threads/queues. |

# 5. Lightweight Mode Policy

- Reduce analysis resolution.
- Process expensive object detector less often.
- Disable optional non-essential overlays.
- Use lower camera FPS or frame skipping if needed.
- Keep temporal timestamps based on monotonic clock, not number of processed frames alone.

# 6. Test Data Handling

- Use synthetic/simulation data where possible.
- Keep real video clips local and controlled.
- Do not commit user camera footage to Git.
- Use anonymized or staged data for documentation.

# 7. Release Gate

1. All automated tests pass.
2. Manual core scenarios pass.
3. No high-severity crash paths found.
4. No secrets in repository.
5. Offline behavior verified.
6. Camera recovery verified.
7. Clip retention verified.
8. README installation verified on Windows.
9. Simulation demo completes full escalation path.

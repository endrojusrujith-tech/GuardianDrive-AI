# Guardian Drive AI - Alert & Emergency Specification

Three-level escalation, local alerts, emergency message, clip lifecycle and recovery

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Alert Levels

| Level | Meaning | Local response | Transition behavior |
| --- | --- | --- | --- |
| Level 0 | Normal | No alert | Monitoring continues. |
| Level 1 | Warning | Voice + sound + GUI | Initial alert uses three sound pulses; driver can recover to cancel escalation. |
| Level 2 | Escalated warning | Stronger voice/sound + GUI + software hazard simulation | No physical hazard control in prototype. |
| Level 3 | Emergency | Emergency event + configured SMS/notification attempts | Sent once per event; record success/failure. |

# 2. Level 1 Behavior

1. Confirm unsafe condition persisted long enough.
2. Start voice prompt and three sound pulses.
3. Show a concise warning on GUI.
4. Start/extend event clip capture.
5. Enter Level-1 recovery window (8 seconds by default).
6. If safe recovery occurs, log resolved event and return to normal.
7. If unsafe condition persists, enter Level 2.

# 3. Level 2 Behavior

1. Start stronger local alert.
2. Set software hazard simulation status to ACTIVE in GUI/log.
3. Continue event clip capture.
4. Enter Level-2 recovery window (12 seconds by default).
5. If safe, stop simulated hazard state and resolve event.
6. If critical condition persists, create Level-3 emergency event.

# 4. Level 3 Behavior

1. Freeze the emergency event payload.
2. Capture final emergency clip window.
3. Collect location if available.
4. Create a local database record before attempting network actions.
5. Attempt notification through the configured provider adapter.
6. Record each contact delivery result.
7. Do not block the monitoring loop while sending notifications.
8. Show emergency notification status on GUI.

# 5. Emergency Message Payload

```text
GUARDIAN DRIVE AI - EMERGENCY ALERT

Driver: <driver_name>
Vehicle: <vehicle_id or Unknown>
Condition: <DROWSY / CRITICAL / ...>
Severity: <CRITICAL>
Time: <local timestamp>
Location: <coordinates or Unavailable>
Recent alerts: <compact summary>
Event ID: <id>
Clip reference: <local/cloud reference when applicable>
```

# 6. Emergency Severity

| Severity | Use | Action |
| --- | --- | --- |
| INFO | System state only | No notification. |
| WARNING | Level 1 | Local driver warning. |
| HIGH | Level 2 | Escalated local response. |
| CRITICAL | Level 3 | Emergency notification workflow. |

# 7. Clip Policy

- Use rolling in-memory encoded frames, not continuous permanent recording.
- Level 1: target 5 seconds before + 10 seconds after event start.
- Level 2: target 5 seconds before + 15 seconds after escalation.
- Level 3: target 10 seconds before + 20 seconds after emergency trigger.
- Save in event-specific directories with generated IDs, never with personal names in filenames.
- If disk or encoding fails, preserve the event metadata and continue monitoring.

# 8. Notification Adapter

Implement a provider interface so the core emergency manager does not depend on one vendor. Development default is a simulator/log provider. A production provider can later implement SMS delivery for India or the deployment region after legal, pricing, and provider requirements are verified.

# 9. Notification Failure

- Do not crash.
- Record provider error.
- Display failure clearly to the local operator.
- Retry with bounded backoff where appropriate.
- Do not generate duplicate emergency events merely because a provider failed.

# 10. Simulation

```text
SIMULATED LEVEL 3
--------------------------------
Event created: EVT-000123
4 emergency contacts loaded
Location: Unavailable
SMS provider: SIMULATOR
Result: simulated delivery
Emergency clip: saved locally
```

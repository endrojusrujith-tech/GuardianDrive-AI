# Guardian Drive AI - Detection & Decision Logic

Thresholds, temporal reasoning, internal risk model, state transitions and escalation

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Important Design Rule

> **Note:** All numerical values in this document are initial prototype defaults. They are not medically or statistically calibrated. The implementation must keep them configurable and tune them using repeatable test scenarios.

# 2. Signal Definitions

| Signal | Name | Meaning |
| --- | --- | --- |
| S1 | Eye closure | Continuous duration of both eyes considered closed. |
| S2 | Blink rate | Short eye closures separated by open-eye periods. |
| S3 | Yawn | Detected mouth-opening event meeting minimum duration/shape criteria. |
| S4 | Head away | Yaw/pitch beyond calibrated forward thresholds. |
| S5 | Head down | Pitch-down posture sustained beyond threshold. |
| S6 | Repeated look-away | Multiple away events in rolling time window. |
| S7 | Phone near face | Phone detection overlapping configurable face-proximity region. |
| S8 | Face quality | Face detection/tracking confidence and usable-region quality. |
| S9 | Camera quality | Brightness/blur/dropout/availability indicators. |

# 3. Initial Thresholds

| Parameter | Initial value | Purpose | Notes |
| --- | --- | --- | --- |
| Head yaw | 25 degrees | Looking away cue | Configurable |
| Head pitch down | 20 degrees | Downward head cue | Configurable |
| Brief away duration | < 2.0 s | Ignore for escalation | Configurable |
| Persistent away duration | >= 4.0 s | Strong distraction cue | Configurable |
| Eye closure soft cue | >= 1.0 s | Drowsiness cue | Configurable |
| Eye closure strong cue | >= 2.0 s | Strong drowsiness cue | Configurable |
| Repeated yawns | 3 in 60 s | Moderate drowsiness cue | Configurable |
| Phone near face | >= 2.0 s | Distraction cue | Configurable |
| Safe recovery | 3.0 s | Return to safe state before canceling escalation | Configurable |
| Level 1 persistence | >= 3.0 s | Unsafe pattern persists | Configurable |
| Level 1 recovery window | 8.0 s | Wait for driver response before Level 2 | Configurable |
| Level 2 recovery window | 12.0 s | Wait for recovery before Level 3 | Configurable |
| Post-event cooldown | 30 s | Suppress duplicate events | Configurable |

# 4. Internal Risk Index

Use a heuristic 0-100 internal risk index. It is an engineering signal, not a medical or safety-certified score.

| Component | Max points | Intent |
| --- | --- | --- |
| Prolonged eye closure | 0-35 | Highest weight for drowsiness evidence |
| Head away/down persistence | 0-20 | Distraction/posture |
| Repeated yawning | 0-15 | Drowsiness cue |
| Phone near face | 0-20 | Distraction cue |
| Repeated look-away | 0-10 | Behavioral persistence |

Risk must be capped at 100 and smoothed over a short rolling window. Low-confidence frames must not increase risk aggressively. Face/camera quality problems should influence confidence/state, not be interpreted as drowsiness.

# 5. Driver State Rules

| State | Entry concept |
| --- | --- |
| NORMAL/ATTENTIVE | Low risk, good confidence, forward attention. |
| DISTRACTED | Persistent head-away/phone/look-away pattern with adequate confidence. |
| DROWSY | Eye closure and/or repeated yawning plus supporting head posture over time. |
| CRITICAL | Persistent severe drowsiness or multi-signal high-risk state that remains after warnings. |
| UNKNOWN | Low confidence, camera failure, severe occlusion, or inability to reliably identify driver state. |

# 6. Temporal Reasoning

```text
For every frame or analysis tick:
  1. Validate camera and face quality.
  2. Compute instantaneous features.
  3. Append to bounded time-series buffers.
  4. Derive durations and counts.
  5. Apply smoothing / hysteresis.
  6. Compute internal risk index.
  7. Update state.
  8. Evaluate alert transition rules.
  9. Emit event only when transition is confirmed.
```

# 7. Alert Escalation State Machine

```text
SAFE
  |
  | unsafe condition persists for configured Level-1 persistence
  v
LEVEL_1
  |
  | driver recovers for safe-recovery time --> SAFE
  |
  | unsafe condition persists for Level-1 recovery window
  v
LEVEL_2
  |
  | driver recovers --> SAFE
  |
  | critical unsafe state persists for Level-2 recovery window
  v
LEVEL_3
  |
  | create emergency event once
  | continue local monitoring
  | do not spam repeated emergency messages
  v
COOLDOWN -> SAFE
```

# 8. Important Non-Escalation Rules

- A brief head turn alone must not cause an alert.
- A single yawn alone must not cause an emergency.
- Phone detection alone must not directly trigger Level 3.
- Low-confidence input must not be treated as critical drowsiness.
- Face absence must first distinguish camera failure/occlusion from actual driver absence.
- Multiple faces should increase uncertainty, not automatically imply emergency.

# 9. Recovery and Hysteresis

- Require safe state for 3 seconds before clearing an active condition.
- Use separate entry and exit thresholds to reduce alert chatter.
- Use 30-second event cooldown unless a materially different critical event occurs.
- Persist state long enough to prevent frame-to-frame toggling.

# Guardian Drive AI - Feature Specification

Detailed behavior of detection, analysis, alerts, GUI and settings

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Feature Map

| Code | Feature | Definition |
| --- | --- | --- |
| F01 | Camera management | Select/open camera, health status, mirror toggle, reconnection. |
| F02 | Face monitoring | Presence, multiple faces, position, usable-region check. |
| F03 | Eye monitoring | Open/closed, blink, closure duration. |
| F04 | Head monitoring | Yaw/pitch direction and persistence. |
| F05 | Yawning | Yawn event and repetition window. |
| F06 | Phone near face | Object detector signal + proximity heuristic. |
| F07 | Behavior engine | Combine signals over time. |
| F08 | Driver state | Human-readable state for GUI. |
| F09 | Risk engine | Internal 0-100 heuristic index. |
| F10 | Alerts | Three levels with recovery/cooldown. |
| F11 | Emergency | Four contacts, message payload, location, clip reference. |
| F12 | History | Local event log and review screen. |
| F13 | Settings | Driver/contact/camera/alert/storage preferences. |
| F14 | Simulation | Prebuilt scenarios for demo and tests. |
| F15 | Night mode | Low-light enhancement + future IR camera support. |

# 2. Face Monitoring

- Detect whether a driver face is available.
- Detect multiple faces and mark identity certainty as limited.
- Calculate normalized face center and position relative to a configurable safe region.
- Do not interpret face absence immediately as drowsiness or emergency; first validate camera health and persistence.
- When multiple faces are present and the driver cannot be uniquely tracked, prefer UNKNOWN over aggressive inference.

# 3. Eye Monitoring

- Use face landmarks to derive eye openness and blink events.
- Track continuous closure duration.
- Track proportion of recent frames with eyes closed (PERCLOS-like internal feature, not a clinical measure).
- Use smoothing to suppress single-frame noise.
- Strong drowsiness evidence comes from sustained closure and/or combinations with yawning/head-down cues.

# 4. Head Direction

- Estimate yaw and pitch relative to a calibrated forward-facing baseline.
- Initial prototype values: yaw > 25 degrees indicates looking away; pitch down > 20 degrees indicates downward head posture.
- A brief movement is not an alert. Persistence matters.
- Allow per-device calibration and configuration because camera placement changes apparent angles.

# 5. Yawning

- Detect yawn events using mouth openness/shape and minimum duration.
- Treat a single yawn as a weak cue.
- Track repeated yawns in a rolling window.
- Initial prototype trigger: 3 yawn events within 60 seconds produces a moderate drowsiness cue; tune during testing.

# 6. Phone Near Face

- Run object detection at a lower cadence than face landmarks if CPU is constrained.
- Detect phone bounding box and estimate whether its center/edge lies within a configurable region near the face.
- Do not trigger emergency solely because a phone is detected.
- Persistent phone-near-face is a distraction cue and may contribute to Level 1.

# 7. Low-Light / Night Support

- Provide a Night Mode setting.
- Use gamma adjustment, CLAHE, and light denoising only when needed.
- Do not over-enhance the image.
- IR camera input should work through the same camera abstraction.
- Low confidence in dark scenes should lead to UNKNOWN/visibility warning rather than fabricated certainty.

# 8. GUI

- Simple main screen with live preview.
- Required indicators: Monitoring status, Driver state, Camera status, current alert message.
- No internal risk number on the main screen.
- Separate Settings and Alert History views.
- Emergency screen clearly states that notifications are being attempted/sent or that a simulation is active.
- Use clear, readable typography and restrained controls.

# 9. Settings

- Driver display name / optional vehicle ID
- Camera selection
- Mirror preview toggle
- Night mode: Auto/On/Off
- Voice volume and alert sound
- Emergency contacts (4)
- Clip retention settings
- Simulation mode
- Optional cloud sync enable/disable
- Advanced developer thresholds kept out of normal user controls

# 10. Alert History

Each event should show timestamp, state, alert level, trigger summary, whether it recovered, whether emergency escalation was attempted, whether notification was successful, clip path/reference, and sync status. Keep sensitive content minimized.

# 11. Simulation Mode

```text
Scenario: brief_head_turn
Expected: no alert

Scenario: sustained_head_turn
Expected: Level 1 -> recovery or escalation

Scenario: prolonged_eye_closure + yawn + head_down
Expected: DROWSY -> Level 1 -> Level 2 -> Level 3 (when enabled)

Scenario: phone_near_face
Expected: DISTRACTED -> Level 1; no automatic Level 3 from phone alone

Scenario: low_confidence
Expected: UNKNOWN; no drowsiness alert
```

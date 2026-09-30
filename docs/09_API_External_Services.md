# Guardian Drive AI - API & External Services Specification

Adapter contracts for SMS, location, notifications, Firebase and future hardware

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Adapter Principle

External services must be accessed through interfaces. The core monitoring application must not depend directly on a specific SMS, GPS, Firebase, or vehicle vendor.

# 2. Interfaces

```text
CameraSource
LocationProvider
SMSProvider
NotificationProvider
CloudSyncProvider
MediaStorageProvider
VehicleInterface
```

# 3. SMS Provider Contract

```text
send_emergency(message, contacts, event) -> NotificationResult
get_status(message_id) -> DeliveryStatus (optional)
validate_configuration() -> ProviderHealth
```

# 4. SMS Provider Development Modes

| Mode | When | Behavior |
| --- | --- | --- |
| Simulator | Default in development | Writes a realistic message to logs/UI without sending. |
| Test/Sandbox | Optional | Uses provider test environment when available. |
| Production adapter | Future | Requires provider credentials, regulatory/provider requirements, delivery monitoring. |

# 5. Location Provider Contract

```text
get_current_location() -> LocationResult
LocationResult = {available, latitude, longitude, accuracy_m, timestamp, source, error}
```

# 6. Location Sources

- Windows location when available.
- External GPS later through serial/NMEA or vendor SDK.
- Vehicle GPS later through VehicleInterface.
- If unavailable, return a valid unavailable result; never fabricate location.

# 7. Notification Provider Contract

```text
notify_emergency(event, contacts) -> NotificationResult
notify_status(message_id) -> DeliveryStatus (optional)
```

# 8. Firebase Sync Contract

```text
enqueue(event)
flush_pending()
get_health()
close()
```

# 9. External Error Model

| Error | Required behavior |
| --- | --- |
| TIMEOUT | Retry with exponential backoff |
| UNAUTHORIZED | Mark configuration error; do not loop indefinitely |
| RATE_LIMIT | Respect provider backoff |
| NETWORK_OFFLINE | Queue locally |
| INVALID_PAYLOAD | Log and mark permanent failure; require developer fix |
| STORAGE_ERROR | Keep metadata; record clip failure |

# 10. Data Payload Rules

- Use ISO 8601 timestamps.
- Use generated event IDs.
- No raw frames in API payloads.
- Location must include source and accuracy when available.
- Notification responses must be normalized to a common schema.

# 11. Future Vehicle Interface

```text
VehicleInterface
  arm_hazard_simulation()
  set_hazard_state(on_off)
  read_vehicle_status()
  close()
```

# 12. Production Boundary

> **Note:** The desktop prototype should never directly control physical vehicle systems. A future vehicle interface must be separately engineered, validated, and safety-reviewed before any physical actuation is considered.

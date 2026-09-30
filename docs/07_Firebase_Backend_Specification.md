# Guardian Drive AI - Firebase Backend Specification

Optional cloud sync, Firestore model, Cloud Functions boundary and media handling

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Backend Philosophy

Firebase is optional infrastructure for cloud-backed features. The local Windows application must work without Firebase. Use Firebase for data that benefits from remote persistence, controlled synchronization, or future mobile/web consumers.

# 2. Firebase Services

| Service | Use | Rationale |
| --- | --- | --- |
| Cloud Firestore | Recommended | Alert metadata, device configuration, emergency-contact metadata as allowed, sync status. |
| Cloud Functions | Recommended | Trusted backend operations, notification orchestration, validation. |
| Cloud Storage | Optional | Emergency clips only when cloud media is explicitly enabled. |
| Firebase Authentication | Deferred | Not required for first local version; add if multi-user/cloud access is introduced. |
| Firebase Cloud Messaging | Future optional | Useful if a future mobile emergency-contact app is built. |

# 3. Firestore Collections

```text
devices/{deviceId}
drivers/{driverId}
settings/{deviceId}
emergencyContacts/{contactId}
alerts/{alertId}
syncQueue/{queueItemId}
```

# 4. Alert Document Fields

| Field | Type | Purpose |
| --- | --- | --- |
| alertId | string | Unique event ID |
| deviceId | string | Logical device identifier |
| driverId | string/null | Local driver reference |
| createdAt | timestamp | Event creation |
| resolvedAt | timestamp/null | Recovery time |
| state | string | Driver state |
| severity | string | INFO/WARNING/HIGH/CRITICAL |
| alertLevel | number | 0-3 |
| triggerSummary | map/string | Compact signal summary |
| location | geo/null | Coordinates when available |
| clipRef | string/null | Cloud Storage reference if enabled |
| notificationStatus | map | Per-provider/contact results |
| syncStatus | string | pending/synced/failed |

# 5. Cloud Functions Boundary

- Validate event payloads.
- Write/normalize cloud records.
- Generate signed media references when appropriate.
- Call notification providers without exposing provider secrets to the desktop client.
- Clean up expired cloud clips/metadata if configured.

# 6. Client-to-Backend Flow

```text
Windows App
   |
   | HTTPS request with device-scoped auth/token
   v
Cloud Function / trusted endpoint
   |
   +--> validate
   +--> write Firestore
   +--> invoke notification provider (if configured)
   +--> return result
```

# 7. Security Requirements

- Least privilege.
- No service-account key in desktop client.
- Validate every request.
- Use server timestamps where practical.
- Restrict Storage paths by event/device identifiers.
- Do not make emergency media public by default.

# 8. Cost Control

- Do not upload continuous frames.
- Sync compact alert metadata.
- Upload video only for explicit emergency/alert retention policy.
- Use bounded retries and deduplication.
- Keep local history independent of cloud availability.

# 9. References

- Firebase Firestore Data Model: https://firebase.google.com/docs/firestore/data-model
- Firebase Cloud Functions: https://firebase.google.com/docs/functions
- Firebase Cloud Messaging: https://firebase.google.com/docs/cloud-messaging
- Firebase Cloud Storage: https://firebase.google.com/docs/storage/

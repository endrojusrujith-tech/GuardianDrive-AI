# Guardian Drive AI - Database Schema

Local SQLite schema plus cloud document mapping

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Local Database Strategy

Use SQLite as the local source of truth for configuration, alert history, and event metadata. This avoids dependence on a network service and gives the application a reliable offline history.

# 2. Tables

| Table | Key fields | Purpose |
| --- | --- | --- |
| drivers | driver_id PK, display_name, vehicle_id, created_at, updated_at | One or more local driver profiles. |
| emergency_contacts | contact_id PK, driver_id FK, name, phone, priority, enabled, created_at, updated_at | Up to four active contacts. |
| settings | key PK, value_json, updated_at | Configuration values. |
| alerts | alert_id PK, created_at, resolved_at, state, severity, level, trigger_json, location_json, clip_path, notification_json, sync_status | Alert/event history. |
| sync_queue | queue_id PK, alert_id, operation, payload_json, attempts, next_retry_at, last_error, status | Offline cloud synchronization. |
| app_events | event_id PK, created_at, category, message, details_json | Operational diagnostics with privacy constraints. |

# 3. Example Alert Record

```text
{
  "alert_id": "EVT-20260925-00123",
  "created_at": "2026-09-25T11:45:12+05:30",
  "state": "DROWSY",
  "severity": "HIGH",
  "level": 2,
  "trigger": {
    "eye_closure_s": 2.4,
    "yawns_60s": 3,
    "head_pitch_down_deg": 23.1
  },
  "location": null,
  "clip_path": "data/clips/EVT-...mp4",
  "notification": {"status": "not_configured"},
  "sync_status": "pending"
}
```

# 4. Firestore Mapping

| SQLite | Firestore | Mapping |
| --- | --- | --- |
| drivers | drivers/{driverId} | Profile metadata only. |
| emergency_contacts | emergencyContacts/{contactId} | Minimize sensitive fields; encrypt/protect as platform supports. |
| alerts | alerts/{alertId} | Cloud copy of compact event metadata. |
| settings | settings/{deviceId} | Cloud-configured settings only if sync is enabled. |
| sync_queue | not necessarily cloud-stored | Local mechanism, not a cloud collection requirement. |

# 5. Indexing Suggestions

- alerts by created_at descending
- alerts by state + created_at
- alerts by severity + created_at
- emergencyContacts by driver_id
- syncQueue by status + next_retry_at

# 6. Retention

- Local alerts: configurable, recommended 90 days for metadata.
- Local clips: 7 days by default for alert clips; emergency clips 30 days by default; configurable.
- Cloud metadata/media: independently configurable.
- Expired media must not remain in sync queue.

# 7. Migration

1. All schema changes are versioned.
2. Migration scripts must be idempotent.
3. Backup local database before destructive migration.
4. Tests must verify migration from the previous schema.

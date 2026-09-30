"""
Guardian Drive AI - Storage Repositories
Data access objects for SQLite tables:
  - DriverRepository
  - SettingsRepository
  - AlertRepository
  - SyncQueueRepository
  - AppEventRepository
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.models import AlertEvent, AlertLevel, DriverState
from app.storage.encryption import LocalProtector
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DriverRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def get_active_driver(self) -> Dict[str, Any]:
        with self._db.transaction() as cur:
            cur.execute("SELECT * FROM drivers ORDER BY created_at ASC LIMIT 1;")
            row = cur.fetchone()
            if row:
                return dict(row)
            # Fallback creation
            now = _utc_now_iso()
            d_id = "driver-default"
            cur.execute(
                "INSERT INTO drivers (driver_id, display_name, vehicle_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?);",
                (d_id, "Default Driver", "CAR-01", now, now),
            )
            return {"driver_id": d_id, "display_name": "Default Driver", "vehicle_id": "CAR-01"}

    def save_driver(self, display_name: str, vehicle_id: str, driver_id: Optional[str] = None) -> str:
        with self._db.transaction() as cur:
            if not driver_id:
                cur.execute("SELECT driver_id FROM drivers LIMIT 1;")
                row = cur.fetchone()
                driver_id = row["driver_id"] if row else "driver-default"

            now = _utc_now_iso()
            cur.execute(
                """
                INSERT INTO drivers (driver_id, display_name, vehicle_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(driver_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    vehicle_id=excluded.vehicle_id,
                    updated_at=excluded.updated_at;
                """,
                (driver_id, display_name, vehicle_id, now, now),
            )
            return driver_id

    def get_contacts(self, driver_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._db.transaction() as cur:
            if not driver_id:
                d = self.get_active_driver()
                driver_id = d["driver_id"]
            cur.execute(
                "SELECT * FROM emergency_contacts WHERE driver_id = ? ORDER BY priority ASC, created_at ASC LIMIT 4;",
                (driver_id,),
            )
            results = []
            for row in cur.fetchall():
                r = dict(row)
                r["phone"] = LocalProtector.unprotect(r["phone"])
                results.append(r)
            return results

    def save_contacts(self, contacts: List[Dict[str, Any]], driver_id: Optional[str] = None) -> None:
        """Saves up to 4 emergency contacts for the driver."""
        with self._db.transaction() as cur:
            if not driver_id:
                d = self.get_active_driver()
                driver_id = d["driver_id"]

            cur.execute("DELETE FROM emergency_contacts WHERE driver_id = ?;", (driver_id,))
            now = _utc_now_iso()
            for idx, c in enumerate(contacts[:4], start=1):
                cid = c.get("contact_id") or f"cnt-{uuid.uuid4().hex[:8]}"
                name = c.get("name", "").strip()
                phone = c.get("phone", "").strip()
                if not name and not phone:
                    continue
                protected_phone = LocalProtector.protect(phone)
                priority = int(c.get("priority", idx))
                enabled = 1 if c.get("enabled", True) else 0
                cur.execute(
                    """
                    INSERT INTO emergency_contacts
                    (contact_id, driver_id, name, phone, priority, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (cid, driver_id, name, protected_phone, priority, enabled, now, now),
                )


class SettingsRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def get(self, key: str, default: Any = None) -> Any:
        with self._db.transaction() as cur:
            cur.execute("SELECT value_json FROM settings WHERE key = ?;", (key,))
            row = cur.fetchone()
            if row:
                try:
                    return json.loads(row["value_json"])
                except Exception:
                    return row["value_json"]
            return default

    def set(self, key: str, value: Any) -> None:
        with self._db.transaction() as cur:
            now = _utc_now_iso()
            val_json = json.dumps(value)
            cur.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at;
                """,
                (key, val_json, now),
            )

    def get_all(self) -> Dict[str, Any]:
        with self._db.transaction() as cur:
            cur.execute("SELECT key, value_json FROM settings;")
            res = {}
            for row in cur.fetchall():
                try:
                    res[row["key"]] = json.loads(row["value_json"])
                except Exception:
                    res[row["key"]] = row["value_json"]
            return res


class AlertRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def record_alert(self, event: AlertEvent) -> str:
        with self._db.transaction() as cur:
            event_id = event.event_id or f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
            created_at = (
                event.timestamp_utc.isoformat()
                if event.timestamp_utc
                else _utc_now_iso()
            )
            state_val = event.driver_state.value if hasattr(event.driver_state, "value") else str(event.driver_state)
            level_val = int(event.alert_level)
            severity = "CRITICAL" if level_val == 3 else ("HIGH" if level_val == 2 else "WARNING")

            trigger_json = json.dumps({"summary": event.trigger_summary, "simulated": event.simulated})
            loc_json = json.dumps({"location": event.location_str})
            notif_json = json.dumps({
                "attempted": event.emergency_attempted,
                "delivered": event.emergency_delivered,
                "provider": event.emergency_provider,
            })

            cur.execute(
                """
                INSERT INTO alerts
                (alert_id, created_at, resolved_at, state, severity, level,
                 trigger_json, location_json, clip_path, notification_json, sync_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    resolved_at=excluded.resolved_at,
                    clip_path=excluded.clip_path,
                    notification_json=excluded.notification_json,
                    sync_status=excluded.sync_status;
                """,
                (
                    event_id,
                    created_at,
                    None,
                    state_val,
                    severity,
                    level_val,
                    trigger_json,
                    loc_json,
                    event.clip_path,
                    notif_json,
                    event.sync_status or "local",
                ),
            )
            return event_id

    def save_event(self, event: AlertEvent) -> str:
        """Alias for record_alert."""
        return self.record_alert(event)


    def resolve_alert(self, event_id: str, resolved_at: Optional[datetime] = None) -> None:
        with self._db.transaction() as cur:
            res_str = (resolved_at or datetime.now(timezone.utc)).isoformat()
            cur.execute("UPDATE alerts SET resolved_at = ? WHERE alert_id = ?;", (res_str, event_id))

    def update_clip_path(self, event_id: str, clip_path: str) -> None:
        with self._db.transaction() as cur:
            cur.execute("UPDATE alerts SET clip_path = ? WHERE alert_id = ?;", (clip_path, event_id))

    def update_alert_level(self, event_id: str, level: AlertLevel, state: DriverState, clip_path: str = "") -> None:
        """Update an existing event as it escalates without duplicating history."""
        level_value = int(level)
        severity = "CRITICAL" if level_value == 3 else ("HIGH" if level_value == 2 else "WARNING")
        with self._db.transaction() as cur:
            cur.execute(
                "UPDATE alerts SET level = ?, severity = ?, state = ?, clip_path = COALESCE(NULLIF(?, ''), clip_path) WHERE alert_id = ?;",
                (level_value, severity, state.value, clip_path, event_id),
            )

    def update_notification_status(self, event_id: str, attempted: bool, delivered: bool, provider: str) -> None:
        with self._db.transaction() as cur:
            notif_json = json.dumps({
                "attempted": attempted,
                "delivered": delivered,
                "provider": provider,
            })
            cur.execute("UPDATE alerts SET notification_json = ? WHERE alert_id = ?;", (notif_json, event_id))

    def update_sync_status(self, event_id: str, sync_status: str) -> None:
        with self._db.transaction() as cur:
            cur.execute("UPDATE alerts SET sync_status = ? WHERE alert_id = ?;", (sync_status, event_id))

    def get_alerts(
        self,
        limit: int = 50,
        offset: int = 0,
        state: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._db.transaction() as cur:
            query = "SELECT * FROM alerts"
            params: List[Any] = []
            conditions = []
            if state:
                conditions.append("state = ?")
                params.append(state)
            if severity:
                conditions.append("severity = ?")
                params.append(severity)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
            params.extend([limit, offset])

            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_alert_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        with self._db.transaction() as cur:
            cur.execute("SELECT * FROM alerts WHERE alert_id = ?;", (event_id,))
            row = cur.fetchone()
            return dict(row) if row else None


class SyncQueueRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def enqueue(self, alert_id: str, operation: str, payload: Dict[str, Any]) -> str:
        with self._db.transaction() as cur:
            qid = f"sq-{uuid.uuid4().hex[:10]}"
            now = _utc_now_iso()
            cur.execute(
                """
                INSERT INTO sync_queue (queue_id, alert_id, operation, payload_json, attempts, next_retry_at, status)
                VALUES (?, ?, ?, ?, 0, ?, 'pending');
                """,
                (qid, alert_id, operation, json.dumps(payload), now),
            )
            return qid

    def peek_pending(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._db.transaction() as cur:
            now = _utc_now_iso()
            cur.execute(
                """
                SELECT * FROM sync_queue
                WHERE status = 'pending' AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY next_retry_at ASC LIMIT ?;
                """,
                (now, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def mark_success(self, queue_id: str) -> None:
        with self._db.transaction() as cur:
            cur.execute("UPDATE sync_queue SET status = 'synced' WHERE queue_id = ?;", (queue_id,))

    def mark_failed(self, queue_id: str, error: str, max_attempts: int = 5) -> None:
        with self._db.transaction() as cur:
            cur.execute("SELECT attempts FROM sync_queue WHERE queue_id = ?;", (queue_id,))
            row = cur.fetchone()
            attempts = (row["attempts"] if row else 0) + 1
            if attempts >= max_attempts:
                new_status = "failed"
                next_retry = None
            else:
                new_status = "pending"
                backoff_seconds = min(3600, 2 ** attempts * 10)
                next_retry = (datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)).isoformat()

            cur.execute(
                """
                UPDATE sync_queue
                SET attempts = ?, last_error = ?, status = ?, next_retry_at = ?
                WHERE queue_id = ?;
                """,
                (attempts, error[:255], new_status, next_retry, queue_id),
            )


class AppEventRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def log(self, category: str, message: str, details: Optional[Dict[str, Any]] = None) -> str:
        with self._db.transaction() as cur:
            eid = f"log-{uuid.uuid4().hex[:8]}"
            now = _utc_now_iso()
            cur.execute(
                """
                INSERT INTO app_events (event_id, created_at, category, message, details_json)
                VALUES (?, ?, ?, ?, ?);
                """,
                (eid, now, category, message, json.dumps(details) if details else None),
            )
            return eid

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._db.transaction() as cur:
            cur.execute("SELECT * FROM app_events ORDER BY created_at DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cur.fetchall()]

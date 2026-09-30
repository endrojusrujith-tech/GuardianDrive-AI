"""
Guardian Drive AI - SQLite Database Manager
Thread-safe local database connection, schema setup, and migrations.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator, Optional

from app.utils.logging_config import get_logger

_log = get_logger(__name__)

DEFAULT_DB_PATH = os.path.join("data", "local", "guardian_drive.db")


class DatabaseManager:
    """
    Manages SQLite database connections with WAL mode and foreign key constraints.
    Thread-safe through thread-local connections.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._ensure_db_dir()
        self.init_schema()

    def _ensure_db_dir(self) -> None:
        parent = os.path.dirname(os.path.abspath(self.db_path))
        os.makedirs(parent, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for atomic database transactions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def close(self) -> None:
        """Closes the current thread's connection if any."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def init_schema(self) -> None:
        """Initializes tables and indexes idempotently."""
        with self._init_lock:
            with self.transaction() as cur:
                # 1. drivers
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS drivers (
                        driver_id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        vehicle_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """)

                # 2. emergency_contacts
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS emergency_contacts (
                        contact_id TEXT PRIMARY KEY,
                        driver_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 1,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (driver_id) REFERENCES drivers(driver_id) ON DELETE CASCADE
                    );
                """)

                # 3. settings
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """)

                # 4. alerts
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        alert_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        resolved_at TEXT,
                        state TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        level INTEGER NOT NULL,
                        trigger_json TEXT,
                        location_json TEXT,
                        clip_path TEXT,
                        notification_json TEXT,
                        sync_status TEXT NOT NULL DEFAULT 'local'
                    );
                """)

                # 5. sync_queue
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sync_queue (
                        queue_id TEXT PRIMARY KEY,
                        alert_id TEXT,
                        operation TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        next_retry_at TEXT,
                        last_error TEXT,
                        status TEXT NOT NULL DEFAULT 'pending'
                    );
                """)

                # 6. app_events
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS app_events (
                        event_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        category TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details_json TEXT
                    );
                """)

                # Indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_state_created ON alerts(state, created_at);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity_created ON alerts(severity, created_at);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_emergency_contacts_driver ON emergency_contacts(driver_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue_status_retry ON sync_queue(status, next_retry_at);")

                # Default driver seed if none exists
                cur.execute("SELECT COUNT(*) as count FROM drivers;")
                row = cur.fetchone()
                if row and row["count"] == 0:
                    import uuid
                    from datetime import datetime, timezone
                    now_str = datetime.now(timezone.utc).isoformat()
                    cur.execute(
                        "INSERT INTO drivers (driver_id, display_name, vehicle_id, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?);",
                        ("driver-default", "Default Driver", "CAR-01", now_str, now_str)
                    )
            _log.info("SQLite database schema initialized at %s", self.db_path)

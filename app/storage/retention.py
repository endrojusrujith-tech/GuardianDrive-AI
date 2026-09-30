"""
Guardian Drive AI - Data Retention Manager
Enforces local data retention policies:
  - Local alert records: 90 days (configurable)
  - Alert video clips: 7 days (configurable)
  - Emergency video clips: 30 days (configurable)
  - Sync queue cleanup: synced items > 7 days pruned
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.config.settings import Settings
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class RetentionManager:
    """Prunes expired clips and database records according to retention policy."""

    def __init__(self, db: DatabaseManager, settings: Optional[Settings] = None) -> None:
        self._db = db
        self._cfg = settings

    def run_pruning(self) -> dict:
        """Executes pruning passes and returns count of removed items."""
        now = datetime.now(timezone.utc)

        # Retention limits
        alerts_retention_days = int(
            self._cfg.get_value("storage", "alerts_retention_days", default=90)
            if self._cfg else 90
        )
        alert_clip_days = int(
            self._cfg.get_value("storage", "alert_clip_retention_days", default=7)
            if self._cfg else 7
        )
        emergency_clip_days = int(
            self._cfg.get_value("storage", "emergency_clip_retention_days", default=30)
            if self._cfg else 30
        )

        cutoff_alerts = (now - timedelta(days=alerts_retention_days)).isoformat()
        cutoff_alert_clips = (now - timedelta(days=alert_clip_days)).isoformat()
        cutoff_emerg_clips = (now - timedelta(days=emergency_clip_days)).isoformat()
        cutoff_synced_queue = (now - timedelta(days=7)).isoformat()

        deleted_clips = 0
        deleted_alerts = 0
        deleted_queue = 0

        try:
            # 1. Prune clips on disk
            with self._db.transaction() as cur:
                # Find expired Level 1/2 clips
                cur.execute(
                    "SELECT alert_id, clip_path FROM alerts WHERE level < 3 AND clip_path IS NOT NULL AND created_at < ?;",
                    (cutoff_alert_clips,),
                )
                for row in cur.fetchall():
                    path = row["clip_path"]
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                            deleted_clips += 1
                        except OSError as e:
                            _log.warning("Could not delete clip file %s: %s", path, e)
                cur.execute(
                    "UPDATE alerts SET clip_path = NULL WHERE level < 3 AND created_at < ?;",
                    (cutoff_alert_clips,),
                )

                # Find expired Level 3 clips
                cur.execute(
                    "SELECT alert_id, clip_path FROM alerts WHERE level >= 3 AND clip_path IS NOT NULL AND created_at < ?;",
                    (cutoff_emerg_clips,),
                )
                for row in cur.fetchall():
                    path = row["clip_path"]
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                            deleted_clips += 1
                        except OSError as e:
                            _log.warning("Could not delete emergency clip file %s: %s", path, e)
                cur.execute(
                    "UPDATE alerts SET clip_path = NULL WHERE level >= 3 AND created_at < ?;",
                    (cutoff_emerg_clips,),
                )

                # 2. Prune old alerts
                cur.execute("DELETE FROM alerts WHERE created_at < ?;", (cutoff_alerts,))
                deleted_alerts = cur.rowcount

                # 3. Prune synced items in queue
                cur.execute("DELETE FROM sync_queue WHERE status = 'synced' AND next_retry_at < ?;", (cutoff_synced_queue,))
                deleted_queue = cur.rowcount

            _log.info(
                "Retention pruning complete: %d clips removed, %d alert records pruned, %d sync queue items pruned",
                deleted_clips, deleted_alerts, deleted_queue,
            )
        except Exception as exc:
            _log.error("Retention pruning error: %s", exc)

        return {
            "deleted_clips": deleted_clips,
            "deleted_alerts": deleted_alerts,
            "deleted_queue": deleted_queue,
        }

"""
Guardian Drive AI - Cloud Sync Queue Worker
Background worker that processes pending sync operations from SQLite.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Optional

from app.cloud.firebase_adapter import CloudAdapter
from app.storage.repositories import AlertRepository, SyncQueueRepository
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class SyncQueueWorker:
    """Processes background sync items with bounded backoff and error recording."""

    def __init__(
        self,
        db: DatabaseManager,
        cloud_adapter: CloudAdapter,
        interval_seconds: float = 30.0,
    ) -> None:
        self._db = db
        self._cloud = cloud_adapter
        self._queue_repo = SyncQueueRepository(db)
        self._alert_repo = AlertRepository(db)
        self._interval = interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SyncQueueThread")
        self._thread.start()
        _log.info("Cloud sync queue worker started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        _log.info("Cloud sync queue worker stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.process_batch()
            except Exception as exc:
                _log.error("SyncQueue processing error: %s", exc)
            self._stop_event.wait(self._interval)

    def process_batch(self, limit: int = 10) -> int:
        if not self._cloud.is_enabled:
            return 0

        pending = self._queue_repo.peek_pending(limit=limit)
        processed = 0

        for item in pending:
            qid = item["queue_id"]
            aid = item["alert_id"]
            op = item["operation"]

            try:
                payload = json.loads(item["payload_json"]) if item["payload_json"] else {}
            except Exception:
                payload = {}

            if op == "sync_alert":
                success = self._cloud.sync_alert(payload)
                if success:
                    self._queue_repo.mark_success(qid)
                    if aid:
                        self._alert_repo.update_sync_status(aid, "synced")
                    processed += 1
                else:
                    self._queue_repo.mark_failed(qid, "Cloud adapter sync returned false")
                    if aid:
                        self._alert_repo.update_sync_status(aid, "sync_failed")

        return processed

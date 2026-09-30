"""
Guardian Drive AI - Firebase / Cloud Adapter
Provides optional synchronization with cloud backends (Firebase Firestore / Cloud Functions).
Maintains clean boundary: no service accounts exposed; graceful offline fallback.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from app.config.settings import Settings
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class CloudAdapter:
    """
    Adapter for communicating with cloud endpoints.
    In prototype/offline mode, operates in simulation/mock mode without raising errors.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._cfg = settings
        self._enabled = bool(settings.get_value("cloud", "enabled", default=False)) if settings else False
        self._endpoint = str(settings.get_value("cloud", "api_endpoint", default="")) if settings else ""
        self._api_key = str(settings.get_value("cloud", "api_key", default="")) if settings else ""
        self._device_id = str(settings.get_value("cloud", "device_id", default="WIN-DEV-001")) if settings else "WIN-DEV-001"

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def sync_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Synchronizes an alert event record with the cloud.
        Returns True if synced successfully, False otherwise.
        """
        if not self._enabled:
            _log.debug("Cloud sync is disabled; skipping cloud alert push.")
            return False

        if not self._endpoint:
            # Simulated cloud sync
            _log.info("Cloud sync simulated for alert %s (no remote endpoint configured)", alert_data.get("alert_id"))
            return True

        try:
            import urllib.request
            payload = json.dumps({
                "deviceId": self._device_id,
                "event": alert_data,
                "syncedAt": time.time(),
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self._endpoint.rstrip('/')}/syncAlert",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Device-Id": self._device_id,
                    "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if 200 <= resp.status < 300:
                    _log.info("Cloud sync successfully pushed alert %s", alert_data.get("alert_id"))
                    return True
                else:
                    _log.warning("Cloud endpoint returned status %d", resp.status)
                    return False
        except Exception as exc:
            _log.warning("Cloud sync request failed for alert %s: %s", alert_data.get("alert_id"), exc)
            return False

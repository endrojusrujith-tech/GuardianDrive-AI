"""
Guardian Drive AI - Emergency Manager
Coordinates Level 3 emergency:
  - Creates event record in SQLite
  - Collects location
  - Saves clip
  - Dispatches notifications through provider
  - Reports results to GUI callback
  - Does NOT block the monitoring loop
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from app.config.settings import Settings
from app.emergency.clip_manager import ClipManager
from app.emergency.location_provider import LocationProvider
from app.emergency.notification_provider import Contact, NotificationProvider
from app.models import AlertEvent, AlertLevel, RiskAssessment
from app.utils.logging_config import get_logger
from app.utils.time_utils import generate_event_id, wall_time, wall_time_local

_log = get_logger(__name__)

_EMERGENCY_MSG_TEMPLATE = """GUARDIAN DRIVE AI - EMERGENCY ALERT

Driver: {driver}
Vehicle: {vehicle}
Condition: {condition}
Severity: CRITICAL
Time: {time}
Location: {location}
Recent alerts: {alerts}
Event ID: {event_id}
Clip reference: {clip_ref}

NOTE: This is a prototype system. Not safety-certified."""


class EmergencyManager:
    """Thread-safe emergency event lifecycle coordinator."""

    def __init__(
        self,
        settings: Settings,
        db_repo,                                     # storage.repositories.EventRepository
        notification_provider: NotificationProvider,
        location_provider: LocationProvider,
        clip_manager: ClipManager,
        on_status_update: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._cfg = settings
        self._db = db_repo
        self._notifier = notification_provider
        self._locator = location_provider
        self._clipper = clip_manager
        self._on_status = on_status_update

    def trigger(self, assessment: RiskAssessment, trigger_ts: float, simulated: bool = False) -> None:
        """
        Fire a Level 3 emergency event.
        Call from any thread — executes asynchronously.
        """
        t = threading.Thread(
            target=self._run,
            args=(assessment, trigger_ts, simulated),
            daemon=True,
        )
        t.start()

    def _run(self, assessment: RiskAssessment, trigger_ts: float, simulated: bool) -> None:
        event_id = generate_event_id()
        _log.critical("Emergency event %s triggered (simulated=%s).", event_id, simulated)

        # 1. Location
        fix = self._locator.get_location()
        loc_str = f"{fix.latitude:.5f},{fix.longitude:.5f}" if fix else "Unavailable"

        # 2. Clip
        clip_path = ""
        try:
            clip_path = self._clipper.save_clip(event_id, AlertLevel.LEVEL3, trigger_ts) or ""
        except Exception as exc:
            _log.error("Clip save failed: %s", exc)

        # 3. Contacts
        contacts_cfg = self._cfg.notification_contacts
        contacts = [Contact(name=c.get("name", ""), phone=c.get("phone", ""))
                    for c in contacts_cfg if c.get("phone")]

        # 4. Message payload
        msg = _EMERGENCY_MSG_TEMPLATE.format(
            driver=self._cfg.driver_name,
            vehicle=self._cfg.vehicle_id or "Unknown",
            condition=assessment.driver_state.value,
            time=wall_time_local().strftime("%Y-%m-%d %H:%M:%S"),
            location=loc_str,
            alerts=f"Level {assessment.alert_level.value}",
            event_id=event_id,
            clip_ref=clip_path or "None",
        )

        # 5. Create DB record
        event = AlertEvent(
            event_id=event_id,
            alert_level=AlertLevel.LEVEL3,
            driver_state=assessment.driver_state,
            timestamp_utc=wall_time(),
            trigger_summary=f"state={assessment.driver_state.value}",
            location_str=loc_str,
            clip_path=clip_path,
            simulated=simulated,
            emergency_provider="SIMULATOR" if simulated else self._cfg.get_value(
                "notifications", "provider", default="simulator"
            ),
        )
        try:
            if self._db:
                self._db.record_alert(event)
        except Exception as exc:
            _log.error("DB save failed: %s", exc)

        # 6. Send notifications
        results = []
        if contacts or simulated:
            if simulated and not contacts:
                contacts = [Contact(name="Simulated Contact", phone="000-0000")]
            try:
                results = self._notifier.send(contacts, msg)
            except Exception as exc:
                _log.error("Notification send failed: %s", exc)

        # 7. Report results
        delivered = sum(1 for r in results if r.success)
        total = len(results)
        status_msg = (
            f"Emergency {event_id}: {delivered}/{total} contacts notified"
            + (" [SIMULATION]" if simulated else "")
        )
        _log.info(status_msg)
        self._notify_gui(status_msg)

        # 8. Update DB with delivery results
        try:
            if self._db:
                event.emergency_attempted = True
                event.emergency_delivered = delivered > 0
                self._db.update_notification_status(event_id, True, delivered > 0, event.emergency_provider)
        except Exception:
            pass

    def _notify_gui(self, msg: str) -> None:
        if self._on_status:
            try:
                self._on_status(msg)
            except Exception:
                pass

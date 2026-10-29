"""
Unit tests for Guardian Drive AI storage layer and SQLite repositories.
"""
import os
import tempfile

import pytest


from app.models import AlertEvent, AlertLevel, DriverState
from app.storage.encryption import LocalProtector
from app.storage.repositories import (
    DriverRepository,
    SettingsRepository,
    AlertRepository,
    SyncQueueRepository,
    AppEventRepository,
)
from app.storage.retention import RetentionManager
from app.storage.sqlite_db import DatabaseManager


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_guardian.db")
    db = DatabaseManager(db_path=db_file)
    yield db
    db.close()


def test_encryption_roundtrip():
    secret = "+919876543210"
    encrypted = LocalProtector.protect(secret)
    assert encrypted != secret
    decrypted = LocalProtector.unprotect(encrypted)
    assert decrypted == secret


def test_driver_repository(temp_db):
    repo = DriverRepository(temp_db)
    driver = repo.get_active_driver()
    assert driver is not None
    assert "driver_id" in driver

    # Save driver
    repo.save_driver("Alex Pilot", "CAR-99", driver["driver_id"])
    updated = repo.get_active_driver()
    assert updated["display_name"] == "Alex Pilot"
    assert updated["vehicle_id"] == "CAR-99"

    # Emergency contacts
    contacts = [
        {"name": "Emergency 1", "phone": "+1234567890", "priority": 1, "enabled": True},
        {"name": "Emergency 2", "phone": "+9876543210", "priority": 2, "enabled": True},
    ]
    repo.save_contacts(contacts, driver_id=driver["driver_id"])
    saved_contacts = repo.get_contacts(driver_id=driver["driver_id"])
    assert len(saved_contacts) == 2
    assert saved_contacts[0]["name"] == "Emergency 1"
    assert saved_contacts[0]["phone"] == "+1234567890"


def test_settings_repository(temp_db):
    repo = SettingsRepository(temp_db)
    repo.set("camera.mirror", True)
    repo.set("camera.device_index", 1)

    assert repo.get("camera.mirror") is True
    assert repo.get("camera.device_index") == 1
    assert repo.get("non_existent", "default_val") == "default_val"


def test_alert_repository(temp_db):
    repo = AlertRepository(temp_db)
    event = AlertEvent(
        event_id="EVT-TEST-001",
        alert_level=AlertLevel.LEVEL2,
        driver_state=DriverState.DROWSY,
        trigger_summary="Prolonged eye closure 2.5s",
        location_str="40.7128,-74.0060",
    )
    eid = repo.record_alert(event)
    assert eid == "EVT-TEST-001"

    alerts = repo.get_alerts()
    assert len(alerts) == 1
    assert alerts[0]["alert_id"] == "EVT-TEST-001"
    assert alerts[0]["state"] == "DROWSY"
    assert alerts[0]["level"] == 2


def test_retention_manager(temp_db):
    retention = RetentionManager(db=temp_db)
    result = retention.run_pruning()
    assert "deleted_clips" in result
    assert "deleted_alerts" in result


def test_notification_simulator():
    from app.emergency.notification_provider import Contact, SimulatorProvider

    provider = SimulatorProvider()
    contacts = [
        Contact(name="One", phone="+15550000001"),
        Contact(name="Two", phone="+15550000002"),
    ]
    results = provider.send(contacts, "EMERGENCY test message")
    assert len(results) == 2
    assert all(r.success for r in results)
    assert all(r.provider == "SIMULATOR" for r in results)
    # Empty contact list is a no-op, never a hard failure
    assert provider.send([], "msg") == []


def test_retention_prunes_old_alerts_and_clips(temp_db, tmp_path):
    from datetime import datetime, timedelta, timezone

    repo = AlertRepository(temp_db)
    retention = RetentionManager(db=temp_db)

    now = datetime.now(timezone.utc)

    def _make_event(level, days_ago, clip_name):
        clip = str(tmp_path / clip_name)
        with open(clip, "wb") as fh:
            fh.write(b"fake-clip-bytes")
        event = AlertEvent(
            alert_level=level,
            driver_state=DriverState.DROWSY,
            timestamp_utc=now - timedelta(days=days_ago),
            trigger_summary="test",
            clip_path=clip,
        )
        return repo.record_alert(event), clip

    # Level 1 alert, 20 days old: past clip retention (7 d), within alert retention (90 d)
    eid_l1, clip_l1 = _make_event(AlertLevel.LEVEL1, 20, "l1_clip.mp4")
    # Level 3 alert, 40 days old: past emergency clip retention (30 d), within alert retention
    eid_l3, clip_l3 = _make_event(AlertLevel.LEVEL3, 40, "l3_clip.mp4")
    # Alert record 100 days old: past alert retention (90 d)
    eid_old, _ = _make_event(AlertLevel.LEVEL2, 100, "old_clip.mp4")

    assert os.path.exists(clip_l1) and os.path.exists(clip_l3)

    result = retention.run_pruning()

    assert not os.path.exists(clip_l1), "expired L1 clip should be removed"
    assert not os.path.exists(clip_l3), "expired L3 clip should be removed"
    assert result["deleted_clips"] >= 2
    assert result["deleted_alerts"] >= 1

    remaining = repo.get_alerts()
    ids = {a["alert_id"] for a in remaining}
    assert eid_l1 in ids  # L1 alert record itself is younger than 90 days
    assert eid_l3 in ids
    assert eid_old not in ids  # 100-day-old alert record pruned
    for row in remaining:
        if row["clip_path"]:
            assert os.path.exists(row["clip_path"]), "remaining clip files must still exist"

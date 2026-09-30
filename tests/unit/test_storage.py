"""
Unit tests for Guardian Drive AI storage layer and SQLite repositories.
"""
import os
import tempfile


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

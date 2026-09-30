"""
Guardian Drive AI - Settings View
Configuration panel for driver details, emergency contacts, camera, audio, and retention.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QSlider,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from app.config.settings import Settings
from app.gui.dialogs import ContactEditDialog
from app.storage.repositories import DriverRepository
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class SettingsView(QWidget):
    """Settings interface for configuring the driver monitoring system."""

    def __init__(self, settings: Settings, db: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self._cfg = settings
        self._db = db
        self._driver_repo = DriverRepository(db)
        self._init_ui()
        self.load_settings()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Scroll area for clean layout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)

        # Styling
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 13px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

        # 1. Driver Profile
        driver_grp = QGroupBox("Driver & Vehicle Profile")
        driver_form = QFormLayout(driver_grp)
        self.driver_name_edit = QLineEdit()
        self.vehicle_id_edit = QLineEdit()
        driver_form.addRow("Driver Name:", self.driver_name_edit)
        driver_form.addRow("Vehicle ID:", self.vehicle_id_edit)
        layout.addWidget(driver_grp)

        # 2. Camera & Video
        cam_grp = QGroupBox("Camera & Vision Settings")
        cam_form = QFormLayout(cam_grp)
        self.cam_index_spin = QSpinBox()
        self.cam_index_spin.setRange(0, 10)
        self.mirror_chk = QCheckBox("Mirror camera preview")
        self.night_mode_combo = QComboBox()
        self.night_mode_combo.addItems(["off", "auto", "on"])
        cam_form.addRow("Camera Device Index:", self.cam_index_spin)
        cam_form.addRow("Preview Orientation:", self.mirror_chk)
        cam_form.addRow("Night Mode (Low Light):", self.night_mode_combo)
        layout.addWidget(cam_grp)

        # 3. Audio & Voice Alerts
        alert_grp = QGroupBox("Alerts & Feedback")
        alert_form = QFormLayout(alert_grp)
        self.audio_chk = QCheckBox("Enable Audio Sound Beeps")
        self.tts_chk = QCheckBox("Enable Text-to-Speech Voice Alerts")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(90)
        alert_form.addRow("Sound Alerts:", self.audio_chk)
        alert_form.addRow("Voice Alerts:", self.tts_chk)
        alert_form.addRow("TTS Volume:", self.volume_slider)
        layout.addWidget(alert_grp)

        # 4. Emergency Contacts (Max 4)
        contact_grp = QGroupBox("Emergency Contacts (Up to 4)")
        c_layout = QVBoxLayout(contact_grp)

        self.contact_table = QTableWidget()
        self.contact_table.setColumnCount(4)
        self.contact_table.setHorizontalHeaderLabels(["Priority", "Name", "Phone", "Active"])
        self.contact_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.contact_table.setMaximumHeight(150)
        c_layout.addWidget(self.contact_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add / Edit Contact")
        add_btn.clicked.connect(self._edit_selected_contact)
        del_btn = QPushButton("Remove Contact")
        del_btn.setStyleSheet("background-color: #dc2626;")
        del_btn.clicked.connect(self._delete_selected_contact)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        c_layout.addLayout(btn_row)
        layout.addWidget(contact_grp)

        # 5. Cloud & Storage Retention
        store_grp = QGroupBox("Storage & Cloud Sync")
        store_form = QFormLayout(store_grp)
        self.cloud_sync_chk = QCheckBox("Enable Cloud Synchronization")
        self.cloud_clip_chk = QCheckBox("Upload Emergency Video Clips to Cloud")
        self.alert_retention_spin = QSpinBox()
        self.alert_retention_spin.setRange(1, 365)
        self.alert_retention_spin.setValue(90)
        self.alert_retention_spin.setSuffix(" days")
        store_form.addRow("Cloud Sync:", self.cloud_sync_chk)
        store_form.addRow("Cloud Media:", self.cloud_clip_chk)
        store_form.addRow("Alert Log Retention:", self.alert_retention_spin)
        layout.addWidget(store_grp)

        # Save Button Bar
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-size: 14px;
                padding: 10px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.save_btn.clicked.connect(self.save_settings)
        action_row.addWidget(self.save_btn)
        layout.addLayout(action_row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_settings(self) -> None:
        # Load Driver Profile
        driver = self._driver_repo.get_active_driver()
        self.driver_name_edit.setText(driver.get("display_name", "Default Driver"))
        self.vehicle_id_edit.setText(driver.get("vehicle_id", "CAR-01"))

        # Camera
        self.cam_index_spin.setValue(int(self._cfg.get_value("camera", "device_index", default=0)))
        self.mirror_chk.setChecked(self._cfg.mirror_preview)
        self.night_mode_combo.setCurrentText(str(self._cfg.get_value("camera", "night_mode", default="off")).lower())

        # Audio
        self.audio_chk.setChecked(bool(self._cfg.get_value("alerts", "sound_enabled", default=True)))
        self.tts_chk.setChecked(bool(self._cfg.get_value("alerts", "tts_enabled", default=True)))
        self.volume_slider.setValue(int(float(self._cfg.get_value("alerts", "tts_volume", default=0.9)) * 100))

        # Storage & Cloud
        self.cloud_sync_chk.setChecked(bool(self._cfg.get_value("cloud", "enabled", default=False)))
        self.cloud_clip_chk.setChecked(bool(self._cfg.get_value("cloud", "upload_clips", default=False)))
        self.alert_retention_spin.setValue(int(self._cfg.get_value("storage", "alerts_retention_days", default=90)))

        # Load Contacts
        self._refresh_contacts_table()

    def _refresh_contacts_table(self) -> None:
        contacts = self._driver_repo.get_contacts()
        self.contact_table.setRowCount(len(contacts))
        for r_idx, c in enumerate(contacts):
            self.contact_table.setItem(r_idx, 0, QTableWidgetItem(str(c.get("priority", r_idx + 1))))
            self.contact_table.setItem(r_idx, 1, QTableWidgetItem(c.get("name", "")))
            self.contact_table.setItem(r_idx, 2, QTableWidgetItem(c.get("phone", "")))
            self.contact_table.setItem(r_idx, 3, QTableWidgetItem("Yes" if c.get("enabled", 1) else "No"))

    def _edit_selected_contact(self) -> None:
        contacts = self._driver_repo.get_contacts()
        curr_row = self.contact_table.currentRow()
        existing = contacts[curr_row] if (0 <= curr_row < len(contacts)) else None

        if not existing and len(contacts) >= 4:
            QMessageBox.warning(self, "Limit Reached", "Maximum of 4 emergency contacts allowed.")
            return

        dlg = ContactEditDialog(self, existing)
        if dlg.exec() == ContactEditDialog.Accepted:
            data = dlg.get_contact_data()
            if existing:
                contacts[curr_row] = {**existing, **data}
            else:
                contacts.append(data)
            self._driver_repo.save_contacts(contacts)
            self._refresh_contacts_table()

    def _delete_selected_contact(self) -> None:
        curr_row = self.contact_table.currentRow()
        contacts = self._driver_repo.get_contacts()
        if 0 <= curr_row < len(contacts):
            contacts.pop(curr_row)
            self._driver_repo.save_contacts(contacts)
            self._refresh_contacts_table()

    def save_settings(self) -> None:
        # Save driver
        d_name = self.driver_name_edit.text().strip() or "Default Driver"
        v_id = self.vehicle_id_edit.text().strip() or "CAR-01"
        self._driver_repo.save_driver(d_name, v_id)

        # Save config
        self._cfg.set_value("camera", "device_index", self.cam_index_spin.value())
        self._cfg.set_value("camera", "mirror_preview", self.mirror_chk.isChecked())
        self._cfg.set_value("camera", "night_mode", self.night_mode_combo.currentText())

        self._cfg.set_value("alerts", "sound_enabled", self.audio_chk.isChecked())
        self._cfg.set_value("alerts", "tts_enabled", self.tts_chk.isChecked())
        self._cfg.set_value("alerts", "tts_volume", self.volume_slider.value() / 100.0)

        self._cfg.set_value("cloud", "enabled", self.cloud_sync_chk.isChecked())
        self._cfg.set_value("cloud", "upload_clips", self.cloud_clip_chk.isChecked())
        self._cfg.set_value("storage", "alerts_retention_days", self.alert_retention_spin.value())

        self._cfg.save()
        QMessageBox.information(self, "Settings Saved", "Guardian Drive AI configuration saved successfully.")

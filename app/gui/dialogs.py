"""
Guardian Drive AI - GUI Dialogs
Emergency alert banner/dialog, contact edit dialog, and information popups.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QFormLayout,
    QMessageBox,
)


class EmergencyDialog(QDialog):
    """
    Modal emergency dialog shown when Level 3 Emergency occurs.
    Displays clear status, countdown/dismissal, and contact dispatch confirmation.
    """

    def __init__(self, parent=None, event_summary: str = "", simulated: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("CRITICAL EMERGENCY ALERT - GUARDIAN DRIVE AI")
        self.setModal(True)
        self.resize(520, 320)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b0b0b;
                color: #ffffff;
                border: 3px solid #ff3333;
                border-radius: 8px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 6px;
                border: 1px solid #ff6666;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("CRITICAL DRIVER CONDITION DETECTED")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff5252;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        if simulated:
            sim_badge = QLabel("[ SIMULATION MODE ACTIVE - NO REAL 911/SMS SENT ]")
            sim_badge.setStyleSheet("color: #ffcc00; font-weight: bold; font-size: 13px;")
            sim_badge.setAlignment(Qt.AlignCenter)
            layout.addWidget(sim_badge)

        self.info_label = QLabel(event_summary or "Level 3 Emergency Protocol Initiated.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 14px; background-color: #3d1414; padding: 12px; border-radius: 4px;")
        layout.addWidget(self.info_label)

        status_lbl = QLabel("• Emergency clip recorded\n• Local database incident logged\n• Dispatching alerts to emergency contacts...")
        status_lbl.setStyleSheet("font-size: 13px; color: #e0e0e0;")
        layout.addWidget(status_lbl)

        layout.addStretch()

        btn_row = QHBoxLayout()
        self.ack_btn = QPushButton("Acknowledge & Dismiss")
        self.ack_btn.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(self.ack_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


class ContactEditDialog(QDialog):
    """Dialog to add or edit an emergency contact."""

    def __init__(self, parent=None, contact_data: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Emergency Contact")
        self.setModal(True)
        self.resize(380, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e2430;
                color: #e2e8f0;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#cancelBtn {
                background-color: #475569;
            }
            QPushButton#cancelBtn:hover {
                background-color: #334155;
            }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Contact Name")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+1234567890 or +91...")
        self.priority_edit = QLineEdit()
        self.priority_edit.setPlaceholderText("1 - 4")
        self.enabled_chk = QCheckBox("Active Contact")
        self.enabled_chk.setChecked(True)

        if contact_data:
            self.name_edit.setText(contact_data.get("name", ""))
            self.phone_edit.setText(contact_data.get("phone", ""))
            self.priority_edit.setText(str(contact_data.get("priority", 1)))
            self.enabled_chk.setChecked(bool(contact_data.get("enabled", True)))

        form.addRow("Name:", self.name_edit)
        form.addRow("Phone Number:", self.phone_edit)
        form.addRow("Priority (1-4):", self.priority_edit)
        form.addRow("", self.enabled_chk)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._validate_and_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _validate_and_save(self) -> None:
        name = self.name_edit.text().strip()
        phone = self.phone_edit.text().strip()
        if not name or not phone:
            QMessageBox.warning(self, "Invalid Input", "Please enter both contact name and phone number.")
            return
        self.accept()

    def get_contact_data(self) -> Dict[str, Any]:
        try:
            prio = int(self.priority_edit.text().strip() or "1")
        except ValueError:
            prio = 1
        return {
            "name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "priority": prio,
            "enabled": self.enabled_chk.isChecked(),
        }

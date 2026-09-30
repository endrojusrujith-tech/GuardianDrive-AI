"""
Guardian Drive AI - Alert History View
Displays recorded alert incidents from local SQLite database:
  - Timestamp, Driver State, Alert Level, Severity
  - Trigger Summary, Recovery status
  - Emergency Dispatch status
  - Video Clip path / open action
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QMessageBox,
)

from app.storage.repositories import AlertRepository
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class HistoryView(QWidget):
    """View presenting past alert events and recorded clips."""

    def __init__(self, db: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._repo = AlertRepository(db)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header controls
        hdr_row = QHBoxLayout()
        title = QLabel("Incident & Alert History")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        hdr_row.addWidget(title)

        hdr_row.addStretch()

        filter_lbl = QLabel("Filter State:")
        filter_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
        hdr_row.addWidget(filter_lbl)

        self.state_filter = QComboBox()
        self.state_filter.addItems(["ALL", "DROWSY", "DISTRACTED", "CRITICAL", "UNKNOWN"])
        self.state_filter.currentTextChanged.connect(self.load_data)
        hdr_row.addWidget(self.state_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        hdr_row.addWidget(refresh_btn)

        layout.addLayout(hdr_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Event ID", "Timestamp (UTC)", "State", "Level", "Severity", "Trigger Summary", "Clip"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                gridline-color: #1e293b;
                border: 1px solid #1e293b;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #1e3a8a;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                font-weight: bold;
                padding: 6px;
                border: none;
            }
        """)
        self.table.cellDoubleClicked.connect(self._on_row_double_click)
        layout.addWidget(self.table)

        # Bottom help
        tip_lbl = QLabel("Double-click a row to open recorded video clip (if available on disk).")
        tip_lbl.setStyleSheet("color: #64748b; font-size: 12px; font-style: italic;")
        layout.addWidget(tip_lbl)

        self.load_data()

    def load_data(self) -> None:
        state_filter = self.state_filter.currentText()
        filt = None if state_filter == "ALL" else state_filter
        alerts = self._repo.get_alerts(limit=100, state=filt)

        self.table.setRowCount(len(alerts))
        for row_idx, alert in enumerate(alerts):
            self.table.setItem(row_idx, 0, QTableWidgetItem(alert.get("alert_id", "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(alert.get("created_at", "")[:19]))

            state_item = QTableWidgetItem(alert.get("state", ""))
            state_val = alert.get("state", "")
            if state_val == "CRITICAL":
                state_item.setForeground(Qt.red)
            elif state_val == "DROWSY":
                state_item.setForeground(Qt.yellow)
            self.table.setItem(row_idx, 2, state_item)

            self.table.setItem(row_idx, 3, QTableWidgetItem(f"L{alert.get('level', 0)}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(alert.get("severity", "")))

            # Parse trigger JSON
            trig_summary = ""
            trig_raw = alert.get("trigger_json")
            if trig_raw:
                try:
                    import json
                    t_dict = json.loads(trig_raw)
                    trig_summary = t_dict.get("summary", "")
                except Exception:
                    trig_summary = str(trig_raw)
            self.table.setItem(row_idx, 5, QTableWidgetItem(trig_summary))

            clip = alert.get("clip_path") or ""
            clip_text = "Available" if clip and os.path.exists(clip) else ("None" if not clip else "Missing")
            clip_item = QTableWidgetItem(clip_text)
            clip_item.setData(Qt.UserRole, clip)
            self.table.setItem(row_idx, 6, clip_item)

    def _on_row_double_click(self, row: int, col: int) -> None:
        clip_item = self.table.item(row, 6)
        if not clip_item:
            return
        clip_path = clip_item.data(Qt.UserRole)
        if not clip_path or not os.path.exists(clip_path):
            QMessageBox.information(self, "No Clip", "No local video clip is available for this event.")
            return

        try:
            # On Windows, open with default video player
            os.startfile(os.path.abspath(clip_path))
        except Exception as exc:
            _log.warning("Could not launch default player for clip: %s", exc)
            QMessageBox.warning(self, "Open Error", f"Unable to open video clip: {exc}")

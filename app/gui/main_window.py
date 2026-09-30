"""
Guardian Drive AI - Main Application Window
PySide6 desktop window containing:
  - Tabbed interface: Live Monitoring, Incident History, Settings
  - Status bar with system diagnostics
  - Clean, dark automotive aesthetic
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QStatusBar,
    QLabel,
    QMessageBox,
)

from app.config.settings import Settings
from app.gui.dialogs import EmergencyDialog
from app.gui.history_view import HistoryView
from app.gui.monitoring_view import MonitoringView
from app.gui.settings_view import SettingsView
from app.models import SimulationScenario
from app.pipeline import PipelineController
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class MainWindow(QMainWindow):
    """Primary application window for Guardian Drive AI."""

    def __init__(self, settings: Settings, db: DatabaseManager) -> None:
        super().__init__()
        self._cfg = settings
        self._db = db

        self.setWindowTitle("Guardian Drive AI - Driver Attention Monitoring System")
        self.resize(1024, 768)
        self.setMinimumSize(800, 600)

        # Global stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0f19;
                color: #f8fafc;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background-color: #0b0f19;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #334155;
                color: #e2e8f0;
            }
            QStatusBar {
                background-color: #0f172a;
                color: #64748b;
                font-size: 12px;
                border-top: 1px solid #1e293b;
            }
        """)

        # Core Pipeline Controller
        self.pipeline = PipelineController(settings=self._cfg, db=self._db, parent=self)

        # Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 1. Monitoring View
        self.monitoring_view = MonitoringView()
        self.tabs.addTab(self.monitoring_view, "Live Monitoring")

        # 2. History View
        self.history_view = HistoryView(db=self._db)
        self.tabs.addTab(self.history_view, "Incident History")

        # 3. Settings View
        self.settings_view = SettingsView(settings=self._cfg, db=self._db)
        self.tabs.addTab(self.settings_view, "Settings")

        # Connect Pipeline signals to MonitoringView
        self.pipeline.status_updated.connect(self.monitoring_view.update_status)
        self.pipeline.frame_ready.connect(self.monitoring_view.update_frame)
        self.pipeline.emergency_triggered.connect(self._on_emergency_triggered)

        # Connect MonitoringView requests to Pipeline
        self.monitoring_view.start_requested.connect(self.pipeline.start_monitoring)
        self.monitoring_view.stop_requested.connect(self.pipeline.stop_monitoring)
        self.monitoring_view.simulation_requested.connect(self.pipeline.start_simulation)
        self.monitoring_view.stop_simulation_requested.connect(self.pipeline.stop_simulation)

        # Status Bar
        self._init_status_bar()

    def _init_status_bar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)

        self.db_status_lbl = QLabel("DB: SQLite (WAL Active)")
        self.db_status_lbl.setStyleSheet("color: #10b981; margin-right: 16px;")
        bar.addPermanentWidget(self.db_status_lbl)

        version_lbl = QLabel("Guardian Drive AI v1.0 (Windows Prototype)")
        version_lbl.setStyleSheet("color: #64748b; margin-right: 12px;")
        bar.addPermanentWidget(version_lbl)

        bar.showMessage("Ready")

    def _on_emergency_triggered(self, summary: str, is_simulated: bool) -> None:
        """Pops up the modal emergency dialog when Level 3 occurs."""
        dlg = EmergencyDialog(self, event_summary=summary, simulated=is_simulated)
        dlg.exec()
        # Refresh history table to display the new emergency event
        self.history_view.load_data()

    def closeEvent(self, event) -> None:
        """Graceful shutdown when closing window."""
        _log.info("Closing application window; stopping pipeline...")
        self.pipeline.stop_monitoring()
        self.pipeline.stop_simulation()
        self._db.close()
        event.accept()

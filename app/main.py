"""
Guardian Drive AI - Application Entry Point
Initializes configuration, storage, vision pipeline, and launches the PySide6 desktop GUI.
"""
from __future__ import annotations

import argparse
import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.config.settings import Settings
from app.gui.main_window import MainWindow
from app.models import SimulationScenario
from app.storage.retention import RetentionManager
from app.storage.sqlite_db import DatabaseManager
from app.utils.logging_config import get_logger, setup_logging

_log = get_logger("guardian_drive")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guardian Drive AI - Driver Attention Monitoring System")
    parser.add_argument("--config", type=str, default=None, help="Path to custom config YAML")
    parser.add_argument("--scenario", type=str, default=None, help="Launch directly into a simulation scenario")
    parser.add_argument("--headless", action="store_true", help="Run without GUI (for automated testing)")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    return parser.parse_args()


def run_app() -> int:
    args = parse_args()
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level)

    _log.info("Starting Guardian Drive AI...")

    # Load configuration
    settings = Settings(config_path=args.config)

    # Initialize local SQLite database
    db = DatabaseManager()

    # Run retention maintenance pass
    retention = RetentionManager(db=db, settings=settings)
    retention.run_pruning()

    if args.headless:
        _log.info("Running in headless mode...")
        from app.pipeline import PipelineController
        # Minimal headless execution loop
        controller = PipelineController(settings=settings, db=db)
        if args.scenario:
            try:
                scen = SimulationScenario(args.scenario)
                controller.start_simulation(scen)
            except ValueError:
                _log.error("Unknown scenario: %s", args.scenario)
                return 1
        else:
            controller.start_monitoring()

        import time
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            _log.info("Headless run interrupted; stopping.")
            controller.stop_monitoring()
            controller.stop_simulation()
            db.close()
        return 0

    # Windows High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("Guardian Drive AI")
    app.setOrganizationName("GuardianDrive")

    window = MainWindow(settings=settings, db=db)
    window.show()

    # If scenario flag passed, auto-start simulation
    if args.scenario:
        try:
            scen = SimulationScenario(args.scenario)
            window.pipeline.start_simulation(scen)
        except ValueError:
            _log.warning("Unknown command-line scenario: %s", args.scenario)

    exit_code = app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(run_app())

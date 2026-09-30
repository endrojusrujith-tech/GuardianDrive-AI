"""
Integration tests for the end-to-end PipelineController.
"""
import os
import tempfile
import time


from app.config.settings import Settings
from app.models import DriverState, GuiStatus, SimulationScenario
from app.pipeline import PipelineController
from app.storage.sqlite_db import DatabaseManager


def test_pipeline_simulation_run():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "pipeline_test.db")
    db = DatabaseManager(db_path=db_file)
    settings = Settings()

    controller = PipelineController(settings=settings, db=db)

    received_statuses = []

    def on_status(status: GuiStatus):
        received_statuses.append(status)

    controller.status_updated.connect(on_status)

    # Start normal driving simulation
    controller.start_simulation(SimulationScenario.NORMAL_DRIVING)

    # Run for 1.0 second
    time.sleep(1.0)

    controller.stop_simulation()
    db.close()

    assert len(received_statuses) > 0
    assert any(s.monitoring_active for s in received_statuses)

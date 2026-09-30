"""
Guardian Drive AI - Automated Test Runner
Runs all unit, scenario, and integration tests using Python standard library unittest.
"""
from __future__ import annotations

import os
import sys
import unittest

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.unit.test_models import (
    test_driver_state_values,
    test_alert_levels,
    test_face_features_defaults,
    test_risk_assessment_defaults,
    test_gui_status_defaults,
)
from tests.unit.test_storage import (
    test_encryption_roundtrip,
    test_driver_repository,
    test_settings_repository,
    test_alert_repository,
    test_retention_manager,
    temp_db,
)
from tests.scenarios.test_scenarios import (
    test_tc04_brief_head_turn_no_alert,
    test_tc05_sustained_head_turn_triggers_distracted,
    test_tc06_brief_eye_closure_no_alert,
    test_tc07_prolonged_eye_closure_triggers_drowsy,
    test_tc10_multi_signal_drowsiness_escalation,
    make_engines,
)
from tests.integration.test_pipeline_flow import test_pipeline_simulation_run
from tests.unit.test_safety_logic import (
    test_low_confidence_never_promotes_alert,
    test_unknown_input_pauses_existing_escalation,
    test_phone_only_cannot_reach_level_three,
)


class TestGuardianDrive(unittest.TestCase):

    def test_01_models(self):
        test_driver_state_values()
        test_alert_levels()
        test_face_features_defaults()
        test_risk_assessment_defaults()
        test_gui_status_defaults()

    def test_02_encryption(self):
        test_encryption_roundtrip()

    def test_03_storage(self):
        # Use temp_db generator
        db_gen = temp_db()
        db = next(db_gen)
        try:
            test_driver_repository(db)
            test_settings_repository(db)
            test_alert_repository(db)
            test_retention_manager(db)
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def test_04_scenarios(self):
        eng = make_engines()
        test_tc04_brief_head_turn_no_alert(eng)
        test_tc05_sustained_head_turn_triggers_distracted(eng)
        test_tc06_brief_eye_closure_no_alert(eng)
        test_tc07_prolonged_eye_closure_triggers_drowsy(eng)
        test_tc10_multi_signal_drowsiness_escalation(eng)

    def test_05_safety_boundaries(self):
        test_low_confidence_never_promotes_alert()
        test_unknown_input_pauses_existing_escalation()
        test_phone_only_cannot_reach_level_three()

    def test_06_pipeline_integration(self):
        test_pipeline_simulation_run()


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGuardianDrive)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

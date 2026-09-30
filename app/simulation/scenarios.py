"""
Guardian Drive AI - Simulation Scenarios
Deterministic scenario definitions for automated tests and live simulation demo:
  1. NORMAL_DRIVING
  2. BRIEF_HEAD_TURN (<2.0s -> NO alert)
  3. SUSTAINED_HEAD_TURN (>=4.0s -> DISTRACTED, Level 1)
  4. REPEATED_YAWNING (3 yawns in 60s)
  5. PROLONGED_EYE_CLOSURE (>=2.5s -> DROWSY, Level 1/2)
  6. MULTI_SIGNAL_DROWSINESS (Closure + yawns + head down -> rapid escalation)
  7. PHONE_DISTRACTION (Phone near face >=4s -> DISTRACTED)
  8. LOW_CONFIDENCE (Occlusion/darkness -> UNKNOWN)
  9. CAMERA_DISCONNECT (Camera failure -> CameraStatus.FAILED)
 10. NO_INTERNET (Offline verification)
 11. FULL_ESCALATION (Drowsiness sustained through Level 1, Level 2, into Level 3)
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple
from app.models import EyeState, FaceFeatures, HeadDirection, SimulationScenario


class ScenarioStep(NamedTuple):
    duration_s: float
    face_detected: bool = True
    face_count: int = 1
    confidence: float = 0.95
    ear: float = 0.32
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    head_dir: HeadDirection = HeadDirection.FORWARD
    mar: float = 0.15
    yawn_detected: bool = False
    phone_detected: bool = False
    phone_conf: float = 0.0
    brightness: float = 130.0
    blur: float = 120.0


# Map each SimulationScenario to a list of sequential ScenarioStep stages
SCENARIOS: Dict[SimulationScenario, List[ScenarioStep]] = {
    # 1. Normal driving: steady forward attention, eyes open
    SimulationScenario.NORMAL_DRIVING: [
        ScenarioStep(duration_s=15.0, ear=0.32, head_yaw=0.0, head_pitch=0.0, head_dir=HeadDirection.FORWARD),
    ],

    # 2. Brief head turn: 1.0 second turn left (MUST NOT trigger alert) followed by forward
    SimulationScenario.BRIEF_HEAD_TURN: [
        ScenarioStep(duration_s=3.0, ear=0.32, head_yaw=0.0, head_dir=HeadDirection.FORWARD),
        ScenarioStep(duration_s=1.0, ear=0.32, head_yaw=-30.0, head_dir=HeadDirection.LEFT),
        ScenarioStep(duration_s=6.0, ear=0.32, head_yaw=0.0, head_dir=HeadDirection.FORWARD),
    ],

    # 3. Sustained head turn: looking away for 5 seconds -> triggers DISTRACTED and Level 1
    SimulationScenario.SUSTAINED_HEAD_TURN: [
        ScenarioStep(duration_s=2.0, ear=0.32, head_yaw=0.0, head_dir=HeadDirection.FORWARD),
        ScenarioStep(duration_s=5.0, ear=0.30, head_yaw=35.0, head_dir=HeadDirection.RIGHT),
        ScenarioStep(duration_s=5.0, ear=0.32, head_yaw=0.0, head_dir=HeadDirection.FORWARD),
    ],

    # 4. Repeated yawning: 3 yawns within 60s
    SimulationScenario.REPEATED_YAWNING: [
        ScenarioStep(duration_s=2.0, ear=0.30),
        ScenarioStep(duration_s=3.0, ear=0.25, mar=0.70, yawn_detected=True),  # Yawn 1
        ScenarioStep(duration_s=4.0, ear=0.30, mar=0.15),
        ScenarioStep(duration_s=3.0, ear=0.25, mar=0.68, yawn_detected=True),  # Yawn 2
        ScenarioStep(duration_s=4.0, ear=0.30, mar=0.15),
        ScenarioStep(duration_s=3.0, ear=0.25, mar=0.72, yawn_detected=True),  # Yawn 3
        ScenarioStep(duration_s=6.0, ear=0.30, mar=0.15),
    ],

    # 5. Prolonged eye closure: eyes shut for 3.5s -> triggers DROWSY and Level 1/2
    SimulationScenario.PROLONGED_EYE_CLOSURE: [
        ScenarioStep(duration_s=2.0, ear=0.32),
        ScenarioStep(duration_s=4.0, ear=0.10),  # Eyes closed (EAR < 0.20)
        ScenarioStep(duration_s=5.0, ear=0.32),  # Driver opens eyes / recovers
    ],

    # 6. Multi-signal drowsiness: prolonged eye closure + yawn + head down posture
    SimulationScenario.MULTI_SIGNAL_DROWSINESS: [
        ScenarioStep(duration_s=2.0, ear=0.32),
        ScenarioStep(duration_s=2.5, ear=0.22, mar=0.68, yawn_detected=True),
        ScenarioStep(duration_s=4.5, ear=0.08, head_pitch=25.0, head_dir=HeadDirection.DOWN),
        ScenarioStep(duration_s=4.0, ear=0.32, head_pitch=0.0, head_dir=HeadDirection.FORWARD),
    ],

    # 7. Phone distraction: phone detected near face for 5.0 seconds
    SimulationScenario.PHONE_DISTRACTION: [
        ScenarioStep(duration_s=2.0, ear=0.32),
        ScenarioStep(duration_s=5.0, ear=0.30, phone_detected=True, phone_conf=0.92),
        ScenarioStep(duration_s=4.0, ear=0.32, phone_detected=False),
    ],

    # 8. Low confidence: face confidence drops to 0.15, low light
    SimulationScenario.LOW_CONFIDENCE: [
        ScenarioStep(duration_s=2.0, ear=0.32, confidence=0.95),
        ScenarioStep(duration_s=5.0, ear=0.32, confidence=0.20, brightness=20.0, blur=30.0),
        ScenarioStep(duration_s=4.0, ear=0.32, confidence=0.95),
    ],

    # 9. Camera disconnect / failure
    SimulationScenario.CAMERA_DISCONNECT: [
        ScenarioStep(duration_s=2.0, face_detected=True),
        ScenarioStep(duration_s=6.0, face_detected=False, confidence=0.0),
    ],

    # 10. No internet: normal driving under offline conditions
    SimulationScenario.NO_INTERNET: [
        ScenarioStep(duration_s=8.0, ear=0.32, head_yaw=0.0, head_dir=HeadDirection.FORWARD),
    ],

    # 11. Full escalation: continuous severe drowsiness past Level 1, past Level 2, into Level 3 emergency!
    SimulationScenario.FULL_ESCALATION: [
        ScenarioStep(duration_s=2.0, ear=0.32),
        # Severe eye closure + head nod down maintained for 20+ seconds
        ScenarioStep(duration_s=25.0, ear=0.08, head_pitch=26.0, head_dir=HeadDirection.DOWN),
        ScenarioStep(duration_s=5.0, ear=0.32, head_pitch=0.0, head_dir=HeadDirection.FORWARD),
    ],
}

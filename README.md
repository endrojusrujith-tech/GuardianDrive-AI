# Guardian Drive AI

Guardian Drive AI is an experimental, local-first Windows driver-monitoring prototype. It is not safety certified, does not prevent accidents, and does not guarantee emergency delivery.

## Run on Windows

1. Install Python 3.11+ and make it available as `python` or `py`.
2. Create a virtual environment and install `pip install -r requirements.txt`.
3. Run `python main.py`.
4. Choose **Start Monitoring**, or select a simulation scenario in the app.

Run a deterministic simulation directly with `python -m app.main --scenario full_escalation`. Automated tests run with `python -m pytest -q`.

The checked-in YuNet model provides face presence/count fallback. For eye, yawn, and head-pose landmarks, obtain a compatible MediaPipe Face Landmarker task file and place it at `models/face_landmarker.task`; the app remains usable in face-presence fallback mode without it.

Frames are processed locally. The app keeps only a rolling in-memory buffer and writes event clips after alerts. Firebase, location, notifications, and hazard functions are replaceable adapters; notifications default to a simulator and no physical vehicle control is implemented.

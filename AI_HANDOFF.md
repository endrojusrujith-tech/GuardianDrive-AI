# Guardian Drive AI - AI Handoff & Usage Guide

## 1. What to save
Keep the complete specification package in the Guardian Drive AI repository under `docs/` and keep the master prompt in `MASTER_PROMPT.md`.

Recommended handoff set:
- `01_Project_Requirements_SRS.md`
- `02_System_Architecture.md`
- `03_Feature_Specification.md`
- `04_Detection_and_Decision_Logic.md`
- `05_Alert_and_Emergency_Specification.md`
- `06_Privacy_and_Security.md`
- `07_Firebase_Backend_Specification.md`
- `08_Database_Schema.md`
- `09_API_External_Services.md`
- `10_Project_Folder_Architecture.md`
- `11_Test_Plan_and_Test_Cases.md`
- `12_Future_Team_Distribution.md`
- `13_Master_Development_Plan.md`
- `PROJECT_RULES.md`
- `MASTER_PROMPT.md`

## 2. How to start in Antigravity
1. Open the existing Guardian Drive AI folder as an Antigravity project.
2. Put the markdown specification files into the repository so the agent can inspect them directly.
3. Put `PROJECT_RULES.md` at repository root.
4. Put `MASTER_PROMPT.md` at repository root.
5. Start the agent with the master prompt. The agent should audit the existing workspace before editing.
6. Let the agent implement the complete build while following the internal stages in the development plan.

## 3. Recommended first instruction
Paste the full master prompt. Do not replace it with only a short sentence such as "build my project".

## 4. When the AI asks about missing credentials
Use the simulator/stub path. Do not stop the local build merely because Firebase, GPS, or SMS credentials are unavailable.

## 5. When the AI asks about missing hardware
Use webcam simulation or provider mocks. The first release does not require physical vehicle hardware.

## 6. What you should personally verify
- Camera works.
- GUI is simple and readable.
- Brief head turns do not cause alerts.
- Multi-signal drowsiness triggers escalation in simulation and controlled testing.
- Phone detection is a distraction cue only.
- Offline mode continues locally.
- Camera disconnect/reconnect works.
- Alert history and event clips work.
- No secrets are committed.

## 7. Useful follow-up prompts
Use the supplemental prompt pack for workspace audits, continuation, testing, false-alert review, performance, security, camera debugging, and release audits.

## 8. Antigravity usage notes
Use the current official Antigravity desktop application on Windows. The official documentation also provides a Windows CLI. For long builds, keep the persistent project documents in the repository and keep implementation status updated.

## 9. Important safety note
Guardian Drive AI is a prototype driver-monitoring project. It should not be represented as a safety-certified automotive product or relied upon as the sole mechanism for preventing accidents or guaranteeing emergency communication.

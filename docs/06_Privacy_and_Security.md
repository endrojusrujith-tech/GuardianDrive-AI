# Guardian Drive AI - Privacy & Security Specification

Data minimization, local storage, cloud boundaries, secrets and retention

**Version:** 1.0  
**Date:** 2026-09-25

# 1. Privacy Position

Guardian Drive AI should collect the minimum data required for its driving-monitoring functions. The default design is local processing with event-only video retention. Cloud storage is optional and should not be required for basic monitoring.

# 2. Data Categories

| Data | Sensitivity | Default handling |
| --- | --- | --- |
| Live camera frames | High sensitivity | Process in memory; discard unless event clip required. |
| Event clips/images | High sensitivity | Local, event-only, limited retention; cloud optional. |
| Alert metadata | Moderate | Local SQLite; optionally synced. |
| Emergency contacts | Sensitive | Store securely; limit access. |
| Driver settings | Moderate | Local; sync only if enabled. |
| Location | Sensitive | Collect only for emergency/event workflows when available. |
| Provider credentials | Secret | Never commit; use secure local secret storage/environment. |

# 3. Video Retention

- No continuous recording to disk.
- Only save clips around alerts/emergencies.
- Default automatic retention: 7 days for local alert clips, configurable.
- Emergency clips may use a separate retention value; recommended default 30 days for prototype testing, configurable.
- Provide a Delete Now / Clear History action for stored local event artifacts.

# 4. Secrets

- Keep `.env.example` in source control but never actual credentials.
- Never place Firebase service-account JSON in the desktop repository or packaged executable.
- Prefer Windows Credential Manager/keyring for long-lived local secrets in a future hardened version.
- Mask secrets in logs.

# 5. Firebase Security Boundary

The Windows desktop app should not contain a privileged Firebase service-account credential. Prefer a least-privilege client/HTTPS adapter or a trusted serverless backend for privileged operations. Firestore uses collections and documents; Cloud Functions can act as a serverless trusted backend; Cloud Storage can store media when explicitly enabled. See the official Firebase documentation listed in the references.

# 6. Offline Privacy

- When offline, data remains local.
- Do not repeatedly retry network operations in a tight loop.
- Queue only the metadata/artifacts that are explicitly configured for sync.
- Delete queued data when local retention rules expire.

# 7. Access Control

- Normal user can start/stop monitoring and manage basic settings.
- Developer/admin functions should be separate and optionally hidden.
- Alert history and emergency clips are local app data and should not be exposed through a public web endpoint by default.

# 8. Logging

- Log system state and errors, not raw video or full emergency contact numbers.
- Use event IDs to correlate logs.
- Avoid logging camera frames, image arrays, credentials, or secret tokens.

# 9. Security Testing

1. Search source tree for accidental secrets.
2. Verify `.gitignore` excludes `.env`, key files, local clips, logs, and credentials.
3. Attempt cloud operations with invalid credentials and verify graceful failure.
4. Verify local data deletion.
5. Verify no privileged service account is packaged.

# 10. Safety Boundary

> **Note:** This application is an experimental driver-monitoring prototype. It should be tested in safe, controlled environments and should not be used as the sole mechanism for preventing accidents or contacting emergency services.

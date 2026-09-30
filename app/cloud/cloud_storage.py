"""
Guardian Drive AI - Cloud Media Storage Adapter
Handles optional upload of emergency video clips.
Disabled by default for privacy; uses signed upload URLs or simulator.
"""
from __future__ import annotations

import os
from typing import Optional

from app.config.settings import Settings
from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class CloudStorageAdapter:
    """Manages optional cloud storage uploads for emergency clips."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._cfg = settings
        self._enabled = bool(settings.get_value("cloud", "upload_clips", default=False)) if settings else False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def upload_clip(self, local_path: str, event_id: str) -> Optional[str]:
        """
        Uploads an emergency clip if enabled.
        Returns cloud storage URL / reference, or None if disabled/failed.
        """
        if not self._enabled:
            _log.debug("Cloud clip upload is disabled.")
            return None

        if not local_path or not os.path.exists(local_path):
            _log.warning("Local clip not found for upload: %s", local_path)
            return None

        # Simulated upload reference
        _log.info("Simulated cloud storage upload for %s (event %s)", local_path, event_id)
        return f"gs://guardian-drive-emergency/{event_id}/{os.path.basename(local_path)}"

"""
Guardian Drive AI - Time Utilities
Use monotonic time for all duration/persistence measurements.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone


def monotonic() -> float:
    """Return a monotonic timestamp in seconds.  Use for duration arithmetic."""
    return time.monotonic()


def wall_time() -> datetime:
    """Return current UTC wall-clock time (for logging/storage)."""
    return datetime.now(timezone.utc)


def wall_time_local() -> datetime:
    """Return current local wall-clock time (for display)."""
    return datetime.now()


def generate_event_id() -> str:
    """Generate a short unique event ID like EVT-A3F2B1."""
    return "EVT-" + uuid.uuid4().hex[:6].upper()


def format_duration(seconds: float) -> str:
    """Format a duration in seconds as a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"

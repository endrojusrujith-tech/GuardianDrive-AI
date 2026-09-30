"""
Guardian Drive AI - Platform Utilities
Windows-specific helpers (power management, system sleep prevention during monitoring, DPAPI).
Provides clean fallbacks on other platforms.
"""
from __future__ import annotations

import os
import sys
import ctypes
from typing import Optional

from app.utils.logging_config import get_logger

_log = get_logger(__name__)

# Windows Execution State flags for preventing sleep
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def is_windows() -> bool:
    return sys.platform.startswith("win")


def prevent_system_sleep(enable: bool = True) -> bool:
    """
    Prevents Windows from entering sleep or turning off the screen while monitoring is active.
    """
    if not is_windows():
        return False
    try:
        if enable:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            _log.debug("System sleep prevention enabled")
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            _log.debug("System sleep prevention restored to default")
        return True
    except Exception as exc:
        _log.warning("Failed to set thread execution state: %s", exc)
        return False


def get_app_data_dir(app_name: str = "GuardianDriveAI") -> str:
    """Returns persistent application data directory."""
    if is_windows():
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        target = os.path.join(base, app_name)
    else:
        target = os.path.expanduser(f"~/.{app_name.lower()}")
    os.makedirs(target, exist_ok=True)
    return target

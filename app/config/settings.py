"""
Guardian Drive AI - Settings Manager
Loads, merges, and validates application configuration from YAML + runtime overrides.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Optional

import yaml

_CONFIG_DIR = Path(__file__).parent
_DEFAULTS_FILE = _CONFIG_DIR / "defaults.yaml"
_USER_FILE = Path("data/local/user_settings.yaml")


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (base modified in-place)."""
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base


class Settings:
    """Central configuration object.  All modules should read from this."""

    _instance: "Settings | None" = None

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._data: dict[str, Any] = {}
        self._load()
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as fh:
                custom = yaml.safe_load(fh) or {}
            _deep_merge(self._data, custom)

    def save(self) -> None:
        """Alias for save_user."""
        self.save_user()


    # ── singleton ────────────────────────────────────────────────────────────
    @classmethod
    def get(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # ── loading ───────────────────────────────────────────────────────────────
    def _load(self) -> None:
        with open(_DEFAULTS_FILE, "r", encoding="utf-8") as fh:
            self._data = yaml.safe_load(fh) or {}

        if _USER_FILE.exists():
            with open(_USER_FILE, "r", encoding="utf-8") as fh:
                user_data = yaml.safe_load(fh) or {}
            _deep_merge(self._data, user_data)

    def reload(self) -> None:
        self._load()

    def save_user(self) -> None:
        """Persist the current in-memory settings to the user override file."""
        _USER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_USER_FILE, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self._data, fh, default_flow_style=False, allow_unicode=True)

    # ── accessors ─────────────────────────────────────────────────────────────
    def get_value(self, *keys: str, default: Any = None) -> Any:
        """Dot-path style access: get_value('thresholds', 'head_yaw_degrees')."""
        node: Any = self._data
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
        return node

    def set_value(self, *args: Any, value: Any = None) -> None:
        """Set a nested value at runtime; accepts keyword or positional value."""
        if value is None and len(args) >= 2:
            *keys, value = args
        else:
            keys = list(args)
        if not keys:
            raise ValueError("at least one settings key is required")
        node = self._data
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value

    def as_dict(self) -> dict:
        return copy.deepcopy(self._data)

    # ── convenience properties ────────────────────────────────────────────────
    @property
    def debug_mode(self) -> bool:
        return bool(self.get_value("app", "debug_mode", default=False))

    @property
    def lightweight_mode(self) -> bool:
        return bool(self.get_value("app", "lightweight_mode", default=False))

    @lightweight_mode.setter
    def lightweight_mode(self, val: bool) -> None:
        self.set_value("app", "lightweight_mode", value=val)

    @property
    def simulation_enabled(self) -> bool:
        return bool(self.get_value("simulation", "enabled", default=False))

    @simulation_enabled.setter
    def simulation_enabled(self, val: bool) -> None:
        self.set_value("simulation", "enabled", value=val)

    @property
    def simulation_scenario(self) -> str:
        return str(self.get_value("simulation", "scenario", default="full_escalation"))

    @property
    def db_path(self) -> str:
        return str(self.get_value("storage", "db_path", default="data/local/guardian.db"))

    @property
    def driver_name(self) -> str:
        return str(self.get_value("driver", "name", default="Driver"))

    @property
    def vehicle_id(self) -> str:
        return str(self.get_value("driver", "vehicle_id", default=""))

    @property
    def camera_device_index(self) -> int:
        return int(self.get_value("camera", "device_index", default=self.get_value("camera", "index", default=0)))

    @property
    def camera_mirror(self) -> bool:
        return bool(self.get_value("camera", "mirror_preview", default=self.get_value("camera", "mirror", default=False)))

    @property
    def night_mode(self) -> str:
        return str(self.get_value("camera", "night_mode", default="off"))

    @property
    def mirror_preview(self) -> bool:
        return bool(self.get_value("camera", "mirror_preview", default=False))


    @mirror_preview.setter
    def mirror_preview(self, val: bool) -> None:
        self.set_value("camera", "mirror_preview", value=val)

    @property
    def tts_enabled(self) -> bool:
        return bool(self.get_value("alerts", "tts_enabled", default=True))

    @property
    def notification_contacts(self) -> list:
        return list(self.get_value("notifications", "sms_contacts", default=[]))

    @notification_contacts.setter
    def notification_contacts(self, val: list) -> None:
        self.set_value("notifications", "sms_contacts", value=val)

"""
Guardian Drive AI - Location Provider Adapter
Abstract interface + Windows/unavailable implementation.
Future: GPS adapter, vehicle CAN bus location.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.utils.logging_config import get_logger

_log = get_logger(__name__)


@dataclass
class LocationFix:
    latitude: float
    longitude: float
    accuracy_m: float
    source: str


class LocationProvider(ABC):
    @abstractmethod
    def get_location(self) -> Optional[LocationFix]:
        """Return current location or None if unavailable."""


class UnavailableLocationProvider(LocationProvider):
    """Default provider when GPS/location is not configured."""

    def get_location(self) -> Optional[LocationFix]:
        return None


class WindowsLocationProvider(LocationProvider):
    """
    Attempts to use the Windows location API.
    Gracefully falls back to None if unavailable or not permitted.
    """

    def get_location(self) -> Optional[LocationFix]:
        # Windows location API is not yet integrated; placeholder for future implementation.
        return None


def build_location_provider(provider_name: str = "unavailable") -> LocationProvider:
    if provider_name == "windows":
        return WindowsLocationProvider()
    return UnavailableLocationProvider()

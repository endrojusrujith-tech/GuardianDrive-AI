"""
Guardian Drive AI - Notification Provider Adapter
Abstract interface + Simulator implementation.
Production providers (Twilio, Vonage, etc.) implement the same interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from app.utils.logging_config import get_logger
from app.utils.time_utils import wall_time_local

_log = get_logger(__name__)


@dataclass
class Contact:
    name: str
    phone: str


@dataclass
class NotificationResult:
    contact: Contact
    success: bool
    provider: str
    message: str = ""


class NotificationProvider(ABC):
    """Abstract SMS/notification provider."""

    @abstractmethod
    def send(self, contacts: List[Contact], message: str) -> List[NotificationResult]:
        """Send emergency message to all contacts. Returns per-contact results."""


class SimulatorProvider(NotificationProvider):
    """
    Development default: logs the message, returns simulated success.
    Does NOT send any real SMS.
    """

    def send(self, contacts: List[Contact], message: str) -> List[NotificationResult]:
        _log.info("=== SIMULATED EMERGENCY NOTIFICATION ===")
        _log.info("Timestamp: %s", wall_time_local().isoformat())
        _log.info("Message:\n%s", message)
        results = []
        for c in contacts:
            _log.info("  [SIMULATED] → %s (%s): delivered", c.name, c.phone)
            results.append(NotificationResult(
                contact=c,
                success=True,
                provider="SIMULATOR",
                message="Simulated delivery",
            ))
        return results


# Alias for backward compatibility
SimulatorNotificationProvider = SimulatorProvider


def build_provider(provider_name: str) -> NotificationProvider:
    """Factory — returns the configured provider or simulator."""
    if provider_name == "simulator" or not provider_name:
        return SimulatorProvider()
    # Future: return TwilioProvider(), VonageProvider(), etc.
    _log.warning("Unknown provider '%s' — falling back to simulator.", provider_name)
    return SimulatorProvider()

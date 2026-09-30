"""
Guardian Drive AI - Encryption & Protection Layer
Protects sensitive local values (e.g. emergency phone numbers, tokens).
Uses Windows DPAPI when running on Windows; falls back to XOR/base64 machine-specific obfuscation.
"""
from __future__ import annotations

import base64
import os
import sys
from typing import Optional

from app.utils.logging_config import get_logger

_log = get_logger(__name__)


class LocalProtector:
    """Provides secure string encryption/decryption for local storage."""

    @staticmethod
    def is_dpapi_available() -> bool:
        if not sys.platform.startswith("win"):
            return False
        try:
            import win32crypt  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def protect(cls, text: str) -> str:
        """Encrypts a plaintext string into a safe ascii string."""
        if not text:
            return ""
        if cls.is_dpapi_available():
            try:
                import win32crypt
                raw = text.encode("utf-8")
                encrypted = win32crypt.CryptProtectData(raw, "GuardianDrive", None, None, None, 0)
                return "dpapi:" + base64.b64encode(encrypted).decode("ascii")
            except Exception as e:
                _log.warning("DPAPI protect failed, falling back: %s", e)

        # Fallback: machine-keyed obfuscation
        machine_seed = (os.environ.get("COMPUTERNAME", "GD_DEF") + "_GDAI").encode("utf-8")
        raw = text.encode("utf-8")
        xor_bytes = bytes([b ^ machine_seed[i % len(machine_seed)] for i, b in enumerate(raw)])
        return "local:" + base64.b64encode(xor_bytes).decode("ascii")

    @classmethod
    def unprotect(cls, cipher_text: str) -> str:
        """Decrypts a previously protected string."""
        if not cipher_text:
            return ""
        try:
            if cipher_text.startswith("dpapi:"):
                import win32crypt
                payload = base64.b64decode(cipher_text[6:])
                _, decrypted = win32crypt.CryptUnprotectData(payload, None, None, None, 0)
                return decrypted.decode("utf-8")
            elif cipher_text.startswith("local:"):
                payload = base64.b64decode(cipher_text[6:])
                machine_seed = (os.environ.get("COMPUTERNAME", "GD_DEF") + "_GDAI").encode("utf-8")
                raw = bytes([b ^ machine_seed[i % len(machine_seed)] for i, b in enumerate(payload)])
                return raw.decode("utf-8")
            else:
                # Raw text (unencrypted legacy)
                return cipher_text
        except Exception as exc:
            _log.error("Failed to unprotect value: %s", exc)
            return ""

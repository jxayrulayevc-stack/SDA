"""Fernet encryption for the full contents of every maFile."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(Exception):
    """Raised when encrypted data cannot be decrypted with the current key."""


class Encryptor:
    def __init__(self, key: str | bytes) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    @staticmethod
    def generate_key() -> str:
        """Return a new Fernet key suitable for ENCRYPTION_KEY."""
        return Fernet.generate_key().decode()

    def encrypt(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return self._fernet.encrypt(raw).decode("ascii")

    def decrypt(self, token: str) -> dict[str, Any]:
        try:
            raw = self._fernet.decrypt(token.encode("ascii"))
        except (InvalidToken, ValueError, UnicodeEncodeError) as exc:
            raise EncryptionError(
                "Encrypted account data is corrupt or was encrypted with another key"
            ) from exc
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EncryptionError("Encrypted account data has invalid format") from exc
        if not isinstance(payload, dict):
            raise EncryptionError("Encrypted account data has invalid format")
        return payload

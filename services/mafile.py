"""Validation of uploaded maFile contents. No secrets are logged or returned."""

from __future__ import annotations

import json
import re
from typing import Any

from core.steam_guard import InvalidSharedSecretError, decode_shared_secret

ALLOWED_SUFFIXES = (".mafile", ".json")
REQUIRED_FIELDS = ("shared_secret", "account_name", "identity_secret")
LOGIN_RE = re.compile(r"^[A-Za-z0-9_-]{3,64}$")
DEFAULT_MAX_UPLOAD_BYTES = 100 * 1024
MAX_SECRET_BYTES = 256
MIN_SECRET_BYTES = 8


class MaFileValidationError(ValueError):
    """Safe-to-show-to-admin validation error (never contains secret values)."""


def validate_mafile(
    raw: bytes,
    filename: str,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> dict[str, Any]:
    if not filename.lower().endswith(ALLOWED_SUFFIXES):
        raise MaFileValidationError("Разрешены только файлы .maFile и .json")
    if not raw:
        raise MaFileValidationError("Файл пуст")
    if len(raw) > max_upload_bytes:
        raise MaFileValidationError("Файл слишком большой (максимум 100 КБ)")
    try:
        payload: Any = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaFileValidationError("Файл не является корректным JSON") from exc
    if not isinstance(payload, dict):
        raise MaFileValidationError("Ожидается JSON-объект maFile")

    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise MaFileValidationError(f"Отсутствует или пустое поле {field}")

    login = payload["account_name"].strip()
    if not LOGIN_RE.fullmatch(login):
        raise MaFileValidationError("Поле account_name имеет некорректный формат")
    payload["account_name"] = login

    for field in ("shared_secret", "identity_secret"):
        try:
            decoded = decode_shared_secret(payload[field])
        except InvalidSharedSecretError as exc:
            raise MaFileValidationError(f"Поле {field} не является корректным base64") from exc
        if not MIN_SECRET_BYTES <= len(decoded) <= MAX_SECRET_BYTES:
            raise MaFileValidationError(f"Поле {field} имеет некорректную длину")

    for field in ("revocation_code", "uri", "serial_number", "token_gid", "secret_1"):
        if field in payload and not isinstance(payload[field], (str, int)):
            raise MaFileValidationError(f"Поле {field} имеет некорректный тип")

    if "server_time" in payload and not isinstance(payload["server_time"], (int, float)):
        raise MaFileValidationError("Поле server_time имеет некорректный тип")
    if "fully_enrolled" in payload and not isinstance(payload["fully_enrolled"], bool):
        raise MaFileValidationError("Поле fully_enrolled имеет некорректный тип")

    return payload

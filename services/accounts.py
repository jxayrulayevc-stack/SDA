"""Business logic for accounts. Framework-agnostic: no aiogram imports here."""

from __future__ import annotations

from dataclasses import dataclass

from core.steam_guard import (
    SteamTimeSync,
    generate_steam_code,
    seconds_until_window_end,
)
from services.mafile import (
    DEFAULT_MAX_UPLOAD_BYTES,
    MaFileValidationError,
    validate_mafile,
)
from storage.accounts import AccountRepository
from storage.crypto import Encryptor


class AccountError(Exception):
    """Base class for expected, admin-facing errors."""


class DuplicateAccount(AccountError):
    def __init__(self, login: str) -> None:
        super().__init__(f"Аккаунт {login} уже существует")
        self.login = login


class UnknownAccount(AccountError):
    def __init__(self, login: str) -> None:
        super().__init__(f"Аккаунт {login} не найден")
        self.login = login


@dataclass(frozen=True)
class AddResult:
    login: str
    replaced: bool = False


@dataclass(frozen=True)
class CodeResult:
    login: str
    code: str
    valid_for: int


class AccountService:
    def __init__(
        self,
        repository: AccountRepository,
        encryptor: Encryptor,
        time_sync: SteamTimeSync,
        *,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    ) -> None:
        self._repository = repository
        self._encryptor = encryptor
        self._time_sync = time_sync
        self._max_upload_bytes = max_upload_bytes

    async def list_accounts(self) -> list[str]:
        return await self._repository.list_logins()

    async def add_account(
        self,
        raw: bytes,
        filename: str,
        *,
        replace: bool = False,
    ) -> AddResult:
        payload = validate_mafile(raw, filename, self._max_upload_bytes)
        login = payload["account_name"]
        existing = await self._repository.get(login)
        if existing is not None and not replace:
            raise DuplicateAccount(login)

        encrypted = self._encryptor.encrypt(payload)
        await self._repository.upsert(login, encrypted)
        return AddResult(login=login, replaced=replace and existing is not None)

    async def delete_account(self, login: str) -> bool:
        return await self._repository.delete(login)

    async def get_code(self, login: str) -> CodeResult:
        stored = await self._repository.get(login)
        if stored is None:
            raise UnknownAccount(login)
        payload = self._encryptor.decrypt(stored.encrypted_data)
        secret = payload["shared_secret"]
        now = self._time_sync.now()
        return CodeResult(
            login=stored.login,
            code=generate_steam_code(secret, now),
            valid_for=seconds_until_window_end(now),
        )


__all__ = [
    "AccountError",
    "AccountService",
    "AddResult",
    "CodeResult",
    "DuplicateAccount",
    "MaFileValidationError",
    "UnknownAccount",
]

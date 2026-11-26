"""Fake data only. No real tokens, IDs, keys or maFiles live in the repository."""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from core.steam_guard import SteamTimeSync
from services.accounts import AccountService
from storage.accounts import AccountRepository
from storage.crypto import Encryptor
from storage.database import Database


@pytest.fixture
def encryption_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
def encryptor(encryption_key: str) -> Encryptor:
    return Encryptor(encryption_key)


@pytest.fixture
def fake_shared_secret() -> str:
    return base64.b64encode(bytes(range(32))).decode("ascii")


@pytest.fixture
def fake_mafile(fake_shared_secret: str) -> dict:
    return {
        "shared_secret": fake_shared_secret,
        "identity_secret": base64.b64encode(bytes(range(32, 64))).decode("ascii"),
        "account_name": "fake_login_one",
        "revocation_code": "FAKE-CODE",
        "server_time": 1700000000,
        "status": 1,
        "fully_enrolled": True,
    }


@pytest.fixture
def mafile_bytes(fake_mafile: dict) -> bytes:
    return json.dumps(fake_mafile).encode("utf-8")


@pytest.fixture
def fixed_time_sync() -> SteamTimeSync:
    async def fixed_time() -> int:
        return 1700000000

    return SteamTimeSync(fetcher=fixed_time)


@pytest.fixture
def database_path(tmp_path) -> Path:
    return tmp_path / "accounts.db"


@pytest.fixture
async def account_service(
    database_path: Path,
    encryptor: Encryptor,
    fixed_time_sync: SteamTimeSync,
) -> AsyncIterator[AccountService]:
    database = Database(database_path)
    await database.initialize()
    await fixed_time_sync.sync_once()
    service = AccountService(
        AccountRepository(database),
        encryptor,
        fixed_time_sync,
    )
    yield service

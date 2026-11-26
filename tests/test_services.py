import json

import pytest

from services.accounts import DuplicateAccount, UnknownAccount
from storage.crypto import Encryptor, Fernet


@pytest.mark.asyncio
async def test_add_list_code_replace_delete(
    account_service,
    mafile_bytes: bytes,
    fake_mafile: dict,
) -> None:
    result = await account_service.add_account(mafile_bytes, "fake.maFile")
    assert result.login == fake_mafile["account_name"]
    assert result.replaced is False
    assert await account_service.list_accounts() == [fake_mafile["account_name"]]

    code = await account_service.get_code(fake_mafile["account_name"])
    assert code.code == "V4HWC"
    assert 1 <= code.valid_for <= 30

    with pytest.raises(DuplicateAccount):
        await account_service.add_account(mafile_bytes, "fake.maFile")

    updated = dict(fake_mafile, server_time=1_700_000_100)
    raw = json.dumps(updated).encode()
    replaced = await account_service.add_account(raw, "fake.maFile", replace=True)
    assert replaced.replaced is True

    assert await account_service.delete_account(fake_mafile["account_name"]) is True
    assert await account_service.list_accounts() == []
    with pytest.raises(UnknownAccount):
        await account_service.get_code(fake_mafile["account_name"])


@pytest.mark.asyncio
async def test_encrypted_at_rest(account_service, database_path, mafile_bytes: bytes) -> None:
    await account_service.add_account(mafile_bytes, "fake.maFile")
    raw = database_path.read_bytes()
    assert b"shared_secret" not in raw
    assert b"V4HWC" not in raw


@pytest.mark.asyncio
async def test_wrong_key_cannot_read(account_service, mafile_bytes: bytes) -> None:
    await account_service.add_account(mafile_bytes, "fake.maFile")
    other = Encryptor(Fernet.generate_key().decode())
    with pytest.raises(Exception):
        other.decrypt(
            (await account_service._repository.get("fake_login_one")).encrypted_data
        )

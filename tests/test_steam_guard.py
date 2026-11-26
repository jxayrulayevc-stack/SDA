import time

import pytest

from core.steam_guard import (
    STEAM_ALPHABET,
    InvalidSharedSecretError,
    SteamTimeSync,
    generate_steam_code,
    seconds_until_window_end,
)


def test_known_vector(fake_shared_secret: str) -> None:
    # Fixed fake secret bytes 0..31, timestamp 1700000000.
    assert generate_steam_code(fake_shared_secret, 1700000000) == "V4HWC"
    assert generate_steam_code(fake_shared_secret, 1700000030) == "CFHJJ"


def test_code_shape_and_stability(fake_shared_secret: str) -> None:
    code = generate_steam_code(fake_shared_secret, 1700000010)
    assert len(code) == 5
    assert set(code) <= set(STEAM_ALPHABET)
    assert code == generate_steam_code(fake_shared_secret, 1700000030)
    assert code != generate_steam_code(fake_shared_secret, 1700000040)


def test_invalid_secret() -> None:
    with pytest.raises(InvalidSharedSecretError):
        generate_steam_code("not-base64!!", 1700000000)


def test_remaining_seconds() -> None:
    assert seconds_until_window_end(1700000010.0) == 30
    assert seconds_until_window_end(1700000020.0) == 20
    assert seconds_until_window_end(1700000039.9) == 1


@pytest.mark.asyncio
async def test_time_sync_uses_server_time() -> None:
    async def fetch() -> int:
        return 1_700_000_000

    sync = SteamTimeSync(fetcher=fetch)
    assert await sync.sync_once() is True
    assert sync.now() == pytest.approx(1_700_000_000, abs=2)


@pytest.mark.asyncio
async def test_time_sync_falls_back_to_system_time() -> None:
    async def broken_fetch() -> int:
        raise OSError("network unavailable")

    sync = SteamTimeSync(fetcher=broken_fetch)
    before = time.time()
    assert await sync.sync_once() is False
    assert before <= sync.now() <= time.time() + 1

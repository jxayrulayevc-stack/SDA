"""Steam Guard code generation and Steam time synchronisation.

No third-party Steam libraries are used: this is the standard two-factor
algorithm (HMAC-SHA1 over a 30-second counter with Steam's custom alphabet).
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import logging
import math
import struct
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

STEAM_ALPHABET = "23456789BCDFGHJKMNPQRTVWXY"
WINDOW_SECONDS = 30
DEFAULT_TIME_URL = "https://api.steampowered.com/ITwoFactorService/QueryTime/v1/"


class InvalidSharedSecretError(ValueError):
    """Raised when shared_secret is not valid base64 or is empty."""


def decode_shared_secret(secret: str) -> bytes:
    try:
        decoded = base64.b64decode(secret, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidSharedSecretError("shared_secret is not valid base64") from exc
    if not decoded:
        raise InvalidSharedSecretError("shared_secret is empty")
    return decoded


def generate_steam_code(shared_secret: str | bytes, timestamp: float) -> str:
    """Generate a 5-character Steam Guard code for the given Unix timestamp."""
    secret = decode_shared_secret(shared_secret) if isinstance(shared_secret, str) else shared_secret
    if not secret:
        raise InvalidSharedSecretError("shared_secret is empty")

    counter = int(timestamp // WINDOW_SECONDS)
    message = struct.pack(">Q", counter)
    digest = hmac.new(secret, message, hashlib.sha1).digest()
    offset = digest[19] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF

    chars: list[str] = []
    base = len(STEAM_ALPHABET)
    for _ in range(5):
        chars.append(STEAM_ALPHABET[value % base])
        value //= base
    return "".join(chars)


def seconds_until_window_end(timestamp: float) -> int:
    """Seconds left in the current 30-second Steam Guard window (1..30)."""
    return max(1, math.ceil(WINDOW_SECONDS - (timestamp % WINDOW_SECONDS)))


class SteamTimeSync:
    """Keeps an offset between local clock and Steam's QueryTime server time.

    Falls back to the system clock if Steam is unreachable. ``fetcher`` is an
    injectable coroutine returning server time; used by tests and useful for
    alternative transports. No secret material is ever passed to it.
    """

    def __init__(
        self,
        url: str = DEFAULT_TIME_URL,
        *,
        interval: int = 3600,
        fetcher: Callable[[], Awaitable[int]] | None = None,
    ) -> None:
        self.url = url
        self.interval = interval
        self._fetcher = fetcher
        self._offset = 0.0
        self._task: asyncio.Task[None] | None = None

    async def _fetch_server_time(self) -> int:
        # Imported lazily so unit tests of the algorithm need no HTTP stack.
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response.raise_for_status()
                payload: dict[str, Any] = await response.json(content_type=None)
        server_time = int(payload["response"]["server_time"])
        if server_time <= 0:
            raise ValueError("Steam returned invalid server_time")
        return server_time

    async def sync_once(self) -> bool:
        """Refresh the offset. Returns True on success, False on fallback."""
        try:
            fetcher = self._fetcher or self._fetch_server_time
            server_time = await fetcher()
            self._offset = float(server_time) - time.time()
            return True
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - Steam time is best-effort
            self._offset = 0.0
            logger.warning("Steam time sync failed (%s); using system time", type(exc).__name__)
            return False

    async def start(self) -> None:
        await self.sync_once()
        self._task = asyncio.create_task(self._sync_loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _sync_loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            await self.sync_once()

    def now(self) -> float:
        return time.time() + self._offset

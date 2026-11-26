"""In-memory rate limit specifically for code requests."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

Handler = Callable[[Any, dict[str, Any]], Awaitable[Any]]
CODE_CALLBACK_PREFIX = "sg:code:"


class CodeRateLimitMiddleware:
    def __init__(self, max_calls: int = 10, window_seconds: int = 60) -> None:
        self._max_calls = max(1, max_calls)
        self._window = max(1, window_seconds)
        self._calls: dict[int, deque[float]] = defaultdict(deque)

    def _is_code_request(self, event: Any) -> bool:
        # Duck typing keeps this testable without constructing aiogram objects.
        text = getattr(event, "text", None)
        if isinstance(text, str):
            text = text.strip()
            if not text:  # documents and media have no text
                return False
            return text.split(maxsplit=1)[0].split("@")[0] == "/code"
        data = getattr(event, "data", None)
        if isinstance(data, str):
            return data.startswith(CODE_CALLBACK_PREFIX)
        return False

    async def __call__(self, handler: Handler, event: Any, data: dict[str, Any]) -> Any:
        if not self._is_code_request(event):
            return await handler(event, data)

        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        calls = self._calls[user_id]
        while calls and now - calls[0] >= self._window:
            calls.popleft()
        if len(calls) >= self._max_calls:
            logger.warning("Code request rate limit reached")
            await event.answer("Слишком много запросов кода. Подождите немного.")
            return None
        calls.append(now)
        return await handler(event, data)

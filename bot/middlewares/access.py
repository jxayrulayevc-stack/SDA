"""Hard access control: non-admins are silently ignored, including callbacks."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

Handler = Callable[[Any, dict[str, Any]], Awaitable[Any]]


class AdminOnlyMiddleware:
    def __init__(self, admin_ids: frozenset[int] | set[int]) -> None:
        self._admin_ids = frozenset(admin_ids)

    async def __call__(self, handler: Handler, event: Any, data: dict[str, Any]) -> Any:
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", None)
        if user_id not in self._admin_ids:
            logger.warning("Access denied: update from non-admin ignored")
            return None
        return await handler(event, data)

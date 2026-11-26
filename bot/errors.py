"""Global error handler: logs the exception type, never secret values."""

from __future__ import annotations

import logging

from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)


async def on_error(event: ErrorEvent, exception: Exception) -> None:
    logger.exception("Unhandled error while processing update", exc_info=exception)
    update = event.update
    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None)
    if chat_id is None:
        callback = getattr(update, "callback_query", None)
        message = getattr(callback, "message", None)
        chat_id = getattr(getattr(message, "chat", None), "id", None)
    if chat_id is not None:
        try:
            await event.bot.send_message(
                chat_id,
                "Произошла ошибка. Попробуйте ещё раз; если повторится — проверьте журнал сервиса.",
            )
        except Exception:  # noqa: BLE001 - error handler must not raise
            logger.warning("Could not send error notification to admin")

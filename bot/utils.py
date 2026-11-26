"""Presentation helpers. Safe for logs: only logins and action names."""

from __future__ import annotations

import asyncio
import html
import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from bot.keyboards import code_keyboard
from services.accounts import AccountService, CodeResult, UnknownAccount

logger = logging.getLogger(__name__)


def accounts_list_text(logins: list[str]) -> str:
    if not logins:
        return (
            "Аккаунтов пока нет. Нажмите «➕ Добавить» или просто отправьте "
            "файл .maFile / .json documents-сообщением."
        )
    return f"Аккаунтов: {len(logins)}. Выберите логин:"


def format_code(result: CodeResult) -> str:
    login = html.escape(result.login)
    return (
        f"🔐 Steam Guard для <code>{login}</code>:\n"
        f"<code>{result.code}</code>\n"
        f"Действует ещё {result.valid_for} сек."
    )


async def safe_edit_text(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Edit a message, ignoring Telegram's 'message is not modified' error."""
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramAPIError:
        logger.warning("Could not delete message %s in chat %s", message_id, chat_id)


class MessageJanitor:
    """Deletes code messages after CODE_TTL_SECONDS and cancels old timers."""

    def __init__(self, bot: Bot, ttl_seconds: int) -> None:
        self._bot = bot
        self._ttl = ttl_seconds
        self._tasks: dict[tuple[int, int], asyncio.Task[None]] = {}

    def schedule(self, chat_id: int, message_id: int) -> None:
        key = (chat_id, message_id)
        previous = self._tasks.get(key)
        if previous is not None:
            previous.cancel()
        self._tasks[key] = asyncio.create_task(self._delete_after(key))

    async def _delete_after(self, key: tuple[int, int]) -> None:
        try:
            await asyncio.sleep(self._ttl)
            await safe_delete(self._bot, *key)
        except asyncio.CancelledError:
            pass
        finally:
            if self._tasks.get(key) is asyncio.current_task():
                self._tasks.pop(key, None)

    async def close(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()
        for task in list(self._tasks.values()):
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()


async def send_code_message(
    bot: Bot,
    chat_id: int,
    login: str,
    accounts: AccountService,
    janitor: MessageJanitor,
) -> Message:
    """Send (or refresh) a code message; never exposes secrets in the reply."""
    try:
        result = await accounts.get_code(login)
    except UnknownAccount:
        return await bot.send_message(chat_id, f"Аккаунт {html.escape(login)} не найден")

    message = await bot.send_message(
        chat_id,
        format_code(result),
        reply_markup=code_keyboard(login),
    )
    janitor.schedule(chat_id, message.message_id)
    logger.info("Code issued for account %s", login)
    return message


async def edit_code_message(
    bot: Bot,
    message: Message,
    login: str,
    accounts: AccountService,
    janitor: MessageJanitor,
) -> None:
    try:
        result = await accounts.get_code(login)
    except UnknownAccount:
        await safe_edit_text(
            bot,
            message.chat.id,
            message.message_id,
            f"Аккаунт {html.escape(login)} не найден",
        )
        return
    await safe_edit_text(
        bot,
        message.chat.id,
        message.message_id,
        format_code(result),
        reply_markup=code_keyboard(login),
    )
    janitor.schedule(message.chat.id, message.message_id)
    logger.info("Code refreshed for account %s", login)


def state_value(data: dict[str, Any], name: str, default: Any = None) -> Any:
    return data.get(name, default)

"""Callback handlers for codes, refresh, replace and delete confirmation."""

from __future__ import annotations

import base64
import html
import logging

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards import (
    AccountCallback,
    accounts_keyboard,
    delete_confirm_keyboard,
    login_by_key,
)
from bot.states import DeleteStates
from bot.utils import (
    MessageJanitor,
    accounts_list_text,
    edit_code_message,
    safe_delete,
    safe_edit_text,
    send_code_message,
)
from services.accounts import AccountService

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(AccountCallback.filter())
async def handle_callback(
    callback: CallbackQuery,
    callback_data: AccountCallback,
    bot: Bot,
    accounts: AccountService,
    state: FSMContext,
    janitor: MessageJanitor,
) -> None:
    action = callback_data.action
    logins = await accounts.list_accounts()
    login = login_by_key(logins, callback_data.key)

    if action in {"code", "refresh"}:
        if login is None:
            await callback.answer("Аккаунт не найден", show_alert=True)
            return
        await callback.answer()
        if callback.message is None:
            return
        if action == "code":
            await safe_delete(bot, callback.message.chat.id, callback.message.message_id)
            await send_code_message(bot, callback.message.chat.id, login, accounts, janitor)
        else:
            await edit_code_message(bot, callback.message, login, accounts, janitor)
        return

    if action == "delete":
        if login is None:
            await callback.answer("Аккаунт не найден", show_alert=True)
            return
        await state.set_state(DeleteStates.confirm)
        await state.update_data(pending_login=login)
        await callback.answer()
        if callback.message is not None:
            await safe_edit_text(
                f"Удалить аккаунт <code>{html.escape(login)}</code>?",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=delete_confirm_keyboard(),
            )
        return

    if action == "confirm_delete":
        current = await state.get_data()
        target = current.get("pending_login")
        await state.clear()
        if not isinstance(target, str):
            await callback.answer("Аккаунт не выбран", show_alert=True)
            return
        removed = await accounts.delete_account(target)
        await callback.answer()
        if callback.message is not None:
            text = (
                f"Аккаунт {html.escape(target)} удалён"
                if removed
                else f"Аккаунт {html.escape(target)} уже удалён"
            )
            await safe_edit_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        logger.info("Account deleted: %s", target)
        return

    if action == "replace":
        current = await state.get_data()
        raw_b64 = current.get("pending_mafile")
        target = current.get("pending_login")
        await state.clear()
        if not isinstance(raw_b64, str) or not isinstance(target, str):
            await callback.answer("Данные файла устарели, отправьте файл снова", show_alert=True)
            return
        raw = base64.b64decode(raw_b64)
        try:
            result = await accounts.add_account(raw, f"{target}.maFile", replace=True)
        except Exception as exc:  # noqa: BLE001 - report a safe message to admin
            logger.error("Replacement failed (%s)", type(exc).__name__)
            await callback.answer("Не удалось заменить аккаунт", show_alert=True)
            return
        await callback.answer()
        if callback.message is not None:
            await safe_edit_text(
                f"Аккаунт {html.escape(result.login)} заменён",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
            )
        logger.info("Account replaced: %s", result.login)
        return

    if action == "add_help":
        await callback.answer()
        if callback.message is not None:
            await safe_edit_text(
                "Отправьте файл .maFile или .json documents-сообщением. "
                "Бот проверит его, зашифрует и удалит сообщение с файлом.",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
            )
        return

    if action in {"refresh_list", "back_to_list"}:
        await callback.answer()
        if callback.message is not None:
            await safe_edit_text(
                accounts_list_text(logins),
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=accounts_keyboard(logins),
            )
        return

    if action == "close":
        await callback.answer()
        if callback.message is not None:
            await safe_delete(bot, callback.message.chat.id, callback.message.message_id)
        return

    if action == "cancel":
        await state.clear()
        await callback.answer()
        if callback.message is not None:
            await safe_edit_text(
                "Отменено",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
            )
        return

    await callback.answer("Неизвестное действие", show_alert=True)

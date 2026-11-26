"""Inline keyboards. Callback payloads contain a short login hash, never secrets."""

from __future__ import annotations

import hashlib

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData


class AccountCallback(CallbackData, prefix="sg"):
    action: str
    key: str


def account_key(login: str) -> str:
    return hashlib.sha256(login.casefold().encode("utf-8")).hexdigest()[:10]


def login_by_key(logins: list[str], key: str) -> str | None:
    for login in logins:
        if account_key(login) == key:
            return login
    return None


def accounts_keyboard(logins: list[str], action: str = "code") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for login in logins:
        builder.button(
            text=login,
            callback_data=AccountCallback(action=action, key=account_key(login)),
        )
    builder.adjust(2)
    return builder.as_markup()


def code_keyboard(login: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔄 Обновить",
        callback_data=AccountCallback(action="refresh", key=account_key(login)),
    )
    return builder.as_markup()


def replace_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Заменить", callback_data=AccountCallback(action="replace", key="1"))
    builder.button(text="❌ Отмена", callback_data=AccountCallback(action="cancel", key="1"))
    return builder.as_markup()


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=AccountCallback(action="confirm_delete", key="1"))
    builder.button(text="❌ Отмена", callback_data=AccountCallback(action="cancel", key="1"))
    return builder.as_markup()

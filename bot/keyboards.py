"""Inline and reply keyboards. Callback payloads contain a short login hash, never secrets."""

from __future__ import annotations

import hashlib

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
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


def main_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom menu so the admin does not have to type commands."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Аккаунты")
    builder.button(text="🗑 Удалить")
    builder.button(text="ℹ️ Помощь")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def accounts_keyboard(logins: list[str], action: str = "code") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for login in logins:
        builder.button(
            text=login,
            callback_data=AccountCallback(action=action, key=account_key(login)),
        )
    builder.button(text="➕ Добавить", callback_data=AccountCallback(action="add_help", key="1"))
    builder.button(
        text="🔄 Обновить список",
        callback_data=AccountCallback(action="refresh_list", key="1"),
    )
    builder.button(text="❌ Закрыть", callback_data=AccountCallback(action="close", key="1"))
    builder.adjust(2)
    return builder.as_markup()


def code_keyboard(login: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔄 Обновить",
        callback_data=AccountCallback(action="refresh", key=account_key(login)),
    )
    builder.button(
        text="📋 К списку",
        callback_data=AccountCallback(action="back_to_list", key="1"),
    )
    builder.adjust(2)
    return builder.as_markup()


def replace_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Заменить",
        callback_data=AccountCallback(action="replace", key="1"),
    )
    builder.button(text="❌ Отмена", callback_data=AccountCallback(action="cancel", key="1"))
    return builder.as_markup()


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да, удалить",
        callback_data=AccountCallback(action="confirm_delete", key="1"),
    )
    builder.button(text="❌ Отмена", callback_data=AccountCallback(action="cancel", key="1"))
    return builder.as_markup()

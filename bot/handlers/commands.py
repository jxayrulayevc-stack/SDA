"""Command handlers: thin layer around AccountService."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import accounts_keyboard
from bot.states import DeleteStates
from bot.utils import MessageJanitor, send_code_message
from services.accounts import AccountService

router = Router()

HELP_TEXT = (
    "Steam Guard бот.\n\n"
    "/accounts — список аккаунтов (нажмите на логин, чтобы получить код)\n"
    "/code <логин> — код нужного аккаунта\n"
    "/delete — удалить аккаунт\n"
    "/help — эта справка\n\n"
    "Чтобы добавить аккаунт, отправьте файл .maFile или .json "
    "(файл будет удалён из чата)."
)


@router.message(Command("start", "help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("accounts"))
async def accounts_command(message: Message, accounts: AccountService) -> None:
    logins = await accounts.list_accounts()
    if not logins:
        await message.answer("Аккаунтов пока нет. Отправьте файл .maFile или .json.")
        return
    await message.answer(
        f"Аккаунтов: {len(logins)}. Выберите логин:",
        reply_markup=accounts_keyboard(logins),
    )


@router.message(Command("code"))
async def code_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    accounts: AccountService,
    janitor: MessageJanitor,
) -> None:
    login = (command.args or "").strip()
    if not login:
        await message.answer("Использование: /code <логин>. Список: /accounts")
        return
    await send_code_message(bot, message.chat.id, login, accounts, janitor)


@router.message(Command("delete"))
async def delete_command(
    message: Message,
    accounts: AccountService,
    state: FSMContext,
) -> None:
    logins = await accounts.list_accounts()
    if not logins:
        await message.answer("Удалять нечего: аккаунтов нет.")
        return
    await state.set_state(DeleteStates.confirm)
    await state.update_data(pending_login=None)
    await message.answer(
        "Выберите аккаунт для удаления:",
        reply_markup=accounts_keyboard(logins, action="delete"),
    )

"""maFile upload handler."""

from __future__ import annotations

import base64
import logging
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import main_keyboard, replace_keyboard
from bot.states import AddStates
from bot.utils import safe_delete
from services.accounts import AccountService, DuplicateAccount
from services.mafile import ALLOWED_SUFFIXES, MaFileValidationError

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.document)
async def upload_mafile(
    message: Message,
    bot: Bot,
    accounts: AccountService,
    state: FSMContext,
    max_upload_bytes: int = 100 * 1024,
) -> None:
    document = message.document
    filename = document.file_name or ""
    declared_size = document.file_size or 0

    if not filename.lower().endswith(ALLOWED_SUFFIXES) or declared_size > max_upload_bytes:
        await safe_delete(bot, message.chat.id, message.message_id)
        await message.answer("Нужен файл .maFile или .json размером до 100 КБ.")
        return

    buffer = BytesIO()
    await bot.download(document, destination=buffer)
    raw = buffer.getvalue()

    chat_id = message.chat.id
    message_id = message.message_id

    async def drop_file_message() -> None:
        # Never leave a maFile in the chat, even when validation fails.
        await safe_delete(bot, chat_id, message_id)

    if len(raw) > max_upload_bytes:
        await drop_file_message()
        await message.answer("Файл слишком большой (максимум 100 КБ).")
        return

    try:
        result = await accounts.add_account(raw, filename)
    except DuplicateAccount as exc:
        await drop_file_message()
        await state.set_state(AddStates.confirm_replace)
        await state.update_data(
            pending_mafile=base64.b64encode(raw).decode("ascii"),
            pending_login=exc.login,
        )
        await message.answer(
            f"Аккаунт {exc.login} уже есть. Заменить?",
            reply_markup=replace_keyboard(),
        )
        return
    except MaFileValidationError as exc:
        await drop_file_message()
        await message.answer(f"Не удалось добавить аккаунт: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - never expose exception internals
        await drop_file_message()
        logger.error("Account import failed (%s)", type(exc).__name__)
        await message.answer("Не удалось добавить аккаунт. Проверьте файл и журнал сервиса.")
        return

    # Saved successfully: only now delete the message containing the file.
    await drop_file_message()
    await message.answer(
        f"Аккаунт {result.login} добавлен",
        reply_markup=main_keyboard(),
    )
    logger.info("Account added: %s", result.login)

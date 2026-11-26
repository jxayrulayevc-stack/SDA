"""Entrypoint: python -m bot.main"""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.errors import on_error
from bot.handlers import callbacks, commands, documents
from bot.middlewares.access import AdminOnlyMiddleware
from bot.middlewares.rate_limit import CodeRateLimitMiddleware
from bot.utils import MessageJanitor
from config import load_settings
from core.steam_guard import SteamTimeSync
from services.accounts import AccountService
from storage.accounts import AccountRepository
from storage.crypto import Encryptor
from storage.database import Database
from storage.permissions import warn_if_insecure

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("steam_guard")
os.umask(0o077)


async def main() -> None:
    settings = load_settings()

    warn_if_insecure(settings.env_file_path, ".env")
    database = Database(settings.data_dir / "accounts.db")
    await database.initialize()
    warn_if_insecure(database.path, "Database")

    encryptor = Encryptor(settings.encryption_key_value)
    time_sync = SteamTimeSync(
        settings.steam_time_url,
        interval=settings.steam_time_sync_interval,
    )
    repository = AccountRepository(database)
    accounts = AccountService(
        repository,
        encryptor,
        time_sync,
        max_upload_bytes=settings.max_upload_bytes,
    )

    bot = Bot(
        token=settings.bot_token_value,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    janitor = MessageJanitor(bot, settings.code_ttl_seconds)

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["accounts"] = accounts
    dispatcher["janitor"] = janitor
    dispatcher["max_upload_bytes"] = settings.max_upload_bytes

    access = AdminOnlyMiddleware(settings.admin_id_set)
    rate_limit = CodeRateLimitMiddleware(
        settings.code_rate_limit,
        settings.rate_limit_window,
    )
    for observer in (
        dispatcher.message,
        dispatcher.callback_query,
        dispatcher.edited_message,
        dispatcher.inline_query,
    ):
        # Registered last = outermost, so access control runs before anything
        # that could reply to an unauthorised user.
        observer.outer_middleware(rate_limit)
        observer.outer_middleware(access)

    dispatcher.errors.register(on_error)
    dispatcher.include_router(documents.router)
    dispatcher.include_router(commands.router)
    dispatcher.include_router(callbacks.router)

    async def on_startup() -> None:
        await time_sync.start()
        logger.info("Bot started; admins configured: %d", len(settings.admin_id_set))

    async def on_shutdown() -> None:
        await janitor.close()
        await time_sync.stop()
        logger.info("Bot stopped")

    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)

    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=["message", "edited_message", "callback_query", "inline_query"],
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

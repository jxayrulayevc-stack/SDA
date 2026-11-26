from types import SimpleNamespace

import pytest

from bot.errors import on_error
from bot.handlers.commands import HELP_TEXT


def test_help_text_is_html_safe() -> None:
    assert "&lt;логин&gt;" in HELP_TEXT
    assert "<логин>" not in HELP_TEXT


@pytest.mark.asyncio
async def test_error_handler_accepts_error_event() -> None:
    event = SimpleNamespace(
        exception=RuntimeError("boom"),
        update=SimpleNamespace(effective_chat=None, callback_query=None),
        bot=SimpleNamespace(send_message=None),
    )
    # aiogram calls handlers with the ErrorEvent as the single positional arg.
    await on_error(event)

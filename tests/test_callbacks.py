from types import SimpleNamespace

import pytest

from bot.handlers.callbacks import handle_callback
from bot.keyboards import AccountCallback, account_key


class FakeBot:
    def __init__(self) -> None:
        self.edits: list[tuple] = []

    async def edit_message_text(self, *args, **kwargs):
        self.edits.append((args, kwargs))


class FakeAccounts:
    async def list_accounts(self) -> list[str]:
        return ["fake_login_one"]

    async def delete_account(self, login: str) -> bool:
        return True


class FakeState:
    def __init__(self, data: dict | None = None) -> None:
        self._data = data or {}

    async def set_state(self, state) -> None:
        pass

    async def update_data(self, **kwargs) -> None:
        self._data.update(kwargs)

    async def get_data(self) -> dict:
        return dict(self._data)

    async def clear(self) -> None:
        self._data.clear()


def _callback() -> SimpleNamespace:
    async def answer(*args, **kwargs):
        return None

    message = SimpleNamespace(chat=SimpleNamespace(id=1), message_id=2)
    return SimpleNamespace(answer=answer, message=message)


@pytest.mark.asyncio
async def test_delete_callback_edits_confirmation() -> None:
    bot = FakeBot()
    data = AccountCallback(action="delete", key=account_key("fake_login_one"))
    await handle_callback(_callback(), data, bot, FakeAccounts(), FakeState(), object())
    assert bot.edits


@pytest.mark.asyncio
async def test_confirm_delete_callback_edits_result() -> None:
    bot = FakeBot()
    data = AccountCallback(action="confirm_delete", key="1")
    state = FakeState({"pending_login": "fake_login_one"})
    await handle_callback(_callback(), data, bot, FakeAccounts(), state, object())
    assert bot.edits
    assert "удалён" in bot.edits[0][0][0]

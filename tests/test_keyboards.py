from bot.keyboards import (
    AccountCallback,
    accounts_keyboard,
    code_keyboard,
    main_keyboard,
)


def _texts(keyboard) -> list[str]:
    return [button.text for row in keyboard.inline_keyboard for button in row]


def test_main_keyboard_has_actions() -> None:
    texts = [button.text for row in main_keyboard().keyboard for button in row]
    assert texts == ["📋 Аккаунты", "🗑 Удалить", "ℹ️ Помощь"]


def test_accounts_keyboard_has_menu_actions() -> None:
    texts = _texts(accounts_keyboard(["fake_login_one"]))
    assert "fake_login_one" in texts
    assert "➕ Добавить" in texts
    assert "🔄 Обновить список" in texts
    assert "❌ Закрыть" in texts


def test_code_keyboard_has_navigation() -> None:
    texts = _texts(code_keyboard("fake_login_one"))
    assert "🔄 Обновить" in texts
    assert "📋 К списку" in texts


def test_callback_data_is_short() -> None:
    data = AccountCallback(action="code", key="a" * 10).pack()
    assert len(data) <= 64

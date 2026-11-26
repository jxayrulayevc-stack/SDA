from types import SimpleNamespace

import pytest

from bot.middlewares.access import AdminOnlyMiddleware


def fake_event(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(from_user=SimpleNamespace(id=user_id))


@pytest.mark.asyncio
async def test_admin_is_allowed() -> None:
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "handled"

    middleware = AdminOnlyMiddleware(frozenset({1001}))
    event = fake_event(1001)
    assert await middleware(handler, event, {}) == "handled"
    assert calls == [event]


@pytest.mark.asyncio
async def test_non_admin_is_ignored() -> None:
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "handled"

    middleware = AdminOnlyMiddleware(frozenset({1001}))
    assert await middleware(handler, fake_event(2002), {}) is None
    assert calls == []


@pytest.mark.asyncio
async def test_callback_from_non_admin_is_ignored() -> None:
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "handled"

    middleware = AdminOnlyMiddleware(frozenset({1001}))
    callback = SimpleNamespace(from_user=SimpleNamespace(id=2002), data="sg:code:abc")
    assert await middleware(handler, callback, {}) is None
    assert calls == []


@pytest.mark.asyncio
async def test_event_without_user_is_ignored() -> None:
    async def handler(event, data):
        return "handled"

    middleware = AdminOnlyMiddleware(frozenset({1001}))
    assert await middleware(handler, SimpleNamespace(), {}) is None

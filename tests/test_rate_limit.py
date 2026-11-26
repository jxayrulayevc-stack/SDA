from types import SimpleNamespace

import pytest

from bot.middlewares.rate_limit import CodeRateLimitMiddleware


def make_message(text: str | None) -> SimpleNamespace:
    async def answer(*args, **kwargs):
        return None

    return SimpleNamespace(text=text, from_user=SimpleNamespace(id=1001), answer=answer)


@pytest.mark.asyncio
async def test_document_without_text_is_not_rate_limited() -> None:
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "handled"

    middleware = CodeRateLimitMiddleware(max_calls=1, window_seconds=60)
    event = make_message(None)
    assert await middleware(handler, event, {}) == "handled"
    assert calls == [event]


@pytest.mark.asyncio
async def test_empty_text_is_not_rate_limited() -> None:
    async def handler(event, data):
        return "handled"

    middleware = CodeRateLimitMiddleware(max_calls=1, window_seconds=60)
    assert await middleware(handler, make_message("   "), {}) == "handled"


@pytest.mark.asyncio
async def test_code_command_is_rate_limited() -> None:
    answers = []

    async def handler(event, data):
        return "handled"

    middleware = CodeRateLimitMiddleware(max_calls=2, window_seconds=60)
    event = make_message("/code fake_login")

    async def record(text):
        answers.append(text)

    event.answer = record
    assert await middleware(handler, event, {}) == "handled"
    assert await middleware(handler, event, {}) == "handled"
    assert await middleware(handler, event, {}) is None
    assert answers


@pytest.mark.asyncio
async def test_other_commands_are_not_rate_limited() -> None:
    async def handler(event, data):
        return "handled"

    middleware = CodeRateLimitMiddleware(max_calls=1, window_seconds=60)
    for _ in range(5):
        assert await middleware(handler, make_message("/accounts"), {}) == "handled"

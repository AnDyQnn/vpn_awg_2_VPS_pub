# -*- coding: utf-8 -*-
"""Обработчик ошибок бота: «not modified» молча, сеть — строкой, остальное — коротко."""
import asyncio
import contextlib
import io
import sys

sys.path.insert(0, "/app")
import bot as B                                   # noqa: E402
from telegram.error import BadRequest, TimedOut   # noqa: E402


class Q:
    answered = 0

    async def answer(self, *a, **k):
        Q.answered += 1


class Upd:
    callback_query = Q()


class Ctx:
    def __init__(self, err):
        self.error = err


async def run(err):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        await B.on_error(Upd(), Ctx(err))
    return buf.getvalue()


async def main():
    out = await run(BadRequest("Message is not modified: specified new message content"))
    assert out == "" and Q.answered == 1, (out, Q.answered)
    print("not modified — молча, часики на кнопке остановлены: ок")

    out = await run(TimedOut("Timed out"))
    assert out.count("\n") == 1 and "Telegram: сеть" in out, out
    print("таймаут — одной строкой: ок")

    try:
        raise ValueError("что-то сломалось")
    except ValueError as e:
        out = await run(e)
    assert "Ошибка обработчика: ValueError" in out and "Traceback" in out, out
    print("прочее — коротко с хвостом трейсбека: ок")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())

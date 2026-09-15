# -*- coding: utf-8 -*-
"""Раздача подписок: маленький веб-сервер рядом с ботом.

Зачем вообще сервер. Ссылку `vless://` можно просто прислать в Telegram, и
человек её один раз вставит. Но тогда любое изменение — новый список
исключений, переезд на другой адрес, смена маскировки — снова собирает всех
тридцать человек на перевыпуск. Ровно от этого мы и уходим.

Подписка решает это так: клиент сам раз в несколько часов читает личную
ссылку и обновляет профиль. Поэтому ссылка постоянная, а содержимое по ней
собирается каждый раз заново из базы.

Почему сервер живёт у бота, а не на узле: содержимое подписки зависит от базы
(кто приостановлен, у кого какой срок, кому что выдано). Узел базы не видит и
видеть не должен — иначе пришлось бы синхронизировать две правды.
"""
import asyncio
import base64
import os
import time

from aiohttp import web

from database import db
import xray

# Порт внутри контейнера. Наружу он выставляется в docker-compose — и только
# если владелец решил включить подписки.
SUB_PORT = int(os.getenv("SUB_PORT", "8080"))

# Как часто клиенту предлагается перечитывать ссылку (часы). Двенадцать —
# компромисс: изменения доезжают за полдня, а сервер не дёргают попусту.
UPDATE_INTERVAL_HOURS = 12

# Сколько байт профиля маршрутизации согласны положить в заголовок. Дальше —
# в тело: длинные заголовки режут посредники, и приложение получит обрезанный
# профиль, даже не узнав об этом.
HEADER_LIMIT = 4096

# Чужие запросы на несуществующие токены — это либо опечатка, либо скан.
# Считаем их и сообщаем владельцу не чаще раза в час, чтобы не устроить спам.
_miss_count = 0
_miss_reported = 0.0


async def _userinfo(rec) -> str:
    """Строка для клиента: сколько потрачено и до какого числа действует.

    Приложения показывают это на карточке профиля — человеку не нужно лезть в
    бота, чтобы узнать, когда кончается срок."""
    used_in, used_out = await db.get_traffic_totals(rec["user_uuid"])
    expire = 0
    if rec.get("expires_at"):
        expire = int(rec["expires_at"].timestamp())
    # total=0 значит «без лимита по объёму» — у нас ограничение не по гигабайтам,
    # а по скорости и поведению, поэтому именно ноль, а не выдуманное число.
    return (f"upload={used_in}; download={used_out}; total=0; expire={expire}")


async def handle_sub(request):
    """Отдаёт профиль по личному токену.

    Отказ всегда выглядит одинаково — 404 без пояснений. По ответу нельзя
    отличить «такого токена нет» от «человек приостановлен»: чужому знать
    незачем, а свой всё равно спросит у бота."""
    global _miss_count, _miss_reported
    token = request.match_info.get("token", "")

    rec = await db.get_xray_by_token(token) if token else None
    if not rec or not rec["is_active"]:
        _miss_count += 1
        now = time.time()
        if _miss_count >= 5 and now - _miss_reported > 3600:
            _miss_reported = now
            try:
                await db.log_event("Подписки",
                                   f"Неизвестных обращений к подпискам: {_miss_count}")
            except Exception:
                pass
            _miss_count = 0
        return web.Response(status=404, text="not found")

    # Сплит едет вместе с подпиской. Профиль с тем же именем приложение
    # обновляет, а не добавляет рядом, — поэтому изменившийся список исключений
    # доезжает до всех сам, без перевыпуска и без действий человека.
    routing, in_body = "", []
    try:
        import happ_routing
        routing = await happ_routing.link()
        if len(routing) > HEADER_LIMIT:
            # Заголовок такой длины по дороге могут обрезать, и приложение
            # получит мусор вместо профиля. Тогда — строкой в теле: чужой
            # клиент её просто пропустит.
            in_body = [routing]
            routing = ""
    except Exception as e:
        print(f"Подписка: профиль маршрутизации не собрался: {e}")

    body = await xray.subscription_body(token, extra=in_body)
    if not body:
        return web.Response(status=404, text="not found")

    name = base64.b64encode((rec.get("name") or "VPN").encode()).decode()
    headers = {
        "profile-update-interval": str(UPDATE_INTERVAL_HOURS),
        "profile-title": f"base64:{name}",
        "subscription-userinfo": await _userinfo(rec),
        # Подписка — личная и всегда свежая: кэшировать её нельзя, иначе
        # отзыв доступа не доедет до клиента.
        "Cache-Control": "no-store",
    }
    if routing:
        headers["routing"] = routing
    return web.Response(
        body=body.encode(),
        content_type="text/plain",
        charset="utf-8",
        headers=headers)


async def handle_root(request):
    """Корень молчит. На сервере с открытым портом это важнее вежливости:
    страница-приветствие сразу говорит сканеру, что тут есть что искать."""
    return web.Response(status=404, text="not found")


async def start_server():
    """Поднимает сервер подписок. Вызывается один раз при старте бота."""
    app = web.Application()
    app.router.add_get("/sub/{token}", handle_sub)
    app.router.add_get("/", handle_root)

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", SUB_PORT)
    await site.start()
    print(f"Сервер подписок слушает порт {SUB_PORT}")
    return runner

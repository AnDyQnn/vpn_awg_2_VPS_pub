# -*- coding: utf-8 -*-
"""Сайт-заглушка: то, что увидит посторонний, постучавшийся на наш адрес.

Зачем он нужен. REALITY на каждом рукопожатии берёт сертификат у сайта-маски и
отдаёт его клиенту; тот, кто пришёл без правильного ключа, туда же и
переадресуется. Пока маской служит чужой крупный сайт, мы зависим от него
целиком: перестанет он отдавать пригодный сертификат — вход умрёт, и мы об этом
узнаем от людей. Именно так у нас две недели не работал один из трёх входов.

Свой сайт эту зависимость снимает: сертификат наш, доступность наша, задержка
нулевая — он на этой же машине.

Чем он НЕ занимается. Он ничего не считает, ничего не читает с диска по просьбе
гостя и ничего не помнит. Ответ у него один и тот же, побайтово. Это не
лаконичность ради красоты: страница стоит на пути любого, кто просканирует наш
адрес, и всё, что она умеет делать, — это то, что можно против нас применить.

Почему она маленькая. Совет «сделай её мегабайт на десять, чтобы объём трафика
выглядел правдоподобно» звучит разумно, но делает из нас усилитель: каждый
случайный сканер вынудит узел с одним ядром отдать десять мегабайт, а таких
запросов бывает тысячи в сутки. Правдоподобия это всё равно не даёт — через VPN
за вечер проходят гигабайты, их десятью мегабайтами не объяснить. Поэтому
страница обычного размера, с честными заголовками и кэшированием: повторный
визит не стоит нам ничего.

Слушает только петлю. Наружу её отдаёт Xray и только тем, кто не прошёл
проверку, — сама она из интернета недостижима.
"""
import asyncio
import os
import ssl

from aiohttp import web

# Петля и только петля. Снаружи сюда попадают исключительно через REALITY,
# который сам решает, кого переадресовать.
DECOY_HOST = "127.0.0.1"
DECOY_PORT = int(os.getenv("DECOY_PORT", "8444"))
CERT_DIR = os.getenv("SUB_CERT_DIR", "/volumes/certs")

# Страница. Ровно один экран, без внешних ссылок, без скриптов, без форм.
# Формы тут особенно неуместны: любое поле ввода — это приглашение его
# попробовать, а нам нечего с ним делать.
PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Сервис временно недоступен</title>
<style>
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;
     justify-content:center;background:#f4f5f7;color:#20242b;
     font:16px/1.6 -apple-system,"Segoe UI",Roboto,Arial,sans-serif;padding:24px}
.card{max-width:520px;background:#fff;border:1px solid #e3e6ea;border-radius:14px;
      padding:32px 28px;box-shadow:0 8px 24px rgba(16,24,40,.06)}
h1{font-size:20px;margin:0 0 12px}
p{margin:0 0 12px;color:#4a5261}
.small{font-size:13px;color:#8b93a1;margin:18px 0 0}
</style></head><body>
<main class="card">
<h1>Сервис временно недоступен</h1>
<p>Страница, которую вы запрашивали, сейчас не обслуживается.
Техническое обслуживание обычно занимает несколько часов.</p>
<p>Если вы попали сюда по ссылке, попробуйте зайти позже.</p>
<p class="small">Ошибка 503 · Service Unavailable</p>
</main></body></html>
"""
BODY = PAGE.encode("utf-8")


async def handle(request):
    """Один ответ на всё. Путь, метод и заголовки гостя не разбираются вовсе.

    Разбирать их было бы нечем и незачем: у сайта нет ни страниц, ни файлов, ни
    состояния. Зато каждая попытка разбора — это место, где можно ошибиться, а
    ошибка здесь видна всему интернету.
    """
    return web.Response(
        body=BODY,
        status=503,
        content_type="text/html",
        charset="utf-8",
        headers={
            # Кэш: повторный визит того же сканера не стоит нам ничего.
            "Cache-Control": "public, max-age=3600",
            "Retry-After": "7200",
            # Ни версии, ни имени движка: это бесплатная подсказка тому, кто
            # ищет, чем нас пробовать.
            "Server": "nginx",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        })


def _ssl_context():
    """Тот же сертификат, что у подписки. Нет его — сайта тоже нет."""
    cert = os.path.join(CERT_DIR, "fullchain.pem")
    key = os.path.join(CERT_DIR, "privkey.pem")
    try:
        if os.path.getsize(cert) < 1 or os.path.getsize(key) < 1:
            return None
    except OSError:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # Только 1.3 и 1.2: REALITY показывает гостю сертификат этого сайта, и
    # набор протоколов тоже часть того, как он выглядит.
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        ctx.load_cert_chain(cert, key)
    except Exception as e:
        print("Заглушка: сертификат не загрузился — %s" % e)
        return None
    return ctx


# Поднята ли она сейчас. Вопрос не праздный: пока заглушка не слушает, выбирать
# её маской нельзя — Reality уводит к ней КАЖДОЕ рукопожатие, и вход с
# неподнятой заглушкой не работает вообще ни у кого.
_up = False


def is_up() -> bool:
    return _up


async def start(app=None):
    """Поднимает заглушку, если есть сертификат. Иначе молчит и ждёт.

    Ждать приходится: сертификат выпускается скриптом на хосте и может
    появиться через минуты после старта бота.
    """
    global _up
    runner = None
    while True:
        ctx = _ssl_context()
        if ctx and runner is None:
            try:
                srv = web.Server(handle)
                runner = web.ServerRunner(srv)
                await runner.setup()
                site = web.TCPSite(runner, DECOY_HOST, DECOY_PORT, ssl_context=ctx)
                await site.start()
                _up = True
                print("Заглушка: поднята на %s:%d" % (DECOY_HOST, DECOY_PORT),
                      flush=True)
            except Exception as e:
                print("Заглушка: не поднялась — %s" % e, flush=True)
                runner = None
                _up = False
        elif ctx is None and runner is not None:
            # Сертификат пропал — значит владелец закрыл подписку наружу.
            # Снимаем и заглушку: отдавать её с истёкшим сертификатом хуже, чем
            # не отдавать вовсе, а маска на неё после этого перестанет
            # предлагаться сама.
            try:
                await runner.cleanup()
            except Exception:
                pass
            runner, _up = None, False
            print("Заглушка: сертификата больше нет — снята", flush=True)
        await asyncio.sleep(600)

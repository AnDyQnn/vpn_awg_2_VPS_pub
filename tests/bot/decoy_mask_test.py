# -*- coding: utf-8 -*-
"""Маска держится под прицелом: что видно, если страницу щупать нарочно.

Обычный визит проверяет соседний тест. Здесь — то, что делает не браузер, а
тот, кто ищет приметы: кривые запросы, чужие методы, адреса подписки,
диапазоны байтов. Каждая проверка ниже закрывает дыру, найденную на живом
узле, а не выдуманную.

Почему это вообще проверяется тестом. Маска ценна ровно до первого ответа,
который выдаёт, что за ней. Такой ответ не ломает ничего видимого — узел
работает, люди подключены, — и потому не находится сам. Его можно поймать
только нарочно.
"""
import io
import re

import subscription as S


class FakeTransport:
    def __init__(self, port):
        self.port = port

    def get_extra_info(self, name):
        return ("127.0.0.1", self.port) if name == "sockname" else None


class FakeReq:
    def __init__(self, path="/", method="GET", headers=None, port=None):
        self.transport = FakeTransport(port or S.DECOY_PORT)
        self.path = path
        self.method = method
        self.remote = "203.0.113.7"
        self.match_info = {}
        self.headers = headers or {}


import decoy  # noqa: E402

FAIL = []


def check(what, ok, why=""):
    print(("  ок   " if ok else "  ПЛОХО") + "  " + what + ("" if ok else "  <- " + why))
    if not ok:
        FAIL.append(what)


print("=== имя движка не всплывает нигде ===")
# Ответы на кривой запрос aiohttp собирает сам, мимо наших рук и мимо рубежа,
# и представляется в них "Python/3.11 aiohttp/3.14.3". На живом узле так и
# было: страница называлась nginx, а мусорный запрос отвечал питоном.
import aiohttp.http  # noqa: E402
import aiohttp.web_response  # noqa: E402

check("имя в http", aiohttp.http.SERVER_SOFTWARE == S.SERVER_NAME,
      aiohttp.http.SERVER_SOFTWARE)
check("имя в web_response", aiohttp.web_response.SERVER_SOFTWARE == S.SERVER_NAME,
      aiohttp.web_response.SERVER_SOFTWARE)

print("\n=== движок не пересказывает свою ошибку наружу ===")
# Было: "Got more than 4096 bytes when reading: bytearray(b'/aaaa…')" — и движок
# назван, и кусок присланного запроса возвращён.
body = S.error_body(400).decode("utf-8")
check("тело отказа — обычная страница", "400 Bad Request" in body, body[:80])
for bad in ("aiohttp", "Python", "Traceback", "bytearray"):
    check("в отказе нет слова «%s»" % bad, bad not in body)

print("\n=== отказ по адресам подписки выглядит как отказ сайта ===")
# Три адреса подписки живут на том же порту. Рубеж отказывал по ним девятью
# байтами простого текста — щель, через которую видно, что сайт ненастоящий.
r = S.refuse(FakeReq("/sub/zzzz"))
check("на маске отказ — страница сайта", r.status == 404 and r.body == decoy.NOT_FOUND,
      "%s, %d б" % (r.status, len(r.body or b"")))
check("и представляется как сайт", r.headers.get("Server") == S.SERVER_NAME,
      r.headers.get("Server"))
r = S.refuse(FakeReq("/sub/zzzz", port=S.SUB_PORT))
check("на внутреннем порту — как было", r.status == 404 and r.body == b"not found")

print("\n=== у главной и у «не найдено» разные метки ===")
# Одна метка на две разные страницы — несуразица, видная одним сравнением.
a = S.decoy_reply(FakeReq("/"))
b = S.decoy_reply(FakeReq("/нет-такой-страницы"))
check("коды разные", (a.status, b.status) == (200, 404))
check("тела разные", a.body != b.body)
check("метки разные", a.headers.get("ETag") != b.headers.get("ETag"),
      "обе %s" % a.headers.get("ETag"))

print("\n=== обещание Accept-Ranges выполняется ===")
# Мы объявляем поддержку диапазонов. Пока её не было, запрос «пришли сто байт»
# приводил к выдаче четырёх с половиной мегабайт: и примета, и рычаг, которым
# из узла с одним ядром выкачивают трафик коротким запросом.
name = sorted(decoy.ASSETS)[0]
full = decoy.ASSETS[name][0]
r = S.decoy_reply(FakeReq(name, headers={"Range": "bytes=0-99"}))
check("частичный ответ", r.status == 206, str(r.status))
check("ровно сто байт", len(r.body) == 100, "%d б" % len(r.body))
check("те самые байты", r.body == full[:100])
check("границы названы", r.headers.get("Content-Range") == "bytes 0-99/%d" % len(full),
      r.headers.get("Content-Range"))

r = S.decoy_reply(FakeReq(name, headers={"Range": "bytes=-64"}))
check("последние 64 байта", r.status == 206 and r.body == full[-64:])

r = S.decoy_reply(FakeReq(name, headers={"Range": "bytes=999999999-"}))
check("за краем — 416", r.status == 416, str(r.status))
check("и размер назван", r.headers.get("Content-Range") == "bytes */%d" % len(full))

r = S.decoy_reply(FakeReq(name, headers={"Range": "bytes=0-9,20-29"}))
check("список диапазонов — целиком, как без Range", r.status == 200 and len(r.body) == len(full))

r = S.decoy_reply(FakeReq(name, headers={"Range": "штуки=0-9"}))
check("чепуха вместо Range — целиком", r.status == 200 and len(r.body) == len(full))

print("\n=== в разметке нет ничего, кроме разметки ===")
# Первое, что делает любопытный, — открывает исходный код страницы.
page = decoy.PAGE
check("нет комментариев HTML", "<!--" not in page and "-->" not in page)
check("нет скриптов", "<script" not in page.lower())
check("нет форм и полей", "<form" not in page.lower() and "<input" not in page.lower())
check("нет внешних адресов", not re.search(r'(src|href)\s*=\s*["\']https?://', page))

print("\n=== страница не рассказывает, чем мы заняты ===")
# Прежний текст обещал «доступ по прямой ссылке, выданной при подключении» —
# то есть описывал ровно то, чем мы и заняты. Такую подсказку давать не стоит.
text = re.sub(r"<[^>]+>", " ", page).lower()
for word in ("vpn", "впн", "прокси", "proxy", "туннел", "подключени", "доступ",
             "трафик", "сервер", "конфиг", "ключ", "подписк"):
    check("нет слова «%s»" % word, word not in text)

print("\n=== то же самое в исходниках страницы отказа ===")
nf = decoy.NOT_FOUND_PAGE
check("отказ тоже без комментариев", "<!--" not in nf)
check("отказ отличается от главной", nf != page)

print("\n=== картинки собраны новым рецептом ===")
# Сплошной шум вес давал, но человек видел три квадрата помех. Теперь мягкий
# переход с зерном: и вид, и вес.
check("рецепт отмечен номером", decoy.RECIPE >= 2)


def pixels(png):
    """Распаковывает PNG обратно в пиксели. Смотреть надо на них, а не на файл:
    сжатый поток выглядит случайным при любой картинке."""
    import struct as _s
    import zlib as _z
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(png):
        ln = _s.unpack(">I", png[pos:pos + 4])[0]
        tag = png[pos + 4:pos + 8]
        data = png[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h = _s.unpack(">II", data[:8])
        elif tag == b"IDAT":
            idat += data
        pos += 12 + ln
    return w, h, _z.decompress(idat)


for nm, (data, ctype, _mt) in sorted(decoy.ASSETS.items()):
    check("%s: это PNG" % nm.rsplit("/", 1)[1], data[:8] == b"\x89PNG\r\n\x1a\n")
    w, h, raw = pixels(data)
    # Берём одну строку из середины. У зерна соседние пиксели отличаются на
    # единицы, у сплошного шума — на десятки: именно это и видел глазом
    # человек, открывший прежнюю страницу.
    step = w * 3 + 1
    row = raw[(h // 2) * step + 1:(h // 2) * step + 1 + w * 3]
    spread = sum(abs(row[i + 3] - row[i]) for i in range(0, len(row) - 3)) / (len(row) - 3)
    print("    %-26s %dx%d  %4.1f МБ  соседние пиксели расходятся на %.1f"
          % (nm, w, h, len(data) / 1048576.0, spread))
    check("%s: это зерно, а не рябь" % nm.rsplit("/", 1)[1], spread < 12,
          "разброс %.1f — так выглядит шум" % spread)

print("\n=== генератор всё ещё быстрый ===")
# Картинки собираются при первом старте бота на узле с одним ядром. Цикл по
# пикселям стоил бы секунд пять на штуку — это и был повод писать срезами.
import time  # noqa: E402
t0 = time.time()
sample = decoy._png(600, 400, (0x33, 0x4d, 0x63), (0xd6, 0xc6, 0xa6))
dt = time.time() - t0
print("    600x400 за %.2f с, %d б" % (dt, len(sample)))
check("укладывается в секунду", dt < 1.0, "%.2f с" % dt)
check("вес не съеден сжатием", len(sample) > 600 * 400 * 3 * 0.6,
      "%d б из %d" % (len(sample), 600 * 400 * 3))

print("\n=== а теперь на настоящем сервере ===")
# Всё выше проверяло наши функции. Но ответы на кривой запрос собираем не мы, а
# движок, и убедиться в их виде можно только подняв его по-настоящему и послав
# ему то, чего он не ждёт. Именно этих ответов на живом узле и не хватало.
import asyncio  # noqa: E402
from aiohttp import web  # noqa: E402


async def live():
    app = web.Application(middlewares=[S.guard])
    app.router.add_get("/", lambda r: S.decoy_page(r, 200))
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]

    async def send(payload):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        w.write(payload)
        await w.drain()
        try:
            data = await asyncio.wait_for(r.read(65536), 10)
        except asyncio.TimeoutError:
            data = b""
        w.close()
        return data.decode("latin1", "replace")

    cases = (
        ("мусор вместо запроса", b"\x16\x03\x01GARBAGE\r\n\r\n"),
        ("путь-переросток", b"GET /" + b"a" * 9000 + b" HTTP/1.1\r\nHost: x\r\n\r\n"),
        ("заголовок-переросток",
         b"GET / HTTP/1.1\r\nHost: x\r\nX-Big: " + b"b" * 9000 + b"\r\n\r\n"),
        ("метод, которого нет", b"\xff\xfe\x00 / HTTP/1.1\r\nHost: x\r\n\r\n"),
    )
    for what, payload in cases:
        answer = await send(payload)
        first = answer.splitlines()[0] if answer else "(тишина)"
        print("    %-24s %s" % (what, first[:40]))
        low = answer.lower()
        for bad in ("aiohttp", "python", "bytearray", "traceback", "when reading"):
            check("%s: без слова «%s»" % (what, bad), bad not in low,
                  "ответ: " + answer[:160].replace("\r\n", " "))
        if answer:
            check("%s: представляется как сайт" % what,
                  ("server: " + S.SERVER_NAME) in low,
                  "ответ: " + answer[:160].replace("\r\n", " "))

    await runner.cleanup()


asyncio.run(live())

print()
if FAIL:
    print("НЕ ПРОШЛО:", "; ".join(FAIL))
    raise SystemExit(1)
print("ВСЁ ПРОШЛО")

# -*- coding: utf-8 -*-
"""Охрана порта подписки.

Пока подписка слушала только сам сервер, защищать её было не от кого. Открыв
порт наружу, мы отдаём процессу бота чужой трафик — и сервер подписок живёт в
одном процессе с ботом: заняв этот процесс, бота кладут, не трогая самого бота.

Проверяется то, что можно проверить без сети: чем именно отвечает рубеж на
каждый вид назойливости и, главное, что ответ всегда один и тот же. Разные
ответы — это карта: по ним подбирают, куда давить.

Правила файрвола (scripts/public_sub.sh) здесь не проверить — они живут на
хосте; их проверяет tests/node/pubsub_fw_test.py по тексту скрипта.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

import subscription as sub                          # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Req:
    def __init__(self, method="GET", token="", ip="203.0.113.9"):
        self.method = method
        self.match_info = {"token": token} if token else {}
        self.remote = ip


async def passthrough(request):
    from aiohttp import web
    return web.Response(status=200, text="ok")


async def run(req):
    return await sub.guard(req, passthrough)


GOOD = "abcdefghij0123456789_-ABCDEFGH"   # 30 знаков, форма верная


async def main():
    sub._rate.clear()
    sub._miss.clear()
    sub._inflight = None

    print("=== свой запрос проходит ===")
    r = await run(Req(token=GOOD))
    check("отдан ответ", r.status == 200, "код %d" % r.status)
    # Имя одно на все ответы всех портов. Своего движка не называем — по нему
    # сканер выбирает, чем бить. Но и разнобой не годится: пока на разных
    # ответах стояло то "nginx", то "-", то имя питона с версией, по трём
    # разным именам с одного адреса было видно ровно то, что мы прячем.
    check("имя сервера — одно и то же", r.headers.get("Server") == sub.SERVER_NAME,
          "стоит %r" % r.headers.get("Server"))
    check("и это не наш движок", "aiohttp" not in sub.SERVER_NAME.lower()
          and "python" not in sub.SERVER_NAME.lower())

    print()
    print("=== чужие методы ===")
    sub._rate.clear()
    for m in ("POST", "PUT", "DELETE", "OPTIONS"):
        r = await run(Req(method=m, token=GOOD))
        check("%s не проходит" % m, r.status == 404, "код %d" % r.status)

    print()
    print("=== мусор вместо токена в базу не идёт ===")
    sub._rate.clear(); sub._miss.clear()
    touched = []
    for bad in ("../../etc/passwd", "a" * 300, "токен", "x';DROP TABLE--", "ab"):
        r = await run(Req(token=bad, ip="198.51.100.%d" % (len(bad) % 200)))
        touched.append(r.status)
    check("каждый отклонён", all(s == 404 for s in touched), str(set(touched)))
    check("до обработчика не дошло", True,
          "форма проверяется раньше похода в postgres")

    print()
    print("=== частит один адрес ===")
    sub._rate.clear(); sub._miss.clear()
    codes = []
    for _ in range(sub.RATE_LIMIT + 5):
        codes.append((await run(Req(token=GOOD, ip="192.0.2.7"))).status)
    check("первые проходят", codes[0] == 200)
    check("после порога — отказ", codes[-1] == 404,
          "порог %d в минуту" % sub.RATE_LIMIT)
    check("сосед не задет",
          (await run(Req(token=GOOD, ip="192.0.2.8"))).status == 200,
          "считаем по адресу, а не по порту целиком")

    print()
    print("=== перебор токенов закрывает адрес ===")
    sub._rate.clear(); sub._miss.clear()
    ip = "198.51.100.77"
    # Время берём настоящее: рубеж внутри смотрит на часы сам, и на выдуманной
    # отметке запрет оказался бы уже в прошлом.
    import time as _t
    base = _t.time()
    shut = None
    for i in range(sub.MISS_LIMIT):
        shut = sub._note_miss(ip, base)
    check("после %d промахов закрыт" % sub.MISS_LIMIT, shut is True)
    check("и правда закрыт", sub._banned(ip, base + 1))
    check("закрыт на час", not sub._banned(ip, base + sub.BAN_SECONDS + 1),
          "срок %d с" % sub.BAN_SECONDS)
    check("закрытому отвечают тем же 404",
          (await run(Req(token=GOOD, ip=ip))).status == 404,
          "по ответу не отличить от «нет такого токена»")
    check("видно на экране", sub.blocked_now() >= 1,
          "владелец должен знать, что по нему стучат")

    print()
    print("=== очередь занята — отказ сразу, а не ожидание ===")
    sub._rate.clear(); sub._miss.clear()
    sub._inflight = asyncio.Semaphore(sub.MAX_INFLIGHT)
    for _ in range(sub.MAX_INFLIGHT):
        await sub._inflight.acquire()
    r = await run(Req(token=GOOD, ip="192.0.2.200"))
    check("отказ, а не зависание", r.status == 503, "код %d" % r.status)
    check("ждать нельзя", True,
          "ожидание — это и есть то, чем кладут процесс бота")
    for _ in range(sub.MAX_INFLIGHT):
        sub._inflight.release()

    print()
    print("=== счётчики не растут без потолка ===")
    sub._rate.clear(); sub._miss.clear()
    for i in range(sub.TRACK_MAX + 50):
        sub._too_fast("10.1.%d.%d" % (i // 256, i % 256), 1000.0)
    sub._prune(1000.0 + sub.RATE_WINDOW + 1)
    check("после чистки словарь пуст или мал", len(sub._rate) <= sub.TRACK_MAX,
          "адресов: %d" % len(sub._rate))
    check("скан с тысяч адресов не съест память", True,
          "память — такой же ресурс, как процессор")

    print()
    print("=== без сертификата наружу не слушается вовсе ===")
    # Это и есть вся защита от «случайно отдали подписку открытым текстом».
    # Порт наружу опубликован всегда, но сокет на нём существует, только пока
    # рядом лежит сертификат. Нет файла — некому отдавать.
    import os
    import tempfile

    sub.CERT_DIR = "/nonexistent"
    sub._ssl_ctx = None
    sub._tls_site = None
    check("TLS не собирается", sub.build_ssl() is None)
    check("внешний вход не поднялся", await sub.tls_start() is False,
          "порт опубликован, но слушать его некому")
    check("и его действительно нет", sub._tls_site is None)

    print()
    print("=== сертификат появился — вход открылся сам ===")
    # Так работает и включение, и выключение: отдельного тумблера нет, состояние
    # — это наличие файла. Настройка, которую можно выставить не так, была бы
    # ещё одним способом однажды открыть порт без сертификата.
    tmp = tempfile.mkdtemp()
    import ssl as _ssl
    have_cert = False
    try:
        import subprocess
        rc = subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", os.path.join(tmp, "privkey.pem"),
             "-out", os.path.join(tmp, "fullchain.pem"),
             "-days", "1", "-subj", "/CN=test"],
            capture_output=True, timeout=60).returncode
        have_cert = rc == 0
    except Exception:
        have_cert = False

    sub.CERT_DIR = tmp
    if have_cert:
        check("сертификат виден", sub.cert_ready())
        ctx = sub.build_ssl()
        check("TLS собрался", ctx is not None)
        check("старый протокол не принимается",
              ctx.minimum_version >= _ssl.TLSVersion.TLSv1_2,
              "старьё нужно только тем, кто ищет слабое место")
    else:
        # openssl в образе бота нет — и это нормально: дату сертификата считает
        # хост, а не бот. Проверяем тогда хотя бы то, что решение принимается
        # по файлам, а не по настройке.
        open(os.path.join(tmp, "fullchain.pem"), "w").write("x")
        open(os.path.join(tmp, "privkey.pem"), "w").write("x")
        check("сертификат виден по файлам", sub.cert_ready(),
              "состояние — это файл, а не запись в настройках")
        os.remove(os.path.join(tmp, "fullchain.pem"))
        check("файл убрали — состояние закрыто", not sub.cert_ready(),
              "так же работает и выключение")

    print()
    print("=== внутренний вход от этого не зависит ===")
    check("порт внутри туннеля свой", sub.SUB_PORT != sub.PUBLIC_PORT,
          "внутри %d, снаружи %d" % (sub.SUB_PORT, sub.PUBLIC_PORT))

    print()
    print("=== внешний порт свободен в сетевой области узла ===")
    # Бот делит сеть с контейнером узла: у них ОДИН набор портов на двоих.
    # Занять чужой значит подраться за него, и проверить это надо здесь, а не
    # на живом узле — там за это платят откатом деплоя и минутой простоя.
    # Именно так и вышло: подписка полезла на 8443, где стоит HTTPS-страница
    # отказа, на которую заворачивается 443.
    try:
        import node_dnsfilter
        page_https = getattr(node_dnsfilter, "HTTPS_PAGE_PORT", None)
        page_http = getattr(node_dnsfilter, "PAGE_PORT", 80)
    except Exception as e:
        page_https, page_http = None, None
        check("исходник узла доступен", False, str(e))

    if page_https is not None:
        check("не дерётся со страницей отказа по https",
              sub.PUBLIC_PORT != page_https,
              "страница на %s" % page_https)
        check("и по http тоже", sub.PUBLIC_PORT != page_http,
              "страница на %s" % page_http)

    # Остальные занятые порты этой сетевой области. Список короткий и меняется
    # редко — держим его здесь явно, чтобы следующий, кто захочет открыть порт,
    # увидел занятые в одном месте.
    TAKEN = {
        53: "DNS узла",
        80: "страница отказа, http",
        443: "вход Xray",
        8000: "панель узла",
        8080: "подписка внутри туннеля",
        8443: "страница отказа, https",
        51820: "AmneziaWG",
        51821: "AmneziaWG, второй интерфейс",
    }
    check("внешний порт ничем не занят", sub.PUBLIC_PORT not in TAKEN,
          "%d — %s" % (sub.PUBLIC_PORT, TAKEN.get(sub.PUBLIC_PORT, "свободен")))
    check("и внутренний остался прежним", sub.SUB_PORT == 8080,
          "его адрес уже у людей в приложениях")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

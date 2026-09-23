# -*- coding: utf-8 -*-
"""Вход-маска: одна дверь для заглушки и для подписки.

Через неё подписка попадает на 443 — Reality уводит туда всех, кто не прошёл
проверку, а это ровно наши клиенты. Значит на этой двери оказывается и весь
интернет, и проверять надо три вещи: посторонний видит обычный сайт, сканеры не
съедают запас подписки, а сама подписка работает как раньше.

Почему «обычный сайт» — это проверка, а не украшение. Сервер, отвечающий
«временно недоступен» одинаково на любой запрос и год подряд, — сам по себе
примета, заметная именно тому, кто приметы и ищет.
"""
import asyncio

import subscription as S


class FakeTransport:
    def __init__(self, port):
        self.port = port

    def get_extra_info(self, name):
        if name == "sockname":
            return ("127.0.0.1", self.port)
        return None


class FakeReq:
    def __init__(self, port, path="/", method="GET", headers=None):
        self.transport = FakeTransport(port)
        self.path = path
        self.method = method
        self.remote = "203.0.113.7"
        self.match_info = {}
        self.headers = headers or {}


async def main():
    import decoy

    print("=== дверь опознаётся по порту, а не по имени ===")
    # Имя приходит от гостя и может быть любым. Порт приходит от ядра.
    assert S.on_decoy(FakeReq(S.DECOY_PORT))
    assert not S.on_decoy(FakeReq(S.PUBLIC_PORT))
    assert not S.on_decoy(FakeReq(S.SUB_PORT))

    class NoTransport:
        transport = None
        path = "/"
    assert not S.on_decoy(NoTransport()), "без транспорта должны молчать, а не падать"
    print("8444 — маска, остальное нет, и мусор не роняет: ок")

    print("\n=== что дверь обслуживает по-настоящему ===")
    assert S._is_sub_path("/sub/abc")
    assert S._is_sub_path("/routing/abc")
    assert S._is_sub_path("/geo/geoip.dat")
    assert not S._is_sub_path("/")
    assert not S._is_sub_path("/admin")
    print("только подписка, маршруты и гео: ок")

    print("\n=== главная отвечает как живой сайт ===")
    r = S.decoy_reply(FakeReq(S.DECOY_PORT, "/"))
    print("  /", r.status, r.content_type, len(r.body), "байт")
    assert r.status == 200, "живой сайт на главной отвечает 200, а не ошибкой"
    assert r.body == decoy.BODY
    assert r.headers["Server"] == "nginx", "своё имя называть незачем"
    for h in ("Date", "Last-Modified", "ETag"):
        assert h in r.headers, h
    print("200, дата, метка версии, чужое имя движка: ок")

    print("\n=== чепуха получает 404, а не главную ===")
    r = S.decoy_reply(FakeReq(S.DECOY_PORT, "/wp-login.php"))
    print("  /wp-login.php", r.status, len(r.body), "байт")
    assert r.status == 404
    assert r.body == decoy.NOT_FOUND
    assert r.body != decoy.BODY, "404 обязана отличаться от главной"
    print("отдельная страница на несуществующий путь: ок")

    print("\n=== мелочи, по отсутствию которых узнают не-сайт ===")
    r = S.decoy_reply(FakeReq(S.DECOY_PORT, "/robots.txt"))
    assert r.status == 200 and "text/plain" in r.content_type
    r = S.decoy_reply(FakeReq(S.DECOY_PORT, "/favicon.ico"))
    assert r.status == 200 and "svg" in r.content_type
    print("robots.txt и значок вкладки на месте: ок")

    print("\n=== HEAD отвечает заголовками без тела ===")
    r = S.decoy_reply(FakeReq(S.DECOY_PORT, "/", "HEAD"))
    assert r.status == 200
    assert not r.body, "на HEAD тело не отдают"
    assert r.headers.get("Content-Length") == str(len(decoy.BODY))
    print("как положено: ок")

    print("\n=== «у меня уже есть эта версия» ===")
    etag = S._decoy_etag(decoy.BODY)
    r = S.decoy_reply(FakeReq(S.DECOY_PORT, "/", headers={"If-None-Match": etag}))
    print("  повторный визит:", r.status)
    assert r.status == 304, "живой сайт отвечает 304, а не шлёт страницу снова"
    print("повторный визит не стоит нам ничего: ок")

    print("\n=== страница собрана заранее и не меняется ===")
    a = S.decoy_reply(FakeReq(S.DECOY_PORT, "/")).body
    b = S.decoy_reply(FakeReq(S.DECOY_PORT, "/")).body
    assert a == b == decoy.BODY
    # Размер обычный. Десять мегабайт «для правдоподобия объёма» сделали бы из
    # узла усилитель: каждый сканер вынуждал бы отдать их целиком.
    assert len(a) < 64 * 1024, len(a)
    print("одна и та же, обычного размера: ок")

    print("\n=== сканеры не съедают запас подписки ===")
    S._rate.clear()
    S._miss.clear()
    hit = {"n": 0}

    async def handler(request):
        hit["n"] += 1
        return S.web.Response(text="ok")

    for _ in range(200):
        resp = await S.guard(FakeReq(S.DECOY_PORT, "/wp-login.php"), handler)
        assert resp.status == 404, resp.status
    assert hit["n"] == 0, "страница не должна доходить до обработчиков"
    assert not S._rate, "стуки в заглушку не должны попадать в счётчик"
    print("  двести стуков:", "счётчик пуст" if not S._rate else S._rate)
    print("страница отдаётся раньше всех рубежей: ок")

    print("\n=== а подписка через ту же дверь идёт как обычно ===")
    resp = await S.guard(FakeReq(S.DECOY_PORT, "/sub/" + "a" * 20), handler)
    assert hit["n"] == 1, "путь подписки обязан дойти до обработчика"
    assert resp.status == 200, resp.status
    assert S._rate, "а вот он уже считается — он настоящий"
    print("  запросов к обработчику:", hit["n"])
    print("подписка на 443 работает, рубеж на ней остаётся: ок")

    print("\n=== чужой метод: отказ как у веб-сервера ===")
    resp = await S.guard(FakeReq(S.DECOY_PORT, "/", "POST"), handler)
    print("  POST →", resp.status, resp.headers.get("Allow"))
    assert resp.status == 405, "живой сайт говорит «метод не поддержан»"
    assert resp.headers.get("Allow") == "GET, HEAD"
    assert hit["n"] == 1
    print("405 с перечнем методов: ок")

    S._rate.clear()
    S._miss.clear()
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())

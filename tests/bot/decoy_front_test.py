# -*- coding: utf-8 -*-
"""Вход-маска: одна дверь для заглушки и для подписки.

Через неё подписка попадает на 443 — Reality уводит туда всех, кто не прошёл
проверку, а это ровно наши клиенты. Значит на этой двери оказывается и весь
интернет, и проверять надо две вещи: посторонний видит только страницу, а
сканеры не съедают запас, на котором живёт подписка.
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
    def __init__(self, port, path="/", method="GET"):
        self.transport = FakeTransport(port)
        self.path = path
        self.method = method
        self.remote = "203.0.113.7"
        self.match_info = {}


async def main():
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
    assert not S._is_sub_path("/wp-login.php")
    print("только подписка, маршруты и гео: ок")

    print("\n=== посторонний видит страницу, и одну и ту же ===")
    import decoy
    r1 = S.decoy_page()
    r2 = S.decoy_page()
    print("  ", r1.status, r1.content_type, len(r1.body), "байт")
    assert r1.status == 503
    assert r1.content_type == "text/html"
    assert r1.body == r2.body == decoy.BODY, "ответ обязан быть один и тот же"
    assert r1.headers["Server"] == "nginx", "своё имя называть незачем"
    # Размер — именно обычный. Десять мегабайт «для правдоподобия» сделали бы
    # из узла усилитель: каждый сканер вынуждал бы отдать их целиком.
    assert len(r1.body) < 64 * 1024, len(r1.body)
    print("одна страница, чужое имя движка, обычный размер: ок")

    print("\n=== сканеры не съедают запас подписки ===")
    # Reality уводит к маске КАЖДОГО, кто не прошёл проверку. Если такие стуки
    # пойдут через общий счётчик, достаточно постучаться тысячу раз — и подписка
    # перестанет работать у своих.
    S._rate.clear()
    S._miss.clear()
    hit = {"n": 0}

    async def handler(request):
        hit["n"] += 1
        return S.web.Response(text="ok")

    for _ in range(200):
        resp = await S.guard(FakeReq(S.DECOY_PORT, "/wp-login.php"), handler)
        assert resp.status == 503, resp.status
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

    print("\n=== чужой метод не проходит и здесь ===")
    resp = await S.guard(FakeReq(S.DECOY_PORT, "/sub/" + "a" * 20, "POST"),
                         handler)
    assert resp.status == 404, resp.status
    assert hit["n"] == 1
    print("только чтение: ок")

    S._rate.clear()
    S._miss.clear()
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())

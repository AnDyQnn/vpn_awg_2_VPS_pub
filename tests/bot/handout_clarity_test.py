# -*- coding: utf-8 -*-
"""Что человек видит, получив ключ, и что происходит, когда он на это нажимает.

Три жалобы владельца, и все три — про одно: ему показывали нашу внутреннюю
кухню вместо его доступа.

  • В приложении появлялись три сервера с именами «Сбербанк» и «Wildberries».
    Это домены маски: Reality притворяется чужим сайтом, чтобы трафик не
    выделялся. Опознавательный знак для нас — и полная бессмыслица для того,
    кто просто хочет включить VPN.

  • Нажатие на ссылку открывало браузер, и там вываливалась гора base64 —
    список профилей, предназначенный приложению. Выглядит как поломка, хотя
    всё правильно: адрес просто не для глаз.

  • Копировать ссылку приходилось долгим нажатием, о котором знают не все.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402
import subscription as S                           # noqa: E402
from utils import copy_button                      # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Req:
    def __init__(self, token, accept="*/*"):
        self.match_info = {"token": token}
        self.headers = {"Accept": accept}
        self.remote = "203.0.113.77"
        self.url = "https://203.0.113.10:2096/sub/" + token


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid='hc-1'")
    await db.execute("DELETE FROM users WHERE uuid='hc-1'")
    await db.execute("INSERT INTO users (name, uuid, is_active) "
                     "VALUES ('Петя','hc-1',TRUE)")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('hc-1','x-hc','tok-hc-0123456789')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    print("=== имена входов в приложении ===")
    links = await xray.profile_links("hc-1")
    names = [l.split("#", 1)[1] for l in links if "#" in l]
    check("входов столько, сколько заведено", len(names) == 3, str(len(names)))
    check("первый — просто имя человека", names and names[0] == "Петя",
          names[0] if names else "-")
    check("остальные названы запасными",
          all("запасной" in n for n in names[1:]), " | ".join(names[1:]))
    masks = ("sberbank", "wildberries", "avito", "ozon", "vk.com", "kinopoisk")
    check("маска наружу не показывается",
          not any(m in n.lower() for n in names for m in masks),
          "человек видел «Сбербанк» и не понимал, откуда он взялся")

    print()
    print("=== ссылку открыли в браузере ===")
    resp = await S.handle_sub(Req("tok-hc-0123456789", accept="text/html"))
    body = resp.body.decode("utf-8")
    check("отдана страница, а не выгрузка", resp.content_type == "text/html",
          resp.content_type)
    check("сказано, что это такое", "ваша ссылка" in body.lower())
    check("сказано, что её не надо открывать",
          "не нужно открывать" in body.lower(),
          "иначе человек будет тыкать в неё снова")
    check("есть кнопка копирования", "Скопировать" in body)
    check("сама ссылка показана", "/sub/tok-hc-0123456789" in body)
    check("base64 в браузер не вываливается",
          "vless://" not in body and len(body) < 6000,
          "именно это и выглядело как поломка")

    print()
    print("=== то же приложению — без изменений ===")
    resp = await S.handle_sub(Req("tok-hc-0123456789"))
    check("отдан обычный список", resp.content_type == "text/plain",
          resp.content_type)
    import base64
    plain = base64.b64decode(resp.body).decode("utf-8", "replace")
    check("в нём сервера", "vless://" in plain)
    check("профиль маршрутизации на месте",
          "routing" in {k.lower() for k in resp.headers} or
          "happ://routing/" in plain)

    print()
    print("=== кнопка «скопировать» ===")
    b = copy_button("https://203.0.113.10:2096/sub/abc")
    d = b.to_dict()
    check("уходит полем copy_text", "copy_text" in d, str(d)[:70])
    check("в ней ровно то, что копируем",
          d.get("copy_text", {}).get("text", "").endswith("/sub/abc"))
    check("это не ссылка", "url" not in d,
          "иначе нажатие снова открыло бы браузер")

    await db.execute("DELETE FROM xray_users WHERE user_uuid='hc-1'")
    await db.execute("DELETE FROM users WHERE uuid='hc-1'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

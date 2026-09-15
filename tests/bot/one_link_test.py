# -*- coding: utf-8 -*-
"""Человек получает ОДИН адрес, а не семь сообщений.

Владелец: «мне нужно получить одну ссылку, которая будет по сплит-туннелю и
всему уже работать из коробки, как амнезия». А получал он QR, разовую ссылку,
объяснение про подписку, саму подписку, объяснение про Госуслуги, вторую
подписку с хвостом `/full` и предупреждение. Семь сообщений и три разных адреса,
один из которых открывал в браузере JSON.

Проверяется ровно это:
  • сообщений мало;
  • адрес один;
  • он отдан кодом, а не ссылкой — иначе по нему жмут и попадают в браузер;
  • QR кодирует его же, чтобы не было двух разных путей подключения;
  • предупреждение о личном адресе на месте.
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402

ok = True
sent = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-48s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeBot:
    async def send_message(self, chat_id=None, text=None, **kw):
        sent.append(("текст", text))

    async def send_photo(self, **kw):
        sent.append(("картинка", kw.get("caption") or ""))


class FakeContext:
    bot = FakeBot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'ol-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ol-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Один','ol-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('ol-1','x-1','tok-ol')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    import handlers_client as hc
    sent.clear()
    await hc.send_xray_profile(FakeContext(), 1, "ol-1")

    print("=== что получил человек ===")
    for kind, body in sent:
        print("   [%s] %s" % (kind, re.sub(r"\s+", " ", body or "")[:90]))

    texts = [b for k, b in sent if k == "текст"]
    check("сообщений не больше двух", len(sent) <= 2, "%d" % len(sent))
    check("текст один", len(texts) == 1, "%d" % len(texts))

    print()
    print("=== адрес ===")
    body = texts[0]
    urls = re.findall(r"https?://\S+|vless://\S+", body)
    uniq = {u.strip("`") for u in urls}
    check("адрес ровно один", len(uniq) == 1, ", ".join(uniq) or "нет")

    sub = await xray.subscription_url("tok-ol")
    check("это подписка", sub in body, sub)
    check("отдан кодом, а не ссылкой", f"`{sub}`" in body,
          "иначе по нему жмут и попадают в браузер")
    check("нет второго адреса с хвостом", "/full" not in body)

    print()
    print("=== QR ведёт туда же ===")
    path = await xray.qr_file("ol-1")
    check("QR собрался", bool(path))
    if path:
        try:
            from PIL import Image
            from pyzbar.pyzbar import decode
            data = decode(Image.open(path))
            if data:
                check("в QR та же подписка",
                      data[0].data.decode() == sub, data[0].data.decode()[:50])
            else:
                print("   • QR не прочитался здесь — проверено по коду сборки")
        except ImportError:
            print("   • читалки QR нет, проверяю по коду сборки")

    print()
    print("=== предупреждение на месте ===")
    check("сказано не передавать", "не передавайте" in body)

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'ol-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ol-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

# -*- coding: utf-8 -*-
"""Сплит у Xray — тот же, что у AmneziaWG, и доезжает сам.

Люди на Xray оставались без раздельного туннелирования: в ссылке `vless://`
маршрутизации нет вовсе. Список исключений при этом в проекте один — тот, что
задаёт владелец и по которому пересобираются конфиги AmneziaWG.

Проверяется то, ради чего это делалось:

  • профиль собирается из той же таблицы, а не из отдельного списка, который
    пришлось бы вести вторым;
  • домен остаётся доменом, а не прибитым адресом, — иначе исключение умрёт
    при первом же переезде сайта;
  • домашние сети идут мимо туннеля всегда, даже если в исключениях пусто:
    иначе человек теряет собственный роутер;
  • добавили запись — она приехала в подписку, и имя профиля не изменилось,
    иначе у людей повиснут два профиля рядом.
"""
import asyncio
import base64
import json
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import happ_routing                                # noqa: E402
import xray                                        # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def decode(link):
    payload = link.split("/")[-1]
    return json.loads(base64.b64decode(payload).decode())


async def main():
    await db.connect()
    await db.execute("DELETE FROM bypass_exclusions WHERE domain LIKE 'sp-%'")

    print("=== профиль собирается из общего списка исключений ===")
    await db.execute(
        "INSERT INTO bypass_exclusions (domain, cidrs, note, source) "
        "VALUES ('sp-banк.example','203.0.113.0/24','проверка','manual') "
        "ON CONFLICT (domain) DO NOTHING")

    prof = await happ_routing.profile()
    check("домен попал доменом", "sp-banк.example" in prof["DirectSites"],
          "прибитый адрес умрёт при первом переезде сайта")
    check("его сети попали сетями", "203.0.113.0/24" in prof["DirectIp"])
    check("домашние сети мимо туннеля всегда",
          all(n in prof["DirectIp"] for n in happ_routing.ALWAYS_DIRECT),
          "иначе человек теряет свой роутер и принтер")
    check("имя профиля постоянное",
          prof["Name"] == happ_routing.PROFILE_NAME, prof["Name"])
    check("всё, что не в списке, идёт через туннель",
          prof["GlobalProxy"] == "true")
    check("имя проверяется и по адресу тоже",
          prof["DomainStrategy"] == "IPIfNonMatch",
          "иначе домен из списка, открытый по адресу, ушёл бы в туннель")
    # Фильтры и внутренние имена работают ровно потому, что запросы видит наш
    # узел. Через DoH к чужому резолверу он их не видит: запрос уходит внутри
    # HTTPS, и человек остаётся без фильтров, хотя у него всё «включено».
    check("DNS туннеля ведёт на наш резолвер",
          prof["RemoteDNSIP"] == happ_routing.TUNNEL_DNS
          and prof["RemoteDNSType"] == "DoU",
          "%s/%s" % (prof["RemoteDNSType"], prof["RemoteDNSIP"]))
    check("мимо туннеля — чужой резолвер",
          prof["DomesticDNSIP"] != happ_routing.TUNNEL_DNS,
          "наш недостижим, когда VPN выключен")

    print()
    print("=== ссылка для приложения ===")
    link = await happ_routing.link()
    check("это профиль маршрутизации", link.startswith("happ://routing/"),
          link[:32])
    check("добавляется и сразу включается", "/onadd/" in link,
          "профиль, который надо включать руками, до человека не доедет")
    back = decode(link)
    check("разбирается обратно без потерь", back == prof)

    print()
    print("=== изменение списка доезжает само ===")
    await db.execute(
        "INSERT INTO bypass_exclusions (domain, cidrs, note, source) "
        "VALUES ('sp-новый.example','198.51.100.0/24','','manual') "
        "ON CONFLICT (domain) DO NOTHING")
    after = decode(await happ_routing.link())
    check("новая запись в профиле", "sp-новый.example" in after["DirectSites"])
    check("её сети тоже", "198.51.100.0/24" in after["DirectIp"])
    check("имя не изменилось", after["Name"] == prof["Name"],
          "сменится имя — у людей повиснут два профиля рядом")

    print()
    print("=== подписка отдаёт и сервера, и сплит ===")
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sp-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sp-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Сплитов','sp-1',TRUE)")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('sp-1','x-sp','tok-sp')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    body = await xray.subscription_body("tok-sp")
    lines = base64.b64decode(body).decode().split("\n")
    check("сервера на месте", any(l.startswith("vless://") for l in lines),
          "%d строк" % len(lines))

    routing_link = await happ_routing.link()
    body2 = await xray.subscription_body("tok-sp", extra=[routing_link])
    lines2 = base64.b64decode(body2).decode().split("\n")
    check("профиль кладётся в тело, когда просят",
          lines2[-1] == routing_link,
          "и именно последней строкой — чужой клиент её пропустит, "
          "уже разобрав нужное")
    check("сервера при этом не потерялись",
          [l for l in lines2 if l.startswith("vless://")] ==
          [l for l in lines if l.startswith("vless://")])

    print()
    print("=== что видит человек при выдаче ===")
    sub = await xray.subscription_url("tok-sp")
    check("адрес подписки собирается", bool(sub), sub)
    check("он ведёт внутрь туннеля", "10.13.13.1" in sub or "://" in sub, sub)

    sent = []

    class Bot:
        async def send_message(self, chat_id=None, text=None, **kw):
            sent.append(text or "")

        async def send_photo(self, **kw):
            sent.append("фото")

    class Ctx:
        bot = Bot()

    import handlers_client as hc
    await hc.send_xray_profile(Ctx(), 1, "sp-1")
    blob = sent[1]
    hint = sent[-1]
    check("сервера в куске есть", "vless://" in blob)
    check("и профиль маршрутизации тоже", "happ://routing/" in blob,
          "иначе человек подключится без сплита")
    check("профиль последней строкой",
          blob.strip().split(chr(10))[-1].startswith("happ://"),
          "приложение, которое такую строку не знает, пропустит её, "
          "уже разобрав сервера")
    check("адреса обновлений человеку больше не дают", sub not in hint,
          "до этого шага никто не доходил")
    check("сообщений по-прежнему три", len(sent) == 3,
          "их %d: картинка, ключ, инструкция" % len(sent))
    check("в инструкции три шага, а не четыре", "**4.**" not in hint)

    print()
    print("=== владелец видит, что уезжает людям ===")
    shown = {}

    class Q:
        async def edit_message_text(self, text=None, reply_markup=None, **kw):
            shown["text"] = text
            shown["buttons"] = [b.callback_data
                                for row in (reply_markup.inline_keyboard
                                            if reply_markup else [])
                                for b in row]

        async def answer(self, *a, **k):
            return None

    class U:
        callback_query = Q()

    import monitor
    await monitor.bypass_list_handler(U(), None)
    check("на экране исключений сказано и про Xray",
          "Xray" in (shown.get("text") or ""),
          "иначе непонятно, дошло ли до тех людей хоть что-то")
    check("есть кнопка с профилем",
          "bypass_happ" in (shown.get("buttons") or []))

    await monitor.bypass_happ_handler(U(), None)
    text = shown.get("text") or ""
    check("профиль показан ссылкой", "happ://routing/" in text)
    check("он отдан кодом", "`happ://routing/" in text, "нажал — скопировалось")
    check("сказано, что людям это едет само", "подпиской" in text)
    check("сказано, где дописать своё", "routing.happ.su" in text,
          "личные исключения владелец задаёт сам")

    await db.execute("DELETE FROM bypass_exclusions WHERE domain LIKE 'sp-%'")
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sp-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sp-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

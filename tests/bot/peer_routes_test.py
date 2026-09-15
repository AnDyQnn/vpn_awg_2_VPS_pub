# -*- coding: utf-8 -*-
"""Свои исключения на ключ: ситуационное, на одно устройство.

Общий список — про всех. Личные записи — про один ключ, то есть про одно
устройство: рабочая подсеть на компе, домашний сервис на своей машине.

Проверяется:
  • личная запись попадает в профиль ИМЕННО этого ключа и не попадает в чужой;
  • домен ложится доменом, сеть — сетью, иначе правило просто не сработает;
  • «через VPN» пишется отдельными полями, а не смешивается с «мимо»;
  • подписка отдаёт профиль того ключа, чей токен спросили;
  • у ключа без личных записей профиль остаётся общим — лишних полей нет.
"""
import asyncio
import base64
import json
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import happ_routing                                # noqa: E402
import handlers_routes as hr                       # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Q:
    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        shown["text"] = text
        shown["buttons"] = [b.callback_data
                            for row in (reply_markup.inline_keyboard
                                        if reply_markup else [])
                            for b in row]

    async def answer(self, *a, **k):
        return None


class Bot:
    def __init__(self):
        self.msgs = []

    async def send_message(self, chat_id=None, text=None, **kw):
        self.msgs.append(text or "")
        shown["text"] = text


class Ctx:
    def __init__(self):
        self.bot = Bot()
        self.user_data = {}


class U:
    callback_query = Q()
    effective_user = type("U", (), {"id": 1})()


class Msg:
    def __init__(self, text):
        self.text = text
        self.chat_id = 1
        self.message_id = 1


class InputUpdate(U):
    def __init__(self, text):
        self.message = Msg(text)


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rt-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Комп','rt-1',TRUE)")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Телефон','rt-2',TRUE)")

    print("=== владелец добавляет своё на один ключ ===")
    ctx = Ctx()
    ctx.user_data["route_uuid"] = "rt-1"
    ctx.user_data["route_dir"] = "direct"
    await hr.handle_route_input(
        InputUpdate("10.50.0.0/16\nvcenter.work.local\nhttps://rdp.work.local/path"),
        ctx)
    rows = await db.list_peer_routes("rt-1")
    values = [r["value"] for r in rows]
    check("записи добавлены", len(rows) == 3, ", ".join(values))
    check("из ссылки взято только имя", "rdp.work.local" in values, str(values))

    prof1 = await happ_routing.profile("rt-1")
    check("сеть легла сетью", "10.50.0.0/16" in prof1["DirectIp"])
    check("домен лёг доменом", "vcenter.work.local" in prof1["DirectSites"],
          "имя, записанное в сети, просто не сработает")

    print()
    print("=== чужой ключ этого не видит ===")
    prof2 = await happ_routing.profile("rt-2")
    check("на телефоне записи нет", "10.50.0.0/16" not in prof2["DirectIp"],
          "это исключение про компьютер, а не про всех")
    check("общий список у него на месте",
          all(n in prof2["DirectIp"] for n in happ_routing.ALWAYS_DIRECT))
    check("лишних полей в чистом профиле нет",
          "ProxySites" not in prof2 and "ProxyIp" not in prof2,
          "профиль читает человек")

    print()
    print("=== «через VPN» — отдельно от «мимо» ===")
    ctx.user_data["route_uuid"] = "rt-1"
    ctx.user_data["route_dir"] = "proxy"
    await hr.handle_route_input(InputUpdate("10.13.13.36/32\nonly-vpn.example"), ctx)
    prof1 = await happ_routing.profile("rt-1")
    check("сеть попала в «через VPN»", "10.13.13.36/32" in prof1.get("ProxyIp", []))
    check("домен тоже", "only-vpn.example" in prof1.get("ProxySites", []))
    check("и не перепутались с «мимо»",
          "10.13.13.36/32" not in prof1["DirectIp"]
          and "only-vpn.example" not in prof1["DirectSites"])

    print()
    print("=== подписка отдаёт профиль именно этого ключа ===")
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'rt-%'")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('rt-1','x-rt1','tok-rt1')")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('rt-2','x-rt2','tok-rt2')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    import subscription as S

    async def headers_for(token):
        resp = await S.handle_sub(type("R", (), {"match_info": {"token": token}})())
        return resp.headers

    h1 = await headers_for("tok-rt1")
    h2 = await headers_for("tok-rt2")
    prof_from = lambda h: json.loads(
        base64.b64decode(h["routing"].split("/")[-1]).decode())
    check("в подписке компа есть его сеть",
          "10.50.0.0/16" in prof_from(h1)["DirectIp"])
    check("в подписке телефона её нет",
          "10.50.0.0/16" not in prof_from(h2)["DirectIp"],
          "иначе личное уехало бы всем")

    print()
    print("=== экран в карточке ключа ===")
    shown.clear()
    await hr.routes_menu(U(), Ctx(), "rt-1")
    check("записи показаны", "10.50.0.0/16" in (shown.get("text") or ""))
    check("видно, что мимо, а что через",
          "Мимо VPN" in (shown.get("text") or "")
          and "Через VPN" in (shown.get("text") or ""))
    check("есть выход к ключу",
          any(b.startswith("user_detail_") for b in shown.get("buttons") or []))

    shown.clear()
    await hr.routes_show(U(), Ctx(), "rt-1")
    check("профиль отдаётся ссылкой кодом",
          "`happ://routing/" in (shown.get("text") or ""))

    rows = await db.list_peer_routes("rt-1")
    await hr.routes_delete(U(), Ctx(), rows[0]["id"], "rt-1")
    check("запись снимается",
          len(await db.list_peer_routes("rt-1")) == len(rows) - 1)

    print()
    print("=== мусор не записывается ===")
    ctx2 = Ctx()
    ctx2.user_data["route_uuid"] = "rt-2"
    ctx2.user_data["route_dir"] = "direct"
    await hr.handle_route_input(InputUpdate("это не адрес и не имя"), ctx2)
    check("ничего не добавлено", not await db.list_peer_routes("rt-2"))
    check("и сказано, что нужно",
          "адрес" in (ctx2.bot.msgs[-1] if ctx2.bot.msgs else ""),
          (ctx2.bot.msgs[-1] if ctx2.bot.msgs else "—")[:40])

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'rt-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rt-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

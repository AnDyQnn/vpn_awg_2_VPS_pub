# -*- coding: utf-8 -*-
"""Каналы одного человека: AmneziaWG и Xray, и переезд между ними.

Главные правила, которые здесь сторожатся:
  • снять AmneziaWG можно только после подключения по Xray — иначе переезд
    оставил бы человека без связи;
  • отозвать Xray у того, у кого нет AmneziaWG, можно только подтвердив —
    это последний канал;
  • чужую подписку по кнопке из карточки ключа не получить.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import handlers_channels as HC                      # noqa: E402
import xui                                          # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-56s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def fake_show(query, context, text, reply_markup=None, **kw):
    shown["text"] = text
    shown["buttons"] = [b.callback_data for row in reply_markup.inline_keyboard
                        for b in row] if reply_markup else []


class Query:
    def __init__(self, uid=1):
        self.from_user = type("U", (), {"id": uid})()
        self.message = type("M", (), {"chat_id": uid})()
        self.alerts = []

    async def answer(self, text="", show_alert=False):
        self.alerts.append(text)


class Upd:
    def __init__(self, uid=1):
        self.callback_query = Query(uid)


class Ctx:
    def __init__(self):
        self.user_data = {}
        self.bot = None


HC.show_screen = fake_show
STATE = {}


async def fake_channels(uuid_val):
    return dict(STATE)


HC.person_channels = fake_channels


async def screen(state):
    STATE.clear()
    STATE.update(state)
    await HC.channels_screen(Upd(), Ctx(), "ch-1")
    return shown["text"], shown["buttons"]


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ch-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Каналов','ch-1',TRUE)")
    base = {"awg": True, "awg_ip": "10.13.13.9", "awg_hs": 0,
            "xray": False, "xray_seen": 0, "xray_first": None}

    print("=== Xray выключен ===")
    os.environ["XRAY_STACK"] = ""
    text, buttons = await screen(base)
    check("сказано, где включить", "Протоколах" in text)
    check("выдать нельзя", not any(b.startswith("ch_xi_") for b in buttons))

    print()
    print("=== Xray включён, у человека только AmneziaWG ===")
    os.environ["XRAY_STACK"] = "xray"
    text, buttons = await screen(base)
    check("можно выдать Xray", "ch_xi_ch-1" in buttons, str(buttons))
    check("снять AmneziaWG нельзя", "ch_ad_ch-1" not in buttons)
    check("есть возврат к человеку", "user_detail_ch-1" in buttons)

    print()
    print("=== Xray выдан, ещё не подключался ===")

    async def url(u):
        return "https://example.ru:2096/sub/abc"
    xui.sub_url = url
    text, buttons = await screen(dict(base, xray=True))
    check("можно прислать и отозвать", "ch_xs_ch-1" in buttons and "ch_xr_ch-1" in buttons)
    check("снять AmneziaWG ещё нельзя", "ch_ad_ch-1" not in buttons)
    check("и сказано почему", "после первого подключения" in text)
    check("адрес подписки на экране", "example.ru:2096" in text)

    print()
    print("=== подключался по Xray ===")
    import time
    text, buttons = await screen(dict(base, xray=True, xray_seen=int(time.time()) - 30))
    check("теперь можно снять AmneziaWG", "ch_ad_ch-1" in buttons, str(buttons))
    check("и видно, что на связи", "на связи" in text)

    print()
    print("=== AmneziaWG снят ===")
    text, buttons = await screen(dict(base, awg=False, awg_ip=None, xray=True,
                                      xray_seen=int(time.time()) - 30))
    check("можно вернуть AmneziaWG", "ch_ar_ch-1" in buttons)
    check("в блоке сказано, что снят", "снят" in text)

    print()
    print("=== отзыв последнего канала — с подтверждением ===")
    ctx = Ctx()
    revoked = []

    async def fake_revoke(u):
        revoked.append(u)
        return True
    xui.revoke = fake_revoke
    STATE.clear()
    STATE.update(dict(base, awg=False, xray=True))
    await HC.revoke_xray(Upd(), ctx, "ch-1")
    check("сначала спрашивает", not revoked and "без" in shown["text"], shown["text"][:60])
    await HC.revoke_xray(Upd(), ctx, "ch-1")
    check("по второму нажатию отзывает", revoked == ["ch-1"])

    print()
    print("=== снять AmneziaWG без подключения по Xray — нельзя ===")
    STATE.clear()
    STATE.update(dict(base, xray=True))
    upd = Upd()
    await HC.drop_awg(upd, Ctx(), "ch-1")
    check("отказ с объяснением", any("подключиться по Xray" in a
                                      for a in upd.callback_query.alerts),
          str(upd.callback_query.alerts))

    print()
    print("=== чужую подписку не получить ===")
    upd = Upd(uid=777)
    await HC.client_xray(upd, Ctx(), "ch-1")
    check("чужому — отказ", "Ключ не найден" in upd.callback_query.alerts,
          str(upd.callback_query.alerts))

    await db.execute("DELETE FROM users WHERE uuid LIKE 'ch-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

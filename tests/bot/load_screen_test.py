# -*- coding: utf-8 -*-
"""«Нагрузка за сутки»: одна карточка на ключ, снятие ключом и всех сразу."""
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.append("/app")
from database import db                      # noqa: E402
import handlers_service as hs                # noqa: E402

FAIL = []


def check(cond, what):
    print(("  ок   " if cond else "  ПЛОХО ") + what)
    if not cond:
        FAIL.append(what)


class Msg:
    message_id = 1
    chat_id = 1
    photo = None
    document = None


class Query:
    def __init__(self):
        self.message = Msg()
        self.text, self.kb, self.alerts = None, None, []

    async def answer(self, text=None, **kw):
        self.alerts.append(text)

    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        self.text, self.kb = text, reply_markup


class Upd:
    def __init__(self):
        self.callback_query = Query()


class Ctx:
    user_data = {}


def buttons(q):
    return [(b.text, b.callback_data) for row in q.kb.inline_keyboard for b in row]


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ls-%'")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('ls-Торрент','ls-1'), ('ls-Видео','ls-2')")
    now = datetime.utcnow()
    for i, pps in enumerate((9000, 7000, 6500, 6200)):     # четыре раза — один ключ
        await db.execute("INSERT INTO pps_events (user_uuid, started_at, ended_at, peak_pps, "
                         "avg_packet_size, upload_share) VALUES ('ls-1',$1,$2,$3,900,0.8)",
                         now - timedelta(hours=i + 1), now - timedelta(hours=i + 1, minutes=-5), pps)
    await db.execute("INSERT INTO pps_events (user_uuid, started_at, ended_at, peak_pps, "
                     "avg_packet_size, upload_share) VALUES ('ls-2',$1,$1,5600,1300,0.05)", now)
    try:
        print("=== экран")
        u = Upd()
        await hs.load_screen(u, Ctx())
        t, b = u.callback_query.text, buttons(u.callback_query)
        check(t.count("ls-Торрент") == 1, "ключ с четырьмя превышениями — одна карточка")
        check("4 раза" in t, "у карточки счётчик «4 раза»")
        check("и ещё 1" in t, "сверх трёх случаев — числом")
        check(t.index("ls-Торрент") < t.index("ls-Видео"), "ключи — по самому сильному пику")
        dels = [x for x in b if x[1].startswith("svc_ev_delu_ls-")]
        check(len(dels) == 2, f"кнопка «Снять» — одна на ключ ({len(dels)})")
        check(any(x[1] == "svc_ev_delall" for x in b), "есть «Снять все за сутки»")
        check(not any(x[1].startswith("svc_ev_del_") for x in b), "кнопок на каждое событие нет")

        print("=== снять ключ")
        u = Upd()
        await hs.events_delete_user(u, Ctx(), "ls-1")
        left1 = await db.fetch_val("SELECT COUNT(*) FROM pps_events WHERE user_uuid='ls-1'")
        left2 = await db.fetch_val("SELECT COUNT(*) FROM pps_events WHERE user_uuid='ls-2'")
        check(left1 == 0 and left2 == 1, "сняты все четыре у ключа, чужое осталось")
        check(u.callback_query.alerts[-1] == "Снято: 4", "ответ «Снято: 4»")

        print("=== снять все")
        u = Upd()
        await hs.events_delete_all_confirm(u, Ctx())
        check("Снять все" in u.callback_query.text and
              any(x[1] == "svc_ev_delall_do" for x in buttons(u.callback_query)),
              "сначала спрашивает подтверждение")
        await hs.events_delete_all(Upd(), Ctx())
        n = await db.fetch_val("SELECT COUNT(*) FROM pps_events WHERE user_uuid LIKE 'ls-%'")
        check(n == 0, "после подтверждения список пуст")
    finally:
        await db.execute("DELETE FROM users WHERE uuid LIKE 'ls-%'")
    print("\nВСЁ ПРОШЛО" if not FAIL else f"\nПРОВАЛЫ: {FAIL}")


asyncio.run(main())

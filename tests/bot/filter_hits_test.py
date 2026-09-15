# -*- coding: utf-8 -*-
"""Попытки на закрытое: факт с узла становится разбираемой заявкой.

Фильтр молчит по определению: домен не открылся — и всё. Владелец узнавал об
этом только от самого человека, а тот, кто ходит на закрытое, приходит
последним.

Проверяется то, ради чего заведено:
  • адрес в туннеле превращается в имя и ключ — по адресу расследовать нечего;
  • внешний адрес записывается тот, что известен сейчас: он меняется;
  • повторный забор не плодит копий — узел отдаёт историю целиком;
  • заявку можно открыть и отметить разобранной, и счётчик это видит.
"""
import asyncio
import sys
from datetime import datetime

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import handlers_hits as hh                         # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


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


class Ctx:
    user_data = {}


async def main():
    await db.connect()
    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'hit-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'hh-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Димон','hh-1',TRUE)")
    await db.execute("DELETE FROM user_ips WHERE uuid LIKE 'hh-%'")
    await db.track_user_ip("hh-1", "203.0.113.77")

    node = [{"ts": 1757930000, "ip": "10.13.13.17",
             "domain": "hit-adult.example", "category": "adult"}]

    async def fake_map():
        return {"hh-1": ["10.13.13.17"]}

    class Resp:
        status = 200

        async def json(self):
            return {"hits": node}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class Session:
        def get(self, url, params=None, timeout=None):
            return Resp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    import filters
    filters.peer_addr_map = fake_map
    hh.api_session = lambda **kw: Session()

    print("=== факт с узла становится заявкой ===")
    added = await hh.collect_hits()
    check("запись принята", added == 1, str(added))
    rows = await db.list_filter_hits(limit=5)
    row = rows[0] if rows else {}
    check("адрес превратился в человека", row.get("name") == "Димон",
          str(row.get("name")))
    check("ключ записан", row.get("user_uuid") == "hh-1")
    check("адрес в туннеле сохранён", row.get("tunnel_ip") == "10.13.13.17")
    check("внешний адрес записан", row.get("public_ip") == "203.0.113.77",
          "через неделю искать его будет негде")
    check("домен и причина на месте",
          row.get("domain") == "hit-adult.example" and row.get("category") == "adult")

    print()
    print("=== повторный забор ничего не дублирует ===")
    before = await db.count_filter_hits()
    await hh.collect_hits()
    check("записей столько же", await db.count_filter_hits() == before,
          "узел отдаёт историю целиком")

    print()
    print("=== разбор ===")
    check("считается неразобранной", await db.count_filter_hits(only_new=True) >= 1)
    shown.clear()
    await hh.hits_screen(U(), Ctx())
    check("в списке видно имя", "Димон" in (shown.get("text") or ""))
    check("заявку можно открыть",
          any(b.startswith("hit_open_") for b in shown.get("buttons") or []))

    hit_id = rows[0]["id"]
    shown.clear()
    await hh.hit_open(U(), Ctx(), hit_id)
    text = shown.get("text") or ""
    for what, piece in (("время", "МСК"), ("имя", "Димон"),
                        ("домен", "hit-adult.example"),
                        ("адрес в туннеле", "10.13.13.17"),
                        ("внешний адрес", "203.0.113.77")):
        check("в заявке есть %s" % what, piece in text)
    check("из заявки можно уйти к ключу",
          any("user_detail_" in b for b in shown.get("buttons") or []))

    fresh = await db.count_filter_hits(only_new=True)
    check("открытая заявка перестала быть новой",
          fresh == 0 or fresh < before, "было %d, стало %d" % (before, fresh))

    print()
    print("=== поиск по номеру со страницы ===")
    # Номер затем и показан человеку, чтобы он прислал его. Искать по нему
    # владелец должен уметь, а не листать список глазами.
    await db.execute("UPDATE filter_hits SET ref='9395-570A' WHERE id=$1", hit_id)
    found = await db.find_filter_hit("9395-570A")
    check("находится как есть", found and found["id"] == hit_id)
    check("регистр не важен",
          (await db.find_filter_hit("9395-570a") or {}).get("id") == hit_id,
          "человек переписывает номер как получится")
    check("дефис не важен",
          (await db.find_filter_hit("9395570A") or {}).get("id") == hit_id)
    check("чужого номера нет", await db.find_filter_hit("0000-0000") is None)
    check("пустой запрос ничего не находит", await db.find_filter_hit("") is None,
          "иначе вернулся бы случайный инцидент")

    said = []

    class B2:
        async def send_message(self, chat_id=None, text=None, **kw):
            said.append(text or "")

    class C2:
        bot = B2()
        user_data = {}

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat_id = 1

    class U2:
        def __init__(self, text):
            self.message = Msg(text)
        effective_user = type("U", (), {"id": 1})()

    ctx2 = C2()
    await hh.hit_find_entered(U2("9395-570a"), ctx2)
    check("экран открылся по номеру", any("Инцидент" in s for s in said),
          (said[-1][:40] if said else "—"))
    check("в нём тот самый домен",
          any("hit-adult.example" in s for s in said))

    said.clear()
    await hh.hit_find_entered(U2("0000-0000"), ctx2)
    check("по чужому номеру честный ответ",
          any("Ничего не нашлось" in s for s in said),
          (said[-1][:40] if said else "—"))

    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'hit-%'")
    await db.execute("DELETE FROM user_ips WHERE uuid LIKE 'hh-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'hh-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

# -*- coding: utf-8 -*-
"""Свой пул фильтров: присланный список становится категорией.

Готовые категории собраны чужими людьми по чужим соображениям. Пул — это
категория владельца: он кидает список, даёт название, и дальше пул ведёт себя
как встроенная.

Проверяется то, ради чего заведено:
  • список разбирается как есть — строками, через запятую, в формате hosts;
  • пул появляется среди категорий и включается человеку;
  • домены уезжают на узел, где лягут в тот же кэш, что и встроенные;
  • удалили пул — он снялся у людей, а не остался висеть категорией-призраком.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import filters as F                                # noqa: E402

ok = True
sent = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Msg:
    def __init__(self, text):
        self.text = text
        self.chat_id = 1
        self.message_id = 1


class Upd:
    def __init__(self, text):
        self.message = Msg(text)


class Bot:
    def __init__(self):
        self.said = []

    async def send_message(self, chat_id=None, text=None, **kw):
        self.said.append(text or "")


class Ctx:
    def __init__(self):
        self.bot = Bot()
        self.user_data = {}


class Resp:
    status = 200

    async def json(self):
        return {"filtered": 0}

    async def text(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class Session:
    def post(self, url, json=None, timeout=None):
        sent.clear()
        sent.update(json or {})
        return Resp()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    await db.connect()
    await db.execute("DELETE FROM filter_pools WHERE title LIKE 'Проверка%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'pl-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Пулов','pl-1',TRUE)")

    async def fake_map():
        return {"pl-1": ["10.13.13.30"]}
    F.peer_addr_map = fake_map
    F.api_session = lambda **kw: Session()

    print("=== список разбирается в любом виде ===")
    parsed = F._parse_domains(
        "pornhub.com\n0.0.0.0 xvideos.com\nhttps://example.org/path\n"
        "  DUP.com , dup.com\n# комментарий\nне домен вовсе\n127.0.0.1 ads.test")
    check("домен как есть", "pornhub.com" in parsed)
    check("формат hosts понят", "xvideos.com" in parsed and "ads.test" in parsed)
    check("из ссылки взято имя", "example.org" in parsed)
    check("повторы схлопнуты", parsed.count("dup.com") == 1, str(parsed))
    check("мусор отброшен", "не домен вовсе" not in parsed, str(parsed))

    print()
    print("=== адреса приводятся к имени домена ===")
    mixed = F._parse_domains(
        "https://www.example.com/page\nwww.example.com\nexample.com\n"
        "http://site.ru:8080/x?a=1")
    check("схема, www, порт и путь срезаны",
          mixed == ["example.com", "site.ru"], str(mixed))

    print()
    print("=== создание группы: сначала имя ===")
    ctx = Ctx()
    await F.pool_title_entered(Upd("Проверка взрослое"), ctx)
    check("группа заведена сразу", ctx.user_data.get("pool_key") is not None)
    check("и сразу просят адреса",
          ctx.user_data.get("state") == "awaiting_pool_domains",
          "имя короткое, его и спрашиваем первым")
    await F.pool_domains_entered(Upd("pornhub.com\nxvideos.com"), ctx)

    pools = await db.list_filter_pools()
    pool = next((p for p in pools if p["title"] == "Проверка взрослое"), None)
    check("пул записан", pool is not None)
    check("домены на месте", pool and len(pool["domains"]) == 2, str(pool))
    check("ключ годится для имени файла на узле",
          pool and all(c.isalnum() or c in "-_" for c in pool["key"]),
          pool["key"] if pool else "—")

    print()
    print("=== пул ведёт себя как категория ===")
    cats = dict(await F.all_categories())
    check("есть среди категорий", pool["key"] in cats, str(list(cats)[-3:]))
    check("под своим названием", cats.get(pool["key"]) == "Проверка взрослое")

    await db.set_user_filter("pl-1", pool["key"], True)
    await F.apply_filters("проверка")
    check("домены уехали на узел",
          sorted((sent.get("pools") or {}).get(pool["key"], [])) ==
          ["pornhub.com", "xvideos.com"], str(sent.get("pools")))
    check("человек под этой категорией",
          (sent.get("clients") or {}).get("10.13.13.30") == [pool["key"]],
          str(sent.get("clients")))

    print()
    print("=== группу можно запретить всем ===")
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

    await F.common_screen(U(), Ctx())
    check("группа есть в общих правилах",
          ("flt_ctog_" + pool["key"]) in (shown.get("buttons") or []),
          "иначе её не найти там, где она нужнее всего")

    print()
    print("=== дописывание ===")
    ctx2 = Ctx()
    ctx2.user_data["pool_key"] = pool["key"]
    await F.pool_domains_entered(Upd("redtube.com\npornhub.com"), ctx2)
    again = await db.get_filter_pool(pool["key"])
    check("новый домен добавлен", "redtube.com" in again["domains"])
    check("повтор не задвоился", again["domains"].count("pornhub.com") == 1,
          str(again["domains"]))

    print()
    print("=== удаление ===")
    await db.delete_filter_pool(pool["key"])
    left = await db.get_user_filters("pl-1")
    check("пула нет", await db.get_filter_pool(pool["key"]) is None)
    check("и у человека он снялся", pool["key"] not in left,
          "иначе осталась бы категория, которой не существует")

    await db.execute("DELETE FROM filter_pools WHERE title LIKE 'Проверка%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'pl-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

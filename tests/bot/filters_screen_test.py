# -*- coding: utf-8 -*-
"""Экран фильтров говорит о деле, а не о размере списков.

Владелец: «Загружено доменов: Для взрослых — 953393 — зачем вот это, это же
мусорная инфа и почему только для взрослых, а остальные что?»

Обе претензии верные. Число доменов в списке — знание, с которым ничего не
сделаешь. А одна категория из многих показывалась потому, что узел держит
списки только тех категорий, которые кому-то включены; экран об этом не
говорил, и выглядело как поломка остальных.

При этом рядом есть вопрос, на который ответить стоит: не оказалась ли
категория включённой БЕЗ списка. Вот это настоящая поломка — запрет стоит, а
закрывать нечем, и человек спокойно ходит куда хотел.

Оговорка про DNS-over-HTTPS честная, но висела всегда, в том числе когда
фильтры не включены никому и обходить нечего.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import filters as F                                # noqa: E402

ok = True
shown = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Q:
    def __init__(self):
        self.data = ""
        self.message = type("M", (), {"chat_id": 1, "message_id": 1})()
        self.from_user = type("U", (), {"id": 1, "username": "admin"})()

    async def answer(self, *a, **k):
        return None


class Upd:
    def __init__(self):
        self.callback_query = Q()
        self.effective_chat = type("C", (), {"id": 1})()
        self.effective_user = type("U", (), {"id": 1, "username": "admin"})()


class Ctx:
    def __init__(self):
        self.user_data = {}


async def fake_screen(query, context, text, **k):
    shown.append(text)


async def render(sizes):
    shown.clear()
    F.list_sizes = lambda: _val(sizes)
    await F.filters_menu(Upd(), Ctx())
    return shown[-1] if shown else ""


async def _val(v):
    return v


async def main():
    await db.connect()
    F.show_screen = fake_screen

    # Стенд: категория «для взрослых» включена всем, как на живом узле.
    await db.set_common_filters(["adult"])

    print("=== счётчика доменов больше нет ===")
    text = await render({"adult": 953393})
    check("числа доменов не показываем", "953393" not in text,
          "с этим числом владелец ничего не делает")
    check("и слова «загружено доменов» тоже нет",
          "Загружено доменов" not in text)

    print()
    print("=== зато видно, когда запрет пустой ===")
    text = await render({})
    check("сказано, что список не загрузился",
          "не загрузились" in text.lower(), "запрет есть, закрывать нечем")
    check("названа категория", "зрослых" in text or "adult" in text)
    check("сказано, что делать", "Применить на узле" in text)

    text = await render({"adult": 953393})
    check("когда список есть — тревоги нет",
          "не загрузились" not in text.lower())

    print()
    print("=== оговорка про DoH — по делу ===")
    check("при включённом фильтре сказана",
          "DNS-over-HTTPS" in text)
    await db.set_common_filters([])
    text = await render({})
    check("когда фильтры никому не включены — молчит",
          "DNS-over-HTTPS" not in text,
          "обходить нечего, а место занимает")

    await db.set_common_filters([])


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

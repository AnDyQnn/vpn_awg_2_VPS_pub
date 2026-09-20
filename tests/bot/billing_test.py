# -*- coding: utf-8 -*-
"""Счета за сервера: суммы, даты и напоминание.

Сервера оплачиваются раз в квартал, и забыть про платёж — значит однажды
обнаружить выключенный узел и тридцать человек без связи. Значит проверять надо
не «экран открывается», а арифметику: сумму к оплате, следующую дату и то, что
напоминание приходит один раз, а не двадцать.

Две вещи, на которых такие штуки обычно и ломаются:

  • Сумма. Человек держит в голове тариф («двести в месяц»), а платит за
    квартал. Показать надо то, что спишут, — иначе он сверит с банком и решит,
    что бот врёт.

  • Дата. Считать «сегодня плюс период» нельзя: платят за несколько дней до
    срока, и график каждый раз уползал бы назад. За год набегает месяц.
"""
import asyncio
import sys
from datetime import date, timedelta

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import billing                                     # noqa: E402

ok = True
sent = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Bot:
    async def send_message(self, chat_id=None, text="", **k):
        sent.append((chat_id, text))


class App:
    bot = Bot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM billing_services WHERE name LIKE 'тест-%'")

    print("=== сумма к оплате считается за период, а не за месяц ===")
    s = {"monthly": 200, "period_months": 3}
    check("двести в месяц по кварталам = 600", billing.amount(s) == 600,
          "показываем то, что спишут, иначе человек сверит с банком")
    check("ежемесячный тариф не умножается",
          billing.amount({"monthly": 350, "period_months": 1}) == 350)
    check("копейки не выдумываем", billing.money(600) == "600 ₽",
          billing.money(600))
    check("а если они есть — показываем", billing.money(99.5) == "99.50 ₽",
          billing.money(99.5))

    print()
    print("=== следующая дата считается от прежней ===")
    d = date(2026, 10, 15)
    check("квартал вперёд", billing.next_due(d, 3) == date(2027, 1, 15))
    check("год вперёд", billing.next_due(d, 12) == date(2027, 10, 15))
    check("через декабрь не спотыкаемся",
          billing.next_due(date(2026, 11, 20), 3) == date(2027, 2, 20))
    # 31 января плюс месяц — такого дня в феврале нет.
    check("31-го в коротком месяце берём последний день",
          billing.next_due(date(2026, 1, 31), 1) == date(2026, 2, 28),
          str(billing.next_due(date(2026, 1, 31), 1)))

    print()
    print("=== разбор строки добавления ===")
    good = billing.parse_add("Хостинг РФ; 200; 3; 15.10.2026; https://e.ru/b")
    check("разобрано", isinstance(good, dict), str(good)[:50])
    check("имя", good["name"] == "Хостинг РФ")
    check("цена", good["monthly"] == 200)
    check("период", good["period_months"] == 3)
    check("дата", good["due_date"] == date(2026, 10, 15))
    check("ссылка", good["url"] == "https://e.ru/b")
    check("без ссылки тоже можно",
          isinstance(billing.parse_add("Домен; 15; 12; 20.09.2027"), dict))
    for bad in ("", "только имя", "Имя; сто; 3; 15.10.2026",
                "Имя; 200; 0; 15.10.2026", "Имя; 200; 3; вчера"):
        if not isinstance(billing.parse_add(bad), str):
            check("мусор отвергается: %r" % bad, False, "принял")
            break
    else:
        check("мусор отвергается со словами", True,
              "человек должен понять, что именно не так")

    print()
    print("=== напоминание: текст как договаривались ===")
    soon = date.today() + timedelta(days=3)
    await db.billing_add("тест-хостинг", "https://h.example/pay", 200, 3, soon, 5)
    await db.billing_add("тест-домен", "", 700, 12, soon, 5)
    due = await db.billing_due()
    mine = [s for s in due if s["name"].startswith("тест-")]
    check("оба попали в напоминание", len(mine) == 2, "нашлось %d" % len(mine))
    text = billing.due_text(mine)
    check("сказано, до какого числа", soon.strftime("%d.%m") in text, text[:60])
    check("сумма первого посчитана за период", "600 ₽" in text)
    check("сумма второго тоже", "8400 ₽" in text)
    check("есть итог", "Всего" in text)
    check("ссылка подставлена", "https://h.example/pay" in text)

    print()
    print("=== напоминают один раз в сутки, а не двадцать ===")
    sent.clear()
    billing.ADMIN_ID = 777
    for s in mine:
        await db.set_setting("billing_notified_%d" % s["id"], "")
    n1 = await billing.check_and_notify(App())
    check("первый раз пришло", n1 == 2 and len(sent) == 1, "отправлено %d" % len(sent))
    n2 = await billing.check_and_notify(App())
    check("второй раз молчим", n2 == 0 and len(sent) == 1,
          "иначе за неделю до срока владелец получит двадцать одинаковых")

    print()
    print("=== далёкий платёж не тревожит ===")
    far = date.today() + timedelta(days=60)
    await db.billing_add("тест-далёкий", "", 100, 1, far, 5)
    due2 = [s["name"] for s in await db.billing_due()]
    check("до срока ещё далеко — молчим", "тест-далёкий" not in due2,
          ", ".join(due2)[:60])

    await db.execute("DELETE FROM billing_services WHERE name LIKE 'тест-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

# -*- coding: utf-8 -*-
"""Изменённый профиль маршрутизации доезжает до приложения.

Владелец обновил подписку пять раз подряд. Каждый раз приложение честно
отвечало «3 servers imported/updated». И каждый раз профиль маршрутизации
оставался прежним — тем, что он получил часом раньше, вместе с правилом,
которое ломало ему интернет.

Причина в документации приложения: профиль с тем же именем обновляется только
если пришедшая в `LastUpdated` дата НОВЕЕ сохранённой. Мы этого поля не
отправляли вовсе — значит новее не было никогда, и профиль у человека застывал
на дне первой выдачи. Чинить что-либо в правилах было бессмысленно: починка не
доезжала.

Но и ставить «сейчас» на каждую отдачу нельзя: увидев дату новее, приложение
принудительно перекачивает гео-файлы, а это двадцать шесть мегабайт. Подписка
обновляется раз в два часа у каждого.

Поэтому дата привязана к содержимому.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import happ_routing as H                           # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    await db.set_setting("happ_profile_all", "")

    print("=== дата вообще есть ===")
    prof = await H.profile()
    stamp = prof.get("LastUpdated")
    check("поле на месте", stamp is not None,
          "без него приложение не обновит профиль никогда")
    check("это число, а не строка", isinstance(stamp, int), repr(stamp))
    check("похоже на время", stamp > 1600000000, str(stamp))

    print()
    print("=== ничего не менялось — дата стоит ===")
    again = (await H.profile()).get("LastUpdated")
    check("та же самая", again == stamp,
          "иначе приложение каждые два часа качало бы 26 Мб гео-файлов")
    third = (await H.profile()).get("LastUpdated")
    check("и на третий раз тоже", third == stamp)

    print()
    print("=== содержимое изменилось — дата ушла вперёд ===")
    # Добавляем исключение: ровно то, ради чего профиль и переезжает к людям.
    await db.execute("DELETE FROM bypass_exclusions WHERE domain='ru-test.example'")
    await db.execute(
        "INSERT INTO bypass_exclusions (domain, cidrs, note, source) "
        "VALUES ('ru-test.example', '', 'проверка', 'manual')")
    changed = await H.profile()
    check("исключение попало в профиль",
          "ru-test.example" in changed["DirectSites"])
    check("дата стала новее", changed["LastUpdated"] > stamp,
          "было %s, стало %s" % (stamp, changed["LastUpdated"]))

    print()
    print("=== и снова замерла ===")
    still = (await H.profile()).get("LastUpdated")
    check("не растёт сама по себе", still == changed["LastUpdated"])

    print()
    print("=== у разных ключей свои даты ===")
    s_all = (await H.profile()).get("LastUpdated")
    s_one = (await H.profile("ru-test-uuid")).get("LastUpdated")
    check("персональный профиль тоже с датой", isinstance(s_one, int))
    check("считаются отдельно",
          (await db.get_setting("happ_profile_ru-test-uuid")) not in (None, ""),
          "иначе личные записи ключа не доехали бы")
    check("общий профиль от этого не сдвинулся",
          (await H.profile()).get("LastUpdated") == s_all)

    await db.execute("DELETE FROM bypass_exclusions WHERE domain='ru-test.example'")
    await db.set_setting("happ_profile_all", "")
    await db.set_setting("happ_profile_ru-test-uuid", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

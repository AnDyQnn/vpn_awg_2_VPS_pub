# -*- coding: utf-8 -*-
"""Правило указывает на человека и переживает смену его адреса.

Владелец сказал прямо: параметров хватает, перевыпуск — это перевыпуск, а не
удаление и создание. Он прав, и вот вторая половина того же.

«Открыть доступ к Пете» записывалось как `10.13.13.7/32`. Адрес живёт до
первого перевыпуска: старый пир держит его, пока не снимется, а новый получает
следующий свободный. После этого правило продолжает означать прежние цифры —
то есть уже чужую машину. На боевом узле было одиннадцать таких правил и ни
одного устойчивого.

Теперь записывается сам человек, а адрес подставляется в момент раскладки —
ровно как у имён в туннеле.

Проверяется:
  • правило записывается на человека, а не на цифры;
  • при раскладке подставляется его сегодняшний адрес;
  • адрес сменился — правило означает того же человека, а не прежние цифры;
  • человек без адреса не превращается в «открыть неизвестно что»;
  • имя человека не попадает в колонку имён туннеля — там его искал бы DNS.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import acl                                         # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


ADDRESSES = {}


async def fake_ip_map():
    return dict(ADDRESSES)


async def main():
    await db.connect()
    acl.peer_ip_map = fake_ip_map
    await db.execute("DELETE FROM users WHERE uuid LIKE 'gp-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ЦЕЛЬ-%'")

    for uuid_val, name in (("gp-petya", "Петя"), ("gp-vasya", "Вася")):
        await db.execute(
            "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
            name, uuid_val)

    role = await db.create_role("ЦЕЛЬ-к-Пете")
    await db.add_role_grant(role, None, "any", None, note="Петя",
                            target_uuid="gp-petya")
    await db.add_user_role("gp-vasya", role)

    print("=== правило записано на человека, а не на цифры ===")
    rows = await db.fetch_all(
        "SELECT cidr, name, note, target_uuid FROM role_grants "
        "WHERE target_uuid='gp-petya'")
    check("правило одно", len(rows) == 1)
    g = rows[0]
    check("адреса в нём нет", not g["cidr"], g["cidr"])
    check("человек записан", g["target_uuid"] == "gp-petya")
    check("имя человека в подписи", g["note"] == "Петя")
    check("колонка имён туннеля пуста", not g["name"],
          "иначе DNS пошёл бы искать человека по имени")

    print()
    print("=== при раскладке подставляется сегодняшний адрес ===")
    ADDRESSES.clear()
    ADDRESSES.update({"gp-petya": "10.13.13.7", "gp-vasya": "10.13.13.8"})
    m = await db.get_access_matrix()
    allow, unresolved = await acl.resolve_grants(m["gp-vasya"]["allow"])
    check("подставился адрес Пети",
          any(x["cidr"] == "10.13.13.7/32" for x in allow),
          ", ".join(x.get("cidr") or "-" for x in allow))
    check("непонятых нет", not unresolved, unresolved)

    print()
    print("=== Петя перевыпустил ключ, адрес сменился ===")
    ADDRESSES["gp-petya"] = "10.13.13.42"
    allow2, _ = await acl.resolve_grants(m["gp-vasya"]["allow"])
    check("правило поехало за человеком",
          any(x["cidr"] == "10.13.13.42/32" for x in allow2),
          ", ".join(x.get("cidr") or "-" for x in allow2))
    check("прежних цифр не осталось",
          not any(x["cidr"] == "10.13.13.7/32" for x in allow2),
          "иначе Вася ходил бы к чужой машине")

    print()
    print("=== человек без адреса не открывает «неизвестно что» ===")
    del ADDRESSES["gp-petya"]
    allow3, unresolved3 = await acl.resolve_grants(m["gp-vasya"]["allow"])
    check("правило пропущено", not allow3, allow3)
    check("и о нём сказано", bool(unresolved3), unresolved3)

    print()
    print("=== подпись на экране — человеческая ===")
    text = acl.grant_text({"target_uuid": "gp-petya", "note": "Петя",
                           "proto": "any"})
    check("видно имя, а не uuid", text == "Петя", text)

    await db.execute("DELETE FROM users WHERE uuid LIKE 'gp-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ЦЕЛЬ-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

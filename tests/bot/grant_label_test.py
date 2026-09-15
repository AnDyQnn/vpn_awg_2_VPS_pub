# -*- coding: utf-8 -*-
"""Разрешение подписано тем, чем оно является.

Правило «доступ к человеку» хранит его uuid, а подпись берётся из заметки. Но
выборка разрешений это поле не читала — и такое правило не опознавалось: имени
нет, адреса нет, значит «?». Владелец выдавал доступ, видел в списке «?» и не
мог понять, что это вообще.

Второе: имена внутри туннеля заводятся позже правил. Когда у адреса появляется
имя, правило должно начать называть его — иначе в списке цифры, и каждый раз
приходится вспоминать, чьи они.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
from acl import grant_text                         # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    await db.execute("DELETE FROM roles WHERE name LIKE 'Проверка%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'gl-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Работяга','gl-1',TRUE)")

    role_id = await db.create_role("Проверка доступов")

    print("=== правило на человека ===")
    await db.add_role_grant(role_id, note="work2", target_uuid="gl-1")
    grants = await db.get_role_grants(role_id)
    person = grants[-1]
    check("поле target_uuid доехало до экрана",
          person.get("target_uuid") == "gl-1",
          "без него правило и превращалось в «?»")
    check("подписано заметкой", grant_text(person) == "work2",
          grant_text(person))

    print()
    print("=== правило на адрес ===")
    await db.add_role_grant(role_id, cidr="10.13.13.30/32")
    net = (await db.get_role_grants(role_id))[-1]
    check("без имени показан адрес", grant_text(net) == "10.13.13.30/32",
          grant_text(net))

    names = {"10.13.13.30": "склад.vpn"}
    labelled = grant_text(net, names)
    check("с именем показано имя", "склад.vpn" in labelled, labelled)
    check("адрес рядом остался", "10.13.13.30" in labelled,
          "правило должно оставаться проверяемым")

    print()
    print("=== порт и протокол не теряются ===")
    await db.add_role_grant(role_id, cidr="10.13.13.31/32", proto="tcp", port=443)
    tcp = (await db.get_role_grants(role_id))[-1]
    check("протокол и порт на месте",
          grant_text(tcp, {"10.13.13.31": "касса.vpn"}) ==
          "касса.vpn (10.13.13.31/32) · tcp 443",
          grant_text(tcp, {"10.13.13.31": "касса.vpn"}))

    print()
    print("=== мёртвое правило видно ===")
    from acl import grant_is_dead
    # Такое лежит на живом узле: у выходного узла маршрут по умолчанию
    # 0.0.0.0/0, и когда-то отсюда брался «адрес пира».
    await db.add_role_grant(role_id, cidr="0.0.0.0/32", note="DE_AGENT")
    dead = (await db.get_role_grants(role_id))[-1]
    check("опознано как мёртвое", grant_is_dead(dead))
    check("и помечено в подписи", "не работает" in grant_text(dead),
          grant_text(dead))
    check("живое правило не помечено",
          not grant_is_dead(net) and "не работает" not in grant_text(net))
    check("правило на человека тоже живое", not grant_is_dead(person))

    print()
    print("=== испорченное правило видно ===")
    broken = {"kind": "net", "name": None, "cidr": None, "proto": "any",
              "port": None, "note": None, "target_uuid": None}
    check("не «?», а объяснение", "без цели" in grant_text(broken),
          grant_text(broken))

    await db.execute("DELETE FROM roles WHERE name LIKE 'Проверка%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'gl-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

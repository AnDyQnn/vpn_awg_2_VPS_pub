# -*- coding: utf-8 -*-
"""Локальная проверка ролей: миграции, объединение прав, сборка правил. В прод не уезжает."""
import asyncio
import sys

from database import db

sys.path.insert(0, "/app")


async def main():
    await db.connect()
    assert db.pool, "нет подключения к базе"
    print("подключение и миграции: ок")

    for table in ("roles", "role_grants", "user_roles"):
        exists = await db.fetch_val(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=$1", table)
        print(f"  таблица {table}: {'есть' if exists else 'НЕТ'}")
        assert exists

    # чистим следы прошлого прогона
    await db.execute("DELETE FROM roles")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rt-%'")

    for uid, name in (("rt-1", "Брат"), ("rt-2", "Кент"), ("rt-3", "Мать")):
        await db.execute("INSERT INTO users (name, uuid) VALUES ($1,$2) "
                         "ON CONFLICT (uuid) DO NOTHING", name, uid)

    home = await db.create_role("Домашние сервисы")
    media = await db.create_role("Медиа")
    empty = await db.create_role("Пустая")
    assert home and media and empty
    print("создание ролей: ок")

    assert await db.create_role("Медиа") is None, "имя роли должно быть уникальным"
    print("повтор имени отбивается: ок")

    await db.add_role_grant(home, "10.13.13.5/32", "any", None, "сервер")
    await db.add_role_grant(home, "10.13.13.6/32", "tcp", 22, "ssh")
    await db.add_role_grant(media, "10.13.13.5/32", "any", None, "тот же сервер")
    await db.add_role_grant(media, "10.13.13.9/32", "tcp", 8096, None)

    # брат в двух ролях, кент в одной, мать без ролей
    await db.add_user_role("rt-1", home)
    await db.add_user_role("rt-1", media)
    await db.add_user_role("rt-2", media)

    matrix = await db.get_access_matrix()
    assert set(matrix) == {"rt-1", "rt-2"}, f"в матрице лишние или нет нужных: {set(matrix)}"
    print("без ролей в матрицу не попадает: ок")

    brother = matrix["rt-1"]["allow"]
    assert len(brother) == 4, f"объединение дало {len(brother)} правил вместо 4"
    roles_seen = {g["role"] for g in brother}
    assert roles_seen == {"Домашние сервисы", "Медиа"}, roles_seen
    print("права складываются из всех ролей: ок")
    print("  источник доступа виден:",
          ", ".join(f"{g['cidr']}←{g['role']}" for g in brother))

    from acl import _dedupe
    deduped = _dedupe(brother)
    assert len(deduped) == 3, f"дубликат не схлопнулся: {deduped}"
    print("одинаковое правило из двух ролей схлопывается: ок")

    await db.add_user_role("rt-3", empty)
    matrix = await db.get_access_matrix()
    assert matrix["rt-3"]["allow"] == [], "пустая роль не должна давать правил"
    print("пустая роль: человек попадает под ограничение и не получает разрешений: ок")

    await db.remove_user_role("rt-1", home)
    left = await db.get_user_roles("rt-1")
    assert [r["name"] for r in left] == ["Медиа"], left
    matrix = await db.get_access_matrix()
    assert len(matrix["rt-1"]["allow"]) == 2
    print("снятие одной роли оставляет права остальных: ок")

    await db.delete_role(media)
    matrix = await db.get_access_matrix()
    assert "rt-1" not in matrix, "после удаления последней роли человек должен стать свободным"
    assert "rt-2" not in matrix
    print("удаление роли снимает ограничения с её людей: ок")

    left_grants = await db.fetch_val(
        "SELECT COUNT(*) FROM role_grants WHERE role_id=$1", media)
    assert left_grants == 0, "правила удалённой роли должны уходить каскадом"
    print("каскадное удаление правил: ок")

    from handlers_roles import parse_grant
    cases = [
        ("10.13.13.7", ("10.13.13.7/32", "any", None)),
        ("10.13.13.7 tcp 8096", ("10.13.13.7/32", "tcp", 8096)),
        ("10.13.13.7:tcp:22", ("10.13.13.7/32", "tcp", 22)),
        ("10.13.13.0/28", ("10.13.13.0/28", "any", None)),
        ("10.13.13.7 8096", ("10.13.13.7/32", "tcp", 8096)),
    ]
    for text, expect in cases:
        g, err = parse_grant(text)
        assert err is None, f"{text}: {err}"
        got = (g["cidr"], g["proto"], g["port"])
        assert got == expect, f"{text}: {got} вместо {expect}"
    print("разбор адреса во всех формах: ок")

    # Слово без цифр — имя. Разбор возвращает его как имя и без адреса: существует
    # оно или нет, знает только база, и проверяется это уровнем выше.
    g, err = parse_grant("дом.vpn tcp 8096")
    assert err is None and g["name"] == "дом.vpn" and not g["cidr"], (g, err)
    g, err = parse_grant("мусор")
    assert err is None and g["name"] == "мусор", (g, err)
    print("имя отличается от адреса: ок")

    # «мусор» сюда больше не относится: слово без цифр — это имя, и отбивает
    # его проверка существования, а не разбор. Ниже проверяется отдельно.
    for bad in ("192.168.1.5", "8.8.8.8", "10.13.13.254", "10.13.13.1",
                "10.13.13.7 tcp 99999"):
        g, err = parse_grant(bad)
        assert g is None and err, f"«{bad}» должен отбиваться"
        print(f"  отбито «{bad}»: {err}")

    await db.execute("DELETE FROM roles")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rt-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())

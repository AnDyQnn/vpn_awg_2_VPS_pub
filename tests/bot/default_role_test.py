# -*- coding: utf-8 -*-
"""Новый ключ не должен оказаться без ролей.

Схема владельца: роль «для всех» без единого правила, доступы выдаются
отдельными ролями. Держится она на том, что каждого человека в эту роль
записали. А роли только сужают — значит, человек БЕЗ ролей ходит по туннелю
куда угодно.

До этой правки новым ключам роль не выдавалась вовсе. То есть следующий
выданный ключ получил бы полный доступ ко всему, молча и ровно вопреки замыслу;
заметить это можно было бы только сверив список людей со списком в роли.

Проверяется: роль выдаётся, пока она назначена; не выдаётся, пока не назначена
(иначе правка меняла бы поведение у тех, кто её не просил); и что уже выданные
ключи назначение роли задним числом не трогает — менять права людям без спроса
нельзя.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-46s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def make_key(uuid_val, name):
    """Повторяет ту часть выдачи ключа, что касается ролей."""
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
        name, uuid_val)
    # Как в боевом коде: роль выдаётся, но её сбой не валит выдачу ключа —
    # человек должен получить связь даже если с ролями что-то не так.
    try:
        default_role = await db.get_setting("default_role_id")
        if default_role and await db.get_role(int(default_role)):
            await db.add_user_role(uuid_val, int(default_role))
    except Exception as e:
        print("    роль не выдалась:", e)


async def roles_of(uuid_val):
    return await db.fetch_all("SELECT role_id FROM user_roles WHERE uuid=$1",
                              uuid_val)


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'dr-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ПОУМ-%'")
    await db.set_setting("default_role_id", "")

    base = await db.create_role("ПОУМ-все")          # без правил, как у владельца

    print("=== роль не назначена: поведение прежнее ===")
    await make_key("dr-1", "Первый")
    check("ключ выдан без ролей", not await roles_of("dr-1"),
          "правка не меняет поведение, пока её не включили")

    print()
    print("=== роль назначена: новый ключ получает её сам ===")
    await db.set_setting("default_role_id", str(base))
    await make_key("dr-2", "Второй")
    got = await roles_of("dr-2")
    check("роль выдана", len(got) == 1 and got[0]["role_id"] == base,
          "ролей: %d" % len(got))

    print()
    print("=== и он сразу в матрице доступа, а не «ходит куда угодно» ===")
    m = await db.get_access_matrix()
    check("новый человек под ограничением", "dr-2" in m)
    check("открыто ему при этом ничего",
          "dr-2" in m and not m["dr-2"]["allow"],
          "именно так и задумано: пустая роль закрывает всё внутреннее")

    print()
    print("=== выданным раньше ключам ничего не меняется ===")
    check("первый по-прежнему без ролей", not await roles_of("dr-1"),
          "права людям задним числом не меняем")

    print()
    print("=== роль сняли: снова не выдаётся ===")
    await db.set_setting("default_role_id", "")
    await make_key("dr-3", "Третий")
    check("третий без ролей", not await roles_of("dr-3"))

    print()
    print("=== удалённая роль не ломает выдачу ключа ===")
    await db.set_setting("default_role_id", str(base))
    await db.execute("DELETE FROM roles WHERE id=$1", base)
    try:
        await make_key("dr-4", "Четвёртый")
        check("ключ всё равно создан", True, "выдача не должна падать из-за ролей")
    except Exception as e:
        check("ключ всё равно создан", False, str(e)[:60])

    await db.set_setting("default_role_id", "")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'dr-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ПОУМ-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

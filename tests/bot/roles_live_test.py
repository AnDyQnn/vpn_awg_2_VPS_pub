# -*- coding: utf-8 -*-
"""Роли ровно так, как их завели руками на бою.

Написано по живому случаю. Владелец создал три роли: «Admin» со всей подсетью,
«All_Users» **без единого правила** на 24 человека и пустую «Work» — и спросил,
работает ли. Убедиться можно было только читая правила iptables на узле.

Пустая роль — главный подвох здесь. Она не безобидна: роль только сужает, и
человек с пустой ролью теряет путь ко всем остальным в сети. При этом интернет,
выход через Германию и имена продолжают работать — потому что роли вообще не
про них. Экран раньше писал «закрыт весь туннель», и это читалось как «человек
остался без связи», хотя это неправда.

`roletest.py` рядом проверяет создание ролей и сложение прав. Здесь — то, чего
там нет: пустая роль, вся подсеть целиком и граница ответственности ролей.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-48s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    # Чистим только своё: соседние тесты живут в этой же базе.
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rl-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ТЕСТ-%'")

    for uuid_val, name in (("rl-adm", "Админ"), ("rl-usr", "Обычный"),
                           ("rl-free", "Безролевой")):
        await db.execute(
            "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
            name, uuid_val)

    whole = await db.create_role("ТЕСТ-вся-сеть")
    empty = await db.create_role("ТЕСТ-пустая")
    one = await db.create_role("ТЕСТ-один-адрес")

    await db.add_role_grant(whole, "10.13.13.0/24", "any", None, "вся подсеть")
    await db.add_role_grant(one, "10.13.13.77/32", "any", None, "один узел")

    await db.add_user_role("rl-adm", whole)
    await db.add_user_role("rl-usr", empty)

    m = await db.get_access_matrix()
    print("=== кого роли вообще касаются ===")
    print("  в матрице:", sorted(m))

    print()
    print("=== без ролей — никаких ограничений ===")
    check("безролевого в матрице нет", "rl-free" not in m,
          "кого нет в матрице, тому ничего не закрывают")

    print()
    print("=== вся подсеть открывается целиком ===")
    adm = m.get("rl-adm", {}).get("allow", [])
    check("админ в матрице", bool(adm))
    check("видит всю подсеть", any(g["cidr"] == "10.13.13.0/24" for g in adm),
          ", ".join(g["cidr"] for g in adm))

    print()
    print("=== пустая роль: человек в матрице, но открыто ноль ===")
    usr = m.get("rl-usr")
    check("человек в матрице есть", usr is not None,
          "пустая роль не безобидна — она сужает")
    check("и открыто ему ничего", usr is not None and not usr["allow"],
          "правил: %d" % (len(usr["allow"]) if usr else -1))

    print()
    print("=== роли не лезут туда, где их быть не должно ===")
    everything = str(m)
    check("нет правил про интернет", "0.0.0.0/0" not in everything,
          "интернет ролями не управляется")
    check("нет правил про выход в Германию", "10.13.13.254" not in everything,
          "выход остаётся доступен всегда")

    print()
    print("=== вторая роль добавляет, а не заменяет ===")
    await db.add_user_role("rl-usr", one)
    m2 = await db.get_access_matrix()
    allow2 = m2.get("rl-usr", {}).get("allow", [])
    check("адрес появился", any(g["cidr"] == "10.13.13.77/32" for g in allow2),
          "правил стало %d" % len(allow2))

    print()
    print("=== снятие роли возвращает как было ===")
    await db.remove_user_role("rl-usr", one)
    m3 = await db.get_access_matrix()
    check("адрес убрался",
          not any(g["cidr"] == "10.13.13.77/32"
                  for g in m3.get("rl-usr", {}).get("allow", [])))

    print()
    print("=== снят со всех ролей — снова ходит куда угодно ===")
    await db.remove_user_role("rl-usr", empty)
    m4 = await db.get_access_matrix()
    check("вышел из матрицы", "rl-usr" not in m4)

    await db.execute("DELETE FROM users WHERE uuid LIKE 'rl-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ТЕСТ-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

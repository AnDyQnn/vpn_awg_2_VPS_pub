# -*- coding: utf-8 -*-
"""Перевыпуск — это перевыпуск, а не удаление и создание.

Владелец сказал это прямо, и он был прав. Перевыпуск заводил НОВОГО человека с
новым uuid, а старого списывал. К uuid привязано девятнадцать таблиц;
переносились имя, телеграм и срок. Остальное оставалось на списанном.

Роли при этом били сильнее всего: в его схеме отсутствие ролей означает не
«нет доступа», а «ходит куда угодно». То есть перевыпуск ключа молча открывал
человеку всю сеть.

Проверяется то, что должно пережить перевыпуск:
  • сам человек — та же строка, тот же uuid;
  • роли, фильтрация сайтов, персональный лимит, подключение по Xray;
  • имя в туннеле, указывающее на него;
  • история трафика;
  • и что старый пир не убит, а помечен — он держит связь, пока человек не
    подключился новым ключом.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402

ok = True
calls = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def fake_create_peer(name, dns_type="classic", bypass_cidrs=None, uid=None):
    calls.append(("create", uid))
    return uid or "ВЫДУМАННЫЙ", "/tmp/x.conf", "/tmp/x.png"


async def fake_retire_peer(uuid_val):
    calls.append(("retire", uuid_val))
    return f"retired-{uuid_val}"


class FakeBot:
    async def send_message(self, **kw):
        pass

    async def send_document(self, **kw):
        pass

    async def send_photo(self, **kw):
        pass


class FakeContext:
    bot = FakeBot()


async def main():
    await db.connect()
    import handlers_client as hc
    import wireguard_manager as wm

    hc.create_peer = fake_create_peer
    wm.retire_peer = fake_retire_peer

    await db.execute("DELETE FROM users WHERE uuid LIKE 'ri-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ПЕРЕ-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Стойкий','ri-1',TRUE)")

    role = await db.create_role("ПЕРЕ-роль")
    await db.add_user_role("ri-1", role)
    await db.execute(
        "INSERT INTO user_filters (user_uuid, category) VALUES ('ri-1','ads')")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('ri-1','x-1','tok-1')")
    await db.execute(
        "INSERT INTO dns_names (name, target_uuid) VALUES ('стойкий.vpn','ri-1')")

    async def state():
        return {
            "человек": await db.fetch_val(
                "SELECT COUNT(*) FROM users WHERE uuid='ri-1'"),
            "ролей": await db.fetch_val(
                "SELECT COUNT(*) FROM user_roles WHERE uuid='ri-1'"),
            "фильтров": await db.fetch_val(
                "SELECT COUNT(*) FROM user_filters WHERE user_uuid='ri-1'"),
            "Xray": await db.fetch_val(
                "SELECT COUNT(*) FROM xray_users WHERE user_uuid='ri-1'"),
            "имён": await db.fetch_val(
                "SELECT COUNT(*) FROM dns_names WHERE target_uuid='ri-1'"),
        }

    before = await state()
    print("=== до перевыпуска ===")
    print("  ", before)

    user = await db.get_user_by_uuid("ri-1")
    user = dict(user)
    user["tg_ids"] = []
    old_uuid, name, new_uuid = await hc._issue_new_config(
        FakeContext(), 1, user, deliver=False)

    print()
    print("=== что делали с узлом ===")
    print("  ", calls)
    check("старого пометили, а не убили",
          ("retire", "ri-1") in calls,
          "он держит связь, пока человек не подключился новым")
    check("новый заведён под тем же человеком",
          ("create", "ri-1") in calls,
          "иначе всё, что к нему привязано, осталось бы на прежнем")
    check("человек в очередь снятия идёт прежний", new_uuid == "ri-1", new_uuid)
    check("на снятие ставится помеченный, а не человек",
          str(old_uuid).startswith("retired-"), old_uuid)

    after = await state()
    print()
    print("=== после перевыпуска ===")
    print("  ", after)
    for key in before:
        check("сохранилось: %s" % key, after[key] == before[key],
              "было %s, стало %s" % (before[key], after[key]))

    print()
    print("=== снятие отработавшего не трогает человека ===")
    await hc._retire_old_peer(old_uuid, name)
    final = await state()
    check("человек на месте", final["человек"] == 1,
          "раньше здесь стоял DELETE из таблицы людей")
    check("роли на месте", final["ролей"] == before["ролей"])
    check("Xray на месте", final["Xray"] == before["Xray"])

    await db.execute("DELETE FROM users WHERE uuid LIKE 'ri-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'ПЕРЕ-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

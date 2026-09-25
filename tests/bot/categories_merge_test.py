# -*- coding: utf-8 -*-
"""Категории слиты — у кого были старые, у того включены новые, само.

«Мошенничество» и «Шифровальщики» вошли в «Опасные сайты», «Слежка» — в
«Рекламу и слежку». Перенос делает бот при запуске: руками на установках
никто ничего не трогает, обновление приезжает само.
"""
import asyncio

from database import db
import filters


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cm-%'")
    for uid in ("cm-1", "cm-2"):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$1,TRUE)", uid)
    # Как было до обновления.
    for uid, cat in (("cm-1", "scam"), ("cm-1", "ransomware"), ("cm-1", "malware"),
                     ("cm-2", "tracking"), ("cm-2", "adult")):
        await db.execute("INSERT INTO user_filters (user_uuid, category) VALUES ($1,$2)",
                         uid, cat)
    await db.execute("INSERT INTO filter_exempt (user_uuid, category) VALUES ('cm-2','scam')")
    await db.set_setting("filters_common", "adult,ransomware,tracking")

    print("=== бот запускается после обновления ===")
    await db.connect()          # миграции — при подключении, как при старте бота
    got = await db.get_all_filters()
    print(" ", {k: v for k, v in got.items() if k.startswith("cm-")})
    assert sorted(got["cm-1"]) == ["malware"], got["cm-1"]
    assert sorted(got["cm-2"]) == ["ads", "adult"], got["cm-2"]
    assert await db.get_user_exempt("cm-2") == ["malware"]
    assert await db.get_common_filters() == ["ads", "adult", "malware"], \
        await db.get_common_filters()
    print("личные, исключения и общие — переведены, повторов нет: ок")

    print("\n=== повторный запуск ничего не портит ===")
    await db.connect()
    assert sorted((await db.get_all_filters())["cm-1"]) == ["malware"]
    assert await db.get_common_filters() == ["ads", "adult", "malware"]
    print("ок")

    print("\n=== на экране — только новые категории ===")
    keys = [k for k, _ in filters.CATEGORIES]
    assert "scam" not in keys and "ransomware" not in keys and "tracking" not in keys, keys
    assert dict(filters.CATEGORIES)["malware"] == "Опасные сайты"
    assert dict(filters.CATEGORIES)["drugs"] == "Наркотики и серые аптеки"
    print(" ", [t for _, t in filters.CATEGORIES])
    print("ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'cm-%'")
    await db.execute("DELETE FROM settings WHERE key='filters_common'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())

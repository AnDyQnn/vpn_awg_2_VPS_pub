# -*- coding: utf-8 -*-
"""Своя группа вешается на человека с его экрана фильтров.

Ключ группы — pool_<имя>_<хвост>, с подчёркиваниями. Кнопка «категория +
uuid» разбиралась по «_» слева, и хвост ключа уезжал в начало uuid: база
отвечала, что такого человека нет, и группа не вешалась. Вторая беда того же
корня: длинное имя группы выводило данные кнопки за 64 байта, и Telegram не
показывал экран вовсе.
"""
import asyncio

from database import db
import filters

UID = "3ee79485-9d85-4dcc-8f09-bc4c0594b576"


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid=$1", UID)
    await db.execute("INSERT INTO users (name, uuid) VALUES ('Брат', $1)", UID)

    short = filters._pool_key("likee")
    long_ = filters._pool_key("Очень длинное название группы likeevideoplus")
    longest = filters._pool_key("abcdefghijklmnopqrstuvwxyz")
    for key, title in ((short, "likee"), (longest, "длинная")):
        await db.save_filter_pool(key, title, ["example-%s.test" % title])

    print("=== кнопка влезает в предел Telegram ===")
    for key in (short, long_, longest):
        for prefix in ("flt_set_", "flt_exc_", "flt_xa_"):
            cb = "%s%s_%s" % (prefix, filters.cat_token(key), UID)
            assert len(cb.encode()) <= 64, (cb, len(cb.encode()))
    print("  самая длинная: %d байт из 64: ок"
          % len(("flt_exc_%s_%s" % (filters.cat_token(longest), UID)).encode()))

    print("\n=== разбор отдаёт настоящий uuid и ключ группы ===")
    for key in (short, longest):
        cb = "flt_set_%s_%s" % (filters.cat_token(key), UID)
        uid, cat = await filters.split_cat_uuid(cb, "flt_set_")
        assert uid == UID and cat == key, (uid, cat)
    # Старая кнопка, оставшаяся в чате, — с полным ключом.
    uid, cat = await filters.split_cat_uuid("flt_set_%s_%s" % (short, UID), "flt_set_")
    assert uid == UID and cat == short, (uid, cat)
    # Встроенная категория — как была.
    uid, cat = await filters.split_cat_uuid("flt_set_adult_%s" % UID, "flt_set_")
    assert uid == UID and cat == "adult"
    print("  новые, старые и встроенные кнопки разбираются: ок")

    print("\n=== группа вешается ===")
    uid, cat = await filters.split_cat_uuid(
        "flt_set_%s_%s" % (filters.cat_token(short), UID), "flt_set_")
    await db.set_user_filter(uid, cat, True)
    assert cat in await db.get_user_filters(UID)
    print("  группа на человеке: ок")

    for key in (short, longest):
        await db.delete_filter_pool(key)
    await db.execute("DELETE FROM users WHERE uuid=$1", UID)
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())

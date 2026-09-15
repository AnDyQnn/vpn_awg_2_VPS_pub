# -*- coding: utf-8 -*-
"""Ссылка доходит до человека текстом — и никакая кнопка этому не мешает.

Я сделал кнопку «Добавить в приложение» со ссылкой `vless://` внутри и решил,
что проверил её: отправил запрос в API телеграма и получил ошибку про
несуществующий чат, а не про ссылку. Принял это за разрешение. На деле проверка
чата идёт РАНЬШЕ проверки ссылки, и про ссылку тот ответ не говорил ничего.

На бою вышло так:

    BadRequest: Inline keyboard button url 'vless://...' is invalid:
    unsupported url protocol

QR уходил, а следующее сообщение — со ссылкой — падало. Человек оставался с
картинкой и без доступа.

Поэтому проверяется теперь не наличие кнопки, а то, что важно: ссылка ушла
текстом, и ни в одной клавиатуре нет схемы, которую телеграм не принимает.
Последнее — по всему исходнику, а не только здесь.
"""
import asyncio
import io
import os
import re
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402

ok = True
sent = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeBot:
    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        sent.append({"text": text, "markup": reply_markup})

    async def send_photo(self, **kw):
        sent.append({"photo": True})


class FakeContext:
    bot = FakeBot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'bt-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'bt-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Ссылкин','bt-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('bt-1','x-1','tok-1')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    link = await xray.profile_link("bt-1")
    print("=== ссылка ===")
    check("собралась", bool(link))
    check("имя человека в хвосте", link.endswith("Ссылкин"), link[-12:])

    print()
    print("=== она доходит до человека текстом ===")
    import handlers_client as hc
    sent.clear()
    await hc.send_xray_profile(FakeContext(), 1, "bt-1")
    texts = [m.get("text") for m in sent if m.get("text")]
    check("ссылка ушла отдельным сообщением", link in texts,
          "её выделяют и копируют")
    check("QR тоже ушёл", any(m.get("photo") for m in sent))
    check("предупреждение о личной ссылке на месте",
          any("не передавайте" in (x or "") for x in texts))

    print()
    print("=== ни одна кнопка не ведёт на схему, которой телеграм не знает ===")
    # Кнопки принимают только http, https и tg. Всё остальное телеграм
    # отвергает целиком — и сообщение не уходит вовсе.
    allowed = ("http://", "https://", "tg://")
    bad = []
    for m in sent:
        kb = m.get("markup")
        if not kb:
            continue
        for row in kb.inline_keyboard:
            for b in row:
                url = getattr(b, "url", None)
                if url and not url.startswith(allowed):
                    bad.append(url[:40])
    check("в отправленном таких нет", not bad, ", ".join(bad) or "—")

    # И по всему исходнику: чтобы следующая такая кнопка не доехала до людей.
    src_bad = []
    for name in sorted(os.listdir("/app")):
        if not name.endswith(".py"):
            continue
        text = io.open(os.path.join("/app", name), encoding="utf-8").read()
        for m in re.finditer(r"InlineKeyboardButton\((?:[^()]|\([^()]*\))*\)", text):
            call = m.group(0)
            if "url=" not in call:
                continue
            # Разрешаем только явно безопасные схемы и подстановки, которые
            # собираются из настроек бота (там всегда http-адрес).
            if re.search(r'url=(f?")(https?|tg)://', call):
                continue
            if re.search(r"url=\w*(link|url|base|sub)\w*\b", call):
                src_bad.append((name, text[:m.start()].count(chr(10)) + 1,
                                re.sub(r"\s+", " ", call)[:70]))
    if src_bad:
        for name, line, snippet in src_bad:
            print("      %s:%d  %s" % (name, line, snippet))
    check("и в исходнике тоже", not src_bad,
          "кнопка с чужой схемой рушит всё сообщение целиком")

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'bt-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'bt-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

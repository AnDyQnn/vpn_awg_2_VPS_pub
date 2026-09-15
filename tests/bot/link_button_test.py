# -*- coding: utf-8 -*-
"""В кнопку нельзя класть схему, которой телеграм не знает.

Я сделал кнопку «Добавить в приложение» со ссылкой `vless://` внутри и решил,
что проверил её: отправил запрос в API телеграма и получил ошибку про
несуществующий чат, а не про ссылку. Принял это за разрешение. На деле проверка
чата идёт РАНЬШЕ проверки ссылки, и тот ответ про ссылку не говорил ничего.

На бою вышло так:

    BadRequest: Inline keyboard button url 'vless://...' is invalid:
    unsupported url protocol

Телеграм отвергает СООБЩЕНИЕ ЦЕЛИКОМ. QR уходил, а следующее сообщение — со
ссылкой — падало, и человек оставался с картинкой и без доступа.

Поэтому проверка идёт по всему исходнику: ни одна кнопка не должна получать
адрес, собранный из чего-то, кроме http, https или tg. Заодно проверяем то, что
человеку в итоге уходит — адрес подписки, обычным http.
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

    print("=== что уходит человеку ===")
    sent.clear()
    await hc_send()
    texts = [m.get("text") for m in sent if m.get("text")]
    body = "\n".join(t for t in texts if t)
    link = await xray.profile_link("bt-1")
    check("ссылка дошла", link in body, link[:50])
    check("она уходит текстом, а не кнопкой", True,
          "схему vless:// телеграм в кнопке не принимает и рушит сообщение")

    print()
    print("=== в отправленном нет чужих схем ===")
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
    check("таких нет", not bad, ", ".join(bad) or "—")

    print()
    print("=== и по всему исходнику тоже ===")
    src_bad = []
    for name in sorted(os.listdir("/app")):
        if not name.endswith(".py"):
            continue
        text = io.open(os.path.join("/app", name), encoding="utf-8").read()
        for m in re.finditer(r"InlineKeyboardButton\((?:[^()]|\([^()]*\))*\)", text):
            call = m.group(0)
            if "url=" not in call:
                continue
            if re.search(r'url=(f?")(https?|tg)://', call):
                continue
            # Адрес, собранный из переменной, проверить статически нельзя —
            # но именно так и появилась та кнопка с `vless://`.
            if re.search(r"url=\w*(link|url|base|sub)\w*\b", call):
                src_bad.append((name, text[:m.start()].count(chr(10)) + 1,
                                re.sub(r"\s+", " ", call)[:70]))
    if src_bad:
        for name, line, snippet in src_bad:
            print("      %s:%d  %s" % (name, line, snippet))
    check("таких нет", not src_bad,
          "кнопка с чужой схемой рушит всё сообщение целиком")

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'bt-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'bt-%'")
    await db.set_setting("server_host", "")


async def hc_send():
    import handlers_client as hc
    await hc.send_xray_profile(FakeContext(), 1, "bt-1")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

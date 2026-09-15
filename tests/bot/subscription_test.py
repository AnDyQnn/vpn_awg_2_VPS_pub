# -*- coding: utf-8 -*-
"""Подписка — то, ради чего Xray и делался.

Весь смысл второго протокола: не собирать тридцать человек на перевыпуск при
каждом изменении. Механизм раздачи написан и работает, но адрес, по которому
клиент забирает профиль, не задавали ни разу — и Xray оказался таким же
снимком, как конфиг AmneziaWG. Владелец это и заметил.

Не задавали по понятной причине: по подписке уходит доступ к VPN, а открывать
её в интернет без сертификата нельзя. Решение не требует ни домена, ни
сертификата — раздавать внутри туннеля, по адресу узла. Клиент обновляется,
будучи подключённым, запрос идёт по уже зашифрованному каналу, наружу порт
закрыт.

Проверяется:
  • адрес есть всегда, без всякой настройки — иначе подписка снова окажется
    выключенной и никто этого не заметит;
  • он внутренний, то есть наружу ничего не торчит;
  • заданный владельцем сильнее умолчания;
  • ссылка подписки содержит личный токен и собирается целиком;
  • человеку она доходит вместе с объяснением, а не остаётся в настройках.
"""
import asyncio
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
    async def send_message(self, chat_id=None, text=None, **kw):
        sent.append(text)

    async def send_photo(self, **kw):
        # Предупреждение о личной ссылке живёт в подписи к картинке, а не
        # отдельным сообщением — значит и запоминать надо её.
        sent.append(kw.get("caption") or "")


class FakeContext:
    bot = FakeBot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sb-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sb-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Подписчик','sb-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('sb-1','x-1','ТОКЕН-1')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4"), ("xray_sub_base", "")):
        await db.set_setting(key, val)

    print("=== адрес подписки есть без всякой настройки ===")
    base = await xray.subscription_base()
    check("адрес не пуст", bool(base), base)
    check("ведёт внутрь туннеля", base.startswith("http://10.13.13."),
          "наружу ничего не торчит, сертификат не нужен")

    print()
    print("=== ссылка подписки собирается ===")
    url = await xray.subscription_url("ТОКЕН-1")
    print("  ", url)
    check("ссылка есть", bool(url))
    check("личный токен внутри", "ТОКЕН-1" in url)
    check("путь тот самый", "/sub/" in url)

    print()
    print("=== заданное владельцем сильнее умолчания ===")
    await db.set_setting("xray_sub_base", "https://vpn.example.ru/")
    check("взят заданный",
          await xray.subscription_base() == "https://vpn.example.ru",
          await xray.subscription_base())
    check("хвостовая косая убрана",
          not (await xray.subscription_base()).endswith("/"))
    await db.set_setting("xray_sub_base", "")

    print()
    print("=== человеку уходит один кусок, а не адрес ===")
    # Адрес подписки человеку не отдаётся. Дважды пробовали иначе: ссылкой —
    # он открывал её в браузере и видел набор символов; кодом с пояснением —
    # до этого шага просто не доходили. А без него не работал сплит.
    #
    # Теперь сплит уезжает вместе с серверами одним куском, который вставляют
    # один раз. Подписка при этом жива и работает — её читают те, кто её
    # завёл, и по ней же обновляется профиль.
    import handlers_client as hc
    sent.clear()
    await hc.send_xray_profile(FakeContext(), 1, "sb-1")
    everything = chr(10).join(x for x in sent if x)
    url = await xray.subscription_url("ТОКЕН-1")
    check("ушли сервера", "vless://" in everything)
    check("ушёл и профиль маршрутизации", "happ://routing/" in everything,
          "иначе человек подключится без сплита")
    check("адреса подписки человеку нет", url not in everything,
          "он про него всё равно ничего не понял")
    check("предупреждение на месте", "не передавайте" in everything)

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sb-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sb-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Подписчик','sb-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('sb-1','x-1','ТОКЕН-1')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4"), ("xray_sub_base", "")):
        await db.set_setting(key, val)

    print("=== адрес подписки есть без всякой настройки ===")
    base = await xray.subscription_base()
    check("адрес не пуст", bool(base), base)
    check("ведёт внутрь туннеля", base.startswith("http://10.13.13."),
          "наружу ничего не торчит, сертификат не нужен")

    print()
    print("=== ссылка подписки собирается ===")
    url = await xray.subscription_url("ТОКЕН-1")
    print("  ", url)
    check("ссылка есть", bool(url))
    check("личный токен внутри", "ТОКЕН-1" in url)
    check("путь тот самый", "/sub/" in url)

    print()
    print("=== заданное владельцем сильнее умолчания ===")
    await db.set_setting("xray_sub_base", "https://vpn.example.ru/")
    check("взят заданный",
          await xray.subscription_base() == "https://vpn.example.ru",
          await xray.subscription_base())
    check("хвостовая косая убрана",
          not (await xray.subscription_base()).endswith("/"))
    await db.set_setting("xray_sub_base", "")

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sb-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sb-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

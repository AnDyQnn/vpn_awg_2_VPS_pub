# -*- coding: utf-8 -*-
"""Несколько входов: маска отвалилась — работают остальные.

Владелец просил переключение между разными масками. Пулом поддоменов это не
решается: все имена в нём принадлежат одному сайту, и ляжет он — ляжет весь
пул. Одним входом тоже нельзя: Reality переадресует проверяющего на сайт
маски, и тот обязан отдать подходящий сертификат — у разных сайтов они разные.

Значит несколько входов, на разных портах, у каждого своя маска. Человеку в
подписку уходят все, и приложение перебирает их само.

Проверяется:
  • в конфиге узла столько входов, сколько масок, и все на разных портах;
  • маски у входов разные — иначе они лягут вместе, и смысла нет;
  • люди и правила у входов общие: правило выбирает канал по человеку, а не по
    тому, через какой вход он пришёл;
  • в подписку уходят ВСЕ входы, а не один;
  • основной идёт первым — приложение пробует по порядку;
  • разовая ссылка остаётся одна, основная.
"""
import asyncio
import base64
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'me-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'me-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Многоходов','me-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('me-1','x-1','tok-me')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("xray_private_key", "PRIV"), ("server_host", "1.2.3.4"),
                     ("xray_dest", ""), ("xray_port", "")):
        await db.set_setting(key, val)

    print("=== входы ===")
    ways = await xray.entries()
    for port, dest in ways:
        print("   %-6s %s" % (port, dest))
    check("входов больше одного", len(ways) > 1, "%d" % len(ways))
    check("порты все разные", len({p for p, _ in ways}) == len(ways))
    check("маски все разные", len({d for _, d in ways}) == len(ways),
          "одинаковые лягут вместе, и смысла в запасных не будет")
    check("основной первый", ways[0][0] == xray.DEFAULT_PORT
          and ways[0][1] == xray.DEFAULT_DEST, str(ways[0]))

    print()
    print("=== конфиг узла ===")

    async def fake_ips():
        return {"me-1": "10.13.13.9"}

    xray.peer_ip_map = fake_ips
    config, addresses, note = await xray.build_config()
    ins = config["inbounds"]
    check("входов в конфиге столько же", len(ins) == len(ways), "%d" % len(ins))
    check("порты совпадают с задуманными",
          [i["port"] for i in ins] == [p for p, _ in ways],
          str([i["port"] for i in ins]))
    check("у каждого своя маска",
          len({i["streamSettings"]["realitySettings"]["dest"] for i in ins}) == len(ins))
    check("метки входов различимы",
          len({i["tag"] for i in ins}) == len(ins),
          ", ".join(i["tag"] for i in ins))
    check("люди у всех входов одни и те же",
          all(i["settings"]["clients"] == ins[0]["settings"]["clients"] for i in ins),
          "иначе человек подключился бы не везде")
    check("правила выбирают канал по человеку",
          all("user" in r for r in config["routing"]["rules"]),
          "а не по входу — иначе запасной вход ходил бы не с того адреса")

    print()
    print("=== что уходит человеку ===")
    links = await xray.profile_links("me-1")
    for l in links:
        print("   ", l[:74], "…")
    check("ссылок столько же, сколько входов", len(links) == len(ways),
          "%d" % len(links))
    check("порты в ссылках разные",
          len({l.split("@")[1].split("?")[0] for l in links}) == len(links))
    check("маски в ссылках разные",
          len({l.split("sni=")[1].split("&")[0] for l in links}) == len(links))

    print()
    print("=== подписка отдаёт все ===")
    body = await xray.subscription_body("tok-me")
    decoded = base64.b64decode(body).decode()
    check("строк в подписке столько же", len(decoded.split(chr(10))) == len(ways),
          "%d" % len(decoded.split(chr(10))))
    check("основной вход первым",
          decoded.split(chr(10))[0] == links[0],
          "приложение пробует по порядку")

    print()
    print("=== разовая ссылка остаётся одна ===")
    single = await xray.profile_link("me-1")
    check("она же основная", single == links[0])
    check("это одна строка", chr(10) not in single)

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'me-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'me-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

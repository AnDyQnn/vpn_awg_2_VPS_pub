# -*- coding: utf-8 -*-
"""Подписка Clash Mi: профиль из конфига AmneziaWG и сервер, который его отдаёт.

Главное свойство — в профиле тот же ключ, что в файле конфига: тот же закрытый
ключ, адрес, сервер и параметры обфускации. Второе — порт смотрит в интернет,
поэтому чужой запрос не должен узнать ничего, а частящий — дойти до базы.
"""
import asyncio
import os
import re
import socket
from datetime import datetime

import aiohttp
from aiohttp import web

import clashsub as cs
from database import db
from utils import CONFIGS_DIR

UID, NAME = "cs-1", "Ника-телефон"
CONF = """[Interface]
PrivateKey = AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=
Address = 10.13.13.77/32
DNS = 1.1.1.1, 1.0.0.1, example.ru
MTU = 1280
Jc = 4
Jmin = 40
Jmax = 70
S1 = 52
S2 = 16
H1 = 1122334455
H2 = 2233445566
H3 = 3344556677
H4 = 4455667788

[Peer]
PublicKey = AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI=
PresharedKey = AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM=
Endpoint = 203.0.113.10:51820
AllowedIPs = 0.0.0.0/5, 8.0.0.0/7
PersistentKeepalive = 25
"""


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cs-%'")
    await db.execute("DELETE FROM bypass_exclusions WHERE note='cs-test'")
    await db.execute("INSERT INTO users (name, uuid, is_active, expires_at) "
                     "VALUES ($1,$2,TRUE,$3)", NAME, UID,
                     datetime(2027, 1, 1))
    for dom, cidrs in (("sberbank.ru", "198.51.100.0/25"),
                       ("кривая-запись", "10.0.0.0/8,0.0.0.0/1,1.2.3.0/24"),
                       ("198.51.100.13", "198.51.100.13/32"),
                       ("кривая-запись.рф", ""),
                       ("мусор, с запятой", "")):
        await db.execute("INSERT INTO bypass_exclusions (domain, cidrs, note) "
                         "VALUES ($1,$2,'cs-test')", dom, cidrs)
    (CONFIGS_DIR / f"{NAME}.conf").write_text(CONF, encoding="utf-8")

    print("=== профиль несёт тот же ключ, что файл ===")
    user = {"uuid": UID, "name": NAME}
    body = await cs.profile_for(user)
    open("/out/clashsub_profile.yaml", "w", encoding="utf-8").write(body)
    for must in ('private-key: "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="',
                 'public-key: "AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI="',
                 'pre-shared-key: "AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM="',
                 'server: "203.0.113.10"', "port: 51820", 'ip: "10.13.13.77"',
                 "mtu: 1280", "jc: 4", "jmin: 40", "jmax: 70", "s1: 52", "s2: 16",
                 'h1: "1122334455"', 'h4: "4455667788"'):
        assert must in body, must
    print("ключ, адрес, сервер, обфускация — из файла: ок")

    print("\n=== DNS — тот же, что в файле, и через туннель ===")
    assert '- "1.1.1.1#VPN"' in body and '- "1.0.0.1#VPN"' in body, body
    assert "example.ru#" not in body, "зона поиска — не адрес DNS"
    print("ок")

    print("\n=== сплит: список обхода, и только безопасная его часть ===")
    rules = [l.strip()[2:] for l in body.splitlines() if l.startswith("  - ") and "," in l]
    print(" ", rules)
    assert "DOMAIN-SUFFIX,sberbank.ru,DIRECT" in rules
    assert "IP-CIDR,198.51.100.0/25,DIRECT" in rules
    assert "IP-CIDR,1.2.3.0/24,DIRECT" in rules
    assert "IP-CIDR,198.51.100.13/32,DIRECT" in rules
    assert not any("10.0.0.0/8,DIRECT" in r or "0.0.0.0/1" in r for r in rules), \
        "служебные сети и полинтернета мимо туннеля пускать нельзя"
    assert not any("DOMAIN-SUFFIX,198." in r for r in rules), "адрес — не имя сайта"
    assert "DOMAIN-SUFFIX,xn----7sbbf1acfj5cdt6k6a.xn--p1ai,DIRECT" in rules, \
        "русское имя едет в punycode, как его и спросит приложение"
    assert not any("мусор" in r or " " in r for r in rules), "мусор в правила не попадает"
    assert rules[0] == "IP-CIDR,203.0.113.10/32,DIRECT,no-resolve", \
        "сам узел — мимо туннеля, иначе с включённым VPN подписка не обновится"
    assert rules[1].startswith("IP-CIDR,10.13.13.0/24,VPN"), "затем туннель"
    own = cs.build_profile("x", cs.parse_conf(CONF), [], "example.ru", self_host="example.ru")
    assert "  - DOMAIN,example.ru,DIRECT\n" in own, "имя узла — тоже напрямую"
    assert rules[-1] == "MATCH,VPN", "всё остальное — в VPN"
    print("мимо VPN — только то, что безопасно; остальное в туннель: ок")

    print("\n=== кривые строки не ломают YAML ===")
    weird = cs.parse_conf(CONF.replace("[Interface]", "# коммент\n[Interface]"))
    prof = cs.build_profile('a"b\\c', weird, [], "vpn")
    assert prof.startswith('# Профиль VPN: a"b\\c')
    print("ок")

    print("\n=== адрес подписки ===")
    tok = await db.sub_token(UID)
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", tok), tok
    assert await db.sub_token(UID) == tok, "токен стабилен, пока его не сменили"
    print("ок")

    print("\n=== сервер ===")
    port = free_port()
    runner = web.AppRunner(cs.make_app(), access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", port).start()
    base = f"http://127.0.0.1:{port}"
    async with aiohttp.ClientSession() as s:
        async def get(path, **kw):
            async with s.get(base + path, **kw) as r:
                return r.status, dict(r.headers), await r.text()

        await db.execute("INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out) "
                         "VALUES ($1, NOW(), 1000, 50000)", UID)
        st, h, text = await get(f"/c/{tok}?overwrite=false")
        assert st == 200, (st, text)
        assert text == body, "сервер отдаёт тот же профиль"
        assert h["profile-update-interval"] == "6", h
        assert "upload=1000; download=50000; total=0; expire=" in h["subscription-userinfo"], h
        assert h["Content-Disposition"].startswith("attachment; filename*=UTF-8''"), h
        assert h["Server"] == "nginx"
        assert (await db.sub_info(UID))["fetch_count"] == 1
        print("  профиль, трафик, срок и имя файла в заголовках: ок")

        st, h, text = await get(f"/c/{tok}", headers={"Accept": "text/html,*/*"})
        assert st == 200 and "Clash Mi" in text and "AQEBAQEBAQEB" not in text, text[:200]
        print("  в браузере — пояснение, а не ключ: ок")

        for path in ("/", "/c/short", "/c/" + "x" * 43, "/robots.txt", "/c/" + tok + "/x"):
            st, h, text = await get(path)
            assert st == 404 and h["Server"] == "nginx" and "AQEBAQEBAQEB" not in text, (path, st)
        async with s.post(f"{base}/c/{tok}") as r:
            assert r.status == 404
        print("  чужое и кривое — одинаковое 404 без подробностей: ок")

        old = tok
        tok = await db.sub_token(UID, rotate=True)
        assert tok != old
        assert (await get(f"/c/{old}"))[0] == 404, "старая ссылка должна умереть сразу"
        assert (await get(f"/c/{tok}"))[0] == 200
        print("  смена ссылки: старая умерла, новая работает: ок")

        # Перебор токенов: после десяти промахов адрес не получает ничего,
        # даже по верному токену.
        cs._miss.clear(); cs._rate.clear()
        for _ in range(cs.MISS_LIMIT):
            await get("/c/" + "y" * 43)
        assert (await get(f"/c/{tok}"))[0] == 404, "перебирающий должен быть отрезан"
        print("  перебор токенов: адрес отрезан: ок")

        cs._miss.clear(); cs._rate.clear()
        codes = [(await get(f"/c/{tok}"))[0] for _ in range(cs.RATE_LIMIT + 3)]
        assert codes[:cs.RATE_LIMIT] == [200] * cs.RATE_LIMIT and codes[-1] == 404, codes
        print("  частящий упирается в предел: ок")
        cs._miss.clear(); cs._rate.clear()

        # Файла конфига нет — отдавать нечего, и это тоже одно и то же 404.
        os.rename(CONFIGS_DIR / f"{NAME}.conf", CONFIGS_DIR / "cs-away.conf")
        assert (await get(f"/c/{tok}"))[0] == 404
        os.rename(CONFIGS_DIR / "cs-away.conf", CONFIGS_DIR / f"{NAME}.conf")
        print("  нет файла конфига — 404: ок")

        await db.execute("DELETE FROM users WHERE uuid=$1", UID)
        assert (await get(f"/c/{tok}"))[0] == 404, "удалённый ключ — мёртвая ссылка"
        assert await db.fetch_val("SELECT COUNT(*) FROM sub_tokens WHERE token=$1", tok) == 0
        print("  ключ удалён — ссылка умерла вместе с ним: ок")
    await runner.cleanup()

    print("\n=== без сертификата порт не открывается ===")
    cs.public_host = lambda: "vpn.example.ru"
    cs.CERT_DIR = "/tmp/cs-no-certs"
    assert not cs.cert_ready()
    assert await cs.sub_url(UID) == "", "без сертификата ссылку не выдаём"
    print("ок")

    (CONFIGS_DIR / f"{NAME}.conf").unlink()
    await db.execute("DELETE FROM bypass_exclusions WHERE note='cs-test'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())

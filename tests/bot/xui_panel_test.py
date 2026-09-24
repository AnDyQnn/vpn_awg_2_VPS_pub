# -*- coding: utf-8 -*-
"""Бот и панель 3X-UI — на настоящей панели, а не на заглушке.

Раннер поднимает рядом свежий контейнер 3X-UI того же образа, что в compose.
Проверяется всё, что бот делает с панелью сам, без человека:

  • первичная настройка: вход заводским логином, свой API-токен, замена
    заводского логина, панель на случайном пути, подписка на имени узла;
  • повторная настройка ничего не ломает и ничего не меняет;
  • вход VLESS + Reality на 443 с маской по умолчанию;
  • профиль маршрутизации Happ в подписке — только сайты из списка обхода;
  • выдача доступа человеку, пауза, отзыв;
  • подписка по выданному адресу действительно отдаёт настройки.
"""
import asyncio
import base64
import json
import os
import sys

os.environ["XUI_SECRETS"] = "/tmp/xui_test.json"
os.environ["XRAY_STACK"] = "xray"
os.environ["PUBLIC_DOMAIN"] = "example.ru"
sys.path.insert(0, "/app")

import aiohttp                                     # noqa: E402
from database import db                            # noqa: E402
import xui                                         # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-56s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    try:
        os.remove(os.environ["XUI_SECRETS"])
    except OSError:
        pass
    await db.execute("DELETE FROM users WHERE uuid LIKE 'xt-%'")
    await db.execute("DELETE FROM bypass_exclusions WHERE domain IN ('gosuslugi.ru','10.9.8.0/24')")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Панельный','xt-1',TRUE)")
    await db.execute(
        "INSERT INTO bypass_exclusions (domain, cidrs) VALUES "
        "('gosuslugi.ru','213.59.0.0/16'), ('10.9.8.0/24','10.9.8.0/24')")

    print("=== первичная настройка ===")
    okb, note = await xui.bootstrap(admin_id=42)
    print("   ", note)
    check("настроилась", okb, note)
    sec = xui.load_secrets()
    check("токен бота заведён", bool(sec.get("token")))
    check("заводской логин заменён", sec.get("user") not in ("", "admin")
          and sec.get("password") not in ("", "admin"))
    check("панель на случайном пути", sec.get("base_path", "/") != "/",
          sec.get("base_path"))
    check("панель отвечает по токену", await xui.ping())

    # Заводской логин больше не пускает.
    try:
        s, _ = await xui._session_login("admin", "admin", sec["base_path"])
        await s.close()
        admin_works = True
    except Exception:
        admin_works = False
    check("admin/admin больше не пускает", not admin_works)

    print()
    print("=== повторная настройка ===")
    okb2, note2 = await xui.bootstrap(admin_id=42)
    check("ничего не меняет", okb2 and note2 == "всё уже на месте", note2)

    print()
    print("=== настройки панели ===")
    st = await xui.api("POST", "panel/api/setting/all")
    check("подписка включена на 2096", st.get("subEnable") and st.get("subPort") == 2096)
    check("подписка на имени узла", st.get("subDomain") == "example.ru", st.get("subDomain"))
    check("время московское", st.get("timeLocation") == "Europe/Moscow")
    check("маршрутизация в подписке включена", st.get("subEnableRouting") is True)
    link = st.get("subRoutingRules") or ""
    check("профиль — ссылкой Happ", link.startswith("happ://routing/onadd/"), link[:30])
    prof = json.loads(base64.b64decode(link.rsplit("/", 1)[1]).decode())
    check("в профиле сайт из списка обхода", "gosuslugi.ru" in prof["DirectSites"])
    check("адресов от кода в профиле нет", prof["DirectIp"] == []
          and "10.9.8.0/24" not in prof["DirectSites"], str(prof["DirectIp"]))
    check("все шесть списков на месте",
          all(isinstance(prof.get(k), list) for k in
              ("DirectSites", "DirectIp", "ProxySites", "ProxyIp", "BlockSites", "BlockIp")))
    check("гео-файлы не с GitHub", "github.com" not in prof["Geoipurl"])

    print()
    print("=== вход ===")
    ib = await xui.managed_inbound()
    check("вход заведён", ib is not None)
    ss = ib["streamSettings"] if isinstance(ib["streamSettings"], dict) else json.loads(ib["streamSettings"])
    rs = ss["realitySettings"]
    check("VLESS на 443", ib["protocol"] == "vless" and ib["port"] == 443)
    check("Reality с маской по умолчанию", rs.get("target", "").startswith(xui.DEFAULT_TARGET),
          rs.get("target"))
    check("адрес в ссылках — имя узла", ib.get("shareAddr") == "example.ru",
          ib.get("shareAddr"))
    check("второй вход не заводится", await xui.ensure_inbound() is False)

    print()
    print("=== выдача человеку ===")
    row = await xui.issue("xt-1")
    check("запись в базе", row and row["email"].startswith("Панельный-"), str(row))
    c = await xui._client(row["email"])
    check("клиент в панели", c is not None)
    check("поток Vision", c and c.get("flow") == "xtls-rprx-vision")
    check("в комментарии наш uuid", c and c.get("comment") == "xt-1")
    again = await xui.issue("xt-1")
    check("повторная выдача — та же подписка", again["sub_id"] == row["sub_id"])
    url = await xui.sub_url("xt-1")
    check("адрес подписки на имени узла", "example.ru:2096" in url, url)

    # Подписку спрашиваем у самой панели — по тому же пути, но на её адресе:
    # имени example.ru в тестовой сети нет. Имя передаём заголовком, как это
    # сделает телефон: по чужому имени сервер подписок не отдаёт ничего.
    local = url.replace("https://example.ru", "http://vpntest-xui").replace(
        "http://example.ru", "http://vpntest-xui")
    async with aiohttp.ClientSession() as s:
        async with s.get(local, headers={"User-Agent": "Happ/1.0"}) as r:
            stranger = r.status
    check("по голому адресу подписку не отдают", stranger in (403, 404), str(stranger))
    async with aiohttp.ClientSession() as s:
        async with s.get(local, headers={"User-Agent": "Happ/1.0",
                                         "Host": "example.ru:2096"}) as r:
            body = await r.text()
            routing = r.headers.get("Routing", "")
    try:
        links = base64.b64decode(body + "=" * (-len(body) % 4)).decode()
    except Exception:
        links = body
    check("подписка отдаёт vless://", "vless://" in links, links[:60])
    check("в ссылке имя узла и маска", "@example.ru:443" in links
          and "sni=" + xui.DEFAULT_TARGET in links, links[:160])
    check("профиль маршрутизации уходит заголовком", routing.startswith("happ://routing/"),
          routing[:30])

    print()
    print("=== пауза и разморозка ===")
    await db.execute("UPDATE users SET is_active=FALSE WHERE uuid='xt-1'")
    await xui.sync_person("xt-1", "тест")
    c = await xui._client(row["email"])
    check("пауза дошла до панели", c and c.get("enable") is False)
    await db.execute("UPDATE users SET is_active=TRUE WHERE uuid='xt-1'")
    await xui.sync_person("xt-1", "тест")
    c = await xui._client(row["email"])
    check("разморозка тоже", c and c.get("enable") is True)
    check("подписка после паузы та же", c and c.get("subId") == row["sub_id"])

    print()
    print("=== сводка и онлайн ===")
    st = await xui.status()
    check("панель в сводке жива", st["panel"] is True)
    check("людей на Xray: 1", st["people"] == 1, str(st["people"]))
    check("вход в сводке", (st.get("inbound") or {}).get("port") == 443)
    check("онлайн отвечает", isinstance(await xui.online_uuids(), set))

    print()
    print("=== отзыв ===")
    check("отозван", await xui.revoke("xt-1") is True)
    check("клиента в панели нет", await xui._client(row["email"]) is None)
    check("записи в базе нет", await db.get_xui_client("xt-1") is None)
    check("повторный отзыв спокоен", await xui.revoke("xt-1") is False)

    await db.execute("DELETE FROM users WHERE uuid LIKE 'xt-%'")
    await db.execute("DELETE FROM bypass_exclusions WHERE domain IN ('gosuslugi.ru','10.9.8.0/24')")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

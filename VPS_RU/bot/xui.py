# -*- coding: utf-8 -*-
"""Второй канал связи: Xray через панель 3X-UI.

Панель живёт в своём контейнере (`vpn_xui`), в одной сетевой области с узлом
и ботом, и бот говорит с ней по её REST API на петле. Сам Xray, входы,
подписки и статистика — её забота; наша — люди: кому выдан доступ, у кого он
приостановлен, кто уже переехал.

Настраивается всё отсюда, руками в панель лезть не нужно:

  • при первом запуске бот входит заводским логином, заводит себе API-токен и
    меняет логин с паролем на случайные — пока этого не случилось, панель
    видна только самому узлу;
  • подписка — на имени узла и с его сертификатом, если они есть;
  • вход — VLESS + Reality на 443, маска из настроек бота;
  • в подписку уезжает профиль маршрутизации Happ: сайты из списка обхода
    идут мимо VPN, как у AmneziaWG.

Доступы и токены лежат в `/volumes/secrets/xui.json`, рядом с остальными
секретами узла: в базе они оказались бы внутри архива бэкапа.
"""
import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import time
from urllib.parse import quote

import aiohttp

from database import db

PANEL_URL = os.getenv("XUI_URL", "http://127.0.0.1:2053").rstrip("/")
SECRETS_FILE = os.getenv("XUI_SECRETS", "/volumes/secrets/xui.json")
# Сертификат глазами бота и глазами панели — одна и та же папка на хосте,
# смонтированная в два контейнера по разным путям.
CERT_DIR_BOT = os.getenv("SUB_CERT_DIR", "/volumes/certs")
CERT_DIR_PANEL = "/certs"
PUBLIC_SUB_STATE = "/volumes/flags/public_sub.json"

INBOUND_PORT = 443
SUB_PORT = 2096
PANEL_PORT = 2053
# Вход, который заводит и сопровождает бот. Остальные входы владелец волен
# заводить в панели сам — бот их не трогает.
INBOUND_REMARK = "vpn-reality"
FLOW = "xtls-rprx-vision"
# Маска по умолчанию. Крупный российский сайт с TLS 1.3 — проверено
# `xray tls ping`. Меняется в панели или кнопкой в боте.
DEFAULT_TARGET = "www.ozon.ru"
KEY_TARGET = "xui_target"

# Гео-файлы для Happ. По умолчанию приложение тянет их с GitHub, который из
# России не открывается, а без них профиль маршрутизации считается
# испорченным целиком. Зеркало на jsDelivr открывается.
GEO_IP = "https://cdn.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/geoip.dat"
GEO_SITE = "https://cdn.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/geosite.dat"
ROUTING_NAME = "Сплит от бота"


class XuiError(Exception):
    pass


# --- состояние стека -----------------------------------------------------------

def stack_enabled() -> bool:
    """Включён ли стек — по профилям compose, переданным в окружение бота."""
    raw = os.getenv("XRAY_STACK", "") or ""
    return "xray" in [p.strip() for p in raw.replace(" ", ",").split(",")]


def load_secrets() -> dict:
    try:
        with open(SECRETS_FILE, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def save_secrets(data: dict):
    os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)
    tmp = SECRETS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, SECRETS_FILE)


def _base(sec=None) -> str:
    path = (sec or load_secrets()).get("base_path") or "/"
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return path


# --- разговор с панелью ----------------------------------------------------------

async def _call(method, path, body=None, token=None, session=None, csrf=None,
                base=None, timeout=20, form=False):
    """Один запрос к панели. Возвращает `obj` ответа или бросает XuiError.

    `form=True` — тело формой, а не JSON: так принимает шаблон Xray."""
    url = PANEL_URL + (base or _base()) + path.lstrip("/")
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if csrf:
        headers["X-CSRF-Token"] = csrf
    own = session is None
    if own:
        session = aiohttp.ClientSession()
    try:
        kw = {"data": body} if form else {"json": body}
        async with session.request(method, url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=timeout), **kw) as r:
            text = await r.text()
            if r.status != 200:
                raise XuiError(f"{method} {path}: код {r.status}")
            try:
                data = json.loads(text) if text.strip() else {}
            except ValueError:
                raise XuiError(f"{method} {path}: ответ не JSON")
    except aiohttp.ClientError as e:
        raise XuiError(f"панель недоступна: {e}")
    except asyncio.TimeoutError:
        raise XuiError("панель не ответила вовремя")
    finally:
        if own:
            await session.close()
    if isinstance(data, dict) and data.get("success") is False:
        raise XuiError(data.get("msg") or f"{path}: отказ")
    return data.get("obj") if isinstance(data, dict) else data


async def api(method, path, body=None, timeout=20, form=False):
    """Запрос с токеном бота."""
    sec = load_secrets()
    if not sec.get("token"):
        raise XuiError("панель ещё не настроена")
    return await _call(method, path, body, token=sec["token"], base=_base(sec),
                       timeout=timeout, form=form)


async def ping() -> bool:
    try:
        await api("GET", "panel/api/server/status", timeout=8)
        return True
    except XuiError:
        return False


async def wait_panel(timeout=180) -> bool:
    """Ждём, пока панель начнёт отвечать хоть чем-то (после старта контейнера)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for base in {_base(), "/"}:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(PANEL_URL + base + "csrf-token",
                                     timeout=aiohttp.ClientTimeout(total=5)) as r:
                        if r.status == 200:
                            return True
            except Exception:
                pass
        await asyncio.sleep(3)
    return False


async def _session_login(user, password, base):
    """Вход по логину: сессия с cookie и токен CSRF для неё.

    Cookie панели ставится на адрес 127.0.0.1, а aiohttp по умолчанию cookie
    для адресов не принимает — отсюда unsafe=True."""
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
    try:
        token = await _call("GET", "csrf-token", session=session, base=base)
        await _call("POST", "login", {"username": user, "password": password},
                    session=session, csrf=token, base=base)
        token = await _call("GET", "csrf-token", session=session, base=base)
        return session, token
    except Exception:
        await session.close()
        raise


# --- первичная настройка -----------------------------------------------------

async def bootstrap(admin_id=0):
    """Приводит панель в рабочее состояние. Безопасно звать сколько угодно раз.

    Возвращает (ok, что сделано)."""
    notes = []
    if not await wait_panel():
        return False, "панель не поднялась за три минуты"
    sec = load_secrets()

    if not (sec.get("token") and await ping()):
        # Свой логин, если он уже заведён, иначе заводской. Заводской
        # срабатывает ровно один раз — сразу после первого запуска.
        tried = []
        if sec.get("user") and sec.get("password"):
            tried.append((sec["user"], sec["password"]))
        tried.append(("admin", "admin"))
        session = csrf = None
        for user, password in tried:
            for base in dict.fromkeys([_base(sec), "/"]):
                try:
                    session, csrf = await _session_login(user, password, base)
                    sec.update(user=user, password=password, base_path=base)
                    break
                except XuiError:
                    continue
            if session:
                break
        if not session:
            return False, "в панель не войти ни своим логином, ни заводским"
        try:
            obj = await _call("POST", "panel/api/setting/apiTokens/create",
                              {"name": "vpn-bot-%d" % int(time.time()),
                               "scope": "admin", "expiresAt": 0},
                              session=session, csrf=csrf, base=sec["base_path"])
        finally:
            await session.close()
        # Токен сохраняем первым: что бы ни случилось дальше, без него бот
        # потерял бы панель насовсем.
        sec["token"] = obj["token"]
        save_secrets(sec)
        notes.append("токен бота заведён")

    if sec.get("user") == "admin" and sec.get("password") == "admin":
        new_user = "vpn" + secrets.token_hex(3)
        new_password = secrets.token_urlsafe(18)
        await api("POST", "panel/api/setting/updateUser",
                  {"oldUsername": "admin", "oldPassword": "admin",
                   "newUsername": new_user, "newPassword": new_password})
        sec.update(user=new_user, password=new_password)
        save_secrets(sec)
        notes.append("заводской логин заменён")

    changed = await configure(admin_id)
    if changed:
        notes.append("настройки: " + ", ".join(changed))
    if await ensure_xray_dns():
        notes.append("DNS Xray — через Германию")
    if await ensure_inbound():
        notes.append("вход %d заведён" % INBOUND_PORT)
    return True, "; ".join(notes) or "всё уже на месте"


def public_host():
    """Как подписку и вход видят снаружи: имя узла или его адрес."""
    from utils import public_domain
    name = public_domain()
    if name:
        return name
    try:
        with open(PUBLIC_SUB_STATE, encoding="utf-8") as f:
            return (json.load(f) or {}).get("ip") or ""
    except Exception:
        return ""


def cert_ready():
    """Есть ли сертификат на имя узла — тогда подписка идёт по HTTPS."""
    from utils import public_domain
    try:
        return bool(public_domain()) and os.path.getsize(
            os.path.join(CERT_DIR_BOT, "fullchain.pem")) > 0 and os.path.getsize(
            os.path.join(CERT_DIR_BOT, "privkey.pem")) > 0
    except OSError:
        return False


async def configure(admin_id=0):
    """Настройки панели, которые ведёт бот. Возвращает список изменённого."""
    sec = load_secrets()
    cur = await api("POST", "panel/api/setting/all")
    want = dict(cur)
    host = public_host()
    tls = cert_ready()
    base = sec.get("base_path") or "/"
    if base == "/":
        # Панель на случайном пути: по голому адресу её не найти даже тому,
        # кто оказался в туннеле.
        base = "/" + secrets.token_hex(6) + "/"

    want.update(
        webBasePath=base,
        webPort=PANEL_PORT,
        subEnable=True,
        subPort=SUB_PORT,
        subListen="",
        subDomain=host,
        subCertFile=(CERT_DIR_PANEL + "/fullchain.pem") if tls else "",
        subKeyFile=(CERT_DIR_PANEL + "/privkey.pem") if tls else "",
        subTitle="VPN",
        subUpdates=12,
        timeLocation="Europe/Moscow",
        tgLang="ru-RU",
        # Профиль маршрутизации Happ — список обхода, как у AmneziaWG.
        subEnableRouting=True,
        subRoutingRules=await routing_link(),
    )
    token = (sec.get("tg_token") or "").strip()
    want["tgBotEnable"] = bool(token)
    if token:
        want["tgBotToken"] = token
        want["tgBotChatId"] = str(admin_id or sec.get("tg_chat") or "")

    changed = [k for k in ("webBasePath", "subDomain", "subCertFile", "subEnable",
                           "subPort", "tgBotEnable", "tgBotChatId",
                           "subEnableRouting", "subRoutingRules", "timeLocation")
               if cur.get(k) != want.get(k)]
    # Сам токен панель наружу не отдаёт — сверяем по отпечатку того, что
    # мы в прошлый раз ей передали.
    token_hash = hashlib.sha1(token.encode()).hexdigest() if token else ""
    if token and sec.get("tg_token_applied") != token_hash:
        changed.append("tgBotToken")

    # Где подписка — запоминаем всегда, а не только при изменениях: по этому
    # собираются ссылки людей, и потерянный файл не должен их ломать.
    sec["sub_path"] = cur.get("subPath") or "/sub/"
    sec["sub_host"] = host
    sec["sub_tls"] = tls
    if not changed:
        save_secrets(sec)
        return []

    await api("POST", "panel/api/setting/update", want)
    sec["tg_token_applied"] = token_hash
    # Путь, порт, подписка и бот применяются только перезапуском панели.
    try:
        await api("POST", "panel/api/setting/restartPanel", timeout=10)
    except XuiError:
        pass
    sec["base_path"] = base
    save_secrets(sec)
    await asyncio.sleep(4)
    if not await wait_panel(60):
        raise XuiError("панель не вернулась после перезапуска")
    return changed


async def refresh_routing():
    """Список обхода изменился — обновить профиль в подписке, без перезапуска
    всего остального. Меняется только одно поле."""
    if not stack_enabled() or not load_secrets().get("token"):
        return False
    cur = await api("POST", "panel/api/setting/all")
    link = await routing_link()
    if cur.get("subRoutingRules") == link and cur.get("subEnableRouting"):
        return False
    cur.update(subEnableRouting=True, subRoutingRules=link)
    await api("POST", "panel/api/setting/update", cur)
    try:
        await api("POST", "panel/api/setting/restartPanel", timeout=10)
    except XuiError:
        pass
    await asyncio.sleep(4)
    await wait_panel(60)
    return True


async def routing_link():
    """Профиль маршрутизации Happ ссылкой: только сайты с вкладки сплит-туннеля.

    Правило владельца: никаких адресов от кода — ни подсетей, ни внутренних
    адресов туннеля. Все шесть списков шлём явно, даже пустые: недостающие
    приложение дополняет из своего профиля по умолчанию, а там частные сети.

    Дата обновления привязана к содержимому: приложение обновляет профиль,
    только если дата новее, а увидев новую — перекачивает гео-файлы."""
    try:
        rows = await db.get_bypass_exclusions()
    except Exception:
        rows = []
    sites = sorted({(r["domain"] or "").strip().lower() for r in rows
                    if (r["domain"] or "").strip()
                    and not (r["domain"].strip()[0].isdigit() or ":" in r["domain"])})
    prof = {
        "Name": ROUTING_NAME,
        "GlobalProxy": "true",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSIP": "1.1.1.1",
        "DomesticDNSType": "DoU",
        "DomesticDNSDomain": "",
        "DomesticDNSIP": "77.88.8.8",
        "DnsHosts": {"cloudflare-dns.com": "1.1.1.1"},
        "Geoipurl": GEO_IP,
        "Geositeurl": GEO_SITE,
        "DirectSites": sites,
        "DirectIp": [],
        "ProxySites": [],
        "ProxyIp": [],
        "BlockSites": [],
        "BlockIp": [],
        "DomainStrategy": "AsIs",
        "FakeDNS": "false",
    }
    digest = hashlib.sha1(json.dumps(prof, ensure_ascii=False, sort_keys=True)
                          .encode()).hexdigest()
    try:
        saved = (await db.get_setting("xui_routing_stamp")) or ""
    except Exception:
        saved = ""
    was, _, when = saved.partition(" ")
    if was == digest and when.isdigit():
        stamp = int(when)
    else:
        stamp = max(int(time.time()), (int(when) + 1) if when.isdigit() else 0)
        try:
            await db.set_setting("xui_routing_stamp", "%s %d" % (digest, stamp))
        except Exception:
            pass
    prof["LastUpdated"] = str(stamp)
    raw = json.dumps(prof, ensure_ascii=False, separators=(",", ":"))
    return "happ://routing/onadd/" + base64.b64encode(raw.encode()).decode()


# DNS самого Xray. Без него Xray резолвит системным резолвером контейнера, а тот
# в сетевой области узла — встроенный DNS Docker, который спрашивает резолвер
# хоста, то есть российского провайдера. Провайдер на заблокированное отвечает
# «такого нет», и у людей на Xray не открывались ровно те сайты, ради которых
# VPN: YouTube, Instagram. Проверено на узле: через 127.0.0.11 — NXDOMAIN,
# через 1.1.1.1 — настоящий адрес.
#
# 1.1.1.1 и 8.8.8.8 — не российские адреса, поэтому запросы к ним узел сам
# уводит в Германию: перехват DNS по дороге им не грозит. Только IPv4 — выхода
# по IPv6 у узла нет, и шестёрка упёрлась бы в тупик.
XRAY_DNS = {"servers": ["1.1.1.1", "8.8.8.8"], "queryStrategy": "UseIPv4"}


async def ensure_xray_dns():
    """Прописывает DNS в шаблон Xray панели. True — пришлось менять."""
    obj = await api("POST", "panel/api/xray/")
    if isinstance(obj, str):
        obj = json.loads(obj)
    tpl = obj.get("xraySetting")
    if isinstance(tpl, str):
        tpl = json.loads(tpl)
    changed = False
    if tpl.get("dns") != XRAY_DNS:
        tpl["dns"] = dict(XRAY_DNS)
        changed = True
    for ob in tpl.get("outbounds") or []:
        # Прямой выход должен спрашивать имена у DNS самого Xray, а не у
        # системы: иначе настройка выше ничего не даёт.
        if ob.get("protocol") == "freedom":
            st = ob.setdefault("settings", {})
            if st.get("domainStrategy") != "UseIPv4":
                st["domainStrategy"] = "UseIPv4"
                changed = True
    if not changed:
        return False
    await api("POST", "panel/api/xray/update",
              {"xraySetting": json.dumps(tpl, ensure_ascii=False),
               "outboundTestUrl": obj.get("outboundTestUrl") or ""}, form=True)
    try:
        await api("POST", "panel/api/server/restartXrayService", timeout=30)
    except XuiError:
        pass
    return True


async def managed_inbound():
    """Вход, который ведёт бот, или None."""
    for ib in await api("GET", "panel/api/inbounds/list") or []:
        if ib.get("remark") == INBOUND_REMARK:
            return ib
    return None


async def ensure_inbound():
    """Заводит вход VLESS + Reality на 443, если его ещё нет. True — завели."""
    if await managed_inbound():
        return False
    keys = await api("GET", "panel/api/server/getNewX25519Cert")
    target = (await db.get_setting(KEY_TARGET)) or DEFAULT_TARGET
    target = target.split(":")[0].strip() or DEFAULT_TARGET
    # Одно имя, ровно то, на которое смотрит маска. Имён может быть
    # несколько, но тогда панель в каждую ссылку подставляет случайное — и
    # имя в подписке менялось бы от обновления к обновлению.
    names = [target]
    host = public_host()
    inbound = {
        "enable": True, "remark": INBOUND_REMARK, "listen": "",
        "port": INBOUND_PORT, "protocol": "vless", "expiryTime": 0, "total": 0,
        "shareAddrStrategy": "custom" if host else "node",
        "shareAddr": host,
        "settings": json.dumps({"clients": [], "decryption": "none", "fallbacks": []}),
        "streamSettings": json.dumps({
            "network": "tcp", "security": "reality",
            "tcpSettings": {"acceptProxyProtocol": False, "header": {"type": "none"}},
            "realitySettings": {
                "show": False, "xver": 0, "target": target + ":443",
                "serverNames": names, "privateKey": keys["privateKey"],
                "shortIds": [secrets.token_hex(4)],
                "settings": {"publicKey": keys["publicKey"], "fingerprint": "chrome",
                             "serverName": "", "spiderX": "/"}}}),
        "sniffing": json.dumps({"enabled": True, "destOverride": ["http", "tls", "quic"],
                                "routeOnly": True}),
    }
    await api("POST", "panel/api/inbounds/add", inbound)
    return True


# Маски, из которых владелец выбирает кнопкой. Крупные российские сайты с
# TLS 1.3 — проверено `xray tls ping`. Любую другую можно задать в панели.
TARGET_PRESETS = ("www.ozon.ru", "www.avito.ru", "ya.ru", "vk.com", "www.wildberries.ru")


async def set_target(host):
    """Сменить маску входа. Клиенты входа остаются на месте: настройки входа
    отправляются целиком, со списком клиентов, как их вернула панель.

    Людям надо обновить подписку — в ссылке меняется имя маски. Приложение
    делает это само раз в двенадцать часов или по кнопке «обновить»."""
    host = (host or "").strip().lower().split(":")[0]
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", host):
        raise XuiError("не похоже на имя сайта")
    ib = await managed_inbound()
    if not ib:
        raise XuiError("вход ещё не заведён")
    ss = ib["streamSettings"]
    if isinstance(ss, str):
        ss = json.loads(ss)
    settings = ib["settings"] if isinstance(ib["settings"], dict) else json.loads(ib["settings"])
    sniff = ib.get("sniffing") or {}
    if isinstance(sniff, str):
        sniff = json.loads(sniff)
    rs = ss.setdefault("realitySettings", {})
    rs["target"] = host + ":443"
    rs.pop("dest", None)
    rs["serverNames"] = [host]
    body = {k: ib.get(k) for k in ("enable", "remark", "listen", "port", "protocol",
                                   "expiryTime", "total", "shareAddrStrategy", "shareAddr")}
    body.update(settings=json.dumps(settings), streamSettings=json.dumps(ss),
                sniffing=json.dumps(sniff))
    await api("POST", "panel/api/inbounds/update/%d" % ib["id"], body)
    await db.set_setting(KEY_TARGET, host)
    return host


# --- доступ к панели и её бот ---------------------------------------------------

async def owner_ips(admin_id):
    """Адреса ключей владельца в туннеле — только с них открывается панель."""
    try:
        from acl import peer_ip_map
        mine = {u["uuid"] for u in await db.get_users_by_tg_id(admin_id)}
        return sorted(ip for uid, ip in (await peer_ip_map()).items() if uid in mine)
    except Exception:
        return []


async def node_gate(enabled, admin_id=0):
    """Открыть или закрыть входы стека на узле и пустить владельца к панели."""
    from utils import api_session, WG_API_URL
    ips = await owner_ips(admin_id) if enabled else []
    async with api_session() as session:
        async with session.post(f"{WG_API_URL}/xray/stack",
                                json={"enabled": bool(enabled), "panel_ips": ips},
                                timeout=15) as r:
            if r.status != 200:
                raise XuiError(f"узел отказал: {await r.text()}")
            return await r.json()


def panel_info():
    sec = load_secrets()
    return {
        "url": "http://10.13.13.1:%d%s" % (PANEL_PORT, _base(sec)),
        "user": sec.get("user") or "",
        "password": sec.get("password") or "",
        "ready": bool(sec.get("token")),
    }


def tg_token():
    return (load_secrets().get("tg_token") or "").strip()


def set_tg_token(token):
    sec = load_secrets()
    sec["tg_token"] = (token or "").strip()
    save_secrets(sec)


TG_TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")


async def tg_bot_username(token=None):
    """Имя бота панели по его токену — для кнопки «перейти в бота»."""
    token = token or tg_token()
    if not token:
        return ""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.telegram.org/bot{token}/getMe",
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                return (data.get("result") or {}).get("username") or ""
    except Exception:
        return ""


# --- люди ----------------------------------------------------------------------

def _email(name, uuid_val):
    """Имя клиента в панели: читаемое и уникальное. В панели по нему ищут
    глазами, поэтому имя человека, а хвост uuid — чтобы тёзки не сталкивались."""
    base = re.sub(r"[^\w.-]+", "_", name or "user", flags=re.UNICODE).strip("_") or "user"
    return f"{base[:24]}-{uuid_val[:4]}"


async def _client(email):
    try:
        obj = await api("GET", "panel/api/clients/get/" + quote(email, safe=""))
        return (obj or {}).get("client")
    except XuiError:
        return None


async def issue(uuid_val):
    """Выдаёт человеку доступ по Xray. Повторный вызов ничего не ломает:
    клиент уже есть — возвращается он же, с прежней подпиской."""
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        raise XuiError("человек не найден")
    row = await db.get_xui_client(uuid_val)
    if row and await _client(row["email"]):
        return row
    ib = await managed_inbound()
    if not ib:
        raise XuiError("вход Xray ещё не заведён")
    email = row["email"] if row else _email(user["name"], uuid_val)
    sub_id = row["sub_id"] if row else secrets.token_hex(8)
    tg = (user.get("tg_ids") or [0])[0] or 0
    client = {"email": email, "subId": sub_id, "flow": FLOW,
              "enable": bool(user.get("is_active", True)), "tgId": int(tg),
              "comment": uuid_val, "limitIp": 0, "totalGB": 0, "expiryTime": 0}
    await api("POST", "panel/api/clients/add", {"client": client, "inboundIds": [ib["id"]]})
    await db.add_xui_client(uuid_val, email, sub_id)
    return await db.get_xui_client(uuid_val)


async def revoke(uuid_val):
    """Отзывает доступ по Xray. Подписка перестаёт отдавать настройки."""
    row = await db.get_xui_client(uuid_val)
    if not row:
        return False
    try:
        await api("POST", "panel/api/clients/del/" + quote(row["email"], safe=""))
    except XuiError as e:
        if "not found" not in str(e).lower():
            raise
    await db.drop_xui_client(uuid_val)
    return True


async def set_enabled(uuid_val, enabled):
    row = await db.get_xui_client(uuid_val)
    if not row:
        return False
    c = await _client(row["email"])
    if not c:
        return False
    if bool(c.get("enable")) == bool(enabled):
        return True
    body = {"email": c["email"], "id": c.get("uuid") or c.get("id"),
            "subId": c.get("subId"), "flow": c.get("flow") or FLOW,
            "enable": bool(enabled), "tgId": c.get("tgId") or 0,
            "comment": c.get("comment") or uuid_val, "limitIp": c.get("limitIp") or 0,
            "totalGB": c.get("totalGB") or 0, "expiryTime": c.get("expiryTime") or 0}
    await api("POST", "panel/api/clients/update/" + quote(row["email"], safe=""), body)
    return True


async def sync_person(uuid_val, reason=""):
    """Пауза и разморозка действуют на оба канала сразу. Молча: панель может
    быть выключена, а главное дело (пауза на AmneziaWG) уже сделано."""
    if not stack_enabled():
        return
    try:
        user = await db.get_user_by_uuid(uuid_val)
        if user:
            await set_enabled(uuid_val, bool(user.get("is_active", True)))
    except Exception as e:
        print(f"Xray: состояние {uuid_val} не синхронизировано ({reason}): {e}")


async def sub_url(uuid_val):
    """Адрес подписки человека, или пусто."""
    row = await db.get_xui_client(uuid_val)
    sec = load_secrets()
    host = sec.get("sub_host") or public_host()
    if not row or not host:
        return ""
    scheme = "https" if sec.get("sub_tls") else "http"
    path = sec.get("sub_path") or "/sub/"
    if not path.endswith("/"):
        path += "/"
    return f"{scheme}://{host}:{SUB_PORT}{path}{row['sub_id']}"


async def online_uuids():
    """Кто сейчас на связи по Xray — по данным панели."""
    if not stack_enabled():
        return set()
    try:
        emails = set(await api("POST", "panel/api/clients/onlines") or [])
    except XuiError:
        return set()
    return {r["user_uuid"] for r in await db.list_xui_clients() if r["email"] in emails}


async def last_online():
    """uuid → когда был на связи (секунды), для тех, кто подключался."""
    if not stack_enabled():
        return {}
    try:
        seen = await api("POST", "panel/api/clients/lastOnline") or {}
    except XuiError:
        return {}
    out = {}
    for r in await db.list_xui_clients():
        ts = seen.get(r["email"])
        if ts:
            out[r["user_uuid"]] = int(ts) // 1000 if int(ts) > 10 ** 11 else int(ts)
    return out


async def traffic(uuid_val):
    row = await db.get_xui_client(uuid_val)
    if not row:
        return None
    try:
        return await api("GET", "panel/api/clients/traffic/" + quote(row["email"], safe=""))
    except XuiError:
        return None


async def status():
    """Сводка для экранов: жива ли панель, вход, сколько людей."""
    out = {"enabled": stack_enabled(), "panel": False, "inbound": None,
           "people": 0, "online": 0}
    try:
        out["people"] = len(await db.list_xui_clients())
    except Exception:
        pass
    if not out["enabled"]:
        return out
    out["panel"] = await ping()
    if out["panel"]:
        try:
            ib = await managed_inbound()
            if ib:
                rs = (ib.get("streamSettings") or {})
                if isinstance(rs, str):
                    rs = json.loads(rs)
                reality = rs.get("realitySettings") or {}
                out["inbound"] = {"port": ib.get("port"), "network": rs.get("network"),
                                  "target": reality.get("target") or reality.get("dest"),
                                  "enable": ib.get("enable")}
            out["online"] = len(await online_uuids())
        except Exception:
            pass
    return out

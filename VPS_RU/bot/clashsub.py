# -*- coding: utf-8 -*-
"""Подписка на ключ AmneziaWG для клиентов на ядре mihomo (Clash Mi и другие).

Не второй протокол и не второй вход. Подписка — ещё один способ получить ТОТ
ЖЕ ключ, что лежит в файле `.conf`: тот же закрытый ключ, тот же адрес в
туннеле, тот же сервер и те же параметры обфускации, только в формате профиля
Clash. Узел не отличает, откуда подключился человек, поэтому роли, фильтры,
лимиты, учёт трафика и имена внутри туннеля работают без единой правки.

Что это даёт сверх файла:
  • список обхода доезжает сам — приложение перечитывает профиль, перевыпуск
    ради новых исключений больше не нужен;
  • перевыпуск ключа доезжает сам — профиль собирается из того же файла, что
    получает человек, и после перевыпуска в нём уже новый ключ;
  • сплит не только по адресам, но и по именам сайтов.

Файл `.conf` остаётся как был: он нужен роутерам, серверам и всем, у кого нет
клиента на mihomo.

Источник правды — файл конфига человека в `/volumes/configs`. Отдельно ключи
нигде не хранятся: второе место означало бы, что однажды они разойдутся.
"""
import asyncio
import ipaddress
import json
import os
import re
import ssl
import time
from urllib.parse import quote

from aiohttp import web

from database import db
from utils import CONFIGS_DIR, public_domain

PUBLIC_PORT = 443
PATH_PREFIX = "/c/"
CERT_DIR = os.getenv("SUB_CERT_DIR", "/volumes/certs")
PUBLIC_SUB_STATE = "/volumes/flags/public_sub.json"
PROXY_NAME = "VPN"
# Как часто клиенту предлагается перечитывать профиль, в часах. Список обхода
# меняется редко, перевыпуск — ещё реже; шесть часов при тридцати людях — это
# сотня запросов в сутки на весь узел.
UPDATE_INTERVAL_HOURS = 6
# DNS — те же адреса, что в файле конфига человека, и тоже через туннель.
# Тогда для узла запрос ничем не отличается от запроса из приложения
# AmneziaWG: он так же заворачивает его на себя, когда у человека фильтры или
# в сети есть свои имена, и так же пропускает дальше, когда нет.
FALLBACK_DNS = ("1.1.1.1", "1.0.0.1")
TUNNEL_NET = "10.13.13.0/24"

# Та же защита, что у узла при сборке AllowedIPs (bypass_safe в ru_wg_api):
# кривая запись в списке обхода не должна увести мимо туннеля служебные сети
# или полинтернета.
BYPASS_MIN_PREFIX = 8
_PROTECTED = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
    "172.16.0.0/12", "192.168.0.0/16", "224.0.0.0/3", "240.0.0.0/4")]


def bypass_safe(cidr):
    try:
        net = ipaddress.ip_network(str(cidr).strip(), strict=False)
    except ValueError:
        return False
    if net.version != 4 or net.prefixlen < BYPASS_MIN_PREFIX:
        return False
    return not any(net.overlaps(p) for p in _PROTECTED)


# --- ФАЙЛ КОНФИГА ------------------------------------------------------------

def conf_path(name):
    """Файл конфига человека — там же, где его ищет выдача файла."""
    for fn in (f"{name}.conf", f"{name}_Full.conf"):
        p = CONFIGS_DIR / fn
        if p.exists():
            return p
    return None


def parse_conf(text):
    """Конфиг AmneziaWG → словарь: секции [Interface] и [Peer], ключи как есть."""
    out = {"Interface": {}, "Peer": {}}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            out.setdefault(section, {})
            continue
        if "=" in line and section:
            k, v = line.split("=", 1)
            out[section][k.strip()] = v.strip()
    return out


# Параметры обфускации, которые понимает mihomo. Наш сервер — AmneziaWG 1.0
# (Jc, Jmin, Jmax, S1, S2, H1–H4), но берём всё, что лежит в конфиге: если узел
# однажды перейдёт на новую версию, подписка повезёт её сама.
_AWG_INT = ("Jc", "Jmin", "Jmax", "S1", "S2", "S3", "S4")
_AWG_STR = ("H1", "H2", "H3", "H4", "I1", "I2", "I3", "I4", "I5")


def _q(value):
    """Строка в YAML. Двойные кавычки JSON — это корректный YAML."""
    return json.dumps(str(value), ensure_ascii=False)


def conf_dns(itf):
    """Адреса DNS из строки конфига. Не-адреса там — зона поиска, её
    mihomo не понимает, и она ему не нужна: имена он спрашивает целиком."""
    out = []
    for part in (itf.get("DNS") or "").split(","):
        part = part.strip()
        try:
            if ipaddress.ip_address(part).version == 4 and part not in out:
                out.append(part)
        except ValueError:
            continue
    return out or list(FALLBACK_DNS)


_SITE_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


def site_name(raw):
    """Имя сайта из списка обхода в том виде, в каком его спросит приложение:
    русские буквы — в punycode. Адрес вместо имени и мусор — пусто: правило
    по имени из них не сложится, а запятая сломала бы строку правила."""
    d = (raw or "").strip().lower().rstrip(".")
    if d.startswith("*."):
        d = d[2:]
    try:
        d = ".".join(p if p.isascii() else p.encode("idna").decode("ascii")
                     for p in d.split("."))
    except Exception:
        return ""
    if not _SITE_RE.match(d):
        return ""
    try:
        ipaddress.ip_address(d)
        return ""
    except ValueError:
        return d


def build_profile(name, conf, bypass_rows, zone):
    """Профиль Clash (mihomo) из конфига AmneziaWG и списка обхода.

    Сплит повторяет AllowedIPs файла: всё в туннель, кроме подсетей из списка
    обхода. Сверх того — имена сайтов из того же списка: правило по имени
    переживает и смену адреса сайта, и CDN."""
    itf, peer = conf["Interface"], conf["Peer"]
    host, _, port = peer["Endpoint"].rpartition(":")
    address = itf["Address"].split(",")[0].split("/")[0].strip()

    lines = [
        "# Профиль VPN: %s" % " ".join(str(name).split()),
        "# Тот же ключ, что в файле конфига AmneziaWG. Обновляется сам.",
        "mixed-port: 7890",
        "allow-lan: false",
        "mode: rule",
        "log-level: warning",
        "ipv6: false",
        "unified-delay: true",
        "tcp-concurrent: true",
        "tun:",
        "  enable: true",
        "  stack: mixed",
        "  auto-route: true",
        "  auto-detect-interface: true",
        "  dns-hijack:",
        "    - any:53",
        "dns:",
        "  enable: true",
        "  ipv6: false",
        "  enhanced-mode: fake-ip",
        "  fake-ip-range: 198.18.0.1/16",
        # Имена внутри туннеля получают настоящие адреса, иначе правило по
        # сети туннеля их не узнает.
        "  fake-ip-filter:",
        "    - %s" % _q("+." + zone),
        "    - %s" % _q("+.lan"),
        "  nameserver:",
    ]
    lines += ["    - %s" % _q("%s#%s" % (ip, PROXY_NAME)) for ip in conf_dns(itf)]
    lines += [
        "proxies:",
        "  - name: %s" % _q(PROXY_NAME),
        "    type: wireguard",
        "    server: %s" % _q(host),
        "    port: %d" % int(port),
        "    ip: %s" % _q(address),
        "    private-key: %s" % _q(itf["PrivateKey"]),
        "    public-key: %s" % _q(peer["PublicKey"]),
    ]
    if peer.get("PresharedKey"):
        lines.append("    pre-shared-key: %s" % _q(peer["PresharedKey"]))
    lines += [
        "    allowed-ips:",
        "      - 0.0.0.0/0",
        "    udp: true",
        "    mtu: %d" % int(itf.get("MTU") or 1280),
    ]
    awg = []
    for k in _AWG_INT:
        if itf.get(k, "").lstrip("-").isdigit():
            awg.append("      %s: %d" % (k.lower(), int(itf[k])))
    for k in _AWG_STR:
        if itf.get(k):
            awg.append("      %s: %s" % (k.lower(), _q(itf[k])))
    if awg:
        lines.append("    amnezia-wg-option:")
        lines += awg

    domains, cidrs = [], []
    for r in bypass_rows:
        d = site_name(r["domain"])
        if d and d not in domains:
            domains.append(d)
        for c in (r["cidrs"] or "").split(","):
            c = c.strip()
            if c and bypass_safe(c) and c not in cidrs:
                cidrs.append(c)

    lines += ["rules:",
              "  - IP-CIDR,%s,%s,no-resolve" % (TUNNEL_NET, PROXY_NAME),
              "  - DOMAIN-SUFFIX,%s,%s" % (zone, PROXY_NAME)]
    lines += ["  - DOMAIN-SUFFIX,%s,DIRECT" % d for d in domains]
    # Без no-resolve: соединение по имени тоже проверяется по адресу, как в
    # файле конфига, где мимо туннеля идёт всё, что попадает в эти сети.
    # Список короткий, так что лишний запрос имени — копейки.
    lines += ["  - IP-CIDR,%s,DIRECT" % c for c in cidrs]
    lines.append("  - MATCH,%s" % PROXY_NAME)
    return "\n".join(lines) + "\n"


async def profile_for(user):
    """Профиль человека или None, если файла конфига нет."""
    path = conf_path(user["name"])
    if not path:
        return None
    conf = parse_conf(path.read_text(encoding="utf-8", errors="ignore"))
    if not conf["Interface"].get("PrivateKey") or not conf["Peer"].get("Endpoint"):
        return None
    from dnsnames import zone
    return build_profile(user["name"], conf, await db.get_bypass_exclusions(), zone())


# --- АДРЕС ПОДПИСКИ ----------------------------------------------------------

def public_host():
    """Имя узла, а без него — его адрес (тот же, на который выпущен сертификат)."""
    name = public_domain()
    if name:
        return name
    try:
        with open(PUBLIC_SUB_STATE, encoding="utf-8") as f:
            return (json.load(f) or {}).get("ip") or ""
    except Exception:
        return ""


async def sub_url(user_uuid, rotate=False):
    """Адрес подписки человека. Пусто — отдавать не на чем (нет сертификата)."""
    host = public_host()
    if not host or not cert_ready():
        return ""
    token = await db.sub_token(user_uuid, rotate=rotate)
    return f"https://{host}{PATH_PREFIX}{token}"


# --- СЕРВЕР ------------------------------------------------------------------
# Порт смотрит в интернет: отвечать ему может кто угодно. Рубежи — те же, что
# держали прежнюю подписку и проверены на ней:
#   • форма токена проверяется до базы — чужой запрос не стоит похода в неё;
#   • частящий адрес и перебирающий токены получают отказ, не доходя до базы;
#   • одновременно — не больше шестнадцати, ждать очередь никто не будет;
#   • отказ всегда один и тот же: по нему не отличить «нет токена» от «закрыт».
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,64}$")
RATE_WINDOW = 60
RATE_LIMIT = 30
MISS_LIMIT = 10
BAN_SECONDS = 3600
MAX_INFLIGHT = 16
TRACK_MAX = 4096
SERVER_NAME = "nginx"

_rate = {}
_miss = {}
_inflight = None
_runner = None
_site = None
_ssl_ctx = None
_cert_seen = None


def _prune(now):
    for store, alive in ((_rate, RATE_WINDOW), (_miss, BAN_SECONDS)):
        for ip in [k for k, v in store.items() if now - v[0] > alive]:
            store.pop(ip, None)
    if len(_rate) > TRACK_MAX:
        _rate.clear()
    if len(_miss) > TRACK_MAX:
        _miss.clear()


def _too_fast(ip, now):
    slot = _rate.get(ip)
    if not slot or now - slot[0] > RATE_WINDOW:
        _rate[ip] = [now, 1]
        return False
    slot[1] += 1
    return slot[1] > RATE_LIMIT


def _banned(ip, now):
    slot = _miss.get(ip)
    return bool(slot) and slot[1] > now


def _note_miss(ip, now):
    slot = _miss.get(ip)
    if not slot or now - slot[0] > BAN_SECONDS:
        _miss[ip] = [now, 0.0, 1]
        return
    slot[2] += 1
    if slot[2] >= MISS_LIMIT and slot[1] <= now:
        slot[1] = now + BAN_SECONDS


def _not_found():
    body = ("<html>\r\n<head><title>404 Not Found</title></head>\r\n<body>\r\n"
            "<center><h1>404 Not Found</h1></center>\r\n<hr><center>"
            + SERVER_NAME + "</center>\r\n</body>\r\n</html>\r\n")
    return web.Response(status=404, body=body.encode(), content_type="text/html",
                        headers={"Server": SERVER_NAME})


@web.middleware
async def guard(request, handler):
    global _inflight
    now = time.time()
    ip = request.remote or "?"
    if len(_rate) > TRACK_MAX or len(_miss) > TRACK_MAX:
        _prune(now)
    if request.method not in ("GET", "HEAD"):
        return _not_found()
    if _banned(ip, now) or _too_fast(ip, now):
        return _not_found()
    if _inflight is None:
        _inflight = asyncio.Semaphore(MAX_INFLIGHT)
    if _inflight.locked():
        return web.Response(status=503, text="busy", headers={"Server": SERVER_NAME})
    async with _inflight:
        resp = await handler(request)
    resp.headers["Server"] = SERVER_NAME
    return resp


BROWSER_PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Подписка VPN</title>
<style>
 body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
 padding:24px;font:16px/1.5 system-ui,sans-serif;background:#f4f6f8;color:#1c2430}
 main{max-width:28rem;background:#fff;border-radius:14px;padding:24px 28px;
 box-shadow:0 2px 12px rgba(0,0,0,.08)}
 @media (prefers-color-scheme:dark){body{background:#12161c;color:#e6e9ee}main{background:#1c222b}}
</style></head><body><main>
<h1 style="font-size:1.3rem;margin-top:0">Это адрес подписки</h1>
<p>Он не для браузера. Скопируйте его и вставьте в приложение <b>Clash Mi</b>:
«Профили» → «＋» → «Добавить по ссылке».</p>
<p>Адрес личный — не передавайте его никому.</p>
</main></body></html>"""


async def handle_sub(request):
    now = time.time()
    ip = request.remote or "?"
    token = request.match_info.get("token", "")
    if not TOKEN_RE.match(token):
        _note_miss(ip, now)
        return _not_found()
    user = await db.sub_by_token(token)
    if not user:
        _note_miss(ip, now)
        return _not_found()
    # Человек открыл ссылку в браузере — объясняем, куда её вставлять, а не
    # показываем закрытый ключ простыней текста.
    if "text/html" in (request.headers.get("Accept") or ""):
        return web.Response(text=BROWSER_PAGE, content_type="text/html")
    body = await profile_for(user)
    if body is None:
        return _not_found()
    await db.sub_fetched(user["uuid"])
    up, down = await db.traffic_totals(user["uuid"])
    expire = int(user["expires_at"].timestamp()) if user.get("expires_at") else 0
    filename = quote("%s.yaml" % user["name"], safe="")
    return web.Response(
        body=body.encode(), content_type="text/yaml", charset="utf-8",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + filename,
            "profile-update-interval": str(UPDATE_INTERVAL_HOURS),
            # total=0 — без лимита по объёму: ограничение у нас по скорости и
            # поведению, а не по гигабайтам.
            "subscription-userinfo": "upload=%d; download=%d; total=0; expire=%d"
                                     % (up, down, expire),
            "Cache-Control": "no-store",
        })


async def handle_other(request):
    return _not_found()


def cert_paths():
    return (os.path.join(CERT_DIR, "fullchain.pem"), os.path.join(CERT_DIR, "privkey.pem"))


def cert_ready():
    try:
        return all(os.path.getsize(p) > 0 for p in cert_paths())
    except OSError:
        return False


def _cert_stamp():
    out = []
    for p in cert_paths():
        try:
            out.append(int(os.stat(p).st_mtime))
        except OSError:
            out.append(0)
    return tuple(out)


def _build_ssl():
    global _ssl_ctx, _cert_seen
    ctx = _ssl_ctx or ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(*cert_paths())
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        ctx.set_alpn_protocols(["http/1.1"])
    except NotImplementedError:
        pass
    _ssl_ctx, _cert_seen = ctx, _cert_stamp()
    return ctx


def make_app():
    app = web.Application(middlewares=[guard], client_max_size=4096)
    app.router.add_get(PATH_PREFIX + "{token}", handle_sub)
    app.router.add_route("*", "/{tail:.*}", handle_other)
    return app


async def _open():
    global _site
    if _site is not None or _runner is None or not cert_ready():
        return False
    site = web.TCPSite(_runner, "0.0.0.0", PUBLIC_PORT, ssl_context=_build_ssl(), backlog=64)
    await site.start()
    _site = site
    print(f"Подписка: слушаю {PUBLIC_PORT} по https")
    return True


async def _close():
    global _site, _ssl_ctx
    if _site is None:
        return False
    await _site.stop()
    _site, _ssl_ctx = None, None
    print("Подписка: сертификата нет — порт закрыт")
    return True


async def serve():
    """Поднимает сервер и следит за сертификатом.

    Без сертификата не слушаем вовсе: в профиле закрытый ключ, отдавать его
    открытым текстом нельзя. Сертификат продлили — перечитываем на месте, без
    перезапуска бота; убрали — закрываем порт."""
    global _runner
    runner = web.AppRunner(make_app(), access_log=None, keepalive_timeout=15,
                           max_line_size=4096, max_field_size=4096)
    await runner.setup()
    _runner = runner
    delay = 5
    while True:
        try:
            if not cert_ready():
                await _close()
            elif _site is None:
                await _open()
            elif _cert_stamp() != _cert_seen:
                _build_ssl()
                print("Подписка: сертификат перечитан")
        except Exception as e:
            print(f"Подписка: {e}")
        await asyncio.sleep(delay)
        delay = 600

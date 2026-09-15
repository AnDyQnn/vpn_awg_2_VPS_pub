import os
import json
import uuid
import subprocess
import urllib.request
import re
import time
import ipaddress
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel

# --- ДОСТУП К API ---
# Панель управления раздаёт приватный ключ сервера и управляет пирами, поэтому она
# закрыта двумя независимыми рубежами:
#   1) правила файрвола в setup_network() — порт недоступен ни с eth0, ни из туннеля;
#   2) общий токен ниже — на случай, если правила однажды слетят (iptables -F и т.п.).
# Токен НЕОБЯЗАТЕЛЕН: если он не задан (старый .env после обновления), API продолжает
# работать как раньше, но пишет предупреждение. Ломать прод обновлением нельзя, а дыру
# в этом случае всё равно закрывает файрвол.
API_TOKEN = os.getenv("API_TOKEN", "").strip()
# Прошлый ключ действует, пока новый не разошёлся: см. агент узла выхода.
API_TOKEN_PREV = os.getenv("API_TOKEN_PREV", "").strip()
OPEN_PATHS = {"/api/health"}          # health дёргает deploy.sh, секретов не отдаёт


def verify_token(request: Request):
    if not API_TOKEN:
        return
    if request.url.path in OPEN_PATHS:
        return
    if request.headers.get("X-Api-Key", "") != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI(dependencies=[Depends(verify_token)])

if not API_TOKEN:
    print("⚠️  API_TOKEN не задан — панель защищена только правилами файрвола. "
          "Добавьте API_TOKEN в .env обеих нод.")

# --- КОНФИГУРАЦИЯ ---
ENV_SERVER_URL = os.getenv("SERVER_URL") or os.getenv("SERVER_IP")
# Порт слушателя. После переезда на новый ключ он меняется навсегда, поэтому
# значение из окружения может оказаться устаревшим: файл-переопределение пишется
# в момент завершения переезда и переживает перезапуск контейнера.
PORT_OVERRIDE_FILE = "/etc/amnezia/amneziawg/listen_port"
SERVER_PORT = int(os.getenv("SERVERPORT", "51820"))
try:
    if os.path.exists(PORT_OVERRIDE_FILE):
        with open(PORT_OVERRIDE_FILE) as _f:
            SERVER_PORT = int(_f.read().strip())
except Exception:
    pass
VPN_SUBNET = os.getenv("INTERNAL_SUBNET", "10.13.13.0")

CONF_DIR = "/etc/amnezia/amneziawg" 
CONF_FILE = f"{CONF_DIR}/wg0.conf"
PRIVATE_KEY_FILE = f"{CONF_DIR}/private.key"
PUBLIC_KEY_FILE = f"{CONF_DIR}/public.key"

OBFUSCATION_PARAMS = (
    "Jc = 4\n"
    "Jmin = 40\n"
    "Jmax = 70\n"
    "S1 = 0\n"
    "S2 = 0\n"
    "H1 = 1\n"
    "H2 = 2\n"
    "H3 = 3\n"
    "H4 = 4\n"
)

# --- SPLIT-TUNNEL: дата-центро-враждебные РФ-сервисы ---
# Эти сервисы блокируют IP хостинга/дата-центра (а сервер — это VPS), поэтому через
# туннель они не работают. Их диапазоны ИСКЛЮЧАЮТСЯ из AllowedIPs нового конфига →
# клиент ходит на них через своё домашнее подключение (резидентский IP) → они снова
# работают. Список держим КОМПАКТНЫМ: каждый диапазон раздувает AllowedIPs и QR.
# routing_version в боте должен совпадать с ROUTING_VERSION ниже.
# ВАЖНО: фактический список исключений приходит от бота в запросе POST /peers
# (поле bypass_cidrs) — источник правды это БД бота (таблица bypass_exclusions).
# BYPASS_CIDRS ниже — лишь аварийный фолбэк, если бот ничего не передал.
ROUTING_VERSION = 1
BYPASS_CIDRS = [
    "213.59.252.0/22",   # gosuslugi.ru
    "109.207.0.0/18",    # www / esia.gosuslugi.ru
    "155.212.204.0/24",  # MAX (max.ru)
    "185.169.155.0/24",  # vseinstrumenti.ru
]

# --- GUARD SPLIT-TUNNEL (порт route_safe/keep_direct из OpenWRT-шлюза) ---------
# Bypass-диапазон уходит «напрямую» (исключается из AllowedIPs → мимо DE). Два риска:
#   1) слишком широкий CIDR (напр. 0.0.0.0/1) — увёл бы ПОЧТИ ВЕСЬ трафик мимо DE;
#   2) CIDR, пересекающий служебную/внутреннюю сеть ноды (RFC1918, loopback, CGNAT,
#      внутренняя сеть DE-туннеля 10.13.13.0/24, docker/host-подсеть eth0) — это
#      порвало бы внутренний роутинг/сам туннель.
# Такие кандидаты отбраковываем. Границы служебных сетей ВЫЧИСЛЯЕМ (не только хардкод):
# к спец-диапазонам добавляем реальную connected-подсеть eth0 контейнера.
BYPASS_MIN_PREFIX = 8   # CIDR шире /8 (меньший префикс) — запрещён
_SPECIAL_PROTECTED = [
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16",
    "224.0.0.0/3", "240.0.0.0/4",
]
_DE_TUNNEL_NET = "10.13.13.0/24"   # внутренняя сеть RU↔DE (входит в 10/8, но явно)

def _protected_nets():
    """Служебные/внутренние сети ноды: спец-диапазоны + ВЫЧИСЛЯЕМАЯ подсеть eth0
    контейнера (docker/host) + сеть DE-туннеля. Возвращает список ip_network."""
    nets = []
    for cidr in _SPECIAL_PROTECTED + [_DE_TUNNEL_NET]:
        try: nets.append(ipaddress.ip_network(cidr))
        except ValueError: pass
    try:
        out = subprocess.run("ip -o -4 addr show dev eth0", shell=True,
                             capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"inet\s+([\d.]+/\d+)", out)
        if m:
            nets.append(ipaddress.ip_network(m.group(1), strict=False))
    except Exception:
        pass
    return nets

def bypass_safe(cidr, min_prefix=BYPASS_MIN_PREFIX):
    """(ok, reason). Порт route_safe: отсекает слишком широкие CIDR и пересечения
    со служебными/внутренними/вычисленными сетями ноды. Идемпотентен, без мутаций."""
    try:
        net = ipaddress.ip_network(str(cidr).strip(), strict=False)
    except ValueError:
        return False, "не IPv4-подсеть"
    if net.version != 4:
        return False, "только IPv4"
    if net.prefixlen < min_prefix:
        return False, f"слишком широкий (/{net.prefixlen} < /{min_prefix}) — увёл бы почти весь трафик мимо DE"
    for p in _protected_nets():
        if net.overlaps(p):
            return False, f"пересекает служебную/внутреннюю сеть {p}"
    return True, "ok"

def build_split_allowed_ips(bypass_cidrs=None):
    """AllowedIPs = весь IPv4 МИНУС bypass-диапазоны, плюс ::/0.
    Клиент гонит в туннель всё, кроме проблемных РФ-сервисов (они идут напрямую).
    bypass_cidrs — список из БД бота; при отсутствии используется фолбэк BYPASS_CIDRS.
    ЗАЩИТА: небезопасные bypass (широкие/служебные) молча отбрасываем — даже кривая
    запись в БД не порвёт роутинг (см. bypass_safe)."""
    cidrs = bypass_cidrs if bypass_cidrs else BYPASS_CIDRS
    cidrs = [c for c in cidrs if bypass_safe(c)[0]]
    nets = [ipaddress.ip_network("0.0.0.0/0")]
    for cidr in cidrs:
        try:
            ex = ipaddress.ip_network(cidr)
        except ValueError:
            continue
        rebuilt = []
        for n in nets:
            if not n.overlaps(ex):
                rebuilt.append(n)
            elif ex.subnet_of(n):
                rebuilt.extend(n.address_exclude(ex))
            # иначе n целиком внутри ex — выкидываем
        nets = rebuilt
    return ", ".join(str(n) for n in nets) + ", ::/0"

if not os.path.exists(CONF_DIR):
    os.makedirs(CONF_DIR, exist_ok=True)

class PeerCreate(BaseModel):
    name: str
    dns_type: str = "classic"
    bypass_cidrs: Optional[List[str]] = None
    # Мастер может задать uuid сам. Нужно для перевыпуска: человек остаётся
    # прежним, меняется только пара ключей, и всё, что к нему привязано —
    # роли, фильтры, история — остаётся на месте.
    uid: Optional[str] = None

class BackupData(BaseModel):
    conf: str
    priv: str
    pub: str

class GhostTarget(BaseModel):
    public_key: str
    purge_config: bool = True

class AclGrant(BaseModel):
    cidr: str
    proto: str = "any"
    port: Optional[int] = None

class AclPeer(BaseModel):
    ip: str
    allow: List[AclGrant] = []

class AclApply(BaseModel):
    peers: List[AclPeer] = []

class DnsFilters(BaseModel):
    clients: dict = {}          # адрес пира -> список категорий
    common: list = []           # категории, включённые сразу всем
    custom: list = []           # свой список доменов владельца
    # Исключения: разрешено вопреки категории. Общие — всем, личные — адресу.
    allow_common: list = []
    allow_clients: dict = {}
    # Свои пулы: ключ категории -> список доменов. Узел кладёт их в тот же кэш,
    # откуда читает встроенные, и дальше не различает их вовсе.
    pools: dict = {}
    bot_link: str = ""          # куда человеку идти с вопросом «почему закрыто»

class DnsNames(BaseModel):
    # имя → адрес в туннеле. Разрешать имена в адреса — дело бота: у него база.
    names: dict = {}
    # адрес человека → верхний DNS, который он выбрал при выдаче ключа.
    # Без этого заворот на узел отнял бы у людей их выбор (например AdGuard).
    upstreams: dict = {}


class MigrationStart(BaseModel):
    port: int = 51821

class MigrationPeer(BaseModel):
    public_key: str
    client_ip: str

class MigrationDe(BaseModel):
    iface: str = "wg1"

class XrayConfig(BaseModel):
    config: dict
    # Адреса людей на Xray: узел поднимает их у себя, иначе отправлять
    # с них нечем — адрес должен принадлежать отправителю.
    addresses: List[str] = []

class ProtocolSwitch(BaseModel):
    name: str
    enabled: bool = True

def run_cmd(cmd):
    try:
        if isinstance(cmd, list):
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode().strip() if e.stderr else str(e)
        raise RuntimeError(err_msg)

def get_public_ip():
    try:
        return urllib.request.urlopen('https://ifconfig.me/ip').read().decode('utf8').strip()
    except Exception:
        return "127.0.0.1"

if ENV_SERVER_URL and ENV_SERVER_URL != "0.0.0.0":
    FINAL_SERVER_IP = ENV_SERVER_URL
else:
    FINAL_SERVER_IP = get_public_ip()

def read_config_blocks():
    if not os.path.exists(CONF_FILE): return[]
    with open(CONF_FILE, 'r') as f: content = f.read()
    pattern = r"(?m)^(?=\[Interface\]|\[Peer\]|# PAUSED \[Peer\])"
    blocks = re.split(pattern, content)
    return [b for b in blocks if b.strip()]

def setup_network():
    print("🔧 Configuring AmneziaWG Interface (RU Master)...")
    
    if not os.path.exists(PRIVATE_KEY_FILE):
        print("🔑 Generating server keys...")
        priv = subprocess.check_output(["wg", "genkey"]).decode().strip()
        with open(PRIVATE_KEY_FILE, "w") as f: f.write(priv)
        proc = subprocess.Popen(["wg", "pubkey"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        pub, _ = proc.communicate(input=priv.encode())
        with open(PUBLIC_KEY_FILE, "w") as f: f.write(pub.decode().strip())

    with open(PRIVATE_KEY_FILE, "r") as f: priv_key = f.read().strip()

    interface_block = f"[Interface]\nPrivateKey = {priv_key}\nListenPort = {SERVER_PORT}\n{OBFUSCATION_PARAMS}\n"
    
    if os.path.exists(CONF_FILE):
        with open(CONF_FILE, "r") as f: current_conf = f.read()
        if "Jc =" not in current_conf or "[Interface]" not in current_conf:
            blocks = read_config_blocks()
            peer_blocks = [b for b in blocks if b.strip().startswith("[Peer]") or b.strip().startswith("# PAUSED")]
            with open(CONF_FILE, "w") as f: f.write(interface_block + "\n" + "\n".join(peer_blocks))
    else:
        with open(CONF_FILE, "w") as f: f.write(interface_block)

    subprocess.run(["ip", "link", "delete", "wg0"], stderr=subprocess.DEVNULL)
    subprocess.Popen(["wireguard-go", "wg0"])
    time.sleep(1)

    server_ip_cidr = f"{VPN_SUBNET.rsplit('.', 1)[0]}.1/24"
    run_cmd(["ip", "address", "add", server_ip_cidr, "dev", "wg0"])
    
    temp_conf = f"/tmp/wg0_init.conf"
    with open(temp_conf, "w") as f: f.write(interface_block)
    
    run_cmd(["wg", "setconf", "wg0", temp_conf])
    run_cmd(["ip", "link", "set", "mtu", "1280", "up", "dev", "wg0"])

    # --- ФИКС rp_filter ДЛЯ АСИММЕТРИЧНОЙ МАРШРУТИЗАЦИИ ---
    # Отключаем строгую проверку обратного пути, чтобы ядро не уничтожало
    # ответы из внешнего интернета, которые приходят через туннель wg0.
    subprocess.run("sysctl -w net.ipv4.conf.all.rp_filter=0", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("sysctl -w net.ipv4.conf.default.rp_filter=0", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("sysctl -w net.ipv4.conf.eth0.rp_filter=0", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("sysctl -w net.ipv4.conf.wg0.rp_filter=0", shell=True, stderr=subprocess.DEVNULL)

    # Очистка таблиц iptables и маршрутов
    run_cmd("iptables -t nat -F")
    run_cmd("iptables -t mangle -F")
    run_cmd("iptables -F")
    subprocess.run("ip rule del fwmark 200 table 200", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("ip route flush table 200", shell=True, stderr=subprocess.DEVNULL)

    # Базовая логика для хождения в интернет
    run_cmd("iptables -P FORWARD ACCEPT")
    # eth0 валиден внутри контейнера Docker
    run_cmd("iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE")
    
    # Маскарадинг для самого интерфейса wg0
    run_cmd("iptables -t nat -A POSTROUTING -o wg0 -j MASQUERADE")
    
    run_cmd("iptables -A FORWARD -i wg0 -j ACCEPT")
    run_cmd("iptables -A FORWARD -o wg0 -j ACCEPT")

    # --- MSS CLAMPING (фикс «интернет периодически тупит» на крупных пакетах) ---
    # Двойной туннель (клиент → RU → DE) с MTU 1280. Крупные TCP-сегменты с DF-битом
    # (полноразмерные 1500Б от серверов/CDN) не влезают в туннель, а при заблокированном
    # ICMP «fragmentation needed» (частый случай у операторов/CDN) PMTU Discovery не
    # срабатывает → пакеты молча теряются, соединение виснет и «тупит» на крупных
    # передачах (страницы грузятся наполовину, видео буферизует, закачки встают), хотя
    # мелкие запросы проходят. Подрезаем MSS в SYN/SYN-ACK под реальный PMTU туннеля
    # (1280-40=1240), чтобы конечные хосты не слали сегменты крупнее, чем туннель несёт.
    # Правило ловит ОБЕ стороны рукопожатия (флаг SYN есть и в SYN, и в SYN-ACK), а через
    # FORWARD проходит и клиент→DE, и обратный трафик DE→клиент — значит обе стороны
    # клиентских TCP-сессий получают корректный MSS.
    # НЕфатально (как правила blocked_nets ниже): если на ядре нет модуля xt_TCPMSS,
    # нода всё равно поднимется на базовой логике, а не уйдёт в отказ на старте.
    subprocess.run("iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu", shell=True, stderr=subprocess.DEVNULL)

    # --- УМНАЯ МАРШРУТИЗАЦИЯ И ИЗОЛЯЦИЯ ---
    
    # 1. Исключения: Локальные сети и Docker-сети не отправляем в Германию
    for subnet in ["127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]:
        run_cmd(f"iptables -t mangle -A PREROUTING -d {subnet} -j RETURN")
        run_cmd(f"iptables -t mangle -A OUTPUT -d {subnet} -j RETURN")

    # 2. ИСКЛЮЧЕНИЕ ПЕТЛИ: Не маркировать трафик, который пришел ИЗ Германии
    run_cmd("iptables -t mangle -A PREROUTING -i wg0 -s 10.13.13.254 -j RETURN")
    
    # 3. ИСКЛЮЧЕНИЕ ПЕТЛИ 2: Зашифрованный трафик самого WireGuard идет мимо туннеля
    run_cmd("iptables -t mangle -A OUTPUT -p udp --sport 51820 -j RETURN")
    run_cmd("iptables -t mangle -A OUTPUT -p udp --dport 51820 -j RETURN")

    # Гарантируем существование наборов (наполняются скриптом update_ru_ips.sh):
    #   ru_nets      — гео-IP РФ (идут напрямую)
    #   blocked_nets — блокировки РКН (antifilter, принудительно в Германию)
    subprocess.run("ipset create ru_nets hash:net family inet hashsize 4096 maxelem 1000000 -exist", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("ipset create blocked_nets hash:net family inet hashsize 4096 maxelem 1000000 -exist", shell=True, stderr=subprocess.DEVNULL)

    # 3.5 ПРИНУДИТЕЛЬНЫЙ ОБХОД: заблокированные РКН ресурсы всегда уходят в Германию,
    #     даже если они размещены на российских IP (повышает качество обхода блокировок).
    #     Делаем НЕфатально: если blocked_nets недоступен, узел всё равно поднимется
    #     на базовой гео-логике, а не уйдёт в полный отказ.
    subprocess.run("iptables -t mangle -A PREROUTING -i wg0 -m set --match-set blocked_nets dst -j MARK --set-mark 200", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("iptables -t mangle -A OUTPUT -m set --match-set blocked_nets dst -j MARK --set-mark 200", shell=True, stderr=subprocess.DEVNULL)

    # 4. Маркируем трафик клиентов (VPN) для отправки в Германию, если это не РУ-сегмент
    run_cmd("iptables -t mangle -A PREROUTING -i wg0 -m set ! --match-set ru_nets dst -j MARK --set-mark 200")

    # 5. Маркируем локальный трафик бота (который живет в одной сети с API)
    run_cmd("iptables -t mangle -A OUTPUT -m set ! --match-set ru_nets dst -j MARK --set-mark 200")
    
    # Создаем отдельную таблицу маршрутизации
    subprocess.run("ip rule add fwmark 200 table 200", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("ip route add default dev wg0 table 200", shell=True, stderr=subprocess.DEVNULL)

    # --- БЕЗОПАСНОСТЬ: панель управления недоступна никому, кроме самого бота ---
    # Бот живёт в сетевом пространстве этого контейнера и ходит через 127.0.0.1, поэтому
    # порт 8000 можно закрыть и снаружи, и со стороны туннеля.
    # ВАЖНО: правила пишутся здесь, а не руками на сервере — setup_network() делает
    # iptables -F при каждом старте контейнера и снесла бы всё, добавленное вручную.
    run_cmd("iptables -A INPUT -i eth0 -p tcp --dport 8000 -j DROP")
    # Страница отказа живёт ТОЛЬКО внутри туннеля. Наружу её порты и так не
    # опубликованы, но закрываем явно: заглушка — вещь внутренняя, в интернете
    # ей делать нечего.
    run_cmd("iptables -A INPUT -i eth0 -p tcp --dport 80 -j DROP")
    # А вот 443 закрывать нельзя, когда включён Xray: это его вход, и люди
    # обязаны достучаться до него из интернета. Правило осталось с тех пор,
    # когда на 443 стояла страница отказа; после переезда страницы на 8443 оно
    # молча рубило подключения — на боевом узле 2881 пакет. Изнутри контейнера
    # при этом всё работало, поэтому выглядело как «конфиг не тот».
    if not proto_state().get("xray"):
        run_cmd("iptables -A INPUT -i eth0 -p tcp --dport 443 -j DROP")
    # Раньше закрывался только eth0, а клиенты приходят по wg0 — и любой пир мог забрать
    # приватный ключ сервера через /api/backup_config. Это и есть та самая дыра.
    run_cmd("iptables -A INPUT -i wg0 -p tcp --dport 8000 -j DROP")
    # Доступ к панели немецкого агента разрешён только с адреса мастера.
    run_cmd("iptables -A FORWARD -i wg0 -o wg0 -p tcp --dport 8000 ! -s 10.13.13.1 -j DROP")

    restore_peers()
    mig_restore()
    # Xray переживает перезапуск контейнера так же, как всё остальное:
    # состояние на диске, поднимаем по нему.
    if proto_state()["xray"]:
        xray_start()
    rebuild_accounting()
    rebuild_acl()
    rebuild_dns_filters()

# --- УЧЁТ ПАКЕТОВ ПО ПИРАМ -------------------------------------------------
# WireGuard считает по пирам только БАЙТЫ — пакетов он не отдаёт вовсе. А упирается
# узел именно в пакеты: на клиентский пакет уходит ~130 мкс процессорного времени,
# то есть потолок около 7-8 тысяч пакетов в секунду независимо от ширины канала.
# Поэтому заводим собственный учёт: отдельная цепочка с парой правил на каждого пира
# (входящее и исходящее направление). Правила без действия — они только считают и
# пропускают пакет дальше. Отсюда же берутся данные для лимитов, графиков и аналитики.
ACCT_CHAIN = "PEER_ACCT"


def _acct_ensure_chain(flush=True):
    """Создаёт цепочку учёта и вешает её первой в FORWARD, OUTPUT и INPUT.

    `flush=False` — когда надо лишь убедиться, что цепочка на месте, и добавить
    в неё пару счётчиков. С очисткой это обнулило бы учёт всех остальных.
    Первой — потому что ниже стоят правила ACCEPT, после которых до нас не дошло бы.

    Трёх точек не бывает много: пакет проходит ЛИБО через FORWARD (трафик пира
    AmneziaWG идёт транзитом), ЛИБО через OUTPUT/INPUT (трафик человека на Xray
    рождается и умирает на самом узле). Дважды один пакет не посчитается.

    В цепочке нет действий — только счёт, поэтому её появление в INPUT и OUTPUT
    ничего не решает и ничего не рвёт."""
    subprocess.run(f"iptables -N {ACCT_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    if flush:
        subprocess.run(f"iptables -F {ACCT_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    for chain in ("FORWARD", "OUTPUT", "INPUT"):
        check = subprocess.run(f"iptables -C {chain} -j {ACCT_CHAIN}", shell=True,
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if check.returncode != 0:
            subprocess.run(f"iptables -I {chain} 1 -j {ACCT_CHAIN}", shell=True,
                           stderr=subprocess.DEVNULL)


def acct_add(ip):
    """Два счётчика на пира: что он отправил и что получил."""
    for spec in (f"-s {ip}", f"-d {ip}"):
        check = subprocess.run(f"iptables -C {ACCT_CHAIN} {spec}", shell=True,
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if check.returncode != 0:
            subprocess.run(f"iptables -A {ACCT_CHAIN} {spec}", shell=True,
                           stderr=subprocess.DEVNULL)


def acct_del(ip):
    for spec in (f"-s {ip}", f"-d {ip}"):
        subprocess.run(f"iptables -D {ACCT_CHAIN} {spec}", shell=True,
                       stderr=subprocess.DEVNULL)


def rebuild_accounting():
    """Пересобирает счётчики по списку пиров из конфига (после рестарта контейнера)."""
    _acct_ensure_chain()
    for b in read_config_blocks():
        m = re.search(r"AllowedIPs\s*=\s*([\d.]+)/32", b)
        if m:
            acct_add(m.group(1))


def read_accounting():
    """Снимок счётчиков: адрес → отправлено/получено в пакетах и байтах.

    Мгновенной скорости здесь нет и быть не может — это накопительные значения.
    Пакеты в секунду считает тот, кто снимает два замера подряд (сборщик в боте)."""
    out = subprocess.run(f"iptables -nvxL {ACCT_CHAIN}", shell=True,
                         capture_output=True, text=True).stdout
    stats = {}
    for line in out.splitlines():
        parts = line.split()
        # Формат строки: pkts bytes target prot opt in out source destination.
        # У наших правил ДЕЙСТВИЯ НЕТ (они только считают), поэтому колонка target
        # пустая и полей получается восемь, а не девять — на этом парсер и спотыкался.
        if len(parts) < 8 or not parts[0].isdigit():
            continue
        pkts, byts, src, dst = int(parts[0]), int(parts[1]), parts[-2], parts[-1]
        if src != "0.0.0.0/0":                       # правило -s: это отдача пира
            ip = src.split("/")[0]
            rec = stats.setdefault(ip, {"tx_packets": 0, "tx_bytes": 0,
                                        "rx_packets": 0, "rx_bytes": 0})
            rec["tx_packets"], rec["tx_bytes"] = pkts, byts
        elif dst != "0.0.0.0/0":                     # правило -d: это приём пира
            ip = dst.split("/")[0]
            rec = stats.setdefault(ip, {"tx_packets": 0, "tx_bytes": 0,
                                        "rx_packets": 0, "rx_bytes": 0})
            rec["rx_packets"], rec["rx_bytes"] = pkts, byts
    return stats


# --- ДОСТУПЫ ВНУТРИ ТУННЕЛЯ (РОЛИ) ----------------------------------------
# Роли ограничивают только одно: кто из пиров к кому ходит ВНУТРИ туннеля.
# Интернета это не касается вовсе, и вот почему важно не перепутать: «мировой»
# трафик клиента тоже идёт через wg0 — он уходит в клиент-сервер 10.13.13.254.
# Поэтому цепочка вешается не на весь wg0→wg0, а только на адреса самого туннеля,
# и адрес агента из неё исключён первым правилом. Иначе роль отрезала бы человеку
# интернет вместо домашнего сервиса.
#
# Ключ доступа — адрес пира: WireGuard сам сверяет ключ с AllowedIPs (/32),
# подделать адрес источника клиент не может.
#
# Разрешение — RETURN, а не ACCEPT: ACCEPT оборвал бы обход FORWARD целиком,
# и ниже перестало бы работать правило, закрывающее панель агента от пиров.
ACL_CHAIN = "WG_ACL"
ACL_STATE_FILE = f"{CONF_DIR}/acl.json"
TUNNEL_NET = f"{VPN_SUBNET}/24"
DE_AGENT_IP = "10.13.13.254"


def _hook_after_accounting(chain, spec):
    """Вешает правило сразу после цепочки учёта.

    Порядок важен: учёт должен посчитать пакет до того, как мы его отбросим.
    Но если цепочка пуста, вставлять «вторым номером» нельзя — iptables просто
    откажет. Поэтому позиция считается по факту."""
    have = subprocess.run(f"iptables -S {chain}", shell=True,
                          capture_output=True, text=True).stdout.splitlines()
    # первая строка — политика цепочки (-P), правила идут за ней
    rules = [l for l in have if l.startswith("-A ")]
    pos = 2 if rules else 1
    subprocess.run(f"iptables -I {chain} {pos} {spec}", shell=True,
                   stderr=subprocess.DEVNULL)


def _acl_ensure_chain():
    subprocess.run(f"iptables -N {ACL_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -F {ACL_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    # Без привязки к интерфейсу: во время переезда пиры живут и на wg0, и на wg1,
    # а адрес назначения из туннельной сети однозначно говорит, что это свои.
    hook = f"-d {TUNNEL_NET} -j {ACL_CHAIN}"
    # FORWARD — транзит пиров AmneziaWG. OUTPUT — люди на Xray: их пакеты
    # рождаются на узле, через FORWARD не проходят вовсе, и без второй точки
    # роли на них просто не действовали бы.
    #
    # INPUT намеренно не трогаем: на адресах Xray никто ничего не слушает, зато
    # в INPUT приходят обращения пиров к самому узлу — к странице отказа, DNS и
    # панели. Правила ролей отрезали бы их человеку, у которого роль есть.
    for chain in ("FORWARD", "OUTPUT"):
        check = subprocess.run(f"iptables -C {chain} {hook}", shell=True,
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if check.returncode != 0:
            _hook_after_accounting(chain, hook)


def _acl_rule_spec(ip, grant):
    """Строит спецификацию правила. Порт без протокола бессмыслен, поэтому при
    указанном порте протокол обязателен — иначе правило молча не добавится."""
    spec = f"-s {ip} -d {grant['cidr']}"
    proto = (grant.get("proto") or "any").lower()
    port = grant.get("port")
    if proto in ("tcp", "udp"):
        spec += f" -p {proto}"
        if port:
            spec += f" --dport {port}"
    return spec


def apply_acl(peers):
    """Пересобирает цепочку целиком: список пиров с ограничениями и что каждому можно.
    Пира нет в списке — правил на него нет, и он ходит куда угодно (роли не назначены)."""
    _acl_ensure_chain()
    # Ответный трафик уже разрешённых сессий и весь путь в интернет через агента.
    subprocess.run(f"iptables -A {ACL_CHAIN} -d {DE_AGENT_IP} -j RETURN",
                   shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -A {ACL_CHAIN} -m conntrack "
                   f"--ctstate ESTABLISHED,RELATED -j RETURN",
                   shell=True, stderr=subprocess.DEVNULL)
    applied = 0
    for peer in peers:
        ip = peer.get("ip")
        if not ip:
            continue
        for grant in peer.get("allow", []):
            if not grant.get("cidr"):
                continue
            subprocess.run(f"iptables -A {ACL_CHAIN} {_acl_rule_spec(ip, grant)} -j RETURN",
                           shell=True, stderr=subprocess.DEVNULL)
            applied += 1
        # Замыкающий запрет — ЯВНЫЙ отказ, а не молчаливый DROP.
        # DROP заставляет клиента ждать таймаута: человек видит «висит» и идёт
        # чинить сеть, которая исправна. Отказ приходит мгновенно и читается как
        # «закрыто», а не «сломалось».
        subprocess.run(f"iptables -A {ACL_CHAIN} -s {ip} -p tcp "
                       f"-j REJECT --reject-with tcp-reset",
                       shell=True, stderr=subprocess.DEVNULL)
        subprocess.run(f"iptables -A {ACL_CHAIN} -s {ip} "
                       f"-j REJECT --reject-with icmp-port-unreachable",
                       shell=True, stderr=subprocess.DEVNULL)
    return applied


ACL_WEB_CHAIN = "WG_ACL_WEB"
# Куда уводить веб-запрос к закрытому сервису: порт клиента → порт страницы.
# 443 отдельно, потому что там нужен TLS, и отвечать по нему должен слушатель
# с сертификатом, а не обычный HTTP.
# Слева — порт, на который стучится человек, справа — порт страницы отказа.
# 443 уводится на 8443: сам 443 на узле занят входом Xray, и это не прихоть —
# трафик к нему неотличим от обычного HTTPS.
ACL_WEB_PORTS = {80: 80, 8080: 80, 8096: 80, 3000: 80, 443: 8443}
BLOCK_PAGE_IP = "10.13.13.1"            # страница отказа живёт на самом узле


def _acl_web_ensure_chain():
    subprocess.run(f"iptables -t nat -N {ACL_WEB_CHAIN}", shell=True,
                   stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -t nat -F {ACL_WEB_CHAIN}", shell=True,
                   stderr=subprocess.DEVNULL)
    hook = f"-d {TUNNEL_NET} -j {ACL_WEB_CHAIN}"
    # PREROUTING — для пиров, OUTPUT — для людей на Xray (их запрос рождается
    # на узле и в PREROUTING не попадает вовсе).
    for chain in ("PREROUTING", "OUTPUT"):
        check = subprocess.run(f"iptables -t nat -C {chain} {hook}", shell=True,
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if check.returncode != 0:
            subprocess.run(f"iptables -t nat -A {chain} {hook}", shell=True,
                           stderr=subprocess.DEVNULL)


def apply_acl_web(peers):
    """Веб-запрос к закрытому сервису уводит на страницу отказа.

    Зеркалит разрешения из основной цепочки: сначала RETURN для всего, что роль
    открыла, и только потом заворот. Иначе человек, которому сервис РАЗРЕШЁН,
    попал бы на страницу отказа вместо самого сервиса.

    Запрос после заворота адресован уже самому узлу и уходит в INPUT, поэтому
    запрет в FORWARD его не касается — порядок таблиц тут работает на нас."""
    _acl_web_ensure_chain()
    for peer in peers:
        ip = peer.get("ip")
        if not ip:
            continue
        for grant in peer.get("allow", []):
            if not grant.get("cidr"):
                continue
            subprocess.run(f"iptables -t nat -A {ACL_WEB_CHAIN} "
                           f"{_acl_rule_spec(ip, grant)} -j RETURN",
                           shell=True, stderr=subprocess.DEVNULL)
        for port, target in ACL_WEB_PORTS.items():
            subprocess.run(f"iptables -t nat -A {ACL_WEB_CHAIN} -s {ip} -p tcp "
                           f"--dport {port} -j DNAT "
                           f"--to-destination {BLOCK_PAGE_IP}:{target}",
                           shell=True, stderr=subprocess.DEVNULL)


def save_acl_state(peers):
    try:
        with open(ACL_STATE_FILE, "w") as f:
            json.dump({"peers": peers, "saved_at": int(time.time())}, f)
    except Exception as e:
        print(f"ACL state save warning: {e}")


def rebuild_acl():
    """Восстанавливает доступы после перезапуска контейнера: setup_network() чистит
    таблицы при каждом старте, поэтому состояние держим на диске, рядом с конфигом."""
    peers = []
    try:
        if os.path.exists(ACL_STATE_FILE):
            with open(ACL_STATE_FILE) as f:
                peers = (json.load(f) or {}).get("peers", [])
    except Exception as e:
        print(f"ACL state read warning: {e}")
    apply_acl(peers)
    apply_acl_web(peers)


# --- ФИЛЬТРАЦИЯ САЙТОВ ПО КАТЕГОРИЯМ --------------------------------------
# Фильтрует отдельный процесс (dnsfilter.py), здесь только две вещи: состояние
# на диске и заворот 53-го порта на себя для тех, у кого фильтры включены.
#
# Заворот нужен потому, что в уже выданных конфигах записан внешний DNS. Менять
# их означало бы перевыпуск всем — вместо этого узел молча забирает запросы себе,
# и только у тех, кого это касается. Ни один существующий конфиг не меняется.
DNS_CHAIN = "DNS_REDIR"
DNS_STATE_FILE = f"{CONF_DIR}/dns_filter.json"
DNS_LOCAL_IP = "10.13.13.1"


def ensure_block_page_reachable():
    """Заворот 443 → 8443 для самого узла.

    Резолвер отвечает на закрытый домен адресом узла. По 80 браузер попадает на
    страницу отказа, а по 443 — во вход Xray: 443 на узле занят им, и это не
    прихоть, трафик Xray должен быть неотличим от обычного HTTPS.

    Раньше этот заворот жил в цепочке доступов и строился по людям с ролями.
    У остальных — то есть у всех, кому включены только фильтры, — запрос уходил
    в Xray, тот пересылал рукопожатие на маскировочный сайт, и человек получал
    ошибку сертификата вместо объяснения, почему сайт закрыт.

    Правило безопасно: на 10.13.13.1:443 нет ничего, кроме страницы отказа.
    Клиенты Xray приходят на внешний адрес, а не на туннельный.
    """
    for chain in ("PREROUTING", "OUTPUT"):
        rule = (f"-d {BLOCK_PAGE_IP} -p tcp --dport 443 "
                f"-j REDIRECT --to-ports 8443")
        check = subprocess.run(f"iptables -t nat -C {chain} {rule}", shell=True,
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if check.returncode != 0:
            subprocess.run(f"iptables -t nat -A {chain} {rule}", shell=True,
                           stderr=subprocess.DEVNULL)


def _dns_ensure_chain():
    subprocess.run(f"iptables -t nat -N {DNS_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -t nat -F {DNS_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    hook = f"-i wg0 -j {DNS_CHAIN}"
    check = subprocess.run(f"iptables -t nat -C PREROUTING {hook}", shell=True,
                           stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    if check.returncode != 0:
        subprocess.run(f"iptables -t nat -I PREROUTING 1 {hook}", shell=True,
                       stderr=subprocess.DEVNULL)
    # Заворот страницы — рядом: он нужен ровно тем же людям и по тому же поводу.
    ensure_block_page_reachable()


def read_dns_full_state():
    """Всё сохранённое состояние фильтров целиком."""
    try:
        with open(DNS_STATE_FILE) as f:
            return json.load(f) or {}
    except Exception:
        return {}


def read_dns_clients():
    """Кому включена фильтрация — из сохранённого состояния."""
    try:
        with open(DNS_STATE_FILE) as f:
            return (json.load(f) or {}).get("clients", {})
    except Exception:
        return {}


def rebuild_dns_chain(clients=None, names=None, everyone=None):
    """Пересобирает цепочку заворота DNS ЦЕЛИКОМ.

    Источников два — фильтрация по людям и свои имена, — а цепочка одна.
    Раньше каждый пересобирал её сам и стирал чужие правила: включили фильтр —
    перестали отвечать имена, завели имя — перестала работать фильтрация.
    Поэтому единственная сборка, и она всегда учитывает оба источника.

    Что не передали — берётся с диска: вызывающему не нужно знать про чужое
    состояние, чтобы не затереть его."""
    if clients is None:
        clients = read_dns_clients()
    if names is None:
        names = read_dns_names()
    if everyone is None:
        state = read_dns_full_state()
        everyone = bool(state.get("common") or state.get("custom"))

    _dns_ensure_chain()
    redirected = 0
    # Сначала адресные правила фильтрации: они уже, и должны стоять выше.
    for ip, cats in (clients or {}).items():
        if not cats:
            continue
        for proto in ("udp", "tcp"):
            subprocess.run(
                f"iptables -t nat -A {DNS_CHAIN} -s {ip} -p {proto} --dport 53 "
                f"-j DNAT --to-destination {DNS_LOCAL_IP}:53",
                shell=True, stderr=subprocess.DEVNULL)
        redirected += 1

    # Затем общий заворот: он нужен и ради имён, и ради общих правил
    # фильтрации — и то и другое действует на всех.
    if names or everyone:
        for proto in ("udp", "tcp"):
            subprocess.run(
                f"iptables -t nat -A {DNS_CHAIN} -s {VPN_SUBNET}/24 -p {proto} "
                f"--dport 53 -j DNAT --to-destination {DNS_LOCAL_IP}:53",
                shell=True, stderr=subprocess.DEVNULL)
    return redirected


def apply_dns_filters(clients, everyone=False):
    """clients: {адрес: [категории]}. Пустой список категорий = фильтров нет.

    `everyone` — когда есть общие правила: тогда через узел должен идти DNS
    всей туннельной сети, иначе общий запрет не действовал бы ни на кого,
    кроме тех, кому и так включили личные категории."""
    return rebuild_dns_chain(clients=clients, everyone=everyone)


DNS_NAMES_FILE = f"{CONF_DIR}/dns_names.json"


def apply_dns_names(names, upstreams=None):
    """Записывает таблицу имён и пересобирает заворот DNS.

    Заворот общий, а не по адресам: имя должно работать у всех, иначе «зайди на
    дом.vpn» превращается в «зайди, если тебе включили». Пока имён нет ни одного,
    ничего не заворачиваем — поведение остаётся прежним, как было до этой
    возможности."""
    with open(DNS_NAMES_FILE, "w") as f:
        json.dump({"names": names or {}, "upstreams": upstreams or {},
                   "saved_at": int(time.time())}, f)
    rebuild_dns_chain(names=names)
    return len(names or {})


def read_dns_names():
    try:
        with open(DNS_NAMES_FILE) as f:
            return (json.load(f) or {}).get("names", {})
    except Exception:
        return {}


def save_pool_list(key, domains):
    """Свой пул — обычный файл категории в кэше узла.

    Так резолверу не нужно знать, что пул чем-то отличается от встроенной
    категории: он и не отличается, кроме того, что список пришёл от владельца,
    а не скачан.
    """
    safe = "".join(c for c in key if c.isalnum() or c in "-_")[:40]
    if not safe:
        return
    path = f"{CONF_DIR}/cache/dns/{safe}.txt"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(domains))
    except OSError as e:
        print(f"Свой пул {safe}: {e}")


def save_dns_state(clients, bot_link="", common=None, custom=None,
                   allow_common=None, allow_clients=None):
    try:
        with open(DNS_STATE_FILE, "w") as f:
            json.dump({"clients": clients, "bot_link": bot_link,
                       "common": list(common or []), "custom": list(custom or []),
                       # Разрешения проверяются раньше запретов: исключение,
                       # которое смотрят после, исключением не является.
                       "allow_common": list(allow_common or []),
                       "allow_clients": {k: list(v) for k, v in
                                         (allow_clients or {}).items()},
                       "saved_at": int(time.time())}, f)
    except Exception as e:
        print(f"DNS state save warning: {e}")


def read_dns_state():
    try:
        if os.path.exists(DNS_STATE_FILE):
            with open(DNS_STATE_FILE) as f:
                return (json.load(f) or {}).get("clients", {})
    except Exception as e:
        print(f"DNS state read warning: {e}")
    return {}


def refresh_dns_lists(clients, common=None):
    """Тянет списки только включённых категорий, в фоне — загрузка не должна
    задерживать ответ панели.

    Общие категории сюда тоже входят: без их списков общий запрет не сработал
    бы, а причина была бы не видна — фильтр просто не нашёл бы доменов."""
    cats = sorted({c for v in (clients or {}).values() for c in v} | set(common or []))
    if not cats:
        return
    subprocess.Popen(f"bash /app/update_dns_lists.sh '{' '.join(cats)}'",
                     shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def rebuild_dns_filters():
    state = read_dns_full_state()
    apply_dns_filters(read_dns_state(),
                      everyone=bool(state.get("common") or state.get("custom")))
    # Файл состояния читает и сам процесс фильтра — ссылка на бота лежит там же
    # и переживает перезапуск вместе с раскладкой.


# --- ПЕРЕЕЗД НА НОВЫЙ КЛЮЧ СЕРВЕРА ----------------------------------------
# Ключ сервера когда-то был доступен через открытую панель, поэтому его надо
# сменить. Просто перевыпустить его нельзя: ключ сервера прописан в конфиге у
# каждого, и смена на месте разом отключила бы всех.
#
# Поэтому рядом поднимается ВТОРОЙ интерфейс на другом порту, со своим ключом и
# усиленной обфускацией. Люди переезжают по одному, каждый в своё время; пока
# последний не переехал, старый интерфейс работает как работал. Ничего не
# выключается по таймеру — снос старого делает владелец кнопкой.
#
# Тем же заходом меняется обфускация: её параметры лежат в [Interface] и должны
# совпадать у клиента и сервера, то есть поменять их можно только вместе с
# выдачей нового конфига. Отдельного повода собирать всех ещё раз не будет.
MIG_IFACE = "wg1"
MIG_CONF = f"{CONF_DIR}/{MIG_IFACE}.conf"
MIG_PRIV = f"{CONF_DIR}/{MIG_IFACE}_private.key"
MIG_PUB = f"{CONF_DIR}/{MIG_IFACE}_public.key"
MIG_STATE = f"{CONF_DIR}/migration.json"
MIG_DEFAULT_PORT = 51821

# Усиленная обфускация для нового интерфейса. H1–H4 — типы заголовков, которые
# AmneziaWG подставляет вместо стандартных; S1/S2 — размеры мусорных вставок в
# рукопожатии. Значения должны совпадать у сервера и клиента, поэтому они
# фиксируются в момент старта переезда и попадают в каждый новый конфиг.
MIG_OBFUSCATION = {
    "Jc": 5, "Jmin": 50, "Jmax": 1000,
    "S1": 88, "S2": 136,
    "H1": 1148549232, "H2": 1584160764, "H3": 1215466561, "H4": 1861193563,
}


def mig_read_state():
    try:
        if os.path.exists(MIG_STATE):
            with open(MIG_STATE) as f:
                return json.load(f) or {}
    except Exception as e:
        print(f"Migration state read warning: {e}")
    return {}


def mig_write_state(state):
    try:
        with open(MIG_STATE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Migration state save warning: {e}")


def mig_iface_up():
    return subprocess.run(f"ip link show {MIG_IFACE}", shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def mig_routing_rules(add=True):
    """Те же правила маршрутизации, что и у основного интерфейса.

    Иначе переехавший получил бы туннель без умной маршрутизации: весь трафик
    пошёл бы мимо клиент-сервера, и РКН-заблокированное перестало бы открываться
    именно у тех, кто послушно переехал первым."""
    act = "-A" if add else "-D"
    cmds = [
        # Трафик ИЗ клиент-сервера метить нельзя — иначе он пойдёт по кругу.
        # Это правило часто забывают, а без него мир-трафик зацикливается.
        f"iptables -t mangle {act} PREROUTING -i {MIG_IFACE} -s {DE_AGENT_IP} -j RETURN",
        f"iptables -t mangle {act} PREROUTING -i {MIG_IFACE} -m set "
        f"--match-set blocked_nets dst -j MARK --set-mark 200",
        f"iptables -t mangle {act} PREROUTING -i {MIG_IFACE} -m set "
        f"! --match-set ru_nets dst -j MARK --set-mark 200",
        f"iptables {act} FORWARD -i {MIG_IFACE} -j ACCEPT",
        f"iptables {act} FORWARD -o {MIG_IFACE} -j ACCEPT",
        f"iptables -t nat {act} POSTROUTING -o {MIG_IFACE} -j MASQUERADE",
        f"iptables {act} INPUT -i {MIG_IFACE} -p tcp --dport 8000 -j DROP",
        f"iptables {act} FORWARD -i {MIG_IFACE} -o {MIG_IFACE} -p tcp "
        f"--dport 8000 ! -s 10.13.13.1 -j DROP",
        # Заворот DNS для тех, у кого включены фильтры: цепочка та же, просто
        # теперь она должна ловить и второй интерфейс.
        f"iptables -t nat {act} PREROUTING -i {MIG_IFACE} -j {DNS_CHAIN}",
    ]
    for c in cmds:
        subprocess.run(c, shell=True, stderr=subprocess.DEVNULL)
    if add:
        # Асимметричная маршрутизация: ответы из интернета приходят через туннель,
        # и строгая проверка обратного пути их бы уничтожала.
        subprocess.run(f"sysctl -w net.ipv4.conf.{MIG_IFACE}.rp_filter=0",
                       shell=True, stderr=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL)


def mig_start(port=MIG_DEFAULT_PORT):
    """Поднимает второй интерфейс. Старый не трогает вовсе."""
    if mig_iface_up():
        return mig_status()

    priv = subprocess.check_output(["wg", "genkey"]).decode().strip()
    proc = subprocess.Popen(["wg", "pubkey"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    pub, _ = proc.communicate(input=priv.encode())
    pub = pub.decode().strip()
    with open(MIG_PRIV, "w") as f:
        f.write(priv)
    os.chmod(MIG_PRIV, 0o600)
    with open(MIG_PUB, "w") as f:
        f.write(pub)

    # Формат тот же, что у основного интерфейса: wg setconf понимает только
    # PrivateKey, ListenPort и параметры обфускации. Address и MTU — дело ip.
    obf = "\n".join(f"{k} = {v}" for k, v in MIG_OBFUSCATION.items())
    interface_block = f"[Interface]\nPrivateKey = {priv}\nListenPort = {port}\n{obf}\n"
    with open(MIG_CONF, "w") as f:
        f.write(interface_block)
    os.chmod(MIG_CONF, 0o600)

    mig_bring_up(interface_block)
    mig_routing_rules(add=True)

    state = {"active": True, "port": port, "pubkey": pub,
             "started_at": int(time.time()), "obfuscation": MIG_OBFUSCATION,
             "moved": []}
    mig_write_state(state)
    return mig_status()


def mig_bring_up(interface_block):
    """Тот же способ, что и для основного интерфейса: свой процесс wireguard-go,
    затем настройка через wg setconf. Адрес интерфейсу НЕ даём — 10.13.13.1/24
    уже висит на wg0, а два одинаковых адреса на разных интерфейсах ядро не примет."""
    subprocess.run(["ip", "link", "delete", MIG_IFACE], stderr=subprocess.DEVNULL)
    subprocess.Popen(["wireguard-go", MIG_IFACE])
    time.sleep(1)
    tmp = f"/tmp/{MIG_IFACE}_init.conf"
    with open(tmp, "w") as f:
        f.write(interface_block)
    run_cmd(["wg", "setconf", MIG_IFACE, tmp])
    run_cmd(["ip", "link", "set", "mtu", "1280", "up", "dev", MIG_IFACE])


def mig_route(client_ip, add=True):
    """Точечный маршрут на переехавшего.

    Общий маршрут 10.13.13.0/24 ведёт в wg0 — без этого правила ответы человеку,
    который уже на новом интерфейсе, уходили бы в старый и терялись. Маршрут /32
    точнее, поэтому выигрывает именно для него и ни на кого больше не влияет."""
    cmd = (["ip", "route", "replace", f"{client_ip}/32", "dev", MIG_IFACE] if add
           else ["ip", "route", "del", f"{client_ip}/32", "dev", MIG_IFACE])
    subprocess.run(cmd, stderr=subprocess.DEVNULL)


def mig_restore():
    """Поднимает второй интерфейс после перезапуска контейнера — вместе с пирами
    и их маршрутами. Без этого переезд прерывался бы любым рестартом узла."""
    state = mig_read_state()
    if not state.get("active") or not os.path.exists(MIG_CONF):
        return
    try:
        with open(MIG_CONF) as f:
            content = f.read()
        interface_block = content.split("[Peer]")[0]
        mig_bring_up(interface_block)
        run_cmd(["wg", "addconf", MIG_IFACE, MIG_CONF])
        for m in re.finditer(r"AllowedIPs\s*=\s*([\d.]+)/32", content):
            mig_route(m.group(1), add=True)
        mig_routing_rules(add=True)
        print(f"Переезд: {MIG_IFACE} восстановлен после перезапуска")
    except Exception as e:
        print(f"Переезд: не удалось восстановить {MIG_IFACE}: {e}")


def de_iface():
    """На каком интерфейсе сейчас живёт клиент-сервер.

    Мир-трафик уходит в него маршрутом `default dev <iface> table 200`. Пока
    агент на старом интерфейсе — это wg0; как только он переехал, маршрут обязан
    переключиться, иначе весь «зарубеж» будет уходить в пустоту."""
    return mig_read_state().get("de_iface", "wg0")


def mig_move_de(iface):
    """Переключает мировой трафик на интерфейс, где теперь живёт агент."""
    subprocess.run(f"ip route replace default dev {iface} table 200",
                   shell=True, stderr=subprocess.DEVNULL)
    state = mig_read_state()
    state["de_iface"] = iface
    mig_write_state(state)
    return {"status": "ok", "de_iface": iface}


def mig_add_peer(public_key, client_ip):
    """Переносит пира на новый интерфейс. Ключ пира тот же самый: меняется ключ
    СЕРВЕРА, а не клиента, поэтому человеку не нужно заводить новое устройство."""
    if not mig_iface_up():
        raise RuntimeError("второй интерфейс не поднят")
    run_cmd(["wg", "set", MIG_IFACE, "peer", public_key,
             "allowed-ips", f"{client_ip}/32"])
    mig_route(client_ip, add=True)
    with open(MIG_CONF, "a") as f:
        f.write(f"\n[Peer]\nPublicKey = {public_key}\nAllowedIPs = {client_ip}/32\n")
    state = mig_read_state()
    moved = set(state.get("moved", []))
    moved.add(public_key)
    state["moved"] = sorted(moved)
    mig_write_state(state)
    return len(moved)


def mig_handshakes(iface):
    out = subprocess.run(f"wg show {iface} dump", shell=True,
                         capture_output=True, text=True).stdout
    res = {}
    for line in out.strip().splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 5:
            try:
                res[parts[0]] = int(parts[4])
            except ValueError:
                pass
    return res


def mig_status():
    state = mig_read_state()
    up = mig_iface_up()
    hs_new = mig_handshakes(MIG_IFACE) if up else {}
    hs_old = mig_handshakes("wg0")
    now = int(time.time())
    # «Переехал» — не тот, кому выдали конфиг, а тот, кто уже поздоровался на
    # новом интерфейсе. Выданный и не поставленный конфиг переездом не считается.
    connected = [k for k, ts in hs_new.items() if ts > 0]
    return {
        "active": bool(up and state.get("active")),
        "port": state.get("port"),
        "pubkey": state.get("pubkey"),
        "obfuscation": state.get("obfuscation", {}),
        "started_at": state.get("started_at"),
        "issued": len(state.get("moved", [])),
        "connected": len(connected),
        "old_peers": len(hs_old),
        "old_active": len([1 for ts in hs_old.values() if ts and now - ts < 86400]),
        "connected_keys": connected,
    }


def mig_abort():
    """Откат: сносим новый интерфейс, старый не трогали и не трогаем."""
    if mig_iface_up():
        mig_routing_rules(add=False)
        # Удаление интерфейса забирает с собой и его маршруты — отдельно чистить
        # каждый /32 не нужно.
        subprocess.run(["ip", "link", "delete", MIG_IFACE], stderr=subprocess.DEVNULL)
    for path in (MIG_CONF, MIG_PRIV, MIG_PUB):
        try:
            os.remove(path)
        except OSError:
            pass
    mig_write_state({"active": False})
    return {"status": "ok"}


def mig_finish():
    """Завершение: новый интерфейс СТАНОВИТСЯ основным.

    Можно было бы просто погасить wg0 и жить на wg1, но тогда пришлось бы
    переучивать на новое имя всё остальное: выдачу пиров, статус, маршрут в
    Германию, правила файрвола, самолечение. Поэтому делаем иначе — переносим
    новый ключ, порт, обфускацию и переехавших пиров в основной конфиг и
    поднимаем всё заново. После этого в системе снова ОДИН интерфейс wg0,
    просто с новым ключом, а второго нет вовсе.

    Не переехавшие сюда не попадают: их пиров в новом конфиге нет, и связь у них
    прекращается — ровно об этом и предупреждает экран подтверждения."""
    if not mig_iface_up():
        raise RuntimeError("второй интерфейс не поднят — завершать нечего")
    state = mig_read_state()
    port = state.get("port", MIG_DEFAULT_PORT)

    with open(MIG_CONF) as f:
        new_conf = f.read()
    if "[Peer]" not in new_conf:
        raise RuntimeError("на новый интерфейс ещё никто не переехал")

    # Новые ключи становятся ключами сервера.
    with open(MIG_PRIV) as f:
        priv = f.read().strip()
    with open(MIG_PUB) as f:
        pub = f.read().strip()
    with open(PRIVATE_KEY_FILE, "w") as f:
        f.write(priv)
    os.chmod(PRIVATE_KEY_FILE, 0o600)
    with open(PUBLIC_KEY_FILE, "w") as f:
        f.write(pub)

    # Конфиг основного интерфейса — это конфиг нового, целиком: его [Interface]
    # с новой обфускацией и его [Peer] тех, кто переехал.
    with open(CONF_FILE, "w") as f:
        f.write(new_conf)
    # Порт запоминаем отдельно: при следующем старте контейнера setup_network
    # собирает [Interface] заново и иначе вернул бы старый порт из окружения.
    with open(PORT_OVERRIDE_FILE, "w") as f:
        f.write(str(port))

    subprocess.run(["ip", "link", "delete", MIG_IFACE], stderr=subprocess.DEVNULL)
    mig_routing_rules(add=False)
    for path in (MIG_CONF, MIG_PRIV, MIG_PUB):
        try:
            os.remove(path)
        except OSError:
            pass

    state = {"finished_at": int(time.time()), "active": False,
             "promoted_port": port, "de_iface": "wg0"}
    mig_write_state(state)

    # Поднимаем основной интерфейс заново — уже с новым ключом и портом.
    globals()["SERVER_PORT"] = port
    setup_network()
    return {"status": "ok", "port": port,
            "note": "новый ключ стал основным, второй интерфейс убран"}


# --- XRAY: ВТОРОЙ ПРОТОКОЛ ------------------------------------------------
# Xray живёт процессом рядом с панелью, как и фильтр DNS, и по той же причине:
# у контейнера нет доступа к докеру, а значит перезапускать себя он должен сам.
#
# Почему это не ломает всё, что построено вокруг адресов: каждому человеку в
# конфиге Xray прописывается свой исходящий канал с его туннельным адресом
# (sendThrough). Поэтому наружу его трафик уходит с того же 10.13.13.x, что и
# по AmneziaWG — счётчики пакетов, лимиты, роли и фильтры продолжают узнавать
# человека, не зная и не интересуясь, каким протоколом он подключился.
#
# Узел намеренно НЕ знает, как устроен конфиг: его целиком собирает бот, у
# которого есть база. Здесь только записать, запустить и доложить состояние.
XRAY_BIN = "/usr/local/bin/xray"
XRAY_CONF = f"{CONF_DIR}/xray.json"
XRAY_STATE = f"{CONF_DIR}/protocols.json"
XRAY_PID = "/tmp/xray.pid"
XRAY_LOG = "/tmp/xray.log"

# Потолок памяти процессу Xray — мягкий, средствами самого рантайма Go.
#
# Жёсткий потолок через RLIMIT_AS здесь не работает, и это проверено на живом
# двоичном файле: Xray ЗАНИМАЕТ 29 МБ, а РЕЗЕРВИРУЕТ 1331 МБ адресного
# пространства. RLIMIT_AS считает второе, поэтому потолок в 256 МБ не страховал
# от утечки, а просто не давал процессу запуститься — при 512 МБ тоже.
#
# GOMEMLIMIT — мягкий потолок кучи: при подходе к нему сборщик мусора работает
# чаще. Процесс замедляется, но живёт и обслуживает людей, а утечка становится
# заметной постепенно, а не падением среди ночи. Жёсткую границу держит
# mem_limit контейнера в compose — он считает реально занятую память.
XRAY_MEM_LIMIT = "192MiB"
# Журнал писался дописыванием без предела, а лежит в записываемом слое
# контейнера — то есть рос на диске хоста. Норма та же, что у контейнеров в
# compose: три файла по 10 МБ, дальше старое вытесняется.
XRAY_LOG_LIMIT = 10 * 1024 * 1024
XRAY_LOG_KEEP = 3


def xray_ports():
    """Порты входов из применённого конфига — источник правды один.

    Вписывать их список в узел вторым экземпляром нельзя: мастер поменяет порт
    на экране, а узел продолжит открывать прежний, и вход окажется за
    закрытой дверью. Молча — ровно так уже было с 443.
    """
    try:
        with open(XRAY_CONF) as f:
            conf = json.load(f)
        found = [int(i["port"]) for i in conf.get("inbounds", []) if i.get("port")]
        return found or [443]
    except (OSError, ValueError, KeyError, TypeError):
        return [443]


def xray_port_gate(open_it: bool, ports=None):
    """Двери для Xray: порты входов снаружи.

    Открыты ровно пока Xray включён. Правила одинаковые, поэтому перед
    добавлением всегда сначала снимаем — иначе при повторных переключениях
    накопится десяток одинаковых строк.
    """
    for port in (ports if ports is not None else xray_ports()):
        rule = f"INPUT -i eth0 -p tcp --dport {port} -j DROP"
        while subprocess.run(f"iptables -C {rule}", shell=True,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL).returncode == 0:
            subprocess.run(f"iptables -D {rule}", shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not open_it:
            run_cmd(f"iptables -A {rule}")


def proto_state():
    """Какие протоколы включены. Нет файла — значит как было раньше:
    AmneziaWG работает, Xray ещё не поднимали."""
    try:
        if os.path.exists(XRAY_STATE):
            with open(XRAY_STATE) as f:
                s = json.load(f) or {}
                return {"awg": bool(s.get("awg", True)), "xray": bool(s.get("xray", False))}
    except Exception as e:
        print(f"Состояние протоколов не читается: {e}")
    return {"awg": True, "xray": False}


def save_proto_state(state):
    try:
        with open(XRAY_STATE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Состояние протоколов не сохранилось: {e}")


# Служебный интерфейс, на котором живут адреса людей, подключённых по Xray.
# Отдельный — чтобы их было видно одной командой и чтобы удаление интерфейса
# снимало разом все адреса, не задевая ничего чужого.
XRAY_IFACE = "xray0"
# Смещение адреса-двойника: 10.13.13.6 → 10.13.13.134. Отсюда предел в 126
# пиров AmneziaWG (адреса выше .127 заняты двойниками) — при тридцати людях
# запас десятикратный, но знать об этом надо.
XRAY_ADDR_OFFSET = 128


def xray_iface_ensure():
    subprocess.run(f"ip link add {XRAY_IFACE} type dummy", shell=True,
                   stderr=subprocess.DEVNULL)
    subprocess.run(f"ip link set up dev {XRAY_IFACE}", shell=True,
                   stderr=subprocess.DEVNULL)


def xray_addresses():
    """Какие адреса-двойники сейчас подняты на узле."""
    out = subprocess.run(f"ip -4 -o addr show dev {XRAY_IFACE}", shell=True,
                         capture_output=True, text=True).stdout
    return {m.group(1) for m in re.finditer(r"inet ([0-9.]+)/", out)}


def xray_sync_addresses(addrs):
    """Приводит адреса на узле в соответствие со списком от бота.

    Лишние снимаются: адрес, оставшийся после удаления человека, продолжал бы
    принимать ответы и считаться в статистике неизвестно за кого."""
    xray_iface_ensure()
    # Цепочка учёта может быть ещё не создана (первый запуск) — проверяем без
    # очистки, иначе обнулили бы счётчики всех пиров.
    _acct_ensure_chain(flush=False)
    want = {a for a in (addrs or []) if a}
    have = xray_addresses()
    for ip in want - have:
        subprocess.run(f"ip addr add {ip}/32 dev {XRAY_IFACE}", shell=True,
                       stderr=subprocess.DEVNULL)
        acct_add(ip)
    for ip in have - want:
        subprocess.run(f"ip addr del {ip}/32 dev {XRAY_IFACE}", shell=True,
                       stderr=subprocess.DEVNULL)
        acct_del(ip)
    return sorted(want)


def xray_log_rotate():
    """Ротация журнала по той же норме, что у контейнеров: три файла по 10 МБ.

    Обрезать «оставив хвост» было бы проще, но тогда пропадает начало беды —
    а именно оно обычно и объясняет, что случилось. Поэтому полноценная
    ротация: свежий файл начинается с нуля, два предыдущих остаются целыми."""
    try:
        if os.path.getsize(XRAY_LOG) < XRAY_LOG_LIMIT:
            return
    except OSError:
        return
    try:
        oldest = f"{XRAY_LOG}.{XRAY_LOG_KEEP - 1}"
        if os.path.exists(oldest):
            os.remove(oldest)
        for n in range(XRAY_LOG_KEEP - 2, 0, -1):
            src = f"{XRAY_LOG}.{n}"
            if os.path.exists(src):
                os.replace(src, f"{XRAY_LOG}.{n + 1}")
        os.replace(XRAY_LOG, f"{XRAY_LOG}.1")
    except OSError as e:
        print(f"Журнал Xray не повернулся: {e}")


def xray_running():
    """Жив ли процесс.

    Сигналом 0 проверять нельзя: он проходит и для зомби — процесса, который
    уже умер, но ещё не прибран родителем. Упавший Xray выглядел бы живым.
    Поэтому смотрим состояние в /proc: «Z» значит мёртв."""
    try:
        with open(XRAY_PID) as f:
            pid = int(f.read().strip())
        with open(f"/proc/{pid}/stat") as f:
            # имя процесса в скобках может содержать пробелы, поэтому режем
            # по последней скобке, а не по первому пробелу
            state = f.read().rsplit(")", 1)[1].split()[0]
        return state != "Z"
    except Exception:
        return False


def xray_check(path):
    """Проверяет конфиг силами самого Xray, ничего не запуская.

    Смысл в порядке действий: ошибка генератора обнаруживается ДО того, как
    рабочий процесс будет остановлен, — связь у людей не прерывается вовсе."""
    try:
        res = subprocess.run([XRAY_BIN, "run", "-test", "-c", path],
                             capture_output=True, text=True, timeout=20)
    except Exception as e:
        return False, f"проверка не выполнилась: {e}"
    if res.returncode == 0:
        return True, "конфиг корректен"
    lines = (res.stderr or res.stdout or "").strip().splitlines()
    return False, (lines[-1].strip() if lines else "Xray не принял конфиг")


def xray_stop():
    try:
        with open(XRAY_PID) as f:
            pid = int(f.read().strip())
        os.kill(pid, 15)
        time.sleep(0.5)
    except Exception:
        pass
    try:
        os.remove(XRAY_PID)
    except OSError:
        pass


def xray_start():
    """Поднимает процесс, если есть конфиг. Без конфига запускать нечего —
    это не ошибка, а просто «ещё никого не завели»."""
    if not os.path.exists(XRAY_CONF):
        return False, "конфиг ещё не создан"
    xray_stop()

    xray_log_rotate()

    # Порты входов могли смениться вместе с конфигом — двери приводим в
    # соответствие с тем, что в нём написано.
    try:
        xray_port_gate(True)
    except Exception as e:
        print(f"Двери Xray не открылись: {e}")

    xray_env = dict(os.environ, GOMEMLIMIT=XRAY_MEM_LIMIT)
    proc = subprocess.Popen([XRAY_BIN, "run", "-c", XRAY_CONF],
                            stdout=open(XRAY_LOG, "a"),
                            stderr=subprocess.STDOUT,
                            env=xray_env)
    with open(XRAY_PID, "w") as f:
        f.write(str(proc.pid))
    time.sleep(1)
    if not xray_running():
        return False, "процесс не удержался, смотри /tmp/xray.log"
    return True, "запущен"


def xray_apply(config, addresses=None):
    """Записывает конфиг от бота и перезапускает процесс.

    Две ступени защиты, потому что цена ошибки — связь у всех сразу:
      1. новый конфиг проверяется во временном файле, рабочий не трогается;
      2. если конфиг верен, а процесс всё равно не встал (занят порт, нет
         прав) — возвращается прежний конфиг и поднимается на нём."""
    # Адреса поднимаем ДО запуска: Xray при старте привязывается к ним, и
    # без адреса процесс просто не поднимется.
    xray_sync_addresses(addresses)

    prev = None
    if os.path.exists(XRAY_CONF):
        with open(XRAY_CONF) as f:
            prev = f.read()

    # Имя временного файла обязано кончаться на .json: Xray определяет формат
    # конфига по расширению и «.json.new» просто не понимает.
    tmp = XRAY_CONF[:-5] + ".new.json"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(tmp, 0o600)

    ok, note = xray_check(tmp)
    if not ok:
        os.remove(tmp)
        raise RuntimeError(f"конфиг не принят: {note}")

    os.replace(tmp, XRAY_CONF)

    if not proto_state()["xray"]:
        return {"status": "ok", "note": "конфиг записан, протокол выключен"}

    ok, note = xray_start()
    if not ok:
        if prev is not None:
            with open(XRAY_CONF, "w") as f:
                f.write(prev)
            xray_start()
            raise RuntimeError(f"процесс не поднялся ({note}), вернул прежний конфиг")
        raise RuntimeError(f"процесс не поднялся: {note}")
    return {"status": "ok", "note": note}


def xray_users_online():
    """Сколько сейчас установлено соединений к Xray. Не число людей, а именно
    соединений: одно устройство держит несколько."""
    try:
        out = subprocess.run("ss -tn state established '( sport = :443 )'",
                             shell=True, capture_output=True, text=True).stdout
        return max(0, len(out.strip().splitlines()) - 1)
    except Exception:
        return 0


def awg_down():
    """Гасит основной интерфейс. Люди на нём теряют связь — поэтому вызывается
    только по явной кнопке владельца и после показа, сколько их."""
    subprocess.run(["ip", "link", "set", "down", "dev", "wg0"], stderr=subprocess.DEVNULL)


def awg_up():
    setup_network()


def restore_peers():
    if not os.path.exists(CONF_FILE): return
    try:
        blocks = read_config_blocks()
        with open("/tmp/wg0_restore.conf", "w") as f:
            for b in blocks:
                if b.strip().startswith("[Peer]"): f.write(b)
        run_cmd(["wg", "addconf", "wg0", "/tmp/wg0_restore.conf"])
    except Exception as e:
        print(f"Restore warning: {e}")

setup_network()

def get_server_pubkey():
    if os.path.exists(PUBLIC_KEY_FILE):
        with open(PUBLIC_KEY_FILE, "r") as f: return f.read().strip()
    return "UNKNOWN"

def get_next_ip():
    used_ips = set(["1", "254"]) # Резервируем .1 (RU) и .254 (DE)
    blocks = read_config_blocks()
    for b in blocks:
        ip_match = re.search(r"AllowedIPs\s*=\s*[\d\.]+\.(\d+)/32", b)
        if ip_match: used_ips.add(ip_match.group(1))

    for i in range(2, 253):
        if str(i) not in used_ips:
            base = VPN_SUBNET.rsplit('.', 1)[0]
            return f"{base}.{i}"
    raise Exception("IP Limit Reached")

# --- API ENDPOINTS ---

@app.get("/api/backup_config")
def get_backup_config():
    try:
        conf, priv, pub = "", "", ""
        if os.path.exists(CONF_FILE):
            with open(CONF_FILE, "r") as f: conf = f.read()
        if os.path.exists(PRIVATE_KEY_FILE):
            with open(PRIVATE_KEY_FILE, "r") as f: priv = f.read()
        if os.path.exists(PUBLIC_KEY_FILE):
            with open(PUBLIC_KEY_FILE, "r") as f: pub = f.read()
        return {"wg0.conf": conf, "private.key": priv, "public.key": pub}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/restore_config")
def restore_backup_config(data: BackupData):
    try:
        with open(CONF_FILE, "w") as f: f.write(data.conf)
        with open(PRIVATE_KEY_FILE, "w") as f: f.write(data.priv)
        with open(PUBLIC_KEY_FILE, "w") as f: f.write(data.pub)
        setup_network()
        return {"status": "restored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    try:
        subprocess.run(["ip", "link", "show", "wg0"], check=True, capture_output=True)
        return {"status": "ok", "role": "RU_Master"}
    except Exception:
        raise HTTPException(status_code=500, detail="Interface wg0 is down")

@app.get("/api/status")
def status():
    try:
        output = subprocess.check_output(["wg", "show", "wg0", "dump"]).decode().strip().split('\n')
        total_peers, active_peers = 0, 0
        now = int(time.time())

        blocks = read_config_blocks()
        for b in blocks:
            if b.strip().startswith("[Peer]"): total_peers += 1

        if len(output) > 1:
            for line in output[1:]:
                parts = line.split('\t')
                if len(parts) >= 5:
                    try:
                        handshake = int(parts[4])
                        if handshake > 0 and (now - handshake) < 180: active_peers += 1
                    except ValueError: pass
        return {"peers_count": total_peers, "active_peers": active_peers, "status": "ok"}
    except Exception as e:
        return {"peers_count": 0, "active_peers": 0, "status": "error", "detail": str(e)}

@app.get("/api/peers")
def get_peers():
    try:
        output = subprocess.check_output(["wg", "show", "wg0", "dump"]).decode().strip().split('\n')
        pubkey_to_uuid = {}
        
        blocks = read_config_blocks()
        for b in blocks:
            uuid_match = re.search(r"# UUID = (\S+)", b)
            pub_match = re.search(r"PublicKey\s*=\s*(\S+)", b)
            if uuid_match and pub_match:
                pubkey_to_uuid[pub_match.group(1)] = uuid_match.group(1)

        peers =[]
        if len(output) > 1:
            for line in output[1:]:
                parts = line.split('\t')
                if len(parts) >= 7:
                    pubkey, endpoint = parts[0], parts[2]
                    # четвёртое поле wg-дампа — адрес пира в туннеле. Раньше просто
                    # выбрасывалось, из-за чего адрес негде было показать.
                    allowed = parts[3].split(",")[0].strip()
                    handshake = int(parts[4]) if parts[4].isdigit() else 0
                    rx, tx = int(parts[5]) if parts[5].isdigit() else 0, int(parts[6]) if parts[6].isdigit() else 0
                    peers.append({
                        "uuid": pubkey_to_uuid.get(pubkey, pubkey),
                        "public_key": pubkey,
                        "endpoint": endpoint,
                        "allowed_ips": allowed,
                        "latest_handshake": handshake,
                        "rx": rx, "tx": tx
                    })
        return peers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accounting")
def get_accounting():
    """Накопительные счётчики пакетов и байтов по адресам пиров.

    Мгновенной нагрузки здесь нет: пакеты в секунду считает сборщик в боте по
    разнице двух замеров. Так узел не хранит истории и остаётся без состояния."""
    try:
        return {"ts": int(time.time()), "peers": read_accounting()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/acl")
def set_acl(req: AclApply):
    """Принимает готовый список ограничений и применяет его целиком.

    Узел намеренно ничего не знает про роли: считать объединение прав — дело бота,
    у которого есть база. Сюда приходит уже готовый ответ на вопрос «кому куда можно»,
    а узел только раскладывает его в правила и запоминает на диск."""
    try:
        peers = [p.model_dump() if hasattr(p, "model_dump") else p.dict()
                 for p in req.peers]
        rules = apply_acl(peers)
        apply_acl_web(peers)
        save_acl_state(peers)
        return {"status": "ok", "peers": len(peers), "rules": rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/acl")
def get_acl():
    """Что реально стоит в правилах прямо сейчас — для аудита и сверки с базой."""
    try:
        out = subprocess.run(f"iptables -nvL {ACL_CHAIN}", shell=True,
                             capture_output=True, text=True).stdout
        state = {}
        if os.path.exists(ACL_STATE_FILE):
            with open(ACL_STATE_FILE) as f:
                state = json.load(f) or {}
        return {"saved_at": state.get("saved_at"),
                "peers": state.get("peers", []),
                "chain": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dns/filters")
def set_dns_filters(req: DnsFilters):
    """Принимает готовую раскладку «кому какие категории» и применяет её.

    Узел не знает ни про людей, ни про роли — только про адреса: кто есть кто,
    знает бот, у которого база. Здесь заворачивается порт и сохраняется состояние,
    а сам разбор запросов делает отдельный процесс."""
    try:
        clients = {str(k): list(v) for k, v in (req.clients or {}).items()}
        # Сохраняем ДО применения: состояние на диске — источник правды для
        # пересборки цепочки, и если применить раньше, пересборка ради имён
        # прочитает старое и сотрёт только что поставленные правила.
        common = [str(c) for c in (req.common or [])]
        custom = [str(d).lower().strip().strip(".") for d in (req.custom or []) if d]
        allow_common = [str(d).lower().strip().strip(".")
                        for d in (req.allow_common or []) if d]
        allow_clients = {str(k): [str(d).lower().strip().strip(".") for d in v if d]
                         for k, v in (req.allow_clients or {}).items()}
        # Свои пулы пишем в кэш до применения: резолвер читает списки оттуда,
        # и категории без файла он считает пустыми.
        for key, domains in (req.pools or {}).items():
            save_pool_list(str(key), [str(d) for d in domains if d])

        save_dns_state(clients, req.bot_link or "", common, custom,
                       allow_common, allow_clients)
        # Общие правила и свой список действуют на всех, поэтому заворачивать
        # DNS надо всем, а не только тем, у кого включены личные категории.
        count = apply_dns_filters(clients, everyone=bool(common or custom))
        refresh_dns_lists(clients, common)
        return {"status": "ok", "filtered": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dns/names")
def set_dns_names(req: DnsNames):
    """Принимает готовую таблицу «имя → адрес».

    Узел не знает ни про людей, ни про то, чьё это имя: адрес подставляет бот,
    у которого база. Поэтому перевыпуск ключа имя не ломает — просто приедет
    новая пара."""
    try:
        names = {str(k).lower().rstrip("."): str(v)
                 for k, v in (req.names or {}).items() if v}
        ups = {str(k): str(v) for k, v in (req.upstreams or {}).items() if v}
        count = apply_dns_names(names, ups)
        return {"status": "ok", "names": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dns/names")
def get_dns_names():
    try:
        return {"names": read_dns_names()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dns/filters")
def get_dns_filters():
    """Что стоит сейчас: раскладка по адресам и размеры загруженных списков."""
    try:
        lists = {}
        cache = f"{CONF_DIR}/cache/dns"
        if os.path.isdir(cache):
            for name in os.listdir(cache):
                if name.endswith(".txt"):
                    path = os.path.join(cache, name)
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        lists[name[:-4]] = sum(1 for line in f
                                               if line.strip() and not line.startswith("#"))
        return {"clients": read_dns_state(), "lists": lists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dns/hits")
def get_dns_hits(since: int = 0, limit: int = 500):
    """Попытки достучаться до закрытого — новее указанного времени.

    Узел знает только адрес в туннеле: кто за ним стоит и с какого внешнего
    адреса пришёл, знает бот. Поэтому здесь голые факты, а разбор — у него.
    """
    try:
        from dnsfilter import read_hits
        return {"hits": read_hits(since=since, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/migration/start")
def api_mig_start(req: MigrationStart):
    try:
        return mig_start(req.port)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/migration/status")
def api_mig_status():
    try:
        return mig_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/migration/peer")
def api_mig_peer(req: MigrationPeer):
    try:
        return {"status": "ok", "issued": mig_add_peer(req.public_key, req.client_ip),
                "server_pubkey": mig_read_state().get("pubkey"),
                "port": mig_read_state().get("port"),
                "obfuscation": mig_read_state().get("obfuscation", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/migration/de")
def api_mig_de(req: MigrationDe):
    """Переключает мировой трафик на интерфейс, где теперь живёт клиент-сервер."""
    try:
        return mig_move_de(req.iface)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/migration/abort")
def api_mig_abort():
    try:
        return mig_abort()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/migration/finish")
def api_mig_finish():
    try:
        return mig_finish()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/xray/config")
def api_xray_config(req: XrayConfig):
    """Принимает готовый конфиг от бота и применяет его."""
    try:
        return xray_apply(req.config, req.addresses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/xray/status")
def api_xray_status():
    """Состояние обоих протоколов — для экрана администрирования."""
    try:
        state = proto_state()
        awg_up_now = subprocess.run("ip link show wg0 up", shell=True,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL).returncode == 0
        # Порт и обфускация лежат в конфиге интерфейса — читаем оттуда, а не
        # держим вторую копию в настройках: копия однажды разойдётся с правдой.
        port, obf = 0, {}
        try:
            head = read_config_blocks()[0]
            m = re.search(r"ListenPort\s*=\s*(\d+)", head)
            if m:
                port = int(m.group(1))
            for key in ("Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4"):
                m = re.search(rf"^{key}\s*=\s*(\S+)", head, re.MULTILINE)
                if m:
                    obf[key] = m.group(1)
        except Exception:
            pass

        # Онлайн — по свежему рукопожатию, тем же мерилом, что и везде.
        online = 0
        try:
            now = int(time.time())
            dump = subprocess.run("wg show wg0 dump", shell=True,
                                  capture_output=True, text=True).stdout.splitlines()
            for line in dump[1:]:
                parts = line.split("	")
                if len(parts) >= 5 and parts[4].isdigit():
                    hs = int(parts[4])
                    if hs and now - hs < 180:
                        online += 1
        except Exception:
            online = -1

        return {
            "awg": {"enabled": state["awg"], "up": awg_up_now,
                    "peers": len(read_config_blocks()) - 1,
                    "port": port, "obfuscation": obf, "online": online},
            "xray": {"enabled": state["xray"], "up": xray_running(),
                     "connections": xray_users_online(),
                     "has_config": os.path.exists(XRAY_CONF)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/xray/keys")
def api_xray_keys():
    """Пара ключей для Reality — генерит сам Xray, нам её только передать."""
    try:
        out = subprocess.run([XRAY_BIN, "x25519"], capture_output=True, text=True).stdout
        keys = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                keys[k.strip().lower().replace(" ", "_")] = v.strip()
        if not keys:
            raise RuntimeError("не удалось сгенерировать ключи")
        return keys
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/protocols")
def api_protocols(req: ProtocolSwitch):
    """Включение и выключение протоколов.

    Выключить ОБА нельзя: это оставило бы узел без входа вообще, а вернуть его
    можно было бы только руками по SSH."""
    try:
        state = proto_state()
        if req.name not in ("awg", "xray"):
            raise RuntimeError("неизвестный протокол")
        other = "xray" if req.name == "awg" else "awg"
        if not req.enabled and not state[other]:
            raise RuntimeError("нельзя выключить оба протокола — узел останется без входа")

        state[req.name] = bool(req.enabled)
        save_proto_state(state)

        if req.name == "xray":
            # Дверь снаружи открывается вместе с протоколом: правило ставится
            # при старте контейнера, а переключают его кнопкой, на ходу.
            xray_port_gate(bool(req.enabled))
            if req.enabled:
                ok, note = xray_start()
            else:
                xray_stop()
                note = "остановлен"
        else:
            if req.enabled:
                awg_up()
                note = "поднят"
            else:
                awg_down()
                note = "погашен"
        return {"status": "ok", "state": state, "note": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reload")
def reload_vpn():
    try:
        setup_network()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- DE-FAILOVER (порт vpn-watchdog из OpenWRT) --------------------------------
# table 200 в норме = `default dev wg0` → мир/РКН-трафик уходит в Германию.
# Если DE лёг, этот трафик попадает в чёрную дыру. Fallback = зеркалим основной
# default-маршрут в table 200 → мир-трафик выходит НАПРЯМУЮ через eth0 (NAT уже есть),
# юзер не теряет интернет (РКН-сайты недоступны, пока DE не вернётся). Restore
# возвращает `default dev wg0`. Переключение атомарное и полностью обратимое.
DE_ROUTE_MODE_FILE = "/run/de_route_mode"

def _main_default_route():
    """Первый default-маршрут основной таблицы (в контейнере: 'via <docker-gw> dev eth0')."""
    out = subprocess.run("ip route show default", shell=True,
                         capture_output=True, text=True).stdout.strip()
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("default") and "wg0" not in line:
            return line
    return ""

def _set_de_route(mode):
    """mode='fallback' → мир-трафик напрямую через eth0; mode='vpn' → через DE (wg0)."""
    if mode == "fallback":
        dr = _main_default_route()
        if not dr:
            return False, "не нашёл основной default-маршрут"
        spec = dr[len("default"):].strip()   # 'via X dev eth0'
        subprocess.run(f"ip route replace default {spec} table 200",
                       shell=True, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(f"ip route replace default dev {de_iface()} table 200",
                       shell=True, stderr=subprocess.DEVNULL)
        mode = "vpn"
    try:
        with open(DE_ROUTE_MODE_FILE, "w") as f: f.write(mode)
    except Exception:
        pass
    return True, mode

@app.post("/routing/de-fallback")
def de_fallback():
    ok, detail = _set_de_route("fallback")
    if not ok:
        raise HTTPException(status_code=500, detail=detail)
    return {"ok": True, "mode": "fallback", "detail": detail}

@app.post("/routing/de-restore")
def de_restore():
    ok, detail = _set_de_route("vpn")
    return {"ok": ok, "mode": "vpn", "detail": detail}

@app.get("/routing/de-mode")
def de_mode():
    try:
        with open(DE_ROUTE_MODE_FILE) as f:
            return {"mode": f.read().strip() or "vpn"}
    except Exception:
        return {"mode": "vpn"}

class BypassCheck(BaseModel):
    cidrs: List[str]

@app.post("/routing/bypass-check")
def bypass_check(req: BypassCheck):
    """Валидация bypass-кандидатов (guard из OpenWRT): бот зовёт перед сохранением,
    чтобы отбраковать широкие/служебные CIDR с понятной причиной."""
    return {"results": [
        {"cidr": c, "ok": (r := bypass_safe(c))[0], "reason": r[1]}
        for c in req.cidrs
    ]}

@app.post("/api/peers")
def create_peer(req: PeerCreate):
    try:
        priv_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
        proc = subprocess.Popen(["wg", "pubkey"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        pub_key, _ = proc.communicate(input=priv_key.encode())
        pub_key = pub_key.decode().strip()
        
        server_pub = get_server_pubkey()
        
        is_de_agent = (req.name == "DE_AGENT")
        client_ip = "10.13.13.254" if is_de_agent else get_next_ip()
        # Свой uuid выдумываем, только если мастер не дал своего.
        uid = (req.uid or "").strip() or str(uuid.uuid4())

        target_dns = "94.140.14.14, 94.140.15.15" if req.dns_type == "adblock" else "1.1.1.1, 1.0.0.1"

        client_allowed_ips = "10.13.13.0/24" if is_de_agent else build_split_allowed_ips(req.bypass_cidrs)

        server_allowed_ips = "0.0.0.0/0, 10.13.13.254/32" if is_de_agent else f"{client_ip}/32"

        config_content = f"""
[Interface]
PrivateKey = {priv_key}
Address = {client_ip}/32
DNS = {target_dns}
MTU = 1280
{OBFUSCATION_PARAMS}

[Peer]
PublicKey = {server_pub}
Endpoint = {FINAL_SERVER_IP}:{SERVER_PORT}
AllowedIPs = {client_allowed_ips}
PersistentKeepalive = 25"""

        peer_block = f"\n[Peer]\n# Name = {req.name}\n# UUID = {uid}\nPublicKey = {pub_key}\nAllowedIPs = {server_allowed_ips}\n"
        
        with open(CONF_FILE, "a") as f: f.write(peer_block)
        run_cmd(["wg", "set", "wg0", "peer", pub_key, "allowed-ips", server_allowed_ips])
        if not is_de_agent:
            acct_add(client_ip)

        return {"uid": uid, "config": config_content, "client_ip": client_ip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kill_ghost")
def kill_ghost(target: GhostTarget):
    try:
        run_cmd(["wg", "set", "wg0", "peer", target.public_key, "remove"])
        if target.purge_config:
            blocks = read_config_blocks()
            new_blocks =[]
            for b in blocks:
                if (b.strip().startswith("[Peer]") or b.strip().startswith("# PAUSED")) and f"PublicKey = {target.public_key}" in b:
                    continue 
                new_blocks.append(b)
            with open(CONF_FILE, 'w') as f: f.write("".join(new_blocks))
        return {"status": "killed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/peers/{uid}/pause")
def pause_peer(uid: str):
    try:
        blocks = read_config_blocks()
        new_blocks =[]
        found = False
        for b in blocks:
            if f"# UUID = {uid}" in b:
                found = True
                if b.strip().startswith("# PAUSED"):
                    new_blocks.append(b)
                    continue
                pub_match = re.search(r"PublicKey\s*=\s*(\S+)", b)
                if pub_match:
                    try: run_cmd(["wg", "set", "wg0", "peer", pub_match.group(1).strip(), "remove"])
                    except: pass
                paused_b = "\n".join([f"# PAUSED {line}" if line.strip() else line for line in b.splitlines()]) + "\n"
                new_blocks.append(paused_b)
            else:
                new_blocks.append(b)

        if not found: raise HTTPException(status_code=404, detail="Peer not found")
        with open(CONF_FILE, "w") as f: f.write("".join(new_blocks))
        return {"status": "paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/peers/{uid}/resume")
def resume_peer(uid: str):
    try:
        blocks = read_config_blocks()
        new_blocks =[]
        found = False
        for b in blocks:
            if f"# UUID = {uid}" in b:
                found = True
                if not b.strip().startswith("# PAUSED"):
                    new_blocks.append(b)
                    continue
                active_b = "\n".join([line.replace("# PAUSED ", "", 1) for line in b.splitlines()]) + "\n"
                new_blocks.append(active_b)
                pub_match = re.search(r"PublicKey\s*=\s*(\S+)", active_b)
                ip_match = re.search(r"AllowedIPs\s*=\s*(\S+)", active_b)
                if pub_match and ip_match:
                    try: run_cmd(["wg", "set", "wg0", "peer", pub_match.group(1).strip(), "allowed-ips", ip_match.group(1).strip()])
                    except: pass
            else:
                new_blocks.append(b)

        if not found: raise HTTPException(status_code=404, detail="Paused peer not found")
        with open(CONF_FILE, "w") as f: f.write("".join(new_blocks))
        return {"status": "resumed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/peers/{uid}/retire")
def retire_peer(uid: str):
    """Помечает пира отработавшим, НЕ снимая его.

    При перевыпуске старый ключ обязан работать, пока человек не подключился
    новым: иначе перевыпуск рвёт связь. Но uuid у них теперь общий — человек
    ведь тот же, — и различать их надо. Помеченный возит трафик как прежде, а
    в списке выглядит как `retired-<uuid>`.

    Снимает его потом обычное удаление, по этому же помеченному имени.
    """
    try:
        blocks = read_config_blocks()
        marked = False
        out = []
        for b in blocks:
            if f"# UUID = {uid}" in b and "retired-" not in b:
                b = b.replace(f"# UUID = {uid}", f"# UUID = retired-{uid}", 1)
                marked = True
            out.append(b)
        if not marked:
            raise HTTPException(status_code=404, detail="Peer not found")
        with open(CONF_FILE, "w") as f:
            f.write("".join(out))
        return {"status": "retired", "uid": f"retired-{uid}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/peers/{uid}")
def delete_peer(uid: str):
    try:
        blocks = read_config_blocks()
        new_blocks =[]
        found = False
        for b in blocks:
            if f"# UUID = {uid}" in b:
                found = True
                pub_match = re.search(r"PublicKey\s*=\s*(\S+)", b)
                if pub_match:
                    try: run_cmd(["wg", "set", "wg0", "peer", pub_match.group(1).strip(), "remove"])
                    except: pass
                ip_match = re.search(r"AllowedIPs\s*=\s*([\d.]+)/32", b)
                if ip_match:
                    acct_del(ip_match.group(1))     # счётчик уходит вместе с пиром
                continue 
            new_blocks.append(b)

        if not found: raise HTTPException(status_code=404, detail="Peer not found")
        with open(CONF_FILE, "w") as f: f.write("".join(new_blocks))
        return {"status": "deleted"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
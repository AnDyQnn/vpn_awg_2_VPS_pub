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
    # Кому какие ОБЩИЕ категории не применять. Адрес -> список категорий.
    # Нужно затем, что общая категория иначе не снимается ни для кого: список
    # общих просто складывался со списком личных, и вывести из него одного
    # человека было нечем.
    except_clients: dict = {}
    # Свои пулы: ключ категории -> список доменов. Узел кладёт их в тот же кэш,
    # откуда читает встроенные, и дальше не различает их вовсе.
    pools: dict = {}
    bot_link: str = ""          # куда человеку идти с вопросом «почему закрыто»

class DnsNames(BaseModel):
    # Зона имён. Узел кладёт её в новые конфиги поисковым доменом: тогда система
    # достраивает короткое имя до полного сама, и человеку не надо набирать
    # третий уровень руками.
    zone: str = ""
    # имя → адрес в туннеле. Разрешать имена в адреса — дело бота: у него база.
    names: dict = {}
    # адрес человека → верхний DNS, который он выбрал при выдаче ключа.
    # Без этого заворот на узел отнял бы у людей их выбор (например AdGuard).
    upstreams: dict = {}


class ProtocolSwitch(BaseModel):
    name: str
    enabled: bool = True

class XrayStack(BaseModel):
    enabled: bool = False
    # Адреса владельца в туннеле: только с них открывается панель 3X-UI.
    panel_ips: List[str] = []

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

    # 3.4 ОТВЕТЫ НА ВХОДЯЩИЕ ОСТАЮТСЯ НА ТОМ ЖЕ ПУТИ, ПО КОТОРОМУ ПРИШЛИ.
    #
    # Правила ниже отправляют в Германию всё, что идёт не на российский адрес.
    # Задумано это про исходящий трафик — но под него попадали и ОТВЕТЫ на
    # входящие соединения. Человек с зарубежного адреса стучится на узел, сервис
    # отвечает, ответ видит «адрес не российский» и уходит в туннель. Клиент
    # не получает ничего: рукопожатие не складывается никогда.
    #
    # Снаружи это выглядело так, будто порты закрыты. Проверено с немецкого
    # узла: SSH (он живёт на хосте, мимо этих правил) отвечает, а 443, 2053,
    # 2083 и 2096 — нет. Российские адреса при этом подключаются нормально,
    # поэтому годами никто и не замечал.
    #
    # Лечится пометкой самого соединения: то, что пришло снаружи, помечаем, а
    # на исходящих пакетах такую метку узнаём и в Германию не отправляем.
    # Клиентский трафик (он приходит с wg0) этих правил не касается вовсе.
    # Первым правилом, а не последним. Выше по цепочке стоят RETURN для частных
    # сетей, и адрес самого контейнера (172.20.0.6) попадает в 172.16.0.0/12 —
    # входящий пакет выходил из цепочки раньше, чем доходил до пометки.
    # Проверено счётчиком: ноль пакетов.
    #
    # Ставить первым безопасно: пометка сама по себе ничего не маршрутизирует,
    # её только читает исключение в OUTPUT.
    run_cmd("iptables -t mangle -I PREROUTING 1 ! -i wg0 -m conntrack "
            "--ctstate NEW -j CONNMARK --set-mark 100")
    run_cmd("iptables -t mangle -I OUTPUT 1 -m connmark --mark 100 -j RETURN")

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
    # Входы Xray (443 — сам вход, 2096 — подписка) открыты, только пока
    # владелец включил стек 3X-UI. Выключен — закрыты явно: страница отказа
    # живёт на 8443 внутри туннеля, слушать эти порты больше некому.
    xray_gate_apply()
    # Раньше закрывался только eth0, а клиенты приходят по wg0 — и любой пир мог забрать
    # приватный ключ сервера через /api/backup_config. Это и есть та самая дыра.
    run_cmd("iptables -A INPUT -i wg0 -p tcp --dport 8000 -j DROP")
    # Доступ к панели немецкого агента разрешён только с адреса мастера.
    run_cmd("iptables -A FORWARD -i wg0 -o wg0 -p tcp --dport 8000 ! -s 10.13.13.1 -j DROP")

    # --- УПРАВЛЕНИЕ ПЕРЕГРУЗКОЙ TCP ВНУТРИ КОНТЕЙНЕРА ---------------------
    # Настройка на хосте сюда НЕ доходит: у контейнера своё сетевое
    # пространство, и способ управления перегрузкой у него свой. Проверено на
    # боевом узле: на хосте bbr, внутри cubic.
    #
    # Соединения, которые рождаются здесь же (бот, страница отказа, резолвер),
    # идут по правилам этого пространства, а не хоста.
    #
    # Нефатально: нет модуля в ядре хоста — остаёмся на прежнем способе.
    subprocess.run("sysctl -w net.ipv4.tcp_congestion_control=bbr",
                   shell=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    try:
        with open("/proc/sys/net/ipv4/tcp_congestion_control") as f:
            print(f"Управление перегрузкой TCP: {f.read().strip()}", flush=True)
    except Exception:
        pass

    restore_peers()
    rebuild_accounting()
    rebuild_acl()
    rebuild_dns_filters()
    # Обход фильтра через чужой DNS закрываем всегда: фильтр без этого держится
    # на честном слове телефона, а телефон по умолчанию спрашивает мимо нас.
    try:
        n = doh_block_apply(True)
        print(f"Обход фильтра через чужой DNS закрыт, правил: {n}", flush=True)
    except Exception as e:
        print(f"Запрет обходного DNS не встал: {e}", flush=True)

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
    идёт транзитом), ЛИБО через OUTPUT/INPUT (обращения к самому узлу и его
    ответы). Дважды один пакет не посчитается.

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
# Сам узел. Роль не имеет права его закрывать: на нём живут резолвер и страница
# отказа. Человек с ролью, которому закрыли узел, терял бы разрешение имён
# целиком: подключение вставало, но ничего не грузилось.
NODE_IP = f"{VPN_SUBNET.rsplit('.', 1)[0]}.1"


# --- ОБХОД ФИЛЬТРА ЧЕРЕЗ DNS ПОВЕРХ HTTPS И TLS ---------------------------
# Фильтр сайтов держится на том, что имена спрашивают у нас. Заворот на 53-м
# порту это обеспечивал — но только для обычного DNS.
#
# А телефон и браузер по умолчанию спрашивают иначе:
#
#   «Приватный DNS» в Android и iOS — это DNS поверх TLS, порт 853;
#   Chrome и Firefox — DNS поверх HTTPS, порт 443 к известным резолверам.
#
# Оба пути идут мимо нас, и фильтр выглядит сломанным, хотя он исправен:
# проверено на узле, запрещённое имя он отдаёт страницей отказа. Просто его не
# спрашивают.
#
# Закрываем оба. Отказ мгновенный, а не молчаливый: приложение, получив отказ,
# возвращается к обычному DNS — то есть к нам. Молчание же заставило бы его
# ждать таймаут и выглядело бы как «интернет тупит».
DOH_CHAIN = "DNS_BYPASS"
DOH_SET = "doh_nets"
# Известные резолверы DNS поверх HTTPS. Список намеренно короткий: сюда входят
# только адреса, которые кроме DNS ничего не отдают, — закрыть их на 443 ничего
# больше не ломает.
DOH_ADDRS = [
    "1.1.1.1", "1.0.0.1", "1.1.1.2", "1.0.0.2", "1.1.1.3", "1.0.0.3",
    "8.8.8.8", "8.8.4.4",
    "9.9.9.9", "9.9.9.10", "9.9.9.11", "149.112.112.112",
    "94.140.14.14", "94.140.15.15", "94.140.14.15", "94.140.15.16",
    "208.67.222.222", "208.67.220.220",
    "45.90.28.0/24", "45.90.30.0/24",
    "76.76.2.0/24", "76.76.10.0/24",
]


def doh_block_apply(enabled=True):
    """Собирает цепочку запрета обходных путей к чужому DNS.

    Вешается на те же две точки, что и правила ролей: транзит пиров и трафик,
    рождающийся на узле."""
    subprocess.run(f"ipset create {DOH_SET} hash:net family inet -exist",
                   shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f"ipset flush {DOH_SET}", shell=True, stderr=subprocess.DEVNULL)
    for addr in DOH_ADDRS:
        subprocess.run(f"ipset add {DOH_SET} {addr} -exist", shell=True,
                       stderr=subprocess.DEVNULL)

    subprocess.run(f"iptables -N {DOH_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -F {DOH_CHAIN}", shell=True, stderr=subprocess.DEVNULL)

    hook = f"-s {TUNNEL_NET} -j {DOH_CHAIN}"
    for chain in ("FORWARD", "OUTPUT"):
        have = subprocess.run(f"iptables -C {chain} {hook}", shell=True,
                              stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if enabled and have.returncode != 0:
            subprocess.run(f"iptables -A {chain} {hook}", shell=True,
                           stderr=subprocess.DEVNULL)
        elif not enabled and have.returncode == 0:
            subprocess.run(f"iptables -D {chain} {hook}", shell=True,
                           stderr=subprocess.DEVNULL)
    if not enabled:
        return 0

    rules = [
        # DNS поверх TLS: «Приватный DNS» в телефоне.
        f"-p tcp --dport 853 -j REJECT --reject-with tcp-reset",
        f"-p udp --dport 853 -j REJECT --reject-with icmp-port-unreachable",
        # DNS поверх HTTPS у известных резолверов — и по TCP, и по QUIC.
        f"-p tcp --dport 443 -m set --match-set {DOH_SET} dst "
        f"-j REJECT --reject-with tcp-reset",
        f"-p udp --dport 443 -m set --match-set {DOH_SET} dst "
        f"-j REJECT --reject-with icmp-port-unreachable",
        # Обычный DNS к чужим резолверам: заворот на 53 уже есть, но он в nat, а
        # его можно обойти, если резолвер слушает нестандартный порт. Здесь
        # закрываем сам факт похода к известному резолверу мимо нас.
        f"-p udp --dport 53 -m set --match-set {DOH_SET} dst "
        f"! -d {NODE_IP} -j REJECT --reject-with icmp-port-unreachable",
    ]
    for spec in rules:
        subprocess.run(f"iptables -A {DOH_CHAIN} {spec}", shell=True,
                       stderr=subprocess.DEVNULL)
    return len(rules)


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
    # Без привязки к интерфейсу: адрес назначения из туннельной сети однозначно
    # говорит, что это свои.
    hook = f"-d {TUNNEL_NET} -j {ACL_CHAIN}"
    # FORWARD — транзит пиров. OUTPUT — пакеты, рождённые на узле.
    #
    # INPUT намеренно не трогаем: в него приходят обращения пиров к самому
    # узлу — к странице отказа, DNS и панели. Правила ролей отрезали бы их
    # человеку, у которого роль есть.
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
    # Панель узла — закрыть до того, как разрешим узел целиком. В INPUT она
    # закрыта правилом с «-i wg0»; здесь — второй замок на случай, если пакет
    # придёт к узлу не с wg0.
    subprocess.run(f"iptables -A {ACL_CHAIN} -d {NODE_IP} -p tcp --dport 8000 "
                   f"-j REJECT --reject-with tcp-reset",
                   shell=True, stderr=subprocess.DEVNULL)
    # Сам узел — раньше любой роли: резолвер и страница отказа.
    subprocess.run(f"iptables -A {ACL_CHAIN} -d {NODE_IP} -j RETURN",
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
# 443 уводится на 8443: там слушает страница отказа с сертификатом.
ACL_WEB_PORTS = {80: 80, 8080: 80, 8096: 80, 3000: 80, 443: 8443}
BLOCK_PAGE_IP = "10.13.13.1"            # страница отказа живёт на самом узле


def _acl_web_ensure_chain():
    subprocess.run(f"iptables -t nat -N {ACL_WEB_CHAIN}", shell=True,
                   stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -t nat -F {ACL_WEB_CHAIN}", shell=True,
                   stderr=subprocess.DEVNULL)
    hook = f"-d {TUNNEL_NET} -j {ACL_WEB_CHAIN}"
    # PREROUTING — для пиров, OUTPUT — для запросов, рождённых на узле.
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
    страницу отказа, а по 443 — сюда: HTTPS-страница отказа слушает 8443.

    Раньше этот заворот жил в цепочке доступов и строился по людям с ролями.
    У остальных — то есть у всех, кому включены только фильтры, — человек
    получал ошибку соединения вместо объяснения, почему сайт закрыт.

    Правило безопасно: на 10.13.13.1:443 нет ничего, кроме страницы отказа.
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


def apply_dns_names(names, upstreams=None, zone=None):
    """Записывает таблицу имён и пересобирает заворот DNS.

    Заворот общий, а не по адресам: имя должно работать у всех, иначе «зайди на
    дом.vpn» превращается в «зайди, если тебе включили». Пока имён нет ни одного,
    ничего не заворачиваем — поведение остаётся прежним, как было до этой
    возможности."""
    with open(DNS_NAMES_FILE, "w") as f:
        json.dump({"names": names or {}, "upstreams": upstreams or {},
                   "zone": zone or "", "saved_at": int(time.time())}, f)
    rebuild_dns_chain(names=names)
    return len(names or {})


def dns_search_zone():
    """Зона имён, если она есть. Идёт в новые конфиги поисковым доменом.

    Смысл в одном: человек набирает «homelab», а система сама достраивает до
    «homelab.имя-узла». Без этого третий уровень приходится набирать руками
    каждый раз, а это ровно та мелочь, из-за которой удобной вещью перестают
    пользоваться.
    """
    try:
        with open(DNS_NAMES_FILE) as f:
            return str(json.load(f).get("zone") or "").strip().lower()
    except Exception:
        return ""


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
                   allow_common=None, allow_clients=None, except_clients=None):
    try:
        with open(DNS_STATE_FILE, "w") as f:
            json.dump({"clients": clients, "bot_link": bot_link,
                       "common": list(common or []), "custom": list(custom or []),
                       # Разрешения проверяются раньше запретов: исключение,
                       # которое смотрят после, исключением не является.
                       "allow_common": list(allow_common or []),
                       "allow_clients": {k: list(v) for k, v in
                                         (allow_clients or {}).items()},
                       "except_clients": {k: list(v) for k, v in
                                          (except_clients or {}).items()},
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


# --- ПРОТОКОЛЫ -----------------------------------------------------------
# Свой вход у узла один — AmneziaWG. Состояние выключателя лежит на диске,
# чтобы решение владельца переживало перезапуск контейнера.
PROTO_STATE = f"{CONF_DIR}/protocols.json"


def proto_state():
    """Состояние входов. Нет файла — AmneziaWG включён, стек Xray выключен.

    Стек Xray — панель 3X-UI в соседнем контейнере. Его состояние лежит под
    ключом `xui`, а не `xray`: под `xray` в старых файлах осталась запись от
    своего Xray, убранного в 8.63.0, и она открыла бы ворота сама."""
    state = {"awg": True, "xui": False, "panel_ips": []}
    try:
        if os.path.exists(PROTO_STATE):
            with open(PROTO_STATE) as f:
                s = json.load(f) or {}
            state["awg"] = bool(s.get("awg", True))
            state["xui"] = bool(s.get("xui", False))
            state["panel_ips"] = [str(ip) for ip in (s.get("panel_ips") or [])
                                  if _is_tunnel_ip(str(ip))]
    except Exception as e:
        print(f"Состояние протоколов не читается: {e}")
    return state


def _is_tunnel_ip(ip):
    """Адрес из сети туннеля — только такие пускаем к панели."""
    import ipaddress as _ip
    try:
        return _ip.ip_address(ip) in _ip.ip_network(f"{VPN_SUBNET}/24", strict=False)
    except ValueError:
        return False


# Порты стека Xray, опубликованные наружу: вход и подписка.
XRAY_PUBLIC_PORTS = (443, 2096)
XRAY_GATE_CHAIN = "XRAY_GATE"
# Панель 3X-UI. Наружу не публикуется; из туннеля — только владельцу.
XUI_PANEL_PORT = 2053
XUI_PANEL_CHAIN = "XUI_PANEL"


def xray_gate_apply(state=None):
    """Ворота стека Xray: входы снаружи и доступ к панели.

    Цепочки свои — перестраиваются целиком, ничего чужого не задевая, и
    переключаются на ходу, без перезапуска контейнера. Порядок в INPUT:
    зацепляем первыми, чтобы общие правила ниже не решили раньше нас."""
    state = state or proto_state()
    ports = ",".join(str(p) for p in XRAY_PUBLIC_PORTS)

    subprocess.run(f"iptables -N {XRAY_GATE_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -F {XRAY_GATE_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    hook = f"-i eth0 -p tcp -m multiport --dports {ports} -j {XRAY_GATE_CHAIN}"
    if subprocess.run(f"iptables -C INPUT {hook}", shell=True, stderr=subprocess.DEVNULL,
                      stdout=subprocess.DEVNULL).returncode != 0:
        subprocess.run(f"iptables -I INPUT 1 {hook}", shell=True, stderr=subprocess.DEVNULL)
    if not state.get("xui"):
        subprocess.run(f"iptables -A {XRAY_GATE_CHAIN} -j DROP", shell=True,
                       stderr=subprocess.DEVNULL)

    subprocess.run(f"iptables -N {XUI_PANEL_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f"iptables -F {XUI_PANEL_CHAIN}", shell=True, stderr=subprocess.DEVNULL)
    hook = f"-p tcp --dport {XUI_PANEL_PORT} -j {XUI_PANEL_CHAIN}"
    if subprocess.run(f"iptables -C INPUT {hook}", shell=True, stderr=subprocess.DEVNULL,
                      stdout=subprocess.DEVNULL).returncode != 0:
        subprocess.run(f"iptables -I INPUT 1 {hook}", shell=True, stderr=subprocess.DEVNULL)
    # Бот ходит к панели по петле — ему можно всегда.
    subprocess.run(f"iptables -A {XUI_PANEL_CHAIN} -i lo -j RETURN", shell=True,
                   stderr=subprocess.DEVNULL)
    for ip in state.get("panel_ips") or []:
        subprocess.run(f"iptables -A {XUI_PANEL_CHAIN} -i wg0 -s {ip}/32 -j RETURN",
                       shell=True, stderr=subprocess.DEVNULL)
    # Остальным — отказ сразу, а не молчание: владелец с чужого ключа увидит
    # «закрыто», а не будет ждать таймаута.
    subprocess.run(f"iptables -A {XUI_PANEL_CHAIN} -p tcp -j REJECT --reject-with tcp-reset",
                   shell=True, stderr=subprocess.DEVNULL)
    return state


def save_proto_state(state):
    try:
        with open(PROTO_STATE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Состояние протоколов не сохранилось: {e}")


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
        except_clients = {str(k): [str(c) for c in v if c]
                          for k, v in (req.except_clients or {}).items()}
        # Свои пулы пишем в кэш до применения: резолвер читает списки оттуда,
        # и категории без файла он считает пустыми.
        for key, domains in (req.pools or {}).items():
            save_pool_list(str(key), [str(d) for d in domains if d])

        save_dns_state(clients, req.bot_link or "", common, custom,
                       allow_common, allow_clients, except_clients)
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
        count = apply_dns_names(names, ups, (req.zone or "").strip().lower())
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


@app.get("/api/dns/bypass-status")
def api_dns_bypass_status():
    """Сколько правил запрета обходного DNS стоит сейчас.

    Нужна сверке: без этого запрета фильтр держится на честном слове телефона,
    а телефон по умолчанию спрашивает имена мимо нас."""
    out = subprocess.run(f"iptables -S {DOH_CHAIN}", shell=True,
                         capture_output=True, text=True).stdout
    rules = [l for l in out.splitlines() if l.startswith("-A ")]
    hooked = 0
    for chain in ("FORWARD", "OUTPUT"):
        body = subprocess.run(f"iptables -S {chain}", shell=True,
                              capture_output=True, text=True).stdout
        if DOH_CHAIN in body:
            hooked += 1
    return {"rules": len(rules), "hooked": hooked}


@app.get("/api/awg/status")
def api_awg_status():
    """Состояние AmneziaWG — для экрана администрирования."""
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
                    "port": port, "obfuscation": obf, "online": online}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/protocols")
def api_protocols(req: ProtocolSwitch):
    """Включение AmneziaWG.

    Выключить единственный вход нельзя: узел остался бы без связи, а вернуть
    его можно было бы только руками по SSH."""
    try:
        if req.name != "awg":
            raise RuntimeError("неизвестный протокол")
        if not req.enabled:
            raise RuntimeError("AmneziaWG — единственный вход узла, выключать его нельзя")
        state = proto_state()
        state["awg"] = True
        save_proto_state(state)
        awg_up()
        return {"status": "ok", "state": state, "note": "поднят"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/xray/stack")
def api_xray_stack_get():
    """Что сейчас с воротами стека Xray."""
    state = proto_state()
    rules = subprocess.run(f"iptables -S {XRAY_GATE_CHAIN}", shell=True,
                           capture_output=True, text=True).stdout
    return {"enabled": state["xui"], "panel_ips": state["panel_ips"],
            "gate_open": "-j DROP" not in rules}


@app.post("/api/xray/stack")
def api_xray_stack(req: XrayStack):
    """Открыть или закрыть входы стека Xray и задать, кому видна панель.

    Сам контейнер 3X-UI включает и выключает хост (профиль compose): у узла
    нет доступа к докеру. Здесь — только правила, и они меняются на ходу."""
    try:
        state = proto_state()
        state["xui"] = bool(req.enabled)
        state["panel_ips"] = [ip for ip in req.panel_ips if _is_tunnel_ip(ip)]
        save_proto_state(state)
        xray_gate_apply(state)
        return {"status": "ok", "enabled": state["xui"], "panel_ips": state["panel_ips"]}
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
        # Германия всегда на wg0: второго интерфейса (переезд на новый ключ)
        # больше нет.
        subprocess.run("ip route replace default dev wg0 table 200",
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

        # Поисковый домен. Клиенты WireGuard понимают в строке DNS не только
        # адреса: имя без точек-адреса они кладут в список поиска системы. Тогда
        # короткое «homelab» достраивается до полного самой системой — надёжнее,
        # чем если бы это делали мы.
        #
        # Агенту не нужен: он не человек и в адресную строку ничего не набирает.
        _zone = "" if is_de_agent else dns_search_zone()
        search_suffix = (", " + _zone) if _zone else ""

        client_allowed_ips = "10.13.13.0/24" if is_de_agent else build_split_allowed_ips(req.bypass_cidrs)

        server_allowed_ips = "0.0.0.0/0, 10.13.13.254/32" if is_de_agent else f"{client_ip}/32"

        config_content = f"""
[Interface]
PrivateKey = {priv_key}
Address = {client_ip}/32
DNS = {target_dns}{search_suffix}
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
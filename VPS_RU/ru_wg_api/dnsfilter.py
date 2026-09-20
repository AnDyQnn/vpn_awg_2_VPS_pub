# -*- coding: utf-8 -*-
"""Свой DNS с фильтрацией по категориям — отдельный процесс рядом с панелью узла.

Зачем свой резолвер. Фильтрация «кому что нельзя» возможна только там, где видно,
КТО спрашивает. Внешний резолвер этого не различает: для 1.1.1.1 все клиенты —
один адрес сервера. А в туннеле адрес пира и есть личность: WireGuard сам сверяет
ключ с AllowedIPs (/32), подделать адрес источника клиент не может.

Почему запросы не приходится переносить руками. Конфиги у людей уже выданы и в них
записан внешний DNS. Вместо перевыпуска узел заворачивает 53-й порт на себя правилом
DNAT — и только для тех, у кого фильтры включены. Остальные ходят к своему резолверу
как раньше: ни один существующий конфиг не меняется.

Чего этот механизм не умеет, и это честно написано в документации: DNS-over-HTTPS в
браузере идёт мимо — там запрос уходит внутри обычного HTTPS к серверу вроде
cloudflare-dns.com, и на уровне DNS его не видно. Фильтр рассчитан на обычную
семейную историю, а не на противостояние тому, кто целенаправленно обходит.

Списки категорий грузятся ТОЛЬКО те, что реально кем-то включены: на узле одно ядро
и два гигабайта, держать в памяти сотни тысяч доменов «на всякий случай» незачем.
"""
import asyncio
import json
import os
import array
import bisect
import hashlib
import re
import socket
import struct
import time

CACHE_DIR = "/etc/amnezia/amneziawg/cache/dns"
STATE_FILE = "/etc/amnezia/amneziawg/dns_filter.json"
# Свои имена внутри туннеля: имя → адрес. Файл пишет бот.
NAMES_FILE = "/etc/amnezia/amneziawg/dns_names.json"
UPSTREAM = os.getenv("DNS_UPSTREAM", "1.1.1.1")
BLOCK_IP = os.getenv("DNS_BLOCK_IP", "10.13.13.1")   # адрес страницы отказа
LISTEN_PORT = int(os.getenv("DNS_PORT", "53"))
STATE_POLL_SECONDS = 5
BLOCK_TTL = 60
# Потолок на категорию. Держим не строки, а отпечатки — восемь байт на домен,
# поэтому миллион помещается в восемь мегабайт и упирается не в память, а в
# здравый смысл: списки длиннее миллиона в природе не встречаются.
MAX_DOMAINS_PER_CATEGORY = 2000000

# Категории и откуда берутся списки. Источники — публичные, в формате «домен в строке»
# или hosts. Если источник недоступен, категория остаётся с прошлым кэшем, а не пустой:
# молча перестать фильтровать хуже, чем фильтровать по вчерашнему списку.
# Значки в одном стиле, но разные: случаи разные, и одинаковая картинка
# стирает разницу ровно там, где человек пытается понять, что произошло.
#
# Фильтр — перечёркнутый глаз: сайт есть, его не показывают.
# Доступы — замок: сервис свой, но закрыт ключом.
ICON_FILTER = (
    '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path class="lockbody" d="M2.5 12S5.9 5.8 12 5.8c2 0 3.7.7 5.1 1.6" fill="none"></path>'
    '<path class="lockbody" d="M20.4 9.2c.6.9 1.1 1.9 1.1 2.8 0 0-3.4 6.2-9.5 6.2-1.3 0-2.5-.3-3.6-.8" fill="none"></path>'
    '<circle class="keyhole" cx="12" cy="12" r="2.6" fill="none"></circle>'
    '<path class="shackle" d="M3.6 3.6 20.4 20.4" fill="none"></path>'
    '</svg>')

ICON_ACCESS = (
    '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path class="shackle" d="M7.6 10.4V7.2a4.4 4.4 0 0 1 8.8 0v3.2" fill="none"></path>'
    '<rect class="lockbody" x="4.2" y="10.4" width="15.6" height="10.4" rx="2.6" fill="none"></rect>'
    '<circle class="keyhole" cx="12" cy="15.6" r="1.25"></circle>'
    '</svg>')

# Категории. Списки публичные, в формате hosts или «домен в строке». Источник
# один и тот же проект, чтобы формат не приходилось угадывать для каждого.
_BL = "https://raw.githubusercontent.com/blocklistproject/Lists/master/%s.txt"

# Категорий здесь ровно столько, сколько есть настоящих источников. «Игры» и
# «Знакомства» отсюда убраны: списков с такими именами в проекте нет, они
# отдавали 404 — и категория выглядела бы включённой, не фильтруя ничего.
# Такое собирается своей группой: владелец приносит список и даёт ему имя.
CATEGORIES = {
    "ads": {
        "title": "Реклама и трекеры",
        "urls": ["https://raw.githubusercontent.com/blocklistproject/Lists/master/ads.txt"],
    },
    "adult": {
        "title": "Для взрослых",
        "urls": ["https://raw.githubusercontent.com/blocklistproject/Lists/master/porn.txt"],
    },
    "gambling": {
        "title": "Азартные игры",
        "urls": ["https://raw.githubusercontent.com/blocklistproject/Lists/master/gambling.txt"],
    },
    "malware": {
        "title": "Вредоносное и фишинг",
        "urls": ["https://raw.githubusercontent.com/blocklistproject/Lists/master/malware.txt",
                 "https://raw.githubusercontent.com/blocklistproject/Lists/master/phishing.txt"],
    },
    "social": {
        "title": "Соцсети",
        "urls": [_BL % "facebook", _BL % "tiktok"],
    },
    "torrent": {
        "title": "Торренты и пиратство",
        "urls": [_BL % "torrent", _BL % "piracy"],
    },
    "crypto": {
        "title": "Криптовалюты и майнинг",
        "urls": [_BL % "crypto"],
    },
    "scam": {
        "title": "Мошенничество",
        "urls": [_BL % "scam", _BL % "fraud"],
    },
    "tracking": {
        "title": "Слежка и телеметрия",
        "urls": [_BL % "tracking", _BL % "smart-tv"],
    },
    "drugs": {
        "title": "Наркотики и алкоголь",
        "urls": [_BL % "drugs", _BL % "abuse"],
    },
    "streaming": {
        "title": "Видео и стриминг",
        "urls": [_BL % "youtube", _BL % "twitter"],
    },
    "ransomware": {
        "title": "Шифровальщики",
        "urls": [_BL % "ransomware"],
    },
}


# --- разбор и сборка DNS-пакета -------------------------------------------
# Пишем руками, а не тянем библиотеку: нужен разбор имени из вопроса и сборка
# ответа с одной A-записью, это полсотни строк. Лишняя зависимость на узле,
# который должен подниматься без интернета, дороже этих строк.

def parse_question(data):
    """Возвращает (имя, qtype, конец_вопроса) или None, если пакет не разобрать."""
    if len(data) < 12:
        return None
    qdcount = struct.unpack("!H", data[4:6])[0]
    if qdcount < 1:
        return None
    pos = 12
    labels = []
    while pos < len(data):
        length = data[pos]
        if length == 0:
            pos += 1
            break
        if length & 0xC0:                      # сжатие в вопросе не встречается
            return None
        pos += 1
        if pos + length > len(data):
            return None
        # latin-1 — чтобы любой байт разобрался без исключения: домены в списках
        # хранятся в punycode, а не в юникоде, и сравниваются как есть.
        labels.append(data[pos:pos + length].decode("latin-1"))
        pos += length
    if pos + 4 > len(data):
        return None
    qtype = struct.unpack("!H", data[pos:pos + 2])[0]
    return ".".join(labels).lower(), qtype, pos + 4


def build_a_response(query, qend, qtype, ip, ttl=BLOCK_TTL):
    """Ответ с адресом.

    На запрос другого типа — IPv6, почтовый обмен и прочее — отвечаем пустым
    успехом, а не NXDOMAIN. Разница принципиальная: NXDOMAIN значит «такого
    имени не существует», и клиент, спросивший сначала A, а потом AAAA (так
    делают все современные), поверит второму ответу и решит, что имени нет
    вовсе — хотя адрес мы ему только что отдали."""
    tid = query[0:2]
    question = query[12:qend]
    if qtype == 1:                              # A
        flags = struct.pack("!H", 0x8180)
        counts = struct.pack("!HHHH", 1, 1, 0, 0)
        answer = (b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, ttl, 4)
                  + socket.inet_aton(ip))
        return tid + flags + counts + question + answer
    flags = struct.pack("!H", 0x8180)           # имя есть, записи такого типа нет
    counts = struct.pack("!HHHH", 1, 0, 0, 0)
    return tid + flags + counts + question


# IPv6 мы не отдаём. Совсем.
#
# Выход у нас только по IPv4: у узла нет ни маршрута по умолчанию для IPv6, ни
# связи по нему вовсе — проверено на живом. Германия, через которую всё уходит,
# тоже доступна только по четвёрке.
#
# А наверх мы ходили как обычный резолвер и честно пересказывали людям чужие
# AAAA-записи. Для `youtube.com` их четыре. Современный телефон, увидев
# IPv6-адрес, предпочитает его — и упирается в тупик с обеих сторон: через
# туннель узел такой адрес не вывезет, мимо туннеля это российская сеть, где
# ютуб и закрыт. Снаружи выглядит как «подключился, и ничего не грузится».
#
# Отвечаем «имя есть, записей такого типа нет» — это ровно то, что видит
# клиент, когда у сайта действительно нет IPv6, и он спокойно берёт IPv4.
# Именно пустой успех, а не отказ: отказ клиент примет за «имени не
# существует» и не станет спрашивать четвёрку вовсе.
#
# Когда у узла появится настоящий IPv6 — эту заглушку надо снять, иначе мы
# будем прятать связь, которая уже есть.
AAAA = 28


def build_no_records(query, qend):
    """Пустой успех: имя есть, записей запрошенного типа нет."""
    tid = query[0:2]
    question = query[12:qend]
    flags = struct.pack("!H", 0x8180)
    counts = struct.pack("!HHHH", 1, 0, 0, 0)
    return tid + flags + counts + question


def build_block_response(query, qend, qtype):
    """Ответ «заблокировано»: на запрос адреса отдаём адрес страницы отказа,
    на всё остальное — NXDOMAIN. Так человек видит объяснение, а не пустоту."""
    return build_a_response(query, qend, qtype, BLOCK_IP)


def build_servfail(query):
    if len(query) < 12:
        return query
    return query[0:2] + struct.pack("!H", 0x8182) + query[4:12] + query[12:]


# --- списки категорий ------------------------------------------------------

def _fingerprint(domain):
    """Восемь байт от имени. Хранить миллион строк в контейнере на 512 МБ
    нельзя, а миллион чисел — восемь мегабайт.

    Берём устойчивый хеш, а не встроенный: встроенный меняется от запуска к
    запуску, и кэш, собранный до перезапуска, перестал бы совпадать сам с собой.
    """
    return int.from_bytes(hashlib.blake2b(domain.encode(), digest_size=8).digest(),
                          "big", signed=True)


def _parse_list(text):
    """Понимает и hosts-формат, и просто домены в строку.

    Возвращает упорядоченный массив отпечатков: проверка бинарным поиском,
    память — восемь байт на домен.
    """
    seen = array.array("q")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        domain = parts[1] if len(parts) > 1 and parts[0] in ("0.0.0.0", "127.0.0.1") else parts[0]
        domain = domain.strip(".").lower()
        if not domain or domain in ("localhost", "localhost.localdomain", "broadcasthost"):
            continue
        if " " in domain or "/" in domain:
            continue
        seen.append(_fingerprint(domain))
        if len(seen) >= MAX_DOMAINS_PER_CATEGORY:
            break
    out = array.array("q", sorted(set(seen)))
    return out


def _has(domains, name):
    """Есть ли имя в категории. Массив упорядочен, поэтому бинарным поиском."""
    if not domains:
        return False
    mark = _fingerprint(name)
    i = bisect.bisect_left(domains, mark)
    return i < len(domains) and domains[i] == mark


class Filters:
    """Состояние фильтров: кто что фильтрует и какие домены в категориях.

    Перечитывается по времени изменения файла — бот пишет его через панель узла.
    Списки держим только для включённых категорий."""

    def __init__(self):
        self.clients = {}          # ip -> [категории]
        self.allow_common = set()  # разрешено всем
        self.allow_clients = {}    # ip -> разрешено лично
        self.domains = {}          # категория -> set(доменов)
        self.common = []           # категории, включённые сразу всем
        self.custom = set()        # свой список доменов владельца
        self.bot_link = ""         # куда идти с вопросом «почему закрыто»
        self._mtime = 0
        self._checked = 0

    def maybe_reload(self):
        now = time.time()
        if now - self._checked < STATE_POLL_SECONDS:
            return
        self._checked = now
        try:
            mtime = os.path.getmtime(STATE_FILE)
        except OSError:
            if self.clients:
                self.clients, self.domains = {}, {}
                self.allow_common, self.allow_clients = set(), {}
            return
        if mtime == self._mtime:
            return
        self._mtime = mtime
        try:
            with open(STATE_FILE) as f:
                state = json.load(f) or {}
        except Exception as e:
            print(f"DNS: не читается состояние фильтров: {e}", flush=True)
            return
        self.clients = {ip: list(cats) for ip, cats in (state.get("clients") or {}).items()}
        # Разрешения: общие и на конкретный адрес. Хранятся строками — их
        # десятки, а не миллион, и по ним удобно отвечать владельцу, что именно
        # сработало.
        self.allow_common = {str(d).lower().strip(".")
                             for d in (state.get("allow_common") or []) if d}
        self.allow_clients = {ip: {str(d).lower().strip(".") for d in doms if d}
                              for ip, doms in (state.get("allow_clients") or {}).items()}
        # Общие категории и свой список — то же самое, но без разбора, кому
        # именно: они действуют на всех, кто ходит через узел.
        self.common = list(state.get("common") or [])
        self.custom = {str(d).lower().strip(".") for d in (state.get("custom") or []) if d}
        self.bot_link = state.get("bot_link") or ""
        self._load_domains()

    def _load_domains(self):
        needed = {c for cats in self.clients.values() for c in cats}
        needed |= set(self.common)
        for cat in list(self.domains):
            if cat not in needed:
                del self.domains[cat]            # освобождаем память
        for cat in needed:
            if cat in self.domains:
                continue
            path = os.path.join(CACHE_DIR, f"{cat}.txt")
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    self.domains[cat] = _parse_list(f.read())
                print(f"DNS: категория {cat} — {len(self.domains[cat])} доменов", flush=True)
            except OSError:
                self.domains[cat] = set()
                print(f"DNS: список категории {cat} ещё не загружен", flush=True)

    @staticmethod
    def _covers(rules, parts):
        """Правило про домен покрывает и его поддомены: разрешили vk.com —
        значит и login.vk.com, иначе сайт всё равно не откроется."""
        for i in range(len(parts) - 1):
            if ".".join(parts[i:]) in rules:
                return True
        return False

    def blocked(self, ip, name):
        """Проверяем и сам домен, и все его родительские: список содержит
        example.com, а спрашивают ads.example.com.

        Сначала свой список владельца — он короткий и важнее всего; потом
        общие категории; потом персональные."""
        parts = name.split(".")

        # Разрешения — первыми. Исключение, которое проверяется после запрета,
        # исключением не является.
        own_allow = self.allow_clients.get(ip)
        if own_allow and self._covers(own_allow, parts):
            return None
        if self.allow_common and self._covers(self.allow_common, parts):
            return None

        if self.custom:
            for i in range(len(parts) - 1):
                if ".".join(parts[i:]) in self.custom:
                    return "свой список"

        cats = list(self.common) + list(self.clients.get(ip) or [])
        if not cats:
            return None
        for cat in cats:
            domains = self.domains.get(cat)
            if not domains:
                continue
            # Проверяем и сам домен, и родительские: в списке example.com, а
            # спрашивают ads.example.com.
            for i in range(len(parts) - 1):
                if _has(domains, ".".join(parts[i:])):
                    return cat
        return None


FILTERS = Filters()


class Names:
    """Свои имена внутри туннеля: имя → адрес.

    Список приходит от бота файлом и перечитывается по времени изменения — тем
    же способом, что и фильтры, чтобы не держать два разных механизма.

    Имя хранится и сравнивается в punycode: клиент присылает его именно так,
    даже если человек набрал русскими буквами."""

    def __init__(self):
        self.map = {}
        self.upstreams = {}
        self.mtime = 0

    def maybe_reload(self):
        try:
            m = os.path.getmtime(NAMES_FILE)
        except OSError:
            if self.map:
                self.map = {}
            return
        if m == self.mtime:
            return
        self.mtime = m
        try:
            with open(NAMES_FILE) as f:
                raw = json.load(f) or {}
        except Exception as e:
            print(f"Имена: не прочитался файл: {e}", flush=True)
            return
        self.map = {str(k).lower().rstrip("."): v
                    for k, v in (raw.get("names") or {}).items() if v}
        # Чей запрос куда пересылать наверх. Пусто — значит всем общий.
        self.upstreams = {str(k): str(v)
                          for k, v in (raw.get("upstreams") or {}).items() if v}
        print(f"Имена: загружено {len(self.map)}, "
              f"своих DNS у {len(self.upstreams)} адресов", flush=True)

    def lookup(self, name):
        return self.map.get((name or "").lower().rstrip("."))

    def upstream_for(self, client_ip):
        """Куда пересылать запрос этого человека.

        Он выбрал свой DNS при выдаче ключа — заворот на узел не повод этот
        выбор отменять."""
        return self.upstreams.get(client_ip) or UPSTREAM


NAMES = Names()

# --- ЖУРНАЛ ПОПЫТОК --------------------------------------------------------
# Файл, а не память: бот забирает записи не мгновенно, а узел может
# перезапуститься. Потолок по размеру — диск на узле маленький, и журнал не
# должен становиться причиной его переполнения.
HITS_FILE = os.path.join(os.path.dirname(STATE_FILE), "dns_hits.jsonl")
HITS_MAX_BYTES = 2 * 1024 * 1024
# Один и тот же домен браузер спрашивает пачками: страница тянет десяток
# поддоменов, а при отказе повторяет. Пишем не чаще раза в минуту на пару
# «адрес + домен», иначе журнал засыпет одна открытая вкладка.
_hit_seen = {}
# Номер, выданный этой паре: его показывает страница отказа, и он обязан
# совпадать с записанным в журнал.
_hit_refs = {}
HIT_QUIET_SECONDS = 60


def hit_ref(client_ip, name, ts):
    """Номер инцидента: короткий, читаемый вслух, одинаковый у узла и у бота.

    Считается из самой попытки — адрес, домен и минута, — поэтому обе стороны
    приходят к нему независимо. Минута, а не секунда: человек открывает страницу
    не в тот же миг, когда браузер спросил адрес.
    """
    raw = "%s|%s|%d" % (client_ip, name, int(ts) // 60)
    digest = hashlib.blake2b(raw.encode(), digest_size=4).hexdigest().upper()
    return digest[:4] + "-" + digest[4:]


def record_hit(client_ip, name, category):
    now = time.time()
    key = (client_ip, name)
    if now - _hit_seen.get(key, 0) < HIT_QUIET_SECONDS:
        return
    _hit_seen[key] = now
    ref = hit_ref(client_ip, name, now)
    # Запоминаем выданный номер: страницу человек открывает не в ту же секунду,
    # что браузер спросил адрес, и пересчёт по времени дал бы ДРУГОЙ номер —
    # тот, которого нет ни в одном журнале. Искать по такому владелец будет
    # долго и безуспешно.
    _hit_refs[key] = ref
    if len(_hit_seen) > 4096:                       # не растим память бесконечно
        for k in sorted(_hit_seen, key=_hit_seen.get)[:2048]:
            del _hit_seen[k]
            _hit_refs.pop(k, None)
    try:
        if os.path.exists(HITS_FILE) and os.path.getsize(HITS_FILE) > HITS_MAX_BYTES:
            # Половину старых отбрасываем: журнал — для разбора недавнего, а не
            # для истории на годы. История живёт у бота, в базе.
            with open(HITS_FILE, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            with open(HITS_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[len(lines) // 2:])
        with open(HITS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": int(now), "ip": client_ip,
                                "domain": name, "category": category,
                                "ref": ref},
                               ensure_ascii=False) + chr(10))
    except OSError as e:
        print(f"Журнал попыток: {e}", flush=True)


def read_hits(since=0, limit=500):
    """Записи новее указанного времени. Бот забирает их и переносит к себе."""
    out = []
    try:
        with open(HITS_FILE, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("ts", 0) > since:
                    out.append(row)
    except OSError:
        return []
    return out[-limit:]


class DnsProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.ensure_future(self.handle(data, addr))

    async def handle(self, data, addr):
        FILTERS.maybe_reload()
        NAMES.maybe_reload()
        parsed = parse_question(data)
        if parsed:
            name, qtype, qend = parsed
            # Свои имена — первым делом: они наши, наверх за ними ходить незачем.
            own = NAMES.lookup(name)
            if own:
                self.transport.sendto(build_a_response(data, qend, qtype, own), addr)
                return
            cat = FILTERS.blocked(addr[0], name)
            if cat:
                record_hit(addr[0], name, cat)
                self.transport.sendto(build_block_response(data, qend, qtype), addr)
                return
            if qtype == AAAA:
                # Наверх за шестёркой не ходим: отдавать её всё равно нельзя.
                self.transport.sendto(build_no_records(data, qend), addr)
                return
        try:
            answer = await forward(data, upstream=NAMES.upstream_for(addr[0]))
        except Exception:
            answer = build_servfail(data)
        self.transport.sendto(answer, addr)


async def forward(data, timeout=3.0, upstream=None):
    """Пересылает запрос наверх. По умолчанию — общий DNS, но у человека может
    быть свой: он выбрал его при выдаче ключа, и заворот на узел не повод
    этот выбор отменять."""
    target = upstream or UPSTREAM
    host, _, port = str(target).partition(":")
    loop = asyncio.get_event_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    try:
        await loop.sock_connect(sock, (host, int(port) if port.isdigit() else 53))
        await loop.sock_sendall(sock, data)
        return await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout)
    finally:
        sock.close()


def _tcp_blocked(ip, name):
    """То же, что и по UDP, но с записью в журнал: запросы приходят обоими
    путями, и попытка по TCP ничем не отличается от попытки по UDP."""
    cat = FILTERS.blocked(ip, name)
    if cat:
        record_hit(ip, name, cat)
    return cat


async def handle_tcp(reader, writer):
    """DNS поверх TCP. Нужен не ради объёмных ответов, а чтобы фильтр нельзя было
    обойти, просто перейдя на TCP: заворачиваются оба порта."""
    try:
        header = await asyncio.wait_for(reader.readexactly(2), 5)
        length = struct.unpack("!H", header)[0]
        data = await asyncio.wait_for(reader.readexactly(length), 5)
        FILTERS.maybe_reload()
        NAMES.maybe_reload()
        ip = writer.get_extra_info("peername")[0]
        parsed = parse_question(data)
        answer = None
        if parsed:
            name, qtype, qend = parsed
            own = NAMES.lookup(name)
            if own:
                answer = build_a_response(data, qend, qtype, own)
            elif _tcp_blocked(ip, name):
                answer = build_block_response(data, qend, qtype)
            elif qtype == AAAA:
                answer = build_no_records(data, qend)
        if answer is None:
            try:
                answer = await forward(data, upstream=NAMES.upstream_for(ip))
            except Exception:
                answer = build_servfail(data)
        writer.write(struct.pack("!H", len(answer)) + answer)
        await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


# --- СТРАНИЦА ОТКАЗА -------------------------------------------------------
# Заблокированный домен разрешается в адрес узла, и сюда же приходит запрос.
# Человек видит объяснение вместо «сайт не открывается» — разница в том, что
# он понимает: сеть работает, закрыт конкретно этот сайт и почему.
#
# Ограничение, которое надо понимать: показать страницу можно только для HTTP.
# Для HTTPS браузер получит ошибку соединения — подменить сертификат чужого сайта
# нельзя, не поставив свой корневой сертификат на каждое устройство. Делать это
# ради страницы отказа неправильно: это уже вскрытие чужого трафика.
BLOCK_PAGE = "/app/blocked.html"
CERT_FILE = "/etc/amnezia/amneziawg/block_page.pem"
_page_cache = None


def ensure_cert():
    """Самоподписанный сертификат для страницы отказа.

    Что он даёт и чего не даёт, чтобы не было сюрпризов: браузер всё равно
    покажет предупреждение о недоверенном сертификате — подписать чужой домен
    по-настоящему невозможно. На обычном сайте человек сможет нажать «всё равно
    перейти» и увидит заглушку. На сайтах с HSTS (а это почти все крупные)
    кнопки «перейти» не будет вовсе, и там всё останется как было — ошибка
    соединения. Поэтому HTTPS здесь бонус, а не основной путь."""
    if os.path.exists(CERT_FILE):
        return CERT_FILE
    cmd = ("openssl req -x509 -newkey rsa:2048 -nodes -days 3650 "
           f"-keyout {CERT_FILE} -out {CERT_FILE} -subj '/CN=blocked' 2>/dev/null")
    rc = os.system(cmd)
    if rc != 0 or not os.path.exists(CERT_FILE):
        print("Страница отказа: сертификат не создан, HTTPS не поднимется", flush=True)
        return None
    os.chmod(CERT_FILE, 0o600)
    return CERT_FILE


CATEGORY_TITLES = {"ads": "реклама и трекеры", "adult": "для взрослых",
                   "gambling": "азартные игры", "malware": "вредоносное и фишинг",
                   "social": "соцсети"}


def _render_block_page(host, category, ref=""):
    """Причин отказа две, и путать их нельзя.

    Фильтр — про внешний сайт из закрытой категории. Роль — про домашний сервис,
    к которому человеку не открыт доступ. Для человека это разные ситуации: в
    первом случае обращаться бессмысленно (так настроено намеренно), во втором
    доступ вполне может быть выдан, если попросить."""
    global _page_cache
    if _page_cache is None:
        try:
            with open(BLOCK_PAGE, encoding="utf-8") as f:
                _page_cache = f.read()
        except OSError:
            _page_cache = ("<!doctype html><meta charset=utf-8>"
                           "<h1>Закрыто</h1><p>__DOMAIN__</p>")
    safe_host = (host or "этот адрес").replace("<", "&lt;").replace(">", "&gt;")[:120]
    # Ссылка на бота: человеку должно быть куда пойти с вопросом, а не просто
    # «закрыто». Адрес бота приходит от него же вместе с раскладкой фильтров.
    # Адрес владельца приходит от бота вместе с раскладкой фильтров: вписывать
    # его в страницу нельзя — однажды разойдётся с настоящим.
    link = FILTERS.bot_link
    contact = (f'<a href="{link}" style="color:#58a6ff">написать владельцу в Telegram</a>'
               if link else "напишите владельцу сети")
    # Блока два, разделитель между ними один: сверху что произошло, под
    # чертой — что с этим делать. Категория стоит строкой ниже запрета: она
    # его уточняет, а не заменяет.
    if category:
        head = "Этот сайт закрыт фильтром"
        why = ('Доступ ограничен администратором'
               '<span class="cat">Категория: %s</span>'
               % CATEGORY_TITLES.get(category, category))
        note = "Если это ошибка — свяжитесь с поддержкой"
        icon = ICON_FILTER
    else:
        head = "Доступ к этому сервису закрыт"
        why = "Доступ ограничен администратором"
        note = "Если это ошибка — свяжитесь с поддержкой"
        icon = ICON_ACCESS
    # Номер показываем только когда он есть: пустая строка «Инцидент —» хуже
    # отсутствующей.
    # Одной строкой: подпись и значение в столбик человек копирует по частям
    # и присылает половину.
    ref_block = ('<p class="ref">Номер инцидента: <span>%s</span></p>'
                 % ref) if ref else ""

    page = _page_cache
    # Кнопка «обратиться» — только когда есть куда. Без адреса убираем её
    # целиком: мёртвая кнопка хуже отсутствующей, по ней жмут впустую.
    if link:
        page = page.replace("__CONTACT_HREF__", link)
    else:
        page = re.sub(r'<a class="cta".*?</a>', "", page, flags=re.S)

    return (page
            .replace("__REF__", ref_block)
            .replace("__DOMAIN__", safe_host)
            .replace("__HEAD__", head)
            .replace("__WHY__", why)
            .replace("__NOTE__", note)
            .replace("__ICON__", icon)
            .replace("__CONTACT__", contact)
            .replace("__CATEGORY__", CATEGORY_TITLES.get(category, category or "")))


async def handle_http(reader, writer):
    """Отдаём страницу на любой путь: человек пришёл сюда не за файлом,
    а потому что его увели с закрытого сайта."""
    try:
        request = await asyncio.wait_for(reader.read(2048), 5)
        host, category = "", ""
        for line in request.decode("latin-1", "ignore").split("\r\n"):
            if line.lower().startswith("host:"):
                host = line.split(":", 1)[1].strip().split(":")[0]
                break
        ip = writer.get_extra_info("peername")
        if ip and host:
            category = FILTERS.blocked(ip[0], host.lower()) or ""
        # Номер берём тот же, что записан в журнале: человек копирует его со
        # страницы, владелец ищет по нему инцидент.
        ref = ""
        if ip and host:
            # Запись делаем и здесь: закрытый доступ к своему сервису режется
            # не фильтром, а правилами, и в журнал он до сих пор не попадал —
            # инцидента с этим номером просто не существовало бы. Повтора не
            # будет: на пару «адрес + домен» стоит минута тишины.
            record_hit(ip[0], host.lower(), category or "доступы")
            # Берём номер, который уже выдан этой паре, а не считаем заново:
            # минута с момента запроса могла смениться, и человек получил бы
            # номер, которого нет в журнале.
            ref = _hit_refs.get((ip[0], host.lower())) or hit_ref(
                ip[0], host.lower(), time.time())
        body = _render_block_page(host, category, ref).encode("utf-8")
        writer.write(b"HTTP/1.1 200 OK\r\n"
                     b"Content-Type: text/html; charset=utf-8\r\n"
                     b"Cache-Control: no-store\r\n"
                     b"Connection: close\r\n"
                     b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
        await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


# Порт TLS-страницы отказа. 443 отдан Xray — см. пояснение ниже по коду.
HTTPS_PAGE_PORT = 8443


async def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    FILTERS.maybe_reload()
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(DnsProtocol, local_addr=("0.0.0.0", LISTEN_PORT))
    server = await asyncio.start_server(handle_tcp, "0.0.0.0", LISTEN_PORT)
    try:
        await asyncio.start_server(handle_http, "0.0.0.0", 80)
        print("Страница отказа слушает :80", flush=True)
        cert = ensure_cert()
        if cert:
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert)
            # Не 443: этот порт занимает Xray, и занимает обоснованно —
            # трафик к нему неотличим от обычного HTTPS. Человек сюда попадает
            # не по адресу, а по правилу подмены, поэтому номер порта ему
            # безразличен.
            await asyncio.start_server(handle_http, "0.0.0.0", HTTPS_PAGE_PORT,
                                       ssl=ctx)
            print(f"Страница отказа слушает :{HTTPS_PAGE_PORT} "
                  f"(самоподписанный)", flush=True)
    except Exception as e:
        # Не фатально: фильтр работает и без страницы, человек просто увидит
        # обычную ошибку соединения.
        print(f"Страница отказа не поднялась: {e}", flush=True)
    print(f"DNS-фильтр слушает :{LISTEN_PORT}, наверх ходит к {UPSTREAM}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

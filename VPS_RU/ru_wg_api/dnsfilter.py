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
MAX_DOMAINS_PER_CATEGORY = 150000

# Категории и откуда берутся списки. Источники — публичные, в формате «домен в строке»
# или hosts. Если источник недоступен, категория остаётся с прошлым кэшем, а не пустой:
# молча перестать фильтровать хуже, чем фильтровать по вчерашнему списку.
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
        "urls": ["https://raw.githubusercontent.com/blocklistproject/Lists/master/facebook.txt",
                 "https://raw.githubusercontent.com/blocklistproject/Lists/master/tiktok.txt"],
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


def build_block_response(query, qend, qtype):
    """Ответ «заблокировано»: на запрос адреса отдаём адрес страницы отказа,
    на всё остальное — NXDOMAIN. Так человек видит объяснение, а не пустоту."""
    return build_a_response(query, qend, qtype, BLOCK_IP)


def build_servfail(query):
    if len(query) < 12:
        return query
    return query[0:2] + struct.pack("!H", 0x8182) + query[4:12] + query[12:]


# --- списки категорий ------------------------------------------------------

def _parse_list(text):
    """Понимает и hosts-формат, и просто домены в строку."""
    out = set()
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
        out.add(domain)
        if len(out) >= MAX_DOMAINS_PER_CATEGORY:
            break
    return out


class Filters:
    """Состояние фильтров: кто что фильтрует и какие домены в категориях.

    Перечитывается по времени изменения файла — бот пишет его через панель узла.
    Списки держим только для включённых категорий."""

    def __init__(self):
        self.clients = {}          # ip -> [категории]
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

    def blocked(self, ip, name):
        """Проверяем и сам домен, и все его родительские: список содержит
        example.com, а спрашивают ads.example.com.

        Сначала свой список владельца — он короткий и важнее всего; потом
        общие категории; потом персональные."""
        parts = name.split(".")
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
            for i in range(len(parts) - 1):
                if ".".join(parts[i:]) in domains:
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
                self.transport.sendto(build_block_response(data, qend, qtype), addr)
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
            elif FILTERS.blocked(ip, name):
                answer = build_block_response(data, qend, qtype)
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


def _render_block_page(host, category):
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
    link = FILTERS.bot_link
    contact = (f'<a href="{link}" style="color:#58a6ff">написать владельцу в Telegram</a>'
               if link else "напишите владельцу сети")
    if category:
        head = "Этот сайт закрыт фильтром"
        why = "Категория: <b>%s</b>" % CATEGORY_TITLES.get(category, category)
        note = ("Так настроено для вашего ключа. Сайт работает — "
                "его не открывает фильтр, а не поломка сети.")
    else:
        head = "Доступ к этому сервису закрыт"
        why = "Он не входит в то, что открыто вашему ключу"
        note = ("Сервис работает и сеть исправна — просто он не открыт для вас. "
                "Это настройка доступов, а не поломка.")
    return (_page_cache
            .replace("__DOMAIN__", safe_host)
            .replace("__HEAD__", head)
            .replace("__WHY__", why)
            .replace("__NOTE__", note)
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
        body = _render_block_page(host, category).encode("utf-8")
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

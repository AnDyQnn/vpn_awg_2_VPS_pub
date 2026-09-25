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
# В python нет готовой константы, а ядру нужна именно она: разрешает занять
# адрес, которого на интерфейсе ещё нет.
IP_FREEBIND = 15
STATE_POLL_SECONDS = 5
BLOCK_TTL = 60
# Потолок на категорию. Держим не строки, а отпечатки — восемь байт на домен.
# «Опасные сайты» — это под четыре миллиона: один только список вредоносного
# больше двух с половиной, и прежний потолок в два миллиона молча отрезал
# четверть. Пять миллионов — сорок мегабайт, узлу по силам.
MAX_DOMAINS_PER_CATEGORY = 5000000

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
    # Реклама и слежка — одно и то же для человека: чужие скрипты на странице,
    # которые показывают баннеры и считают, куда он ходит. Списки при этом
    # почти не пересекаются (из 144 тысяч трекеров 137 в рекламном нет),
    # поэтому берутся все три; телеметрия телевизоров — туда же.
    "ads": {
        "title": "Реклама и слежка",
        "urls": [_BL % "ads", _BL % "tracking", _BL % "smart-tv"],
    },
    "adult": {
        "title": "Для взрослых",
        "urls": ["https://raw.githubusercontent.com/blocklistproject/Lists/master/porn.txt"],
    },
    "gambling": {
        "title": "Азартные игры",
        "urls": ["https://raw.githubusercontent.com/blocklistproject/Lists/master/gambling.txt"],
    },
    # Всё, что опасно открыть: вирусы, фишинг, мошенничество, обманные сайты,
    # вредные перенаправления, серверы шифровальщиков. Раньше это были четыре
    # отдельные категории, и владельцу приходилось угадывать, какая чем
    # отличается. «Шифровальщики» были почти целиком внутри вредоносного
    # (1901 из 1904), а «мошенничество» — наоборот, почти целиком снаружи.
    "malware": {
        "title": "Опасные сайты",
        "urls": [_BL % "malware", _BL % "phishing", _BL % "ransomware",
                 _BL % "scam", _BL % "fraud", _BL % "redirect", _BL % "abuse"],
    },
    "social": {
        "title": "Соцсети",
        "urls": [_BL % "facebook", _BL % "tiktok", _BL % "twitter"],
        # Внешние списки — Facebook с Instagram и WhatsApp, TikTok и Twitter.
        # Российских соцсетей в них нет вовсе: владелец закрывал «Соцсети», а
        # ВКонтакте и Одноклассники открывались. Дописываем сами; работает и
        # тогда, когда внешний список не скачался. Telegram не трогаем: через
        # него работает бот и кнопка «написать владельцу» на странице отказа.
        "extra": [
            # ВКонтакте
            "vk.com", "vk.ru", "vk.me", "vkontakte.ru", "vk.cc", "vk.link",
            "userapi.com", "vkuser.net", "vkuseraudio.net", "vkuservideo.net",
            "vk-cdn.net", "vk-portal.net", "vkontakte.com",
            # Одноклассники и «Мой мир»
            "ok.ru", "odnoklassniki.ru", "odkl.ru", "okcdn.ru", "mycdn.me",
            "my.mail.ru",
            # Остальные крупные
            "twitter.com", "x.com", "twimg.com", "t.co",
            "instagram.com", "cdninstagram.com", "threads.net", "threads.com",
            "pinterest.com", "pinimg.com", "snapchat.com", "reddit.com",
            "redd.it", "redditmedia.com", "redditstatic.com", "tumblr.com",
            "linkedin.com", "licdn.com", "likee.video", "like.video",
        ],
    },
    "torrent": {
        "title": "Торренты и пиратство",
        "urls": [_BL % "torrent", _BL % "piracy"],
        # Внешние списки маленькие (под пять тысяч) и русских сайтов в них
        # почти нет: rutracker и kinozal есть, rutor, nnmclub и онлайн-
        # кинотеатры с пиратским видео — нет.
        "extra": [
            "rutracker.org", "rutracker.net", "rutracker.cc", "rutor.info",
            "rutor.is", "rutor.org", "nnmclub.to", "nnm-club.me", "nnm-club.ws",
            "kinozal.tv", "kinozal.me", "kinozal.guru", "rustorka.com",
            "tfile.cc", "megapeer.vip", "fast-torrent.club", "torrent-igruha.org",
            "thepiratebay.org", "1337x.to", "rarbg.to", "yts.mx", "nyaa.si",
            "lordfilm.tv", "lordfilm.ru", "hdrezka.ag", "rezka.ag", "hdrezka.me",
            "kinogo.biz", "baskino.me", "seasonvar.ru", "filmix.ac",
            "zona.plus", "kinokrad.co", "gidonline.io",
        ],
    },
    "crypto": {
        "title": "Криптовалюты",
        "urls": [_BL % "crypto"],
        # Внешний список — майнинг в браузере и часть бирж; крупных бирж,
        # которыми пользуются из России, в нём нет.
        "extra": [
            "binance.com", "bybit.com", "okx.com", "kucoin.com", "htx.com",
            "huobi.com", "mexc.com", "gate.io", "bitget.com", "coinbase.com",
            "kraken.com", "bingx.com", "exmo.com", "exmo.me", "garantex.org",
            "coinmarketcap.com", "coingecko.com",
            "bestchange.ru", "bestchange.com",
        ],
    },
    # Источник называет это «сайтами нелегальных наркотиков», по факту там
    # больше всего серых аптек. «Алкоголь» в названии был без единого списка
    # под ним, а «abuse» — это обманные сайты, им место в опасных.
    "drugs": {
        "title": "Наркотики и серые аптеки",
        "urls": [_BL % "drugs", _BL % "vaping"],
    },
    "streaming": {
        "title": "Видео и стриминг",
        # Twitter отсюда перенесён в соцсети: это не видео.
        "urls": [_BL % "youtube"],
        # Внешний список — только YouTube, и то без самого youtube.com.
        # Российских и мировых видеосервисов в нём нет вовсе.
        "extra": [
            "youtube.com", "youtu.be", "ytimg.com", "googlevideo.com",
            "youtube-nocookie.com", "youtubei.googleapis.com",
            "rutube.ru", "rutube.sport", "vkvideo.ru", "vk.video",
            "twitch.tv", "ttvnw.net", "jtvnw.net", "netflix.com", "nflxvideo.net",
            "kinopoisk.ru", "hd.kinopoisk.ru", "ivi.ru", "ivi.tv", "okko.tv",
            "wink.ru", "premier.one", "start.ru", "more.tv", "kion.ru",
            "amediateka.ru", "smotrim.ru", "dzen.ru", "tiktok.com",
            "kick.com", "trovo.live", "vkplay.live", "live.vkvideo.ru",
        ],
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


# --- ИМЯ-ИНДИКАТОР ДЛЯ БРАУЗЕРА -------------------------------------------
# Firefox включает свой собственный DNS поверх HTTPS по умолчанию и тем самым
# обходит фильтр. Но перед этим он спрашивает особое имя: если сеть отвечает на
# него «такого нет», он считает, что у сети свои правила, и свой DNS НЕ
# включает.
#
# Это вежливый путь: браузер отказывается от обхода сам, а не бьётся в закрытую
# дверь. Резать ему соединения мы тоже умеем (запрет на узле), но это грубее и
# заметнее для человека.
#
# Список именно отказных имён держим отдельно от фильтра категорий: это не
# «запрещённый сайт», а служебный ответ, и в журнал попыток он попадать не
# должен — иначе владелец увидит десятки «нарушений» на ровном месте.
CANARY_NAMES = {
    # Firefox: «есть ли у сети свои правила»
    "use-application-dns.net",
    # Apple и Chrome смотрят на доступность своих резолверов по именам —
    # отказ по ним тоже возвращает их к обычному DNS.
    "mozilla.cloudflare-dns.com",
    "dns.google",
    "dns.quad9.net",
    "doh.opendns.com",
    "dns.adguard.com",
    "dns.nextdns.io",
    "chrome.cloudflare-dns.com",
}


def build_nxdomain(query):
    """Ответ «такого имени нет». Не блокировка и не ошибка — именно отсутствие.

    Важно отвечать именно так: на «сервер не смог» браузер попробует ещё раз и
    другим путём, а на «такого нет» — примет и успокоится."""
    out = bytearray(query[:12])
    out[2] = 0x81
    out[3] = 0x83          # ответ, рекурсия доступна, код 3 — имени нет
    out[6:8] = b"\x00\x00"   # записей в ответе нет
    out[8:10] = b"\x00\x00"
    out[10:12] = b"\x00\x00"
    return bytes(out) + query[12:]


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


def _domain_of(line):
    """Домен из строки списка: hosts-формат или просто домен. Пусто — мусор."""
    line = line.strip()
    if not line or line.startswith("#"):
        return ""
    parts = line.split()
    domain = parts[1] if len(parts) > 1 and parts[0] in ("0.0.0.0", "127.0.0.1") else parts[0]
    domain = domain.strip(".").lower()
    if not domain or domain in ("localhost", "localhost.localdomain", "broadcasthost"):
        return ""
    if "/" in domain:
        return ""
    return domain


def _parse_lines(lines):
    """Упорядоченный массив отпечатков без повторов: проверка бинарным
    поиском, восемь байт на домен.

    Раньше строки собирались в множество чисел и сортировались целиком. На
    списке вредоносного в два с половиной миллиона это сотни мегабайт на пике —
    при потолке контейнера в полгигабайта. Теперь отпечатки раскладываются по
    256 корзинам по старшему байту, и сортируется по одной корзине: пик —
    шестнадцать байт на домен, а не сотня."""
    buckets = [array.array("q") for _ in range(256)]
    n = 0
    for line in lines:
        domain = _domain_of(line)
        if not domain:
            continue
        fp = _fingerprint(domain)
        buckets[(fp >> 56) & 0xFF].append(fp)
        n += 1
        if n >= MAX_DOMAINS_PER_CATEGORY:
            break
    out = array.array("q")
    # Числа со знаком: отрицательные (старший байт 0x80–0xFF) идут первыми.
    for b in list(range(128, 256)) + list(range(0, 128)):
        last = None
        for v in sorted(buckets[b]):
            if v != last:
                out.append(v)
                last = v
        buckets[b] = None
    return out


def _parse_list(text):
    """Список, пришедший строкой (свой довесок, свои группы)."""
    return _parse_lines(text.splitlines())


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
        self.except_clients = {}   # ip -> какие ОБЩИЕ категории ему не применять
        self.domains = {}          # категория -> set(доменов)
        self.common = []           # категории, включённые сразу всем
        self.custom = set()        # свой список доменов владельца
        self.bot_link = ""         # куда идти с вопросом «почему закрыто»
        self._mtime = 0
        self._checked = 0
        self._mtimes = {}          # категория -> время файла, с которого загружена
        self._loading = set()      # категории, которые грузятся прямо сейчас

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
                self.except_clients = {}
            return
        if mtime == self._mtime:
            # Раскладка та же, но список категории мог обновиться на диске.
            self._load_domains()
            return
        self._mtime = mtime
        try:
            with open(STATE_FILE) as f:
                state = json.load(f) or {}
        except Exception as e:
            print(f"DNS: не читается состояние фильтров: {e}", flush=True)
            return
        self.clients = {ip: _canon(cats) for ip, cats in (state.get("clients") or {}).items()}
        # Разрешения: общие и на конкретный адрес. Хранятся строками — их
        # десятки, а не миллион, и по ним удобно отвечать владельцу, что именно
        # сработало.
        self.allow_common = {str(d).lower().strip(".")
                             for d in (state.get("allow_common") or []) if d}
        self.allow_clients = {ip: {str(d).lower().strip(".") for d in doms if d}
                              for ip, doms in (state.get("allow_clients") or {}).items()}
        self.except_clients = {ip: set(_canon(c for c in cats if c))
                               for ip, cats in
                               (state.get("except_clients") or {}).items()}
        # Общие категории и свой список — то же самое, но без разбора, кому
        # именно: они действуют на всех, кто ходит через узел.
        self.common = _canon(state.get("common") or [])
        self.custom = {str(d).lower().strip(".") for d in (state.get("custom") or []) if d}
        self.bot_link = state.get("bot_link") or ""
        self._load_domains()

    def _load_domains(self, sync=False):
        """Держит в памяти ровно включённые категории и свежие их списки.

        Загрузка — в фоне. Список опасных сайтов — три миллиона строк и
        полминуты работы; прежде она шла внутри DNS-сервера, и всё это время
        DNS не отвечал никому. Теперь резолвер отвечает как обычно, а
        категория начинает действовать, когда список готов (свой довесок —
        сразу). Обновлённый файл — раз в 12 часов его перекачивает узел —
        подхватывается сам: раньше загруженная категория не перечитывалась
        до перезапуска."""
        needed = {c for cats in self.clients.values() for c in cats}
        needed |= set(self.common)
        for cat in list(self.domains):
            if cat not in needed:
                del self.domains[cat]            # освобождаем память
                self._mtimes.pop(cat, None)
        for cat in needed:
            path = os.path.join(CACHE_DIR, f"{cat}.txt")
            try:
                mt = os.path.getmtime(path)
            except OSError:
                mt = 0
            if cat in self.domains and self._mtimes.get(cat) == mt:
                continue
            if cat in self._loading:
                continue
            extras = (CATEGORIES.get(cat) or {}).get("extra") or []
            if cat not in self.domains and extras:
                self.domains[cat] = _parse_list("\n".join(extras))
            self._loading.add(cat)
            if sync:
                self._load_one(cat, path, mt)
            else:
                import threading
                threading.Thread(target=self._load_one, args=(cat, path, mt),
                                 daemon=True).start()

    def _load_one(self, cat, path, mt):
        # Свой довесок категории — всегда, даже без скачанного списка.
        extras = (CATEGORIES.get(cat) or {}).get("extra") or []
        try:
            try:
                # Построчно, а не целиком: файл опасных сайтов — сотня мегабайт.
                with open(path, encoding="utf-8", errors="ignore") as f:
                    import itertools
                    arr = _parse_lines(itertools.chain(f, extras))
                note = f"DNS: категория {cat} — {len(arr)} доменов"
            except OSError:
                arr = _parse_list("\n".join(extras)) if extras else array.array("q")
                note = (f"DNS: список категории {cat} ещё не загружен"
                        + (f", работает свой довесок ({len(arr)})" if extras else ""))
            self.domains[cat] = arr              # подмена одним присваиванием
            self._mtimes[cat] = mt
            print(note, flush=True)
        except Exception as e:
            print(f"DNS: категория {cat} не загрузилась: {e}", flush=True)
        finally:
            self._loading.discard(cat)

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

        # Общие категории — за вычетом того, что снято лично с этого адреса.
        # Личные категории вычетом не трогаем: если владелец включил человеку
        # категорию сам, он этого и хотел, а исключение относится к общему.
        skip = self.except_clients.get(ip) or ()
        cats = [c for c in self.common if c not in skip]
        cats += list(self.clients.get(ip) or [])
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
        self.zone = str(raw.get("zone") or "").lower().strip(".")
        print(f"Имена: загружено {len(self.map)}, "
              f"своих DNS у {len(self.upstreams)} адресов", flush=True)

    zone = ""

    def lookup(self, name):
        return self.map.get((name or "").lower().rstrip("."))

    def service_host(self):
        """Служебное имя узла — то, на котором живёт страница отказа.

        Берём имя в зоне, ведущее на адрес страницы, в той форме, в какой его
        набирает браузер (punycode). Своего имени нет — пусто."""
        if not self.zone:
            return ""
        cands = sorted(n for n, ip in self.map.items()
                       if ip == BLOCK_IP and n.isascii()
                       and n.endswith("." + self.zone))
        return cands[0] if cands else ""

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
            # Служебные имена, по которым браузер решает, включать ли свой
            # DNS. Отвечаем «такого нет» — и он не включает. В журнал попыток
            # это не пишем: нарушения тут нет, спрашивает сам браузер.
            if name in CANARY_NAMES:
                self.transport.sendto(build_nxdomain(data), addr)
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
# Ограничение, которое надо понимать: показать страницу ВМЕСТО ЧУЖОГО САЙТА
# можно только для HTTP. Для HTTPS браузер получит ошибку соединения — подменить
# сертификат чужого сайта нельзя, не поставив свой корневой сертификат на каждое
# устройство. Делать это ради страницы отказа неправильно: это уже вскрытие
# чужого трафика.
#
# А вот на СВОИ имена сертификат настоящий бывает — и с ним страница открывается
# без единого предупреждения. Речь про «дом.example.ru» и «закрыто.example.ru»:
# туда человека уводит не подмена, а наше же имя, и сертификат «*.example.ru»
# покрывает их все. Берётся он из той же папки, что у подписки, и только на
# чтение.
BLOCK_PAGE = "/app/blocked.html"
CERT_FILE = "/etc/amnezia/amneziawg/block_page.pem"
# Папка с настоящим сертификатом. Монтируется в контейнер только на чтение;
# нет её — работаем как раньше, на самоподписанном.
REAL_CERT_DIR = os.getenv("BLOCK_CERT_DIR", "/certs")
_page_cache = None
_cert_seen = None


def real_cert():
    """Пара файлов настоящего сертификата, если она на месте."""
    cert = os.path.join(REAL_CERT_DIR, "fullchain.pem")
    key = os.path.join(REAL_CERT_DIR, "privkey.pem")
    try:
        if os.path.getsize(cert) > 0 and os.path.getsize(key) > 0:
            return cert, key
    except OSError:
        pass
    return None


def cert_stamp():
    """Метка файлов — по ней видно, что сертификат продлили."""
    pair = real_cert()
    if not pair:
        return None
    try:
        return tuple(int(os.stat(f).st_mtime) for f in pair)
    except OSError:
        return None


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


CATEGORY_TITLES = {"ads": "реклама и слежка", "adult": "для взрослых",
                   "gambling": "азартные игры", "malware": "опасный сайт",
                   "social": "соцсети", "torrent": "торренты и пиратство",
                   "crypto": "криптовалюты", "drugs": "наркотики и серые аптеки",
                   "streaming": "видео и стриминг"}

# Прежние категории, слитые в новые. Раскладка от бота старой версии или
# застрявшая на диске всё равно должна работать, а не молча перестать
# фильтровать.
CATEGORY_ALIASES = {"scam": "malware", "ransomware": "malware", "tracking": "ads"}


def _canon(cats):
    out = []
    for c in cats or []:
        c = CATEGORY_ALIASES.get(str(c), str(c))
        if c not in out:
            out.append(c)
    return out


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


# --- ПЕРЕНАПРАВЛЕНИЕ НА СВОЁ ИМЯ -------------------------------------------
# Закрытый сайт по http уводим на страницу узла на СВОЁМ имени:
# «https://blocked.example.ru/?site=…». Там сертификат настоящий, и человек
# видит страницу с замком и нашим адресом, а не чужой адрес со страницей
# внутри. Это не подмена — обычное перенаправление с нашего же ответа.
#
# По https так нельзя и не будет: чтобы ответить перенаправлением, надо сначала
# пройти рукопожатие от имени чужого сайта, а его сертификата у нас нет. Но
# Chrome, получив ошибку на https, сам откатывается на http — и тогда
# перенаправление срабатывает; проверено браузером.
#
# Только когда сертификат покрывает служебное имя. Без своего домена
# сертификат выпущен на адрес, и перенаправление увело бы на ошибку — там
# страница отдаётся прямо, как раньше.
_SITE_RE = re.compile(r"^[a-z0-9.-]{1,253}$")
_REF_RE = re.compile(r"^[A-Z0-9-]{0,16}$")
_CAT_RE = re.compile(r"^[\w -]{0,40}$")
_cert_names = {"stamp": None, "names": []}


def _cert_covers(host):
    """Покрывает ли настоящий сертификат это имя (точно или «*.» на уровень)."""
    pair = real_cert()
    if not pair or not host:
        return False
    stamp = cert_stamp()
    if _cert_names["stamp"] != stamp:
        try:
            import ssl
            info = ssl._ssl._test_decode_cert(pair[0])
            names = [v.lower() for k, v in info.get("subjectAltName", ()) if k == "DNS"]
        except Exception:
            names = []
        _cert_names.update(stamp=stamp, names=names)
    for n in _cert_names["names"]:
        if n == host:
            return True
        if n.startswith("*.") and host.count(".") == n.count(".") \
                and host.split(".", 1)[1] == n[2:]:
            return True
    return False


def redirect_target(host, category, ref):
    """Адрес страницы на своём имени — или пусто, если перенаправлять некуда."""
    from urllib.parse import urlencode
    NAMES.maybe_reload()
    svc = NAMES.service_host()
    if not svc or host == svc or not _cert_covers(svc):
        return ""
    return "https://%s/?%s" % (svc, urlencode({"site": host, "c": category, "ref": ref}))


def _query(request_line):
    """Параметры из строки запроса «GET /?site=…&c=… HTTP/1.1»."""
    from urllib.parse import parse_qs, urlsplit
    try:
        target = request_line.split(" ")[1]
        return {k: v[0] for k, v in parse_qs(urlsplit(target).query).items()}
    except Exception:
        return {}


async def handle_http(reader, writer):
    """Отдаём страницу на любой путь: человек пришёл сюда не за файлом,
    а потому что его увели с закрытого сайта."""
    try:
        request = await asyncio.wait_for(reader.read(2048), 5)
        host, category = "", ""
        lines = request.decode("latin-1", "ignore").split("\r\n")
        for line in lines:
            if line.lower().startswith("host:"):
                host = line.split(":", 1)[1].strip().split(":")[0].lower()
                break
        ip = writer.get_extra_info("peername")
        tls = writer.get_extra_info("ssl_object") is not None

        # Пришли по перенаправлению на своё имя: что закрыто и почему, сказано
        # в адресе. Инцидент уже записан при первом запросе — второй раз не пишем.
        q = _query(lines[0]) if lines else {}
        NAMES.maybe_reload()
        if tls and host and host == NAMES.service_host() and q.get("site"):
            site = q.get("site", "").lower()
            cat = q.get("c", "")
            ref = q.get("ref", "")
            if _SITE_RE.match(site) and _CAT_RE.match(cat) and _REF_RE.match(ref):
                if cat == "доступы":
                    cat = ""
                body = _render_block_page(site, cat, ref).encode("utf-8")
                writer.write(b"HTTP/1.1 200 OK\r\n"
                             b"Content-Type: text/html; charset=utf-8\r\n"
                             b"Cache-Control: no-store\r\n"
                             b"Connection: close\r\n"
                             b"Content-Length: " + str(len(body)).encode()
                             + b"\r\n\r\n" + body)
                await writer.drain()
                return

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
        # По http — перенаправляем на своё имя, если есть куда.
        target = "" if tls else redirect_target(host, category or "доступы", ref)
        if target:
            writer.write(b"HTTP/1.1 302 Found\r\n"
                         b"Location: " + target.encode("ascii", "ignore") + b"\r\n"
                         b"Cache-Control: no-store\r\n"
                         b"Connection: close\r\n"
                         b"Content-Length: 0\r\n\r\n")
            await writer.drain()
            return
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


def build_page_ctx():
    """Готовит TLS для страницы. Настоящий сертификат предпочтительнее.

    Разница видна человеку и только человеку: на своё имя настоящий открывается
    молча, а самоподписанный — через красный замок и «всё равно перейти». Для
    чужого закрытого сайта оба одинаково не подходят, и это не лечится ничем.
    """
    global _cert_seen
    import ssl
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    pair = real_cert()
    if pair:
        try:
            ctx.load_cert_chain(pair[0], pair[1])
            _cert_seen = cert_stamp()
            return ctx, "настоящий"
        except Exception as e:
            print(f"Страница отказа: настоящий сертификат не читается — {e}",
                  flush=True)
    cert = ensure_cert()
    if not cert:
        return None, ""
    try:
        ctx.load_cert_chain(cert)
    except Exception as e:
        print(f"Страница отказа: свой сертификат не читается — {e}", flush=True)
        return None, ""
    _cert_seen = None
    return ctx, "самоподписанный"


async def cert_watch(ctx):
    """Следит за сертификатом: продление и появление.

    Перечитываем цепочку на месте — SSLContext это разрешает, и новые
    соединения берут уже новый сертификат. Перезапускать ради этого узел
    значило бы рвать всем связь раз в три месяца.

    Здесь же и переход с самоподписанного на настоящий: он появляется не при
    старте, а когда владелец задаст имя и доступ к зоне. Ждать перезапуска
    узла ради этого незачем.
    """
    global _cert_seen
    while True:
        await asyncio.sleep(600)
        try:
            stamp = cert_stamp()
            if stamp == _cert_seen:
                continue
            pair = real_cert()
            if not pair:
                continue
            ctx.load_cert_chain(pair[0], pair[1])
            was = _cert_seen
            _cert_seen = stamp
            print("Страница отказа: сертификат "
                  + ("перечитан" if was else "стал настоящим"), flush=True)
        except Exception as e:
            print(f"Страница отказа: сертификат обновить не вышло — {e}",
                  flush=True)


# Порт TLS-страницы отказа. Человек попадает сюда по правилу подмены 443 → 8443.
HTTPS_PAGE_PORT = 8443


async def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    FILTERS.maybe_reload()
    loop = asyncio.get_event_loop()
    # Общий сокет создаём руками, а не через local_addr: asyncio не ставит на
    # него разрешение делить адрес, и тогда второй сокет — на адресе узла —
    # занять этот же порт уже не сможет.
    wide = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    wide.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    wide.setblocking(False)
    wide.bind(("0.0.0.0", LISTEN_PORT))
    await loop.create_datagram_endpoint(DnsProtocol, sock=wide)
    # Второй сокет — ровно на адресе узла.
    #
    # Сокет на 0.0.0.0 сам выбирает, с какого адреса отвечать, по маршруту до
    # спрашивающего. Для пира это наш адрес: до пира идти через wg0. Но если
    # спрашивает кто-то, чей адрес живёт на самом узле, маршрут ведёт в петлю,
    # и ядро подставляет в ответ адрес спрашивающего — такой ответ клиент
    # выбрасывает. Сокет с явным адресом ядро предпочитает общему, и ответ
    # уходит с адреса узла всегда.
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Адрес может ещё не подняться к моменту старта резолвера: контейнер
        # поднимает сеть отдельно. FREEBIND разрешает занять его заранее.
        try:
            sock.setsockopt(socket.IPPROTO_IP, IP_FREEBIND, 1)
        except OSError:
            pass
        sock.setblocking(False)
        sock.bind((BLOCK_IP, LISTEN_PORT))
        await loop.create_datagram_endpoint(DnsProtocol, sock=sock)
        print(f"DNS слушает отдельно на {BLOCK_IP}:{LISTEN_PORT} — "
              f"ответы уходят с адреса узла", flush=True)
    except OSError as e:
        # Не повод падать: пиры работают и через общий сокет.
        print(f"Не вышло занять {BLOCK_IP}:{LISTEN_PORT} отдельно: {e}. "
              f"Пиры обслуживаются общим сокетом.", flush=True)
    server = await asyncio.start_server(handle_tcp, "0.0.0.0", LISTEN_PORT)
    try:
        await asyncio.start_server(handle_http, "0.0.0.0", 80)
        print("Страница отказа слушает :80", flush=True)
        ctx, kind = build_page_ctx()
        if ctx:
            # Не 443: человек сюда попадает не по адресу, а по правилу
            # подмены, поэтому номер порта ему безразличен, а 443 на узле
            # остаётся свободным.
            await asyncio.start_server(handle_http, "0.0.0.0", HTTPS_PAGE_PORT,
                                       ssl=ctx)
            print(f"Страница отказа слушает :{HTTPS_PAGE_PORT} ({kind})",
                  flush=True)
            asyncio.ensure_future(cert_watch(ctx))
    except Exception as e:
        # Не фатально: фильтр работает и без страницы, человек просто увидит
        # обычную ошибку соединения.
        print(f"Страница отказа не поднялась: {e}", flush=True)
    print(f"DNS-фильтр слушает :{LISTEN_PORT}, наверх ходит к {UPSTREAM}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

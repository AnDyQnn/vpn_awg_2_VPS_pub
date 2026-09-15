import os
import re
import socket
import ipaddress
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from datetime import datetime, timedelta

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Базовая (минимальная) версия формата маршрутизации конфига. Фактическая «текущая»
# версия живёт в БД (settings.routing_version) и поднимается при каждом изменении
# списка split-tunnel исключений — тогда все ранее выданные ключи становятся
# «устаревшими» и им уходит ежедневное напоминание о перевыпуске. Эта константа —
# нижняя граница (на случай пустого settings) и точка синхронизации с api.py.
ROUTING_VERSION = 1

# --- SPLIT-TUNNEL: дата-центро-враждебные РФ-сервисы (обход мимо VPN) ---
# Базовый список для ПЕРВИЧНОГО наполнения БД (таблица bypass_exclusions). Дальше
# список живёт в БД и пополняется анализатором/админом. Каждая запись: домен,
# подсети (через запятую), примечание.
BASE_BYPASS = [
    ("gosuslugi.ru", "213.59.252.0/22,109.207.0.0/18", "Госуслуги и ЕСИА (esia)"),
    ("max.ru", "155.212.204.0/24", "Мессенджер MAX"),
    ("vseinstrumenti.ru", "185.169.155.0/24", "ВсеИнструменты"),
]

# Предупреждение про приложения, которые блокируют VPN на уровне ядра телефона.
GOSUSLUGI_APP_WARNING = (
    "⚠️ *Важно про приложения Госуслуг/банков:*\n"
    "Часть мобильных приложений (например, «Госуслуги») блокирует работу при включённом "
    "VPN на уровне ядра телефона — через приложение они могут не открываться. "
    "В этом случае пользуйтесь *версией в браузере* (она ходит напрямую через исключение), "
    "либо временно отключайте VPN для такого приложения."
)


def analyze_resource(target: str):
    """Резолвит домен/URL в список IPv4 и агрегирует их в /24-подсети для добавления
    в split-tunnel исключения. Это БЛОКИРУЮЩАЯ операция (DNS) — вызывать через
    asyncio.to_thread. Возвращает dict: {domain, ips, cidrs, error}."""
    raw = (target or "").strip()
    if not raw:
        return {"domain": "", "ips": [], "cidrs": [], "error": "Пустой адрес"}

    # Достаём хост из URL или принимаем «голый» домен (отрезаем путь/порт)
    if "://" in raw:
        host = urlparse(raw).hostname or ""
    else:
        host = raw.split("/")[0].split(":")[0]
    host = (host or "").strip().lower().lstrip("@")
    if not host:
        return {"domain": "", "ips": [], "cidrs": [], "error": "Не удалось извлечь домен"}

    try:
        infos = socket.getaddrinfo(host, 443, socket.AF_INET)
        ips = sorted({i[4][0] for i in infos})
    except Exception as e:
        return {"domain": host, "ips": [], "cidrs": [], "error": f"DNS не разрешился: {e}"}

    if not ips:
        return {"domain": host, "ips": [], "cidrs": [], "error": "Адрес не разрешился в IPv4"}

    cidrs = sorted({str(ipaddress.ip_network(f"{ip}/24", strict=False)) for ip in ips})
    return {"domain": host, "ips": ips, "cidrs": cidrs, "error": None}

VERSION_FILE = "/app/VERSION_FILE"
BACKUP_FILE = "/volumes/backups/backup_latest.tar.gz"
GIT_REPO = os.getenv("GIT_REPO", "") 
GIT_USERNAME = os.getenv("GIT_USERNAME", "")
GIT_TOKEN = os.getenv("GIT_TOKEN", "")

# API серверов (Бот и WireGuard теперь в одной сети, поэтому 127.0.0.1)
WG_API_URL = os.getenv("WG_API_URL", "http://127.0.0.1:8000/api")
DE_AGENT_URL = os.getenv("DE_AGENT_URL", "http://10.13.13.254:8000/api")

# Токен для панелей узлов. Все запросы бота идут только на WG_API_URL и DE_AGENT_URL —
# наружу не ходит ни один, поэтому заголовок можно вешать на сессию целиком, не рискуя
# отправить токен постороннему хосту. Токен необязателен: без него узлы работают как
# раньше (см. комментарий в ru_wg_api/api.py), обновление ничего не ломает.
API_TOKEN = os.getenv("API_TOKEN", "").strip()
API_HEADERS = {"X-Api-Key": API_TOKEN} if API_TOKEN else {}


# Пароль архива бэкапа. Живёт ТОЛЬКО в .env на хосте: в базе он оказался бы внутри
# того самого архива, который защищает, и, потеряв сервер, ты получил бы зашифрованную
# копию с паролем внутри неё. В архив .env не входит.
BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD", "").strip()

FLAGS_DIR = Path("/volumes/flags")


def request_env_change(key: str, value: str):
    """Просит демон на хосте записать переменную в .env и пересоздать контейнеры.

    Сам бот .env не видит: он получает переменные окружения, а не файл. Поэтому
    кладём строку во флаг, демон её применяет и сразу затирает файл.
    """
    import secrets
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    # Своё имя на каждую просьбу. Раньше файл был один на всех, и записывался
    # он перезаписью: бот выдавал токен панелей при первом запуске, владелец
    # тут же задавал пароль архива — и одна из двух просьб исчезала бесследно.
    flag = FLAGS_DIR / ("set_env." + secrets.token_hex(6))
    with open(flag, "w") as f:
        f.write(f"{key}={value}\n")
    try:
        os.chmod(flag, 0o600)
    except OSError:
        pass
    return flag


async def env_change_applied(flag=None, timeout: int = 45) -> bool:
    """Дождаться, пока демон на хосте заберёт просьбу.

    Раньше бот писал «записано и применяется» сразу после того, как положил
    файл. Но положить — не значит применить: если демон не запущен, просьба
    лежит вечно, а человек уверен, что всё сделал. Пароль архива после такого
    спрашивается снова и снова, и выглядит это как поломка бота.

    Ждём именно свой файл: чужая просьба могла появиться и исчезнуть в то же
    окно, и тогда ответ был бы про неё.

    Признак простой: демон забирает файл, когда применил. Исчез — применено.
    """
    import asyncio
    if flag is None:
        return False
    for _ in range(max(1, timeout)):
        if not flag.exists():
            return True
        await asyncio.sleep(1)
    return False


def api_session(**kwargs):
    """Сессия для запросов к панелям узлов — с токеном, если он задан."""
    import aiohttp
    headers = dict(kwargs.pop("headers", {}) or {})
    headers.update(API_HEADERS)
    return aiohttp.ClientSession(headers=headers, **kwargs)

CONFIGS_DIR = Path("/volumes/configs")
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

# --- ГЛОБАЛЬНОЕ СОСТОЯНИЕ ---
state_data = {
    "dashboard_running": False,
    "dashboard_task": None,
    "graph_running": False,
    "graph_task": None,
    "active_menus": {},
    "last_known_active_count": -1,
    "support_context": {},
    "bg_tasks": set(),
    # адрес → когда по нему в последний раз шли пакеты. Отсюда «на связи»
    # для Xray: рукопожатий там нет, а трафик есть.
    "addr_seen": {}
}

# --- ВРЕМЯ (МОСКВА UTC+3) ---
def get_moscow_now():
    """Возвращает текущее Московское время"""
    return datetime.utcnow() + timedelta(hours=3)

def dt_to_moscow(dt):
    """Конвертирует UTC datetime из базы данных в Московское время"""
    if not dt: return dt
    return dt + timedelta(hours=3)

def ts_to_moscow(ts):
    """Конвертирует Unix Timestamp в Московское время"""
    return datetime.utcfromtimestamp(ts) + timedelta(hours=3)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def check_admin(user_id):
    return user_id == ADMIN_ID

def escape_md(text: str) -> str:
    if not text: return ""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

# Карта транслитерации кириллицы (для имён тоннелей AmneziaWG)
_TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'і': 'i', 'ї': 'yi', 'є': 'e', 'ґ': 'g',
}

def sanitize_name(raw: str, fallback: str = "user") -> str:
    """Делает имя ключа безопасным для имени тоннеля AmneziaWG/WireGuard.

    Приложение AmneziaWG принимает только имена вида [A-Za-z0-9_=+.-] длиной
    до 15 символов и ругается «неверно задано поле имя» на кириллицу/эмодзи.
    Здесь: кириллица -> латиница (транслит), эмодзи/символы -> отбрасываются,
    пробелы -> '_'. Регистр латиницы сохраняется ('Иван' -> 'Ivan').
    """
    if not raw:
        return fallback
    out = []
    for ch in raw.strip():
        low = ch.lower()
        if low in _TRANSLIT_MAP:
            t = _TRANSLIT_MAP[low]
            out.append(t.upper() if ch.isupper() else t)
        elif ch.isascii() and ch.isalnum():
            out.append(ch)
        elif ch in ' _-.':
            out.append('_')
        # всё прочее (эмодзи, иероглифы, спецсимволы) — отбрасываем
    name = re.sub(r'_+', '_', ''.join(out)).strip('_-.')
    name = name[:15].strip('_-.')
    return name or fallback

async def extract_tg_id(message, context):
    if not message: return None

    if message.contact and message.contact.user_id:
        return message.contact.user_id

    if message.forward_date:
        if message.forward_from:
            return message.forward_from.id
        return "HIDDEN"

    if message.text:
        text = message.text.strip()
        if text.lstrip('-').isdigit():
            return int(text)
        if text.startswith("@"):
            try:
                chat = await context.bot.get_chat(text)
                return chat.id
            except BadRequest:
                return "INVALID"

    return None

def get_current_version():
    try:
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r") as f: return f.read().strip()
    except Exception: pass
    return "Unknown"

def get_update_info():
    local_hash = "unknown"
    local_version = get_current_version()
    remote_hash = "unknown"
    remote_version = "unknown"

    try:
        if os.path.exists("/volumes/VERSION"):
            with open("/volumes/VERSION", "r") as f:
                local_hash = f.read().strip()[:7]
    except Exception: pass

    try:
        if not GIT_REPO: return local_hash, local_version, remote_hash, remote_version
        auth_repo_url = GIT_REPO
        if GIT_TOKEN and "https://" in GIT_REPO and "@" not in GIT_REPO:
            prefix = "https://"
            suffix = GIT_REPO[len(prefix):]
            auth_repo_url = f"{prefix}{GIT_USERNAME}:{GIT_TOKEN}@{suffix}" if GIT_USERNAME else f"{prefix}{GIT_TOKEN}@{suffix}"
        
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        
        cmd_hash = f"git ls-remote '{auth_repo_url}' refs/heads/main refs/heads/master"
        output = subprocess.check_output(cmd_hash, shell=True, stderr=subprocess.STDOUT, env=env, timeout=15).decode().strip()
        if output:
            remote_hash = output.split()[0][:7]

        cmd_ver = (
            "rm -rf /tmp/repo_check && mkdir -p /tmp/repo_check && cd /tmp/repo_check && "
            "git init && "
            f"git remote add origin '{auth_repo_url}' && "
            "git config core.sparseCheckout true && "
            "echo 'VPS_RU/VERSION' >> .git/info/sparse-checkout && "
            "echo 'VERSION' >> .git/info/sparse-checkout && "
            "(git pull --depth=1 origin main >/dev/null 2>&1 || git pull --depth=1 origin master >/dev/null 2>&1) && "
            "(cat VPS_RU/VERSION 2>/dev/null || cat VERSION 2>/dev/null)"
        )
        output_ver = subprocess.check_output(cmd_ver, shell=True, stderr=subprocess.STDOUT, env=env, timeout=30).decode().strip()
        if output_ver:
            remote_version = output_ver.split('\n')[-1].strip()

    except Exception as e:
        print(f"Error checking update: {e}")

    return local_hash, local_version, remote_hash, remote_version

async def safe_delete(context, chat_id, message_id):
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception: pass

async def stop_bg_tasks():
    state_data["dashboard_running"] = False
    if state_data["dashboard_task"]:
        state_data["dashboard_task"].cancel()
        state_data["dashboard_task"] = None
    state_data["graph_running"] = False
    if state_data["graph_task"]:
        state_data["graph_task"].cancel()
        state_data["graph_task"] = None

# Имя пира клиент-сервера. Он не человек: через него проходит мировой трафик
# всех остальных, поэтому в лимитах, подборе и сводке ему не место.
AGENT_PEER_NAME = "DE_AGENT"


def is_agent(name) -> bool:
    return (name or "").strip().upper() == AGENT_PEER_NAME


async def show_screen(query, context, text, reply_markup=None, parse_mode=None,
                      disable_preview=False):
    """Показывает экран поверх текущего сообщения.

    Если текущее сообщение — картинка (например график), редактировать текст
    нельзя: у медиа его нет, и Telegram отвечает отказом. В этом случае картинка
    убирается, а экран приходит новым сообщением. Для человека разницы нет,
    для кнопок — принципиальная: иначе они молча ничего не делают.
    """
    from telegram.constants import ParseMode as _PM
    if parse_mode is None:
        parse_mode = _PM.MARKDOWN

    msg = getattr(query, "message", None)
    is_media = bool(getattr(msg, "photo", None) or getattr(msg, "document", None))

    if not is_media:
        try:
            return await query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode=parse_mode,
                disable_web_page_preview=disable_preview)
        except Exception as e:
            low = str(e).lower()
            if "no text" not in low and "can't be edited" not in low and "not modified" not in low:
                raise
            if "not modified" in low:
                return None

    chat_id = msg.chat_id if msg else query.from_user.id
    if msg:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        except Exception:
            pass
    return await context.bot.send_message(chat_id=chat_id, text=text,
                                          reply_markup=reply_markup,
                                          parse_mode=parse_mode,
                                          disable_web_page_preview=disable_preview)


async def send_copyable(bot, chat_id, text, **kwargs):
    """Шлёт текст так, чтобы он копировался одним касанием.

    Telegram копирует в буфер целиком то, что помечено как код. Пометка идёт
    сущностью, а не разметкой: в ссылках попадаются знаки, которые разметка
    принимает на свой счёт, и одно непарное подчёркивание роняет сообщение
    целиком — так уже терялась выдача ключа.

    Длина — в кодовых единицах UTF-16, как её считает Telegram: имя в ссылке
    бывает с эмодзи, и там обычный len() промахивается.
    """
    from telegram import MessageEntity
    length = len(text.encode("utf-16-le")) // 2
    return await bot.send_message(
        chat_id=chat_id, text=text,
        entities=[MessageEntity(type=MessageEntity.CODE, offset=0, length=length)],
        **kwargs)


def exit_kb(*extra, to_client=False):
    """Клавиатура для сообщения, которым разговор закончился.

    Такое сообщение обязано иметь выход: иначе человек упирается в него и лезет
    листать чат вверх в поисках чего-нибудь нажимаемого. `extra` — пары
    (подпись, callback) для более точного возврата: к тому, что только что
    получилось, а не просто в начало.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    rows = [[InlineKeyboardButton(title, callback_data=data)]
            for title, data in extra]
    if to_client:
        rows.append([InlineKeyboardButton("🏠 Личный кабинет",
                                          callback_data="client_menu")])
    else:
        rows.append([InlineKeyboardButton("🔙 Главное меню",
                                          callback_data="back_to_main")])
    return InlineKeyboardMarkup(rows)


def deregister_menu(chat_id):
    if chat_id in state_data["active_menus"]:
        del state_data["active_menus"][chat_id]

async def broadcast_message(app, text, db_ref):
    try:
        tg_ids = await db_ref.get_all_tg_ids()
        if ADMIN_ID not in tg_ids: tg_ids.append(ADMIN_ID)
        tg_ids = list(set(tg_ids))
        for uid in tg_ids:
            try:
                if uid == ADMIN_ID:
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛡 Панель управления", callback_data="back_to_main")]])
                else:
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Личный кабинет", callback_data="client_menu")]])
                
                await app.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown", reply_markup=kb)
            except Exception: pass
    except Exception as e: print(f"Broadcast error: {e}")
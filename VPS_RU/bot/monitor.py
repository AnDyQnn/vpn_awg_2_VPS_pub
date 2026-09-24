import json
import os
import re
import time
import socket
import ipaddress
import psutil
import asyncio
import aiohttp
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import (
    api_session,
    get_moscow_now, dt_to_moscow, broadcast_message, DE_AGENT_URL, WG_API_URL,
    is_agent,
    ADMIN_ID, escape_md, GOSUSLUGI_APP_WARNING, analyze_resource, CONFIGS_DIR, ROUTING_VERSION,
    get_update_info, state_data
)

# --- SPLIT-TUNNEL: дата-центро-враждебные РФ-сервисы (мимо VPN, через домашний канал) ---
# Источник правды — БД (таблица bypass_exclusions, см. database.py). Здесь только
# логика проверки дрейфа и формирования уведомлений.

UPGRADE_INSTRUCTION = (
    "🔄 *Как обновить (новый ключ выдаётся автоматически):*\n"
    "1️⃣ Нажми «Перевыпустить» ниже — бот пришлёт новый `.conf` и QR.\n"
    "2️⃣ В приложении *AmneziaWG* удали старое подключение.\n"
    "3️⃣ Добавь новое одним из способов:\n"
    "   • *QR:* «＋» → «Сканировать QR-код» → наведи на новый QR;\n"
    "   • *Файл:* «＋» → «Импорт из файла» → выбери новый `.conf`.\n"
    "4️⃣ Включи VPN. Готово — сервисы из списка ниже заработают."
)

def _check_bypass_drift(entries):
    """Синхронно: резолвит домены исключений и проверяет, что их IP всё ещё внутри
    заявленных подсетей. entries: список (domain, [cidr, ...]). Возвращает список
    'ушедших' адресов (drift)."""
    drifted = []
    for domain, cidrs in entries:
        nets = []
        for c in cidrs:
            try:
                nets.append(ipaddress.ip_network(c))
            except ValueError:
                continue
        if not nets:
            continue
        try:
            infos = socket.getaddrinfo(domain, 443, socket.AF_INET)
            ips = sorted({i[4][0] for i in infos})
        except Exception:
            continue
        for ip in ips:
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if not any(addr in n for n in nets):
                drifted.append((domain, ip))
    return drifted

async def _bypass_drift_entries():
    """Готовит (domain, [cidr,...]) из БД для проверки дрейфа."""
    rows = await db.get_bypass_exclusions()
    return [(r['domain'], [c.strip() for c in (r['cidrs'] or '').split(',') if c.strip()]) for r in rows]


def _config_is_split_tunnel(name):
    """Определяет по выданному .conf, применён ли split-tunnel (обход), читая AllowedIPs.
    Полный туннель содержит '0.0.0.0/0', split-tunnel — раздробленные подсети без него.
    Возвращает True/False, либо None если файл не найден (судить не можем)."""
    for fn in (f"{name}.conf", f"{name}_Full.conf", f"{name}_Smart.conf"):
        p = CONFIGS_DIR / fn
        if p.exists():
            try:
                txt = p.read_text()
            except Exception:
                continue
            m = re.search(r"AllowedIPs\s*=\s*(.+)", txt)
            if m:
                return "0.0.0.0/0" not in m.group(1)
    return None


async def repair_traffic_directions():
    """Разворачивает промежутки истории, записанные с перепутанными колонками.

    Сборщик когда-то писал приём в колонку отдачи: любой качающий выглядел
    раздающим, и по такой истории нельзя было понять ни кто качает, ни кто
    раздаёт. Сборщик починен, но записанное тогда так и лежит перевёрнутым.

    Почему само, а не кнопкой. Это не выбор и не настройка: перевёрнутые данные
    просто неверны, и держать их такими незачем. Кнопка предлагала владельцу
    решать то, у чего один правильный ответ.

    Делается один раз за всю жизнь установки — по отметке в настройках. Даже
    если разбор данных однажды ошибётся, второй попытки у него не будет.
    """
    try:
        if await db.get_setting("traffic_direction_repaired"):
            return 0
        spans = await db.find_inverted_spans()
        if not spans:
            return 0
        total = 0
        parts = []
        for start_h, end_h in spans:
            n = await db.count_hourly_range(start_h, end_h)
            if not n:
                continue
            await db.swap_hourly_range(start_h, end_h)
            total += n
            parts.append(f"{start_h:%d.%m %H:%M}–{end_h:%d.%m %H:%M}")
        if not total:
            return 0
        await db.set_setting("traffic_direction_repaired",
                             datetime.utcnow().strftime("%Y-%m-%dT%H:%M"))
        await db.log_event(
            "Трафик",
            f"История развёрнута автоматически: строк {total}, "
            f"промежутки: {', '.join(parts)}")
        print(f"Трафик: развёрнуто строк {total}, промежутки {parts}")
        return total
    except Exception as e:
        print(f"Трафик: развернуть историю не вышло: {e}")
        return 0


async def reconcile_routing_versions():
    """Одноразовая сверка при старте: чинит ключи, которые УЖЕ были перевыпущены до
    фикса бага (routing_version записался как 0), хотя их конфиг по факту содержит
    split-tunnel. Такие ключи иначе бесконечно получали бы напоминания о перевыпуске.
    Настоящие старые ключи (полный туннель) остаются на 0 и продолжают получать
    напоминания — это корректно."""
    try:
        rows = await db.fetch_all("SELECT uuid, name, COALESCE(routing_version,0) AS rv FROM users")
    except Exception as e:
        print(f"reconcile_routing_versions: {e}")
        return 0

    fixed = 0
    for r in rows:
        if r['rv'] >= ROUTING_VERSION:
            continue
        is_split = await asyncio.to_thread(_config_is_split_tunnel, r['name'])
        if is_split is True:
            await db.execute("UPDATE users SET routing_version=$1 WHERE uuid=$2", ROUTING_VERSION, r['uuid'])
            fixed += 1
    if fixed:
        await db.log_event("Routing", f"Reconciled routing_version for {fixed} already-reissued key(s).")
        print(f"✅ Реконсиляция: проставлена актуальная routing_version у {fixed} уже-перевыпущенных ключей.")
    return fixed

notified_cache = set()
last_ip_cache = {}

ghost_cache = {}
paused_cache = {}
flapping_cache = {}
resource_alert_cache = {}
# online_since[uuid] = ts начала ТЕКУЩЕЙ сессии (первый раз, когда увидели пира онлайн).
# Ведётся в alert_loop (always-on, каждые 10с): не затирается свежими хэндшейками, поэтому
# длительность онлайна растёт корректно (баг: раньше показывали «сколько прошло с хэндшейка»,
# а он обновляется keepalive каждые ~2 мин → всегда 0–3 мин). Чистится, когда пир ушёл офлайн.
online_since = {}

# --- АНТИ-ШЕРИНГ: отличаем реальный шеринг от легитимной смены сети ---
# Истинный шеринг = НЕСКОЛЬКО устройств онлайн ОДНОВРЕМЕННО: endpoint пира быстро
# «пинг-понгует» между малым числом адресов и не затихает (каждое устройство шлёт
# handshake каждые ~25с keepalive). Легитимное переключение (самолёт/Wi-Fi/моб.) даёт
# лишь пару смен и успокаивается, либо идёт через РАЗНЫЕ сети.
# Поэтому баним только при УСТОЙЧИВОЙ осцилляции между малым числом адресов.
FLAP_WINDOW = 300          # окно наблюдения, сек
FLAP_MIN_JUMPS = 8         # минимум смен адреса в окне (раньше было 3 — ловило легит-свитч)
FLAP_MAX_DISTINCT = 3      # ...при этом всего <= стольких уникальных адресов (пинг-понг)

# Авто-абсорбция дрейфа: верхний предел подсетей на один домен, чтобы авто-расширение
# не раздуло AllowedIPs/QR (если сервис рассеян по многим IP — зовём админа вручную).
MAX_CIDRS_PER_DOMAIN = 10

# ------------------------ АЛЕРТЫ АДМИНУ (+ авто-очистка в 00:00) ------------------------
async def notify_admin(app, text, **kw):
    """Шлёт алерт админу И запоминает message_id, чтобы в 00:00 их автоматически удалить из
    чата (не засорять). Возвращает объект сообщения (или None). chat_id передаём позиционно,
    чтобы этот helper не попал под массовую замену вызовов."""
    if not ADMIN_ID:
        return None
    try:
        msg = await app.bot.send_message(ADMIN_ID, text, **kw)
    except Exception:
        return None
    # Номер сообщения здесь больше не записываем: этим занимается chat_cleanup,
    # и занимается перехватом отправки — то есть знает про ВСЕ сообщения
    # владельцу, а не только про тревоги. Два списка на один чат означали бы две
    # правды о том, что уже удалено, и они однажды разойдутся.
    return msg

# Полуночная чистка тревог жила здесь и знала только про них. Её заменил
# chat_cleanup: он считает не места отправки, а сами отправленные сообщения, и
# потому не пропускает ни биллинг, ни архивы, ни ответы на нажатия.


# ------------------------ DASHBOARD ------------------------
def _bar(pct, width=10):
    """Юникод-шкала загрузки для моноширинного блока Telegram: ██████░░░░."""
    try:
        pct = max(0.0, min(100.0, float(pct)))
    except (TypeError, ValueError):
        pct = 0.0
    filled = int(round(pct / 100.0 * width))
    return "█" * filled + "░" * (width - filled)

def _metrics_block(cpu, ram, disk):
    """Три ровные моноширинные строки метрик со шкалами (колонки не пляшут)."""
    def _f(x):
        try: return float(x)
        except (TypeError, ValueError): return 0.0
    return (
        f"`CPU  {_bar(cpu)} {_f(cpu):3.0f}%`\n"
        f"`RAM  {_bar(ram)} {_f(ram):3.0f}%`\n"
        f"`Диск {_bar(disk)} {_f(disk):3.0f}%`"
    )

async def get_dashboard():
    cpu_ru = psutil.cpu_percent()
    ram_ru = psutil.virtual_memory().percent
    disk_ru = psutil.disk_usage("/").percent

    # RU: активные VPN-сессии (и жив ли WG-API)
    active, total, ru_ok = 0, 0, True
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/status", timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    total = data.get("peers_count", 0)
                    active = data.get("active_peers", 0)
                else:
                    ru_ok = False
    except Exception:
        ru_ok = False

    # DE: ресурсы агента (и жив ли он)
    de_ok, cpu_de, ram_de, disk_de = False, 0, 0, 0
    try:
        async with api_session() as session:
            async with session.get(f"{DE_AGENT_URL}/system_stats", timeout=3) as resp:
                if resp.status == 200:
                    d = await resp.json()
                    cpu_de, ram_de, disk_de = d.get('cpu', 0), d.get('ram', 0), d.get('disk', 0)
                    de_ok = True
    except Exception:
        pass

    try:
        bypass_count = len(await db.get_all_bypass_cidrs())
        outdated_count = len(await db.get_outdated_keys(await db.get_routing_version()))
    except Exception:
        bypass_count = outdated_count = 0

    # Одна статус-точка на ноду: 🔴 недоступна/перегруз, 🟡 средне, 🟢 ок.
    def node_dot(ok, cpu, ram, disk):
        """Цвет узла. У диска пороги свои и выше остальных: на узле с десятью
        гигабайтами система занимает больше половины, и 73% — обычное рабочее
        состояние. С общим порогом в 70% кружок горел бы жёлтым всегда, то есть
        не значил бы ничего."""
        if not ok:
            return "🔴"
        load = max(float(cpu or 0), float(ram or 0))
        disk = float(disk or 0)
        if load >= 90 or disk >= 93:
            return "🔴"
        if load >= 70 or disk >= 85:
            return "🟡"
        return "🟢"

    ru_dot = node_dot(ru_ok, cpu_ru, ram_ru, disk_ru)
    de_dot = node_dot(de_ok, cpu_de, ram_de, disk_de)
    ru_block = _metrics_block(cpu_ru, ram_ru, disk_ru) if ru_ok else "_мастер недоступен_"
    de_block = _metrics_block(cpu_de, ram_de, disk_de) if de_ok else "_агент недоступен_"
    sep = "━━━━━━━━━━━━━━"

    return (
        f"📊 **Дашборд** · Россия и Германия\n"
        f"{sep}\n"
        f"{ru_dot} 🇷🇺 **RU** · мастер\n"
        f"{ru_block}\n\n"
        f"{de_dot} 🇩🇪 **DE** · агент обхода\n"
        f"{de_block}\n"
        f"{sep}\n"
        f"🔌 Сессий: **{active}** из {total}\n"
        f"🌐 Исключений: **{bypass_count}**   ♻️ Старых ключей: **{outdated_count}**"
    )

# ------------------------ СИСТЕМНЫЕ АЛЕРТЫ ------------------------

# Сколько раз подряд узел должен не ответить, прежде чем звать владельца.
#
# Раньше хватало одного неудачного запроса с пятисекундным ожиданием — и
# приходило «Агент недоступен, упал туннель или сервис». Хватало занятого
# агента, снятия копии или секундной задержки в туннеле. Владелец бежал
# смотреть, а там всё работало.
#
# Проверки идут раз в пять минут, так что три промаха — это четверть часа
# молчания подряд. Настоящее падение столько не прячется, а случайная заминка
# не доживает.
DE_MISSES_TO_ALERT = 3
_de_misses = 0


def _overloaded(load1, cores):
    """Перегружен ли узел. Судим по среднему за минуту, а не по мгновению.

    Мгновенный замер показывает сотню на ровном месте: хватает ночной проверки
    обновлений или снятия копии. Такие тревоги приходят регулярно, ничего не
    значат — и их перестают читать вместе с настоящими.

    Полтора на ядро: кратковременная очередь это норма, устойчивая — нет.
    """
    try:
        return float(load1) / max(1, int(cores or 1)) >= 1.5
    except (TypeError, ValueError):
        return False


async def resource_monitor_loop(app):
    global _de_misses
    while True:
        await asyncio.sleep(300)
        now = time.time()

        def should_alert(key):
            if key not in resource_alert_cache or (now - resource_alert_cache[key]) > 3600:
                resource_alert_cache[key] = now
                return True
            return False

        # Тревоги разного рода: у них разные заголовки. Раньше всё шло под
        # «Критическая нагрузка», и сообщение о недоступном узле читалось как
        # «упал И перегружен» разом — ровно то, чего не было.
        load_alerts = []
        down_alerts = []

        try:
            import os as _os
            load1 = _os.getloadavg()[0]
            cores = psutil.cpu_count() or 1
        except Exception:
            load1, cores = 0, 1
        ram_ru = psutil.virtual_memory().percent
        disk_ru = psutil.disk_usage("/").percent

        if _overloaded(load1, cores) and should_alert("RU_CPU"):
            load_alerts.append(f"🇷🇺 **Мастер:** среднее за минуту {load1:.2f} на {cores} ядр.")
        if ram_ru > 95 and should_alert("RU_RAM"):
            load_alerts.append(f"🇷🇺 **Мастер, память:** {ram_ru}%")
        if disk_ru > 90 and should_alert("RU_DISK"):
            load_alerts.append(f"🇷🇺 **Мастер, диск:** {disk_ru}%")

        try:
            async with api_session() as session:
                async with session.get(f"{DE_AGENT_URL}/system_stats", timeout=10) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"код {resp.status}")
                    de_data = await resp.json()
            _de_misses = 0
            ram_de = de_data.get("ram", 0)
            disk_de = de_data.get("disk", 0)
            # Германия отдаёт и мгновенный процент, и среднее — если умеет.
            # Не умеет (старая версия) — по нагрузке её просто не судим, а не
            # выдумываем тревогу из мгновенного замера.
            load_de = de_data.get("load1")
            cores_de = de_data.get("cores", 1)
            if load_de is not None and _overloaded(load_de, cores_de) and should_alert("DE_CPU"):
                load_alerts.append(
                    f"🇩🇪 **Германия:** среднее за минуту {float(load_de):.2f} на {cores_de} ядр.")
            if ram_de > 95 and should_alert("DE_RAM"):
                load_alerts.append(f"🇩🇪 **Германия, память:** {ram_de}%")
            if disk_de > 90 and should_alert("DE_DISK"):
                load_alerts.append(f"🇩🇪 **Германия, диск:** {disk_de}%")
        except Exception as e:
            _de_misses += 1
            if _de_misses >= DE_MISSES_TO_ALERT and should_alert("DE_DOWN"):
                down_alerts.append(
                    f"🇩🇪 **Германия не отвечает** — подряд {_de_misses} раза, "
                    f"это больше четверти часа.\n_Последняя причина: {e}_")

        if not (load_alerts or down_alerts) or not ADMIN_ID:
            continue

        parts = []
        if down_alerts:
            parts.append("🚨 **Узел не отвечает**\n\n" + "\n".join(down_alerts))
        if load_alerts:
            parts.append("⚠️ **Высокая нагрузка**\n\n" + "\n".join(load_alerts))
        try:
            await notify_admin(app, text="\n\n".join(parts), parse_mode="Markdown")
        except Exception:
            pass


# ------------------------ MONITOR & ANTI-SHARING ------------------------
async def alert_loop(app):
    wg_is_down = False
    
    while True:
        try:
            async with api_session() as session:
                async with session.get(f"{WG_API_URL}/peers", timeout=5) as resp:
                    resp.raise_for_status()
                    peers_data = await resp.json()

            if wg_is_down:
                wg_is_down = False
                if ADMIN_ID:
                    kb_admin = InlineKeyboardMarkup([[InlineKeyboardButton("🛡 В админку", callback_data="back_to_main")]])
                    await notify_admin(app, text="✅ VPN-сервер снова в сети.", reply_markup=kb_admin)
                    await db.log_event("System", "VPN Server is back online.")

            now = int(time.time())
            active_uuids = set()
            
            users_list = await db.get_all_users()
            users_dict = {u['uuid']: u for u in users_list}

            for peer in peers_data:
                uuid_val = peer.get("uuid")
                pubkey = peer.get("public_key")
                handshake = peer.get("latest_handshake", 0)
                endpoint = peer.get("endpoint", "")
                
                if not pubkey or pubkey == "(none)": continue
                
                is_ghost = False
                is_paused_violation = False
                
                if uuid_val not in users_dict: is_ghost = True
                elif not users_dict[uuid_val].get('is_active', True): is_paused_violation = True
                    
                if is_ghost or is_paused_violation:
                    try:
                        async with api_session() as kill_session:
                            await kill_session.post(f"{WG_API_URL}/kill_ghost", json={"public_key": pubkey, "purge_config": is_ghost}, timeout=5)
                    except Exception: pass
                    
                    if endpoint and endpoint != "(none)":
                        if is_ghost:
                            if pubkey not in ghost_cache or (now - ghost_cache[pubkey] > 3600):
                                ghost_cache[pubkey] = now
                                msg = f"🚨 **Несанкционированный доступ!**\n\nНеизвестный ключ (Призрак) попытался подключиться.\n📱 IP: `{endpoint}`\n🔑 PubKey: `{pubkey}`\n\n🛡 Сессия принудительно разорвана."
                                if ADMIN_ID: await notify_admin(app, text=msg, parse_mode="Markdown")
                                await db.log_event("Security", f"Killed ghost connection from {endpoint}")
                        elif is_paused_violation:
                            if uuid_val not in paused_cache or (now - paused_cache[uuid_val] > 3600):
                                paused_cache[uuid_val] = now
                                u_name = escape_md(users_dict[uuid_val]['name'])
                                msg = f"🛡 **Блокировка доступа!**\n\nОтключенный пользователь **{u_name}** попытался подключиться.\n📱 IP: `{endpoint}`\n\n⛔️ Доступ отклонен."
                                if ADMIN_ID: await notify_admin(app, text=msg, parse_mode="Markdown")
                                await db.log_event("Security", f"Blocked access for paused user {users_dict[uuid_val]['name']}")
                    continue

                hostname = endpoint.split(":")[0] if endpoint and endpoint != "(none)" else ""

                if handshake > 0 and (now - handshake) < 180 and hostname:
                    active_uuids.add(uuid_val)
                    online_since.setdefault(uuid_val, now)   # старт сессии — только при первом появлении
                    user = users_dict.get(uuid_val)

                    if user:
                        prev_ip, prev_time = last_ip_cache.get(uuid_val, ("", 0))
                        
                        if hostname != prev_ip and prev_ip != "":
                            events = flapping_cache.get(uuid_val, [])
                            events.append((hostname, now))
                            events = [(ip, t) for (ip, t) in events if (now - t) < FLAP_WINDOW]
                            flapping_cache[uuid_val] = events

                            distinct_ips = len({ip for ip, _ in events})
                            # Бан ТОЛЬКО при устойчивом пинг-понге: много смен между малым
                            # числом адресов (несколько устройств онлайн одновременно).
                            # Легитимное переключение сети сюда не попадает.
                            if len(events) >= FLAP_MIN_JUMPS and distinct_ips <= FLAP_MAX_DISTINCT:
                                try:
                                    async with api_session() as session:
                                        await session.post(f"{WG_API_URL}/peers/{uuid_val}/pause")
                                except Exception: pass
                                
                                await db.execute("UPDATE users SET is_active=FALSE WHERE uuid=$1", uuid_val)
                                await db.log_event("Security", f"KEY COMPROMISED (Flapping): {user['name']}")
                                
                                if ADMIN_ID:
                                    safe_name = escape_md(user['name'])
                                    alert_msg = f"🚨 **КЛЮЧ СКОМПРОМЕТИРОВАН!**\n\n👤 Пользователь: **{safe_name}**\n🔄 Устойчивое переключение между {distinct_ips} адресами ({len(events)} смен за 5 мин) — похоже на одновременное использование на нескольких устройствах.\n⛔️ **Ключ заморожен.**"
                                    await notify_admin(app, text=alert_msg, parse_mode="Markdown")

                                tg_ids = user.get('tg_ids', [])
                                kb_client = InlineKeyboardMarkup([[InlineKeyboardButton("🆘 Связаться с Админом", callback_data="support_start")]])
                                for tid in tg_ids:
                                    try: await app.bot.send_message(chat_id=tid, text="⚠️ **Ваш VPN-ключ заблокирован.**\n\nЗафиксировано использование на нескольких устройствах. Обратитесь к администратору.", parse_mode="Markdown", reply_markup=kb_client)
                                    except: pass
                                
                                flapping_cache[uuid_val] = []
                                last_ip_cache[uuid_val] = (hostname, now)
                                continue

                        # Трек IP (система доверенных адресов): при смене адреса или раз в ~5 мин.
                        # Отдельный алерт на смену адреса УБРАН: единичная смена (WiFi↔моб.) — норма.
                        # Реальный абьюз — пинг-понг между адресами (будто 2 юзера на одном ключе) —
                        # ловит и БАНИТ detect flapping выше, он же и уведомляет админа.
                        if hostname != prev_ip or (now - prev_time) > 300:
                            await db.track_user_ip(uuid_val, hostname)

                        last_ip_cache[uuid_val] = (hostname, now)

                    if uuid_val not in notified_cache:
                        device_set = await db.device_set(uuid_val)
                        if user:
                            safe_name = escape_md(user['name'])
                            if not device_set:
                                await db.execute("UPDATE users SET device=$1, first_connected_at=NOW() WHERE uuid=$2", hostname, uuid_val)
                                await db.log_event("Connection", f"First connection by {user['name']} from {hostname}")
                                if ADMIN_ID: await notify_admin(app, text=f"🎉 **Новое подключение!**\n\n👤 {safe_name}\n📱 `{hostname}`\n🆔 `{uuid_val}`", parse_mode="Markdown")

                                tg_ids = user.get('tg_ids',[])
                                if tg_ids:
                                    msg_tg = f"🟢 **VPN Подключен!**\n\nКлюч: **{safe_name}**."
                                    kb_client = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Личный кабинет", callback_data="client_menu")]])
                                    for tid in tg_ids:
                                        try: await app.bot.send_message(chat_id=tid, text=msg_tg, parse_mode="Markdown", reply_markup=kb_client)
                                        except Exception: pass
                        notified_cache.add(uuid_val) 

            disconnected_uuids = notified_cache - active_uuids
            for uid in disconnected_uuids: notified_cache.remove(uid)
            # Пир ушёл офлайн — сбрасываем старт сессии (при возврате начнётся заново).
            for uid in [u for u in online_since if u not in active_uuids]:
                online_since.pop(uid, None)

        except Exception as e:
            if not wg_is_down and isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                wg_is_down = True
                await db.log_event("Error", "VPN API is unreachable")
                if ADMIN_ID: await notify_admin(app, text="⚠️ VPN-сервер недоступен!")

        await asyncio.sleep(10)

# ------------------------ SELF-HEALING ------------------------
async def self_healing_loop(app):
    fail_count = 0
    while True:
        try:
            async with api_session() as session:
                async with session.get(f"{WG_API_URL}/health", timeout=5) as resp:
                    if resp.status == 200: fail_count = 0
                    else: fail_count += 1
        except Exception: fail_count += 1

        if fail_count >= 3:
            fail_count = 0
            await db.log_event("Self-Healing", "Interface hang detected. Triggering hard restart of wg0 container.")
            if ADMIN_ID:
                try: await notify_admin(app, text="⚙️ **Самовосстановление:** туннель завис, перезапускаю.")
                except Exception: pass
            
            os.makedirs("/volumes/flags", exist_ok=True)
            with open("/volumes/flags/do_restart_wg", "w") as f: f.write("true")

        await asyncio.sleep(180)

# ------------------------ DE SELF-HEALING ------------------------
async def de_self_healing_loop(app):
    """Ватчдог немецкой ноды: если туннель DE недоступен несколько проверок подряд, просим
    DE-агент пересоздать wg0 (endpoint /wg/reload — он же заново ставит MSS-clamp). Аналог
    self_healing_loop, но для DE и через агентский API (у RU — через флаг на своём хосте).
    Если сам агент не отвечает (например, сетевой обрыв) — авто-починка невозможна, зовём
    админа. Контейнер агента и так поднимается сам (restart=always) при краше.

    DIRECT-FALLBACK (порт vpn-watchdog из OpenWRT-шлюза): пока DE недоступен, мир/РКН-трафик
    (fwmark 200 → table 200 → dev wg0) попадал бы в чёрную дыру. Поэтому уводим его НАПРЯМУЮ
    через RU (юзер не теряет интернет: обычные сайты работают; РКН-заблокированные — нет,
    пока DE не вернётся), а когда DE поднимается — авто-возвращаем маршрут через Германию."""
    de_down = False
    fail_count = 0
    route_fallback = False
    wg_base = WG_API_URL.rsplit("/api", 1)[0]   # routing-эндпоинты вне /api

    async def _de_route(action):   # action: 'de-fallback' | 'de-restore'
        try:
            async with api_session() as s:
                async with s.post(f"{wg_base}/routing/{action}", timeout=8) as r:
                    return r.status == 200
        except Exception:
            return False

    while True:
        await asyncio.sleep(180)
        ok = False
        try:
            async with api_session() as session:
                async with session.get(f"{DE_AGENT_URL}/wg/status", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        ok = (data.get("status") == "online")
        except Exception:
            ok = False

        if ok:
            if route_fallback:
                restored = await _de_route("de-restore")
                route_fallback = not restored
                if restored and ADMIN_ID:
                    try: await notify_admin(app, text="🔼 DE вернулся — трафик мир/РКН снова идёт через Германию.")
                    except Exception: pass
            if de_down and ADMIN_ID:
                try: await notify_admin(app, text="✅ Туннель DE снова в норме.")
                except Exception: pass
            de_down = False
            fail_count = 0
            continue

        fail_count += 1
        if fail_count >= 3:
            fail_count = 0
            de_down = True
            await db.log_event("Self-Healing", "DE tunnel unhealthy — triggering wg reload on DE agent.")
            reloaded = False
            try:
                async with api_session() as session:
                    async with session.post(f"{DE_AGENT_URL}/wg/reload", timeout=15) as resp:
                        reloaded = (resp.status == 200)
            except Exception:
                reloaded = False
            # DIRECT-FALLBACK: пока DE не поднялся — мир/РКН-трафик напрямую через RU.
            if not route_fallback:
                route_fallback = await _de_route("de-fallback")
                if route_fallback:
                    await db.log_event("Self-Healing", "DE down — traffic switched to DIRECT via RU (fallback).")
            if ADMIN_ID:
                msg = ("⚙️ **Самовосстановление · Германия:** туннель лежал, отправил команду пересобрать его."
                       if reloaded else
                       "⚠️ **Самовосстановление · Германия:** туннель недоступен, и агент не отвечает — нужен ручной взгляд.")
                if route_fallback:
                    msg += ("\n🔻 Мир/РКН-трафик временно идёт **напрямую через RU** — обычные сайты работают, "
                            "РКН-заблокированные недоступны, пока DE не вернётся (вернётся автоматически).")
                try: await notify_admin(app, text=msg, parse_mode="Markdown")
                except Exception: pass

# ------------------------ EXPIRATION LOGIC ------------------------
async def _ask_owner(app, uuid_val, reason, last_handshake=None, was_expires_at=None):
    """Ставит ключ на паузу и задаёт владельцу вопрос, что с ним делать.

    Пауза — безопасное состояние: доступа нет, но адрес и сам ключ на месте, поэтому
    любое решение ещё обратимо. Вопрос кладётся в базу, а сообщение — лишь способ
    его показать: даже если чат почистится или бот перезапустится, вопрос останется
    в разделе «Ждут решения», а кнопки в старом сообщении продолжат работать.
    """
    from handlers_keylife import decision_text, decision_keyboard

    try:
        async with api_session() as session:
            await session.post(f"{WG_API_URL}/peers/{uuid_val}/pause")
    except Exception:
        pass
    await db.execute("UPDATE users SET is_active=FALSE WHERE uuid=$1", uuid_val)
    await db.add_pending_decision(uuid_val, reason, last_handshake, was_expires_at)

    if not ADMIN_ID:
        return
    try:
        # Намеренно не через notify_admin: тот регистрирует сообщение на удаление
        # в полночь, а вопрос с кнопками не должен исчезать сам.
        await app.bot.send_message(ADMIN_ID, await decision_text(uuid_val),
                                   reply_markup=decision_keyboard(uuid_val),
                                   parse_mode="Markdown")
    except Exception as e:
        print(f"KeyLife: не удалось отправить вопрос: {e}")


async def expiration_loop(app):
    while True:
        try:
            users = await db.get_all_users()
            now = datetime.utcnow()
            for u in users:
                if u['is_active'] and u['expires_at'] and u['expires_at'] < now:
                    uuid_val, safe_name = u['uuid'], escape_md(u['name'])

                    # Владелец мог заранее сказать «этот продлевать само» — тогда
                    # ключ не отключается вовсе и вопрос не задаётся.
                    policy = await db.get_key_policy(uuid_val)
                    if policy.get("mode") == "auto" and policy.get("extend_days"):
                        days = int(policy["extend_days"])
                        await db.execute(
                            "UPDATE users SET expires_at=$2 WHERE uuid=$1",
                            uuid_val, now + timedelta(days=days))
                        await db.log_event(
                            "KeyLife", f"Ключ {u['name']} продлён автоматически на {days} дн.")
                        if ADMIN_ID:
                            await notify_admin(
                                app,
                                text=f"♻️ Ключ **{safe_name}** продлён автоматически "
                                     f"на {days} дн. — так было решено в прошлый раз.",
                                parse_mode="Markdown")
                        continue

                    await _ask_owner(app, uuid_val, "expired",
                                     last_handshake=u.get('last_active_at'),
                                     was_expires_at=u.get('expires_at'))
                    await db.log_event("Expiration",
                                       f"Key {u['name']} expired and was paused.")

                    kb_client = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Личный кабинет", callback_data="client_menu")]])
                    for tid in u.get('tg_ids', []):
                        try: await app.bot.send_message(chat_id=tid, text=f"⏳ Ваш VPN-ключ **{safe_name}** просрочен и был отключен.", parse_mode="Markdown", reply_markup=kb_client)
                        except Exception: pass
        except Exception as e: print(f"Expiration loop error: {e}")
        await asyncio.sleep(3600)

# ------------------------ INACTIVITY LOGIC ------------------------
async def inactivity_loop(app):
    """Спящие ключи. Автопродление сюда намеренно не применяется: оно про срок,
    а спячка — про то, что ключом не пользуются. Продлевать само то, чем никто не
    пользуется, значит вечно держать занятым адрес и живой ключ."""
    while True:
        try:
            from handlers_keylife import dormant_days
            threshold = await dormant_days()
            users = await db.get_all_users()
            now = datetime.utcnow()
            for u in users:
                if u.get('is_active', False):
                    # Свежий ключ без единого подключения считается от даты выдачи —
                    # иначе выданный и ещё не поставленный ключ «уснул» бы сразу.
                    last_active = u.get('last_active_at') or u.get('created_at')
                    if last_active and (now - last_active).days >= threshold:
                        await _ask_owner(app, u['uuid'], "dormant",
                                         last_handshake=u.get('last_active_at'))
                        await db.log_event(
                            "Inactivity",
                            f"Key {u['name']} paused after {threshold} days of inactivity.")
        except Exception as e: print(f"Inactivity loop error: {e}")
        await asyncio.sleep(86400) 

# ------------------------ WEEKLY REPORTS ------------------------
async def weekly_report_loop(app):
    while True:
        now_msk = get_moscow_now()
        if now_msk.weekday() == 6 and now_msk.hour == 20:
            try:
                users = await db.get_all_users()
                stats_24 = await db.get_stats_24h()
                live_data = {}
                try:
                    async with api_session() as session:
                        async with session.get(f"{WG_API_URL}/peers", timeout=5) as resp:
                            if resp.status == 200:
                                peers = await resp.json()
                                for p in peers: live_data[p.get('uuid')] = p.get('rx', 0) + p.get('tx', 0)
                except Exception: pass

                for u in users:
                    tg_ids = u.get('tg_ids',[])
                    if not tg_ids: continue
                    uuid_val = u['uuid']
                    user_stats =[s for s in stats_24 if s['user_uuid'] == uuid_val]
                    total_bytes = 0
                    prev_val = 0
                    
                    for s in user_stats:
                        val = s['bytes_in'] + s['bytes_out']
                        delta = val - prev_val
                        if delta < 0: delta = val
                        if prev_val == 0: delta = 0
                        total_bytes += delta
                        prev_val = val
                        
                    if uuid_val in live_data:
                        live_val = live_data[uuid_val]
                        if user_stats:
                            delta = live_val - prev_val
                            if delta < 0: delta = live_val
                            total_bytes += delta
                        else: total_bytes += live_val
                            
                    mb_used = round(total_bytes / (1024 * 1024), 2)
                    safe_name = escape_md(u['name'])
                    msg = f"📊 **Еженедельный отчет VPN**\n\nКлюч: **{safe_name}**\nИспользовано трафика: `{mb_used} MB`\nВаш VPN работает стабильно! 🚀"
                    kb_client = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Личный кабинет", callback_data="client_menu")]])
                    for tid in tg_ids:
                        try: await app.bot.send_message(chat_id=tid, text=msg, parse_mode="Markdown", reply_markup=kb_client)
                        except Exception: pass
                        
                await db.log_event("System", "Weekly reports dispatched.")
            except Exception as e: print(f"Weekly report error: {e}")
            await asyncio.sleep(86400)
        else: await asyncio.sleep(3600)

async def cleanup_peers():
    while True:
        await asyncio.sleep(3600)
        notified_cache.clear()

async def stats_collector_loop():
    while True:
        try:
            async with api_session() as session:
                async with session.get(f"{WG_API_URL}/peers", timeout=10) as resp:
                    if resp.status == 200:
                        peers_data = await resp.json()
                        now = int(time.time())
                        for peer in peers_data:
                            uuid_val, rx, tx, hs = peer.get("uuid"), peer.get("rx", 0), peer.get("tx", 0), peer.get("latest_handshake", 0)
                            if uuid_val and len(uuid_val) < 40:
                                await db.save_stats(uuid_val, rx, tx)
                                if hs > 0 and (now - hs) < 180: await db.execute("UPDATE users SET last_active_at=NOW() WHERE uuid=$1", uuid_val)
        except Exception: pass
        await asyncio.sleep(300)

async def log_cleanup_loop(app):
    while True:
        try:
            await db.cleanup_old_logs(days=7)
            # Инциденты: разобранные месяц, неразобранные квартал. Раньше
            # они не убирались вовсе и копились с первого дня.
            gone = await db.cleanup_filter_hits()
            if gone:
                print("Инциденты: убрано старых — %d" % gone)
            os.makedirs("/volumes/flags", exist_ok=True)
            with open("/volumes/flags/do_cleanup", "w") as f: f.write("true")
        except Exception as e: print(f"🧹 Cleanup error: {e}")
        await asyncio.sleep(86400)

# ------------------------ СНЯТИЕ СТАРЫХ КЛЮЧЕЙ ПОСЛЕ ПЕРЕВЫПУСКА ------------------------
# Старый ключ снимается не по таймеру, а когда новый реально заработал и продержался
# выдержку. Очередь лежит в базе, поэтому рестарт бота или деплой её не теряют —
# раньше задача жила в памяти процесса и при перезапуске старый пир оставался навсегда.
RETIRE_CONFIRM_MINUTES = 10      # сколько новый ключ должен прожить до снятия старого
RETIRE_STALE_DAYS = 7            # столько ждём, потом зовём админа и НЕ трогаем ключ


async def retire_watch_loop(app):
    while True:
        try:
            pending = await db.get_pending_retire()
            if pending:
                handshakes = {}
                async with api_session() as session:
                    async with session.get(f"{WG_API_URL}/peers", timeout=10) as r:
                        if r.status == 200:
                            for p in await r.json():
                                handshakes[p.get("uuid")] = int(p.get("latest_handshake") or 0)

                now = datetime.utcnow()
                for row in pending:
                    old_uuid, new_uuid = row["old_uuid"], row["new_uuid"]
                    name = row["name"] or old_uuid[:8]

                    if handshakes.get(new_uuid, 0) > 0 and not row["first_handshake_at"]:
                        await db.mark_retire_handshake(old_uuid)
                        await db.log_event(
                            "Client Regen",
                            f"Новый ключ {name} вышел на связь, старый снимется через "
                            f"{RETIRE_CONFIRM_MINUTES} мин.")
                        continue

                    first = row["first_handshake_at"]
                    if first and (now - first).total_seconds() >= RETIRE_CONFIRM_MINUTES * 60:
                        from wireguard_manager import delete_peer
                        try:
                            await delete_peer(old_uuid, name, purge_files=False)
                        except Exception as e:
                            print(f"Снятие старого ключа {name}: {e}")
                        await db.execute("DELETE FROM users WHERE uuid=$1", old_uuid)
                        await db.drop_pending_retire(old_uuid)
                        await db.log_event(
                            "Client Regen",
                            f"Старый ключ {name} снят: новый работает "
                            f"{RETIRE_CONFIRM_MINUTES} мин.")
                        continue

                    # Новый ключ так и не заработал — зовём админа, но ничего не трогаем.
                    age_days = (now - row["created_at"]).days if row["created_at"] else 0
                    if not first and age_days >= RETIRE_STALE_DAYS and not row["notified"]:
                        await db.mark_retire_notified(old_uuid)
                        if ADMIN_ID:
                            await notify_admin(app, text=(
                                f"🔑 **Перевыпуск завис**\n\n"
                                f"Ключ: **{escape_md(name)}**\n"
                                f"Новый конфиг выдан {age_days} дн. назад, но им так и не "
                                f"подключились. Старый ключ продолжает работать — "
                                f"ничего не отключено."), parse_mode="Markdown")
        except Exception as e:
            print(f"Наблюдение за перевыпуском: {e}")

        await asyncio.sleep(60)

# ------------------------ КОНТРОЛЬ НАГРУЗКИ ------------------------
# Узел упирается в пакеты, а не в мегабиты: на клиентский пакет уходит около 130 мкс
# процессорного времени, отсюда потолок примерно 7-8 тысяч пакетов в секунду. WireGuard
# пакеты по пирам не считает, поэтому узел ведёт собственный учёт правилами файрвола,
# а этот сборщик снимает два замера подряд и получает нагрузку в пакетах в секунду.
ACCT_INTERVAL = 15           # секунд между замерами
DEFAULT_PPS_LIMIT = 5000     # пока порог не задан из админки
EVENT_CLOSE_MISSES = 2       # столько замеров ниже порога закрывают эпизод


async def _effective_limit(uuid, common_limit, personal):
    """Порог для конкретного пира: своё правило важнее общего, у освобождённых порога нет."""
    rule = personal.get(uuid)
    if not rule:
        return common_limit
    if rule["mode"] == "unlimited":
        return None
    if rule["mode"] == "custom" and rule["limit_pps"]:
        return int(rule["limit_pps"])
    return common_limit


async def load_collector_loop(app):
    # Разовая свёртка уже накопленной статистики в часовые срезы: неделя истории
    # становится доступна сразу, а не копится с нуля после включения.
    try:
        rows = await db.backfill_hourly_from_stats()
        if rows:
            print(f"📊 Часовые срезы: свёрнуто из накопленной статистики, строк {rows}")
    except Exception as e:
        print(f"Свёртка истории: {e}")

    prev_snapshot, prev_ts = None, None
    hot = {}          # uuid → сведения о текущем превышении
    tick = 0

    while True:
        try:
            async with api_session() as session:
                async with session.get(f"{WG_API_URL}/accounting", timeout=10) as r:
                    acct = await r.json() if r.status == 200 else None
                async with session.get(f"{WG_API_URL}/peers", timeout=10) as r:
                    peers = await r.json() if r.status == 200 else []

            if acct and acct.get("peers"):
                snapshot, ts = acct["peers"], acct.get("ts", int(time.time()))
                ip_to_uuid = {
                    str(p.get("allowed_ips", "")).split("/")[0]: p.get("uuid")
                    for p in peers if p.get("allowed_ips")
                }
                if prev_snapshot and prev_ts and ts > prev_ts:
                    dt = ts - prev_ts
                    # Клиент-сервер — не человек: он несёт трафик всех остальных
                    # и под человеческие лимиты попадать не должен.
                    agent_uuids = {u["uuid"] for u in await db.get_all_users()
                                   if is_agent(u["name"])}
                    common = int(await db.get_setting("pps_limit") or DEFAULT_PPS_LIMIT)
                    mode = (await db.get_setting("pps_mode") or "observe")
                    personal = await db.get_peer_limits()
                    hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

                    merged = {}
                    for ip, cur in snapshot.items():
                        old = prev_snapshot.get(ip)
                        uuid_val = ip_to_uuid.get(ip)
                        if not old or not uuid_val:
                            continue

                        # Счётчики могли обнулиться — контейнер перезапускали.
                        rec = merged.setdefault(uuid_val, [0, 0, 0, 0])
                        # Узел считает от лица пира: `tx` — он отдал, `rx` — он
                        # принял. В базе договорённость обратная (см. insights):
                        # bytes_in — это ОТДАЧА человека, bytes_out — его ПРИЁМ.
                        # Раньше здесь приём уезжал в колонку отдачи, и доля
                        # отдачи выходила перевёрнутой: любой качающий получал
                        # «отдаёт больше, чем принимает».
                        up_pkt = max(0, cur["tx_packets"] - old["tx_packets"])
                        down_pkt = max(0, cur["rx_packets"] - old["rx_packets"])
                        rec[0] += up_pkt
                        rec[1] += down_pkt
                        rec[2] += max(0, cur["tx_bytes"] - old["tx_bytes"])
                        rec[3] += max(0, cur["rx_bytes"] - old["rx_bytes"])

                    # Имена — от лица человека и в том же смысле, что в базе:
                    # in — его отдача, out — его приём.
                    for uuid_val, (d_pkt_in, d_pkt_out, d_byt_in, d_byt_out) in merged.items():
                        pps = (d_pkt_in + d_pkt_out) / dt
                        total_pkt = d_pkt_in + d_pkt_out
                        avg_size = (d_byt_in + d_byt_out) / total_pkt if total_pkt else 0

                        await db.add_hourly(uuid_val, hour, d_byt_in, d_byt_out,
                                            d_pkt_in, d_pkt_out, pps)

                        if uuid_val in agent_uuids:
                            continue
                        limit = await _effective_limit(uuid_val, common, personal)
                        if limit and pps > limit:
                            rec = hot.setdefault(uuid_val, {
                                "peak": 0, "size": 0, "misses": 0,
                                "started": datetime.utcnow(), "up": 0, "down": 0})
                            rec["peak"] = max(rec["peak"], pps)
                            rec["size"] = avg_size or rec["size"]
                            # in — отдача человека, out — его приём.
                            rec["up"] += d_byt_in
                            rec["down"] += d_byt_out
                            rec["misses"] = 0
                        elif uuid_val in hot:
                            hot[uuid_val]["misses"] += 1
                            if hot[uuid_val]["misses"] >= EVENT_CLOSE_MISSES:
                                rec = hot.pop(uuid_val)
                                total = rec["up"] + rec["down"]
                                await db.record_pps_event(
                                    uuid_val, rec["peak"], rec["size"],
                                    throttled=(mode == "enforce"),
                                    started_at=rec.get("started"),
                                    upload_share=(rec["up"] / total) if total else None)

                prev_snapshot, prev_ts = snapshot, ts

            tick += 1
            if tick % 20 == 0:                      # раз в пять минут
                await db.drop_expired_peer_limits()
        except Exception as e:
            print(f"Сборщик нагрузки: {e}")

        await asyncio.sleep(ACCT_INTERVAL)

# ------------------------ AUTO-REBOOT ------------------------
async def auto_reboot_loop(app):
    while True:
        now_msk = get_moscow_now()
        if now_msk.weekday() == 6 and now_msk.hour == 4:
            try:
                last_reboot = await db.get_setting("last_auto_reboot")
                today_str = now_msk.strftime("%Y-%m-%d")
                if last_reboot != today_str:
                    await db.set_setting("last_auto_reboot", today_str)
                    text = "🔄 **Плановое обслуживание!**\n\nСервер автоматически уходит на перезагрузку."
                    await broadcast_message(app, text, db)
                    os.makedirs("/volumes/flags", exist_ok=True)
                    with open("/volumes/flags/was_rebooting", "w") as f: f.write("true")
                    with open("/volumes/flags/do_reboot", "w") as f: f.write("reboot_requested")
            except Exception as e: print(f"Auto-reboot error: {e}")

        # DE: отдельный плановый ребут в вс 06:00 MSK — со стаггером от ребута RU (04:00) и
        # от ночного apt DE (03:00 Berlin ≈ 04:00–05:00 MSK), чтобы применялись накопившиеся
        # kernel/security-обновления (у DE нет своего авто-ребута, только у RU). DE ребутится
        # через свой агент: POST /host/reboot → флаг do_reboot на DE → host_updater ребутит.
        if now_msk.weekday() == 6 and now_msk.hour == 6:
            try:
                today_str = now_msk.strftime("%Y-%m-%d")
                if await db.get_setting("last_auto_reboot_de") != today_str:
                    await db.set_setting("last_auto_reboot_de", today_str)
                    try:
                        async with api_session() as session:
                            await session.post(f"{DE_AGENT_URL}/host/reboot", timeout=5)
                        await db.log_event("System", "Weekly DE auto-reboot triggered.")
                        if ADMIN_ID:
                            await notify_admin(app, text="🔄 **Плановый ребут DE** (Германия) — применяю накопившиеся обновления.", parse_mode="Markdown")
                    except Exception:
                        await db.log_event("Error", "Weekly DE auto-reboot: DE agent unreachable.")
                        if ADMIN_ID:
                            try: await notify_admin(app, text="⚠️ Плановый ребут DE не удался: агент недоступен.")
                            except Exception: pass
            except Exception as e: print(f"DE auto-reboot error: {e}")
        await asyncio.sleep(60)

# ------------------------ НЕДЕЛЬНЫЙ ОТЧЁТ ОБ ОБСЛУЖИВАНИИ ------------------------
def _read_flag(name):
    """Отчёт, положенный скриптом обслуживания. Нет файла — значит, не было."""
    try:
        with open(f"/volumes/flags/{name}") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _delta(now, was, unit="%", better="меньше"):
    """Цифра рядом с прошлой неделей. Без прошлой — просто цифра."""
    if now is None:
        return "—"
    if was is None or was == now:
        return f"{now}{unit}"
    sign = "+" if now > was else "−"
    return f"{now}{unit} (было {was}{unit}, {sign}{abs(now - was)}{unit})"


def _node_block(title, health, gc):
    lines = [f"**{title}**"]
    if not health and not gc:
        lines.append("_обслуживание ещё не отрабатывало_")
        return lines, {}

    snap = {}
    if health:
        snap["disk"] = health.get("disk_used_pct")
        snap["upgradable"] = health.get("packages_upgradable")
        snap["reboot"] = bool(health.get("reboot_required"))
    if gc:
        snap["freed"] = gc.get("freed_mb")
    return lines, snap


async def weekly_health_loop(app):
    """Раз в неделю: что сделало обслуживание и что изменилось с прошлого раза."""
    while True:
        now_msk = get_moscow_now()
        if not (now_msk.weekday() == 6 and now_msk.hour == 7):
            await asyncio.sleep(600)
            continue

        today = now_msk.strftime("%Y-%m-%d")
        try:
            if await db.get_setting("last_weekly_health") == today:
                await asyncio.sleep(3600)
                continue
            await db.set_setting("last_weekly_health", today)

            prev = {}
            try:
                prev = json.loads(await db.get_setting("weekly_health_prev") or "{}")
            except ValueError:
                prev = {}

            health = _read_flag("host_health.json")
            gc = _read_flag("gc.json")
            contract = _read_flag("contract.json")

            # Германия своих отчётов показать не может — у неё нет бота. Она их
            # просто отдаёт, а собирает и показывает мастер.
            de_health = de_gc = None
            try:
                async with api_session() as session:
                    async with session.get(f"{DE_AGENT_URL}/host/maintenance",
                                           timeout=10) as resp:
                        if resp.status == 200:
                            d = await resp.json()
                            de_health, de_gc = d.get("health"), d.get("gc")
            except Exception:
                pass

            lines = [f"🧹 **Недельное обслуживание** · {now_msk.strftime('%d.%m')}", ""]
            snap = {}

            for title, h, g, key in (("Мастер · Россия", health, gc, "ru"),
                                     ("Выход · Германия", de_health, de_gc, "de")):
                block, s = _node_block(title, h, g)
                lines += block
                if s:
                    was = prev.get(key, {})
                    lines.append("Диск " + _delta(s.get("disk"), was.get("disk")))
                    freed = s.get("freed")
                    if freed and freed > 0:
                        lines.append(f"Уборка освободила {freed} МБ")
                    elif freed is not None:
                        lines.append("Уборка: заметного мусора не было")
                    upg = s.get("upgradable")
                    if upg:
                        lines.append(f"Пакетов ждёт обновления: {upg}")
                    if s.get("reboot"):
                        lines.append("⚠️ Нужна перезагрузка — плановая не применила обновления")
                    snap[key] = s
                lines.append("")


            # Сверка базы с узлом: её делает только мастер, за обе стороны.
            if contract and contract.get("answered"):
                n_err = contract.get("error", 0)
                n_warn = contract.get("warning", 0)
                n_ok = contract.get("ok", 0)
                was_err = prev.get("contract_err")
                if n_err:
                    lines.append(f"❗️ **Расхождений базы и узла: {n_err}**")
                    for row in contract.get("lines") or []:
                        if row.get("status") == "error":
                            lines.append(f"• {row.get('name')} — {row.get('msg')}")
                elif was_err:
                    lines.append(f"✅ Сверка: всё сошлось ({n_ok} проверок). "
                                 f"На прошлой неделе было расхождений: {was_err}")
                else:
                    lines.append(f"✅ Сверка: всё сошлось ({n_ok} проверок)")
                if n_warn:
                    # Не только число: «предупреждений 3» не говорит ничего, а
                    # разбираться потом приходится по журналу вручную.
                    lines.append(f"_предупреждений: {n_warn}_")
                    for row in contract.get("lines") or []:
                        if row.get("status") == "warning":
                            lines.append(f"     • {row.get('name')} — "
                                         f"{row.get('msg')}")
                snap["contract_err"] = n_err
            elif contract is not None:
                lines.append("⚠️ Сверка базы с узлом не дала ответа")

            await db.set_setting("weekly_health_prev", json.dumps(snap))
            await notify_admin(app, text=chr(10).join(lines).strip(),
                               parse_mode=ParseMode.MARKDOWN)
            await db.log_event("System", "Weekly maintenance report sent.")
        except Exception as e:
            print(f"Недельный отчёт обслуживания: {e}")
        await asyncio.sleep(3600)


# ------------------------ SCHEDULED UPDATE ------------------------
async def scheduled_update_loop(app):
    while True:
        try:
            target_str = await db.get_setting("scheduled_update")
            if target_str:
                target_dt = datetime.strptime(target_str, "%Y-%m-%d %H:%M:%S")
                now_msk = get_moscow_now()
                if now_msk >= target_dt:
                    await db.execute("DELETE FROM settings WHERE key='scheduled_update'")
                    text = "🚀 **Обновление системы началось!**\n\nСервис уйдет в оффлайн на 1-2 минуты."
                    await broadcast_message(app, text, db)
                    os.makedirs("/volumes/flags", exist_ok=True)
                    with open("/volumes/flags/was_updating", "w") as f: f.write("true")
                    with open("/volumes/flags/do_update", "w") as f: f.write("update_requested")
        except Exception as e: pass
        await asyncio.sleep(60)

async def auto_update_check_loop(app):
    """АВТООБНОВЛЕНИЯ «когда выходят обновы»: если тумблер включён (auto_update_enabled=true),
    раз в 6 часов сверяет локальную версию с репозиторием и при новой версии САМ запускает
    БЕЗОПАСНОЕ обновление ОБЕИХ нод — тем же путём, что и «Обновить всё»: команда DE по туннелю
    + флаг do_update для RU. Даунтайма-риска нет: deploy.sh делает health-check и авто-откат на
    прошлый коммит при сбое. По умолчанию ВЫКЛЮЧЕНО — тогда обновления только вручную/по расписанию."""
    await asyncio.sleep(300)   # дать боту/БД подняться
    while True:
        try:
            if (await db.get_setting("auto_update_enabled")) == "true":
                local_hash, local_ver, remote_hash, remote_ver = await asyncio.to_thread(get_update_info)
                new_available = (remote_hash not in ("unknown", "")
                                 and local_hash not in ("unknown", "")
                                 and remote_hash != local_hash)
                if new_available:
                    await db.log_event("Update", f"Auto-update: new version {remote_ver} ({remote_hash}) — applying (RU+DE).")
                    # DE — командой по туннелю (не критично, если агент не ответил)
                    try:
                        async with api_session() as session:
                            await session.post(f"{DE_AGENT_URL}/host/update", timeout=5)
                    except Exception:
                        pass
                    # оповещаем пользователей и запускаем RU (deploy.sh сам сделает бэкап+откат)
                    try:
                        await broadcast_message(app, "⚠️ **Технические работы**\n\nАвтообновление серверов. Связь может прерваться на 1–2 минуты.", db)
                    except Exception:
                        pass
                    if ADMIN_ID:
                        try:
                            await notify_admin(app, text=(f"🔄 **Автообновление**\n\nВышла версия `{remote_ver}` — применяю на обеих нодах.\n"
                                                          "Идёт с health-check и авто-откатом при сбое."), parse_mode="Markdown")
                        except Exception:
                            pass
                    os.makedirs("/volumes/flags", exist_ok=True)
                    with open("/volumes/flags/was_updating", "w") as f: f.write("true")
                    with open("/volumes/flags/do_update", "w") as f: f.write("update_requested")
        except Exception as e:
            print(f"auto_update_check_loop error: {e}")
        await asyncio.sleep(6 * 3600)   # проверка раз в 6 часов

# ------------------------ ROUTING UPGRADE (split-tunnel напоминания) ------------------------
async def routing_upgrade_loop(app):
    """Ежедневно в 8:00 МСК напоминает владельцам устаревших ключей перевыпустить конфиг
    (чтобы заработали Госуслуги/MAX/банки) — по КАЖДОМУ ключу отдельно, пока не обновят.
    Заодно раз в день проверяет дрейф bypass-IP и алертит админа."""
    while True:
        now_msk = get_moscow_now()
        if now_msk.hour == 8:
            today = now_msk.strftime("%Y-%m-%d")
            try:
                if await db.get_setting("last_routing_notice") != today:
                    await db.set_setting("last_routing_notice", today)
                    await _send_upgrade_notices(app)
            except Exception as e:
                print(f"Routing upgrade loop error: {e}")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(600)

async def bypass_reresolve_loop(app):
    """РАЗ В ЧАС перерезолвит домены split-tunnel исключений и авто-абсорбирует дрейф IP в БД
    (bump=False → без нагона перевыпусков). Держит адреса исключений свежими — по мотивам
    OpenWRT-шлюза (там домен→ipset по таймеру). ВАЖНО: у уже выданных клиентов bypass запечён
    в AllowedIPs их .conf — новые IP они получат лишь при ПЕРЕВЫПУСКЕ конфига; здесь свежими
    остаются БД и все новые/перевыпущенные ключи + авто-добавление «уехавших» /24."""
    await asyncio.sleep(120)  # дать боту/БД подняться
    while True:
        try:
            await _auto_absorb_drift(app)
        except Exception as e:
            print(f"bypass_reresolve_loop error: {e}")
        await asyncio.sleep(3600)

async def _send_upgrade_notices(app):
    current_version = await db.get_routing_version()
    outdated = await db.get_outdated_keys(current_version)
    rows = await db.get_bypass_exclusions()
    domains = ", ".join(f"`{escape_md(r['domain'])}`" for r in rows) if rows else "—"
    sent = 0
    for k in outdated:
        name = escape_md(k['name'])
        text = (
            f"🔔 **Обновите конфиг ключа «{name}»**\n\n"
            "Перевыпустите конфиг, чтобы получить прямой доступ (мимо VPN) к сервисам, "
            "которые блокируют дата-центры:\n"
            f"{domains}\n\n"
            "Старый ключ продолжит работать как прежде, но без обхода этих сервисов.\n\n"
            + UPGRADE_INSTRUCTION + "\n\n" + GOSUSLUGI_APP_WARNING
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Перевыпустить этот ключ", callback_data=f"client_regen_{k['uuid']}")],
            [InlineKeyboardButton("🌐 Список исключений", callback_data="client_bypass_info")],
            [InlineKeyboardButton("🔕 Не напоминать", callback_data="client_notify_off")],
            [InlineKeyboardButton("🏠 Личный кабинет", callback_data="client_menu")],
        ])
        for tid in k.get('tg_ids', []):
            try:
                # Уважаем персональный opt-out: пользователь мог сам отключить напоминания
                if not await db.get_routing_notify(tid):
                    continue
                await app.bot.send_message(chat_id=tid, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
                sent += 1
            except Exception:
                pass
    if sent:
        await db.log_event("Routing", f"Daily upgrade notice sent ({sent} msg).")
    return sent

async def _auto_absorb_drift(app=None):
    """Сам сканирует адреса исключений и при дрейфе IP (адрес сервиса вышел за пределы
    заявленных подсетей) АВТОМАТИЧЕСКИ добавляет новую /24 в нужный домен — без ручной
    работы админа. bump=False: не поднимаем routing_version, чтобы не вызывать лавину
    перевыпусков (новые/перевыпущенные ключи и так получат актуальный список).
    Если домен рассеялся по многим IP (> MAX_CIDRS_PER_DOMAIN) — это уже не дрейф, а
    смена инфраструктуры: тогда один раз зовём админа.
    Возвращает (changed, overflow)."""
    entries = await _bypass_drift_entries()
    drifted = await asyncio.to_thread(_check_bypass_drift, entries)  # [(domain, ip), ...]
    if not drifted:
        return [], []

    # группируем новые /24 по домену
    by_domain = {}
    for domain, ip in drifted:
        try:
            net = str(ipaddress.ip_network(f"{ip}/24", strict=False))
        except ValueError:
            continue
        by_domain.setdefault(domain, set()).add(net)

    rows = {r['domain']: r for r in await db.get_bypass_exclusions()}
    changed, overflow = [], []
    for domain, new_nets in by_domain.items():
        r = rows.get(domain)
        if not r:
            continue
        cur = [c.strip() for c in (r['cidrs'] or '').split(',') if c.strip()]
        add = [n for n in sorted(new_nets) if n not in cur]
        if not add:
            continue
        if len(cur) + len(add) > MAX_CIDRS_PER_DOMAIN:
            overflow.append((domain, add))
            continue
        await db.add_bypass_exclusion(domain, cur + add, note=r['note'] or '', source=r['source'] or 'auto', bump=False)
        changed.append((domain, add))

    if changed:
        await db.log_event("Routing", "Auto-absorbed bypass drift: " + "; ".join(f"{d}+{','.join(n)}" for d, n in changed))
        if app and ADMIN_ID:
            lines = ["🔄 **Исключения авто-обновлены (дрейф IP)**\n",
                     "Сам добавил новые подсети — _действий не требуется_:"]
            lines += [f"• `{escape_md(d)}` → `{', '.join(n)}`" for d, n in changed]
            lines.append("\nНовые ключи получат их сразу; существующим — при следующем перевыпуске.")
            try:
                await notify_admin(app, text="\n".join(lines), parse_mode=ParseMode.MARKDOWN)
            except Exception:
                pass

    if overflow and app and ADMIN_ID:
        await db.log_event("Routing", "Bypass drift overflow (manual review): " + "; ".join(d for d, _ in overflow))
        lines = ["⚠️ **Сервис сменил инфраструктуру (нужен взгляд)**\n",
                 f"Эти домены рассеялись по >{MAX_CIDRS_PER_DOMAIN} подсетям — авто-добавлять не стал, "
                 "чтобы не раздуть конфиг/QR. Проверь в 🌐 Исключения:"]
        lines += [f"• `{escape_md(d)}` → `{', '.join(n)}`" for d, n in overflow]
        try:
            await notify_admin(app, text="\n".join(lines), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    return changed, overflow

# --- Ручной запуск из админки ---
async def run_bypass_check_handler(update, context):
    query = update.callback_query
    await query.answer("Сканирую и авто-обновляю адреса...")
    try:
        # ручной запуск делает то же, что и фоновый: сам абсорбирует дрейф
        changed, overflow = await _auto_absorb_drift(app=None)
        cidrs_count = len(await db.get_all_bypass_cidrs())
        outdated = await db.get_outdated_keys(await db.get_routing_version())
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка проверки: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]))
        return

    lines = [
        "🛡 **Проверка split-tunnel (исключения)**\n",
        f"🚫 Подсетей-исключений (мимо VPN): **{cidrs_count}**",
        f"♻️ Ключей на старом формате: **{len(outdated)}**\n",
    ]
    if changed:
        lines.append("🔄 **Авто-добавил подсети (дрейф IP):**")
        lines += [f"• `{d}` → `{', '.join(n)}`" for d, n in changed]
    if overflow:
        lines.append("⚠️ **Рассеялись по многим IP — нужен ручной взгляд:**")
        lines += [f"• `{d}`" for d, _ in overflow]
    if not changed and not overflow:
        lines.append("✅ Все сервисы в пределах заявленных подсетей.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Список исключений", callback_data="bypass_list")],
        [InlineKeyboardButton("📨 Разослать напоминания сейчас", callback_data="bypass_notify_now")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ])
    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def bypass_notify_now_handler(update, context):
    query = update.callback_query
    await query.answer("Рассылаю напоминания...")
    sent = await _send_upgrade_notices(context.application)
    await query.edit_message_text(
        f"✅ Напоминания разосланы по устаревшим ключам (сообщений: {sent}).",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
    )

# ------------------------ УПРАВЛЕНИЕ ИСКЛЮЧЕНИЯМИ (АДМИН) ------------------------
async def bypass_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rows = await db.get_bypass_exclusions()
    rv = await db.get_routing_version()

    lines = [
        f"🌐 **Исключения split-tunnel** (версия маршрутизации: `{rv}`)\n",
        "Эти подсети идут мимо VPN (через домашний канал клиента). При любом изменении "
        "списка версия поднимается, и пользователям уходит напоминание о перевыпуске.\n",
    ]
    kb = []
    if rows:
        for r in rows:
            note = f" — {escape_md(r['note'])}" if r['note'] else ""
            lines.append(f"• `{escape_md(r['domain'])}`{note}\n  `{r['cidrs']}`")
            kb.append([InlineKeyboardButton(f"🗑 {r['domain']}", callback_data=f"bypass_del_{r['id']}")])
    else:
        lines.append("_Список пуст._")

    kb.append([InlineKeyboardButton("➕ Добавить вручную", callback_data="bypass_add_manual")])
    kb.append([InlineKeyboardButton("📨 Напомнить о перевыпуске", callback_data="bypass_notify_now")])
    kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

async def bypass_del_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, exid: str):
    query = update.callback_query
    new_v = await db.remove_bypass_exclusion(exid)
    await db.log_event("Routing", f"Bypass exclusion removed (id={exid}); routing -> v{new_v}.")
    await query.answer(f"Удалено. Версия маршрутизации: {new_v}.")
    await bypass_list_handler(update, context)

async def bypass_add_manual_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = "awaiting_bypass_add"
    kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="bypass_list")]]
    await query.edit_message_text(
        "➕ **Добавить исключение**\n\nПришлите домен или ссылку (например, `mos.ru` "
        "или `https://lk.gosuslugi.ru`). Я разрешу адрес в IP и добавлю его подсети (/24) "
        "в обход VPN.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
    )

async def bypass_add_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, req_id: str, approve: bool = True):
    query = update.callback_query
    req = await db.get_bypass_request(req_id)
    if not req:
        await query.answer("Заявка не найдена.", show_alert=True)
        return
    if req['status'] != 'pending':
        await query.answer(f"Заявка уже обработана ({req['status']}).", show_alert=True)
        return

    if approve:
        cidrs = [c.strip() for c in (req['cidrs'] or '').split(',') if c.strip()]
        new_v = await db.add_bypass_exclusion(req['domain'], cidrs, note="по заявке клиента", source="client")
        await db.set_bypass_request_status(req_id, "approved")
        await db.log_event("Routing", f"Bypass exclusion added by request: {req['domain']} -> v{new_v}.")
        await query.edit_message_text(
            f"✅ Добавлено в исключения: `{escape_md(req['domain'])}`\n"
            f"Версия маршрутизации: `{new_v}` — клиентам уйдёт напоминание о перевыпуске.",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await context.application.bot.send_message(
                chat_id=req['tg_id'],
                text=(f"✅ Сайт `{escape_md(req['domain'])}` добавлен в исключения!\n"
                      "Перевыпустите ключ в «Мои ключи», чтобы доступ заработал."),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Мои ключи", callback_data="client_my_keys")]])
            )
        except Exception:
            pass
    else:
        await db.set_bypass_request_status(req_id, "rejected")
        await query.edit_message_text(f"❌ Заявка на `{escape_md(req['domain'])}` отклонена.", parse_mode=ParseMode.MARKDOWN)


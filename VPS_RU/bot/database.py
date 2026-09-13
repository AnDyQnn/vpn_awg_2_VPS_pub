import asyncpg
import os
import asyncio
from pathlib import Path
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

# --- Единый аккуратный стиль Excel-выгрузок ---
_HDR_FILL = PatternFill("solid", fgColor="1F4E78")   # тёмно-синяя шапка
_HDR_FONT = Font(bold=True, color="FFFFFF", size=11)
# Светофор. Бледные пастельные заливки не работали: в таблице на тридцать строк
# критичное значение не отличалось от обычного, и глазами всё равно приходилось
# читать каждую строку. Берём насыщенные цвета и белый текст поверх — так
# проблемные места видно, не вчитываясь.
_OK_FILL = PatternFill("solid", fgColor="107C41")    # зелёный: всё в порядке
_WARN_FILL = PatternFill("solid", fgColor="E8A317")  # жёлтый: стоит посмотреть
_BAD_FILL = PatternFill("solid", fgColor="C00000")   # красный: требует решения
_OFF_FILL = PatternFill("solid", fgColor="7F7F7F")   # серый: выключено, не авария
_TOT_FILL = PatternFill("solid", fgColor="FFF2CC")   # мягкий жёлтый (итоги)
_WHITE_BOLD = Font(bold=True, color="FFFFFF")


def _mark(cell, fill):
    """Заливка плюс белый жирный текст: на насыщенном фоне чёрный не читается."""
    cell.fill = fill
    cell.font = _WHITE_BOLD
    cell.alignment = Alignment(horizontal="center")
_THIN = Side(style="thin", color="D9D9D9")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

def _style_sheet(ws, header_row=1, autofilter=True):
    """Оформляет шапку: жирный белый текст на синем, по центру, рамка; замораживает
    строку заголовка и включает автофильтр — чтобы таблица была читаемой и удобной."""
    for cell in ws[header_row]:
        cell.fill = _HDR_FILL
        cell.font = _HDR_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _BORDER
    ws.row_dimensions[header_row].height = 22
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
    if autofilter and ws.max_column >= 1 and ws.max_row >= 1:
        ws.auto_filter.ref = ws.dimensions
from utils import dt_to_moscow, BASE_BYPASS, ROUTING_VERSION, is_agent

CONFIGS_DIR = Path("/volumes/configs")
WG_CONF_PATH = Path("/volumes/wireguard/wg0.conf")

class Database:
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv("DATABASE_URL", "postgres://vpn:vpnpass@postgres:5432/vpndb")

    async def connect(self):
        for i in range(5):
            try:
                self.pool = await asyncpg.create_pool(dsn=self.database_url)
                await self.init_tables()
                await self._check_migrations()
                print("Успешное подключение к БД")
                break
            except Exception as e:
                print(f"Попытка подключения к БД {i+1} неудачна: {e}")
                await asyncio.sleep(2)

    async def init_tables(self):
        pass

    async def _check_migrations(self):
        try:
            await self.execute("""
                CREATE TABLE IF NOT EXISTS user_tg_links (
                    uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    tg_id BIGINT,
                    UNIQUE(uuid, tg_id)
                );
            """)
            await self.execute("""
                CREATE TABLE IF NOT EXISTS events_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    event_type TEXT,
                    message TEXT
                );
            """)
            await self.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    message TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            await self.execute("""
                CREATE TABLE IF NOT EXISTS user_ips (
                    uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    ip TEXT,
                    status TEXT DEFAULT 'pending',
                    first_seen TIMESTAMP DEFAULT NOW(),
                    last_seen TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (uuid, ip)
                );
            """)

            res_exp = await self.fetch_all("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='expires_at';")
            if not res_exp:
                await self.execute("ALTER TABLE users ADD COLUMN expires_at TIMESTAMP;")
                
            res_act = await self.fetch_all("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='is_active';")
            if not res_act:
                await self.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")

            res_last = await self.fetch_all("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='last_active_at';")
            if not res_last:
                await self.execute("ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP;")

            # routing_version: формат маршрутизации конфига. 0 = старый (полный туннель,
            # без обхода дата-центро-враждебных РФ-сервисов). Новые/перевыпущенные ключи
            # получают актуальную версию. Старые ключи остаются на 0 и работают как раньше.
            res_rv = await self.fetch_all("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='routing_version';")
            if not res_rv:
                await self.execute("ALTER TABLE users ADD COLUMN routing_version INTEGER DEFAULT 0;")

            # --- SPLIT-TUNNEL: динамический список исключений (обход мимо VPN) ---
            # Источник правды для split-tunnel. build_split_allowed_ips в api.py
            # получает эти подсети при создании конфига; при любом изменении списка
            # routing_version поднимается → все старые ключи становятся устаревшими.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS bypass_exclusions (
                    id SERIAL PRIMARY KEY,
                    domain TEXT UNIQUE,
                    cidrs TEXT,
                    note TEXT,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            # Заявки клиентов на добавление неработающего ресурса в исключения
            await self.execute("""
                CREATE TABLE IF NOT EXISTS bypass_requests (
                    id SERIAL PRIMARY KEY,
                    domain TEXT,
                    cidrs TEXT,
                    tg_id BIGINT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            # Персональные настройки уведомлений (на уровне Telegram-аккаунта).
            # routing_notify=FALSE → пользователь сам отключил напоминания о смене
            # политик маршрутизации/исключений (перевыпуск конфига).
            await self.execute("""
                CREATE TABLE IF NOT EXISTS notify_prefs (
                    tg_id BIGINT PRIMARY KEY,
                    routing_notify BOOLEAN DEFAULT TRUE,
                    -- какую версию человек уже видел: «Что нового» показывает только
                    -- накопленное с неё, а не весь список изменений заново
                    seen_version TEXT
                );
            """)
            # --- ОЧЕРЕДЬ СНЯТИЯ СТАРЫХ КЛЮЧЕЙ ---
            # При перевыпуске человек какое-то время живёт на двух ключах: новый выдан,
            # старый ещё работает. Снимаем старый только когда новый реально заработал,
            # и не раньше выдержки — одиночное рукопожатие бывает случайным, а снести
            # старый раньше времени значит оставить человека без обоих.
            # Очередь в базе, а не в памяти: рестарт бота и деплой её не теряют.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS pending_retire (
                    old_uuid TEXT PRIMARY KEY,
                    new_uuid TEXT,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    first_handshake_at TIMESTAMP,
                    notified BOOLEAN DEFAULT FALSE
                );
            """)

            res_sv = await self.fetch_all(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name='notify_prefs' AND column_name='seen_version';")
            if not res_sv:
                await self.execute("ALTER TABLE notify_prefs ADD COLUMN seen_version TEXT;")

            # --- КОНТРОЛЬ НАГРУЗКИ ---
            # Узел упирается не в ширину канала, а в пакеты: на клиентский пакет уходит
            # около 130 мкс процессорного времени, то есть потолок примерно 7-8 тысяч
            # пакетов в секунду. Обычный трафик даёт около килобайта на пакет, торрент —
            # втрое-вчетверо больше пакетов на ту же полосу, отсюда и скачки нагрузки.
            #
            # Персональные правила. Их нет у большинства: пир без записи живёт на общем
            # пороге. Режим 'unlimited' снимает ограничение совсем (свои машины),
            # 'custom' задаёт свой порог. expires_at позволяет ограничить на сутки и
            # забыть — правило снимется само.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS peer_limits (
                    user_uuid TEXT PRIMARY KEY REFERENCES users(uuid) ON DELETE CASCADE,
                    mode TEXT NOT NULL DEFAULT 'default',
                    limit_pps INTEGER,
                    expires_at TIMESTAMP,
                    set_by BIGINT,
                    set_at TIMESTAMP DEFAULT NOW()
                );
            """)
            # Превышения порога. Пишется в режиме наблюдения тоже — чтобы было на чём
            # подбирать порог, никого при этом не ограничивая.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS pps_events (
                    id SERIAL PRIMARY KEY,
                    user_uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    started_at TIMESTAMP DEFAULT NOW(),
                    ended_at TIMESTAMP,
                    peak_pps INTEGER,
                    avg_packet_size INTEGER,
                    throttled BOOLEAN DEFAULT FALSE
                );
            """)
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_pps_events_user_time ON pps_events(user_uuid, started_at);")

            # --- АНАЛИТИКА ---
            # Часовые срезы на каждого. Таблица stats хранит замеры с шагом пять минут
            # и чистится за неделю — по ней не построить ни окна активности, ни разбивки
            # по дням недели. Здесь один ряд на человека в час, поэтому 90 дней истории
            # занимают копейки, а аналитика становится настоящей.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS traffic_hourly (
                    user_uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    hour TIMESTAMP NOT NULL,
                    bytes_in BIGINT DEFAULT 0,
                    bytes_out BIGINT DEFAULT 0,
                    packets_in BIGINT DEFAULT 0,
                    packets_out BIGINT DEFAULT 0,
                    peak_pps INTEGER DEFAULT 0,
                    samples INTEGER DEFAULT 0,
                    PRIMARY KEY (user_uuid, hour)
                );
            """)
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_traffic_hourly_hour ON traffic_hourly(hour);")

            # --- ВТОРОЙ ПРОТОКОЛ: XRAY ---
            # Человек остаётся один, меняется только способ подключения. Поэтому
            # здесь не «вторые пользователи», а приписка к существующему: его
            # идентификатор в Xray и токен личной ссылки на подписку.
            #
            # Токен отдельно от идентификатора намеренно: ссылку можно отозвать,
            # не трогая само подключение, и наоборот — сменить доступ, не меняя
            # ссылку, которую человек уже сохранил.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS xray_users (
                    user_uuid TEXT PRIMARY KEY REFERENCES users(uuid) ON DELETE CASCADE,
                    xray_uuid TEXT NOT NULL,
                    sub_token TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    first_seen_at TIMESTAMP,
                    revoked_at TIMESTAMP
                );
            """)
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_xray_token ON xray_users(sub_token);")

            # --- ФИЛЬТРАЦИЯ САЙТОВ ---
            # Категории на человека, а не на роль: роль про домашние сервисы,
            # фильтр про внешний интернет, и людям они назначаются по разной
            # логике. Схема ролей к фильтрам готова (role_grants.kind), но
            # связывать их сейчас значило бы решать за владельца.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS user_filters (
                    user_uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    category TEXT,
                    set_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (user_uuid, category)
                );
            """)

            # --- ДОСТАВКА КЛЮЧА ---
            # Telegram не даёт отметок «прочитано» — их нет в API вовсе, и спорить
            # с этим бесполезно. Поэтому следим не за чтением, а за действиями,
            # каждое из которых видно боту: отправлено → не дошло (бот заблокирован)
            # → человек нажал кнопку → скачал файл → подключился.
            # Запись одна на ключ: при перевыпуске стадии обнуляются, потому что
            # доставлять начинают заново.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS key_delivery (
                    user_uuid TEXT PRIMARY KEY REFERENCES users(uuid) ON DELETE CASCADE,
                    tg_id BIGINT,
                    sent_at TIMESTAMP,
                    blocked_at TIMESTAMP,
                    opened_at TIMESTAMP,
                    downloaded_at TIMESTAMP,
                    connected_at TIMESTAMP,
                    last_error TEXT,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # --- СРОК И СПЯЧКА КЛЮЧА ---
            # Решение о судьбе ключа принимает владелец, а не таймер. Поэтому оно
            # живёт в базе, а не в сообщении Telegram: перезапуск бота не должен
            # терять вопрос, а кнопки в старом сообщении обязаны работать и после.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS pending_decisions (
                    id SERIAL PRIMARY KEY,
                    user_uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    reason TEXT,
                    last_handshake TIMESTAMP,
                    was_expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    resolved_at TIMESTAMP,
                    resolution TEXT
                );
            """)
            # Один нерешённый вопрос на ключ. Частичный индекс, а не UNIQUE на колонку:
            # решённые записи остаются историей и не должны мешать новым.
            await self.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_open "
                "ON pending_decisions(user_uuid) WHERE resolved_at IS NULL;")
            # Что делать в следующий раз: спросить снова или продлить самому.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS key_policy (
                    user_uuid TEXT PRIMARY KEY REFERENCES users(uuid) ON DELETE CASCADE,
                    mode TEXT DEFAULT 'ask',
                    extend_days INTEGER,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # --- РОЛИ: доступы внутри туннеля ---
            # Ролей у человека может быть несколько, и права складываются. «Нет роли»
            # означает полный доступ — противоречия нет: относительно этого состояния
            # любая роль СУЖАЕТ, а несколько ролей сужают меньше, чем одна.
            # kind заведён на вырост: сейчас только 'net' (адреса внутри туннеля),
            # позже сюда же лягут категории фильтрации сайтов, без переделки схемы.
            await self.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            await self.execute("""
                CREATE TABLE IF NOT EXISTS role_grants (
                    id SERIAL PRIMARY KEY,
                    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                    kind TEXT DEFAULT 'net',
                    cidr TEXT,
                    proto TEXT DEFAULT 'any',
                    port INTEGER,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            await self.execute("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                    granted_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (uuid, role_id)
                );
            """)

            # Первичное наполнение базовым списком (дата-центро-враждебные РФ-сервисы)
            existing = await self.fetch_val("SELECT COUNT(*) FROM bypass_exclusions")
            if not existing:
                for domain, cidrs, note in BASE_BYPASS:
                    await self.execute(
                        "INSERT INTO bypass_exclusions (domain, cidrs, note, source) VALUES ($1,$2,$3,'base') ON CONFLICT (domain) DO NOTHING",
                        domain, cidrs, note
                    )

        except Exception as e:
            print(f"Migration error: {e}")

    async def get_seen_version(self, tg_id):
        return await self.fetch_val("SELECT seen_version FROM notify_prefs WHERE tg_id=$1", tg_id)

    async def set_seen_version(self, tg_id, version):
        await self.execute(
            """INSERT INTO notify_prefs (tg_id, seen_version) VALUES ($1,$2)
               ON CONFLICT (tg_id) DO UPDATE SET seen_version=$2""", tg_id, version)

    # ------------------------ ОЧЕРЕДЬ СНЯТИЯ СТАРЫХ КЛЮЧЕЙ ------------------------
    async def queue_retire(self, old_uuid, new_uuid, name):
        await self.execute(
            """INSERT INTO pending_retire (old_uuid, new_uuid, name)
               VALUES ($1,$2,$3) ON CONFLICT (old_uuid) DO UPDATE
               SET new_uuid=$2, name=$3, created_at=NOW(),
                   first_handshake_at=NULL, notified=FALSE""",
            old_uuid, new_uuid, name)

    async def get_pending_retire(self):
        return await self.fetch_all(
            "SELECT old_uuid, new_uuid, name, created_at, first_handshake_at, notified "
            "FROM pending_retire ORDER BY created_at")

    async def mark_retire_handshake(self, old_uuid):
        await self.execute(
            "UPDATE pending_retire SET first_handshake_at=NOW() "
            "WHERE old_uuid=$1 AND first_handshake_at IS NULL", old_uuid)

    async def mark_retire_notified(self, old_uuid):
        await self.execute("UPDATE pending_retire SET notified=TRUE WHERE old_uuid=$1", old_uuid)

    async def drop_pending_retire(self, old_uuid):
        await self.execute("DELETE FROM pending_retire WHERE old_uuid=$1", old_uuid)

    # ------------------------ КОНТРОЛЬ НАГРУЗКИ ------------------------
    # --- ВТОРОЙ ПРОТОКОЛ: XRAY -------------------------------------------
    async def add_xray_user(self, user_uuid, xray_uuid, sub_token):
        """Заводит человеку подключение по Xray. Повторный вызов перевыпускает:
        и идентификатор, и токен ссылки — это и есть «отозвать утёкшую ссылку»."""
        await self.execute(
            """INSERT INTO xray_users (user_uuid, xray_uuid, sub_token)
               VALUES ($1,$2,$3)
               ON CONFLICT (user_uuid) DO UPDATE SET
                   xray_uuid=$2, sub_token=$3, created_at=NOW(),
                   first_seen_at=NULL, revoked_at=NULL""",
            user_uuid, xray_uuid, sub_token)

    async def get_xray_user(self, user_uuid):
        rows = await self.fetch_all(
            "SELECT xray_uuid, sub_token, created_at, first_seen_at, revoked_at "
            "FROM xray_users WHERE user_uuid=$1", user_uuid)
        return dict(rows[0]) if rows else None

    async def get_xray_by_token(self, token):
        """Кому принадлежит ссылка. Отозванные не отдаём — иначе отзыв ничего
        не значил бы до следующей выдачи."""
        rows = await self.fetch_all(
            "SELECT x.user_uuid, x.xray_uuid, u.name, u.is_active, u.expires_at "
            "FROM xray_users x JOIN users u ON u.uuid = x.user_uuid "
            "WHERE x.sub_token=$1 AND x.revoked_at IS NULL", token)
        return dict(rows[0]) if rows else None

    async def list_xray_users(self):
        """Все действующие подключения Xray — из них собирается конфиг узла."""
        rows = await self.fetch_all(
            "SELECT x.user_uuid, x.xray_uuid, x.first_seen_at, u.name, u.is_active "
            "FROM xray_users x JOIN users u ON u.uuid = x.user_uuid "
            "WHERE x.revoked_at IS NULL ORDER BY u.name")
        return [dict(r) for r in rows]

    async def mark_xray_seen(self, user_uuid):
        """Первое живое подключение. Именно оно считается переездом, а не факт
        выдачи ссылки."""
        await self.execute(
            "UPDATE xray_users SET first_seen_at=NOW() "
            "WHERE user_uuid=$1 AND first_seen_at IS NULL", user_uuid)

    async def revoke_xray(self, user_uuid):
        await self.execute(
            "UPDATE xray_users SET revoked_at=NOW() WHERE user_uuid=$1", user_uuid)

    async def count_xray_users(self):
        return await self.fetch_val(
            "SELECT COUNT(*) FROM xray_users WHERE revoked_at IS NULL") or 0

    # --- ФИЛЬТРАЦИЯ САЙТОВ -----------------------------------------------
    async def get_user_filters(self, uuid):
        rows = await self.fetch_all(
            "SELECT category FROM user_filters WHERE user_uuid=$1 ORDER BY category", uuid)
        return [r["category"] for r in rows]

    async def set_user_filter(self, uuid, category, on: bool):
        if on:
            await self.execute(
                "INSERT INTO user_filters (user_uuid, category) VALUES ($1,$2) "
                "ON CONFLICT DO NOTHING", uuid, category)
        else:
            await self.execute(
                "DELETE FROM user_filters WHERE user_uuid=$1 AND category=$2",
                uuid, category)

    async def get_all_filters(self):
        """uuid -> список категорий. Кого здесь нет — у того фильтров нет,
        и его запросы узел не перехватывает вовсе."""
        rows = await self.fetch_all(
            "SELECT user_uuid, category FROM user_filters ORDER BY user_uuid")
        out = {}
        for r in rows:
            out.setdefault(r["user_uuid"], []).append(r["category"])
        return out

    async def count_filtered_users(self):
        return await self.fetch_val(
            "SELECT COUNT(DISTINCT user_uuid) FROM user_filters") or 0

    # --- ДОСТАВКА КЛЮЧА --------------------------------------------------
    async def delivery_sent(self, uuid, tg_id):
        """Конфиг ушёл в чат. Стадии сбрасываются: доставка началась заново
        (перевыпуск, повторная отправка), и старые отметки к ней не относятся."""
        await self.execute(
            "INSERT INTO key_delivery (user_uuid, tg_id, sent_at, updated_at) "
            "VALUES ($1,$2,NOW(),NOW()) ON CONFLICT (user_uuid) DO UPDATE SET "
            "tg_id=$2, sent_at=NOW(), blocked_at=NULL, opened_at=NULL, "
            "downloaded_at=NULL, connected_at=NULL, last_error=NULL, updated_at=NOW()",
            uuid, tg_id)

    async def delivery_blocked(self, uuid, tg_id, error):
        """Telegram не принял сообщение: чаще всего человек не запускал бота
        или заблокировал его. Это не ошибка отправки, а состояние доставки."""
        await self.execute(
            "INSERT INTO key_delivery (user_uuid, tg_id, blocked_at, last_error, updated_at) "
            "VALUES ($1,$2,NOW(),$3,NOW()) ON CONFLICT (user_uuid) DO UPDATE SET "
            "tg_id=$2, blocked_at=NOW(), last_error=$3, updated_at=NOW()",
            uuid, tg_id, str(error)[:400])

    async def delivery_opened(self, tg_id):
        """Человек нажал кнопку в боте — значит сообщение он увидел.
        Отмечаем только первый раз и только то, что ещё не отмечено."""
        await self.execute(
            "UPDATE key_delivery SET opened_at=NOW(), updated_at=NOW() "
            "WHERE tg_id=$1 AND sent_at IS NOT NULL AND opened_at IS NULL", tg_id)

    async def delivery_downloaded(self, uuid):
        await self.execute(
            "UPDATE key_delivery SET downloaded_at=NOW(), "
            "opened_at=COALESCE(opened_at, NOW()), updated_at=NOW() "
            "WHERE user_uuid=$1 AND downloaded_at IS NULL", uuid)

    async def delivery_connected(self, uuid):
        """Ставится по живому рукопожатию — единственная стадия, которую
        подтверждает не Telegram, а сам туннель."""
        await self.execute(
            "UPDATE key_delivery SET connected_at=NOW(), updated_at=NOW() "
            "WHERE user_uuid=$1 AND connected_at IS NULL", uuid)

    async def get_delivery(self, uuid):
        rows = await self.fetch_all(
            "SELECT tg_id, sent_at, blocked_at, opened_at, downloaded_at, "
            "connected_at, last_error FROM key_delivery WHERE user_uuid=$1", uuid)
        return dict(rows[0]) if rows else None

    async def get_stuck_deliveries(self, hours=24):
        """Кому отправили, но дело не дошло до подключения. Это и есть ответ на
        вопрос «дошёл ли ключ» — без отметок о прочтении, по действиям."""
        rows = await self.fetch_all("""
            SELECT d.user_uuid, u.name, d.tg_id, d.sent_at, d.blocked_at,
                   d.opened_at, d.downloaded_at, d.last_error
            FROM key_delivery d JOIN users u ON u.uuid = d.user_uuid
            WHERE d.connected_at IS NULL
              AND (d.blocked_at IS NOT NULL
                   OR d.sent_at < NOW() - ($1 || ' hours')::INTERVAL)
            ORDER BY COALESCE(d.sent_at, d.blocked_at)
        """, str(hours))
        return [dict(r) for r in rows]

    # --- СРОК И СПЯЧКА КЛЮЧА --------------------------------------------
    async def add_pending_decision(self, uuid, reason, last_handshake=None,
                                   was_expires_at=None):
        """Ставит вопрос по ключу. Если вопрос уже открыт — второй раз не задаём."""
        await self.execute(
            "INSERT INTO pending_decisions (user_uuid, reason, last_handshake, was_expires_at) "
            "SELECT $1,$2,$3,$4 WHERE NOT EXISTS ("
            "  SELECT 1 FROM pending_decisions WHERE user_uuid=$1 AND resolved_at IS NULL)",
            uuid, reason, last_handshake, was_expires_at)

    async def get_pending_decisions(self):
        rows = await self.fetch_all("""
            SELECT d.id, d.user_uuid, d.reason, d.last_handshake, d.was_expires_at,
                   d.created_at, u.name
            FROM pending_decisions d JOIN users u ON u.uuid = d.user_uuid
            WHERE d.resolved_at IS NULL ORDER BY d.created_at
        """)
        return [dict(r) for r in rows]

    async def get_pending_decision(self, uuid):
        rows = await self.fetch_all(
            "SELECT id, user_uuid, reason, last_handshake, was_expires_at, created_at "
            "FROM pending_decisions WHERE user_uuid=$1 AND resolved_at IS NULL", uuid)
        return dict(rows[0]) if rows else None

    async def resolve_decision(self, uuid, resolution):
        await self.execute(
            "UPDATE pending_decisions SET resolved_at=NOW(), resolution=$2 "
            "WHERE user_uuid=$1 AND resolved_at IS NULL", uuid, resolution)

    async def get_key_policy(self, uuid):
        """Нет записи — значит спрашивать. Умолчание намеренно осторожное:
        молча продлевать ключ можно только по явному решению владельца."""
        rows = await self.fetch_all(
            "SELECT mode, extend_days FROM key_policy WHERE user_uuid=$1", uuid)
        return dict(rows[0]) if rows else {"mode": "ask", "extend_days": None}

    async def set_key_policy(self, uuid, mode, extend_days=None):
        await self.execute(
            "INSERT INTO key_policy (user_uuid, mode, extend_days, updated_at) "
            "VALUES ($1,$2,$3,NOW()) ON CONFLICT (user_uuid) DO UPDATE SET "
            "mode=$2, extend_days=$3, updated_at=NOW()", uuid, mode, extend_days)

    # --- РОЛИ ------------------------------------------------------------
    async def list_roles(self):
        """Список ролей с двумя числами: сколько правил внутри и сколько человек."""
        rows = await self.fetch_all("""
            SELECT r.id, r.name, r.note,
                   (SELECT COUNT(*) FROM role_grants g WHERE g.role_id = r.id) AS grants,
                   (SELECT COUNT(*) FROM user_roles u WHERE u.role_id = r.id) AS members
            FROM roles r ORDER BY r.name
        """)
        return [dict(r) for r in rows]

    async def get_role(self, role_id):
        row = await self.fetch_all("SELECT id, name, note FROM roles WHERE id=$1", role_id)
        return dict(row[0]) if row else None

    async def create_role(self, name):
        return await self.fetch_val(
            "INSERT INTO roles (name) VALUES ($1) ON CONFLICT (name) DO NOTHING RETURNING id",
            name)

    async def delete_role(self, role_id):
        await self.execute("DELETE FROM roles WHERE id=$1", role_id)

    async def get_role_grants(self, role_id):
        rows = await self.fetch_all(
            "SELECT id, kind, cidr, proto, port, note FROM role_grants "
            "WHERE role_id=$1 ORDER BY id", role_id)
        return [dict(r) for r in rows]

    async def add_role_grant(self, role_id, cidr, proto="any", port=None, note=None):
        await self.execute(
            "INSERT INTO role_grants (role_id, kind, cidr, proto, port, note) "
            "VALUES ($1,'net',$2,$3,$4,$5)", role_id, cidr, proto, port, note)

    async def delete_role_grant(self, grant_id):
        await self.execute("DELETE FROM role_grants WHERE id=$1", grant_id)

    async def get_role_members(self, role_id):
        rows = await self.fetch_all(
            "SELECT u.uuid, u.name FROM user_roles ur JOIN users u ON u.uuid = ur.uuid "
            "WHERE ur.role_id=$1 ORDER BY u.name", role_id)
        return [dict(r) for r in rows]

    async def add_user_role(self, uuid, role_id):
        await self.execute(
            "INSERT INTO user_roles (uuid, role_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
            uuid, role_id)

    async def remove_user_role(self, uuid, role_id):
        await self.execute("DELETE FROM user_roles WHERE uuid=$1 AND role_id=$2",
                           uuid, role_id)

    async def get_user_roles(self, uuid):
        rows = await self.fetch_all(
            "SELECT r.id, r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id "
            "WHERE ur.uuid=$1 ORDER BY r.name", uuid)
        return [dict(r) for r in rows]

    async def get_access_matrix(self):
        """Кому что можно внутри туннеля — уже с объединением по всем его ролям.

        Возвращаются ТОЛЬКО те, у кого есть хотя бы одна роль: остальные ходят
        без ограничений, и правил для них не создаётся вовсе. Имя роли идёт
        рядом с правилом, чтобы в карточке было видно, откуда взялся доступ."""
        rows = await self.fetch_all("""
            SELECT ur.uuid, u.name AS user_name, r.name AS role_name,
                   g.cidr, g.proto, g.port
            FROM user_roles ur
            JOIN users u ON u.uuid = ur.uuid
            JOIN roles r ON r.id = ur.role_id
            LEFT JOIN role_grants g ON g.role_id = r.id AND g.kind = 'net'
            ORDER BY u.name
        """)
        matrix = {}
        for r in rows:
            rec = matrix.setdefault(r["uuid"], {"name": r["user_name"], "allow": []})
            if r["cidr"]:
                rec["allow"].append({"cidr": r["cidr"], "proto": r["proto"],
                                     "port": r["port"], "role": r["role_name"]})
        return matrix

    async def get_peer_limits(self):
        """Персональные правила. Кого здесь нет — тот на общем пороге."""
        rows = await self.fetch_all(
            "SELECT user_uuid, mode, limit_pps, expires_at FROM peer_limits")
        return {r["user_uuid"]: dict(r) for r in rows}

    async def set_peer_limit(self, uuid, mode, limit_pps=None, expires_at=None, set_by=None):
        await self.execute(
            """INSERT INTO peer_limits (user_uuid, mode, limit_pps, expires_at, set_by, set_at)
               VALUES ($1,$2,$3,$4,$5,NOW())
               ON CONFLICT (user_uuid) DO UPDATE SET
                   mode=$2, limit_pps=$3, expires_at=$4, set_by=$5, set_at=NOW()""",
            uuid, mode, limit_pps, expires_at, set_by)

    async def clear_peer_limit(self, uuid):
        await self.execute("DELETE FROM peer_limits WHERE user_uuid=$1", uuid)

    async def drop_expired_peer_limits(self):
        """Временные правила («ограничить на сутки») снимаются сами."""
        return await self.execute(
            "DELETE FROM peer_limits WHERE expires_at IS NOT NULL AND expires_at < NOW()")

    async def record_pps_event(self, uuid, peak_pps, avg_packet_size, throttled=False):
        await self.execute(
            """INSERT INTO pps_events (user_uuid, ended_at, peak_pps, avg_packet_size, throttled)
               VALUES ($1, NOW(), $2, $3, $4)""",
            uuid, int(peak_pps), int(avg_packet_size or 0), throttled)

    async def get_pps_events(self, hours=24):
        return await self.fetch_all(
            """SELECT e.user_uuid, u.name, e.started_at, e.ended_at, e.peak_pps,
                      e.avg_packet_size, e.throttled
               FROM pps_events e LEFT JOIN users u ON u.uuid = e.user_uuid
               WHERE e.started_at > NOW() - ($1 || ' hours')::interval
               ORDER BY e.peak_pps DESC""", str(hours))

    # ------------------------ ЧАСОВЫЕ СРЕЗЫ ------------------------
    async def add_hourly(self, uuid, hour, b_in, b_out, p_in, p_out, peak_pps):
        await self.execute(
            """INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out,
                                           packets_in, packets_out, peak_pps, samples)
               VALUES ($1,$2,$3,$4,$5,$6,$7,1)
               ON CONFLICT (user_uuid, hour) DO UPDATE SET
                   bytes_in   = traffic_hourly.bytes_in   + $3,
                   bytes_out  = traffic_hourly.bytes_out  + $4,
                   packets_in = traffic_hourly.packets_in + $5,
                   packets_out= traffic_hourly.packets_out+ $6,
                   peak_pps   = GREATEST(traffic_hourly.peak_pps, $7),
                   samples    = traffic_hourly.samples + 1""",
            uuid, hour, int(b_in), int(b_out), int(p_in), int(p_out), int(peak_pps))

    async def backfill_hourly_from_stats(self):
        """Сворачивает уже накопленную статистику в часовые срезы — чтобы неделя
        истории была доступна сразу, а не копилась с нуля. Запускается один раз."""
        done = await self.get_setting("hourly_backfill_done")
        if done:
            return 0
        await self.execute(
            """INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out, samples)
               SELECT user_uuid, date_trunc('hour', last_seen),
                      MAX(bytes_in) - MIN(bytes_in), MAX(bytes_out) - MIN(bytes_out),
                      COUNT(*)
               FROM stats
               WHERE last_seen IS NOT NULL AND user_uuid IS NOT NULL
               GROUP BY user_uuid, date_trunc('hour', last_seen)
               ON CONFLICT (user_uuid, hour) DO NOTHING""")
        await self.set_setting("hourly_backfill_done", "1")
        return await self.fetch_val("SELECT COUNT(*) FROM traffic_hourly")

    async def get_hourly(self, hours=24, uuid=None):
        """Часовые срезы для графиков. Без uuid — сумма по всем, с uuid — один человек."""
        if uuid:
            return await self.fetch_all(
                """SELECT hour, bytes_in, bytes_out, packets_in, packets_out, peak_pps
                   FROM traffic_hourly
                   WHERE user_uuid=$1 AND hour > NOW() - ($2 || ' hours')::interval
                   ORDER BY hour""", uuid, str(hours))
        return await self.fetch_all(
            """SELECT hour,
                      SUM(bytes_in)   AS bytes_in,
                      SUM(bytes_out)  AS bytes_out,
                      SUM(packets_in) AS packets_in,
                      SUM(packets_out) AS packets_out,
                      MAX(peak_pps)   AS peak_pps
               FROM traffic_hourly
               WHERE hour > NOW() - ($1 || ' hours')::interval
               GROUP BY hour ORDER BY hour""", str(hours))

    async def get_user_profile(self, uuid, days=30):
        """Слепок поведения человека для сводки и аналитики: объёмы, окно активности,
        дни недели, доля отдачи, средний размер пакета, превышения лимита."""
        rows = await self.fetch_all(
            """SELECT hour, bytes_in, bytes_out, packets_in, packets_out, peak_pps
               FROM traffic_hourly
               WHERE user_uuid=$1 AND hour > NOW() - ($2 || ' days')::interval""",
            uuid, str(days))
        if not rows:
            return None

        b_in = sum(r["bytes_in"] or 0 for r in rows)
        b_out = sum(r["bytes_out"] or 0 for r in rows)
        p_in = sum(r["packets_in"] or 0 for r in rows)
        p_out = sum(r["packets_out"] or 0 for r in rows)
        peak = max((r["peak_pps"] or 0) for r in rows)

        # окно активности: часы, на которые приходится основной объём
        by_hour = {}
        by_dow = {}
        for r in rows:
            h = dt_to_moscow(r["hour"])
            total = (r["bytes_in"] or 0) + (r["bytes_out"] or 0)
            by_hour[h.hour] = by_hour.get(h.hour, 0) + total
            by_dow[h.weekday()] = by_dow.get(h.weekday(), 0) + total

        top_hours = sorted(by_hour.items(), key=lambda kv: kv[1], reverse=True)[:4]
        hours_sorted = sorted(h for h, _ in top_hours)
        top_dow = sorted(by_dow.items(), key=lambda kv: kv[1], reverse=True)[:2]

        exceeded = await self.fetch_val(
            """SELECT COUNT(*) FROM pps_events
               WHERE user_uuid=$1 AND started_at > NOW() - ($2 || ' days')::interval""",
            uuid, str(days)) or 0

        total_packets = p_in + p_out
        return {
            "bytes_in": b_in, "bytes_out": b_out,
            "packets_in": p_in, "packets_out": p_out,
            "peak_pps": peak,
            "avg_packet": int((b_in + b_out) / total_packets) if total_packets else 0,
            # Доля ОТДАЧИ считается от bytes_in: это то, что сервер принял от пира,
            # то есть отправленное человеком. Профиль раздачи
            # отличается от профиля потребления как раз этой долей.
            "upload_share": round(b_in / (b_in + b_out) * 100) if (b_in + b_out) else 0,
            "active_hours": hours_sorted,
            "top_weekdays": [d for d, _ in top_dow],
            "exceeded": exceeded,
            "hours_seen": len(rows),
        }

    async def cleanup_hourly(self, days=90):
        await self.execute(
            f"DELETE FROM traffic_hourly WHERE hour < NOW() - INTERVAL '{int(days)} DAYS'")

    # ------------------------ SPLIT-TUNNEL EXCLUSIONS ------------------------
    async def get_bypass_exclusions(self):
        return await self.fetch_all(
            "SELECT id, domain, cidrs, note, source, created_at FROM bypass_exclusions ORDER BY created_at ASC"
        )

    async def get_all_bypass_cidrs(self):
        """Плоский дедуплицированный список всех CIDR из исключений (для AllowedIPs)."""
        rows = await self.fetch_all("SELECT cidrs FROM bypass_exclusions")
        seen, res = set(), []
        for r in rows:
            for c in (r['cidrs'] or "").split(","):
                c = c.strip()
                if c and c not in seen:
                    seen.add(c)
                    res.append(c)
        return res

    async def add_bypass_exclusion(self, domain, cidrs, note="", source="manual", bump=True):
        """Добавляет/обновляет исключение. bump=True поднимает routing_version (все ключи
        станут устаревшими → напоминание о перевыпуске). Для тихого авто-расширения при
        дрейфе IP вызывать с bump=False."""
        cidrs_str = ",".join(cidrs) if isinstance(cidrs, (list, tuple)) else str(cidrs)
        await self.execute(
            "INSERT INTO bypass_exclusions (domain, cidrs, note, source) VALUES ($1,$2,$3,$4) "
            "ON CONFLICT (domain) DO UPDATE SET cidrs=$2, note=$3, source=$4",
            domain, cidrs_str, note, source
        )
        if bump:
            return await self.bump_routing_version()
        return await self.get_routing_version()

    async def remove_bypass_exclusion(self, exid):
        await self.execute("DELETE FROM bypass_exclusions WHERE id=$1", int(exid))
        return await self.bump_routing_version()

    async def add_bypass_request(self, domain, cidrs, tg_id):
        cidrs_str = ",".join(cidrs) if isinstance(cidrs, (list, tuple)) else str(cidrs)
        return await self.fetch_val(
            "INSERT INTO bypass_requests (domain, cidrs, tg_id) VALUES ($1,$2,$3) RETURNING id",
            domain, cidrs_str, tg_id
        )

    async def get_bypass_request(self, req_id):
        rows = await self.fetch_all("SELECT id, domain, cidrs, tg_id, status FROM bypass_requests WHERE id=$1", int(req_id))
        return rows[0] if rows else None

    async def set_bypass_request_status(self, req_id, status):
        await self.execute("UPDATE bypass_requests SET status=$1 WHERE id=$2", status, int(req_id))

    async def get_routing_notify(self, tg_id):
        """Включены ли у пользователя напоминания о смене политик. По умолчанию True."""
        v = await self.fetch_val("SELECT routing_notify FROM notify_prefs WHERE tg_id=$1", tg_id)
        return True if v is None else bool(v)

    async def set_routing_notify(self, tg_id, enabled):
        await self.execute(
            "INSERT INTO notify_prefs (tg_id, routing_notify) VALUES ($1,$2) "
            "ON CONFLICT (tg_id) DO UPDATE SET routing_notify=$2",
            tg_id, bool(enabled)
        )

    async def toggle_routing_notify(self, tg_id):
        new_state = not await self.get_routing_notify(tg_id)
        await self.set_routing_notify(tg_id, new_state)
        return new_state

    async def get_routing_version(self):
        """Текущая (эффективная) версия маршрутизации. Хранится в settings и не может
        быть ниже базовой константы ROUTING_VERSION."""
        v = await self.get_setting("routing_version")
        try:
            return max(int(v), ROUTING_VERSION) if v is not None else ROUTING_VERSION
        except (TypeError, ValueError):
            return ROUTING_VERSION

    async def bump_routing_version(self):
        """Поднимает версию маршрутизации на 1 → все ранее выданные ключи становятся
        устаревшими и получат напоминание о перевыпуске."""
        new = await self.get_routing_version() + 1
        await self.set_setting("routing_version", str(new))
        return new

    async def get_outdated_keys(self, current_version):
        """Ключи со старым форматом маршрутизации, у которых есть привязка Telegram —
        для ежедневного напоминания «перевыпусти конфиг»."""
        query = """
            SELECT u.uuid, u.name, ARRAY_REMOVE(ARRAY_AGG(l.tg_id), NULL) as tg_ids
            FROM users u
            JOIN user_tg_links l ON u.uuid = l.uuid
            WHERE COALESCE(u.routing_version, 0) < $1
            GROUP BY u.uuid, u.name
        """
        return await self.fetch_all(query, current_version)

    async def track_user_ip(self, uuid, ip):
        existing = await self.fetch_val("SELECT status FROM user_ips WHERE uuid=$1 AND ip=$2", uuid, ip)
        if not existing:
            await self.execute("INSERT INTO user_ips (uuid, ip) VALUES ($1, $2)", uuid, ip)
            return True 
        else:
            await self.execute("UPDATE user_ips SET last_seen = NOW() WHERE uuid=$1 AND ip=$2", uuid, ip)
            if existing == 'pending':
                await self.execute("UPDATE user_ips SET status = 'trusted' WHERE uuid=$1 AND status = 'pending' AND first_seen < NOW() - INTERVAL '48 HOURS'", uuid)
            return False 

    async def get_user_ips(self, uuid):
        query = "SELECT ip, status, first_seen, last_seen FROM user_ips WHERE uuid=$1 ORDER BY last_seen DESC LIMIT 8"
        return await self.fetch_all(query, uuid)

    async def log_event(self, event_type, message):
        try:
            query = "INSERT INTO events_log (event_type, message) VALUES ($1, $2)"
            await self.execute(query, event_type, message)
        except Exception as e:
            print(f"Failed to log event (ignored): {e}")

    async def execute(self, query, *args):
        for i in range(3):
            try:
                if not self.pool: await self.connect()
                async with self.pool.acquire() as conn:
                    return await conn.execute(query, *args)
            except Exception as e:
                print(f"DB Execute Error: {e}. Retrying {i+1}/3...")
                await asyncio.sleep(2)
                if i == 2: raise

    async def fetch_all(self, query, *args):
        for i in range(3):
            try:
                if not self.pool: await self.connect()
                async with self.pool.acquire() as conn:
                    return await conn.fetch(query, *args)
            except Exception as e:
                print(f"DB Fetch Error: {e}. Retrying {i+1}/3...")
                await asyncio.sleep(2)
                if i == 2: raise
    
    async def fetch_val(self, query, *args):
        for i in range(3):
            try:
                if not self.pool: await self.connect()
                async with self.pool.acquire() as conn:
                    return await conn.fetchval(query, *args)
            except Exception as e:
                print(f"DB Fetchval Error: {e}. Retrying {i+1}/3...")
                await asyncio.sleep(2)
                if i == 2: raise

    async def device_set(self, uuid):
        query = "SELECT device FROM users WHERE uuid=$1"
        result = await self.fetch_all(query, uuid)
        if result and result[0]["device"]:
            return True
        return False

    async def get_all_users(self):
        query = """
            SELECT u.id, u.name, u.uuid, u.device, u.is_active, u.expires_at, u.created_at, u.first_connected_at, u.last_active_at,
                   ARRAY_REMOVE(ARRAY_AGG(l.tg_id), NULL) as tg_ids
            FROM users u
            LEFT JOIN user_tg_links l ON u.uuid = l.uuid
            GROUP BY u.id, u.name, u.uuid, u.device, u.is_active, u.expires_at, u.created_at, u.first_connected_at, u.last_active_at
            ORDER BY u.created_at DESC
        """
        return await self.fetch_all(query)
    
    async def get_user_by_uuid(self, uuid):
        query = """
            SELECT u.id, u.name, u.uuid, u.device, u.is_active, u.expires_at, u.created_at, u.first_connected_at, u.last_active_at,
                   ARRAY_REMOVE(ARRAY_AGG(l.tg_id), NULL) as tg_ids
            FROM users u
            LEFT JOIN user_tg_links l ON u.uuid = l.uuid
            WHERE u.uuid=$1
            GROUP BY u.id, u.name, u.uuid, u.device, u.is_active, u.expires_at, u.created_at, u.first_connected_at, u.last_active_at
        """
        rows = await self.fetch_all(query, uuid)
        return rows[0] if rows else None

    async def get_users_by_tg_id(self, tg_id):
        query = """
            SELECT u.id, u.name, u.uuid, u.device, u.is_active, u.expires_at, u.created_at, u.first_connected_at, u.last_active_at,
                   ARRAY_REMOVE(ARRAY_AGG(l.tg_id), NULL) as tg_ids 
            FROM users u
            JOIN user_tg_links l ON u.uuid = l.uuid
            WHERE l.tg_id=$1
            GROUP BY u.id, u.name, u.uuid, u.device, u.is_active, u.expires_at, u.created_at, u.first_connected_at, u.last_active_at
        """
        return await self.fetch_all(query, tg_id)

    async def link_user_telegram(self, uuid, tg_id):
        await self.execute("INSERT INTO user_tg_links (uuid, tg_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", uuid, tg_id)
        await self.log_event("Link TG", f"Linked TG {tg_id} to key {uuid}")

    async def unlink_user_telegram(self, uuid, tg_id):
        await self.execute("DELETE FROM user_tg_links WHERE uuid=$1 AND tg_id=$2", uuid, tg_id)
        await self.log_event("Unlink TG", f"Unlinked TG {tg_id} from key {uuid}")

    async def get_all_tg_ids(self):
        query = "SELECT DISTINCT tg_id FROM user_tg_links"
        rows = await self.fetch_all(query)
        return [r['tg_id'] for r in rows]

    async def save_stats(self, uuid, rx, tx):
        user = await self.get_user_by_uuid(uuid)
        if user:
            query = "INSERT INTO stats (user_uuid, bytes_in, bytes_out, last_seen) VALUES ($1, $2, $3, NOW())"
            await self.execute(query, uuid, rx, tx)

    async def get_stats_24h(self):
        query = """
            SELECT s.user_uuid, u.name, s.bytes_in, s.bytes_out, s.last_seen 
            FROM stats s
            JOIN users u ON s.user_uuid = u.uuid
            WHERE s.last_seen >= NOW() - INTERVAL '24 HOURS'
            ORDER BY s.last_seen ASC
        """
        return await self.fetch_all(query)

    async def cleanup_old_logs(self, days=7):
        await self.execute(f"DELETE FROM events_log WHERE timestamp < NOW() - INTERVAL '{days} DAYS'")
        await self.execute(f"DELETE FROM stats WHERE last_seen < NOW() - INTERVAL '{days} DAYS'")
        await self.execute(f"DELETE FROM user_ips WHERE status = 'pending' AND last_seen < NOW() - INTERVAL '7 DAYS'")

    async def set_setting(self, key, value):
        await self.execute("INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2", key, str(value))

    async def get_setting(self, key):
        return await self.fetch_val("SELECT value FROM settings WHERE key=$1", key)

    async def export_to_excel(self, path):
        users = await self.get_all_users()
        wb = Workbook()
        
        ws = wb.active
        ws.title = "VPN Users"

        headers =["Имя", "UUID", "Устройство", "Статус", "Годен до", "TG IDs", "Создано", "Первый Вход", "Посл. Активность", "Конфиг (Текст)", "QR Код"]
        ws.append(headers)

        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 20
        ws.column_dimensions['F'].width = 25
        ws.column_dimensions['G'].width = 20
        ws.column_dimensions['H'].width = 20
        ws.column_dimensions['I'].width = 20
        ws.column_dimensions['J'].width = 45
        ws.column_dimensions['K'].width = 25

        for index, u in enumerate(users, start=2):
            status_text = "Активен" if u['is_active'] else "Пауза"
            exp_text = dt_to_moscow(u['expires_at']).strftime("%Y-%m-%d %H:%M") if u['expires_at'] else "Навсегда"
            
            ws.cell(row=index, column=1, value=u['name'])
            ws.cell(row=index, column=2, value=u['uuid'])
            ws.cell(row=index, column=3, value=u['device'] or "")
            st_cell = ws.cell(row=index, column=4, value=status_text)
            _mark(st_cell, _OK_FILL if u['is_active'] else _OFF_FILL)
            st_cell.alignment = Alignment(horizontal="center")
            ws.cell(row=index, column=5, value=exp_text)
            
            tg_ids_str = ", ".join(map(str, u.get('tg_ids',[])))
            ws.cell(row=index, column=6, value=tg_ids_str)
            
            ws.cell(row=index, column=7, value=dt_to_moscow(u['created_at']).strftime("%Y-%m-%d %H:%M") if u['created_at'] else "")
            ws.cell(row=index, column=8, value=dt_to_moscow(u['first_connected_at']).strftime("%Y-%m-%d %H:%M") if u['first_connected_at'] else "")
            ws.cell(row=index, column=9, value=dt_to_moscow(u['last_active_at']).strftime("%Y-%m-%d %H:%M") if u.get('last_active_at') else "Нет данных")

            conf_path = CONFIGS_DIR / f"{u['name']}.conf"
            if not conf_path.exists():
                conf_path = CONFIGS_DIR / f"{u['name']}_Full.conf"
                
            if conf_path.exists():
                with open(conf_path, "r") as f:
                    conf_text = f.read()
                cell = ws.cell(row=index, column=10, value=conf_text)
                cell.alignment = Alignment(wrap_text=True, vertical="top")

            qr_path = CONFIGS_DIR / f"{u['name']}.png"
            if not qr_path.exists():
                qr_path = CONFIGS_DIR / f"{u['name']}_Full.png"

            if qr_path.exists():
                try:
                    img = ExcelImage(str(qr_path))
                    img.width = 150
                    img.height = 150
                    ws.add_image(img, f"K{index}")
                    ws.row_dimensions[index].height = 120
                except Exception as e:
                    ws.cell(row=index, column=11, value=f"Ошибка картинки: {e}")
            else:
                ws.row_dimensions[index].height = 120

        _style_sheet(ws)

        ws_events = wb.create_sheet(title="События системы")
        ws_events.append(["Дата и время (МСК)", "Тип события", "Сообщение"])
        ws_events.column_dimensions['A'].width = 25
        ws_events.column_dimensions['B'].width = 20
        ws_events.column_dimensions['C'].width = 70

        logs = await self.fetch_all("SELECT timestamp, event_type, message FROM events_log ORDER BY timestamp DESC")
        for row in logs:
            ws_events.append([dt_to_moscow(row['timestamp']).strftime("%Y-%m-%d %H:%M:%S"), row['event_type'], row['message']])
        _style_sheet(ws_events)

        ws_wg = wb.create_sheet(title="wg0.conf")
        ws_wg.column_dimensions['A'].width = 120
        if WG_CONF_PATH.exists():
            with open(WG_CONF_PATH, "r") as f:
                wg_text = f.read()
            cell = ws_wg.cell(row=1, column=1, value=wg_text)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        else:
            ws_wg.cell(row=1, column=1, value="Файл wg0.conf не найден в контейнере!")

        wb.save(path)
        return path

    # ------------------------ СВОДНЫЙ ЛИСТ ------------------------
    @staticmethod
    def _verdict(profile, user, exceeded):
        """Строка-вывод по человеку: чтобы таблицу можно было не читать глазами.

        Собирается из того, что реально видно в цифрах: когда человек в сети, что он
        делает с каналом и создаёт ли проблемы. Ни одного слова наугад."""
        if not profile:
            return "Нет данных — активности не было"

        parts = []

        hours = profile["active_hours"]
        if hours:
            night = sum(1 for h in hours if h < 7)
            evening = sum(1 for h in hours if 18 <= h <= 23)
            day = sum(1 for h in hours if 9 <= h <= 17)
            if night >= 2:
                parts.append("ночная активность")
            elif evening >= 2:
                parts.append("вечерний")
            elif day >= 2:
                parts.append("дневной")

        share = profile["upload_share"]
        avg = profile["avg_packet"]
        if share >= 40:
            parts.append("профиль раздачи")
        elif avg and avg < 500:
            parts.append("мелкие пакеты, похоже на торрент")
        else:
            parts.append("потребление")

        if exceeded:
            parts.append(f"превышений лимита: {exceeded}")
        elif profile["hours_seen"] >= 24:
            parts.append("стабилен")

        gb = (profile["bytes_in"] + profile["bytes_out"]) / 1024 ** 3
        if gb >= 0.1:
            parts.append(f"{gb:.1f} ГБ за период")

        text = ", ".join(parts)
        return text[:1].upper() + text[1:] if text else "Активности не было"

    async def export_summary_to_excel(self, path, days=30):
        """Одна страница, строка на человека: объёмы, поведение и вывод текстом.

        Раньше выгрузка делала отдельный лист на каждого — тридцать листов, которые
        никто не открывал. Здесь всё в одной таблице, с фильтром по колонкам.
        """
        # Клиент-сервер из сводки исключаем: это канал, а не человек, и его
        # строка всегда выглядела бы аварийной, оттягивая внимание от живых.
        users = [u for u in await self.get_all_users() if not is_agent(u["name"])]
        limits = await self.get_peer_limits()
        common_limit = int(await self.get_setting("pps_limit") or 5000)

        # адреса пиров берём у узла: в базе их нет, а в таблице они полезны
        peer_ips = {}
        try:
            from utils import api_session, WG_API_URL
            async with api_session() as session:
                async with session.get(f"{WG_API_URL}/peers", timeout=5) as r:
                    if r.status == 200:
                        for p in await r.json():
                            peer_ips[p.get("uuid")] = (p.get("allowed_ips") or "").split("/")[0]
        except Exception:
            pass

        wb = Workbook()
        ws = wb.active
        ws.title = "Сводка"

        headers = [
            "Имя", "Адрес", "Статус", "Лимит", "Скачал, ГБ", "Отдал, ГБ",
            "Доля отдачи, %", "Средний пакет, Б", "Пик пак/с", "Превышений",
            "Окно активности", "Дни недели", "Последняя активность", "Вывод",
        ]
        ws.append(headers)
        widths = [18, 14, 10, 18, 12, 11, 14, 17, 11, 12, 20, 16, 20, 52]
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

        DOW = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        row = 2
        total_in = total_out = 0

        for u in users:
            uuid_val = u["uuid"]
            profile = await self.get_user_profile(uuid_val, days=days)
            exceeded = await self.fetch_val(
                """SELECT COUNT(*) FROM pps_events WHERE user_uuid=$1
                   AND started_at > NOW() - ($2 || ' days')::interval""",
                uuid_val, str(days)) or 0

            rule = limits.get(uuid_val)
            if not rule:
                limit_text = f"общий, {common_limit}"
            elif rule["mode"] == "unlimited":
                limit_text = "без ограничений"
            else:
                limit_text = f"свой, {rule['limit_pps']}"

            b_in = profile["bytes_in"] if profile else 0
            b_out = profile["bytes_out"] if profile else 0
            total_in += b_in
            total_out += b_out

            window = ""
            if profile and profile["active_hours"]:
                hrs = profile["active_hours"]
                window = f"{min(hrs):02d}:00–{max(hrs) + 1:02d}:00"
            dows = ""
            if profile and profile["top_weekdays"]:
                dows = ", ".join(DOW[d] for d in profile["top_weekdays"])

            ws.cell(row=row, column=1, value=u["name"])
            ws.cell(row=row, column=2, value=peer_ips.get(uuid_val, ""))
            st = ws.cell(row=row, column=3, value="Активен" if u["is_active"] else "Пауза")
            _mark(st, _OK_FILL if u["is_active"] else _OFF_FILL)
            ws.cell(row=row, column=4, value=limit_text)
            # Колонки с точки зрения ЧЕЛОВЕКА, а не сервера: он «скачал» то, что
            # сервер ему отдал, и «отдал» то, что сервер от него принял.
            ws.cell(row=row, column=5, value=round(b_out / 1024 ** 3, 2))
            ws.cell(row=row, column=6, value=round(b_in / 1024 ** 3, 2))
            # Доля отдачи: у обычного человека она мала. Высокая — это раздача.
            share = profile["upload_share"] if profile else 0
            sh = ws.cell(row=row, column=7, value=share)
            if share >= 40:
                _mark(sh, _BAD_FILL)
            elif share >= 25:
                _mark(sh, _WARN_FILL)

            # Средний размер пакета: ниже полукилобайта — почерк торрента.
            avg_p = profile["avg_packet"] if profile else 0
            ap = ws.cell(row=row, column=8, value=avg_p)
            if avg_p and avg_p < 500:
                _mark(ap, _BAD_FILL)
            elif avg_p and avg_p < 700:
                _mark(ap, _WARN_FILL)

            # Пик пакетов в секунду — относительно того, что реально тянет узел.
            peak = profile["peak_pps"] if profile else 0
            pk = ws.cell(row=row, column=9, value=peak)
            if peak >= 7000:
                _mark(pk, _BAD_FILL)
            elif peak >= 4000:
                _mark(pk, _WARN_FILL)

            ex = ws.cell(row=row, column=10, value=exceeded)
            if exceeded >= 3:
                _mark(ex, _BAD_FILL)
            elif exceeded:
                _mark(ex, _WARN_FILL)
            ws.cell(row=row, column=11, value=window)
            ws.cell(row=row, column=12, value=dows)
            ws.cell(row=row, column=13,
                    value=dt_to_moscow(u["last_active_at"]).strftime("%d.%m.%Y %H:%M")
                    if u.get("last_active_at") else "нет данных")
            verdict = self._verdict(profile, u, exceeded)
            v = ws.cell(row=row, column=14, value=verdict)
            v.alignment = Alignment(wrap_text=True, vertical="top")
            # Красим сам вывод: строка с «торрентом» или превышениями должна
            # находиться взглядом, а не чтением всех тридцати строк.
            low = verdict.lower()
            if "торрент" in low or "превышений" in low:
                v.fill = _BAD_FILL
                v.font = Font(bold=True, color="FFFFFF")
            elif "раздачи" in low or "ночная" in low:
                v.fill = _WARN_FILL
                v.font = Font(bold=True, color="FFFFFF")
            row += 1

        # итоговая строка
        ws.cell(row=row, column=1, value="ИТОГО").font = Font(bold=True)
        ws.cell(row=row, column=5, value=round(total_out / 1024 ** 3, 2)).font = Font(bold=True)
        ws.cell(row=row, column=6, value=round(total_in / 1024 ** 3, 2)).font = Font(bold=True)
        ws.cell(row=row, column=14,
                value=f"Пользователей: {len(users)} · период: {days} дн.").font = Font(bold=True)
        for col in range(1, len(headers) + 1):
            ws.cell(row=row, column=col).fill = _TOT_FILL

        _style_sheet(ws)
        wb.save(path)
        return path

    async def export_logs_to_excel(self, path):
        users = await self.get_all_users()
        wb = Workbook()
        wb.remove(wb.active)

        if not users:
            ws = wb.create_sheet("Пусто")
            ws.append(["Нет пользователей"])
            wb.save(path)
            return path

        # Лист-сводка (общая картина по всем) — идёт первым, чтобы сразу видеть итоги
        summary = wb.create_sheet("Сводка")
        summary.append(["Пользователь", "Скачано, MB", "Отправлено, MB", "Всего, MB", "Точек"])
        for col, w in zip("ABCDE", (28, 16, 16, 16, 10)):
            summary.column_dimensions[col].width = w

        for u in users:
            safe_name = "".join([c for c in u['name'] if c.isalnum() or c == '_'])[:30]
            if not safe_name: safe_name = u['uuid'][:8]

            ws = wb.create_sheet(title=safe_name)
            ws.append(["Время МСК", "Скачано, MB", "Отправлено, MB", "Прирост, MB"])
            for col, w in zip("ABCD", (20, 16, 16, 16)):
                ws.column_dimensions[col].width = w

            query = "SELECT bytes_in, bytes_out, last_seen FROM stats WHERE user_uuid=$1 ORDER BY last_seen ASC"
            user_stats = await self.fetch_all(query, u['uuid'])

            prev_total = 0
            n_points = 0
            last_in = last_out = 0
            for row in user_stats:
                total_bytes = row['bytes_in'] + row['bytes_out']
                delta_bytes = total_bytes - prev_total
                if delta_bytes < 0: delta_bytes = total_bytes
                if prev_total == 0: delta_bytes = 0
                prev_total = total_bytes
                last_in, last_out = row['bytes_in'], row['bytes_out']
                n_points += 1

                ws.append([
                    dt_to_moscow(row['last_seen']).strftime("%Y-%m-%d %H:%M:%S"),
                    round(row['bytes_in'] / (1024 * 1024), 2),
                    round(row['bytes_out'] / (1024 * 1024), 2),
                    round(delta_bytes / (1024 * 1024), 2)
                ])

            # Итоговая строка по пользователю (выделена)
            tin = round(last_in / (1024 * 1024), 2)
            tout = round(last_out / (1024 * 1024), 2)
            tot_row = ws.max_row + 1
            ws.append(["ИТОГО", tin, tout, round(tin + tout, 2)])
            for cell in ws[tot_row]:
                cell.font = Font(bold=True)
                cell.fill = _TOT_FILL
            _style_sheet(ws)
            summary.append([u['name'], tin, tout, round(tin + tout, 2), n_points])

        _style_sheet(summary)
        wb.save(path)
        return path

db = Database()
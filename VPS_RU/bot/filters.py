# -*- coding: utf-8 -*-
"""Фильтрация сайтов по категориям: экраны и передача раскладки на узел.

Три вещи в проекте похожи, но решают разное, и путать их дорого:
  • split-tunnel — маршрут: что идёт мимо туннеля напрямую;
  • роли — доступ к домашним сервисам ВНУТРИ туннеля;
  • фильтры — что человеку не открывается в интернете.
Здесь именно третье.

Как это работает без перевыпуска конфигов: в выданных конфигах записан внешний DNS,
и менять их значило бы выдавать всем новые. Вместо этого узел заворачивает 53-й порт
на себя — и только для тех, у кого фильтры включены. Различать людей можно потому,
что в туннеле адрес пира и есть личность: WireGuard сверяет ключ с AllowedIPs.

Чего фильтр не умеет, и это надо говорить прямо: DNS-over-HTTPS в браузере идёт мимо.
Он рассчитан на обычную семейную историю, а не на того, кто целенаправленно обходит.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import exit_kb, escape_md, WG_API_URL, api_session, show_screen

# Адрес бота узел сам не знает: он живёт в сети, а не в Telegram. Бот сообщает
# его вместе с раскладкой фильтров, чтобы на странице отказа было куда написать.
BOT_LINK = {"url": ""}


def remember_bot_link(username):
    if username:
        BOT_LINK["url"] = f"https://t.me/{str(username).lstrip('@')}"

# Порядок важен: сверху то, что включают чаще всего.
CATEGORIES = [
    ("ads", "Реклама и трекеры"),
    ("adult", "Для взрослых"),
    ("gambling", "Азартные игры"),
    ("malware", "Вредоносное и фишинг"),
    ("social", "Соцсети"),
    ("torrent", "Торренты и пиратство"),
    ("crypto", "Криптовалюты и майнинг"),
    ("scam", "Мошенничество"),
    ("tracking", "Слежка и телеметрия"),
    ("drugs", "Наркотики и алкоголь"),
    ("games", "Игры"),
    ("streaming", "Видео и стриминг"),
    ("dating", "Знакомства"),
    ("ransomware", "Шифровальщики"),
]
TITLES = dict(CATEGORIES)


async def peer_ip_map():
    """uuid → адрес в туннеле. Узел знает людей только по адресам."""
    from acl import peer_ip_map as _map
    return await _map()


def parse_site(raw: str):
    """Достаёт домен из чего угодно: ссылки, адреса с www, просто имени.

    Возвращает (домен, ошибка). Домен приводится к нижнему регистру и без
    `www.`: списки хранятся именно так, а человек пишет как придётся."""
    import re

    text = (raw or "").strip().lower()
    if not text:
        return None, "Пустая строка"
    text = re.sub(r"^[a-z]+://", "", text)      # отрезаем протокол
    text = text.split("/")[0].split("?")[0]     # путь и параметры не нужны
    text = text.split("@")[-1]                  # на случай почтового вида
    text = text.strip(".")
    if text.startswith("www."):
        text = text[4:]
    if not re.match(r"^[a-z0-9а-яё-]+(\.[a-z0-9а-яё-]+)+$", text):
        return None, "Не похоже на адрес сайта. Пример: `example.com`"
    return text, None


async def peer_addr_map():
    """uuid → все адреса человека: пир AmneziaWG и двойник Xray, если он есть.
    Живёт здесь же, рядом с `peer_ip_map`, чтобы точка подмены была одна."""
    from acl import peer_addr_map as _map
    return await _map()


async def all_categories():
    """Что можно включить человеку: встроенные категории и свои пулы.

    Пул ведёт себя как категория во всём — включается, попадает под исключения,
    называется на странице отказа своим именем. Разница только в том, откуда
    взялся список.
    """
    own = []
    try:
        own = [(p["key"], p["title"]) for p in await db.list_filter_pools()]
    except Exception:
        own = []
    return list(CATEGORIES) + own


async def titles():
    """Название по ключу — и для встроенных, и для своих."""
    out = dict(TITLES)
    try:
        for pool in await db.list_filter_pools():
            out[pool["key"]] = pool["title"]
    except Exception:
        pass
    return out


async def apply_filters(reason: str = ""):
    """Отдаёт узлу готовую раскладку «адрес → категории».

    Считает бот: база есть только у него. Узел получает адреса и списки, заворачивает
    порт и подтягивает нужные списки доменов — только те, что кем-то включены."""
    try:
        by_uuid = await db.get_all_filters()
        ips = await peer_addr_map()
    except Exception as e:
        return False, f"не удалось собрать фильтры: {e}"

    clients = {}
    for uuid_val, cats in by_uuid.items():
        if not cats:
            continue
        # Оба адреса человека: фильтр должен работать и по AmneziaWG, и по Xray.
        for ip in ips.get(uuid_val, []):
            clients[ip] = cats

    try:
        common = await db.get_common_filters()
        custom = await db.get_custom_blocks()
    except Exception:
        common, custom = [], []

    # Исключения — вопреки категории. Личные привязаны к ключу, а узел знает
    # только адреса, поэтому здесь же переводим одно в другое.
    try:
        allow_common, allow_by_uuid = await db.get_all_filter_allow()
    except Exception:
        allow_common, allow_by_uuid = [], {}
    allow_clients = {}
    for uuid_val, domains in allow_by_uuid.items():
        for ip in ips.get(uuid_val, []):
            allow_clients[ip] = domains

    # Свои пулы едут вместе с раскладкой: узел кладёт их в тот же кэш, откуда
    # читает встроенные категории, и дальше не различает.
    try:
        pools = {p["key"]: p["domains"] for p in await db.list_filter_pools()}
    except Exception:
        pools = {}

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/dns/filters",
                                    json={"clients": clients,
                                          "common": common,
                                          "custom": custom,
                                          "allow_common": allow_common,
                                          "allow_clients": allow_clients,
                                          "pools": pools,
                                          "bot_link": BOT_LINK["url"]}, timeout=10) as resp:
                if resp.status != 200:
                    return False, f"узел отклонил фильтры: {await resp.text()}"
                data = await resp.json()
    except Exception as e:
        return False, f"узел недоступен: {e}"

    msg = f"Фильтры применены: под фильтром {data.get('filtered', 0)} чел."
    if allow_common or allow_clients:
        msg += (f" · исключений: {len(allow_common)} общих, "
                f"{sum(len(v) for v in allow_clients.values())} личных")
    if common:
        msg += f" · общих правил: {len(common)}"
    if custom:
        msg += f" · свой список: {len(custom)}"
    if reason:
        msg += f" ({reason})"
    try:
        await db.log_event("Filters", msg)
    except Exception:
        pass
    return True, msg


async def list_sizes():
    """Сколько доменов реально загружено по категориям — чтобы на экране было
    видно, работает фильтр или список ещё не подтянулся."""
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/dns/filters", timeout=5) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("lists", {})
    except Exception:
        pass
    return {}


async def filters_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    by_uuid = await db.get_all_filters()
    sizes = await list_sizes()

    common = await db.get_common_filters()
    custom = await db.get_custom_blocks()

    lines = ["🧹 **Фильтрация сайтов**", "",
             "_🚫 Запреты · 🟢 Исключения_", ""]
    if common or custom:
        parts = []
        if common:
            parts.append("категорий для всех: "
                         + ", ".join(TITLES.get(c, c) for c in common))
        if custom:
            parts.append(f"свой список: {len(custom)}")
        lines.append("🌍 **Общие правила** — " + "; ".join(parts))
        lines.append("")
    if not by_uuid:
        lines += ["Фильтры никому не включены — интернет у всех открыт полностью.",
                  "",
                  "Фильтр закрывает сайты по категориям и работает через свой DNS. "
                  "Перевыпускать конфиги не нужно: узел сам забирает запросы тех, "
                  "кому фильтр включён."]
    else:
        lines.append(f"Под фильтром: {len(by_uuid)} чел.")
        lines.append("")
        for uuid_val, cats in by_uuid.items():
            user = await db.get_user_by_uuid(uuid_val)
            name = escape_md((user or {}).get("name") or uuid_val[:8])
            titles = ", ".join(TITLES.get(c, c) for c in cats)
            lines.append(f"• **{name}** — {titles}")

    if sizes:
        lines += ["", "_Загружено доменов: "
                  + ", ".join(f"{TITLES.get(k, k)} — {v}" for k, v in sizes.items()) + "._"]

    lines += ["", "⚠️ _В браузере с DNS-over-HTTPS фильтр обходится: там запрос "
                  "уходит внутри HTTPS и на уровне DNS его не видно._"]

    kb = [[InlineKeyboardButton("🌍 Общие правила", callback_data="flt_common")],
          [InlineKeyboardButton("🟢 Исключения из запретов",
                                callback_data="flt_alw_all")],
          [InlineKeyboardButton("📦 Группы фильтров", callback_data="flt_pool_list")],
          [InlineKeyboardButton("👤 Выбрать человека", callback_data="flt_pick_0")]]
    if by_uuid:
        kb.append([InlineKeyboardButton("🔄 Применить на узле", callback_data="flt_apply")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)



# --- ИСКЛЮЧЕНИЯ ------------------------------------------------------------
# Категория закрывает пачку сайтов скопом, и почти всегда в этой пачке есть
# что-то нужное. Исключение разрешает такой сайт вопреки категории — всем или
# одному человеку. Проверяется раньше запретов, иначе смысла бы не имело.

async def allow_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       uuid_val=None):
    """Список исключений: общих или одного ключа."""
    query = update.callback_query
    rows = await db.list_filter_allow(uuid_val=uuid_val, common=uuid_val is None)

    if uuid_val:
        user = await db.get_user_by_uuid(uuid_val)
        who = escape_md((user or {}).get("name") or uuid_val[:8])
        head = f"🟢 **Исключения из запретов · {who}**"
        back = f"flt_user_{uuid_val}"
        add = f"flt_alw_add_{uuid_val}"
        scope = ("Эти сайты открыты **только этому ключу**, даже если категория "
                 "закрыта ему или всем.")
    else:
        head = "🟢 **Общие исключения из запретов**"
        back = "flt_common"
        add = "flt_alw_add_all"
        scope = ("Эти сайты открыты **всем**, даже если закрыта категория, "
                 "в которую они входят.")

    lines = [head, "", scope, ""]
    if not rows:
        lines.append("_Пока пусто._")
    else:
        for row in rows:
            lines.append(f"  🟢 `{escape_md(row['domain'])}`")
    lines += ["", "_Разрешение сильнее запрета, а личное сильнее общего: "
                  "правило про конкретного человека заведомо осознаннее._"]

    kb = [[InlineKeyboardButton("➕ Разрешить сайт", callback_data=add)]]
    for row in rows:
        kb.append([InlineKeyboardButton(f"🗑 {row['domain'][:28]}",
                                        callback_data=f"flt_alw_del_{row['id']}"
                                                      f"_{uuid_val or 'all'}")])
    kb.append([InlineKeyboardButton("🔙 Назад", callback_data=back)])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def allow_add_request(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            uuid_val=None):
    query = update.callback_query
    context.user_data["state"] = "awaiting_filter_allow"
    context.user_data["allow_uuid"] = uuid_val
    who = "всем" if not uuid_val else "этому ключу"
    await show_screen(
        query, context,
        f"➕ **Разрешить сайт {who}**\n\n"
        "Пришлите домен или несколько — по одному в строке:\n"
        "`vk.com`\n`work-chat.example`\n\n"
        "Поддомены попадают под правило сами: разрешили `vk.com` — откроется и "
        "`login.vk.com`, иначе сайт всё равно не заработает.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена",
                                   callback_data=(f"flt_alw_{uuid_val}" if uuid_val
                                                  else "flt_alw_all"))]]),
        parse_mode=ParseMode.MARKDOWN)


async def allow_add_entered(update, context):
    """Разбирает присланное. Возвращает True, если сообщение было для нас."""
    uuid_val = context.user_data.get("allow_uuid")
    context.user_data["state"] = None
    raw = (update.message.text or "").strip()

    added, bad = [], []
    for part in raw.replace(",", "\n").split("\n"):
        value = part.strip().lower()
        if not value:
            continue
        if "://" in value:
            value = value.split("://", 1)[1]
        value = value.split("/")[0].strip(".")
        if not value or " " in value or "." not in value:
            bad.append(part.strip()[:30])
            continue
        await db.add_filter_allow(value, uuid_val)
        added.append(value)

    back = f"flt_alw_{uuid_val}" if uuid_val else "flt_alw_all"
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🟢 К исключениям", callback_data=back)]])
    if not added:
        await context.bot.send_message(
            chat_id=update.message.chat_id, reply_markup=kb,
            text="⚠️ Ничего не разобрал. Нужен домен — например, `vk.com`.",
            parse_mode=ParseMode.MARKDOWN)
        return True

    ok, msg = await apply_filters("добавлено исключение")
    text = "🟢 Разрешено вопреки запрету: " + ", ".join(f"`{a}`" for a in added)
    if bad:
        text += "\n\n⚠️ Не понял: " + ", ".join(bad)
    text += "\n\n" + ("Применено на узле." if ok else f"⚠️ Узел: {msg}")
    await context.bot.send_message(chat_id=update.message.chat_id, text=text,
                                   reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    return True


async def allow_remove(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       allow_id, uuid_val=None):
    await db.delete_filter_allow(allow_id)
    await apply_filters("снято исключение")
    await update.callback_query.answer("Убрано")
    await allow_screen(update, context, uuid_val)


# --- ГРУППЫ ФИЛЬТРОВ -------------------------------------------------------------
# Готовые категории собраны чужими людьми по чужим соображениям: в них нет
# российских ресурсов и нет того, что владелец считает лишним именно у себя.
# Пул — это категория, собранная им самим: список доменов и название.

def _pool_key(title):
    """Короткий ключ из названия. По нему пул знают узел и база, поэтому только
    латиница и цифры: кириллицу в имени файла кэша узел бы не принял."""
    import hashlib
    slug = "".join(c for c in (title or "").lower()
                   if c.isalnum() and c.isascii())[:16]
    tail = hashlib.blake2b(title.encode(), digest_size=2).hexdigest()
    return ("pool_" + (slug + "_" if slug else "") + tail)[:40]


async def pool_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pools = await db.list_filter_pools()

    lines = ["📦 **Группы фильтров**", ""]
    if not pools:
        lines += [
            "Групп нет.",
            "",
            "Группа — это своя категория: даёте ей название, заливаете список "
            "адресов, и дальше она включается людям так же, как встроенные.",
            "",
            "_Пригодится там, где готовые списки не подходят: свои ресурсы, "
            "российские сервисы, «то, что не надо детям» по вашему разумению._",
        ]
    else:
        for pool in pools:
            lines.append(f"  📦 **{escape_md(pool['title'])}** — "
                         f"{len(pool['domains'])} доменов")

    kb = [[InlineKeyboardButton("➕ Добавить группу", callback_data="flt_pool_new")]]
    for pool in pools:
        kb.append([InlineKeyboardButton(f"📦 {pool['title'][:26]}",
                                        callback_data=f"flt_pool_o_{pool['key']}")])
    kb.append([InlineKeyboardButton("🔙 К фильтрам", callback_data="flt_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def pool_open(update: Update, context: ContextTypes.DEFAULT_TYPE, key):
    query = update.callback_query
    pool = await db.get_filter_pool(key)
    if not pool:
        await query.answer("Группы нет", show_alert=True)
        return await pool_list(update, context)

    shown = pool["domains"][:12]
    lines = [f"📦 **{escape_md(pool['title'])}**", "",
             f"Доменов: **{len(pool['domains'])}**", ""]
    lines += [f"  `{escape_md(d)}`" for d in shown]
    if len(pool["domains"]) > len(shown):
        lines.append(f"  …и ещё {len(pool['domains']) - len(shown)}")
    lines += ["", "_Включается человеку так же, как встроенная категория._"]

    kb = [[InlineKeyboardButton("➕ Добавить адреса",
                                callback_data=f"flt_pool_a_{key}")],
          [InlineKeyboardButton("🗑 Удалить группу", callback_data=f"flt_pool_d_{key}")],
          [InlineKeyboardButton("🔙 К группам", callback_data="flt_pool_list")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


# Подсказка про формат — одна на оба случая: и при создании группы, и при
# дописывании. Человек копирует адреса откуда попало, и ему надо сразу сказать,
# что приводить их к одному виду не нужно.
ASK_DOMAINS = (
    "Пришлите список **построчно** — по адресу в строке. Можно сразу сотни: "
    "выкачали перечень и вставили целиком.\n\n"
    "Вид значения не важен, всё это один и тот же сайт:\n"
    "`https://www.example.com/page`\n"
    "`www.example.com`\n"
    "`example.com`\n"
    "`0.0.0.0 example.com`\n\n"
    "_Схему, `www`, порт и путь срежу сам. Повторы уберу._")


async def pool_add_request(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           key=None):
    """Спрашивает адреса. Для новой группы это второй шаг: имя уже дали."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_pool_domains"
    context.user_data["pool_key"] = key

    if key:
        pool = await db.get_filter_pool(key)
        head = f"📦 **Адреса в группу «{escape_md((pool or {}).get('title', ''))}»**"
        back = f"flt_pool_o_{key}"
    else:
        head = "📦 **Адреса в новую группу**"
        back = "flt_pool_list"

    await show_screen(
        query, context, head + "\n\n" + ASK_DOMAINS,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data=back)]]),
        parse_mode=ParseMode.MARKDOWN)


async def pool_name_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Первый шаг новой группы — название.

    Раньше сначала просили список, а имя спрашивали после: человек вставлял
    три сотни строк и только тогда узнавал, что нужно ещё и назвать. Порядок
    развёрнут — сперва имя, оно короткое.
    """
    query = update.callback_query
    context.user_data["state"] = "awaiting_pool_title"
    context.user_data["pool_domains"] = []
    await show_screen(
        query, context,
        "📦 **Новая группа**\n\n"
        "Как её назвать? Название увидит человек на странице отказа — пишите "
        "так, чтобы ему было понятно: «Взрослое», «Игры», «Соцсети без ВК».\n\n"
        "_Адреса попрошу следующим шагом._",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="flt_pool_list")]]),
        parse_mode=ParseMode.MARKDOWN)


def _parse_domains(raw):
    """Приводит присланное к именам доменов.

    Люди копируют адреса откуда попало: `https://www.site.ru/page`, `www.site.ru`,
    `site.ru`, строка из hosts-файла. Это один и тот же домен, и различать их
    нельзя: правило по `www.site.ru` не закроет `site.ru`, и человек будет
    уверен, что фильтр не работает.

    Поэтому срезаем схему, `www`, порт, путь и точку на конце. Остаётся имя.
    """
    out = []
    for part in (raw or "").replace(",", "\n").replace(";", "\n").split("\n"):
        value = part.strip().lower()
        if not value or value.startswith("#"):
            continue

        chunks = value.split()
        if len(chunks) > 1 and chunks[0] in ("0.0.0.0", "127.0.0.1", "::1"):
            value = chunks[1]                    # строка из hosts-файла
        elif len(chunks) > 1:
            continue                             # фраза, а не адрес

        if "://" in value:
            value = value.split("://", 1)[1]     # http://, https://, любая схема
        value = value.split("/")[0]              # путь
        value = value.split("?")[0].split("#")[0]
        value = value.split("@")[-1]             # логин в адресе
        value = value.split(":")[0]              # порт
        value = value.strip(".")
        if value.startswith("www."):
            # `www` — не отдельный сайт. Оставить его значило бы завести
            # правило, которое не сработает на том же сайте без `www`.
            value = value[4:]

        if value and "." in value and " " not in value and len(value) <= 100:
            out.append(value)
    # Порядок не важен, а повторы в присланных списках бывают всегда.
    return sorted(set(out))


async def pool_domains_entered(update, context):
    """Принял список адресов в уже созданную группу."""
    key = context.user_data.get("pool_key")
    domains = _parse_domains(update.message.text or "")
    chat_id = update.message.chat_id

    if not domains:
        context.user_data["state"] = None
        await context.bot.send_message(
            chat_id=chat_id, text="⚠️ Ни одного домена не разобрал.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 К группам", callback_data="flt_pool_list")]]))
        return True

    if key:
        pool = await db.get_filter_pool(key)
        if not pool:
            context.user_data["state"] = None
            return True
        merged = sorted(set(pool["domains"]) | set(domains))
        await db.save_filter_pool(key, pool["title"], merged)
        context.user_data["state"] = None
        ok, msg = await apply_filters("дописан пул")
        await context.bot.send_message(
            chat_id=chat_id, parse_mode=ParseMode.MARKDOWN,
            text=(f"📦 В группу «{escape_md(pool['title'])}» добавлено "
                  f"**{len(merged) - len(pool['domains'])}** новых, всего "
                  f"**{len(merged)}**.\n\n"
                  + ("Применено на узле." if ok else f"⚠️ Узел: {msg}")),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📦 К группе",
                                       callback_data=f"flt_pool_o_{key}")]]))
        return True

    # Сюда можно попасть только без имени группы — значит, разговор потерян.
    context.user_data["state"] = None
    await context.bot.send_message(
        chat_id=chat_id,
        text="⚠️ Непонятно, в какую группу. Откройте её и нажмите "
             "«Добавить адреса».",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📦 К группам",
                                   callback_data="flt_pool_list")]]))
    return True

async def pool_title_entered(update, context):
    """Имя получено — группа заведена, осталось наполнить.

    Заводим сразу, ещё пустой: держать имя в памяти до конца разговора нельзя,
    разговор человек может и бросить.
    """
    title = (update.message.text or "").strip()[:40]
    context.user_data["state"] = None
    chat_id = update.message.chat_id

    if not title:
        await context.bot.send_message(
            chat_id=chat_id, text="⚠️ Пустое название — группа не создана.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📦 К группам",
                                       callback_data="flt_pool_list")]]))
        return True

    key = _pool_key(title)
    await db.save_filter_pool(key, title, [])
    context.user_data["state"] = "awaiting_pool_domains"
    context.user_data["pool_key"] = key
    await context.bot.send_message(
        chat_id=chat_id, parse_mode=ParseMode.MARKDOWN,
        text=("📦 Группа «%s» создана." % escape_md(title)
              + chr(10) + chr(10) + ASK_DOMAINS),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Позже",
                                   callback_data="flt_pool_o_" + key)]]))
    return True


async def pool_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, key):
    pool = await db.get_filter_pool(key)
    await db.delete_filter_pool(key)
    await apply_filters("удалена группа")
    await update.callback_query.answer(
        f"Пул «{(pool or {}).get('title', '')}» удалён" if pool else "Удалено")
    await pool_list(update, context)

async def pick_user(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    users = await db.get_all_users()
    by_uuid = await db.get_all_filters()
    per = 8
    total = max(1, (len(users) + per - 1) // per)
    page = max(0, min(page, total - 1))
    chunk = users[page * per:(page + 1) * per]

    kb = []
    for u in chunk:
        mark = "🧹 " if by_uuid.get(u["uuid"]) else ""
        kb.append([InlineKeyboardButton(f"{mark}{u['name']}",
                                        callback_data=f"flt_user_{u['uuid']}")])
    if total > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"flt_pick_{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="svc_noop"))
        if page < total - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"flt_pick_{page+1}"))
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Фильтры", callback_data="flt_menu")])

    await show_screen(query, context, "\U0001F464 **Выберите человека**\n\n"
                                  "Отмеченные значком уже под фильтром.",
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def user_filters_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              uuid_val: str):
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Ключ не найден")
        return await filters_menu(update, context)

    mine = set(await db.get_user_filters(uuid_val))
    lines = [f"🧹 **Фильтры: {escape_md(user['name'])}**", ""]
    if mine:
        lines.append(f"Запрещено категорий: **{len(mine)}** из {len(CATEGORIES)}.")
    else:
        lines.append("Запретов нет — интернет открыт полностью.")
    lines += ["", "Нажмите на категорию, чтобы запретить её. Нажмите ещё раз — "
                  "запрет снимется.",
              "", "_Закрытый сайт не просто не открывается: человек попадает "
                  "на страницу с объяснением._"]

    # 🚫 стоит у запрещённых. У остальных знака нет вовсе: пустая строка
    # читается как «ничего не делаем», а любой значок пришлось бы объяснять.
    kb = [[InlineKeyboardButton(("🚫 " if key in mine else "") + title,
                                callback_data=f"flt_set_{key}_{uuid_val}")]
          for key, title in await all_categories()]
    kb.append([InlineKeyboardButton("🔙 К человеку",
                                    callback_data=f"user_detail_{uuid_val}")])
    # Исключения — рядом с категориями: закрыл «соцсети», тут же оставил рабочий
    # чат. Разносить это по разным экранам значит ломать один жест на два.
    kb.append([InlineKeyboardButton("🟢 Исключения из запретов",
                                    callback_data=f"flt_alw_{uuid_val}")])
    kb.append([InlineKeyboardButton("🧹 К списку фильтров", callback_data="flt_pick_0")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def toggle_filter(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        uuid_val: str, category: str):
    mine = set(await db.get_user_filters(uuid_val))
    await db.set_user_filter(uuid_val, category, category not in mine)
    ok, msg = await apply_filters("изменение категорий")
    await update.callback_query.answer(msg if ok else msg, show_alert=not ok)
    await user_filters_screen(update, context, uuid_val)


async def apply_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, msg = await apply_filters("применение вручную")
    await update.callback_query.answer(msg, show_alert=True)
    await filters_menu(update, context)


# --- ОБЩИЕ ПРАВИЛА --------------------------------------------------------
async def common_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Правила, действующие сразу на всех.

    Отдельный экран, а не «выдать всем по очереди»: тридцать карточек руками —
    это не настройка, а работа, и она разъезжается при первом же новом ключе."""
    query = update.callback_query
    common = await db.get_common_filters()
    custom = await db.get_custom_blocks()

    lines = ["🌍 **Общие правила**", "",
             "Действуют на всех, кто ходит через узел, включая тех, кому "
             "личные фильтры не включали.", ""]
    if common:
        lines.append("Категории: " + ", ".join(TITLES.get(c, c) for c in common))
    else:
        lines.append("Категории не выбраны.")
    if custom:
        shown = ", ".join(f"`{d}`" for d in custom[:8])
        lines.append(f"Свой список ({len(custom)}): {shown}"
                     + ("…" if len(custom) > 8 else ""))
    else:
        lines.append("Свой список пуст.")

    kb = []
    for key, title in CATEGORIES:
        mark = "✅" if key in common else "⬜️"
        kb.append([InlineKeyboardButton(f"{mark} {title}",
                                        callback_data=f"flt_ctog_{key}")])
    kb.append([InlineKeyboardButton("➕ Закрыть сайт", callback_data="flt_cadd")])
    if custom:
        kb.append([InlineKeyboardButton("🚫 Свой список запретов",
                                        callback_data="flt_clist")])
    kb.append([InlineKeyboardButton("🔙 Фильтры", callback_data="flt_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def common_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    common = set(await db.get_common_filters())
    common.symmetric_difference_update({key})
    await db.set_common_filters(common)
    ok, msg = await apply_filters("общие правила")
    await update.callback_query.answer(msg if ok else f"Не вышло: {msg}",
                                       show_alert=not ok)
    await common_screen(update, context)


async def custom_add_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "awaiting_block_site"
    await show_screen(update.callback_query, context,
                      "➕ **Закрыть сайт**\n\nПришлите адрес: `example.com` или "
                      "ссылку целиком — разберу сам.\n\n"
                      "_Закроется и сам сайт, и его поддомены. Правило подействует "
                      "на всех._",
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("🔙 Общие правила",
                                                 callback_data="flt_common")]]),
                      parse_mode=ParseMode.MARKDOWN)


async def custom_add_entered(update: Update, context: ContextTypes.DEFAULT_TYPE, raw):
    chat_id = update.effective_chat.id
    domain, err = parse_site(raw)
    if err:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {err}",
                                       parse_mode=ParseMode.MARKDOWN,
        reply_markup=exit_kb(("🚫 Свои блокировки", "flt_custom")))
        return
    context.user_data["state"] = None
    await db.add_custom_block(domain)
    ok, msg = await apply_filters(f"закрыт сайт {domain}")
    await context.bot.send_message(
        chat_id=chat_id,
        text=(f"✅ `{domain}` закрыт для всех.\n\n{msg}" if ok else f"⚠️ {msg}"),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Общие правила", callback_data="flt_common")]]),
        parse_mode=ParseMode.MARKDOWN)


async def custom_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    """Свой список с кнопками снятия: закрыть сайт легко, снять — тоже."""
    query = update.callback_query
    items = await db.get_custom_blocks()
    per = 8
    chunk = items[page * per:(page + 1) * per]

    lines = ["🚫 **Свой список запретов**", "",
             f"Закрыто сайтов: {len(items)}. Нажмите, чтобы снять запрет."]
    kb = [[InlineKeyboardButton(f"🗑 {d}", callback_data=f"flt_cdel_{d}")]
          for d in chunk]
    nav = []
    if page:
        nav.append(InlineKeyboardButton("←", callback_data=f"flt_cpg_{page - 1}"))
    if (page + 1) * per < len(items):
        nav.append(InlineKeyboardButton("→", callback_data=f"flt_cpg_{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Общие правила", callback_data="flt_common")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def custom_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, domain: str):
    await db.remove_custom_block(domain)
    ok, msg = await apply_filters(f"снят запрет {domain}")
    await update.callback_query.answer(msg if ok else f"Не вышло: {msg}",
                                       show_alert=not ok)
    await custom_list(update, context)

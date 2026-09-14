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

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/dns/filters",
                                    json={"clients": clients,
                                          "common": common,
                                          "custom": custom,
                                          "bot_link": BOT_LINK["url"]}, timeout=10) as resp:
                if resp.status != 200:
                    return False, f"узел отклонил фильтры: {await resp.text()}"
                data = await resp.json()
    except Exception as e:
        return False, f"узел недоступен: {e}"

    msg = f"Фильтры применены: под фильтром {data.get('filtered', 0)} чел."
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

    lines = ["🧹 **Фильтрация сайтов**", ""]
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
          [InlineKeyboardButton("👤 Выбрать человека", callback_data="flt_pick_0")]]
    if by_uuid:
        kb.append([InlineKeyboardButton("🔄 Применить на узле", callback_data="flt_apply")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


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
        lines.append("Отмеченные категории для него закрыты.")
    else:
        lines.append("Фильтров нет — интернет открыт полностью.")
    lines += ["", "_Закрытый сайт не просто не открывается: человек попадает "
                  "на страницу с объяснением._"]

    kb = [[InlineKeyboardButton(("✅ " if key in mine else "➖ ") + title,
                                callback_data=f"flt_set_{key}_{uuid_val}")]
          for key, title in CATEGORIES]
    kb.append([InlineKeyboardButton("🔙 К человеку",
                                    callback_data=f"user_detail_{uuid_val}")])
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
        kb.append([InlineKeyboardButton("📋 Свой список", callback_data="flt_clist")])
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

    lines = ["📋 **Свой список**", "",
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

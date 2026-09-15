# -*- coding: utf-8 -*-
"""Попытки достучаться до закрытого: сбор с узла и разбор владельцем.

Фильтр работал молча: домен не открылся — и всё. Владелец узнавал об этом,
только если человек приходил жаловаться, а тот, кто ходит на закрытое, приходит
последним.

Узел пишет голый факт: когда, с какого адреса в туннеле, куда. Здесь факт
обрастает тем, что знает только бот: чей это ключ, как человека зовут, с какого
внешнего адреса он в этот момент подключался.

Разбор устроен как заявки, а не лента: посмотрел — отметил разобранным. Лента,
в которой всё вперемешку и ничего нельзя закрыть, перестаёт читаться на второй
неделе.
"""
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import WG_API_URL, api_session, escape_md, dt_to_moscow, show_screen

PER_PAGE = 8


async def collect_hits():
    """Забирает с узла новое и раскладывает по людям.

    Забираем по времени последней записи у себя: узел отдаёт историю целиком,
    а повторы отсекает сама база.
    """
    try:
        since = await db.last_filter_hit_ts()
    except Exception:
        since = 0

    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/dns/hits",
                                   params={"since": since}, timeout=10) as resp:
                if resp.status != 200:
                    return 0
                rows = (await resp.json()).get("hits") or []
    except Exception:
        return 0
    if not rows:
        return 0

    # Адрес в туннеле → человек. Карта одна на всю пачку: людей немного, а
    # запрашивать её на каждую запись значило бы долбить узел зря.
    try:
        from filters import peer_addr_map
        ips = await peer_addr_map()
    except Exception:
        ips = {}
    who = {}
    for uuid_val, addrs in (ips or {}).items():
        for addr in addrs:
            who[addr] = uuid_val

    names, publics = {}, {}
    added = 0
    for row in rows:
        ip = row.get("ip") or ""
        uuid_val = who.get(ip)
        name = None
        public = None
        if uuid_val:
            if uuid_val not in names:
                try:
                    user = await db.get_user_by_uuid(uuid_val)
                    names[uuid_val] = user["name"] if user else None
                except Exception:
                    names[uuid_val] = None
            name = names[uuid_val]
            # Внешний адрес — тот, что известен сейчас. Он меняется, и записать
            # его задним числом уже не выйдет: через неделю искать будет негде.
            if uuid_val not in publics:
                try:
                    seen = await db.get_user_ips(uuid_val)
                    publics[uuid_val] = seen[0]["ip"] if seen else None
                except Exception:
                    publics[uuid_val] = None
            public = publics[uuid_val]
        try:
            await db.add_filter_hit(
                datetime.utcfromtimestamp(int(row.get("ts") or 0)),
                uuid_val, name, ip, public,
                (row.get("domain") or "").lower(), row.get("category"),
                row.get("ref"))
            added += 1
        except Exception:
            pass
    return added


async def hits_loop(app):
    """Забираем раз в пять минут. Чаще незачем: разбирают такое не в реальном
    времени, а узел не должен отвечать на опросы вместо работы."""
    await asyncio.sleep(90)
    while True:
        try:
            await collect_hits()
        except Exception as e:
            print(f"Попытки на закрытое: {e}")
        await asyncio.sleep(300)


def _when(dt):
    return dt_to_moscow(dt).strftime("%d.%m %H:%M") if dt else "—"


async def hits_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    """Список заявок. Свежие сверху, неразобранные помечены."""
    query = update.callback_query
    await collect_hits()

    total = await db.count_filter_hits()
    fresh = await db.count_filter_hits(only_new=True)
    rows = await db.list_filter_hits(limit=PER_PAGE, offset=page * PER_PAGE)

    lines = ["🚨 **Инциденты**", ""]
    if not rows:
        lines += ["Пока никто никуда не стучался.", "",
                  "_Записываются обращения к доменам, которые закрыты фильтром "
                  "или доступами. Если фильтры никому не включены, здесь будет "
                  "пусто._"]
    else:
        lines.append(f"Всего: **{total}**, не разобрано: **{fresh}**")
        lines.append("")
        for row in rows:
            mark = "🔴" if not row["seen_at"] else "▫️"
            who = escape_md(row["name"] or "неизвестный ключ")
            lines.append(f"{mark} {_when(row['happened_at'])} · **{who}**")
            lines.append(f"     `{escape_md(row['domain'])}`"
                         + (f" · `{row['ref']}`" if row.get("ref") else ""))

    kb = []
    for row in rows:
        mark = "🔴" if not row["seen_at"] else "▫️"
        title = f"{mark} {_when(row['happened_at'])} · {(row['name'] or '?')[:14]}"
        kb.append([InlineKeyboardButton(title, callback_data=f"hit_open_{row['id']}")])

    nav = []
    if page:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"hit_pg_{page - 1}"))
    if (page + 1) * PER_PAGE < total:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"hit_pg_{page + 1}"))
    if nav:
        kb.append(nav)
    if fresh:
        kb.append([InlineKeyboardButton("✅ Отметить все разобранными",
                                        callback_data="hit_seen_all")])
    # Поиск по номеру — то, ради чего номер и показан человеку. Ставим рядом со
    # списком: сюда владелец приходит с номером в руках.
    kb.append([InlineKeyboardButton("🔎 Найти по номеру", callback_data="hit_find")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def hit_open(update: Update, context: ContextTypes.DEFAULT_TYPE, hit_id):
    """Одна заявка целиком — всё, что нужно для разбора, на одном экране."""
    query = update.callback_query
    row = await db.get_filter_hit(hit_id)
    if not row:
        await query.answer("Заявки нет", show_alert=True)
        return await hits_screen(update, context)

    await db.mark_filter_hit_seen(hit_id)

    lines = [
        "🚨 **Инцидент** `%s`" % (row.get("ref") or "без номера"), "",
        f"🕒 {_when(row['happened_at'])} (МСК)",
        f"👤 {escape_md(row['name'] or 'ключ не определён')}",
        f"🌐 Домен: `{escape_md(row['domain'])}`",
        f"🚦 Причина: {escape_md(row['category'] or 'доступы')}",
        "",
        f"📍 В туннеле: `{row['tunnel_ip'] or '—'}`",
        f"📡 Внешний адрес: `{row['public_ip'] or 'не записан'}`",
    ]
    if row["user_uuid"]:
        lines.append(f"🔑 Ключ: `{row['user_uuid']}`")
    else:
        lines += ["", "_Адрес в туннеле не сошёлся ни с одним ключом: пир могли "
                      "снять или перевыпустить после события._"]

    kb = []
    if row["user_uuid"]:
        kb.append([InlineKeyboardButton("🔑 Открыть ключ",
                                        callback_data=f"user_detail_{row['user_uuid']}")])
        kb.append([InlineKeyboardButton("🧹 Фильтры этого ключа",
                                        callback_data=f"flt_user_{row['user_uuid']}")])
    kb.append([InlineKeyboardButton("🔙 К списку", callback_data="hit_list")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)



async def hit_find_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просит номер. Он приходит от человека — с экрана, из переписки, вслух."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_hit_ref"
    await show_screen(
        query, context,
        "🔎 **Поиск по номеру**\n\n"
        "Пришлите номер инцидента — тот, что человек видел на странице:\n"
        "`9395-570A`\n\n"
        "_Регистр и дефис не важны: перепишут как получится._",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="hit_list")]]),
        parse_mode=ParseMode.MARKDOWN)


async def hit_find_entered(update, context):
    """Разбирает присланный номер и открывает инцидент."""
    context.user_data["state"] = None
    raw = (update.message.text or "").strip()
    chat_id = update.message.chat_id

    row = None
    try:
        row = await db.find_filter_hit(raw)
    except Exception as e:
        print(f"Поиск инцидента: {e}")

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚨 К инцидентам", callback_data="hit_list")]])
    if not row:
        await context.bot.send_message(
            chat_id=chat_id, reply_markup=kb, parse_mode=ParseMode.MARKDOWN,
            text=(f"Ничего не нашлось по `{escape_md(raw[:24])}`.\n\n"
                  "Такое бывает, если номер переписали с ошибкой или запись уже "
                  "вытеснена — журнал на узле хранит недавнее, а не всю "
                  "историю."))
        return True

    lines = [
        "🚨 **Инцидент** `%s`" % (row.get("ref") or "без номера"), "",
        f"🕒 {_when(row['happened_at'])} (МСК)",
        f"👤 {escape_md(row['name'] or 'ключ не определён')}",
        f"🌐 Домен: `{escape_md(row['domain'])}`",
        f"🚦 Причина: {escape_md(row['category'] or 'доступы')}",
        "",
        f"📍 В туннеле: `{row['tunnel_ip'] or '—'}`",
        f"📡 Внешний адрес: `{row['public_ip'] or 'не записан'}`",
    ]
    buttons = []
    if row.get("user_uuid"):
        lines.append(f"🔑 Ключ: `{row['user_uuid']}`")
        buttons.append([InlineKeyboardButton(
            "🔑 Открыть ключ", callback_data=f"user_detail_{row['user_uuid']}")])
        buttons.append([InlineKeyboardButton(
            "🧹 Фильтры этого ключа", callback_data=f"flt_user_{row['user_uuid']}")])
    buttons.append([InlineKeyboardButton("🚨 К инцидентам", callback_data="hit_list")])

    try:
        await db.mark_filter_hit_seen(row["id"])
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text="\n".join(lines),
                                   reply_markup=InlineKeyboardMarkup(buttons),
                                   parse_mode=ParseMode.MARKDOWN)
    return True

async def hits_seen_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.mark_all_filter_hits_seen()
    await update.callback_query.answer("Отмечено")
    await hits_screen(update, context)

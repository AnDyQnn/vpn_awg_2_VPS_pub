# -*- coding: utf-8 -*-
"""Экраны имён внутри туннеля.

Правило экранов то же, что и везде: за кнопкой видно, что именно произойдёт.
Поэтому в списке рядом с именем написано не только «куда», но и «к кому» —
имя, привязанное к человеку, переживает смену адреса, а привязанное к цифрам
живёт ровно до тех пор, пока цифры не изменились.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import dnsnames as dn
from database import db
from utils import escape_md, show_screen

PER_PAGE = 8


def _target_line(row):
    if row["name"] == dn.NODE_NAME:
        return "→ страница отказа на узле (служебное)"
    if row["target_uuid"]:
        who = escape_md(row["person"] or "человек удалён")
        return f"→ {who} (адрес подставляется сам)"
    return f"→ `{row['target_ip']}`"


async def names_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rows = await db.list_dns_names()

    lines = ["🏷 **Имена внутри туннеля**", ""]
    if not rows:
        lines += [
            "Имён пока нет. Их можно придумывать свободно: внутри VPN "
            f"имена раздаём мы сами, в интернете их не существует.",
            "",
            f"Заведёте «дом» — получится `дом.{dn.ZONE}`, и по нему будут "
            "открываться ваши сервисы вместо адреса с цифрами.",
        ]
    else:
        for row in rows[:PER_PAGE]:
            lines.append(f"  `{row['name']}` {_target_line(row)}")
        if len(rows) > PER_PAGE:
            lines.append(f"  …и ещё {len(rows) - PER_PAGE}")
        lines += ["", "_Имя, привязанное к человеку, переживает перевыпуск "
                      "ключа и переезд: адрес подставляется живым._"]

    kb = [[InlineKeyboardButton("➕ Завести имя", callback_data="dnm_add")]]
    for row in rows[:PER_PAGE]:
        kb.append([InlineKeyboardButton(f"🏷 {row['name']}",
                                        callback_data=f"dnm_open_{row['name']}")])
    kb.append([InlineKeyboardButton("🔄 Применить заново", callback_data="dnm_apply")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def add_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["state"] = "awaiting_dns_name"
    await show_screen(query, context,
                      "🏷 **Новое имя**\n\nНапишите одно слово — например, `дом` "
                      f"или `kino`. Зона `.{dn.ZONE}` добавится сама.\n\n"
                      "_Русские буквы можно: до сети они доедут как надо._",
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("🔙 Отмена", callback_data="dnm_menu")]]),
                      parse_mode=ParseMode.MARKDOWN)


async def name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE, raw):
    """Имя введено — спрашиваем, на кого оно ведёт."""
    name, err = dn.normalize(raw)
    chat_id = update.effective_chat.id
    if err:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {err}")
        return
    if await db.get_dns_name(name):
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Имя `{name}` уже занято. Откройте его в списке, чтобы "
                 f"переназначить или удалить.", parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data["state"] = None
    context.user_data["dns_new_name"] = name
    await _target_picker(context, chat_id, name)


async def _target_picker(context, chat_id, name, page=0):
    users = await db.get_all_users()
    users = sorted(users, key=lambda u: (u.get("name") or "").lower())
    start = page * PER_PAGE
    chunk = users[start:start + PER_PAGE]

    kb = [[InlineKeyboardButton(f"👤 {u['name']}",
                                callback_data=f"dnm_to_{u['uuid']}")] for u in chunk]
    nav = []
    if page:
        nav.append(InlineKeyboardButton("←", callback_data=f"dnm_pg_{page - 1}"))
    if start + PER_PAGE < len(users):
        nav.append(InlineKeyboardButton("→", callback_data=f"dnm_pg_{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔢 Указать адрес вручную", callback_data="dnm_manual")])
    kb.append([InlineKeyboardButton("🔙 Отмена", callback_data="dnm_menu")])

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🏷 `{name}`\n\nНа кого будет вести это имя?\n\n"
             "_Человек — обычный случай: адрес подставится сам и переживёт "
             "перевыпуск ключа. Адрес вручную — для того, что пиром не является: "
             "сам узел, железка за роутером._",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def target_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page):
    name = context.user_data.get("dns_new_name")
    if not name:
        return await names_menu(update, context)
    await update.callback_query.answer()
    await _target_picker(context, update.effective_chat.id, name, page)


async def target_person(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    name = context.user_data.get("dns_new_name")
    if not name:
        return await names_menu(update, context)
    await db.set_dns_name(name, target_uuid=uuid_val)
    context.user_data["dns_new_name"] = None
    ok, msg = await dn.apply_names("заведено имя")
    await update.callback_query.answer(msg if ok else f"Не вышло: {msg}", show_alert=not ok)
    await names_menu(update, context)


async def manual_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("dns_new_name")
    if not name:
        return await names_menu(update, context)
    context.user_data["state"] = "awaiting_dns_ip"
    await update.callback_query.answer()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🏷 `{name}`\n\nНапишите адрес в туннеле — например, `10.13.13.5`.",
        parse_mode=ParseMode.MARKDOWN)


async def manual_entered(update: Update, context: ContextTypes.DEFAULT_TYPE, raw):
    import ipaddress
    name = context.user_data.get("dns_new_name")
    chat_id = update.effective_chat.id
    if not name:
        return
    try:
        ip = str(ipaddress.IPv4Address((raw or "").strip()))
    except Exception:
        await context.bot.send_message(chat_id=chat_id,
                                       text="⚠️ Это не похоже на адрес. Пример: `10.13.13.5`",
                                       parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data["state"] = None
    context.user_data["dns_new_name"] = None
    await db.set_dns_name(name, target_ip=ip)
    ok, msg = await dn.apply_names("заведено имя")
    await context.bot.send_message(chat_id=chat_id,
                                   text=(f"✅ `{name}` → `{ip}`\n\n{msg}" if ok
                                         else f"⚠️ {msg}"),
                                   parse_mode=ParseMode.MARKDOWN)


async def name_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, name):
    query = update.callback_query
    row = await db.get_dns_name(name)
    if not row:
        return await names_menu(update, context)
    full = await db.list_dns_names()
    row = next((r for r in full if r["name"] == name), row)

    table, _ = await dn.resolve_all()
    now = table.get(name)

    lines = [f"🏷 **{escape_md(name)}**", "",
             _target_line(row),
             f"Сейчас отвечает: `{now}`" if now
             else "_Сейчас не отвечает: у цели нет адреса в туннеле._"]

    kb = [[InlineKeyboardButton("✏️ Переименовать", callback_data=f"dnm_ren_{name}")],
          [InlineKeyboardButton("🎯 Сменить цель", callback_data=f"dnm_re_{name}")],
          [InlineKeyboardButton("🗑 Удалить имя", callback_data=f"dnm_del_{name}")],
          [InlineKeyboardButton("🔙 К именам", callback_data="dnm_menu")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def rename_request(update: Update, context: ContextTypes.DEFAULT_TYPE, name):
    context.user_data["state"] = "awaiting_dns_rename"
    context.user_data["dns_old_name"] = name
    await show_screen(update.callback_query, context,
                      f"✏️ **Переименовать `{name}`**\n\nНапишите новое слово. "
                      f"Цель останется прежней.",
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("🔙 Отмена",
                                                 callback_data=f"dnm_open_{name}")]]),
                      parse_mode=ParseMode.MARKDOWN)


async def rename_entered(update: Update, context: ContextTypes.DEFAULT_TYPE, raw):
    old = context.user_data.get("dns_old_name")
    chat_id = update.effective_chat.id
    if not old:
        return
    new, err = dn.normalize(raw)
    if err:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {err}")
        return
    if await db.get_dns_name(new):
        await context.bot.send_message(chat_id=chat_id,
                                       text=f"⚠️ Имя `{new}` уже занято.",
                                       parse_mode=ParseMode.MARKDOWN)
        return
    context.user_data["state"] = None
    context.user_data["dns_old_name"] = None
    await db.rename_dns_name(old, new)
    ok, msg = await dn.apply_names("переименование")
    await context.bot.send_message(
        chat_id=chat_id,
        text=(f"✅ `{old}` теперь `{new}`\n\n{msg}" if ok else f"⚠️ {msg}"),
        parse_mode=ParseMode.MARKDOWN)


async def retarget_request(update: Update, context: ContextTypes.DEFAULT_TYPE, name):
    context.user_data["dns_new_name"] = name
    await update.callback_query.answer()
    await _target_picker(context, update.effective_chat.id, name)


async def delete_name(update: Update, context: ContextTypes.DEFAULT_TYPE, name):
    await db.delete_dns_name(name)
    ok, msg = await dn.apply_names("удаление имени")
    await update.callback_query.answer(msg if ok else f"Не вышло: {msg}", show_alert=not ok)
    await names_menu(update, context)


async def apply_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Применяю…")
    ok, msg = await dn.apply_names("вручную")
    await query.answer(msg, show_alert=not ok)
    await names_menu(update, context)

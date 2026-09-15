# -*- coding: utf-8 -*-
"""Свои исключения на конкретный ключ.

Общий список — про то, что у всех: российские сервисы, которым нужен
российский адрес. Но бывает ситуационное: рабочая подсеть на компе, домашний
сервис на своей машине, конкретный сайт на телефоне. В общий список такое
класть нельзя — оно касается одного устройства, а приедет всем.

Ключ здесь и есть устройство, поэтому запись висит на ключе. Приложение
получает один профиль: общий список плюс личные записи этого ключа. Двух не
делаем намеренно — активным всё равно бывает только один.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import happ_routing
from database import db
from utils import show_screen, escape_md

ASK = ("➕ **{title}**\n\n"
       "Пришлите адрес сети или имя сайта — по одному в строке, можно "
       "несколько сразу:\n"
       "`10.50.0.0/16`\n"
       "`vcenter.work.local`\n\n"
       "{note}")

NOTE_DIRECT = ("Это пойдёт **мимо VPN**, напрямую с устройства. Так делают для "
               "рабочих сетей и всего, что должно видеть настоящий адрес.")
NOTE_PROXY = ("Это пойдёт **через VPN**, даже если общий список отправляет его "
              "мимо. Так делают для исключений из исключений.")


def _line(row):
    arrow = "↩️" if row["direction"] == "direct" else "🔒"
    return f"{arrow} `{escape_md(row['value'])}`"


async def routes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Что настроено лично на этом ключе."""
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Ключ не найден", show_alert=True)
        return
    rows = await db.list_peer_routes(uuid_val)
    info = await happ_routing.summary(uuid_val)

    lines = [f"🌐 **Свои исключения · {escape_md(user['name'])}**", ""]
    if not rows:
        lines += [
            "Личных записей нет — на этом ключе работает только общий список.",
            "",
            f"В нём сейчас доменов {info['domains']}, сетей {info['nets']} "
            f"плюс домашние сети.",
            "",
            "_Личные записи нужны для ситуационного: рабочая подсеть, "
            "домашний сервис, конкретный сайт на одном устройстве._",
        ]
    else:
        direct = [r for r in rows if r["direction"] == "direct"]
        proxy = [r for r in rows if r["direction"] == "proxy"]
        if direct:
            lines.append("**Мимо VPN:**")
            lines += ["  " + _line(r) for r in direct]
        if proxy:
            if direct:
                lines.append("")
            lines.append("**Через VPN:**")
            lines += ["  " + _line(r) for r in proxy]
        lines += ["", "_Едет вместе с общим списком, одним профилем. "
                      "Доезжает при следующем обновлении подписки._"]

    kb = [[InlineKeyboardButton("➕ Мимо VPN", callback_data=f"rt_add_d_{uuid_val}"),
           InlineKeyboardButton("➕ Через VPN", callback_data=f"rt_add_p_{uuid_val}")]]
    for row in rows:
        kb.append([InlineKeyboardButton(f"🗑 {row['value'][:28]}",
                                        callback_data=f"rt_del_{row['id']}_{uuid_val}")])
    if rows:
        kb.append([InlineKeyboardButton("📱 Профиль этого ключа",
                                        callback_data=f"rt_show_{uuid_val}")])
    kb.append([InlineKeyboardButton("🔙 К ключу",
                                    callback_data=f"user_detail_{uuid_val}")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def routes_ask(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     direction, uuid_val):
    query = update.callback_query
    context.user_data["state"] = "awaiting_route_add"
    context.user_data["route_uuid"] = uuid_val
    context.user_data["route_dir"] = direction
    title = "Мимо VPN" if direction == "direct" else "Через VPN"
    note = NOTE_DIRECT if direction == "direct" else NOTE_PROXY
    kb = [[InlineKeyboardButton("✖️ Отмена", callback_data=f"rt_menu_{uuid_val}")]]
    await show_screen(query, context, ASK.format(title=title, note=note),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def routes_delete(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        route_id, uuid_val):
    await db.delete_peer_route(route_id)
    await db.log_event("Маршруты", f"Своё исключение снято ({uuid_val})")
    await update.callback_query.answer("Убрано")
    await routes_menu(update, context, uuid_val)


async def routes_show(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Готовый профиль этого ключа — чтобы проверить или отдать скрипту."""
    query = update.callback_query
    await query.answer()
    link = await happ_routing.link(uuid_val=uuid_val)
    info = await happ_routing.summary(uuid_val)
    sub = ""
    try:
        import xray
        rec = await db.get_xray_user(uuid_val)
        if rec:
            base = await xray.subscription_base()
            sub = f"{base}/routing/{rec['sub_token']}"
    except Exception:
        sub = ""

    lines = [
        "📱 **Профиль этого ключа**", "",
        f"Мимо туннеля: доменов **{info['domains']}**, сетей **{info['nets']}** "
        f"плюс {info['always']} домашних и служебных.",
        "",
        "Людям он уезжает подпиской сам. Ссылка ниже — тот же профиль, "
        "нажмите, чтобы скопировать:",
        f"`{link}`",
    ]
    if sub:
        lines += [
            "",
            "Скрипту нужен не она, а сам JSON — он лежит по адресу внутри "
            "туннеля:",
            f"`{sub}`",
            "",
            "_Тот же личный токен, что и у подписки: второй секрет с той же "
            "силой заводить незачем._",
        ]
    kb = [[InlineKeyboardButton("🔙 К исключениям",
                                callback_data=f"rt_menu_{uuid_val}")]]
    await query.edit_message_text("\n".join(lines),
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  disable_web_page_preview=True)


async def handle_route_input(update, context):
    """Разбирает присланное: по записи в строке, пустые пропускаем."""
    uuid_val = context.user_data.get("route_uuid")
    direction = context.user_data.get("route_dir") or "direct"
    context.user_data["state"] = None
    if not uuid_val:
        return False

    raw = (update.message.text or "").strip()
    added, bad = [], []
    for part in raw.replace(",", "\n").split("\n"):
        value = part.strip()
        if not value:
            continue
        # Ссылку человек присылает целиком, а нужно только имя.
        if "://" in value:
            value = value.split("://", 1)[1]
        value = value.split("/")[0] if ("/" in value and "." in value.split("/")[0]
                                        and not value.split("/")[-1].isdigit()) else value
        if len(value) > 100 or " " in value:
            bad.append(value[:30])
            continue
        await db.add_peer_route(uuid_val, value, direction)
        added.append(value)

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🌐 К исключениям", callback_data=f"rt_menu_{uuid_val}")]])
    if not added:
        await context.bot.send_message(
            chat_id=update.message.chat_id, reply_markup=kb,
            text="⚠️ Ничего не разобрал. Нужен адрес сети или имя сайта.")
        return True

    where = "мимо VPN" if direction == "direct" else "через VPN"
    text = f"✅ Добавлено {where}: " + ", ".join(f"`{a}`" for a in added)
    if bad:
        text += "\n\n⚠️ Не понял: " + ", ".join(bad)
    text += "\n\nДоедет до устройства при следующем обновлении подписки."
    await context.bot.send_message(chat_id=update.message.chat_id, text=text,
                                   reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await db.log_event("Маршруты", f"Свои исключения: +{len(added)} ({uuid_val})")
    return True

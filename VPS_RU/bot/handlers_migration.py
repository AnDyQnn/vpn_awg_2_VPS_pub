# -*- coding: utf-8 -*-
"""Экраны переезда на новый ключ сервера.

Устройство экранов подчинено одному правилу: ничего необратимого без явного
нажатия и без показанных последствий. Поэтому «Завершить» сначала показывает
список отстающих и прямо пишет, что с ними будет, и только потом даёт кнопку.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import migration as mg
from database import db
from utils import escape_md, show_screen


async def migration_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    st = await mg.status()

    if st.get("error"):
        await show_screen(query, context, 
            f"🔑 **Переезд на новый ключ**\n\nУзел не ответил: `{escape_md(st['error'])}`",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]]),
            parse_mode=ParseMode.MARKDOWN)
        return

    lines = ["🔑 **Переезд на новый ключ сервера**", ""]
    if not st.get("active"):
        lines += [
            "Сейчас все работают на исходном ключе.",
            "",
            "Переезд поднимает **второй интерфейс** на другом порту — со своим "
            "ключом и усиленной обфускацией. Люди переезжают по одному, старый "
            "интерфейс всё это время работает. Ничего не отключится само.",
            "",
            "Человеку не нужно заводить ключ заново: меняется ключ сервера, "
            "а его собственный ключ и адрес остаются прежними.",
        ]
        kb = [[InlineKeyboardButton("▶️ Поднять второй интерфейс",
                                    callback_data="mig_start")],
              [InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]]
    else:
        lag = await mg.laggards()
        lines += [
            f"Второй интерфейс поднят на порту `{st.get('port')}`.",
            f"Выдано новых конфигов: **{st.get('issued', 0)}**",
            f"Уже подключились на новом: **{st.get('connected', 0)}**",
            f"Осталось на старом: **{len(lag)}**",
        ]
        if lag:
            lines.append("")
            lines.append("Ещё не переехали: " +
                         escape_md(", ".join(l["name"] for l in lag[:12])) +
                         ("…" if len(lag) > 12 else ""))
        lines += ["", "_«Переехал» считается по живому рукопожатию на новом "
                      "интерфейсе, а не по факту выдачи конфига._"]
        de_moved = st.get("de_iface") == "wg1" if "de_iface" in st else False
        kb = [[InlineKeyboardButton(
                   ("✅ Клиент-сервер переехал" if de_moved
                    else "🌍 Перевести клиент-сервер"),
                   callback_data="mig_de")],
              [InlineKeyboardButton("📨 Выдать новые конфиги", callback_data="mig_issue_0")],
              [InlineKeyboardButton("🏁 Завершить переезд", callback_data="mig_finish")],
              [InlineKeyboardButton("✖️ Отменить переезд", callback_data="mig_abort")],
              [InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]]

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def migration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Поднимаю интерфейс…")
    ok, data = await mg.start()
    if not ok:
        await show_screen(query, context, 
            f"⚠️ Не получилось: `{escape_md(str(data))}`",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="mig_menu")]]),
            parse_mode=ParseMode.MARKDOWN)
        return
    await migration_menu(update, context)


async def migration_issue(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          page: int = 0):
    """Список тех, кому ещё не выдали новый конфиг. По одному, а не всем разом:
    рассылка тридцати файлов подряд — верный способ, чтобы половина потерялась."""
    query = update.callback_query
    st = await mg.status()
    if not st.get("active"):
        return await migration_menu(update, context)

    lag = await mg.laggards()
    per = 8
    total = max(1, (len(lag) + per - 1) // per)
    page = max(0, min(page, total - 1))
    chunk = lag[page * per:(page + 1) * per]

    kb = [[InlineKeyboardButton(f"📨 {l['name']}",
                                callback_data=f"mig_send_{l['uuid']}")] for l in chunk]
    if total > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"mig_issue_{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="svc_noop"))
        if page < total - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"mig_issue_{page+1}"))
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Переезд", callback_data="mig_menu")])

    text = ("📨 **Кому выдать новый конфиг**\n\n"
            "Старый ключ продолжит работать, пока человек не поставит новый.")
    if not chunk:
        text = "Все переехали — можно завершать."
    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def migration_send(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    await query.answer("Готовлю конфиг…")
    st = await mg.status()
    if not st.get("active"):
        return await migration_menu(update, context)

    conf, qr = await mg.issue_for(uuid_val, st["pubkey"], st["port"],
                                  st.get("obfuscation", {}))
    if not conf:
        await query.answer(f"Не вышло: {qr}", show_alert=True)
        return

    user = await db.get_user_by_uuid(uuid_val)
    sent_to = []
    from delivery import track_send
    for tid in (user.get("tg_ids") or []):
        async def _send(tid=tid):
            await context.bot.send_message(
                chat_id=tid,
                text=("🔑 **Новый конфиг для вашего ключа**\n\n"
                      "Мы меняем ключ сервера. Поставьте этот конфиг вместо старого — "
                      "он заменяет прежний профиль в приложении.\n\n"
                      "**Старый пока работает**, так что можно не торопиться: "
                      "поставьте, когда будет удобно."),
                parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_document(chat_id=tid, document=open(conf, "rb"),
                                            caption=f"📄 {user['name']}")
            await context.bot.send_photo(chat_id=tid, photo=open(qr, "rb"))

        ok, err = await track_send(uuid_val, tid, _send)
        sent_to.append(f"{tid}: {'отправлено' if ok else err}")

    if not sent_to:
        with open(conf, "rb") as f:
            await context.bot.send_document(chat_id=query.message.chat_id, document=f,
                                            caption=f"📄 {user['name']} — Telegram не привязан")
    await query.answer("Конфиг выдан")
    await migration_issue(update, context)


async def migration_de(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перевод клиент-сервера. Делается ПЕРВЫМ: пока он на старом интерфейсе,
    завершать переезд нельзя — вместе со старым интерфейсом умрёт и выход
    в интернет для всех, кто уже переехал."""
    query = update.callback_query
    await query.answer("Перевожу клиент-сервер, это до минуты…")
    ok, msg = await mg.move_de()
    await query.answer(msg, show_alert=True)
    await migration_menu(update, context)


async def migration_finish_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lag = await mg.laggards()
    st = await mg.status()
    lines = ["🏁 **Завершить переезд?**", ""]
    if st.get("de_iface") != "wg1":
        lines += ["⛔ **Сначала переведите клиент-сервер.**", "",
                  "Он тоже пир старого интерфейса. Если остановить старый сейчас, "
                  "выход в интернет пропадёт у всех — включая тех, кто уже переехал.",
                  ""]
        kb = [[InlineKeyboardButton("🌍 Перевести клиент-сервер", callback_data="mig_de")],
              [InlineKeyboardButton("🔙 Назад", callback_data="mig_menu")]]
        await show_screen(query, context, "\n".join(lines),
                                      reply_markup=InlineKeyboardMarkup(kb),
                                      parse_mode=ParseMode.MARKDOWN)
        return
    if lag:
        lines.append(f"**{len(lag)} чел. ещё не переехали**: "
                     + escape_md(", ".join(l["name"] for l in lag[:12]))
                     + ("…" if len(lag) > 12 else ""))
        lines.append("")
        lines.append("Если завершить сейчас, у них **пропадёт связь**, пока они не "
                     "поставят новый конфиг. Конфиги им уже выданы или ещё нет — "
                     "видно на экране выдачи.")
    else:
        lines.append("Все переехали: на старом интерфейсе никого не осталось.")
    lines += ["", "Старый интерфейс будет остановлен. Отменить это нельзя — "
                  "обратно он поднимется только руками."]

    kb = [[InlineKeyboardButton("🏁 Да, остановить старый", callback_data="mig_finish_ok")],
          [InlineKeyboardButton("✖️ Отмена", callback_data="mig_menu")]]
    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def migration_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, msg = await mg.finish()
    await update.callback_query.answer(msg, show_alert=True)
    await migration_menu(update, context)


async def migration_abort_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("✖️ Да, отменить переезд", callback_data="mig_abort_ok")],
          [InlineKeyboardButton("🔙 Назад", callback_data="mig_menu")]]
    await show_screen(update.callback_query, context, 
        "✖️ **Отменить переезд?**\n\n"
        "Второй интерфейс будет снят. Старый не пострадает — он и так всё это "
        "время работал. Те, кто уже поставил новый конфиг, вернутся на старый "
        "сами: их прежний профиль в приложении заменён, поэтому им нужно будет "
        "выдать конфиг заново.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def migration_abort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, msg = await mg.abort()
    await update.callback_query.answer(msg, show_alert=True)
    await migration_menu(update, context)

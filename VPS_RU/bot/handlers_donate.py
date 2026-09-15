# -*- coding: utf-8 -*-
"""Экраны поддержки проекта: настройка у владельца, просьба у людей.

Правило то же, что и на остальных экранах: за кнопкой видно, что произойдёт.
Поэтому в списке реквизитов сразу написано, что именно человек увидит, — а не
«карта №3». И поэтому же у владельца есть предпросмотр: текст про деньги
читается иначе, чем пишется, и увидеть его чужими глазами надо до того, как он
уйдёт к людям.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import donate
from database import db
from utils import show_screen, escape_md

# Подсказки на ввод. Держим рядом: владелец читает их один раз, а ошибка в
# реквизитах стоит дороже любой другой опечатки в этом боте.
ASK_CARD = ("💳 **Номер карты**\n\n"
            "Пришлите одним сообщением банк и номер через запятую:\n"
            "`Сбербанк, 2202 2020 1111 2222`\n\n"
            "Можно добавить подпись третьей частью — например, на чьё имя:\n"
            "`Сбербанк, 2202 2020 1111 2222, Андрей П.`")

ASK_PHONE = ("📱 **Телефон для СБП**\n\n"
             "Пришлите одним сообщением банк и номер через запятую:\n"
             "`Т-Банк, +7 900 000-00-00`\n\n"
             "Третьей частью можно добавить подпись — например, имя получателя.")

ASK_QR = ("🖼 **Картинка с QR**\n\n"
          "Пришлите саму картинку — ту, что показывает банковское приложение "
          "при оплате по QR.\n\n"
          "Бот запомнит её и будет пересылать людям. Файл никуда класть не "
          "нужно.")

ASK_DAYS = ("⏱ **Свой срок**\n\n"
            "Пришлите число дней одним сообщением — например, `21`.\n\n"
            "Меньше суток нельзя, больше года бессмысленно: это уже не "
            "напоминание, а выключенное напоминание.")

ASK_TEXT = ("✍️ **Текст обращения**\n\n"
            "Пришлите новый текст одним сообщением. Реквизиты подставятся под "
            "ним сами — их писать не надо.\n\n"
            "Что стоит оставить в любом варианте: доступ от перевода не "
            "зависит, и реквизиты бывают только в боте. Первое отличает "
            "просьбу от условия, второе однажды спасёт кого-нибудь от "
            "мошенника.")


def _label(row):
    """Подпись кнопки: по ней должно быть понятно, какой это реквизит,
    без захода внутрь."""
    head = row["bank"] or donate.KINDS.get(row["kind"], "Перевод")
    if row["kind"] == "qr":
        return f"🖼 {head}"
    tail = donate.pretty_value(row["kind"], row["value"])
    if len(tail) > 12:
        tail = "…" + tail[-9:]
    icon = "💳" if row["kind"] == "card" else "📱"
    return f"{icon} {head} · {tail}"


# --- ВЛАДЕЛЕЦ -------------------------------------------------------------
async def donate_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rows = await donate.methods()
    on = await donate.enabled()
    rem = await donate.reminder_enabled()
    days = await donate.reminder_days()

    lines = ["💳 **Поддержка проекта**", ""]
    if not rows:
        lines += [
            "Реквизитов нет, и кнопки у людей тоже нет: за ней было бы пусто.",
            "",
            "Заведите карту, телефон для СБП или картинку с QR — "
            "и кнопку можно будет включить.",
        ]
    else:
        lines.append(f"Реквизитов: **{len(rows)}**")
        for row in rows:
            lines.append(f"  • {_label(row)}")
        lines.append("")
        lines.append("👤 *Кнопка у людей:* "
                     + ("**включена**" if on else "выключена"))
        lines.append("🔔 *Напоминание после обновлений:* "
                     + (f"раз в {days} дн." if rem else "выключено"))
        if rem:
            lines.append("     _Идёт следом за «что нового» и только тем, кому "
                         "оно ушло._")

    kb = []
    if rows:
        kb.append([InlineKeyboardButton(
            "🚫 Убрать кнопку у людей" if on else "✅ Показать кнопку людям",
            callback_data="don_toggle")])
    kb.append([InlineKeyboardButton("➕ Карта", callback_data="don_add_card"),
               InlineKeyboardButton("➕ Телефон", callback_data="don_add_phone")])
    kb.append([InlineKeyboardButton("➕ QR-картинка", callback_data="don_add_qr")])
    for row in rows:
        kb.append([InlineKeyboardButton(_label(row),
                                        callback_data=f"don_open_{row['id']}")])
    kb.append([InlineKeyboardButton("✍️ Текст обращения", callback_data="don_text")])
    if rows:
        kb.append([InlineKeyboardButton(
            "🔕 Не напоминать после обновлений" if rem
            else f"🔔 Напоминать раз в {days} дн.",
            callback_data="don_rem_toggle")])
        if rem:
            kb.append([InlineKeyboardButton(f"⏱ Периодичность · {days} дн.",
                                            callback_data="don_period")])
        kb.append([InlineKeyboardButton("👁 Как это видят люди",
                                        callback_data="don_preview")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def donate_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    on = await donate.enabled()
    await donate.set_enabled(not on)
    await db.log_event("Донаты", "Кнопка поддержки "
                       + ("включена" if not on else "выключена"))
    await update.callback_query.answer(
        "Кнопка появилась у людей" if not on else "Кнопку убрали")
    await donate_menu(update, context)


async def donate_reminder_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    on = await donate.reminder_enabled()
    await donate.set_reminder(not on)
    await update.callback_query.answer(
        "Будем напоминать" if not on else "Напоминать не будем")
    await donate_menu(update, context)


async def donate_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Как часто напоминать. Цифра здесь — не про вежливость, а про то, сколько
    раз подряд человек готов услышать одну и ту же просьбу."""
    query = update.callback_query
    now = await donate.reminder_days()

    text = ("⏱ **Как часто напоминать**", "",
            f"Сейчас: **раз в {now} дн.**", "",
            "Напоминание уходит следом за «что нового» и только тому, кому это "
            "«что нового» реально пришло. Срок считается по каждому человеку "
            "отдельно, а не по проекту: подключился сегодня — отсчёт с "
            "сегодня.")
    kb = []
    row = []
    for days in donate.PERIOD_CHOICES:
        mark = "✅ " if days == now else ""
        row.append(InlineKeyboardButton(f"{mark}раз в {days} дн.",
                                        callback_data=f"don_per_{days}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("✍️ Своё число", callback_data="don_per_own")])
    kb.append([InlineKeyboardButton("🔙 Назад", callback_data="don_menu")])

    await show_screen(query, context, "\n".join(text),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def donate_period_set(update: Update, context: ContextTypes.DEFAULT_TYPE, days):
    applied = await donate.set_reminder_days(days)
    await db.log_event("Донаты", f"Напоминание раз в {applied} дн.")
    await update.callback_query.answer(f"Раз в {applied} дн.")
    await donate_menu(update, context)


async def donate_ask(update: Update, context: ContextTypes.DEFAULT_TYPE, kind):
    """Просит прислать реквизит. Состояние — в user_data: ввод разбирает
    общий обработчик сообщений."""
    query = update.callback_query
    context.user_data["state"] = f"awaiting_donate_{kind}"
    ask = {"card": ASK_CARD, "phone": ASK_PHONE, "qr": ASK_QR,
           "text": ASK_TEXT, "days": ASK_DAYS}[kind]
    await show_screen(query, context, ask,
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("✖️ Отмена",
                                                 callback_data="don_menu")]]),
                      parse_mode=ParseMode.MARKDOWN)


async def donate_open(update: Update, context: ContextTypes.DEFAULT_TYPE, method_id):
    query = update.callback_query
    row = await db.get_donate_method(method_id)
    if not row:
        await query.answer("Реквизит уже удалён", show_alert=True)
        return await donate_menu(update, context)

    lines = [f"{_label(row)}", ""]
    lines.append(f"Вид: {donate.KINDS.get(row['kind'], row['kind'])}")
    if row["kind"] == "qr":
        lines.append("Картинка отправляется людям по кнопке на экране поддержки.")
    else:
        lines.append(f"Номер: `{donate.pretty_value(row['kind'], row['value'])}`")
    if row["note"]:
        lines.append(f"Подпись: {escape_md(row['note'])}")

    kb = [[InlineKeyboardButton("🗑 Удалить", callback_data=f"don_del_{row['id']}")],
          [InlineKeyboardButton("🔙 Назад", callback_data="don_menu")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def donate_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, method_id):
    await db.delete_donate_method(method_id)
    # Последний реквизит ушёл — кнопке у людей вести некуда.
    if not await donate.methods():
        await donate.set_enabled(False)
    await db.log_event("Донаты", "Реквизит удалён")
    await update.callback_query.answer("Удалено")
    await donate_menu(update, context)


async def donate_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тот же экран, что у людей, — но с выходом обратно в настройку.

    Текст про деньги читается не так, как пишется. Увидеть его чужими глазами
    надо до того, как он уйдёт к тридцати знакомым, а не после.
    """
    query = update.callback_query
    kb = [[InlineKeyboardButton("🔙 К настройке", callback_data="don_menu")]]
    await show_screen(query, context, await donate.screen_text(),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


# --- ЧЕЛОВЕК --------------------------------------------------------------
async def client_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await donate.visible():
        await query.answer("Сейчас это выключено", show_alert=True)
        return

    kb = []
    if await donate.qr_methods():
        kb.append([InlineKeyboardButton("🖼 Показать QR",
                                        callback_data="client_donate_qr")])
    kb.append([InlineKeyboardButton("🏠 Личный кабинет", callback_data="client_menu")])
    await show_screen(query, context, await donate.screen_text(),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def client_donate_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Картинку шлём отдельным сообщением: экран с текстом остаётся на месте,
    а QR можно увеличить и показать банковскому приложению."""
    query = update.callback_query
    rows = await donate.qr_methods()
    if not rows:
        await query.answer("QR не заведён", show_alert=True)
        return
    await query.answer()
    for row in rows:
        caption = row["bank"] or "QR для оплаты"
        if row["note"]:
            caption += f" · {row['note']}"
        await context.bot.send_photo(chat_id=update.effective_user.id,
                                     photo=row["value"], caption=caption)


# --- ВВОД ОТ ВЛАДЕЛЬЦА ----------------------------------------------------
async def handle_donate_input(update, context, state):
    """Разбирает присланный реквизит или текст. Возвращает True, если сообщение
    было для нас, — общий обработчик по этому признаку останавливается."""
    kind = state.replace("awaiting_donate_", "")
    if kind not in ("card", "phone", "qr", "text", "days"):
        return False
    context.user_data["state"] = None
    chat_id = update.message.chat_id

    back = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 К настройке", callback_data="don_menu")]])

    if kind == "qr":
        photo = update.message.photo
        if not photo:
            await context.bot.send_message(
                chat_id=chat_id, reply_markup=back,
                text="⚠️ Это не картинка. Пришлите QR картинкой — "
                     "сжатым фото, а не файлом.")
            return True
        # Берём самый крупный размер: телеграм присылает лесенку, и мелкий
        # вариант в банковском приложении не считается.
        await db.add_donate_method("qr", photo[-1].file_id, bank="QR · СБП")
        await db.log_event("Донаты", "Добавлен QR")
        await context.bot.send_message(
            chat_id=chat_id, reply_markup=back,
            text="✅ QR сохранён. Люди получат его кнопкой на экране поддержки.")
        return True

    raw = (update.message.text or "").strip()
    if not raw:
        await context.bot.send_message(chat_id=chat_id, reply_markup=back,
                                       text="⚠️ Пустое сообщение — ничего не изменилось.")
        return True

    if kind == "days":
        digits = "".join(c for c in raw if c.isdigit())
        if not digits:
            await context.bot.send_message(
                chat_id=chat_id, reply_markup=back,
                text="⚠️ Нужно число дней — например, `21`.",
                parse_mode=ParseMode.MARKDOWN)
            return True
        applied = await donate.set_reminder_days(digits)
        await db.log_event("Донаты", f"Напоминание раз в {applied} дн.")
        await context.bot.send_message(
            chat_id=chat_id, reply_markup=back,
            text=f"✅ Напоминаем раз в {applied} дн.")
        return True

    if kind == "text":
        await donate.set_text(raw)
        await db.log_event("Донаты", "Изменён текст обращения")
        await context.bot.send_message(
            chat_id=chat_id, reply_markup=back,
            text="✅ Текст сохранён. Посмотрите его кнопкой «Как это видят люди».")
        return True

    parts = [p.strip() for p in raw.split(",")]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        await context.bot.send_message(
            chat_id=chat_id, reply_markup=back, parse_mode=ParseMode.MARKDOWN,
            text="⚠️ Нужны банк и номер через запятую — например:\n"
                 "`Сбербанк, 2202 2020 1111 2222`")
        return True

    bank, value = parts[0], parts[1]
    note = parts[2] if len(parts) > 2 and parts[2] else None
    await db.add_donate_method(kind, value, bank=bank, note=note)
    await db.log_event("Донаты", f"Добавлен реквизит: {bank}")
    await context.bot.send_message(
        chat_id=chat_id, reply_markup=back, parse_mode=ParseMode.MARKDOWN,
        text=f"✅ Сохранено: **{escape_md(bank)}** · "
             f"`{donate.pretty_value(kind, value)}`")
    return True

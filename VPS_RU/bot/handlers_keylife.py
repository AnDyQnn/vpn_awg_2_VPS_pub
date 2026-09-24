# -*- coding: utf-8 -*-
"""Судьба ключа: истёк срок или ключ уснул.

Раньше решение принимал таймер: ключ молча отключался, админу приходил текст без
кнопок. Теперь ключ ставится на паузу (безопасное состояние, доступ прекращён,
адрес пока занят), а владельцу приходит вопрос с выбором — удалить или продлить.

Пока решения нет, ключ остаётся на паузе, а вопрос копится в разделе «Ждут решения»
и в счётчике на кнопке «Админка». Ничего не пропадает: вопрос лежит в базе, а не в
сообщении Telegram, поэтому кнопки в старом сообщении работают и после перезапуска.

Отдельно спрашивается, что делать в следующий раз с этим же ключом: спросить снова
или продлевать на тот же срок самому. Второе — только по явному выбору владельца.
"""
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import escape_md, dt_to_moscow, show_screen
from wireguard_manager import delete_peer, resume_peer

TERMS = [(7, "7 дней"), (30, "30 дней"), (90, "90 дней"), (0, "Бессрочно")]
DEFAULT_DORMANT_DAYS = 30


async def dormant_days() -> int:
    try:
        return int(await db.get_setting("dormant_days") or DEFAULT_DORMANT_DAYS)
    except Exception:
        return DEFAULT_DORMANT_DAYS


def _ago(dt):
    if not dt:
        return "ни разу"
    days = (datetime.utcnow() - dt).days
    if days <= 0:
        return "сегодня"
    if days == 1:
        return "вчера"
    return f"{days} дн. назад"


async def decision_text(uuid_val) -> str:
    """Один и тот же текст и в алярме, и на экране решения — чтобы вопрос выглядел
    одинаково, откуда бы к нему ни пришли."""
    user = await db.get_user_by_uuid(uuid_val)
    dec = await db.get_pending_decision(uuid_val)
    if not user or not dec:
        return ""

    head = ("⏳ **Истёк срок ключа**" if dec["reason"] == "expired"
            else "💤 **Ключ уснул**")
    lines = [head, "", f"Ключ: **{escape_md(user['name'])}**"]
    if dec["reason"] == "dormant":
        lines.append(f"Не подключался: {_ago(dec['last_handshake'])} "
                     f"(порог — {await dormant_days()} дн.)")
    else:
        lines.append("Последнее соединение: " + _ago(dec["last_handshake"]))
        if dec["was_expires_at"]:
            lines.append("Срок был до: "
                         + dt_to_moscow(dec["was_expires_at"]).strftime("%d.%m.%Y %H:%M"))
    lines.append("Выдан: " + dt_to_moscow(user["created_at"]).strftime("%d.%m.%Y"))
    lines += ["", "Ключ **на паузе** — доступа нет, адрес пока за ним.",
              "Пока не решишь, так и останется."]
    return "\n".join(lines)


def decision_keyboard(uuid_val):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♻️ Продлить", callback_data=f"kd_ext_{uuid_val}"),
         InlineKeyboardButton("🗑 Удалить", callback_data=f"kd_del_{uuid_val}")],
        [InlineKeyboardButton("📋 Все вопросы", callback_data="kd_list")],
    ])


async def pending_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """«Ждут решения» — список всех неотвеченных вопросов."""
    query = update.callback_query
    items = await db.get_pending_decisions()

    if not items:
        text = ("📋 **Ждут решения**\n\nПусто — все ключи живые, "
                "ни один не истёк и не уснул.")
        kb = [[InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]]
    else:
        lines = ["📋 **Ждут решения**", "",
                 "Все они сейчас на паузе и ждут, что с ними делать.", ""]
        kb = []
        for it in items:
            mark = "⏳" if it["reason"] == "expired" else "💤"
            why = "истёк срок" if it["reason"] == "expired" else "уснул"
            lines.append(f"{mark} **{escape_md(it['name'])}** — {why}, "
                         f"ждёт с {dt_to_moscow(it['created_at']).strftime('%d.%m')}")
            kb.append([InlineKeyboardButton(f"{mark} {it['name']}",
                                            callback_data=f"kd_open_{it['user_uuid']}")])
        text = "\n".join(lines)
        kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def decision_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    text = await decision_text(uuid_val)
    if not text:
        await query.answer("Вопрос уже закрыт")
        return await pending_screen(update, context)
    await show_screen(query, context, text, reply_markup=decision_keyboard(uuid_val),
                                  parse_mode=ParseMode.MARKDOWN)


async def extend_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await update.callback_query.answer("Ключ уже удалён")
        return await pending_screen(update, context)

    kb = [[InlineKeyboardButton(label, callback_data=f"kd_set_{days}_{uuid_val}")]
          for days, label in TERMS]
    kb.append([InlineKeyboardButton("✖️ Назад", callback_data=f"kd_open_{uuid_val}")])
    await show_screen(update.callback_query, context, 
        f"♻️ **На сколько продлить «{escape_md(user['name'])}»?**\n\n"
        "Ключ снова заработает сразу — тот же самый, перевыпускать и "
        "пересылать конфиг не нужно.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def do_extend(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    uuid_val, days: int):
    """Продление: снимаем паузу и ставим новый срок. Ключ тот же — у человека
    ничего не меняется, повторно слать конфиг не нужно."""
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Ключ уже удалён", show_alert=True)
        return await pending_screen(update, context)

    expires = None if days == 0 else datetime.utcnow() + timedelta(days=days)
    try:
        await resume_peer(uuid_val)
    except Exception as e:
        await query.answer(f"Узел не снял паузу: {e}", show_alert=True)
        return

    await db.execute("UPDATE users SET is_active=TRUE, expires_at=$2 WHERE uuid=$1",
                     uuid_val, expires)
    # Вернуть право пользоваться — на обоих каналах.
    try:
        import xui
        await xui.sync_person(uuid_val, "продление")
    except Exception as e:
        print(f"Xray: продление не дошло до панели: {e}")
    await db.resolve_decision(uuid_val, f"extended:{days}")
    await db.log_event("KeyLife",
                       f"Ключ {user['name']} продлён на "
                       f"{'бессрочно' if days == 0 else str(days) + ' дн.'}")

    # Сообщаем человеку: для него ключ просто ожил, и он должен понимать почему.
    for tid in user.get("tg_ids", []):
        try:
            await context.bot.send_message(
                chat_id=tid,
                text=f"✅ Ваш ключ **{escape_md(user['name'])}** снова активен."
                     + ("" if days == 0 else f"\nСрок продлён на {days} дн."),
                parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    await policy_menu(update, context, uuid_val, days)


async def policy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      uuid_val, days: int):
    """Что делать в следующий раз. Спрашивается ПОСЛЕ продления, а не до:
    сначала закрыли вопрос, потом решаем, повторять ли его вообще."""
    user = await db.get_user_by_uuid(uuid_val)
    name = escape_md(user["name"]) if user else "ключ"
    pol = await db.get_key_policy(uuid_val)

    now = ("спрашивать" if pol["mode"] == "ask"
           else f"продлевать само на {pol['extend_days']} дн.")
    if days == 0:
        text = (f"✅ **«{name}» продлён бессрочно.**\n\n"
                "Срок больше не истечёт, спрашивать будет не о чем. "
                "Ключ всё ещё может уснуть — если им не пользоваться.")
        kb = [[InlineKeyboardButton("📋 Ждут решения", callback_data="kd_list")],
              [InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]]
    else:
        text = (f"✅ **«{name}» продлён на {days} дн.**\n\n"
                f"Что делать, когда срок истечёт снова?\n"
                f"Сейчас: {now}.")
        kb = [[InlineKeyboardButton("❓ Спрашивать снова",
                                    callback_data=f"kd_pol_ask_{uuid_val}")],
              [InlineKeyboardButton(f"♻️ Продлевать само на {days} дн.",
                                    callback_data=f"kd_pol_{days}_{uuid_val}")],
              [InlineKeyboardButton("📋 Ждут решения", callback_data="kd_list")]]

    await show_screen(update.callback_query, context, 
        text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def set_policy(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     uuid_val, mode: str):
    """mode: «ask» или число дней для автопродления."""
    if mode == "ask":
        await db.set_key_policy(uuid_val, "ask", None)
        msg = "Буду спрашивать"
    else:
        await db.set_key_policy(uuid_val, "auto", int(mode))
        msg = f"Буду продлевать само на {mode} дн."
    await db.log_event("KeyLife", f"Политика ключа {uuid_val}: {msg}")
    await update.callback_query.answer(msg)
    await pending_screen(update, context)


async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await update.callback_query.answer("Ключ уже удалён")
        return await pending_screen(update, context)

    roles = await db.get_user_roles(uuid_val)
    extra = []
    if roles:
        extra.append("роли: " + ", ".join(r["name"] for r in roles))
    if (await db.get_peer_limits()).get(uuid_val):
        extra.append("персональное правило нагрузки")

    lines = [f"🗑 **Удалить ключ «{escape_md(user['name'])}»?**", "",
             "Пир снимется с узла, адрес освободится и уйдёт следующему."]
    if extra:
        lines.append("Заодно удалится: " + escape_md(", ".join(extra)) + ".")
    lines.append("")
    lines.append("Отменить это нельзя — конфиг перестанет работать навсегда.")

    kb = [[InlineKeyboardButton("🗑 Удалить", callback_data=f"kd_delok_{uuid_val}"),
           InlineKeyboardButton("✖️ Отмена", callback_data=f"kd_open_{uuid_val}")]]
    await show_screen(update.callback_query, context, 
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN)


async def do_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Ключ уже удалён")
        return await pending_screen(update, context)

    try:
        await delete_peer(uuid_val, user["name"])
    except Exception as e:
        await query.answer(f"Узел не отдал пир: {e}", show_alert=True)
        return

    # Доступ по Xray — до удаления записи: после неё не останется, по какому
    # имени искать клиента в панели.
    try:
        import xui
        await xui.revoke(uuid_val)
    except Exception as e:
        print(f"Xray: доступ не отозван при удалении: {e}")
    # Запись в users уходит с каскадом: роли, лимиты, статистика, вопрос по ключу.
    await db.execute("DELETE FROM users WHERE uuid=$1", uuid_val)
    await db.log_event("KeyLife", f"Ключ {user['name']} удалён по решению владельца")

    # Доступы пересобираем: адрес освободился и завтра достанется другому,
    # а правило, выданное на этот адрес, осталось бы висеть на новом хозяине.
    # Пересобираем И доступы, И фильтры: то и другое узел применяет по адресу,
    # а адрес освободился. Раньше здесь были только доступы — фильтр оставался
    # на адресе и доставался следующему хозяину.
    try:
        from restrictions import reapply
        await reapply("удалён ключ")
    except Exception as e:
        print(f"KeyLife: не удалось пересобрать ограничения: {e}")

    await query.answer("Ключ удалён")
    await pending_screen(update, context)

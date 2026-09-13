# -*- coding: utf-8 -*-
"""Стадии доставки ключа.

Telegram не сообщает, прочитано ли сообщение — такой отметки нет в API вовсе.
Зато видно каждое действие человека в боте, и по ним выстраивается цепочка,
которая отвечает на настоящий вопрос: «ключ дошёл или нет».

    отправлено → не дошло (бот заблокирован)
               → нажал кнопку → скачал файл → подключился

Последняя стадия — единственная, которую подтверждает не Telegram, а сам туннель:
рукопожатие означает, что конфиг не просто получен, а поставлен и работает.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import escape_md, dt_to_moscow, show_screen

STUCK_HOURS = 24        # столько ждём молча, потом показываем как застрявшее


def _when(dt):
    return dt_to_moscow(dt).strftime("%d.%m %H:%M") if dt else ""


def stage(rec):
    """Текущая стадия: (значок, короткая подпись). Идём от конца — важнее
    всего, докуда доехало, а не что было по дороге."""
    if not rec or (not rec.get("sent_at") and not rec.get("blocked_at")):
        return "—", "не отправляли"
    if rec.get("connected_at"):
        return "✅", "подключился"
    if rec.get("downloaded_at"):
        return "📥", "скачал, но не подключился"
    if rec.get("opened_at"):
        return "👀", "видел сообщение, файл не брал"
    if rec.get("blocked_at"):
        return "🚫", "не дошло — бот заблокирован или не запущен"
    return "📨", "отправлено, реакции нет"


def describe(rec) -> str:
    """Полная цепочка для карточки: что произошло и когда."""
    icon, short = stage(rec)
    if not rec or (not rec.get("sent_at") and not rec.get("blocked_at")):
        return "📨 **Доставка:** конфиг в Telegram не отправляли"

    lines = [f"{icon} **Доставка:** {short}"]
    steps = [("отправлено", rec.get("sent_at")),
             ("нажал кнопку", rec.get("opened_at")),
             ("скачал файл", rec.get("downloaded_at")),
             ("подключился", rec.get("connected_at"))]
    for label, dt in steps:
        if dt:
            lines.append(f"  • {label} — {_when(dt)}")
    if rec.get("blocked_at"):
        lines.append(f"  • не доставлено — {_when(rec['blocked_at'])}")
        if rec.get("last_error"):
            lines.append(f"  • причина: `{escape_md(str(rec['last_error'])[:80])}`")
    return "\n".join(lines)


async def delivery_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """«Доставка ключей» — только те, у кого дело не дошло до подключения.
    Дошедшие не показываем: список нужен, чтобы понять, кому помочь."""
    query = update.callback_query
    items = await db.get_stuck_deliveries(STUCK_HOURS)

    if not items:
        text = ("📨 **Доставка ключей**\n\n"
                "Все отправленные ключи дошли до подключения.")
        kb = [[InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]]
    else:
        lines = ["📨 **Доставка ключей**", "",
                 "Отправлено, но человек ещё не подключился:", ""]
        kb = []
        for it in items:
            icon, short = stage(it)
            lines.append(f"{icon} **{escape_md(it['name'])}** — {short}")
            if it.get("blocked_at"):
                lines.append("      конфиг не ушёл: бот не запущен или заблокирован")
            kb.append([InlineKeyboardButton(f"{icon} {it['name']}",
                                            callback_data=f"user_detail_{it['user_uuid']}")])
        lines += ["", f"_Молчание первые {STUCK_HOURS} ч нормально — сюда попадают "
                      "только те, кто дольше._"]
        text = "\n".join(lines)
        kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def track_send(uuid, tg_id, coro_factory):
    """Отправляет и сразу записывает исход.

    Смысл обёртки в том, что «не доставлено» — это не ошибка, о которой надо
    молча написать в лог, а состояние ключа: администратор должен видеть, что
    человек конфиг не получил, и знать почему.
    Возвращает (успех, ошибка)."""
    try:
        await coro_factory()
    except Exception as e:
        try:
            await db.delivery_blocked(uuid, tg_id, e)
        except Exception:
            pass
        return False, e
    try:
        await db.delivery_sent(uuid, tg_id)
    except Exception:
        pass
    return True, None

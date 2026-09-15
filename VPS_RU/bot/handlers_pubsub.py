# -*- coding: utf-8 -*-
"""Подписка наружу: экран в администрировании.

Подписка живёт внутри туннеля, и по умолчанию так и остаётся. Прочитать её
можно, только уже будучи подключённым, — значит первая настройка идёт куском
текста, а изменения доезжают рассылкой.

Открыв её наружу, получаем обратное: человек вставляет один адрес, и дальше
сервера, маскировки и список исключений приезжают к нему сами. Цена — открытый
порт, и решать, платить её или нет, должен владелец, а не обновление.

Сама работа делается на хосте (scripts/public_sub.sh): сертификат, правила
файрвола и таймер продления боту из контейнера недоступны. Отсюда только
просьба и показ того, что получилось.
"""
import json
import os
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import show_screen

FLAGS_DIR = "/volumes/flags"
STATE_FILE = os.path.join(FLAGS_DIR, "public_sub.json")
LOG_FILE = os.path.join(FLAGS_DIR, "public_sub.log")
CERT_FILE = os.path.join(os.getenv("SUB_CERT_DIR", "/volumes/certs"),
                         "fullchain.pem")


def state():
    """Что в последний раз сказал скрипт на хосте."""
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def is_on():
    """Включена ли. Судим по сертификату, а не по записи о намерении.

    Запись говорит, чего хотели; файл сертификата — что получилось. Когда они
    расходятся, правда за файлом."""
    try:
        return os.path.getsize(CERT_FILE) > 0
    except OSError:
        return False


def cert_days_left():
    """Сколько суток осталось сертификату. None — неизвестно.

    Дату считает скрипт на хосте и кладёт в свой отчёт. Разбирать сертификат
    здесь было бы лишней зависимостью: openssl в образе бота нет, а тащить его
    туда ради одной даты — менять образ ради строки на экране."""
    until = state().get("until")
    if not until:
        return None
    try:
        return (float(until) - time.time()) / 86400.0
    except (TypeError, ValueError):
        return None


async def _ask_host(mode: str):
    """Просьба хосту. В файле одно слово — on или off."""
    os.makedirs(FLAGS_DIR, exist_ok=True)
    with open(os.path.join(FLAGS_DIR, "do_public_sub"), "w") as f:
        f.write(mode + "\n")


async def screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    on = is_on()
    st = state()

    lines = ["🌐 **Подписка наружу**", ""]
    if on:
        left = cert_days_left()
        port = st.get("port", 8443)
        lines.append(f"Состояние: **открыта**, порт `{port}`")
        if left is not None:
            lines.append("Сертификат: осталось **%.1f сут.**" % left)
            if left < 1:
                lines.append("     ⚠️ _Меньше суток. Проверьте таймер "
                             "продления: `systemctl list-timers vpn-subcert`._")
        try:
            import subscription
            shut = subscription.blocked_now()
            if shut:
                lines.append(f"Закрыто адресов за назойливость: **{shut}**")
        except Exception:
            pass
    else:
        lines.append("Состояние: **закрыта** — подписку видно только изнутри")

    lines += [
        "",
        "Пока подписка закрыта, прочитать её можно, лишь уже подключившись. "
        "Поэтому первая настройка идёт куском текста, а новые исключения и "
        "переезды доезжают рассылкой.",
        "",
        "Открытая работает наоборот: человек вставляет один адрес, и дальше "
        "всё приезжает само.",
        "",
        "_Домен не нужен и покупать ничего не надо: сертификат выдаётся прямо "
        "на IP-адрес, бесплатно. Живёт он неделю, продление стоит таймером "
        "дважды в сутки._",
    ]

    if not on:
        lines += [
            "",
            "**Что появится наружу.** Один порт, и на нём только чтение "
            "подписки по личному токену. На всё остальное — молчание.",
            "",
            "Охрана порта: не больше 8 соединений и 30 запросов в минуту с "
            "одного адреса, потолок 50 в секунду на весь порт, а десять "
            "промахов по токену закрывают адрес на час.",
        ]

    msg = (st.get("msg") or "").strip()
    if msg and st.get("state") == "error":
        lines += ["", f"⚠️ Последняя попытка: _{msg}_"]

    kb = []
    if on:
        kb.append([InlineKeyboardButton("🔒 Закрыть наружу",
                                        callback_data="psub_off")])
        kb.append([InlineKeyboardButton("🔄 Продлить сертификат сейчас",
                                        callback_data="psub_renew")])
    else:
        kb.append([InlineKeyboardButton("🌐 Открыть наружу",
                                        callback_data="psub_on")])
    kb.append([InlineKeyboardButton("🔙 Администрирование",
                                    callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def turn_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть. Спрашиваем один раз: это меняет то, что видно из интернета."""
    query = update.callback_query
    if context.user_data.get("psub_sure") != "on":
        context.user_data["psub_sure"] = "on"
        text = ("🌐 **Открыть подписку наружу?**\n\n"
                "На сервере появится ещё один открытый порт. До сих пор "
                "снаружи были видны только входы VPN.\n\n"
                "Что будет сделано:\n"
                "• взят бесплатный сертификат на IP-адрес;\n"
                "• на порт поставлена охрана — по числу соединений, по частоте "
                "и по промахам с одного адреса;\n"
                "• заведён таймер продления, дважды в сутки.\n\n"
                "_Закрыть обратно можно той же кнопкой, всё снимется._")
        kb = [[InlineKeyboardButton("✅ Да, открыть", callback_data="psub_on")],
              [InlineKeyboardButton("✖️ Отмена", callback_data="psub_menu")]]
        return await show_screen(query, context, text,
                                 reply_markup=InlineKeyboardMarkup(kb),
                                 parse_mode=ParseMode.MARKDOWN)

    context.user_data.pop("psub_sure", None)
    await _ask_host("on")
    await db.log_event("Подписки", "Владелец открыл подписку наружу")
    await query.answer("Открываю, это займёт до минуты")
    await _wait_screen(update, context,
                       "Беру сертификат и ставлю охрану порта…")


async def turn_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _ask_host("off")
    await db.log_event("Подписки", "Владелец закрыл подписку наружу")
    await query.answer("Закрываю")
    await _wait_screen(update, context, "Снимаю правила и закрываю порт…")


async def renew_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Продлить руками. Тот же путь, которым ходит таймер."""
    query = update.callback_query
    os.makedirs(FLAGS_DIR, exist_ok=True)
    with open(os.path.join(FLAGS_DIR, "do_public_sub"), "w") as f:
        f.write("on\n")
    await query.answer("Продлеваю")
    await _wait_screen(update, context, "Обновляю сертификат…")


async def _wait_screen(update, context, what):
    """Ждём хост и показываем, чем кончилось.

    Демон обходит флаги раз в пять секунд, а сертификат берётся не мгновенно.
    Сказать «сделано» сразу после того, как положил просьбу, — значит соврать:
    ровно на этом уже обжигались с паролем архива."""
    import asyncio
    query = update.callback_query
    await show_screen(query, context, f"⏳ {what}",
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("🔄 Обновить",
                                                 callback_data="psub_menu")]]),
                      parse_mode=ParseMode.MARKDOWN)
    flag = os.path.join(FLAGS_DIR, "do_public_sub")
    for _ in range(90):
        await asyncio.sleep(1)
        if not os.path.exists(flag):
            # Демон забрал просьбу. Дадим скрипту доработать и покажем итог.
            await asyncio.sleep(3)
            break
    await screen(update, context)


def status_line():
    """Строка для экрана администрирования и для отчёта проверки."""
    if not is_on():
        return "🌐 *Подписка наружу:* закрыта, видно только изнутри"
    left = cert_days_left()
    tail = (", сертификат на %.1f сут." % left) if left is not None else ""
    if left is not None and left < 1:
        tail += " ⚠️"
    return "🌐 *Подписка наружу:* открыта" + tail

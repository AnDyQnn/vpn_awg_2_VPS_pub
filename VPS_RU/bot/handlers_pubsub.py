# -*- coding: utf-8 -*-
"""Подписка наружу: экран в администрировании.

Открыта по умолчанию, и настройки у этого нет. Смысл подписки в том, что
человек вставляет один адрес, а дальше сервера, маскировки и список исключений
приезжают к нему сами; закрытая подписка это отменяет — прочитать её можно,
только уже подключившись.

Безопасность здесь держится не тумблером, а устройством: внешний порт
опубликован всегда, но бот слушает его ТОЛЬКО пока рядом лежит действующий
сертификат. Нет сертификата — нет и сокета, снаружи порт молчит как закрытый.
Поэтому подписку нельзя случайно отдать открытым текстом: её физически некому
отдать.

Отсюда — показ состояния и возможность закрыть, если однажды понадобится.
Настоящая работа (сертификат, правила файрвола, таймер продления) делается на
хосте: scripts/public_sub.sh. Боту из контейнера ни iptables, ни systemd
недоступны.
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
        port = st.get("port", 2096)
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

    if on:
        lines += [
            "",
            "Человек вставляет один адрес — и дальше сервера, маскировки и "
            "список исключений приезжают к нему сами. Ни рассылок, ни "
            "перевыпусков.",
            "",
            "**Что видно снаружи.** Один порт, и на нём только чтение подписки "
            "по личному токену. На всё остальное — молчание, одно и то же на "
            "любой запрос.",
            "",
            "Охрана: не больше 8 соединений и 30 запросов в минуту с одного "
            "адреса, потолок 50 в секунду на весь порт, а десять промахов по "
            "токену закрывают адрес на час.",
        ]
    else:
        lines += [
            "",
            "Пока закрыта, прочитать подписку можно, лишь уже подключившись. "
            "Значит первую настройку придётся отдавать текстом, а новые "
            "исключения и переезды — рассылать.",
            "",
            "_Открыть можно кнопкой ниже. Домен не нужен и покупать ничего не "
            "надо: сертификат выдаётся прямо на IP-адрес, бесплатно._",
        ]

    if on:
        lines += [
            "",
            "_Открыть порт без сертификата нельзя: бот слушает его только пока "
            "сертификат лежит рядом. Поэтому настройки у этого нет — настройка, "
            "которую можно выставить не так, была бы способом однажды отдать "
            "подписку открытым текстом._",
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
    have = (os.getenv("PUBLIC_DOMAIN") or "").strip()
    kb.append([InlineKeyboardButton(
        ("🌐 Имя · " + have) if have else "🌐 Задать своё имя",
        callback_data="psub_domain")])
    kb.append([InlineKeyboardButton("🔙 Администрирование",
                                    callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def turn_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть обратно. Это возврат к обычному состоянию, поэтому без
    подтверждений: спрашивать имеет смысл там, где что-то теряют."""
    query = update.callback_query
    await _ask_host("on")
    await db.log_event("Подписки", "Владелец открыл подписку наружу")
    await query.answer("Открываю, это займёт до минуты")
    await _wait_screen(update, context,
                       "Беру сертификат и ставлю охрану порта…")


async def turn_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Закрыть. Здесь спросить и надо: это выключает автообновление у всех.

    После закрытия новые исключения и переезды перестанут доезжать сами — их
    снова придётся рассылать, а первую настройку отдавать текстом."""
    query = update.callback_query
    if context.user_data.get("psub_sure") != "off":
        context.user_data["psub_sure"] = "off"
        text = ("🔒 **Закрыть подписку наружу?**\n\n"
                "Она откроется только изнутри туннеля. Это значит:\n"
                "• новые исключения и переезды перестанут доезжать сами;\n"
                "• первую настройку снова придётся отдавать текстом;\n"
                "• у тех, кто уже подписан, профиль замрёт на текущем.\n\n"
                "_Открытый порт сам по себе ничего не стоит: снаружи по нему "
                "отдаётся только подписка по личному токену, всё остальное "
                "молчит._")
        kb = [[InlineKeyboardButton("🔒 Да, закрыть", callback_data="psub_off")],
              [InlineKeyboardButton("✖️ Отмена", callback_data="psub_menu")]]
        return await show_screen(query, context, text,
                                 reply_markup=InlineKeyboardMarkup(kb),
                                 parse_mode=ParseMode.MARKDOWN)
    context.user_data.pop("psub_sure", None)
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


# --- Своё имя узла -----------------------------------------------------------
#
# Домен нигде в коде не зашит: у каждой установки он свой, а копия проекта не
# должна требовать правки исходников. Живёт он в `.env` ноды, а вписывается
# отсюда — тем же путём, что пароль архива и токен панелей: бот кладёт просьбу
# в `volumes/flags`, демон на хосте пишет её в файл и пересоздаёт контейнеры.
# Своими руками в `.env` не лезет никто.

def domain_ok(name):
    """Похоже ли это на имя, которое выдержит выпуск сертификата.

    Проверяем до отправки, а не после: certbot отказывает на минуте ожидания, и
    человек к тому времени уже не помнит, что именно вписал.

    Разбор общий с остальными — в utils. Раньше он был свой, и это значило, что
    имя, принятое здесь, могло не совпасть с тем, что увидит подписка или зона
    имён внутри туннеля.
    """
    from utils import public_domain
    return public_domain(name) or None


def current_domain():
    from utils import public_domain
    return public_domain()


async def domain_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Что даёт своё имя и как его задать."""
    query = update.callback_query
    have = current_domain()
    lines = ["🌐 **Своё имя узла**", ""]
    if have:
        lines += [f"Сейчас: `{have}`", ""]
    else:
        lines += ["Сейчас имени нет — работаем по адресу.", ""]
    lines += [
        "Что меняется, когда имя есть:",
        "",
        "• **Сертификат живёт 90 дней вместо 160 часов.** На голый адрес "
        "Let's Encrypt выдаёт только короткий; пропустили продление — подписка "
        "умерла разом у всех.",
        "• **Подписку можно увести на 443.** Нестандартные порты режут "
        "мобильные операторы, и тогда профиль не доезжает до телефона вовсе.",
        "• **Имена внутри туннеля переезжают в это же имя.** «дом.vpn» "
        "становится «дом.<имя>», и зона остаётся одна. Правила доступа "
        "переезжают вместе с именами.",
        "• **Маской входа может стать свой сайт.** Тогда вход перестаёт "
        "зависеть от чужого: сертификат наш, отклик нулевой.",
        "",
        "Маску подключения имя не заменяет: она остаётся на крупном стороннем "
        "сайте, безликое имя в ней только мешает.",
        "",
        "_Перед тем как вписывать, заведите A-запись домена на адрес узла и "
        "дождитесь, пока она разойдётся. Если имя ещё не отвечает, выпуск "
        "сертификата на него не пройдёт — подписка останется на адресе, и я "
        "скажу об этом._",
    ]
    kb = [[InlineKeyboardButton("✏️ Задать имя", callback_data="psub_domain_set")]]
    if have:
        kb.append([InlineKeyboardButton("🗑 Убрать имя",
                                        callback_data="psub_domain_off")])
    kb.append([InlineKeyboardButton("🔙 Подписка наружу",
                                    callback_data="psub_menu")])
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def domain_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просит вписать имя."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_public_domain"
    await show_screen(
        query, context,
        "✏️ **Пришлите имя узла**\n\nОдной строкой, без `https://` и без "
        "косой черты в конце. Например: `example.ru`",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="psub_domain")]]),
        parse_mode=ParseMode.MARKDOWN)


async def domain_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Убирает имя: возвращаемся на адрес."""
    from utils import request_env_change, env_change_applied
    query = update.callback_query
    await query.answer("Убираю…")
    flag = request_env_change("PUBLIC_DOMAIN", "")
    ok = await env_change_applied(flag)
    await db.log_event("Подписки", "Своё имя узла убрано" if ok
                       else "Просьба убрать имя положена, демон не ответил")
    await show_screen(
        query, context,
        ("🌐 Имя убрано — подписка вернётся на адрес при следующем выпуске "
         "сертификата." if ok else
         "⚠️ Просьба положена, но демон на хосте не ответил.\n"
         "`systemctl status vpn-updater`"),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Подписка наружу",
                                   callback_data="psub_menu")]]),
        parse_mode=ParseMode.MARKDOWN)

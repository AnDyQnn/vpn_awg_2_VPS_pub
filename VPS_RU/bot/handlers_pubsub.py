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
    have = current_domain()
    kb.append([InlineKeyboardButton(
        ("🌐 Имя · " + have) if have else "🌐 Задать своё имя",
        callback_data="psub_domain")])
    if have:
        # Видно сразу, есть ли сертификат на внутренние имена: без него все
        # наши собственные страницы открываются с предупреждением, а заметить
        # это по одной строке «подписка открыта» невозможно.
        kb.append([InlineKeyboardButton(
            "🔑 Внутренние имена · есть" if wildcard_on()
            else "🔑 Внутренние имена · без сертификата",
            callback_data="psub_zone")])
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
        # Отдельным криком — случай, когда закрытие рвёт не только подписку.
        # Сертификат здесь один на всё: закрыв подписку, мы убираем его, а
        # вместе с ним и сайт-заглушку. Если она стоит маской входа, Xray
        # перестанет принимать на основном порту у ВСЕХ — Reality ходит к маске
        # в каждом рукопожатии. Такое узнают от людей, если не сказать заранее.
        try:
            import xray
            self_mask = (await db.get_setting("xray_dest")) == xray.SELF_DEST
        except Exception:
            self_mask = False
        if self_mask:
            text += ("\n\n⚠️ **Сейчас маской входа Xray стоит свой сайт.** "
                     "Сертификат у них общий: закрыв подписку, вы уберёте и "
                     "его, а вместе с ним — заглушку. Основной вход Xray "
                     "перестанет принимать у всех, и люди уйдут на запасные "
                     "входы.\n\nСначала смените маску на обычную: "
                     "«Протоколы → Xray → Маска входа».")
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


# --- Доступ к зоне домена ----------------------------------------------------
#
# Нужен ровно для одного: сертификата на «*.имя». Он единственный покрывает
# имена внутри туннеля — «дом.example.ru», «закрыто.example.ru», — потому что
# снаружи этих имён нет и обычную проверку они пройти не могут ни одним
# способом. Без него браузер ругается на каждую нашу собственную страницу.
#
# Логин с паролем живут ТОЛЬКО в .env на хосте. В контейнер бота они не
# передаются вовсе: боту они не нужны, а всё, что попадает в контейнер, попадает
# и в его окружение, и в вывод отладки, и однажды — в чужие руки. Поэтому здесь
# видно лишь «задано или нет», и это не неудобство, а устройство.

ZONE_FLAG = os.path.join(FLAGS_DIR, "do_zone_check")
ZONE_RESULT = os.path.join(FLAGS_DIR, "zone_check.json")

# Где живёт пара. Не в .env, и это не мелочь.
#
# Переменная окружения доезжает до контейнера только пересозданием — то есть
# каждая правка роняла бы бота, хотя самому боту эта пара не нужна вовсе: ею
# пользуется скрипт на хосте. Файл в общей папке снимает и то, и другое: правка
# мгновенная, а в окружение контейнеров значение не попадает совсем — значит не
# попадёт ни в вывод отладки, ни в `docker inspect`.
#
# В архив бэкапа папка тоже не входит: туда кладутся wireguard, configs и дамп
# базы, и только они.
SECRETS_DIR = "/volumes/secrets"
ZONE_SECRET = os.path.join(SECRETS_DIR, "regru.conf")


def zone_creds_write(user, password):
    """Кладёт пару рядом, куда смотрит хост. Права — только владельцу."""
    os.makedirs(SECRETS_DIR, exist_ok=True)
    try:
        os.chmod(SECRETS_DIR, 0o700)
    except OSError:
        pass
    tmp = ZONE_SECRET + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("REGRU_API_USER=%s\nREGRU_API_PASSWORD=%s\n" % (user, password))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    # Подменяем целиком: скрипт на хосте может читать файл ровно сейчас, и
    # застать его наполовину переписанным он не должен.
    os.replace(tmp, ZONE_SECRET)


def zone_creds_clear():
    for f in (ZONE_SECRET, ZONE_SECRET + ".tmp"):
        try:
            os.remove(f)
        except OSError:
            pass


def zone_api_on():
    """Задана ли пара для доступа к зоне.

    Смотрим на файл сами: он лежит в общей папке, и бот его видит. Спрашивать
    об этом хост значило бы узнавать о своей же правке с задержкой."""
    try:
        return os.path.getsize(ZONE_SECRET) > 0
    except OSError:
        return bool(state().get("dns_api"))


def wildcard_on():
    """Покрывает ли нынешний сертификат внутренние имена."""
    return bool(state().get("wild"))


def zone_check_result():
    try:
        with open(ZONE_RESULT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


async def zone_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    have_domain = bool(current_domain())
    api = zone_api_on()
    wild = wildcard_on()

    lines = ["🔑 **Сертификат на внутренние имена**", ""]
    if not have_domain:
        lines += ["Сначала нужно своё имя узла — без него этой задачи не "
                  "существует.", ""]
    elif wild:
        lines += ["Состояние: **есть**. Сертификат покрывает и сам домен, и "
                  "всё внутри туннеля.", ""]
    elif api:
        lines += ["Состояние: доступ к зоне задан, но сертификат ещё обычный. "
                  "Нажмите «Обновить сертификат» в разделе подписки.", ""]
    else:
        lines += ["Состояние: **нет**. Наши собственные страницы открываются "
                  "с предупреждением браузера.", ""]

    lines += [
        "**Зачем.** Имена внутри туннеля снаружи не существуют, поэтому обычную "
        "проверку они пройти не могут — и сертификата на них не бывает. "
        "Единственный, который их покрывает, — на «звёздочку»: `*.имя`. "
        "Выдаётся он по проверке через зону домена: центр просит положить "
        "временную запись, и класть её умеет только тот, у кого есть доступ к "
        "зоне.",
        "",
        "**Что это чинит.** Предупреждение браузера на странице отказа "
        "фильтра, на «доступ закрыт» и на выдаче ключей. Сейчас человек видит "
        "красный замок там, где ему показывает страницу его же сеть.",
        "",
        "**Чем за это платят.** На узле появляется доступ к управлению зоной "
        "домена. Отнимут узел — отнимут и возможность переписать записи. Это "
        "настоящее повышение ставок, и уменьшить его стоит двумя вещами:",
        "",
        "• В панели reg.ru у API есть **белый список адресов** — впишите туда "
        "адрес узла и только его.",
        "• Пароль для API там задаётся **отдельно** от пароля к кабинету. "
        "Задайте отдельный: тогда это доступ к зоне, а не ко всему аккаунту.",
        "",
        "_Пара лежит файлом на сервере, с правами только владельцу, и ни в "
        "одно окружение не попадает — ни в `docker inspect`, ни в отладку, ни "
        "в архив бэкапа. Менять её можно на ходу: ничего не перезапускается._",
    ]

    res = zone_check_result()
    if res:
        mark = "✅" if res.get("ok") else "⚠️"
        lines += ["", f"{mark} Последняя проверка: {res.get('msg', '—')}"]

    kb = []
    if have_domain:
        kb.append([InlineKeyboardButton(
            "✏️ Задать доступ" if not api else "✏️ Заменить пару",
            callback_data="psub_zone_set")])
        if api:
            kb.append([InlineKeyboardButton("🔍 Проверить доступ",
                                            callback_data="psub_zone_check")])
            kb.append([InlineKeyboardButton("🗑 Убрать доступ",
                                            callback_data="psub_zone_off")])
    else:
        kb.append([InlineKeyboardButton("🌐 Сначала задать имя узла",
                                        callback_data="psub_domain")])
    kb.append([InlineKeyboardButton("🔙 Подписка наружу", callback_data="psub_menu")])
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def zone_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Спрашиваем логин. Пароль — следующим сообщением, и оно сразу удаляется."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_regru_user"
    await show_screen(
        query, context,
        "✏️ **Логин в reg.ru**\n\nОдной строкой — тот, которым входите в "
        "кабинет.\n\n_Следующим сообщением спрошу пароль для API. Оно будет "
        "удалено сразу, как только прочитаю._",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="psub_zone")]]),
        parse_mode=ParseMode.MARKDOWN)


async def zone_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Убирает пару. Сертификат при этом остаётся — он уже выдан и живёт своё."""
    query = update.callback_query
    await query.answer("Убираю…")
    zone_creds_clear()
    try:
        os.remove(ZONE_RESULT)
    except OSError:
        pass
    await db.log_event("Подписки", "Доступ к зоне домена убран")
    await show_screen(
        query, context,
        "🔑 Доступ убран.\n\nНынешний сертификат продолжит работать до конца "
        "срока, но продлить «звёздочку» будет нечем — при следующем продлении "
        "она сменится на обычный, и предупреждения браузера вернутся.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Назад", callback_data="psub_zone")]]),
        parse_mode=ParseMode.MARKDOWN)


async def zone_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка без выпуска: кладём временную запись и тут же убираем.

    Отдельно от выпуска намеренно. Опечатка в пароле иначе всплыла бы через
    несколько минут в середине выпуска и стоила бы попытки у удостоверяющего
    центра — а их на неделю считанные единицы."""
    import asyncio
    query = update.callback_query
    os.makedirs(FLAGS_DIR, exist_ok=True)
    try:
        os.remove(ZONE_RESULT)
    except OSError:
        pass
    with open(ZONE_FLAG, "w") as f:
        f.write("check\n")
    await query.answer("Проверяю…")
    await show_screen(query, context, "⏳ Спрашиваю регистратора…",
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("🔄 Обновить",
                                                 callback_data="psub_zone")]]),
                      parse_mode=ParseMode.MARKDOWN)
    for _ in range(60):
        await asyncio.sleep(1)
        if os.path.exists(ZONE_RESULT):
            break
    await zone_screen(update, context)

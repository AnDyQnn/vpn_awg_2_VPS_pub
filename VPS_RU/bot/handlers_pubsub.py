# -*- coding: utf-8 -*-
"""Домен и сертификаты: экран в администрировании.

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
    """Главный экран раздела: где мы стоим и что делать дальше.

    Раньше здесь была только подписка наружу, и экран рассказывал про неё. Но
    настроек стало три — имя, сертификаты, доступ снаружи, — и связаны они
    порядком: без имени нет хорошего сертификата, без сертификата нет ни
    покрытия внутренних имён, ни своей маски.

    Поэтому экран устроен как путь, а не как список тумблеров: пока шаг не
    сделан, он назван шагом и стоит первым. Сделан — превращается в строку
    состояния.
    """
    query = update.callback_query
    on = is_on()
    st = state()
    have = current_domain()
    wild = wildcard_on()

    lines = ["🌐 **Домен и сертификаты**", ""]

    # --- Где мы стоим. Три строки, по одной на настройку ---
    lines.append("**Имя узла:** `%s`" % have if have
                 else "**Имя узла:** не задано — работаем по IP-адресу")

    left = cert_days_left()
    named = cert_named()
    if not on:
        lines.append("**Сертификат:** нет — доступ снаружи закрыт")
    else:
        # Что за сертификат стоит СЕЙЧАС — по самому сертификату, а не по тому,
        # вписан ли домен. Между этими двумя вещами лежит отдельный шаг.
        if wild:
            what = "на имя и «звёздочку»"
        elif named:
            what = "на имя"
        else:
            what = "на адрес"
        srok = ("осталось %.1f сут." % left) if left is not None \
            else "срок не читается"
        lines.append("**Сертификат:** %s, %s" % (what, srok))
        if have and not named:
            lines.append("     ⚠️ _Имя задано, но сертификат ещё прежний — "
                         "нажмите «Обновить сертификат»._")
        if left is not None and left < 1:
            lines.append("     ⚠️ _Меньше суток. Проверьте таймер продления: "
                         "`systemctl list-timers vpn-subcert`._")

    if have:
        lines.append("**Внутренние имена:** " + (
            "покрыты сертификатом" if wild
            else "**без сертификата** — браузер ругается на наши страницы"))

    port = st.get("port", 2096)
    # Не просто «открыт/закрыт»: само слово ничего не объясняет, а решение по
    # нему принимают. Говорим, что это значит для человека.
    lines.append("**Доступ снаружи:** " + (
        ("открыт, порт `%s` — люди обновляют профиль даже с выключенным VPN"
         % port) if on else
        "закрыт — профиль обновляется только из туннеля"))

    # --- Что делать дальше. Только когда есть что ---
    # Что делать дальше — одной строкой. Подробности живут в документации, а
    # экран настройки не место для рассказа, зачем эта настройка нужна: сюда
    # приходят уже решившими и ищут, что нажать.
    if not have:
        lines += ["", "**Дальше:** купить домен, направить его A-записью на "
                      "этот сервер, вписать имя кнопкой ниже."]
    elif not named:
        lines += ["", "**Дальше:** «Обновить сертификат» — он выпустится уже "
                      "на имя. Занимает несколько минут."]
    elif not wild:
        lines += ["", "**Дальше:** доступ к зоне домена — вторая кнопка. "
                      "Пароль бот придумает сам."]
    elif not on:
        lines += ["", "**Дальше:** открыть доступ снаружи, иначе подписка "
                      "читается только из туннеля."]
    else:
        lines += ["", "Всё настроено."]
        try:
            import subscription
            shut = subscription.blocked_now()
            if shut:
                lines.append(f"Закрыто адресов за назойливость: **{shut}**")
        except Exception:
            pass

    msg = (st.get("msg") or "").strip()
    if msg and st.get("state") == "error":
        lines += ["", f"⚠️ Последняя попытка: _{msg}_"]

    # --- Кнопки. Невыполненный шаг назван шагом и стоит первым ---
    kb = []
    if not have:
        kb.append([InlineKeyboardButton("1️⃣ Вписать имя узла",
                                        callback_data="psub_domain")])
    else:
        kb.append([InlineKeyboardButton("🌐 Имя узла · " + have,
                                        callback_data="psub_domain")])
        if wild:
            kb.append([InlineKeyboardButton(
                "🔑 Сертификат внутренних имён · есть",
                callback_data="psub_zone")])
        else:
            kb.append([InlineKeyboardButton(
                "2️⃣ Сертификат внутренних имён",
                callback_data="psub_zone")])

    if on:
        kb.append([InlineKeyboardButton("🔄 Обновить сертификат",
                                        callback_data="psub_renew")])
        kb.append([InlineKeyboardButton("🔒 Закрыть доступ снаружи",
                                        callback_data="psub_off")])
    else:
        kb.append([InlineKeyboardButton("🌐 Открыть доступ снаружи",
                                        callback_data="psub_on")])

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
    taken = False
    for _ in range(90):
        await asyncio.sleep(1)
        if not os.path.exists(flag):
            # Демон забрал просьбу. Дадим скрипту доработать и покажем итог.
            taken = True
            await asyncio.sleep(3)
            break

    if not taken:
        # Просьба всё ещё лежит. Ждать дальше незачем — выпуск сертификата
        # занимает минуты, а экран не должен висеть столько. Но и молчать
        # нельзя: молчание здесь читается как «кнопка не работает».
        busy = os.path.exists(os.path.join(FLAGS_DIR, "do_update"))
        why = ("сейчас идёт обновление системы" if busy
               else "демон занят другой задачей")
        await show_screen(
            query, context,
            "⏳ **Просьба принята, но ещё не выполнена**\n\n"
            "Служба на сервере одна на все задачи, и %s. Ваша просьба в "
            "очереди и не потеряется — выполнится сама.\n\n"
            "_Выпуск сертификата занимает несколько минут: временная запись "
            "должна разойтись по серверам имён. Загляните сюда через "
            "пять-десять минут._" % why,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 Проверить сейчас",
                                       callback_data="psub_menu")]]),
            parse_mode=ParseMode.MARKDOWN)
        return

    await screen(update, context)


def status_line():
    """Строка для экрана администрирования и для отчёта проверки."""
    if not is_on():
        return "🌐 *Домен и сертификаты:* доступ снаружи закрыт"
    left = cert_days_left()
    tail = (", сертификат на %.1f сут." % left) if left is not None else ""
    if left is not None and left < 1:
        tail += " ⚠️"
    return "🌐 *Домен и сертификаты:* доступ снаружи открыт" + tail


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
        "Что нужно до того, как вписывать:",
        "",
        "1. Домен куплен.",
        "2. A-запись `@` ведёт на адрес этого сервера.",
        "3. Запись разошлась — обычно от часа до суток.",
        "",
        "_Если имя ещё не отвечает, сертификат на него не выпустится: подписка "
        "останется на адресе, и я скажу об этом. Ничего не сломается._",
    ]
    kb = [[InlineKeyboardButton("✏️ Задать имя", callback_data="psub_domain_set")]]
    if have:
        kb.append([InlineKeyboardButton("🗑 Убрать имя",
                                        callback_data="psub_domain_off")])
    kb.append([InlineKeyboardButton("🔙 Домен и сертификаты",
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
            [[InlineKeyboardButton("🔙 Домен и сертификаты",
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


def cert_named():
    """Выписан ли нынешний сертификат на ИМЯ, а не на адрес.

    Спрашиваем сам сертификат, а не настройки: между «домен вписан» и
    «сертификат выпущен на домен» лежит отдельный шаг, и пока он не сделан,
    сертификат остаётся прежним. Экран, показывающий намерение вместо факта,
    хуже отсутствующего — по нему нельзя понять, сделан шаг или нет.
    """
    return bool(state().get("named"))


def zone_check_result():
    try:
        with open(ZONE_RESULT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


async def zone_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сертификат на внутренние имена: что сделать, а не зачем это нужно.

    Зачем — в документации. Здесь человек уже решил и ищет, что нажать; лекция
    на экране действия только прячет нужное.
    """
    query = update.callback_query
    have_domain = bool(current_domain())
    api = zone_api_on()
    wild = wildcard_on()

    lines = ["🔑 **Сертификат внутренних имён**", ""]
    if not have_domain:
        lines += ["Сначала нужно имя узла — без него этого шага не существует."]
    elif wild:
        lines += ["Состояние: **есть**. Наши страницы открываются без "
                  "предупреждения браузера."]
    elif api:
        lines += ["Доступ к зоне задан, сертификата ещё нет.", "",
                  "**Дальше:** «Проверить доступ», затем «Обновить сертификат» "
                  "в разделе выше."]
    else:
        lines += [
            "Без него страница отказа, «доступ закрыт» и выдача ключей "
            "открываются с красным замком.", "",
            "**Что сделать — по порядку:**",
            "",
            "1. В reg.ru → «Настройки API»:",
            "   `reg.ru/user/account/#/settings/api/`",
            "2. Там «Диапазоны IP-адресов» → добавить адрес этого сервера.",
            "3. Там же «Альтернативный пароль» → «Настроить».",
            "4. Здесь кнопкой ниже: логин, потом пароль.",
            "",
            "_Логин — тот, которым входите в reg.ru. Если входите по почте, "
            "почта и есть логин._",
        ]

    res = zone_check_result()
    if res:
        mark = "✅" if res.get("ok") else "⚠️"
        lines += ["", f"{mark} Проверка: {res.get('msg', '—')}"]

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
    kb.append([InlineKeyboardButton("🔙 Домен и сертификаты",
                                    callback_data="psub_menu")])
    await show_screen(query, context, chr(10).join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)



async def zone_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Спрашиваем логин. Про пароль спросим следующим шагом — там выбор."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_regru_user"
    await show_screen(
        query, context,
        "✏️ **Логин в reg.ru**\n\nОдной строкой.\n\n"
        "_Если входите в reg.ru по почте — почта и есть логин, её и пишите._",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="psub_zone")]]),
        parse_mode=ParseMode.MARKDOWN)


def make_password(length: int = 16) -> str:
    """Придумывает пароль для API — так же, как бот придумывает токен панелей.

    Только буквы и цифры, и это осознанно. Пароль проезжает через поле в чужой
    панели, через JSON регистратора и через оболочку на хосте; знак, который
    где-то из этой цепочки имеет своё значение, ломает всё в самом неудобном
    месте — на продлении сертификата через три месяца.

    Шестнадцать знаков, а не сорок. Сорок reg.ru не принимает — отвечает
    «пароль слишком длинный», а предела своего нигде не пишет. Шестнадцать из
    шестидесяти двух — это девяносто пять бит, и подбирать их всё равно
    неоткуда: перед API стоит список разрешённых адресов. Длина здесь не то,
    что нас защищает.

    Все три вида знаков — обязательно: чужие панели часто требуют именно их.
    """
    import secrets
    import string
    abc = string.ascii_letters + string.digits
    while True:
        out = "".join(secrets.choice(abc) for _ in range(length))
        if (any(c.isupper() for c in out) and any(c.islower() for c in out)
                and any(c.isdigit() for c in out)):
            return out


async def zone_password_step(context, chat_id):
    """Выбор: придумать пароль здесь или вписать уже готовый.

    Придумать здесь — короче на один поход в панель и надёжнее: пароль, который
    человек сочиняет сам, обычно тот же, что и везде, а этот лежит на сервере.
    """
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔑 **Пароль для API**\n\nЭто НЕ пароль от кабинета — в reg.ru "
             "он задаётся отдельно: «Настройки API» → «Альтернативный "
             "пароль».\n\nМогу придумать его сам — останется вставить в "
             "панель.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Придумать пароль",
                                  callback_data="psub_zone_gen")],
            [InlineKeyboardButton("✏️ Вписать свой",
                                  callback_data="psub_zone_own")],
            [InlineKeyboardButton("✖️ Отмена", callback_data="psub_zone")],
        ]))


async def zone_own(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Владелец задал пароль в панели сам — ждём его текстом."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_regru_password"
    await query.answer()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✏️ Пришлите пароль для API одной строкой.\n\n"
             "_Сообщение удалю сразу, как прочитаю._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="psub_zone")]]))


async def zone_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Придумывает пароль, кладёт его на сервер и показывает владельцу.

    Порядок именно такой: сначала записали, потом показали. Показать и не
    записать значит оставить человека с паролем, который он вставит в панель, а
    на сервере его не будет — и выпуск сертификата провалится без всякой
    видимой причины.
    """
    from utils import send_copyable
    query = update.callback_query
    chat_id = update.effective_chat.id
    user = context.user_data.get("regru_user", "")
    if not user:
        await query.answer("Логин потерялся — начните заново", show_alert=True)
        return await zone_screen(update, context)

    password = make_password()
    try:
        zone_creds_write(user, password)
    except Exception as e:
        await query.answer("Не записалось: %s" % e, show_alert=True)
        return
    context.user_data["state"] = None
    await query.answer("Придумал")
    await db.log_event("Подписки", "Задан доступ к зоне домена (пароль придуман)")

    await context.bot.send_message(
        chat_id=chat_id,
        text="🔑 **Вот пароль. Скопируйте и вставьте его в reg.ru.**\n\n"
             "«Альтернативный пароль» → «Настроить»:\n"
             "`reg.ru/user/account/#/settings/api/`",
        parse_mode=ParseMode.MARKDOWN)
    await send_copyable(context.bot, chat_id, password)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Здесь он уже записан — на сервере, файлом, только для владельца.\n\n"
             "Как вставите в панель, нажмите «Проверить доступ»: положу в зону "
             "временную запись и тут же уберу. Так опечатка находится за "
             "секунды, а не в середине выпуска сертификата.\n\n"
             "_Это сообщение с паролем можно удалить, как только вставите: "
             "перечитывать его больше неоткуда и незачем._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔍 Проверить доступ",
                                   callback_data="psub_zone_check")],
             [InlineKeyboardButton("🔙 Назад", callback_data="psub_zone")]]))


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

# -*- coding: utf-8 -*-
"""Экраны второго протокола: подключения человека и управление Xray.

Правило то же, что и на остальных экранах: ничего необратимого без показанных
последствий. Поэтому выключение протокола сначала говорит, у скольких человек
оборвётся связь, и только потом даёт кнопку; отключение AmneziaWG у человека
недоступно, пока он ни разу не подключился по Xray.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import xray
from database import db
from utils import (exit_kb, escape_md, show_screen, send_copyable,
                   copy_button)

BACK_SERVICE = [InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]


def _ago(sec):
    if sec is None:
        return "ни разу"
    if sec < 60:
        return f"{sec} сек назад"
    if sec < 3600:
        return f"{sec // 60} мин назад"
    if sec < 86400:
        return f"{sec // 3600} ч назад"
    return f"{sec // 86400} дн назад"


def connections_block(state):
    """Блок «Подключения» для карточки человека. Отдельной функцией — он нужен
    и в карточке, и на экране подключений, и расходиться они не должны."""
    lines = ["🔌 **Подключения:**"]
    if state["awg_ip"]:
        mark = "🟢" if (state["awg_handshake"] is not None
                        and state["awg_handshake"] < 180) else "⚪"
        lines.append(f"  {mark} AmneziaWG — {_ago(state['awg_handshake'])}")
    else:
        lines.append("  ▫️ AmneziaWG — не выдан")

    if not state["has_xray"]:
        lines.append("  ▫️ Xray — не выдан")
    elif state["xray_online"]:
        lines.append("  🟢 Xray — на связи")
    elif state["xray_seen"]:
        lines.append("  ⚪ Xray — подключался, сейчас нет")
    else:
        lines.append("  🟡 Xray — выдан, ни разу не подключался")
    return "\n".join(lines)


# --- ЭКРАН ПОДКЛЮЧЕНИЙ ОДНОГО ЧЕЛОВЕКА ------------------------------------
async def connections_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Человек не найден", show_alert=True)
        return

    state = await xray.person_state(uuid_val)
    lines = [f"🔌 **Подключения · {escape_md(user['name'])}**", "",
             connections_block(state), ""]

    if state["has_xray"]:
        url = await xray.subscription_url(state["sub_token"])
        lines.append("Адрес подписки выдан. Он постоянный и переживает "
                     "перевыпуск: приложение забирает по нему новый ключ само, "
                     "человеку делать нечего.")
        if url:
            lines.append("Подписка обновляется по личному адресу автоматически.")
        else:
            lines.append("_Автообновление выключено: адрес сервера подписок не "
                         "задан. Профиль работает, но изменения придётся "
                         "высылать заново._")
    else:
        lines.append("Xray этому человеку ещё не выдавали.")

    kb = []
    if state["has_xray"]:
        kb.append([InlineKeyboardButton("📨 Выслать ссылку", callback_data=f"xr_send_{uuid_val}")])
        # Не «ссылку»: она как раз остаётся. Меняется ключ доступа — старый
        # перестаёт работать, а адрес у человека прежний.
        kb.append([InlineKeyboardButton("♻️ Перевыпустить ключ",
                                        callback_data=f"xr_issue_{uuid_val}")])
        # Отключить AmneziaWG можно только тому, кто уже доехал по Xray.
        if state["awg_ip"]:
            if state["xray_seen"]:
                kb.append([InlineKeyboardButton("🔻 Убрать AmneziaWG",
                                                callback_data=f"xr_dropawg_{uuid_val}")])
            else:
                kb.append([InlineKeyboardButton("🔒 Убрать AmneziaWG — рано",
                                                callback_data=f"xr_why_{uuid_val}")])
    else:
        kb.append([InlineKeyboardButton("➕ Выдать Xray", callback_data=f"xr_issue_{uuid_val}")])

    kb.append([InlineKeyboardButton("🔙 К человеку", callback_data=f"user_detail_{uuid_val}")])
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def why_locked(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    await update.callback_query.answer(
        "Человек ещё ни разу не подключился по Xray. Уберём AmneziaWG сейчас — "
        "останется без связи вовсе.", show_alert=True)


async def issue_xray(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    await query.answer("Выдаю…")
    ok, res = await xray.issue(uuid_val)
    if ok:
        # Адрес-двойник заводится в момент выдачи: раскладка ограничений на
        # узле про него ещё ничего не знает.
        from restrictions import reapply
        await reapply("выдана ссылка Xray")
    if not ok:
        await query.answer(f"Не вышло: {res}", show_alert=True)
        return
    await connections_screen(update, context, uuid_val)


async def send_link(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Отправляет человеку ссылку и QR в личные сообщения."""
    query = update.callback_query
    await query.answer("Готовлю…")

    user = await db.get_user_by_uuid(uuid_val)
    # Тот же кусок, что уходит человеку: сервера и профиль маршрутизации.
    # Иначе владелец пересылает одно, а бот отдаёт другое — и разбираться,
    # почему у человека нет сплита, приходится вслепую.
    link = await xray.bundle_text(uuid_val)
    if not link:
        await query.answer("Ссылка не собралась: проверьте адрес сервера в настройках",
                           show_alert=True)
        return
    qr = await xray.qr_file(uuid_val)

    text = await instructions(uuid_val)

    from delivery import track_send
    sent = 0
    for tid in (user.get("tg_ids") or []):
        async def _send(tid=tid):
            await context.bot.send_message(chat_id=tid, text=text,
                                           parse_mode=ParseMode.MARKDOWN,
                                           disable_web_page_preview=True)
            if qr:
                await context.bot.send_photo(chat_id=tid, photo=open(qr, "rb"))
            # Ссылку отдельным сообщением и кодом: так она не ломается о
            # собственные подчёркивания. А рядом — кнопка «скопировать»:
            # адрес подписки некоторые клиенты Telegram делают нажимаемым
            # прямо в коде, и человек, ткнув в него, попадал в браузер и видел
            # гору base64 вместо подписки.
            await send_copyable(context.bot, tid, link,
                                reply_markup=InlineKeyboardMarkup(
                                    [[copy_button(link)]]))
        ok, err = await track_send(uuid_val, tid, _send)
        sent += 1 if ok else 0

    if not sent:
        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text=f"{user['name']} — Telegram не привязан, "
                                            f"ссылка ниже")
        await send_copyable(context.bot, query.message.chat_id, link,
                            reply_markup=InlineKeyboardMarkup(
                                [[copy_button(link)]]))
    await query.answer("Отправлено" if sent else "Telegram не привязан — ссылка здесь")
    await connections_screen(update, context, uuid_val)


async def drop_awg(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Снимает пир AmneziaWG человеку, который уже переехал."""
    query = update.callback_query
    state = await xray.person_state(uuid_val)
    if not state["xray_seen"]:
        return await why_locked(update, context, uuid_val)

    await query.answer("Убираю…")
    from utils import api_session, WG_API_URL
    try:
        async with api_session() as session:
            async with session.delete(f"{WG_API_URL}/peers/{uuid_val}", timeout=15) as r:
                if r.status != 200:
                    await query.answer(f"Узел отказал: {await r.text()}", show_alert=True)
                    return
    except Exception as e:
        await query.answer(f"Узел недоступен: {e}", show_alert=True)
        return
    await db.log_event("Xray", f"Пир AmneziaWG снят: {uuid_val}")
    await connections_screen(update, context, uuid_val)


# --- АДМИНИСТРИРОВАНИЕ ПРОТОКОЛОВ -----------------------------------------
async def protocols_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    st = await xray.status()

    lines = ["🔀 **Протоколы**", ""]
    if st.get("error"):
        lines.append(f"Узел не ответил: `{escape_md(str(st['error']))}`")
        kb = [BACK_SERVICE]
    else:
        awg, xr = st.get("awg", {}), st.get("xray", {})
        total = await db.fetch_val("SELECT COUNT(*) FROM users") or 0
        on_xray = await db.count_xray_users()
        online_xray = len(await xray.online_uuids())

        lines += [
            f"🔷 **AmneziaWG** — {'включён' if awg.get('enabled') else 'выключен'}",
            f"  пиров: {max(awg.get('peers', 0), 0)} · интерфейс "
            f"{'поднят' if awg.get('up') else 'опущен'}",
            "",
            f"🔶 **Xray** — {'включён' if xr.get('enabled') else 'выключен'}",
            f"  людей: {on_xray} из {total} · на связи: {online_xray} · "
            f"соединений: {xr.get('connections', 0)}",
        ]
        if xr.get("enabled") and not xr.get("up"):
            lines.append("  ⚠️ протокол включён, но процесс не работает")

        kb = [[InlineKeyboardButton("🔷 AmneziaWG", callback_data="proto_awg"),
               InlineKeyboardButton("🔶 Xray", callback_data="proto_xray")],
              [InlineKeyboardButton("🚚 Перевод людей на Xray", callback_data="xr_move")],
              BACK_SERVICE]

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def awg_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    st = await xray.status()
    awg = st.get("awg", {})

    obf = awg.get("obfuscation") or {}
    # Обфускация — это и есть то, чем AmneziaWG отличается от обычного
    # WireGuard, поэтому показываем её параметры, а не факт «включена».
    obf_line = " · ".join(f"{k}={v}" for k, v in obf.items()) if obf else "не задана"
    online = awg.get("online", -1)

    lines = ["🔷 **AmneziaWG**", "",
             "Туннель на уровне IP. Остаётся для шлюзов, роутеров и всех, кому "
             "нужен не только браузер.", "",
             f"Состояние: **{'включён' if awg.get('enabled') else 'выключен'}**",
             f"Интерфейс: {'поднят' if awg.get('up') else 'опущен'} · "
             f"порт `{awg.get('port') or '—'}`",
             f"Пиров: {max(awg.get('peers', 0), 0)}"
             + (f" · на связи: {online}" if online >= 0 else ""),
             f"Обфускация: `{escape_md(obf_line)}`"]

    kb = [[InlineKeyboardButton("🔑 Переезд на новый ключ", callback_data="mig_menu")]]
    if awg.get("enabled"):
        kb.append([InlineKeyboardButton("⏹ Выключить протокол", callback_data="proto_off_awg")])
    else:
        kb.append([InlineKeyboardButton("▶️ Включить протокол", callback_data="proto_on_awg")])
    kb.append([InlineKeyboardButton("🔙 Протоколы", callback_data="proto_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def xray_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    st = await xray.status()
    xr = st.get("xray", {})
    cfg = await xray.settings()
    base = await xray.subscription_base()

    lines = ["🔶 **Xray**", "",
             "Вход, неотличимый от обычного HTTPS. Подписка обновляется сама — "
             "ради этого всё и делалось.", "",
             f"Состояние: **{'включён' if xr.get('enabled') else 'выключен'}**",
             f"Процесс: {'работает' if xr.get('up') else 'не работает'}",
             f"Порт: `{cfg['port']}` · маска: `{escape_md(cfg['dest'])}`",
             f"Людей: {await db.count_xray_users()} · "
             f"соединений: {xr.get('connections', 0)}",
             ""]
    lines.append(f"Подписки: `{escape_md(base)}`" if base
                 else "Подписки: _адрес не задан, автообновление выключено_")
    lines.append("Приложение: Happ, ссылки на все системы")

    kb = [[InlineKeyboardButton("🔄 Применить конфиг заново", callback_data="xr_apply")],
          [InlineKeyboardButton("🎭 Маска входа", callback_data="xr_mask"),
           InlineKeyboardButton("📱 Приложения", callback_data="xr_apps")]]
    if xr.get("enabled"):
        kb.append([InlineKeyboardButton("⏹ Выключить протокол", callback_data="proto_off_xray")])
    else:
        kb.append([InlineKeyboardButton("▶️ Включить протокол", callback_data="proto_on_xray")])
    kb.append([InlineKeyboardButton("🔙 Протоколы", callback_data="proto_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


# Маски, проверенные с узла: TLS 1.3, X25519, HTTP/2 — всё, что требует Reality.
# Время отклика измерено оттуда же. Порядок — от меньшего риска к большему.
MASKS = [
    ("avito.ru", "75 мс", "быстрее всех, пул из 5 имён"),
    ("wildberries.ru", "93 мс", "маркетплейс, крупные передачи выглядят своими"),
    ("sberbank.ru", "101 мс", "банк: такое не блокируют никогда"),
    ("vk.com", "116 мс", "у всех и всегда, пул из 3 имён"),
    ("ozon.ru", "125 мс", "маркетплейс, то же самое"),
    ("kinopoisk.ru", "156 мс", "видео, длинные передачи естественны"),
]


async def mask_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор домена, которым прикидывается вход."""
    query = update.callback_query
    cfg = await xray.settings()
    cur = cfg["dest"]

    lines = ["🎭 **Маска входа**", "",
             "Домен, которым вход прикидывается для наблюдателя со стороны. "
             "Его же видит проверяющий, если решит постучаться на порт.", "",
             f"Сейчас: `{escape_md(cur)}`", "",
             "Выбирать стоит то, что не отключат и не заблокируют: если домен "
             "перестанет отвечать с узла, люди продолжат работать, а вот "
             "защита от проверки отвалится — и молча.", "",
             "Узел стоит в России, поэтому российские домены правдоподобнее: "
             "домашний хостинг, отдающий зарубежный сайт, выглядит страннее. "
             "И отвечают они втрое быстрее — а отклик видит именно "
             "проверяющий.", "",
             "_Где есть пул — каждому человеку достаётся своё имя из него, и "
             "снаружи трафик не выглядит обращением всех к одному адресу. "
             "Имена в пуле — поддомены одного домена: ляжет он — ляжет пул._",
             ""]

    issued = await db.count_xray_users()
    if issued:
        lines.append(f"⚠️ Ключей уже выдано: {issued}. Смена маски меняет "
                     "ссылку. У тех, кто подключён по подписке, она обновится "
                     "сама; у остальных придётся перевыдать.")
        lines.append("")

    kb = []
    for host, ping, note in MASKS:
        mark = "✅ " if host == cur else ""
        pool = len(xray.mask_names(host))
        kb.append([InlineKeyboardButton(f"{mark}{host} · {ping}",
                                        callback_data=f"xr_mask_{host}")])
        tail = f" · имён в пуле: {pool}" if pool > 1 else ""
        lines.append(f"• `{escape_md(host)}` — {note}{tail}")
    kb.append([InlineKeyboardButton("🔙 Xray", callback_data="proto_xray")])

    await show_screen(query, context, chr(10).join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def mask_set(update: Update, context: ContextTypes.DEFAULT_TYPE, host):
    """Ставит выбранную маску и сразу применяет конфиг."""
    query = update.callback_query
    known = [h for h, _p, _n in MASKS]
    if host not in known:
        await query.answer("Неизвестная маска", show_alert=True)
        return
    cur = await xray.settings()
    if cur["dest"] == host:
        await query.answer("Эта маска уже стоит")
        await mask_screen(update, context)
        return

    await db.set_setting("xray_dest", host)
    await query.answer("Применяю…")
    ok, msg = await xray.apply_config(f"смена маски на {host}")
    await db.log_event("Xray", f"Mask changed to {host}: {msg}")
    await query.answer(msg, show_alert=not ok)
    await mask_screen(update, context)


async def apply_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Применяю…")
    ok, msg = await xray.apply_config("вручную")
    await query.answer(msg, show_alert=not ok)
    await xray_screen(update, context)


async def apps_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """То же, что видит человек. Показывается владельцу, чтобы он мог глазами
    проверить, куда именно отправляет родню."""
    query = update.callback_query
    lines = ["📱 **Приложение Happ**", "",
             "Один клиент на все платформы — его ссылки и уходят людям "
             "вместе с профилем:", "",
             xray.apps_markdown(await xray.apps_list()), "",
             "_Ссылки официальные: магазины приложений и релизы разработчика._"]

    kb = [[InlineKeyboardButton("🔙 Xray", callback_data="proto_xray")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN,
                      disable_preview=True)


# --- ВЫКЛЮЧАТЕЛИ ----------------------------------------------------------
async def switch_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, name):
    """Спрашивает подтверждение, показав, у скольких людей оборвётся связь."""
    query = update.callback_query
    if name == "awg":
        st = await xray.status()
        count = max(st.get("awg", {}).get("peers", 0), 0)
        who = f"пиров AmneziaWG: **{count}**"
        title = "🔷 Выключить AmneziaWG?"
    else:
        count = len(await xray.online_uuids())
        who = f"на связи по Xray сейчас: **{count}**"
        title = "🔶 Выключить Xray?"

    text = (f"{title}\n\n"
            f"Связь оборвётся у всех, кто сидит на этом протоколе прямо сейчас. "
            f"{who}\n\n"
            f"Включить обратно можно здесь же — ключи и ссылки никуда не денутся.")
    kb = [[InlineKeyboardButton("⏹ Да, выключить", callback_data=f"proto_offok_{name}")],
          [InlineKeyboardButton("Отмена", callback_data=f"proto_{name}")]]
    await show_screen(query, context, text,
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def switch_do(update: Update, context: ContextTypes.DEFAULT_TYPE, name, enabled):
    query = update.callback_query
    await query.answer("Минуту…")
    ok, msg = await xray.switch(name, enabled)
    await query.answer(msg, show_alert=not ok)
    if name == "awg":
        await awg_screen(update, context)
    else:
        await xray_screen(update, context)


# --- ПЕРЕВОД ЛЮДЕЙ --------------------------------------------------------
async def move_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перевод по одному, по образцу переезда на новый ключ: выдали → ждём
    живого подключения → только потом убираем старое."""
    query = update.callback_query
    # Только живые: приостановленному переезжать незачем, а в цифре, по
    # которой решают «кого ещё перевести», он только мешает.
    users = [u for u in await db.get_all_users() if u.get("is_active")]
    issued = {r["user_uuid"]: r for r in await db.list_xray_users()}

    moved, waiting, untouched = [], [], []
    for u in users:
        rec = issued.get(u["uuid"])
        if not rec:
            untouched.append(u["name"])
        elif rec["first_seen_at"]:
            moved.append(u["name"])
        else:
            waiting.append(u["name"])

    lines = ["🚚 **Перевод людей на Xray**", "",
             f"Переехали: **{len(moved)}**",
             f"Выдано, но ещё не подключались: **{len(waiting)}**",
             f"Не выдавали: **{len(untouched)}**", ""]
    if waiting:
        lines.append("Ждём: " + escape_md(", ".join(waiting[:12]))
                     + ("…" if len(waiting) > 12 else ""))
    if untouched:
        lines.append("Не выдавали: " + escape_md(", ".join(untouched[:12]))
                     + ("…" if len(untouched) > 12 else ""))
    lines += ["", "_«Переехал» считается по живому подключению, а не по факту "
                  "выдачи ссылки. AmneziaWG у человека снимается вручную, из его "
                  "карточки, и только после переезда._"]

    kb = [[InlineKeyboardButton("👥 К списку людей", callback_data="users_page_0")],
          [InlineKeyboardButton("🔙 Протоколы", callback_data="proto_menu")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


# --- ВЫДАЧА ССЫЛКИ --------------------------------------------------------
# Короткие обозначения платформ для кнопок: в callback_data 64 байта, и
# русские названия туда не влезут вместе с идентификатором человека.
PLATFORM_KEYS = {
    "ios": "iPhone / iPad",
    "android": "Android",
    "win": "Windows",
    "mac": "macOS",
    "linux": "Linux",
}


def platform_keyboard(uuid_val, back=None):
    """Кнопки выбора системы. По две в ряд — так они остаются читаемыми
    и на телефоне, и на десктопе."""
    keys = list(PLATFORM_KEYS.items())
    rows, pair = [], []
    for key, title in keys:
        pair.append(InlineKeyboardButton(title, callback_data=f"client_plat_{key}_{uuid_val}"))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    if back:
        rows.append([InlineKeyboardButton("🔙 Назад", callback_data=back)])
    return InlineKeyboardMarkup(rows)


async def instructions(uuid_val=None, platform=None):
    """Три шага, которые человек делает один раз.

    Без выбранной системы показываем все — это случай владельца, который
    смотрит, что именно уходит людям. Человеку же приходит один набор: его."""
    apps = await xray.apps_list()
    lines = ["🔑 **Ваш доступ к VPN**", ""]
    if platform and PLATFORM_KEYS.get(platform) in apps:
        title = PLATFORM_KEYS[platform]
        links = " · ".join(f"[{label}]({url})" for label, url in apps[title])
        lines.append(f"**1.** Поставьте приложение **Happ** для {title}: {links}")
    else:
        lines.append("**1.** Поставьте приложение **Happ** — выберите свою систему:")
        lines.append(xray.apps_markdown(apps))
    # Когда подписка открыта наружу, человек получает один адрес — и дальше
    # приложение обновляет себя само. Про это стоит сказать: иначе при первом
    # же изменении он будет ждать нового сообщения, которого не будет.
    one_address = bool(uuid_val) and bool(await xray.public_sub_url(uuid_val))
    lines += [
        "**2.** Отсканируйте картинку ниже или скопируйте текст под ней — "
        "профиль добавится сам",
        "**3.** Включите VPN в приложении",
    ]
    if one_address:
        lines += [
            "",
            "Больше ничего делать не нужно: новые сервера и настройки "
            "приложение подтянет само.",
        ]
    lines += [
        "",
        "⚠️ Ссылка личная. По ней подключаются к вашему доступу — "
        "не передавайте её никому.",
    ]
    return "\n".join(lines)


async def handout(update, context, uuid_val, name, tg_id=None):
    """Выдаёт человеку подключение по Xray и рассылает ссылку.

    Владельцу — всегда: если Telegram у человека не привязан, ссылку надо
    передать как-то иначе, и она должна быть под рукой."""
    chat_id = update.effective_chat.id
    ok, res = await xray.issue(uuid_val)
    if ok:
        # Адрес-двойник заводится в момент выдачи: раскладка ограничений на
        # узле про него ещё ничего не знает.
        from restrictions import reapply
        await reapply("выдана ссылка Xray")
    if not ok:
        await context.bot.send_message(chat_id=chat_id,
                                       text=f"⚠️ Ключ создан, но Xray не выдан: {res}",
        reply_markup=exit_kb(("👥 Люди", "list_users")))
        return False

    # Тот же кусок, что уходит человеку: сервера и профиль маршрутизации.
    # Иначе владелец пересылает одно, а бот отдаёт другое — и разбираться,
    # почему у человека нет сплита, приходится вслепую.
    link = await xray.bundle_text(uuid_val)
    if not link:
        # Пустой текст Telegram не принимает: раньше здесь падала вся выдача, и
        # ссылки не оставалось ни у владельца, ни у человека. Причина всегда
        # одна — неизвестен адрес, по которому до узла достучатся снаружи.
        await context.bot.send_message(
            chat_id=chat_id,
            text=("\u26a0\ufe0f Ключ создан, но ссылку собрать не вышло.\n\n"
                  "Не задан адрес сервера для Xray. Он берётся из конфигов "
                  "AmneziaWG сам; если конфигов ещё нет, задайте его вручную."),
            reply_markup=exit_kb(("\U0001f465 Люди", "list_users")))
        return False

    qr = await xray.qr_file(uuid_val)
    text = await instructions(uuid_val)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ **Ключ создан: {escape_md(name)}**\n\nВыдан по Xray — ссылкой.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=exit_kb(("👥 Люди", "list_users")))
    if qr:
        await context.bot.send_photo(chat_id=chat_id, photo=open(qr, "rb"))
    # Ссылка отдельным сообщением и кодом: не ломается о собственные
    # подчёркивания. Кнопка «скопировать» кладёт её в буфер по нажатию —
    # раньше человек тыкал в адрес подписки, попадал в браузер и видел гору
    # base64 вместо подписки.
    #
    # Кнопка именно копирующая, а не ссылочная: схему `vless://` Telegram в
    # ссылке не принимает вовсе.
    await send_copyable(context.bot, chat_id, link,
                        reply_markup=InlineKeyboardMarkup([[copy_button(link)]]))

    if tg_id:
        from delivery import track_send

        async def _send():
            # Человеку — то же самое, что при перевыпуске: один адрес
            # подписки. Два разных первых впечатления от одного и того же
            # продукта только путают.
            from handlers_client import send_xray_profile
            if not await send_xray_profile(context, tg_id, uuid_val):
                raise RuntimeError("профиль не собрался")

        sent, err = await track_send(uuid_val, tg_id, _send)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(f"✅ Ссылка отправлена клиенту `{tg_id}`." if sent
                  else f"⚠️ Клиент `{tg_id}` ссылку не получил: `{err}`"),
            parse_mode=ParseMode.MARKDOWN,
        reply_markup=exit_kb(("👥 Люди", "list_users")))

    await context.bot.send_message(
        chat_id=chat_id, text="Готово! Что делаем дальше?",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")]]))
    return True

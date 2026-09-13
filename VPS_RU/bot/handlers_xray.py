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
from utils import escape_md, show_screen

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
        lines.append("Ссылка на профиль выдана. Она постоянная: изменения "
                     "доезжают сами, перевыпускать не нужно.")
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
        kb.append([InlineKeyboardButton("♻️ Перевыпустить (старая умрёт)",
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
    if not ok:
        await query.answer(f"Не вышло: {res}", show_alert=True)
        return
    await connections_screen(update, context, uuid_val)


async def send_link(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Отправляет человеку ссылку и QR в личные сообщения."""
    query = update.callback_query
    await query.answer("Готовлю…")

    user = await db.get_user_by_uuid(uuid_val)
    link = await xray.profile_link(uuid_val)
    if not link:
        await query.answer("Ссылка не собралась: проверьте адрес сервера в настройках",
                           show_alert=True)
        return
    qr = await xray.qr_file(uuid_val)

    text = ("🔑 **Ваш доступ к VPN**\n\n"
            "1. Поставьте приложение для VPN\n"
            "2. Отсканируйте картинку ниже или нажмите на ссылку — профиль "
            "добавится сам\n"
            "3. Включите VPN в приложении\n\n"
            "⚠️ Ссылка личная. По ней подключаются к вашему доступу — "
            "не передавайте её никому.")

    from delivery import track_send
    sent = 0
    for tid in (user.get("tg_ids") or []):
        async def _send(tid=tid):
            await context.bot.send_message(chat_id=tid, text=text,
                                           parse_mode=ParseMode.MARKDOWN)
            if qr:
                await context.bot.send_photo(chat_id=tid, photo=open(qr, "rb"))
            # Ссылку отдельным сообщением и без разметки: подчёркивания в
            # ссылке Telegram принимает за курсив и ломает её.
            await context.bot.send_message(chat_id=tid, text=link)
        ok, err = await track_send(uuid_val, tid, _send)
        sent += 1 if ok else 0

    if not sent:
        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text=f"{user['name']} — Telegram не привязан, "
                                            f"ссылка ниже")
        await context.bot.send_message(chat_id=query.message.chat_id, text=link)
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

    lines = ["🔷 **AmneziaWG**", "",
             "Туннель на уровне IP. Остаётся для шлюзов, роутеров и всех, кому "
             "нужен не только браузер.", "",
             f"Состояние: **{'включён' if awg.get('enabled') else 'выключен'}**",
             f"Интерфейс: {'поднят' if awg.get('up') else 'опущен'}",
             f"Пиров: {max(awg.get('peers', 0), 0)}"]

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
    base = await db.get_setting("xray_sub_base") or ""

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
    lines.append("Приложения: " + ("список утверждён" if await xray.apps_approved()
                                   else "_список не утверждён, людям не показывается_"))

    kb = [[InlineKeyboardButton("🔄 Применить конфиг заново", callback_data="xr_apply")],
          [InlineKeyboardButton("📱 Приложения", callback_data="xr_apps")]]
    if xr.get("enabled"):
        kb.append([InlineKeyboardButton("⏹ Выключить протокол", callback_data="proto_off_xray")])
    else:
        kb.append([InlineKeyboardButton("▶️ Включить протокол", callback_data="proto_on_xray")])
    kb.append([InlineKeyboardButton("🔙 Протоколы", callback_data="proto_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def apply_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Применяю…")
    ok, msg = await xray.apply_config("вручную")
    await query.answer(msg, show_alert=not ok)
    await xray_screen(update, context)


async def apps_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    apps = await xray.apps_list()
    approved = await xray.apps_approved()

    lines = ["📱 **Приложения по платформам**", ""]
    for platform, names in apps.items():
        lines.append(f"**{platform}**: " + escape_md(", ".join(names)))
    lines += ["",
              "Ссылок здесь намеренно нет: отправлять человека по ссылке, "
              "которую никто не проверял, нельзя. Названия ищутся в магазине "
              "приложений.", ""]
    lines.append("Список **утверждён** и показывается людям." if approved
                 else "Список **не утверждён**: человек видит только ссылку на "
                      "профиль, без советов, что ставить.")

    kb = [[InlineKeyboardButton("🚫 Снять утверждение" if approved
                                else "✅ Утвердить список", callback_data="xr_apps_ok")],
          [InlineKeyboardButton("🔙 Xray", callback_data="proto_xray")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def apps_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = await xray.apps_approved()
    await db.set_setting("xray_apps_ok", "0" if now else "1")
    await update.callback_query.answer("Снято" if now else "Утверждено")
    await apps_screen(update, context)


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
    users = await db.get_all_users()
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

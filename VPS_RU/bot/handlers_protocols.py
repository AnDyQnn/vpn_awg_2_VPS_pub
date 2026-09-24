# -*- coding: utf-8 -*-
"""Экран «Протоколы»: два канала связи и всё, что к ним относится.

  • AmneziaWG — свой вход узла. Выключить его отсюда нельзя: это вход по
    умолчанию, и узел без него остался бы без связи у всех, кто на нём сидит.
  • Xray — панель 3X-UI в соседнем контейнере. Включается и выключается
    здесь же; всё остальное бот настраивает в ней сам (см. xui.py).

Правило то же, что на остальных экранах: ничего необратимого без показанных
последствий. Выключение Xray сначала говорит, у скольких людей оборвётся связь.
"""
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import (api_session, WG_API_URL, escape_md, show_screen,
                   request_env_change, env_change_applied, ADMIN_ID,
                   send_copyable, copy_button, exit_kb)
import xui

BACK_SERVICE = [InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]
BACK_PROTO = [InlineKeyboardButton("🔙 Протоколы", callback_data="proto_menu")]
# Кому сообщить, чем кончилось включение: бот при этом перезапускается, и
# экран, с которого нажимали, пропадает вместе с ним.
KEY_NOTIFY = "xui_notify_chat"


async def status():
    """Состояние AmneziaWG с узла. При отказе — {"error": ...}."""
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/awg/status", timeout=10) as r:
                if r.status == 200:
                    return await r.json()
    except Exception as e:
        return {"error": str(e)}
    return {"error": "узел не ответил"}


def status_line(st):
    """Строка для сводки администрирования."""
    if st.get("error"):
        return "🔀 *Протоколы:* узел не ответил"
    awg = st.get("awg") or {}
    line = "🔀 *Протоколы:* AmneziaWG " + ("работает" if awg.get("up") else "НЕ поднят")
    line += ", Xray " + ("включён" if xui.stack_enabled() else "выключен")
    return line


async def protocols_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    st = await status()

    lines = ["🔀 **Протоколы**", ""]
    kb = []
    if st.get("error"):
        lines.append(f"Узел не ответил: `{escape_md(str(st['error']))}`")
    else:
        awg = st.get("awg") or {}
        obf = awg.get("obfuscation") or {}
        # Обфускация — это и есть то, чем AmneziaWG отличается от обычного
        # WireGuard, поэтому показываем её параметры, а не факт «включена».
        obf_line = " · ".join(f"{k}={v}" for k, v in obf.items()) if obf else "не задана"
        online = awg.get("online", -1)
        lines += [
            "🔷 **AmneziaWG**",
            f"Интерфейс: {'поднят' if awg.get('up') else '**опущен**'} · "
            f"порт `{awg.get('port') or '—'}`",
            f"Пиров: {max(awg.get('peers', 0), 0)}"
            + (f" · на связи: {online}" if online >= 0 else ""),
            f"Обфускация: `{escape_md(obf_line)}`",
        ]
        if not awg.get("up"):
            # Интерфейс лежит — кнопка поднять. Выключателя нет намеренно.
            kb.append([InlineKeyboardButton("▶️ Поднять AmneziaWG",
                                            callback_data="proto_on_awg")])

    lines += ["", "🔶 **Xray** · панель 3X-UI"]
    xs = await xui.status()
    if not xs["enabled"]:
        lines.append("Выключен — контейнера панели нет, порты 443 и 2096 закрыты.")
        if xs["people"]:
            lines.append(f"Выдано людям: {xs['people']} — заработает при включении.")
        kb.append([InlineKeyboardButton("▶️ Включить Xray", callback_data="xr_on")])
    else:
        if not xs["panel"]:
            lines.append("Включён, но панель не отвечает — поднимается или сломалась.")
        else:
            ib = xs.get("inbound") or {}
            if ib:
                lines.append(f"Вход: `{ib.get('port')}` · {escape_md(str(ib.get('network')))} "
                             f"· Reality, маска `{escape_md(str(ib.get('target')))}`")
            else:
                lines.append("Входа ещё нет — бот заведёт его сам.")
            lines.append(f"Людей: {xs['people']} · на связи: {xs['online']}")
        kb.append([InlineKeyboardButton("🖥 Панель 3X-UI", callback_data="xr_panel"),
                   InlineKeyboardButton("🤖 Бот панели", callback_data="xr_bot")])
        kb.append([InlineKeyboardButton("🎭 Маска входа", callback_data="xr_mask"),
                   InlineKeyboardButton("🚚 Переезд", callback_data="xr_move")])
        kb.append([InlineKeyboardButton("⏹ Выключить Xray", callback_data="xr_off")])
    kb.append(BACK_SERVICE)
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def awg_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поднимает интерфейс, если он лёг."""
    query = update.callback_query
    await query.answer("Минуту…")
    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/protocols",
                                    json={"name": "awg", "enabled": True},
                                    timeout=30) as r:
                if r.status != 200:
                    await query.answer(f"Узел отказал: {await r.text()}", show_alert=True)
    except Exception as e:
        await query.answer(f"Узел недоступен: {e}", show_alert=True)
    await protocols_menu(update, context)


# --- ВКЛЮЧЕНИЕ И ВЫКЛЮЧЕНИЕ СТЕКА ------------------------------------------

async def xray_on_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = ("▶️ **Включить Xray?**\n\n"
            "Хост скачает образ панели 3X-UI (около полугигабайта — первый раз "
            "это несколько минут), поднимет её рядом с узлом и откроет порты "
            "443 и 2096. Бот при этом перезапустится.\n\n"
            "Дальше бот настроит панель сам: сменит заводской логин, заведёт "
            "вход на 443 и подписку. Итог пришлю отдельным сообщением.\n\n"
            "_AmneziaWG это не касается — он продолжает работать как работал._")
    kb = [[InlineKeyboardButton("▶️ Да, включить", callback_data="xr_on_ok")],
          [InlineKeyboardButton("✖️ Отмена", callback_data="proto_menu")]]
    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def xray_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Включаю…")
    await db.set_setting(KEY_NOTIFY, str(query.message.chat_id))
    flag = request_env_change("COMPOSE_PROFILES", "xray")
    await db.log_event("Xray", "Владелец включил стек Xray")
    await show_screen(query, context,
                      "⏳ **Включаю Xray**\n\nПросьба передана хосту. Сейчас бот "
                      "перезапустится, а когда панель поднимется и настроится — "
                      "пришлю итог сообщением.",
                      reply_markup=InlineKeyboardMarkup([BACK_PROTO]),
                      parse_mode=ParseMode.MARKDOWN)
    if not await env_change_applied(flag, timeout=60):
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="⚠️ Хост не забрал просьбу за минуту. Проверьте демон: "
                 "`systemctl status vpn-updater`", parse_mode=ParseMode.MARKDOWN,
            reply_markup=exit_kb(("🔀 Протоколы", "proto_menu")))


async def xray_off_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    online = len(await xui.online_uuids())
    people = len(await db.list_xui_clients())
    text = ("⏹ **Выключить Xray?**\n\n"
            f"Связь оборвётся у всех, кто сидит на Xray прямо сейчас: **{online}**. "
            f"Выдано людям: {people}.\n\n"
            "Порты 443 и 2096 закроются сразу, контейнер панели уберётся. "
            "Настройки панели, люди и их подписки сохраняются — при включении "
            "всё вернётся как было.")
    kb = [[InlineKeyboardButton("⏹ Да, выключить", callback_data="xr_off_ok")],
          [InlineKeyboardButton("✖️ Отмена", callback_data="proto_menu")]]
    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def xray_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Выключаю…")
    # Ворота закрываем сами и сразу — не дожидаясь хоста.
    try:
        await xui.node_gate(False)
    except Exception as e:
        print(f"Xray: ворота не закрылись: {e}")
    await db.set_setting(KEY_NOTIFY, str(query.message.chat_id))
    request_env_change("COMPOSE_PROFILES", "")
    await db.log_event("Xray", "Владелец выключил стек Xray")
    await show_screen(query, context,
                      "⏹ **Xray выключается**\n\nПорты закрыты. Хост уберёт "
                      "контейнер панели, бот перезапустится.",
                      reply_markup=InlineKeyboardMarkup([BACK_PROTO]),
                      parse_mode=ParseMode.MARKDOWN)


async def on_startup(app):
    """Зовётся при старте бота: привести узел и панель к включённому состоянию.

    Ворота узла выставляются всегда — и при выключенном стеке тоже: так порты
    закрываются даже там, где их когда-то открыли."""
    enabled = xui.stack_enabled()
    try:
        await xui.node_gate(enabled, ADMIN_ID)
    except Exception as e:
        print(f"Xray: ворота узла не выставлены: {e}")
    chat = await db.get_setting(KEY_NOTIFY)
    if not enabled:
        if chat:
            await db.set_setting(KEY_NOTIFY, "")
            await _say(app, chat, "⏹ Xray выключен: панель убрана, порты 443 и 2096 закрыты.")
        return
    try:
        ok, note = await xui.bootstrap(ADMIN_ID)
    except Exception as e:
        ok, note = False, str(e)
    print(f"Xray: {'готово' if ok else 'не настроилось'} — {note}")
    if chat:
        await db.set_setting(KEY_NOTIFY, "")
        if ok:
            info = xui.panel_info()
            await _say(app, chat,
                       "✅ **Xray включён**\n\n" + escape_md(note) + "\n\n"
                       f"Панель: `{info['url']}`\n"
                       "Открывается только из VPN, с ваших ключей. Логин и пароль — "
                       "«Протоколы → Панель 3X-UI».")
        else:
            await _say(app, chat, "⚠️ **Xray не настроился**\n\n" + escape_md(note))


async def _say(app, chat, text):
    try:
        await app.bot.send_message(chat_id=int(chat), text=text,
                                   parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=exit_kb(("🔀 Протоколы", "proto_menu")))
    except Exception as e:
        print(f"Xray: сообщение владельцу не ушло: {e}")


# --- ПАНЕЛЬ И ЕЁ БОТ ---------------------------------------------------------

async def panel_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    info = xui.panel_info()
    ips = await xui.owner_ips(ADMIN_ID)
    lines = ["🖥 **Панель 3X-UI**", ""]
    if not info["ready"]:
        lines.append("Панель ещё не настроена — бот делает это сам после включения.")
    else:
        lines += [f"Адрес: `{info['url']}`",
                  "Логин и пароль — следующим сообщением, чтобы скопировать.",
                  "",
                  "Открывается **только из VPN** и только с ваших ключей: "
                  + (", ".join(f"`{ip}`" for ip in ips) if ips else "**ваших ключей не найдено**")
                  + ". С чужого ключа и из интернета её не видно.",
                  "",
                  "_В панели можно менять всё — маску, транспорт, лимиты. Бот не "
                  "трогает то, чего не заводил сам: вход `vpn-reality` он "
                  "сопровождает, остальное ваше._"]
    kb = [[InlineKeyboardButton("🔄 Обновить доступ к панели", callback_data="xr_panel_acl")],
          BACK_PROTO]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    if info["ready"]:
        creds = f"{info['user']}\n{info['password']}"
        await send_copyable(context.bot, query.message.chat_id, creds,
                            reply_markup=InlineKeyboardMarkup([[copy_button(creds)]]))


async def panel_acl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        res = await xui.node_gate(True, ADMIN_ID)
        await query.answer("Доступ: " + (", ".join(res.get("panel_ips") or []) or "никому"),
                           show_alert=True)
    except Exception as e:
        await query.answer(f"Не вышло: {e}", show_alert=True)


async def bot_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    token = xui.tg_token()
    lines = ["🤖 **Бот панели 3X-UI**", "",
             "У панели свой бот: отчёты, алерты о входах и нагрузке, бэкап её "
             "базы. Людям он не нужен — для них остаётся этот бот.", ""]
    kb = []
    if token:
        name = await xui.tg_bot_username(token)
        lines.append("Подключён" + (f": @{escape_md(name)}" if name else "") + ".")
        if name:
            kb.append([InlineKeyboardButton("↗️ Перейти в бота панели",
                                            url=f"https://t.me/{name}")])
        kb.append([InlineKeyboardButton("✏️ Сменить токен", callback_data="xr_bot_set"),
                   InlineKeyboardButton("🗑 Отключить", callback_data="xr_bot_off")])
    else:
        lines += ["Не подключён. Создайте бота у @BotFather (`/newbot`) и пришлите "
                  "сюда его токен — бот сам пропишет его в панель."]
        kb.append([InlineKeyboardButton("✏️ Задать токен", callback_data="xr_bot_set")])
    kb.append(BACK_PROTO)
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def bot_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["state"] = "awaiting_xui_tg_token"
    await show_screen(query, context,
                      "✏️ **Пришлите токен бота панели**\n\nВида `123456789:AA…`. "
                      "Сообщение с токеном я удалю сразу после чтения.",
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("✖️ Отмена", callback_data="xr_bot")]]),
                      parse_mode=ParseMode.MARKDOWN)


async def bot_token_entered(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Ответ текстом на «Задать токен». True — сообщение наше."""
    context.user_data["state"] = None
    token = (text or "").strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    if not xui.TG_TOKEN_RE.match(token):
        await update.effective_chat.send_message(
            "❌ Не похоже на токен бота. Он выглядит как `123456789:AA…`.",
            parse_mode=ParseMode.MARKDOWN)
        return True
    if token.split(":")[0] == (os.getenv("BOT_TOKEN", "").split(":")[0]):
        await update.effective_chat.send_message(
            "❌ Это токен этого самого бота. Панели нужен свой, отдельный.")
        return True
    name = await xui.tg_bot_username(token)
    if not name:
        await update.effective_chat.send_message(
            "❌ Telegram не узнал такой токен. Проверьте, что скопирован целиком.")
        return True
    xui.set_tg_token(token)
    note = "сохранён — применится при следующем включении Xray"
    if xui.stack_enabled():
        try:
            await xui.configure(ADMIN_ID)
            note = "прописан в панель"
        except Exception as e:
            note = f"сохранён, но в панель не прописался: {e}"
    await db.log_event("Xray", f"Токен бота панели задан (@{name})")
    await update.effective_chat.send_message(
        f"🤖 Бот @{escape_md(name)}: {escape_md(note)}.\n\nНапишите ему /start.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "↗️ Перейти в бота панели", url=f"https://t.me/{name}")],
            [InlineKeyboardButton("🔙 Протоколы", callback_data="proto_menu")]]),
        parse_mode=ParseMode.MARKDOWN)
    return True


async def bot_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    xui.set_tg_token("")
    if xui.stack_enabled():
        try:
            await xui.configure(ADMIN_ID)
        except Exception as e:
            await query.answer(f"В панели не выключился: {e}", show_alert=True)
    await db.log_event("Xray", "Бот панели отключён")
    await bot_screen(update, context)


# --- МАСКА ВХОДА -------------------------------------------------------------

async def mask_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cur = (await db.get_setting(xui.KEY_TARGET)) or xui.DEFAULT_TARGET
    lines = ["🎭 **Маска входа**", "",
             f"Сейчас: `{escape_md(cur)}`", "",
             "Reality выдаёт вход за HTTPS к этому сайту. Сайт должен открываться "
             "с сервера и держать TLS 1.3 — все варианты ниже проверены.", "",
             "_После смены людям надо обновить подписку в приложении — в ссылке "
             "меняется имя маски. Приложение делает это само раз в 12 часов._"]
    kb = []
    row = []
    for host in xui.TARGET_PRESETS:
        mark = "✅ " if host == cur else ""
        row.append(InlineKeyboardButton(mark + host, callback_data="xr_mask_" + host))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append(BACK_PROTO)
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def mask_set(update: Update, context: ContextTypes.DEFAULT_TYPE, host):
    query = update.callback_query
    if host not in xui.TARGET_PRESETS:
        await query.answer("Такой маски в списке нет", show_alert=True)
        return
    try:
        await xui.set_target(host)
        await db.log_event("Xray", f"Маска входа: {host}")
        await query.answer("Маска сменена")
    except Exception as e:
        await query.answer(f"Не вышло: {e}", show_alert=True)
    await mask_screen(update, context)


# --- ПЕРЕЕЗД МЕЖДУ КАНАЛАМИ --------------------------------------------------

async def move_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кто на каком канале. Переезд — по одному, из карточки человека, или
    всем сразу отсюда: выдать Xray тем, у кого его ещё нет. AmneziaWG при
    этом остаётся — снять его можно только после живого подключения по Xray."""
    query = update.callback_query
    from acl import peer_ip_map
    users = [u for u in await db.get_all_users() if u.get("is_active")]
    peers = set((await peer_ip_map()).keys())
    x = {r["user_uuid"]: r for r in await db.list_xui_clients()}
    both = [u for u in users if u["uuid"] in peers and u["uuid"] in x]
    awg_only = [u for u in users if u["uuid"] in peers and u["uuid"] not in x]
    xray_only = [u for u in users if u["uuid"] not in peers and u["uuid"] in x]
    waiting = [u for u in users if u["uuid"] in x and not x[u["uuid"]]["first_seen_at"]]

    def names(lst):
        return escape_md(", ".join(u["name"] for u in lst[:12])) + ("…" if len(lst) > 12 else "")

    lines = ["🚚 **Переезд между каналами**", "",
             f"Только AmneziaWG: **{len(awg_only)}**",
             f"Оба канала: **{len(both)}**",
             f"Только Xray: **{len(xray_only)}**",
             f"Xray выдан, ещё не подключались: **{len(waiting)}**"]
    if waiting:
        lines += ["", "Ждём: " + names(waiting)]
    lines += ["", "_Переезд по одному — из карточки человека, кнопка «Каналы». "
                  "Кнопка ниже выдаёт Xray всем, у кого его нет, и присылает им "
                  "подписку. AmneziaWG у них остаётся._"]
    kb = []
    if awg_only and xui.stack_enabled():
        kb.append([InlineKeyboardButton(f"📤 Выдать Xray всем ({len(awg_only)})",
                                        callback_data="xr_move_all")])
    kb.append([InlineKeyboardButton("👥 К списку людей", callback_data="users_page_0")])
    kb.append(BACK_PROTO)
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def move_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if context.user_data.get("xr_move_sure") != "all":
        context.user_data["xr_move_sure"] = "all"
        kb = [[InlineKeyboardButton("📤 Да, выдать всем", callback_data="xr_move_all")],
              [InlineKeyboardButton("✖️ Отмена", callback_data="xr_move")]]
        return await show_screen(
            query, context,
            "📤 **Выдать Xray всем, у кого его нет?**\n\nКаждому с привязанным "
            "Telegram уйдёт подписка и инструкция. AmneziaWG у людей остаётся — "
            "они сами выберут, чем пользоваться.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    context.user_data.pop("xr_move_sure", None)
    await query.answer("Выдаю…")
    from handlers_channels import deliver_xray
    from acl import peer_ip_map
    peers = set((await peer_ip_map()).keys())
    have = {r["user_uuid"] for r in await db.list_xui_clients()}
    done = sent = failed = 0
    for u in await db.get_all_users():
        if not u.get("is_active") or u["uuid"] not in peers or u["uuid"] in have:
            continue
        try:
            await xui.issue(u["uuid"])
            done += 1
            sent += await deliver_xray(context.bot, u["uuid"], to_owner=False)
        except Exception as e:
            failed += 1
            print(f"Xray: {u['name']} не выдан: {e}")
    await db.log_event("Xray", f"Массовая выдача: {done}, отправлено {sent}, ошибок {failed}")
    await query.answer(f"Выдано: {done}, отправлено: {sent}, ошибок: {failed}",
                       show_alert=True)
    await move_screen(update, context)

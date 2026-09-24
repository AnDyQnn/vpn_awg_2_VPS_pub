# -*- coding: utf-8 -*-
"""Экран «Протоколы»: как люди подключаются к узлу.

Свой вход у узла один — AmneziaWG. Экран показывает его состояние и
параметры обфускации. Выключить AmneziaWG отсюда нельзя: это единственный
вход, и узел остался бы без связи, а вернуть его можно было бы только руками
по SSH.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from utils import api_session, WG_API_URL, escape_md, show_screen

BACK_SERVICE = [InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]


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
    return "🔀 *Протоколы:* AmneziaWG " + ("работает" if awg.get("up") else "НЕ поднят")


async def protocols_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    st = await status()

    lines = ["🔀 **Протоколы**", ""]
    if st.get("error"):
        lines.append(f"Узел не ответил: `{escape_md(str(st['error']))}`")
        kb = [BACK_SERVICE]
        return await show_screen(query, context, "\n".join(lines),
                                 reply_markup=InlineKeyboardMarkup(kb),
                                 parse_mode=ParseMode.MARKDOWN)

    awg = st.get("awg") or {}
    obf = awg.get("obfuscation") or {}
    # Обфускация — это и есть то, чем AmneziaWG отличается от обычного
    # WireGuard, поэтому показываем её параметры, а не факт «включена».
    obf_line = " · ".join(f"{k}={v}" for k, v in obf.items()) if obf else "не задана"
    online = awg.get("online", -1)

    lines += [
        "🔷 **AmneziaWG**",
        "",
        f"Интерфейс: {'поднят' if awg.get('up') else '**опущен**'} · "
        f"порт `{awg.get('port') or '—'}`",
        f"Пиров: {max(awg.get('peers', 0), 0)}"
        + (f" · на связи: {online}" if online >= 0 else ""),
        f"Обфускация: `{escape_md(obf_line)}`",
    ]
    kb = []
    if not awg.get("up"):
        # Интерфейс лежит — кнопка поднять. Выключателя нет намеренно: вход
        # единственный.
        kb.append([InlineKeyboardButton("▶️ Поднять интерфейс", callback_data="proto_on_awg")])
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

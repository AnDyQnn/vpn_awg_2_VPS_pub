# -*- coding: utf-8 -*-
"""Каналы одного человека: AmneziaWG и Xray, и переезд между ними.

Человек один, способов подключиться у него может быть два. Переезд идёт по
образцу перевыпуска ключа: сначала новое, и только после живого подключения —
снятие старого. Поэтому «Снять AmneziaWG» доступно, только когда человек уже
подключался по Xray: иначе переезд оставил бы его без связи.
"""
import io
import time

import qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import (escape_md, show_screen, send_copyable, copy_button, exit_kb,
                   ADMIN_ID)
import xui

# Официальные ссылки на Happ — клиент Xray, который понимает подписку вместе с
# профилем маршрутизации (сайты мимо VPN). Для российского аккаунта App Store
# своя сборка: основную там не найти.
HAPP_APPS = (
    ("iPhone / iPad", "App Store",
     "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215"),
    ("iPhone · российский аккаунт", "App Store",
     "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"),
    ("Android", "Google Play",
     "https://play.google.com/store/apps/details?id=com.happproxy"),
    ("Android без Play", "apk",
     "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk"),
    ("Windows", "установщик",
     "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe"),
    ("macOS", "образ",
     "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.macOS.universal.dmg"),
    ("Linux", "deb",
     "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.linux.x64.deb"),
)


def _ago(ts):
    if not ts:
        return "ни разу"
    sec = max(0, int(time.time()) - int(ts))
    if sec < 180:
        return "на связи"
    if sec < 3600:
        return f"{sec // 60} мин назад"
    if sec < 86400:
        return f"{sec // 3600} ч назад"
    return f"{sec // 86400} дн назад"


async def person_channels(uuid_val):
    """Что у человека с каналами — для карточки и экрана каналов."""
    from acl import peer_ip_map
    from utils import api_session, WG_API_URL
    ip = (await peer_ip_map()).get(uuid_val)
    hs = 0
    if ip:
        try:
            async with api_session() as s:
                async with s.get(f"{WG_API_URL}/peers", timeout=10) as r:
                    for p in (await r.json() if r.status == 200 else []):
                        if p.get("uuid") == uuid_val:
                            hs = int(p.get("latest_handshake") or 0)
        except Exception:
            pass
    row = await db.get_xui_client(uuid_val)
    seen = (await xui.last_online()).get(uuid_val, 0) if row else 0
    return {"awg": bool(ip), "awg_ip": ip, "awg_hs": hs,
            "xray": bool(row), "xray_seen": seen,
            "xray_first": row["first_seen_at"] if row else None}


def channels_block(st):
    lines = ["🔀 **Каналы:**"]
    if st["awg"]:
        lines.append(f"  🔷 AmneziaWG — {_ago(st['awg_hs'])}")
    else:
        lines.append("  ▫️ AmneziaWG — снят")
    if not st["xray"]:
        lines.append("  ▫️ Xray — не выдан")
    elif st["xray_seen"]:
        lines.append(f"  🔶 Xray — {_ago(st['xray_seen'])}")
    elif st["xray_first"]:
        lines.append("  🔶 Xray — подключался")
    else:
        lines.append("  🟡 Xray — выдан, ещё не подключался")
    return "\n".join(lines)


async def channels_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Человек не найден", show_alert=True)
        return
    st = await person_channels(uuid_val)
    lines = [f"🔀 **Каналы · {escape_md(user['name'])}**", "", channels_block(st), ""]
    kb = []
    if not xui.stack_enabled():
        lines.append("_Xray выключен — включается в «Протоколах»._")
    elif not st["xray"]:
        kb.append([InlineKeyboardButton("🔶 Выдать Xray", callback_data=f"ch_xi_{uuid_val}")])
    else:
        url = await xui.sub_url(uuid_val)
        if url:
            lines.append(f"Подписка: `{url}`")
        kb.append([InlineKeyboardButton("📨 Прислать подписку", callback_data=f"ch_xs_{uuid_val}"),
                   InlineKeyboardButton("🗑 Отозвать Xray", callback_data=f"ch_xr_{uuid_val}")])
    if st["awg"]:
        if st["xray"] and (st["xray_seen"] or st["xray_first"]):
            kb.append([InlineKeyboardButton("🔷 Снять AmneziaWG — переехал",
                                            callback_data=f"ch_ad_{uuid_val}")])
        elif st["xray"]:
            lines.append("_Снять AmneziaWG можно после первого подключения по Xray._")
    else:
        kb.append([InlineKeyboardButton("🔷 Вернуть AmneziaWG", callback_data=f"ch_ar_{uuid_val}")])
    kb.append([InlineKeyboardButton("🔙 К человеку", callback_data=f"user_detail_{uuid_val}")])
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


def _qr_png(text):
    buf = io.BytesIO()
    qrcode.make(text, error_correction=qrcode.constants.ERROR_CORRECT_M).save(buf)
    buf.seek(0)
    return buf


def happ_markdown():
    return "\n".join(f"• {title}: [{store}]({url})" for title, store, url in HAPP_APPS)


def instructions_text():
    return ("🔶 **Подключение по Xray**\n\n"
            "**1.** Поставьте приложение **Happ**:\n" + happ_markdown() + "\n\n"
            "**2.** Скопируйте адрес подписки выше и в Happ нажмите «＋» → "
            "«Вставить из буфера». На телефоне можно отсканировать QR.\n\n"
            "**3.** Включите VPN.\n\n"
            "Российские сервисы идут мимо VPN сами — список приезжает вместе с "
            "подпиской и обновляется без вас.\n\n"
            "⚠️ Адрес личный — не передавайте его никому.")


async def send_subscription(bot, chat_id, uuid_val, with_help=True):
    """QR, адрес подписки кодом и инструкция. False — адреса нет."""
    url = await xui.sub_url(uuid_val)
    if not url:
        return False
    await bot.send_photo(chat_id=chat_id, photo=_qr_png(url),
                         caption="🔶 Ваша подписка Xray. Она личная — не передавайте её.")
    await send_copyable(bot, chat_id, url,
                        reply_markup=InlineKeyboardMarkup([[copy_button(url)]]))
    if with_help:
        await bot.send_message(chat_id=chat_id, text=instructions_text(),
                               parse_mode=ParseMode.MARKDOWN,
                               disable_web_page_preview=True,
                               reply_markup=exit_kb(to_client=True))
    try:
        await db.delivery_downloaded(uuid_val)
    except Exception:
        pass
    return True


async def deliver_xray(bot, uuid_val, to_owner=True):
    """Отправить подписку человеку (всем его Telegram) и, по желанию, владельцу.
    Возвращает, скольким людям ушло."""
    user = await db.get_user_by_uuid(uuid_val)
    sent = 0
    for tid in (user or {}).get("tg_ids", []):
        try:
            await bot.send_message(
                chat_id=tid,
                text="🔶 **Вам выдан второй способ подключения — Xray.**\n\n"
                     "Он пригодится, если основной VPN у вашего оператора работает "
                     "плохо. Старое подключение остаётся — пользуйтесь тем, что "
                     "работает лучше.", parse_mode=ParseMode.MARKDOWN)
            if await send_subscription(bot, tid, uuid_val):
                sent += 1
        except Exception as e:
            print(f"Xray: {tid} не получил подписку: {e}")
    if to_owner and ADMIN_ID and ADMIN_ID not in {int(t) for t in (user or {}).get("tg_ids", [])}:
        await send_subscription(bot, ADMIN_ID, uuid_val, with_help=False)
    return sent


async def issue_xray(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    await query.answer("Выдаю…")
    try:
        await xui.issue(uuid_val)
    except Exception as e:
        await query.answer(f"Не вышло: {e}", show_alert=True)
        return
    sent = await deliver_xray(context.bot, uuid_val)
    await db.log_event("Xray", f"Выдан Xray: {uuid_val}, отправлено {sent}")
    await channels_screen(update, context, uuid_val)


async def send_sub(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    await query.answer("Отправляю…")
    sent = await deliver_xray(context.bot, uuid_val)
    if not sent:
        await query.answer("У человека нет Telegram — подписка ушла только вам",
                           show_alert=True)


async def revoke_xray(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    query = update.callback_query
    st = await person_channels(uuid_val)
    if not st["awg"] and context.user_data.get("ch_sure") != "xr" + uuid_val:
        context.user_data["ch_sure"] = "xr" + uuid_val
        kb = [[InlineKeyboardButton("🗑 Да, отозвать", callback_data=f"ch_xr_{uuid_val}")],
              [InlineKeyboardButton("✖️ Отмена", callback_data=f"ch_{uuid_val}")]]
        return await show_screen(
            query, context,
            "⚠️ **У человека нет AmneziaWG.** Отозвав Xray, вы оставите его без "
            "связи вовсе. Сначала «Вернуть AmneziaWG», если это не то, чего хотите.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    context.user_data.pop("ch_sure", None)
    try:
        await xui.revoke(uuid_val)
        await db.log_event("Xray", f"Xray отозван: {uuid_val}")
    except Exception as e:
        await query.answer(f"Не вышло: {e}", show_alert=True)
        return
    await channels_screen(update, context, uuid_val)


async def drop_awg(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Снять AmneziaWG у того, кто уже подключался по Xray."""
    query = update.callback_query
    st = await person_channels(uuid_val)
    if not (st["xray"] and (st["xray_seen"] or st["xray_first"])):
        await query.answer("Сначала человек должен подключиться по Xray", show_alert=True)
        return
    if context.user_data.get("ch_sure") != "ad" + uuid_val:
        context.user_data["ch_sure"] = "ad" + uuid_val
        kb = [[InlineKeyboardButton("🔷 Да, снять", callback_data=f"ch_ad_{uuid_val}")],
              [InlineKeyboardButton("✖️ Отмена", callback_data=f"ch_{uuid_val}")]]
        return await show_screen(
            query, context,
            "🔷 **Снять AmneziaWG?**\n\nКонфиг AmneziaWG у человека перестанет "
            "работать. Роли, фильтры и история остаются — человек тот же. "
            "Вернуть можно здесь же: выдастся новый конфиг.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    context.user_data.pop("ch_sure", None)
    user = await db.get_user_by_uuid(uuid_val)
    from wireguard_manager import delete_peer
    try:
        await delete_peer(uuid_val, user["name"])
    except Exception as e:
        await query.answer(f"Узел отказал: {e}", show_alert=True)
        return
    from restrictions import reapply
    await reapply("снят AmneziaWG")
    await db.log_event("Xray", f"Снят AmneziaWG после переезда: {user['name']}")
    await channels_screen(update, context, uuid_val)


async def restore_awg(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Вернуть AmneziaWG: новый пир под тем же человеком и конфиг ему."""
    query = update.callback_query
    await query.answer("Выдаю…")
    user = await db.get_user_by_uuid(uuid_val)
    from wireguard_manager import create_peer
    try:
        cidrs = await db.get_all_bypass_cidrs()
        _uid, c_path, q_path = await create_peer(user["name"], bypass_cidrs=cidrs,
                                                 uid=uuid_val)
        await db.execute("UPDATE users SET routing_version=$1 WHERE uuid=$2",
                         await db.get_routing_version(), uuid_val)
    except Exception as e:
        await query.answer(f"Узел отказал: {e}", show_alert=True)
        return
    from restrictions import reapply
    await reapply("возвращён AmneziaWG")
    for tid in {int(t) for t in user.get("tg_ids", []) + ([ADMIN_ID] if ADMIN_ID else [])}:
        try:
            await context.bot.send_document(chat_id=tid, document=open(c_path, "rb"),
                                            caption=f"📄 Конфиг AmneziaWG: {user['name']}")
            await context.bot.send_photo(chat_id=tid, photo=open(q_path, "rb"))
        except Exception as e:
            print(f"AmneziaWG: {tid} не получил конфиг: {e}")
    await db.log_event("Xray", f"Возвращён AmneziaWG: {user['name']}")
    await channels_screen(update, context, uuid_val)


# --- глазами человека --------------------------------------------------------

async def client_xray(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val):
    """Человек сам просит свою подписку из карточки ключа."""
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user or int(query.from_user.id) not in {int(t) for t in user.get("tg_ids", [])}:
        await query.answer("Ключ не найден", show_alert=True)
        return
    await query.answer("Отправляю…")
    if not await send_subscription(context.bot, query.message.chat_id, uuid_val):
        await query.answer("Xray для этого ключа сейчас недоступен", show_alert=True)

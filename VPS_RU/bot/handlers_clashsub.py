# -*- coding: utf-8 -*-
"""Подписка Clash Mi: экраны в боте.

Сама подписка — в clashsub.py. Здесь только то, что видит человек: ссылка,
QR и три шага; у администратора — та же ссылка, счётчик обращений, отправка
человеку и смена ссылки, если она утекла.

Файл конфига AmneziaWG остаётся главным способом: подписка — дополнение для
тех, у кого есть Clash Mi. Роутерам, серверам на Linux и всем без mihomo
нужен файл.
"""
import io

import qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import clashsub
from database import db
from utils import check_admin, dt_to_moscow, escape_md

# Clash Mi на всех системах. На iPhone он есть в российском App Store; для
# остальных систем — сборки с GitHub (для Android — apk).
CLASHMI_APPS = (
    ("iPhone / iPad", "App Store", "https://apps.apple.com/app/id6744321968"),
    ("Android, Windows, macOS, Linux", "GitHub",
     "https://github.com/KaringX/clashmi/releases/latest"),
)
# Приставка просит Clash Mi не накладывать свои настройки поверх профиля:
# DNS, сплит и правила в нём уже наши.
LINK_SUFFIX = "?overwrite=false"


def available():
    """Можно ли выдавать подписку: есть имя или адрес узла и сертификат."""
    return bool(clashsub.public_host()) and clashsub.cert_ready()


def _qr_png(text):
    buf = io.BytesIO()
    qrcode.make(text, error_correction=qrcode.constants.ERROR_CORRECT_M).save(buf)
    buf.seek(0)
    return buf


def client_text(name, link):
    apps = "\n".join(f"• {t}: [{s}]({u})" for t, s, u in CLASHMI_APPS)
    return "\n".join([
        f"🔗 *Подписка: {escape_md(name)}*",
        "",
        "Тот же ключ, что в конфиге AmneziaWG, только ссылкой. Приложение само "
        "подтягивает новый список сайтов мимо VPN и новый ключ после перевыпуска.",
        "",
        "*1.* Поставьте *Clash Mi*:",
        apps,
        "*2.* «Профили» → «＋» → «Добавить по ссылке», вставьте ссылку:",
        f"`{link}`",
        "*3.* Включите VPN",
        "",
        "⚠️ Ссылка личная: в ней ваш ключ. Не передавайте её никому.",
        "Подписка и конфиг — один ключ: на двух устройствах сразу они будут "
        "выбивать друг друга.",
    ])


async def _send_sub(bot, chat_id, user, link, back):
    await bot.send_photo(chat_id=chat_id, photo=_qr_png(link))
    await bot.send_message(
        chat_id=chat_id, text=client_text(user["name"], link),
        parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "🔙 К ключу", callback_data=back)]]))


async def client_sub_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str):
    """Подписка из карточки ключа. Только владельцу ключа: по ссылке отдаётся
    закрытый ключ, чужая кнопка не должна её выдавать."""
    query = update.callback_query
    uid = update.effective_user.id
    user = await db.get_user_by_uuid(uuid_val)
    if not user or (uid not in (user.get("tg_ids") or []) and not check_admin(uid)):
        await query.answer("Ключ не найден.", show_alert=True)
        return
    if not available():
        await query.answer("Подписка сейчас недоступна. Пользуйтесь конфигом "
                           "AmneziaWG — он работает как прежде.", show_alert=True)
        return
    await query.answer()
    link = await clashsub.sub_url(uuid_val) + LINK_SUFFIX
    await _send_sub(context.bot, query.message.chat_id, user, link,
                    f"client_key_manage_{uuid_val}")


# --- АДМИНИСТРАТОР -----------------------------------------------------------

def _when(dt):
    return dt_to_moscow(dt).strftime("%d.%m.%Y %H:%M") if dt else "—"


async def admin_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str, note=""):
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Ключ не найден.", show_alert=True)
        return
    back = [InlineKeyboardButton("🔙 К ключу", callback_data=f"user_detail_{uuid_val}")]
    if not available():
        text = ("🔗 *Подписка Clash Mi*\n\nНедоступна: у узла нет сертификата. "
                "Он выпускается в разделе «Домен и сертификаты».")
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=InlineKeyboardMarkup([back]))
        return
    link = await clashsub.sub_url(uuid_val) + LINK_SUFFIX
    info = await db.sub_info(uuid_val) or {}
    lines = [f"🔗 *Подписка Clash Mi: {escape_md(user['name'])}*", "",
             f"`{link}`", "",
             f"Выдана: {_when(info.get('created_at'))}",
             f"Последнее обновление: {_when(info.get('fetched_at'))}",
             f"Обращений: {info.get('fetch_count') or 0}"]
    if note:
        lines += ["", note]
    kb = []
    if user.get("tg_ids"):
        kb.append([InlineKeyboardButton("📤 Отправить человеку",
                                        callback_data=f"csub_send_{uuid_val}")])
    kb.append([InlineKeyboardButton("🖼 QR сюда", callback_data=f"csub_qr_{uuid_val}")])
    kb.append([InlineKeyboardButton("♻️ Сменить ссылку", callback_data=f"csub_rot_{uuid_val}")])
    kb.append(back)
    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  disable_web_page_preview=True)


async def admin_send(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str):
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user or not user.get("tg_ids") or not available():
        await query.answer("Отправить некуда.", show_alert=True)
        return
    link = await clashsub.sub_url(uuid_val) + LINK_SUFFIX
    sent, failed = 0, 0
    for tg in user["tg_ids"]:
        try:
            await _send_sub(context.bot, tg, user, link, f"client_key_manage_{uuid_val}")
            sent += 1
        except Exception:
            failed += 1
    await query.answer(f"Отправлено: {sent}" + (f", не дошло: {failed}" if failed else ""),
                       show_alert=True)


async def admin_qr(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str):
    query = update.callback_query
    if not available():
        await query.answer("Подписка недоступна.", show_alert=True)
        return
    await query.answer()
    link = await clashsub.sub_url(uuid_val) + LINK_SUFFIX
    await context.bot.send_photo(chat_id=query.message.chat_id, photo=_qr_png(link))


async def admin_rotate_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str):
    query = update.callback_query
    text = ("♻️ *Сменить ссылку подписки?*\n\nСтарая перестанет работать сразу. "
            "Ключ AmneziaWG не меняется: VPN у человека не отвалится, просто "
            "приложение не сможет обновлять профиль, пока в него не добавят "
            "новую ссылку.")
    kb = [[InlineKeyboardButton("✅ Сменить", callback_data=f"csub_dorot_{uuid_val}")],
          [InlineKeyboardButton("🔙 Отмена", callback_data=f"csub_menu_{uuid_val}")]]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(kb))


async def admin_rotate(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str):
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await update.callback_query.answer("Ключ не найден.", show_alert=True)
        return
    await clashsub.sub_url(uuid_val, rotate=True)
    await db.log_event("Subscription", f"Сменена ссылка подписки: {user['name']}")
    await admin_screen(update, context, uuid_val,
                       note="✅ Ссылка сменена, старая больше не работает.")


async def dispatch_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Кнопки csub_*: действие и ключ."""
    for prefix, fn in (("csub_menu_", admin_screen), ("csub_send_", admin_send),
                       ("csub_qr_", admin_qr), ("csub_rot_", admin_rotate_confirm),
                       ("csub_dorot_", admin_rotate)):
        if data.startswith(prefix):
            await fn(update, context, data[len(prefix):])
            return True
    return False

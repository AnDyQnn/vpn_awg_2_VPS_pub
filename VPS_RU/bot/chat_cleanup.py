# -*- coding: utf-8 -*-
"""Чистка чатов в конце дня: бот убирает за собой.

Она была и раньше, но знала только про тревоги. Их шлют через один помощник,
который запоминает номер сообщения, — таких мест тридцать. А мимо него владельцу
пишут ещё десяток мест напрямую (биллинг, архивы, выгрузки, выдача ключей,
решения) и десятки ответов на его же нажатия. Ни одно в список не попадало, и в
полночь их никто не трогал. Снаружи это выглядело ровно как «чистка не
работает» — и это была правда, просто не вся.

Почему перехватом, а не аккуратной записью в каждом месте. Правило «не забудь
записать номер» соблюдалось бы ровно до следующего нового экрана — что и
произошло. Перехват не забывает ничего и не требует помнить о себе; тем же
приёмом в проекте раскрашиваются подписи кнопок.

Что остаётся после чистки:

- у владельца — архивы (закреплённая копия системы и архивы узлов) и главное
  меню: экран, на котором он сейчас, становится главным меню, а не исчезает;
- у человека — его главное меню. Ключи и ссылки он заново берёт оттуда же,
  поэтому копия в переписке не последний экземпляр;
- написанное самими людьми: бот убирает только своё.

Раньше «не трогать экран» означало «не трогать два последних сообщения». Но
экран редактируется на месте: отправлен он утром, а тревоги пришли после него.
К полуночи он был уже не среди последних — и уходил вместе со всем остальным,
а с ним и закреплённый архив. Теперь экран узнаётся по тому, какое сообщение
бот показывал человеку, а не по порядку.

Про предел Telegram. Бот может удалять свои сообщения не старше 48 часов, и это
не обходится ничем. Для чистки в конце дня этого хватает с запасом: к полуночи
самому старому сообщению сутки. Но если бот сутки лежал, всё, что старше
предела, останется в чате навсегда — и обещать обратное нельзя.
"""
import asyncio
import time

from database import db
from utils import get_moscow_now

# Предел самого Telegram, в часах. Старше — не удалится, и пытаться незачем.
TG_LIMIT_HOURS = 47.5

ON_KEY = "chat_cleanup_on"
DONE_KEY = "chat_cleanup_done"
LAST_KEY = "chat_cleanup_last"

# Ночная уборка идёт в первые часы суток, а не ровно в полночь: если бот в
# полночь перезапускался, уборка пройдёт, как только он поднимется.
NIGHT_HOURS = 6

# Пауза перед первым проходом и между проверками. Вынесены отдельно, чтобы
# проверка могла прогнать сутки за секунду: иначе цикл, смотрящий на часы,
# нечем испытать, кроме как ожиданием.
START_DELAY = 120
CHECK_SECONDS = 120

_patched = False


async def enabled():
    return (await db.get_setting(ON_KEY) or "1") == "1"


def _targets():
    """Классы, которые надо перехватить.

    Их два, и это не перестраховка. Приложение шлёт не голым `Bot`, а `ExtBot`,
    и тот переопределяет `send_message` своей версией — с ограничением частоты.
    Перехват, поставленный только на `Bot`, до живого бота не доезжает вовсе:
    вызов уходит в переопределение, а оно ничего не записывает. Снаружи это
    выглядит как работающая чистка, которой нечего чистить.
    """
    out = []
    try:
        from telegram import Bot
        out.append(Bot)
    except Exception:
        pass
    try:
        from telegram.ext import ExtBot
        out.append(ExtBot)
    except Exception:
        pass
    return out


def _kind(name, kwargs):
    """Что за сообщение: архив, экран с кнопками или прочее."""
    caption = str(kwargs.get("caption") or "")
    if name == "send_document" and "Архив" in caption:
        return "backup"
    if name == "send_message" and kwargs.get("reply_markup") is not None:
        return "menu"
    return ""


def apply(admin_id, classes=None):
    """Перехватывает отправку сообщений в личные чаты — один раз при старте."""
    global _patched
    if _patched or not admin_id:
        return False

    def wrap(name, original):
        async def sender(self, chat_id=None, *args, **kwargs):
            msg = await original(self, chat_id, *args, **kwargs)
            try:
                # Личный чат — положительный номер; группы не наши.
                if msg is not None and int(chat_id) > 0:
                    await db.remember_chat_msg(int(chat_id), int(msg.message_id),
                                               _kind(name, kwargs))
            except Exception:
                # Запись служебная. Не отдать сообщение из-за того, что не
                # записали его номер, значило бы обменять важное на неважное.
                pass
            return msg
        return sender

    touched = 0
    for cls in (classes if classes is not None else _targets()):
        for name in ("send_message", "send_document", "send_photo"):
            # Только то, что класс объявил САМ. Унаследованное трогать нельзя:
            # оно уже перехвачено у родителя, и обёртка легла бы вторым слоем —
            # одно сообщение записалось бы дважды.
            if name not in cls.__dict__:
                continue
            setattr(cls, name, wrap(name, cls.__dict__[name]))
            touched += 1

    _patched = touched > 0
    return _patched


def _screen_of(app, chat_id):
    """Сообщение, которое человек видит как экран, — если бот его помнит."""
    try:
        at = (getattr(app, "user_data", None) or {}).get(int(chat_id), {}).get("screen_at")
        if at and int(at[0]) == int(chat_id):
            return int(at[1])
    except Exception:
        pass
    try:
        from utils import state_data
        mid = state_data.get("active_menus", {}).get(int(chat_id))
        if mid:
            return int(mid)
    except Exception:
        pass
    return None


def _last_menu(rows):
    """Последнее сообщение с кнопками, которое ещё можно править."""
    fresh = time.time() - TG_LIMIT_HOURS * 3600
    for r in rows:                      # rows — свежие первыми
        if r.get("kind") == "menu" and (r.get("sent_at") or 0) > fresh:
            return int(r["message_id"])
    return None


async def admin_menu(app, chat_id):
    from handlers_admin import main_menu_view
    from telegram.constants import ParseMode
    text, markup, _ = await main_menu_view(None, chat_id)
    return text, markup, ParseMode.MARKDOWN


async def user_menu(app, chat_id):
    from handlers_client import client_menu_view
    first = ""
    try:
        first = (await app.bot.get_chat(int(chat_id))).first_name or ""
    except Exception:
        pass
    return await client_menu_view(int(chat_id), first)


async def _put_menu(app, chat_id, anchor, build):
    """Оставляет в чате главное меню: правит экран, а нет его — шлёт новое, без звука."""
    text, markup, mode = await build(app, chat_id)
    if anchor:
        try:
            await app.bot.edit_message_text(chat_id=int(chat_id), message_id=int(anchor),
                                            text=text, reply_markup=markup, parse_mode=mode)
            return int(anchor)
        except Exception as e:
            if "not modified" in str(e).lower():
                return int(anchor)
    msg = await app.bot.send_message(chat_id=int(chat_id), text=text, reply_markup=markup,
                                     parse_mode=mode, disable_notification=True)
    if build is admin_menu:
        try:
            from utils import state_data
            state_data["active_menus"][int(chat_id)] = msg.message_id
        except Exception:
            pass
    return msg.message_id


async def sweep_chat(app, chat_id, anchor=None, keep=()):
    """Убирает записанное в одном чате, кроме экрана, архивов и того, что в keep.

    Экран, если его не назвали, ищется сам: сперва тот, что бот помнит, потом
    последнее сообщение с кнопками. Возвращает (сколько убрано, экран)."""
    rows = await db.chat_msgs(int(chat_id))
    if anchor is None:
        anchor = _screen_of(app, chat_id)
    if anchor is None:
        anchor = _last_menu(rows)
    keep = {int(m) for m in keep}
    gone = 0
    for r in rows:
        mid = int(r["message_id"])
        if mid == anchor or mid in keep or r.get("kind") == "backup":
            continue
        try:
            await app.bot.delete_message(chat_id=int(chat_id), message_id=mid)
            gone += 1
        except Exception:
            # Уже удалено руками, старше предела Telegram или закреплено.
            # Второй раз пробовать незачем — забываем и идём дальше.
            pass
        await db.forget_chat_msg(int(chat_id), mid)
    return gone, anchor


async def _backup_ids():
    """Закреплённый архив системы — его номер хранится отдельно."""
    try:
        v = await db.get_setting("backup_message_id")
        return {int(v)} if v and str(v).isdigit() else set()
    except Exception:
        return set()


async def sweep(app, admin_id, anchor=None):
    """Убирает всё, что бот прислал владельцу, кроме архивов и экрана.

    Возвращает, сколько убрано."""
    if not admin_id:
        return 0
    gone, _ = await sweep_chat(app, admin_id, anchor=anchor, keep=await _backup_ids())

    # Старые тревоги, записанные прежним способом. Забираем и их, иначе они
    # остались бы в чате навсегда: список под них после той версии больше никто
    # не пополняет.
    legacy = []
    try:
        cur = await db.get_setting("admin_alert_msgs") or ""
        legacy = [int(x) for x in cur.split(",") if x.strip().isdigit()]
    except Exception:
        legacy = []
    for mid in legacy:
        if mid == anchor:
            continue
        try:
            await app.bot.delete_message(chat_id=int(admin_id), message_id=mid)
            gone += 1
        except Exception:
            pass
    if legacy:
        await db.set_setting("admin_alert_msgs", "")
    return gone


async def sweep_all(app, admin_id):
    """Ночная уборка: чат владельца и чаты людей, каждому — главное меню.

    Возвращает (убрано у владельца, убрано у людей, чатов людей)."""
    mine = 0
    if admin_id:
        anchor = _screen_of(app, admin_id)
        if anchor is None:
            anchor = _last_menu(await db.chat_msgs(int(admin_id)))
        mine = await sweep(app, admin_id, anchor=anchor)
        if mine or anchor:
            try:
                await _put_menu(app, admin_id, anchor, admin_menu)
            except Exception as e:
                print(f"Чистка чата: меню владельца не поставилось ({e})")

    theirs, chats = 0, 0
    for chat_id in await db.chat_ids():
        if admin_id and int(chat_id) == int(admin_id):
            continue
        try:
            gone, anchor = await sweep_chat(app, chat_id)
        except Exception as e:
            print(f"Чистка чата {chat_id}: {e}")
            continue
        theirs += gone
        if gone or anchor:
            chats += 1
            try:
                await _put_menu(app, chat_id, anchor, user_menu)
            except Exception:
                # Человек мог заблокировать бота — это его право.
                pass
        await asyncio.sleep(0.05)       # не упираться в предел частоты Telegram
    return mine, theirs, chats


async def loop(app, admin_id):
    """Раз в сутки, в начале дня по Москве.

    Проверяем каждые две минуты, а не спим до полуночи: бот перезапускается
    (выкладка, перезагрузка), и сон, переживший перезапуск, — это сон, который
    не проснулся. Отметка о сделанном за сегодня не даёт убрать дважды.
    """
    await asyncio.sleep(START_DELAY)
    while True:
        try:
            now = get_moscow_now()
            today = now.strftime("%Y-%m-%d")
            if now.hour < NIGHT_HOURS and await enabled():
                if (await db.get_setting(DONE_KEY)) != today:
                    await db.set_setting(DONE_KEY, today)
                    mine, theirs, chats = await sweep_all(app, admin_id)
                    note = (f"{now.strftime('%d.%m %H:%M')} — у вас {mine}, "
                            f"у людей {theirs} (чатов: {chats})")
                    await db.set_setting(LAST_KEY, note)
                    await db.log_event("System", f"Чистка чата: {note}")
                    print(f"Чистка чата: {note}")
        except Exception as e:
            print(f"Чистка чата: {e}")
        await asyncio.sleep(CHECK_SECONDS)


# --- Экран -----------------------------------------------------------------
#
# Тумблер здесь нужен не «чтобы был». Чистка удаляет и выданные ключи — это
# копии, и перевыдать их два нажатия, но решение так делать принимает владелец,
# а не мы за него.

async def screen(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode
    from utils import show_screen, ADMIN_ID

    query = update.callback_query
    on = await enabled()
    keep = await _backup_ids()
    waiting = len([r for r in await db.chat_msgs(int(ADMIN_ID or 0))
                   if r.get("kind") != "backup" and r["message_id"] not in keep])
    last = await db.get_setting(LAST_KEY) or "ещё не было"

    lines = ["🧹 **Чистка чата**", "",
             ("Состояние: **включена** · каждую ночь после 00:00 МСК" if on
              else "Состояние: **выключена**"),
             f"Последняя ночная: {last}",
             f"Ждёт уборки у вас: **{waiting}**", "",
             "Ночью бот убирает из чатов всё, что присылал сам: тревоги, "
             "ответы на нажатия, сводки, выданные ключи.",
             "",
             "**Что остаётся.** У вас — архивы и главное меню. У людей — их "
             "главное меню: ключи и ссылки они берут оттуда заново.",
             "",
             "«Убрать сейчас» чистит только этот чат, экран остаётся.",
             "",
             "_Telegram разрешает боту удалять своё не старше 48 часов. Для "
             "суточной уборки этого с запасом, но если бот сутки лежал — всё, "
             "что старше, останется навсегда._"]

    kb = [[InlineKeyboardButton("🧹 Убрать сейчас", callback_data="chat_clean_now")],
          [InlineKeyboardButton("🔕 Выключить" if on else "🔔 Включить",
                                callback_data="chat_clean_toggle")],
          [InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")]]
    await show_screen(query, context, chr(10).join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def clean_now(update, context):
    """Убрать, не дожидаясь ночи. Только этот чат; экран остаётся."""
    from utils import ADMIN_ID
    query = update.callback_query
    # Отвечаем на нажатие один раз — в конце, с итогом: второй ответ на то же
    # нажатие Telegram отвергает.
    try:
        gone = await sweep(context.application, ADMIN_ID,
                           anchor=query.message.message_id)
    except Exception as e:
        await query.answer("Не вышло: %s" % e, show_alert=True)
        return
    await query.answer("Убрано сообщений: %d" % gone, show_alert=True)
    await screen(update, context)


async def toggle(update, context):
    on = await enabled()
    await db.set_setting(ON_KEY, "0" if on else "1")
    await update.callback_query.answer("Выключено" if on else "Включено")
    await screen(update, context)

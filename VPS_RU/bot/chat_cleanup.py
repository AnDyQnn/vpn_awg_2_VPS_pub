# -*- coding: utf-8 -*-
"""Чистка чата владельца в конце дня: бот убирает за собой.

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

Что считается безопасным и почему. Ключи и конфигурации удаляются тоже — это
копии. Настоящий получатель забрал свой в личном чате, а владелец перевыдаёт
любой ключ из карточки человека в два нажатия. Копия в переписке не последний
экземпляр и хранилищем быть не должна.

Чего чистка НЕ делает:

- не трогает чужие чаты. Человек хранит свой ключ сам, и решать за него, когда
  ему пора его потерять, мы не вправе;
- не трогает последние сообщения: экран, на который владелец смотрит сейчас,
  исчезнуть не должен — вместе с ним исчезнут кнопки;
- не трогает то, что бот не отправлял, — сообщения самого владельца.

Про предел Telegram. Бот может удалять свои сообщения не старше 48 часов, и это
не обходится ничем. Для чистки в конце дня этого хватает с запасом: к полуночи
самому старому сообщению сутки. Но если бот сутки лежал, всё, что старше
предела, останется в чате навсегда — и обещать обратное нельзя.
"""
import asyncio

from database import db
from utils import get_moscow_now

# Сколько последних сообщений не трогаем никогда. Двух хватает: текущий экран и
# то, что бот прислал следом за ним.
KEEP_LAST = 2

# Предел самого Telegram, в часах. Старше — не удалится, и пытаться незачем.
TG_LIMIT_HOURS = 47.5

ON_KEY = "chat_cleanup_on"
DONE_KEY = "chat_cleanup_done"

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


def apply(admin_id, classes=None):
    """Перехватывает отправку сообщений владельцу — один раз при старте."""
    global _patched
    if _patched or not admin_id:
        return False

    def wrap(original):
        async def sender(self, chat_id=None, *args, **kwargs):
            msg = await original(self, chat_id, *args, **kwargs)
            try:
                if str(chat_id) == str(admin_id) and msg is not None:
                    await db.remember_chat_msg(int(chat_id), int(msg.message_id))
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
            setattr(cls, name, wrap(cls.__dict__[name]))
            touched += 1

    _patched = touched > 0
    return _patched


async def sweep(app, admin_id):
    """Убирает всё, что бот прислал владельцу. Возвращает, сколько убрано."""
    if not admin_id:
        return 0
    rows = await db.chat_msgs(int(admin_id), keep_last=KEEP_LAST)

    # Старые тревоги, записанные прежним способом. Забираем и их, иначе они
    # остались бы в чате навсегда: список под них после этой версии больше никто
    # не пополняет.
    legacy = []
    try:
        cur = await db.get_setting("admin_alert_msgs") or ""
        legacy = [int(x) for x in cur.split(",") if x.strip().isdigit()]
    except Exception:
        legacy = []

    known = {r["message_id"] for r in rows}
    gone = 0
    for mid in [r["message_id"] for r in rows] + [m for m in legacy
                                                  if m not in known]:
        try:
            await app.bot.delete_message(chat_id=int(admin_id), message_id=mid)
            gone += 1
        except Exception:
            # Уже удалено руками, старше предела Telegram или закреплено.
            # Второй раз пробовать незачем — забываем и идём дальше.
            pass
        await db.forget_chat_msg(int(admin_id), mid)
    if legacy:
        await db.set_setting("admin_alert_msgs", "")
    return gone


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
            if now.hour == 0 and await enabled():
                if (await db.get_setting(DONE_KEY)) != today:
                    await db.set_setting(DONE_KEY, today)
                    gone = await sweep(app, admin_id)
                    print(f"Чистка чата: убрано сообщений — {gone}")
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
    waiting = len(await db.chat_msgs(int(ADMIN_ID or 0), keep_last=KEEP_LAST))

    lines = ["🧹 **Чистка чата**", "",
             ("Состояние: **включена**" if on else "Состояние: **выключена**"),
             f"Ждёт уборки сообщений: **{waiting}**", "",
             "В начале суток бот убирает из этого чата всё, что присылал сам: "
             "тревоги, ответы на нажатия, сводки, архивы, копии выданных ключей.",
             "",
             "**Почему копии ключей — не потеря.** Настоящий получатель забрал "
             "свой в личном чате, а перевыдать любой ключ можно из карточки "
             "человека в два нажатия. Переписка хранилищем быть не должна.",
             "",
             "**Чего чистка не делает:** не трогает чужие чаты, не трогает "
             "последние сообщения (иначе исчезнет экран, на который вы "
             "смотрите) и не трогает написанное вами.",
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
    """Убрать, не дожидаясь начала суток."""
    from utils import ADMIN_ID
    query = update.callback_query
    await query.answer("Убираю…")
    try:
        gone = await sweep(context.application, ADMIN_ID)
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

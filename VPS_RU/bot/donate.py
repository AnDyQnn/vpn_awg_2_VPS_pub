# -*- coding: utf-8 -*-
"""Поддержка проекта деньгами: обращение и реквизиты.

Бот управляет доступом, и просьба о деньгах из того же окна, где человеку
выдают и отключают ключ, легко читается как условие: «заплати, иначе отключат».
Поэтому в тексте по умолчанию прямо сказано, что доступ от перевода не зависит.
Это не вежливость, а единственное, что отличает просьбу от давления.

Вторая строчка, которая здесь не случайна: реквизиты бывают только в боте. Их
разносят скриншотами, и однажды кто-нибудь напишет в общий чат «карта
поменялась, кидайте сюда» — пусть человеку будет с чем сверить.

Сам текст лежит в настройках, а не в коде: переписать его можно из админки, без
выкладки. В коде — только то, с чего начинают.
"""
import re

from database import db

# Реквизит бывает трёх видов. Больше не нужно: карта и телефон покрывают
# переводы, картинка — тех, кто платит из банковского приложения по QR.
KINDS = {
    "card": "Карта",
    "phone": "Телефон · СБП",
    "qr": "QR · СБП",
}

DEFAULT_TEXT = (
    "Этот VPN бесплатный и таким останется: доступ от перевода никак не "
    "зависит, ничего не отключится и не замедлится, если вы не платите.\n\n"
    "Но бесплатный он только для вас. Я плачу за две виртуалки — в России и "
    "Германии, — сам их настраиваю, чиню и обновляю. Это мои деньги и моё "
    "время, и трачу я их, чтобы у вас просто работало.\n\n"
    "Если проект вам полезен и есть возможность — скиньтесь на "
    "инфраструктуру. Любая сумма помогает, регулярность не нужна.\n\n"
    "Реквизиты ниже. Они бывают только здесь, в боте: если где-то ещё вам "
    "пишут, что «карта поменялась», — это не я."
)

# Напоминание едет следом за «что нового» и поэтому должно быть коротким:
# человек только что прочитал список изменений, длинный текст он пролистает.
REMINDER_TEXT = (
    "Кстати: проект держится на двух оплаченных виртуалках и свободном "
    "времени. Доступ от этого не зависит, но если хочется поддержать — "
    "кнопка ниже."
)

DEFAULT_REMINDER_DAYS = 14


async def enabled():
    """Показывать ли людям кнопку. По умолчанию — нет: реквизитов ещё нет,
    и кнопка вела бы на пустой экран."""
    return (await db.get_setting("donate_enabled")) == "1"


async def set_enabled(on):
    await db.set_setting("donate_enabled", "1" if on else "0")


async def text():
    saved = await db.get_setting("donate_text")
    return saved if saved else DEFAULT_TEXT


async def set_text(value):
    await db.set_setting("donate_text", value)


async def reminder_enabled():
    """Напоминание после обновлений. По умолчанию выключено — включает владелец,
    когда реквизиты на месте."""
    return (await db.get_setting("donate_reminder")) == "1"


async def set_reminder(on):
    await db.set_setting("donate_reminder", "1" if on else "0")


async def reminder_days():
    """Сколько дней молчать между напоминаниями.

    Пустая настройка — это «не задано», а не «ноль дней»: раньше она
    превращалась в единицу, и на экране писалось «раз в 1 дн.».
    """
    raw = (await db.get_setting("donate_reminder_days") or "").strip()
    if not raw:
        return DEFAULT_REMINDER_DAYS
    try:
        return max(1, int(raw))
    except Exception:
        return DEFAULT_REMINDER_DAYS


async def methods():
    return await db.list_donate_methods()


def pretty_value(kind, value):
    """Номер в том виде, в каком его удобно читать и сверять.

    Карту разбиваем по четыре: слитные шестнадцать цифр глазом не проверить, а
    человек именно сверяет — он переводит деньги незнакомому номеру.
    """
    raw = (value or "").strip()
    if kind == "card":
        digits = re.sub(r"\D", "", raw)
        if len(digits) in (16, 18, 19, 20):
            return " ".join(digits[i:i + 4] for i in range(0, len(digits), 4))
        return digits or raw
    return raw


async def screen_text():
    """Обращение и реквизиты одним экраном.

    Номера отдаются кодом: в Telegram по коду достаточно нажать, чтобы он
    скопировался целиком. Руками такое не перепечатывают без ошибок.
    """
    lines = ["❤️ **Поддержать проект**", "", await text()]
    rows = await methods()
    money = [r for r in rows if r["kind"] != "qr"]
    pictures = [r for r in rows if r["kind"] == "qr"]

    if money:
        lines.append("")
        for row in money:
            head = row["bank"] or KINDS.get(row["kind"], "Перевод")
            lines.append(f"**{head}**")
            lines.append(f"`{pretty_value(row['kind'], row['value'])}`")
            if row["note"]:
                lines.append(row["note"])
            lines.append("")
    if pictures:
        lines.append("Есть QR для оплаты из банковского приложения — "
                     "кнопка ниже.")
    if not rows:
        lines.append("")
        lines.append("_Реквизиты ещё не заведены._")
    return "\n".join(lines).rstrip()


async def qr_methods():
    return [r for r in await methods() if r["kind"] == "qr"]


async def visible():
    """Кнопку показываем, только если она куда-то ведёт: включена и есть чем
    платить. Кнопка, за которой пусто, хуже отсутствующей."""
    return await enabled() and bool(await methods())


async def should_remind(tg_id):
    """Напоминать ли этому человеку сейчас.

    Ограничение по дням здесь не для красоты: версии выходят пачками, и без
    него человек получил бы просьбу о деньгах несколько раз за день. После
    такого выключают уведомления целиком, вместе с полезными.
    """
    if not await reminder_enabled() or not await visible():
        return False
    days = await reminder_days()
    try:
        last = await db.get_donate_reminded_at(tg_id)
    except Exception:
        return False
    if not last:
        return True
    from datetime import datetime
    return (datetime.utcnow() - last).total_seconds() >= days * 86400

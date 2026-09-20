# -*- coding: utf-8 -*-
"""Счета за сервера: сколько, кому и до какого числа.

Зачем это внутри бота, а не в календаре. Сервера оплачиваются раз в квартал, и
забыть про платёж — значит однажды обнаружить выключенный узел и тридцать
человек без связи. Заметить это первым должен владелец, а не они.

Как считается сумма. Человек помнит тариф — «двести в месяц», — а не сумму
списания за квартал. Поэтому храним помесячную цену и период, а сумму к оплате
выводим сами: цена × число месяцев. Так же, как это делает сам хостер.

Как считается дата. Хранится ближайшая, до которой надо заплатить. Оплатил —
кнопка сдвигает её на период вперёд, а не на «сегодня плюс период»: иначе
оплата на день раньше каждый раз сдвигала бы весь график назад.

Напоминание приходит один раз в сутки и только когда есть о чём: у каждого
сервиса свой запас дней, потому что один хостер присылает счёт за неделю, а
другой выключает в день окончания.
"""
import asyncio
from datetime import date, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import show_screen, escape_md, ADMIN_ID

# Раз в сутки: счета не меняются чаще, а лишнее напоминание учит его
# игнорировать.
CHECK_SECONDS = 6 * 3600
PERIODS = [(1, "ежемесячно"), (3, "раз в квартал"),
           (6, "раз в полгода"), (12, "раз в год")]


def period_name(months):
    for m, name in PERIODS:
        if m == months:
            return name
    return "раз в %d мес." % months


def amount(service):
    """Сколько платить за один раз: помесячная цена × период."""
    return float(service["monthly"] or 0) * int(service["period_months"] or 1)


def money(value):
    """Рубли без копеек, если они нулевые: «600 ₽», а не «600.00 ₽»."""
    v = float(value or 0)
    return ("%d ₽" % round(v)) if abs(v - round(v)) < 0.005 else ("%.2f ₽" % v)


def next_due(current, months):
    """Следующая дата платежа — от прежней, а не от сегодня.

    Разница видна не сразу, но она принципиальна: платят обычно за несколько
    дней до срока, и считая «сегодня + период», мы бы каждый раз уводили
    график на эти дни назад. За год набегает месяц.
    """
    if not current:
        current = date.today()
    y, m = current.year, current.month + int(months)
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    day = current.day
    # 31-е в феврале не существует: берём последний день месяца.
    while day > 28:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1
    return date(y, m, day)


def due_text(services, header="Необходимо оплатить"):
    """Текст напоминания: по дате, со ссылками и итогом."""
    by_date = {}
    for s in services:
        by_date.setdefault(s["due_date"], []).append(s)

    lines = []
    total_all = 0.0
    for when in sorted(by_date):
        block = by_date[when]
        lines.append("**%s до %s:**" % (header, when.strftime("%d.%m")))
        total = 0.0
        for s in block:
            total += amount(s)
            name = escape_md(s["name"])
            title = "[%s](%s)" % (name, s["url"]) if s.get("url") else name
            lines.append("• %s — %s" % (title, money(amount(s))))
        if len(block) > 1:
            lines.append("Всего — **%s**" % money(total))
        total_all += total
        lines.append("")
    if len(by_date) > 1:
        lines.append("Итого — **%s**" % money(total_all))
    return "\n".join(lines).strip()


# ------------------------------------------------------------------ экраны --
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список сервисов и ближайшие платежи."""
    query = update.callback_query
    items = await db.billing_list(only_active=False)

    lines = ["💳 **Счета за сервера**", ""]
    if not items:
        lines += ["Пока ничего не заведено.", "",
                  "_Сюда вносятся хостинги и домены: сколько стоит в месяц, "
                  "раз во сколько платите и до какого числа. Бот напомнит "
                  "заранее и посчитает сумму._"]
    else:
        total_month = sum(float(s["monthly"] or 0) for s in items if s["is_active"])
        for s in items:
            mark = "" if s["is_active"] else "⏸ "
            when = s["due_date"].strftime("%d.%m.%Y") if s["due_date"] else "срок не задан"
            lines.append("%s**%s** — %s, %s" % (
                mark, escape_md(s["name"]), money(amount(s)),
                period_name(s["period_months"])))
            lines.append("     до %s · %s/мес" % (when, money(s["monthly"])))
        lines += ["", "В месяц выходит **%s**" % money(total_month)]

    due = await db.billing_due()
    if due:
        lines += ["", "⚠️ " + due_text(due, header="Пора платить")]

    kb = [[InlineKeyboardButton("➕ Добавить сервис", callback_data="bill_add")]]
    for s in items:
        kb.append([InlineKeyboardButton(
            "%s · %s" % (s["name"][:20], money(amount(s))),
            callback_data="bill_open_%d" % s["id"])])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def open_service(update: Update, context: ContextTypes.DEFAULT_TYPE, sid):
    """Один сервис: всё про него и что с ним можно сделать."""
    query = update.callback_query
    s = await db.billing_get(sid)
    if not s:
        await query.answer("Сервиса нет", show_alert=True)
        return await menu(update, context)

    when = s["due_date"]
    left = (when - date.today()).days if when else None
    lines = [
        "💳 **%s**" % escape_md(s["name"]), "",
        "Цена: **%s в месяц**" % money(s["monthly"]),
        "Платим: %s → **%s** за раз" % (period_name(s["period_months"]),
                                        money(amount(s))),
        "Срок: %s" % (when.strftime("%d.%m.%Y") if when else "не задан"),
    ]
    if left is not None:
        lines.append("Осталось: **%d дн.**" % left if left >= 0
                     else "⚠️ Просрочено на **%d дн.**" % -left)
    lines.append("Напомнить за %d дн." % s["notify_days"])
    if s.get("url"):
        lines += ["", "[Личный кабинет](%s)" % s["url"]]
    if not s["is_active"]:
        lines += ["", "_Сервис отключён: в напоминаниях не участвует._"]

    kb = [
        [InlineKeyboardButton("✅ Оплатил — сдвинуть срок",
                              callback_data="bill_paid_%d" % s["id"])],
        [InlineKeyboardButton("✏️ Цена", callback_data="bill_ed_monthly_%d" % s["id"]),
         InlineKeyboardButton("✏️ Срок", callback_data="bill_ed_due_%d" % s["id"])],
        [InlineKeyboardButton("✏️ Период", callback_data="bill_ed_period_%d" % s["id"]),
         InlineKeyboardButton("✏️ Ссылка", callback_data="bill_ed_url_%d" % s["id"])],
        [InlineKeyboardButton("⏸ Отключить" if s["is_active"] else "▶️ Включить",
                              callback_data="bill_toggle_%d" % s["id"])],
        [InlineKeyboardButton("🗑 Удалить", callback_data="bill_del_%d" % s["id"])],
        [InlineKeyboardButton("🔙 Счета", callback_data="bill_menu")],
    ]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def add_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заводим сервис одной строкой: так быстрее, чем пять вопросов подряд."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_billing_add"
    await show_screen(
        query, context,
        "➕ **Новый сервис**\n\nПришлите одной строкой, через точку с запятой:\n\n"
        "`имя; цена в месяц; раз во сколько месяцев; дата платежа; ссылка`\n\n"
        "Например:\n`Хостинг РФ; 200; 3; 15.10.2026; https://example.ru/billing`\n\n"
        "_Ссылку можно не писать. Дата — ближайший платёж._",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="bill_menu")]]),
        parse_mode=ParseMode.MARKDOWN)


def parse_add(text):
    """Разбирает строку добавления. Возвращает словарь или строку с ошибкой."""
    parts = [p.strip() for p in (text or "").split(";")]
    if len(parts) < 4:
        return "нужно хотя бы четыре части через точку с запятой"
    name, price, period, due = parts[0], parts[1], parts[2], parts[3]
    url = parts[4] if len(parts) > 4 else ""
    if not name:
        return "имя пустое"
    try:
        monthly = float(price.replace(",", ".").replace(" ", ""))
    except ValueError:
        return "цену не разобрать: «%s»" % price
    try:
        months = int(period)
        if months < 1 or months > 60:
            raise ValueError
    except ValueError:
        return "период должен быть числом месяцев от 1 до 60"
    when = parse_date(due)
    if not when:
        return "дату не разобрать: «%s», нужно вроде 15.10.2026" % due
    return {"name": name[:60], "monthly": monthly, "period_months": months,
            "due_date": when, "url": url[:200]}


def parse_date(text):
    """Дата в человеческом виде: 15.10.2026, 15.10.26, 15.10 (этот год)."""
    raw = (text or "").strip().replace("/", ".").replace("-", ".")
    bits = [b for b in raw.split(".") if b]
    if len(bits) < 2:
        return None
    try:
        d, m = int(bits[0]), int(bits[1])
        y = int(bits[2]) if len(bits) > 2 else date.today().year
        if y < 100:
            y += 2000
        when = date(y, m, d)
    except ValueError:
        return None
    # Без года и дата уже прошла — значит имелся в виду следующий год.
    if len(bits) == 2 and when < date.today():
        when = date(when.year + 1, m, d)
    return when


async def mark_paid(update: Update, context: ContextTypes.DEFAULT_TYPE, sid):
    """Сдвигает срок на период вперёд."""
    query = update.callback_query
    s = await db.billing_get(sid)
    if not s:
        return await menu(update, context)
    when = next_due(s["due_date"], s["period_months"])
    await db.billing_set(sid, due_date=when)
    await db.log_event("Счета", "%s оплачен, следующий платёж %s" % (
        s["name"], when.strftime("%d.%m.%Y")))
    await query.answer("Следующий платёж %s" % when.strftime("%d.%m.%Y"))
    await open_service(update, context, sid)


# ------------------------------------------------------------ напоминание --
async def reminder_loop(app):
    """Раз в несколько часов смотрит, не пора ли платить.

    Пишет не чаще раза в сутки на сервис: иначе за неделю до срока владелец
    получит два десятка одинаковых сообщений и перестанет их читать.
    """
    await asyncio.sleep(120)
    while True:
        try:
            await check_and_notify(app)
        except Exception as e:
            print("Счета: напоминание не отправлено — %s" % e)
        await asyncio.sleep(CHECK_SECONDS)


async def check_and_notify(app):
    """Один проход. Возвращает, о скольких сервисах напомнили."""
    if not ADMIN_ID:
        return 0
    due = await db.billing_due()
    if not due:
        return 0
    today = date.today().isoformat()
    fresh = []
    for s in due:
        key = "billing_notified_%d" % s["id"]
        if (await db.get_setting(key)) == today:
            continue
        fresh.append(s)
    if not fresh:
        return 0
    text = "💳 " + due_text(fresh)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💳 Счета", callback_data="bill_menu")]])
    await app.bot.send_message(chat_id=ADMIN_ID, text=text,
                               parse_mode=ParseMode.MARKDOWN,
                               reply_markup=kb,
                               disable_web_page_preview=True)
    for s in fresh:
        await db.set_setting("billing_notified_%d" % s["id"], today)
    return len(fresh)

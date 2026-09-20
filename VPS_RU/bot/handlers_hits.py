# -*- coding: utf-8 -*-
"""Попытки достучаться до закрытого: сбор с узла и разбор владельцем.

Фильтр работал молча: домен не открылся — и всё. Владелец узнавал об этом,
только если человек приходил жаловаться, а тот, кто ходит на закрытое, приходит
последним.

Узел пишет голый факт: когда, с какого адреса в туннеле, куда. Здесь факт
обрастает тем, что знает только бот: чей это ключ, как человека зовут, с какого
внешнего адреса он в этот момент подключался.

Разбор устроен как заявки, а не лента: посмотрел — отметил разобранным. Лента,
в которой всё вперемешку и ничего нельзя закрыть, перестаёт читаться на второй
неделе.
"""
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import WG_API_URL, api_session, escape_md, dt_to_moscow, show_screen

PER_PAGE = 8


async def collect_hits():
    """Забирает с узла новое и раскладывает по людям.

    Забираем по времени последней записи у себя: узел отдаёт историю целиком,
    а повторы отсекает сама база.
    """
    try:
        since = await db.last_filter_hit_ts()
    except Exception:
        since = 0

    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/dns/hits",
                                   params={"since": since}, timeout=10) as resp:
                if resp.status != 200:
                    return 0
                rows = (await resp.json()).get("hits") or []
    except Exception:
        return 0
    if not rows:
        return 0

    # Адрес в туннеле → человек. Карта одна на всю пачку: людей немного, а
    # запрашивать её на каждую запись значило бы долбить узел зря.
    try:
        from filters import peer_addr_map
        ips = await peer_addr_map()
    except Exception:
        ips = {}
    who = {}
    for uuid_val, addrs in (ips or {}).items():
        for addr in addrs:
            who[addr] = uuid_val

    names, publics = {}, {}
    added = 0
    for row in rows:
        ip = row.get("ip") or ""
        uuid_val = who.get(ip)
        name = None
        public = None
        if uuid_val:
            if uuid_val not in names:
                try:
                    user = await db.get_user_by_uuid(uuid_val)
                    names[uuid_val] = user["name"] if user else None
                except Exception:
                    names[uuid_val] = None
            name = names[uuid_val]
            # Внешний адрес — тот, что известен сейчас. Он меняется, и записать
            # его задним числом уже не выйдет: через неделю искать будет негде.
            if uuid_val not in publics:
                try:
                    seen = await db.get_user_ips(uuid_val)
                    publics[uuid_val] = seen[0]["ip"] if seen else None
                except Exception:
                    publics[uuid_val] = None
            public = publics[uuid_val]
        try:
            await db.add_filter_hit(
                datetime.utcfromtimestamp(int(row.get("ts") or 0)),
                uuid_val, name, ip, public,
                (row.get("domain") or "").lower(), row.get("category"),
                row.get("ref"))
            added += 1
        except Exception:
            pass
    return added


# Категории, о которых не пишем. Это не цензура сводки, а разница в природе
# события: к трекерам браузер стучится сам, десятками за одну открытую
# страницу, и человек про это даже не знает. Сводка из таких строк — шум, в
# котором тонет единственное, ради чего её читают.
#
# Спрятать их совсем тоже нельзя: тогда числа в сводке не сойдутся с числами на
# экране. Поэтому они идут одной строкой в конце.
QUIET_CATEGORIES = {"ads", "tracking"}

# Как часто писать. Не чаще: инциденты приходят пачками, и сводка раз в пять
# минут превратилась бы в ту же ленту, от которой мы уходим.
NOTIFY_QUIET_MINUTES = 60
NOTIFY_CHOICES = (15, 60, 180, 720)

# Сколько строк в одной сводке. Дальше — «и ещё N»: длинное сообщение читают по
# диагонали, а короткое читают.
NOTIFY_LINES = 8

LAST_KEY = "hits_notified_id"
AT_KEY = "hits_notified_at"
ON_KEY = "hits_notify_on"
EVERY_KEY = "hits_notify_every"


async def notify_enabled():
    return (await db.get_setting(ON_KEY) or "1") == "1"


async def notify_every():
    try:
        return int(await db.get_setting(EVERY_KEY) or NOTIFY_QUIET_MINUTES)
    except (TypeError, ValueError):
        return NOTIFY_QUIET_MINUTES


def _digest_text(rows, quiet_count):
    """Сводка: кто, куда и сколько раз. Людьми, а не строками журнала."""
    by_person = {}
    for r in rows:
        who = r["name"] or (r["tunnel_ip"] or "неизвестный ключ")
        by_person.setdefault(who, []).append(r)

    lines = ["🚨 **Новые инциденты**", ""]
    shown = 0
    for who, items in sorted(by_person.items(),
                             key=lambda kv: -len(kv[1])):
        if shown >= NOTIFY_LINES:
            break
        doms = []
        for it in items:
            d = it["domain"]
            if d not in doms:
                doms.append(d)
        tail = (", …и ещё %d" % (len(doms) - 3)) if len(doms) > 3 else ""
        lines.append("**%s** — %d" % (escape_md(who), len(items)))
        lines.append("     `%s`%s" % (escape_md(", ".join(doms[:3])), tail))
        shown += 1
    left = len(by_person) - shown
    if left > 0:
        lines.append("")
        lines.append("_…и ещё людей: %d._" % left)
    if quiet_count:
        lines.append("")
        lines.append("_Плюс %d по рекламе и трекерам — о них не пишу: туда "
                     "браузер ходит сам._" % quiet_count)
    return chr(10).join(lines)


async def notify_new(app):
    """Одна сводка, не чаще выбранного промежутка. Возвращает, о скольких сказано."""
    from utils import ADMIN_ID
    if not ADMIN_ID or not await notify_enabled():
        return 0

    try:
        last_id = int(await db.get_setting(LAST_KEY) or 0)
    except (TypeError, ValueError):
        last_id = 0

    # Первый запуск: не вываливаем всю историю разом — она может копиться
    # неделями, и первое же сообщение было бы стеной текста. Запоминаем точку и
    # пишем со следующего раза.
    if not last_id:
        await db.set_setting(LAST_KEY, await db.hits_max_id())
        return 0

    rows = await db.hits_since(last_id)
    if not rows:
        return 0

    # Тишина между сводками. Считаем ПОСЛЕ того, как убедились, что есть о чём
    # писать: иначе пустой проход двигал бы отсчёт и сводка приходила бы реже
    # обещанного.
    import time as _time
    try:
        at = float(await db.get_setting(AT_KEY) or 0)
    except (TypeError, ValueError):
        at = 0
    if _time.time() - at < await notify_every() * 60:
        return 0

    loud = [r for r in rows if (r.get("category") or "") not in QUIET_CATEGORIES]
    quiet_count = len(rows) - len(loud)

    # Отметку двигаем в любом случае: и тихие тоже разобраны, просто молча.
    await db.set_setting(LAST_KEY, rows[-1]["id"])
    if not loud:
        return 0

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚨 Открыть инциденты", callback_data="hit_list")],
         [InlineKeyboardButton("🔕 Реже или выключить",
                               callback_data="hit_notify")]])
    try:
        await app.bot.send_message(chat_id=ADMIN_ID,
                                   text=_digest_text(loud, quiet_count),
                                   parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb,
                                   disable_web_page_preview=True)
    except Exception as e:
        print(f"Инциденты: сводка не ушла — {e}")
        return 0
    await db.set_setting(AT_KEY, _time.time())
    return len(loud)


async def hits_loop(app):
    """Забираем раз в пять минут. Чаще незачем: разбирают такое не в реальном
    времени, а узел не должен отвечать на опросы вместо работы."""
    await asyncio.sleep(90)
    while True:
        try:
            await collect_hits()
            await notify_new(app)
        except Exception as e:
            print(f"Попытки на закрытое: {e}")
        await asyncio.sleep(300)


async def notify_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Как часто писать о новых инцидентах."""
    query = update.callback_query
    on = await notify_enabled()
    every = await notify_every()

    lines = ["🔔 **Сводка по инцидентам**", "",
             ("Сейчас: **раз в %d мин.**" % every) if on
             else "Сейчас: **выключена**", "",
             "Приходит одной сводкой, а не строкой на каждый случай: инциденты "
             "идут пачками, и лента из них перестаёт читаться на второй день.",
             "",
             "_Реклама и трекеры в сводку не попадают — туда браузер ходит сам, "
             "десятками за одну страницу. Их число видно последней строкой, "
             "чтобы цифры сходились с экраном._"]

    kb = [[InlineKeyboardButton(("✅ " if on and d == every else "") +
                                ("%d мин." % d if d < 60 else "%d ч." % (d // 60)),
                                callback_data=f"hit_notify_{d}")
           for d in NOTIFY_CHOICES]]
    kb.append([InlineKeyboardButton("🔕 Выключить сводку" if on
                                    else "🔔 Включить сводку",
                                    callback_data="hit_notify_off")])
    kb.append([InlineKeyboardButton("🔙 К инцидентам", callback_data="hit_list")])
    await show_screen(query, context, chr(10).join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def notify_set(update: Update, context: ContextTypes.DEFAULT_TYPE, minutes):
    if minutes not in NOTIFY_CHOICES:
        await update.callback_query.answer("Такого промежутка нет", show_alert=True)
        return
    await db.set_setting(EVERY_KEY, int(minutes))
    await db.set_setting(ON_KEY, "1")
    await update.callback_query.answer("Готово")
    await notify_screen(update, context)


async def notify_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    on = await notify_enabled()
    await db.set_setting(ON_KEY, "0" if on else "1")
    await update.callback_query.answer("Выключено" if on else "Включено")
    await notify_screen(update, context)


def _when(dt):
    return dt_to_moscow(dt).strftime("%d.%m %H:%M") if dt else "—"


async def hits_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    """Список заявок. Свежие сверху, неразобранные помечены.

    Список ОДИН. Раньше он печатался дважды — сначала текстом, потом теми же
    строками в кнопках, — и читать приходилось одно и то же по два раза. Кнопка
    и есть строка списка: по ней и жмут.
    """
    query = update.callback_query
    await collect_hits()

    total = await db.count_filter_hits()
    fresh = await db.count_filter_hits(only_new=True)
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, pages - 1))
    rows = await db.list_filter_hits(limit=PER_PAGE, offset=page * PER_PAGE)

    lines = ["🚨 **Инциденты**", ""]
    if not rows:
        lines += ["Пока никто никуда не стучался.", "",
                  "_Записываются обращения к доменам, которые закрыты фильтром "
                  "или доступами. Если фильтры никому не включены, здесь будет "
                  "пусто._"]
    else:
        lines.append("Всего **%d**, не разобрано **%d**" % (total, fresh))
        if pages > 1:
            lines.append("Страница **%d** из **%d**" % (page + 1, pages))
        lines += ["", "🔴 — не разобрано, ▫️ — разобрано.",
                  "_Нажмите на строку, чтобы открыть._"]

    kb = []
    for row in rows:
        mark = "🔴" if not row["seen_at"] else "▫️"
        # Всё, по чему узнают строку, — в самой кнопке: когда, кто, куда.
        # Домен обрезаем с конца: начало у него осмысленное, хвост — зона.
        who = (row["name"] or row["tunnel_ip"] or "?")[:12]
        dom = row["domain"] or ""
        if len(dom) > 22:
            dom = dom[:21] + "…"
        kb.append([InlineKeyboardButton(
            "%s %s · %s · %s" % (mark, _when(row["happened_at"]), who, dom),
            callback_data="hit_open_%s" % row["id"])])

    # Переключатель страниц: со стрелками по краям и номером посередине.
    # Одни стрелки не говорят ни где ты, ни сколько осталось.
    if pages > 1:
        nav = []
        nav.append(InlineKeyboardButton(
            "◀️" if page else "·",
            callback_data=("hit_pg_%d" % (page - 1)) if page else "svc_noop"))
        nav.append(InlineKeyboardButton("%d / %d" % (page + 1, pages),
                                        callback_data="svc_noop"))
        nav.append(InlineKeyboardButton(
            "▶️" if page + 1 < pages else "·",
            callback_data=("hit_pg_%d" % (page + 1)) if page + 1 < pages
            else "svc_noop"))
        kb.append(nav)

    # Две кнопки уборки стоят порознь и названы по-разному не для красоты.
    # Нажатые подряд они означают «удалить всё»: сначала всё становится
    # разобранным, потом разобранное исчезает. Рядом и одинаковыми они читались
    # бы как два шага одной уборки — и однажды ею бы и стали.
    if fresh:
        kb.append([InlineKeyboardButton("👁 Пометить просмотренными · %d" % fresh,
                                        callback_data="hit_seen_all")])
    seen = total - fresh
    if seen:
        kb.append([InlineKeyboardButton("🗑 Удалить просмотренные · %d" % seen,
                                        callback_data="hit_drop_seen")])
    # Поиск по номеру — то, ради чего номер и показан человеку. Ставим рядом со
    # списком: сюда владелец приходит с номером в руках.
    kb.append([InlineKeyboardButton("🔎 Найти по номеру", callback_data="hit_find")])
    kb.append([InlineKeyboardButton("🗓 Сколько хранить", callback_data="hit_keep"),
               InlineKeyboardButton("🔔 Сводка", callback_data="hit_notify")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, chr(10).join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def drop_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет просмотренные — сейчас, а не по сроку.

    С подтверждением: удаление безвозвратно, а кнопка стоит рядом с пометкой
    «просмотрено». Промахнуться по соседней и стереть разбор целиком — слишком
    дешёвая ошибка для такой цены.
    """
    query = update.callback_query
    if context.user_data.get("hit_drop_sure") != "1":
        context.user_data["hit_drop_sure"] = "1"
        seen = (await db.count_filter_hits()) - (await db.count_filter_hits(only_new=True))
        await show_screen(
            query, context,
            "🗑 **Удалить просмотренные?**\n\n"
            "Карточек: **%d**. Удаление безвозвратно — номера со страницы "
            "отказа по ним больше не найдутся.\n\n"
            "_Непросмотренные останутся на месте._" % seen,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🗑 Да, удалить",
                                       callback_data="hit_drop_seen")],
                 [InlineKeyboardButton("✖️ Отмена", callback_data="hit_list")]]),
            parse_mode=ParseMode.MARKDOWN)
        return
    context.user_data["hit_drop_sure"] = None
    try:
        gone = await db.delete_seen_hits()
    except Exception as e:
        await query.answer("Не вышло: %s" % e, show_alert=True)
        return
    await query.answer("Удалено разобранных: %d" % gone, show_alert=True)
    await hits_screen(update, context)



async def hit_open(update: Update, context: ContextTypes.DEFAULT_TYPE, hit_id):
    """Одна заявка целиком — всё, что нужно для разбора, на одном экране."""
    query = update.callback_query
    row = await db.get_filter_hit(hit_id)
    if not row:
        await query.answer("Заявки нет", show_alert=True)
        return await hits_screen(update, context)

    await db.mark_filter_hit_seen(hit_id)

    lines = [
        "🚨 **Инцидент** `%s`" % (row.get("ref") or "без номера"), "",
        f"🕒 {_when(row['happened_at'])} (МСК)",
        f"👤 {escape_md(row['name'] or 'ключ не определён')}",
        f"🌐 Домен: `{escape_md(row['domain'])}`",
        f"🚦 Причина: {escape_md(row['category'] or 'доступы')}",
        "",
        f"📍 В туннеле: `{row['tunnel_ip'] or '—'}`",
        f"📡 Внешний адрес: `{row['public_ip'] or 'не записан'}`",
    ]
    if row["user_uuid"]:
        lines.append(f"🔑 Ключ: `{row['user_uuid']}`")
    else:
        lines += ["", "_Адрес в туннеле не сошёлся ни с одним ключом: пир могли "
                      "снять или перевыпустить после события._"]

    kb = []
    if row["user_uuid"]:
        kb.append([InlineKeyboardButton("🔑 Открыть ключ",
                                        callback_data=f"user_detail_{row['user_uuid']}")])
        kb.append([InlineKeyboardButton("🧹 Фильтры этого ключа",
                                        callback_data=f"flt_user_{row['user_uuid']}")])
    kb.append([InlineKeyboardButton("🔙 К списку", callback_data="hit_list")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)



async def hit_find_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просит номер. Он приходит от человека — с экрана, из переписки, вслух."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_hit_ref"
    await show_screen(
        query, context,
        "🔎 **Поиск по номеру**\n\n"
        "Пришлите номер инцидента — тот, что человек видел на странице:\n"
        "`9395-570A`\n\n"
        "_Регистр и дефис не важны: перепишут как получится._",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="hit_list")]]),
        parse_mode=ParseMode.MARKDOWN)


async def hit_find_entered(update, context):
    """Разбирает присланный номер и открывает инцидент."""
    context.user_data["state"] = None
    raw = (update.message.text or "").strip()
    chat_id = update.message.chat_id

    row = None
    try:
        row = await db.find_filter_hit(raw)
    except Exception as e:
        print(f"Поиск инцидента: {e}")

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚨 К инцидентам", callback_data="hit_list")]])
    if not row:
        await context.bot.send_message(
            chat_id=chat_id, reply_markup=kb, parse_mode=ParseMode.MARKDOWN,
            text=(f"Ничего не нашлось по `{escape_md(raw[:24])}`.\n\n"
                  "Такое бывает, если номер переписали с ошибкой или запись уже "
                  "вытеснена — журнал на узле хранит недавнее, а не всю "
                  "историю."))
        return True

    lines = [
        "🚨 **Инцидент** `%s`" % (row.get("ref") or "без номера"), "",
        f"🕒 {_when(row['happened_at'])} (МСК)",
        f"👤 {escape_md(row['name'] or 'ключ не определён')}",
        f"🌐 Домен: `{escape_md(row['domain'])}`",
        f"🚦 Причина: {escape_md(row['category'] or 'доступы')}",
        "",
        f"📍 В туннеле: `{row['tunnel_ip'] or '—'}`",
        f"📡 Внешний адрес: `{row['public_ip'] or 'не записан'}`",
    ]
    buttons = []
    if row.get("user_uuid"):
        lines.append(f"🔑 Ключ: `{row['user_uuid']}`")
        buttons.append([InlineKeyboardButton(
            "🔑 Открыть ключ", callback_data=f"user_detail_{row['user_uuid']}")])
        buttons.append([InlineKeyboardButton(
            "🧹 Фильтры этого ключа", callback_data=f"flt_user_{row['user_uuid']}")])
    buttons.append([InlineKeyboardButton("🚨 К инцидентам", callback_data="hit_list")])

    try:
        await db.mark_filter_hit_seen(row["id"])
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text="\n".join(lines),
                                   reply_markup=InlineKeyboardMarkup(buttons),
                                   parse_mode=ParseMode.MARKDOWN)
    return True

async def hits_seen_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.mark_all_filter_hits_seen()
    await update.callback_query.answer("Отмечено")
    await hits_screen(update, context)


async def keep_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сколько хранить карточки.

    Два срока, а не один, потому что карточки разные. Разобранная — прочитанная
    история: неделю она ещё нужна, дальше только копится. Неразобранная ждёт
    владельца, и выбросить её раньше значит выбросить то, чего он не видел.
    """
    query = update.callback_query
    seen_days, new_days = await db.hits_keep_days()

    lines = ["🗓 **Сколько хранить инциденты**", "",
             f"Разобранные: **{seen_days} дн.** — первый ряд кнопок",
             f"Неразобранные: **{new_days} дн.** — второй ряд", "",
             "Сроки разные не случайно. Разобранная карточка — прочитанная "
             "история, она интересна несколько дней. Неразобранная ещё ждёт "
             "вас, и выбросить её раньше значит выбросить то, чего вы не "
             "видели.", "",
             "_Совсем без хранения нельзя: человек приходит с номером со "
             "страницы отказа, и этот номер должен где-то находиться._"]

    kb = [
        [InlineKeyboardButton(("✅ " if d == seen_days else "") + str(d),
                              callback_data=f"hit_keep_seen_{d}")
         for d in db.HITS_KEEP_CHOICES],
        [InlineKeyboardButton(("✅ " if d == new_days else "") + str(d),
                              callback_data=f"hit_keep_new_{d}")
         for d in db.HITS_KEEP_CHOICES],
        [InlineKeyboardButton("🧹 Убрать то, что старше срока",
                              callback_data="hit_keep_now")],
        [InlineKeyboardButton("🔙 К инцидентам", callback_data="hit_list")],
    ]

    await show_screen(query, context, chr(10).join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def keep_set(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   which: str, days: int):
    if days not in db.HITS_KEEP_CHOICES:
        await update.callback_query.answer("Такого срока нет", show_alert=True)
        return
    await db.set_hits_keep(**{which: days})
    seen_days, new_days = await db.hits_keep_days()
    # Говорим, если поправили сами: неразобранные не могут жить меньше
    # разобранных, и молча подменённое число выглядело бы как непонятая кнопка.
    if which == "new" and new_days != days:
        await update.callback_query.answer(
            "Неразобранные не могут храниться меньше разобранных — "
            "оставил %d дн." % new_days, show_alert=True)
    else:
        await update.callback_query.answer("Готово")
    await keep_screen(update, context)


async def keep_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Убрать старое прямо сейчас, не дожидаясь уборки."""
    query = update.callback_query
    try:
        gone = await db.cleanup_filter_hits()
    except Exception as e:
        await query.answer("Не вышло: %s" % e, show_alert=True)
        return
    await query.answer("Убрано карточек: %d" % gone, show_alert=True)
    await keep_screen(update, context)

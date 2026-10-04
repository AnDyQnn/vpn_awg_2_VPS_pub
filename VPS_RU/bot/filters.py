# -*- coding: utf-8 -*-
"""Фильтрация сайтов по категориям: экраны и передача раскладки на узел.

Три вещи в проекте похожи, но решают разное, и путать их дорого:
  • split-tunnel — маршрут: что идёт мимо туннеля напрямую;
  • роли — доступ к домашним сервисам ВНУТРИ туннеля;
  • фильтры — что человеку не открывается в интернете.
Здесь именно третье.

Как это работает без перевыпуска конфигов: в выданных конфигах записан внешний DNS,
и менять их значило бы выдавать всем новые. Вместо этого узел заворачивает 53-й порт
на себя — и только для тех, у кого фильтры включены. Различать людей можно потому,
что в туннеле адрес пира и есть личность: WireGuard сверяет ключ с AllowedIPs.

Чего фильтр не умеет, и это надо говорить прямо: DNS-over-HTTPS в браузере идёт мимо.
Он рассчитан на обычную семейную историю, а не на того, кто целенаправленно обходит.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from utils import (exit_kb, escape_md, WG_API_URL, api_session, show_screen,
                   dt_to_moscow)

# Адрес бота узел сам не знает: он живёт в сети, а не в Telegram. Бот сообщает
# его вместе с раскладкой фильтров, чтобы на странице отказа было куда написать.
BOT_LINK = {"url": ""}


def remember_bot_link(username):
    if username:
        BOT_LINK["url"] = f"https://t.me/{str(username).lstrip('@')}"

# Порядок важен: сверху то, что включают чаще всего.
CATEGORIES = [
    ("malware", "Опасные сайты"),
    ("ads", "Реклама и слежка"),
    ("adult", "Для взрослых"),
    ("gambling", "Азартные игры"),
    ("social", "Соцсети"),
    ("streaming", "Видео и стриминг"),
    ("torrent", "Торренты и пиратство"),
    ("crypto", "Криптовалюты"),
    ("drugs", "Наркотики и серые аптеки"),
]
# Прежние категории, слитые в новые: «Мошенничество» и «Шифровальщики» — в
# опасные сайты, «Слежка» — в рекламу. База переводится при старте бота;
# словарь нужен и для старых записей в журнале инцидентов.
CATEGORY_ALIASES = {"scam": "malware", "ransomware": "malware", "tracking": "ads"}
TITLES = dict(CATEGORIES)


async def peer_ip_map():
    """uuid → адрес в туннеле. Узел знает людей только по адресам."""
    from acl import peer_ip_map as _map
    return await _map()


def parse_site(raw: str):
    """Достаёт домен из чего угодно: ссылки, адреса с www, просто имени.

    Возвращает (домен, ошибка). Домен приводится к нижнему регистру и без
    `www.`: списки хранятся именно так, а человек пишет как придётся."""
    import re

    text = (raw or "").strip().lower()
    if not text:
        return None, "Пустая строка"
    text = re.sub(r"^[a-z]+://", "", text)      # отрезаем протокол
    text = text.split("/")[0].split("?")[0]     # путь и параметры не нужны
    text = text.split("@")[-1]                  # на случай почтового вида
    text = text.strip(".")
    if text.startswith("www."):
        text = text[4:]
    if not re.match(r"^[a-z0-9а-яё-]+(\.[a-z0-9а-яё-]+)+$", text):
        return None, "Не похоже на адрес сайта. Пример: `example.com`"
    return text, None


async def peer_addr_map():
    """uuid → все адреса человека в туннеле.
    Живёт здесь же, рядом с `peer_ip_map`, чтобы точка подмены была одна."""
    from acl import peer_addr_map as _map
    return await _map()


async def all_categories():
    """Что можно включить человеку: встроенные категории и свои пулы.

    Пул ведёт себя как категория во всём — включается, попадает под исключения,
    называется на странице отказа своим именем. Разница только в том, откуда
    взялся список.
    """
    own = []
    try:
        own = [(p["key"], p["title"]) for p in await db.list_filter_pools()]
    except Exception:
        own = []
    return list(CATEGORIES) + own


async def titles():
    """Название по ключу — и для встроенных, и для своих."""
    out = dict(TITLES)
    try:
        for pool in await db.list_filter_pools():
            out[pool["key"]] = pool["title"]
    except Exception:
        pass
    return out


async def apply_filters(reason: str = ""):
    """Отдаёт узлу готовую раскладку «адрес → категории».

    Считает бот: база есть только у него. Узел получает адреса и списки, заворачивает
    порт и подтягивает нужные списки доменов — только те, что кем-то включены."""
    try:
        by_uuid = await db.get_all_filters()
        ips = await peer_addr_map()
    except Exception as e:
        return False, f"не удалось собрать фильтры: {e}"

    clients = {}
    for uuid_val, cats in by_uuid.items():
        if not cats:
            continue
        # Все адреса человека: фильтр должен работать на каждом.
        for ip in ips.get(uuid_val, []):
            clients[ip] = cats

    try:
        common = await db.get_common_filters()
        custom = await db.get_custom_blocks()
    except Exception:
        common, custom = [], []

    # Мягкий режим: категории, которые не режем, но отмечаем. Что уже режется
    # общей категорией, из наблюдения убираем — там и так запрет.
    try:
        watch = [c for c in await db.get_watch_filters() if c not in common]
    except Exception:
        watch = []

    # Исключения — вопреки категории. Личные привязаны к ключу, а узел знает
    # только адреса, поэтому здесь же переводим одно в другое.
    try:
        allow_common, allow_by_uuid = await db.get_all_filter_allow()
    except Exception:
        allow_common, allow_by_uuid = [], {}
    allow_clients = {}
    for uuid_val, domains in allow_by_uuid.items():
        for ip in ips.get(uuid_val, []):
            allow_clients[ip] = domains

    # Снятое лично с общих категорий. Тоже переводим ключи в адреса: узел про
    # людей не знает, он знает адреса.
    try:
        exempt_by_uuid = await db.get_all_exempt()
    except Exception:
        exempt_by_uuid = {}
    except_clients = {}
    for uuid_val, cats in exempt_by_uuid.items():
        for ip in ips.get(uuid_val, []):
            except_clients[ip] = cats

    # Свои пулы едут вместе с раскладкой: узел кладёт их в тот же кэш, откуда
    # читает встроенные категории, и дальше не различает.
    try:
        pools = {p["key"]: p["domains"] for p in await db.list_filter_pools()}
    except Exception:
        # Не прочитали — не шлём вовсе: узел по пустому списку решил бы, что
        # групп нет, и убрал бы их файлы.
        pools = None

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/dns/filters",
                                    json={"clients": clients,
                                          "except_clients": except_clients,
                                          "common": common,
                                          "custom": custom,
                                          "allow_common": allow_common,
                                          "allow_clients": allow_clients,
                                          "watch": watch,
                                          "pools": pools,
                                          "bot_link": BOT_LINK["url"]}, timeout=10) as resp:
                if resp.status != 200:
                    return False, f"узел отклонил фильтры: {await resp.text()}"
                data = await resp.json()
    except Exception as e:
        return False, f"узел недоступен: {e}"

    # Общие правила и свой список действуют на всех: число «лично под
    # фильтром» их не видит, и владелец, закрыв сайт всем, читал «0 чел.».
    if common or custom:
        # Агент в Германии — не человек, в число не входит.
        people = sum(1 for addrs in ips.values()
                     if any(a != "10.13.13.254" for a in addrs))
        msg = (f"Фильтры применены: общие правила — на всех ({people} чел.)"
               + (f", лично ещё {data.get('filtered', 0)}"
                  if data.get("filtered") else ""))
    else:
        msg = f"Фильтры применены: под фильтром {data.get('filtered', 0)} чел."
    if allow_common or allow_clients:
        msg += (f" · исключений: {len(allow_common)} общих, "
                f"{sum(len(v) for v in allow_clients.values())} личных")
    if common:
        msg += f" · общих правил: {len(common)}"
    if custom:
        msg += f" · свой список: {len(custom)}"
    if reason:
        msg += f" ({reason})"
    try:
        await db.log_event("Filters", msg)
    except Exception:
        pass
    return True, msg


async def list_sizes():
    """Сколько доменов реально загружено по категориям — чтобы на экране было
    видно, работает фильтр или список ещё не подтянулся.

    None — узел не ответил. Это не то же самое, что «списков нет»: во время
    выкладки одно ядро узла занято сборкой, и ответ идёт по двадцать секунд.
    Раньше молчание читалось как пустые списки, и экран советовал жать
    «Применить» — при живых фильтрах и без того занятом узле."""
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/dns/filters", timeout=5) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("lists", {})
    except Exception:
        pass
    return None


async def filters_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    by_uuid = await db.get_all_filters()
    sizes = await list_sizes()

    common = await db.get_common_filters()
    custom = await db.get_custom_blocks()

    # Названия берём вместе со своими группами: иначе группа показывалась бы
    # своим внутренним ключом вроде `pool_1631`.
    TITLES_ALL = await titles()

    lines = ["🧹 **Фильтрация сайтов**", "",
             "_🚫 Запреты · 🟢 Исключения_", ""]
    if common or custom:
        parts = []
        if common:
            parts.append("категорий для всех: "
                         + ", ".join(TITLES_ALL.get(c, c) for c in common))
        if custom:
            parts.append(f"свой список: {len(custom)}")
        lines.append("🌍 **Общие правила** — " + "; ".join(parts))
        lines.append("")
    if not by_uuid and (common or custom):
        lines.append("Лично никому не включены — действуют только общие правила, "
                     "на всех.")
    elif not by_uuid:
        lines += ["Фильтры никому не включены — интернет у всех открыт полностью.",
                  "",
                  "Фильтр закрывает сайты по категориям и работает через свой DNS. "
                  "Перевыпускать конфиги не нужно: узел сам забирает запросы тех, "
                  "кому фильтр включён."]
    else:
        lines.append(f"Под фильтром: {len(by_uuid)} чел.")
        lines.append("")
        for uuid_val, cats in by_uuid.items():
            user = await db.get_user_by_uuid(uuid_val)
            name = escape_md((user or {}).get("name") or uuid_val[:8])
            # Имя переменной не должно совпадать с именем функции titles():
            # присваивание делает её локальной на всю функцию, и вызов выше
            # падает с UnboundLocalError — экран просто не открывался.
            cat_names = ", ".join(TITLES_ALL.get(c, c) for c in cats)
            lines.append(f"• **{name}** — {cat_names}")

    # Сколько доменов в списке — знание бесполезное: с ним ничего не сделаешь,
    # а увидев одну категорию из многих, владелец решал, что остальные сломаны.
    # Узел держит списки только тех категорий, которые кому-то включены, — и
    # это ровно то, о чём стоит сказать: не размер списка, а не оказалась ли
    # категория включённой БЕЗ списка. Вот это уже поломка: запрет стоит, а
    # закрывать нечем, и человек ходит куда хотел.
    on_now = set(common)
    for cats in by_uuid.values():
        on_now.update(cats)
    if sizes is None and on_now:
        lines += ["", "⏳ _Узел сейчас не ответил — проверить, загружены ли "
                      "списки, не вышло. Фильтры при этом работают как работали; "
                      "загляните через минуту._"]
    empty = sorted(c for c in on_now if sizes is not None and not sizes.get(c))
    if empty:
        lines += ["", "⚠️ **Списки не загрузились: "
                  + ", ".join(TITLES_ALL.get(c, c) for c in empty)
                  + ".** Запрет включён, а закрывать нечем — "
                    "нажмите «Применить на узле»."]

    # Оговорка нужна только тогда, когда фильтры кому-то включены: без них
    # обходить нечего, и предупреждение просто занимает экран.
    if on_now:
        lines += ["", "⚠️ _В браузере с DNS-over-HTTPS фильтр обходится: там "
                      "запрос уходит внутри HTTPS и на уровне DNS его не видно._"]

    watch = await db.get_watch_filters()
    if watch:
        total = await db.watch_total(168)
        lines.append("")
        lines.append("👁 **Мягкий контроль:** %s · обращений за неделю: %d"
                     % (", ".join(TITLES_ALL.get(c, c) for c in watch), total))

    kb = [[InlineKeyboardButton("🌍 Общие правила", callback_data="flt_common")],
          [InlineKeyboardButton("🟢 Исключения из запретов",
                                callback_data="flt_alw_all")],
          [InlineKeyboardButton("👁 Мягкий контроль", callback_data="flt_watch")],
          [InlineKeyboardButton("📦 Группы фильтров", callback_data="flt_pool_list")],
          [InlineKeyboardButton("👤 Выбрать человека", callback_data="flt_pick_0")]]
    if by_uuid:
        kb.append([InlineKeyboardButton("🔄 Применить на узле", callback_data="flt_apply")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)



# --- ИСКЛЮЧЕНИЯ ------------------------------------------------------------
# Категория закрывает пачку сайтов скопом, и почти всегда в этой пачке есть
# что-то нужное. Исключение разрешает такой сайт вопреки категории — всем или
# одному человеку. Проверяется раньше запретов, иначе смысла бы не имело.

async def allow_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       uuid_val=None):
    """Исключения из запретов: общие или для одного человека.

    Исключение — это «можно вопреки запрету». Видов три: сайт всем, сайт одному
    и целая категория одному. Третий раньше жил на другом экране, и человек,
    пришедший сюда со словами «открой мне весь этот блок», его не находил.
    """
    query = update.callback_query
    rows = await db.list_filter_allow(uuid_val=uuid_val, common=uuid_val is None)

    if uuid_val:
        user = await db.get_user_by_uuid(uuid_val)
        who = escape_md((user or {}).get("name") or uuid_val[:8])
        head = f"🟢 **Исключения · {who}**"
        # Назад — к человеку, откуда сюда и приходят.
        back = f"flt_user_{uuid_val}"
        add = f"flt_alw_add_{uuid_val}"
        scope = ("Открыто **только этому ключу**, даже если категория закрыта "
                 "ему или всем.")
    else:
        head = "🟢 **Общие исключения**"
        # Назад — в меню фильтров: именно оттуда сюда и жмут. Раньше вело в
        # «Общие правила» — экран, с которого сюда не приходят вовсе.
        back = "flt_menu"
        add = "flt_alw_add_all"
        scope = ("Открыто **всем**, даже если закрыта категория, в которую эти "
                 "сайты входят.")

    lines = [head, "", scope, "", "**Сайты:**"]
    if not rows:
        lines.append("_пока пусто_")
    else:
        for row in rows:
            lines.append(f"  🟢 `{escape_md(row['domain'])}`")

    kb = [[InlineKeyboardButton("➕ Разрешить сайт", callback_data=add)]]
    if not uuid_val:
        # Отсюда начинается «открыть кому-то конкретному»: человек приходит на
        # общий экран и ищет, как сделать исключение для себя.
        kb.append([InlineKeyboardButton("👤 Исключения для человека",
                                        callback_data="flt_pick_0")])
    for row in rows:
        kb.append([InlineKeyboardButton(f"🗑 {row['domain'][:28]}",
                                        callback_data=f"flt_alw_del_{row['id']}"
                                                      f"_{uuid_val or 'all'}")])

    # --- Третий вид: категория целиком, и только для человека ---------------
    #
    # Для «всех» его не бывает по смыслу: снять общий запрет со всех — это и
    # есть выключить общий запрет, для чего есть свой экран.
    if uuid_val:
        common = set(await db.get_common_filters())
        exempt = set(await db.get_user_exempt(uuid_val))
        titles = dict(await all_categories())

        lines += ["", "**Категории целиком:**"]
        if not common:
            lines.append("_для всех ничего не закрыто — выводить не из чего_")
        else:
            opened = [titles.get(k, k) for k in sorted(common) if k in exempt]
            lines.append("открыто: " + (", ".join(opened) if opened else "ничего"))
            lines.append("")
            lines.append("_Нажмите категорию, чтобы открыть её этому человеку "
                         "вопреки общему запрету._")
            for key in sorted(common):
                mark = "🟢 " if key in exempt else "🌍 "
                kb.append([InlineKeyboardButton(
                    mark + titles.get(key, key),
                    callback_data=f"flt_xa_{cat_token(key)}_{uuid_val}")])

    lines += ["", "_Разрешение сильнее запрета, а личное сильнее общего: "
                  "правило про конкретного человека заведомо осознаннее._"]

    kb.append([InlineKeyboardButton("🔙 Назад", callback_data=back)])

    await show_screen(query, context, chr(10).join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)



async def allow_add_request(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            uuid_val=None):
    query = update.callback_query
    context.user_data["state"] = "awaiting_filter_allow"
    context.user_data["allow_uuid"] = uuid_val
    who = "всем" if not uuid_val else "этому ключу"
    await show_screen(
        query, context,
        f"➕ **Разрешить сайт {who}**\n\n"
        "Пришлите домен или несколько — по одному в строке:\n"
        "`vk.com`\n`work-chat.example`\n\n"
        "Поддомены попадают под правило сами: разрешили `vk.com` — откроется и "
        "`login.vk.com`, иначе сайт всё равно не заработает.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена",
                                   callback_data=(f"flt_alw_{uuid_val}" if uuid_val
                                                  else "flt_alw_all"))]]),
        parse_mode=ParseMode.MARKDOWN)


async def allow_add_entered(update, context):
    """Разбирает присланное. Возвращает True, если сообщение было для нас."""
    uuid_val = context.user_data.get("allow_uuid")
    context.user_data["state"] = None
    raw = (update.message.text or "").strip()

    added, bad = [], []
    for part in raw.replace(",", "\n").split("\n"):
        value = part.strip().lower()
        if not value:
            continue
        if "://" in value:
            value = value.split("://", 1)[1]
        value = value.split("/")[0].strip(".")
        if not value or " " in value or "." not in value:
            bad.append(part.strip()[:30])
            continue
        await db.add_filter_allow(value, uuid_val)
        added.append(value)

    back = f"flt_alw_{uuid_val}" if uuid_val else "flt_alw_all"
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🟢 К исключениям", callback_data=back)]])
    if not added:
        await context.bot.send_message(
            chat_id=update.message.chat_id, reply_markup=kb,
            text="⚠️ Ничего не разобрал. Нужен домен — например, `vk.com`.",
            parse_mode=ParseMode.MARKDOWN)
        return True

    ok, msg = await apply_filters("добавлено исключение")
    text = "🟢 Разрешено вопреки запрету: " + ", ".join(f"`{a}`" for a in added)
    if bad:
        text += "\n\n⚠️ Не понял: " + ", ".join(bad)
    text += "\n\n" + ("Применено на узле." if ok else f"⚠️ Узел: {msg}")
    await context.bot.send_message(chat_id=update.message.chat_id, text=text,
                                   reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    return True


async def allow_remove(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       allow_id, uuid_val=None):
    await db.delete_filter_allow(allow_id)
    await apply_filters("снято исключение")
    await update.callback_query.answer("Убрано")
    await allow_screen(update, context, uuid_val)


# --- ГРУППЫ ФИЛЬТРОВ -------------------------------------------------------------
# Готовые категории собраны чужими людьми по чужим соображениям: в них нет
# российских ресурсов и нет того, что владелец считает лишним именно у себя.
# Пул — это категория, собранная им самим: список доменов и название.

def cat_token(key):
    """Категория в данных кнопки.

    Своя группа зовётся ключом вида pool_<имя>_<хвост> — с подчёркиваниями и
    длиной до 26 знаков. В кнопке она стоит рядом с uuid человека, и вышло
    две беды: разбор по «_» принимал хвост ключа за начало uuid (группа не
    вешалась — база отказывала), а длинное имя выводило данные кнопки за 64
    байта, после чего Telegram не показывал экран вовсе. Поэтому в кнопку идёт
    короткий знак: P и хвост ключа."""
    if key.startswith("pool_"):
        return "P" + key.rsplit("_", 1)[-1]
    return key


async def cat_from_token(tok):
    """Обратно из знака в ключ. Полный ключ (старые кнопки в чате) — как есть."""
    if len(tok) == 5 and tok[0] == "P":
        for pool in await db.list_filter_pools():
            if pool["key"].rsplit("_", 1)[-1] == tok[1:]:
                return pool["key"]
    return tok


async def split_cat_uuid(data, prefix):
    """«<префикс><категория>_<uuid>» → (uuid, категория). uuid подчёркиваний
    не содержит, поэтому режем справа: в ключе группы они есть."""
    tok, uuid_val = data[len(prefix):].rsplit("_", 1)
    return uuid_val, await cat_from_token(tok)


def _pool_key(title):
    """Короткий ключ из названия. По нему пул знают узел и база, поэтому только
    латиница и цифры: кириллицу в имени файла кэша узел бы не принял."""
    import hashlib
    slug = "".join(c for c in (title or "").lower()
                   if c.isalnum() and c.isascii())[:16]
    tail = hashlib.blake2b(title.encode(), digest_size=2).hexdigest()
    return ("pool_" + (slug + "_" if slug else "") + tail)[:40]


async def pool_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pools = await db.list_filter_pools()

    lines = ["📦 **Группы фильтров**", ""]
    if not pools:
        lines += [
            "Групп нет.",
            "",
            "Группа — это своя категория: даёте ей название, заливаете список "
            "адресов, и дальше она включается людям так же, как встроенные.",
            "",
            "_Пригодится там, где готовые списки не подходят: свои ресурсы, "
            "российские сервисы, «то, что не надо детям» по вашему разумению._",
        ]
    else:
        for pool in pools:
            lines.append(f"  📦 **{escape_md(pool['title'])}** — "
                         f"{len(pool['domains'])} доменов")

    kb = [[InlineKeyboardButton("➕ Добавить группу", callback_data="flt_pool_new")]]
    for pool in pools:
        kb.append([InlineKeyboardButton(f"📦 {pool['title'][:26]}",
                                        callback_data=f"flt_pool_o_{pool['key']}")])
    kb.append([InlineKeyboardButton("🔙 К фильтрам", callback_data="flt_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


# Сколько знаков списка кладём в сообщение. Предел Telegram — 4096 на всё
# сообщение вместе с заголовком и подписью, поэтому с запасом.
POOL_INLINE_CHARS = 3200


def _fit_domains(domains, limit=POOL_INLINE_CHARS):
    """Сколько адресов с начала списка влезает в сообщение целиком."""
    out, size = [], 0
    for d in domains:
        size += len(d) + 1
        if size > limit:
            break
        out.append(d)
    return out


async def pool_file(update: Update, context: ContextTypes.DEFAULT_TYPE, key):
    """Весь список группы файлом — для длинных, что не влезли в сообщение."""
    import io
    query = update.callback_query
    pool = await db.get_filter_pool(key)
    if not pool:
        await query.answer("Группы нет", show_alert=True)
        return await pool_list(update, context)
    await query.answer()
    buf = io.BytesIO(("\n".join(pool["domains"]) + "\n").encode("utf-8"))
    buf.name = "%s.txt" % (key[len("pool_"):] if key.startswith("pool_") else key)
    await context.bot.send_document(
        chat_id=query.message.chat_id, document=buf,
        caption="📦 %s — %d доменов" % (pool["title"], len(pool["domains"])))


async def pool_open(update: Update, context: ContextTypes.DEFAULT_TYPE, key):
    query = update.callback_query
    pool = await db.get_filter_pool(key)
    if not pool:
        await query.answer("Группы нет", show_alert=True)
        return await pool_list(update, context)

    # Список — одним блоком кода: Telegram копирует его целиком одним нажатием,
    # и его можно сразу переслать или вставить в такую же группу у другого
    # владельца. Раньше показывались первые двенадцать адресов по одному.
    domains = pool["domains"]
    shown = _fit_domains(domains)
    n_nets = sum(1 for d in domains if is_net(d))
    n_masks = sum(1 for d in domains if is_mask(d))
    lines = [f"📦 **{escape_md(pool['title'])}**", "",
             f"Доменов: **{len(domains) - n_nets - n_masks}**"
             + (f" · подсетей: **{n_nets}**" if n_nets else "")
             + (f" · масок: **{n_masks}**" if n_masks else ""), ""]
    if shown:
        lines += ["```", "\n".join(shown), "```"]
    if len(domains) > len(shown):
        lines.append(f"…и ещё {len(domains) - len(shown)} — весь список файлом "
                     f"по кнопке ниже.")
    lines += ["", "_Включается человеку так же, как встроенная категория._"]

    kb = [[InlineKeyboardButton("➕ Добавить адреса",
                                callback_data=f"flt_pool_a_{key}")]]
    if len(domains) > len(shown):
        kb.append([InlineKeyboardButton("📄 Весь список файлом",
                                        callback_data=f"flt_pool_f_{key}")])
    kb += [[InlineKeyboardButton("🗑 Удалить группу", callback_data=f"flt_pool_d_{key}")],
           [InlineKeyboardButton("🔙 К группам", callback_data="flt_pool_list")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


# Подсказка про формат — одна на оба случая: и при создании группы, и при
# дописывании. Человек копирует адреса откуда попало, и ему надо сразу сказать,
# что приводить их к одному виду не нужно.
ASK_DOMAINS = (
    "Пришлите список **построчно** — по адресу в строке. Можно сразу сотни: "
    "выкачали перечень и вставили целиком.\n\n"
    "Вид значения не важен, всё это один и тот же сайт:\n"
    "`https://www.example.com/page`\n"
    "`www.example.com`\n"
    "`example.com`\n"
    "`0.0.0.0 example.com`\n\n"
    "_Схему, `www`, порт и путь срежу сам. Повторы уберу._\n\n"
    "Можно и подсети: `169.136.66.0/24`. Их закрывает уже не DNS, а "
    "файрвол — для приложений, которые при закрытых доменах идут на "
    "зашитые адреса.\n\n"
    "И маски: `маска:nalog.ru` — если приложение прячет свой трафик под "
    "чужой сайт на нестандартном порту. Настоящий сайт не пострадает: "
    "он работает на 443.")


async def pool_add_request(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           key=None):
    """Спрашивает адреса. Для новой группы это второй шаг: имя уже дали."""
    query = update.callback_query
    context.user_data["state"] = "awaiting_pool_domains"
    context.user_data["pool_key"] = key

    if key:
        pool = await db.get_filter_pool(key)
        head = f"📦 **Адреса в группу «{escape_md((pool or {}).get('title', ''))}»**"
        back = f"flt_pool_o_{key}"
    else:
        head = "📦 **Адреса в новую группу**"
        back = "flt_pool_list"

    await show_screen(
        query, context, head + "\n\n" + ASK_DOMAINS,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data=back)]]),
        parse_mode=ParseMode.MARKDOWN)


async def pool_name_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Первый шаг новой группы — название.

    Раньше сначала просили список, а имя спрашивали после: человек вставлял
    три сотни строк и только тогда узнавал, что нужно ещё и назвать. Порядок
    развёрнут — сперва имя, оно короткое.
    """
    query = update.callback_query
    context.user_data["state"] = "awaiting_pool_title"
    context.user_data["pool_domains"] = []
    await show_screen(
        query, context,
        "📦 **Новая группа**\n\n"
        "Как её назвать? Название увидит человек на странице отказа — пишите "
        "так, чтобы ему было понятно: «Взрослое», «Игры», «Соцсети без ВК».\n\n"
        "_Адреса попрошу следующим шагом._",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Отмена", callback_data="flt_pool_list")]]),
        parse_mode=ParseMode.MARKDOWN)


def _parse_net(value):
    """«169.136.66.0/24» или «169.136.66.7» → подсеть; иначе None."""
    import ipaddress
    try:
        net = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError:
        return None
    if net.version != 4 or net.prefixlen < 8 or not net.is_global:
        return None
    return str(net)


def is_net(entry):
    """Строка группы — подсеть, а не домен."""
    return "/" in entry and _parse_net(entry) is not None


MASK_PREFIXES = ("маска:", "mask:")


def _parse_mask(value):
    """«маска:nalog.ru» → «маска:nalog.ru»; не маска или кривая — None.

    Маска — имя, которым приложение представляется в начале шифрованного
    соединения, идя при этом на свой сервер. Likee называет себя nalog.ru и
    ya.ru на портах вроде 21278. Узел режет такое соединение, если оно не на
    443: настоящие сайты на других портах себя так не называют."""
    import re
    v = value.strip().lower()
    for p in MASK_PREFIXES:
        if v.startswith(p):
            name = v[len(p):].strip().strip(".")
            if re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", name):
                return "маска:" + name
            return None
    return None


def is_mask(entry):
    return str(entry).startswith("маска:")


def _parse_domains(raw):
    """Приводит присланное к именам доменов.

    Люди копируют адреса откуда попало: `https://www.site.ru/page`, `www.site.ru`,
    `site.ru`, строка из hosts-файла. Это один и тот же домен, и различать их
    нельзя: правило по `www.site.ru` не закроет `site.ru`, и человек будет
    уверен, что фильтр не работает.

    Поэтому срезаем схему, `www`, порт, путь и точку на конце. Остаётся имя.
    """
    import re
    out = []
    for part in (raw or "").replace(",", "\n").replace(";", "\n").split("\n"):
        value = part.strip().lower()
        if not value or value.startswith("#"):
            continue

        # Подсеть или адрес IPv4 — тоже годится: её закрывает не DNS, а
        # файрвол узла. Нужно для приложений, которые при закрытых доменах идут
        # на зашитые адреса (Likee — в сеть Bigo). Частные сети и слишком
        # широкие (шире /8) не берём: одна опечатка закрыла бы человеку всё.
        if value.startswith(MASK_PREFIXES):
            mask = _parse_mask(value)
            if mask:
                out.append(mask)
            continue                             # кривая маска — не домен

        net = _parse_net(value)
        if net:
            out.append(net)
            continue
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}(/\d{1,2})?$", value):
            continue                             # отвергнутая сеть — не домен

        chunks = value.split()
        if len(chunks) > 1 and chunks[0] in ("0.0.0.0", "127.0.0.1", "::1"):
            value = chunks[1]                    # строка из hosts-файла
        elif len(chunks) > 1:
            continue                             # фраза, а не адрес

        if "://" in value:
            value = value.split("://", 1)[1]     # http://, https://, любая схема
        value = value.split("/")[0]              # путь
        value = value.split("?")[0].split("#")[0]
        value = value.split("@")[-1]             # логин в адресе
        value = value.split(":")[0]              # порт
        value = value.strip(".")
        if value.startswith("www."):
            # `www` — не отдельный сайт. Оставить его значило бы завести
            # правило, которое не сработает на том же сайте без `www`.
            value = value[4:]

        if value and "." in value and " " not in value and len(value) <= 100:
            out.append(value)
    # Порядок не важен, а повторы в присланных списках бывают всегда.
    return sorted(set(out))


async def pool_domains_entered(update, context):
    """Принял список адресов в уже созданную группу."""
    key = context.user_data.get("pool_key")
    domains = _parse_domains(update.message.text or "")
    chat_id = update.message.chat_id

    if not domains:
        context.user_data["state"] = None
        await context.bot.send_message(
            chat_id=chat_id, text="⚠️ Ни одного домена не разобрал.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 К группам", callback_data="flt_pool_list")]]))
        return True

    if key:
        pool = await db.get_filter_pool(key)
        if not pool:
            context.user_data["state"] = None
            return True
        merged = sorted(set(pool["domains"]) | set(domains))
        await db.save_filter_pool(key, pool["title"], merged)
        context.user_data["state"] = None
        ok, msg = await apply_filters("дописан пул")
        await context.bot.send_message(
            chat_id=chat_id, parse_mode=ParseMode.MARKDOWN,
            text=(f"📦 В группу «{escape_md(pool['title'])}» добавлено "
                  f"**{len(merged) - len(pool['domains'])}** новых, всего "
                  f"**{len(merged)}**.\n\n"
                  + ("Применено на узле." if ok else f"⚠️ Узел: {msg}")),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📦 К группе",
                                       callback_data=f"flt_pool_o_{key}")]]))
        return True

    # Сюда можно попасть только без имени группы — значит, разговор потерян.
    context.user_data["state"] = None
    await context.bot.send_message(
        chat_id=chat_id,
        text="⚠️ Непонятно, в какую группу. Откройте её и нажмите "
             "«Добавить адреса».",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📦 К группам",
                                   callback_data="flt_pool_list")]]))
    return True

async def pool_title_entered(update, context):
    """Имя получено — группа заведена, осталось наполнить.

    Заводим сразу, ещё пустой: держать имя в памяти до конца разговора нельзя,
    разговор человек может и бросить.
    """
    title = (update.message.text or "").strip()[:40]
    context.user_data["state"] = None
    chat_id = update.message.chat_id

    if not title:
        await context.bot.send_message(
            chat_id=chat_id, text="⚠️ Пустое название — группа не создана.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📦 К группам",
                                       callback_data="flt_pool_list")]]))
        return True

    key = _pool_key(title)
    await db.save_filter_pool(key, title, [])
    context.user_data["state"] = "awaiting_pool_domains"
    context.user_data["pool_key"] = key
    await context.bot.send_message(
        chat_id=chat_id, parse_mode=ParseMode.MARKDOWN,
        text=("📦 Группа «%s» создана." % escape_md(title)
              + chr(10) + chr(10) + ASK_DOMAINS),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✖️ Позже",
                                   callback_data="flt_pool_o_" + key)]]))
    return True


async def pool_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, key):
    pool = await db.get_filter_pool(key)
    await db.delete_filter_pool(key)
    await apply_filters("удалена группа")
    await update.callback_query.answer(
        f"Пул «{(pool or {}).get('title', '')}» удалён" if pool else "Удалено")
    await pool_list(update, context)

async def pick_user(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    users = await db.get_all_users()
    by_uuid = await db.get_all_filters()
    per = 8
    total = max(1, (len(users) + per - 1) // per)
    page = max(0, min(page, total - 1))
    chunk = users[page * per:(page + 1) * per]

    kb = []
    for u in chunk:
        mark = "🧹 " if by_uuid.get(u["uuid"]) else ""
        kb.append([InlineKeyboardButton(f"{mark}{u['name']}",
                                        callback_data=f"flt_user_{u['uuid']}")])
    if total > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"flt_pick_{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="svc_noop"))
        if page < total - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"flt_pick_{page+1}"))
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Фильтры", callback_data="flt_menu")])

    await show_screen(query, context, "\U0001F464 **Выберите человека**\n\n"
                                  "Отмеченные значком уже под фильтром.",
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def user_filters_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              uuid_val: str):
    """Категории одного человека.

    Состояний у категории три, и путать их нельзя.

    Личный запрет — владелец закрыл её этому человеку. Общий — она закрыта
    всем сразу. Личное исключение — она закрыта всем, но этому человеку
    открыта.

    Третьего раньше не было вовсе, и это было настоящей дырой: общая категория
    не снималась ни для кого. Единственным обходом оставалось перечислять
    домены поштучно в разрешениях — для категории вроде «для взрослых» это не
    работает и работать не может.
    """
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Ключ не найден")
        return await filters_menu(update, context)

    mine = set(await db.get_user_filters(uuid_val))
    common = set(await db.get_common_filters())
    exempt = set(await db.get_user_exempt(uuid_val))

    closed = (mine | common) - (exempt - mine)
    lines = [f"🧹 **Фильтры: {escape_md(user['name'])}**", ""]
    if closed:
        lines.append(f"Закрыто категорий: **{len(closed)}** из {len(CATEGORIES)}.")
    else:
        lines.append("Запретов нет — интернет открыт полностью.")

    if common:
        lines += ["", "🌍 — закрыто для всех. Такую категорию можно открыть "
                      "лично этому человеку: нажмите, и она станет 🟢."]
    lines += ["", "_Закрытый сайт не просто не открывается: человек попадает "
                  "на страницу с объяснением._"]

    # Значок говорит, откуда запрет. Одинаковый значок на личный и общий
    # запрет означал бы, что владелец не понимает, почему снятие не работает.
    kb = []
    for key, title in await all_categories():
        if key in mine:
            mark, cb = "🚫 ", f"flt_set_{cat_token(key)}_{uuid_val}"
        elif key in common and key in exempt:
            mark, cb = "🟢 ", f"flt_exc_{cat_token(key)}_{uuid_val}"
        elif key in common:
            mark, cb = "🌍 ", f"flt_exc_{cat_token(key)}_{uuid_val}"
        else:
            mark, cb = "", f"flt_set_{cat_token(key)}_{uuid_val}"
        kb.append([InlineKeyboardButton(mark + title, callback_data=cb)])

    kb.append([InlineKeyboardButton("🔙 К человеку",
                                    callback_data=f"user_detail_{uuid_val}")])
    # Исключения — рядом с категориями: закрыл «соцсети», тут же оставил рабочий
    # чат. Разносить это по разным экранам значит ломать один жест на два.
    kb.append([InlineKeyboardButton("🟢 Исключения из запретов",
                                    callback_data=f"flt_alw_{uuid_val}")])
    kb.append([InlineKeyboardButton("🧹 К списку фильтров", callback_data="flt_pick_0")])

    await show_screen(query, context, chr(10).join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def toggle_exempt(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        uuid_val: str, category: str, back: str = "user"):
    """Снимает с человека общую категорию или возвращает её."""
    query = update.callback_query
    now = set(await db.get_user_exempt(uuid_val))
    turning_on = category not in now
    await db.set_user_exempt(uuid_val, category, turning_on)
    ok, msg = await apply_filters("личное исключение из общей категории")
    titles_map = dict(await all_categories())
    name = titles_map.get(category, category)
    if ok:
        await query.answer(("«%s» открыта лично" % name) if turning_on
                           else ("«%s» снова закрыта по общему правилу" % name))
    else:
        await query.answer(msg, show_alert=True)
    # Возвращаемся туда, откуда нажали. Один и тот же переключатель живёт на
    # двух экранах, и уводить человека с того, где он работает, — верный способ
    # заставить его искать дорогу обратно.
    if back == "allow":
        await allow_screen(update, context, uuid_val)
    else:
        await user_filters_screen(update, context, uuid_val)



async def toggle_filter(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        uuid_val: str, category: str):
    mine = set(await db.get_user_filters(uuid_val))
    await db.set_user_filter(uuid_val, category, category not in mine)
    ok, msg = await apply_filters("изменение категорий")
    await update.callback_query.answer(msg if ok else msg, show_alert=not ok)
    await user_filters_screen(update, context, uuid_val)


async def apply_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, msg = await apply_filters("применение вручную")
    await update.callback_query.answer(msg, show_alert=True)
    await filters_menu(update, context)


# --- ОБЩИЕ ПРАВИЛА --------------------------------------------------------
async def common_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Правила, действующие сразу на всех.

    Отдельный экран, а не «выдать всем по очереди»: тридцать карточек руками —
    это не настройка, а работа, и она разъезжается при первом же новом ключе."""
    query = update.callback_query
    common = await db.get_common_filters()
    custom = await db.get_custom_blocks()

    lines = ["🌍 **Общие правила**", "",
             "Действуют на всех, кто ходит через узел, включая тех, кому "
             "личные фильтры не включали.", ""]
    if common:
        all_titles = await titles()
        lines.append("Категории: " + ", ".join(all_titles.get(c, c) for c in common))
    else:
        lines.append("Категории не выбраны.")
    if custom:
        shown = ", ".join(f"`{d}`" for d in custom[:8])
        lines.append(f"Свой список ({len(custom)}): {shown}"
                     + ("…" if len(custom) > 8 else ""))
    else:
        lines.append("Свой список пуст.")

    kb = []
    # Свои группы — здесь же: группа это категория, и запрещать её всем должно
    # быть можно так же, как встроенную. Иначе владелец собирает группу и не
    # находит её ровно там, где она нужнее всего.
    for key, title in await all_categories():
        mark = "🚫" if key in common else ""
        kb.append([InlineKeyboardButton(f"{mark} {title}".strip(),
                                        callback_data=f"flt_ctog_{key}")])
    kb.append([InlineKeyboardButton("➕ Закрыть сайт", callback_data="flt_cadd")])
    if custom:
        kb.append([InlineKeyboardButton("🚫 Свой список запретов",
                                        callback_data="flt_clist")])
    kb.append([InlineKeyboardButton("🔙 Фильтры", callback_data="flt_menu")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def common_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    common = set(await db.get_common_filters())
    common.symmetric_difference_update({key})
    await db.set_common_filters(common)
    ok, msg = await apply_filters("общие правила")
    await update.callback_query.answer(msg if ok else f"Не вышло: {msg}",
                                       show_alert=not ok)
    await common_screen(update, context)


# --- МЯГКИЙ КОНТРОЛЬ ------------------------------------------------------
# Категория не режется, но обращения к ней отмечаются. Наблюдение для
# владельца; человек по-прежнему открывает сайт и ничего не замечает.
async def watch_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    watch = set(await db.get_watch_filters())
    common = set(await db.get_common_filters())

    lines = ["👁 **Мягкий контроль**", "",
             "Категория не блокируется — человек открывает сайт как обычно. "
             "Мы лишь отмечаем обращения к ней и сводим их для вас.", ""]
    total = await db.watch_total(168)
    lines.append("Обращений за неделю: %d" % total)

    kb = []
    for key, title in await all_categories():
        if key in common:
            # То, что уже режется всем, наблюдать нечем: туда и так не пройти.
            continue
        mark = "👁" if key in watch else ""
        kb.append([InlineKeyboardButton(f"{mark} {title}".strip(),
                                        callback_data=f"flt_wtog_{key}")])
    if watch:
        kb.append([InlineKeyboardButton("📊 Кто и куда ходит",
                                        callback_data="flt_wstat")])
    keep = await db.watch_keep_days()
    kb.append([InlineKeyboardButton("🗓 Хранить: %d дн." % keep, callback_data="flt_wkeep"),
               InlineKeyboardButton("🧹 Очистить журнал", callback_data="flt_wclr")])
    kb.append([InlineKeyboardButton("🔙 Фильтры", callback_data="flt_menu")])
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def watch_keep_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сколько дней хранить журнал мягкого контроля. Старше — убирается сам,
    раз в сутки."""
    query = update.callback_query
    keep = await db.watch_keep_days()
    lines = ["🗓 **Сколько хранить журнал мягкого контроля**", "",
             "Записи старше срока убираются сами, раз в сутки.",
             "Сейчас: **%d дн.**" % keep]
    kb = [[InlineKeyboardButton(("✅ " if d == keep else "") + "%d дн." % d,
                                callback_data=f"flt_wkeep_{d}")
           for d in db.WATCH_KEEP_CHOICES],
          [InlineKeyboardButton("🔙 Мягкий контроль", callback_data="flt_watch")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def watch_keep_set(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    if days not in db.WATCH_KEEP_CHOICES:
        await update.callback_query.answer("Такого срока нет", show_alert=True)
        return
    await db.set_watch_keep_days(days)
    gone = await db.cleanup_filter_hits()
    await update.callback_query.answer("Готово" + (", убрано старых: %d" % gone if gone else ""))
    await watch_keep_screen(update, context)


async def watch_clear_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    total = await db.fetch_val("SELECT COUNT(*) FROM filter_hits WHERE watch") or 0
    lines = ["🧹 **Очистить журнал мягкого контроля?**", "",
             "Будут удалены все записи наблюдения: %d. Инциденты запрета "
             "и настройки категорий не затрагиваются." % total]
    kb = [[InlineKeyboardButton("✅ Очистить", callback_data="flt_wclr_do")],
          [InlineKeyboardButton("🔙 Отмена", callback_data="flt_watch")]]
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def watch_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = await db.clear_watch_hits()
    await update.callback_query.answer("Удалено записей: %d" % n)
    await watch_screen(update, context)


async def watch_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    watch = set(await db.get_watch_filters())
    watch.symmetric_difference_update({key})
    await db.set_watch_filters(watch)
    ok, msg = await apply_filters("мягкий контроль")
    await update.callback_query.answer(msg if ok else f"Не вышло: {msg}",
                                       show_alert=not ok)
    await watch_screen(update, context)


async def watch_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Люди за неделю: сколько обращений и по каким категориям. Каждого можно
    открыть и увидеть его сайты."""
    query = update.callback_query
    rows = await db.watch_summary(168)
    all_titles = await titles()

    people = {}
    for r in rows:
        p = people.setdefault(r["key"], {"who": r["who"], "hits": 0, "cats": []})
        p["hits"] += r["hits"]
        p["cats"].append(all_titles.get(r["category"], r["category"]))

    lines = ["📊 **Мягкий контроль: за неделю**", ""]
    kb = []
    if not people:
        lines.append("Обращений пока нет.")
    else:
        lines.append("Нажмите на человека, чтобы увидеть сайты.")
        for key, p in sorted(people.items(), key=lambda kv: -kv[1]["hits"])[:20]:
            label = "%s — %d · %s" % (p["who"] or "?", p["hits"], ", ".join(p["cats"]))
            kb.append([InlineKeyboardButton(label[:60], callback_data=f"flt_wper_{key}")])
    kb.append([InlineKeyboardButton("🔙 Мягкий контроль", callback_data="flt_watch")])
    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def watch_person_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    """Сайты одного человека в мягком режиме, свежие сверху."""
    query = update.callback_query
    rows = await db.watch_person(key, 168)
    all_titles = await titles()
    user = await db.get_user_by_uuid(key)
    who = (user or {}).get("name") or key

    lines = ["👁 **%s: за неделю**" % escape_md(who), ""]
    if not rows:
        lines.append("Обращений нет.")
    for r in rows:
        cat = all_titles.get(r["category"], r["category"])
        when = dt_to_moscow(r["last_at"]).strftime("%d.%m %H:%M") if r["last_at"] else ""
        lines.append("`%s` — %s, %d (посл. %s)"
                     % (escape_md(r["domain"]), escape_md(cat), r["hits"], when))
    kb = [[InlineKeyboardButton("🔙 Кто и куда ходит", callback_data="flt_wstat")]]
    await show_screen(query, context, "\n".join(lines)[:4000],
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def custom_add_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "awaiting_block_site"
    await show_screen(update.callback_query, context,
                      "➕ **Закрыть сайт**\n\nПришлите адрес: `example.com` или "
                      "ссылку целиком — разберу сам.\n\n"
                      "_Закроется и сам сайт, и его поддомены. Правило подействует "
                      "на всех._",
                      reply_markup=InlineKeyboardMarkup(
                          [[InlineKeyboardButton("🔙 Общие правила",
                                                 callback_data="flt_common")]]),
                      parse_mode=ParseMode.MARKDOWN)


async def custom_add_entered(update: Update, context: ContextTypes.DEFAULT_TYPE, raw):
    chat_id = update.effective_chat.id
    domain, err = parse_site(raw)
    if err:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {err}",
                                       parse_mode=ParseMode.MARKDOWN,
        reply_markup=exit_kb(("🚫 Свои блокировки", "flt_custom")))
        return
    context.user_data["state"] = None
    await db.add_custom_block(domain)
    ok, msg = await apply_filters(f"закрыт сайт {domain}")
    await context.bot.send_message(
        chat_id=chat_id,
        text=(f"✅ `{domain}` закрыт для всех.\n\n{msg}" if ok else f"⚠️ {msg}"),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Общие правила", callback_data="flt_common")]]),
        parse_mode=ParseMode.MARKDOWN)


async def custom_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    """Свой список с кнопками снятия: закрыть сайт легко, снять — тоже."""
    query = update.callback_query
    items = await db.get_custom_blocks()
    per = 8
    chunk = items[page * per:(page + 1) * per]

    lines = ["🚫 **Свой список запретов**", "",
             f"Закрыто сайтов: {len(items)}. Нажмите, чтобы снять запрет."]
    kb = [[InlineKeyboardButton(f"🗑 {d}", callback_data=f"flt_cdel_{d}")]
          for d in chunk]
    nav = []
    if page:
        nav.append(InlineKeyboardButton("←", callback_data=f"flt_cpg_{page - 1}"))
    if (page + 1) * per < len(items):
        nav.append(InlineKeyboardButton("→", callback_data=f"flt_cpg_{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Общие правила", callback_data="flt_common")])

    await show_screen(query, context, "\n".join(lines),
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def custom_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, domain: str):
    await db.remove_custom_block(domain)
    ok, msg = await apply_filters(f"снят запрет {domain}")
    await update.callback_query.answer(msg if ok else f"Не вышло: {msg}",
                                       show_alert=not ok)
    await custom_list(update, context)

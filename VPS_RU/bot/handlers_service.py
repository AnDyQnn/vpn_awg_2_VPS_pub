# -*- coding: utf-8 -*-
"""Раздел «Администрирование»: сводка состояния и контроль нагрузки.

Экран собран по принципу «сводка и действия»: сверху текстом то, что происходит
прямо сейчас, ниже кнопки. Сводка читается из базы и последнего снимка счётчиков,
а не опрашивает узлы при каждом открытии — на одном ядре лишние запросы ни к чему.

Три вещи, которые легко перепутать и которые здесь намеренно разведены:
  • контроль нагрузки — про ресурсы сервера, сколько пакетов человек вправе занять;
  • доступы внутри туннеля — про домашние сервисы;
  • фильтрация сайтов — про внешний интернет.
Сплит-туннель к ним не относится вовсе: это маршрутизация, а не ограничение.
"""
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from insights import event_verdict, node_ceiling
from utils import escape_md, dt_to_moscow, state_data, safe_delete, show_screen

DEFAULT_PPS_LIMIT = 5000
DEFAULT_BURST = 10000
# Потолок узла теперь один на весь проект и считается по факту —
# см. node_ceiling() в insights.py.
STEP = 500


async def _settings():
    limit = int(await db.get_setting("pps_limit") or DEFAULT_PPS_LIMIT)
    burst = int(await db.get_setting("pps_burst") or DEFAULT_BURST)
    mode = await db.get_setting("pps_mode") or "observe"
    return limit, burst, mode


async def admin_waiting():
    """Что ждёт внимания — разбором, а не одним числом.

    Раньше здесь считалась только сумма, а экран администрирования собирал те
    же данные заново и своими запросами. Две копии одной величины расходятся
    молча: на кнопке одно число, на экране другое, и объяснить его нечем.

    Отдаём список (подпись, сколько, куда вести). Число на кнопке — сумма.
    """
    items = []

    async def add(title, query, target, *args):
        try:
            n = await db.fetch_val(query, *args) or 0
        except Exception:
            n = 0
        if n:
            items.append((title, n, target))

    await add("обращений в поддержку",
              "SELECT COUNT(*) FROM support_tickets WHERE status='open'",
              "support_admin_menu")
    await add("нагружали сервер за сутки",
              "SELECT COUNT(DISTINCT user_uuid) FROM pps_events "
              "WHERE started_at > NOW() - INTERVAL '24 HOURS'",
              "svc_load")
    await add("в очереди на перевыпуск",
              "SELECT COUNT(*) FROM pending_retire", "kd_list")
    await add("решений по ключам",
              "SELECT COUNT(*) FROM pending_decisions WHERE resolved_at IS NULL",
              "kd_list")
    try:
        stuck = len(await db.get_stuck_deliveries())
    except Exception:
        stuck = 0
    if stuck:
        items.append(("не вышли на связь", stuck, "deliv_list"))
    return items


async def admin_counter() -> int:
    """Число на кнопке «Администрирование»: сколько всего ждёт внимания.
    Считаем только то, что требует действия, — уведомления сюда не лезут."""
    return sum(n for _title, n, _target in await admin_waiting())


async def service_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сводка + действия. Главная кнопка меняет подпись по состоянию, но остаётся
    на своём месте — чтобы глаз привыкал к расположению, а не переучивался."""
    query = update.callback_query
    limit, burst, mode = await _settings()

    # кто выходил за лимит за сутки
    try:
        events = await db.get_pps_events(24)
    except Exception:
        events = []
    offenders = {e["user_uuid"]: e for e in events}

    try:
        tickets = await db.fetch_val(
            "SELECT COUNT(*) FROM support_tickets WHERE status='open'") or 0
    except Exception:
        tickets = 0

    try:
        pending = await db.get_pending_retire()
    except Exception:
        pending = []

    try:
        personal = await db.get_peer_limits()
    except Exception:
        personal = {}

    mode_line = ("только наблюдение" if mode == "observe" else "ограничение включено")
    # Разбор числа с кнопки — первым делом. Иначе человек видит «3» на главной,
    # заходит сюда и читает три раздела прозой, не понимая, какие именно три.
    waiting = await admin_waiting()
    lines = ["🛡 **Администрирование**", ""]
    if waiting:
        lines.append(f"⏳ **Ждёт внимания: {sum(n for _t, n, _g in waiting)}**")
        for title, n, _target in waiting:
            lines.append(f"     • {n} — {title}")
        lines.append("_Кнопки на каждое — ниже._")
        lines.append("")
    lines += [
        f"🚦 *Ограничение нагрузки:* {mode_line}",
        f"     лимит `{limit}` пакетов в секунду, запас `{burst}`",
    ]
    if offenders:
        top = events[0]
        who = escape_md(top["name"] or "без имени")
        lines.append(f"     за сутки за лимит выходил {len(offenders)} чел. — {who} "
                     f"до `{top['peak_pps']}`")
    else:
        lines.append("     за сутки за лимит никто не выходил")
    if personal:
        lines.append(f"     персональных правил: {len(personal)}")

    lines.append("")
    if pending:
        waiting = sum(1 for p in pending if not p["first_handshake_at"])
        lines.append(f"🔑 *Перевыпуск ключей:* в очереди {len(pending)}, "
                     f"ещё не подключились {waiting}")
    else:
        lines.append("🔑 *Перевыпуск ключей:* очередь пуста")

    lines.append("")
    try:
        stuck = await db.get_stuck_deliveries()
    except Exception:
        stuck = []
    if stuck:
        blocked = sum(1 for s in stuck if s["blocked_at"])
        tail = f", из них не дошло {blocked}" if blocked else ""
        lines.append(f"📨 *Не подключились:* {len(stuck)} чел.{tail}")
    else:
        lines.append("📨 *Не подключились:* таких нет, все вышли на связь")

    lines.append("")
    try:
        decisions = await db.get_pending_decisions()
    except Exception:
        decisions = []
    if decisions:
        expired = sum(1 for d in decisions if d["reason"] == "expired")
        dormant = len(decisions) - expired
        parts = []
        if expired:
            parts.append(f"истёк срок — {expired}")
        if dormant:
            parts.append(f"уснули — {dormant}")
        lines.append("📋 *Ждут решения:* " + ", ".join(parts) + " (на паузе)")
    else:
        lines.append("📋 *Ждут решения:* нет, все ключи живые")

    lines.append("")
    try:
        roles = await db.list_roles()
        restricted = len(await db.get_access_matrix())
    except Exception:
        roles, restricted = [], 0
    if not roles:
        lines.append("🛡 *Доступы внутри туннеля:* ролей нет, все ходят друг к другу")
    else:
        lines.append(f"🛡 *Доступы внутри туннеля:* ролей {len(roles)}, "
                     f"под ограничением {restricted} чел.")

    try:
        filtered = await db.count_filtered_users()
    except Exception:
        filtered = 0
    try:
        names_count = await db.count_dns_names()
    except Exception:
        names_count = 0
    lines.append("🏷 *Имена в туннеле:* "
                 + (f"заведено {names_count}" if names_count
                    else "нет, ходим по адресам"))

    lines.append("🧹 *Фильтрация сайтов:* "
                 + (f"включена у {filtered} чел." if filtered
                    else "никому не включена"))

    lines.append("")
    # Протоколы — про способ подключения, а не про людей, поэтому отдельной
    # строкой и отдельным разделом.
    try:
        import xray
        on_xray = await db.count_xray_users()
        st = await xray.status()
        awg_on = st.get("awg", {}).get("enabled", True)
        xr_on = st.get("xray", {}).get("enabled", False)
        lines.append("🔀 *Протоколы:* AmneziaWG "
                     + ("включён" if awg_on else "выключен")
                     + ", Xray " + ("включён" if xr_on else "выключен")
                     + (f", на Xray {on_xray} чел." if on_xray else ""))
    except Exception:
        lines.append("🔀 *Протоколы:* узел не ответил")

    lines.append("")
    try:
        import donate
        d_rows = await donate.methods()
        if not d_rows:
            lines.append("💳 *Поддержка проекта:* реквизитов нет")
        else:
            lines.append("💳 *Поддержка проекта:* реквизитов " + str(len(d_rows))
                         + (", кнопка у людей есть" if await donate.enabled()
                            else ", кнопка у людей выключена"))
    except Exception:
        pass

    lines.append("")
    lines.append(f"🆘 *Обращения:* {'открытых нет' if not tickets else f'{tickets} открытых'}")

    main_label = ("🚦 Включить ограничение" if mode == "observe"
                  else "👁 Вернуть наблюдение")
    keyboard = []
    # Кнопка на каждое, что ждёт: человек пришёл сюда именно за этим, и
    # число на главной должно приводить его к делу, а не к прозе.
    # Одинаковые переходы схлопываем — решения и очередь перевыпуска живут
    # на одном экране, две кнопки в одно место только путают.
    seen_targets = set()
    for _title, _n, _target in waiting:
        if _target in seen_targets:
            continue
        seen_targets.add(_target)
        keyboard.append([InlineKeyboardButton(f"➡️ {_title} · {_n}",
                                              callback_data=_target)])
    keyboard += [
        [InlineKeyboardButton(main_label, callback_data="svc_mode_toggle")],
        [InlineKeyboardButton("📊 Нагрузка", callback_data="svc_load"),
         InlineKeyboardButton("⚖️ Лимиты", callback_data="svc_limits")],
        [InlineKeyboardButton("🔀 Протоколы", callback_data="proto_menu")],
        [InlineKeyboardButton("🛡 Доступы · роли", callback_data="roles_menu"),
         InlineKeyboardButton("🧹 Фильтры", callback_data="flt_menu")],
        [InlineKeyboardButton("🏷 Имена в туннеле", callback_data="dnm_menu"),
         # Не «Поддержка»: ниже есть «🆘 Поддержка» про обращения, и две кнопки
         # с одним словом читаются как одна и та же.
         InlineKeyboardButton("💳 Донаты", callback_data="don_menu")],
        [InlineKeyboardButton(
            "📋 Ждут решения" + (f" · {len(decisions)}" if decisions else ""),
            callback_data="kd_list"),
         InlineKeyboardButton(
            "📨 Не подключились" + (f" · {len(stuck)}" if stuck else ""),
            callback_data="deliv_list")],
    ]
    if not tickets:
        keyboard.append([InlineKeyboardButton("🆘 Поддержка", callback_data="support_admin_menu")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(keyboard),
                                  parse_mode=ParseMode.MARKDOWN)


async def toggle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение наблюдение ↔ ограничение. Отдельным экраном с подтверждением:
    показываем, кого и как заденет, прежде чем что-то включать."""
    query = update.callback_query
    limit, burst, mode = await _settings()

    if mode == "observe":
        try:
            events = await db.get_pps_events(24)
        except Exception:
            events = []
        free = len([1 for r in (await db.get_peer_limits()).values()
                    if r["mode"] == "unlimited"])
        # Пакеты по килобайту — обычная загрузка; мелкие пакеты торрента дают ту же
        # цифру пакетов при заметно меньшей скорости, поэтому лимит бьёт по нему.
        mbits = round(limit * 1200 * 8 / 1_000_000)
        text = (
            f"🚦 **Включить ограничение?**\n\n"
            f"Лимит `{limit}` пакетов в секунду на человека.\n\n"
            f"• обычная загрузка — примерно до {mbits} Мбит/с, не заденет\n"
            f"• торрент упрётся заметно раньше: его пакеты мелкие\n"
            f"• без ограничений остаются: {free}\n\n"
            f"За сутки наблюдения лимит сработал бы "
            f"{len({e['user_uuid'] for e in events})} раз(а)."
        )
        kb = [[InlineKeyboardButton("✅ Включить", callback_data="svc_mode_on"),
               InlineKeyboardButton("✖️ Отмена", callback_data="svc_menu")]]
    else:
        text = ("👁 **Вернуть режим наблюдения?**\n\n"
                "Ограничение перестанет применяться, но превышения по-прежнему "
                "будут записываться — чтобы было на чём подбирать порог.")
        kb = [[InlineKeyboardButton("✅ Вернуть наблюдение", callback_data="svc_mode_off"),
               InlineKeyboardButton("✖️ Отмена", callback_data="svc_menu")]]

    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, enforce: bool):
    await db.set_setting("pps_mode", "enforce" if enforce else "observe")
    await db.log_event("Load control",
                       f"Режим контроля нагрузки: {'ограничение' if enforce else 'наблюдение'}")
    await update.callback_query.answer(
        "Ограничение включено" if enforce else "Вернули наблюдение")
    await service_menu(update, context)


async def load_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кто нагружал сервер за сутки. Не «пробития порога», а понятные цифры."""
    # Потолок узла берём по факту, а не из вписанной цифры:
    # человек однажды выдал больше замера, и узел устоял.
    ceiling = await node_ceiling()
    query = update.callback_query
    limit, _, _ = await _settings()
    try:
        events = await db.get_pps_events(24)
    except Exception:
        events = []

    if not events:
        text = ("📊 **Нагрузка за сутки**\n\n"
                "За последние сутки за лимит никто не выходил.\n\n"
                f"Разрешено `{limit}` пакетов в секунду на человека, "
                f"сервер в сумме тянет около `{ceiling}`.")
    else:
        lines = ["📊 **Нагрузка за сутки**", ""]
        seen = set()
        for e in events:
            if e["user_uuid"] in seen:
                continue
            seen.add(e["user_uuid"])
            when = dt_to_moscow(e["ended_at"] or e["started_at"])
            verdict, worrying = event_verdict(dict(e), short=True)
            mark = "⚠️" if worrying else "•"
            # Одна строка на человека: кто, что это было, пик, когда.
            # Подробности — в его карточке, здесь они только мешают смотреть.
            lines.append(
                f"{mark} **{escape_md(e['name'] or 'без имени')}** — {verdict} · "
                f"`{e['peak_pps']}` пак/с · {when.strftime('%d.%m %H:%M')}")
            if len(seen) >= 8:
                break
        lines.append("")
        lines.append(f"Лимит `{limit}` пак/с на человека, узел тянет `{ceiling}`.")
        text = "\n".join(lines)

    kb = [[InlineKeyboardButton("📈 График нагрузки", callback_data="svc_chart")],
          [InlineKeyboardButton("⚖️ Лимиты", callback_data="svc_limits")],
          [InlineKeyboardButton("🔙 Назад", callback_data="svc_menu")]]
    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def limits_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий порог и персональные правила. В списке только те, у кого правило
    отличается от общего — иначе экран разрастётся на всех пиров сразу."""
    # Потолок узла берём по факту, а не из вписанной цифры:
    # человек однажды выдал больше замера, и узел устоял.
    ceiling = await node_ceiling()
    query = update.callback_query
    limit, burst, _ = await _settings()
    try:
        personal = await db.get_peer_limits()
        users = {u["uuid"]: u["name"] for u in await db.get_all_users()}
    except Exception:
        personal, users = {}, {}

    lines = [
        "⚖️ **Лимиты**", "",
        f"Общий лимит: `{limit}` пакетов в секунду",
        f"Кратковременный запас: `{burst}`", "",
        f"Сервер в сумме тянет около `{ceiling}` пакетов в секунду.",
        "Видео в 4К берёт примерно 2500, обычный браузинг — сотни.", "",
    ]
    if personal:
        lines.append("*Персональные правила:*")
        for uuid_val, rule in list(personal.items())[:10]:
            name = escape_md(users.get(uuid_val, uuid_val[:8]))
            if rule["mode"] == "unlimited":
                lines.append(f"  ♾ {name} — без ограничений")
            elif rule["mode"] == "custom":
                until = ""
                if rule["expires_at"]:
                    until = f", до {dt_to_moscow(rule['expires_at']).strftime('%d.%m %H:%M')}"
                lines.append(f"  ✂️ {name} — `{rule['limit_pps']}`{until}")
    else:
        lines.append("Персональных правил нет — все на общем лимите.")

    kb = [
        [InlineKeyboardButton(f"➖ {STEP}", callback_data="svc_limit_down"),
         # без разметки: кнопки Telegram markdown не понимают и показали бы кавычки
         InlineKeyboardButton(f"{limit} пак/с", callback_data="svc_noop"),
         InlineKeyboardButton(f"➕ {STEP}", callback_data="svc_limit_up")],
        [InlineKeyboardButton("3000", callback_data="svc_limit_3000"),
         InlineKeyboardButton("5000", callback_data="svc_limit_5000"),
         InlineKeyboardButton("6000", callback_data="svc_limit_6000")],
        [InlineKeyboardButton("👥 Правила по людям", callback_data="users_page_0")],
        [InlineKeyboardButton("🔙 Назад", callback_data="svc_menu")],
    ]
    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def change_limit(update: Update, context: ContextTypes.DEFAULT_TYPE, value: str):
    """Порог меняется шагом или готовым значением. Ниже тысячи и выше потолка узла
    не пускаем: первое душит всех, второе не имеет смысла."""
    # Потолок узла берём по факту, а не из вписанной цифры:
    # человек однажды выдал больше замера, и узел устоял.
    ceiling = await node_ceiling()
    limit, _, _ = await _settings()
    if value == "up":
        new = limit + STEP
    elif value == "down":
        new = limit - STEP
    else:
        new = int(value)
    new = max(1000, min(ceiling + 2000, new))
    await db.set_setting("pps_limit", str(new))
    await update.callback_query.answer(f"Лимит: {new} пакетов в секунду")
    await limits_screen(update, context)


async def set_peer_rule(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        uuid_val: str, mode: str):
    """Правило для конкретного человека: общий порог, свой или без ограничений.
    Временное правило («на сутки») снимается само — приструнить на вечер и забыть."""
    query = update.callback_query
    limit, _, _ = await _settings()

    if mode == "default":
        await db.clear_peer_limit(uuid_val)
        note = "переведён на общий лимит"
    elif mode == "unlimited":
        await db.set_peer_limit(uuid_val, "unlimited", None, None, query.from_user.id)
        note = "без ограничений"
    elif mode == "day":
        await db.set_peer_limit(uuid_val, "custom", max(1000, limit // 2),
                                datetime.utcnow() + timedelta(days=1), query.from_user.id)
        note = "ограничен на сутки"
    else:
        await db.set_peer_limit(uuid_val, "custom", max(1000, limit // 2), None,
                                query.from_user.id)
        note = "свой лимит"

    await db.log_event("Load control", f"Правило для {uuid_val}: {note}")
    await query.answer(f"Готово: {note}")

    await peer_limit_screen(update, context, uuid_val)


async def peer_limit_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            uuid_val: str):
    """Что человеку разрешено по пакетам и что можно поменять.

    Ограничение считается в пакетах в секунду, а не в мегабитах: узел упирается
    именно в пакеты. Поэтому на экране сразу написано, чему примерно равен предел
    в привычной скорости — иначе число ни о чём не говорит."""
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        await query.answer("Ключ не найден")
        return

    common, _, mode = await _settings()
    rule = (await db.get_peer_limits()).get(uuid_val)
    try:
        exceeded = await db.fetch_val(
            "SELECT COUNT(*) FROM pps_events WHERE user_uuid=$1 "
            "AND started_at > NOW() - INTERVAL '24 HOURS'", uuid_val) or 0
    except Exception:
        exceeded = 0

    if not rule:
        now_line = f"общий предел — **{common}** пакетов в секунду"
    elif rule["mode"] == "unlimited":
        now_line = "**без ограничения**"
    else:
        until = ""
        if rule["expires_at"]:
            until = (" (до " + dt_to_moscow(rule["expires_at"]).strftime("%d.%m %H:%M")
                     + ", потом вернётся общий)")
        now_line = f"свой предел — **{rule['limit_pps']}** пакетов в секунду{until}"

    mbits = round(common * 1200 * 8 / 1_000_000)
    lines = [
        f"🚦 **Ограничение: {escape_md(user['name'])}**",
        "",
        f"Сейчас: {now_line}.",
    ]
    if mode != "enforce":
        lines.append("⚠️ Режим наблюдения: ограничение записывается, но **не применяется**.")
    if exceeded:
        lines.append(f"За сутки упирался в предел: {exceeded} раз(а).")
    lines += [
        "",
        f"_Считаем пакеты, а не мегабиты: узел упирается именно в них. "
        f"{common} пак/с — это примерно {mbits} Мбит/с обычной загрузки, "
        f"а торрент упрётся раньше: его пакеты мелкие._",
    ]

    half = max(1000, common // 2)
    kb = [
        [InlineKeyboardButton(f"📐 Общий предел · {common} пак/с",
                              callback_data=f"svc_rule_default_{uuid_val}")],
        [InlineKeyboardButton(f"✂️ Свой предел · {half} пак/с",
                              callback_data=f"svc_rule_custom_{uuid_val}")],
        [InlineKeyboardButton("♾ Снять ограничение",
                              callback_data=f"svc_rule_unlimited_{uuid_val}")],
        [InlineKeyboardButton(f"⏱ Придушить на сутки · {half} пак/с",
                              callback_data=f"svc_rule_day_{uuid_val}")],
        [InlineKeyboardButton("🔙 К пользователю", callback_data=f"user_detail_{uuid_val}")],
    ]
    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)

async def load_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str = None):
    """Картинка с двумя панелями: скорость и пакеты.

    Отдаётся как экран: текущее сообщение убирается, картинка приходит с
    подписью и кнопками возврата. Иначе график падал в чат отдельным фото,
    с которого некуда нажать.

    На персональном графике опорная линия — лимит этого человека. Потолок узла
    там был бы бессмысленным: один пир до него не дотянется.
    """
    # Потолок узла берём по факту, а не из вписанной цифры:
    # человек однажды выдал больше замера, и узел устоял.
    ceiling = await node_ceiling()
    query = update.callback_query
    await query.answer("Рисую…")
    from graphs import generate_load_graph

    limit_line, title, who = None, None, None
    if uuid_val:
        user = await db.get_user_by_uuid(uuid_val)
        who = (user or {}).get("name", uuid_val[:8])
        title = f"Нагрузка за сутки · {who}"
        rule = (await db.get_peer_limits()).get(uuid_val)
        common = int(await db.get_setting("pps_limit") or DEFAULT_PPS_LIMIT)
        if not rule:
            limit_line = common
        elif rule["mode"] == "custom":
            limit_line = int(rule["limit_pps"] or common)
        # без ограничений — линию не рисуем вовсе

    try:
        path = await generate_load_graph(hours=24, uuid=uuid_val,
                                         title=title, limit_line=limit_line)
    except Exception as e:
        await show_screen(query, context, 
            f"⚠️ График не построился: `{escape_md(str(e))}`",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Графики", callback_data="vpn_graph")]]),
            parse_mode=ParseMode.MARKDOWN)
        return

    if who:
        caption = (f"📉 **{escape_md(who)}** — сутки\n"
                   f"Сверху скорость, снизу пакеты. Линия — "
                   f"{'его предел ' + str(limit_line) + ' пак/с' if limit_line else 'без ограничения'}.")
    else:
        caption = ("🚦 **Нагрузка узла за сутки**\n"
                   f"Сверху скорость, снизу пакеты. Линия — потолок узла, "
                   f"около {ceiling} пакетов в секунду.")

    # График про человека умеет вернуть к этому человеку: чаще всего сюда и
    # заходят из его карточки, а не из списка графиков.
    kb = []
    if uuid_val:
        kb.append([InlineKeyboardButton("🔙 К человеку",
                                        callback_data=f"user_detail_{uuid_val}")])
    kb.append([InlineKeyboardButton("👤 Выбрать человека", callback_data="svc_pick_0")])
    kb.append([InlineKeyboardButton("📊 Графики", callback_data="vpn_graph")])

    await safe_delete(context, query.message.chat_id, query.message.message_id)
    with open(path, "rb") as f:
        await context.bot.send_photo(chat_id=query.message.chat_id, photo=f,
                                     caption=caption,
                                     reply_markup=InlineKeyboardMarkup(kb),
                                     parse_mode=ParseMode.MARKDOWN)


async def charts_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Кого стоит посмотреть на графике.

    Картинок ровно столько же, сколько людей, и листать их все бессмысленно —
    интересны двое-трое. Поэтому экран отвечает не «вот все», а «вот эти, и вот
    почему». Кнопка «показать любого» остаётся: подбор — подсказка, а не запрет.
    """
    from insights import chart_candidates

    query = update.callback_query
    online = set()
    try:
        from utils import WG_API_URL, api_session
        import time as _time
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=5) as resp:
                if resp.status == 200:
                    now = int(_time.time())
                    for p in await resp.json():
                        hs = p.get("latest_handshake", 0)
                        if hs and now - hs < 180 and p.get("uuid"):
                            online.add(p["uuid"])
    except Exception:
        pass

    try:
        picks = await chart_candidates(online)
    except Exception as e:
        picks = []
        print(f"Подбор графиков: {e}")

    lines = ["📉 **Кому смотреть графики**", ""]
    kb = []
    if not picks:
        lines.append("Ничего примечательного за сутки: ни превышений, ни "
                     "неестественного потока, ни всплесков.")
        lines.append("")
        lines.append("Можно посмотреть общий график или выбрать человека вручную.")
    else:
        lines.append("Подобраны по поведению за сутки:")
        lines.append("")
        # Не больше пяти и по одной причине в строке: список из восьми человек
        # с одинаковым длинным хвостом причин читать невозможно, а решение по
        # нему всё равно принимается по верхним.
        for p in picks[:5]:
            lines.append(f"• **{escape_md(p['name'])}** — {p['reasons'][0]}")
            if len(p["reasons"]) > 1:
                lines.append(f"    и ещё: {'; '.join(p['reasons'][1:3])}")
            kb.append([InlineKeyboardButton(f"📉 {p['name']}",
                                            callback_data=f"svc_pchart_{p['uuid']}")])
        if len(picks) > 5:
            lines.append(f"\n_И ещё {len(picks) - 5} — через «Выбрать человека»._")

    kb.append([InlineKeyboardButton("👤 Выбрать человека", callback_data="svc_pick_0")])
    kb.append([InlineKeyboardButton("🔙 Графики", callback_data="vpn_graph")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def pick_peer_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Полный список — на случай, когда подбор не угадал."""
    query = update.callback_query
    users = await db.get_all_users()
    per = 8
    total = max(1, (len(users) + per - 1) // per)
    page = max(0, min(page, total - 1))
    chunk = users[page * per:(page + 1) * per]

    kb = [[InlineKeyboardButton(u["name"], callback_data=f"svc_pchart_{u['uuid']}")]
          for u in chunk]
    if total > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"svc_pick_{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="svc_noop"))
        if page < total - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"svc_pick_{page+1}"))
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Графики", callback_data="vpn_graph")])

    await show_screen(query, context, "👤 **График по человеку**",
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def graphs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единый вход во все графики.

    Три картинки отвечают на разные вопросы, и это написано прямо на экране:
    сколько прокачали, упираемся ли в потолок узла, и кого стоит посмотреть
    отдельно."""
    from insights import chart_candidates

    query = update.callback_query
    try:
        picks = await chart_candidates()
    except Exception:
        picks = []

    lines = [
        "📈 **Графики**",
        "",
        "📊 *Трафик* — сколько прокачали за период, по людям.",
        "🚦 *Нагрузка* — скорость и пакеты на двух панелях с линией потолка "
        "узла: видно, упираемся или нет.",
        "📉 *Подбор* — у кого за сутки было что-то примечательное.",
    ]
    if picks:
        lines.append("")
        lines.append(f"Сейчас в подборе: **{len(picks)}** — "
                     + escape_md(", ".join(p["name"] for p in picks[:5]))
                     + ("…" if len(picks) > 5 else ""))

    kb = [
        [InlineKeyboardButton("📊 Трафик по людям", callback_data="graph_traffic")],
        [InlineKeyboardButton("🚦 Нагрузка · скорость и пакеты", callback_data="svc_chart")],
        [InlineKeyboardButton(
            "📉 Подбор" + (f" · {len(picks)}" if picks else ""),
            callback_data="svc_charts")],
        [InlineKeyboardButton("👤 Выбрать человека", callback_data="svc_pick_0")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
    ]
    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)

async def whats_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Три последних версии. Кнопка нужна и админу: догадаться, что список изменений
    лежит в клиентском режиме, невозможно — особенно если проект кто-то скачал."""
    query = update.callback_query
    from changelog import admin_text, repo_markdown, fit

    text = admin_text()
    link = repo_markdown()
    if link:
        text += "\n\n" + link
    kb = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
    await show_screen(query, context, fit(text), reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)



# ------------------------ ТОКЕН ПАНЕЛЕЙ ------------------------
# Токен закрывает панели узлов вторым рубежом поверх правил файрвола. Его значение
# никого не интересует и нигде не вводится руками — бот генерирует его сам при первом
# запуске, если в окружении пусто, и раскладывает на обе ноды. Никаких кнопок.

async def _de_env_status():
    """Что у узла выхода задано. None — не ответил."""
    from utils import DE_AGENT_URL, api_session
    try:
        async with api_session() as session:
            async with session.get(f"{DE_AGENT_URL}/host/env_status", timeout=8) as r:
                if r.status != 200:
                    return None
                return await r.json()
    except Exception:
        return None


async def _push_token_to_de(token):
    from utils import DE_AGENT_URL, api_session
    try:
        async with api_session() as session:
            async with session.post(f"{DE_AGENT_URL}/host/set_env",
                                    json={"key": "API_TOKEN", "value": token},
                                    timeout=10) as r:
                return r.status == 200
    except Exception as e:
        print(f"Токен на клиент-сервер: {e}")
        return False


async def ensure_api_token(app):
    """Доводит токен панелей до одинакового состояния на обеих нодах.

    Раньше это было разовым действием: сгенерировать, разослать, записать в базу
    отметку «выдан». Результат не проверялся ни разу, поэтому любая потеря по
    дороге — а терялось тихо — делала отметку ложью. Бот считал дело сделанным,
    а панели оставались без токена.

    Теперь это состояние, которое поддерживается:
      • токена нет — выдаём и ДОЖИДАЕМСЯ, пока запись применится;
      • токен есть, а у Германии нет — досылаем;
      • совпали — молчим.

    Момент выбран не случайно: бот стартует сразу после деплоя, когда контейнеры
    и так только что пересоздавались. Значит короткий разрыв, неизбежный при
    записи переменной, приходится ровно на то же окно, а не на середину дня.
    """
    import secrets
    from utils import (API_TOKEN, ADMIN_ID, request_env_change,
                       env_change_applied)

    async def tell(text):
        if not ADMIN_ID:
            return
        try:
            await app.bot.send_message(chat_id=ADMIN_ID, text=text)
        except Exception:
            pass

    # --- токен у мастера есть: сверяем с узлом выхода ---------------------
    if API_TOKEN:
        status = await _de_env_status()
        if status is None:
            # Германия молчит — не повод что-то менять. Она примет мастера и
            # без токена: адрес в туннеле подделать нельзя.
            return
        if status.get("API_TOKEN"):
            return
        if await _push_token_to_de(API_TOKEN):
            await db.log_event("Security", "Токен панелей досаждён на клиент-сервер")
            await tell("🔑 Клиент-сервер получил токен панелей — обе панели "
                       "закрыты вторым рубежом поверх файрвола.")
        return

    # --- токена нет вовсе: выдаём ----------------------------------------
    token = secrets.token_urlsafe(24)
    flag = request_env_change("API_TOKEN", token)
    if not await env_change_applied(flag, timeout=60):
        # Отметку НЕ ставим: иначе бот запомнит несделанное как сделанное.
        await db.log_event("Security", "Токен панелей: запись не применилась")
        await tell("⚠️ Токен панелей выдать не вышло: служба обновлений на "
                   "сервере не ответила.\n\n"
                   "Проверьте: systemctl status vpn-updater\n"
                   "Панели пока защищены только файрволом. Бот попробует снова "
                   "при следующем запуске.")
        return

    from datetime import datetime
    await db.set_setting("api_token_issued_at", datetime.utcnow().isoformat())
    await db.log_event("Security", "Токен панелей выдан автоматически")
    print("🔑 Токен панелей выдан автоматически")
    # На Германию токен уедет следующим запуском: запись переменной пересоздаёт
    # контейнеры, и этот процесс прямо сейчас закончится. Досылать отсюда
    # бессмысленно — не успеем.
    await tell("🔑 Токен панелей выдан автоматически — бот сейчас перезапустится "
               "и досадит его на клиент-сервер.")


async def watch_api_token(app):
    """Повторная сверка во время работы.

    Узел выхода поднимается не всегда одновременно с мастером: он мог быть
    выключен, перезагружаться, обновляться. Раз в час проверяем заново, чтобы
    состояние сошлось само, а не после того, как кто-то заметит.
    """
    import asyncio
    while True:
        await asyncio.sleep(3600)
        try:
            await ensure_api_token(app)
        except Exception as e:
            print(f"Сверка токена панелей: {e}")


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
from utils import escape_md, dt_to_moscow, state_data, safe_delete

DEFAULT_PPS_LIMIT = 5000
DEFAULT_BURST = 10000
NODE_CEILING = 7500          # замеренный потолок узла, клиентских пакетов в секунду
STEP = 500


async def _settings():
    limit = int(await db.get_setting("pps_limit") or DEFAULT_PPS_LIMIT)
    burst = int(await db.get_setting("pps_burst") or DEFAULT_BURST)
    mode = await db.get_setting("pps_mode") or "observe"
    return limit, burst, mode


async def admin_counter() -> int:
    """Число на кнопке «Админка»: сколько всего ждёт внимания.
    Считаем только то, что требует действия, — уведомления сюда не лезут."""
    total = 0
    try:
        total += await db.fetch_val(
            "SELECT COUNT(*) FROM support_tickets WHERE status='open'") or 0
        total += await db.fetch_val(
            "SELECT COUNT(DISTINCT user_uuid) FROM pps_events "
            "WHERE started_at > NOW() - INTERVAL '24 HOURS'") or 0
        total += await db.fetch_val("SELECT COUNT(*) FROM pending_retire") or 0
        total += await db.fetch_val(
            "SELECT COUNT(*) FROM pending_decisions WHERE resolved_at IS NULL") or 0
        total += len(await db.get_stuck_deliveries())
    except Exception:
        pass
    return total


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
    lines = [
        "🛡 **Администрирование**",
        "",
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
        lines.append(f"📨 *Доставка ключей:* не подключились {len(stuck)}{tail}")
    else:
        lines.append("📨 *Доставка ключей:* все отправленные ключи дошли")

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
    lines.append("🧹 *Фильтрация сайтов:* "
                 + (f"включена у {filtered} чел." if filtered
                    else "никому не включена"))

    lines.append("")
    lines.append(f"🆘 *Обращения:* {'открытых нет' if not tickets else f'{tickets} открытых'}")

    main_label = ("🚦 Включить ограничение" if mode == "observe"
                  else "👁 Вернуть наблюдение")
    keyboard = []
    if tickets:
        keyboard.append([InlineKeyboardButton(f"🆘 Поддержка · {tickets}",
                                              callback_data="support_admin_menu")])
    keyboard += [
        [InlineKeyboardButton(main_label, callback_data="svc_mode_toggle")],
        [InlineKeyboardButton("📊 Нагрузка", callback_data="svc_load"),
         InlineKeyboardButton("⚖️ Лимиты", callback_data="svc_limits")],
        [InlineKeyboardButton("🔑 Переезд на новый ключ", callback_data="mig_menu")],
        [InlineKeyboardButton("🛡 Доступы · роли", callback_data="roles_menu"),
         InlineKeyboardButton("🧹 Фильтры", callback_data="flt_menu")],
        [InlineKeyboardButton(
            "📋 Ждут решения" + (f" · {len(decisions)}" if decisions else ""),
            callback_data="kd_list"),
         InlineKeyboardButton(
            "📨 Доставка" + (f" · {len(stuck)}" if stuck else ""),
            callback_data="deliv_list")],
    ]
    if not tickets:
        keyboard.append([InlineKeyboardButton("🆘 Поддержка", callback_data="support_admin_menu")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")])

    await query.edit_message_text("\n".join(lines),
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

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb),
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
                f"сервер в сумме тянет около `{NODE_CEILING}`.")
    else:
        lines = ["📊 **Нагрузка за сутки**", ""]
        seen = set()
        for e in events:
            if e["user_uuid"] in seen:
                continue
            seen.add(e["user_uuid"])
            when = dt_to_moscow(e["ended_at"] or e["started_at"])
            size = e["avg_packet_size"] or 0
            hint = " (мелкие пакеты — похоже на торрент)" if 0 < size < 500 else ""
            lines.append(
                f"**{escape_md(e['name'] or 'без имени')}** — до `{e['peak_pps']}` "
                f"пакетов в секунду\n"
                f"     {when.strftime('%d.%m %H:%M')}, средний пакет {size} байт{hint}")
            if len(seen) >= 8:
                break
        lines.append("")
        lines.append(f"Разрешено `{limit}` в секунду, сервер тянет около `{NODE_CEILING}`.")
        text = "\n".join(lines)

    kb = [[InlineKeyboardButton("📈 График нагрузки", callback_data="svc_chart")],
          [InlineKeyboardButton("⚖️ Лимиты", callback_data="svc_limits")],
          [InlineKeyboardButton("🔙 Назад", callback_data="svc_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def limits_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий порог и персональные правила. В списке только те, у кого правило
    отличается от общего — иначе экран разрастётся на всех пиров сразу."""
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
        f"Сервер в сумме тянет около `{NODE_CEILING}` пакетов в секунду.",
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
    await query.edit_message_text("\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def change_limit(update: Update, context: ContextTypes.DEFAULT_TYPE, value: str):
    """Порог меняется шагом или готовым значением. Ниже тысячи и выше потолка узла
    не пускаем: первое душит всех, второе не имеет смысла."""
    limit, _, _ = await _settings()
    if value == "up":
        new = limit + STEP
    elif value == "down":
        new = limit - STEP
    else:
        new = int(value)
    new = max(1000, min(NODE_CEILING + 2000, new))
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

    from handlers_users import render_user_detail
    await render_user_detail(context, query.message.chat_id, query.message.message_id, uuid_val)

async def load_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_val: str = None):
    """Картинка с двумя панелями: скорость и пакеты.

    Отдаётся как экран: текущее сообщение убирается, картинка приходит с
    подписью и кнопками возврата. Иначе график падал в чат отдельным фото,
    с которого некуда нажать.

    На персональном графике опорная линия — лимит этого человека. Потолок узла
    там был бы бессмысленным: один пир до него не дотянется.
    """
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
        await query.edit_message_text(
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
                   f"около {NODE_CEILING} пакетов в секунду.")

    kb = [[InlineKeyboardButton("👤 Выбрать человека", callback_data="svc_pick_0")],
          [InlineKeyboardButton("🔙 Графики", callback_data="vpn_graph")]]

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

    await query.edit_message_text("\n".join(lines),
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

    await query.edit_message_text("👤 **Чей график построить?**",
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
    await query.edit_message_text("\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)

async def whats_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Три последних версии. Кнопка нужна и админу: догадаться, что список изменений
    лежит в клиентском режиме, невозможно — особенно если проект кто-то скачал."""
    query = update.callback_query
    from changelog import admin_text, repo_link, fit

    text = admin_text()
    link = repo_link()
    if link:
        text += "\n\nИсходный код: " + link
    kb = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
    await query.edit_message_text(fit(text), reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)



# ------------------------ ТОКЕН ПАНЕЛЕЙ ------------------------
# Токен закрывает панели узлов вторым рубежом поверх правил файрвола. Его значение
# никого не интересует и нигде не вводится руками — бот генерирует его сам при первом
# запуске, если в окружении пусто, и раскладывает на обе ноды. Никаких кнопок.

async def ensure_api_token(app):
    """Выдаёт токен автоматически, если его нет.

    Момент выбран не случайно: бот стартует сразу после деплоя, когда контейнеры
    и так только что пересоздавались. Значит короткий разрыв, неизбежный при записи
    переменной, приходится ровно на то же окно, а не на середину рабочего дня.

    Защита от повторов: если запись почему-то не доехала, вторая попытка будет не
    раньше чем через час — иначе бот при каждом старте пересоздавал бы контейнеры.
    """
    import secrets
    from datetime import datetime, timedelta
    from utils import API_TOKEN, ADMIN_ID, request_env_change, DE_AGENT_URL, api_session

    if API_TOKEN:
        return

    try:
        last = await db.get_setting("api_token_issued_at")
        if last and datetime.utcnow() - datetime.fromisoformat(last) < timedelta(hours=1):
            return
    except Exception:
        pass

    token = secrets.token_urlsafe(24)
    de_ok = False
    try:
        async with api_session() as session:
            async with session.post(f"{DE_AGENT_URL}/host/set_env",
                                    json={"key": "API_TOKEN", "value": token},
                                    timeout=10) as r:
                de_ok = r.status == 200
    except Exception as e:
        print(f"Токен на клиент-сервер: {e}")

    request_env_change("API_TOKEN", token)
    await db.set_setting("api_token_issued_at", datetime.utcnow().isoformat())
    await db.log_event("Security", "Токен панелей выдан автоматически")
    print("🔑 Токен панелей выдан автоматически")

    if ADMIN_ID:
        try:
            await app.bot.send_message(
                chat_id=ADMIN_ID,
                text=("🔑 Токен панелей выдан автоматически — панели узлов закрыты "
                      "вторым рубежом поверх файрвола.\n\n"
                      + ("Клиент-сервер тоже получил его."
                         if de_ok else
                         "⚠️ Клиент-сервер не ответил — он получит токен при следующем "
                         "запуске бота. До тех пор его панель защищена файрволом."))
            )
        except Exception:
            pass

import os
import time
import aiohttp
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils import exit_kb, escape_md, stop_bg_tasks, deregister_menu, ADMIN_ID, CONFIGS_DIR, WG_API_URL, dt_to_moscow, api_session
from database import db
from acl import grant_text
from delivery import track_send, describe as delivery_text
from wireguard_manager import create_peer, delete_peer, pause_peer, resume_peer
from handlers_client import send_client_menu

async def users_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    await stop_bg_tasks()
    deregister_menu(update.effective_chat.id)
    
    users = await db.get_all_users()
    
    live_peers = {}
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    now = int(time.time())
                    for p in data:
                        hs = p.get('latest_handshake', 0)
                        if hs > 0 and (now - hs) < 180:
                            live_peers[p.get('uuid')] = True
    except: pass

    items_per_page = 5
    total_users = len(users)
    total_pages = max(1, (total_users + items_per_page - 1) // items_per_page)
    
    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0

    start = page * items_per_page
    end = start + items_per_page
    current_users = users[start:end]

    keyboard =[]
    for u in current_users:
        if not u.get('is_active', True):
            status_icon = "🔴"
        elif live_peers.get(u['uuid']):
            status_icon = "🟢"
        else:
            status_icon = "🟡"
            
        keyboard.append([InlineKeyboardButton(f"{status_icon} {u['name']}", callback_data=f"user_detail_{u['uuid']}")])

    if total_pages > 1:
        prev_page = (page - 1) % total_pages
        next_page = (page + 1) % total_pages
        nav_row =[
            InlineKeyboardButton("⬅️ Назад", callback_data=f"users_page_{prev_page}"),
            InlineKeyboardButton("Вперед ➡️", callback_data=f"users_page_{next_page}")
        ]
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")])
    
    text = (
        "👥 **Управление пользователями**\n"
        "🟢 Онлайн | 🟡 Офлайн | 🔴 Отключен\n\n"
        "Выберите пользователя:\n\n"
        f"📄 Страница: `[{page + 1}/{total_pages}]`"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def _tg_line(context, tg_ids):
    """Привязки человека: логин и числовой id.

    Логин — то, по чему владелец узнаёт человека; id — то, по чему его находит
    бот. Поэтому оба, а не вместо.

    Если логин ещё не известен, спрашиваем Telegram — но только в этом случае:
    иначе карточка ходила бы в сеть при каждом открытии. Узнав, запоминаем.
    """
    if not tg_ids:
        return "Не привязан"
    try:
        known = await db.get_tg_usernames(tg_ids)
    except Exception:
        known = {}

    parts = []
    for tid in tg_ids:
        login = known.get(tid)
        if not login and context is not None:
            try:
                chat = await context.bot.get_chat(tid)
                login = chat.username
                if login:
                    await db.set_tg_username(tid, login)
            except Exception:
                login = None
        parts.append(f"@{escape_md(login)} · `{tid}`" if login else f"`{tid}`")
    return ", ".join(parts)


async def render_user_detail(context, chat_id, message_id, uuid):
    user = await db.get_user_by_uuid(uuid)
    if not user: return

    # Адрес пира и время рукопожатия приходят от узла в том же ответе — раньше
    # бралась только отметка «онлайн», а адрес просто выбрасывался.
    is_online, peer_ip, hs_ago = False, None, None
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    now = int(time.time())
                    for p in data:
                        if p.get('uuid') == uuid:
                            hs = p.get('latest_handshake', 0)
                            peer_ip = (p.get('allowed_ips') or '').split('/')[0] or None
                            if hs > 0:
                                hs_ago = now - hs
                                if hs_ago < 180:
                                    is_online = True
    except: pass

    def _ago(sec):
        if sec is None:
            return "ни разу"
        if sec < 60:
            return f"{sec} сек назад"
        if sec < 3600:
            return f"{sec // 60} мин назад"
        if sec < 86400:
            return f"{sec // 3600} ч назад"
        return f"{sec // 86400} дн назад"

    # Действующее правило нагрузки. Нет правила — человек на общем лимите, и это
    # нормальное состояние, а не недонастроенное.
    limit_line = "общий"
    try:
        rule = (await db.get_peer_limits()).get(uuid)
        common = int(await db.get_setting("pps_limit") or 5000)
        if not rule:
            limit_line = f"общий, `{common}` пак/с"
        elif rule["mode"] == "unlimited":
            limit_line = "без ограничений"
        else:
            until = ""
            if rule["expires_at"]:
                until = f", до {dt_to_moscow(rule['expires_at']).strftime('%d.%m %H:%M')}"
            limit_line = f"свой, `{rule['limit_pps']}` пак/с{until}"
    except Exception:
        pass

    # Не просто «сколько раз», а что это было: последний случай словами.
    # Иначе разовая загрузка с телефона и торрент выглядят одинаково.
    exceeded, last_verdict, last_worrying = 0, "", False
    try:
        rows = await db.fetch_all(
            "SELECT started_at, ended_at, peak_pps, avg_packet_size, upload_share "
            "FROM pps_events WHERE user_uuid=$1 "
            "AND started_at > NOW() - INTERVAL '24 HOURS' "
            "ORDER BY started_at DESC", uuid)
        exceeded = len(rows)
        if rows:
            from insights import event_verdict
            last_verdict, last_worrying = event_verdict(dict(rows[0]))
    except Exception:
        pass

    if not user.get('is_active', True): status_str = "🔴 Отключен"
    elif is_online: status_str = "🟢 Онлайн"
    else: status_str = "🟡 Офлайн"

    safe_name = escape_md(user['name'])
    tg_ids = user.get('tg_ids',[])
    tg_status = await _tg_line(context, tg_ids)
    
    exp_str = dt_to_moscow(user['expires_at']).strftime('%d.%m.%Y %H:%M') if user.get('expires_at') else "Навсегда"
    created_str = dt_to_moscow(user['created_at']).strftime('%d.%m.%Y')
    
    user_ips = await db.get_user_ips(uuid)
    trusted_list = [r['ip'] for r in user_ips if r['status'] == 'trusted']
    pending_list = [r['ip'] for r in user_ips if r['status'] == 'pending']
    
    ips_text = ""
    if trusted_list or pending_list:
        ips_text += "\n🌐 **Сети, с которых подключались:**\n"
        for ip in trusted_list[:4]: ips_text += f"  ✅ `{ip}` (Доверенная)\n"
        for ip in pending_list[:4]: ips_text += f"  ⏳ `{ip}` (Проверка)\n"
        if len(trusted_list) + len(pending_list) > 8: ips_text += "  ...\n"
    else:
        ips_text += "\n🌐 **Сети:** Пока нет данных\n"

    # Доступы внутри туннеля. Пишем не только роли, но и что они дают: иначе
    # по названию роли непонятно, открыт человеку домашний сервер или нет.
    # Источник доступа (какая роль его дала) указан рядом — при нескольких ролях
    # это единственный способ понять, откуда взялось разрешение.
    roles_text = ""
    try:
        user_roles = await db.get_user_roles(uuid)
        if not user_roles:
            roles_text = "\n🛡 **Доступы:** без ограничений (ролей нет)\n"
        else:
            names = ", ".join(escape_md(r["name"]) for r in user_roles)
            roles_text = f"\n🛡 **Роли:** {names}\n"
            allow = (await db.get_access_matrix()).get(uuid, {}).get("allow", [])
            if allow:
                seen = set()
                for g in allow[:6]:
                    line = grant_text(g)
                    if line in seen:
                        continue
                    seen.add(line)
                    roles_text += f"  • `{line}` — из «{escape_md(g['role'])}»\n"
                if len(allow) > 6:
                    roles_text += "  • …\n"
            else:
                roles_text += "  ⚠️ роли ничего не открывают — туннель закрыт целиком\n"
    except Exception:
        pass

    # Подключения: человек один, протоколов у него может быть два. Блок
    # собирается там же, где экран подключений, чтобы они не разошлись.
    conn_text, conn_state = "", None
    try:
        import xray
        from handlers_xray import connections_block
        conn_state = await xray.person_state(uuid)
        conn_text = "\n" + connections_block(conn_state) + "\n"
    except Exception:
        pass

    # Доставка: Telegram не говорит, прочитано ли сообщение, поэтому показываем
    # цепочку действий — она точнее отвечает на вопрос «ключ дошёл», чем галочка.
    try:
        delivery_line = "\n" + delivery_text(await db.get_delivery(uuid)) + "\n"
    except Exception:
        delivery_line = ""

    text = (
        f"👤 **{safe_name}**\n"
        f"🆔 `{user['uuid']}`\n"
        f"📊 Статус: {status_str}\n"
        f"🌐 Адрес в туннеле: `{peer_ip or 'не выдан'}`\n"
        f"🤝 Последнее соединение: {_ago(hs_ago)}\n"
        f"🚦 Лимит: {limit_line}"
        + (f" · за сутки на пределе: {exceeded}\n"
           f"{'⚠️' if last_worrying else '💬'} {last_verdict}\n"
           if exceeded else "\n")
        + f"⏳ Годен до: {exp_str} (МСК)\n"
        f"📱 TG ID: {tg_status}\n"
        f"📅 Создан: {created_str}\n"
        f"{conn_text}"
        f"{delivery_line}"
        f"{roles_text}"
        f"{ips_text}"
    )

    keyboard =[]
    if user.get('is_active', True):
        keyboard.append([InlineKeyboardButton("⏸ Заморозить ключ", callback_data=f"act_pause_{uuid}")])
    else:
        keyboard.append([InlineKeyboardButton("▶️ Разморозить ключ", callback_data=f"act_resume_{uuid}")])

    # Правило нагрузки прямо из карточки: чаще всего оно и нужно именно здесь,
    # когда смотришь на конкретного человека.
    # Раньше тут стояли «Общий / Свой / Без лимита» — по подписям невозможно
    # понять ни что они делают, ни что стоит сейчас. Теперь одна строка с
    # текущим состоянием, а выбор — на отдельном экране с объяснениями.
    keyboard.append([
        InlineKeyboardButton(f"🚦 Ограничение: {limit_line.split(',')[0]}",
                             callback_data=f"svc_lim_{uuid}"),
    ])
    keyboard.append([
        InlineKeyboardButton("📉 История нагрузки", callback_data=f"svc_pchart_{uuid}"),
    ])
    if conn_state is not None:
        label = ("🔌 Подключения" if conn_state["has_xray"]
                 else "🔌 Подключения · выдать Xray")
        keyboard.append([InlineKeyboardButton(label, callback_data=f"xr_conn_{uuid}")])
    keyboard.append([InlineKeyboardButton("🛡 Доступы · роли", callback_data=f"role_u_{uuid}"),
                     InlineKeyboardButton("🧹 Фильтры", callback_data=f"flt_user_{uuid}")])
    # Свои исключения — про это устройство, а не про всех. Число на кнопке,
    # чтобы не заходить внутрь ради проверки, есть ли там что-нибудь.
    try:
        own_routes = await db.count_peer_routes(uuid)
    except Exception:
        own_routes = 0
    keyboard.append([InlineKeyboardButton(
        "🌐 Свои исключения" + (f" · {own_routes}" if own_routes else ""),
        callback_data=f"rt_menu_{uuid}")])
    keyboard.append([InlineKeyboardButton("✏️ Переименовать ключ", callback_data=f"rename_user_{uuid}")])
    keyboard.append([InlineKeyboardButton("🔗 Привязать TG ID", callback_data=f"link_tg_{uuid}")])
    if tg_ids:
        keyboard.append([InlineKeyboardButton("✂️ Отвязать TG ID", callback_data=f"unlink_tg_{uuid}")])
    
    if user_ips:
        keyboard.append([InlineKeyboardButton("🧹 Сбросить историю сетей", callback_data=f"clear_ips_{uuid}")])
    
    keyboard.extend([[InlineKeyboardButton("📨 Отправить конфиг", callback_data=f"act_resend_{uuid}")],[InlineKeyboardButton("❌ Удалить пользователя", callback_data=f"confirm_delete_{uuid}")],[InlineKeyboardButton("🔙 Назад к списку", callback_data="users_page_0")]
    ])
    
    if message_id:
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        except Exception: pass

async def user_detail_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid):
    await stop_bg_tasks()
    chat_id = update.effective_chat.id
    deregister_menu(chat_id)
    await render_user_detail(context, chat_id, update.callback_query.message.message_id, uuid)

async def clear_user_ips(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid):
    await db.execute("DELETE FROM user_ips WHERE uuid=$1", uuid)
    await update.callback_query.answer("История IP-адресов очищена!")
    await user_detail_menu(update, context, uuid)

async def confirm_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid):
    deregister_menu(update.effective_chat.id)
    user = await db.get_user_by_uuid(uuid)
    if not user: return
    text = f"⚠️ **Вы уверены, что хотите удалить {escape_md(user['name'])}?**\n\nКлюч перестанет работать, файлы будут удалены навсегда."
    keyboard = [[InlineKeyboardButton("✅ ДА, Удалить", callback_data=f"do_delete_{uuid}")],[InlineKeyboardButton("🔙 Нет, отмена", callback_data=f"user_detail_{uuid}")]]
    await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def action_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid):
    user = await db.get_user_by_uuid(uuid)
    if not user: 
        await update.callback_query.answer("Пользователь уже удален")
        await users_list_menu(update, context, 0)
        return

    await update.callback_query.answer("Удаление...")
    try:
        await delete_peer(uuid, user['name'])
        await db.execute("DELETE FROM users WHERE uuid=$1", uuid)
        # Вместе с человеком с узла уходит и его адрес-двойник: иначе он
        # остался бы принимать ответы и считаться неизвестно за кого.
        try:
            from xray import sync_person
            await sync_person("человек удалён")
        except Exception as e:
            print(f"Xray: конфиг не пересобран после удаления: {e}")
        await db.log_event("Delete", f"Deleted key {user['name']}")
        await update.callback_query.answer("Успешно удален!", show_alert=True)
        await users_list_menu(update, context, 0)
    except Exception as e:
        await update.callback_query.message.reply_text(f"❌ Ошибка удаления: {e}")

async def action_resend_config(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid):
    user = await db.get_user_by_uuid(uuid)
    if not user: return
    
    await update.callback_query.answer("Поиск файлов...")
    name = user['name']
    chat_id = update.effective_chat.id
    
    cf = CONFIGS_DIR / f"{name}.conf"
    qf = CONFIGS_DIR / f"{name}.png"
    cf_old = CONFIGS_DIR / f"{name}_Full.conf"
    qf_old = CONFIGS_DIR / f"{name}_Full.png"

    try:
        if cf.exists():
            await context.bot.send_document(chat_id=chat_id, document=open(cf, "rb"), caption=f"📄 Ваш конфиг: {name}")
            if qf.exists(): await context.bot.send_photo(chat_id=chat_id, photo=open(qf, "rb"))
        elif cf_old.exists():
            await context.bot.send_document(chat_id=chat_id, document=open(cf_old, "rb"), caption=f"📄 Ваш конфиг: {name} (старый формат)")
            if qf_old.exists(): await context.bot.send_photo(chat_id=chat_id, photo=open(qf_old, "rb"))
        else:
            await update.callback_query.answer("❌ Файлы конфигурации не найдены на диске!", show_alert=True)
    except Exception as e:
        await update.callback_query.answer(f"Ошибка отправки: {e}", show_alert=True)

async def default_proto():
    """Какой протокол предлагать при создании ключа.

    Xray — только если он включён на узле. Иначе человек получил бы ссылку на
    протокол, которого там нет: она выглядит рабочей и молча не работает.
    Узел молчит — тоже AmneziaWG: он работал всегда и точно поднят."""
    try:
        import xray
        state = await xray.status()
        return "xray" if state.get("xray", {}).get("enabled") else "awg"
    except Exception:
        return "awg"


async def key_role_name(context):
    """Какой доступ достанется этому ключу и как это назвать словами."""
    rid = context.user_data.get("new_key_role_id")
    if rid is None:
        stored = await db.get_setting("default_role_id") or ""
        rid = int(stored) if str(stored).isdigit() else 0
        context.user_data["new_key_role_id"] = rid
    if not rid:
        return 0, None
    role = await db.get_role(int(rid))
    if not role:                      # роль удалили, пока заводили ключ
        context.user_data["new_key_role_id"] = 0
        return 0, None
    return int(rid), role["name"]


async def new_key_screen(context, name):
    """Экран срока. Протокол здесь же строкой: по умолчанию Xray, AmneziaWG —
    для тех, кому нужен туннель на уровне IP (роутеры, шлюзы, домашний сервер).

    И доступ. Роли только сужают: у кого ролей нет — тот ходит по туннелю куда
    угодно. Значит, спрашивать надо здесь, когда человека заводят, а не
    надеяться, что владелец вспомнит потом."""
    proto = context.user_data.get("proto", "xray")
    if proto == "xray":
        note = ("🔶 Будет выдан **Xray** — ссылкой. Профиль обновляется сам, "
                "перевыпускать при изменениях не придётся.")
        switch = "🔧 Нужен AmneziaWG (для опытных)"
    else:
        note = ("🔷 Будет выдан **AmneziaWG** — файлом конфига. Нужен, если "
                "подключается роутер, шлюз или домашний сервер.")
        switch = "🔶 Вернуть Xray (обычный случай)"

    _rid, role_name = await key_role_name(context)
    access = (f"🛡 Доступ: **{escape_md(role_name)}**" if role_name
              else "🛡 Доступ: **без роли** — будет видеть всех в туннеле")

    text = (f"Имя: **{escape_md(name)}**" + '\\n\\n' + note + '\\n\\n' + access + '\\n\\n'
            + "Выберите срок действия ключа:")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 День", callback_data="set_exp_1"),
         InlineKeyboardButton("1 Неделя", callback_data="set_exp_7")],
        [InlineKeyboardButton("1 Месяц", callback_data="set_exp_30"),
         InlineKeyboardButton("Навсегда", callback_data="set_exp_0")],
        [InlineKeyboardButton(switch, callback_data="new_proto")],
        [InlineKeyboardButton("🛡 Сменить доступ", callback_data="new_key_role")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")],
    ])
    return text, keyboard


async def new_key_role_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор доступа для этого ключа. Общую настройку не трогает."""
    query = update.callback_query
    roles = await db.list_roles()
    cur, _name = await key_role_name(context)

    lines = ["🛡 **Доступ для нового ключа**", "",
             "Роль сужает доступ внутри туннеля. Без роли человек видит всех "
             "остальных — поэтому «без роли» здесь не то же самое, что «я "
             "ничего не выбрал».", "",
             "_Интернет, выход через Германию и страница блокировки работают "
             "при любом выборе._", ""]

    kb = []
    for r in roles:
        mark = "✅ " if r["id"] == cur else ""
        hint = "" if r["grants"] else " · ничего не открывает"
        kb.append([InlineKeyboardButton(f"{mark}{r['name']}{hint}",
                                        callback_data=f"nkrole_{r['id']}")])
    kb.append([InlineKeyboardButton(("✅ " if not cur else "") + "Без роли · видит всех",
                                    callback_data="nkrole_0")])
    kb.append([InlineKeyboardButton("🔙 Назад", callback_data="new_key_back")])

    await query.edit_message_text(chr(10).join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def new_key_role_set(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           role_id: int):
    context.user_data["new_key_role_id"] = int(role_id)
    await update.callback_query.answer()
    text, kb = await new_key_screen(context, context.user_data.get("name", ""))
    await update.callback_query.edit_message_text(text, reply_markup=kb,
                                                  parse_mode=ParseMode.MARKDOWN)



async def generate_key_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_bg_tasks()
    deregister_menu(update.effective_chat.id)
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
    await update.callback_query.edit_message_text("✏️ Введите имя пользователя:", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["state"] = "awaiting_name"
    context.user_data["menu_msg_id"] = update.callback_query.message.message_id

async def finish_key_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_id=None):
    name = context.user_data.get("name")
    exp_days = context.user_data.get("expiry_days", 0)
    dns_type = context.user_data.get("dns_type", "classic")
    chat_id = update.effective_chat.id
    menu_id = context.user_data.get("menu_msg_id")

    if menu_id:
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text="⏳ Генерирую конфигурацию...")
        except: pass

    try:
        # Новый ключ получает актуальный набор split-tunnel исключений и текущую
        # (динамическую) версию маршрутизации — чтобы он сразу считался «свежим».
        bypass_cidrs = await db.get_all_bypass_cidrs()
        rv = await db.get_routing_version()
        new_uid, c_path, q_path = await create_peer(name, dns_type=dns_type, bypass_cidrs=bypass_cidrs)
        expires_at = datetime.utcnow() + timedelta(days=exp_days) if exp_days > 0 else None

        await db.execute("INSERT INTO users (name, uuid, created_at, expires_at, routing_version) VALUES ($1, $2, NOW(), $3, $4) ON CONFLICT (uuid) DO NOTHING", name, new_uid, expires_at, rv)
        await db.log_event("Create Key", f"Created key {name}. Expiry: {exp_days} days. DNS: {dns_type}")

        # Новый адрес в туннеле — новая строка в раскладке на узле. Без этого
        # общие правила и роли начинали действовать на него не сразу, а со
        # следующего изменения настроек.
        from restrictions import reapply
        await reapply("выдан ключ")
        
        if tg_id: await db.link_user_telegram(new_uid, tg_id)

        # Роль по умолчанию. Без неё новый человек оказался бы вообще без
        # ролей, а это в нашей схеме значит «ходит куда угодно» — то есть
        # полный доступ, молча и мимо замысла.
        try:
            role_id, _ = await key_role_name(context)
            if role_id:
                await db.add_user_role(new_uid, role_id)
                from acl import apply_access_rules
                await apply_access_rules("новый ключ: выданный доступ")
        except Exception as e:
            # Ключ важнее роли: человек должен получить связь даже если с
            # ролями что-то не так. Роль довыдадут руками.
            print(f"Роль новому ключу не выдалась: {e}")

        # Xray по умолчанию. Пир при этом создаётся всегда — он держит за
        # человеком адрес в туннеле, на котором стоит весь учёт, — но конфиг
        # AmneziaWG человеку не отдаётся, чтобы не путать его двумя способами.
        if context.user_data.get("proto", "xray") == "xray":
            from handlers_xray import handout as xray_handout
            await xray_handout(update, context, new_uid, name, tg_id)
            context.user_data["state"] = None
            context.user_data["proto"] = "xray"
            return
        
        await context.bot.send_message(chat_id=chat_id, text=f"✅ **Ключ сгенерирован!**\n\nВы можете добавить его в приложение AmneziaWG.", parse_mode=ParseMode.MARKDOWN,
        reply_markup=exit_kb(("👥 Люди", "list_users")))
        await context.bot.send_document(chat_id=chat_id, document=open(c_path, "rb"), caption=f"📄 {name}")
        await context.bot.send_photo(chat_id=chat_id, photo=open(q_path, "rb"))
        
        if tg_id:
            # Исход отправки записываем: «не дошло» — это не строчка в логе,
            # а состояние ключа, которое админ должен видеть в карточке.
            async def _send_to_client():
                await context.bot.send_message(chat_id=tg_id, text="🎉 **Привет!** Администратор создал для вас VPN-ключ и привязал его к этому Telegram-аккаунту.\n\nВот ваш файл конфигурации:", parse_mode=ParseMode.MARKDOWN)
                await context.bot.send_document(chat_id=tg_id, document=open(c_path, "rb"), caption=f"📄 Ваш VPN конфиг: {name}")
                await context.bot.send_photo(chat_id=tg_id, photo=open(q_path, "rb"))
                await send_client_menu(context, tg_id)

            ok, err = await track_send(new_uid, tg_id, _send_to_client)
            if ok:
                await context.bot.send_message(chat_id=chat_id, text=f"✅ Конфиг и меню успешно отправлены клиенту `{tg_id}`.",
        reply_markup=exit_kb(("👥 Люди", "list_users")))
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Клиент `{tg_id}` не получил конфиг (возможно, он не запустил бота командой /start):\n`{err}`", parse_mode=ParseMode.MARKDOWN,
        reply_markup=exit_kb(("👥 Люди", "list_users")))
        
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")]]
        await context.bot.send_message(chat_id=chat_id, text="Готово! Что делаем дальше?", reply_markup=InlineKeyboardMarkup(keyboard))
        
        context.user_data["state"] = None
    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_main")]]
        if menu_id: await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text=f"❌ Ошибка: {e}", reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data["state"] = None
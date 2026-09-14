# -*- coding: utf-8 -*-
"""Экраны ролей: кто к каким домашним сервисам ходит внутри туннеля.

Роль описывается двумя списками, и на экране они так и разведены:
  • «Что входит» — адреса, которые роль открывает;
  • «Кто входит» — люди, которым она выдана.

Два места, где легко запутаться, и поэтому они проговариваются прямо в интерфейсе:
  1. Человек без ролей ходит куда угодно. Роль не добавляет прав, а сужает —
     как только выдана первая, всё неперечисленное закрывается.
  2. Ролей может быть несколько, и права складываются. Поэтому удаление из одной
     роли не обязательно закрывает доступ: его могут давать остальные.

Самому пользователю роли не показываются — ему это знать незачем.
"""
import ipaddress

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from acl import apply_access_rules, peer_ip_map, grant_text
from database import db
from utils import exit_kb, escape_md, show_screen

TUNNEL_NET = ipaddress.ip_network("10.13.13.0/24")
MASTER_IP = ipaddress.ip_address("10.13.13.1")
AGENT_IP = ipaddress.ip_address("10.13.13.254")
PAGE_SIZE = 8


def _back(role_id=None):
    if role_id:
        return [InlineKeyboardButton("🔙 К роли", callback_data=f"role_open_{role_id}")]
    return [InlineKeyboardButton("🔙 Роли", callback_data="roles_menu")]


async def roles_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    roles = await db.list_roles()

    lines = ["🛡 **Доступы внутри туннеля**", ""]
    if not roles:
        lines += [
            "Ролей пока нет — значит все ходят друг к другу без ограничений.",
            "",
            "Роль нужна, чтобы закрыть домашние сервисы от тех, кому они ни к чему.",
            "Как только человеку выдана первая роль, всё неперечисленное в ней "
            "для него закрывается.",
        ]
    else:
        lines.append("Роль открывает адреса внутри туннеля. У кого ролей нет — "
                     "тот ходит куда угодно.")
        lines.append("")
        for r in roles:
            warn = "  ⚠️ ничего не открывает" if not r["grants"] else ""
            lines.append(f"• **{escape_md(r['name'])}** — правил {r['grants']}, "
                         f"людей {r['members']}{warn}")

    lines += ["", "_Интернет и скорость роли не трогают — только доступ к своим._"]

    kb = [[InlineKeyboardButton(f"{r['name']} · {r['members']} чел.",
                                callback_data=f"role_open_{r['id']}")]
          for r in roles]
    kb.append([InlineKeyboardButton("➕ Создать роль", callback_data="role_new")])
    if roles:
        kb.append([InlineKeyboardButton("🔄 Применить на узле", callback_data="role_apply")])
    kb.append([InlineKeyboardButton("🔙 Администрирование", callback_data="svc_menu")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def role_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, role_id: int):
    query = update.callback_query
    role = await db.get_role(role_id)
    if not role:
        await query.answer("Роль удалена")
        return await roles_menu(update, context)

    grants = await db.get_role_grants(role_id)
    members = await db.get_role_members(role_id)

    lines = [f"🛡 **Роль: {escape_md(role['name'])}**", "", "*Что входит*"]
    if grants:
        for g in grants:
            note = f" — {escape_md(g['note'])}" if g.get("note") else ""
            lines.append(f"• `{grant_text(g)}`{note}")
    else:
        lines.append("_пусто — роль не открывает ничего_")
        # «Закрыт весь туннель» звучало страшнее, чем есть: интернет, выход
        # через Германию и имена продолжают работать — закрыт только путь к
        # другим людям внутри сети. Владелец завёл такую роль на 24 человека и
        # имел право понять это без чтения правил файрвола.
        lines.append("Её обладателям закрыт доступ **к другим людям** в сети. "
                     "Интернет, выход через Германию и имена работают как "
                     "обычно — роли их не трогают.")

    lines += ["", "*Кто входит*"]
    if members:
        for m in members:
            lines.append(f"• {escape_md(m['name'])}")
    else:
        lines.append("_никого_")

    if members and grants:
        lines += ["", "_У человека может быть несколько ролей: права складываются. "
                      "Убрать его отсюда — не значит закрыть доступ, если его даёт "
                      "другая роль._"]

    kb = []
    for g in grants:
        kb.append([InlineKeyboardButton(f"➖ {grant_text(g)}",
                                        callback_data=f"role_gdel_{role_id}_{g['id']}")])
    kb.append([InlineKeyboardButton("➕ Открыть доступ", callback_data=f"role_gadd_{role_id}")])
    for m in members:
        kb.append([InlineKeyboardButton(f"➖ {m['name']}",
                                        callback_data=f"role_mdel_{role_id}_{m['uuid']}")])
    kb.append([InlineKeyboardButton("➕ Добавить человека",
                                    callback_data=f"role_madd_{role_id}_0")])
    kb.append([InlineKeyboardButton("🗑 Удалить роль", callback_data=f"role_del_{role_id}")])
    kb.append(_back())

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def role_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "awaiting_role_name"
    await show_screen(update.callback_query, context, 
        "➕ **Новая роль**\n\nПришли название — например «Домашние сервисы» "
        "или «Только интернет».\n\nДля отмены нажми «Отмена».",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "✖️ Отмена", callback_data="roles_menu")]]),
        parse_mode=ParseMode.MARKDOWN)


async def grant_add_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, role_id: int):
    """Обычный случай — открыть доступ к конкретному пиру, поэтому он кнопками.
    Подсеть или отдельный порт набираются руками: это редкий случай."""
    query = update.callback_query
    ips = await peer_ip_map()
    users = await db.get_all_users()

    try:
        names = await db.list_dns_names()
    except Exception:
        names = []

    kb = []
    # Имена первыми: правило по имени читается и через полгода, а «10.13.13.5»
    # требует помнить, что такое .5.
    for row in names[:8]:
        kb.append([InlineKeyboardButton(
            f"🏷 {row['name']}",
            callback_data=f"role_gname_{role_id}_{row['name']}")])
    for u in users:
        ip = ips.get(u["uuid"])
        if not ip:
            continue
        kb.append([InlineKeyboardButton(f"{u['name']} · {ip}",
                                        callback_data=f"role_gpeer_{role_id}_{u['uuid']}")])
    # Самый частый случай для роли администратора — открыть всё внутри
    # туннеля. Раньше это набиралось руками.
    kb.append([InlineKeyboardButton("🌐 Весь туннель",
                                    callback_data=f"role_gall_{role_id}")])
    kb.append([InlineKeyboardButton("✍️ Ввести имя или адрес",
                                    callback_data=f"role_gman_{role_id}")])
    kb.append(_back(role_id))

    head = "🛡 **Доступы роли**\n\nВыберите, к чему роль даёт доступ."
    if names:
        head += ("\n\n🏷 Имена сверху — их лучше и выбирать: имя разрешается "
                 "в адрес каждый раз заново и переживает перевыпуск ключа.")
    head += "\n\nНужен только один порт или целая подсеть — введите вручную."

    await show_screen(query, context, head,
                      reply_markup=InlineKeyboardMarkup(kb),
                      parse_mode=ParseMode.MARKDOWN)


async def grant_whole_tunnel(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             role_id: int):
    """Открывает всю туннельную сеть разом.

    Интернета это не касается: роли ограничивают только обмен внутри туннеля,
    а мировой трафик уходит на клиент-сервер, разрешённый до всех запретов."""
    query = update.callback_query
    await db.add_role_grant(role_id, cidr=str(TUNNEL_NET))
    ok, msg = await apply_access_rules("открыт весь туннель")
    await query.answer(msg if ok else f"Не вышло: {msg}", show_alert=not ok)
    await role_screen(update, context, role_id)


async def grant_name(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     role_id: int, name: str):
    """Открыть доступ к имени целиком, без указания порта."""
    query = update.callback_query
    if not await db.get_dns_name(name):
        await query.answer("Такого имени уже нет", show_alert=True)
        return await grant_add_screen(update, context, role_id)
    await db.add_role_grant(role_id, name=name)
    ok, msg = await apply_access_rules("добавлено правило по имени")
    await query.answer(msg if ok else f"Не вышло: {msg}", show_alert=not ok)
    await role_screen(update, context, role_id)


async def grant_manual(update: Update, context: ContextTypes.DEFAULT_TYPE, role_id: int):
    context.user_data["state"] = "awaiting_role_grant"
    context.user_data["role_id"] = role_id
    await show_screen(update.callback_query, context, 
        "🛡 **Новый доступ**\n\nПришли имя или адрес внутри туннеля. Примеры:\n"
        "`дом.vpn` — всё, что на этой машине\n"
        "`дом.vpn tcp 8096` — только один порт\n"
        "`10.13.13.7` — то же самое, но адресом\n"
        "`10.13.13.0/28` — диапазон адресов\n\n"
        "Имя лучше адреса: оно разрешается в адрес каждый раз заново и "
        "переживает перевыпуск ключа. Адрес должен быть внутри "
        "`10.13.13.0/24`: роли управляют доступом внутри туннеля, а не "
        "выходом в интернет.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "✖️ Отмена", callback_data=f"role_open_{role_id}")]]),
        parse_mode=ParseMode.MARKDOWN)


def _looks_like_address(token: str) -> bool:
    """Адрес это или имя. Достаточно первого знака: имя начинается с буквы."""
    head = token.split("/")[0]
    return bool(head) and head[0].isdigit()


def parse_grant(text: str):
    """Разбирает «10.13.13.7 tcp 8096» в любом порядке. Возвращает (grant, ошибка).

    Проверка адреса здесь не формальность: цепочка на узле висит только на адресах
    туннеля, и правило для 192.168.x просто никогда бы не сработало — админ бы
    считал доступ настроенным, а он бы не работал."""
    tokens = [t for t in text.replace(",", " ").replace(":", " ").split() if t]
    if not tokens:
        return None, "пустая строка"

    cidr, proto, port = None, "any", None
    for t in tokens:
        low = t.lower()
        if low in ("tcp", "udp"):
            proto = low
        elif t.isdigit():
            port = int(t)
        elif cidr is None:
            cidr = t
        else:
            return None, f"не понял часть «{t}»"

    if not cidr:
        return None, "не вижу адреса"

    # Не похоже на адрес — считаем именем. Проверять его существование здесь
    # нельзя (это синхронный разбор), поэтому проверка живёт выше, там же, где
    # видно базу: имя, которого нет, до правил не доедет.
    if not _looks_like_address(cidr):
        return {"name": cidr.lower().rstrip("."), "cidr": None,
                "proto": proto, "port": port}, None

    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return None, f"«{cidr}» — не адрес и не подсеть"
    if net.version != 4:
        return None, "нужен адрес IPv4"
    if not net.subnet_of(TUNNEL_NET):
        return None, (f"адрес вне туннеля. Роли открывают доступ внутри "
                      f"`{TUNNEL_NET}`, интернет они не ограничивают")
    if port is not None and not (1 <= port <= 65535):
        return None, "порт вне диапазона"
    if port is not None and proto == "any":
        proto = "tcp"           # порт без протокола не имеет смысла
    if net.num_addresses == 1:
        addr = net.network_address
        if addr == AGENT_IP:
            return None, "это адрес клиент-сервера — через него идёт интернет, "\
                         "он и так открыт всем"
        if addr == MASTER_IP:
            return None, "это адрес самого мастера, он правилами не управляется"

    return {"cidr": str(net), "proto": proto, "port": port}, None


async def members_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         role_id: int, page: int = 0):
    query = update.callback_query
    role = await db.get_role(role_id)
    members = {m["uuid"] for m in await db.get_role_members(role_id)}
    users = [u for u in await db.get_all_users() if u["uuid"] not in members]

    total = max(1, (len(users) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total - 1))
    chunk = users[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    kb = [[InlineKeyboardButton(u["name"],
                                callback_data=f"role_mset_{role_id}_{u['uuid']}")]
          for u in chunk]
    if total > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"role_madd_{role_id}_{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="svc_noop"))
        if page < total - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"role_madd_{role_id}_{page+1}"))
        kb.append(nav)
    kb.append(_back(role_id))

    text = (f"➕ **Кого добавить в «{escape_md(role['name'])}»**\n\n"
            "Как только человек попадает в первую свою роль, всё, что ролями "
            "не открыто, для него закрывается.")
    if not chunk:
        text = "Все уже в этой роли."
    await show_screen(query, context, text, reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def _apply_and_answer(update, context, role_id, note):
    ok, msg = await apply_access_rules(note)
    await update.callback_query.answer(msg if ok else f"Правила не применены: {msg}",
                                       show_alert=not ok)
    if role_id:
        await role_screen(update, context, role_id)
    else:
        await roles_menu(update, context)


async def grant_peer(update, context, role_id: int, uuid_val: str):
    ips = await peer_ip_map()
    ip = ips.get(uuid_val)
    if not ip:
        await update.callback_query.answer("У этого пира нет адреса", show_alert=True)
        return
    user = await db.get_user_by_uuid(uuid_val)
    await db.add_role_grant(role_id, f"{ip}/32", "any", None,
                            user["name"] if user else None)
    await _apply_and_answer(update, context, role_id, "открыт доступ к пиру")


async def grant_del(update, context, role_id: int, grant_id: int):
    await db.delete_role_grant(grant_id)
    await _apply_and_answer(update, context, role_id, "правило удалено")


async def member_add(update, context, role_id: int, uuid_val: str):
    await db.add_user_role(uuid_val, role_id)
    await _apply_and_answer(update, context, role_id, "человек добавлен в роль")


async def member_del(update, context, role_id: int, uuid_val: str):
    await db.remove_user_role(uuid_val, role_id)
    other = await db.get_user_roles(uuid_val)
    await db.log_event("Roles", f"Из роли {role_id} убран {uuid_val}")
    if other:
        names = ", ".join(r["name"] for r in other)
        await update.callback_query.answer(
            f"Убран. Доступ остаётся: {names}", show_alert=True)
        await apply_access_rules("человек убран из роли")
        return await role_screen(update, context, role_id)
    await _apply_and_answer(update, context, role_id,
                            "человек убран из роли, ограничений на нём больше нет")


async def role_delete_confirm(update, context, role_id: int):
    role = await db.get_role(role_id)
    members = await db.get_role_members(role_id)
    orphan = []
    for m in members:
        if len(await db.get_user_roles(m["uuid"])) == 1:
            orphan.append(m["name"])

    lines = [f"🗑 **Удалить роль «{escape_md(role['name'])}»?**", ""]
    if orphan:
        lines.append("После удаления снова без ограничений станут: "
                     + escape_md(", ".join(orphan)) + ".")
    elif members:
        lines.append("Люди из неё останутся с правами от других своих ролей.")
    else:
        lines.append("В роли никого нет.")

    kb = [[InlineKeyboardButton("🗑 Удалить", callback_data=f"role_delok_{role_id}"),
           InlineKeyboardButton("✖️ Отмена", callback_data=f"role_open_{role_id}")]]
    await show_screen(update.callback_query, context, 
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN)


async def role_delete(update, context, role_id: int):
    role = await db.get_role(role_id)
    await db.delete_role(role_id)
    await db.log_event("Roles", f"Удалена роль {role['name'] if role else role_id}")
    await _apply_and_answer(update, context, None, "роль удалена")


async def user_roles_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            uuid_val: str):
    """Роли конкретного человека — из его карточки. Тумблером, потому что здесь
    вопрос стоит как «выдать или снять», а не «кого набрать в роль»."""
    query = update.callback_query
    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        return await query.answer("Пользователь не найден")

    roles = await db.list_roles()
    mine = {r["id"] for r in await db.get_user_roles(uuid_val)}

    lines = [f"🛡 **Доступы: {escape_md(user['name'])}**", ""]
    if not roles:
        lines.append("Ролей пока нет. Пока их нет, все ходят по туннелю свободно.")
    elif not mine:
        lines.append("Ролей не выдано — человек ходит по туннелю без ограничений.")
        lines.append("Первая же выданная роль закроет всё, что в ней не перечислено.")
    else:
        lines.append("Права складываются из всех отмеченных ролей.")

    kb = [[InlineKeyboardButton(("✅ " if r["id"] in mine else "➖ ") + r["name"],
                                callback_data=f"role_ut_{r['id']}_{uuid_val}")]
          for r in roles]
    kb.append([InlineKeyboardButton("🛡 Все роли", callback_data="roles_menu")])
    kb.append([InlineKeyboardButton("🔙 К пользователю",
                                    callback_data=f"user_detail_{uuid_val}")])

    await show_screen(query, context, "\n".join(lines),
                                  reply_markup=InlineKeyboardMarkup(kb),
                                  parse_mode=ParseMode.MARKDOWN)


async def user_role_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           role_id: int, uuid_val: str):
    mine = {r["id"] for r in await db.get_user_roles(uuid_val)}
    if role_id in mine:
        await db.remove_user_role(uuid_val, role_id)
    else:
        await db.add_user_role(uuid_val, role_id)
    ok, msg = await apply_access_rules("роль переключена из карточки")
    await update.callback_query.answer(msg if ok else msg, show_alert=not ok)
    await user_roles_screen(update, context, uuid_val)


async def role_apply(update, context):
    ok, msg = await apply_access_rules("применение вручную")
    await update.callback_query.answer(msg, show_alert=True)
    await roles_menu(update, context)


# --- ввод текстом ----------------------------------------------------------
async def handle_role_text(update, context, state: str) -> bool:
    """Возвращает True, если сообщение относилось к ролям и уже обработано."""
    text = (update.message.text or "").strip()
    chat_id = update.message.chat_id

    if state == "awaiting_role_name":
        context.user_data["state"] = None
        if not text:
            await context.bot.send_message(chat_id, "Пустое название — отменил.",
        reply_markup=exit_kb(("👥 Роли", "roles_menu")))
            return True
        role_id = await db.create_role(text[:40])
        if not role_id:
            await context.bot.send_message(chat_id, "Роль с таким названием уже есть.",
        reply_markup=exit_kb(("👥 Роли", "roles_menu")))
            return True
        await db.log_event("Roles", f"Создана роль {text[:40]}")
        kb = [[InlineKeyboardButton("➕ Открыть доступ",
                                    callback_data=f"role_gadd_{role_id}")],
              [InlineKeyboardButton("➕ Добавить человека",
                                    callback_data=f"role_madd_{role_id}_0")],
              [InlineKeyboardButton("🔙 Роли", callback_data="roles_menu")]]
        await context.bot.send_message(
            chat_id,
            f"✅ Роль «{escape_md(text[:40])}» создана.\n\n"
            "Пока в ней нет ни одного разрешения, и выдавать её людям рано: "
            "она закроет им весь туннель. Сначала добавь, что открывать.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return True

    if state == "awaiting_role_grant":
        context.user_data["state"] = None
        role_id = context.user_data.get("role_id")
        grant, err = parse_grant(text)
        kb = [[InlineKeyboardButton("🔙 К роли", callback_data=f"role_open_{role_id}")]]
        if err:
            await context.bot.send_message(
                chat_id, f"⚠️ Не добавил: {err}.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
            return True
        if grant.get("name"):
            # Имя должно существовать: правило на выдуманное имя выглядит
            # настроенным, а доступа не даёт.
            from dnsnames import normalize
            full, err_name = normalize(grant["name"])
            if err_name or not await db.get_dns_name(full):
                await context.bot.send_message(
                    chat_id,
                    f"⚠️ Имени `{escape_md(grant['name'])}` нет. Заведите его в "
                    f"разделе «Имена в туннеле» или укажите адрес.",
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode=ParseMode.MARKDOWN)
                return True
            grant["name"] = full
        await db.add_role_grant(role_id, cidr=grant["cidr"], proto=grant["proto"],
                                port=grant["port"], name=grant.get("name"))
        ok, msg = await apply_access_rules("добавлено правило")
        await context.bot.send_message(
            chat_id,
            f"✅ Добавлено: `{grant_text(grant)}`\n\n{msg if ok else '⚠️ ' + msg}",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return True

    return False

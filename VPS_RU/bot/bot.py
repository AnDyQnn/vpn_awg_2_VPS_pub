import logging
import asyncio
import aiohttp
import html
import os
import json
import time
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat, MenuButtonCommands
)
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from utils import (
    request_env_change,
    api_session,
    BOT_TOKEN, ADMIN_ID, WG_API_URL, DE_AGENT_URL, escape_md, state_data, stop_bg_tasks, deregister_menu,
    safe_delete, get_current_version, broadcast_message, extract_tg_id, check_admin, sanitize_name,
    env_change_applied,
    analyze_resource, CONFIGS_DIR
)
from database import db
from backup_manager import fetch_de_backup, test_restore
from ui import main_menu
from monitor import (
    alert_loop, cleanup_peers, stats_collector_loop, self_healing_loop,
    de_self_healing_loop, midnight_alert_cleanup_loop,
    expiration_loop, inactivity_loop, weekly_report_loop, log_cleanup_loop,
    auto_reboot_loop, scheduled_update_loop, auto_update_check_loop, resource_monitor_loop,
    routing_upgrade_loop, bypass_reresolve_loop, run_bypass_check_handler, bypass_notify_now_handler,
    load_collector_loop, retire_watch_loop, notify_admin, migration_watch_loop, weekly_health_loop,
    bypass_list_handler, bypass_happ_handler,
    bypass_del_handler, bypass_add_manual_handler, bypass_add_request_handler,
    reconcile_routing_versions
)
from wireguard_manager import pause_peer, resume_peer

from handlers_client import (
    client_menu, send_client_menu, check_connection_handler, client_stats_handler, 
    client_regen_confirm, client_regen_action, support_start_handler, support_run_audit_handler, 
    support_ask_msg_handler, client_download_handler, client_select_check_menu, client_check_all_handler,
    client_my_keys_handler, client_key_manage_handler, client_regen_all_confirm_handler, client_regen_all_action_handler,
    client_how_handler, client_platform_handler, client_apps_handler,
    client_bypass_info_handler, client_report_site_handler, client_notify_toggle_handler, client_notify_off_handler,
    cmd_keys, cmd_status, cmd_support, cmd_help, client_whats_new
)
from handlers_service import (
    service_menu, toggle_mode, set_mode, load_screen, limits_screen,
    change_limit, set_peer_rule, load_chart, whats_new,
    ensure_api_token, watch_api_token, rotate_loop, charts_screen,
    token_screen, token_toggle, token_now, token_rollback,
    traffic_fix_screen, traffic_fix_apply,
    pick_peer_screen, graphs_menu,
    event_delete,
    peer_limit_screen
)
from handlers_admin import (
    ask_backup_password,
    return_to_main_menu, update_persistent_backup, start_dashboard, confirm_reboot, do_reboot_server, 
    send_vpn_graph, online_users_menu, check_update, do_update, backup_now, download_logs, restore_cmd, 
    restore_file_handler, export_excel, run_audit_handler, schedule_update_menu, toggle_auto_update,
    support_admin_menu, support_user_tickets, support_ticket_detail, support_reply_start, support_close_ticket,
    de_confirm_reboot, do_de_reboot_server, de_read_logs,
    de_update, de_backup, de_run_audit, update_all
)
from handlers_users import (
    users_list_menu, user_detail_menu, confirm_delete_menu, action_delete_user, action_resend_config,
    new_key_screen, default_proto, new_key_role_screen, new_key_role_set,
    generate_key_request, finish_key_creation, render_user_detail, clear_user_ips
)
from handlers_roles import (
    default_role_screen, default_role_set,
    roles_menu, role_screen, role_new, grant_add_screen, grant_manual, grant_peer,
    grant_del, members_screen, member_add, member_del, role_delete_confirm,
    role_delete, role_apply, handle_role_text, user_roles_screen,
    user_role_toggle,
    grant_name, grant_whole_tunnel
)
from handlers_keylife import (
    pending_screen, decision_screen, extend_menu, do_extend, set_policy,
    delete_confirm, do_delete
)
from delivery import delivery_screen
from xray import sync_person as xray_sync
from handlers_xray import (
    protocols_menu, awg_screen, xray_screen, switch_confirm, switch_do,
    apply_now as xray_apply_now, apps_screen, move_screen,
    connections_screen, issue_xray, send_link, drop_awg, why_locked,
    mask_screen, mask_set,
)
from handlers_hits import (
    hits_screen, hit_open, hits_seen_all, hits_loop,
    hit_find_request, hit_find_entered,
)
from handlers_routes import (
    routes_menu, routes_ask, routes_delete, routes_show, handle_route_input,
)
from handlers_donate import (
    donate_menu, donate_toggle, donate_reminder_toggle, donate_preview,
    donate_ask, donate_open, donate_delete, handle_donate_input,
    donate_period, donate_period_set,
    client_donate, client_donate_qr,
)
from handlers_dnsnames import (
    names_menu, add_request as dnm_add, name_entered as dnm_name_entered,
    target_page as dnm_page, target_person as dnm_person,
    manual_request as dnm_manual, manual_entered as dnm_ip_entered,
    name_screen as dnm_open, rename_request as dnm_rename,
    rename_entered as dnm_rename_entered, retarget_request as dnm_retarget,
    delete_name as dnm_delete, apply_now as dnm_apply,
)
from handlers_migration import (
    migration_menu, migration_start, migration_issue, migration_send,
    migration_finish_confirm, migration_finish, migration_abort_confirm,
    migration_abort, migration_de
)
from filters import (
    common_screen as flt_common, common_toggle as flt_ctoggle,
    custom_add_request as flt_cadd, custom_add_entered as flt_centered,
    custom_list as flt_clist, custom_remove as flt_cremove,
    pool_list as flt_pools, pool_open as flt_pool_open,
    pool_name_request as flt_pool_new,
    pool_add_request as flt_pool_add, pool_domains_entered as flt_pool_doms,
    pool_title_entered as flt_pool_title, pool_delete as flt_pool_del,
    allow_screen as flt_allow, allow_add_request as flt_allow_add,
    allow_add_entered as flt_allow_entered, allow_remove as flt_allow_del,
    filters_menu, pick_user as filters_pick_user, user_filters_screen,
    toggle_filter, apply_now as filters_apply_now, apply_filters
)
from acl import apply_access_rules

# --- ЗАДАЧИ БОТА (СИНХРОНИЗАЦИЯ И МОНИТОРИНГ) ---
async def sync_wg_config():
    try:
        saved_json = await db.get_setting("wg_config_backup")
        if saved_json:
            saved_data = json.loads(saved_json)
            async with api_session() as session:
                async with session.get(f"{WG_API_URL}/backup_config", timeout=5) as resp:
                    if resp.status == 200:
                        current_data = await resp.json()
                        cur_conf = current_data.get("wg0.conf", "")
                        saved_conf = saved_data.get("wg0.conf", "")
                        
                        if len(cur_conf) < 50 or "[Peer]" not in cur_conf:
                            if "[Peer]" in saved_conf:
                                print("🔄 Restoring wg0.conf and keys from Database Backup...")
                                await session.post(f"{WG_API_URL}/restore_config", json=saved_data)

        print("🔍 Проведение аудита ключей (БД vs VPN)...")
        db_users = await db.get_all_users()
        db_uuids = [u['uuid'] for u in db_users]
        
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=5) as resp:
                if resp.status == 200:
                    wg_peers = await resp.json()
                    ghosts = 0
                    for p in wg_peers:
                        wg_uuid = p.get('uuid')
                        wg_pubkey = p.get('public_key')
                        
                        should_kill = False
                        if wg_uuid and wg_uuid not in db_uuids:
                            should_kill = True
                        
                        if should_kill and wg_pubkey:
                            print(f"👻 Удаление 'призрака' при запуске: {wg_pubkey}")
                            await session.post(f"{WG_API_URL}/kill_ghost", json={"public_key": wg_pubkey, "purge_config": True})
                            ghosts += 1
                    
                    if ghosts > 0:
                        print(f"✅ Аудит завершен. Уничтожено: {ghosts}")
                    else:
                        print("✅ Аудит завершен. База и VPN синхронизированы.")

    except Exception as e:
        print(f"Error syncing wg config: {e}")

async def watch_online_count(app):
    """Держит главное меню живым.

    Раньше обновлялась только клавиатура, и то по двум числам — онлайну и
    обращениям. Текст сводки застывал, счётчик на кнопке «Администрирование»
    терялся при первом же обновлении, а новые вопросы по ключам и застрявшая
    доставка экран вообще не трогали.

    Теперь сверяется всё, что на экране видно: пересобираем меню и сравниваем
    с тем, что показано. Изменилось — перерисовываем целиком, нет — молчим,
    чтобы не дёргать Telegram каждые пять секунд.
    """
    from handlers_admin import main_menu_view

    while True:
        try:
            if state_data["active_menus"]:
                text, markup, _ = await main_menu_view()
                if text != state_data.get("last_menu_text"):
                    state_data["last_menu_text"] = text
                    for chat_id in list(state_data["active_menus"].keys()):
                        if not check_admin(chat_id):
                            continue
                        message_id = state_data["active_menus"][chat_id]
                        try:
                            await app.bot.edit_message_text(
                                chat_id=chat_id, message_id=message_id,
                                text=text, reply_markup=markup,
                                parse_mode=ParseMode.MARKDOWN)
                        except Exception as e:
                            low = str(e).lower()
                            # «не изменилось» — нормально; «нет сообщения» или
                            # «нельзя редактировать» означают, что экран уехал.
                            if "not modified" in low:
                                continue
                            if "not found" in low or "no text" in low or "can't be edited" in low:
                                deregister_menu(chat_id)
        except Exception:
            pass
        await asyncio.sleep(5)


async def notify_users_whats_new(app):
    """Рассылает каждому только накопившееся лично для него.

    Текст у всех разный: кто-то видел прошлую версию, кто-то — нет. Поэтому не
    общая рассылка, а по человеку; отметка о просмотре ставится только тем, кому
    сообщение действительно ушло, иначе новость молча пропала бы."""
    try:
        from changelog import user_text, fit
        version = get_current_version()
        tg_ids = await db.get_all_tg_ids()
    except Exception as e:
        print(f"Что нового: не удалось подготовить рассылку: {e}")
        return

    sent = 0
    for tg_id in tg_ids or []:
        try:
            seen = await db.get_seen_version(tg_id)
            body = user_text(since_version=seen)
            if not body:
                continue
            await app.bot.send_message(chat_id=tg_id, text=fit(body, 3500),
                                       parse_mode=ParseMode.MARKDOWN)
            await db.set_seen_version(tg_id, version)
            sent += 1
            # Напоминание о поддержке — отдельным сообщением и не каждому:
            # внутри списка изменений просьба о деньгах читается как ещё один
            # пункт списка, а несколько раз за день — как попрошайничество.
            try:
                import donate
                if await donate.should_remind(tg_id):
                    await app.bot.send_message(
                        chat_id=tg_id, text=donate.REMINDER_TEXT,
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton("❤️ Поддержать проект",
                                                   callback_data="client_donate")]]))
                    await db.set_donate_reminded_at(tg_id)
            except Exception as e:
                print(f"Напоминание о поддержке: {tg_id} не получил: {e}")
        except Exception as e:
            # Заблокировал бота или закрыл личку — не повод останавливать рассылку
            # и не повод считать, что он прочитал.
            print(f"Что нового: {tg_id} не получил: {e}")
    if sent:
        await db.log_event("System", f"«Что нового» отправлено: {sent} чел.")


async def check_update_completion(app):
    flag_update = "/volumes/flags/was_updating"
    flag_reboot = "/volumes/flags/was_rebooting"

    # Деплой/ребут ПЕРЕСОЗДают этот контейнер, поэтому после старта в течение ~3 минут
    # ждём метку: deploy.sh ставит was_updating ПОСЛЕ успешного health-check, ребут —
    # was_rebooting до перезагрузки. Раньше была разовая проверка → метку, появившуюся
    # на пару секунд позже старта бота, не ловили, и уведомление не приходило.
    text = None
    for _ in range(36):  # 36 × 5с = 180с
        if os.path.exists(flag_update):
            os.remove(flag_update)
            # Список изменений админу сразу после обновления: он его и запускает,
            # и лезть за ним в отдельное меню не должен.
            try:
                from changelog import admin_text, repo_markdown
                note = admin_text(limit=1)
                link = repo_markdown()
                if link:
                    note += chr(10) + chr(10) + link
                if ADMIN_ID:
                    from changelog import fit
                    # Через notify_admin: иначе номер сообщения нигде не
                    # записан и полуночная уборка чата его не найдёт.
                    await notify_admin(app, text=fit(note),
                                       parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                print(f'Список изменений после обновления: {e}')
            text = f"✅ **Обновление завершено!**\n\nСервер снова онлайн.\nТекущая версия: `{get_current_version()}`\nВсе системы в норме."
            break
        if os.path.exists(flag_reboot):
            os.remove(flag_reboot)
            text = "✅ **Сервер перезагружен.**\n\nСервисы VPN восстановлены и готовы к работе."
            break
        await asyncio.sleep(5)

    if text:
        await asyncio.sleep(3)
        try:
            await broadcast_message(app, text, db)
            await db.log_event("System", "Server update/reboot sequence completed successfully.")
            await notify_users_whats_new(app)
            
            if ADMIN_ID:
                try:
                    active_count = 0
                    async with api_session() as session:
                        async with session.get(f"{WG_API_URL}/status", timeout=2) as resp:
                            if resp.status == 200: 
                                active_count = (await resp.json()).get("active_peers", 0)
                    
                    try:
                        supp_count = await db.fetch_val("SELECT COUNT(*) FROM support_tickets WHERE status='open'")
                        supp_count = supp_count or 0
                    except Exception:
                        supp_count = 0

                    # Пароль архива спрашиваем и здесь. Это отдельный путь отправки
                    # меню, и раньше он проверку обходил — как раз сразу после
                    # обновления, когда напомнить важнее всего.
                    from handlers_admin import backup_password_gate
                    
                    class _GateCtx:
                        bot = app.bot
                    
                    if await backup_password_gate(_GateCtx, ADMIN_ID):
                        return
                    
                    # Раньше здесь строилось своё короткое сообщение — из-за него
                    # меню после обновления приходило узким и без сводки. Одна
                    # отрисовка на оба пути: и по кнопке, и после деплоя.
                    from handlers_admin import return_to_main_menu
                    
                    class _MenuCtx:
                        bot = app.bot
                    
                    await return_to_main_menu(None, _MenuCtx, chat_id=ADMIN_ID)
                except Exception: pass
        except Exception as e:
            print(f"Check update completion error: {e}")

async def auto_backup_loop(app):
    """Раз в 12 часов: копия мастера, копия немецкой ноды и — раз в неделю — пробное
    восстановление дампа в отдельную базу.

    Раньше здесь была только копия мастера. Немецкая нода не бэкапилась вообще, хотя
    ручка у агента есть, а проверялось ли хоть что-то — не проверялось: архив мог
    неделями собираться битым, и узнали бы об этом в худший момент."""
    cycles = 0
    while True:
        await asyncio.sleep(43200)
        cycles += 1
        try:
            await update_persistent_backup(app)
        except Exception as e:
            print(f"Автобэкап мастера: {e}")

        try:
            path = await fetch_de_backup(DE_AGENT_URL)
            print(f"💾 Копия немецкой ноды сохранена: {path}")
        except Exception as e:
            print(f"Автобэкап агента: {e}")

        if cycles % 14 == 0:            # примерно раз в неделю
            try:
                ok, why = await test_restore()
                print(f"🧪 Пробное восстановление: {why}")
                if not ok and ADMIN_ID:
                    await notify_admin(
                        app,
                        text=("⚠️ **Резервная копия не восстанавливается**\n\n"
                              f"{why}\n\nАрхив собирается, но из него нельзя подняться — "
                              "разберитесь до того, как он понадобится."),
                        parse_mode="Markdown")
            except Exception as e:
                print(f"Проверка восстановления: {e}")

# --- ОСНОВНЫЕ РОУТЕРЫ СООБЩЕНИЙ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if check_admin(user_id):
        context.user_data["state"] = None
        await stop_bg_tasks()
        await safe_delete(context, update.effective_chat.id, update.message.message_id)
        await return_to_main_menu(update, context)
        
        task = asyncio.create_task(update_persistent_backup(context))
        state_data.setdefault("bg_tasks", set()).add(task)
        task.add_done_callback(lambda t: state_data["bg_tasks"].discard(t))
        return

    keys = await db.get_users_by_tg_id(user_id)
    if keys: 
        await client_menu(update, context)
    else: 
        await context.bot.send_message(chat_id=user_id, text="⛔️ **Нет доступа**\n\nУ вас нет привязанных ключей.\nПопросите администратора добавить ваш Telegram ID.", parse_mode=ParseMode.MARKDOWN)

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    await safe_delete(context, update.effective_chat.id, update.message.message_id)

async def _filter_bypass_cidrs(cidrs):
    """Валидация bypass-подсетей через guard wg-api (route_safe): (safe, rejected_msgs).
    Отсекает широкие/служебные CIDR. Если wg-api недоступен — не блокируем ввод
    (на бэке build_split_allowed_ips всё равно отфильтрует небезопасные при выдаче конфига)."""
    wg_base = WG_API_URL.rsplit("/api", 1)[0]
    try:
        async with api_session() as s:
            async with s.post(f"{wg_base}/routing/bypass-check", json={"cidrs": list(cidrs)}, timeout=8) as r:
                if r.status != 200:
                    return list(cidrs), []
                data = await r.json()
    except Exception:
        return list(cidrs), []
    safe, rejected = [], []
    for item in data.get("results", []):
        if item.get("ok"):
            safe.append(item["cidr"])
        else:
            rejected.append(f"{item['cidr']} — {item.get('reason', '')}")
    return safe, rejected

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    chat_id = update.message.chat_id
    user_msg_id = update.message.message_id

    # Ввод по ролям (название роли, адрес доступа) — только для админа.
    if state in ("awaiting_role_name", "awaiting_role_grant"):
        if not check_admin(update.effective_user.id):
            context.user_data["state"] = None
            return
        if await handle_role_text(update, context, state):
            return

    # Номер инцидента — от человека, но разбирает его владелец.
    if state == "awaiting_hit_ref":
        if not check_admin(update.effective_user.id):
            context.user_data["state"] = None
            return
        if await hit_find_entered(update, context):
            return

    # Свои пулы: список доменов и название для него.
    if state in ("awaiting_pool_domains", "awaiting_pool_title"):
        if not check_admin(update.effective_user.id):
            context.user_data["state"] = None
            return
        handler = (flt_pool_doms if state == "awaiting_pool_domains"
                   else flt_pool_title)
        if await handler(update, context):
            return

    # Исключения из фильтра разрешают сайт вопреки запрету — только владелец.
    if state == "awaiting_filter_allow":
        if not check_admin(update.effective_user.id):
            context.user_data["state"] = None
            return
        if await flt_allow_entered(update, context):
            return

    # Свои исключения меняют маршрутизацию на чужом устройстве — только владелец.
    if state == "awaiting_route_add":
        if not check_admin(update.effective_user.id):
            context.user_data["state"] = None
            return
        if await handle_route_input(update, context):
            return

    # Реквизиты и текст обращения — только от владельца: это его деньги и его
    # слова, и подменить их не должен никто.
    if state and state.startswith("awaiting_donate_"):
        if not check_admin(update.effective_user.id):
            context.user_data["state"] = None
            return
        if await handle_donate_input(update, context, state):
            return

    # Пароль архива бэкапа: записываем в .env через демон на хосте и сразу удаляем
    # сообщение — пароль не должен остаться висеть в переписке.
    if state == "awaiting_backup_password":
        context.user_data["state"] = None
        if ADMIN_ID and chat_id != ADMIN_ID:
            return
        pw = (update.message.text or "").strip()
        await safe_delete(context, chat_id, user_msg_id)
        if len(pw) < 8:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Слишком короткий пароль — нужно хотя бы 8 символов. Попробуйте снова.")
            await return_to_main_menu(update, context, chat_id=chat_id)
            return
        flag = request_env_change("BACKUP_PASSWORD", pw)
        await context.bot.send_message(
            chat_id=chat_id,
            text="🔐 Пароль передан на сервер. Жду, пока применится…")
        # Положить просьбу — не значит применить её. Записывает переменную демон
        # на хосте; если он не запущен, просьба пролежит вечно, а бот раньше
        # рапортовал об успехе и снова требовал пароль на следующем экране.
        if await env_change_applied(flag):
            text = ("🔐 Пароль записан в `.env` — бот сейчас перезапустится.\n\n"
                    "⚠️ Сохраните пароль отдельно: без него архивы не открыть, "
                    "а в базе его нет намеренно.")
        else:
            text = ("⚠️ **Пароль не применился.**\n\n"
                    "Записывает его служба обновлений на сервере, и она не "
                    "ответила. Проверьте её:\n"
                    "`systemctl status vpn-updater`\n"
                    "`systemctl restart vpn-updater`\n\n"
                    "Пароль не потерян: просьба лежит в `volumes/flags/set_env` "
                    "и применится, как только служба поднимется.")
        await context.bot.send_message(chat_id=chat_id, text=text,
                                       parse_mode=ParseMode.MARKDOWN)
        return

    # Кастомная рассылка: админ прислал свой текст → шлём его ВСЕМ пользователям.
    if state == "awaiting_broadcast_text":
        context.user_data["state"] = None
        if ADMIN_ID and chat_id != ADMIN_ID:
            return
        text = update.message.text
        if not text or not text.strip():
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Пустое сообщение — рассылка отменена.")
            return
        try:
            await broadcast_message(context.application, text, db)
            await db.log_event("System", "Admin sent custom broadcast.")
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ **Рассылка отправлена** всем пользователям.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_main")]]),
                parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка рассылки: {e}")
        return

    if state == "awaiting_support_message":
        target_uuid = state_data["support_context"].get(chat_id)
        msg_text = update.message.text or "Контент без текста"
        
        user_name = "Неизвестный"
        if target_uuid:
            user = await db.get_user_by_uuid(target_uuid)
            if user: user_name = user['name']
            
            await db.execute("INSERT INTO support_tickets (user_uuid, message) VALUES ($1, $2)", target_uuid, msg_text)

        admin_text = f"🚨 <b>НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ</b> 🚨\n\n"
        admin_text += f"👤 Пользователь: <a href='tg://user?id={update.effective_user.id}'>{html.escape(update.effective_user.first_name)}</a>\n"
        admin_text += f"🔑 Ключ: <code>{html.escape(user_name)}</code>\n"
        admin_text += f"\n📝 <b>Описание проблемы:</b>\n<i>{html.escape(msg_text)}</i>"

        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode=ParseMode.HTML)
            await db.log_event("Support", f"Ticket from {user_name}: {msg_text[:50]}...")
            
            await context.bot.send_message(chat_id=chat_id, text="✅ **Ваше сообщение успешно отправлено!**\n\nОно зарегистрировано в системе. Администратор ответит вам в ближайшее время.", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text="❌ Ошибка отправки сообщения. Попробуйте позже.")

        context.user_data["state"] = None
        if chat_id in state_data["support_context"]:
            del state_data["support_context"][chat_id]

        await client_menu(update, context)
        return

    if state == "awaiting_bypass_report":
        target = update.message.text or ""
        context.user_data["state"] = None
        res = await asyncio.to_thread(analyze_resource, target)

        if res["error"] or not res["cidrs"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Не удалось проанализировать «{escape_md(target)}»: {escape_md(res.get('error') or 'адрес не разрешился')}.",
                parse_mode=ParseMode.MARKDOWN
            )
            await client_menu(update, context)
            return

        req_id = await db.add_bypass_request(res["domain"], res["cidrs"], update.effective_user.id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(f"✅ Принято! Адрес `{escape_md(res['domain'])}` ({len(res['cidrs'])} подсетей) "
                  "отправлен администратору. После добавления вам придёт уведомление "
                  "с предложением перевыпустить ключ."),
            parse_mode=ParseMode.MARKDOWN
        )
        if ADMIN_ID:
            ips = ", ".join(res["ips"][:5])
            cidrs = ", ".join(res["cidrs"])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Добавить в исключения", callback_data=f"bypass_addreq_{req_id}")],
                [InlineKeyboardButton("❌ Отклонить", callback_data=f"bypass_rejreq_{req_id}")],
            ])
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(f"🌐 **Заявка на исключение (split-tunnel)**\n\n"
                          f"👤 От: `{update.effective_user.id}`\n"
                          f"🔗 Домен: `{escape_md(res['domain'])}`\n"
                          f"📡 IP: `{ips}`\n"
                          f"📦 Подсети: `{cidrs}`\n\n"
                          "Добавить в обход VPN?"),
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            except Exception:
                pass
        await client_menu(update, context)
        return

    if not check_admin(update.effective_user.id): return
    await safe_delete(context, chat_id, user_msg_id)

    # ---------------- ОБРАБОТЧИКИ АДМИНА ----------------
    if state == "awaiting_rename":
        uuid_val = context.user_data.get("target_uuid")
        menu_id = context.user_data.get("menu_msg_id")
        context.user_data["state"] = None
        user = await db.get_user_by_uuid(uuid_val)
        if not user:
            return
        old_name = user["name"]
        new_name = sanitize_name(update.message.text)
        if new_name and new_name != old_name:
            # переименовываем КЭШ-файлы конфигов (тот же ключ, содержимое не меняется) —
            # чтобы и сам файл у пользователя назывался по-новому. Туннель/ключ НЕ трогаем.
            for suf in (".conf", "_Full.conf", ".png", "_Full.png"):
                try:
                    src = CONFIGS_DIR / f"{old_name}{suf}"
                    if src.exists():
                        src.rename(CONFIGS_DIR / f"{new_name}{suf}")
                except Exception:
                    pass
            await db.execute("UPDATE users SET name=$1 WHERE uuid=$2", new_name, uuid_val)
            await db.log_event("Rename", f"Key {uuid_val}: '{old_name}' → '{new_name}'")
        if menu_id:
            await render_user_detail(context, chat_id, menu_id, uuid_val)
        return

    if state == "awaiting_bypass_add":
        target = update.message.text or ""
        context.user_data["state"] = None
        res = await asyncio.to_thread(analyze_resource, target)
        if res["error"] or not res["cidrs"]:
            kb = [[InlineKeyboardButton("🌐 К списку исключений", callback_data="bypass_list")]]
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Не удалось: {escape_md(res.get('error') or 'адрес не разрешился')}", reply_markup=InlineKeyboardMarkup(kb))
            return
        # GUARD (порт route_safe из OpenWRT): отсекаем слишком широкие CIDR (увели бы
        # весь трафик мимо DE) и пересечения со служебными/внутренними сетями ноды —
        # иначе можно порвать роутинг/DE-туннель. Проверку делает wg-api (знает свои сети).
        safe_cidrs, rejected = await _filter_bypass_cidrs(res["cidrs"])
        if not safe_cidrs:
            kb = [[InlineKeyboardButton("🌐 К списку исключений", callback_data="bypass_list")]]
            await context.bot.send_message(
                chat_id=chat_id,
                text=("❌ Отклонено — подсети небезопасны для обхода (порвали бы маршрутизацию):\n"
                      f"{escape_md('; '.join(rejected))}"),
                reply_markup=InlineKeyboardMarkup(kb))
            return
        new_v = await db.add_bypass_exclusion(res["domain"], safe_cidrs, note="добавлено вручную", source="manual")
        await db.log_event("Routing", f"Bypass exclusion added manually: {res['domain']} -> v{new_v}.")
        skipped_line = (f"\n⚠️ Пропущены небезопасные: `{escape_md('; '.join(rejected))}`" if rejected else "")
        kb = [[InlineKeyboardButton("🌐 К списку исключений", callback_data="bypass_list")]]
        await context.bot.send_message(
            chat_id=chat_id,
            text=(f"✅ Добавлено: `{escape_md(res['domain'])}`\n"
                  f"Подсети: `{', '.join(safe_cidrs)}`{skipped_line}\n"
                  f"Версия маршрутизации: `{new_v}` — пользователям уйдёт напоминание о перевыпуске."),
            parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if state == "awaiting_schedule_time":
        time_str = update.message.text.strip()
        menu_id = context.user_data.get("menu_msg_id")
        
        try:
            dt = datetime.strptime(time_str, "%d.%m.%Y %H:%M")
            dt_db_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            await db.set_setting("scheduled_update", dt_db_str)
            
            kb = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
            text_success = f"✅ Обновление успешно запланировано на {time_str} (МСК).\nПользователи оповещены."
            if menu_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text=text_success, reply_markup=InlineKeyboardMarkup(kb))
            else:
                await context.bot.send_message(chat_id=chat_id, text=text_success, reply_markup=InlineKeyboardMarkup(kb))
            
            text_broadcast = f"⚙️ **Внимание!**\n\nЗапланировано техническое обновление системы.\n📅 Время: **{time_str} (МСК)**.\nВ этот период VPN может быть временно недоступен (1-2 минуты)."
            await broadcast_message(context.application, text_broadcast, db)
            
            context.user_data["state"] = None
        except ValueError:
            kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
            err_text = "❌ **Неверный формат!**\n\nПожалуйста, используйте формат: `ДД.ММ.ГГГГ ЧЧ:ММ`\nНапример: `15.05.2024 14:30`"
            if menu_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text=err_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if state == "awaiting_support_reply":
        ticket_id = context.user_data.get("reply_ticket_id")
        reply_text = update.message.text.strip()
        menu_id = context.user_data.get("menu_msg_id")
        
        ticket = await db.fetch_all("SELECT user_uuid FROM support_tickets WHERE id=$1", int(ticket_id))
        if ticket:
            uuid_val = ticket[0]['user_uuid']
            user = await db.get_user_by_uuid(uuid_val)
            if user and user.get('tg_ids'):
                for tid in user['tg_ids']:
                    try:
                        await context.bot.send_message(chat_id=tid, text=f"🛠 **Ответ от Техподдержки:**\n\n_{escape_md(reply_text)}_", parse_mode="Markdown")
                    except: pass
            
            await db.execute("UPDATE support_tickets SET status='closed' WHERE id=$1", int(ticket_id))
            
            kb = [[InlineKeyboardButton("🔙 К списку обращений", callback_data="support_admin_menu")]]
            if menu_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text="✅ Ответ отправлен, обращение закрыто.", reply_markup=InlineKeyboardMarkup(kb))
        
        context.user_data["state"] = None
        return

    if state == "awaiting_block_site":
        await flt_centered(update, context, update.message.text)
        return

    if state == "awaiting_dns_name":
        await dnm_name_entered(update, context, update.message.text)
        return

    if state == "awaiting_dns_ip":
        await dnm_ip_entered(update, context, update.message.text)
        return

    if state == "awaiting_dns_rename":
        await dnm_rename_entered(update, context, update.message.text)
        return

    if state == "awaiting_name":
        # Транслит рус->лат + обрезка эмодзи, чтобы имя приняло приложение AmneziaWG
        name = sanitize_name(update.message.text)
        context.user_data["name"] = name
        menu_id = context.user_data.get("menu_msg_id")
        
        if "proto" not in context.user_data:
            context.user_data["proto"] = await default_proto()
        if menu_id:
            text, keyboard = await new_key_screen(context, name)
            await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id,
                                                text=text, reply_markup=keyboard,
                                                parse_mode=ParseMode.MARKDOWN)
        # Срок действия выбирается КНОПКОЙ (set_exp_*), текст больше не ждём → сбрасываем состояние.
        context.user_data["state"] = None

    elif state in["awaiting_tg_link_new_key", "awaiting_tg_link_existing"]:
        result = await extract_tg_id(update.message, context)
        
        menu_id = context.user_data.get("menu_msg_id")
        keyboard = [[InlineKeyboardButton("⏩ Пропустить/Отмена", callback_data="skip_tg_link")]]
        
        if result == "HIDDEN":
            text = "🔒 **Профиль пользователя скрыт!**\n\nTelegram не позволяет получить ID при пересылке сообщений от пользователей с настройками приватности.\n\n✅ **Решение:** Попросите пользователя прислать свой **Контакт** (📎 -> Контакт) и перешлите его сюда."
            if menu_id: await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            return
        
        if result == "INVALID":
            text = "❌ **Пользователь не найден**\n\nБот не может найти этого пользователя по @username. Возможно, он еще не запускал этого бота.\nПопросите ID или Контакт."
            if menu_id: await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            return

        if not result or not isinstance(result, int):
            text = "❌ **Не удалось определить ID**\n\nОтправьте:\n1. **Контакт** 📎 (лучший способ)\n2. Пересланное сообщение (если профиль открыт)\n3. Числовой ID\n4. @username (если юзер запускал бота)"
            if menu_id: await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            return

        if state == "awaiting_tg_link_new_key":
            await finish_key_creation(update, context, result)
        else:
            uuid_val = context.user_data.get("target_uuid")
            await db.link_user_telegram(uuid_val, result)
            context.user_data["state"] = None
            await context.bot.send_message(chat_id=chat_id, text=f"✅ Успешно привязан ID `{result}`!", parse_mode=ParseMode.MARKDOWN)
            if menu_id: await render_user_detail(context, chat_id, menu_id, uuid_val)
            
            try:
                await context.bot.send_message(
                    chat_id=result,
                    text="🎉 **Привет!** Администратор привязал этот Telegram-аккаунт к вашему VPN-ключу.\n\nТеперь вы можете управлять своим подключением прямо здесь.",
                    parse_mode=ParseMode.MARKDOWN
                )
                await send_client_menu(context, result)
                await context.bot.send_message(chat_id=chat_id, text=f"✅ Приветственное сообщение успешно отправлено пользователю `{result}`.")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Пользователь `{result}` не получил меню (возможно, он еще не запустил бота командой /start):\n`{e}`", parse_mode=ParseMode.MARKDOWN)

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data not in ["start_dashboard", "vpn_graph", "show_online"]: 
        await stop_bg_tasks()

    query = update.callback_query
    data = query.data

    # Любой переход означает, что сообщение больше не показывает главное меню.
    # Снимаем его с авто-перерисовки здесь, а не в каждом экране по отдельности:
    # иначе фоновый счётчик онлайна подменяет клавиатуру и
    # получается текст одного экрана с кнопками другого.
    if data != "back_to_main":
        deregister_menu(update.effective_chat.id)
    
    # Подменю управления серверами
    if data in ["menu_ru_server", "menu_de_server", "menu_backups"]:
        from handlers_admin import sub_menu_router
        await sub_menu_router(update, context)
        return
    
    # Роутер функций
    
    if data == "support_start": await support_start_handler(update, context); return
    if data.startswith("support_audit_"): await support_run_audit_handler(update, context, data.split("support_audit_")[1]); return
    if data.startswith("support_ask_"): await support_ask_msg_handler(update, context, data.split("support_ask_")[1]); return

    if data == "client_menu":
        context.user_data["state"] = None
        await client_menu(update, context)
        return
        
    if data == "client_my_keys": await client_my_keys_handler(update, context); return
    if data.startswith("client_key_manage_"): await client_key_manage_handler(update, context, data.split("client_key_manage_")[1]); return
    if data == "client_regen_all": await client_regen_all_confirm_handler(update, context); return
    if data == "do_client_regen_all": await client_regen_all_action_handler(update, context); return
    
    if data == "client_select_check": await client_select_check_menu(update, context); return
    if data == "client_check_all": await client_check_all_handler(update, context); return
    if data.startswith("check_conn_"): await check_connection_handler(update, context, data.replace("check_conn_", "")); return
    
    if data == "client_stats": await client_stats_handler(update, context); return
    if data == "client_bypass_info": await client_bypass_info_handler(update, context); return
    if data == "client_report_site": await client_report_site_handler(update, context); return
    if data == "client_apps": await client_apps_handler(update, context); return
    if data == "client_donate": await client_donate(update, context); return
    if data == "client_donate_qr": await client_donate_qr(update, context); return
    if data == "client_whats_new": await client_whats_new(update, context); return
    if data == "client_notify_toggle": await client_notify_toggle_handler(update, context); return
    if data == "client_notify_off": await client_notify_off_handler(update, context); return
    if data.startswith("client_download_"): await client_download_handler(update, context, data.split("client_download_")[1]); return
    
    if data.startswith("client_plat_"):
        parts = data.split("_", 3)          # client | plat | система | uuid
        await client_platform_handler(update, context, parts[2], parts[3]); return
    if data.startswith("client_how_"): await client_how_handler(update, context, data.split("client_how_")[1]); return
    if data.startswith("client_regen_"): await client_regen_confirm(update, context, data.split("client_regen_")[1]); return
    if data.startswith("do_client_regen_"): await client_regen_action(update, context, data.split("do_client_regen_")[1]); return

    if not check_admin(update.effective_user.id): return await query.answer("Доступ запрещен")

    # --- Экраны администратора ---
    # ВСЁ, что ниже, доступно только владельцу. Раньше часть этих экранов стояла
    # ВЫШЕ проверки, а сами обработчики прав не проверяют: защитой служило лишь то,
    # что у пользователя нет таких кнопок. Но callback_data не секрет — обратиться
    # по ней может кто угодно, кому она известна.
    if data == "run_audit": await run_audit_handler(update, context); return
    if data == "svc_menu": await service_menu(update, context); return
    if data == "svc_mode_toggle": await toggle_mode(update, context); return
    if data == "svc_mode_on": await set_mode(update, context, True); return
    if data == "svc_mode_off": await set_mode(update, context, False); return
    # Токен панелей: состояние, переключатель расписания и смена по кнопке.
    if data == "svc_token": await token_screen(update, context); return
    if data == "svc_tok_toggle": await token_toggle(update, context); return
    if data == "svc_tok_now": await token_now(update, context); return
    if data == "svc_tok_back": await token_rollback(update, context); return
    if data == "svc_tfix": await traffic_fix_screen(update, context); return
    if data == "svc_tfix_go": await traffic_fix_apply(update, context); return
    if data == "svc_load": await load_screen(update, context); return
    if data.startswith("svc_ev_del_"):
        await event_delete(update, context, data.split("svc_ev_del_")[1]); return
    if data == "svc_chart": await load_chart(update, context); return
    if data == "vpn_graph": await graphs_menu(update, context); return
    if data == "svc_charts": await charts_screen(update, context); return
    if data.startswith("svc_pick_"):
        await pick_peer_screen(update, context, int(data.split("_")[-1])); return
    if data == "svc_whatsnew": await whats_new(update, context); return
    if data.startswith("svc_pchart_"):
        await load_chart(update, context, data.replace("svc_pchart_", "")); return
    if data == "svc_limits": await limits_screen(update, context); return
    if data.startswith("svc_lim_"):
        await peer_limit_screen(update, context, data.split("_", 2)[2]); return
    if data == "svc_noop": await update.callback_query.answer(); return
    if data == "svc_limit_up": await change_limit(update, context, "up"); return
    if data == "svc_limit_down": await change_limit(update, context, "down"); return
    if data.startswith("svc_limit_"):
        await change_limit(update, context, data.replace("svc_limit_", "")); return
    if data.startswith("svc_rule_"):
        _, _, mode, uuid_val = data.split("_", 3)
        await set_peer_rule(update, context, uuid_val, mode); return

    if data == "set_backup_pw": await ask_backup_password(update, context); return

    # --- Роли: доступы внутри туннеля ---
    # Намеренно ПОСЛЕ проверки админа: роли решают, кто к кому ходит, и открывать
    # эти экраны кому попало нельзя.
    # --- Судьба ключа: истёк срок или уснул ---
    # Вопрос живёт в базе, поэтому эти кнопки работают и в старом сообщении
    # после перезапуска бота.
    if data == "kd_list": await pending_screen(update, context); return
    if data == "deliv_list": await delivery_screen(update, context); return

    # --- Переезд на новый ключ сервера ---
    # Необратимое здесь только одно — остановка старого интерфейса, и она
    # спрятана за отдельным экраном со списком тех, кто ещё не переехал.
    if data == "mig_menu": await migration_menu(update, context); return
    if data == "mig_start": await migration_start(update, context); return
    if data == "mig_de": await migration_de(update, context); return
    if data.startswith("mig_issue_"):
        await migration_issue(update, context, int(data.split("_")[-1])); return
    if data.startswith("mig_send_"):
        await migration_send(update, context, data.split("_", 2)[2]); return
    if data == "mig_finish": await migration_finish_confirm(update, context); return
    if data == "mig_finish_ok": await migration_finish(update, context); return
    if data == "mig_abort": await migration_abort_confirm(update, context); return
    if data == "mig_abort_ok": await migration_abort(update, context); return

    # --- Протоколы: AmneziaWG и Xray ---
    if data == "proto_menu": await protocols_menu(update, context); return
    if data == "proto_awg": await awg_screen(update, context); return
    if data == "proto_xray": await xray_screen(update, context); return
    if data == "proto_on_awg": await switch_do(update, context, "awg", True); return
    if data == "proto_on_xray": await switch_do(update, context, "xray", True); return
    # offok проверяется раньше off_: короткий префикс перехватил бы длинный
    if data.startswith("proto_offok_"):
        await switch_do(update, context, data.split("_")[-1], False); return
    if data.startswith("proto_off_"):
        await switch_confirm(update, context, data.split("_")[-1]); return

    if data == "xr_apply": await xray_apply_now(update, context); return
    if data == "xr_apps": await apps_screen(update, context); return
    if data == "xr_mask": await mask_screen(update, context); return
    if data.startswith("xr_mask_"):
        await mask_set(update, context, data[len("xr_mask_"):]); return
    if data == "xr_move": await move_screen(update, context); return
    # Свои исключения на ключ. Длинные префиксы раньше коротких: иначе
    # короткий перехватит чужое нажатие.
    if data.startswith("rt_menu_"):
        await routes_menu(update, context, data.split("rt_menu_")[1]); return
    if data.startswith("rt_show_"):
        await routes_show(update, context, data.split("rt_show_")[1]); return
    if data.startswith("rt_add_d_"):
        await routes_ask(update, context, "direct", data.split("rt_add_d_")[1]); return
    if data.startswith("rt_add_p_"):
        await routes_ask(update, context, "proxy", data.split("rt_add_p_")[1]); return
    if data.startswith("rt_del_"):
        rid, _, uid = data.split("rt_del_")[1].partition("_")
        await routes_delete(update, context, rid, uid); return

    if data.startswith("xr_conn_"):
        await connections_screen(update, context, data.split("_", 2)[2]); return
    if data.startswith("xr_issue_"):
        await issue_xray(update, context, data.split("_", 2)[2]); return
    if data.startswith("xr_send_"):
        await send_link(update, context, data.split("_", 2)[2]); return
    if data.startswith("xr_dropawg_"):
        await drop_awg(update, context, data.split("_", 2)[2]); return
    if data.startswith("xr_why_"):
        await why_locked(update, context, data.split("_", 2)[2]); return
    # --- Имена внутри туннеля ---
    # Порядок важен: длинные префиксы проверяются раньше коротких, иначе
    # короткий перехватит чужое нажатие.
    if data == "don_menu": await donate_menu(update, context); return
    if data == "don_toggle": await donate_toggle(update, context); return
    if data == "don_rem_toggle": await donate_reminder_toggle(update, context); return
    if data == "don_preview": await donate_preview(update, context); return
    if data == "don_period": await donate_period(update, context); return
    if data == "don_per_own": await donate_ask(update, context, "days"); return
    if data.startswith("don_per_"):
        await donate_period_set(update, context, data.split("don_per_")[1]); return
    if data == "don_text": await donate_ask(update, context, "text"); return
    if data.startswith("don_add_"):
        await donate_ask(update, context, data.split("don_add_")[1]); return
    if data.startswith("don_open_"):
        await donate_open(update, context, data.split("don_open_")[1]); return
    if data.startswith("don_del_"):
        await donate_delete(update, context, data.split("don_del_")[1]); return

    if data == "dnm_menu": await names_menu(update, context); return
    if data == "dnm_add": await dnm_add(update, context); return
    if data == "dnm_apply": await dnm_apply(update, context); return
    if data == "dnm_manual": await dnm_manual(update, context); return
    if data.startswith("dnm_pg_"):
        await dnm_page(update, context, int(data.split("_")[-1])); return
    if data.startswith("dnm_to_"):
        await dnm_person(update, context, data.split("_", 2)[2]); return
    if data.startswith("dnm_open_"):
        await dnm_open(update, context, data.split("_", 2)[2]); return
    if data.startswith("dnm_ren_"):
        await dnm_rename(update, context, data.split("_", 2)[2]); return
    if data.startswith("dnm_re_"):
        await dnm_retarget(update, context, data.split("_", 2)[2]); return
    if data.startswith("dnm_del_"):
        await dnm_delete(update, context, data.split("_", 2)[2]); return

    # --- Фильтрация сайтов ---
    # Попытки на закрытое. Длинные префиксы раньше коротких.
    if data == "hit_list": await hits_screen(update, context); return
    if data == "hit_seen_all": await hits_seen_all(update, context); return
    if data == "hit_find": await hit_find_request(update, context); return
    if data.startswith("hit_pg_"):
        await hits_screen(update, context, int(data.split("hit_pg_")[1])); return
    if data.startswith("hit_open_"):
        await hit_open(update, context, data.split("hit_open_")[1]); return

    if data == "flt_menu": await filters_menu(update, context); return
    if data == "flt_common": await flt_common(update, context); return
    if data == "flt_cadd": await flt_cadd(update, context); return
    if data == "flt_clist": await flt_clist(update, context); return
    if data.startswith("flt_ctog_"):
        await flt_ctoggle(update, context, data.split("_", 2)[2]); return
    if data.startswith("flt_cdel_"):
        await flt_cremove(update, context, data.split("_", 2)[2]); return
    if data.startswith("flt_cpg_"):
        await flt_clist(update, context, int(data.split("_")[-1])); return
    if data == "flt_apply": await filters_apply_now(update, context); return

    # Свои пулы фильтров.
    if data == "flt_pool_list": await flt_pools(update, context); return
    if data == "flt_pool_new": await flt_pool_new(update, context); return
    if data.startswith("flt_pool_o_"):
        await flt_pool_open(update, context, data.split("flt_pool_o_")[1]); return
    if data.startswith("flt_pool_a_"):
        await flt_pool_add(update, context, data.split("flt_pool_a_")[1]); return
    if data.startswith("flt_pool_d_"):
        await flt_pool_del(update, context, data.split("flt_pool_d_")[1]); return

    # Исключения. Порядок проверок: сначала длинные и точные префиксы.
    if data == "flt_alw_all": await flt_allow(update, context, None); return
    if data == "flt_alw_add_all": await flt_allow_add(update, context, None); return
    if data.startswith("flt_alw_add_"):
        await flt_allow_add(update, context, data.split("flt_alw_add_")[1]); return
    if data.startswith("flt_alw_del_"):
        rest = data.split("flt_alw_del_")[1]
        aid, _, who = rest.partition("_")
        await flt_allow_del(update, context, aid,
                            None if who == "all" else who); return
    if data.startswith("flt_alw_"):
        await flt_allow(update, context, data.split("flt_alw_")[1]); return
    if data.startswith("flt_pick_"):
        await filters_pick_user(update, context, int(data.split("_")[-1])); return
    if data.startswith("flt_user_"):
        await user_filters_screen(update, context, data.split("_", 2)[2]); return
    if data.startswith("flt_set_"):
        parts = data.split("_", 3)          # flt | set | категория | uuid
        await toggle_filter(update, context, parts[3], parts[2]); return
    if data.startswith("kd_open_"):
        await decision_screen(update, context, data.split("_", 2)[2]); return
    if data.startswith("kd_ext_"):
        await extend_menu(update, context, data.split("_", 2)[2]); return
    if data.startswith("kd_set_"):
        parts = data.split("_", 3)          # kd | set | дни | uuid
        await do_extend(update, context, parts[3], int(parts[2])); return
    if data.startswith("kd_pol_"):
        parts = data.split("_", 3)          # kd | pol | ask или дни | uuid
        await set_policy(update, context, parts[3], parts[2]); return
    # delok проверяется раньше del_: короткий префикс перехватил бы длинный
    if data.startswith("kd_delok_"):
        await do_delete(update, context, data.split("_", 2)[2]); return
    if data.startswith("kd_del_"):
        await delete_confirm(update, context, data.split("_", 2)[2]); return

    if data == "roles_menu": await roles_menu(update, context); return
    if data.startswith("role_ut_"):
        parts = data.split("_", 3)          # role | ut | id | uuid
        await user_role_toggle(update, context, int(parts[2]), parts[3]); return
    if data.startswith("role_u_"):
        await user_roles_screen(update, context, data.split("_", 2)[2]); return
    if data == "role_new": await role_new(update, context); return
    if data == "new_key_role": await new_key_role_screen(update, context); return
    if data == "new_key_back":
        text, kb = await new_key_screen(context, context.user_data.get("name", ""))
        await query.edit_message_text(text, reply_markup=kb,
                                      parse_mode=ParseMode.MARKDOWN)
        return
    if data.startswith("nkrole_"):
        await new_key_role_set(update, context, int(data.rsplit("_", 1)[1])); return
    if data == "role_default": await default_role_screen(update, context); return
    if data.startswith("role_defset_"):
        await default_role_set(update, context, int(data.rsplit("_", 1)[1])); return
    if data == "role_apply": await role_apply(update, context); return
    if data.startswith("role_open_"):
        await role_screen(update, context, int(data.split("_")[-1])); return
    if data.startswith("role_gadd_"):
        await grant_add_screen(update, context, int(data.split("_")[-1])); return
    if data.startswith("role_gman_"):
        await grant_manual(update, context, int(data.split("_")[-1])); return
    if data.startswith("role_gall_"):
        await grant_whole_tunnel(update, context, int(data.split("_")[-1])); return
    if data.startswith("role_gname_"):
        parts = data.split("_", 3)          # role | gname | id | имя
        await grant_name(update, context, int(parts[2]), parts[3]); return
    if data.startswith("role_gpeer_"):
        parts = data.split("_", 3)          # role | gpeer | id | uuid (в uuid дефисы)
        await grant_peer(update, context, int(parts[2]), parts[3]); return
    if data.startswith("role_gdel_"):
        parts = data.split("_")
        await grant_del(update, context, int(parts[2]), int(parts[3])); return
    if data.startswith("role_madd_"):
        parts = data.split("_")
        await members_screen(update, context, int(parts[2]), int(parts[3])); return
    if data.startswith("role_mset_"):
        await member_add(update, context, int(data.split("_")[2]),
                         data.split("_", 3)[3]); return
    if data.startswith("role_mdel_"):
        await member_del(update, context, int(data.split("_")[2]),
                         data.split("_", 3)[3]); return
    # delok проверяется раньше del_: иначе более короткий префикс перехватил бы его
    if data.startswith("role_delok_"):
        await role_delete(update, context, int(data.split("_")[-1])); return
    if data.startswith("role_del_"):
        await role_delete_confirm(update, context, int(data.split("_")[-1])); return

    if data == "back_to_main": await return_to_main_menu(update, context); return
    if data == "toggle_auto_update": await toggle_auto_update(update, context); return
    if data == "schedule_update": await schedule_update_menu(update, context); return
    
    if data == "de_confirm_reboot": await de_confirm_reboot(update, context); return
    if data == "do_de_reboot_server": await do_de_reboot_server(update, context); return
    if data == "de_read_logs_full":
        await de_read_logs(update, context, full=True); return
    if data == "de_read_logs": await de_read_logs(update, context); return
    if data == "de_update": await de_update(update, context); return
    if data == "update_all": await update_all(update, context); return
    if data == "de_backup": await de_backup(update, context); return
    if data == "de_run_audit": await de_run_audit(update, context); return
    
    if data == "maintenance_warn":
        kb = [
            [InlineKeyboardButton("✍️ Своя рассылка (свой текст)", callback_data="broadcast_custom")],
            [InlineKeyboardButton("⚠️ Стандартное: тех. работы", callback_data="do_maintenance_warn")],
            [InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")],
        ]
        await query.edit_message_text(
            "📢 **Рассылка всем пользователям**\n\nВыберите, что отправить:",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return
    if data == "broadcast_custom":
        context.user_data["state"] = "awaiting_broadcast_text"
        await query.edit_message_text(
            "✍️ **Своя рассылка**\n\nПришли текст — я разошлю его всем пользователям (у кого привязан Telegram).\n"
            "Поддерживается *Markdown* (\\*жирный\\*, \\_курсив\\_).\n\nДля отмены нажми «Отмена» или /start.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]),
            parse_mode=ParseMode.MARKDOWN)
        return
    if data == "do_maintenance_warn":
        await broadcast_message(context.application, "⚠️ **Внимание!**\n\nВ настоящий момент проводится техническое обслуживание сервера.\nВозможны временные перебои в работе сервиса в течение ближайших часов.\nСпасибо за понимание!", db)
        await db.log_event("System", "Admin sent Maintenance broadcast.")
        await query.edit_message_text("✅ Предупреждение успешно разослано.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_main")]]))
        return
        
    if data == "bypass_list": await bypass_list_handler(update, context); return
    if data == "bypass_happ": await bypass_happ_handler(update, context); return
    if data == "bypass_add_manual": await bypass_add_manual_handler(update, context); return
    if data.startswith("bypass_del_"): await bypass_del_handler(update, context, data.split("bypass_del_")[1]); return
    if data.startswith("bypass_addreq_"): await bypass_add_request_handler(update, context, data.split("bypass_addreq_")[1], approve=True); return
    if data.startswith("bypass_rejreq_"): await bypass_add_request_handler(update, context, data.split("bypass_rejreq_")[1], approve=False); return

    if data == "support_admin_menu": await support_admin_menu(update, context); return
    if data.startswith("supp_usr_"): await support_user_tickets(update, context, data.split("supp_usr_")[1]); return
    if data.startswith("supp_tkt_"): await support_ticket_detail(update, context, data.split("supp_tkt_")[1]); return
    if data.startswith("supp_rep_"): await support_reply_start(update, context, data.split("supp_rep_")[1]); return
    if data.startswith("supp_clo_"): await support_close_ticket(update, context, data.split("supp_clo_")[1]); return

    if data == "skip_tg_link":
        if context.user_data.get("state") == "awaiting_tg_link_new_key":
            await finish_key_creation(update, context, None)
        else:
            uuid_val = context.user_data.get("target_uuid")
            await user_detail_menu(update, context, uuid_val)
        return
    
    if data == "new_proto":
        # Переключатель протокола прямо на экране срока: один шаг вместо
        # лишнего вопроса, и по умолчанию всё равно Xray.
        now = context.user_data.get("proto", "xray")
        context.user_data["proto"] = "awg" if now == "xray" else "xray"
        text, keyboard = await new_key_screen(context, context.user_data.get("name", ""))
        await query.edit_message_text(text, reply_markup=keyboard,
                                      parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("set_exp_"):
        context.user_data["expiry_days"] = int(data.split("_")[2])
        if context.user_data.get("proto", "xray") == "awg":
            keyboard = [[InlineKeyboardButton("🌍 Классический DNS (1.1.1.1)", callback_data="set_dns_classic")],[InlineKeyboardButton("🛡 AdBlock DNS (Без рекламы)", callback_data="set_dns_adblock")],[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
            await query.edit_message_text("Выберите DNS-сервер:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        # У Xray выбор DNS ни на что не влияет: имена резолвит узел, и фильтрация
        # живёт там же. Спрашивать не о чем — сразу к привязке Telegram.
        context.user_data["dns_type"] = "classic"
        keyboard = [[InlineKeyboardButton("⏩ Пропустить", callback_data="skip_tg_link")]]
        await query.edit_message_text(
            "🔗 **Привязка Telegram**\n\nОтправьте:\n1️⃣ **Контакт** 📎 (Рекомендуется)\n"
            "2️⃣ @username\n3️⃣ ID",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        context.user_data["state"] = "awaiting_tg_link_new_key"
        return
    if data.startswith("set_dns_"):
        context.user_data["dns_type"] = data.split("_")[2]
        keyboard = [[InlineKeyboardButton("⏩ Пропустить", callback_data="skip_tg_link")]]
        await query.edit_message_text("🔗 **Привязка Telegram**\n\nОтправьте:\n1️⃣ **Контакт** 📎 (Рекомендуется)\n2️⃣ @username\n3️⃣ ID", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        context.user_data["state"] = "awaiting_tg_link_new_key"
        return

    if data.startswith("users_page_"): await users_list_menu(update, context, int(data.split("_")[2])); return
    if data.startswith("user_detail_"): await user_detail_menu(update, context, data.split("user_detail_")[1]); return
    if data.startswith("clear_ips_"): await clear_user_ips(update, context, data.split("clear_ips_")[1]); return
        
    if data.startswith("rename_user_"):
        uuid_val = data.split("rename_user_")[1]
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"user_detail_{uuid_val}")]]
        await query.edit_message_text(
            "✏️ **Переименование ключа**\n\nОтправьте новое имя (рус/лат; эмодзи и спецсимволы уберутся).\n\n"
            "_Это только имя для отображения и файла конфига — на работу VPN и существующий ключ НЕ влияет._",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        context.user_data["state"] = "awaiting_rename"
        context.user_data["target_uuid"] = uuid_val
        context.user_data["menu_msg_id"] = query.message.message_id
        return

    if data.startswith("link_tg_"):
        uuid_val = data.split("link_tg_")[1]
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=f"user_detail_{uuid_val}")]]
        await query.edit_message_text("🔗 **Привязка Telegram**\n\nОтправьте:\n1️⃣ **Контакт** 📎\n2️⃣ @username\n3️⃣ ID", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        context.user_data["state"] = "awaiting_tg_link_existing"
        context.user_data["target_uuid"] = uuid_val
        context.user_data["menu_msg_id"] = query.message.message_id
        return
    if data.startswith("unlink_tg_"):
        uuid_val = data.split("unlink_tg_")[1]
        user = await db.get_user_by_uuid(uuid_val)
        keyboard = [[InlineKeyboardButton(f"❌ {tid}", callback_data=f"do_unlink_{uuid_val}_{tid}")] for tid in user.get('tg_ids',[])]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"user_detail_{uuid_val}")])
        await query.edit_message_text("Выберите ID для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data.startswith("do_unlink_"):
        parts = data.split("_")
        await db.unlink_user_telegram(parts[2], int(parts[3]))
        await query.answer("Успешно отвязан!")
        await user_detail_menu(update, context, parts[2])
        return

    if data.startswith("act_pause_"):
        uuid_val = data.split("act_pause_")[1]
        await query.answer("Заморозка...")
        await pause_peer(uuid_val)
        await db.execute("UPDATE users SET is_active=FALSE WHERE uuid=$1", uuid_val)
        # Пауза должна действовать сразу на обоих протоколах.
        await xray_sync("пауза")
        await db.log_event("Pause", f"Manually paused key {uuid_val}")
        await user_detail_menu(update, context, uuid_val)
        return
    if data.startswith("act_resume_"):
        uuid_val = data.split("act_resume_")[1]
        await query.answer("Восстановление...")
        await resume_peer(uuid_val)
        # Сбрасываем таймер протухания по неиспользованию: иначе только что
        # размороженный «протухший» ключ (last_active_at 30+ дней назад) будет снова
        # вырублен inactivity_loop в течение суток. Реальный handshake обновит поле
        # заново в течение 5 мин, если клиент действительно подключится.
        await db.execute("UPDATE users SET is_active=TRUE, last_active_at=NOW() WHERE uuid=$1", uuid_val)
        await xray_sync("разморозка")
        await db.log_event("Resume", f"Manually resumed key {uuid_val}")
        await user_detail_menu(update, context, uuid_val)
        return
    if data.startswith("confirm_delete_"): await confirm_delete_menu(update, context, data.split("confirm_delete_")[1]); return
    if data.startswith("do_delete_"): await action_delete_user(update, context, data.split("do_delete_")[1]); return
    if data.startswith("act_resend_"): await action_resend_config(update, context, data.split("act_resend_")[1]); return
    if data == "close_graph": await return_to_main_menu(update, context); return

    actions = {
        "start_dashboard": start_dashboard, "stop_dashboard": return_to_main_menu,
        "confirm_reboot": confirm_reboot, "do_reboot_server": do_reboot_server,
        "gen_key": generate_key_request, "graph_traffic": send_vpn_graph,
        "show_online": online_users_menu, "backup": backup_now, 
        "download_logs": download_logs, "restore": restore_cmd, 
        "check_update": check_update, "do_update": do_update,
        "show_users": lambda u, c: users_list_menu(u, c, 0), "export_excel": export_excel,
        "run_bypass_check": run_bypass_check_handler, "bypass_notify_now": bypass_notify_now_handler
    }
    
    if data in actions: await actions[data](update, context)
    else: await query.answer("...")

async def setup_bot_ui(application):
    """Нативный UI Telegram: кнопка-меню ☰ + список slash-команд (раздельно для
    клиентов и админа)."""
    client_cmds = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("keys", "🔑 Мои ключи и конфиги"),
        BotCommand("status", "⚡️ Проверить соединение"),
        BotCommand("support", "🆘 Сообщить о проблеме"),
        BotCommand("help", "❓ Помощь"),
    ]
    try:
        await application.bot.set_my_commands(client_cmds, scope=BotCommandScopeDefault())
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        if ADMIN_ID:
            admin_cmds = [
                BotCommand("start", "🛡 Панель управления"),
                BotCommand("keys", "🔑 Мои ключи"),
                BotCommand("status", "⚡️ Проверить соединение"),
                BotCommand("help", "❓ Помощь"),
            ]
            await application.bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(ADMIN_ID))
    except Exception as e:
        print(f"setup_bot_ui error: {e}")

async def start_subscriptions():
    """Поднимает сервер подписок. Ошибка здесь не должна ронять бота: без
    подписок он работает как прежде, а вот без бота не работает ничего."""
    try:
        from subscription import start_server
        await start_server()
    except Exception as e:
        print(f"Подписки: сервер не поднялся: {e}")


async def wait_for_node(timeout=90):
    """Ждём, пока панель узла начнёт отвечать.

    Узел поднимается дольше бота: настраивает сеть, наполняет наборы адресов,
    поднимает интерфейс. Всё восстановление состояния — роли, фильтры, имена,
    конфиг Xray — идёт через его панель, и начинать его раньше бессмысленно:
    первый же запрос упадёт, а второй раз никто не попробует.

    Возвращает True, если дождались. Не дождались — работаем дальше: бот нужен
    владельцу и без узла, хотя бы чтобы узнать, что узел лёг.
    """
    from utils import WG_API_URL, api_session
    deadline = time.monotonic() + timeout
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            async with api_session() as session:
                async with session.get(f"{WG_API_URL}/health", timeout=3) as r:
                    if r.status == 200:
                        if attempt > 1:
                            print(f"Узел ответил с {attempt}-й попытки, "
                                  f"продолжаю восстановление состояния.")
                        return True
        except Exception:
            pass
        await asyncio.sleep(2)
    print("Узел не ответил за %d с — состояние восстановить не удалось. "
          "Роли, фильтры, имена и Xray останутся прежними до следующей "
          "попытки." % timeout)
    return False


async def post_init(application):
    state_data.setdefault("bg_tasks", set())
    # Момент запуска этой сборки. Нужен там, где надо отделить записанное
    # текущим кодом от записанного прежним, — например, разворачивая историю
    # трафика, которую старый сборщик писал зеркально.
    from datetime import datetime
    state_data.setdefault("bot_started_at", datetime.utcnow())

    await setup_bot_ui(application)

    # Сначала дожидаемся узла: всё, что ниже, ходит через его панель, и без
    # неё просто впустую отпечатает ошибки. Так и было — после каждого
    # обновления узел оставался без ролей, фильтров, имён и с прежним Xray.
    await wait_for_node()

    await sync_wg_config()

    # Чиним ключи, перевыпущенные до фикса бага (routing_version=0 при свежем конфиге)
    await reconcile_routing_versions()

    # Доступы внутри туннеля восстанавливаем при каждом старте: узел чистит таблицы
    # при перезапуске контейнера, а база — источник правды.
    try:
        ok, msg = await apply_access_rules("старт бота")
        if not ok:
            print(f"Роли: {msg}")
    except Exception as e:
        print(f"Роли: не удалось применить доступы: {e}")

    # Пароль архива: напоминаем сразу при запуске, не дожидаясь, пока владелец
    # сам откроет меню. Архив уносит ключ сервера и конфиги всех людей — молчать
    # о том, что он лежит открытым, нельзя.
    try:
        from handlers_admin import backup_password_gate

        class _StartCtx:
            bot = application.bot

        await backup_password_gate(_StartCtx, ADMIN_ID)
    except Exception as e:
        print(f"Пароль архива: не удалось напомнить: {e}")


    # Своё имя в Telegram бот узнаёт только у самого Telegram — запоминаем его
    # для страницы отказа, где человеку нужна ссылка «спросить владельца».
    try:
        from filters import remember_bot_link
        me = await application.bot.get_me()
        remember_bot_link(me.username)
    except Exception as e:
        print(f"Фильтры: не удалось узнать имя бота: {e}")

    # Фильтры — по той же причине: заворот 53-го порта живёт в правилах,
    # а правила чистятся при перезапуске контейнера узла.
    try:
        ok, msg = await apply_filters("старт бота")
        if not ok:
            print(f"Фильтры: {msg}")
    except Exception as e:
        print(f"Фильтры: не удалось применить: {e}")

    # Xray — по той же причине, что фильтры и роли: контейнер узла при
    # перезапуске теряет и адреса людей, и правила учёта. Пока конфиг не
    # применён заново, человек на Xray просто не выйдет в сеть.
    try:
        import xray
        state = await xray.status()
        if state.get("xray", {}).get("enabled"):
            ok, msg = await xray.apply_config("старт бота")
            print(f"Xray: {msg}" if ok else f"Xray: {msg}")
    except Exception as e:
        print(f"Xray: не удалось применить конфиг при старте: {e}")
    # Имена: адреса людей могли смениться, пока бот лежал, — раскладку стоит
    # пересобрать при старте, как это делается с ролями и фильтрами.
    try:
        from dnsnames import apply_names, ensure_node_name
        # Служебное имя заводим при старте: с ним у владельца сразу есть
        # рабочий пример, а страница отказа перестаёт быть адресом с цифрами.
        await ensure_node_name()
        if await db.count_dns_names():
            ok, msg = await apply_names("старт бота")
            print(f"Имена: {msg}")
    except Exception as e:
        print(f"Имена: не удалось применить при старте: {e}")

    tasks =[
        asyncio.create_task(alert_loop(application)),
        asyncio.create_task(cleanup_peers()),
        asyncio.create_task(stats_collector_loop()),
        asyncio.create_task(watch_online_count(application)),
        asyncio.create_task(check_update_completion(application)),
        asyncio.create_task(self_healing_loop(application)),
        asyncio.create_task(de_self_healing_loop(application)),
        asyncio.create_task(expiration_loop(application)),
        asyncio.create_task(inactivity_loop(application)),
        asyncio.create_task(weekly_report_loop(application)),
        asyncio.create_task(log_cleanup_loop(application)),
        asyncio.create_task(auto_backup_loop(application)),
        asyncio.create_task(auto_reboot_loop(application)),
        asyncio.create_task(scheduled_update_loop(application)),
        asyncio.create_task(auto_update_check_loop(application)),
        asyncio.create_task(resource_monitor_loop(application)),
        asyncio.create_task(routing_upgrade_loop(application)),
        asyncio.create_task(bypass_reresolve_loop(application)),
        asyncio.create_task(midnight_alert_cleanup_loop(application)),
        asyncio.create_task(load_collector_loop(application)),
        asyncio.create_task(retire_watch_loop(application)),
        asyncio.create_task(migration_watch_loop(application)),
        # Недельный разбор обслуживания: что убралось, что разошлось с базой,
        # и чем это отличается от прошлой недели. Воскресенье 07:00 МСК —
        # после планового ребута и уборки на обеих нодах.
        asyncio.create_task(weekly_health_loop(application)),
        # Раздача подписок Xray: клиенты сами перечитывают профиль, поэтому
        # сервер должен подняться до того, как кто-то попытается обновиться.
        asyncio.create_task(start_subscriptions()),
        # токен панелей выдаётся сам, если его нет — вводить ничего не нужно
        asyncio.create_task(ensure_api_token(application)),
        # Попытки на закрытое забираем с узла и складываем как заявки.
        asyncio.create_task(hits_loop(application)),
        # И дальше раз в час: клиент-сервер мог подняться позже мастера, и
        # догонять его иначе было бы нечем.
        asyncio.create_task(watch_api_token(application)),
        # Смена токена по расписанию — если владелец её включил.
        asyncio.create_task(rotate_loop(application)),
    ]
    state_data["bg_tasks"].update(tasks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.connect())
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    # Нативные slash-команды (регистрируем ДО общего обработчика команд)
    app.add_handler(CommandHandler("keys", cmd_keys))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("support", cmd_support))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, restore_file_handler))
    app.add_handler(MessageHandler(~filters.COMMAND & ~filters.Document.ALL, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(CallbackQueryHandler(button_router))
    
    print("Бот успешно запущен (Dual Node System Enabled)...")
    app.run_polling()
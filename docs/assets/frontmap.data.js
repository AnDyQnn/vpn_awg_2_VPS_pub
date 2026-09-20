// Собрано из исходников: python docs/assets/build_frontmap.py
// Руками не править — перезапишется. Правки делаются в самом боте.
window.FRONTMAP = {
 "names": {},
 "generated": true,
 "screens": [
  {
   "id": "menu",
   "file": "billing.py",
   "line": 104,
   "title": "Список сервисов и ближайшие платежи.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "sum",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "float",
    "money",
    "due_text",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "money",
    "period_name",
    "money",
    "amount",
    "money",
    "amount"
   ],
   "buttons": [
    {
     "label": "➕ Добавить сервис",
     "data": "bill_add",
     "line": 130,
     "dynamic": false,
     "to": "add_request",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 135,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 132,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "open_service",
   "file": "billing.py",
   "line": 141,
   "title": "Один сервис: всё про него и что с ним можно сделать.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "menu",
    "escape_md",
    "money",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "period_name",
    "money",
    "InlineKeyboardMarkup",
    "amount"
   ],
   "buttons": [
    {
     "label": "✅ Оплатил — сдвинуть срок",
     "data": "«меняется»",
     "line": 168,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "✏️ Цена",
     "data": "«меняется»",
     "line": 170,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "✏️ Срок",
     "data": "«меняется»",
     "line": 171,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "✏️ Период",
     "data": "«меняется»",
     "line": 172,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "✏️ Ссылка",
     "data": "«меняется»",
     "line": 173,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "⏸ Отключить / ▶️ Включить",
     "data": "«меняется»",
     "line": 174,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🗑 Удалить",
     "data": "«меняется»",
     "line": 176,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🔙 Счета",
     "data": "bill_menu",
     "line": 177,
     "dynamic": false,
     "to": "menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "add_request",
   "file": "billing.py",
   "line": 184,
   "title": "Заводим сервис одной строкой: так быстрее, чем пять вопросов подряд.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "bill_menu",
     "line": 195,
     "dynamic": false,
     "to": "menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "mark_paid",
   "file": "billing.py",
   "line": 245,
   "title": "Сдвигает срок на период вперёд.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "next_due",
    "open_service",
    "menu"
   ],
   "buttons": [
    {
     "label": "✅ Оплатил — сдвинуть срок",
     "data": "«меняется»",
     "line": 168,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "open_service"
    },
    {
     "label": "✏️ Цена",
     "data": "«меняется»",
     "line": 170,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "open_service"
    },
    {
     "label": "✏️ Срок",
     "data": "«меняется»",
     "line": 171,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "open_service"
    },
    {
     "label": "✏️ Период",
     "data": "«меняется»",
     "line": 172,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "open_service"
    },
    {
     "label": "✏️ Ссылка",
     "data": "«меняется»",
     "line": 173,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "open_service"
    },
    {
     "label": "⏸ Отключить / ▶️ Включить",
     "data": "«меняется»",
     "line": 174,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "open_service"
    },
    {
     "label": "🗑 Удалить",
     "data": "«меняется»",
     "line": 176,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "open_service"
    },
    {
     "label": "🔙 Счета",
     "data": "bill_menu",
     "line": 177,
     "dynamic": false,
     "to": "menu",
     "how": "точно",
     "inherited": "open_service"
    }
   ]
  },
  {
   "id": "check_and_notify",
   "file": "billing.py",
   "line": 275,
   "title": "Один проход. Возвращает, о скольких сервисах напомнили.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "len",
    "due_text",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "💳 Счета",
     "data": "bill_menu",
     "line": 293,
     "dynamic": false,
     "to": "menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "notify_users_whats_new",
   "file": "bot.py",
   "line": 230,
   "title": "Рассылает каждому только накопившееся лично для него.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "get_current_version",
    "print",
    "user_text",
    "print",
    "print",
    "fit",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "❤️ Поддержать проект",
     "data": "client_donate",
     "line": 264,
     "dynamic": false,
     "to": "client_donate",
     "how": "точно"
    }
   ]
  },
  {
   "id": "handle_message",
   "file": "bot.py",
   "line": 439,
   "title": "",
   "side": "client",
   "kind": "router",
   "calls": [
    "request_env_change",
    "request_env_change",
    "isinstance",
    "check_admin",
    "safe_delete",
    "sanitize_name",
    "sanitize_name",
    "drop_screen",
    "check_admin",
    "handle_role_text",
    "check_admin",
    "hit_find_entered",
    "check_admin",
    "handler",
    "check_admin",
    "flt_allow_entered",
    "check_admin",
    "handle_route_input",
    "check_admin",
    "handle_donate_input",
    "safe_delete",
    "len",
    "env_change_applied",
    "safe_delete",
    "env_change_applied",
    "InlineKeyboardMarkup",
    "safe_delete",
    "safe_delete",
    "safe_delete",
    "safe_delete",
    "client_menu",
    "InlineKeyboardMarkup",
    "client_menu",
    "_filter_bypass_cidrs",
    "flt_centered",
    "dnm_name_entered",
    "dnm_ip_entered",
    "dnm_rename_entered",
    "return_to_main_menu",
    "broadcast_message",
    "client_menu",
    "render_user_detail",
    "InlineKeyboardButton",
    "broadcast_message",
    "int",
    "default_proto",
    "new_key_screen",
    "extract_tg_id",
    "str",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "int",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "int",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "isinstance",
    "finish_key_creation",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "render_user_detail",
    "send_client_menu",
    "float",
    "escape_md",
    "len",
    "escape_md",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "escape_md",
    "escape_md",
    "escape_md",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "escape_md",
    "str",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🌐 К списку исключений",
     "data": "bypass_list",
     "line": 850,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "🌐 К списку исключений",
     "data": "bypass_list",
     "line": 832,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "🌐 К списку исключений",
     "data": "bypass_list",
     "line": 840,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 869,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 К списку обращений",
     "data": "support_admin_menu",
     "line": 904,
     "dynamic": false,
     "to": "support_admin_menu",
     "how": "точно"
    },
    {
     "label": "⏩ Пропустить/Отмена",
     "data": "skip_tg_link",
     "line": 947,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    },
    {
     "label": "🔑 Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 571,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Домен и сертификаты",
     "data": "psub_menu",
     "line": 573,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "✅ Добавить в исключения",
     "data": "bypass_addreq_…",
     "line": 779,
     "dynamic": false,
     "to": "bypass_add_request_handler",
     "how": "по приставке «bypass_addreq_»"
    },
    {
     "label": "❌ Отклонить",
     "data": "bypass_rejreq_…",
     "line": 780,
     "dynamic": false,
     "to": "bypass_add_request_handler",
     "how": "по приставке «bypass_rejreq_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 881,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔑 К сертификату внутренних имён",
     "data": "psub_zone",
     "line": 632,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    },
    {
     "label": "💳 Счета",
     "data": "bill_menu",
     "line": 661,
     "dynamic": false,
     "to": "menu",
     "how": "точно"
    },
    {
     "label": "💳 К сервису",
     "data": "«меняется»",
     "line": 697,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🔙 В меню",
     "data": "back_to_main",
     "line": 716,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "button_router",
   "file": "bot.py",
   "line": 984,
   "title": "",
   "side": "admin",
   "kind": "router",
   "calls": [
    "deregister_menu",
    "check_admin",
    "int",
    "stop_bg_tasks",
    "sub_menu_router",
    "support_start_handler",
    "support_run_audit_handler",
    "support_ask_msg_handler",
    "client_menu",
    "client_my_keys_handler",
    "client_key_manage_handler",
    "client_regen_all_confirm_handler",
    "client_regen_all_action_handler",
    "client_select_check_menu",
    "client_check_all_handler",
    "check_connection_handler",
    "client_stats_handler",
    "client_bypass_info_handler",
    "client_report_site_handler",
    "client_apps_handler",
    "client_donate",
    "client_donate_qr",
    "client_whats_new",
    "client_notify_toggle_handler",
    "client_notify_off_handler",
    "client_download_handler",
    "client_platform_handler",
    "client_how_handler",
    "client_regen_confirm",
    "client_regen_action",
    "run_audit_handler",
    "service_menu",
    "toggle_mode",
    "set_mode",
    "set_mode",
    "backups_list_screen",
    "token_screen",
    "token_toggle",
    "token_now",
    "token_rollback",
    "load_screen",
    "event_delete",
    "load_chart",
    "graphs_menu",
    "charts_screen",
    "pick_peer_screen",
    "whats_new",
    "load_chart",
    "limits_screen",
    "peer_limit_screen",
    "change_limit",
    "change_limit",
    "change_limit",
    "set_peer_rule",
    "ask_backup_password",
    "pending_screen",
    "delivery_screen",
    "migration_menu",
    "migration_start",
    "migration_de",
    "migration_issue",
    "migration_send",
    "migration_finish_confirm",
    "migration_finish",
    "migration_abort_confirm",
    "migration_abort",
    "protocols_menu",
    "awg_screen",
    "xray_screen",
    "switch_do",
    "switch_do",
    "switch_do",
    "switch_do",
    "switch_confirm",
    "xray_apply_now",
    "apps_screen",
    "mask_screen",
    "mask_set",
    "move_screen",
    "routes_menu",
    "routes_show",
    "routes_ask",
    "routes_ask",
    "routes_delete",
    "connections_screen",
    "issue_xray",
    "send_link",
    "drop_awg",
    "why_locked",
    "donate_menu",
    "donate_toggle",
    "donate_reminder_toggle",
    "donate_preview",
    "donate_period",
    "donate_ask",
    "donate_period_set",
    "donate_ask",
    "donate_ask",
    "donate_open",
    "donate_delete",
    "names_menu",
    "dnm_add",
    "dnm_apply",
    "dnm_manual",
    "dnm_page",
    "dnm_person",
    "dnm_open",
    "dnm_rename",
    "dnm_retarget",
    "dnm_delete",
    "hits_screen",
    "hits_seen_all",
    "hits_drop_seen",
    "hit_find_request",
    "hits_notify_screen",
    "hits_notify_toggle",
    "hits_notify_set",
    "hits_keep_screen",
    "hits_keep_now",
    "hits_keep_set",
    "hits_keep_set",
    "hits_screen",
    "hit_open",
    "filters_menu",
    "flt_common",
    "flt_cadd",
    "flt_clist",
    "flt_ctoggle",
    "flt_cremove",
    "flt_clist",
    "filters_apply_now",
    "flt_pools",
    "flt_pool_new",
    "flt_pool_open",
    "flt_pool_add",
    "flt_pool_del",
    "flt_allow",
    "flt_allow_add",
    "flt_allow_add",
    "flt_allow_del",
    "flt_allow",
    "filters_pick_user",
    "user_filters_screen",
    "toggle_exempt",
    "toggle_filter",
    "decision_screen",
    "extend_menu",
    "do_extend",
    "set_policy",
    "do_delete",
    "delete_confirm",
    "roles_menu",
    "user_role_toggle",
    "user_roles_screen",
    "role_new",
    "new_key_role_screen",
    "new_key_screen",
    "new_key_role_set",
    "default_role_screen",
    "default_role_set",
    "role_apply",
    "role_screen",
    "grant_add_screen",
    "grant_manual",
    "grant_whole_tunnel",
    "grant_name",
    "grant_peer",
    "grant_del",
    "members_screen",
    "member_add",
    "member_del",
    "role_delete",
    "role_delete_confirm",
    "return_to_main_menu",
    "toggle_auto_update",
    "schedule_update_menu",
    "de_confirm_reboot",
    "do_de_reboot_server",
    "de_read_logs",
    "de_read_logs",
    "de_update",
    "update_all",
    "de_backup",
    "de_run_audit",
    "broadcast_message",
    "bypass_list_handler",
    "bypass_happ_handler",
    "bypass_add_manual_handler",
    "bypass_del_handler",
    "bypass_add_request_handler",
    "bypass_add_request_handler",
    "support_admin_menu",
    "support_user_tickets",
    "support_ticket_detail",
    "support_reply_start",
    "support_close_ticket",
    "new_key_screen",
    "users_list_menu",
    "user_detail_menu",
    "clear_user_ips",
    "user_detail_menu",
    "pause_peer",
    "xray_sync",
    "user_detail_menu",
    "resume_peer",
    "xray_sync",
    "user_detail_menu",
    "confirm_delete_menu",
    "action_delete_user",
    "action_resend_config",
    "return_to_main_menu",
    "users_list_menu",
    "show_screen",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "int",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "finish_key_creation",
    "user_detail_menu",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "int",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "int",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "len",
    "InlineKeyboardMarkup",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✍️ Своя рассылка (свой текст)",
     "data": "broadcast_custom",
     "line": 1401,
     "dynamic": false,
     "to": "шаг: broadcast_custom",
     "how": "точно"
    },
    {
     "label": "⚠️ Стандартное: тех. работы",
     "data": "do_maintenance_warn",
     "line": 1402,
     "dynamic": false,
     "to": "broadcast_message",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1403,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "⏩ Пропустить",
     "data": "skip_tg_link",
     "line": 1463,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    },
    {
     "label": "⏩ Пропустить",
     "data": "skip_tg_link",
     "line": 1472,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1483,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1495,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "❌ …",
     "data": "do_unlink_…_…",
     "line": 1504,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «do_unlink_»"
    },
    {
     "label": "🔙 Назад",
     "data": "user_detail_…",
     "line": 1505,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🌍 Классический DNS (1.1.1.1)",
     "data": "set_dns_classic",
     "line": 1457,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🛡 AdBlock DNS (Без рекламы)",
     "data": "set_dns_adblock",
     "line": 1457,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1457,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1414,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 В меню",
     "data": "back_to_main",
     "line": 1420,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "«меняется»",
     "line": 1112,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "screen",
   "file": "chat_cleanup.py",
   "line": 180,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "len",
    "enabled",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "int",
    "InlineKeyboardMarkup",
    "chr"
   ],
   "buttons": [
    {
     "label": "🧹 Убрать сейчас",
     "data": "chat_clean_now",
     "line": 207,
     "dynamic": false,
     "to": "clean_now",
     "how": "точно"
    },
    {
     "label": "🔕 Выключить / 🔔 Включить",
     "data": "chat_clean_toggle",
     "line": 208,
     "dynamic": false,
     "to": "toggle",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 210,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "clean_now",
   "file": "chat_cleanup.py",
   "line": 216,
   "title": "Убрать, не дожидаясь начала суток.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "screen",
    "sweep"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 192,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "1️⃣ Вписать имя узла",
     "data": "psub_domain",
     "line": 169,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "«меняется»",
     "data": "psub_domain",
     "line": 172,
     "dynamic": true,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔄 Обновить сертификат",
     "data": "psub_renew",
     "line": 184,
     "dynamic": false,
     "to": "renew_now",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔒 Закрыть доступ снаружи",
     "data": "psub_off",
     "line": 186,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🌐 Открыть доступ снаружи",
     "data": "psub_on",
     "line": 189,
     "dynamic": false,
     "to": "turn_on",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔑 Сертификат внутренних имён · есть",
     "data": "psub_zone",
     "line": 175,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "2️⃣ Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 179,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно",
     "inherited": "screen"
    }
   ]
  },
  {
   "id": "toggle",
   "file": "chat_cleanup.py",
   "line": 230,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "enabled",
    "screen"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 192,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "1️⃣ Вписать имя узла",
     "data": "psub_domain",
     "line": 169,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "«меняется»",
     "data": "psub_domain",
     "line": 172,
     "dynamic": true,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔄 Обновить сертификат",
     "data": "psub_renew",
     "line": 184,
     "dynamic": false,
     "to": "renew_now",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔒 Закрыть доступ снаружи",
     "data": "psub_off",
     "line": 186,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🌐 Открыть доступ снаружи",
     "data": "psub_on",
     "line": 189,
     "dynamic": false,
     "to": "turn_on",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔑 Сертификат внутренних имён · есть",
     "data": "psub_zone",
     "line": 175,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "2️⃣ Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 179,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно",
     "inherited": "screen"
    }
   ]
  },
  {
   "id": "delivery_screen",
   "file": "delivery.py",
   "line": 65,
   "title": "«Доставка ключей» — только те, у кого дело не дошло до подключения.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "show_screen",
    "stage",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 74,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 89,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "… …",
     "data": "user_detail_…",
     "line": 84,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "filters_menu",
   "file": "filters.py",
   "line": 213,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "set",
    "sorted",
    "list_sizes",
    "titles",
    "show_screen",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "🌍 Общие правила",
     "data": "flt_common",
     "line": 276,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно"
    },
    {
     "label": "🟢 Исключения из запретов",
     "data": "flt_alw_all",
     "line": 277,
     "dynamic": false,
     "to": "allow_screen",
     "how": "точно"
    },
    {
     "label": "📦 Группы фильтров",
     "data": "flt_pool_list",
     "line": 279,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    },
    {
     "label": "👤 Выбрать человека",
     "data": "flt_pick_0",
     "line": 280,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 283,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🔄 Применить на узле",
     "data": "flt_apply",
     "line": 282,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно"
    }
   ]
  },
  {
   "id": "allow_screen",
   "file": "filters.py",
   "line": 296,
   "title": "Список исключений: общих или одного ключа.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "escape_md",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "➕ Разрешить сайт",
     "data": "«меняется»",
     "line": 326,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 331,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🗑 …",
     "data": "flt_alw_del_…_…",
     "line": 328,
     "dynamic": false,
     "to": "allow_remove",
     "how": "по приставке «flt_alw_del_»"
    }
   ]
  },
  {
   "id": "allow_add_request",
   "file": "filters.py",
   "line": 338,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "flt_alw_… / flt_alw_all",
     "line": 352,
     "dynamic": false,
     "to": "allow_screen",
     "how": "по приставке «flt_alw_»"
    }
   ]
  },
  {
   "id": "allow_add_entered",
   "file": "filters.py",
   "line": 358,
   "title": "Разбирает присланное. Возвращает True, если сообщение было для нас.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "apply_filters",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🟢 К исключениям",
     "data": "«меняется»",
     "line": 380,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "allow_remove",
   "file": "filters.py",
   "line": 398,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_filters",
    "allow_screen"
   ],
   "buttons": [
    {
     "label": "➕ Разрешить сайт",
     "data": "«меняется»",
     "line": 326,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "allow_screen"
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 331,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "allow_screen"
    },
    {
     "label": "🗑 …",
     "data": "flt_alw_del_…_…",
     "line": 328,
     "dynamic": false,
     "to": "allow_remove",
     "how": "по приставке «flt_alw_del_»",
     "inherited": "allow_screen"
    }
   ]
  },
  {
   "id": "pool_list",
   "file": "filters.py",
   "line": 421,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "len"
   ],
   "buttons": [
    {
     "label": "➕ Добавить группу",
     "data": "flt_pool_new",
     "line": 441,
     "dynamic": false,
     "to": "pool_name_request",
     "how": "точно"
    },
    {
     "label": "🔙 К фильтрам",
     "data": "flt_menu",
     "line": 445,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "📦 …",
     "data": "flt_pool_o_…",
     "line": 443,
     "dynamic": false,
     "to": "pool_open",
     "how": "по приставке «flt_pool_o_»"
    }
   ]
  },
  {
   "id": "pool_open",
   "file": "filters.py",
   "line": 452,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "len",
    "len",
    "show_screen",
    "pool_list",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "len",
    "escape_md",
    "InlineKeyboardMarkup",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "➕ Добавить адреса",
     "data": "flt_pool_a_…",
     "line": 467,
     "dynamic": false,
     "to": "pool_add_request",
     "how": "по приставке «flt_pool_a_»"
    },
    {
     "label": "🗑 Удалить группу",
     "data": "flt_pool_d_…",
     "line": 469,
     "dynamic": false,
     "to": "pool_delete",
     "how": "по приставке «flt_pool_d_»"
    },
    {
     "label": "🔙 К группам",
     "data": "flt_pool_list",
     "line": 470,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pool_add_request",
   "file": "filters.py",
   "line": 490,
   "title": "Спрашивает адреса. Для новой группы это второй шаг: имя уже дали.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "escape_md",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "«меняется»",
     "line": 508,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "pool_name_request",
   "file": "filters.py",
   "line": 512,
   "title": "Первый шаг новой группы — название.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "flt_pool_list",
     "line": 529,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pool_domains_entered",
   "file": "filters.py",
   "line": 573,
   "title": "Принял список адресов в уже созданную группу.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_parse_domains",
    "sorted",
    "apply_filters",
    "set",
    "set",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "len",
    "InlineKeyboardButton",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "📦 К группам",
     "data": "flt_pool_list",
     "line": 614,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    },
    {
     "label": "🔙 К группам",
     "data": "flt_pool_list",
     "line": 584,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    },
    {
     "label": "📦 К группе",
     "data": "flt_pool_o_…",
     "line": 603,
     "dynamic": false,
     "to": "pool_open",
     "how": "по приставке «flt_pool_o_»"
    }
   ]
  },
  {
   "id": "pool_title_entered",
   "file": "filters.py",
   "line": 618,
   "title": "Имя получено — группа заведена, осталось наполнить.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_pool_key",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "chr",
    "chr",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "✖️ Позже",
     "data": "«меняется»",
     "line": 645,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "📦 К группам",
     "data": "flt_pool_list",
     "line": 632,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pool_delete",
   "file": "filters.py",
   "line": 650,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_filters",
    "pool_list"
   ],
   "buttons": [
    {
     "label": "➕ Добавить группу",
     "data": "flt_pool_new",
     "line": 441,
     "dynamic": false,
     "to": "pool_name_request",
     "how": "точно",
     "inherited": "pool_list"
    },
    {
     "label": "🔙 К фильтрам",
     "data": "flt_menu",
     "line": 445,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно",
     "inherited": "pool_list"
    },
    {
     "label": "📦 …",
     "data": "flt_pool_o_…",
     "line": 443,
     "dynamic": false,
     "to": "pool_open",
     "how": "по приставке «flt_pool_o_»",
     "inherited": "pool_list"
    }
   ]
  },
  {
   "id": "pick_user",
   "file": "filters.py",
   "line": 658,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "max",
    "max",
    "min",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len"
   ],
   "buttons": [
    {
     "label": "…/…",
     "data": "svc_noop",
     "line": 676,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "🔙 Фильтры",
     "data": "flt_menu",
     "line": 680,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "……",
     "data": "flt_user_…",
     "line": 670,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    },
    {
     "label": "⬅️",
     "data": "flt_pick_…",
     "line": 675,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    },
    {
     "label": "➡️",
     "data": "flt_pick_…",
     "line": 678,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    }
   ]
  },
  {
   "id": "user_filters_screen",
   "file": "filters.py",
   "line": 688,
   "title": "Категории одного человека.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "set",
    "set",
    "set",
    "all_categories",
    "show_screen",
    "filters_menu",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len",
    "len",
    "chr"
   ],
   "buttons": [
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 740,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🟢 Исключения из запретов",
     "data": "flt_alw_…",
     "line": 744,
     "dynamic": false,
     "to": "allow_screen",
     "how": "по приставке «flt_alw_»"
    },
    {
     "label": "🧹 К списку фильтров",
     "data": "flt_pick_0",
     "line": 746,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 738,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "toggle_exempt",
   "file": "filters.py",
   "line": 753,
   "title": "Снимает с человека общую категорию или возвращает её.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "set",
    "dict",
    "apply_filters",
    "user_filters_screen",
    "all_categories"
   ],
   "buttons": [
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 740,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "🟢 Исключения из запретов",
     "data": "flt_alw_…",
     "line": 744,
     "dynamic": false,
     "to": "allow_screen",
     "how": "по приставке «flt_alw_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "🧹 К списку фильтров",
     "data": "flt_pick_0",
     "line": 746,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 738,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "user_filters_screen"
    }
   ]
  },
  {
   "id": "toggle_filter",
   "file": "filters.py",
   "line": 772,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "set",
    "apply_filters",
    "user_filters_screen"
   ],
   "buttons": [
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 740,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "🟢 Исключения из запретов",
     "data": "flt_alw_…",
     "line": 744,
     "dynamic": false,
     "to": "allow_screen",
     "how": "по приставке «flt_alw_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "🧹 К списку фильтров",
     "data": "flt_pick_0",
     "line": 746,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 738,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "user_filters_screen"
    }
   ]
  },
  {
   "id": "apply_now",
   "file": "filters.py",
   "line": 781,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_filters",
    "filters_menu"
   ],
   "buttons": [
    {
     "label": "🌍 Общие правила",
     "data": "flt_common",
     "line": 276,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно",
     "inherited": "filters_menu"
    },
    {
     "label": "🟢 Исключения из запретов",
     "data": "flt_alw_all",
     "line": 277,
     "dynamic": false,
     "to": "allow_screen",
     "how": "точно",
     "inherited": "filters_menu"
    },
    {
     "label": "📦 Группы фильтров",
     "data": "flt_pool_list",
     "line": 279,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно",
     "inherited": "filters_menu"
    },
    {
     "label": "👤 Выбрать человека",
     "data": "flt_pick_0",
     "line": 280,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»",
     "inherited": "filters_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 283,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "filters_menu"
    },
    {
     "label": "🔄 Применить на узле",
     "data": "flt_apply",
     "line": 282,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно",
     "inherited": "filters_menu"
    }
   ]
  },
  {
   "id": "common_screen",
   "file": "filters.py",
   "line": 788,
   "title": "Правила, действующие сразу на всех.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "all_categories",
    "show_screen",
    "titles",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "➕ Закрыть сайт",
     "data": "flt_cadd",
     "line": 820,
     "dynamic": false,
     "to": "custom_add_request",
     "how": "точно"
    },
    {
     "label": "🔙 Фильтры",
     "data": "flt_menu",
     "line": 824,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "flt_ctog_…",
     "line": 818,
     "dynamic": true,
     "to": "common_toggle",
     "how": "по приставке «flt_ctog_»"
    },
    {
     "label": "🚫 Свой список запретов",
     "data": "flt_clist",
     "line": 822,
     "dynamic": false,
     "to": "custom_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "common_toggle",
   "file": "filters.py",
   "line": 831,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "set",
    "apply_filters",
    "common_screen"
   ],
   "buttons": [
    {
     "label": "➕ Закрыть сайт",
     "data": "flt_cadd",
     "line": 820,
     "dynamic": false,
     "to": "custom_add_request",
     "how": "точно",
     "inherited": "common_screen"
    },
    {
     "label": "🔙 Фильтры",
     "data": "flt_menu",
     "line": 824,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно",
     "inherited": "common_screen"
    },
    {
     "label": "«меняется»",
     "data": "flt_ctog_…",
     "line": 818,
     "dynamic": true,
     "to": "common_toggle",
     "how": "по приставке «flt_ctog_»",
     "inherited": "common_screen"
    },
    {
     "label": "🚫 Свой список запретов",
     "data": "flt_clist",
     "line": 822,
     "dynamic": false,
     "to": "custom_list",
     "how": "точно",
     "inherited": "common_screen"
    }
   ]
  },
  {
   "id": "custom_add_request",
   "file": "filters.py",
   "line": 841,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Общие правила",
     "data": "flt_common",
     "line": 849,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "custom_add_entered",
   "file": "filters.py",
   "line": 854,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "parse_site",
    "apply_filters",
    "InlineKeyboardMarkup",
    "exit_kb",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Общие правила",
     "data": "flt_common",
     "line": 869,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "custom_list",
   "file": "filters.py",
   "line": 873,
   "title": "Свой список с кнопками снятия: закрыть сайт легко, снять — тоже.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "len",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "len",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🗑 …",
     "data": "flt_cdel_…",
     "line": 882,
     "dynamic": false,
     "to": "custom_remove",
     "how": "по приставке «flt_cdel_»"
    },
    {
     "label": "←",
     "data": "flt_cpg_…",
     "line": 886,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»"
    },
    {
     "label": "→",
     "data": "flt_cpg_…",
     "line": 888,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»"
    },
    {
     "label": "🔙 Общие правила",
     "data": "flt_common",
     "line": 891,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "custom_remove",
   "file": "filters.py",
   "line": 898,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_filters",
    "custom_list"
   ],
   "buttons": [
    {
     "label": "🗑 …",
     "data": "flt_cdel_…",
     "line": 882,
     "dynamic": false,
     "to": "custom_remove",
     "how": "по приставке «flt_cdel_»",
     "inherited": "custom_list"
    },
    {
     "label": "←",
     "data": "flt_cpg_…",
     "line": 886,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»",
     "inherited": "custom_list"
    },
    {
     "label": "→",
     "data": "flt_cpg_…",
     "line": 888,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»",
     "inherited": "custom_list"
    },
    {
     "label": "🔙 Общие правила",
     "data": "flt_common",
     "line": 891,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно",
     "inherited": "custom_list"
    }
   ]
  },
  {
   "id": "backup_password_gate",
   "file": "handlers_admin.py",
   "line": 26,
   "title": "Показывает блокирующий экран, если пароль архива не задан.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 Задать пароль",
     "data": "set_backup_pw",
     "line": 45,
     "dynamic": false,
     "to": "ask_backup_password",
     "how": "точно"
    }
   ]
  },
  {
   "id": "ask_backup_password",
   "file": "handlers_admin.py",
   "line": 59,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [],
   "buttons": []
  },
  {
   "id": "return_to_main_menu",
   "file": "handlers_admin.py",
   "line": 162,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "stop_bg_tasks",
    "backup_password_gate",
    "main_menu_view",
    "str",
    "safe_delete"
   ],
   "buttons": [
    {
     "label": "🔑 Задать пароль",
     "data": "set_backup_pw",
     "line": 45,
     "dynamic": false,
     "to": "ask_backup_password",
     "how": "точно",
     "inherited": "backup_password_gate"
    }
   ]
  },
  {
   "id": "backups_list_screen",
   "file": "handlers_admin.py",
   "line": 193,
   "title": "Что за копии лежат на сервере: когда, целые ли, зашифрованы ли.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "sum",
    "show_screen",
    "print",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len",
    "dt_to_moscow",
    "escape_md",
    "escape_md",
    "len"
   ],
   "buttons": [
    {
     "label": "💾 Сделать копию сейчас",
     "data": "backup",
     "line": 235,
     "dynamic": false,
     "to": "backup_now",
     "how": "точно"
    },
    {
     "label": "🔙 Архивы и база",
     "data": "menu_backups",
     "line": 236,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    }
   ]
  },
  {
   "id": "dashboard_loop",
   "file": "handlers_admin.py",
   "line": 282,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "get_dashboard",
    "InlineKeyboardButton",
    "str",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню · остановить",
     "data": "back_to_main",
     "line": 286,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "start_dashboard",
   "file": "handlers_admin.py",
   "line": 294,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "dashboard_loop"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню · остановить",
     "data": "back_to_main",
     "line": 286,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "dashboard_loop"
    }
   ]
  },
  {
   "id": "confirm_reboot",
   "file": "handlers_admin.py",
   "line": 307,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🚨 Да, перезагрузить",
     "data": "do_reboot_server",
     "line": 310,
     "dynamic": false,
     "to": "do_reboot_server",
     "how": "точно"
    },
    {
     "label": "🔙 Нет, отмена",
     "data": "back_to_main",
     "line": 310,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "do_reboot_server",
   "file": "handlers_admin.py",
   "line": 313,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "broadcast_message",
    "open",
    "open",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 321,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_confirm_reboot",
   "file": "handlers_admin.py",
   "line": 333,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🚨 Да, перезагрузить",
     "data": "do_de_reboot_server",
     "line": 336,
     "dynamic": false,
     "to": "do_de_reboot_server",
     "how": "точно"
    },
    {
     "label": "🔙 Нет, отмена",
     "data": "back_to_main",
     "line": 336,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "do_de_reboot_server",
   "file": "handlers_admin.py",
   "line": 339,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "api_session",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 350,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 345,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 348,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_read_logs",
   "file": "handlers_admin.py",
   "line": 371,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "api_session",
    "_useful_lines",
    "open",
    "safe_delete",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "open",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Клиент-сервер",
     "data": "menu_de_server",
     "line": 403,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    },
    {
     "label": "📄 Полный журнал",
     "data": "de_read_logs_full",
     "line": 401,
     "dynamic": false,
     "to": "de_read_logs",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 415,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 413,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_update",
   "file": "handlers_admin.py",
   "line": 456,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "_get_de_deploy_ts",
    "api_session",
    "_watch_de_update",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 472,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 466,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 470,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_backup",
   "file": "handlers_admin.py",
   "line": 474,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "api_session",
    "open",
    "safe_delete",
    "InlineKeyboardMarkup",
    "open",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 497,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 491,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 495,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_run_audit",
   "file": "handlers_admin.py",
   "line": 499,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "range",
    "stop_bg_tasks",
    "api_session",
    "api_session",
    "InlineKeyboardMarkup",
    "Exception",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "send_de_audit_report",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 534,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 513,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "send_de_audit_report",
   "file": "handlers_admin.py",
   "line": 536,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "open",
    "sum",
    "sum",
    "safe_delete",
    "open",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "get_moscow_now"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 576,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "graph_loop",
   "file": "handlers_admin.py",
   "line": 590,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "generate_vpn_graph",
    "open",
    "InputMediaPhoto",
    "InlineKeyboardButton",
    "str",
    "InlineKeyboardMarkup",
    "get_moscow_now"
   ],
   "buttons": [
    {
     "label": "🔙 Назад · остановить",
     "data": "back_to_main",
     "line": 596,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "send_vpn_graph",
   "file": "handlers_admin.py",
   "line": 604,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "safe_delete",
    "generate_vpn_graph",
    "graph_loop",
    "InlineKeyboardButton",
    "return_to_main_menu",
    "notify_admin",
    "open",
    "InlineKeyboardMarkup",
    "get_moscow_now"
   ],
   "buttons": [
    {
     "label": "🔙 Назад · остановить",
     "data": "back_to_main",
     "line": 613,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "online_users_menu",
   "file": "handlers_admin.py",
   "line": 622,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "int",
    "api_session",
    "int",
    "divmod",
    "divmod",
    "max",
    "InlineKeyboardMarkup",
    "safe_delete",
    "ts_to_moscow",
    "str",
    "escape_md",
    "_fmt_dur",
    "InlineKeyboardMarkup",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 661,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 665,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "check_update",
   "file": "handlers_admin.py",
   "line": 667,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "deregister_menu",
    "escape_md",
    "escape_md",
    "stop_bg_tasks",
    "str",
    "str",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "print",
    "InlineKeyboardMarkup",
    "str"
   ],
   "buttons": [
    {
     "label": "🇷🇺 Обновить RU",
     "data": "do_update",
     "line": 692,
     "dynamic": false,
     "to": "do_update",
     "how": "точно"
    },
    {
     "label": "🇷🇺 Переустановить RU",
     "data": "do_update",
     "line": 695,
     "dynamic": false,
     "to": "do_update",
     "how": "точно"
    },
    {
     "label": "🔄 Обновить всё (RU + DE)",
     "data": "update_all",
     "line": 703,
     "dynamic": false,
     "to": "update_all",
     "how": "точно"
    },
    {
     "label": "🇩🇪 Обновить DE",
     "data": "de_update",
     "line": 704,
     "dynamic": false,
     "to": "de_update",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "toggle_auto_update",
     "line": 705,
     "dynamic": true,
     "to": "toggle_auto_update",
     "how": "точно"
    },
    {
     "label": "📅 Запланировать обновление",
     "data": "schedule_update",
     "line": 706,
     "dynamic": false,
     "to": "schedule_update_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 707,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "toggle_auto_update",
   "file": "handlers_admin.py",
   "line": 720,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "check_update",
    "print"
   ],
   "buttons": [
    {
     "label": "🇷🇺 Обновить RU",
     "data": "do_update",
     "line": 692,
     "dynamic": false,
     "to": "do_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🇷🇺 Переустановить RU",
     "data": "do_update",
     "line": 695,
     "dynamic": false,
     "to": "do_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🔄 Обновить всё (RU + DE)",
     "data": "update_all",
     "line": 703,
     "dynamic": false,
     "to": "update_all",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🇩🇪 Обновить DE",
     "data": "de_update",
     "line": 704,
     "dynamic": false,
     "to": "de_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "«меняется»",
     "data": "toggle_auto_update",
     "line": 705,
     "dynamic": true,
     "to": "toggle_auto_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "📅 Запланировать обновление",
     "data": "schedule_update",
     "line": 706,
     "dynamic": false,
     "to": "schedule_update_menu",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 707,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "check_update"
    }
   ]
  },
  {
   "id": "schedule_update_menu",
   "file": "handlers_admin.py",
   "line": 732,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "stop_bg_tasks",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 735,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "do_update",
   "file": "handlers_admin.py",
   "line": 746,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "broadcast_message",
    "open",
    "update_persistent_backup",
    "isinstance"
   ],
   "buttons": [
    {
     "label": "🛡 Панель управления",
     "data": "back_to_main",
     "line": 501,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "broadcast_message"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 503,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно",
     "inherited": "broadcast_message"
    }
   ]
  },
  {
   "id": "update_all",
   "file": "handlers_admin.py",
   "line": 787,
   "title": "Обновить ОБЕ ноды разом: сначала DE (по туннелю через агентский API), затем RU",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_get_de_deploy_ts",
    "broadcast_message",
    "open",
    "api_session",
    "update_persistent_backup",
    "_watch_de_update"
   ],
   "buttons": [
    {
     "label": "🛡 Панель управления",
     "data": "back_to_main",
     "line": 501,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "broadcast_message"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 503,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно",
     "inherited": "broadcast_message"
    }
   ]
  },
  {
   "id": "support_admin_menu",
   "file": "handlers_admin.py",
   "line": 825,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 849,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "👤 … (… шт)",
     "data": "supp_usr_…",
     "line": 847,
     "dynamic": false,
     "to": "support_user_tickets",
     "how": "по приставке «supp_usr_»"
    }
   ]
  },
  {
   "id": "support_user_tickets",
   "file": "handlers_admin.py",
   "line": 852,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "escape_md",
    "InlineKeyboardButton",
    "len",
    "dt_to_moscow",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Назад к списку",
     "data": "support_admin_menu",
     "line": 866,
     "dynamic": false,
     "to": "support_admin_menu",
     "how": "точно"
    },
    {
     "label": "[…] …",
     "data": "supp_tkt_…",
     "line": 864,
     "dynamic": false,
     "to": "support_ticket_detail",
     "how": "по приставке «supp_tkt_»"
    }
   ]
  },
  {
   "id": "support_ticket_detail",
   "file": "handlers_admin.py",
   "line": 869,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "int",
    "support_admin_menu",
    "dt_to_moscow",
    "escape_md",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✍️ Ответить",
     "data": "supp_rep_…",
     "line": 884,
     "dynamic": false,
     "to": "support_reply_start",
     "how": "по приставке «supp_rep_»"
    },
    {
     "label": "✅ Закрыть без ответа",
     "data": "supp_clo_…",
     "line": 885,
     "dynamic": false,
     "to": "support_close_ticket",
     "how": "по приставке «supp_clo_»"
    },
    {
     "label": "🔙 К пользователю",
     "data": "supp_usr_…",
     "line": 886,
     "dynamic": false,
     "to": "support_user_tickets",
     "how": "по приставке «supp_usr_»"
    }
   ]
  },
  {
   "id": "support_reply_start",
   "file": "handlers_admin.py",
   "line": 890,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "supp_tkt_…",
     "line": 896,
     "dynamic": false,
     "to": "support_ticket_detail",
     "how": "по приставке «supp_tkt_»"
    }
   ]
  },
  {
   "id": "support_close_ticket",
   "file": "handlers_admin.py",
   "line": 899,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "support_admin_menu",
    "int"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 849,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "support_admin_menu"
    },
    {
     "label": "👤 … (… шт)",
     "data": "supp_usr_…",
     "line": 847,
     "dynamic": false,
     "to": "support_user_tickets",
     "how": "по приставке «supp_usr_»",
     "inherited": "support_admin_menu"
    }
   ]
  },
  {
   "id": "backup_now",
   "file": "handlers_admin.py",
   "line": 906,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "update_persistent_backup",
    "safe_delete"
   ],
   "buttons": []
  },
  {
   "id": "download_logs",
   "file": "handlers_admin.py",
   "line": 917,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "notify_admin",
    "open"
   ],
   "buttons": []
  },
  {
   "id": "restore_cmd",
   "file": "handlers_admin.py",
   "line": 926,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 929,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "restore_file_handler",
   "file": "handlers_admin.py",
   "line": 934,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "check_admin",
    "safe_delete",
    "restore_backup",
    "update_persistent_backup",
    "return_to_main_menu",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 970,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 952,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "export_excel",
   "file": "handlers_admin.py",
   "line": 973,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "notify_admin",
    "open"
   ],
   "buttons": []
  },
  {
   "id": "run_audit_handler",
   "file": "handlers_admin.py",
   "line": 980,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "range",
    "sum",
    "stop_bg_tasks",
    "open",
    "list",
    "enumerate",
    "open",
    "len",
    "sum",
    "sum",
    "sum",
    "len",
    "safe_delete",
    "open",
    "open",
    "len",
    "InlineKeyboardButton",
    "open",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "get_moscow_now"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 1111,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 1049,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 1058,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "sub_menu_router",
   "file": "handlers_admin.py",
   "line": 1121,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "menu_ru_server",
    "menu_de_server",
    "menu_backups"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить систему",
     "data": "check_update",
     "line": 30,
     "dynamic": false,
     "to": "check_update",
     "how": "точно",
     "inherited": "menu_ru_server"
    },
    {
     "label": "🔑 Панель токенов",
     "data": "svc_token",
     "line": 32,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно",
     "inherited": "menu_ru_server"
    },
    {
     "label": "🛠 Аудит мастера",
     "data": "run_audit",
     "line": 33,
     "dynamic": false,
     "to": "run_audit_handler",
     "how": "точно",
     "inherited": "menu_ru_server"
    },
    {
     "label": "🛡 Проверка исключений",
     "data": "run_bypass_check",
     "line": 34,
     "dynamic": false,
     "to": "run_bypass_check_handler",
     "how": "точно",
     "inherited": "menu_ru_server"
    },
    {
     "label": "🌐 Исключения · мимо VPN",
     "data": "bypass_list",
     "line": 35,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно",
     "inherited": "menu_ru_server"
    },
    {
     "label": "📢 Рассылка пользователям",
     "data": "maintenance_warn",
     "line": 36,
     "dynamic": false,
     "to": "шаг: maintenance_warn",
     "how": "точно",
     "inherited": "menu_ru_server"
    },
    {
     "label": "🚨 Перезагрузить мастер",
     "data": "confirm_reboot",
     "line": 37,
     "dynamic": false,
     "to": "confirm_reboot",
     "how": "точно",
     "inherited": "menu_ru_server"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 38,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "menu_ru_server"
    }
   ]
  },
  {
   "id": "check_connection_animation",
   "file": "handlers_client.py",
   "line": 141,
   "title": "",
   "side": "client",
   "kind": "menu",
   "calls": [
    "range",
    "api_session",
    "InlineKeyboardButton",
    "int",
    "ts_to_moscow",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len"
   ],
   "buttons": [
    {
     "label": "🔙 К списку проверок",
     "data": "client_select_check",
     "line": 169,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно"
    },
    {
     "label": "🔄 Проверить еще раз",
     "data": "check_conn_…",
     "line": 175,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»"
    }
   ]
  },
  {
   "id": "send_client_menu",
   "file": "handlers_client.py",
   "line": 181,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "check_admin",
    "check_admin",
    "escape_md",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "has_unseen_changes",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 Мои ключи",
     "data": "client_my_keys",
     "line": 205,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    },
    {
     "label": "📊 Статистика",
     "data": "client_stats",
     "line": 206,
     "dynamic": false,
     "to": "client_stats_handler",
     "how": "точно"
    },
    {
     "label": "⚡️ Проверить связь",
     "data": "client_select_check",
     "line": 207,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно"
    },
    {
     "label": "🌐 Рос. сервисы",
     "data": "client_bypass_info",
     "line": 208,
     "dynamic": false,
     "to": "client_bypass_info_handler",
     "how": "точно"
    },
    {
     "label": "📱 Приложения",
     "data": "client_apps",
     "line": 209,
     "dynamic": false,
     "to": "client_apps_handler",
     "how": "точно"
    },
    {
     "label": "🆘 Сообщить о проблеме",
     "data": "support_start",
     "line": 210,
     "dynamic": false,
     "to": "support_start_handler",
     "how": "точно"
    },
    {
     "label": "… Что нового",
     "data": "client_whats_new",
     "line": 227,
     "dynamic": false,
     "to": "client_whats_new",
     "how": "точно"
    },
    {
     "label": "🚪 Выйти из режима клиента",
     "data": "back_to_main",
     "line": 230,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "❤️ Поддержать проект",
     "data": "client_donate",
     "line": 218,
     "dynamic": false,
     "to": "client_donate",
     "how": "точно"
    },
    {
     "label": "🚪 Вернуться в Админку",
     "data": "back_to_main",
     "line": 196,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_menu",
   "file": "handlers_client.py",
   "line": 332,
   "title": "Главный экран клиента: сводка, а не просто счётчик ключей.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "sum",
    "check_admin",
    "_client_context",
    "check_admin",
    "min",
    "dt_to_moscow",
    "_days_left",
    "_limit_line",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "has_unseen_changes",
    "InlineKeyboardButton",
    "escape_md",
    "len",
    "_exceeded_24h",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "escape_md",
    "escape_md",
    "_pause_reason",
    "_times",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔑 Мои ключи",
     "data": "client_my_keys",
     "line": 414,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    },
    {
     "label": "📊 Статистика",
     "data": "client_stats",
     "line": 415,
     "dynamic": false,
     "to": "client_stats_handler",
     "how": "точно"
    },
    {
     "label": "⚡️ Проверить связь",
     "data": "client_select_check",
     "line": 416,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно"
    },
    {
     "label": "🌐 Рос. сервисы",
     "data": "client_bypass_info",
     "line": 417,
     "dynamic": false,
     "to": "client_bypass_info_handler",
     "how": "точно"
    },
    {
     "label": "📱 Приложения",
     "data": "client_apps",
     "line": 418,
     "dynamic": false,
     "to": "client_apps_handler",
     "how": "точно"
    },
    {
     "label": "🆘 Сообщить о проблеме",
     "data": "support_start",
     "line": 419,
     "dynamic": false,
     "to": "support_start_handler",
     "how": "точно"
    },
    {
     "label": "… Что нового",
     "data": "client_whats_new",
     "line": 435,
     "dynamic": false,
     "to": "client_whats_new",
     "how": "точно"
    },
    {
     "label": "🚪 Выйти из режима клиента",
     "data": "back_to_main",
     "line": 438,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🚪 Вернуться в Админку",
     "data": "back_to_main",
     "line": 358,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "❤️ Поддержать проект",
     "data": "client_donate",
     "line": 427,
     "dynamic": false,
     "to": "client_donate",
     "how": "точно"
    },
    {
     "label": "🆘 Сообщить о проблеме",
     "data": "support_start",
     "line": 369,
     "dynamic": false,
     "to": "support_start_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_my_keys_handler",
   "file": "handlers_client.py",
   "line": 447,
   "title": "Список ключей: в подписи кнопки — состояние, в тексте — что значат значки.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "_client_context",
    "_key_icon",
    "len",
    "InlineKeyboardButton",
    "_pause_reason",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "dt_to_moscow"
   ],
   "buttons": [
    {
     "label": "🔙 В главное меню",
     "data": "client_menu",
     "line": 479,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "… …",
     "data": "client_key_manage_…",
     "line": 472,
     "dynamic": false,
     "to": "client_key_manage_handler",
     "how": "по приставке «client_key_manage_»"
    },
    {
     "label": "🔄 Перевыпустить все ключи",
     "data": "client_regen_all",
     "line": 478,
     "dynamic": false,
     "to": "client_regen_all_confirm_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_key_manage_handler",
   "file": "handlers_client.py",
   "line": 497,
   "title": "Карточка ключа глазами владельца ключа, а не администратора.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "bool",
    "get_live_peers_status",
    "int",
    "_days_left",
    "_traffic_24h",
    "_exceeded_24h",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "dt_to_moscow",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "_xray_online",
    "_limit_line",
    "_human_bytes",
    "_pause_reason",
    "_times"
   ],
   "buttons": [
    {
     "label": "📥 Конфиг Xray / 📥 Конфиг AmneziaWG",
     "data": "client_download_…",
     "line": 559,
     "dynamic": false,
     "to": "client_download_handler",
     "how": "по приставке «client_download_»"
    },
    {
     "label": "⚡️ Проверить связь",
     "data": "check_conn_…",
     "line": 561,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»"
    },
    {
     "label": "🔄 Перевыпустить",
     "data": "client_regen_…",
     "line": 562,
     "dynamic": false,
     "to": "client_regen_confirm",
     "how": "по приставке «client_regen_»"
    },
    {
     "label": "🔙 К списку ключей",
     "data": "client_my_keys",
     "line": 567,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    },
    {
     "label": "❓ Как подключить",
     "data": "client_how_…",
     "line": 565,
     "dynamic": false,
     "to": "client_how_handler",
     "how": "по приставке «client_how_»"
    }
   ]
  },
  {
   "id": "client_regen_all_confirm_handler",
   "file": "handlers_client.py",
   "line": 573,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✅ Да, перевыпустить все",
     "data": "do_client_regen_all",
     "line": 575,
     "dynamic": false,
     "to": "client_regen_all_action_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "client_my_keys",
     "line": 575,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_regen_all_action_handler",
   "file": "handlers_client.py",
   "line": 583,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "safe_delete",
    "_queue_retire",
    "exit_kb",
    "InlineKeyboardMarkup",
    "_issue_new_config",
    "exit_kb",
    "InlineKeyboardButton",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🏠 Меню",
     "data": "client_menu",
     "line": 595,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_select_check_menu",
   "file": "handlers_client.py",
   "line": 629,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🚀 Проверить все ключи",
     "data": "client_check_all",
     "line": 640,
     "dynamic": false,
     "to": "client_check_all_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "client_menu",
     "line": 641,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "🔎 …",
     "data": "check_conn_…",
     "line": 638,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»"
    }
   ]
  },
  {
   "id": "client_check_all_handler",
   "file": "handlers_client.py",
   "line": 645,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "int",
    "escape_md",
    "next",
    "api_session",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "ts_to_moscow",
    "ts_to_moscow",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Назад",
     "data": "client_select_check",
     "line": 696,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "client_select_check",
     "line": 659,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_download_handler",
   "file": "handlers_client.py",
   "line": 761,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "send_xray_profile",
    "open",
    "exit_kb",
    "open"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 478,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "exit_kb"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 481,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно",
     "inherited": "exit_kb"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 484,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "exit_kb"
    }
   ]
  },
  {
   "id": "check_connection_handler",
   "file": "handlers_client.py",
   "line": 793,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "check_connection_animation"
   ],
   "buttons": [
    {
     "label": "🔙 К списку проверок",
     "data": "client_select_check",
     "line": 169,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно",
     "inherited": "check_connection_animation"
    },
    {
     "label": "🔄 Проверить еще раз",
     "data": "check_conn_…",
     "line": 175,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»",
     "inherited": "check_connection_animation"
    }
   ]
  },
  {
   "id": "client_stats_handler",
   "file": "handlers_client.py",
   "line": 803,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "round",
    "api_session",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 В меню",
     "data": "client_menu",
     "line": 847,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_regen_confirm",
   "file": "handlers_client.py",
   "line": 850,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✅ Да, перевыпустить",
     "data": "do_client_regen_…",
     "line": 852,
     "dynamic": false,
     "to": "client_regen_action",
     "how": "по приставке «do_client_regen_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "client_key_manage_…",
     "line": 852,
     "dynamic": false,
     "to": "client_key_manage_handler",
     "how": "по приставке «client_key_manage_»"
    }
   ]
  },
  {
   "id": "client_regen_action",
   "file": "handlers_client.py",
   "line": 870,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "safe_delete",
    "_queue_retire",
    "reapply",
    "send_xray_profile",
    "_issue_new_config",
    "InlineKeyboardMarkup",
    "exit_kb",
    "exit_kb",
    "exit_kb",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 В меню",
     "data": "client_menu",
     "line": 877,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "support_start_handler",
   "file": "handlers_client.py",
   "line": 930,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "len",
    "support_run_audit_handler",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "client_menu",
     "line": 947,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "🔑 …",
     "data": "support_audit_…",
     "line": 946,
     "dynamic": false,
     "to": "support_run_audit_handler",
     "how": "по приставке «support_audit_»"
    }
   ]
  },
  {
   "id": "support_run_audit_handler",
   "file": "handlers_client.py",
   "line": 951,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "escape_md",
    "api_session",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "int",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✅ Проблема решена",
     "data": "client_menu",
     "line": 1015,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "❌ Не помогло, написать владельцу",
     "data": "support_ask_…",
     "line": 1015,
     "dynamic": false,
     "to": "support_ask_msg_handler",
     "how": "по приставке «support_ask_»"
    },
    {
     "label": "🔙 Назад",
     "data": "client_menu",
     "line": 959,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "support_ask_msg_handler",
   "file": "handlers_client.py",
   "line": 1019,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "client_menu",
     "line": 1026,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_bypass_info_handler",
   "file": "handlers_client.py",
   "line": 1033,
   "title": "",
   "side": "client",
   "kind": "menu",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "📝 Сообщить о неработающем сайте",
     "data": "client_report_site",
     "line": 1054,
     "dynamic": false,
     "to": "client_report_site_handler",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "client_notify_toggle",
     "line": 1055,
     "dynamic": true,
     "to": "client_notify_toggle_handler",
     "how": "точно"
    },
    {
     "label": "🔙 В меню",
     "data": "client_menu",
     "line": 1056,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_notify_toggle_handler",
   "file": "handlers_client.py",
   "line": 1060,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "client_bypass_info_handler"
   ],
   "buttons": [
    {
     "label": "📝 Сообщить о неработающем сайте",
     "data": "client_report_site",
     "line": 1054,
     "dynamic": false,
     "to": "client_report_site_handler",
     "how": "точно",
     "inherited": "client_bypass_info_handler"
    },
    {
     "label": "«меняется»",
     "data": "client_notify_toggle",
     "line": 1055,
     "dynamic": true,
     "to": "client_notify_toggle_handler",
     "how": "точно",
     "inherited": "client_bypass_info_handler"
    },
    {
     "label": "🔙 В меню",
     "data": "client_menu",
     "line": 1056,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно",
     "inherited": "client_bypass_info_handler"
    }
   ]
  },
  {
   "id": "client_notify_off_handler",
   "file": "handlers_client.py",
   "line": 1068,
   "title": "Быстрое отключение прямо из текста уведомления (кнопка «Не напоминать»).",
   "side": "client",
   "kind": "screen",
   "calls": [],
   "buttons": []
  },
  {
   "id": "cmd_status",
   "file": "handlers_client.py",
   "line": 1082,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔎 …",
     "data": "check_conn_…",
     "line": 1089,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»"
    },
    {
     "label": "🚀 Проверить все ключи",
     "data": "client_check_all",
     "line": 1090,
     "dynamic": false,
     "to": "client_check_all_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Меню",
     "data": "client_menu",
     "line": 1091,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "cmd_support",
   "file": "handlers_client.py",
   "line": 1094,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔑 …",
     "data": "support_audit_…",
     "line": 1101,
     "dynamic": false,
     "to": "support_run_audit_handler",
     "how": "по приставке «support_audit_»"
    },
    {
     "label": "🏠 Меню",
     "data": "client_menu",
     "line": 1102,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "cmd_help",
   "file": "handlers_client.py",
   "line": 1105,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🏠 Меню",
     "data": "client_menu",
     "line": 1116,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_report_site_handler",
   "file": "handlers_client.py",
   "line": 1119,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "client_bypass_info",
     "line": 1122,
     "dynamic": false,
     "to": "client_bypass_info_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_whats_new",
   "file": "handlers_client.py",
   "line": 1132,
   "title": "Что изменилось — накопленное с прошлого раза, а если всё прочитано, то",
   "side": "client",
   "kind": "screen",
   "calls": [
    "user_text",
    "InlineKeyboardMarkup",
    "parse_releases",
    "last_user_text",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 В личный кабинет",
     "data": "client_menu",
     "line": 1161,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_how_handler",
   "file": "handlers_client.py",
   "line": 1176,
   "title": "Те же три шага, что при выдаче — человек забывает, и это нормально.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "instructions",
    "platform_keyboard"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "client_plat_…_…",
     "line": 579,
     "dynamic": true,
     "to": "client_platform_handler",
     "how": "по приставке «client_plat_»",
     "inherited": "platform_keyboard"
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 586,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "platform_keyboard"
    }
   ]
  },
  {
   "id": "client_apps_handler",
   "file": "handlers_client.py",
   "line": 1193,
   "title": "Где взять приложение — экран из личного кабинета.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔑 Мои ключи",
     "data": "client_my_keys",
     "line": 1228,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 1229,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_platform_handler",
   "file": "handlers_client.py",
   "line": 1236,
   "title": "Три шага под выбранную систему — и кнопка прислать ссылку заново.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "instructions",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "📥 Прислать ссылку заново",
     "data": "client_download_…",
     "line": 1242,
     "dynamic": false,
     "to": "client_download_handler",
     "how": "по приставке «client_download_»"
    },
    {
     "label": "🔙 Другая система",
     "data": "client_how_…",
     "line": 1244,
     "dynamic": false,
     "to": "client_how_handler",
     "how": "по приставке «client_how_»"
    }
   ]
  },
  {
   "id": "names_menu",
   "file": "handlers_dnsnames.py",
   "line": 29,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "_target_line",
    "len"
   ],
   "buttons": [
    {
     "label": "➕ Завести имя",
     "data": "dnm_add",
     "line": 51,
     "dynamic": false,
     "to": "add_request",
     "how": "точно"
    },
    {
     "label": "🔄 Применить заново",
     "data": "dnm_apply",
     "line": 55,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 56,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🏷 …",
     "data": "dnm_open_…",
     "line": 53,
     "dynamic": false,
     "to": "name_screen",
     "how": "по приставке «dnm_open_»"
    }
   ]
  },
  {
   "id": "add_request",
   "file": "handlers_dnsnames.py",
   "line": 63,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "dnm_menu",
     "line": 71,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "_target_picker",
   "file": "handlers_dnsnames.py",
   "line": 96,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "sorted",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "👤 …",
     "data": "dnm_to_…",
     "line": 102,
     "dynamic": false,
     "to": "target_person",
     "how": "по приставке «dnm_to_»"
    },
    {
     "label": "←",
     "data": "dnm_pg_…",
     "line": 106,
     "dynamic": false,
     "to": "target_page",
     "how": "по приставке «dnm_pg_»"
    },
    {
     "label": "→",
     "data": "dnm_pg_…",
     "line": 108,
     "dynamic": false,
     "to": "target_page",
     "how": "по приставке «dnm_pg_»"
    },
    {
     "label": "🔢 Указать адрес вручную",
     "data": "dnm_manual",
     "line": 111,
     "dynamic": false,
     "to": "manual_request",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "dnm_menu",
     "line": 112,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "target_page",
   "file": "handlers_dnsnames.py",
   "line": 123,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_target_picker",
    "names_menu"
   ],
   "buttons": [
    {
     "label": "👤 …",
     "data": "dnm_to_…",
     "line": 102,
     "dynamic": false,
     "to": "target_person",
     "how": "по приставке «dnm_to_»",
     "inherited": "_target_picker"
    },
    {
     "label": "←",
     "data": "dnm_pg_…",
     "line": 106,
     "dynamic": false,
     "to": "target_page",
     "how": "по приставке «dnm_pg_»",
     "inherited": "_target_picker"
    },
    {
     "label": "→",
     "data": "dnm_pg_…",
     "line": 108,
     "dynamic": false,
     "to": "target_page",
     "how": "по приставке «dnm_pg_»",
     "inherited": "_target_picker"
    },
    {
     "label": "🔢 Указать адрес вручную",
     "data": "dnm_manual",
     "line": 111,
     "dynamic": false,
     "to": "manual_request",
     "how": "точно",
     "inherited": "_target_picker"
    },
    {
     "label": "🔙 Отмена",
     "data": "dnm_menu",
     "line": 112,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно",
     "inherited": "_target_picker"
    }
   ]
  },
  {
   "id": "target_person",
   "file": "handlers_dnsnames.py",
   "line": 131,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "names_menu",
    "names_menu"
   ],
   "buttons": [
    {
     "label": "➕ Завести имя",
     "data": "dnm_add",
     "line": 51,
     "dynamic": false,
     "to": "add_request",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🔄 Применить заново",
     "data": "dnm_apply",
     "line": 55,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 56,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🏷 …",
     "data": "dnm_open_…",
     "line": 53,
     "dynamic": false,
     "to": "name_screen",
     "how": "по приставке «dnm_open_»",
     "inherited": "names_menu"
    }
   ]
  },
  {
   "id": "manual_request",
   "file": "handlers_dnsnames.py",
   "line": 142,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "names_menu",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "dnm_menu",
     "line": 152,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "name_screen",
   "file": "handlers_dnsnames.py",
   "line": 181,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "next",
    "_target_line",
    "show_screen",
    "names_menu",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✏️ Переименовать",
     "data": "dnm_ren_…",
     "line": 198,
     "dynamic": false,
     "to": "rename_request",
     "how": "по приставке «dnm_ren_»"
    },
    {
     "label": "🔙 К именам",
     "data": "dnm_menu",
     "line": 209,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно"
    },
    {
     "label": "🎯 Сменить цель",
     "data": "dnm_re_…",
     "line": 207,
     "dynamic": false,
     "to": "retarget_request",
     "how": "по приставке «dnm_re_»"
    },
    {
     "label": "🗑 Удалить имя",
     "data": "dnm_del_…",
     "line": 208,
     "dynamic": false,
     "to": "delete_name",
     "how": "по приставке «dnm_del_»"
    }
   ]
  },
  {
   "id": "rename_request",
   "file": "handlers_dnsnames.py",
   "line": 215,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "dnm_open_…",
     "line": 222,
     "dynamic": false,
     "to": "name_screen",
     "how": "по приставке «dnm_open_»"
    }
   ]
  },
  {
   "id": "_back_kb",
   "file": "handlers_dnsnames.py",
   "line": 227,
   "title": "Выход из сообщения, которым разговор закончился.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Имена",
     "data": "dnm_menu",
     "line": 236,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно"
    },
    {
     "label": "🏷 …",
     "data": "dnm_open_…",
     "line": 234,
     "dynamic": false,
     "to": "name_screen",
     "how": "по приставке «dnm_open_»"
    }
   ]
  },
  {
   "id": "retarget_request",
   "file": "handlers_dnsnames.py",
   "line": 271,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_target_picker"
   ],
   "buttons": [
    {
     "label": "👤 …",
     "data": "dnm_to_…",
     "line": 102,
     "dynamic": false,
     "to": "target_person",
     "how": "по приставке «dnm_to_»",
     "inherited": "_target_picker"
    },
    {
     "label": "←",
     "data": "dnm_pg_…",
     "line": 106,
     "dynamic": false,
     "to": "target_page",
     "how": "по приставке «dnm_pg_»",
     "inherited": "_target_picker"
    },
    {
     "label": "→",
     "data": "dnm_pg_…",
     "line": 108,
     "dynamic": false,
     "to": "target_page",
     "how": "по приставке «dnm_pg_»",
     "inherited": "_target_picker"
    },
    {
     "label": "🔢 Указать адрес вручную",
     "data": "dnm_manual",
     "line": 111,
     "dynamic": false,
     "to": "manual_request",
     "how": "точно",
     "inherited": "_target_picker"
    },
    {
     "label": "🔙 Отмена",
     "data": "dnm_menu",
     "line": 112,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно",
     "inherited": "_target_picker"
    }
   ]
  },
  {
   "id": "delete_name",
   "file": "handlers_dnsnames.py",
   "line": 277,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "names_menu",
    "names_menu"
   ],
   "buttons": [
    {
     "label": "➕ Завести имя",
     "data": "dnm_add",
     "line": 51,
     "dynamic": false,
     "to": "add_request",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🔄 Применить заново",
     "data": "dnm_apply",
     "line": 55,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 56,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🏷 …",
     "data": "dnm_open_…",
     "line": 53,
     "dynamic": false,
     "to": "name_screen",
     "how": "по приставке «dnm_open_»",
     "inherited": "names_menu"
    }
   ]
  },
  {
   "id": "apply_now",
   "file": "handlers_dnsnames.py",
   "line": 290,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "names_menu"
   ],
   "buttons": [
    {
     "label": "➕ Завести имя",
     "data": "dnm_add",
     "line": 51,
     "dynamic": false,
     "to": "add_request",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🔄 Применить заново",
     "data": "dnm_apply",
     "line": 55,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 56,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "names_menu"
    },
    {
     "label": "🏷 …",
     "data": "dnm_open_…",
     "line": 53,
     "dynamic": false,
     "to": "name_screen",
     "how": "по приставке «dnm_open_»",
     "inherited": "names_menu"
    }
   ]
  },
  {
   "id": "donate_menu",
   "file": "handlers_donate.py",
   "line": 65,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len",
    "_label",
    "InlineKeyboardButton",
    "_label"
   ],
   "buttons": [
    {
     "label": "➕ Карта",
     "data": "don_add_card",
     "line": 98,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»"
    },
    {
     "label": "➕ Телефон",
     "data": "don_add_phone",
     "line": 99,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»"
    },
    {
     "label": "➕ QR-картинка",
     "data": "don_add_qr",
     "line": 100,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»"
    },
    {
     "label": "✍️ Текст обращения",
     "data": "don_text",
     "line": 104,
     "dynamic": false,
     "to": "donate_ask",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 115,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🚫 Убрать кнопку у людей / ✅ Показать кнопку людям",
     "data": "don_toggle",
     "line": 95,
     "dynamic": false,
     "to": "donate_toggle",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "don_open_…",
     "line": 102,
     "dynamic": true,
     "to": "donate_open",
     "how": "по приставке «don_open_»"
    },
    {
     "label": "🔕 Не напоминать после обновлений / 🔔 Напоминать раз в … дн.",
     "data": "don_rem_toggle",
     "line": 106,
     "dynamic": false,
     "to": "donate_reminder_toggle",
     "how": "точно"
    },
    {
     "label": "👁 Предпросмотр",
     "data": "don_preview",
     "line": 113,
     "dynamic": false,
     "to": "donate_preview",
     "how": "точно"
    },
    {
     "label": "⏱ Периодичность · … дн.",
     "data": "don_period",
     "line": 111,
     "dynamic": false,
     "to": "donate_period",
     "how": "точно"
    }
   ]
  },
  {
   "id": "donate_toggle",
   "file": "handlers_donate.py",
   "line": 122,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "donate_menu"
   ],
   "buttons": [
    {
     "label": "➕ Карта",
     "data": "don_add_card",
     "line": 98,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ Телефон",
     "data": "don_add_phone",
     "line": 99,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ QR-картинка",
     "data": "don_add_qr",
     "line": 100,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "✍️ Текст обращения",
     "data": "don_text",
     "line": 104,
     "dynamic": false,
     "to": "donate_ask",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 115,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🚫 Убрать кнопку у людей / ✅ Показать кнопку людям",
     "data": "don_toggle",
     "line": 95,
     "dynamic": false,
     "to": "donate_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "«меняется»",
     "data": "don_open_…",
     "line": 102,
     "dynamic": true,
     "to": "donate_open",
     "how": "по приставке «don_open_»",
     "inherited": "donate_menu"
    },
    {
     "label": "🔕 Не напоминать после обновлений / 🔔 Напоминать раз в … дн.",
     "data": "don_rem_toggle",
     "line": 106,
     "dynamic": false,
     "to": "donate_reminder_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "👁 Предпросмотр",
     "data": "don_preview",
     "line": 113,
     "dynamic": false,
     "to": "donate_preview",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "⏱ Периодичность · … дн.",
     "data": "don_period",
     "line": 111,
     "dynamic": false,
     "to": "donate_period",
     "how": "точно",
     "inherited": "donate_menu"
    }
   ]
  },
  {
   "id": "donate_reminder_toggle",
   "file": "handlers_donate.py",
   "line": 132,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "donate_menu"
   ],
   "buttons": [
    {
     "label": "➕ Карта",
     "data": "don_add_card",
     "line": 98,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ Телефон",
     "data": "don_add_phone",
     "line": 99,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ QR-картинка",
     "data": "don_add_qr",
     "line": 100,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "✍️ Текст обращения",
     "data": "don_text",
     "line": 104,
     "dynamic": false,
     "to": "donate_ask",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 115,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🚫 Убрать кнопку у людей / ✅ Показать кнопку людям",
     "data": "don_toggle",
     "line": 95,
     "dynamic": false,
     "to": "donate_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "«меняется»",
     "data": "don_open_…",
     "line": 102,
     "dynamic": true,
     "to": "donate_open",
     "how": "по приставке «don_open_»",
     "inherited": "donate_menu"
    },
    {
     "label": "🔕 Не напоминать после обновлений / 🔔 Напоминать раз в … дн.",
     "data": "don_rem_toggle",
     "line": 106,
     "dynamic": false,
     "to": "donate_reminder_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "👁 Предпросмотр",
     "data": "don_preview",
     "line": 113,
     "dynamic": false,
     "to": "donate_preview",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "⏱ Периодичность · … дн.",
     "data": "don_period",
     "line": 111,
     "dynamic": false,
     "to": "donate_period",
     "how": "точно",
     "inherited": "donate_menu"
    }
   ]
  },
  {
   "id": "donate_period",
   "file": "handlers_donate.py",
   "line": 140,
   "title": "Как часто напоминать. Цифра здесь — не про вежливость, а про то, сколько",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "…раз в … дн.",
     "data": "don_per_…",
     "line": 156,
     "dynamic": false,
     "to": "donate_period_set",
     "how": "по приставке «don_per_»"
    },
    {
     "label": "✍️ Своё число",
     "data": "don_per_own",
     "line": 163,
     "dynamic": false,
     "to": "donate_ask",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "don_menu",
     "line": 164,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "donate_period_set",
   "file": "handlers_donate.py",
   "line": 171,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "donate_menu"
   ],
   "buttons": [
    {
     "label": "➕ Карта",
     "data": "don_add_card",
     "line": 98,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ Телефон",
     "data": "don_add_phone",
     "line": 99,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ QR-картинка",
     "data": "don_add_qr",
     "line": 100,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "✍️ Текст обращения",
     "data": "don_text",
     "line": 104,
     "dynamic": false,
     "to": "donate_ask",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 115,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🚫 Убрать кнопку у людей / ✅ Показать кнопку людям",
     "data": "don_toggle",
     "line": 95,
     "dynamic": false,
     "to": "donate_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "«меняется»",
     "data": "don_open_…",
     "line": 102,
     "dynamic": true,
     "to": "donate_open",
     "how": "по приставке «don_open_»",
     "inherited": "donate_menu"
    },
    {
     "label": "🔕 Не напоминать после обновлений / 🔔 Напоминать раз в … дн.",
     "data": "don_rem_toggle",
     "line": 106,
     "dynamic": false,
     "to": "donate_reminder_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "👁 Предпросмотр",
     "data": "don_preview",
     "line": 113,
     "dynamic": false,
     "to": "donate_preview",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "⏱ Периодичность · … дн.",
     "data": "don_period",
     "line": 111,
     "dynamic": false,
     "to": "donate_period",
     "how": "точно",
     "inherited": "donate_menu"
    }
   ]
  },
  {
   "id": "donate_ask",
   "file": "handlers_donate.py",
   "line": 178,
   "title": "Просит прислать реквизит. Состояние — в user_data: ввод разбирает",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "don_menu",
     "line": 187,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "donate_open",
   "file": "handlers_donate.py",
   "line": 192,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "donate_menu",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "_label",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🗑 Удалить",
     "data": "don_del_…",
     "line": 208,
     "dynamic": false,
     "to": "donate_delete",
     "how": "по приставке «don_del_»"
    },
    {
     "label": "🔙 Назад",
     "data": "don_menu",
     "line": 209,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "donate_delete",
   "file": "handlers_donate.py",
   "line": 215,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "donate_menu"
   ],
   "buttons": [
    {
     "label": "➕ Карта",
     "data": "don_add_card",
     "line": 98,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ Телефон",
     "data": "don_add_phone",
     "line": 99,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "➕ QR-картинка",
     "data": "don_add_qr",
     "line": 100,
     "dynamic": false,
     "to": "donate_ask",
     "how": "по приставке «don_add_»",
     "inherited": "donate_menu"
    },
    {
     "label": "✍️ Текст обращения",
     "data": "don_text",
     "line": 104,
     "dynamic": false,
     "to": "donate_ask",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 115,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "🚫 Убрать кнопку у людей / ✅ Показать кнопку людям",
     "data": "don_toggle",
     "line": 95,
     "dynamic": false,
     "to": "donate_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "«меняется»",
     "data": "don_open_…",
     "line": 102,
     "dynamic": true,
     "to": "donate_open",
     "how": "по приставке «don_open_»",
     "inherited": "donate_menu"
    },
    {
     "label": "🔕 Не напоминать после обновлений / 🔔 Напоминать раз в … дн.",
     "data": "don_rem_toggle",
     "line": 106,
     "dynamic": false,
     "to": "donate_reminder_toggle",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "👁 Предпросмотр",
     "data": "don_preview",
     "line": 113,
     "dynamic": false,
     "to": "donate_preview",
     "how": "точно",
     "inherited": "donate_menu"
    },
    {
     "label": "⏱ Периодичность · … дн.",
     "data": "don_period",
     "line": 111,
     "dynamic": false,
     "to": "donate_period",
     "how": "точно",
     "inherited": "donate_menu"
    }
   ]
  },
  {
   "id": "donate_preview",
   "file": "handlers_donate.py",
   "line": 225,
   "title": "Тот же экран, что у людей, — но с выходом обратно в настройку.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 К настройке",
     "data": "don_menu",
     "line": 232,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_donate",
   "file": "handlers_donate.py",
   "line": 239,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 249,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "🖼 Показать QR",
     "data": "client_donate_qr",
     "line": 247,
     "dynamic": false,
     "to": "client_donate_qr",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_donate_qr",
   "file": "handlers_donate.py",
   "line": 255,
   "title": "Картинку шлём отдельным сообщением: экран с текстом остаётся на месте,",
   "side": "admin",
   "kind": "screen",
   "calls": [],
   "buttons": []
  },
  {
   "id": "handle_donate_input",
   "file": "handlers_donate.py",
   "line": 273,
   "title": "Разбирает присланный реквизит или текст. Возвращает True, если сообщение",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "len",
    "InlineKeyboardButton",
    "len",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🔙 К настройке",
     "data": "don_menu",
     "line": 283,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "notify_new",
   "file": "handlers_hits.py",
   "line": 168,
   "title": "Одна сводка, не чаще выбранного промежутка. Возвращает, о скольких сказано.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "len",
    "int",
    "float",
    "len",
    "len",
    "print",
    "notify_enabled",
    "notify_every",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "_digest_text"
   ],
   "buttons": [
    {
     "label": "🚨 Открыть инциденты",
     "data": "hit_list",
     "line": 210,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🔕 Реже или выключить",
     "data": "hit_notify",
     "line": 211,
     "dynamic": false,
     "to": "notify_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "notify_screen",
   "file": "handlers_hits.py",
   "line": 239,
   "title": "Как часто писать о новых инцидентах.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "notify_enabled",
    "notify_every",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "chr"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "hit_notify_…",
     "line": 255,
     "dynamic": true,
     "to": "notify_set",
     "how": "по приставке «hit_notify_»"
    },
    {
     "label": "🔕 Выключить сводку / 🔔 Включить сводку",
     "data": "hit_notify_off",
     "line": 259,
     "dynamic": false,
     "to": "notify_toggle",
     "how": "точно"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 262,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "notify_set",
   "file": "handlers_hits.py",
   "line": 268,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "notify_screen",
    "int"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "hit_notify_…",
     "line": 255,
     "dynamic": true,
     "to": "notify_set",
     "how": "по приставке «hit_notify_»",
     "inherited": "notify_screen"
    },
    {
     "label": "🔕 Выключить сводку / 🔔 Включить сводку",
     "data": "hit_notify_off",
     "line": 259,
     "dynamic": false,
     "to": "notify_toggle",
     "how": "точно",
     "inherited": "notify_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 262,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно",
     "inherited": "notify_screen"
    }
   ]
  },
  {
   "id": "notify_toggle",
   "file": "handlers_hits.py",
   "line": 278,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "notify_enabled",
    "notify_screen"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "hit_notify_…",
     "line": 255,
     "dynamic": true,
     "to": "notify_set",
     "how": "по приставке «hit_notify_»",
     "inherited": "notify_screen"
    },
    {
     "label": "🔕 Выключить сводку / 🔔 Включить сводку",
     "data": "hit_notify_off",
     "line": 259,
     "dynamic": false,
     "to": "notify_toggle",
     "how": "точно",
     "inherited": "notify_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 262,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно",
     "inherited": "notify_screen"
    }
   ]
  },
  {
   "id": "hits_screen",
   "file": "handlers_hits.py",
   "line": 289,
   "title": "Список заявок. Свежие сверху, неразобранные помечены.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "max",
    "max",
    "collect_hits",
    "min",
    "show_screen",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "chr",
    "_when"
   ],
   "buttons": [
    {
     "label": "◀️ / ·",
     "data": "svc_noop",
     "line": 335,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "svc_noop",
     "line": 338,
     "dynamic": true,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "▶️ / ·",
     "data": "svc_noop",
     "line": 340,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "🔎 Найти по номеру",
     "data": "hit_find",
     "line": 354,
     "dynamic": false,
     "to": "hit_find_request",
     "how": "точно"
    },
    {
     "label": "🗓 Сколько хранить",
     "data": "hit_keep",
     "line": 355,
     "dynamic": false,
     "to": "keep_screen",
     "how": "точно"
    },
    {
     "label": "🔔 Сводка",
     "data": "hit_notify",
     "line": 356,
     "dynamic": false,
     "to": "notify_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 357,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 327,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "✅ Отметить все разобранными",
     "data": "hit_seen_all",
     "line": 347,
     "dynamic": false,
     "to": "hits_seen_all",
     "how": "точно"
    },
    {
     "label": "🗑 Удалить разобранные",
     "data": "hit_drop_seen",
     "line": 350,
     "dynamic": false,
     "to": "drop_seen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "drop_seen",
   "file": "handlers_hits.py",
   "line": 364,
   "title": "Удаляет разобранные — сейчас, а не по сроку.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "hits_screen"
   ],
   "buttons": [
    {
     "label": "◀️ / ·",
     "data": "svc_noop",
     "line": 335,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "svc_noop",
     "line": 338,
     "dynamic": true,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "▶️ / ·",
     "data": "svc_noop",
     "line": 340,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔎 Найти по номеру",
     "data": "hit_find",
     "line": 354,
     "dynamic": false,
     "to": "hit_find_request",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🗓 Сколько хранить",
     "data": "hit_keep",
     "line": 355,
     "dynamic": false,
     "to": "keep_screen",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔔 Сводка",
     "data": "hit_notify",
     "line": 356,
     "dynamic": false,
     "to": "notify_screen",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 357,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 327,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "hits_screen"
    },
    {
     "label": "✅ Отметить все разобранными",
     "data": "hit_seen_all",
     "line": 347,
     "dynamic": false,
     "to": "hits_seen_all",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🗑 Удалить разобранные",
     "data": "hit_drop_seen",
     "line": 350,
     "dynamic": false,
     "to": "drop_seen",
     "how": "точно",
     "inherited": "hits_screen"
    }
   ]
  },
  {
   "id": "hit_open",
   "file": "handlers_hits.py",
   "line": 377,
   "title": "Одна заявка целиком — всё, что нужно для разбора, на одном экране.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "hits_screen",
    "InlineKeyboardButton",
    "_when",
    "escape_md",
    "escape_md",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 К списку",
     "data": "hit_list",
     "line": 409,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🔑 Открыть ключ",
     "data": "user_detail_…",
     "line": 405,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🧹 Фильтры этого ключа",
     "data": "flt_user_…",
     "line": 407,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    }
   ]
  },
  {
   "id": "hit_find_request",
   "file": "handlers_hits.py",
   "line": 417,
   "title": "Просит номер. Он приходит от человека — с экрана, из переписки, вслух.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "hit_list",
     "line": 428,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "hit_find_entered",
   "file": "handlers_hits.py",
   "line": 432,
   "title": "Разбирает присланный номер и открывает инцидент.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "print",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "_when",
    "escape_md",
    "escape_md",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🚨 К инцидентам",
     "data": "hit_list",
     "line": 472,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🚨 К инцидентам",
     "data": "hit_list",
     "line": 445,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🔑 Открыть ключ",
     "data": "user_detail_…",
     "line": 468,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🧹 Фильтры этого ключа",
     "data": "flt_user_…",
     "line": 470,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    }
   ]
  },
  {
   "id": "hits_seen_all",
   "file": "handlers_hits.py",
   "line": 483,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "hits_screen"
   ],
   "buttons": [
    {
     "label": "◀️ / ·",
     "data": "svc_noop",
     "line": 335,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "svc_noop",
     "line": 338,
     "dynamic": true,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "▶️ / ·",
     "data": "svc_noop",
     "line": 340,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔎 Найти по номеру",
     "data": "hit_find",
     "line": 354,
     "dynamic": false,
     "to": "hit_find_request",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🗓 Сколько хранить",
     "data": "hit_keep",
     "line": 355,
     "dynamic": false,
     "to": "keep_screen",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔔 Сводка",
     "data": "hit_notify",
     "line": 356,
     "dynamic": false,
     "to": "notify_screen",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 357,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 327,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "hits_screen"
    },
    {
     "label": "✅ Отметить все разобранными",
     "data": "hit_seen_all",
     "line": 347,
     "dynamic": false,
     "to": "hits_seen_all",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🗑 Удалить разобранные",
     "data": "hit_drop_seen",
     "line": 350,
     "dynamic": false,
     "to": "drop_seen",
     "how": "точно",
     "inherited": "hits_screen"
    }
   ]
  },
  {
   "id": "keep_screen",
   "file": "handlers_hits.py",
   "line": 489,
   "title": "Сколько хранить карточки.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "str",
    "str",
    "chr"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "hit_keep_seen_…",
     "line": 510,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_seen_»"
    },
    {
     "label": "«меняется»",
     "data": "hit_keep_new_…",
     "line": 513,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_new_»"
    },
    {
     "label": "🧹 Убрать то, что старше срока",
     "data": "hit_keep_now",
     "line": 516,
     "dynamic": false,
     "to": "keep_now",
     "how": "точно"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 518,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "keep_set",
   "file": "handlers_hits.py",
   "line": 526,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "keep_screen"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "hit_keep_seen_…",
     "line": 510,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_seen_»",
     "inherited": "keep_screen"
    },
    {
     "label": "«меняется»",
     "data": "hit_keep_new_…",
     "line": 513,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_new_»",
     "inherited": "keep_screen"
    },
    {
     "label": "🧹 Убрать то, что старше срока",
     "data": "hit_keep_now",
     "line": 516,
     "dynamic": false,
     "to": "keep_now",
     "how": "точно",
     "inherited": "keep_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 518,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно",
     "inherited": "keep_screen"
    }
   ]
  },
  {
   "id": "keep_now",
   "file": "handlers_hits.py",
   "line": 544,
   "title": "Убрать старое прямо сейчас, не дожидаясь уборки.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "keep_screen"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "hit_keep_seen_…",
     "line": 510,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_seen_»",
     "inherited": "keep_screen"
    },
    {
     "label": "«меняется»",
     "data": "hit_keep_new_…",
     "line": 513,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_new_»",
     "inherited": "keep_screen"
    },
    {
     "label": "🧹 Убрать то, что старше срока",
     "data": "hit_keep_now",
     "line": 516,
     "dynamic": false,
     "to": "keep_now",
     "how": "точно",
     "inherited": "keep_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 518,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно",
     "inherited": "keep_screen"
    }
   ]
  },
  {
   "id": "decision_keyboard",
   "file": "handlers_keylife.py",
   "line": 72,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "♻️ Продлить",
     "data": "kd_ext_…",
     "line": 74,
     "dynamic": false,
     "to": "extend_menu",
     "how": "по приставке «kd_ext_»"
    },
    {
     "label": "🗑 Удалить",
     "data": "kd_del_…",
     "line": 75,
     "dynamic": false,
     "to": "delete_confirm",
     "how": "по приставке «kd_del_»"
    },
    {
     "label": "📋 Все вопросы",
     "data": "kd_list",
     "line": 76,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pending_screen",
   "file": "handlers_keylife.py",
   "line": 80,
   "title": "«Ждут решения» — список всех неотвеченных вопросов.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "escape_md",
    "dt_to_moscow"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 88,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 101,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "… …",
     "data": "kd_open_…",
     "line": 98,
     "dynamic": false,
     "to": "decision_screen",
     "how": "по приставке «kd_open_»"
    }
   ]
  },
  {
   "id": "decision_screen",
   "file": "handlers_keylife.py",
   "line": 107,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "decision_text",
    "show_screen",
    "pending_screen",
    "decision_keyboard"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 88,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "pending_screen"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 101,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "pending_screen"
    },
    {
     "label": "… …",
     "data": "kd_open_…",
     "line": 98,
     "dynamic": false,
     "to": "decision_screen",
     "how": "по приставке «kd_open_»",
     "inherited": "pending_screen"
    }
   ]
  },
  {
   "id": "extend_menu",
   "file": "handlers_keylife.py",
   "line": 117,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "pending_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "kd_set_…_…",
     "line": 123,
     "dynamic": true,
     "to": "do_extend",
     "how": "по приставке «kd_set_»"
    },
    {
     "label": "✖️ Назад",
     "data": "kd_open_…",
     "line": 125,
     "dynamic": false,
     "to": "decision_screen",
     "how": "по приставке «kd_open_»"
    }
   ]
  },
  {
   "id": "do_extend",
   "file": "handlers_keylife.py",
   "line": 133,
   "title": "Продление: снимаем паузу и ставим новый срок. Ключ тот же — у человека",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "policy_menu",
    "pending_screen",
    "timedelta",
    "resume_peer",
    "sync_person",
    "print",
    "str",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "📋 Ждут решения",
     "data": "kd_list",
     "line": 192,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно",
     "inherited": "policy_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 193,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "policy_menu"
    },
    {
     "label": "❓ Спрашивать снова",
     "data": "kd_pol_ask_…",
     "line": 198,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»",
     "inherited": "policy_menu"
    },
    {
     "label": "♻️ Продлевать само на … дн.",
     "data": "kd_pol_…_…",
     "line": 200,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»",
     "inherited": "policy_menu"
    },
    {
     "label": "📋 Ждут решения",
     "data": "kd_list",
     "line": 202,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно",
     "inherited": "policy_menu"
    }
   ]
  },
  {
   "id": "policy_menu",
   "file": "handlers_keylife.py",
   "line": 178,
   "title": "Что делать в следующий раз. Спрашивается ПОСЛЕ продления, а не до:",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "escape_md",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "📋 Ждут решения",
     "data": "kd_list",
     "line": 192,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 193,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "❓ Спрашивать снова",
     "data": "kd_pol_ask_…",
     "line": 198,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»"
    },
    {
     "label": "♻️ Продлевать само на … дн.",
     "data": "kd_pol_…_…",
     "line": 200,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»"
    },
    {
     "label": "📋 Ждут решения",
     "data": "kd_list",
     "line": 202,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "set_policy",
   "file": "handlers_keylife.py",
   "line": 208,
   "title": "mode: «ask» или число дней для автопродления.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "pending_screen",
    "int"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 88,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "pending_screen"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 101,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "pending_screen"
    },
    {
     "label": "… …",
     "data": "kd_open_…",
     "line": 98,
     "dynamic": false,
     "to": "decision_screen",
     "how": "по приставке «kd_open_»",
     "inherited": "pending_screen"
    }
   ]
  },
  {
   "id": "delete_confirm",
   "file": "handlers_keylife.py",
   "line": 222,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "pending_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🗑 Удалить",
     "data": "kd_delok_…",
     "line": 242,
     "dynamic": false,
     "to": "do_delete",
     "how": "по приставке «kd_delok_»"
    },
    {
     "label": "✖️ Отмена",
     "data": "kd_open_…",
     "line": 243,
     "dynamic": false,
     "to": "decision_screen",
     "how": "по приставке «kd_open_»"
    }
   ]
  },
  {
   "id": "do_delete",
   "file": "handlers_keylife.py",
   "line": 249,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "pending_screen",
    "pending_screen",
    "delete_peer",
    "reapply",
    "print"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 88,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "pending_screen"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 101,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "pending_screen"
    },
    {
     "label": "… …",
     "data": "kd_open_…",
     "line": 98,
     "dynamic": false,
     "to": "decision_screen",
     "how": "по приставке «kd_open_»",
     "inherited": "pending_screen"
    }
   ]
  },
  {
   "id": "migration_menu",
   "file": "handlers_migration.py",
   "line": 17,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "len",
    "escape_md",
    "escape_md",
    "len",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "▶️ Поднять второй интерфейс",
     "data": "mig_start",
     "line": 41,
     "dynamic": false,
     "to": "migration_start",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 43,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "✅ Клиент-сервер переехал / 🌍 Перевести клиент-сервер",
     "data": "mig_de",
     "line": 60,
     "dynamic": false,
     "to": "migration_de",
     "how": "точно"
    },
    {
     "label": "📨 Выдать новые конфиги",
     "data": "mig_issue_0",
     "line": 64,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»"
    },
    {
     "label": "🏁 Завершить переезд",
     "data": "mig_finish",
     "line": 65,
     "dynamic": false,
     "to": "migration_finish_confirm",
     "how": "точно"
    },
    {
     "label": "✖️ Отменить переезд",
     "data": "mig_abort",
     "line": 66,
     "dynamic": false,
     "to": "migration_abort_confirm",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 67,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 25,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "migration_start",
   "file": "handlers_migration.py",
   "line": 74,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "migration_menu",
    "show_screen",
    "InlineKeyboardMarkup",
    "escape_md",
    "str",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Назад",
     "data": "mig_menu",
     "line": 82,
     "dynamic": false,
     "to": "migration_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "migration_issue",
   "file": "handlers_migration.py",
   "line": 88,
   "title": "Список тех, кому ещё не выдали новый конфиг. По одному, а не всем разом:",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "max",
    "max",
    "min",
    "show_screen",
    "migration_menu",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len"
   ],
   "buttons": [
    {
     "label": "📨 …",
     "data": "mig_send_…",
     "line": 103,
     "dynamic": false,
     "to": "migration_send",
     "how": "по приставке «mig_send_»"
    },
    {
     "label": "…/…",
     "data": "svc_noop",
     "line": 109,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "🔙 Переезд",
     "data": "mig_menu",
     "line": 113,
     "dynamic": false,
     "to": "migration_menu",
     "how": "точно"
    },
    {
     "label": "⬅️",
     "data": "mig_issue_…",
     "line": 108,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»"
    },
    {
     "label": "➡️",
     "data": "mig_issue_…",
     "line": 111,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»"
    }
   ]
  },
  {
   "id": "migration_send",
   "file": "handlers_migration.py",
   "line": 123,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "migration_issue",
    "migration_menu",
    "track_send",
    "open",
    "open",
    "open"
   ],
   "buttons": [
    {
     "label": "📨 …",
     "data": "mig_send_…",
     "line": 103,
     "dynamic": false,
     "to": "migration_send",
     "how": "по приставке «mig_send_»",
     "inherited": "migration_issue"
    },
    {
     "label": "…/…",
     "data": "svc_noop",
     "line": 109,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "migration_issue"
    },
    {
     "label": "🔙 Переезд",
     "data": "mig_menu",
     "line": 113,
     "dynamic": false,
     "to": "migration_menu",
     "how": "точно",
     "inherited": "migration_issue"
    },
    {
     "label": "⬅️",
     "data": "mig_issue_…",
     "line": 108,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»",
     "inherited": "migration_issue"
    },
    {
     "label": "➡️",
     "data": "mig_issue_…",
     "line": 111,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»",
     "inherited": "migration_issue"
    }
   ]
  },
  {
   "id": "migration_de",
   "file": "handlers_migration.py",
   "line": 164,
   "title": "Перевод клиент-сервера. Делается ПЕРВЫМ: пока он на старом интерфейсе,",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "migration_menu"
   ],
   "buttons": [
    {
     "label": "▶️ Поднять второй интерфейс",
     "data": "mig_start",
     "line": 41,
     "dynamic": false,
     "to": "migration_start",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 43,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "✅ Клиент-сервер переехал / 🌍 Перевести клиент-сервер",
     "data": "mig_de",
     "line": 60,
     "dynamic": false,
     "to": "migration_de",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "📨 Выдать новые конфиги",
     "data": "mig_issue_0",
     "line": 64,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»",
     "inherited": "migration_menu"
    },
    {
     "label": "🏁 Завершить переезд",
     "data": "mig_finish",
     "line": 65,
     "dynamic": false,
     "to": "migration_finish_confirm",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "✖️ Отменить переезд",
     "data": "mig_abort",
     "line": 66,
     "dynamic": false,
     "to": "migration_abort_confirm",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 67,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 25,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    }
   ]
  },
  {
   "id": "migration_finish_confirm",
   "file": "handlers_migration.py",
   "line": 175,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "escape_md",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "🏁 Да, остановить старый",
     "data": "mig_finish_ok",
     "line": 204,
     "dynamic": false,
     "to": "migration_finish",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "mig_menu",
     "line": 205,
     "dynamic": false,
     "to": "migration_menu",
     "how": "точно"
    },
    {
     "label": "🌍 Перевести клиент-сервер",
     "data": "mig_de",
     "line": 185,
     "dynamic": false,
     "to": "migration_de",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "mig_menu",
     "line": 186,
     "dynamic": false,
     "to": "migration_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "migration_finish",
   "file": "handlers_migration.py",
   "line": 211,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "migration_menu"
   ],
   "buttons": [
    {
     "label": "▶️ Поднять второй интерфейс",
     "data": "mig_start",
     "line": 41,
     "dynamic": false,
     "to": "migration_start",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 43,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "✅ Клиент-сервер переехал / 🌍 Перевести клиент-сервер",
     "data": "mig_de",
     "line": 60,
     "dynamic": false,
     "to": "migration_de",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "📨 Выдать новые конфиги",
     "data": "mig_issue_0",
     "line": 64,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»",
     "inherited": "migration_menu"
    },
    {
     "label": "🏁 Завершить переезд",
     "data": "mig_finish",
     "line": 65,
     "dynamic": false,
     "to": "migration_finish_confirm",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "✖️ Отменить переезд",
     "data": "mig_abort",
     "line": 66,
     "dynamic": false,
     "to": "migration_abort_confirm",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 67,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 25,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    }
   ]
  },
  {
   "id": "migration_abort_confirm",
   "file": "handlers_migration.py",
   "line": 217,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✖️ Да, отменить переезд",
     "data": "mig_abort_ok",
     "line": 218,
     "dynamic": false,
     "to": "migration_abort",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "mig_menu",
     "line": 219,
     "dynamic": false,
     "to": "migration_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "migration_abort",
   "file": "handlers_migration.py",
   "line": 229,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "migration_menu"
   ],
   "buttons": [
    {
     "label": "▶️ Поднять второй интерфейс",
     "data": "mig_start",
     "line": 41,
     "dynamic": false,
     "to": "migration_start",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 43,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "✅ Клиент-сервер переехал / 🌍 Перевести клиент-сервер",
     "data": "mig_de",
     "line": 60,
     "dynamic": false,
     "to": "migration_de",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "📨 Выдать новые конфиги",
     "data": "mig_issue_0",
     "line": 64,
     "dynamic": false,
     "to": "migration_issue",
     "how": "по приставке «mig_issue_»",
     "inherited": "migration_menu"
    },
    {
     "label": "🏁 Завершить переезд",
     "data": "mig_finish",
     "line": 65,
     "dynamic": false,
     "to": "migration_finish_confirm",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "✖️ Отменить переезд",
     "data": "mig_abort",
     "line": 66,
     "dynamic": false,
     "to": "migration_abort_confirm",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 67,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 25,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "migration_menu"
    }
   ]
  },
  {
   "id": "screen",
   "file": "handlers_pubsub.py",
   "line": 80,
   "title": "Главный экран раздела: где мы стоим и что делать дальше.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "is_on",
    "state",
    "current_domain",
    "wildcard_on",
    "cert_days_left",
    "cert_named",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 192,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "1️⃣ Вписать имя узла",
     "data": "psub_domain",
     "line": 169,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "psub_domain",
     "line": 172,
     "dynamic": true,
     "to": "domain_screen",
     "how": "точно"
    },
    {
     "label": "🔄 Обновить сертификат",
     "data": "psub_renew",
     "line": 184,
     "dynamic": false,
     "to": "renew_now",
     "how": "точно"
    },
    {
     "label": "🔒 Закрыть доступ снаружи",
     "data": "psub_off",
     "line": 186,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно"
    },
    {
     "label": "🌐 Открыть доступ снаружи",
     "data": "psub_on",
     "line": 189,
     "dynamic": false,
     "to": "turn_on",
     "how": "точно"
    },
    {
     "label": "🔑 Сертификат внутренних имён · есть",
     "data": "psub_zone",
     "line": 175,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    },
    {
     "label": "2️⃣ Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 179,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "turn_on",
   "file": "handlers_pubsub.py",
   "line": 200,
   "title": "Открыть обратно. Это возврат к обычному состоянию, поэтому без",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_ask_host",
    "_wait_screen"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить",
     "data": "psub_menu",
     "line": 276,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "_wait_screen"
    }
   ]
  },
  {
   "id": "turn_off",
   "file": "handlers_pubsub.py",
   "line": 211,
   "title": "Закрыть. Здесь спросить и надо: это выключает автообновление у всех.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_ask_host",
    "_wait_screen",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔒 Да, закрыть",
     "data": "psub_off",
     "line": 244,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "psub_menu",
     "line": 245,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "renew_now",
   "file": "handlers_pubsub.py",
   "line": 256,
   "title": "Продлить руками. Тот же путь, которым ходит таймер.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "open",
    "_wait_screen"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить",
     "data": "psub_menu",
     "line": 276,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "_wait_screen"
    }
   ]
  },
  {
   "id": "_wait_screen",
   "file": "handlers_pubsub.py",
   "line": 266,
   "title": "Ждём хост и показываем, чем кончилось.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "range",
    "show_screen",
    "screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить",
     "data": "psub_menu",
     "line": 276,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "domain_screen",
   "file": "handlers_pubsub.py",
   "line": 327,
   "title": "Что даёт своё имя и как его задать.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "current_domain",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✏️ Задать имя",
     "data": "psub_domain_set",
     "line": 346,
     "dynamic": false,
     "to": "domain_ask",
     "how": "точно"
    },
    {
     "label": "🔙 Домен и сертификаты",
     "data": "psub_menu",
     "line": 350,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "🗑 Убрать имя",
     "data": "psub_domain_off",
     "line": 348,
     "dynamic": false,
     "to": "domain_off",
     "how": "точно"
    }
   ]
  },
  {
   "id": "domain_ask",
   "file": "handlers_pubsub.py",
   "line": 357,
   "title": "Просит вписать имя.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "psub_domain",
     "line": 366,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "domain_off",
   "file": "handlers_pubsub.py",
   "line": 370,
   "title": "Убирает имя: возвращаемся на адрес.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "request_env_change",
    "env_change_applied",
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Домен и сертификаты",
     "data": "psub_menu",
     "line": 386,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_screen",
   "file": "handlers_pubsub.py",
   "line": 482,
   "title": "Сертификат на внутренние имена: что сделать, а не зачем это нужно.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "bool",
    "zone_api_on",
    "wildcard_on",
    "zone_check_result",
    "current_domain",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "chr"
   ],
   "buttons": [
    {
     "label": "🔙 Домен и сертификаты",
     "data": "psub_menu",
     "line": 537,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "✏️ Задать доступ / ✏️ Заменить пару",
     "data": "psub_zone_set",
     "line": 526,
     "dynamic": false,
     "to": "zone_ask",
     "how": "точно"
    },
    {
     "label": "🌐 Сначала задать имя узла",
     "data": "psub_domain",
     "line": 535,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно"
    },
    {
     "label": "🔍 Проверить доступ",
     "data": "psub_zone_check",
     "line": 530,
     "dynamic": false,
     "to": "zone_check",
     "how": "точно"
    },
    {
     "label": "🗑 Убрать доступ",
     "data": "psub_zone_off",
     "line": 532,
     "dynamic": false,
     "to": "zone_off",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_ask",
   "file": "handlers_pubsub.py",
   "line": 545,
   "title": "Спрашиваем логин. Про пароль спросим следующим шагом — там выбор.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "psub_zone",
     "line": 554,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_password_step",
   "file": "handlers_pubsub.py",
   "line": 584,
   "title": "Выбор: придумать пароль здесь или вписать уже готовый.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🎲 Придумать пароль",
     "data": "psub_zone_gen",
     "line": 598,
     "dynamic": false,
     "to": "zone_generate",
     "how": "точно"
    },
    {
     "label": "✏️ Вписать свой",
     "data": "psub_zone_own",
     "line": 600,
     "dynamic": false,
     "to": "zone_own",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "psub_zone",
     "line": 602,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_own",
   "file": "handlers_pubsub.py",
   "line": 606,
   "title": "Владелец задал пароль в панели сам — ждём его текстом.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "psub_zone",
     "line": 617,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_generate",
   "file": "handlers_pubsub.py",
   "line": 620,
   "title": "Придумывает пароль, кладёт его на сервер и показывает владельцу.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "make_password",
    "zone_creds_write",
    "send_copyable",
    "zone_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔍 Проверить доступ",
     "data": "psub_zone_check",
     "line": 663,
     "dynamic": false,
     "to": "zone_check",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "psub_zone",
     "line": 665,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_off",
   "file": "handlers_pubsub.py",
   "line": 668,
   "title": "Убирает пару. Сертификат при этом остаётся — он уже выдан и живёт своё.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "zone_creds_clear",
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Назад",
     "data": "psub_zone",
     "line": 684,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_check",
   "file": "handlers_pubsub.py",
   "line": 688,
   "title": "Проверка без выпуска: кладём временную запись и тут же убираем.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "range",
    "open",
    "show_screen",
    "zone_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить",
     "data": "psub_zone",
     "line": 706,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "_back",
   "file": "handlers_roles.py",
   "line": 32,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Роли",
     "data": "roles_menu",
     "line": 35,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно"
    },
    {
     "label": "🔙 К роли",
     "data": "role_open_…",
     "line": 34,
     "dynamic": false,
     "to": "role_screen",
     "how": "по приставке «role_open_»"
    }
   ]
  },
  {
   "id": "roles_menu",
   "file": "handlers_roles.py",
   "line": 38,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "next",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "str",
    "str",
    "escape_md",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "… · … чел.",
     "data": "role_open_…",
     "line": 73,
     "dynamic": false,
     "to": "role_screen",
     "how": "по приставке «role_open_»"
    },
    {
     "label": "➕ Создать роль",
     "data": "role_new",
     "line": 76,
     "dynamic": false,
     "to": "role_new",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 83,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🆕 Роль для новых ключей · … / ",
     "data": "role_default",
     "line": 78,
     "dynamic": false,
     "to": "default_role_screen",
     "how": "точно"
    },
    {
     "label": "🔄 Применить на узле",
     "data": "role_apply",
     "line": 82,
     "dynamic": false,
     "to": "role_apply",
     "how": "точно"
    }
   ]
  },
  {
   "id": "role_screen",
   "file": "handlers_roles.py",
   "line": 90,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "_back",
    "show_screen",
    "roles_menu",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "grant_text",
    "escape_md",
    "grant_text",
    "str",
    "peer_ip_map"
   ],
   "buttons": [
    {
     "label": "➕ Открыть доступ",
     "data": "role_gadd_…",
     "line": 149,
     "dynamic": false,
     "to": "grant_add_screen",
     "how": "по приставке «role_gadd_»"
    },
    {
     "label": "➕ Добавить человека",
     "data": "role_madd_…_0",
     "line": 153,
     "dynamic": false,
     "to": "members_screen",
     "how": "по приставке «role_madd_»"
    },
    {
     "label": "🗑 Удалить роль",
     "data": "role_del_…",
     "line": 155,
     "dynamic": false,
     "to": "role_delete_confirm",
     "how": "по приставке «role_del_»"
    },
    {
     "label": "➖ …",
     "data": "role_gdel_…_…",
     "line": 147,
     "dynamic": false,
     "to": "grant_del",
     "how": "по приставке «role_gdel_»"
    },
    {
     "label": "➖ …",
     "data": "role_mdel_…_…",
     "line": 151,
     "dynamic": false,
     "to": "member_del",
     "how": "по приставке «role_mdel_»"
    }
   ]
  },
  {
   "id": "default_role_screen",
   "file": "handlers_roles.py",
   "line": 163,
   "title": "Какая роль достаётся новому ключу сама.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "next",
    "_back",
    "show_screen",
    "str",
    "str",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "str",
    "str",
    "escape_md",
    "chr"
   ],
   "buttons": [
    {
     "label": "………",
     "data": "role_defset_…",
     "line": 181,
     "dynamic": false,
     "to": "default_role_set",
     "how": "по приставке «role_defset_»"
    },
    {
     "label": "✖️ Не выдавать роль",
     "data": "role_defset_0",
     "line": 184,
     "dynamic": false,
     "to": "default_role_set",
     "how": "по приставке «role_defset_»"
    }
   ]
  },
  {
   "id": "default_role_set",
   "file": "handlers_roles.py",
   "line": 193,
   "title": "Ставит роль по умолчанию. Задним числом никого не трогает: уже выданные",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "default_role_screen",
    "default_role_screen",
    "str"
   ],
   "buttons": [
    {
     "label": "………",
     "data": "role_defset_…",
     "line": 181,
     "dynamic": false,
     "to": "default_role_set",
     "how": "по приставке «role_defset_»",
     "inherited": "default_role_screen"
    },
    {
     "label": "✖️ Не выдавать роль",
     "data": "role_defset_0",
     "line": 184,
     "dynamic": false,
     "to": "default_role_set",
     "how": "по приставке «role_defset_»",
     "inherited": "default_role_screen"
    }
   ]
  },
  {
   "id": "role_new",
   "file": "handlers_roles.py",
   "line": 213,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "roles_menu",
     "line": 218,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "grant_add_screen",
   "file": "handlers_roles.py",
   "line": 223,
   "title": "Обычный случай — открыть доступ к конкретному пиру, поэтому он кнопками.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "peer_ip_map",
    "_back",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🌐 Весь туннель",
     "data": "role_gall_…",
     "line": 250,
     "dynamic": false,
     "to": "grant_whole_tunnel",
     "how": "по приставке «role_gall_»"
    },
    {
     "label": "✍️ Ввести имя или адрес",
     "data": "role_gman_…",
     "line": 252,
     "dynamic": false,
     "to": "grant_manual",
     "how": "по приставке «role_gman_»"
    },
    {
     "label": "🏷 …",
     "data": "role_gname_…_…",
     "line": 239,
     "dynamic": false,
     "to": "grant_name",
     "how": "по приставке «role_gname_»"
    },
    {
     "label": "… · …",
     "data": "role_gpeer_…_…",
     "line": 246,
     "dynamic": false,
     "to": "grant_peer",
     "how": "по приставке «role_gpeer_»"
    }
   ]
  },
  {
   "id": "grant_whole_tunnel",
   "file": "handlers_roles.py",
   "line": 267,
   "title": "Открывает всю туннельную сеть разом.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_access_rules",
    "role_screen",
    "str"
   ],
   "buttons": [
    {
     "label": "➕ Открыть доступ",
     "data": "role_gadd_…",
     "line": 149,
     "dynamic": false,
     "to": "grant_add_screen",
     "how": "по приставке «role_gadd_»",
     "inherited": "role_screen"
    },
    {
     "label": "➕ Добавить человека",
     "data": "role_madd_…_0",
     "line": 153,
     "dynamic": false,
     "to": "members_screen",
     "how": "по приставке «role_madd_»",
     "inherited": "role_screen"
    },
    {
     "label": "🗑 Удалить роль",
     "data": "role_del_…",
     "line": 155,
     "dynamic": false,
     "to": "role_delete_confirm",
     "how": "по приставке «role_del_»",
     "inherited": "role_screen"
    },
    {
     "label": "➖ …",
     "data": "role_gdel_…_…",
     "line": 147,
     "dynamic": false,
     "to": "grant_del",
     "how": "по приставке «role_gdel_»",
     "inherited": "role_screen"
    },
    {
     "label": "➖ …",
     "data": "role_mdel_…_…",
     "line": 151,
     "dynamic": false,
     "to": "member_del",
     "how": "по приставке «role_mdel_»",
     "inherited": "role_screen"
    }
   ]
  },
  {
   "id": "grant_name",
   "file": "handlers_roles.py",
   "line": 280,
   "title": "Открыть доступ к имени целиком, без указания порта.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_access_rules",
    "role_screen",
    "grant_add_screen"
   ],
   "buttons": [
    {
     "label": "➕ Открыть доступ",
     "data": "role_gadd_…",
     "line": 149,
     "dynamic": false,
     "to": "grant_add_screen",
     "how": "по приставке «role_gadd_»",
     "inherited": "role_screen"
    },
    {
     "label": "➕ Добавить человека",
     "data": "role_madd_…_0",
     "line": 153,
     "dynamic": false,
     "to": "members_screen",
     "how": "по приставке «role_madd_»",
     "inherited": "role_screen"
    },
    {
     "label": "🗑 Удалить роль",
     "data": "role_del_…",
     "line": 155,
     "dynamic": false,
     "to": "role_delete_confirm",
     "how": "по приставке «role_del_»",
     "inherited": "role_screen"
    },
    {
     "label": "➖ …",
     "data": "role_gdel_…_…",
     "line": 147,
     "dynamic": false,
     "to": "grant_del",
     "how": "по приставке «role_gdel_»",
     "inherited": "role_screen"
    },
    {
     "label": "➖ …",
     "data": "role_mdel_…_…",
     "line": 151,
     "dynamic": false,
     "to": "member_del",
     "how": "по приставке «role_mdel_»",
     "inherited": "role_screen"
    }
   ]
  },
  {
   "id": "grant_manual",
   "file": "handlers_roles.py",
   "line": 293,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "role_open_…",
     "line": 311,
     "dynamic": false,
     "to": "role_screen",
     "how": "по приставке «role_open_»"
    }
   ]
  },
  {
   "id": "members_screen",
   "file": "handlers_roles.py",
   "line": 378,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "max",
    "max",
    "min",
    "_back",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "role_mset_…_…",
     "line": 389,
     "dynamic": true,
     "to": "member_add",
     "how": "по приставке «role_mset_»"
    },
    {
     "label": "…/…",
     "data": "svc_noop",
     "line": 396,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "⬅️",
     "data": "role_madd_…_…",
     "line": 395,
     "dynamic": false,
     "to": "members_screen",
     "how": "по приставке «role_madd_»"
    },
    {
     "label": "➡️",
     "data": "role_madd_…_…",
     "line": 398,
     "dynamic": false,
     "to": "members_screen",
     "how": "по приставке «role_madd_»"
    }
   ]
  },
  {
   "id": "grant_peer",
   "file": "handlers_roles.py",
   "line": 421,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "peer_ip_map",
    "_apply_and_answer"
   ],
   "buttons": []
  },
  {
   "id": "grant_del",
   "file": "handlers_roles.py",
   "line": 439,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_apply_and_answer"
   ],
   "buttons": []
  },
  {
   "id": "member_add",
   "file": "handlers_roles.py",
   "line": 444,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_apply_and_answer"
   ],
   "buttons": []
  },
  {
   "id": "member_del",
   "file": "handlers_roles.py",
   "line": 449,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_apply_and_answer",
    "apply_access_rules",
    "role_screen"
   ],
   "buttons": [
    {
     "label": "➕ Открыть доступ",
     "data": "role_gadd_…",
     "line": 149,
     "dynamic": false,
     "to": "grant_add_screen",
     "how": "по приставке «role_gadd_»",
     "inherited": "role_screen"
    },
    {
     "label": "➕ Добавить человека",
     "data": "role_madd_…_0",
     "line": 153,
     "dynamic": false,
     "to": "members_screen",
     "how": "по приставке «role_madd_»",
     "inherited": "role_screen"
    },
    {
     "label": "🗑 Удалить роль",
     "data": "role_del_…",
     "line": 155,
     "dynamic": false,
     "to": "role_delete_confirm",
     "how": "по приставке «role_del_»",
     "inherited": "role_screen"
    },
    {
     "label": "➖ …",
     "data": "role_gdel_…_…",
     "line": 147,
     "dynamic": false,
     "to": "grant_del",
     "how": "по приставке «role_gdel_»",
     "inherited": "role_screen"
    },
    {
     "label": "➖ …",
     "data": "role_mdel_…_…",
     "line": 151,
     "dynamic": false,
     "to": "member_del",
     "how": "по приставке «role_mdel_»",
     "inherited": "role_screen"
    }
   ]
  },
  {
   "id": "role_delete_confirm",
   "file": "handlers_roles.py",
   "line": 463,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🗑 Удалить",
     "data": "role_delok_…",
     "line": 480,
     "dynamic": false,
     "to": "role_delete",
     "how": "по приставке «role_delok_»"
    },
    {
     "label": "✖️ Отмена",
     "data": "role_open_…",
     "line": 481,
     "dynamic": false,
     "to": "role_screen",
     "how": "по приставке «role_open_»"
    }
   ]
  },
  {
   "id": "role_delete",
   "file": "handlers_roles.py",
   "line": 487,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "str",
    "str",
    "_apply_and_answer"
   ],
   "buttons": []
  },
  {
   "id": "user_roles_screen",
   "file": "handlers_roles.py",
   "line": 499,
   "title": "Роли конкретного человека — из его карточки. Тумблером, потому что здесь",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "role_ut_…_…",
     "line": 520,
     "dynamic": true,
     "to": "user_role_toggle",
     "how": "по приставке «role_ut_»"
    },
    {
     "label": "🛡 Все роли",
     "data": "roles_menu",
     "line": 523,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно"
    },
    {
     "label": "🔙 К пользователю",
     "data": "user_detail_…",
     "line": 524,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "user_role_toggle",
   "file": "handlers_roles.py",
   "line": 532,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_access_rules",
    "user_roles_screen"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "role_ut_…_…",
     "line": 520,
     "dynamic": true,
     "to": "user_role_toggle",
     "how": "по приставке «role_ut_»",
     "inherited": "user_roles_screen"
    },
    {
     "label": "🛡 Все роли",
     "data": "roles_menu",
     "line": 523,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно",
     "inherited": "user_roles_screen"
    },
    {
     "label": "🔙 К пользователю",
     "data": "user_detail_…",
     "line": 524,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "user_roles_screen"
    }
   ]
  },
  {
   "id": "role_apply",
   "file": "handlers_roles.py",
   "line": 544,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "apply_access_rules",
    "roles_menu"
   ],
   "buttons": [
    {
     "label": "… · … чел.",
     "data": "role_open_…",
     "line": 73,
     "dynamic": false,
     "to": "role_screen",
     "how": "по приставке «role_open_»",
     "inherited": "roles_menu"
    },
    {
     "label": "➕ Создать роль",
     "data": "role_new",
     "line": 76,
     "dynamic": false,
     "to": "role_new",
     "how": "точно",
     "inherited": "roles_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 83,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "roles_menu"
    },
    {
     "label": "🆕 Роль для новых ключей · … / ",
     "data": "role_default",
     "line": 78,
     "dynamic": false,
     "to": "default_role_screen",
     "how": "точно",
     "inherited": "roles_menu"
    },
    {
     "label": "🔄 Применить на узле",
     "data": "role_apply",
     "line": 82,
     "dynamic": false,
     "to": "role_apply",
     "how": "точно",
     "inherited": "roles_menu"
    }
   ]
  },
  {
   "id": "handle_role_text",
   "file": "handlers_roles.py",
   "line": 551,
   "title": "Возвращает True, если сообщение относилось к ролям и уже обработано.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "parse_grant",
    "normalize",
    "apply_access_rules",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "exit_kb",
    "exit_kb",
    "escape_md",
    "InlineKeyboardMarkup",
    "grant_text",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "➕ Открыть доступ",
     "data": "role_gadd_…",
     "line": 568,
     "dynamic": false,
     "to": "grant_add_screen",
     "how": "по приставке «role_gadd_»"
    },
    {
     "label": "➕ Добавить человека",
     "data": "role_madd_…_0",
     "line": 570,
     "dynamic": false,
     "to": "members_screen",
     "how": "по приставке «role_madd_»"
    },
    {
     "label": "🔙 Роли",
     "data": "roles_menu",
     "line": 572,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно"
    },
    {
     "label": "🔙 К роли",
     "data": "role_open_…",
     "line": 585,
     "dynamic": false,
     "to": "role_screen",
     "how": "по приставке «role_open_»"
    }
   ]
  },
  {
   "id": "routes_menu",
   "file": "handlers_routes.py",
   "line": 39,
   "title": "Что настроено лично на этом ключе.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "_line",
    "_line"
   ],
   "buttons": [
    {
     "label": "➕ Мимо VPN",
     "data": "rt_add_d_…",
     "line": 74,
     "dynamic": false,
     "to": "routes_ask",
     "how": "по приставке «rt_add_d_»"
    },
    {
     "label": "➕ Через VPN",
     "data": "rt_add_p_…",
     "line": 75,
     "dynamic": false,
     "to": "routes_ask",
     "how": "по приставке «rt_add_p_»"
    },
    {
     "label": "🔙 К ключу",
     "data": "user_detail_…",
     "line": 82,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🗑 …",
     "data": "rt_del_…_…",
     "line": 77,
     "dynamic": false,
     "to": "routes_delete",
     "how": "по приставке «rt_del_»"
    },
    {
     "label": "📱 Профиль этого ключа",
     "data": "rt_show_…",
     "line": 80,
     "dynamic": false,
     "to": "routes_show",
     "how": "по приставке «rt_show_»"
    }
   ]
  },
  {
   "id": "routes_ask",
   "file": "handlers_routes.py",
   "line": 90,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✖️ Отмена",
     "data": "rt_menu_…",
     "line": 98,
     "dynamic": false,
     "to": "routes_menu",
     "how": "по приставке «rt_menu_»"
    }
   ]
  },
  {
   "id": "routes_delete",
   "file": "handlers_routes.py",
   "line": 104,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "routes_menu"
   ],
   "buttons": [
    {
     "label": "➕ Мимо VPN",
     "data": "rt_add_d_…",
     "line": 74,
     "dynamic": false,
     "to": "routes_ask",
     "how": "по приставке «rt_add_d_»",
     "inherited": "routes_menu"
    },
    {
     "label": "➕ Через VPN",
     "data": "rt_add_p_…",
     "line": 75,
     "dynamic": false,
     "to": "routes_ask",
     "how": "по приставке «rt_add_p_»",
     "inherited": "routes_menu"
    },
    {
     "label": "🔙 К ключу",
     "data": "user_detail_…",
     "line": 82,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "routes_menu"
    },
    {
     "label": "🗑 …",
     "data": "rt_del_…_…",
     "line": 77,
     "dynamic": false,
     "to": "routes_delete",
     "how": "по приставке «rt_del_»",
     "inherited": "routes_menu"
    },
    {
     "label": "📱 Профиль этого ключа",
     "data": "rt_show_…",
     "line": 80,
     "dynamic": false,
     "to": "routes_show",
     "how": "по приставке «rt_show_»",
     "inherited": "routes_menu"
    }
   ]
  },
  {
   "id": "routes_show",
   "file": "handlers_routes.py",
   "line": 112,
   "title": "Готовый профиль этого ключа — чтобы проверить или отдать скрипту.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 К исключениям",
     "data": "rt_menu_…",
     "line": 147,
     "dynamic": false,
     "to": "routes_menu",
     "how": "по приставке «rt_menu_»"
    }
   ]
  },
  {
   "id": "handle_route_input",
   "file": "handlers_routes.py",
   "line": 155,
   "title": "Разбирает присланное: по записи в строке, пустые пропускаем.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "len",
    "InlineKeyboardButton",
    "len"
   ],
   "buttons": [
    {
     "label": "🌐 К исключениям",
     "data": "rt_menu_…",
     "line": 181,
     "dynamic": false,
     "to": "routes_menu",
     "how": "по приставке «rt_menu_»"
    }
   ]
  },
  {
   "id": "service_menu",
   "file": "handlers_service.py",
   "line": 84,
   "title": "Сводка + действия. Главная кнопка меняет подпись по состоянию, но остаётся",
   "side": "client",
   "kind": "menu",
   "calls": [
    "set",
    "_settings",
    "admin_waiting",
    "escape_md",
    "sum",
    "sum",
    "sum",
    "len",
    "show_screen",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "sum",
    "len",
    "len",
    "len",
    "len",
    "len",
    "str",
    "len",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "svc_mode_toggle",
     "line": 265,
     "dynamic": true,
     "to": "toggle_mode",
     "how": "точно"
    },
    {
     "label": "📊 Нагрузка",
     "data": "svc_load",
     "line": 266,
     "dynamic": false,
     "to": "load_screen",
     "how": "точно"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 267,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно"
    },
    {
     "label": "🔀 Протоколы",
     "data": "proto_menu",
     "line": 268,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно"
    },
    {
     "label": "🌐 Домен и сертификаты",
     "data": "psub_menu",
     "line": 269,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "roles_menu",
     "line": 270,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_menu",
     "line": 271,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "🚨 Инциденты · … / ",
     "data": "hit_list",
     "line": 272,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🏷 Имена в туннеле",
     "data": "dnm_menu",
     "line": 275,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно"
    },
    {
     "label": "💳 Донаты",
     "data": "don_menu",
     "line": 278,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно"
    },
    {
     "label": "🧾 Биллинг",
     "data": "bill_menu",
     "line": 281,
     "dynamic": false,
     "to": "menu",
     "how": "точно"
    },
    {
     "label": "📋 Ждут решения · … / ",
     "data": "kd_list",
     "line": 283,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно"
    },
    {
     "label": "📨 Не подключились · … / ",
     "data": "deliv_list",
     "line": 286,
     "dynamic": false,
     "to": "delivery_screen",
     "how": "точно"
    },
    {
     "label": "🧹 Чистка чата",
     "data": "chat_clean",
     "line": 292,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 296,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "➡️ … · …",
     "data": "«меняется»",
     "line": 262,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🆘 Поддержка",
     "data": "support_admin_menu",
     "line": 295,
     "dynamic": false,
     "to": "support_admin_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "toggle_mode",
   "file": "handlers_service.py",
   "line": 303,
   "title": "Переключение наблюдение ↔ ограничение. Отдельным экраном с подтверждением:",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_settings",
    "len",
    "round",
    "show_screen",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✅ Включить",
     "data": "svc_mode_on",
     "line": 328,
     "dynamic": false,
     "to": "set_mode",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "svc_menu",
     "line": 329,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "✅ Вернуть наблюдение",
     "data": "svc_mode_off",
     "line": 334,
     "dynamic": false,
     "to": "set_mode",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "svc_menu",
     "line": 335,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "set_mode",
   "file": "handlers_service.py",
   "line": 341,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "service_menu"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "svc_mode_toggle",
     "line": 265,
     "dynamic": true,
     "to": "toggle_mode",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "📊 Нагрузка",
     "data": "svc_load",
     "line": 266,
     "dynamic": false,
     "to": "load_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 267,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🔀 Протоколы",
     "data": "proto_menu",
     "line": 268,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🌐 Домен и сертификаты",
     "data": "psub_menu",
     "line": 269,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "roles_menu",
     "line": 270,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_menu",
     "line": 271,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🚨 Инциденты · … / ",
     "data": "hit_list",
     "line": 272,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🏷 Имена в туннеле",
     "data": "dnm_menu",
     "line": 275,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "💳 Донаты",
     "data": "don_menu",
     "line": 278,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🧾 Биллинг",
     "data": "bill_menu",
     "line": 281,
     "dynamic": false,
     "to": "menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "📋 Ждут решения · … / ",
     "data": "kd_list",
     "line": 283,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "📨 Не подключились · … / ",
     "data": "deliv_list",
     "line": 286,
     "dynamic": false,
     "to": "delivery_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🧹 Чистка чата",
     "data": "chat_clean",
     "line": 292,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 296,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "➡️ … · …",
     "data": "«меняется»",
     "line": 262,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "service_menu"
    },
    {
     "label": "🆘 Поддержка",
     "data": "support_admin_menu",
     "line": 295,
     "dynamic": false,
     "to": "support_admin_menu",
     "how": "точно",
     "inherited": "service_menu"
    }
   ]
  },
  {
   "id": "load_screen",
   "file": "handlers_service.py",
   "line": 350,
   "title": "Кто нагружал сервер за сутки. Не «пробития порога», а понятные цифры.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "node_ceiling",
    "_settings",
    "set",
    "show_screen",
    "dt_to_moscow",
    "event_verdict",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "dict",
    "len",
    "dt_to_moscow",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "📈 График нагрузки",
     "data": "svc_chart",
     "line": 400,
     "dynamic": false,
     "to": "load_chart",
     "how": "точно"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 401,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 402,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🗑 Снять: … · …",
     "data": "svc_ev_del_…",
     "line": 398,
     "dynamic": false,
     "to": "event_delete",
     "how": "по приставке «svc_ev_del_»"
    }
   ]
  },
  {
   "id": "event_delete",
   "file": "handlers_service.py",
   "line": 407,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "load_screen"
   ],
   "buttons": [
    {
     "label": "📈 График нагрузки",
     "data": "svc_chart",
     "line": 400,
     "dynamic": false,
     "to": "load_chart",
     "how": "точно",
     "inherited": "load_screen"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 401,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно",
     "inherited": "load_screen"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 402,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "load_screen"
    },
    {
     "label": "🗑 Снять: … · …",
     "data": "svc_ev_del_…",
     "line": 398,
     "dynamic": false,
     "to": "event_delete",
     "how": "по приставке «svc_ev_del_»",
     "inherited": "load_screen"
    }
   ]
  },
  {
   "id": "limits_screen",
   "file": "handlers_service.py",
   "line": 415,
   "title": "Общий порог и персональные правила. В списке только те, у кого правило",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "node_ceiling",
    "_settings",
    "show_screen",
    "list",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "dt_to_moscow"
   ],
   "buttons": [
    {
     "label": "➖ …",
     "data": "svc_limit_down",
     "line": 451,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно"
    },
    {
     "label": "… пак/с",
     "data": "svc_noop",
     "line": 453,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "➕ …",
     "data": "svc_limit_up",
     "line": 454,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно"
    },
    {
     "label": "3000",
     "data": "svc_limit_3000",
     "line": 455,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»"
    },
    {
     "label": "5000",
     "data": "svc_limit_5000",
     "line": 456,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»"
    },
    {
     "label": "6000",
     "data": "svc_limit_6000",
     "line": 457,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»"
    },
    {
     "label": "👥 Правила по людям",
     "data": "users_page_0",
     "line": 458,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 459,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "change_limit",
   "file": "handlers_service.py",
   "line": 466,
   "title": "Порог меняется шагом или готовым значением. Ниже тысячи и выше потолка узла",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "max",
    "node_ceiling",
    "_settings",
    "min",
    "limits_screen",
    "int",
    "str"
   ],
   "buttons": [
    {
     "label": "➖ …",
     "data": "svc_limit_down",
     "line": 451,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно",
     "inherited": "limits_screen"
    },
    {
     "label": "… пак/с",
     "data": "svc_noop",
     "line": 453,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "limits_screen"
    },
    {
     "label": "➕ …",
     "data": "svc_limit_up",
     "line": 454,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно",
     "inherited": "limits_screen"
    },
    {
     "label": "3000",
     "data": "svc_limit_3000",
     "line": 455,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»",
     "inherited": "limits_screen"
    },
    {
     "label": "5000",
     "data": "svc_limit_5000",
     "line": 456,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»",
     "inherited": "limits_screen"
    },
    {
     "label": "6000",
     "data": "svc_limit_6000",
     "line": 457,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»",
     "inherited": "limits_screen"
    },
    {
     "label": "👥 Правила по людям",
     "data": "users_page_0",
     "line": 458,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»",
     "inherited": "limits_screen"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 459,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "limits_screen"
    }
   ]
  },
  {
   "id": "set_peer_rule",
   "file": "handlers_service.py",
   "line": 485,
   "title": "Правило для конкретного человека: общий порог, свой или без ограничений.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_settings",
    "peer_limit_screen",
    "max",
    "max",
    "timedelta"
   ],
   "buttons": [
    {
     "label": "📐 Общий предел · … пак/с",
     "data": "svc_rule_default_…",
     "line": 565,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "✂️ Свой предел · … пак/с",
     "data": "svc_rule_custom_…",
     "line": 567,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "♾ Снять ограничение",
     "data": "svc_rule_unlimited_…",
     "line": 569,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "⏱ Придушить на сутки · … пак/с",
     "data": "svc_rule_day_…",
     "line": 571,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "🔙 К пользователю",
     "data": "user_detail_…",
     "line": 573,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "peer_limit_screen"
    }
   ]
  },
  {
   "id": "peer_limit_screen",
   "file": "handlers_service.py",
   "line": 513,
   "title": "Что человеку разрешено по пакетам и что можно поменять.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "round",
    "max",
    "_settings",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardMarkup",
    "dt_to_moscow"
   ],
   "buttons": [
    {
     "label": "📐 Общий предел · … пак/с",
     "data": "svc_rule_default_…",
     "line": 565,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "✂️ Свой предел · … пак/с",
     "data": "svc_rule_custom_…",
     "line": 567,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "♾ Снять ограничение",
     "data": "svc_rule_unlimited_…",
     "line": 569,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "⏱ Придушить на сутки · … пак/с",
     "data": "svc_rule_day_…",
     "line": 571,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "🔙 К пользователю",
     "data": "user_detail_…",
     "line": 573,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "load_chart",
   "file": "handlers_service.py",
   "line": 579,
   "title": "Картинка с двумя панелями: скорость и пакеты.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "node_ceiling",
    "int",
    "safe_delete",
    "open",
    "generate_load_graph",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "int",
    "show_screen",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "escape_md",
    "str",
    "str",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "👤 Выбрать человека",
     "data": "svc_pick_0",
     "line": 635,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "📊 Графики",
     "data": "vpn_graph",
     "line": 636,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    },
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 633,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🔙 Графики",
     "data": "vpn_graph",
     "line": 616,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "charts_screen",
   "file": "handlers_service.py",
   "line": 646,
   "title": "Кого стоит посмотреть на графике.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "set",
    "show_screen",
    "api_session",
    "chart_candidates",
    "print",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "len",
    "InlineKeyboardMarkup",
    "int",
    "InlineKeyboardButton",
    "escape_md",
    "len"
   ],
   "buttons": [
    {
     "label": "👤 Выбрать человека",
     "data": "svc_pick_0",
     "line": 699,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "🔙 Графики",
     "data": "vpn_graph",
     "line": 700,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    },
    {
     "label": "📉 …",
     "data": "svc_pchart_…",
     "line": 694,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»"
    }
   ]
  },
  {
   "id": "pick_peer_screen",
   "file": "handlers_service.py",
   "line": 707,
   "title": "Полный список — на случай, когда подбор не угадал.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "max",
    "max",
    "min",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "len"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "svc_pchart_…",
     "line": 716,
     "dynamic": true,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»"
    },
    {
     "label": "…/…",
     "data": "svc_noop",
     "line": 722,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "🔙 Графики",
     "data": "vpn_graph",
     "line": 726,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    },
    {
     "label": "⬅️",
     "data": "svc_pick_…",
     "line": 721,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "➡️",
     "data": "svc_pick_…",
     "line": 724,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    }
   ]
  },
  {
   "id": "graphs_menu",
   "file": "handlers_service.py",
   "line": 733,
   "title": "Единый вход во все графики.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "chart_candidates",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "len",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "📊 Трафик по людям",
     "data": "graph_traffic",
     "line": 762,
     "dynamic": false,
     "to": "send_vpn_graph",
     "how": "точно"
    },
    {
     "label": "🚦 Нагрузка · скорость и пакеты",
     "data": "svc_chart",
     "line": 763,
     "dynamic": false,
     "to": "load_chart",
     "how": "точно"
    },
    {
     "label": "📉 Подбор · … / ",
     "data": "svc_charts",
     "line": 764,
     "dynamic": false,
     "to": "charts_screen",
     "how": "точно"
    },
    {
     "label": "👤 Выбрать человека",
     "data": "svc_pick_0",
     "line": 767,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 768,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "whats_new",
   "file": "handlers_service.py",
   "line": 774,
   "title": "Три последних версии. Кнопка нужна и админу: догадаться, что список изменений",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "admin_text",
    "repo_markdown",
    "show_screen",
    "InlineKeyboardButton",
    "fit",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 784,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "ensure_api_token",
   "file": "handlers_service.py",
   "line": 836,
   "title": "Доводит токен панелей до одинакового состояния на обеих нодах.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "request_env_change",
    "print",
    "tell",
    "_de_env_status",
    "_push_token_to_de",
    "env_change_applied",
    "tell",
    "tell",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 Панель токенов",
     "data": "svc_token",
     "line": 864,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "rotate_loop",
   "file": "handlers_service.py",
   "line": 989,
   "title": "Раз в сутки смотрит, не пора ли. Время — воскресное утро, то же окно,",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "rotation_enabled",
    "get_moscow_now",
    "print",
    "rotate_api_token",
    "timedelta",
    "rotation_days",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 Панель токенов",
     "data": "svc_token",
     "line": 1020,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "token_screen",
   "file": "handlers_service.py",
   "line": 1030,
   "title": "Смена токена панелей: состояние и переключатель.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "rotation_days",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔁 Сменить сейчас",
     "data": "svc_tok_now",
     "line": 1053,
     "dynamic": false,
     "to": "token_now",
     "how": "точно"
    },
    {
     "label": "🔙 Мастер-сервер",
     "data": "menu_ru_server",
     "line": 1058,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    },
    {
     "label": "↩️ Вернуть прошлый ключ",
     "data": "svc_tok_back",
     "line": 1055,
     "dynamic": false,
     "to": "token_rollback",
     "how": "точно"
    }
   ]
  },
  {
   "id": "token_toggle",
   "file": "handlers_service.py",
   "line": 1064,
   "title": "Выключателя больше нет — смена идёт всегда.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "token_screen"
   ],
   "buttons": [
    {
     "label": "🔁 Сменить сейчас",
     "data": "svc_tok_now",
     "line": 1053,
     "dynamic": false,
     "to": "token_now",
     "how": "точно",
     "inherited": "token_screen"
    },
    {
     "label": "🔙 Мастер-сервер",
     "data": "menu_ru_server",
     "line": 1058,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно",
     "inherited": "token_screen"
    },
    {
     "label": "↩️ Вернуть прошлый ключ",
     "data": "svc_tok_back",
     "line": 1055,
     "dynamic": false,
     "to": "token_rollback",
     "how": "точно",
     "inherited": "token_screen"
    }
   ]
  },
  {
   "id": "token_rollback",
   "file": "handlers_service.py",
   "line": 1074,
   "title": "Возврат к прошлому ключу.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "request_env_change",
    "_push_env_to_de",
    "env_change_applied",
    "show_screen",
    "token_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 К панели токенов",
     "data": "svc_token",
     "line": 1099,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "token_now",
   "file": "handlers_service.py",
   "line": 1103,
   "title": "Смена по кнопке. Спрашивать подтверждение незачем: кнопка и есть",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "rotate_api_token",
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 К панели токенов",
     "data": "svc_token",
     "line": 1112,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "tell",
   "file": "handlers_service.py",
   "line": 857,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 Панель токенов",
     "data": "svc_token",
     "line": 864,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "users_list_menu",
   "file": "handlers_users.py",
   "line": 16,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "deregister_menu",
    "len",
    "max",
    "stop_bg_tasks",
    "api_session",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "int",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "⬅️ Назад",
     "data": "users_page_…",
     "line": 61,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    },
    {
     "label": "Вперед ➡️",
     "data": "users_page_…",
     "line": 62,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 66,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "… …",
     "data": "user_detail_…",
     "line": 55,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "render_user_detail",
   "file": "handlers_users.py",
   "line": 111,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "escape_md",
    "int",
    "len",
    "_tg_line",
    "api_session",
    "event_verdict",
    "dt_to_moscow",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "dict",
    "dt_to_moscow",
    "len",
    "len",
    "set",
    "connections_block",
    "delivery_text",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "int",
    "escape_md",
    "grant_text",
    "len",
    "_ago",
    "InlineKeyboardMarkup",
    "escape_md",
    "dt_to_moscow",
    "str"
   ],
   "buttons": [
    {
     "label": "🚦 Ограничение: …",
     "data": "svc_lim_…",
     "line": 289,
     "dynamic": false,
     "to": "peer_limit_screen",
     "how": "по приставке «svc_lim_»"
    },
    {
     "label": "📉 История нагрузки",
     "data": "svc_pchart_…",
     "line": 293,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "role_u_…",
     "line": 299,
     "dynamic": false,
     "to": "user_roles_screen",
     "how": "по приставке «role_u_»"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_user_…",
     "line": 300,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    },
    {
     "label": "🌐 Свои исключения · … / ",
     "data": "rt_menu_…",
     "line": 307,
     "dynamic": false,
     "to": "routes_menu",
     "how": "по приставке «rt_menu_»"
    },
    {
     "label": "✏️ Переименовать ключ",
     "data": "rename_user_…",
     "line": 310,
     "dynamic": false,
     "to": "шаг: rename_user_",
     "how": "по приставке «rename_user_»"
    },
    {
     "label": "🔗 Привязать TG ID",
     "data": "link_tg_…",
     "line": 311,
     "dynamic": false,
     "to": "шаг: link_tg_",
     "how": "по приставке «link_tg_»"
    },
    {
     "label": "⏸ Заморозить ключ",
     "data": "act_pause_…",
     "line": 279,
     "dynamic": false,
     "to": "pause_peer",
     "how": "по приставке «act_pause_»"
    },
    {
     "label": "▶️ Разморозить ключ",
     "data": "act_resume_…",
     "line": 281,
     "dynamic": false,
     "to": "resume_peer",
     "how": "по приставке «act_resume_»"
    },
    {
     "label": "«меняется»",
     "data": "xr_conn_…",
     "line": 298,
     "dynamic": true,
     "to": "connections_screen",
     "how": "по приставке «xr_conn_»"
    },
    {
     "label": "✂️ Отвязать TG ID",
     "data": "unlink_tg_…",
     "line": 313,
     "dynamic": false,
     "to": "шаг: unlink_tg_",
     "how": "по приставке «unlink_tg_»"
    },
    {
     "label": "🧹 Сбросить историю сетей",
     "data": "clear_ips_…",
     "line": 316,
     "dynamic": false,
     "to": "clear_user_ips",
     "how": "по приставке «clear_ips_»"
    },
    {
     "label": "📨 Конфиг AmneziaWG",
     "data": "act_resend_…",
     "line": 318,
     "dynamic": false,
     "to": "action_resend_config",
     "how": "по приставке «act_resend_»"
    },
    {
     "label": "❌ Удалить пользователя",
     "data": "confirm_delete_…",
     "line": 318,
     "dynamic": false,
     "to": "confirm_delete_menu",
     "how": "по приставке «confirm_delete_»"
    },
    {
     "label": "🔙 Назад к списку",
     "data": "users_page_0",
     "line": 318,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    }
   ]
  },
  {
   "id": "user_detail_menu",
   "file": "handlers_users.py",
   "line": 325,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "render_user_detail"
   ],
   "buttons": [
    {
     "label": "🚦 Ограничение: …",
     "data": "svc_lim_…",
     "line": 289,
     "dynamic": false,
     "to": "peer_limit_screen",
     "how": "по приставке «svc_lim_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "📉 История нагрузки",
     "data": "svc_pchart_…",
     "line": 293,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "role_u_…",
     "line": 299,
     "dynamic": false,
     "to": "user_roles_screen",
     "how": "по приставке «role_u_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_user_…",
     "line": 300,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🌐 Свои исключения · … / ",
     "data": "rt_menu_…",
     "line": 307,
     "dynamic": false,
     "to": "routes_menu",
     "how": "по приставке «rt_menu_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "✏️ Переименовать ключ",
     "data": "rename_user_…",
     "line": 310,
     "dynamic": false,
     "to": "шаг: rename_user_",
     "how": "по приставке «rename_user_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🔗 Привязать TG ID",
     "data": "link_tg_…",
     "line": 311,
     "dynamic": false,
     "to": "шаг: link_tg_",
     "how": "по приставке «link_tg_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "⏸ Заморозить ключ",
     "data": "act_pause_…",
     "line": 279,
     "dynamic": false,
     "to": "pause_peer",
     "how": "по приставке «act_pause_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "▶️ Разморозить ключ",
     "data": "act_resume_…",
     "line": 281,
     "dynamic": false,
     "to": "resume_peer",
     "how": "по приставке «act_resume_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "«меняется»",
     "data": "xr_conn_…",
     "line": 298,
     "dynamic": true,
     "to": "connections_screen",
     "how": "по приставке «xr_conn_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "✂️ Отвязать TG ID",
     "data": "unlink_tg_…",
     "line": 313,
     "dynamic": false,
     "to": "шаг: unlink_tg_",
     "how": "по приставке «unlink_tg_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🧹 Сбросить историю сетей",
     "data": "clear_ips_…",
     "line": 316,
     "dynamic": false,
     "to": "clear_user_ips",
     "how": "по приставке «clear_ips_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "📨 Конфиг AmneziaWG",
     "data": "act_resend_…",
     "line": 318,
     "dynamic": false,
     "to": "action_resend_config",
     "how": "по приставке «act_resend_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "❌ Удалить пользователя",
     "data": "confirm_delete_…",
     "line": 318,
     "dynamic": false,
     "to": "confirm_delete_menu",
     "how": "по приставке «confirm_delete_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🔙 Назад к списку",
     "data": "users_page_0",
     "line": 318,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»",
     "inherited": "render_user_detail"
    }
   ]
  },
  {
   "id": "clear_user_ips",
   "file": "handlers_users.py",
   "line": 331,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "user_detail_menu"
   ],
   "buttons": [
    {
     "label": "🚦 Ограничение: …",
     "data": "svc_lim_…",
     "line": 289,
     "dynamic": false,
     "to": "peer_limit_screen",
     "how": "по приставке «svc_lim_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "📉 История нагрузки",
     "data": "svc_pchart_…",
     "line": 293,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "role_u_…",
     "line": 299,
     "dynamic": false,
     "to": "user_roles_screen",
     "how": "по приставке «role_u_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_user_…",
     "line": 300,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🌐 Свои исключения · … / ",
     "data": "rt_menu_…",
     "line": 307,
     "dynamic": false,
     "to": "routes_menu",
     "how": "по приставке «rt_menu_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "✏️ Переименовать ключ",
     "data": "rename_user_…",
     "line": 310,
     "dynamic": false,
     "to": "шаг: rename_user_",
     "how": "по приставке «rename_user_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🔗 Привязать TG ID",
     "data": "link_tg_…",
     "line": 311,
     "dynamic": false,
     "to": "шаг: link_tg_",
     "how": "по приставке «link_tg_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "⏸ Заморозить ключ",
     "data": "act_pause_…",
     "line": 279,
     "dynamic": false,
     "to": "pause_peer",
     "how": "по приставке «act_pause_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "▶️ Разморозить ключ",
     "data": "act_resume_…",
     "line": 281,
     "dynamic": false,
     "to": "resume_peer",
     "how": "по приставке «act_resume_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "«меняется»",
     "data": "xr_conn_…",
     "line": 298,
     "dynamic": true,
     "to": "connections_screen",
     "how": "по приставке «xr_conn_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "✂️ Отвязать TG ID",
     "data": "unlink_tg_…",
     "line": 313,
     "dynamic": false,
     "to": "шаг: unlink_tg_",
     "how": "по приставке «unlink_tg_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🧹 Сбросить историю сетей",
     "data": "clear_ips_…",
     "line": 316,
     "dynamic": false,
     "to": "clear_user_ips",
     "how": "по приставке «clear_ips_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "📨 Конфиг AmneziaWG",
     "data": "act_resend_…",
     "line": 318,
     "dynamic": false,
     "to": "action_resend_config",
     "how": "по приставке «act_resend_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "❌ Удалить пользователя",
     "data": "confirm_delete_…",
     "line": 318,
     "dynamic": false,
     "to": "confirm_delete_menu",
     "how": "по приставке «confirm_delete_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🔙 Назад к списку",
     "data": "users_page_0",
     "line": 318,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»",
     "inherited": "user_detail_menu"
    }
   ]
  },
  {
   "id": "confirm_delete_menu",
   "file": "handlers_users.py",
   "line": 336,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "✅ ДА, Удалить",
     "data": "do_delete_…",
     "line": 341,
     "dynamic": false,
     "to": "action_delete_user",
     "how": "по приставке «do_delete_»"
    },
    {
     "label": "🔙 Нет, отмена",
     "data": "user_detail_…",
     "line": 341,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "action_delete_user",
   "file": "handlers_users.py",
   "line": 344,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "users_list_menu",
    "delete_peer",
    "reapply",
    "users_list_menu",
    "sync_person",
    "print"
   ],
   "buttons": [
    {
     "label": "⬅️ Назад",
     "data": "users_page_…",
     "line": 61,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»",
     "inherited": "users_list_menu"
    },
    {
     "label": "Вперед ➡️",
     "data": "users_page_…",
     "line": 62,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»",
     "inherited": "users_list_menu"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 66,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "users_list_menu"
    },
    {
     "label": "… …",
     "data": "user_detail_…",
     "line": 55,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "users_list_menu"
    }
   ]
  },
  {
   "id": "action_resend_config",
   "file": "handlers_users.py",
   "line": 374,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "open",
    "open",
    "open",
    "open"
   ],
   "buttons": []
  },
  {
   "id": "new_key_screen",
   "file": "handlers_users.py",
   "line": 429,
   "title": "Экран срока. Протокол здесь же строкой: по умолчанию Xray, AmneziaWG —",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "InlineKeyboardMarkup",
    "key_role_name",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "1 День",
     "data": "set_exp_1",
     "line": 453,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "1 Неделя",
     "data": "set_exp_7",
     "line": 454,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "1 Месяц",
     "data": "set_exp_30",
     "line": 455,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "Навсегда",
     "data": "set_exp_0",
     "line": 456,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "«меняется»",
     "data": "new_proto",
     "line": 457,
     "dynamic": true,
     "to": "new_key_screen",
     "how": "точно"
    },
    {
     "label": "🛡 Сменить доступ",
     "data": "new_key_role",
     "line": 458,
     "dynamic": false,
     "to": "new_key_role_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 459,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "new_key_role_screen",
   "file": "handlers_users.py",
   "line": 464,
   "title": "Выбор доступа для этого ключа. Общую настройку не трогает.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "key_role_name",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "chr"
   ],
   "buttons": [
    {
     "label": "✅  / Без роли · видит всех",
     "data": "nkrole_0",
     "line": 483,
     "dynamic": false,
     "to": "new_key_role_set",
     "how": "по приставке «nkrole_»"
    },
    {
     "label": "🔙 Назад",
     "data": "new_key_back",
     "line": 485,
     "dynamic": false,
     "to": "new_key_screen",
     "how": "точно"
    },
    {
     "label": "………",
     "data": "nkrole_…",
     "line": 481,
     "dynamic": false,
     "to": "new_key_role_set",
     "how": "по приставке «nkrole_»"
    }
   ]
  },
  {
   "id": "new_key_role_set",
   "file": "handlers_users.py",
   "line": 492,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "int",
    "new_key_screen"
   ],
   "buttons": [
    {
     "label": "1 День",
     "data": "set_exp_1",
     "line": 453,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "1 Неделя",
     "data": "set_exp_7",
     "line": 454,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "1 Месяц",
     "data": "set_exp_30",
     "line": 455,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "Навсегда",
     "data": "set_exp_0",
     "line": 456,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "«меняется»",
     "data": "new_proto",
     "line": 457,
     "dynamic": true,
     "to": "new_key_screen",
     "how": "точно",
     "inherited": "new_key_screen"
    },
    {
     "label": "🛡 Сменить доступ",
     "data": "new_key_role",
     "line": 458,
     "dynamic": false,
     "to": "new_key_role_screen",
     "how": "точно",
     "inherited": "new_key_screen"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 459,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "new_key_screen"
    }
   ]
  },
  {
   "id": "generate_key_request",
   "file": "handlers_users.py",
   "line": 502,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "deregister_menu",
    "stop_bg_tasks",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 505,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "finish_key_creation",
   "file": "handlers_users.py",
   "line": 510,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "to_self",
    "create_peer",
    "reapply",
    "timedelta",
    "key_role_name",
    "print",
    "xray_handout",
    "_owner_copy",
    "track_send",
    "InlineKeyboardButton",
    "apply_access_rules",
    "exit_kb",
    "send_client_menu",
    "_owner_copy",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "open",
    "open",
    "open",
    "open",
    "exit_kb",
    "exit_kb",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 В главное меню",
     "data": "back_to_main",
     "line": 603,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 В меню",
     "data": "back_to_main",
     "line": 608,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "connections_screen",
   "file": "handlers_xray.py",
   "line": 56,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "connections_block",
    "show_screen",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 104,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "📨 Конфиг Xray",
     "data": "xr_send_…",
     "line": 87,
     "dynamic": false,
     "to": "send_link",
     "how": "по приставке «xr_send_»"
    },
    {
     "label": "♻️ Перевыпустить ключ",
     "data": "xr_issue_…",
     "line": 91,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»"
    },
    {
     "label": "➕ Выдать Xray",
     "data": "xr_issue_…",
     "line": 102,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»"
    },
    {
     "label": "🔻 Убрать AmneziaWG",
     "data": "xr_dropawg_…",
     "line": 96,
     "dynamic": false,
     "to": "drop_awg",
     "how": "по приставке «xr_dropawg_»"
    },
    {
     "label": "🔒 Убрать AmneziaWG — рано",
     "data": "xr_why_…",
     "line": 99,
     "dynamic": false,
     "to": "why_locked",
     "how": "по приставке «xr_why_»"
    }
   ]
  },
  {
   "id": "why_locked",
   "file": "handlers_xray.py",
   "line": 110,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [],
   "buttons": []
  },
  {
   "id": "issue_xray",
   "file": "handlers_xray.py",
   "line": 116,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "connections_screen",
    "reapply"
   ],
   "buttons": [
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 104,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "connections_screen"
    },
    {
     "label": "📨 Конфиг Xray",
     "data": "xr_send_…",
     "line": 87,
     "dynamic": false,
     "to": "send_link",
     "how": "по приставке «xr_send_»",
     "inherited": "connections_screen"
    },
    {
     "label": "♻️ Перевыпустить ключ",
     "data": "xr_issue_…",
     "line": 91,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»",
     "inherited": "connections_screen"
    },
    {
     "label": "➕ Выдать Xray",
     "data": "xr_issue_…",
     "line": 102,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»",
     "inherited": "connections_screen"
    },
    {
     "label": "🔻 Убрать AmneziaWG",
     "data": "xr_dropawg_…",
     "line": 96,
     "dynamic": false,
     "to": "drop_awg",
     "how": "по приставке «xr_dropawg_»",
     "inherited": "connections_screen"
    },
    {
     "label": "🔒 Убрать AmneziaWG — рано",
     "data": "xr_why_…",
     "line": 99,
     "dynamic": false,
     "to": "why_locked",
     "how": "по приставке «xr_why_»",
     "inherited": "connections_screen"
    }
   ]
  },
  {
   "id": "send_link",
   "file": "handlers_xray.py",
   "line": 131,
   "title": "Отправляет человеку ссылку и QR в личные сообщения.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "instructions",
    "connections_screen",
    "track_send",
    "send_copyable",
    "send_copyable",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "open",
    "copy_button",
    "copy_button"
   ],
   "buttons": [
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 104,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "connections_screen"
    },
    {
     "label": "📨 Конфиг Xray",
     "data": "xr_send_…",
     "line": 87,
     "dynamic": false,
     "to": "send_link",
     "how": "по приставке «xr_send_»",
     "inherited": "connections_screen"
    },
    {
     "label": "♻️ Перевыпустить ключ",
     "data": "xr_issue_…",
     "line": 91,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»",
     "inherited": "connections_screen"
    },
    {
     "label": "➕ Выдать Xray",
     "data": "xr_issue_…",
     "line": 102,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»",
     "inherited": "connections_screen"
    },
    {
     "label": "🔻 Убрать AmneziaWG",
     "data": "xr_dropawg_…",
     "line": 96,
     "dynamic": false,
     "to": "drop_awg",
     "how": "по приставке «xr_dropawg_»",
     "inherited": "connections_screen"
    },
    {
     "label": "🔒 Убрать AmneziaWG — рано",
     "data": "xr_why_…",
     "line": 99,
     "dynamic": false,
     "to": "why_locked",
     "how": "по приставке «xr_why_»",
     "inherited": "connections_screen"
    }
   ]
  },
  {
   "id": "drop_awg",
   "file": "handlers_xray.py",
   "line": 180,
   "title": "Снимает пир AmneziaWG человеку, который уже переехал.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "connections_screen",
    "why_locked",
    "api_session"
   ],
   "buttons": [
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 104,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "connections_screen"
    },
    {
     "label": "📨 Конфиг Xray",
     "data": "xr_send_…",
     "line": 87,
     "dynamic": false,
     "to": "send_link",
     "how": "по приставке «xr_send_»",
     "inherited": "connections_screen"
    },
    {
     "label": "♻️ Перевыпустить ключ",
     "data": "xr_issue_…",
     "line": 91,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»",
     "inherited": "connections_screen"
    },
    {
     "label": "➕ Выдать Xray",
     "data": "xr_issue_…",
     "line": 102,
     "dynamic": false,
     "to": "issue_xray",
     "how": "по приставке «xr_issue_»",
     "inherited": "connections_screen"
    },
    {
     "label": "🔻 Убрать AmneziaWG",
     "data": "xr_dropawg_…",
     "line": 96,
     "dynamic": false,
     "to": "drop_awg",
     "how": "по приставке «xr_dropawg_»",
     "inherited": "connections_screen"
    },
    {
     "label": "🔒 Убрать AmneziaWG — рано",
     "data": "xr_why_…",
     "line": 99,
     "dynamic": false,
     "to": "why_locked",
     "how": "по приставке «xr_why_»",
     "inherited": "connections_screen"
    }
   ]
  },
  {
   "id": "protocols_menu",
   "file": "handlers_xray.py",
   "line": 203,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "len",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "max",
    "str"
   ],
   "buttons": [
    {
     "label": "🔷 AmneziaWG",
     "data": "proto_awg",
     "line": 229,
     "dynamic": false,
     "to": "awg_screen",
     "how": "точно"
    },
    {
     "label": "🔶 Xray",
     "data": "proto_xray",
     "line": 230,
     "dynamic": false,
     "to": "xray_screen",
     "how": "точно"
    },
    {
     "label": "🚚 Перевод людей на Xray",
     "data": "xr_move",
     "line": 231,
     "dynamic": false,
     "to": "move_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "awg_screen",
   "file": "handlers_xray.py",
   "line": 239,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "max"
   ],
   "buttons": [
    {
     "label": "🔑 Переезд на новый ключ",
     "data": "mig_menu",
     "line": 260,
     "dynamic": false,
     "to": "migration_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Протоколы",
     "data": "proto_menu",
     "line": 265,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно"
    },
    {
     "label": "⏹ Выключить протокол",
     "data": "proto_off_awg",
     "line": 262,
     "dynamic": false,
     "to": "switch_confirm",
     "how": "по приставке «proto_off_»"
    },
    {
     "label": "▶️ Включить протокол",
     "data": "proto_on_awg",
     "line": 264,
     "dynamic": false,
     "to": "switch_do",
     "how": "точно"
    }
   ]
  },
  {
   "id": "xray_screen",
   "file": "handlers_xray.py",
   "line": 272,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "any",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔄 Применить конфиг заново",
     "data": "xr_apply",
     "line": 302,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно"
    },
    {
     "label": "🎭 Маска входа",
     "data": "xr_mask",
     "line": 303,
     "dynamic": false,
     "to": "mask_screen",
     "how": "точно"
    },
    {
     "label": "📱 Приложения",
     "data": "xr_apps",
     "line": 304,
     "dynamic": false,
     "to": "apps_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Протоколы",
     "data": "proto_menu",
     "line": 312,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно"
    },
    {
     "label": "⏹ Выключить протокол",
     "data": "proto_off_xray",
     "line": 309,
     "dynamic": false,
     "to": "switch_confirm",
     "how": "по приставке «proto_off_»"
    },
    {
     "label": "▶️ Включить протокол",
     "data": "proto_on_xray",
     "line": 311,
     "dynamic": false,
     "to": "switch_do",
     "how": "точно"
    },
    {
     "label": "➡️ …",
     "data": "«меняется»",
     "line": 307,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "mask_screen",
   "file": "handlers_xray.py",
   "line": 336,
   "title": "Выбор домена, которым прикидывается вход.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "len",
    "show_screen",
    "InlineKeyboardButton",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "escape_md",
    "chr",
    "public_domain"
   ],
   "buttons": [
    {
     "label": "🔙 Xray",
     "data": "proto_xray",
     "line": 396,
     "dynamic": false,
     "to": "xray_screen",
     "how": "точно"
    },
    {
     "label": "…свой сайт · 0 мс",
     "data": "xr_mask_…",
     "line": 373,
     "dynamic": false,
     "to": "mask_set",
     "how": "по приставке «xr_mask_»"
    },
    {
     "label": "…… · …",
     "data": "xr_mask_…",
     "line": 387,
     "dynamic": false,
     "to": "mask_set",
     "how": "по приставке «xr_mask_»"
    }
   ]
  },
  {
   "id": "mask_set",
   "file": "handlers_xray.py",
   "line": 403,
   "title": "Ставит выбранную маску и сразу применяет конфиг.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "mask_screen",
    "mask_screen"
   ],
   "buttons": [
    {
     "label": "🔙 Xray",
     "data": "proto_xray",
     "line": 396,
     "dynamic": false,
     "to": "xray_screen",
     "how": "точно",
     "inherited": "mask_screen"
    },
    {
     "label": "…свой сайт · 0 мс",
     "data": "xr_mask_…",
     "line": 373,
     "dynamic": false,
     "to": "mask_set",
     "how": "по приставке «xr_mask_»",
     "inherited": "mask_screen"
    },
    {
     "label": "…… · …",
     "data": "xr_mask_…",
     "line": 387,
     "dynamic": false,
     "to": "mask_set",
     "how": "по приставке «xr_mask_»",
     "inherited": "mask_screen"
    }
   ]
  },
  {
   "id": "apply_now",
   "file": "handlers_xray.py",
   "line": 433,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "xray_screen"
   ],
   "buttons": [
    {
     "label": "🔄 Применить конфиг заново",
     "data": "xr_apply",
     "line": 302,
     "dynamic": false,
     "to": "apply_now",
     "how": "точно",
     "inherited": "xray_screen"
    },
    {
     "label": "🎭 Маска входа",
     "data": "xr_mask",
     "line": 303,
     "dynamic": false,
     "to": "mask_screen",
     "how": "точно",
     "inherited": "xray_screen"
    },
    {
     "label": "📱 Приложения",
     "data": "xr_apps",
     "line": 304,
     "dynamic": false,
     "to": "apps_screen",
     "how": "точно",
     "inherited": "xray_screen"
    },
    {
     "label": "🔙 Протоколы",
     "data": "proto_menu",
     "line": 312,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно",
     "inherited": "xray_screen"
    },
    {
     "label": "⏹ Выключить протокол",
     "data": "proto_off_xray",
     "line": 309,
     "dynamic": false,
     "to": "switch_confirm",
     "how": "по приставке «proto_off_»",
     "inherited": "xray_screen"
    },
    {
     "label": "▶️ Включить протокол",
     "data": "proto_on_xray",
     "line": 311,
     "dynamic": false,
     "to": "switch_do",
     "how": "точно",
     "inherited": "xray_screen"
    },
    {
     "label": "➡️ …",
     "data": "«меняется»",
     "line": 307,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "xray_screen"
    }
   ]
  },
  {
   "id": "apps_screen",
   "file": "handlers_xray.py",
   "line": 441,
   "title": "То же, что видит человек. Показывается владельцу, чтобы он мог глазами",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Xray",
     "data": "proto_xray",
     "line": 451,
     "dynamic": false,
     "to": "xray_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "switch_confirm",
   "file": "handlers_xray.py",
   "line": 459,
   "title": "Спрашивает подтверждение, показав, у скольких людей оборвётся связь.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "max",
    "len",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "⏹ Да, выключить",
     "data": "proto_offok_…",
     "line": 476,
     "dynamic": false,
     "to": "switch_do",
     "how": "по приставке «proto_offok_»"
    },
    {
     "label": "Отмена",
     "data": "proto_…",
     "line": 477,
     "dynamic": false,
     "to": null,
     "how": "подставляется на лету"
    }
   ]
  },
  {
   "id": "switch_do",
   "file": "handlers_xray.py",
   "line": 483,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "awg_screen",
    "xray_screen",
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "chr"
   ],
   "buttons": [
    {
     "label": "▶️ Включить всё равно",
     "data": "proto_onok_xray",
     "line": 503,
     "dynamic": false,
     "to": "switch_do",
     "how": "точно"
    },
    {
     "label": "Отмена",
     "data": "proto_xray",
     "line": 505,
     "dynamic": false,
     "to": "xray_screen",
     "how": "точно"
    },
    {
     "label": "➡️ …",
     "data": "«меняется»",
     "line": 502,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "move_screen",
   "file": "handlers_xray.py",
   "line": 521,
   "title": "Перевод по одному, по образцу переезда на новый ключ: выдали → ждём",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "show_screen",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "len",
    "len",
    "len",
    "InlineKeyboardMarkup",
    "escape_md",
    "escape_md",
    "len",
    "len"
   ],
   "buttons": [
    {
     "label": "👥 К списку людей",
     "data": "users_page_0",
     "line": 554,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    },
    {
     "label": "🔙 Протоколы",
     "data": "proto_menu",
     "line": 555,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "platform_keyboard",
   "file": "handlers_xray.py",
   "line": 573,
   "title": "Кнопки выбора системы. По две в ряд — так они остаются читаемыми",
   "side": "client",
   "kind": "menu",
   "calls": [
    "list",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "len",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "client_plat_…_…",
     "line": 579,
     "dynamic": true,
     "to": "client_platform_handler",
     "how": "по приставке «client_plat_»"
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 586,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "handout",
   "file": "handlers_xray.py",
   "line": 627,
   "title": "Выдаёт человеку подключение по Xray и рассылает ссылку.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "to_self",
    "instructions",
    "reapply",
    "send_copyable",
    "_owner_copy",
    "track_send",
    "exit_kb",
    "RuntimeError",
    "_owner_copy",
    "InlineKeyboardMarkup",
    "exit_kb",
    "exit_kb",
    "InlineKeyboardMarkup",
    "send_xray_profile",
    "exit_kb",
    "escape_md",
    "open",
    "InlineKeyboardButton",
    "copy_button"
   ],
   "buttons": [
    {
     "label": "🔙 В главное меню",
     "data": "back_to_main",
     "line": 724,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "alert_loop",
   "file": "monitor.py",
   "line": 498,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "int",
    "set",
    "api_session",
    "InlineKeyboardMarkup",
    "isinstance",
    "notify_admin",
    "api_session",
    "len",
    "escape_md",
    "notify_admin",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "len",
    "_xray_sync",
    "escape_md",
    "InlineKeyboardMarkup",
    "notify_admin",
    "api_session",
    "notify_admin",
    "notify_admin",
    "notify_admin",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🛡 В админку",
     "data": "back_to_main",
     "line": 511,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🆘 Связаться с Админом",
     "data": "support_start",
     "line": 593,
     "dynamic": false,
     "to": "support_start_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 623,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "expiration_loop",
   "file": "monitor.py",
   "line": 776,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "print",
    "InlineKeyboardMarkup",
    "escape_md",
    "int",
    "_ask_owner",
    "notify_admin",
    "InlineKeyboardButton",
    "timedelta"
   ],
   "buttons": [
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 809,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "weekly_report_loop",
   "file": "monitor.py",
   "line": 842,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "get_moscow_now",
    "round",
    "escape_md",
    "InlineKeyboardMarkup",
    "print",
    "api_session",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 885,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "announce_xray_connects",
   "file": "monitor.py",
   "line": 992,
   "title": "Один проход: кто вышел на связь по Xray впервые. Возвращает, скольких.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "escape_md",
    "InlineKeyboardMarkup",
    "notify_admin",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 1022,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "_send_xray_split_notice",
   "file": "monitor.py",
   "line": 1537,
   "title": "Человеку на Xray — готовый кусок, а не предложение перевыпустить ключ.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "copy_button",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "send_copyable",
    "print"
   ],
   "buttons": [
    {
     "label": "🌐 Список исключений",
     "data": "client_bypass_info",
     "line": 1560,
     "dynamic": false,
     "to": "client_bypass_info_handler",
     "how": "точно"
    },
    {
     "label": "🔕 Не напоминать",
     "data": "client_notify_off",
     "line": 1561,
     "dynamic": false,
     "to": "client_notify_off_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 1562,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "_send_upgrade_notices",
   "file": "monitor.py",
   "line": 1580,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "escape_md",
    "InlineKeyboardMarkup",
    "print",
    "_send_xray_split_notice",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "🔄 Перевыпустить этот ключ",
     "data": "client_regen_…",
     "line": 1610,
     "dynamic": false,
     "to": "client_regen_confirm",
     "how": "по приставке «client_regen_»"
    },
    {
     "label": "🌐 Список исключений",
     "data": "client_bypass_info",
     "line": 1611,
     "dynamic": false,
     "to": "client_bypass_info_handler",
     "how": "точно"
    },
    {
     "label": "🔕 Не напоминать",
     "data": "client_notify_off",
     "line": 1612,
     "dynamic": false,
     "to": "client_notify_off_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 1613,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "run_bypass_check_handler",
   "file": "monitor.py",
   "line": 1692,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "len",
    "_auto_absorb_drift",
    "len",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🌐 Список исключений",
     "data": "bypass_list",
     "line": 1719,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "📨 Разослать напоминания сейчас",
     "data": "bypass_notify_now",
     "line": 1720,
     "dynamic": false,
     "to": "bypass_notify_now_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1721,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1701,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "bypass_notify_now_handler",
   "file": "monitor.py",
   "line": 1725,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "_send_upgrade_notices",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1731,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "bypass_list_handler",
   "file": "monitor.py",
   "line": 1735,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "escape_md",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "➕ Добавить вручную",
     "data": "bypass_add_manual",
     "line": 1767,
     "dynamic": false,
     "to": "bypass_add_manual_handler",
     "how": "точно"
    },
    {
     "label": "📱 Профиль для Xray",
     "data": "bypass_happ",
     "line": 1768,
     "dynamic": false,
     "to": "bypass_happ_handler",
     "how": "точно"
    },
    {
     "label": "📨 Напомнить о перевыпуске",
     "data": "bypass_notify_now",
     "line": 1769,
     "dynamic": false,
     "to": "bypass_notify_now_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1770,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🗑 …",
     "data": "bypass_del_…",
     "line": 1751,
     "dynamic": false,
     "to": "bypass_del_handler",
     "how": "по приставке «bypass_del_»"
    }
   ]
  },
  {
   "id": "bypass_happ_handler",
   "file": "monitor.py",
   "line": 1773,
   "title": "Готовый профиль маршрутизации — чтобы проверить его на своём устройстве.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 К исключениям",
     "data": "bypass_list",
     "line": 1802,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "bypass_del_handler",
   "file": "monitor.py",
   "line": 1809,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "bypass_list_handler"
   ],
   "buttons": [
    {
     "label": "➕ Добавить вручную",
     "data": "bypass_add_manual",
     "line": 1767,
     "dynamic": false,
     "to": "bypass_add_manual_handler",
     "how": "точно",
     "inherited": "bypass_list_handler"
    },
    {
     "label": "📱 Профиль для Xray",
     "data": "bypass_happ",
     "line": 1768,
     "dynamic": false,
     "to": "bypass_happ_handler",
     "how": "точно",
     "inherited": "bypass_list_handler"
    },
    {
     "label": "📨 Напомнить о перевыпуске",
     "data": "bypass_notify_now",
     "line": 1769,
     "dynamic": false,
     "to": "bypass_notify_now_handler",
     "how": "точно",
     "inherited": "bypass_list_handler"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1770,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "bypass_list_handler"
    },
    {
     "label": "🗑 …",
     "data": "bypass_del_…",
     "line": 1751,
     "dynamic": false,
     "to": "bypass_del_handler",
     "how": "по приставке «bypass_del_»",
     "inherited": "bypass_list_handler"
    }
   ]
  },
  {
   "id": "bypass_add_manual_handler",
   "file": "monitor.py",
   "line": 1816,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "bypass_list",
     "line": 1820,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "bypass_add_request_handler",
   "file": "monitor.py",
   "line": 1828,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "escape_md",
    "InlineKeyboardMarkup",
    "escape_md",
    "escape_md",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔑 Мои ключи",
     "data": "client_my_keys",
     "line": 1854,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "main_menu",
   "file": "ui.py",
   "line": 7,
   "title": "Поддержка переехала внутрь раздела администрирования: сервисные настройки",
   "side": "client",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "📊 Дашборд",
     "data": "start_dashboard",
     "line": 12,
     "dynamic": false,
     "to": "start_dashboard",
     "how": "точно"
    },
    {
     "label": "📈 Трафик",
     "data": "vpn_graph",
     "line": 13,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    },
    {
     "label": "🔑 Создать ключ",
     "data": "gen_key",
     "line": 14,
     "dynamic": false,
     "to": "generate_key_request",
     "how": "точно"
    },
    {
     "label": "🟢 Онлайн · …",
     "data": "show_online",
     "line": 15,
     "dynamic": false,
     "to": "online_users_menu",
     "how": "точно"
    },
    {
     "label": "👥 Пользователи",
     "data": "users_page_0",
     "line": 16,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    },
    {
     "label": "⚙️ Администрирование · … / ",
     "data": "svc_menu",
     "line": 17,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🖥 Мастер-сервер",
     "data": "menu_ru_server",
     "line": 20,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    },
    {
     "label": "🌍 Клиент-сервер",
     "data": "menu_de_server",
     "line": 21,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    },
    {
     "label": "💾 Архивы и база",
     "data": "menu_backups",
     "line": 22,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    },
    {
     "label": "👤 Режим клиента",
     "data": "client_menu",
     "line": 23,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "📄 Что нового",
     "data": "svc_whatsnew",
     "line": 24,
     "dynamic": false,
     "to": "whats_new",
     "how": "точно"
    }
   ]
  },
  {
   "id": "menu_ru_server",
   "file": "ui.py",
   "line": 28,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить систему",
     "data": "check_update",
     "line": 30,
     "dynamic": false,
     "to": "check_update",
     "how": "точно"
    },
    {
     "label": "🔑 Панель токенов",
     "data": "svc_token",
     "line": 32,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    },
    {
     "label": "🛠 Аудит мастера",
     "data": "run_audit",
     "line": 33,
     "dynamic": false,
     "to": "run_audit_handler",
     "how": "точно"
    },
    {
     "label": "🛡 Проверка исключений",
     "data": "run_bypass_check",
     "line": 34,
     "dynamic": false,
     "to": "run_bypass_check_handler",
     "how": "точно"
    },
    {
     "label": "🌐 Исключения · мимо VPN",
     "data": "bypass_list",
     "line": 35,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "📢 Рассылка пользователям",
     "data": "maintenance_warn",
     "line": 36,
     "dynamic": false,
     "to": "шаг: maintenance_warn",
     "how": "точно"
    },
    {
     "label": "🚨 Перезагрузить мастер",
     "data": "confirm_reboot",
     "line": 37,
     "dynamic": false,
     "to": "confirm_reboot",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 38,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "menu_de_server",
   "file": "ui.py",
   "line": 42,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить клиент-сервер",
     "data": "de_update",
     "line": 44,
     "dynamic": false,
     "to": "de_update",
     "how": "точно"
    },
    {
     "label": "🛠 Аудит клиента",
     "data": "de_run_audit",
     "line": 45,
     "dynamic": false,
     "to": "de_run_audit",
     "how": "точно"
    },
    {
     "label": "📑 Журнал клиента",
     "data": "de_read_logs",
     "line": 46,
     "dynamic": false,
     "to": "de_read_logs",
     "how": "точно"
    },
    {
     "label": "🚨 Перезагрузить клиент",
     "data": "de_confirm_reboot",
     "line": 47,
     "dynamic": false,
     "to": "de_confirm_reboot",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 48,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "menu_backups",
   "file": "ui.py",
   "line": 52,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "💾 Копия мастера",
     "data": "backup",
     "line": 54,
     "dynamic": false,
     "to": "backup_now",
     "how": "точно"
    },
    {
     "label": "♻️ Восстановить мастер",
     "data": "restore",
     "line": 55,
     "dynamic": false,
     "to": "restore_cmd",
     "how": "точно"
    },
    {
     "label": "💾 Копия клиента",
     "data": "de_backup",
     "line": 56,
     "dynamic": false,
     "to": "de_backup",
     "how": "точно"
    },
    {
     "label": "📦 Список копий",
     "data": "backup_list",
     "line": 59,
     "dynamic": false,
     "to": "backups_list_screen",
     "how": "точно"
    },
    {
     "label": "📊 Сводка · Excel",
     "data": "download_logs",
     "line": 60,
     "dynamic": false,
     "to": "download_logs",
     "how": "точно"
    },
    {
     "label": "📊 База · Excel",
     "data": "export_excel",
     "line": 61,
     "dynamic": false,
     "to": "export_excel",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 62,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "copy_button",
   "file": "utils.py",
   "line": 450,
   "title": "Кнопка, которая кладёт текст в буфер по нажатию.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 465,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "exit_kb",
   "file": "utils.py",
   "line": 469,
   "title": "Клавиатура для сообщения, которым разговор закончился.",
   "side": "client",
   "kind": "menu",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 478,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 481,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 484,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "broadcast_message",
   "file": "utils.py",
   "line": 493,
   "title": "",
   "side": "client",
   "kind": "menu",
   "calls": [
    "list",
    "set",
    "print",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🛡 Панель управления",
     "data": "back_to_main",
     "line": 501,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 503,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pause_peer",
   "file": "wireguard_manager.py",
   "line": 56,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "api_session",
    "backup_wg_config",
    "Exception"
   ],
   "buttons": []
  },
  {
   "id": "resume_peer",
   "file": "wireguard_manager.py",
   "line": 62,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "api_session",
    "backup_wg_config",
    "Exception"
   ],
   "buttons": []
  },
  {
   "id": "шаг: maintenance_warn",
   "file": "bot.py",
   "line": 1399,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "✍️ Своя рассылка (свой текст)",
     "data": "broadcast_custom",
     "line": 1401,
     "dynamic": false,
     "to": "шаг: broadcast_custom",
     "how": "точно"
    },
    {
     "label": "⚠️ Стандартное: тех. работы",
     "data": "do_maintenance_warn",
     "line": 1402,
     "dynamic": false,
     "to": "broadcast_message",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1403,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: broadcast_custom",
   "file": "bot.py",
   "line": 1409,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1414,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: set_exp_",
   "file": "bot.py",
   "line": 1454,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "⏩ Пропустить",
     "data": "skip_tg_link",
     "line": 1463,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    },
    {
     "label": "🌍 Классический DNS (1.1.1.1)",
     "data": "set_dns_classic",
     "line": 1457,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🛡 AdBlock DNS (Без рекламы)",
     "data": "set_dns_adblock",
     "line": 1457,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1457,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: set_dns_",
   "file": "bot.py",
   "line": 1470,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "⏩ Пропустить",
     "data": "skip_tg_link",
     "line": 1472,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: rename_user_",
   "file": "bot.py",
   "line": 1481,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1483,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "шаг: link_tg_",
   "file": "bot.py",
   "line": 1493,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1495,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "шаг: unlink_tg_",
   "file": "bot.py",
   "line": 1501,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "❌ …",
     "data": "do_unlink_…_…",
     "line": 1504,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «do_unlink_»"
    },
    {
     "label": "🔙 Назад",
     "data": "user_detail_…",
     "line": 1505,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  }
 ],
 "dangling": [
  {
   "from": "pick_user",
   "label": "…/…",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "hits_screen",
   "label": "◀️ / ·",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "hits_screen",
   "label": "«меняется»",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "hits_screen",
   "label": "▶️ / ·",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "drop_seen",
   "label": "◀️ / ·",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "drop_seen",
   "label": "«меняется»",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "drop_seen",
   "label": "▶️ / ·",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "hits_seen_all",
   "label": "◀️ / ·",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "hits_seen_all",
   "label": "«меняется»",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "hits_seen_all",
   "label": "▶️ / ·",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "migration_issue",
   "label": "…/…",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "migration_send",
   "label": "…/…",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "members_screen",
   "label": "…/…",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "limits_screen",
   "label": "… пак/с",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "change_limit",
   "label": "… пак/с",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  },
  {
   "from": "pick_peer_screen",
   "label": "…/…",
   "data": "svc_noop",
   "to": "(без перехода)",
   "why": "обработчика с таким именем нет"
  }
 ],
 "counts": {
  "screens": 273,
  "buttons": 954,
  "admin": 228,
  "client": 45
 },
 "reachable": 188,
 "unrouted": 1
};

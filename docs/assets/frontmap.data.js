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
   "line": 215,
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
     "line": 249,
     "dynamic": false,
     "to": "client_donate",
     "how": "точно"
    }
   ]
  },
  {
   "id": "handle_message",
   "file": "bot.py",
   "line": 424,
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
     "line": 827,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "🌐 К списку исключений",
     "data": "bypass_list",
     "line": 809,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "🌐 К списку исключений",
     "data": "bypass_list",
     "line": 817,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 846,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 К списку обращений",
     "data": "support_admin_menu",
     "line": 881,
     "dynamic": false,
     "to": "support_admin_menu",
     "how": "точно"
    },
    {
     "label": "⏩ Пропустить/Отмена",
     "data": "skip_tg_link",
     "line": 922,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    },
    {
     "label": "🔑 Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 548,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Домен и сертификаты",
     "data": "psub_menu",
     "line": 550,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "✅ Добавить в исключения",
     "data": "bypass_addreq_…",
     "line": 756,
     "dynamic": false,
     "to": "bypass_add_request_handler",
     "how": "по приставке «bypass_addreq_»"
    },
    {
     "label": "❌ Отклонить",
     "data": "bypass_rejreq_…",
     "line": 757,
     "dynamic": false,
     "to": "bypass_add_request_handler",
     "how": "по приставке «bypass_rejreq_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 858,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔑 К сертификату внутренних имён",
     "data": "psub_zone",
     "line": 609,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    },
    {
     "label": "💳 Счета",
     "data": "bill_menu",
     "line": 638,
     "dynamic": false,
     "to": "menu",
     "how": "точно"
    },
    {
     "label": "💳 К сервису",
     "data": "«меняется»",
     "line": 674,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🔙 В меню",
     "data": "back_to_main",
     "line": 693,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "button_router",
   "file": "bot.py",
   "line": 959,
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
    "protocols_menu",
    "proto_awg_up",
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
    "bypass_add_manual_handler",
    "bypass_del_handler",
    "bypass_add_request_handler",
    "bypass_add_request_handler",
    "support_admin_menu",
    "support_user_tickets",
    "support_ticket_detail",
    "support_reply_start",
    "support_close_ticket",
    "users_list_menu",
    "user_detail_menu",
    "clear_user_ips",
    "user_detail_menu",
    "pause_peer",
    "user_detail_menu",
    "resume_peer",
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
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "finish_key_creation",
    "user_detail_menu",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
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
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
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
     "line": 1326,
     "dynamic": false,
     "to": "шаг: broadcast_custom",
     "how": "точно"
    },
    {
     "label": "⚠️ Стандартное: тех. работы",
     "data": "do_maintenance_warn",
     "line": 1327,
     "dynamic": false,
     "to": "broadcast_message",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1328,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🌍 Классический DNS (1.1.1.1)",
     "data": "set_dns_classic",
     "line": 1370,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🛡 AdBlock DNS (Без рекламы)",
     "data": "set_dns_adblock",
     "line": 1370,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1370,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "⏩ Пропустить",
     "data": "skip_tg_link",
     "line": 1375,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1386,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1398,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "❌ …",
     "data": "do_unlink_…_…",
     "line": 1407,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «do_unlink_»"
    },
    {
     "label": "🔙 Назад",
     "data": "user_detail_…",
     "line": 1408,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1339,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 В меню",
     "data": "back_to_main",
     "line": 1345,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "«меняется»",
     "line": 1087,
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
     "line": 179,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "1️⃣ Вписать имя узла",
     "data": "psub_domain",
     "line": 156,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "«меняется»",
     "data": "psub_domain",
     "line": 159,
     "dynamic": true,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔄 Обновить сертификат",
     "data": "psub_renew",
     "line": 171,
     "dynamic": false,
     "to": "renew_now",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🗑 Убрать сертификат",
     "data": "psub_off",
     "line": 173,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔑 Выпустить сертификат",
     "data": "psub_on",
     "line": 176,
     "dynamic": false,
     "to": "turn_on",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔑 Сертификат внутренних имён · есть",
     "data": "psub_zone",
     "line": 162,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "2️⃣ Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 166,
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
     "line": 179,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "1️⃣ Вписать имя узла",
     "data": "psub_domain",
     "line": 156,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "«меняется»",
     "data": "psub_domain",
     "line": 159,
     "dynamic": true,
     "to": "domain_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔄 Обновить сертификат",
     "data": "psub_renew",
     "line": 171,
     "dynamic": false,
     "to": "renew_now",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🗑 Убрать сертификат",
     "data": "psub_off",
     "line": 173,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔑 Выпустить сертификат",
     "data": "psub_on",
     "line": 176,
     "dynamic": false,
     "to": "turn_on",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "🔑 Сертификат внутренних имён · есть",
     "data": "psub_zone",
     "line": 162,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно",
     "inherited": "screen"
    },
    {
     "label": "2️⃣ Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 166,
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
   "title": "Исключения из запретов: общие или для одного человека.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "escape_md",
    "set",
    "set",
    "dict",
    "show_screen",
    "InlineKeyboardButton",
    "sorted",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "all_categories",
    "InlineKeyboardMarkup",
    "sorted",
    "chr",
    "escape_md",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "➕ Разрешить сайт",
     "data": "«меняется»",
     "line": 332,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 370,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "👤 Исключения для человека",
     "data": "flt_pick_0",
     "line": 336,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    },
    {
     "label": "🗑 …",
     "data": "flt_alw_del_…_…",
     "line": 339,
     "dynamic": false,
     "to": "allow_remove",
     "how": "по приставке «flt_alw_del_»"
    },
    {
     "label": "«меняется»",
     "data": "flt_xa_…_…",
     "line": 363,
     "dynamic": true,
     "to": "toggle_exempt",
     "how": "по приставке «flt_xa_»"
    }
   ]
  },
  {
   "id": "allow_add_request",
   "file": "filters.py",
   "line": 378,
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
     "line": 392,
     "dynamic": false,
     "to": "allow_screen",
     "how": "по приставке «flt_alw_»"
    }
   ]
  },
  {
   "id": "allow_add_entered",
   "file": "filters.py",
   "line": 398,
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
     "line": 420,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "allow_remove",
   "file": "filters.py",
   "line": 438,
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
     "line": 332,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "allow_screen"
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 370,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "allow_screen"
    },
    {
     "label": "👤 Исключения для человека",
     "data": "flt_pick_0",
     "line": 336,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»",
     "inherited": "allow_screen"
    },
    {
     "label": "🗑 …",
     "data": "flt_alw_del_…_…",
     "line": 339,
     "dynamic": false,
     "to": "allow_remove",
     "how": "по приставке «flt_alw_del_»",
     "inherited": "allow_screen"
    },
    {
     "label": "«меняется»",
     "data": "flt_xa_…_…",
     "line": 363,
     "dynamic": true,
     "to": "toggle_exempt",
     "how": "по приставке «flt_xa_»",
     "inherited": "allow_screen"
    }
   ]
  },
  {
   "id": "pool_list",
   "file": "filters.py",
   "line": 461,
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
     "line": 481,
     "dynamic": false,
     "to": "pool_name_request",
     "how": "точно"
    },
    {
     "label": "🔙 К фильтрам",
     "data": "flt_menu",
     "line": 485,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "📦 …",
     "data": "flt_pool_o_…",
     "line": 483,
     "dynamic": false,
     "to": "pool_open",
     "how": "по приставке «flt_pool_o_»"
    }
   ]
  },
  {
   "id": "pool_open",
   "file": "filters.py",
   "line": 492,
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
     "line": 507,
     "dynamic": false,
     "to": "pool_add_request",
     "how": "по приставке «flt_pool_a_»"
    },
    {
     "label": "🗑 Удалить группу",
     "data": "flt_pool_d_…",
     "line": 509,
     "dynamic": false,
     "to": "pool_delete",
     "how": "по приставке «flt_pool_d_»"
    },
    {
     "label": "🔙 К группам",
     "data": "flt_pool_list",
     "line": 510,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pool_add_request",
   "file": "filters.py",
   "line": 530,
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
     "line": 548,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "pool_name_request",
   "file": "filters.py",
   "line": 552,
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
     "line": 569,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pool_domains_entered",
   "file": "filters.py",
   "line": 613,
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
     "line": 654,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    },
    {
     "label": "🔙 К группам",
     "data": "flt_pool_list",
     "line": 624,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    },
    {
     "label": "📦 К группе",
     "data": "flt_pool_o_…",
     "line": 643,
     "dynamic": false,
     "to": "pool_open",
     "how": "по приставке «flt_pool_o_»"
    }
   ]
  },
  {
   "id": "pool_title_entered",
   "file": "filters.py",
   "line": 658,
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
     "line": 685,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "📦 К группам",
     "data": "flt_pool_list",
     "line": 672,
     "dynamic": false,
     "to": "pool_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "pool_delete",
   "file": "filters.py",
   "line": 690,
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
     "line": 481,
     "dynamic": false,
     "to": "pool_name_request",
     "how": "точно",
     "inherited": "pool_list"
    },
    {
     "label": "🔙 К фильтрам",
     "data": "flt_menu",
     "line": 485,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно",
     "inherited": "pool_list"
    },
    {
     "label": "📦 …",
     "data": "flt_pool_o_…",
     "line": 483,
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
   "line": 698,
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
     "line": 716,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "🔙 Фильтры",
     "data": "flt_menu",
     "line": 720,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "……",
     "data": "flt_user_…",
     "line": 710,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    },
    {
     "label": "⬅️",
     "data": "flt_pick_…",
     "line": 715,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    },
    {
     "label": "➡️",
     "data": "flt_pick_…",
     "line": 718,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    }
   ]
  },
  {
   "id": "user_filters_screen",
   "file": "filters.py",
   "line": 728,
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
     "line": 780,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🟢 Исключения из запретов",
     "data": "flt_alw_…",
     "line": 784,
     "dynamic": false,
     "to": "allow_screen",
     "how": "по приставке «flt_alw_»"
    },
    {
     "label": "🧹 К списку фильтров",
     "data": "flt_pick_0",
     "line": 786,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 778,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "toggle_exempt",
   "file": "filters.py",
   "line": 793,
   "title": "Снимает с человека общую категорию или возвращает её.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "set",
    "dict",
    "apply_filters",
    "all_categories",
    "allow_screen",
    "user_filters_screen"
   ],
   "buttons": [
    {
     "label": "➕ Разрешить сайт",
     "data": "«меняется»",
     "line": 332,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "allow_screen"
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 370,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "allow_screen"
    },
    {
     "label": "👤 Исключения для человека",
     "data": "flt_pick_0",
     "line": 336,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»",
     "inherited": "allow_screen"
    },
    {
     "label": "🗑 …",
     "data": "flt_alw_del_…_…",
     "line": 339,
     "dynamic": false,
     "to": "allow_remove",
     "how": "по приставке «flt_alw_del_»",
     "inherited": "allow_screen"
    },
    {
     "label": "«меняется»",
     "data": "flt_xa_…_…",
     "line": 363,
     "dynamic": true,
     "to": "toggle_exempt",
     "how": "по приставке «flt_xa_»",
     "inherited": "allow_screen"
    }
   ]
  },
  {
   "id": "toggle_filter",
   "file": "filters.py",
   "line": 818,
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
     "line": 780,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "🟢 Исключения из запретов",
     "data": "flt_alw_…",
     "line": 784,
     "dynamic": false,
     "to": "allow_screen",
     "how": "по приставке «flt_alw_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "🧹 К списку фильтров",
     "data": "flt_pick_0",
     "line": 786,
     "dynamic": false,
     "to": "pick_user",
     "how": "по приставке «flt_pick_»",
     "inherited": "user_filters_screen"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 778,
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
   "line": 827,
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
   "line": 834,
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
     "line": 866,
     "dynamic": false,
     "to": "custom_add_request",
     "how": "точно"
    },
    {
     "label": "🔙 Фильтры",
     "data": "flt_menu",
     "line": 870,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "flt_ctog_…",
     "line": 864,
     "dynamic": true,
     "to": "common_toggle",
     "how": "по приставке «flt_ctog_»"
    },
    {
     "label": "🚫 Свой список запретов",
     "data": "flt_clist",
     "line": 868,
     "dynamic": false,
     "to": "custom_list",
     "how": "точно"
    }
   ]
  },
  {
   "id": "common_toggle",
   "file": "filters.py",
   "line": 877,
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
     "line": 866,
     "dynamic": false,
     "to": "custom_add_request",
     "how": "точно",
     "inherited": "common_screen"
    },
    {
     "label": "🔙 Фильтры",
     "data": "flt_menu",
     "line": 870,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно",
     "inherited": "common_screen"
    },
    {
     "label": "«меняется»",
     "data": "flt_ctog_…",
     "line": 864,
     "dynamic": true,
     "to": "common_toggle",
     "how": "по приставке «flt_ctog_»",
     "inherited": "common_screen"
    },
    {
     "label": "🚫 Свой список запретов",
     "data": "flt_clist",
     "line": 868,
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
   "line": 887,
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
     "line": 895,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "custom_add_entered",
   "file": "filters.py",
   "line": 900,
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
     "line": 915,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "custom_list",
   "file": "filters.py",
   "line": 919,
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
     "line": 928,
     "dynamic": false,
     "to": "custom_remove",
     "how": "по приставке «flt_cdel_»"
    },
    {
     "label": "←",
     "data": "flt_cpg_…",
     "line": 932,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»"
    },
    {
     "label": "→",
     "data": "flt_cpg_…",
     "line": 934,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»"
    },
    {
     "label": "🔙 Общие правила",
     "data": "flt_common",
     "line": 937,
     "dynamic": false,
     "to": "common_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "custom_remove",
   "file": "filters.py",
   "line": 944,
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
     "line": 928,
     "dynamic": false,
     "to": "custom_remove",
     "how": "по приставке «flt_cdel_»",
     "inherited": "custom_list"
    },
    {
     "label": "←",
     "data": "flt_cpg_…",
     "line": 932,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»",
     "inherited": "custom_list"
    },
    {
     "label": "→",
     "data": "flt_cpg_…",
     "line": 934,
     "dynamic": false,
     "to": "custom_list",
     "how": "по приставке «flt_cpg_»",
     "inherited": "custom_list"
    },
    {
     "label": "🔙 Общие правила",
     "data": "flt_common",
     "line": 937,
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
   "line": 149,
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
   "line": 180,
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
     "line": 222,
     "dynamic": false,
     "to": "backup_now",
     "how": "точно"
    },
    {
     "label": "🔙 Архивы и база",
     "data": "menu_backups",
     "line": 223,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    }
   ]
  },
  {
   "id": "dashboard_loop",
   "file": "handlers_admin.py",
   "line": 269,
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
     "line": 273,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "start_dashboard",
   "file": "handlers_admin.py",
   "line": 281,
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
     "line": 273,
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
   "line": 294,
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
     "line": 297,
     "dynamic": false,
     "to": "do_reboot_server",
     "how": "точно"
    },
    {
     "label": "🔙 Нет, отмена",
     "data": "back_to_main",
     "line": 297,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "do_reboot_server",
   "file": "handlers_admin.py",
   "line": 300,
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
     "line": 308,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_confirm_reboot",
   "file": "handlers_admin.py",
   "line": 320,
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
     "line": 323,
     "dynamic": false,
     "to": "do_de_reboot_server",
     "how": "точно"
    },
    {
     "label": "🔙 Нет, отмена",
     "data": "back_to_main",
     "line": 323,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "do_de_reboot_server",
   "file": "handlers_admin.py",
   "line": 326,
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
     "line": 337,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 332,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 335,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_read_logs",
   "file": "handlers_admin.py",
   "line": 358,
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
     "line": 390,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    },
    {
     "label": "📄 Полный журнал",
     "data": "de_read_logs_full",
     "line": 388,
     "dynamic": false,
     "to": "de_read_logs",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 402,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 400,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_update",
   "file": "handlers_admin.py",
   "line": 443,
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
     "line": 459,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 453,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 457,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_backup",
   "file": "handlers_admin.py",
   "line": 461,
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
     "line": 484,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 478,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 482,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "de_run_audit",
   "file": "handlers_admin.py",
   "line": 486,
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
     "line": 521,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 500,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "send_de_audit_report",
   "file": "handlers_admin.py",
   "line": 523,
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
     "line": 563,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "graph_loop",
   "file": "handlers_admin.py",
   "line": 577,
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
     "line": 583,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "send_vpn_graph",
   "file": "handlers_admin.py",
   "line": 591,
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
     "line": 600,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "online_users_menu",
   "file": "handlers_admin.py",
   "line": 609,
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
     "line": 648,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 652,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "check_update",
   "file": "handlers_admin.py",
   "line": 654,
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
     "line": 679,
     "dynamic": false,
     "to": "do_update",
     "how": "точно"
    },
    {
     "label": "🇷🇺 Переустановить RU",
     "data": "do_update",
     "line": 682,
     "dynamic": false,
     "to": "do_update",
     "how": "точно"
    },
    {
     "label": "🔄 Обновить всё (RU + DE)",
     "data": "update_all",
     "line": 690,
     "dynamic": false,
     "to": "update_all",
     "how": "точно"
    },
    {
     "label": "🇩🇪 Обновить DE",
     "data": "de_update",
     "line": 691,
     "dynamic": false,
     "to": "de_update",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "toggle_auto_update",
     "line": 692,
     "dynamic": true,
     "to": "toggle_auto_update",
     "how": "точно"
    },
    {
     "label": "📅 Запланировать обновление",
     "data": "schedule_update",
     "line": 693,
     "dynamic": false,
     "to": "schedule_update_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 694,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "toggle_auto_update",
   "file": "handlers_admin.py",
   "line": 707,
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
     "line": 679,
     "dynamic": false,
     "to": "do_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🇷🇺 Переустановить RU",
     "data": "do_update",
     "line": 682,
     "dynamic": false,
     "to": "do_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🔄 Обновить всё (RU + DE)",
     "data": "update_all",
     "line": 690,
     "dynamic": false,
     "to": "update_all",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🇩🇪 Обновить DE",
     "data": "de_update",
     "line": 691,
     "dynamic": false,
     "to": "de_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "«меняется»",
     "data": "toggle_auto_update",
     "line": 692,
     "dynamic": true,
     "to": "toggle_auto_update",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "📅 Запланировать обновление",
     "data": "schedule_update",
     "line": 693,
     "dynamic": false,
     "to": "schedule_update_menu",
     "how": "точно",
     "inherited": "check_update"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 694,
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
   "line": 719,
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
     "line": 722,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "do_update",
   "file": "handlers_admin.py",
   "line": 733,
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
     "line": 498,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "broadcast_message"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 500,
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
   "line": 774,
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
     "line": 498,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "broadcast_message"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 500,
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
   "line": 812,
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
     "line": 836,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "👤 … (… шт)",
     "data": "supp_usr_…",
     "line": 834,
     "dynamic": false,
     "to": "support_user_tickets",
     "how": "по приставке «supp_usr_»"
    }
   ]
  },
  {
   "id": "support_user_tickets",
   "file": "handlers_admin.py",
   "line": 839,
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
     "line": 853,
     "dynamic": false,
     "to": "support_admin_menu",
     "how": "точно"
    },
    {
     "label": "[…] …",
     "data": "supp_tkt_…",
     "line": 851,
     "dynamic": false,
     "to": "support_ticket_detail",
     "how": "по приставке «supp_tkt_»"
    }
   ]
  },
  {
   "id": "support_ticket_detail",
   "file": "handlers_admin.py",
   "line": 856,
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
     "line": 871,
     "dynamic": false,
     "to": "support_reply_start",
     "how": "по приставке «supp_rep_»"
    },
    {
     "label": "✅ Закрыть без ответа",
     "data": "supp_clo_…",
     "line": 872,
     "dynamic": false,
     "to": "support_close_ticket",
     "how": "по приставке «supp_clo_»"
    },
    {
     "label": "🔙 К пользователю",
     "data": "supp_usr_…",
     "line": 873,
     "dynamic": false,
     "to": "support_user_tickets",
     "how": "по приставке «supp_usr_»"
    }
   ]
  },
  {
   "id": "support_reply_start",
   "file": "handlers_admin.py",
   "line": 877,
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
     "line": 883,
     "dynamic": false,
     "to": "support_ticket_detail",
     "how": "по приставке «supp_tkt_»"
    }
   ]
  },
  {
   "id": "support_close_ticket",
   "file": "handlers_admin.py",
   "line": 886,
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
     "line": 836,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "support_admin_menu"
    },
    {
     "label": "👤 … (… шт)",
     "data": "supp_usr_…",
     "line": 834,
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
   "line": 893,
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
   "line": 904,
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
   "line": 913,
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
     "line": 916,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "restore_file_handler",
   "file": "handlers_admin.py",
   "line": 921,
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
     "line": 957,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 939,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "export_excel",
   "file": "handlers_admin.py",
   "line": 960,
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
   "line": 967,
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
     "line": 1098,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 1036,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 1045,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "sub_menu_router",
   "file": "handlers_admin.py",
   "line": 1108,
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
   "line": 487,
   "title": "Карточка ключа глазами владельца ключа, а не администратора.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "get_live_peers_status",
    "int",
    "_days_left",
    "_traffic_24h",
    "_exceeded_24h",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "escape_md",
    "dt_to_moscow",
    "InlineKeyboardMarkup",
    "_limit_line",
    "_human_bytes",
    "_pause_reason",
    "_times"
   ],
   "buttons": [
    {
     "label": "📥 Конфиг AmneziaWG",
     "data": "client_download_…",
     "line": 543,
     "dynamic": false,
     "to": "client_download_handler",
     "how": "по приставке «client_download_»"
    },
    {
     "label": "⚡️ Проверить связь",
     "data": "check_conn_…",
     "line": 545,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»"
    },
    {
     "label": "🔄 Перевыпустить",
     "data": "client_regen_…",
     "line": 546,
     "dynamic": false,
     "to": "client_regen_confirm",
     "how": "по приставке «client_regen_»"
    },
    {
     "label": "❓ Как подключить",
     "data": "client_how_…",
     "line": 548,
     "dynamic": false,
     "to": "client_how_handler",
     "how": "по приставке «client_how_»"
    },
    {
     "label": "🔙 К списку ключей",
     "data": "client_my_keys",
     "line": 550,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_regen_all_confirm_handler",
   "file": "handlers_client.py",
   "line": 556,
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
     "line": 558,
     "dynamic": false,
     "to": "client_regen_all_action_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "client_my_keys",
     "line": 558,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_regen_all_action_handler",
   "file": "handlers_client.py",
   "line": 566,
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
     "line": 578,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_select_check_menu",
   "file": "handlers_client.py",
   "line": 612,
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
     "line": 623,
     "dynamic": false,
     "to": "client_check_all_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "client_menu",
     "line": 624,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "🔎 …",
     "data": "check_conn_…",
     "line": 621,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»"
    }
   ]
  },
  {
   "id": "client_check_all_handler",
   "file": "handlers_client.py",
   "line": 628,
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
     "line": 679,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "client_select_check",
     "line": 642,
     "dynamic": false,
     "to": "client_select_check_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_download_handler",
   "file": "handlers_client.py",
   "line": 684,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "open",
    "exit_kb",
    "open"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 475,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "exit_kb"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 478,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно",
     "inherited": "exit_kb"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 481,
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
   "line": 710,
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
   "line": 720,
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
     "line": 764,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_regen_confirm",
   "file": "handlers_client.py",
   "line": 767,
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
     "line": 769,
     "dynamic": false,
     "to": "client_regen_action",
     "how": "по приставке «do_client_regen_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "client_key_manage_…",
     "line": 769,
     "dynamic": false,
     "to": "client_key_manage_handler",
     "how": "по приставке «client_key_manage_»"
    }
   ]
  },
  {
   "id": "client_regen_action",
   "file": "handlers_client.py",
   "line": 780,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "safe_delete",
    "_queue_retire",
    "_issue_new_config",
    "InlineKeyboardMarkup",
    "exit_kb",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔙 В меню",
     "data": "client_menu",
     "line": 787,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "support_start_handler",
   "file": "handlers_client.py",
   "line": 808,
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
     "line": 825,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "🔑 …",
     "data": "support_audit_…",
     "line": 824,
     "dynamic": false,
     "to": "support_run_audit_handler",
     "how": "по приставке «support_audit_»"
    }
   ]
  },
  {
   "id": "support_run_audit_handler",
   "file": "handlers_client.py",
   "line": 829,
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
     "line": 893,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "❌ Не помогло, написать владельцу",
     "data": "support_ask_…",
     "line": 893,
     "dynamic": false,
     "to": "support_ask_msg_handler",
     "how": "по приставке «support_ask_»"
    },
    {
     "label": "🔙 Назад",
     "data": "client_menu",
     "line": 837,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "support_ask_msg_handler",
   "file": "handlers_client.py",
   "line": 897,
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
     "line": 904,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_bypass_info_handler",
   "file": "handlers_client.py",
   "line": 911,
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
     "line": 932,
     "dynamic": false,
     "to": "client_report_site_handler",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "client_notify_toggle",
     "line": 933,
     "dynamic": true,
     "to": "client_notify_toggle_handler",
     "how": "точно"
    },
    {
     "label": "🔙 В меню",
     "data": "client_menu",
     "line": 934,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_notify_toggle_handler",
   "file": "handlers_client.py",
   "line": 938,
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
     "line": 932,
     "dynamic": false,
     "to": "client_report_site_handler",
     "how": "точно",
     "inherited": "client_bypass_info_handler"
    },
    {
     "label": "«меняется»",
     "data": "client_notify_toggle",
     "line": 933,
     "dynamic": true,
     "to": "client_notify_toggle_handler",
     "how": "точно",
     "inherited": "client_bypass_info_handler"
    },
    {
     "label": "🔙 В меню",
     "data": "client_menu",
     "line": 934,
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
   "line": 946,
   "title": "Быстрое отключение прямо из текста уведомления (кнопка «Не напоминать»).",
   "side": "client",
   "kind": "screen",
   "calls": [],
   "buttons": []
  },
  {
   "id": "cmd_status",
   "file": "handlers_client.py",
   "line": 960,
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
     "line": 967,
     "dynamic": false,
     "to": "check_connection_handler",
     "how": "по приставке «check_conn_»"
    },
    {
     "label": "🚀 Проверить все ключи",
     "data": "client_check_all",
     "line": 968,
     "dynamic": false,
     "to": "client_check_all_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Меню",
     "data": "client_menu",
     "line": 969,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "cmd_support",
   "file": "handlers_client.py",
   "line": 972,
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
     "line": 979,
     "dynamic": false,
     "to": "support_run_audit_handler",
     "how": "по приставке «support_audit_»"
    },
    {
     "label": "🏠 Меню",
     "data": "client_menu",
     "line": 980,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "cmd_help",
   "file": "handlers_client.py",
   "line": 983,
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
     "line": 994,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_report_site_handler",
   "file": "handlers_client.py",
   "line": 997,
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
     "line": 1000,
     "dynamic": false,
     "to": "client_bypass_info_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_whats_new",
   "file": "handlers_client.py",
   "line": 1010,
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
     "line": 1039,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "platform_keyboard",
   "file": "handlers_client.py",
   "line": 1077,
   "title": "Кнопки выбора системы. По две в ряд — так они остаются читаемыми",
   "side": "client",
   "kind": "menu",
   "calls": [
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "len",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "«меняется»",
     "data": "client_plat_…_…",
     "line": 1082,
     "dynamic": true,
     "to": "client_platform_handler",
     "how": "по приставке «client_plat_»"
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 1089,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "client_how_handler",
   "file": "handlers_client.py",
   "line": 1122,
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
     "line": 1082,
     "dynamic": true,
     "to": "client_platform_handler",
     "how": "по приставке «client_plat_»",
     "inherited": "platform_keyboard"
    },
    {
     "label": "🔙 Назад",
     "data": "«меняется»",
     "line": 1089,
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
   "line": 1133,
   "title": "Где взять приложение — экран из личного кабинета.",
   "side": "client",
   "kind": "screen",
   "calls": [
    "awg_apps_markdown",
    "InlineKeyboardButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup"
   ],
   "buttons": [
    {
     "label": "🔑 Мои ключи",
     "data": "client_my_keys",
     "line": 1140,
     "dynamic": false,
     "to": "client_my_keys_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 1141,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "client_platform_handler",
   "file": "handlers_client.py",
   "line": 1148,
   "title": "Три шага под выбранную систему — и кнопка прислать конфиг заново.",
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
     "label": "📥 Прислать конфиг заново",
     "data": "client_download_…",
     "line": 1153,
     "dynamic": false,
     "to": "client_download_handler",
     "how": "по приставке «client_download_»"
    },
    {
     "label": "🔙 Другая система",
     "data": "client_how_…",
     "line": 1155,
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
   "line": 176,
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
     "line": 218,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🔕 Реже или выключить",
     "data": "hit_notify",
     "line": 219,
     "dynamic": false,
     "to": "notify_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "notify_screen",
   "file": "handlers_hits.py",
   "line": 247,
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
     "line": 263,
     "dynamic": true,
     "to": "notify_set",
     "how": "по приставке «hit_notify_»"
    },
    {
     "label": "🔕 Выключить сводку / 🔔 Включить сводку",
     "data": "hit_notify_off",
     "line": 267,
     "dynamic": false,
     "to": "notify_toggle",
     "how": "точно"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 270,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "notify_set",
   "file": "handlers_hits.py",
   "line": 276,
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
     "line": 263,
     "dynamic": true,
     "to": "notify_set",
     "how": "по приставке «hit_notify_»",
     "inherited": "notify_screen"
    },
    {
     "label": "🔕 Выключить сводку / 🔔 Включить сводку",
     "data": "hit_notify_off",
     "line": 267,
     "dynamic": false,
     "to": "notify_toggle",
     "how": "точно",
     "inherited": "notify_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 270,
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
   "line": 286,
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
     "line": 263,
     "dynamic": true,
     "to": "notify_set",
     "how": "по приставке «hit_notify_»",
     "inherited": "notify_screen"
    },
    {
     "label": "🔕 Выключить сводку / 🔔 Включить сводку",
     "data": "hit_notify_off",
     "line": 267,
     "dynamic": false,
     "to": "notify_toggle",
     "how": "точно",
     "inherited": "notify_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 270,
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
   "line": 297,
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
     "line": 343,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "svc_noop",
     "line": 346,
     "dynamic": true,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "▶️ / ·",
     "data": "svc_noop",
     "line": 348,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "🔎 Найти по номеру",
     "data": "hit_find",
     "line": 367,
     "dynamic": false,
     "to": "hit_find_request",
     "how": "точно"
    },
    {
     "label": "🗓 Сколько хранить",
     "data": "hit_keep",
     "line": 368,
     "dynamic": false,
     "to": "keep_screen",
     "how": "точно"
    },
    {
     "label": "🔔 Сводка",
     "data": "hit_notify",
     "line": 369,
     "dynamic": false,
     "to": "notify_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 370,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 335,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "«меняется»",
     "data": "hit_seen_all",
     "line": 359,
     "dynamic": true,
     "to": "hits_seen_all",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "hit_drop_seen",
     "line": 363,
     "dynamic": true,
     "to": "drop_seen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "drop_seen",
   "file": "handlers_hits.py",
   "line": 377,
   "title": "Удаляет просмотренные — сейчас, а не по сроку.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "hits_screen",
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🗑 Да, удалить",
     "data": "hit_drop_seen",
     "line": 395,
     "dynamic": false,
     "to": "drop_seen",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "hit_list",
     "line": 397,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "hit_open",
   "file": "handlers_hits.py",
   "line": 411,
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
     "line": 443,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🔑 Открыть ключ",
     "data": "user_detail_…",
     "line": 439,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🧹 Фильтры этого ключа",
     "data": "flt_user_…",
     "line": 441,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    }
   ]
  },
  {
   "id": "hit_find_request",
   "file": "handlers_hits.py",
   "line": 451,
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
     "line": 462,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "hit_find_entered",
   "file": "handlers_hits.py",
   "line": 466,
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
     "line": 506,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🚨 К инцидентам",
     "data": "hit_list",
     "line": 479,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🔑 Открыть ключ",
     "data": "user_detail_…",
     "line": 502,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🧹 Фильтры этого ключа",
     "data": "flt_user_…",
     "line": 504,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    }
   ]
  },
  {
   "id": "hits_seen_all",
   "file": "handlers_hits.py",
   "line": 517,
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
     "line": 343,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "svc_noop",
     "line": 346,
     "dynamic": true,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "▶️ / ·",
     "data": "svc_noop",
     "line": 348,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔎 Найти по номеру",
     "data": "hit_find",
     "line": 367,
     "dynamic": false,
     "to": "hit_find_request",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🗓 Сколько хранить",
     "data": "hit_keep",
     "line": 368,
     "dynamic": false,
     "to": "keep_screen",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔔 Сводка",
     "data": "hit_notify",
     "line": 369,
     "dynamic": false,
     "to": "notify_screen",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 370,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "«меняется»",
     "line": 335,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "hit_seen_all",
     "line": 359,
     "dynamic": true,
     "to": "hits_seen_all",
     "how": "точно",
     "inherited": "hits_screen"
    },
    {
     "label": "«меняется»",
     "data": "hit_drop_seen",
     "line": 363,
     "dynamic": true,
     "to": "drop_seen",
     "how": "точно",
     "inherited": "hits_screen"
    }
   ]
  },
  {
   "id": "keep_screen",
   "file": "handlers_hits.py",
   "line": 523,
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
     "line": 544,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_seen_»"
    },
    {
     "label": "«меняется»",
     "data": "hit_keep_new_…",
     "line": 547,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_new_»"
    },
    {
     "label": "🧹 Убрать то, что старше срока",
     "data": "hit_keep_now",
     "line": 550,
     "dynamic": false,
     "to": "keep_now",
     "how": "точно"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 552,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "keep_set",
   "file": "handlers_hits.py",
   "line": 560,
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
     "line": 544,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_seen_»",
     "inherited": "keep_screen"
    },
    {
     "label": "«меняется»",
     "data": "hit_keep_new_…",
     "line": 547,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_new_»",
     "inherited": "keep_screen"
    },
    {
     "label": "🧹 Убрать то, что старше срока",
     "data": "hit_keep_now",
     "line": 550,
     "dynamic": false,
     "to": "keep_now",
     "how": "точно",
     "inherited": "keep_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 552,
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
   "line": 578,
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
     "line": 544,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_seen_»",
     "inherited": "keep_screen"
    },
    {
     "label": "«меняется»",
     "data": "hit_keep_new_…",
     "line": 547,
     "dynamic": true,
     "to": "keep_set",
     "how": "по приставке «hit_keep_new_»",
     "inherited": "keep_screen"
    },
    {
     "label": "🧹 Убрать то, что старше срока",
     "data": "hit_keep_now",
     "line": 550,
     "dynamic": false,
     "to": "keep_now",
     "how": "точно",
     "inherited": "keep_screen"
    },
    {
     "label": "🔙 К инцидентам",
     "data": "hit_list",
     "line": 552,
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
    "str",
    "escape_md"
   ],
   "buttons": [
    {
     "label": "📋 Ждут решения",
     "data": "kd_list",
     "line": 185,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно",
     "inherited": "policy_menu"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 186,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "policy_menu"
    },
    {
     "label": "❓ Спрашивать снова",
     "data": "kd_pol_ask_…",
     "line": 191,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»",
     "inherited": "policy_menu"
    },
    {
     "label": "♻️ Продлевать само на … дн.",
     "data": "kd_pol_…_…",
     "line": 193,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»",
     "inherited": "policy_menu"
    },
    {
     "label": "📋 Ждут решения",
     "data": "kd_list",
     "line": 195,
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
   "line": 171,
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
     "line": 185,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Администрирование",
     "data": "svc_menu",
     "line": 186,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "❓ Спрашивать снова",
     "data": "kd_pol_ask_…",
     "line": 191,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»"
    },
    {
     "label": "♻️ Продлевать само на … дн.",
     "data": "kd_pol_…_…",
     "line": 193,
     "dynamic": false,
     "to": "set_policy",
     "how": "по приставке «kd_pol_»"
    },
    {
     "label": "📋 Ждут решения",
     "data": "kd_list",
     "line": 195,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "set_policy",
   "file": "handlers_keylife.py",
   "line": 201,
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
   "line": 215,
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
     "line": 235,
     "dynamic": false,
     "to": "do_delete",
     "how": "по приставке «kd_delok_»"
    },
    {
     "label": "✖️ Отмена",
     "data": "kd_open_…",
     "line": 236,
     "dynamic": false,
     "to": "decision_screen",
     "how": "по приставке «kd_open_»"
    }
   ]
  },
  {
   "id": "do_delete",
   "file": "handlers_keylife.py",
   "line": 242,
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
   "id": "protocols_menu",
   "file": "handlers_protocols.py",
   "line": 38,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "status",
    "show_screen",
    "show_screen",
    "escape_md",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "escape_md",
    "InlineKeyboardMarkup",
    "max",
    "str"
   ],
   "buttons": [
    {
     "label": "▶️ Поднять интерфейс",
     "data": "proto_on_awg",
     "line": 70,
     "dynamic": false,
     "to": "awg_up",
     "how": "точно"
    }
   ]
  },
  {
   "id": "awg_up",
   "file": "handlers_protocols.py",
   "line": 77,
   "title": "Поднимает интерфейс, если он лёг.",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "protocols_menu",
    "api_session"
   ],
   "buttons": [
    {
     "label": "▶️ Поднять интерфейс",
     "data": "proto_on_awg",
     "line": 70,
     "dynamic": false,
     "to": "awg_up",
     "how": "точно",
     "inherited": "protocols_menu"
    }
   ]
  },
  {
   "id": "screen",
   "file": "handlers_pubsub.py",
   "line": 73,
   "title": "Главный экран раздела: где мы стоим и что делать дальше.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "is_on",
    "state",
    "current_domain",
    "wildcard_on",
    "zone_api_on",
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
     "line": 179,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "1️⃣ Вписать имя узла",
     "data": "psub_domain",
     "line": 156,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно"
    },
    {
     "label": "«меняется»",
     "data": "psub_domain",
     "line": 159,
     "dynamic": true,
     "to": "domain_screen",
     "how": "точно"
    },
    {
     "label": "🔄 Обновить сертификат",
     "data": "psub_renew",
     "line": 171,
     "dynamic": false,
     "to": "renew_now",
     "how": "точно"
    },
    {
     "label": "🗑 Убрать сертификат",
     "data": "psub_off",
     "line": 173,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно"
    },
    {
     "label": "🔑 Выпустить сертификат",
     "data": "psub_on",
     "line": 176,
     "dynamic": false,
     "to": "turn_on",
     "how": "точно"
    },
    {
     "label": "🔑 Сертификат внутренних имён · есть",
     "data": "psub_zone",
     "line": 162,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    },
    {
     "label": "2️⃣ Сертификат внутренних имён",
     "data": "psub_zone",
     "line": 166,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "turn_on",
   "file": "handlers_pubsub.py",
   "line": 187,
   "title": "Выпустить сертификат. Без подтверждений: здесь ничего не теряют.",
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
     "line": 239,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "_wait_screen"
    },
    {
     "label": "🔄 Проверить сейчас",
     "data": "psub_menu",
     "line": 268,
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
   "line": 196,
   "title": "Убрать сертификат. Спрашиваем: страница отказа вернётся на",
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
     "label": "🗑 Да, убрать",
     "data": "psub_off",
     "line": 207,
     "dynamic": false,
     "to": "turn_off",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "psub_menu",
     "line": 208,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "renew_now",
   "file": "handlers_pubsub.py",
   "line": 219,
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
     "line": 239,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "_wait_screen"
    },
    {
     "label": "🔄 Проверить сейчас",
     "data": "psub_menu",
     "line": 268,
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
   "line": 229,
   "title": "Ждём хост и показываем, чем кончилось.",
   "side": "admin",
   "kind": "menu",
   "calls": [
    "range",
    "show_screen",
    "screen",
    "show_screen",
    "InlineKeyboardMarkup",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "InlineKeyboardButton"
   ],
   "buttons": [
    {
     "label": "🔄 Обновить",
     "data": "psub_menu",
     "line": 239,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "🔄 Проверить сейчас",
     "data": "psub_menu",
     "line": 268,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "domain_screen",
   "file": "handlers_pubsub.py",
   "line": 314,
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
     "line": 333,
     "dynamic": false,
     "to": "domain_ask",
     "how": "точно"
    },
    {
     "label": "🔙 Домен и сертификаты",
     "data": "psub_menu",
     "line": 337,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "🗑 Убрать имя",
     "data": "psub_domain_off",
     "line": 335,
     "dynamic": false,
     "to": "domain_off",
     "how": "точно"
    }
   ]
  },
  {
   "id": "domain_ask",
   "file": "handlers_pubsub.py",
   "line": 344,
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
     "line": 353,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "domain_off",
   "file": "handlers_pubsub.py",
   "line": 357,
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
     "line": 373,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_screen",
   "file": "handlers_pubsub.py",
   "line": 469,
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
     "line": 524,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "✏️ Задать доступ / ✏️ Заменить пару",
     "data": "psub_zone_set",
     "line": 513,
     "dynamic": false,
     "to": "zone_ask",
     "how": "точно"
    },
    {
     "label": "🌐 Сначала задать имя узла",
     "data": "psub_domain",
     "line": 522,
     "dynamic": false,
     "to": "domain_screen",
     "how": "точно"
    },
    {
     "label": "🔍 Проверить доступ",
     "data": "psub_zone_check",
     "line": 517,
     "dynamic": false,
     "to": "zone_check",
     "how": "точно"
    },
    {
     "label": "🗑 Убрать доступ",
     "data": "psub_zone_off",
     "line": 519,
     "dynamic": false,
     "to": "zone_off",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_ask",
   "file": "handlers_pubsub.py",
   "line": 532,
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
     "line": 541,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_password_step",
   "file": "handlers_pubsub.py",
   "line": 571,
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
     "line": 585,
     "dynamic": false,
     "to": "zone_generate",
     "how": "точно"
    },
    {
     "label": "✏️ Вписать свой",
     "data": "psub_zone_own",
     "line": 587,
     "dynamic": false,
     "to": "zone_own",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "psub_zone",
     "line": 589,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_own",
   "file": "handlers_pubsub.py",
   "line": 593,
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
     "line": 604,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_generate",
   "file": "handlers_pubsub.py",
   "line": 607,
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
     "line": 650,
     "dynamic": false,
     "to": "zone_check",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "psub_zone",
     "line": 652,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_off",
   "file": "handlers_pubsub.py",
   "line": 655,
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
     "line": 672,
     "dynamic": false,
     "to": "zone_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "zone_check",
   "file": "handlers_pubsub.py",
   "line": 676,
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
     "line": 694,
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
     "line": 258,
     "dynamic": true,
     "to": "toggle_mode",
     "how": "точно"
    },
    {
     "label": "📊 Нагрузка",
     "data": "svc_load",
     "line": 259,
     "dynamic": false,
     "to": "load_screen",
     "how": "точно"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 260,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно"
    },
    {
     "label": "🔀 Протоколы",
     "data": "proto_menu",
     "line": 261,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно"
    },
    {
     "label": "🌐 Домен и сертификаты",
     "data": "psub_menu",
     "line": 262,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "roles_menu",
     "line": 263,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_menu",
     "line": 264,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно"
    },
    {
     "label": "🚨 Инциденты · … / ",
     "data": "hit_list",
     "line": 265,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно"
    },
    {
     "label": "🏷 Имена в туннеле",
     "data": "dnm_menu",
     "line": 268,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно"
    },
    {
     "label": "💳 Донаты",
     "data": "don_menu",
     "line": 271,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно"
    },
    {
     "label": "🧾 Биллинг",
     "data": "bill_menu",
     "line": 274,
     "dynamic": false,
     "to": "menu",
     "how": "точно"
    },
    {
     "label": "📋 Ждут решения · … / ",
     "data": "kd_list",
     "line": 276,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно"
    },
    {
     "label": "📨 Не подключились · … / ",
     "data": "deliv_list",
     "line": 279,
     "dynamic": false,
     "to": "delivery_screen",
     "how": "точно"
    },
    {
     "label": "🧹 Чистка чата",
     "data": "chat_clean",
     "line": 285,
     "dynamic": false,
     "to": "screen",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 289,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "➡️ … · …",
     "data": "«меняется»",
     "line": 255,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🆘 Поддержка",
     "data": "support_admin_menu",
     "line": 288,
     "dynamic": false,
     "to": "support_admin_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "toggle_mode",
   "file": "handlers_service.py",
   "line": 296,
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
     "line": 321,
     "dynamic": false,
     "to": "set_mode",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "svc_menu",
     "line": 322,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "✅ Вернуть наблюдение",
     "data": "svc_mode_off",
     "line": 327,
     "dynamic": false,
     "to": "set_mode",
     "how": "точно"
    },
    {
     "label": "✖️ Отмена",
     "data": "svc_menu",
     "line": 328,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "set_mode",
   "file": "handlers_service.py",
   "line": 334,
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
     "line": 258,
     "dynamic": true,
     "to": "toggle_mode",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "📊 Нагрузка",
     "data": "svc_load",
     "line": 259,
     "dynamic": false,
     "to": "load_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 260,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🔀 Протоколы",
     "data": "proto_menu",
     "line": 261,
     "dynamic": false,
     "to": "protocols_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🌐 Домен и сертификаты",
     "data": "psub_menu",
     "line": 262,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "roles_menu",
     "line": 263,
     "dynamic": false,
     "to": "roles_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_menu",
     "line": 264,
     "dynamic": false,
     "to": "filters_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🚨 Инциденты · … / ",
     "data": "hit_list",
     "line": 265,
     "dynamic": false,
     "to": "hits_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🏷 Имена в туннеле",
     "data": "dnm_menu",
     "line": 268,
     "dynamic": false,
     "to": "names_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "💳 Донаты",
     "data": "don_menu",
     "line": 271,
     "dynamic": false,
     "to": "donate_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🧾 Биллинг",
     "data": "bill_menu",
     "line": 274,
     "dynamic": false,
     "to": "menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "📋 Ждут решения · … / ",
     "data": "kd_list",
     "line": 276,
     "dynamic": false,
     "to": "pending_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "📨 Не подключились · … / ",
     "data": "deliv_list",
     "line": 279,
     "dynamic": false,
     "to": "delivery_screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🧹 Чистка чата",
     "data": "chat_clean",
     "line": 285,
     "dynamic": false,
     "to": "screen",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 289,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "service_menu"
    },
    {
     "label": "➡️ … · …",
     "data": "«меняется»",
     "line": 255,
     "dynamic": true,
     "to": null,
     "how": null,
     "inherited": "service_menu"
    },
    {
     "label": "🆘 Поддержка",
     "data": "support_admin_menu",
     "line": 288,
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
   "line": 343,
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
     "line": 393,
     "dynamic": false,
     "to": "load_chart",
     "how": "точно"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 394,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 395,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    },
    {
     "label": "🗑 Снять: … · …",
     "data": "svc_ev_del_…",
     "line": 391,
     "dynamic": false,
     "to": "event_delete",
     "how": "по приставке «svc_ev_del_»"
    }
   ]
  },
  {
   "id": "event_delete",
   "file": "handlers_service.py",
   "line": 400,
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
     "line": 393,
     "dynamic": false,
     "to": "load_chart",
     "how": "точно",
     "inherited": "load_screen"
    },
    {
     "label": "⚖️ Лимиты",
     "data": "svc_limits",
     "line": 394,
     "dynamic": false,
     "to": "limits_screen",
     "how": "точно",
     "inherited": "load_screen"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 395,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно",
     "inherited": "load_screen"
    },
    {
     "label": "🗑 Снять: … · …",
     "data": "svc_ev_del_…",
     "line": 391,
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
   "line": 408,
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
     "line": 444,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно"
    },
    {
     "label": "… пак/с",
     "data": "svc_noop",
     "line": 446,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "➕ …",
     "data": "svc_limit_up",
     "line": 447,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно"
    },
    {
     "label": "3000",
     "data": "svc_limit_3000",
     "line": 448,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»"
    },
    {
     "label": "5000",
     "data": "svc_limit_5000",
     "line": 449,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»"
    },
    {
     "label": "6000",
     "data": "svc_limit_6000",
     "line": 450,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»"
    },
    {
     "label": "👥 Правила по людям",
     "data": "users_page_0",
     "line": 451,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 452,
     "dynamic": false,
     "to": "service_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "change_limit",
   "file": "handlers_service.py",
   "line": 459,
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
     "line": 444,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно",
     "inherited": "limits_screen"
    },
    {
     "label": "… пак/с",
     "data": "svc_noop",
     "line": 446,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно",
     "inherited": "limits_screen"
    },
    {
     "label": "➕ …",
     "data": "svc_limit_up",
     "line": 447,
     "dynamic": false,
     "to": "change_limit",
     "how": "точно",
     "inherited": "limits_screen"
    },
    {
     "label": "3000",
     "data": "svc_limit_3000",
     "line": 448,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»",
     "inherited": "limits_screen"
    },
    {
     "label": "5000",
     "data": "svc_limit_5000",
     "line": 449,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»",
     "inherited": "limits_screen"
    },
    {
     "label": "6000",
     "data": "svc_limit_6000",
     "line": 450,
     "dynamic": false,
     "to": "change_limit",
     "how": "по приставке «svc_limit_»",
     "inherited": "limits_screen"
    },
    {
     "label": "👥 Правила по людям",
     "data": "users_page_0",
     "line": 451,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»",
     "inherited": "limits_screen"
    },
    {
     "label": "🔙 Назад",
     "data": "svc_menu",
     "line": 452,
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
   "line": 478,
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
     "line": 558,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "✂️ Свой предел · … пак/с",
     "data": "svc_rule_custom_…",
     "line": 560,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "♾ Снять ограничение",
     "data": "svc_rule_unlimited_…",
     "line": 562,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "⏱ Придушить на сутки · … пак/с",
     "data": "svc_rule_day_…",
     "line": 564,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»",
     "inherited": "peer_limit_screen"
    },
    {
     "label": "🔙 К пользователю",
     "data": "user_detail_…",
     "line": 566,
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
   "line": 506,
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
     "line": 558,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "✂️ Свой предел · … пак/с",
     "data": "svc_rule_custom_…",
     "line": 560,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "♾ Снять ограничение",
     "data": "svc_rule_unlimited_…",
     "line": 562,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "⏱ Придушить на сутки · … пак/с",
     "data": "svc_rule_day_…",
     "line": 564,
     "dynamic": false,
     "to": "set_peer_rule",
     "how": "по приставке «svc_rule_»"
    },
    {
     "label": "🔙 К пользователю",
     "data": "user_detail_…",
     "line": 566,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "load_chart",
   "file": "handlers_service.py",
   "line": 572,
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
     "line": 628,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "📊 Графики",
     "data": "vpn_graph",
     "line": 629,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    },
    {
     "label": "🔙 К человеку",
     "data": "user_detail_…",
     "line": 626,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    },
    {
     "label": "🔙 Графики",
     "data": "vpn_graph",
     "line": 609,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "charts_screen",
   "file": "handlers_service.py",
   "line": 639,
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
     "line": 692,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "🔙 Графики",
     "data": "vpn_graph",
     "line": 693,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    },
    {
     "label": "📉 …",
     "data": "svc_pchart_…",
     "line": 687,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»"
    }
   ]
  },
  {
   "id": "pick_peer_screen",
   "file": "handlers_service.py",
   "line": 700,
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
     "line": 709,
     "dynamic": true,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»"
    },
    {
     "label": "…/…",
     "data": "svc_noop",
     "line": 715,
     "dynamic": false,
     "to": "(без перехода)",
     "how": "точно"
    },
    {
     "label": "🔙 Графики",
     "data": "vpn_graph",
     "line": 719,
     "dynamic": false,
     "to": "graphs_menu",
     "how": "точно"
    },
    {
     "label": "⬅️",
     "data": "svc_pick_…",
     "line": 714,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "➡️",
     "data": "svc_pick_…",
     "line": 717,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    }
   ]
  },
  {
   "id": "graphs_menu",
   "file": "handlers_service.py",
   "line": 726,
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
     "line": 755,
     "dynamic": false,
     "to": "send_vpn_graph",
     "how": "точно"
    },
    {
     "label": "🚦 Нагрузка · скорость и пакеты",
     "data": "svc_chart",
     "line": 756,
     "dynamic": false,
     "to": "load_chart",
     "how": "точно"
    },
    {
     "label": "📉 Подбор · … / ",
     "data": "svc_charts",
     "line": 757,
     "dynamic": false,
     "to": "charts_screen",
     "how": "точно"
    },
    {
     "label": "👤 Выбрать человека",
     "data": "svc_pick_0",
     "line": 760,
     "dynamic": false,
     "to": "pick_peer_screen",
     "how": "по приставке «svc_pick_»"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 761,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "whats_new",
   "file": "handlers_service.py",
   "line": 767,
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
     "line": 777,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "ensure_api_token",
   "file": "handlers_service.py",
   "line": 829,
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
     "line": 857,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "rotate_loop",
   "file": "handlers_service.py",
   "line": 982,
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
     "line": 1013,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "token_screen",
   "file": "handlers_service.py",
   "line": 1023,
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
     "line": 1046,
     "dynamic": false,
     "to": "token_now",
     "how": "точно"
    },
    {
     "label": "🔙 Мастер-сервер",
     "data": "menu_ru_server",
     "line": 1051,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно"
    },
    {
     "label": "↩️ Вернуть прошлый ключ",
     "data": "svc_tok_back",
     "line": 1048,
     "dynamic": false,
     "to": "token_rollback",
     "how": "точно"
    }
   ]
  },
  {
   "id": "token_toggle",
   "file": "handlers_service.py",
   "line": 1057,
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
     "line": 1046,
     "dynamic": false,
     "to": "token_now",
     "how": "точно",
     "inherited": "token_screen"
    },
    {
     "label": "🔙 Мастер-сервер",
     "data": "menu_ru_server",
     "line": 1051,
     "dynamic": false,
     "to": "sub_menu_router",
     "how": "точно",
     "inherited": "token_screen"
    },
    {
     "label": "↩️ Вернуть прошлый ключ",
     "data": "svc_tok_back",
     "line": 1048,
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
   "line": 1067,
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
     "line": 1092,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "token_now",
   "file": "handlers_service.py",
   "line": 1096,
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
     "line": 1105,
     "dynamic": false,
     "to": "token_screen",
     "how": "точно"
    }
   ]
  },
  {
   "id": "tell",
   "file": "handlers_service.py",
   "line": 850,
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
     "line": 857,
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
    "dict",
    "dt_to_moscow",
    "len",
    "len",
    "set",
    "delivery_text",
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
     "line": 277,
     "dynamic": false,
     "to": "peer_limit_screen",
     "how": "по приставке «svc_lim_»"
    },
    {
     "label": "📉 История нагрузки",
     "data": "svc_pchart_…",
     "line": 281,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "role_u_…",
     "line": 283,
     "dynamic": false,
     "to": "user_roles_screen",
     "how": "по приставке «role_u_»"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_user_…",
     "line": 284,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»"
    },
    {
     "label": "✏️ Переименовать ключ",
     "data": "rename_user_…",
     "line": 285,
     "dynamic": false,
     "to": "шаг: rename_user_",
     "how": "по приставке «rename_user_»"
    },
    {
     "label": "🔗 Привязать TG ID",
     "data": "link_tg_…",
     "line": 286,
     "dynamic": false,
     "to": "шаг: link_tg_",
     "how": "по приставке «link_tg_»"
    },
    {
     "label": "⏸ Заморозить ключ",
     "data": "act_pause_…",
     "line": 267,
     "dynamic": false,
     "to": "pause_peer",
     "how": "по приставке «act_pause_»"
    },
    {
     "label": "▶️ Разморозить ключ",
     "data": "act_resume_…",
     "line": 269,
     "dynamic": false,
     "to": "resume_peer",
     "how": "по приставке «act_resume_»"
    },
    {
     "label": "✂️ Отвязать TG ID",
     "data": "unlink_tg_…",
     "line": 288,
     "dynamic": false,
     "to": "шаг: unlink_tg_",
     "how": "по приставке «unlink_tg_»"
    },
    {
     "label": "🧹 Сбросить историю сетей",
     "data": "clear_ips_…",
     "line": 291,
     "dynamic": false,
     "to": "clear_user_ips",
     "how": "по приставке «clear_ips_»"
    },
    {
     "label": "📨 Конфиг AmneziaWG",
     "data": "act_resend_…",
     "line": 293,
     "dynamic": false,
     "to": "action_resend_config",
     "how": "по приставке «act_resend_»"
    },
    {
     "label": "❌ Удалить пользователя",
     "data": "confirm_delete_…",
     "line": 293,
     "dynamic": false,
     "to": "confirm_delete_menu",
     "how": "по приставке «confirm_delete_»"
    },
    {
     "label": "🔙 Назад к списку",
     "data": "users_page_0",
     "line": 293,
     "dynamic": false,
     "to": "users_list_menu",
     "how": "по приставке «users_page_»"
    }
   ]
  },
  {
   "id": "user_detail_menu",
   "file": "handlers_users.py",
   "line": 300,
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
     "line": 277,
     "dynamic": false,
     "to": "peer_limit_screen",
     "how": "по приставке «svc_lim_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "📉 История нагрузки",
     "data": "svc_pchart_…",
     "line": 281,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "role_u_…",
     "line": 283,
     "dynamic": false,
     "to": "user_roles_screen",
     "how": "по приставке «role_u_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_user_…",
     "line": 284,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "✏️ Переименовать ключ",
     "data": "rename_user_…",
     "line": 285,
     "dynamic": false,
     "to": "шаг: rename_user_",
     "how": "по приставке «rename_user_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🔗 Привязать TG ID",
     "data": "link_tg_…",
     "line": 286,
     "dynamic": false,
     "to": "шаг: link_tg_",
     "how": "по приставке «link_tg_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "⏸ Заморозить ключ",
     "data": "act_pause_…",
     "line": 267,
     "dynamic": false,
     "to": "pause_peer",
     "how": "по приставке «act_pause_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "▶️ Разморозить ключ",
     "data": "act_resume_…",
     "line": 269,
     "dynamic": false,
     "to": "resume_peer",
     "how": "по приставке «act_resume_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "✂️ Отвязать TG ID",
     "data": "unlink_tg_…",
     "line": 288,
     "dynamic": false,
     "to": "шаг: unlink_tg_",
     "how": "по приставке «unlink_tg_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🧹 Сбросить историю сетей",
     "data": "clear_ips_…",
     "line": 291,
     "dynamic": false,
     "to": "clear_user_ips",
     "how": "по приставке «clear_ips_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "📨 Конфиг AmneziaWG",
     "data": "act_resend_…",
     "line": 293,
     "dynamic": false,
     "to": "action_resend_config",
     "how": "по приставке «act_resend_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "❌ Удалить пользователя",
     "data": "confirm_delete_…",
     "line": 293,
     "dynamic": false,
     "to": "confirm_delete_menu",
     "how": "по приставке «confirm_delete_»",
     "inherited": "render_user_detail"
    },
    {
     "label": "🔙 Назад к списку",
     "data": "users_page_0",
     "line": 293,
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
   "line": 306,
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
     "line": 277,
     "dynamic": false,
     "to": "peer_limit_screen",
     "how": "по приставке «svc_lim_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "📉 История нагрузки",
     "data": "svc_pchart_…",
     "line": 281,
     "dynamic": false,
     "to": "load_chart",
     "how": "по приставке «svc_pchart_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🛡 Доступы · роли",
     "data": "role_u_…",
     "line": 283,
     "dynamic": false,
     "to": "user_roles_screen",
     "how": "по приставке «role_u_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🧹 Фильтры",
     "data": "flt_user_…",
     "line": 284,
     "dynamic": false,
     "to": "user_filters_screen",
     "how": "по приставке «flt_user_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "✏️ Переименовать ключ",
     "data": "rename_user_…",
     "line": 285,
     "dynamic": false,
     "to": "шаг: rename_user_",
     "how": "по приставке «rename_user_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🔗 Привязать TG ID",
     "data": "link_tg_…",
     "line": 286,
     "dynamic": false,
     "to": "шаг: link_tg_",
     "how": "по приставке «link_tg_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "⏸ Заморозить ключ",
     "data": "act_pause_…",
     "line": 267,
     "dynamic": false,
     "to": "pause_peer",
     "how": "по приставке «act_pause_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "▶️ Разморозить ключ",
     "data": "act_resume_…",
     "line": 269,
     "dynamic": false,
     "to": "resume_peer",
     "how": "по приставке «act_resume_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "✂️ Отвязать TG ID",
     "data": "unlink_tg_…",
     "line": 288,
     "dynamic": false,
     "to": "шаг: unlink_tg_",
     "how": "по приставке «unlink_tg_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🧹 Сбросить историю сетей",
     "data": "clear_ips_…",
     "line": 291,
     "dynamic": false,
     "to": "clear_user_ips",
     "how": "по приставке «clear_ips_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "📨 Конфиг AmneziaWG",
     "data": "act_resend_…",
     "line": 293,
     "dynamic": false,
     "to": "action_resend_config",
     "how": "по приставке «act_resend_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "❌ Удалить пользователя",
     "data": "confirm_delete_…",
     "line": 293,
     "dynamic": false,
     "to": "confirm_delete_menu",
     "how": "по приставке «confirm_delete_»",
     "inherited": "user_detail_menu"
    },
    {
     "label": "🔙 Назад к списку",
     "data": "users_page_0",
     "line": 293,
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
   "line": 311,
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
     "line": 316,
     "dynamic": false,
     "to": "action_delete_user",
     "how": "по приставке «do_delete_»"
    },
    {
     "label": "🔙 Нет, отмена",
     "data": "user_detail_…",
     "line": 316,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "action_delete_user",
   "file": "handlers_users.py",
   "line": 319,
   "title": "",
   "side": "admin",
   "kind": "screen",
   "calls": [
    "users_list_menu",
    "delete_peer",
    "reapply",
    "users_list_menu"
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
   "line": 342,
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
   "line": 383,
   "title": "Экран срока. Выдаётся AmneziaWG — файлом конфига и QR.",
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
    "escape_md"
   ],
   "buttons": [
    {
     "label": "1 День",
     "data": "set_exp_1",
     "line": 398,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "1 Неделя",
     "data": "set_exp_7",
     "line": 399,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "1 Месяц",
     "data": "set_exp_30",
     "line": 400,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "Навсегда",
     "data": "set_exp_0",
     "line": 401,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»"
    },
    {
     "label": "🛡 Сменить доступ",
     "data": "new_key_role",
     "line": 402,
     "dynamic": false,
     "to": "new_key_role_screen",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 403,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "new_key_role_screen",
   "file": "handlers_users.py",
   "line": 408,
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
     "line": 427,
     "dynamic": false,
     "to": "new_key_role_set",
     "how": "по приставке «nkrole_»"
    },
    {
     "label": "🔙 Назад",
     "data": "new_key_back",
     "line": 429,
     "dynamic": false,
     "to": "new_key_screen",
     "how": "точно"
    },
    {
     "label": "………",
     "data": "nkrole_…",
     "line": 425,
     "dynamic": false,
     "to": "new_key_role_set",
     "how": "по приставке «nkrole_»"
    }
   ]
  },
  {
   "id": "new_key_role_set",
   "file": "handlers_users.py",
   "line": 436,
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
     "line": 398,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "1 Неделя",
     "data": "set_exp_7",
     "line": 399,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "1 Месяц",
     "data": "set_exp_30",
     "line": 400,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "Навсегда",
     "data": "set_exp_0",
     "line": 401,
     "dynamic": false,
     "to": "шаг: set_exp_",
     "how": "по приставке «set_exp_»",
     "inherited": "new_key_screen"
    },
    {
     "label": "🛡 Сменить доступ",
     "data": "new_key_role",
     "line": 402,
     "dynamic": false,
     "to": "new_key_role_screen",
     "how": "точно",
     "inherited": "new_key_screen"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 403,
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
   "line": 446,
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
     "line": 449,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "finish_key_creation",
   "file": "handlers_users.py",
   "line": 454,
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
     "line": 537,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 В меню",
     "data": "back_to_main",
     "line": 542,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "alert_loop",
   "file": "monitor.py",
   "line": 407,
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
     "line": 420,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🆘 Связаться с Админом",
     "data": "support_start",
     "line": 501,
     "dynamic": false,
     "to": "support_start_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 531,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "expiration_loop",
   "file": "monitor.py",
   "line": 683,
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
     "line": 716,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "weekly_report_loop",
   "file": "monitor.py",
   "line": 749,
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
     "line": 792,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "_send_upgrade_notices",
   "file": "monitor.py",
   "line": 1294,
   "title": "",
   "side": "client",
   "kind": "screen",
   "calls": [
    "escape_md",
    "InlineKeyboardMarkup",
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
     "line": 1311,
     "dynamic": false,
     "to": "client_regen_confirm",
     "how": "по приставке «client_regen_»"
    },
    {
     "label": "🌐 Список исключений",
     "data": "client_bypass_info",
     "line": 1312,
     "dynamic": false,
     "to": "client_bypass_info_handler",
     "how": "точно"
    },
    {
     "label": "🔕 Не напоминать",
     "data": "client_notify_off",
     "line": 1313,
     "dynamic": false,
     "to": "client_notify_off_handler",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 1314,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "run_bypass_check_handler",
   "file": "monitor.py",
   "line": 1393,
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
     "line": 1420,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    },
    {
     "label": "📨 Разослать напоминания сейчас",
     "data": "bypass_notify_now",
     "line": 1421,
     "dynamic": false,
     "to": "bypass_notify_now_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1422,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1402,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "bypass_notify_now_handler",
   "file": "monitor.py",
   "line": 1426,
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
     "line": 1432,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "bypass_list_handler",
   "file": "monitor.py",
   "line": 1436,
   "title": "",
   "side": "admin",
   "kind": "menu",
   "calls": [
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
     "line": 1456,
     "dynamic": false,
     "to": "bypass_add_manual_handler",
     "how": "точно"
    },
    {
     "label": "📨 Напомнить о перевыпуске",
     "data": "bypass_notify_now",
     "line": 1457,
     "dynamic": false,
     "to": "bypass_notify_now_handler",
     "how": "точно"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1458,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🗑 …",
     "data": "bypass_del_…",
     "line": 1452,
     "dynamic": false,
     "to": "bypass_del_handler",
     "how": "по приставке «bypass_del_»"
    }
   ]
  },
  {
   "id": "bypass_del_handler",
   "file": "monitor.py",
   "line": 1461,
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
     "line": 1456,
     "dynamic": false,
     "to": "bypass_add_manual_handler",
     "how": "точно",
     "inherited": "bypass_list_handler"
    },
    {
     "label": "📨 Напомнить о перевыпуске",
     "data": "bypass_notify_now",
     "line": 1457,
     "dynamic": false,
     "to": "bypass_notify_now_handler",
     "how": "точно",
     "inherited": "bypass_list_handler"
    },
    {
     "label": "🔙 Назад",
     "data": "back_to_main",
     "line": 1458,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно",
     "inherited": "bypass_list_handler"
    },
    {
     "label": "🗑 …",
     "data": "bypass_del_…",
     "line": 1452,
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
   "line": 1468,
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
     "line": 1472,
     "dynamic": false,
     "to": "bypass_list_handler",
     "how": "точно"
    }
   ]
  },
  {
   "id": "bypass_add_request_handler",
   "file": "monitor.py",
   "line": 1480,
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
     "line": 1506,
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
   "line": 447,
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
     "line": 462,
     "dynamic": true,
     "to": null,
     "how": null
    }
   ]
  },
  {
   "id": "exit_kb",
   "file": "utils.py",
   "line": 466,
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
     "line": 475,
     "dynamic": true,
     "to": null,
     "how": null
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 478,
     "dynamic": false,
     "to": "client_menu",
     "how": "точно"
    },
    {
     "label": "🔙 Главное меню",
     "data": "back_to_main",
     "line": 481,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "broadcast_message",
   "file": "utils.py",
   "line": 490,
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
     "line": 498,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    },
    {
     "label": "🏠 Личный кабинет",
     "data": "client_menu",
     "line": 500,
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
   "line": 1324,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "✍️ Своя рассылка (свой текст)",
     "data": "broadcast_custom",
     "line": 1326,
     "dynamic": false,
     "to": "шаг: broadcast_custom",
     "how": "точно"
    },
    {
     "label": "⚠️ Стандартное: тех. работы",
     "data": "do_maintenance_warn",
     "line": 1327,
     "dynamic": false,
     "to": "broadcast_message",
     "how": "точно"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1328,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: broadcast_custom",
   "file": "bot.py",
   "line": 1334,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1339,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: set_exp_",
   "file": "bot.py",
   "line": 1368,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "🌍 Классический DNS (1.1.1.1)",
     "data": "set_dns_classic",
     "line": 1370,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🛡 AdBlock DNS (Без рекламы)",
     "data": "set_dns_adblock",
     "line": 1370,
     "dynamic": false,
     "to": "шаг: set_dns_",
     "how": "по приставке «set_dns_»"
    },
    {
     "label": "🔙 Отмена",
     "data": "back_to_main",
     "line": 1370,
     "dynamic": false,
     "to": "return_to_main_menu",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: set_dns_",
   "file": "bot.py",
   "line": 1373,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "⏩ Пропустить",
     "data": "skip_tg_link",
     "line": 1375,
     "dynamic": false,
     "to": "finish_key_creation",
     "how": "точно"
    }
   ]
  },
  {
   "id": "шаг: rename_user_",
   "file": "bot.py",
   "line": 1384,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1386,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "шаг: link_tg_",
   "file": "bot.py",
   "line": 1396,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "🔙 Отмена",
     "data": "user_detail_…",
     "line": 1398,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «user_detail_»"
    }
   ]
  },
  {
   "id": "шаг: unlink_tg_",
   "file": "bot.py",
   "line": 1404,
   "title": "шаг мастера, нарисован прямо в роутере",
   "side": "admin",
   "kind": "step",
   "calls": [],
   "buttons": [
    {
     "label": "❌ …",
     "data": "do_unlink_…_…",
     "line": 1407,
     "dynamic": false,
     "to": "user_detail_menu",
     "how": "по приставке «do_unlink_»"
    },
    {
     "label": "🔙 Назад",
     "data": "user_detail_…",
     "line": 1408,
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
  "screens": 242,
  "buttons": 817,
  "admin": 199,
  "client": 43
 },
 "reachable": 163,
 "unrouted": 0
};

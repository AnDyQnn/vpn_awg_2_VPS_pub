from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Единый стиль меню: подписи короткие и полные (влезают на телефоне), глагол/иконка спереди,
# национальные флаги для нод, единая кнопка возврата «🔙 Главное меню». Важные действия —
# на всю ширину строки, парные — по два в ряд. callback_data не меняем (совместимость).

def main_menu(active_count=0, support_count=0):
    keyboard = [
        [InlineKeyboardButton("📊 Дашборд", callback_data="start_dashboard"),
         InlineKeyboardButton("📈 Трафик", callback_data="vpn_graph")],
        [InlineKeyboardButton("🔑 Создать ключ", callback_data="gen_key"),
         InlineKeyboardButton(f"🟢 Онлайн · {active_count}", callback_data="show_online")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="users_page_0"),
         InlineKeyboardButton(f"🆘 Поддержка · {support_count}", callback_data="support_admin_menu")],
        [InlineKeyboardButton("🇷🇺 Сервер RU", callback_data="menu_ru_server"),
         InlineKeyboardButton("🇩🇪 Сервер DE", callback_data="menu_de_server")],
        [InlineKeyboardButton("💾 Бэкапы и база", callback_data="menu_backups"),
         InlineKeyboardButton("👤 Режим клиента", callback_data="client_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_ru_server():
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить систему", callback_data="check_update")],
        [InlineKeyboardButton("🛠 Аудит RU", callback_data="run_audit"),
         InlineKeyboardButton("🛡 Проверка bypass", callback_data="run_bypass_check")],
        [InlineKeyboardButton("🌐 Split-tunnel · исключения", callback_data="bypass_list")],
        [InlineKeyboardButton("📢 Рассылка пользователям", callback_data="maintenance_warn")],
        [InlineKeyboardButton("🚨 Перезагрузить RU", callback_data="confirm_reboot")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_de_server():
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить агента DE", callback_data="de_update")],
        [InlineKeyboardButton("🛠 Аудит DE", callback_data="de_run_audit"),
         InlineKeyboardButton("📑 Логи DE", callback_data="de_read_logs")],
        [InlineKeyboardButton("🚨 Перезагрузить DE", callback_data="de_confirm_reboot")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_backups():
    keyboard = [
        [InlineKeyboardButton("💾 Бэкап RU", callback_data="backup"),
         InlineKeyboardButton("♻️ Восстановить RU", callback_data="restore")],
        [InlineKeyboardButton("💾 Бэкап DE", callback_data="de_backup")],
        [InlineKeyboardButton("📝 Логи сети · Excel", callback_data="download_logs"),
         InlineKeyboardButton("📊 База · Excel", callback_data="export_excel")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

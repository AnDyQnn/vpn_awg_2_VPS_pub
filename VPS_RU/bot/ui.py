from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Единый стиль меню: подписи короткие и полные (влезают на телефоне), глагол/иконка спереди,
# национальные флаги для нод, единая кнопка возврата «🔙 Главное меню». Важные действия —
# на всю ширину строки, парные — по два в ряд. callback_data не меняем (совместимость).

def main_menu(active_count=0, support_count=0, admin_count=0):
    """Поддержка переехала внутрь раздела администрирования: сервисные настройки
    и обращения — это одна кухня, и в главном меню им тесно. На освободившемся
    месте — «Админка» со счётчиком всего, что ждёт внимания."""
    keyboard = [
        [InlineKeyboardButton("📊 Наблюдение", callback_data="start_dashboard"),
         InlineKeyboardButton("📈 Трафик", callback_data="vpn_graph")],
        [InlineKeyboardButton("🔑 Создать ключ", callback_data="gen_key"),
         InlineKeyboardButton(f"🟢 Онлайн · {active_count}", callback_data="show_online")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="users_page_0"),
         InlineKeyboardButton(
             "⚙️ Администрирование" + (f" · {admin_count}" if admin_count else ""),
             callback_data="svc_menu")],
        [InlineKeyboardButton("🖥 Мастер-сервер", callback_data="menu_ru_server"),
         InlineKeyboardButton("🌍 Клиент-сервер", callback_data="menu_de_server")],
        [InlineKeyboardButton("💾 Архивы и база", callback_data="menu_backups"),
         InlineKeyboardButton("👤 Режим клиента", callback_data="client_menu")],
        [InlineKeyboardButton("📄 Что нового", callback_data="svc_whatsnew")],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_ru_server():
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить систему", callback_data="check_update")],
        [InlineKeyboardButton("🛠 Аудит мастера", callback_data="run_audit"),
         InlineKeyboardButton("🛡 Проверка исключений", callback_data="run_bypass_check")],
        [InlineKeyboardButton("🌐 Исключения · мимо VPN", callback_data="bypass_list")],
        [InlineKeyboardButton("📢 Рассылка пользователям", callback_data="maintenance_warn")],
        [InlineKeyboardButton("🚨 Перезагрузить мастер", callback_data="confirm_reboot")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_de_server():
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить клиент-сервер", callback_data="de_update")],
        [InlineKeyboardButton("🛠 Аудит клиента", callback_data="de_run_audit"),
         InlineKeyboardButton("📑 Журнал клиента", callback_data="de_read_logs")],
        [InlineKeyboardButton("🚨 Перезагрузить клиент", callback_data="de_confirm_reboot")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_backups():
    keyboard = [
        [InlineKeyboardButton("💾 Копия мастера", callback_data="backup"),
         InlineKeyboardButton("♻️ Восстановить мастер", callback_data="restore")],
        [InlineKeyboardButton("💾 Копия клиента", callback_data="de_backup")],
        [InlineKeyboardButton("📊 Сводка · Excel", callback_data="download_logs"),
         InlineKeyboardButton("📊 База · Excel", callback_data="export_excel")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

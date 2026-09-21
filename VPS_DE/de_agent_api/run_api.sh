#!/bin/bash

# Включаем форвардинг трафика на уровне ядра контейнера
sysctl -w net.ipv4.ip_forward=1

echo "🔧 Configuring WireGuard paths..."
mkdir -p /etc/wireguard

# Создаем симлинк (wg-quick ищет конфиги в /etc/wireguard)
ln -sf /etc/amnezia/amneziawg/wg0.conf /etc/wireguard/wg0.conf

# Пробуем поднять туннель при старте, если конфиг уже существует
if [ -f "/etc/wireguard/wg0.conf" ]; then
    echo " Setting up wg0 interface..."
    
    # Страховка: зачищаем DNS-строку, если она туда как-то попала
    sed -i '/^DNS/d' /etc/wireguard/wg0.conf
    
    # Удаляем зависший интерфейс
    ip link delete wg0 2>/dev/null || true
    
    # Поднимаем туннель
    wg-quick up wg0 || echo "⚠️ Warning: Could not start wg0 automatically"

    # Настраиваем маскарад
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE || true

    # MSS clamping (фикс «интернет тупит» на крупных пакетах): туннель wg0 имеет MTU 1280.
    # Подрезаем MSS в TCP-рукопожатии под реальный PMTU, чтобы полноразмерные пакеты из
    # интернета Германии не терялись на входе в туннель при заблокированном ICMP. ВАЖНО:
    # применяем именно здесь, в стартовом пути — он выполняется при каждом рестарте/пересборке
    # контейнера (в т.ч. при деплое), тогда как reload_wg() дёргается лишь при ручном reload.
    # Идемпотентно (-C || -A), чтобы не плодить дубли, если правило уже есть.
    iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null \
        || iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu || true
else
    echo "⚠️ Warning: wg0.conf not found. Waiting for manual config upload from RU Master."
fi

# --- БЕЗОПАСНОСТЬ: панель агента доступна только мастеру ---
# Порт 8000 смотрит в туннель, то есть был открыт любому пиру: можно было перенастроить
# туннель, скачать конфиги и перезагрузить хост. Пускаем только мастера 10.13.13.1.
# Правила идемпотентны (-C || добавить) и переживают перезапуск интерфейса, потому что
# цепочку INPUT здесь никто не флашит.
iptables -C INPUT -i wg0 -s 10.13.13.1 -p tcp --dport 8000 -j ACCEPT 2>/dev/null \
    || iptables -I INPUT 1 -i wg0 -s 10.13.13.1 -p tcp --dport 8000 -j ACCEPT || true
# Петлю пускаем обязательно и ПЕРВЫМ правилом: запрос с 127.0.0.1 приходит
# только изнутри контейнера, снаружи его подделать нельзя. Без этого исключения
# правило ниже отрезает панель от самого узла — и сторож, проверяющий её
# локально, считает живую панель мёртвой.
iptables -C INPUT -i lo -p tcp --dport 8000 -j ACCEPT 2>/dev/null \
    || iptables -I INPUT 1 -i lo -p tcp --dport 8000 -j ACCEPT || true
iptables -C INPUT -p tcp --dport 8000 -j DROP 2>/dev/null \
    || iptables -A INPUT -p tcp --dport 8000 -j DROP || true

echo "🚀 Starting DE Agent (AmneziaWG Client + Monitor API)..."

# Запускаем API агента
exec /opt/venv/bin/python3 -u -m uvicorn api:app --host 0.0.0.0 --port 8000 --app-dir /app
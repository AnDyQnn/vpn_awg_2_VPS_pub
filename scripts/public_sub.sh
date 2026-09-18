#!/bin/bash
# Подписка наружу: сертификат на IP-адрес, открытый порт и охрана на нём.
#
# ЗАЧЕМ. Подписка живёт внутри туннеля, и по умолчанию это правильно: наружу
# ничего не торчит. Но у такой подписки есть цена — прочитать её можно, только
# уже будучи подключённым. Значит первая настройка идёт куском текста, а
# изменения доезжают рассылкой.
#
# Открыв её наружу, получаем обратное: человек вставляет один адрес, и дальше
# сервера, маскировки и список исключений приезжают к нему сами.
#
# ПОЧЕМУ БЕЗ ДОМЕНА. С 15 января 2026 Let's Encrypt выдаёт сертификаты прямо на
# IP-адрес — бесплатно. Условие одно: профиль "shortlived", он единственный
# разрешает IP вместо имени. Срок жизни 160 часов, чуть меньше семи суток,
# поэтому продление стоит таймером дважды в сутки, а не раз в два месяца.
#
# ПОЧЕМУ ПОРТ 80 СВОБОДЕН. Страница отказа слушает 80 внутри сети контейнеров и
# наружу не опубликована: на публичном адресе заняты 443, 2053, 2083 (входы
# Xray) и 51820/51821 (UDP). Проверить — ss -lntp, строка с :80.
#
# ГДЕ ОХРАНА ПОРТА. Не в ufw. Docker пишет свои правила в PREROUTING и FORWARD
# раньше, чем ufw успевает сказать своё, и запрет в ufw на опубликованный порт
# контейнера просто не действует — это давняя и известная его особенность.
# Единственная цепочка, которую Docker не перебивает, — DOCKER-USER: её он сам
# зовёт первой. Туда и ставим.
#
# Скрипт идемпотентен: повторный запуск ничего не ломает и не перевыпускает
# сертификат, пока тот свеж.
set -u

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SELF_DIR")"
NODE_DIR="${2:-$ROOT_DIR/VPS_RU}"
CERT_DIR="$NODE_DIR/volumes/certs"
FLAGS_DIR="$NODE_DIR/volumes/flags"
STATE="$FLAGS_DIR/public_sub.json"
# Отметка «владелец закрыл сам». Нужна потому, что выкладка зовёт этот скрипт с
# "on" каждый раз: без отметки первое же обновление молча отменяло бы решение
# владельца и снова открывало порт. Решение человека должно переживать деплой.
OFF_MARK="$FLAGS_DIR/public_sub.off"

# Порт наружу. 2096 — общеизвестный запасной HTTPS, такой же, как занятые
# Xray 2053 и 2083: среди чужого трафика не выделяется.
#
# Не 8443: тот внутри сетевой области узла уже занят HTTPS-страницей отказа, на
# которую заворачивается 443.
PUBLIC_PORT=2096
# Куда Docker разворачивает этот порт: статический адрес контейнера из
# docker-compose и порт сервера подписок внутри него.
CONT_IP=172.20.0.6
CONT_PORT=2096
CHAIN=VPN_SUB
CERT_NAME=vpn-node-ip
LIVE="/etc/letsencrypt/live/$CERT_NAME"

# Минимальная версия certbot: флаг --ip-address появился в 5.3. В apt лежит
# гораздо более старая, поэтому ставим свою в отдельное окружение.
NEED_MAJOR=5
NEED_MINOR=3
VENV=/opt/certbot-ip

mkdir -p "$CERT_DIR" "$FLAGS_DIR"

say() { echo "[подписка] $*"; }

public_ip() {
    # Свой адрес спрашиваем у маршрутизации, а не у внешнего сервиса: тот может
    # не ответить или ответить чужим, а ошибиться здесь значит выписать
    # сертификат не на себя.
    ip -4 route get 1.1.1.1 2>/dev/null |
        awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}'
}


cert_until() {
    # Срок в секундах эпохи. Бот берёт его отсюда, а не разбирает сертификат
    # сам: openssl в образе бота нет, и тащить его туда ради одной даты значит
    # менять образ ради строки на экране.
    [ -s "$CERT_DIR/fullchain.pem" ] || { echo 0; return; }
    D=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ -n "$D" ]; then date -d "$D" +%s 2>/dev/null || echo 0; else echo 0; fi
}

report() {   # report <состояние> <сообщение>
    printf '{"state":"%s","msg":"%s","port":%s,"at":%s,"until":%s,"ip":"%s"}\n' \
        "$1" "$2" "$PUBLIC_PORT" "$(date +%s)" "$(cert_until)" "$(public_ip)" > "$STATE"
    say "$2"
}

# ---------------------------------------------------------------- certbot ---

certbot_bin() {
    for C in "$VENV/bin/certbot" "$(command -v certbot 2>/dev/null)"; do
        [ -x "$C" ] || continue
        V="$("$C" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)"
        MAJ="${V%%.*}"; MIN="${V##*.}"
        [ -z "$MAJ" ] && continue
        if [ "$MAJ" -gt "$NEED_MAJOR" ] ||
           { [ "$MAJ" -eq "$NEED_MAJOR" ] && [ "$MIN" -ge "$NEED_MINOR" ]; }; then
            echo "$C"; return 0
        fi
    done
    return 1
}

ensure_certbot() {
    C="$(certbot_bin)" && { echo "$C"; return 0; }
    # Своё окружение, а не apt: в apt версия старше нужной на годы, а ставить
    # системный python из pip — верный способ однажды сломать систему.
    say "ставлю certbot $NEED_MAJOR.$NEED_MINOR и новее в $VENV" >&2
    LOG=/tmp/certbot-install.log
    : > "$LOG"

    # Ждём замок dpkg, а не падаем об него. На узле работают ночные
    # автообновления, и попасть в их минуту — обычное дело: без ожидания
    # установка проваливалась мгновенно и молча, а шаг выглядел как «не
    # получилось», хотя пакет ставится прекрасно.
    APT_OPTS="-o DPkg::Lock::Timeout=180"
    DEBIAN_FRONTEND=noninteractive apt-get $APT_OPTS update -qq >>"$LOG" 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get $APT_OPTS install -y python3-venv >>"$LOG" 2>&1

    if ! python3 -m venv "$VENV" >>"$LOG" 2>&1; then
        # Пакета нет и не будет (бывает на урезанных образах). Тогда делаем
        # окружение без pip и приносим pip отдельно — это работает без apt
        # вовсе и ничего системного не трогает.
        say "python3-venv недоступен, беру pip напрямую" >&2
        rm -rf "$VENV"
        python3 -m venv --without-pip "$VENV" >>"$LOG" 2>&1 || {
            say "окружение не создалось, подробности в $LOG" >&2
            return 1
        }
        curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py >>"$LOG" 2>&1 &&
            "$VENV/bin/python" /tmp/get-pip.py -q >>"$LOG" 2>&1
        rm -f /tmp/get-pip.py
    fi

    "$VENV/bin/pip" install -q --upgrade pip certbot >>"$LOG" 2>&1
    C="$(certbot_bin)" || {
        say "certbot не встал, подробности в $LOG" >&2
        tail -5 "$LOG" | sed 's/^/[подписка]   /' >&2
        return 1
    }
    echo "$C"
}

port80_free() {
    ss -lntH 2>/dev/null | awk '{print $4}' | grep -qE '(^|[.:])80$' && return 1
    return 0
}

issue() {
    IP="$(public_ip)"
    if [ -z "$IP" ]; then
        report "error" "не удалось определить свой публичный адрес"
        return 1
    fi
    say "адрес: $IP"

    CB="$(ensure_certbot)"
    if [ -z "$CB" ]; then
        report "error" "certbot нужной версии не установился"
        return 1
    fi
    say "certbot: $CB"

    if ! port80_free; then
        report "error" "порт 80 занят — проверку провести негде"
        ss -lntp 2>/dev/null | grep -E '(^|[.:])80 ' | sed 's/^/[подписка]   /'
        return 1
    fi

    # --ip-address, а не -d: для адреса это отдельный флаг. Профиль shortlived
    # обязателен — остальные профили IP не принимают вовсе. Проверка только
    # http-01 или tls-alpn-01: DNS-01 для адреса невозможен по определению.
    "$CB" certonly --standalone --non-interactive --agree-tos \
        --register-unsafely-without-email \
        --preferred-profile shortlived \
        --cert-name "$CERT_NAME" \
        --ip-address "$IP" >/tmp/certbot.log 2>&1
    if [ $? -ne 0 ]; then
        report "error" "сертификат не выдан, подробности в /tmp/certbot.log"
        tail -8 /tmp/certbot.log | sed 's/^/[подписка]   /'
        return 1
    fi
    copy_cert
}

copy_cert() {
    [ -s "$LIVE/fullchain.pem" ] || { say "сертификата нет в $LIVE"; return 1; }
    cp -L "$LIVE/fullchain.pem" "$CERT_DIR/fullchain.pem" &&
    cp -L "$LIVE/privkey.pem"   "$CERT_DIR/privkey.pem"   || {
        report "error" "сертификат есть, но не скопировался в volumes/certs"
        return 1
    }
    # Бот перечитывает эти файлы сам, раз в десять минут сверяя время правки, —
    # перезапускать его ради продления не нужно.
    chmod 644 "$CERT_DIR/fullchain.pem"
    chmod 640 "$CERT_DIR/privkey.pem"
    return 0
}

# ---------------------------------------------------------------- файрвол ---

firewall_on() {
    # Своя цепочка: так правила видно одним списком, и снять их можно разом,
    # ничего чужого не задев.
    iptables -N "$CHAIN" 2>/dev/null
    iptables -F "$CHAIN"

    # Docker переписывает адрес назначения ещё в PREROUTING, поэтому сюда
    # пакет приходит уже с внутренним портом и контейнерным адресом. Сужаем до
    # них, чтобы правила никогда не задели ни Xray, ни туннель.
    M="-p tcp -d $CONT_IP --dport $CONT_PORT -m conntrack --ctstate NEW"

    # 1. Сколько соединений разом с одного адреса.
    #
    #    Пределы считались под подписку — короткий текстовый ответ, один запрос
    #    на клиента. С тех пор этот же порт раздаёт гео-файлы приложения:
    #    двадцать семь мегабайт, которые телефон тянет в несколько потоков
    #    сразу. Восьми соединений на это не хватало, и человек получал вместо
    #    файлов обрыв — а приложение считает профиль без гео-файлов испорченным
    #    целиком, то есть не работает ВООБЩЕ ничего.
    #
    #    Второе, что упускал прежний расчёт: мобильные операторы держат тысячи
    #    абонентов за одним публичным адресом. «Один адрес» — это не один
    #    человек, и любой предел на адрес бьёт по соседям по вышке.
    #
    #    Поэтому шестьдесят четыре. Для скана это по-прежнему тесно, для
    #    телефона — с запасом.
    iptables -A "$CHAIN" $M \
        -m connlimit --connlimit-above 64 --connlimit-mask 32 -j DROP

    # 2. Как часто с одного адреса. Живой клиент приходит раз в два часа, но
    #    приходит не один: за адресом оператора их может быть много, и каждый
    #    тянет ещё и гео-файлы. Перебор токенов на таком фоне всё равно виден —
    #    он идёт сотнями в секунду, а не четырьмя в секунду.
    iptables -A "$CHAIN" $M \
        -m hashlimit --hashlimit-above 240/min --hashlimit-burst 60 \
        --hashlimit-mode srcip --hashlimit-name sub_src -j DROP

    # 3. Потолок на весь порт. Правила выше считают по адресу и против потока с
    #    тысячи адресов не помогут — а это держит порт целиком, сколько бы их
    #    ни было. Тридцать человек столько не создадут никогда.
    iptables -A "$CHAIN" $M \
        -m hashlimit --hashlimit-above 50/sec --hashlimit-burst 100 \
        --hashlimit-mode dstip --hashlimit-name sub_all -j DROP

    # DROP, а не REJECT: молчание не стоит нам ничего и говорит сканеру меньше
    # — по нему он не отличит закрытый порт от занятого.

    # Docker зовёт DOCKER-USER первой и своими правилами её не перекрывает —
    # это единственное место, где наш фильтр переживёт перезапуск докера.
    iptables -C DOCKER-USER -j "$CHAIN" 2>/dev/null ||
        iptables -I DOCKER-USER 1 -j "$CHAIN"

    # ufw здесь ничего не решает (Docker идёт раньше), но пусть список портов в
    # нём отражает правду — иначе следующий человек будет искать причину не
    # там, где она есть.
    ufw allow "$PUBLIC_PORT"/tcp >/dev/null 2>&1 || true
    say "охрана порта $PUBLIC_PORT поставлена в DOCKER-USER"
}

firewall_off() {
    iptables -D DOCKER-USER -j "$CHAIN" 2>/dev/null
    iptables -F "$CHAIN" 2>/dev/null
    iptables -X "$CHAIN" 2>/dev/null
    ufw delete allow "$PUBLIC_PORT"/tcp >/dev/null 2>&1 || true
}

# ----------------------------------------------------------------- таймер ---

timer_on() {
    {
        echo "[Unit]"
        echo "Description=Продление сертификата подписки и проверка охраны порта"
        echo "After=docker.service"
        echo
        echo "[Service]"
        echo "Type=oneshot"
        echo "ExecStart=/bin/bash $SELF_DIR/public_sub.sh renew $NODE_DIR"
    } > /etc/systemd/system/vpn-subcert.service

    # Дважды в сутки. Сертификат живёт 160 часов, certbot берётся за продление,
    # когда осталась треть срока — около 53 часов. То есть на каждое продление
    # у нас больше сотни попыток: пропустить одну не страшно, пропустить все
    # значит оставить без подписки сразу всех.
    {
        echo "[Unit]"
        echo "Description=Продление сертификата подписки дважды в сутки"
        echo
        echo "[Timer]"
        echo "OnBootSec=3min"
        echo "OnCalendar=*-*-* 04,16:20:00"
        echo "RandomizedDelaySec=20min"
        echo "Persistent=true"
        echo
        echo "[Install]"
        echo "WantedBy=timers.target"
    } > /etc/systemd/system/vpn-subcert.timer

    systemctl daemon-reload >/dev/null 2>&1
    systemctl enable --now vpn-subcert.timer >/dev/null 2>&1
    say "продление поставлено таймером, дважды в сутки"
}

timer_off() {
    systemctl disable --now vpn-subcert.timer >/dev/null 2>&1
    rm -f /etc/systemd/system/vpn-subcert.timer
    rm -f /etc/systemd/system/vpn-subcert.service
    systemctl daemon-reload >/dev/null 2>&1
}

# ------------------------------------------------------------------ режимы ---

case "${1:-status}" in
  ensure)
    # Так зовут выкладка и установщик: «сделай как надо, если владелец не
    # запрещал». Отличается от "on" ровно одним — уважает отметку.
    if [ -f "$OFF_MARK" ]; then
        say "владелец закрыл подписку наружу — не трогаю"
        exit 0
    fi
    # Через bash, а не напрямую: бит запуска на этом файле не гарантирован.
    # Обновление раздаёт права только внутри папки ноды, а мы лежим в общей —
    # и "exec" молча упирался в «Permission denied».
    exec bash "$0" on "$NODE_DIR"
    ;;

  on)
    rm -f "$OFF_MARK"
    issue || exit 1
    firewall_on
    timer_on
    # Ничего в .env писать не нужно. Состояние — это наличие сертификата, и
    # бот видит его сам: раз в десять минут он сверяет файлы и открывает или
    # закрывает внешний вход. Переменная, которую можно забыть выставить, была
    # бы ещё одним способом однажды открыть порт без сертификата.
    report "on" "подписка открыта наружу на порту $PUBLIC_PORT"
    say "бот подхватит сертификат в течение десяти минут"
    ;;

  renew)
    # Таймер зовёт это же дважды в сутки — заодно возвращая правила файрвола,
    # если их сняли перезапуском докера или перезагрузкой.
    if [ ! -s "$CERT_DIR/fullchain.pem" ]; then
        say "подписка наружу не включена — продлевать нечего"
        exit 0
    fi
    firewall_on
    CB="$(certbot_bin)"
    if [ -z "$CB" ]; then
        report "error" "certbot пропал — продлить нечем"
        exit 1
    fi
    "$CB" renew --cert-name "$CERT_NAME" --standalone --non-interactive \
        >/tmp/certbot-renew.log 2>&1
    if copy_cert; then
        UNTIL=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        report "on" "сертификат действует до $UNTIL"
    else
        report "error" "продление не удалось, подробности в /tmp/certbot-renew.log"
    fi
    ;;

  firewall)
    firewall_on
    iptables -L "$CHAIN" -n -v --line-numbers
    ;;

  off)
    # Отметку ставим ДО всего остального: если дальше что-то не доработает,
    # решение владельца всё равно уже записано и переживёт выкладку.
    : > "$OFF_MARK"
    firewall_off
    timer_off
    # Сертификат убран — значит бот закроет внешний вход сам. Порт останется
    # опубликованным, но слушать его будет некому.
    rm -f "$CERT_DIR/fullchain.pem" "$CERT_DIR/privkey.pem"
    report "off" "подписка снова только внутри туннеля"
    say "бот закроет внешний вход в течение десяти минут"
    ;;

  status)
    if [ -s "$CERT_DIR/fullchain.pem" ]; then
        UNTIL=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        SUBJ=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -text 2>/dev/null |
               grep -A1 'Subject Alternative Name' | tail -1 | sed 's/^ *//')
        say "включена; $SUBJ; действует до $UNTIL"
    elif [ -f "$OFF_MARK" ]; then
        say "выключена владельцем — выкладка её не откроет"
    else
        say "выключена"
    fi
    echo "--- охрана порта ---"
    iptables -L "$CHAIN" -n -v 2>/dev/null || say "правил нет"
    ;;

  *)
    say "использование: public_sub.sh ensure|on|off|renew|firewall|status [папка ноды]"
    exit 1
    ;;
esac

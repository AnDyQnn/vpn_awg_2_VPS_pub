#!/bin/bash
# Сертификат узла: выпуск, продление, уборка.
#
# ЗАЧЕМ. Страница отказа и свои сервисы внутри туннеля открываются по нашим
# именам («дом.example.ru»). С настоящим сертификатом браузер не ругается; без
# него страница работает на самоподписанном.
#
# НА ЧТО ВЫПУСКАЕТСЯ. Есть домен и доступ к его зоне — на имя и все поддомены
# (проверка через DNS). Есть только домен — на имя. Нет домена — на IP-адрес:
# с 15 января 2026 Let's Encrypt выдаёт такие профилем "shortlived", срок 160
# часов, поэтому продление стоит таймером дважды в сутки.
#
# ИМЯ ФАЙЛА. Раньше этот же скрипт открывал наружу подписку Xray на порту 2096.
# Подписки больше нет, а имя осталось: его зовут демон обновлений и отчёты на
# уже работающих узлах. Правила охраны того порта скрипт при любом вызове
# снимает — на узлах, где они стояли, они больше ничего не охраняют.
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

# Порт и цепочка прежней подписки наружу — только чтобы убрать их следы.
OLD_PORT=2096
CHAIN=VPN_SUB
CERT_NAME=vpn-node-ip
LIVE="/etc/letsencrypt/live/$CERT_NAME"

# Минимальная версия certbot: флаг --ip-address появился в 5.3. В apt лежит
# гораздо более старая, поэтому ставим свою в отдельное окружение.
NEED_MAJOR=5
NEED_MINOR=3
VENV=/opt/certbot-ip

mkdir -p "$CERT_DIR" "$FLAGS_DIR"

say() { echo "[сертификат] $*"; }

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
    # «wild» и «dns_api» бот показывает на экране, но сами логин с паролем к
    # нему не попадают и попасть не могут: в контейнер они не передаются вовсе.
    WILD=false; cert_is_wild && WILD=true
    NAMED=false; cert_named && NAMED=true
    DAPI=false; dns_api_ready && DAPI=true
    printf '{"state":"%s","msg":"%s","at":%s,"until":%s,"ip":"%s","domain":"%s","wild":%s,"named":%s,"dns_api":%s}\n' \
        "$1" "$2" "$(date +%s)" "$(cert_until)" "$(public_ip)" \
        "$(read_domain)" "$WILD" "$NAMED" "$DAPI" > "$STATE"
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
        tail -5 "$LOG" | sed 's/^/[сертификат]   /' >&2
        return 1
    }
    echo "$C"
}

port80_free() {
    ss -lntH 2>/dev/null | awk '{print $4}' | grep -qE '(^|[.:])80$' && return 1
    return 0
}

# Домен берётся из .env ноды, а не из кода: он у каждой установки свой, и
# зашивать его в проект значит требовать правку кода от каждого, кто поднимет
# копию. Пусто — работаем по адресу, как и раньше.
read_env() {   # read_env КЛЮЧ
    [ -f "$NODE_DIR/.env" ] || return 0
    grep -E "^$1=" "$NODE_DIR/.env" 2>/dev/null |
        tail -1 | cut -d= -f2- | tr -d "\"' \r"
}

read_domain() { read_env PUBLIC_DOMAIN; }

# Есть ли доступ к зоне домена. Без него сертификат на «звёздочку» невозможен:
# удостоверяющий центр проверяет владение записью в DNS, и класть её умеет
# только тот, у кого есть доступ к зоне.
#
# Пара лежит файлом, а не в .env: ею пользуется только хост, и гонять ради неё
# пересоздание контейнеров незачем. .env оставлен запасным путём.
ZONE_SECRET="$NODE_DIR/volumes/secrets/regru.conf"

read_secret() {   # read_secret КЛЮЧ
    for F in "$ZONE_SECRET" "$NODE_DIR/.env"; do
        [ -f "$F" ] || continue
        V=$(grep -E "^$1=" "$F" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "\"' \r")
        [ -n "$V" ] && { printf '%s' "$V"; return 0; }
    done
    return 0
}

dns_api_ready() {
    [ -n "$(read_secret REGRU_API_USER)" ] && [ -n "$(read_secret REGRU_API_PASSWORD)" ]
}

# Покрывает ли нынешний сертификат «звёздочку». По этому же признаку решается,
# чем его продлевать: у выданного по DNS проверка другая, и навязать ему
# http-01 значит сломать продление.
cert_is_wild() {
    [ -s "$CERT_DIR/fullchain.pem" ] || return 1
    openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -text 2>/dev/null |
        grep -q 'DNS:\*\.'
}

# Выписан ли нынешний сертификат на ИМЯ, а не на адрес. Спрашиваем сам
# сертификат, а не настройки: между «домен вписан» и «сертификат на домен» лежит
# отдельный шаг, и бот обязан показывать, сделан он или нет.
cert_named() {
    [ -s "$CERT_DIR/fullchain.pem" ] || return 1
    openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -text 2>/dev/null |
        grep -A1 'Subject Alternative Name' | grep -q 'DNS:'
}

issue() {
    DOMAIN="$(read_domain)"
    IP="$(public_ip)"
    if [ -z "$IP" ]; then
        report "error" "не удалось определить свой публичный адрес"
        return 1
    fi
    say "адрес: $IP"
    [ -n "$DOMAIN" ] && say "домен: $DOMAIN"

    CB="$(ensure_certbot)"
    if [ -z "$CB" ]; then
        report "error" "certbot нужной версии не установился"
        return 1
    fi
    say "certbot: $CB"

    if ! port80_free; then
        report "error" "порт 80 занят — проверку провести негде"
        ss -lntp 2>/dev/null | grep -E '(^|[.:])80 ' | sed 's/^/[сертификат]   /'
        return 1
    fi

    # Два разных случая, и путать их нельзя.
    #
    # ДОМЕН — обычная выдача через `-d`, срок девяносто дней, профиль по
    # умолчанию. Так живёт весь интернет.
    #
    # АДРЕС — отдельный флаг `--ip-address` и обязательный профиль
    # `shortlived`: остальные профили IP не принимают вовсе, а срок у такого
    # сертификата сто шестьдесят часов, меньше недели. Проверка только http-01
    # или tls-alpn-01 — DNS-01 для адреса невозможен по определению.
    #
    # Домен поэтому не просто «красивее»: он снимает недельный срок и вместе с
    # ним целый класс отказов, когда продление не прошло и вход умер у всех.
    # Сначала «звёздочка», если есть доступ к зоне. Она покрывает не только сам
    # домен, но и всё, что внутри туннеля: «дом.example.ru»,
    # «закрыто.example.ru». Другого способа получить на них сертификат не
    # существует — снаружи этих имён нет, и обычную проверку они не пройдут.
    #
    # Проверка здесь другая, dns-01: центр просит положить запись в зону домена.
    # Кладёт её крючок, логин с паролем он читает из .env сам.
    if [ -n "$DOMAIN" ] && dns_api_ready; then
        say "выпускаю на домен и все поддомены через запись в DNS (срок 90 дней)"
        say "проверка идёт через зону — это занимает несколько минут"
        HOOK="$SELF_DIR/dns_regru.sh"
        # NODE_DIR отдаём ОКРУЖЕНИЕМ, а не приставкой к команде крючка.
        # Приставка выглядит естественно, но certbot проверяет крючок как
        # существующую программу и ищет файл с именем «NODE_DIR=/root/...».
        # Не находит — и выпуск падает ещё до первого запроса к центру, с
        # сообщением, в котором виновата будто бы система.
        #
        # Своё окружение certbot передаёт крючкам целиком, так что
        # переменная до скрипта доедет.
        export NODE_DIR
        "$CB" certonly --manual --non-interactive --agree-tos \
            --register-unsafely-without-email \
            --preferred-challenges dns \
            --manual-auth-hook "bash $HOOK add" \
            --manual-cleanup-hook "bash $HOOK clean" \
            --cert-name "$CERT_NAME" \
            -d "$DOMAIN" -d "*.$DOMAIN" >/tmp/certbot-wild.log 2>&1
        if [ $? -eq 0 ]; then
            copy_cert && report "on" "сертификат на «$DOMAIN» и все его поддомены выдан"
            return $?
        fi
        # Не вышло. Дальше по лестнице — обычный сертификат на один домен. Но
        # только если сужать нечего.
        #
        # У нас уже может лежать действующая «звёздочка»: выкладка зовёт этот
        # скрипт каждый раз, а регистратор мог просто не ответить сегодня.
        # Обычный выпуск с тем же именем линии, но меньшим списком имён,
        # ЗАМЕНЯЕТ линию — сертификат сузился бы, и внутренние имена остались
        # бы без покрытия. Молча, на ровном месте, из-за чужой пятиминутной
        # неполадки.
        #
        # Поэтому: есть живая «звёздочка» — оставляем её и уходим. Она
        # действует, а следующая попытка будет при следующей выкладке или по
        # таймеру продления.
        if cert_is_wild && [ "$(cert_until)" -gt "$(date +%s)" ]; then
            report "warning" "сертификат на поддомены продлить не вышло, действующий остался; подробности в /tmp/certbot-wild.log"
            tail -5 /tmp/certbot-wild.log | sed 's/^/[сертификат]   /'
            return 0
        fi
        say "на поддомены не вышло, беру обычный сертификат; подробности в /tmp/certbot-wild.log"
        tail -12 /tmp/certbot-wild.log | sed 's/^/[сертификат]   /'
    fi

    if [ -n "$DOMAIN" ]; then
        say "выпускаю на домен (срок 90 дней)"
        "$CB" certonly --standalone --non-interactive --agree-tos \
            --register-unsafely-without-email \
            --cert-name "$CERT_NAME" \
            -d "$DOMAIN" >/tmp/certbot.log 2>&1
        RC=$?
        if [ $RC -ne 0 ]; then
            # Домен мог не разойтись по миру: свежая запись расходится до
            # суток. Не оставляем узел без сертификата — откатываемся на адрес,
            # который работал до сих пор, и говорим об этом вслух.
            report "warning" "на домен не вышло — беру адрес; подробности в /tmp/certbot.log"
            tail -5 /tmp/certbot.log | sed 's/^/[сертификат]   /'
            DOMAIN=""
        fi
    fi
    if [ -z "$DOMAIN" ]; then
        say "выпускаю на адрес (срок 160 часов)"
        "$CB" certonly --standalone --non-interactive --agree-tos \
            --register-unsafely-without-email \
            --preferred-profile shortlived \
            --cert-name "$CERT_NAME" \
            --ip-address "$IP" >/tmp/certbot.log 2>&1
        if [ $? -ne 0 ]; then
            report "error" "сертификат не выдан, подробности в /tmp/certbot.log"
            tail -8 /tmp/certbot.log | sed 's/^/[сертификат]   /'
            return 1
        fi
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

# ------------------------------------------------- следы прежней подписки ---

old_guard_cleanup() {
    # Охрана порта подписки Xray жила в DOCKER-USER. Порт больше никто не
    # публикует и не слушает, так что правила снимаем — молча и безопасно:
    # цепочка своя, ничего чужого в ней нет.
    iptables -D DOCKER-USER -j "$CHAIN" 2>/dev/null
    iptables -F "$CHAIN" 2>/dev/null
    iptables -X "$CHAIN" 2>/dev/null
    ufw delete allow "$OLD_PORT"/tcp >/dev/null 2>&1 || true
}

# ----------------------------------------------------------------- таймер ---

timer_on() {
    {
        echo "[Unit]"
        echo "Description=Продление сертификата узла"
        echo "After=docker.service"
        echo
        echo "[Service]"
        echo "Type=oneshot"
        echo "ExecStart=/bin/bash $SELF_DIR/public_sub.sh renew $NODE_DIR"
    } > /etc/systemd/system/vpn-subcert.service

    # Дважды в сутки. Сертификат живёт 160 часов, certbot берётся за продление,
    # когда осталась треть срока — около 53 часов. То есть на каждое продление
    # у нас больше сотни попыток: пропустить одну не страшно, пропустить все
    # значит оставить страницу отказа без сертификата.
    {
        echo "[Unit]"
        echo "Description=Продление сертификата узла дважды в сутки"
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
    old_guard_cleanup
    if [ -f "$OFF_MARK" ]; then
        say "владелец убрал сертификат — не выпускаю"
        exit 0
    fi
    # Через bash, а не напрямую: бит запуска на этом файле не гарантирован.
    # Обновление раздаёт права только внутри папки ноды, а мы лежим в общей —
    # и "exec" молча упирался в «Permission denied».
    exec bash "$0" on "$NODE_DIR"
    ;;

  on)
    rm -f "$OFF_MARK"
    old_guard_cleanup
    issue || exit 1
    timer_on
    # Ничего в .env писать не нужно. Состояние — это наличие сертификата, и
    # бот и страница отказа видят его сами.
    report "on" "сертификат выпущен"
    ;;

  renew)
    # Таймер зовёт это же дважды в сутки.
    old_guard_cleanup
    if [ ! -s "$CERT_DIR/fullchain.pem" ]; then
        say "сертификата нет — продлевать нечего"
        exit 0
    fi
    CB="$(certbot_bin)"
    if [ -z "$CB" ]; then
        report "error" "certbot пропал — продлить нечем"
        exit 1
    fi
    # Чем продлевать, решает сам сертификат. У выданного по записи в DNS
    # проверка другая, и навязать ему «--standalone» значит сломать продление:
    # certbot послушается флага и пойдёт проверять по http, которого для
    # «звёздочки» не бывает вовсе.
    if cert_is_wild; then
        say "продлеваю сертификат на поддомены — проверка снова через зону"
        NODE_DIR="$NODE_DIR" "$CB" renew --cert-name "$CERT_NAME" --non-interactive \
            >/tmp/certbot-renew.log 2>&1
    else
        "$CB" renew --cert-name "$CERT_NAME" --standalone --non-interactive \
            >/tmp/certbot-renew.log 2>&1
    fi
    if copy_cert; then
        UNTIL=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        report "on" "сертификат действует до $UNTIL"
    else
        report "error" "продление не удалось, подробности в /tmp/certbot-renew.log"
    fi
    ;;

  firewall)
    # Прежняя команда охраны порта. Её ещё может позвать старый сторож на
    # узле до обновления — теперь она только убирает следы.
    old_guard_cleanup
    ;;

  off)
    # Отметку ставим ДО всего остального: если дальше что-то не доработает,
    # решение владельца всё равно уже записано и переживёт выкладку.
    : > "$OFF_MARK"
    old_guard_cleanup
    timer_off
    rm -f "$CERT_DIR/fullchain.pem" "$CERT_DIR/privkey.pem"
    report "off" "сертификат убран, страница отказа на самоподписанном"
    ;;

  status)
    if [ -s "$CERT_DIR/fullchain.pem" ]; then
        UNTIL=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        SUBJ=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -text 2>/dev/null |
               grep -A1 'Subject Alternative Name' | tail -1 | sed 's/^ *//')
        say "есть; $SUBJ; действует до $UNTIL"
    elif [ -f "$OFF_MARK" ]; then
        say "убран владельцем — выкладка его не выпустит"
    else
        say "нет"
    fi
    ;;

  *)
    say "использование: public_sub.sh ensure|on|off|renew|status [папка ноды]"
    exit 1
    ;;
esac

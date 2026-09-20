#!/bin/bash
# Подтверждение владения доменом через запись в DNS — для сертификата на «звёздочку».
#
# ЗАЧЕМ ЭТО ВООБЩЕ НУЖНО. Обычная проверка (http-01) требует, чтобы имя
# отвечало из интернета. Наши внутренние имена — «дом.example.ru»,
# «закрыто.example.ru» — снаружи не существуют вовсе, и такую проверку пройти
# не могут ни одним способом. Значит сертификата на них не будет никогда, а
# без него браузер ругается на КАЖДУЮ нашу собственную страницу: и на отказ
# фильтра, и на «доступ закрыт», и на выдачу ключей.
#
# Единственный сертификат, который покрывает имена, не существующие снаружи, —
# на «*.example.ru». И выдаётся он только по проверке dns-01: удостоверяющий
# центр просит положить в зону домена временную запись TXT. Класть её умеет
# только тот, у кого есть доступ к зоне, — то есть регистратор.
#
# ЧЕМ ЗА ЭТО ПЛАТЯТ, честно и вслух. На узле появляется доступ к управлению
# зоной домена. Если узел отнимут, отнимут и возможность переписать записи
# домена. Это настоящее повышение ставок, и принимать его должен владелец,
# а не мы за него. Уменьшить его можно и нужно:
#
#   1. В панели reg.ru у API-доступа есть белый список адресов. Впишите туда
#      адрес узла и только его. Тогда украденная пара логин-пароль бесполезна
#      откуда-либо ещё.
#   2. Пароль для API там задаётся ОТДЕЛЬНО от пароля к личному кабинету.
#      Задайте отдельный — тогда это доступ к зоне, а не ко всему аккаунту.
#   3. Пара живёт отдельным файлом на хосте, с правами 600, и ни в одно
#      окружение не попадает: ни в контейнер, ни в `docker inspect`, ни в
#      отладочный вывод. В архив бэкапа эта папка тоже не входит.
#
# Зовётся этот файл не руками, а certbot'ом — двумя крючками:
#
#   dns_regru.sh add     положить запись (certbot даёт CERTBOT_DOMAIN и
#                        CERTBOT_VALIDATION в окружении)
#   dns_regru.sh clean   убрать её же
#
# Проверить пару можно отдельно: dns_regru.sh check <папка ноды>
set -u

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SELF_DIR")"
NODE_DIR="${NODE_DIR:-${2:-$ROOT_DIR/VPS_RU}}"
ENV_FILE="$NODE_DIR/.env"

API="https://api.reg.ru/api/regru2"
# Сколько ждём, пока запись разойдётся по серверам имён домена. Пять минут —
# с запасом: reg.ru обновляет свою зону за минуту-другую. Ждать обязательно:
# центр спросит запись сразу, и не дождавшись мы получим отказ на ровном месте.
WAIT_SECONDS=300
POLL_SECONDS=10

say() { echo "[dns-01] $*"; }

# Пара живёт файлом рядом с остальными данными ноды, а не в .env.
#
# Причина простая и её стоит помнить: переменная окружения доезжает до
# контейнеров только их пересозданием. Пересоздавать всё ради пары, которой ни
# один контейнер не пользуется, — это ронять бота на ровном месте. А ещё то,
# что не попало в окружение, не попадёт ни в `docker inspect`, ни в отладочный
# вывод, ни в чужие глаза через них.
#
# .env оставлен запасным путём: у кого пара уже там, у того всё продолжит
# работать.
SECRET_FILE="$NODE_DIR/volumes/secrets/regru.conf"

read_env() {   # read_env КЛЮЧ
    for F in "$SECRET_FILE" "$ENV_FILE"; do
        [ -f "$F" ] || continue
        V=$(grep -E "^$1=" "$F" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "\"'\r")
        [ -n "$V" ] && { printf '%s' "$V"; return 0; }
    done
    return 0
}

# Экранирование для JSON: только то, что действительно ломает разбор. Пароль
# сюда попадает как есть, и кавычка в нём — обычное дело.
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

creds() {
    USER_NAME="$(read_env REGRU_API_USER)"
    USER_PASS="$(read_env REGRU_API_PASSWORD)"
    [ -n "$USER_NAME" ] && [ -n "$USER_PASS" ]
}

# Корень зоны. Имя, которое проверяет центр, выглядит как
# «_acme-challenge.example.ru», а регистратору надо сказать отдельно домен
# («example.ru») и отдельно поддомен («_acme-challenge»).
#
# Берём домен из .env, а не спрашиваем у регистратора списком: список — это
# лишний запрос с паролем, а домен у нас и так записан.
zone_parts() {   # zone_parts <полное имя из certbot>
    # Домен — наоборот, переменная окружения: им пользуется и бот тоже.
    ZONE="$(read_env PUBLIC_DOMAIN)"
    if [ -z "$ZONE" ]; then
        say "имени узла нет — не знаю, в какой зоне писать"
        return 1
    fi
    case ".$1" in
        *".$ZONE") SUB="${1%".$ZONE"}" ;;
        *)
            say "имя «$1» не из зоны «$ZONE» — не трогаю чужое"
            return 1 ;;
    esac
    [ -z "$SUB" ] && SUB="@"
    return 0
}

call() {   # call <метод> <json>
    # Весь input_data уходит одним параметром, и кодирует его curl. Так
    # безопаснее, чем собирать проценты руками: в пароле может быть что угодно.
    curl -sS --max-time 30 -X POST \
        --data-urlencode "input_data=$2" \
        --data "input_format=json" \
        "$API/$1" 2>&1
}

ok_answer() {   # ok_answer <ответ>
    # Регистратор отвечает полем result. Проверяем именно его, а не отсутствие
    # слова «error» где-нибудь в тексте: так ответ «всё хорошо, но…» не сойдёт
    # за успех, и наоборот.
    printf '%s' "$1" | grep -q '"result"[[:space:]]*:[[:space:]]*"success"'
}

# Ждём, пока запись увидят сами серверы имён домена. Спрашиваем их напрямую,
# минуя кэши: обычный резолвер может неделю помнить, что записи нет.
wait_visible() {   # wait_visible <полное имя> <значение>
    command -v dig >/dev/null 2>&1 || {
        say "dig не найден — жду вслепую 120 секунд"
        sleep 120
        return 0
    }
    NS=$(dig +short NS "$ZONE" 2>/dev/null | head -1)
    [ -z "$NS" ] && NS=""
    WAITED=0
    while [ "$WAITED" -lt "$WAIT_SECONDS" ]; do
        if [ -n "$NS" ]; then
            OUT=$(dig +short TXT "$1" "@$NS" 2>/dev/null)
        else
            OUT=$(dig +short TXT "$1" 2>/dev/null)
        fi
        if printf '%s' "$OUT" | grep -qF "$2"; then
            say "запись видна через $WAITED с"
            return 0
        fi
        sleep "$POLL_SECONDS"
        WAITED=$((WAITED + POLL_SECONDS))
    done
    # Не считаем это провалом: бывает, что свой же сервер имён отвечает
    # позже, чем видит центр. Пусть попробует — откажет, так откажет внятно.
    say "за $WAIT_SECONDS с запись так и не показалась — пробую всё равно"
    return 0
}

case "${1:-}" in
  add)
    creds || { say "пары логин-пароль для доступа к зоне нет"; exit 1; }
    zone_parts "${CERTBOT_DOMAIN:?нет CERTBOT_DOMAIN}" || exit 1
    NAME="_acme-challenge"
    [ "$SUB" != "@" ] && NAME="_acme-challenge.$SUB"
    JSON="{\"username\":\"$(json_escape "$USER_NAME")\",\"password\":\"$(json_escape "$USER_PASS")\",\"domains\":[{\"dname\":\"$ZONE\"}],\"subdomain\":\"$NAME\",\"text\":\"${CERTBOT_VALIDATION:?нет CERTBOT_VALIDATION}\",\"output_content_type\":\"plain\"}"
    ANSWER="$(call zone/add_txt "$JSON")"
    if ! ok_answer "$ANSWER"; then
        say "регистратор не принял запись:"
        printf '%s\n' "$ANSWER" | head -3 | sed 's/^/[dns-01]   /'
        exit 1
    fi
    say "запись положена: $NAME.$ZONE"
    wait_visible "$NAME.$ZONE" "$CERTBOT_VALIDATION"
    ;;

  clean)
    # Уборка обязана быть тихой и не валить выпуск: сертификат уже получен,
    # а забытая запись TXT — мусор, а не поломка.
    creds || exit 0
    zone_parts "${CERTBOT_DOMAIN:-}" || exit 0
    NAME="_acme-challenge"
    [ "$SUB" != "@" ] && NAME="_acme-challenge.$SUB"
    JSON="{\"username\":\"$(json_escape "$USER_NAME")\",\"password\":\"$(json_escape "$USER_PASS")\",\"domains\":[{\"dname\":\"$ZONE\"}],\"subdomain\":\"$NAME\",\"content\":\"${CERTBOT_VALIDATION:-}\",\"record_type\":\"TXT\",\"output_content_type\":\"plain\"}"
    ANSWER="$(call zone/remove_record "$JSON")"
    ok_answer "$ANSWER" && say "запись убрана" || say "запись убрать не вышло — она истечёт сама"
    exit 0
    ;;

  check)
    # Проверка пары БЕЗ выпуска сертификата: кладём запись и тут же убираем.
    # Нужна затем, чтобы владелец узнал об опечатке в пароле сейчас, а не через
    # минуту ожидания в середине выпуска.
    creds || { say "пары логин-пароль для доступа к зоне нет"; exit 1; }
    ZONE="$(read_env PUBLIC_DOMAIN)"
    [ -z "$ZONE" ] && { say "имени узла нет"; exit 1; }
    PROBE="vpn-proba-$(date +%s)"
    JSON="{\"username\":\"$(json_escape "$USER_NAME")\",\"password\":\"$(json_escape "$USER_PASS")\",\"domains\":[{\"dname\":\"$ZONE\"}],\"subdomain\":\"_acme-check\",\"text\":\"$PROBE\",\"output_content_type\":\"plain\"}"
    ANSWER="$(call zone/add_txt "$JSON")"
    if ! ok_answer "$ANSWER"; then
        say "не вышло — вот что ответил регистратор:"
        printf '%s\n' "$ANSWER" | head -3 | sed 's/^/[dns-01]   /'
        say "частые причины: пароль для API задаётся отдельно от пароля кабинета;"
        say "адрес узла не внесён в белый список API в панели reg.ru"
        exit 1
    fi
    JSON="{\"username\":\"$(json_escape "$USER_NAME")\",\"password\":\"$(json_escape "$USER_PASS")\",\"domains\":[{\"dname\":\"$ZONE\"}],\"subdomain\":\"_acme-check\",\"content\":\"$PROBE\",\"record_type\":\"TXT\",\"output_content_type\":\"plain\"}"
    call zone/remove_record "$JSON" >/dev/null 2>&1
    say "доступ к зоне «$ZONE» есть, запись положена и убрана"
    ;;

  *)
    say "использование: dns_regru.sh add|clean|check [папка ноды]"
    exit 1
    ;;
esac

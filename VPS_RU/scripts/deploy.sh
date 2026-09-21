#!/bin/bash
# Универсальный скрипт деплоя (сам определяет, RU это или DE).
#
# Принцип минимального даунтайма:
#   1) тянем код, 2) СОБИРАЕМ образы пока старые контейнеры ещё работают,
#   3) только если сборка удалась — быстро пересоздаём контейнеры (краткий рестарт).
# Если сборка падает (например, недоступен индекс пакетов) — прод НЕ трогаем,
# VPN продолжает работать на старой версии. Даунтайм только на шаге пересоздания.

# 0. САМОПОДМЕНА: работаем из копии, а не из файла в репозитории.
#
# Дальше идёт git reset --hard, который перезаписывает в том числе ЭТОТ скрипт.
# bash читает файл по мере выполнения, а не целиком: если содержимое сдвинулось,
# интерпретатор продолжит с той же позиции в байтах и попадёт в середину другой
# строки. Отсюда и берётся ощущение, что «обновление надо запускать дважды».
# Копируем себя во временный файл и работаем оттуда — тогда одного запуска хватает.
if [ -z "${DEPLOY_SELF_COPY:-}" ]; then
    SELF_COPY="$(mktemp /tmp/deploy_self.XXXXXX.sh)"
    cp "${BASH_SOURCE[0]}" "$SELF_COPY"
    chmod +x "$SELF_COPY"
    export DEPLOY_SELF_COPY="${BASH_SOURCE[0]}"
    bash "$SELF_COPY" "$@"
    rc=$?
    rm -f "$SELF_COPY"
    exit $rc
fi

# 1. Абсолютные пути (магия контекста)
# При работе из копии путь берём из переменной — иначе SCRIPT_DIR указал бы в /tmp.
if [ -n "${DEPLOY_SELF_COPY:-}" ] && [ -f "$DEPLOY_SELF_COPY" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$DEPLOY_SELF_COPY")" && pwd)"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
_ORIG_SCRIPT_DIR="$SCRIPT_DIR"
NODE_DIR="$(dirname "$SCRIPT_DIR")"        # VPS_RU или VPS_DE
PROJECT_ROOT="$(dirname "$NODE_DIR")"      # корень репозитория

echo "[Deploy] Начинаем процесс обновления..."
echo "[Deploy] Рабочая папка ноды: $NODE_DIR"
echo "[Deploy] Корень проекта: $PROJECT_ROOT"

# 2. Обновляем код всего проекта (контейнеры пока РАБОТАЮТ — даунтайма нет)
echo "[Deploy] Шаг 1: Обновление кода из Git..."
cd "$PROJECT_ROOT" || { echo "Ошибка: не могу перейти в корень $PROJECT_ROOT"; exit 1; }

# Подтягиваем переменные из .env ноды (если там лежит GIT_TOKEN для приватных репо)
if [ -f "$NODE_DIR/.env" ]; then
    export $(grep -E -v '^#' "$NODE_DIR/.env" | xargs)
fi

# Запоминаем ТЕКУЩИЙ коммит — на случай отката, если новая версия сломается.
PREV_HASH="$(git rev-parse HEAD 2>/dev/null)"
echo "[Deploy] Текущая версия (для возможного отката): ${PREV_HASH:0:7}"

# Шаг 0: БЭКАП БД перед обновлением (страховка). pg_dumpall из работающего postgres —
# быстро, без остановки; обе базы (vpndb бота + cpdb CP). Ротация: храним последние 5.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^vpn_db$'; then
    echo "[Deploy] Шаг 0: Бэкап БД перед обновлением..."
    BK_DIR="$NODE_DIR/volumes/backups"; mkdir -p "$BK_DIR"
    PRE_BACKUP="$BK_DIR/pre_update_$(date +%Y%m%d_%H%M%S).sql.gz"
    if docker exec vpn_db sh -c 'pg_dumpall -U "$POSTGRES_USER"' 2>/dev/null | gzip > "$PRE_BACKUP"; then
        echo "[Deploy] ✅ Бэкап: $PRE_BACKUP ($(du -h "$PRE_BACKUP" | cut -f1))"
        ls -1t "$BK_DIR"/pre_update_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
    else
        echo "[Deploy] ⚠️ Бэкап не удался — продолжаю (данные в томе сохраняются и так)"
        rm -f "$PRE_BACKUP"
    fi
fi

# ЗАЩИТА .env (креды бота/БД). Идея: .env живёт только на сервере и НЕ должен быть в git —
# тогда reset --hard его не трогает. Но некоторые старые репы всё же держат .env
# отслеживаемым, и тогда reset его снесёт. Поэтому дополнительно бэкапим .env перед reset и
# восстанавливаем после, если источник его не содержит — так креды не пропадут НИКОГДА.
ENV_BAK="/tmp/.env.$(basename "$NODE_DIR").bak"
[ -f "$NODE_DIR/.env" ] && cp -f "$NODE_DIR/.env" "$ENV_BAK"

# Источник кода — GIT_REPO из .env (единый источник истины: и деплой, и проверка обновлений
# в боте берут ИМЕННО его). Наводим origin на этот URL (с токеном для приватных репо), иначе
# деплой и проверка смотрят в РАЗНЫЕ репозитории — и бот вечно показывает «есть обновление».
if [ -n "${GIT_REPO:-}" ]; then
    AUTH_URL="$GIT_REPO"
    # если https:// и в URL ещё нет учётки (@) — подставляем токен для приватных репо
    if [ -n "${GIT_TOKEN:-}" ] && [ "${GIT_REPO#https://}" != "$GIT_REPO" ] && [ "${GIT_REPO#*@}" = "$GIT_REPO" ]; then
        if [ -n "${GIT_USERNAME:-}" ]; then
            AUTH_URL="https://${GIT_USERNAME}:${GIT_TOKEN}@${GIT_REPO#https://}"
        else
            AUTH_URL="https://${GIT_TOKEN}@${GIT_REPO#https://}"
        fi
    fi
    git remote set-url origin "$AUTH_URL" 2>/dev/null || git remote add origin "$AUTH_URL"
fi

# Сбрасываем локальные изменения (если файлы правились руками) и тянем свежие
git fetch --all
git reset --hard origin/main || git reset --hard origin/master
git pull origin main || git pull origin master

# Восстанавливаем .env, если reset --hard его снёс (в источнике его нет, напр. _pub).
if [ ! -f "$NODE_DIR/.env" ] && [ -f "$ENV_BAK" ]; then
    cp -f "$ENV_BAK" "$NODE_DIR/.env"
    echo "[Deploy] .env восстановлен из бэкапа (креды сохранены)"
fi

# 1b. ПЕРЕХОД НА ОБНОВЛЁННЫЙ СКРИПТ.
#
# Работаем из копии, снятой ДО git pull, — иначе reset --hard перезаписал бы файл
# у нас под ногами. Но из этого следует неприятное: правки в самом деплое не
# действуют никогда. Скрипт делает свою работу по старым правилам, а новые лежат
# рядом и ждут следующего раза, которого при неудаче не наступит: откат
# возвращает дерево назад вместе с ними.
#
# Так и вышло: проверка после обновления отклоняла здоровую версию, а починка
# этой проверки не могла доехать, потому что её отбрасывала она же.
#
# Поэтому: код обновился — передаём работу новому скрипту. Один раз, по метке,
# чтобы не закружиться.
if [ -z "${DEPLOY_HANDOVER:-}" ] && [ -f "$_ORIG_SCRIPT_DIR/deploy.sh" ]; then
    if ! cmp -s "$0" "$_ORIG_SCRIPT_DIR/deploy.sh"; then
        echo "[Deploy] Скрипт обновления изменился — передаю работу новой версии."
        NEW_COPY="$(mktemp /tmp/deploy_new.XXXXXX.sh)"
        cp "$_ORIG_SCRIPT_DIR/deploy.sh" "$NEW_COPY"
        chmod +x "$NEW_COPY"
        DEPLOY_HANDOVER=1 DEPLOY_SELF_COPY="$_ORIG_SCRIPT_DIR/deploy.sh"             bash "$NEW_COPY" "$@"
        rc=$?
        rm -f "$NEW_COPY"
        exit $rc
    fi
fi

# Фиксируем актуальный коммит, чтобы бот не считал, что обновление всё ещё доступно.
# (Раньше volumes/VERSION писался только install.sh → локальный хеш «застывал».)
mkdir -p "$NODE_DIR/volumes"
NEW_HASH="$(git rev-parse HEAD 2>/dev/null | cut -c1-7)"
if [ -n "$NEW_HASH" ]; then
    echo "$NEW_HASH" > "$NODE_DIR/volumes/VERSION"
    echo "[Deploy] Текущий коммит зафиксирован: $NEW_HASH"
fi

# 3. Права на скрипты этой ноды
echo "[Deploy] Шаг 2: Выдача прав на скрипты в папке $NODE_DIR..."
cd "$NODE_DIR" || exit 1
find . -type f -name "*.sh" -exec chmod +x {} \;
# Общие скрипты лежат вне папки ноды, а запускают их и systemd-юниты, и сам
# деплой. Без бита запуска они молча упираются в «Permission denied» — так и
# вышло с настройкой подписки: шаг отработал за секунду и ничего не сделал.
find "$PROJECT_ROOT/scripts" -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null

# 3b. Гарантируем swap И ПРИ ОБНОВЛЕНИИ (а не только при install.sh): если на ноде
# его ещё нет — подтянется сам. Идемпотентно, прод не трогает.
if [ -f "$PROJECT_ROOT/scripts/ensure_swap.sh" ]; then
    echo "[Deploy] Шаг 2b: Проверка swap..."
    bash "$PROJECT_ROOT/scripts/ensure_swap.sh" || true
fi

# 3c. Ночные авто-обновления системы (идемпотентно): переносим apt на ночь, чтобы
#     обновления не спайкали нагрузку среди дня на 1-ядерном VPS. Прод не трогает.
if [ -f "$PROJECT_ROOT/scripts/ensure_host_maintenance.sh" ]; then
    echo "[Deploy] Шаг 2c: Настройка ночных авто-обновлений..."
    bash "$PROJECT_ROOT/scripts/ensure_host_maintenance.sh" "$NODE_DIR" || true
fi

# 3d. Версия проекта для тегов образов. Берём из файла VERSION (сначала ноды, потом корня),
#     чтобы в `docker images` было видно, какая версия крутится, вместо безликого latest.
# Источник версии ОДИН — корневой файл. Версия в папке ноды когда-то отстала
# и молча подсовывалась вместо настоящей: образы получали чужой тег, а бот
# показывал старый номер.
if [ -f "$PROJECT_ROOT/VERSION" ]; then
    APP_VERSION="$(tr -d '[:space:]' < "$PROJECT_ROOT/VERSION")"
elif [ -f "$NODE_DIR/VERSION" ]; then
    APP_VERSION="$(tr -d '[:space:]' < "$NODE_DIR/VERSION")"
else
    APP_VERSION="dev"
fi
export APP_VERSION

# Кладём версию в .env, а не только в это окружение. Теги образов в compose —
# `${APP_VERSION:-dev}`, и без переменной любой другой вызов `docker compose`
# (демон обновлений, сторож, руки) соберёт себе `:dev` с нуля вместо того, чтобы
# взять готовый образ. Файл гитом не отслеживается — выкладка его не затрёт.
if [ -f "$NODE_DIR/.env" ]; then
    if grep -q "^APP_VERSION=" "$NODE_DIR/.env"; then
        sed -i "s|^APP_VERSION=.*|APP_VERSION=$APP_VERSION|" "$NODE_DIR/.env"
    else
        echo "APP_VERSION=$APP_VERSION" >> "$NODE_DIR/.env"
    fi
fi
echo "[Deploy] Версия проекта: $APP_VERSION (тег образов)"

# 3e. Демон хоста крутит СТАРЫЙ файл скрипта: git его заменил, но процесс уже
#     запущен со старым кодом, и новые возможности демона заработали бы только со
#     второго обновления.
#
#     ВАЖНО: перезапускать его здесь нельзя — когда обновление запущено кнопкой
#     из бота, именно этот демон и является нашим родителем, и перезапуск оборвал бы
#     деплой на середине. Он планируется в самом конце скрипта, см. пояснение там.

# 4. СБОРКА новых образов, пока старые контейнеры ещё работают (даунтайм = 0)
echo "[Deploy] Шаг 3: Сборка новых образов (старые контейнеры продолжают работать)..."
# Сборка пишет полосу прогресса псевдографикой и перерисовывает её
# десятки раз в секунду. В терминале это одна строка, а в журнале —
# отдельная запись на каждую перерисовку: на узле выхода за один деплой
# так набежало 2,5 миллиона строк и полгигабайта syslog при диске в 10 ГБ.
# `--progress plain` пишет по строке на шаг, а не на кадр.
# Сборка идёт с пониженным приоритетом. На одном ядре она иначе забирает узел
# себе: замеренная средняя нагрузка доходила до пяти, и люди в этот момент
# чувствовали VPN тормозящим — хотя ничего не ломалось, просто очередь.
#
# Сборке спешить некуда, туннелю — есть куда. nice отдаёт ей процессор по
# остаточному принципу, ionice — диск (а пишет она много и мелко), и один поток
# вместо нескольких: на одном ядре параллельные шаги ничего не ускоряют, а
# очередь удлиняют.
BUILD_NICE=""
command -v nice >/dev/null 2>&1 && BUILD_NICE="nice -n 15"
command -v ionice >/dev/null 2>&1 && BUILD_NICE="$BUILD_NICE ionice -c2 -n7"

if ! env BUILDKIT_MAX_PARALLELISM=1 $BUILD_NICE docker compose build --progress plain; then
    echo "[Deploy] ❌ Сборка не удалась — работающие контейнеры НЕ трогаю."
    echo "[Deploy] Деплой отменён, VPN продолжает работать на старой версии."
    exit 1
fi

# 5. Быстрое пересоздание контейнеров на новых образах (минимальный даунтайм).
#    --remove-orphans: снести контейнеры сервисов, которых больше нет в compose
#    (например, удалённые control_plane/caddy) — чтобы не висели и не жрали ресурсы.
echo "[Deploy] Шаг 4: Применение новых образов (краткий перезапуск)..."
docker compose up -d --remove-orphans

# 6. HEALTH-CHECK новой версии. Если контейнер крашится/рестартит — ОТКАТ на предыдущую
#    версию (даунгрейд): возвращаем код, пересобираем, поднимаем. VPN/данные защищены.
echo "[Deploy] Шаг 5: Health-check новой версии (даю контейнерам подняться)..."
sleep 15
problem=""

# Health-gate МАРШРУТИЗАЦИИ (по мотивам gateway-selfcheck из OpenWRT): контейнеры могут
# быть "running", но ядро VPN сломано (нет wg0 / пустая table 200 / нет fwmark / API молчит).
# Тогда прод "жив", но трафик не ходит. Проверяем на RU-ноде; провал → тот же откат.
#
# Проверяем НЕ одним выстрелом. Раньше здесь была единственная попытка через 25
# секунд после пересоздания, и этого хватало ровно до тех пор, пока узел
# стартовал быстро. На одном ядре, сразу после сборки, панель узла поднимается
# дольше: она читает списки фильтров на сотни тысяч имён. Деплой, который через
# десять секунд был бы здоров, откатывался как больной — и это худший вид
# поломки, потому что выглядит он как защита.
#
# Даём полторы минуты и опрашиваем каждые три секунды. Первый успех выигрывает.
# Настоящая поломка от этого не спрячется: она не пройдёт ни одной попытки, а
# рухнувший контейнер поймает проверка состояний ниже.
HEALTH_WAIT=90
HEALTH_STEP=3

routing_health() {   # печатает причину или молчит, если всё хорошо
    docker exec vpn_wireguard ip link show wg0 >/dev/null 2>&1 || { echo 'нет wg0'; return; }
    docker exec vpn_wireguard ip route show table 200 2>/dev/null | grep -q '^default' || { echo 'table200 без default'; return; }
    docker exec vpn_wireguard sh -c 'ip rule show 2>/dev/null | grep -qi "fwmark 0xc8"' || { echo 'нет fwmark-правила'; return; }
    docker exec vpn_wireguard sh -c 'curl -sf --max-time 5 http://127.0.0.1:8000/api/health >/dev/null 2>&1' || { echo 'wg-api не отвечает'; return; }
}

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^vpn_wireguard$'; then
    WAITED=0
    while :; do
        rc_msg="$(routing_health)"
        [ -z "$rc_msg" ] && break
        [ "$WAITED" -ge "$HEALTH_WAIT" ] && break
        sleep "$HEALTH_STEP"
        WAITED=$((WAITED + HEALTH_STEP))
    done
    if [ -n "$rc_msg" ]; then
        problem="$problem routing($rc_msg, ждали ${WAITED}с)"
    elif [ "$WAITED" -gt 0 ]; then
        echo "[Deploy] Ядро маршрутизации поднялось через ${WAITED}с."
    fi
fi

# Состояния контейнеров смотрим ПОСЛЕ ожидания: контейнер, падающий по кругу, к
# этому моменту успеет показать себя, а медленный — успеет подняться.
for id in $(docker compose ps -q 2>/dev/null); do
    name="$(docker inspect -f '{{.Name}}' "$id" 2>/dev/null | sed 's#^/##')"
    st="$(docker inspect -f '{{.State.Status}}' "$id" 2>/dev/null)"
    case "$st" in
        restarting|exited|dead) problem="$problem $name($st)";;
    esac
done

if [ -n "$problem" ] && [ -n "$PREV_HASH" ]; then
    echo "[Deploy] ⛔ Новая версия нездорова:$problem"
    # Откат уносит с собой и улики. Без этих строк остаётся только «не
    # отвечает», а почему — выяснять уже негде: контейнеры пересозданы.
    for c in vpn_wireguard vpn_bot; do
        docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$c" || continue
        echo "[Deploy] --- последние строки $c ---"
        docker logs --tail 25 "$c" 2>&1 | sed 's/^/[Deploy]   /'
    done
    echo "[Deploy] ↩️  ОТКАТ на предыдущую версию ${PREV_HASH:0:7}..."
    cd "$PROJECT_ROOT" && git reset --hard "$PREV_HASH"
    cd "$NODE_DIR"
    if env BUILDKIT_MAX_PARALLELISM=1 $BUILD_NICE docker compose build --progress plain \
            && docker compose up -d; then
        echo "${PREV_HASH:0:7}" > "$NODE_DIR/volumes/VERSION"
        echo "[Deploy] ✅ Откат выполнен — прод снова на рабочей версии ${PREV_HASH:0:7}."
        echo "[Deploy] ℹ️  Бэкап БД до апдейта: $PRE_BACKUP (восстановить вручную при необходимости)."
    else
        echo "[Deploy] ❌ Откат не собрался — нужно вмешательство руками. Бэкап: $PRE_BACKUP"
    fi
    docker image prune -f
    exit 1
fi
echo "[Deploy] ✅ Health-check ок — новая версия работает."

# 6b. Метка для бота: пересозданный бот её ловит (поллит ~3 мин) и шлёт «✅ Обновление
#     завершено» с актуальной версией. Ставится ТОЛЬКО при успехе (на откате — нет),
#     поэтому ложного уведомления при неудаче не будет.
mkdir -p "$NODE_DIR/volumes/flags" && date +%s > "$NODE_DIR/volumes/flags/was_updating"

# 7. Сборщик мусора. Докер (неиспользуемые образы, кэш сборки, остановленные
#    контейнеры), кэш пакетов, старые ядра, хвосты удалённых пакетов, прошивки
#    железа, которого на виртуальной машине нет. Именованные тома не трогает:
#    данные проекта лежат в ./volumes. Каждое удаление сборщик сначала
#    проигрывает всухую и отменяет шаг целиком, если под нож идёт нужное.
#    Дальше за мусором следит недельная уборка тем же сборщиком.
# Подписка наружу. Идёт при каждой выкладке и ничего не перевыпускает, пока
# сертификат свеж, — это проверка, а не действие. Нужна она потому, что
# сертификат на IP живёт неделю: узел, простоявший выключенным восемь дней,
# поднялся бы с мёртвым сертификатом и молчащим входом.
#
# Заодно возвращаются правила охраны порта: их снимает перезапуск докера, а
# докер здесь перезапускается каждый раз.
if [ -f "$PROJECT_ROOT/scripts/public_sub.sh" ]; then
    echo "[Deploy] Подписка наружу..."
    # Ошибку не глотаем молча: подписка не обязана подняться (может не быть
    # свободного порта 80, может не ответить удостоверяющий центр), но знать об
    # этом надо — иначе люди останутся без автообновления, а в журнале будет
    # ровно ничего.
    if ! bash "$PROJECT_ROOT/scripts/public_sub.sh" ensure "$NODE_DIR"; then
        echo "[Deploy] ⚠️  Подписка наружу не поднялась — см. строки выше."
        echo "[Deploy]     Внутри туннеля она работает, обновление в силе."
    fi
fi

# Сверка базы с узлом сразу после обновления. Раньше она шла только по
# воскресеньям, а расходится состояние как раз при выкладке: не доехала
# команда, не поднялся контейнер, потерялось правило. Ждать до выходных, чтобы
# об этом узнать, — неделя с молча сломанным узлом.
#
# Ничего не меняет, только читает. Результат кладётся в volumes/flags, откуда
# его берёт недельный отчёт, и дублируется в журнал системы.
#
# Идёт ПОСЛЕ подписки, и это важно. Перезапуск докера снимает правила охраны
# порта, возвращает их шаг подписки — а сверка стояла перед ним и каждый раз
# видела молчащий вход. В отчёте после КАЖДОЙ выкладки лежало расхождение
# «сертификат есть, а порт молчит», которого через минуту уже не было.
# Проверка, которая врёт по расписанию, обесценивает и остальные свои строки.
if [ -f "$PROJECT_ROOT/scripts/contract_check.sh" ]; then
    echo "[Deploy] Сверка базы с узлом..."
    bash "$PROJECT_ROOT/scripts/contract_check.sh" "$NODE_DIR" || true
fi

if [ -f "$PROJECT_ROOT/scripts/gc.sh" ]; then
    GC_FLAGS_DIR="$NODE_DIR/volumes/flags" bash "$PROJECT_ROOT/scripts/gc.sh" || true
else
    docker system prune -af
fi

echo "[Deploy] ✅ Обновление успешно завершено для ноды $(basename "$NODE_DIR")!"

# --- Перезапуск демона обновления, последним делом ------------------------
# Демон запускает выкладку отдельной службой, так что перезапуск её не тронет.
# Но и сам перезапуск должен быть точным и повторяемым — тут было две ловушки.
#
# Первая: у таймеров systemd погрешность по умолчанию — минута. «Через 15
# секунд» на деле срабатывало через 65, ровно посреди следующей выкладки.
# AccuracySec=1s возвращает сроку смысл.
#
# Вторая: имя службы постоянное, а --collect не стоял. Отработавшая единица
# оставалась висеть, и следующее планирование упиралось в занятое имя — молча,
# потому что вывод уходил в /dev/null, а ошибку глотал || true. Демон тогда не
# перезапускался вовсе: новый код лежал на диске, а работал старый.
if command -v systemd-run >/dev/null 2>&1; then
    if systemd-run --on-active=15 --unit=vpn-updater-refresh --collect \
        --timer-property=AccuracySec=1s \
        systemctl restart "vpn-updater" >/dev/null 2>&1; then
        echo "[Deploy] Демон хоста перезапустится через 15 секунд — подхватит новый код."
    else
        echo "[Deploy] ⚠️  Не удалось назначить перезапуск демона — он останется на старом коде."
        echo "[Deploy]     Поправить руками: systemctl restart vpn-updater"
    fi
fi

# --- BBR: УПРАВЛЕНИЕ ПЕРЕГРУЗКОЙ TCP --------------------------------------
# Узел, поставленный до появления этой настройки, её не имеет, а установщик на
# нём больше не запускается. Ставим при обновлении — идемпотентно и нефатально.
if [ ! -f /etc/sysctl.d/99-bbr.conf ] && modprobe tcp_bbr 2>/dev/null; then
    grep -qx tcp_bbr /etc/modules-load.d/bbr.conf 2>/dev/null \
        || echo tcp_bbr > /etc/modules-load.d/bbr.conf
    printf 'net.core.default_qdisc = fq\nnet.ipv4.tcp_congestion_control = bbr\n' \
        > /etc/sysctl.d/99-bbr.conf
    sysctl -q -p /etc/sysctl.d/99-bbr.conf 2>/dev/null || true
    echo "[Deploy] Управление перегрузкой TCP: $(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null)"
fi

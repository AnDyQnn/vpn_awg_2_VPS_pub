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
if ! docker compose build --progress plain; then
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
sleep 25
problem=""
for id in $(docker compose ps -q 2>/dev/null); do
    name="$(docker inspect -f '{{.Name}}' "$id" 2>/dev/null | sed 's#^/##')"
    st="$(docker inspect -f '{{.State.Status}}' "$id" 2>/dev/null)"
    case "$st" in
        restarting|exited|dead) problem="$problem $name($st)";;
    esac
done

# Health-gate МАРШРУТИЗАЦИИ (по мотивам gateway-selfcheck из OpenWRT): контейнеры могут
# быть "running", но ядро VPN сломано (нет wg0 / пустая table 200 / нет fwmark / API молчит).
# Тогда прод "жив", но трафик не ходит. Проверяем на RU-ноде; провал → тот же откат.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^vpn_wireguard$'; then
    rc_msg="$(
        docker exec vpn_wireguard ip link show wg0 >/dev/null 2>&1 || { echo 'нет wg0'; exit 0; }
        docker exec vpn_wireguard ip route show table 200 2>/dev/null | grep -q '^default' || { echo 'table200 без default'; exit 0; }
        docker exec vpn_wireguard sh -c 'ip rule show 2>/dev/null | grep -qi "fwmark 0xc8"' || { echo 'нет fwmark-правила'; exit 0; }
        docker exec vpn_wireguard sh -c 'curl -sf --max-time 5 http://127.0.0.1:8000/api/health >/dev/null 2>&1' || { echo 'wg-api не отвечает'; exit 0; }
    )"
    [ -n "$rc_msg" ] && problem="$problem routing($rc_msg)"
fi

if [ -n "$problem" ] && [ -n "$PREV_HASH" ]; then
    echo "[Deploy] ⛔ Новая версия нездорова:$problem"
    echo "[Deploy] ↩️  ОТКАТ на предыдущую версию ${PREV_HASH:0:7}..."
    cd "$PROJECT_ROOT" && git reset --hard "$PREV_HASH"
    cd "$NODE_DIR"
    if docker compose build --progress plain && docker compose up -d; then
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
# Сверка базы с узлом сразу после обновления. Раньше она шла только по
# воскресеньям, а расходится состояние как раз при выкладке: не доехала
# команда, не поднялся контейнер, потерялось правило. Ждать до выходных, чтобы
# об этом узнать, — неделя с молча сломанным узлом.
#
# Ничего не меняет, только читает. Результат кладётся в volumes/flags, откуда
# его берёт недельный отчёт, и дублируется в журнал системы.
if [ -f "$PROJECT_ROOT/scripts/contract_check.sh" ]; then
    echo "[Deploy] Сверка базы с узлом..."
    bash "$PROJECT_ROOT/scripts/contract_check.sh" "$NODE_DIR" || true
fi

# Подписка наружу. Идёт при каждой выкладке и ничего не перевыпускает, пока
# сертификат свеж, — это проверка, а не действие. Нужна она потому, что
# сертификат на IP живёт неделю: узел, простоявший выключенным восемь дней,
# поднялся бы с мёртвым сертификатом и молчащим входом.
#
# Заодно возвращаются правила охраны порта: их снимает перезапуск докера, а
# докер здесь перезапускается каждый раз.
if [ -f "$PROJECT_ROOT/scripts/public_sub.sh" ]; then
    echo "[Deploy] Подписка наружу..."
    bash "$PROJECT_ROOT/scripts/public_sub.sh" ensure "$NODE_DIR" || true
fi

if [ -f "$PROJECT_ROOT/scripts/gc.sh" ]; then
    GC_FLAGS_DIR="$NODE_DIR/volumes/flags" bash "$PROJECT_ROOT/scripts/gc.sh" || true
else
    docker system prune -af
fi

echo "[Deploy] ✅ Обновление успешно завершено для ноды $(basename "$NODE_DIR")!"

# --- Перезапуск демона обновления, последним делом ------------------------
# Когда обновление запущено кнопкой из бота, этот демон — наш родитель, и его
# перезапуск обрывает деплой. Раньше задача ставилась «через минуту» в начале,
# но сборка идёт три-пять минут, и перезапуск приходился ровно на её середину.
# Теперь он планируется здесь: работа уже сделана, осталось только выйти.
if command -v systemd-run >/dev/null 2>&1; then
    systemd-run --on-active=15 --unit=vpn-updater-refresh \
        systemctl restart "vpn-updater" >/dev/null 2>&1 || true
    echo "[Deploy] Демон хоста перезапустится через 15 секунд — подхватит новый код."
fi

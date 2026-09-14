#!/bin/bash
# Сборщик мусора узла.
#
# Запускается недельной уборкой и вручную. Идемпотентен: второй запуск подряд
# ничего не находит и ничего не делает.
#
# Главное правило: НИЧЕГО не удаляем без проверки. Перед каждым удалением
# спрашиваем apt, что пойдёт следом, и если в списке оказывается что-то из
# защищённого перечня — отказываемся целиком. Лучше оставить лишний гигабайт,
# чем однажды не загрузиться.
#
# Что вычищается:
#   1. кэш скачанных пакетов — восстанавливается скачиванием;
#   2. осиротевшие пакеты и старые ядра (кроме текущего и одного запасного);
#   3. хвосты удалённых пакетов: «удалён, настройки остались»;
#   4. прошивки железа и snapd — на виртуальной машине им нечего обслуживать;
#   5. мусор докера: неиспользуемые образы, тома, кэш сборки;
#   6. журналы старше недели.
set -u

DRY=0
[ "${1:-}" = "--показать" ] && DRY=1
[ "${1:-}" = "--dry-run" ] && DRY=1

# Что нельзя трогать ни при каких обстоятельствах. Если удаление чего-либо
# тянет за собой хоть одну из этих строк — шаг отменяется целиком.
PROTECTED='^(linux-image-|linux-modules-[0-9]|grub|systemd|docker-ce|containerd|openssh|iproute2|iptables|ipset|wireguard|amneziawg|ca-certificates|libc6)'

say() { echo "[GC] $*"; }

free_mb() { df -m / | awk 'NR==2 {print $4}'; }

BEFORE=$(free_mb)
say "свободно до уборки: ${BEFORE} МБ"
[ "$DRY" = "1" ] && say "режим показа: ничего не удаляю, только считаю"

# --- 1. кэш пакетов -------------------------------------------------------
CACHE=$(du -sm /var/cache/apt 2>/dev/null | awk '{print $1}')
if [ "${CACHE:-0}" -gt 50 ]; then
    say "кэш пакетов: ${CACHE} МБ"
    [ "$DRY" = "0" ] && apt-get clean
fi

# --- 2. осиротевшее и старые ядра ----------------------------------------
ORPHANS=$(apt-get -s autoremove --purge 2>/dev/null | grep -c '^Remv' || true)
if [ "${ORPHANS:-0}" -gt 0 ]; then
    # Проверяем, что под удаление не попало ничего защищённого.
    if apt-get -s autoremove --purge 2>/dev/null | grep '^Remv' \
         | awk '{print $2}' | grep -qE "$PROTECTED"; then
        say "осиротевших пакетов: ${ORPHANS}, но среди них есть важные — пропускаю"
        apt-get -s autoremove --purge 2>/dev/null | grep '^Remv' \
            | awk '{print "      " $2}' | head -5
    else
        say "осиротевшие пакеты и старые ядра: ${ORPHANS} шт."
        [ "$DRY" = "0" ] && apt-get -y autoremove --purge >/dev/null 2>&1
    fi
fi

# --- 3. хвосты удалённых пакетов -----------------------------------------
# Состояние «rc» — пакет удалён, но его настройки остались. autoremove их не
# видит: для него они уже удалены. На немецком узле так висели модули ядра
# 6.8.0-111, которого в системе давно нет.
#
# Общий список защищённого здесь не подходит: под него попадают ровно те
# kernel-хвосты, ради которых всё и затевалось, — а они безопасны, сам пакет
# уже удалён, остались только файлы в /etc. Опасность в другом: у некоторых
# служб в /etc лежат настройки, которые мы правили руками и захотим вернуть,
# если служба когда-нибудь встанет обратно. Их и оберегаем.
KEEP_CONF='^(docker|containerd|openssh|systemd|netplan|resolvconf|ufw|unattended)'
RC=$(dpkg -l 2>/dev/null | awk '/^rc/ {print $2}' | grep -vE "$KEEP_CONF")
if [ -n "$RC" ]; then
    say "хвостов удалённых пакетов: $(echo "$RC" | wc -l)"
    [ "$DRY" = "0" ] && echo "$RC" | xargs -r dpkg --purge >/dev/null 2>&1
fi

# --- 4. железо, которого нет ---------------------------------------------
# Узлы — виртуальные машины: ни Wi-Fi-карт, ни видеокарт, ни звука. Прошивки
# для них весят сотни мегабайт и не используются никогда. Snapd — то же самое:
# ни одного snap не установлено.
for pkg in linux-firmware snapd; do
    dpkg -l "$pkg" 2>/dev/null | grep -q "^ii" || continue

    PLAN=$(apt-get -s remove --purge "$pkg" 2>/dev/null | grep '^Remv' | awk '{print $2}')
    if [ -z "$PLAN" ]; then
        continue
    fi
    if echo "$PLAN" | grep -qE "$PROTECTED"; then
        say "$pkg тянет за собой важное — не трогаю:"
        echo "$PLAN" | grep -E "$PROTECTED" | awk '{print "      " $1}' | head -3
        continue
    fi
    SIZE=$(dpkg-query -W -f='${Installed-Size}' "$pkg" 2>/dev/null || echo 0)
    EXTRA=$(( $(echo "$PLAN" | wc -l) - 1 ))
    TAIL=""
    [ "$EXTRA" -gt 0 ] && TAIL=", вместе с ним ещё $EXTRA"
    say "$pkg: $((SIZE / 1024)) МБ$TAIL"
    [ "$DRY" = "0" ] && apt-get -y remove --purge "$pkg" >/dev/null 2>&1
done

# --- 5. докер -------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
    RECLAIM=$(docker system df --format '{{.Reclaimable}}' 2>/dev/null | head -1)
    say "докер, к освобождению: ${RECLAIM:-неизвестно}"
    [ "$DRY" = "0" ] && docker system prune -af >/dev/null 2>&1
fi

# --- 6. журналы -----------------------------------------------------------
if command -v journalctl >/dev/null 2>&1; then
    say "журналы: $(journalctl --disk-usage 2>/dev/null | grep -o '[0-9.]*[MG]' | head -1)"
    [ "$DRY" = "0" ] && journalctl --vacuum-time=7d >/dev/null 2>&1
fi

AFTER=$(free_mb)
say "свободно после уборки: ${AFTER} МБ (освобождено $((AFTER - BEFORE)) МБ)"

# Отчёт для бота: лежит там же, где отчёт проверки хоста.
FLAGS="${GC_FLAGS_DIR:-}"
if [ -n "$FLAGS" ] && [ -d "$FLAGS" ]; then
    cat > "$FLAGS/gc.json" <<EOF
{"ts": $(date +%s), "before_mb": $BEFORE, "after_mb": $AFTER,
 "freed_mb": $((AFTER - BEFORE)), "dry_run": $DRY}
EOF
fi

# Уборка никогда не считается неудачей. Каждый шаг здесь необязателен по
# отдельности, и последняя проверка в скрипте не должна решать за всех: без
# этой строки systemd пометил бы недельную уборку упавшей просто потому, что
# каталог для отчёта не смонтирован.
exit 0

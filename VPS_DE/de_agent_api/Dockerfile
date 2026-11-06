# Используем официальный образ AmneziaWG
# Базовый образ ЗАКРЕПЛЁН по digest, а не по тегу latest.
# С latest апстрим мог подменить бинарник WireGuard при любой пересборке — а пересборка
# случается на каждом деплое. Это единственный способ уронить туннель «само по себе».
# Обновлять осознанно: docker pull amneziavpn/amnezia-wg:latest, взять новый digest,
# заменить строку ниже, проверить на стенде.
FROM amneziavpn/amnezia-wg@sha256:ea050861bd2012a6265817636ce7c0c15764ef955782d953cef42e05c1381250
# Копии wg и wg-quick мимо /usr/bin. В новых Ubuntu (24.10+) у хоста есть
# профили AppArmor «wg» и «wg-quick»: они цепляются к /usr/bin/wg по пути и
# действуют даже внутри контейнера — не дают wg подключиться к сокету
# wireguard-go (/run/wireguard/wg0.sock), и узел падал на старте. Профиль
# ловит wg в любом системном bin/sbin (в /usr/local/sbin тоже — проверено),
# поэтому копия лежит в /opt/wgtools/bin и стоит в PATH первой: все вызовы
# «wg» попадают на неё. На старых Ubuntu ничего не меняется.
RUN mkdir -p /opt/wgtools/bin && \
    for b in wg wg-quick; do [ -x /usr/bin/$b ] && cp /usr/bin/$b /opt/wgtools/bin/$b; done; true
ENV PATH="/opt/wgtools/bin:${PATH}"

# Устанавливаем Python и системные зависимости (включая компиляторы для psutil)
# Устойчивость к блокировке зеркала Alpine (ТСПУ/провайдер иногда режут dl-cdn):
# перебираем зеркала, меняя только ХОСТ (версия Alpine сохраняется через sed) —
# сначала штатное, затем RU-дружественные (yandex, aliyun). Плохое зеркало пропускается.
RUN set -e; \
    pkgs="python3 py3-pip iproute2 iptables curl bash procps iputils gcc musl-dev python3-dev linux-headers"; \
    cp /etc/apk/repositories /etc/apk/repositories.orig; \
    ok=0; \
    for M in "KEEP" "https://mirror.yandex.ru/mirrors/alpine" "https://mirrors.aliyun.com/alpine"; do \
        if [ "$M" = "KEEP" ]; then cp /etc/apk/repositories.orig /etc/apk/repositories; \
        else sed -E "s#https?://[^/]+/alpine#$M#g" /etc/apk/repositories.orig > /etc/apk/repositories; fi; \
        if apk add --no-cache $pkgs; then ok=1; break; fi; \
        echo ">>> apk-зеркало недоступно, пробую следующее..."; \
    done; \
    [ "$ok" = "1" ] || { echo "ВСЕ apk-зеркала недоступны" >&2; exit 1; }

# Создаем виртуальное окружение и ставим пакеты.
# Устойчивость к блокировке/недоступности индекса пакетов (даунтайм в проде недопустим):
# перебираем источники, первый рабочий выигрывает: свой PIP_MIRROR -> PyPI -> aliyun -> tuna.
COPY requirements.txt /app/requirements.txt
ARG PIP_MIRROR=
RUN python3 -m venv /opt/venv && \
    ok=0; \
    for IDX in "$PIP_MIRROR" "DEFAULT" "https://mirrors.aliyun.com/pypi/simple/" "https://pypi.tuna.tsinghua.edu.cn/simple/"; do \
        [ -z "$IDX" ] && continue; \
        echo ">>> pip via ${IDX}"; \
        if [ "$IDX" = "DEFAULT" ]; then \
            /opt/venv/bin/pip install --no-cache-dir --timeout 20 --retries 1 -r /app/requirements.txt && { ok=1; break; }; \
        else \
            /opt/venv/bin/pip install --no-cache-dir --timeout 60 --retries 3 --index-url "$IDX" -r /app/requirements.txt && { ok=1; break; }; \
        fi; \
        echo ">>> источник недоступен, пробую следующий..."; \
    done; \
    [ "$ok" = "1" ] || { echo "ВСЕ источники pip недоступны" >&2; exit 1; }


# Копируем скрипты
COPY run_api.sh /run_api.sh
RUN chmod +x /run_api.sh

COPY api.py /app/api.py
WORKDIR /app

# Переопределяем Entrypoint для запуска FastAPI
ENTRYPOINT ["/run_api.sh"]
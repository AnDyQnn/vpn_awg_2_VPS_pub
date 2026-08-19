# Используем официальный образ AmneziaWG
FROM amneziavpn/amnezia-wg:latest

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
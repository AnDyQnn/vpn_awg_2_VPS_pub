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

# Устойчивость к блокировке зеркала Alpine (ТСПУ/провайдер иногда режут dl-cdn):
# перебираем зеркала, меняя только ХОСТ (версия Alpine сохраняется через sed) —
# сначала штатное, затем RU-дружественные (yandex, aliyun). Плохое зеркало пропускается.
RUN set -e; \
    pkgs="python3 py3-pip iproute2 iptables curl bash procps iputils ipset openssl"; \
    cp /etc/apk/repositories /etc/apk/repositories.orig; \
    ok=0; \
    for M in "KEEP" "https://mirror.yandex.ru/mirrors/alpine" "https://mirrors.aliyun.com/alpine"; do \
        if [ "$M" = "KEEP" ]; then cp /etc/apk/repositories.orig /etc/apk/repositories; \
        else sed -E "s#https?://[^/]+/alpine#$M#g" /etc/apk/repositories.orig > /etc/apk/repositories; fi; \
        if apk add --no-cache $pkgs; then ok=1; break; fi; \
        echo ">>> apk-зеркало недоступно, пробую следующее..."; \
    done; \
    [ "$ok" = "1" ] || { echo "ВСЕ apk-зеркала недоступны" >&2; exit 1; }

# Устойчивость к блокировке/недоступности индекса пакетов (даунтайм в проде недопустим).
# Перебираем источники, первый рабочий выигрывает: свой PIP_MIRROR -> PyPI -> aliyun -> tuna.
# Свой первым: docker compose build --build-arg PIP_MIRROR=<url-до-simple/>
ARG PIP_MIRROR=
RUN python3 -m venv /opt/venv && \
    ok=0; \
    for IDX in "$PIP_MIRROR" "DEFAULT" "https://mirrors.aliyun.com/pypi/simple/" "https://pypi.tuna.tsinghua.edu.cn/simple/"; do \
        [ -z "$IDX" ] && continue; \
        echo ">>> pip via ${IDX}"; \
        if [ "$IDX" = "DEFAULT" ]; then \
            /opt/venv/bin/pip install --no-cache-dir --timeout 20 --retries 1 fastapi uvicorn pydantic && { ok=1; break; }; \
        else \
            /opt/venv/bin/pip install --no-cache-dir --timeout 60 --retries 3 --index-url "$IDX" fastapi uvicorn pydantic && { ok=1; break; }; \
        fi; \
        echo ">>> источник недоступен, пробую следующий..."; \
    done; \
    [ "$ok" = "1" ] || { echo "ВСЕ источники pip недоступны" >&2; exit 1; }

COPY update_ru_ips.sh /app/update_ru_ips.sh
COPY run_api.sh /run_api.sh
RUN chmod +x /run_api.sh && chmod +x /app/update_ru_ips.sh

COPY api.py /app/api.py
COPY dnsfilter.py /app/dnsfilter.py
COPY blocked.html /app/blocked.html
COPY update_dns_lists.sh /app/update_dns_lists.sh
WORKDIR /app

ENTRYPOINT ["/run_api.sh"]
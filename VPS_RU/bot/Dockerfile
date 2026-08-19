FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные утилиты прямо в образ.
# Устойчивость к блокировке зеркала Debian (ТСПУ/провайдер иногда режут deb.debian.org):
# перебираем зеркала по очереди, первое рабочее выигрывает — сначала штатное из образа,
# затем RU-дружественные (yandex, ftp.ru.debian.org). Плохое зеркало просто пропускается.
RUN set -e; \
    pkgs="curl git iputils-ping postgresql-client"; \
    cp /etc/apt/sources.list /etc/apt/sources.list.orig 2>/dev/null || true; \
    ok=0; \
    for M in "KEEP" "http://mirror.yandex.ru/debian" "http://ftp.ru.debian.org/debian"; do \
        if [ "$M" = "KEEP" ]; then \
            [ -f /etc/apt/sources.list.orig ] && cp /etc/apt/sources.list.orig /etc/apt/sources.list; \
        else \
            rm -f /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
            printf 'deb %s bookworm main\ndeb %s bookworm-updates main\n' "$M" "$M" > /etc/apt/sources.list; \
        fi; \
        if apt-get update && apt-get install -y --no-install-recommends $pkgs; then ok=1; break; fi; \
        echo ">>> apt-зеркало недоступно, пробую следующее..."; \
    done; \
    [ "$ok" = "1" ] || { echo "ВСЕ apt-зеркала недоступны" >&2; exit 1; }; \
    rm -rf /var/lib/apt/lists/*

# Настройка Git
RUN git config --global --add safe.directory '*' && \
    git config --global credential.helper ""

COPY requirements.txt .
# Устойчивость к блокировке/недоступности индекса пакетов (даунтайм в проде недопустим).
# Перебираем источники по очереди, первый рабочий выигрывает: свой PIP_MIRROR (если задан)
# -> официальный PyPI (быстрый фейл при блоке Fastly) -> aliyun -> tuna (оба мимо Fastly,
# доступны из РФ). Если ВСЕ недоступны — сборка падает, но прод не трогается (см. deploy.sh).
# Свой первым: docker compose build --build-arg PIP_MIRROR=<url-до-simple/>
ARG PIP_MIRROR=
RUN ok=0; \
    for IDX in "$PIP_MIRROR" "DEFAULT" "https://mirrors.aliyun.com/pypi/simple/" "https://pypi.tuna.tsinghua.edu.cn/simple/"; do \
        [ -z "$IDX" ] && continue; \
        echo ">>> pip via ${IDX}"; \
        if [ "$IDX" = "DEFAULT" ]; then \
            pip install --no-cache-dir --timeout 20 --retries 1 -r requirements.txt && { ok=1; break; }; \
        else \
            pip install --no-cache-dir --timeout 60 --retries 3 --index-url "$IDX" -r requirements.txt && { ok=1; break; }; \
        fi; \
        echo ">>> источник недоступен, пробую следующий..."; \
    done; \
    [ "$ok" = "1" ] || { echo "ВСЕ источники pip недоступны" >&2; exit 1; }

COPY . .

CMD ["python", "bot.py"]
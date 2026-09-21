# Мост Xray на стороне Германии — отдельным контейнером.
#
# Почему отдельным, а не процессом внутри агента. Вся затея со вторым каналом в
# том, чтобы амнезия и Xray не делили судьбу. Живи мост внутри агента —
# перезапуск агента (выкладка, сбой, смена конфига туннеля) ронял бы оба канала
# разом, и по железу они остались бы связаны, хотя по протоколу уже нет.
#
# Контейнеру не нужен доступ к докеру: конфиг ему кладут в общий том, а он сам
# замечает, что файл изменился, и перезапускает процесс. Поэтому здесь нет ни
# сокета докера, ни лишних прав.
FROM alpine:3.20

# Версия закреплена и обязана совпадать с той, что на мастере: концы одного
# канала должны говорить на одном диалекте. «Последняя» на каждой пересборке
# означала бы, что однажды они разойдутся молча.
ARG XRAY_VERSION=v26.3.27
RUN set -e; \
    apk add --no-cache ca-certificates curl unzip; \
    for M in "https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-64.zip" \
             "https://ghproxy.net/https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-64.zip"; do \
        if curl -fsSL --max-time 120 -o /tmp/xray.zip "$M"; then break; fi; \
        echo ">>> источник Xray недоступен, пробую следующий..."; \
    done; \
    unzip -o -q /tmp/xray.zip -d /usr/local/bin/ xray geoip.dat geosite.dat; \
    chmod +x /usr/local/bin/xray; \
    rm -f /tmp/xray.zip; \
    apk del unzip; \
    /usr/local/bin/xray version | head -1

COPY run_xray.sh /run_xray.sh
RUN chmod +x /run_xray.sh

# Здесь лежит конфиг от мастера и сюда же пишется состояние. Том общий с
# агентом: он кладёт конфиг, мы его подхватываем.
VOLUME ["/etc/xray"]

ENTRYPOINT ["/run_xray.sh"]

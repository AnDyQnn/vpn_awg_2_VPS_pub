ARG REL
FROM ubuntu:${REL}
ENV container=docker DEBIAN_FRONTEND=noninteractive
# Как «минимальный» образ VPS у хостера: systemd, сеть, git — и ничего лишнего
# (без sshd, без docker, без ufw).
RUN apt-get update && apt-get install -y --no-install-recommends \
      systemd systemd-sysv dbus iproute2 iputils-ping ca-certificates curl git kmod \
      procps less nano cron needrestart unattended-upgrades \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/systemd/system/*.wants/* 2>/dev/null; \
    systemctl mask getty.target systemd-logind.service console-getty.service 2>/dev/null; true
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]

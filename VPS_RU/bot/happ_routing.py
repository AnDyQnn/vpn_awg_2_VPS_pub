# -*- coding: utf-8 -*-
"""Сплит для Xray: тот же список исключений, что и у AmneziaWG.

У AmneziaWG сплит живёт внутри ключа: в `AllowedIPs` перечислено всё, что идёт
мимо туннеля, и человек получает готовый конфиг. У Xray в ссылке `vless://`
маршрутизации нет вовсе — она задаётся отдельным профилем на стороне клиента.
Поэтому люди на Xray оставались без сплита, хотя список исключений в проекте
один и тот же.

Профиль собирается из той же таблицы `bypass_exclusions`. Причём полнее, чем у
AmneziaWG: тому можно отдать только адреса, а здесь домен остаётся доменом.
Разница не косметическая — Amnezia один раз резолвит имя и прибивает результат
гвоздём, а правило по домену срабатывает в момент подключения и переживает и
смену адреса, и CDN.

Доставка — подпиской. Имя профиля постоянное, а профиль с тем же именем при
получении перезаписывается: добавили адрес в исключения — он доехал до всех сам,
без перевыпуска и без действий человека.
"""
import base64
import json

from database import db

# Имя постоянное: по нему приложение и понимает, что это тот же профиль, и
# обновляет его, а не плодит копии. Менять нельзя — сменится имя, и у людей
# останется висеть старый профиль рядом с новым.
PROFILE_NAME = "Сплит от бота"

# Приватные диапазоны и служебное. В списке исключений их нет и быть не должно:
# там ресурсы, которые должны видеть российский адрес, а это — домашняя сеть,
# link-local, multicast и широковещательный. Через туннель им ходить незачем
# никогда, иначе человек теряет собственный роутер и принтер.
ALWAYS_DIRECT = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "224.0.0.0/4",
    # С маской, а не голым адресом: списки схлопываются через разбор сетей, и
    # после него запись всё равно станет такой. Пусть она с самого начала
    # совпадает с тем, что уедет человеку.
    "255.255.255.255/32",
]


def _is_net(value):
    """Сеть это или имя. Различаем по первому знаку: адреса начинаются с
    цифры, домены — нет. Точнее здесь и не нужно, а ошибиться дорого:
    имя, записанное в сети, просто не сработает."""
    value = (value or "").strip()
    return bool(value) and (value[0].isdigit() or ":" in value)


def _collapse(nets):
    """Схлопывает сети в минимальный набор.

    Список исключений набирается по одному домену за раз, и в нём копятся
    соседние и вложенные подсети: /24 внутри /16, две половинки одной /23.
    На поведение это не влияет, а профиль раздувает — а он должен помещаться
    в QR, который человек сканирует телефоном.

    Что не разобралось, оставляем как есть: лучше лишняя строка, чем молча
    выброшенное правило.
    """
    import ipaddress
    parsed, kept = [], []
    for item in nets:
        try:
            parsed.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            kept.append(item)
    try:
        merged = [str(n) for n in ipaddress.collapse_addresses(parsed)]
    except (TypeError, ValueError):
        merged = [str(n) for n in parsed]
    return merged + kept


async def profile(uuid_val=None):
    """Профиль маршрутизации для приложения.

    `DirectSites` — домены, `DirectIp` — сети: и то и другое идёт напрямую,
    мимо туннеля. Всё остальное — через него.

    `uuid_val` добавляет личные записи этого ключа. Ключ здесь и есть
    устройство, так что «на телефоне одно, на компе другое» получается само,
    без второго профиля: приложение всё равно держит активным только один.
    """
    try:
        rows = await db.get_bypass_exclusions()
    except Exception:
        rows = []
    domains = []
    for row in rows:
        name = (row["domain"] or "").strip().lower()
        # В таблице попадаются записи, заведённые по адресу, а не по имени, —
        # такие пойдут сетями, доменом их записывать нельзя.
        if name and not name[0].isdigit():
            domains.append(name)

    try:
        cidrs = await db.get_all_bypass_cidrs()
    except Exception:
        cidrs = []

    # Заведённые сети держим отдельно от домашних. Схлопывать их вместе нельзя:
    # почти всё, что добавляют вручную, лежит внутри 10.0.0.0/8, и при слиянии
    # запись просто исчезает из профиля. Работать она продолжит — 10/8 и так
    # идёт мимо туннеля, — но владелец, открыв профиль, своей записи не найдёт
    # и решит, что её не сохранили.
    listed = []
    for cidr in cidrs:
        if cidr not in listed:
            listed.append(cidr)

    # Личные записи ключа — поверх общего списка.
    proxy_sites, proxy_ip = [], []
    if uuid_val:
        try:
            rows = await db.list_peer_routes(uuid_val)
        except Exception:
            rows = []
        for row in rows:
            value = (row["value"] or "").strip()
            if not value:
                continue
            if row["direction"] == "proxy":
                (proxy_ip if _is_net(value) else proxy_sites).append(value)
            elif _is_net(value):
                if value not in listed:
                    listed.append(value)
            else:
                domains.append(value.lower())

    prof = {
        "Name": PROFILE_NAME,
        "GlobalProxy": "true",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSIP": "1.1.1.1",
        "DomesticDNSType": "DoH",
        "DomesticDNSDomain": "https://dns.google/dns-query",
        "DomesticDNSIP": "8.8.8.8",
        "DnsHosts": {"cloudflare-dns.com": "1.1.1.1", "dns.google": "8.8.8.8"},
        "DirectSites": sorted(set(domains)),
        "DirectIp": list(ALWAYS_DIRECT) + _collapse(listed),
        # Имя, не совпавшее ни с одним правилом по имени, проверяется ещё и по
        # адресу: иначе домен из исключений, к которому обратились по адресу,
        # ушёл бы в туннель.
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }
    # Пустые списки не кладём вовсе: профиль читает человек, и лишние поля в
    # нём только мешают понять, что вообще настроено.
    if proxy_sites:
        prof["ProxySites"] = sorted(set(proxy_sites))
    if proxy_ip:
        prof["ProxyIp"] = proxy_ip
    return prof


async def link(activate=True, uuid_val=None):
    """Ссылка, по которой приложение забирает профиль.

    `onadd` — добавить и сразу включить: профиль, который надо ещё найти и
    включить руками, до человека не доедет. `add` оставлен для показа владельцу.
    """
    raw = json.dumps(await profile(uuid_val), ensure_ascii=False,
                     separators=(",", ":"))
    payload = base64.b64encode(raw.encode()).decode()
    return "happ://routing/%s/%s" % ("onadd" if activate else "add", payload)


async def summary(uuid_val=None):
    """Короткая сводка для экранов: сколько чего мимо туннеля."""
    prof = await profile(uuid_val)
    return {
        "domains": len(prof["DirectSites"]),
        "nets": len(prof["DirectIp"]) - len(ALWAYS_DIRECT),
        "always": len(ALWAYS_DIRECT),
    }

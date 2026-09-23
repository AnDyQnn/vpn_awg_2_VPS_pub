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

# DNS для того, что идёт через туннель: обычный публичный DoH, запрос к нему
# уходит через прокси. Не внутренний адрес туннеля `10.13.13.1`: человек на Xray
# внутри туннеля не сидит. Узел пропускает такие запросы от адресов-двойников —
# см. doh_block_apply в ru_wg_api/api.py.
REMOTE_DNS_URL = "https://cloudflare-dns.com/dns-query"
REMOTE_DNS_IP = "1.1.1.1"


def _is_net(value):
    """Адрес это или имя.

    Различаем по первому знаку: адреса начинаются с цифры, IPv6 содержит
    двоеточие, домены — ни то ни другое."""
    value = (value or "").strip()
    return bool(value) and (value[0].isdigit() or ":" in value)


async def _stamp(prof, uuid_val):
    """Отметка времени профиля. Меняется ТОЛЬКО когда меняется содержимое.

    Без неё приложение профиль не обновляет вовсе. Из документации: профиль с
    тем же именем обновляется, если пришедшая в `LastUpdated` дата НОВЕЕ
    сохранённой. Нет даты — нет обновления, и человек живёт со снимком, снятым
    в день первой выдачи. Владелец пять раз подряд обновил подписку, каждый раз
    получил «3 servers imported/updated» — и все пять раз профиль остался
    прежним, часовой давности, с правилом, которое ломало ему интернет.

    Почему не просто «сейчас». Та же документация: увидев дату новее,
    приложение ПРИНУДИТЕЛЬНО перекачивает гео-файлы, а это двадцать шесть
    мегабайт. Подписка обновляется раз в два часа у каждого — и мы бы устроили
    людям постоянную закачку на ровном месте.

    Поэтому дата привязана к содержимому: считаем отпечаток профиля и двигаем
    время вперёд, только когда отпечаток изменился. Ничего не менялось — дата
    прежняя, приложение спокойно проходит мимо.
    """
    import hashlib
    import json as _json
    import time as _time

    body = _json.dumps({k: v for k, v in prof.items() if k != "LastUpdated"},
                       ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(body.encode()).hexdigest()
    key = "happ_profile_" + (uuid_val or "all")
    now = int(_time.time())
    try:
        saved = (await db.get_setting(key)) or ""
        was, _, when = saved.partition(" ")
        if was == digest and when.isdigit():
            return int(when)
        # Строго больше прежней, иначе обновление не признают новым. Две правки
        # в одну секунду — обычное дело: владелец добавляет исключения подряд.
        if when.isdigit() and now <= int(when):
            now = int(when) + 1
        await db.set_setting(key, "%s %d" % (digest, now))
    except Exception as e:
        # База недоступна — отдаём профиль с текущим временем. Лишняя закачка
        # гео-файлов неприятна, но профиль без даты не доедет вовсе.
        print("Профиль маршрутизации: отметка времени не сохранилась: %s" % e)
    return now


# Резолвер по умолчанию для трафика мимо туннеля. Яндекс, потому что он быстрее
# отвечает из России, а сюда идёт именно то, что решили не заворачивать.
DIRECT_DNS_DEFAULT = "77.88.8.8"


async def _direct_dns(uuid_val):
    """Какой резолвер человек выбрал при выдаче ключа.

    Читаем из его же конфига, а не спрашиваем заново: там это и записано, и
    другого источника правды нет. Нет конфига (человек только на Xray) — берём
    обычный.
    """
    if not uuid_val:
        return DIRECT_DNS_DEFAULT
    try:
        from acl import peer_ip_map
        from dnsnames import client_upstreams
        ip = (await peer_ip_map()).get(uuid_val)
        if not ip:
            return DIRECT_DNS_DEFAULT
        chosen = (await client_upstreams()).get(ip)
        return chosen or DIRECT_DNS_DEFAULT
    except Exception:
        # Это удобство, а не рубеж: не вышло — профиль всё равно должен
        # собраться, иначе человек останется вообще без настроек.
        return DIRECT_DNS_DEFAULT


async def profile(uuid_val=None):
    """Профиль маршрутизации для приложения: ТОЛЬКО сайты.

    Правило владельца: в профиле Xray — только сайты с вкладки сплит-туннеля в
    боте, те же, что у AmneziaWG. Никаких адресов: ни сетей, ни внутренних
    адресов туннеля, ни домашних сетей, ни адреса узла. Нужные адреса владелец
    заводит сам.

    Раньше сюда подкладывалось много своего, и всё — адресами. Подсети, которые
    бот сам выводил из доменов обхода. Вся `10.0.0.0/8` без нашей `/24` — то
    есть адреса вокруг самого VPN шли напрямую. Адрес узла. `0.0.0.0/0` в
    туннельные. И DNS на внутренний `10.13.13.1`, который существует только
    внутри нашего туннеля, — а человек на Xray внутри туннеля не сидит. Логика
    AmneziaWG, перенесённая туда, где она не на месте.

    `uuid_val` добавляет личные записи этого ключа — то, что владелец вписал
    сам на экране «личные маршруты». Адреса попадают в профиль только отсюда.
    """
    try:
        rows = await db.get_bypass_exclusions()
    except Exception:
        rows = []
    domains = []
    for row in rows:
        name = (row["domain"] or "").strip().lower()
        # Запись, заведённая адресом, а не именем, — не сайт. В профиль не идёт.
        if name and not _is_net(name):
            domains.append(name)

    # Личные записи ключа — то, что владелец вписал сам на экране «личные
    # маршруты». Это и есть «нужные адреса настрою сам»: адреса отсюда идут в
    # профиль как есть, ровно те, что вписаны. Из общего списка адреса не идут.
    proxy_sites, direct_ip, proxy_ip = [], [], []
    if uuid_val:
        try:
            rows = await db.list_peer_routes(uuid_val)
        except Exception:
            rows = []
        for row in rows:
            value = (row["value"] or "").strip().lower()
            if not value:
                continue
            to_proxy = row["direction"] == "proxy"
            if _is_net(value):
                (proxy_ip if to_proxy else direct_ip).append(value)
            else:
                (proxy_sites if to_proxy else domains).append(value)

    prof = {
        "Name": PROFILE_NAME,
        # Всё, что не сайт из списка обхода, — через туннель.
        "GlobalProxy": "true",
        # DNS того, что идёт через туннель: обычный публичный резолвер, запрос
        # к нему уходит через прокси. Не внутренний адрес туннеля — телефон на
        # Xray внутри туннеля не сидит.
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": REMOTE_DNS_URL,
        "RemoteDNSIP": REMOTE_DNS_IP,
        # Адрес DoH-резолвера без отдельного запроса DNS — как в примерах
        # документации приложения. Это не правило маршрутизации, а стартовый
        # адрес самого резолвера.
        "DnsHosts": {"cloudflare-dns.com": REMOTE_DNS_IP},
        # DNS для сайтов из списка обхода: они идут напрямую, и резолвер нужен
        # такой, до которого телефон достаёт без туннеля. Выбор самого человека,
        # тот же, что при выдаче ключа AmneziaWG.
        "DomesticDNSType": "DoU",
        "DomesticDNSDomain": "",
        "DomesticDNSIP": await _direct_dns(uuid_val),
        "DirectSites": sorted(set(domains)),
        # Правил по адресам нет — значит и разрешать имя заранее, чтобы
        # сверить его с адресами, незачем. Имя идёт как есть.
        "DomainStrategy": "AsIs",
        "FakeDNS": "false",
    }

    # Гео-файлы. Нашим правилам они не нужны, но приложение без них считает
    # профиль испорченным целиком. По умолчанию оно тянет их с GitHub, который
    # из России не открывается, поэтому раздаём со своего узла.
    try:
        import xray
        base = await xray.subscription_base()
    except Exception:
        base = ""
    if base:
        prof["Geositeurl"] = f"{base}/geo/geosite.dat"
        prof["Geoipurl"] = f"{base}/geo/geoip.dat"
    # Все списки — ЯВНО, даже пустые. Документация приложения: недостающие поля
    # оно дополняет из своего профиля по умолчанию, а в том в DirectIp стоят
    # 10.0.0.0/8, 192.168.0.0/16 и прочие частные сети. Не пришлём пустой
    # список — получим их обратно, хотя в профиле их быть не должно. Форма та
    # же, что в примере из документации: все шесть списков на месте.
    prof["ProxySites"] = sorted(set(proxy_sites))
    prof["DirectIp"] = list(dict.fromkeys(direct_ip))
    prof["ProxyIp"] = list(dict.fromkeys(proxy_ip))
    prof["BlockSites"] = []
    prof["BlockIp"] = []
    # Дата — последней: она считается по всему остальному.
    prof["LastUpdated"] = await _stamp(prof, uuid_val)
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
        # Адресов в профиле больше нет — только сайты.
        "nets": 0,
        "always": 0,
    }

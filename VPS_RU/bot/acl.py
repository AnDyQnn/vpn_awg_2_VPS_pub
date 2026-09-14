# -*- coding: utf-8 -*-
"""Доступы внутри туннеля: перевод ролей в правила узла.

Роль — это ответ на вопрос «к каким домашним сервисам человек ходит». К интернету
и к скорости она отношения не имеет: «мировой» трафик уходит в клиент-сервер и
цепочкой доступов не затрагивается.

Модель намеренно простая:
  • ролей у человека может быть сколько угодно, права СКЛАДЫВАЮТСЯ;
  • нет ни одной роли — значит без ограничений, как было до всего этого;
  • запрета, который бьёт разрешение, нет: роль умеет только открывать. Иначе
    пришлось бы объяснять, почему из двух ролей одна отменяет другую, — а это
    первый шаг к правам, в которых никто не разберётся.

Считает объединение бот, потому что база есть только у него; узел получает готовый
список «кому куда можно» и раскладывает его в правила файрвола.
"""
from database import db
from utils import WG_API_URL, api_session


# Подсеть туннеля: всё, что вне её, адресом пира не является.
TUNNEL_PREFIX = "10.13.13."


async def peer_ip_map():
    """uuid → адрес пира в туннеле. Адрес живёт в конфиге WireGuard, не в базе,
    поэтому спрашиваем узел. Пир без адреса (ещё не создан) просто пропускается."""
    mapping = {}
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=5) as resp:
                if resp.status != 200:
                    return mapping
                for p in await resp.json():
                    ip = (p.get("allowed_ips") or "").split("/")[0].strip()
                    # Адрес пира — только то, что внутри туннеля. У выходного
                    # узла здесь маршрут по умолчанию, и «0.0.0.0/0» давало
                    # адрес «0.0.0.0»: он попадал в списки и превращался в
                    # правило, которое не открывает ничего.
                    if p.get("uuid") and ip.startswith(TUNNEL_PREFIX):
                        mapping[p["uuid"]] = ip
    except Exception as e:
        print(f"ACL: не удалось получить адреса пиров: {e}")
    return mapping


async def peer_addr_map():
    """uuid → ВСЕ адреса человека в туннеле.

    Их может быть два: адрес пира AmneziaWG и адрес-двойник, с которого ходит
    Xray. Правила пишутся на адрес, поэтому человеку, у которого есть оба
    подключения, нужны оба — иначе запрет перестанет действовать сразу после
    переключения протокола."""
    ips = await peer_ip_map()
    try:
        from database import db
        from xray import twin_addr
        with_xray = {r["user_uuid"] for r in await db.list_xray_users()}
    except Exception:
        with_xray = set()

    out = {}
    for uuid_val, ip in ips.items():
        addrs = [ip]
        if uuid_val in with_xray:
            twin = twin_addr(ip)
            if twin:
                addrs.append(twin)
        out[uuid_val] = addrs
    return out


def _dedupe(grants):
    """Две роли легко дают одно и то же правило — в файрвол оно нужно один раз."""
    seen, out = set(), []
    for g in grants:
        key = (g["cidr"], (g.get("proto") or "any"), g.get("port"))
        if key not in seen:
            seen.add(key)
            out.append({"cidr": g["cidr"], "proto": g.get("proto") or "any",
                        "port": g.get("port")})
    return out


async def resolve_grants(grants):
    """Превращает имена в адреса. Возвращает (правила, непонятые имена).

    Имя разрешается здесь, а не при добавлении правила: между «открыть доступ
    к дом.vpn» и раскладкой адрес мог смениться, и правило обязано означать
    по-прежнему домашний сервер, а не бывший его адрес.

    Имя без адреса пропускается: открыть «неизвестно что» опаснее, чем не
    открыть ничего."""
    from dnsnames import resolve_all

    table = None
    people = None
    out, unresolved = [], []
    for grant in grants:
        # Цель-человек: его сегодняшний адрес спрашиваем у узла прямо сейчас.
        # Записанные цифры устаревают при первом же перевыпуске ключа, а
        # человек — нет.
        if grant.get("target_uuid"):
            if people is None:
                people = await peer_ip_map()
            ip = people.get(grant["target_uuid"])
            if not ip:
                unresolved.append(f"человек {grant['target_uuid'][:8]}")
                continue
            out.append({**grant, "cidr": f"{ip}/32"})
            continue
        if not grant.get("name"):
            out.append(grant)
            continue
        if table is None:
            table, _ = await resolve_all()
        ip = table.get(grant["name"])
        if not ip:
            unresolved.append(grant["name"])
            continue
        # /32: имя всегда указывает на одну машину, а не на сеть.
        out.append({**grant, "cidr": f"{ip}/32"})
    return out, unresolved


async def build_payload():
    """Список пиров с ограничениями. Кого здесь нет — тот ходит куда угодно."""
    matrix = await db.get_access_matrix()
    ips = await peer_addr_map()
    peers, skipped = [], []
    for uuid, rec in matrix.items():
        allow, unresolved = await resolve_grants(rec["allow"])
        skipped += unresolved
        allow = _dedupe(allow)
        for ip in ips.get(uuid, []):
            peers.append({"ip": ip, "allow": allow})
    return peers, sorted(set(skipped))


async def apply_access_rules(reason: str = ""):
    """Применяет текущее состояние базы на узле. Вызывается после любого изменения
    ролей и при старте бота — узел чистит таблицы при перезапуске контейнера.

    Возвращает (успех, текст) — текст годится и для лога, и для показа админу."""
    try:
        peers, unresolved = await build_payload()
    except Exception as e:
        return False, f"не удалось собрать правила: {e}"

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/acl", json={"peers": peers},
                                    timeout=10) as resp:
                if resp.status != 200:
                    return False, f"узел отклонил правила: {await resp.text()}"
                data = await resp.json()
    except Exception as e:
        return False, f"узел недоступен: {e}"

    msg = (f"Доступы применены: под ограничением {data.get('peers', 0)} чел., "
           f"правил {data.get('rules', 0)}")
    if unresolved:
        # Молчать нельзя: человек считает доступ открытым, а правила нет.
        msg += f" · не разрешились имена: {', '.join(unresolved)}"
    if reason:
        msg += f" ({reason})"
    try:
        await db.log_event("Roles", msg)
    except Exception:
        pass
    return True, msg


def grant_text(grant) -> str:
    """Человеческая запись правила: «дом.vpn», «10.13.13.7 · tcp 443».

    Имя показываем как есть, а не разрешённый адрес: правило написано про имя,
    и подстановка цифр только запутала бы — завтра они будут другие."""
    # У правила-на-человека имени туннеля нет — там подпись с его именем.
    if grant.get("target_uuid"):
        target = grant.get("note") or "человек"
    else:
        target = grant.get("name") or grant.get("cidr") or "?"
    proto = (grant.get("proto") or "any").lower()
    port = grant.get("port")
    if proto in ("tcp", "udp"):
        return f"{target} · {proto}{' ' + str(port) if port else ''}"
    return str(target)

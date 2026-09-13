# -*- coding: utf-8 -*-
"""Xray как второй протокол: сборка конфига и управление им.

Главное решение, на котором всё держится: каждому человеку в конфиге выдаётся
свой исходящий канал с ЕГО туннельным адресом (`sendThrough`). Поэтому наружу
трафик уходит с того же `10.13.13.x`, что и по AmneziaWG, и всё построенное
вокруг адресов — счётчики пакетов, лимиты, роли, фильтры, графики — продолжает
узнавать человека, не зная и не интересуясь протоколом.

Без этого пришлось бы писать заново половину системы: Xray сам по себе отдаёт
только байты по пользователю и отправляет всех с адреса сервера.

Конфиг собирается ЦЕЛИКОМ здесь, у бота, потому что база есть только у него.
Узел его просто записывает и запускает — он намеренно не знает, как конфиг
устроен, иначе его пришлось бы переучивать при каждом изменении модели.
"""
import base64
import json
import secrets
import uuid as uuid_lib

from database import db
from utils import WG_API_URL, api_session

# Порт входа. 443 выбран не для красоты: трафик к нему неотличим от обычного
# HTTPS, а блокировка этого порта ломает провайдеру половину интернета.
DEFAULT_PORT = 443
# Чужой сайт, под который маскируется рукопожатие. Должен быть крупным,
# доступным из России и поддерживать TLS 1.3.
DEFAULT_DEST = "www.microsoft.com"


async def settings():
    """Настройки входа. Ключи Reality генерятся один раз и живут в базе:
    сменить их — значит отключить всех, кто уже подключён."""
    return {
        "port": int(await db.get_setting("xray_port") or DEFAULT_PORT),
        "dest": await db.get_setting("xray_dest") or DEFAULT_DEST,
        "private_key": await db.get_setting("xray_private_key") or "",
        "public_key": await db.get_setting("xray_public_key") or "",
        "short_id": await db.get_setting("xray_short_id") or "",
    }


async def ensure_keys():
    """Просит узел сгенерировать пару ключей, если её ещё нет.

    Генерирует именно Xray на узле, а не мы: формат ключей — его внутреннее
    дело, и повторять его реализацию у себя значит однажды разойтись с ней."""
    cur = await settings()
    if cur["private_key"] and cur["public_key"] and cur["short_id"]:
        return cur

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/xray/keys", timeout=15) as r:
                if r.status != 200:
                    return None
                keys = await r.json()
    except Exception as e:
        print(f"Xray: не удалось получить ключи: {e}")
        return None

    private = keys.get("privatekey") or keys.get("private_key")
    public = keys.get("password") or keys.get("publickey") or keys.get("public_key")
    if not private or not public:
        print(f"Xray: узел вернул неожиданный формат ключей: {list(keys)}")
        return None

    await db.set_setting("xray_private_key", private)
    await db.set_setting("xray_public_key", public)
    # Короткий идентификатор — часть маскировки, произвольные шестнадцатеричные
    # символы чётной длины.
    await db.set_setting("xray_short_id", secrets.token_hex(4))
    return await settings()


async def peer_ip_map():
    """uuid человека → его адрес в туннеле. Адрес живёт в конфиге WireGuard,
    поэтому спрашиваем узел."""
    from acl import peer_ip_map as _map
    return await _map()


async def build_config():
    """Собирает конфиг целиком: вход, по каналу на человека, правила.

    Человек без адреса в туннеле пропускается: без адреса `sendThrough`
    невозможен, а значит он выпал бы из всего учёта. Лучше не выдать доступ,
    чем выдать невидимый для системы."""
    cfg = await ensure_keys()
    if not cfg:
        return None, "нет ключей Reality"

    people = await db.list_xray_users()
    ips = await peer_ip_map()

    clients, outbounds, rules = [], [], []
    skipped = []
    for person in people:
        # Приостановленный человек в конфиг не попадает вовсе — отключает
        # сервер, а не ссылка: иначе он работал бы на старом профиле до
        # следующего обновления подписки.
        if not person["is_active"]:
            continue
        ip = ips.get(person["user_uuid"])
        if not ip:
            skipped.append(person["name"])
            continue

        tag = f"out-{person['user_uuid'][:8]}"
        clients.append({
            "id": person["xray_uuid"],
            "email": person["user_uuid"],      # имя учётной записи = наш uuid
            "flow": "xtls-rprx-vision",
        })
        outbounds.append({
            "protocol": "freedom",
            "tag": tag,
            # Вот он, ключевой параметр: трафик этого человека уходит с его
            # собственного туннельного адреса.
            "sendThrough": ip,
        })
        rules.append({
            "type": "field",
            "user": [person["user_uuid"]],
            "outboundTag": tag,
        })

    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "tag": "in-vless",
            "listen": "0.0.0.0",
            "port": cfg["port"],
            "protocol": "vless",
            "settings": {"clients": clients, "decryption": "none"},
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": f"{cfg['dest']}:443",
                    "serverNames": [cfg["dest"]],
                    "privateKey": cfg["private_key"],
                    "shortIds": [cfg["short_id"]],
                },
            },
        }],
        # Запасной канал нужен всегда: если человек почему-то не совпал ни с
        # одним правилом, он должен просто выйти в интернет, а не упереться в
        # тишину.
        "outbounds": outbounds + [{"protocol": "freedom", "tag": "direct"}],
        "routing": {"domainStrategy": "AsIs", "rules": rules},
    }
    return config, (f"пропущены без адреса: {', '.join(skipped)}" if skipped else "")


async def apply_config(reason=""):
    """Отдаёт собранный конфиг узлу. Узел применяет его с откатом: если новый
    конфиг не поднимется, вернётся прежний."""
    config, note = await build_config()
    if not config:
        return False, note or "конфиг не собрался"

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/xray/config",
                                    json={"config": config}, timeout=30) as r:
                data = await r.json() if r.status == 200 else await r.text()
                if r.status != 200:
                    return False, f"узел отклонил конфиг: {data}"
    except Exception as e:
        return False, f"узел недоступен: {e}"

    people = len(config["inbounds"][0]["settings"]["clients"])
    msg = f"Xray обновлён: людей {people}"
    if note:
        msg += f" ({note})"
    if reason:
        msg += f" · {reason}"
    try:
        await db.log_event("Xray", msg)
    except Exception:
        pass
    return True, msg


async def status():
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/xray/status", timeout=10) as r:
                if r.status == 200:
                    return await r.json()
    except Exception as e:
        return {"error": str(e)}
    return {"error": "узел не ответил"}


async def switch(name: str, enabled: bool):
    """Включение и выключение протокола. Выключить оба узел не даст."""
    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/protocols",
                                    json={"name": name, "enabled": enabled},
                                    timeout=30) as r:
                data = await r.json() if r.status == 200 else await r.text()
                if r.status != 200:
                    return False, str(data)
    except Exception as e:
        return False, str(e)
    await db.log_event("Xray", f"Протокол {name}: "
                               f"{'включён' if enabled else 'выключен'}")
    return True, data.get("note", "готово")


async def issue(user_uuid):
    """Заводит человеку подключение по Xray и возвращает его ссылку.

    Повторный вызов перевыпускает: старый идентификатор и старая ссылка
    перестают работать. Это и есть «ссылка утекла, отзови»."""
    token = secrets.token_urlsafe(24)
    await db.add_xray_user(user_uuid, str(uuid_lib.uuid4()), token)
    ok, msg = await apply_config("выдано подключение")
    return ok, (token if ok else msg)


async def profile_link(user_uuid) -> str:
    """Сама строка подключения — то, что человек вставляет в приложение."""
    rec = await db.get_xray_user(user_uuid)
    if not rec:
        return ""
    cfg = await settings()
    user = await db.get_user_by_uuid(user_uuid)
    host = await db.get_setting("server_host") or ""
    if not host or not cfg["public_key"]:
        return ""
    name = (user or {}).get("name", "vpn")
    return (f"vless://{rec['xray_uuid']}@{host}:{cfg['port']}"
            f"?type=tcp&security=reality&sni={cfg['dest']}"
            f"&fp=chrome&pbk={cfg['public_key']}&sid={cfg['short_id']}"
            f"&flow=xtls-rprx-vision#{name}")


async def subscription_url(token: str) -> str:
    """Адрес личной подписки — то, что человек вставляет в приложение один раз
    и больше не трогает.

    Пусто, если владелец не указал, по какому адресу сервер подписок доступен
    снаружи. Гадать нельзя: подписка по неверному адресу выглядит как рабочая,
    а на деле молча перестаёт обновляться."""
    base = (await db.get_setting("xray_sub_base") or "").strip().rstrip("/")
    if not base or not token:
        return ""
    return f"{base}/sub/{token}"


async def subscription_body(token: str) -> str:
    """Тело подписки: список профилей в base64 — формат, который понимают
    все клиенты этого семейства.

    Пусто отдаём намеренно: если человек приостановлен или ссылка отозвана,
    клиент при следующем обновлении получит пустой список и профиль исчезнет."""
    rec = await db.get_xray_by_token(token)
    if not rec or not rec["is_active"]:
        return ""
    link = await profile_link(rec["user_uuid"])
    if not link:
        return ""
    await db.mark_xray_seen(rec["user_uuid"])
    return base64.b64encode(link.encode()).decode()

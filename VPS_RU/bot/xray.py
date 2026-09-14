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
import os
from utils import CONFIGS_DIR, WG_API_URL, api_session

# Порт входа. 443 выбран не для красоты: трафик к нему неотличим от обычного
# HTTPS, а блокировка этого порта ломает провайдеру половину интернета.
DEFAULT_PORT = 443
# Чужой сайт, под который маскируется рукопожатие. Должен быть крупным,
# доступным из России и поддерживать TLS 1.3.
# Домен, которым прикидывается вход.
#
# Узел стоит в России — значит и маска должна быть своя: домашний хостинг,
# отдающий www.microsoft.com, выглядит страннее, чем отдающий объявления.
# Замерено с самого узла: avito 86 мс против microsoft 261. Отклик видит не
# клиент, а проверяющий, которого туда переадресуют, — медленный ответ сам по
# себе примета.
#
# Меняется из бота, экран «Маска входа», там же замеры по остальным.
DEFAULT_DEST = "avito.ru"


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

    # Имена полей у генератора меняются от версии к версии: было «Private key»
    # и «Public key», в 26.3 стало «PrivateKey» и «Password (PublicKey)».
    # Поэтому ищем по смыслу, а не по точному совпадению — иначе следующее
    # переименование снова оставит человека без ключа.
    def _find(*hints):
        for name, value in keys.items():
            plain = name.replace("_", "").replace("(", "").replace(")", "")
            if all(h in plain for h in hints):
                return value
        return None

    private = _find("private")
    public = _find("public") or keys.get("password")
    if not private or not public:
        print(f"Xray: узел вернул неожиданный формат ключей: {list(keys)}")
        return None

    await db.set_setting("xray_private_key", private)
    await db.set_setting("xray_public_key", public)
    # Короткий идентификатор — часть маскировки, произвольные шестнадцатеричные
    # символы чётной длины.
    await db.set_setting("xray_short_id", secrets.token_hex(4))
    return await settings()


# Смещение адреса-двойника. Человек на Xray отправляет трафик не со своего
# туннельного адреса, а с его отражения во второй половине сети:
# 10.13.13.6 → 10.13.13.134.
#
# Почему не тот же адрес, как задумывалось сначала: отправлять можно только с
# адреса, который принадлежит самому узлу. Адрес пира лежит ЗА туннелем — ответы
# на него ушли бы в туннель, к выключенному клиенту, а не в Xray. Проверено на
# стенде: с чужого адреса не уходит ни один запрос.
#
# Двойник решает это, ничего не ломая: он из той же туннельной сети, поэтому
# правила, написанные на сеть целиком — учёт, роли, фильтры, маршрут в Германию —
# накрывают его сами. А номер сохраняется, и человека видно по адресу как раньше.
XRAY_ADDR_OFFSET = 128


def twin_addr(peer_ip: str):
    """Адрес-двойник для Xray. Пусто, если адрес не из нижней половины сети."""
    try:
        parts = [int(x) for x in peer_ip.split(".")]
        if len(parts) != 4 or not 1 <= parts[3] < XRAY_ADDR_OFFSET:
            return ""
        parts[3] += XRAY_ADDR_OFFSET
        return ".".join(str(x) for x in parts)
    except Exception:
        return ""


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
    addresses, skipped = [], []
    for person in people:
        # Приостановленный человек в конфиг не попадает вовсе — отключает
        # сервер, а не ссылка: иначе он работал бы на старом профиле до
        # следующего обновления подписки.
        if not person["is_active"]:
            continue
        twin = twin_addr(ips.get(person["user_uuid"]) or "")
        if not twin:
            skipped.append(person["name"])
            continue
        addresses.append(twin)

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
            # собственного адреса, а не с общего адреса сервера.
            "sendThrough": twin,
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
    return config, addresses, (f"пропущены без адреса: {', '.join(skipped)}"
                               if skipped else "")


async def apply_config(reason=""):
    """Отдаёт собранный конфиг узлу. Узел применяет его с откатом: если новый
    конфиг не поднимется, вернётся прежний."""
    config, addresses, note = await build_config()
    if not config:
        return False, note or "конфиг не собрался"

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/xray/config",
                                    json={"config": config,
                                          "addresses": addresses},
                                    timeout=30) as r:
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


async def sync_person(reason=""):
    """Пересобирает конфиг узла после изменения состояния человека.

    Вызывается после паузы, разморозки, продления и удаления — везде, где
    менялось право человека пользоваться VPN. Конфиг собирается целиком, так
    что кто именно изменился, знать не нужно; важно лишь, что изменение
    доезжает до узла сразу, а не к следующему обновлению подписки.

    Если протокол выключен, делать нечего: конфига на узле нет."""
    st = await status()
    if not st.get("xray", {}).get("enabled"):
        return False, "протокол выключен"
    return await apply_config(reason)


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


async def server_host() -> str:
    """Адрес, по которому до узла достучится человек снаружи.

    Сначала — настройка: владелец мог задать имя вместо адреса. Если её нет,
    берём из конфигов AmneziaWG: там в `Endpoint` стоит ровно тот адрес, по
    которому люди подключаются сейчас, то есть заведомо верный.

    У самого узла спрашивать бесполезно: наружу он ходит через Германию и
    ответит немецким адресом.
    """
    host = (await db.get_setting("server_host") or "").strip()
    if host:
        return host
    try:
        for name in os.listdir(CONFIGS_DIR):
            if not name.endswith(".conf"):
                continue
            with open(os.path.join(CONFIGS_DIR, name), encoding="utf-8") as f:
                for line in f:
                    if line.strip().lower().startswith("endpoint"):
                        found = line.split("=", 1)[1].strip().rsplit(":", 1)[0]
                        if found:
                            # Запоминаем: искать заново при каждой выдаче ключа
                            # незачем, а владелец сможет переопределить.
                            await db.set_setting("server_host", found)
                            return found
    except OSError:
        pass
    return ""


def link_keyboard(link, back=None):
    """Кнопка, открывающая ссылку в приложении, и выход рядом.

    Схему `vless://` Telegram в кнопке принимает — проверено его же API.
    Откроется ли приложение, зависит от того, зарегистрировало ли оно схему
    в системе; поэтому сама ссылка остаётся текстом и её можно скопировать,
    даже если нажатие ни к чему не приведёт.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    rows = [[InlineKeyboardButton("📲 Добавить в приложение", url=link)]]
    if back:
        rows.append([InlineKeyboardButton(back[0], callback_data=back[1])])
    return InlineKeyboardMarkup(rows)


async def profile_link(user_uuid) -> str:
    """Сама строка подключения — то, что человек вставляет в приложение."""
    rec = await db.get_xray_user(user_uuid)
    if not rec:
        return ""
    cfg = await settings()
    user = await db.get_user_by_uuid(user_uuid)
    host = await server_host()
    if not host or not cfg["public_key"]:
        return ""
    name = (user or {}).get("name", "vpn")
    return (f"vless://{rec['xray_uuid']}@{host}:{cfg['port']}"
            f"?type=tcp&security=reality&sni={cfg['dest']}"
            f"&fp=chrome&pbk={cfg['public_key']}&sid={cfg['short_id']}"
            f"&flow=xtls-rprx-vision#{name}")


# Адрес узла внутри туннеля. По нему живут и DNS, и страница отказа, и сервер
# подписок — всё внутреннее, до чего человек достаёт, только будучи подключённым.
TUNNEL_SELF = "10.13.13.1"
SUB_PORT_DEFAULT = 8080


async def subscription_base() -> str:
    """Откуда клиент забирает свой профиль.

    По умолчанию — адрес узла ВНУТРИ туннеля. Так подписка не выходит в
    интернет вовсе: запрос идёт по уже зашифрованному каналу, и ни домен, ни
    сертификат не нужны. Снаружи этот порт закрыт.

    Владелец может задать своё — например, настоящее имя с сертификатом, когда
    оно появится. Тогда профиль будет обновляться и при выключенном VPN.
    """
    base = (await db.get_setting("xray_sub_base") or "").strip().rstrip("/")
    if base:
        return base
    return f"http://{TUNNEL_SELF}:{SUB_PORT_DEFAULT}"


async def subscription_url(token: str) -> str:
    """Адрес личной подписки — то, что человек вставляет в приложение один раз
    и больше не трогает.

    По умолчанию ведёт на узел внутри туннеля — так подписка не выходит в
    интернет и не требует сертификата. Владелец может задать своё имя."""
    base = await subscription_base()
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


# --- КТО НА СВЯЗИ ---------------------------------------------------------
# У AmneziaWG есть рукопожатие, у Xray — нет. Зато есть счётчики по
# адресу-двойнику: если по нему только что шли пакеты, человек на связи.
# Это даже честнее рукопожатия — оно бывает и у телефона, лежащего в кармане.
ONLINE_WINDOW = 180


async def online_uuids():
    """Кто сейчас на связи по Xray."""
    import time as _time
    from utils import state_data

    seen = state_data.get("addr_seen", {})
    now = _time.time()
    out = set()
    for uuid_val, ip in (await peer_ip_map()).items():
        twin = twin_addr(ip)
        if twin and now - seen.get(twin, 0) < ONLINE_WINDOW:
            out.add(uuid_val)
    return out


async def person_state(uuid_val):
    """Сводка по подключениям одного человека — для карточки и экрана.

    Собирается из двух источников: пиры узла (AmneziaWG) и наша таблица (Xray).
    Ключевое поле — `first_seen_at`: переездом считается живое подключение, а
    не факт выдачи ссылки."""
    rec = await db.get_xray_user(uuid_val)
    state = {
        "has_xray": bool(rec),
        "xray_seen": rec["first_seen_at"] if rec else None,
        "xray_online": uuid_val in await online_uuids(),
        "sub_token": rec["sub_token"] if rec else "",
        "awg_ip": None,
        "awg_handshake": None,
    }
    try:
        import time as _time
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=5) as r:
                if r.status == 200:
                    for peer in await r.json():
                        if peer.get("uuid") != uuid_val:
                            continue
                        state["awg_ip"] = (peer.get("allowed_ips") or "").split("/")[0]
                        hs = peer.get("latest_handshake", 0)
                        if hs:
                            state["awg_handshake"] = int(_time.time()) - hs
    except Exception:
        pass
    return state


# --- ПРИЛОЖЕНИЕ -----------------------------------------------------------
# Клиент один на все платформы — Happ. Человеку, которому выдают VPN, выбор не
# нужен, ему нужно, чтобы заработало; одинаковая инструкция для всех дешевле
# любого списка альтернатив.
#
# Ссылки официальные, из репозитория проекта. Для iPhone их две: в российском
# магазине лежит отдельное издание, и по ссылке на глобальное оно не ставится.
APPS = {
    "iPhone / iPad": [
        ("App Store",
         "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215"),
        ("App Store · российский аккаунт",
         "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"),
    ],
    "Android": [
        ("Google Play",
         "https://play.google.com/store/apps/details?id=com.happproxy"),
        ("Файлом, если Play недоступен",
         "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk"),
    ],
    "Windows": [
        ("Установщик",
         "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe"),
    ],
    "macOS": [
        ("Образ",
         "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.macOS.universal.dmg"),
    ],
    "Linux": [
        ("deb",
         "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.linux.x64.deb"),
        ("rpm",
         "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.linux.x64.rpm"),
        ("Arch",
         "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.linux.x64.pkg.tar.zst"),
    ],
}


async def apps_list():
    """Приложения по платформам. Свой список, если владелец его правил."""
    raw = await db.get_setting("xray_apps")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return APPS


def apps_markdown(apps=None):
    """Готовый кусок сообщения со ссылками.

    Ссылки оформлены подписью, а не голым адресом: в адресах бывают знаки,
    которые Telegram принимает за разметку и ломает ссылку."""
    lines = []
    for platform, items in (apps or APPS).items():
        links = " · ".join(f"[{label}]({url})" for label, url in items)
        lines.append(f"  • **{platform}**: {links}")
    return "\n".join(lines)


async def qr_file(uuid_val):
    """QR со ссылкой на профиль — его сканируют приложением на телефоне."""
    link = await profile_link(uuid_val)
    if not link:
        return None
    import qrcode
    path = f"/tmp/xray_{uuid_val}.png"
    qrcode.make(link, error_correction=qrcode.constants.ERROR_CORRECT_L).save(path)
    return path

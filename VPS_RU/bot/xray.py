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
import hashlib
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


# Пул имён для маскировки. Все они обслуживаются одним и тем же `dest`, поэтому
# сертификат подходит каждому — проверено на живом узле для всех пяти.
#
# Зачем пул: снаружи трафик тридцати человек не выглядит обращением к одному и
# тому же имени. Это не защита сама по себе, но однообразие — примета.
MASK_POOL = {
    "avito.ru": ["avito.ru", "www.avito.ru", "m.avito.ru",
                 "static.avito.ru", "api.avito.ru"],
    "wildberries.ru": ["wildberries.ru", "www.wildberries.ru"],
    "ozon.ru": ["ozon.ru", "www.ozon.ru"],
    "vk.com": ["vk.com", "www.vk.com", "m.vk.com"],
    "kinopoisk.ru": ["kinopoisk.ru", "www.kinopoisk.ru"],
}


# Своя заглушка вместо чужого сайта. Хранится этим словом, а не адресом:
# адрес заглушки может поменяться, а выбор владельца — нет.
#
# Что это даёт. Обычная маска — чужой сайт, и мы зависим от него целиком:
# перестанет он отдавать пригодный сертификат, и вход умрёт, а узнаем мы об
# этом от людей. Ровно так у нас две недели не работал вход со Сбербанком.
# Со своей заглушкой сертификат наш, доступность наша, отклик нулевой.
#
# Чем за это платим, и это надо понимать до, а не после. Reality показывает
# сертификат маски в КАЖДОМ рукопожатии, а не только подозрительному гостю.
# Значит упавшая заглушка роняет этот вход целиком — тогда как чужой сайт
# лежит редко. Спасает то, что запасные входы остаются на чужих масках:
# приложение перейдёт на живой вход само.
SELF_DEST = "self"
# Куда Reality переадресует. Петля: заглушка живёт в том же сетевом
# пространстве, что и узел, наружу не опубликована.
SELF_ADDR = os.getenv("DECOY_ADDR", "127.0.0.1:8444")


def mask_names(dest: str):
    """Имена, которыми прикрывается вход. Как минимум сам домен.

    У своей заглушки имя ровно одно — имя узла: сертификат выписан на него, а
    придумывать поддомены без записей в DNS значит выдать себя.
    """
    if dest == SELF_DEST:
        from utils import public_domain
        domain = public_domain()
        return [domain] if domain else []
    return MASK_POOL.get(dest, [dest])


def dest_addr(dest: str) -> str:
    """Адрес, на который Reality уводит рукопожатие."""
    return SELF_ADDR if dest == SELF_DEST else f"{dest}:443"


def self_mask_ready():
    """Можно ли сейчас выбрать свою заглушку. Возвращает (можно, почему нет).

    Проверяем оба условия отдельно, потому что лечатся они по-разному: имени
    нет — купи и впиши; заглушка не поднята — открой подписку наружу, ей нужен
    тот же сертификат.
    """
    from utils import public_domain
    if not public_domain():
        return False, "у узла нет своего имени"
    try:
        import decoy
        if not decoy.is_up():
            return False, "заглушка не поднята — ей нужен сертификат"
    except Exception as e:
        return False, f"заглушка недоступна: {e}"
    return True, ""


def mask_for(dest: str, user_uuid: str) -> str:
    """Какое имя достанется этому человеку.

    Выбирается по нему самому, а не случайно: в уже выданной ссылке имя зашито,
    и если оно будет меняться при каждой пересборке конфига, старые ссылки
    перестанут подключаться.
    """
    names = mask_names(dest)
    if not names:
        # Такое бывает ровно в одном случае: маской выбран свой сайт, а имя
        # узла с тех пор убрали. Ссылку в этот момент всё равно собирают —
        # подписка идёт своим расписанием и о выборе маски не знает. Пустая
        # строка здесь оборвала бы её молча, поэтому берём обычную маску:
        # ссылка будет рабочей, а несоответствие увидит сверка.
        names = mask_names(DEFAULT_DEST)
    if len(names) == 1:
        return names[0]
    digest = hashlib.sha256((user_uuid or "").encode()).digest()
    return names[digest[0] % len(names)]


# Входы: порт и маска для каждого. Первый — основной, он на 443 и выглядит
# обычным HTTPS. Остальные — запасные, на общеизвестных запасных портах HTTPS.
#
# Зачем несколько: маску могут заблокировать целиком, и тогда вход с ней
# умирает. Человеку в подписку уходят все входы, и приложение само переходит на
# живой. Одним входом так нельзя — Reality переадресует проверяющего на сайт
# маски, и тот обязан отдать подходящий сертификат; у разных сайтов они разные.
# Сбербанк отсюда убран, и возвращать его нельзя.
#
# Он отдаёт сертификат «Russian Trusted Root CA» — удостоверяющего центра,
# которого нет в доверенных хранилищах телефонов и браузеров. А в REALITY
# клиент проверяет сертификат маски как настоящий: не проверился — соединение
# оборвано. Родная проверка Xray говорит это прямым текстом:
#
#     xray tls ping sberbank.ru
#     Pinging with SNI
#     Handshake failure: tls: failed to verify certificate:
#                        x509: certificate signed by unknown authority
#
# То есть вход с этой маской не работал никогда и работать не мог. Обиднее
# всего, что в выборе он стоял с подписью «банк: такое не блокируют никогда» —
# то есть сам себя рекомендовал.
#
# Проверять маску надо именно `xray tls ping <домен>`, а не доступностью сайта
# в браузере: браузер в России доверяет российскому центру, а телефон человека
# за границей — нет, и владелец увидит «у меня открывается», когда у людей не
# работает.
DEFAULT_ENTRIES = [
    (443, "avito.ru"),
    (2053, "wildberries.ru"),
    (2083, "ozon.ru"),
]


async def entries():
    """Входы в порядке предпочтения: сначала основной, потом запасные.

    Основной берётся из настроек — владелец мог сменить порт или маску на
    экране. Запасные идут следом и маску с основным не делят: смысл в том,
    чтобы они не падали вместе.
    """
    cfg_port = int(await db.get_setting("xray_port") or DEFAULT_PORT)
    cfg_dest = await db.get_setting("xray_dest") or DEFAULT_DEST
    # Своя заглушка могла быть выбрана тогда, когда имя и сертификат были на
    # месте, а сейчас их нет — например, владелец закрыл подписку наружу.
    # Собрать вход с пустым списком имён значит собрать вход, на который
    # никто не подключится, и не сказать об этом ни слова.
    if cfg_dest == SELF_DEST and not mask_names(SELF_DEST):
        print("Xray: своя заглушка выбрана, но имени узла нет — "
              "основной вход беру на " + DEFAULT_DEST, flush=True)
        cfg_dest = DEFAULT_DEST
    out = [(cfg_port, cfg_dest)]
    for port, dest in DEFAULT_ENTRIES:
        if port == cfg_port or dest == cfg_dest:
            continue
        out.append((port, dest))
    return out


async def readiness():
    """Чего Xray не хватает, чтобы работать так, как задумано.

    Зачем отдельным списком. Xray устроен сложнее амнезии: ему нужны разом
    ключи, маска, имя узла и открытая наружу подписка, каждое едет своим путём,
    а отказ любого выглядит одинаково — «VPN не работает». Владелец должен
    видеть недостающее заранее, одним экраном, а не выяснять это через неделю
    по жалобам.

    Обязательное отделено от желательного честно: без ключей вход не
    поднимется вовсе, а без имени узла он поднимется и будет работать — просто
    с коротким сертификатом и на порту, который режут мобильные операторы.

    Возвращает список: (в порядке ли, обязательно ли, что, почему, куда идти
    чинить).
    """
    from utils import public_domain
    cfg = await settings()
    out = []

    keys = bool(cfg["private_key"] and cfg["public_key"] and cfg["short_id"])
    out.append((keys, True, "Ключи Reality",
                "без них вход не поднимется; создаются сами при применении "
                "конфига", "xr_apply"))

    dest_ok, dest_why = True, ""
    if cfg["dest"] == SELF_DEST:
        dest_ok, dest_why = self_mask_ready()
    out.append((dest_ok, True, "Маска входа",
                dest_why or f"сейчас «{cfg['dest']}»", "xr_mask"))

    domain = public_domain()
    out.append((bool(domain), False, "Своё имя узла",
                "без него сертификат живёт 160 часов вместо 90 дней, а "
                "подписка остаётся на порту, который режут мобильные "
                "операторы", "psub_domain"))

    try:
        import handlers_pubsub
        sub_out = handlers_pubsub.is_on()
    except Exception:
        sub_out = False
    out.append((sub_out, False, "Подписка наружу",
                "пока закрыта, профиль обновляется только у подключённых к "
                "туннелю: изменения не доедут до того, у кого VPN как раз не "
                "работает", "psub_menu"))
    return out


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
        # Три значения, как и на удачном пути. Раньше здесь возвращалось два, и
        # вызывающий падал при распаковке вместо того, чтобы сказать человеку,
        # в чём дело: узел не отвечает или ключи ещё не заведены. Снаружи это
        # выглядело как молчащая кнопка, а не как понятная неудача.
        return None, [], "нет ключей Reality: узел не ответил"

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

    ways = await entries()
    config = {
        "log": {"loglevel": "warning"},
        # Один вход на маску. Люди и правила у всех общие: правило выбирает
        # канал по человеку, а не по тому, через какой вход он пришёл.
        "inbounds": [{
            "tag": f"in-vless-{port}",
            "listen": "0.0.0.0",
            "port": port,
            "protocol": "vless",
            "settings": {"clients": clients, "decryption": "none"},
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": dest_addr(dest),
                    # Весь пул имён этой маски: вход обязан принять любое,
                    # потому что у разных людей в ссылке зашиты разные.
                    "serverNames": mask_names(dest),
                    "privateKey": cfg["private_key"],
                    "shortIds": [cfg["short_id"]],
                },
            },
        } for port, dest in ways],
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


async def issue(user_uuid, new_address=False):
    """Заводит человеку подключение по Xray и возвращает адрес его подписки.

    Повторный вызов — это перевыпуск: ключ доступа меняется, старый перестаёт
    работать. А вот АДРЕС ПОДПИСКИ остаётся прежним, и это принципиально.

    Раньше менялось и то и другое. Получалось вот что: человек перевыпускал
    ключ, адрес в его приложении умирал (404), приложение молча оставалось со
    старыми серверами — и с уже отозванным ключом. Снаружи это выглядело как
    «перевыпустил, и ничего не работает», а починить можно было только вставив
    новый адрес руками. То есть подписка переставала быть подпиской ровно в тот
    момент, когда она нужнее всего.

    Теперь приложение по тому же адресу забирает новый ключ само, и человеку
    делать нечего.

    `new_address=True` меняет и адрес — это отдельный случай: утёк сам адрес
    подписки, а не ключ. Тогда новый адрес человеку придётся вставить заново, и
    просить об этом надо осознанно.
    """
    have = await db.get_xray_user(user_uuid)
    token = (have or {}).get("sub_token") if not new_address else None
    token = token or secrets.token_urlsafe(24)
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
async def profile_links(user_uuid):
    """Все входы этого человека, по одной ссылке на каждый.

    Порядок важен: первым идёт основной. Приложение пробует по порядку и
    переходит к следующему, когда предыдущий молчит, — ради этого несколько
    входов и заводились.
    """
    out = []
    for i, (port, dest) in enumerate(await entries()):
        link = await profile_link(user_uuid, port=port, dest=dest, index=i)
        if link:
            out.append(link)
    return out


async def profile_link(user_uuid, port=None, dest=None, index=0) -> str:
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
    # Вход: по умолчанию основной, но подписка собирает ссылку на каждый.
    port = port or cfg["port"]
    dest = dest or cfg["dest"]
    # Имя входа в приложении.
    #
    # Раньше сюда подставлялась маска — домен, которым прикидывается вход. Для
    # нас это опознавательный знак, а человек видел в списке «Сбербанк» и
    # «Wildberries» и справедливо не понимал, откуда у него чужие сервера и
    # почему их три. Маска — наша внутренняя кухня, показывать её незачем.
    #
    # Пишем то, что человеку и правда нужно знать: какой вход основной, а какие
    # запасные. Пробуются они по порядку, и это единственное, что про них важно.
    if index > 0:
        name = f"{name} · запасной {index}"
    return (f"vless://{rec['xray_uuid']}@{host}:{port}"
            f"?type=tcp&security=reality&sni={mask_for(dest, user_uuid)}"
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

    # Своё имя, если заведено. Оно идёт раньше адреса по двум причинам, и обе
    # про людей, а не про красоту: сертификат на имя живёт девяносто дней
    # вместо ста шестидесяти часов, и по имени подписку можно держать на
    # обычном 443, который не режут мобильные операторы.
    #
    # Берётся из окружения, не из кода: у каждой установки имя своё, а копия
    # проекта не должна требовать правки исходников.
    # Имя годится только вместе с ОТКРЫТОЙ наружу подпиской: сам по себе
    # домен порта не открывает. Раньше проверки не было, и владелец, вписавший
    # имя при закрытой подписке, раздал бы всем ссылку в никуда — а выглядела
    # бы она совершенно правильной.
    from utils import public_domain
    domain = public_domain()
    if domain:
        try:
            import handlers_pubsub
            if not handlers_pubsub.is_on():
                domain = ""
            port = handlers_pubsub.state().get("port", 2096)
        except Exception:
            port = 2096
    if domain:
        # 443 в адресе не пишут — он и так по умолчанию, а лишнее двоеточие в
        # ссылке человек принимает за ошибку.
        return ("https://%s" % domain) if int(port) == 443 else \
               ("https://%s:%s" % (domain, port))
    # Подписка открыта наружу — значит адрес у неё публичный, и знать об этом
    # человеку незачем: ссылка меняется сама вместе с тумблером. Иначе после
    # включения все получали бы адрес внутри туннеля, который снаружи молчит.
    try:
        import handlers_pubsub
        st = handlers_pubsub.state()
        if handlers_pubsub.is_on() and st.get("ip"):
            return f"https://{st['ip']}:{st.get('port', 8443)}"
    except Exception:
        pass
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


async def subscription_body(token: str, extra=None) -> str:
    """Тело подписки: список профилей в base64 — формат, который понимают
    все клиенты этого семейства.

    Пусто отдаём намеренно: если человек приостановлен или ссылка отозвана,
    клиент при следующем обновлении получит пустой список и профиль исчезнет.

    `extra` — строки, которые надо доложить к списку (сейчас это профиль
    маршрутизации). Кладём их в конец: клиент, который такую строку не знает,
    пропустит её, уже разобрав всё нужное.
    """
    rec = await db.get_xray_by_token(token)
    if not rec or not rec["is_active"]:
        return ""
    # Все входы, а не один: приложение перебирает их и переходит на живой,
    # когда маска отваливается. Перебирать оно может только присланное.
    links = await profile_links(rec["user_uuid"])
    if not links:
        return ""
    # Отметку «подключился» здесь НЕ ставим. Сюда приходит приложение за
    # списком серверов — это выдача, а не связь. Разница не словесная: по
    # этой отметке владельцу открывается кнопка «Убрать AmneziaWG», и
    # поставленная авансом она предлагает снять рабочий доступ человеку,
    # который по Xray ещё ни байта не передал. Ставит её теперь сборщик
    # трафика — когда по адресу реально пошли пакеты.
    return base64.b64encode("\n".join(links + list(extra or [])).encode()).decode()


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


# Картинку делаем крупной: код с профилем плотный, и мелкими точками он не
# читается с экрана чужой камерой. Восемь точек на модуль — размер, при котором
# сканируется и с телефона, и с монитора.
QR_BOX = 8


async def public_sub_url(uuid_val):
    """Личный адрес подписки, но только пока она открыта наружу.

    Изнутри туннеля адрес есть всегда — и на первую настройку он не годится:
    чтобы его прочитать, надо уже быть подключённым, а человек как раз ещё не
    подключён. Поэтому отдаём его, только когда снаружи и правда отвечают.
    """
    try:
        import handlers_pubsub
        if not handlers_pubsub.is_on():
            return ""
    except Exception:
        return ""
    rec = await db.get_xray_user(uuid_val)
    if not rec or not rec.get("sub_token"):
        return ""
    return await subscription_url(rec["sub_token"])


async def bundle_lines(uuid_val):
    """Всё, что нужно приложению.

    Пока подписка открыта наружу — это ОДИН адрес, и больше ничего. Приложение
    само заберёт по нему сервера, маскировки и профиль маршрутизации и само же
    будет обновлять их дальше. Ровно в этом и был смысл: человек вставляет одно,
    а не разбирается, какая из четырёх строк за что отвечает.

    Пока подписка закрыта, по адресу снаружи никто не ответит, и отдавать его
    нельзя — тогда идут сами сервера и профиль последней строкой. Приложение,
    которое такую строку не знает, пропустит её, уже разобрав сервера.
    """
    sub = await public_sub_url(uuid_val)
    if sub:
        return [sub]

    links = await profile_links(uuid_val)
    if not links:
        return []
    try:
        import happ_routing
        routing = await happ_routing.link(uuid_val=uuid_val)
        if routing:
            links = links + [routing]
    except Exception as e:
        # Без профиля подключение всё равно соберётся — просто без сплита.
        print(f"Сплит: профиль не собрался для {uuid_val}: {e}")
    return links


async def bundle_text(uuid_val):
    return "\n".join(await bundle_lines(uuid_val))


async def qr_file(uuid_val):
    """QR с тем же, что уходит текстом: сервера и сплит.

    Раньше кодировалась одна ссылка, и телефон получал подключение без
    раздельного туннелирования, а компьютер — с ним. Один и тот же ключ вёл
    себя по-разному в зависимости от того, как его заводили.
    """
    lines = await bundle_lines(uuid_val)
    if not lines:
        return None
    import qrcode
    path = f"/tmp/xray_{uuid_val}.png"

    def draw(payload):
        code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L,
                             box_size=QR_BOX, border=4)
        code.add_data(payload)
        # fit=True подбирает размер кода под данные — вплоть до предельного,
        # а не обрезает их.
        code.make(fit=True)
        code.make_image().save(path)

    try:
        draw("\n".join(lines))
    except qrcode.exceptions.DataOverflowError:
        # Предел QR — около 2950 байт, упереться в него можно только очень
        # длинным списком исключений. Тогда в картинке остаются сервера: без
        # них не будет вообще ничего, а сплит доедет текстом рядом.
        print(f"QR: профиль не влез в картинку для {uuid_val}")
        draw("\n".join(l for l in lines if not l.startswith("happ://")))
    return path

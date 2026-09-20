# -*- coding: utf-8 -*-
"""Имена вместо адресов внутри туннеля.

Внутри VPN имена раздаём мы сами: наш DNS обслуживает клиентов туннеля, и
наружу эти имена не существуют. Поэтому придумывать их можно свободно — ни
регистрировать, ни оплачивать нечего.

Одна оговорка появляется вместе со своим доменом: имена живут в нём же, и
заведённое внутри «www» закроет настоящий «www» этого домена — для всех, кто в
туннеле. Это свойство любого внутреннего DNS, а не наша поломка; лечится тем,
что вещи называют так, как их называют вслух: «дом», «печать», «нас».

Главное решение: имя привязывается **к человеку**, а не к цифрам. Адрес
подставляется живым при каждой раскладке, поэтому перевыпуск ключа, переезд на
новый ключ сервера или смена адреса имя не ломают — на узел просто приедет
новая пара. Привязка к конкретному адресу тоже есть: она нужна тому, что пиром
не является, — самому узлу, железке за роутером, сервису в домашней сети.
"""
import re

from database import db
from utils import WG_API_URL, api_session, public_domain

# Зона, в которой живут наши имена, когда своего домена у узла ещё нет.
#
# Она выдуманная, и это её единственная проблема: выдуманную зону не подтвердит
# ни один удостоверяющий центр, поэтому всё наше собственное — страница отказа,
# страница «доступ закрыт», выдача ключей — жило по имени, на которое нельзя
# получить настоящий сертификат. Браузер ругался на каждую нашу же страницу.
LOCAL_ZONE = "vpn"


def zone() -> str:
    """Зона, в которой живут имена ПРЯМО СЕЙЧАС.

    Есть у узла своё имя — имена живут в нём: «дом» становится
    «дом.example.ru». Нет — работаем в местной зоне, как и раньше.

    Зона одна на всю установку. Держать обе сразу было бы хуже всего: одно и то
    же устройство отзывалось бы на два имени, правила доступа ссылались бы на
    одно из них наугад, и однажды выяснилось бы, что доступ открыт не туда.
    """
    return public_domain() or LOCAL_ZONE


# Оглядка на прошлое: под каким именем зона была при прошлой раскладке. Нужна
# затем, чтобы заметить переезд и увести имена за собой.
ZONE_KEY = "dns_zone"

# Имя из букв, цифр и дефиса. Русские буквы разрешены: до DNS они доезжают
# в punycode, и переводим их мы сами — человеку это знать незачем.
_ALLOWED = re.compile(r"^[a-zа-яё0-9][a-zа-яё0-9-]{0,30}$", re.IGNORECASE)


def normalize(raw: str, in_zone: str = None):
    """Приводит введённое человеком к полному имени.

    Возвращает (имя, ошибка). Голое слово дополняется зоной: человек пишет
    «дом», получает «дом.example.ru».

    Зону отрезаем ПЕРЕД проверкой на точки, а не после: в настоящем домене
    точки есть, и прежний порядок отвергал бы собственное же имя.
    """
    z = in_zone or zone()
    name = (raw or "").strip().lower().rstrip(".")
    if not name:
        return None, "Пустое имя"
    head = name[: -len(z) - 1] if name.endswith("." + z) else name
    if "." in head:
        return None, (f"Точки в имени не нужны — пишите одно слово, "
                      f"зона «.{z}» добавится сама")
    if not _ALLOWED.match(head):
        return None, ("Имя может состоять из букв, цифр и дефиса, "
                      "до 31 знака, и начинаться с буквы или цифры")
    return f"{head}.{z}", None


def to_punycode(name: str) -> str:
    """Имя так, как его пришлёт клиент. Русские буквы в DNS едут в punycode,
    и сравнивать надо именно эту форму."""
    try:
        return ".".join(
            part if part.isascii() else part.encode("idna").decode("ascii")
            for part in name.split(".")
        )
    except Exception:
        return name


# Служебное имя самого узла: на нём живёт страница отказа, на которую
# уводятся закрытые сайты и сервисы. Заводится само — иначе страница так и
# осталась бы адресом с цифрами, который никто не помнит.
NODE_HEAD = "закрыто"
NODE_IP = "10.13.13.1"


def default_node_name() -> str:
    """Как называется служебное имя, пока его не переименовали."""
    return f"{NODE_HEAD}.{zone()}"

# Название служебного имени владелец может сменить, поэтому текущее живёт в
# настройках, а не в коде. Иначе переименование выглядело бы как создание
# второго имени: старое название система заводила бы заново.
NODE_NAME_KEY = "dns_node_name"
NODE_NAME_DONE = "dns_node_name_created"


async def node_name():
    """Как сейчас называется служебное имя."""
    return (await db.get_setting(NODE_NAME_KEY)) or default_node_name()


async def remember_node_name(name):
    """Запоминает новое название после переименования."""
    await db.set_setting(NODE_NAME_KEY, name)


async def ensure_node_name():
    """Заводит служебное имя ОДИН раз, при первом запуске.

    Дальше оно живёт своей жизнью: переименовали — запомнили новое название,
    удалили — значит удалили. Спорить с владельцем о содержимом его же системы
    система не должна."""
    if await db.get_setting(NODE_NAME_DONE):
        return False
    name = default_node_name()
    await db.set_dns_name(name, target_ip=NODE_IP,
                          comment="страница отказа на узле")
    await db.set_setting(NODE_NAME_KEY, name)
    await db.set_setting(NODE_NAME_DONE, "1")
    return True


def _zone_of(name: str) -> str:
    """Зона имени — всё, что после первого слова. Голова точек не содержит."""
    return name.split(".", 1)[1] if "." in name else ""


async def migrate_zone():
    """Уводит уже заведённые имена в новую зону.

    Зона меняется редко — обычно один раз в жизни установки, когда у узла
    появляется настоящее имя. Но к этому моменту имена уже заведены, на них уже
    ссылаются правила доступа, и оставить их в прежней зоне значит оставить
    половину системы говорящей на языке, которого больше нет: человек открывает
    «дом.example.ru», а правило доступа знает только «дом.vpn».

    Поэтому имена переезжают сами, вместе с правилами. Возвращает
    (сколько переехало, что не влезло).
    """
    new = zone()
    rows = await db.list_dns_names()
    old = await db.get_setting(ZONE_KEY)
    if old is None:
        # Первый запуск после обновления: прежней отметки нет. Зону узнаём по
        # самим именам — предполагать «наверняка было .vpn» нельзя, домен могли
        # задать и раньше, чем мы научились переезжать.
        zones = {_zone_of(r["name"]) for r in rows} - {""}
        old = zones.pop() if len(zones) == 1 else new
    if old == new:
        await db.set_setting(ZONE_KEY, new)
        return 0, []

    moved, clashed = [], []
    for row in rows:
        if _zone_of(row["name"]) != old:
            continue
        head = row["name"][: -len(old) - 1]
        target = f"{head}.{new}"
        if await db.get_dns_name(target):
            # Такое имя в новой зоне уже есть. Молча затереть его значит увести
            # чей-то доступ на чужое устройство — лучше оставить оба и сказать.
            clashed.append(row["name"])
            continue
        await db.rename_dns_name(row["name"], target)
        moved.append(target)

    # Служебное имя помним отдельно: иначе оно завелось бы заново в новой зоне
    # рядом с переехавшим, и на узле их стало бы два.
    svc = await db.get_setting(NODE_NAME_KEY)
    if svc and _zone_of(svc) == old:
        await db.set_setting(NODE_NAME_KEY, svc[: -len(old) - 1] + "." + new)

    await db.set_setting(ZONE_KEY, new)
    try:
        await db.log_event("Имена", f"Зона «{old}» → «{new}»: переехало "
                                    f"{len(moved)}" +
                           (f", осталось из-за совпадения: "
                            f"{', '.join(clashed)}" if clashed else ""))
    except Exception:
        pass
    return len(moved), clashed


async def resolve_all():
    """Собирает таблицу «имя → адрес» для узла.

    Имя, привязанное к человеку без адреса (пир ещё не создан), пропускается:
    лучше не ответить вовсе, чем увести человека не туда."""
    rows = await db.list_dns_names()
    ips = {}
    if any(r["target_uuid"] for r in rows):
        from acl import peer_ip_map
        ips = await peer_ip_map()

    table, skipped = {}, []
    for row in rows:
        ip = row["target_ip"] or ips.get(row["target_uuid"])
        if not ip:
            skipped.append(row["name"])
            continue
        table[row["name"]] = ip
        # Обе формы: человек мог назвать имя русскими буквами.
        puny = to_punycode(row["name"])
        if puny != row["name"]:
            table[puny] = ip

        # И короткая форма — одно слово, без зоны. Набирать третий уровень в
        # адресной строке каждый раз незачем, а односложных имён в интернете не
        # бывает: перехватить этим чужое нельзя.
        #
        # Работает сразу и у всех, без перевыдачи ключей. Полное имя при этом
        # остаётся главным: на него ссылаются правила доступа, и короткое —
        # только удобство поверх.
        head = row["name"].split(".", 1)[0]
        if head and head not in table:
            table[head] = ip
            puny_head = to_punycode(head)
            if puny_head != head:
                table[puny_head] = ip
    return table, skipped


async def client_upstreams():
    """Адрес в туннеле → верхний DNS, который выбрал сам человек.

    Берётся из его же конфига: там строка `DNS = ...`, записанная при выдаче
    ключа. Ради этого и читаем файлы, а не гадаем: часть людей сознательно
    выбрала AdGuard, и заворот на узел не должен у них это отнять."""
    import re
    from pathlib import Path
    from utils import CONFIGS_DIR

    by_name = {}
    try:
        for path in Path(CONFIGS_DIR).glob("*.conf"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            dns = re.search(r"^DNS\s*=\s*([^\n,]+)", text, re.MULTILINE)
            addr = re.search(r"^Address\s*=\s*([\d.]+)", text, re.MULTILINE)
            if dns and addr:
                by_name[addr.group(1).strip()] = dns.group(1).strip()
    except Exception as e:
        print(f"Имена: не удалось прочитать конфиги: {e}")
    return by_name


async def apply_names(reason: str = ""):
    """Отдаёт таблицу узлу. Узел заворачивает DNS туннеля на себя, только пока
    имена есть; когда последнее удалено — заворот снимается сам."""
    try:
        # Переезд зоны — раньше всего остального: раскладывать на узел надо уже
        # переехавшие имена, иначе до следующей раскладки в сети живёт старое.
        moved, clashed = await migrate_zone()
        await ensure_node_name()
        table, skipped = await resolve_all()
    except Exception as e:
        return False, f"не удалось собрать имена: {e}"

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/dns/names",
                                    json={"names": table,
                                          "zone": zone(),
                                          "upstreams": await client_upstreams()},
                                    timeout=15) as resp:
                if resp.status != 200:
                    return False, f"узел отклонил имена: {await resp.text()}"
    except Exception as e:
        return False, f"узел недоступен: {e}"

    msg = f"Имена применены: {len(await db.list_dns_names())}"
    if moved:
        msg += f", переехало в зону «{zone()}»: {moved}"
    if clashed:
        msg += f" (не переехали, имя занято: {', '.join(clashed)})"
    if skipped:
        msg += f" (без адреса пока: {', '.join(skipped)})"
    if reason:
        msg += f" · {reason}"
    try:
        await db.log_event("Имена", msg)
    except Exception:
        pass
    return True, msg

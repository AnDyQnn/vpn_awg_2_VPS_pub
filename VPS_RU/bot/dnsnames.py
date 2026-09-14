# -*- coding: utf-8 -*-
"""Имена вместо адресов внутри туннеля.

Внутри VPN имена раздаём мы сами: наш DNS обслуживает клиентов туннеля, и
наружу эти имена не существуют. Поэтому придумывать их можно свободно — ни
регистрировать, ни оплачивать нечего.

Главное решение: имя привязывается **к человеку**, а не к цифрам. Адрес
подставляется живым при каждой раскладке, поэтому перевыпуск ключа, переезд на
новый ключ сервера или смена адреса имя не ломают — на узел просто приедет
новая пара. Привязка к конкретному адресу тоже есть: она нужна тому, что пиром
не является, — самому узлу, железке за роутером, сервису в домашней сети.
"""
import re

from database import db
from utils import WG_API_URL, api_session

# Зона, в которой живут наши имена. Короткая и не пересекается с настоящими
# доменами интернета, поэтому запрос на неё никогда не уйдёт наверх.
ZONE = "vpn"

# Имя из букв, цифр и дефиса. Русские буквы разрешены: до DNS они доезжают
# в punycode, и переводим их мы сами — человеку это знать незачем.
_ALLOWED = re.compile(r"^[a-zа-яё0-9][a-zа-яё0-9-]{0,30}$", re.IGNORECASE)


def normalize(raw: str):
    """Приводит введённое человеком к полному имени.

    Возвращает (имя, ошибка). Голое слово дополняется зоной: человек пишет
    «дом», получает «дом.vpn»."""
    name = (raw or "").strip().lower().rstrip(".")
    if not name:
        return None, "Пустое имя"
    if name.endswith("." + ZONE):
        head = name[: -len(ZONE) - 1]
    elif "." in name:
        return None, f"Точки в имени не нужны — пишите одно слово, зона «.{ZONE}» добавится сама"
    else:
        head = name
    if not _ALLOWED.match(head):
        return None, ("Имя может состоять из букв, цифр и дефиса, "
                      "до 31 знака, и начинаться с буквы или цифры")
    return f"{head}.{ZONE}", None


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
NODE_NAME = f"закрыто.{ZONE}"
NODE_IP = "10.13.13.1"


async def ensure_node_name():
    """Проверяет, что служебное имя на месте. Удалить его владелец может —
    это его система; но само оно не пропадёт."""
    if await db.get_dns_name(NODE_NAME):
        return False
    await db.set_dns_name(NODE_NAME, target_ip=NODE_IP,
                          comment="страница отказа на узле")
    return True


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
        await ensure_node_name()
        table, skipped = await resolve_all()
    except Exception as e:
        return False, f"не удалось собрать имена: {e}"

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/dns/names",
                                    json={"names": table,
                                          "upstreams": await client_upstreams()},
                                    timeout=15) as resp:
                if resp.status != 200:
                    return False, f"узел отклонил имена: {await resp.text()}"
    except Exception as e:
        return False, f"узел недоступен: {e}"

    msg = f"Имена применены: {len(await db.list_dns_names())}"
    if skipped:
        msg += f" (без адреса пока: {', '.join(skipped)})"
    if reason:
        msg += f" · {reason}"
    try:
        await db.log_event("Имена", msg)
    except Exception:
        pass
    return True, msg

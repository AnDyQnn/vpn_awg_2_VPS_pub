# -*- coding: utf-8 -*-
"""Переезд на новый ключ сервера.

Зачем. Ключ сервера какое-то время был доступен через открытую панель узла —
значит, его надо сменить. Сменить на месте нельзя: этот ключ прописан в конфиге
у каждого, и правка разом отключила бы всех.

Как. Рядом поднимается второй интерфейс на другом порту, со своим ключом и
усиленной обфускацией. Люди переезжают по одному: каждому выдаётся новый конфиг,
старый при этом продолжает работать. Пока последний не переехал, старый интерфейс
живёт. Ничего не выключается по таймеру — старый интерфейс сносит владелец
кнопкой, и только после того, как увидит список отстающих.

Важная деталь про конфиги: меняется ключ СЕРВЕРА, а не клиента. Поэтому новый
конфиг — это старый файл, в котором заменены ключ сервера, порт и параметры
обфускации. Приватный ключ человека и его адрес в туннеле остаются прежними,
значит роли, лимиты и статистика продолжают работать без переноса.
"""
import re
from pathlib import Path

from database import db
from utils import WG_API_URL, api_session, CONFIGS_DIR

OBF_KEYS = ("Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4")


async def status():
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/migration/status", timeout=10) as r:
                if r.status == 200:
                    return await r.json()
    except Exception as e:
        return {"error": str(e)}
    return {"error": "узел не ответил"}


async def start(port: int = 51821):
    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/migration/start",
                                    json={"port": port}, timeout=30) as r:
                data = await r.json()
                if r.status != 200:
                    return False, str(data)
    except Exception as e:
        return False, str(e)
    await db.log_event("Migration", f"Поднят второй интерфейс на порту {port}")
    return True, data


async def abort():
    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/migration/abort", timeout=30) as r:
                if r.status != 200:
                    return False, await r.text()
    except Exception as e:
        return False, str(e)
    await db.log_event("Migration", "Переезд отменён, второй интерфейс снят")
    return True, "Переезд отменён, старый интерфейс не пострадал"


async def finish():
    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/migration/finish", timeout=30) as r:
                if r.status != 200:
                    return False, await r.text()
    except Exception as e:
        return False, str(e)
    await db.log_event("Migration", "Старый интерфейс остановлен, переезд завершён")
    return True, "Старый интерфейс остановлен"


async def peers_snapshot():
    """uuid → (публичный ключ, адрес). Ключ пира нужен, чтобы прописать его
    на новом интерфейсе, а адрес — чтобы он остался прежним."""
    out = {}
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=10) as r:
                if r.status != 200:
                    return out
                for p in await r.json():
                    ip = (p.get("allowed_ips") or "").split("/")[0]
                    if p.get("uuid") and p.get("public_key") and ip:
                        out[p["uuid"]] = (p["public_key"], ip)
    except Exception as e:
        print(f"Переезд: не получил список пиров: {e}")
    return out


def rewrite_config(text: str, server_pubkey: str, port: int, obfuscation: dict,
                   endpoint_host: str = None) -> str:
    """Меняет в конфиге ровно три вещи: ключ сервера, порт и обфускацию.

    Остальное не трогаем намеренно: адрес, приватный ключ человека, DNS и
    AllowedIPs остаются как были — иначе переезд превратился бы в перевыпуск
    со всеми его последствиями."""
    lines = text.splitlines()
    out, section = [], ""
    seen_obf = set()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            if section == "Interface":
                for key in OBF_KEYS:
                    if key not in seen_obf and key in obfuscation:
                        out.append(f"{key} = {obfuscation[key]}")
            section = stripped.strip("[]")
            out.append(line)
            continue

        key = stripped.split("=")[0].strip()
        if section == "Interface" and key in OBF_KEYS:
            if key in obfuscation:
                out.append(f"{key} = {obfuscation[key]}")
                seen_obf.add(key)
            continue
        if section == "Peer" and key == "PublicKey":
            out.append(f"PublicKey = {server_pubkey}")
            continue
        if section == "Peer" and key == "Endpoint":
            host = endpoint_host or stripped.split("=", 1)[1].strip().rsplit(":", 1)[0]
            out.append(f"Endpoint = {host}:{port}")
            continue
        out.append(line)

    if section == "Interface":
        for key in OBF_KEYS:
            if key not in seen_obf and key in obfuscation:
                out.append(f"{key} = {obfuscation[key]}")

    return "\n".join(out).strip() + "\n"


async def issue_for(uuid_val, server_pubkey, port, obfuscation):
    """Готовит новый конфиг человеку и прописывает его на новом интерфейсе.

    Возвращает (путь к конфигу, путь к QR) или (None, причина)."""
    import qrcode

    user = await db.get_user_by_uuid(uuid_val)
    if not user:
        return None, "ключ не найден"
    snap = await peers_snapshot()
    if uuid_val not in snap:
        return None, "пира нет на узле"
    public_key, client_ip = snap[uuid_val]

    conf_path = Path(CONFIGS_DIR) / f"{user['name']}.conf"
    if not conf_path.exists():
        return None, "файла конфига нет на диске"

    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/migration/peer",
                                    json={"public_key": public_key,
                                          "client_ip": client_ip}, timeout=15) as r:
                if r.status != 200:
                    return None, await r.text()
    except Exception as e:
        return None, str(e)

    new_text = rewrite_config(conf_path.read_text(encoding="utf-8"),
                              server_pubkey, port, obfuscation)
    conf_path.write_text(new_text, encoding="utf-8")
    qr_path = Path(CONFIGS_DIR) / f"{user['name']}.png"
    qrcode.make(new_text, error_correction=qrcode.constants.ERROR_CORRECT_L).save(qr_path)

    await db.log_event("Migration", f"Новый конфиг выдан: {user['name']}")
    return str(conf_path), str(qr_path)


async def laggards():
    """Кто ещё не переехал: есть на старом интерфейсе и не здоровался на новом."""
    st = await status()
    if st.get("error") or not st.get("active"):
        return []
    moved = set(st.get("connected_keys", []))
    snap = await peers_snapshot()
    out = []
    for uuid_val, (pub, ip) in snap.items():
        if pub in moved:
            continue
        user = await db.get_user_by_uuid(uuid_val)
        if user:
            out.append({"uuid": uuid_val, "name": user["name"]})
    return out

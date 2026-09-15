# -*- coding: utf-8 -*-
"""Сверка базы с тем, что реально стоит на узле.

Это не тест кода — код на узле между воскресеньями не меняется, и проверять
его по таймеру незачем. Это проверка того, что РЕАЛЬНОСТЬ не разошлась с базой,
а она расходится сама: от перезапуска контейнера, от правки руками, от команды,
которая не доехала, от сбоя посреди применения.

Именно такие расхождения и ломали узел раньше, и заметить их было нечем: бот
показывает базу, узел живёт своей жизнью, и пока человек не пожалуется, разницы
никто не видит.

Запускается на живом узле, ничего не меняет — только читает. Вывод устроен так,
чтобы его без разбора складывал аудит: строки вида «состояние|название|что
именно», где состояние — ok, warning или error.
"""
import asyncio
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, "/app")

# Подсеть туннеля: всё, что вне её, адресом пира не является. Нужна, чтобы
# отличить настоящий адрес от маршрута по умолчанию у выходного узла.
TUNNEL_PREFIX = "10.13.13."
EXIT_ROUTE = "0.0.0.0/0"

WG_API_URL = os.getenv("WG_API_URL", "http://127.0.0.1:8000/api")
DE_AGENT_URL = os.getenv("DE_AGENT_URL", "http://10.13.13.254:8000/api")
API_TOKEN = os.getenv("API_TOKEN", "").strip()

LINES = []


def say(status, name, msg):
    LINES.append("%s|%s|%s" % (status, name, msg))


def node_get(path):
    """Чтение с узла. Ошибку не глотаем — она сама по себе результат."""
    req = urllib.request.Request(WG_API_URL + path)
    if API_TOKEN:
        req.add_header("X-Api-Key", API_TOKEN)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def de_get(path):
    """То же, но у агента Германии — по туннелю."""
    req = urllib.request.Request(DE_AGENT_URL + path)
    if API_TOKEN:
        req.add_header("X-Api-Key", API_TOKEN)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


async def main():
    from database import db
    await db.connect()

    # --- пиры: база против интерфейса --------------------------------------
    #
    # Расхождение в любую сторону — беда, но разная. Нет на узле того, что есть
    # в базе, — человек не подключится и не поймёт почему. Есть на узле то,
    # чего нет в базе, — это «призрак»: доступ, которым владеет неизвестно кто.
    try:
        rows = await db.fetch_all(
            "SELECT uuid, name FROM users WHERE is_active = TRUE")
        db_uuids = {r["uuid"] for r in rows}
        peers = node_get("/peers")          # отдаётся голым списком
        node_uuids = {p.get("uuid") for p in peers if p.get("uuid")}

        missing = db_uuids - node_uuids
        ghosts = node_uuids - db_uuids
        if missing:
            names = [r["name"] for r in rows if r["uuid"] in missing][:3]
            say("error", "Пиры: база против узла",
                "%d из базы нет на узле (%s)" % (len(missing), ", ".join(names)))
        elif ghosts:
            say("error", "Пиры: база против узла",
                "%d лишних на узле — доступ без владельца" % len(ghosts))
        else:
            say("ok", "Пиры: база против узла", "%d, совпадают" % len(db_uuids))
    except Exception as e:
        say("error", "Пиры: база против узла", "не удалось сверить: %s" % e)

    # --- Xray: у каждого должен быть парный адрес --------------------------
    #
    # Xray отправляет трафик человека с отдельного адреса, «двойника» его
    # пира — только так узел умеет считать и разграничивать. Нет двойника —
    # человек подключится, но учёт и роли на него не подействуют, то есть
    # ограничения окажутся выключены молча.
    try:
        xrows = await db.fetch_all(
            "SELECT user_uuid FROM xray_users WHERE revoked_at IS NULL")
        x = node_get("/xray/status").get("xray") or {}
        if not xrows:
            say("ok", "Xray: ключи и узел", "ключей не выдано")
        elif not x.get("has_config"):
            say("error", "Xray: ключи и узел",
                "%d ключей выдано, а конфига на узле нет" % len(xrows))
        elif not x.get("up"):
            say("error", "Xray: ключи и узел",
                "%d ключей выдано, процесс не работает" % len(xrows))
        else:
            say("ok", "Xray: ключи и узел",
                "%d ключей, процесс работает" % len(xrows))
    except Exception as e:
        say("warning", "Xray: ключи и узел", "не удалось сверить: %s" % e)

    # --- роли: что записано и что реально стоит ----------------------------
    #
    # Роль — это правила в файрволе. Между базой и правилами расхождение
    # означает, что доступ либо шире, либо уже обещанного, и в первом случае
    # это дыра, про которую никто не знает.
    try:
        grants = await db.fetch_val(
            "SELECT COUNT(*) FROM role_grants") or 0
        acl = node_get("/acl")
        applied = len(acl.get("peers") or [])
        chain = acl.get("chain") or ""
        rules = max(0, len([l for l in chain.split("\n")
                            if l.strip() and not l.startswith("Chain")
                            and not l.strip().startswith("pkts")]))
        if grants and not rules:
            say("error", "Роли: база против правил",
                "в базе %d правил, на узле пусто" % grants)
        elif not acl.get("saved_at"):
            say("warning", "Роли: база против правил", "раскладка ни разу не применялась")
        else:
            say("ok", "Роли: база против правил",
                "%d человек под ролями, %d строк в цепочке" % (applied, rules))
    except Exception as e:
        say("warning", "Роли: база против правил", "не удалось сверить: %s" % e)

    # --- имена внутри туннеля ----------------------------------------------
    try:
        names_db = await db.fetch_all("SELECT name FROM dns_names")
        on_node = node_get("/dns/names").get("names") or {}
        missing = {r["name"] for r in names_db} - set(on_node)
        if missing:
            say("error", "Имена внутри туннеля",
                "%d из базы не разложены (%s)"
                % (len(missing), ", ".join(sorted(missing)[:3])))
        else:
            say("ok", "Имена внутри туннеля", "%d, разложены" % len(names_db))
    except Exception as e:
        say("warning", "Имена внутри туннеля", "не удалось сверить: %s" % e)

    # --- учёт: у каждого живого адреса должен быть счётчик -----------------
    #
    # Без счётчика человек невидим для статистики и для контроля нагрузки: его
    # трафик не учитывается вообще, и на графике его просто нет.
    try:
        acct = node_get("/accounting").get("peers") or {}
        peers = node_get("/peers")
        # Только адреса внутри туннеля. У выходного узла в этом поле стоит
        # маршрут по умолчанию — счётчика на него нет и быть не должно.
        addrs = {p.get("allowed_ips", "").split("/")[0]
                 for p in peers if p.get("allowed_ips")}
        addrs = {a for a in addrs if a.startswith(TUNNEL_PREFIX)}
        blind = addrs - set(acct)
        if blind:
            say("error", "Учёт трафика по адресам",
                "%d адресов без счётчика (%s)"
                % (len(blind), ", ".join(sorted(blind)[:3])))
        else:
            say("ok", "Учёт трафика по адресам", "%d адресов под счётом" % len(addrs))
    except Exception as e:
        say("warning", "Учёт трафика по адресам", "не удалось сверить: %s" % e)


    # --- Германия: она про базу не знает, сверить может только мастер ------
    try:
        de_alive = de_get("/health")
        say("ok", "Агент Германии", "отвечает")
    except Exception as e:
        de_alive = None
        say("error", "Агент Германии", "не отвечает: %s" % e)

    # Туннель до Германии. Проверяем ВСЕГДА, а не только когда агент ответил:
    # если он молчит, именно здесь и написано почему.
    try:
        peers = node_get("/peers")
        # Выходной узел узнаём по маршруту по умолчанию: он единственный, кому
        # разрешено принимать весь трафик. По адресу 10.13.13.254 его искать
        # нельзя — узел отдаёт только первую из разрешённых сетей, а первой
        # стоит как раз маршрут.
        de_peer = [p for p in peers
                   if EXIT_ROUTE in p.get("allowed_ips", "")
                   or p.get("allowed_ips", "").startswith("10.13.13.254")]
        if not de_peer:
            say("error", "Туннель до Германии", "пира Германии нет на узле")
        elif not de_peer[0].get("latest_handshake"):
            say("error", "Туннель до Германии", "рукопожатий не было")
        else:
            age = int(time.time()) - de_peer[0]["latest_handshake"]
            if age > 600:
                say("error", "Туннель до Германии", "молчит %d мин" % (age // 60))
            else:
                say("ok", "Туннель до Германии", "рукопожатие %d с назад" % age)
    except Exception as e:
        say("warning", "Туннель до Германии", "не удалось сверить: %s" % e)

    # Версия. Мастер обновился, Германия нет — так уже было, и увидеть это было
    # неоткуда: обе ноды по отдельности выглядели здоровыми. Обе стороны хранят
    # короткий хеш коммита, который применил деплой.
    if de_alive is not None:
        try:
            mine = ""
            if os.path.exists("/volumes/VERSION"):
                mine = open("/volumes/VERSION").read().strip()[:7]
            there = (de_get("/host/deploy_status").get("hash") or "")[:7]
            if not mine or not there:
                say("warning", "Версии мастера и Германии",
                    "одна из сторон версию не записала")
            elif mine != there:
                say("warning", "Версии мастера и Германии",
                    "мастер %s, Германия %s" % (mine, there))
            else:
                say("ok", "Версии мастера и Германии", "совпадают (%s)" % mine)
        except Exception as e:
            say("warning", "Версии мастера и Германии", "не удалось сверить: %s" % e)


def check_env_described():
    """Переменные, без которых узел работает молча неправильно.

    У знакомого владельца пропали обе разом: ни `API_TOKEN`, ни
    `BACKUP_PASSWORD` не были даже описаны в `.env`. Установщик их не заводил,
    и отличить «не задано» от «задано пустым» было нечем — снаружи и то и
    другое выглядит одинаково, а узел при этом не ходит к соседу и не шифрует
    архивы.

    Проверяем то, что видит контейнер: дошло ли значение. Самого файла отсюда
    не видно, и это правильно — важен результат, а не строка в нём.
    """
    for key, why in (("API_TOKEN", "узлы не разговаривают друг с другом"),
                     ("BACKUP_PASSWORD", "архивы лежат незашифрованными")):
        if os.getenv(key, "").strip():
            say("ok", "Переменная %s" % key, "задана")
        else:
            say("error", "Переменная %s" % key, "пуста — %s" % why)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        say("error", "Сверка базы с узлом", "не отработала: %s" % e)
    check_env_described()
    print("\n".join(LINES))

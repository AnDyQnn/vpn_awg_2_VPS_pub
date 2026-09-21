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

    # --- свой канал в Германию: записан или нет ----------------------------
    #
    # Расходится это молча и надолго. В базе канал включён, а моста нет —
    # люди идут общим туннелем, связь у них есть, никто ничего не замечает. И
    # так месяцами, пока владелец не вспомнит, что канал вообще был.
    try:
        import cascade
        ch = await cascade.settings()
        if not ch.get("uuid"):
            say("ok", "Свой канал в Германию", "не настроен")
        elif not ch.get("on"):
            say("ok", "Свой канал в Германию", "выключен вручную")
        else:
            alive = await cascade.bridge_present()
            if alive:
                say("ok", "Свой канал в Германию", "мост на связи")
            else:
                say("warning", "Свой канал в Германию",
                    "включён, но моста нет — люди идут общим туннелем")
    except Exception as e:
        say("warning", "Свой канал в Германию", "не удалось сверить: %s" % e)

    # --- запрет обходного DNS ----------------------------------------------
    #
    # Без него фильтр держится на честном слове телефона: «Приватный DNS» и
    # браузерный DNS поверх HTTPS идут мимо нас, и фильтр выглядит сломанным,
    # хотя он исправен.
    try:
        st = node_get("/dns/bypass-status") or {}
        n = int(st.get("rules") or 0)
        if n >= 3:
            say("ok", "Запрет обходного DNS", "%d правил" % n)
        else:
            say("warning", "Запрет обходного DNS",
                "не настроен — фильтр обходят через DNS поверх HTTPS")
    except Exception as e:
        say("warning", "Запрет обходного DNS", "не удалось сверить: %s" % e)

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

    await check_dead_grants()


async def check_dead_grants():
    """Правила, которые не совпадут ни с одним пакетом.

    Роли — про своих, и адрес вне туннеля здесь взяться не может. Такие записи
    появляются от старых ошибок сбора адресов и остаются лежать: в цепочку
    уходит строка, которая никогда не сработает, а владелец видит её в списке
    доступов и верит ей.
    """
    try:
        sys.path.insert(0, "/app")
        from database import db
        from acl import grant_is_dead
        roles = await db.list_roles()
    except Exception as e:
        say("warning", "Мёртвые правила доступа", "не удалось проверить: %s" % e)
        return

    dead = []
    for role in roles:
        try:
            for grant in await db.get_role_grants(role["id"]):
                if grant_is_dead(grant):
                    dead.append("%s: %s" % (role["name"],
                                            grant.get("cidr") or grant.get("note") or "?"))
        except Exception:
            continue

    if dead:
        say("warning", "Мёртвые правила доступа",
            "%d — ничего не открывают: %s" % (len(dead), "; ".join(dead[:4])))
    else:
        say("ok", "Мёртвые правила доступа", "таких нет")


def check_category_lists():
    """Категория, у которой не загрузился список, ничего не фильтрует.

    Снаружи это незаметно: она показывается владельцу как обычная, включается
    человеку, значится включённой — и молча пропускает всё. Так и было с двумя
    категориями, у которых источник отдавал 404.

    Смотрим то же, что видит резолвер: файлы кэша. Пустой или отсутствующий
    файл у включённой кем-то категории — ошибка, а не мелочь.
    """
    cache = "/etc/amnezia/amneziawg/cache/dns"
    state = "/etc/amnezia/amneziawg/dns_filter.json"
    try:
        with open(state, encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        say("ok", "Списки категорий", "фильтры никому не включены")
        return

    used = set(data.get("common") or [])
    for cats in (data.get("clients") or {}).values():
        used.update(cats or [])
    if not used:
        say("ok", "Списки категорий", "фильтры никому не включены")
        return

    empty = []
    for cat in sorted(used):
        path = os.path.join(cache, "%s.txt" % cat)
        try:
            if os.path.getsize(path) < 100:
                empty.append(cat)
        except OSError:
            empty.append(cat)

    if empty:
        say("error", "Списки категорий",
            "не загрузились: %s — эти категории ничего не фильтруют"
            % ", ".join(empty))
    else:
        say("ok", "Списки категорий", "все загружены (%d)" % len(used))


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


def check_public_sub():
    """Подписка наружу: жив ли сертификат и слушают ли внешний порт.

    Сертификат на IP живёт 160 часов — меньше недели. Недельный отчёт приходит
    раз в неделю, и если про сертификат в нём не сказано, узнать о его смерти
    неоткуда: подписка просто перестанет обновляться у всех сразу, молча.

    Отсюда видно ровно две вещи — файл и сокет. Правила файрвола и таймер
    продления живут на хосте, их смотрит проверка хоста.
    """
    cert = os.path.join(os.getenv("SUB_CERT_DIR", "/volumes/certs"),
                        "fullchain.pem")
    state_file = "/volumes/flags/public_sub.json"
    try:
        size = os.path.getsize(cert)
    except OSError:
        size = 0
    if not size:
        # Закрыта — это нормальное состояние, а не поломка.
        say("ok", "Подписка наружу", "закрыта, видна только изнутри")
        return

    left = None
    try:
        with open(state_file, encoding="utf-8") as f:
            until = json.load(f).get("until")
        if until:
            left = (float(until) - time.time()) / 86400.0
    except Exception:
        left = None

    if left is None:
        say("warning", "Подписка наружу · сертификат", "срок неизвестен")
    elif left < 1:
        say("error", "Подписка наружу · сертификат",
            "истекает меньше чем через сутки — продление не доехало")
    elif left < 3:
        say("warning", "Подписка наружу · сертификат",
            "осталось %.1f сут." % left)
    else:
        say("ok", "Подписка наружу · сертификат", "осталось %.1f сут." % left)

    # Сокет. Сертификат может лежать, а вход не подняться — например, бота
    # перезапустили в ту минуту, когда файла ещё не было.
    try:
        import socket
        s = socket.socket()
        s.settimeout(3)
        s.connect(("127.0.0.1", 2096))
        s.close()
        say("ok", "Подписка наружу · внешний вход", "порт 2096 отвечает")
    except Exception as e:
        say("error", "Подписка наружу · внешний вход",
            "сертификат есть, а порт молчит: %s" % e)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        say("error", "Сверка базы с узлом", "не отработала: %s" % e)
    check_category_lists()
    check_env_described()
    check_public_sub()
    print("\n".join(LINES))

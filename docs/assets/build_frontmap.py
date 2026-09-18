# -*- coding: utf-8 -*-
"""Собирает карту экранов бота из исходников — для frontmap.html.

Зачем отдельный сборщик, а не карта руками. Карта, нарисованная руками,
устаревает в тот же день: кнопку переименовали, экран добавили, ветку убрали —
а на картинке всё по-старому. Такая карта хуже отсутствующей, потому что ей
верят. Поэтому читаем сам код: подписи кнопок, их `callback_data` и то, какой
обработчик за каждой стоит.

Что считается экраном. Функция-обработчик, в которой собирается клавиатура.
Кнопки внутри неё — исходящие связи; куда ведёт каждая, разбирается по роутеру
`bot.py`: точные сравнения `data == "..."` и префиксные `data.startswith("...")`.

Что мы честно не знаем. Подписи, собранные из переменных и f-строк, целиком
вычислить нельзя — они зависят от данных. Такие помечаем как «меняется», а не
выдумываем. Лучше дырка с табличкой, чем гладкая ложь.

Запуск:  python docs/assets/build_frontmap.py
Результат: docs/assets/frontmap.data.js
"""
import ast
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BOT = os.path.join(ROOT, "VPS_RU", "bot")
OUT = os.path.join(HERE, "frontmap.data.js")

# Экраны клиента — это его личный кабинет. Опознаём по файлу и по приставке
# `callback_data`: у клиентских веток она своя с самого начала проекта.
CLIENT_FILES = {"handlers_client.py", "delivery.py"}
CLIENT_PREFIXES = ("client_", "support_", "don_pay", "bypass_req")


def literal(node):
    """Текст узла, если он вычислим. Иначе — None и пометка «меняется»."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        # f-строка: берём постоянные куски, переменные заменяем на многоточие.
        out = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                out.append(part.value)
            else:
                out.append("…")
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = literal(node.left), literal(node.right)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.IfExp):
        # Тернарник в подписи: показываем оба исхода, они оба настоящие.
        a, b = literal(node.body), literal(node.orelse)
        if a is not None and b is not None:
            return a + " / " + b if a != b else a
        return a if a is not None else b
    return None


def buttons_in(func):
    """Кнопки, объявленные внутри функции, в порядке появления в коде."""
    found = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name != "InlineKeyboardButton":
            continue
        label = literal(node.args[0]) if node.args else None
        data = None
        for kw in node.keywords:
            if kw.arg == "callback_data":
                data = literal(kw.value)
            elif kw.arg == "url":
                data = "url:" + (literal(kw.value) or "…")
        found.append({
            "label": label if label is not None else "«меняется»",
            "data": data if data is not None else "«меняется»",
            "line": node.lineno,
            "dynamic": label is None or data is None,
        })
    return found


def routes_from_bot():
    """Куда ведёт каждый `callback_data`.

    Роутер разложен четырьмя способами сразу, и учитывать надо все — пропустив
    любой, мы нарисуем оборванную ветку там, где её нет:

      • `if data == "x": await screen(...)` — точное сравнение;
      • `if data.startswith("x_"): ...`     — по приставке;
      • `if data in ["a", "b"]: ...`        — списком;
      • `actions = {"a": func, ...}`        — таблицей в конце.

    И ещё одно: половина имён в роутере — псевдонимы из `import ... as ...`.
    `flt_common` на самом деле `common_screen` из filters.py, и без разбора
    псевдонимов такие связи выглядят как «обработчика с таким именем нет».
    """
    src = io.open(os.path.join(BOT, "bot.py"), encoding="utf-8").read()
    alias = {}
    for m in re.finditer(r"([a-z_][a-z0-9_]*)\s+as\s+([a-z_][a-z0-9_]*)", src):
        alias[m.group(2)] = m.group(1)

    def real(name):
        return alias.get(name, name)

    exact, prefix, inline = {}, {}, []
    tree = ast.parse(src)

    # Ветку от вызова может отделять что угодно: сброс состояния, комментарий,
    # импорт, вложенное условие. Регулярками это не ловится — читаем дерево.
    def keys_of(test):
        """Какие `callback_data` отбирает это условие."""
        ex, pre = [], []
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            left, op, right = test.left, test.ops[0], test.comparators[0]
            if getattr(left, "id", None) == "data":
                if isinstance(op, ast.Eq):
                    v = literal(right)
                    if v:
                        ex.append(v)
                elif isinstance(op, ast.In) and isinstance(right, (ast.List, ast.Tuple)):
                    for item in right.elts:
                        v = literal(item)
                        if v:
                            ex.append(v)
        if isinstance(test, ast.Call) and getattr(test.func, "attr", "") == "startswith":
            if getattr(test.func.value, "id", None) == "data" and test.args:
                v = literal(test.args[0])
                if v:
                    pre.append(v)
        return ex, pre

    # Не обработчики: разбор самой строки (`data.split(...)`), стройматериал
    # клавиатуры и встроенные функции. Взяв любое из этого за цель перехода,
    # карта показала бы связь «кнопка ведёт в split», и доверять ей стало бы
    # нельзя.
    NOT_HANDLERS = {
        "split", "partition", "replace", "strip", "lower", "upper", "append",
        "join", "get", "pop", "format", "startswith", "endswith",
        "int", "str", "len", "list", "dict", "set", "bool", "float", "print",
        "InlineKeyboardButton", "InlineKeyboardMarkup", "escape_md",
    }

    def handler_in(body):
        """Обработчик, который зовёт ветка. Ответы телеграму — не обработчики."""
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if isinstance(f, ast.Name):
                if f.id in NOT_HANDLERS:
                    continue
                return f.id
            if isinstance(f, ast.Attribute):
                if f.attr in NOT_HANDLERS:
                    continue
                base = getattr(f.value, "id", "")
                # `query.answer()`, `context.bot.send_message()` — это ответ, а
                # не переход. Обработчик из модуля (`hps.turn_on`) — переход.
                if base in ("query", "update", "context", "db", "data",
                            "os", "asyncio", "time", "json"):
                    continue
                if isinstance(f.value, ast.Attribute):
                    continue
                return f.attr
        return None

    def walk_ifs(body):
        for node in body:
            if not isinstance(node, ast.If):
                continue
            ex, pre = keys_of(node.test)
            if ex or pre:
                fn = handler_in(node.body)
                # Вложенные условия разбираем первыми: они точнее внешнего.
                walk_ifs(node.body)
                own = buttons_in(ast.Module(body=node.body, type_ignores=[]))
                if fn:
                    for k in ex:
                        exact.setdefault(k, real(fn))
                    for k in pre:
                        prefix.setdefault(k, real(fn))
                elif own:
                    # Шаг мастера, нарисованный прямо в роутере: отдельной
                    # функции у него нет, но экран — самый настоящий. Выдача
                    # ключа целиком так и устроена: срок, DNS, привязка
                    # Telegram. Без этих узлов карта обрывалась бы на полпути.
                    name = "шаг: " + (ex + pre)[0]
                    inline.append({"id": name, "keys": ex + pre,
                                   "line": node.lineno, "buttons": own})
                    for k in ex:
                        exact.setdefault(k, name)
                    for k in pre:
                        prefix.setdefault(k, name)
                else:
                    for k in ex:
                        exact.setdefault(k, "(без перехода)")
            else:
                walk_ifs(node.body)
            walk_ifs(node.orelse)

    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            walk_ifs(fn.body)
    # Таблицей: `actions = {...}` в самом конце роутера.
    tbl = re.search(r"actions = \{(.*?)\n    \}", src, re.S)
    if tbl:
        for key, fn in re.findall(
                r'"([^"]+)":\s*(?:lambda[^,]*?:\s*)?([a-z_][a-z0-9_]*)', tbl.group(1)):
            exact.setdefault(key, real(fn))
    return exact, prefix, inline


def target_of(data, exact, prefix):
    """Обработчик, которому достанется нажатие. Префикс — самый длинный.

    У половины кнопок `callback_data` собирается на лету: `act_pause_<uuid>`.
    Такие мы знаем только до первой подстановки — дальше многоточие. Искать по
    ним точное совпадение бессмысленно, зато приставка известна целиком, и
    именно по приставке их и разбирает роутер.
    """
    head = data.split("…")[0] if "…" in data else data
    if head == data and data in exact:
        return exact[data], "точно"
    best = ""
    for p in prefix:
        if head.startswith(p) and len(p) > len(best):
            best = p
    if best:
        return prefix[best], "по приставке «%s»" % best
    if head != data:
        # Приставка не нашлась, но и судить о такой кнопке строго нельзя:
        # говорим прямо, что разобрать не смогли.
        return None, "подставляется на лету"
    return None, None


def title_of(func):
    """Человеческое имя экрана — первая строка пояснения к функции."""
    doc = ast.get_docstring(func) or ""
    first = doc.strip().split("\n")[0].strip()
    return first[:80] if first else ""


# Роутеры — не экраны. Внутри `button_router` объявлены десятки клавиатур
# подтверждения, и свалить их в один узел значит нарисовать помойку вместо
# карты. Помечаем отдельно: пусть будут видны, но не выдают себя за экран.
ROUTERS = {"button_router", "handle_message", "handle_photo", "handle_document"}


def calls_in(func):
    """Имена функций, которые зовёт эта функция. Нужны, чтобы сшить экран со
    сборщиком меню: обработчик сам кнопок не объявляет, он зовёт `main_menu()`
    и ему подобных, а вся клавиатура живёт там."""
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None)
            if name:
                out.append(name)
    return out


def main():
    exact, prefix, inline = routes_from_bot()
    screens = []
    all_funcs = set()
    for fname in sorted(os.listdir(BOT)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(BOT, fname)
        try:
            tree = ast.parse(io.open(path, encoding="utf-8").read())
        except SyntaxError as e:
            print("пропускаю %s: %s" % (fname, e))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            all_funcs.add(node.name)
            btns = buttons_in(node)
            # Обработчики без кнопок тоже берём: часть из них зовёт сборщик
            # меню, и клавиатура у них появится ниже, при сшивке.
            if not btns and node.name not in exact.values() and \
                    node.name not in prefix.values():
                continue
            for b in btns:
                to, how = target_of(b["data"], exact, prefix)
                b["to"] = to
                b["how"] = how
            side = "client" if (
                fname in CLIENT_FILES
                or any(b["data"].startswith(CLIENT_PREFIXES) for b in btns)
            ) else "admin"
            screens.append({
                "id": node.name,
                "file": fname,
                "line": node.lineno,
                "title": title_of(node),
                "side": side,
                "kind": "router" if node.name in ROUTERS else "screen",
                "calls": calls_in(node),
                "buttons": btns,
            })

    # Шаги, нарисованные прямо в роутере, — такие же узлы карты.
    for step in inline:
        for b in step["buttons"]:
            to, how = target_of(b["data"], exact, prefix)
            b["to"], b["how"] = to, how
        screens.append({
            "id": step["id"], "file": "bot.py", "line": step["line"],
            "title": "шаг мастера, нарисован прямо в роутере",
            "side": "client" if step["keys"][0].startswith(CLIENT_PREFIXES) else "admin",
            "kind": "step", "calls": [], "buttons": step["buttons"],
        })

    # Сшиваем: обработчик, который сам кнопок не объявляет, но зовёт сборщик
    # меню, показывает именно его клавиатуру. Без этого «Главное меню» у нас
    # вело бы в пустоту — а оно ведёт в `main_menu()` из ui.py.
    by_id = {s["id"]: s for s in screens}
    MENUS = {s["id"] for s in screens if s["file"] == "ui.py"}
    for s in screens:
        if s["kind"] == "router":
            continue
        # Клавиатура из ui.py — это и есть то, что человек видит на экране.
        # Доклеиваем её к собственным кнопкам обработчика, а не «вместо»:
        # `return_to_main_menu` рисует главное меню и вдобавок свою строку.
        for name in s["calls"]:
            if name in MENUS and by_id.get(name, {}).get("buttons"):
                have = {(b["label"], b["data"]) for b in s["buttons"]}
                s["buttons"] = [dict(b, inherited=name)
                                for b in by_id[name]["buttons"]
                                if (b["label"], b["data"]) not in have] + s["buttons"]
                break
        if s["buttons"]:
            continue
        for name in s["calls"]:
            src = by_id.get(name)
            if src and src["buttons"]:
                s["buttons"] = [dict(b, inherited=name) for b in src["buttons"]]
                break
    # Сборщики меню после сшивки — уже не самостоятельные экраны: их содержимое
    # показано у тех, кто их зовёт. Держим их как «часть экрана».
    used = {b.get("inherited") for s in screens for b in s["buttons"]}
    for s in screens:
        if s["id"] in used:
            s["kind"] = "menu"

    # Экран, на который кто-то ведёт, но которого мы не нашли, — это дыра:
    # либо обработчик не рисует клавиатуру (действие), либо его нет вовсе.
    known = set(by_id)
    dangling = []
    for s in screens:
        for b in s["buttons"]:
            if b["to"] and b["to"] not in known:
                dangling.append({"from": s["id"], "label": b["label"],
                                 "data": b["data"], "to": b["to"],
                                 "why": ("обработчик есть, но клавиатуру не рисует"
                                         if b["to"] in all_funcs
                                         else "обработчика с таким именем нет")})

    data = {
        "generated": True,
        "screens": screens,
        "dangling": dangling,
        "counts": {
            "screens": len(screens),
            "buttons": sum(len(s["buttons"]) for s in screens),
            "admin": sum(1 for s in screens if s["side"] == "admin"),
            "client": sum(1 for s in screens if s["side"] == "client"),
        },
    }
    # Самопроверка перед записью.
    #
    # Роутер бота разложен четырьмя способами, и разбирается он здесь по живому
    # коду. Стоит кому-то переписать роутер иначе — разбор тихо перестанет
    # находить связи, и карта выродится в россыпь карточек без единой стрелки.
    # Выглядеть это будет не как поломка, а как «ну вот такая у нас теперь
    # архитектура». Поэтому лучше не записать карту вовсе, чем записать пустую.
    beef = []
    for root in ("main_menu", "send_client_menu"):
        s = next((x for x in screens if x["id"] == root), None)
        if not s or not s["buttons"]:
            beef.append("не найден корень «%s» или он без кнопок" % root)
    seen, queue = {"main_menu"}, ["main_menu"]
    idx = {s["id"]: s for s in screens}
    while queue:
        cur = idx.get(queue.pop())
        for b in (cur or {}).get("buttons", []):
            if b["to"] and b["to"] in idx and b["to"] not in seen:
                seen.add(b["to"])
                queue.append(b["to"])
    if len(seen) < 50:
        beef.append("от главного меню доступно всего %d экранов" % len(seen))
    total = sum(len(s["buttons"]) for s in screens)
    lost = sum(1 for s in screens for b in s["buttons"]
               if not b["to"] and not b["dynamic"]
               and not str(b["data"]).startswith("url:"))
    if total and lost * 10 > total:
        beef.append("без ветки в роутере %d кнопок из %d" % (lost, total))
    if beef:
        print("Карта не записана — разбор роутера развалился:")
        for line in beef:
            print("  •", line)
        print("Скорее всего роутер `bot.py` переписан иначе, чем умеет "
              "`routes_from_bot()`. Починить надо разбор, а не пороги.")
        raise SystemExit(1)
    data["reachable"] = len(seen)
    data["unrouted"] = lost

    body = json.dumps(data, ensure_ascii=False, indent=1)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        "// Собрано из исходников: python docs/assets/build_frontmap.py\n"
        "// Руками не править — перезапишется. Правки делаются в самом боте.\n"
        "window.FRONTMAP = " + body + ";\n")
    print("экранов: %d, кнопок: %d (админ %d, клиент %d)" % (
        data["counts"]["screens"], data["counts"]["buttons"],
        data["counts"]["admin"], data["counts"]["client"]))
    print("от главного меню доступно: %d, кнопок без ветки: %d" % (
        data["reachable"], data["unrouted"]))
    print("висячих связей: %d" % len(dangling))
    print("записано: %s" % OUT)


if __name__ == "__main__":
    main()

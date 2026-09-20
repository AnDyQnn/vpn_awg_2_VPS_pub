# -*- coding: utf-8 -*-
"""Личное исключение из общей категории — на самом резолвере.

Проверка бота говорит, что раскладка уехала правильной. Здесь проверяется то,
что с ней делает резолвер, — потому что именно он решает, открыть сайт или нет,
и ошибка тут означает либо открытый детям запрет, либо закрытый владельцу
интернет.
"""
import importlib.util
import io
import os
import sys

SRC = "/app/dnsfilter.py"

spec = importlib.util.spec_from_file_location("dnsfilter", SRC)
dnsfilter = importlib.util.module_from_spec(spec)
sys.modules["dnsfilter"] = dnsfilter
spec.loader.exec_module(dnsfilter)

OWNER = "10.13.13.2"
CHILD = "10.13.13.3"


def main():
    print("=== готовим категорию с одним доменом ===")
    os.makedirs(dnsfilter.CACHE_DIR, exist_ok=True)
    with io.open(os.path.join(dnsfilter.CACHE_DIR, "adult.txt"), "w",
                 encoding="utf-8") as f:
        f.write("0.0.0.0 porn.example\n")

    f = dnsfilter.Filters()
    f.domains = {"adult": dnsfilter._parse_list("0.0.0.0 porn.example\n")}
    f.common = {"adult"}
    f.clients = {}
    f.custom = set()
    f.allow_common = set()
    f.allow_clients = {}
    f.except_clients = {}
    print("категория «adult» закрыта для всех: ок")

    print()
    print("=== без исключения закрыто обоим ===")
    assert f.blocked(OWNER, "porn.example") == "adult"
    assert f.blocked(CHILD, "porn.example") == "adult"
    # И поддомены тоже: список содержит корень, а спрашивают вглубь.
    assert f.blocked(CHILD, "cdn.porn.example") == "adult"
    print("владелец и ребёнок — оба закрыты: ок")

    print()
    print("=== исключение открывает ОДНОМУ ===")
    f.except_clients = {OWNER: {"adult"}}
    assert f.blocked(OWNER, "porn.example") is None, "владельцу должно открыться"
    assert f.blocked(CHILD, "porn.example") == "adult", "ребёнку — нет"
    assert f.blocked(OWNER, "cdn.porn.example") is None
    print("открылось ровно одному адресу: ок")

    print()
    print("=== личный запрет сильнее исключения из общего ===")
    # Разные намерения: «сними с меня общее» и «закрой это лично ему». Второе
    # обязано пережить первое, иначе владелец, закрывший категорию человеку,
    # однажды обнаружит её открытой.
    f.clients = {OWNER: ["adult"]}
    assert f.blocked(OWNER, "porn.example") == "adult"
    f.clients = {}
    print("личный запрет не снимается исключением: ок")

    print()
    print("=== исключение не открывает ЧУЖУЮ категорию ===")
    f.domains["gambling"] = dnsfilter._parse_list("0.0.0.0 casino.example\n")
    f.common = {"adult", "gambling"}
    assert f.blocked(OWNER, "casino.example") == "gambling", \
        "снято было только «adult»"
    print("снимается ровно то, что снято: ок")

    print()
    print("=== свой список владельца сильнее всего ===")
    # Он короткий и заводится руками — значит выражает намерение точнее любой
    # категории. Исключение из общего его не отменяет.
    f.custom = {"porn.example"}
    assert f.blocked(OWNER, "porn.example") == "свой список"
    f.custom = set()
    print("свой список переживает исключение: ок")

    print()
    print("=== адрес без исключений работает как раньше ===")
    f.except_clients = {}
    assert f.blocked(OWNER, "porn.example") == "adult"
    assert f.blocked(OWNER, "example.org") is None
    print("поведение по умолчанию не изменилось: ок")

    print()
    print("ВСЁ ПРОШЛО")


main()

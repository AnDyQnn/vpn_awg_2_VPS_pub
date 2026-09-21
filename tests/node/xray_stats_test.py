# -*- coding: utf-8 -*-
"""Разбор счётчиков Xray: на нём держится учёт людей на своём канале.

Когда трафик уходит внутрь соединения моста, счётчики файрвола его не видят —
байты считает сам Xray, по учётному имени. Если разбор ошибётся, учёт покажет
нули, а понять это по работающему узлу нельзя ничем: узел жив, люди в сети,
графики пустые.

Поэтому разбор проверяется отдельно и на том, что приходит на самом деле, — в
том числе на мусоре, которого в ответе быть не должно, но однажды окажется.
"""
import ast
import io
import json
import os
import subprocess
import time

SRC = "/app/api.py"
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = [n for n in tree.body
          if isinstance(n, ast.FunctionDef) and n.name == "xray_stats_parse"]
assert picked, "разбор счётчиков не найден в api.py"
ns = {"subprocess": subprocess, "os": os, "json": json, "time": time}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)
parse = ns["xray_stats_parse"]

print("=== обычный ответ ===")
data = {"stat": [
    {"name": "user>>>alice>>>traffic>>>uplink", "value": "1200"},
    {"name": "user>>>alice>>>traffic>>>downlink", "value": "34000"},
    {"name": "user>>>bob>>>traffic>>>uplink", "value": "7"},
]}
got = parse(data)
print(" ", got)
assert got == {"alice": {"up": 1200, "down": 34000},
               "bob": {"up": 7, "down": 0}}, got
print("  байты разложены по людям и направлениям: ок")

print("\n=== счётчики не про людей не попадают в учёт ===")
# Входы и каналы — это про узел. Попади они сюда, в статистике появился бы
# несуществующий посетитель с чужим трафиком.
data = {"stat": [
    {"name": "inbound>>>in-vless-443>>>traffic>>>uplink", "value": "999999"},
    {"name": "outbound>>>direct>>>traffic>>>downlink", "value": "888888"},
    {"name": "user>>>alice>>>traffic>>>uplink", "value": "10"},
]}
got = parse(data)
print(" ", got)
assert got == {"alice": {"up": 10, "down": 0}}, got
print("  отсеяны: ок")

print("\n=== мусор не ломает разбор и не становится трафиком ===")
data = {"stat": [
    {"name": "user>>>alice>>>traffic", "value": "5"},          # частей не хватает
    {"name": "user>>>>>>traffic>>>uplink", "value": "5"},      # имя пустое
    {"name": "user>>>bob>>>traffic>>>uplink", "value": "нет"}, # не число
    {"name": "user>>>bob>>>traffic>>>downlink", "value": -8},  # отрицательное
    {"name": "user>>>bob>>>traffic>>>uplink", "value": 3},
]}
got = parse(data)
print(" ", got)
assert got == {"bob": {"up": 3, "down": 0}}, got
print("  мусор отброшен, живое число осталось: ок")

print("\n=== пустота — это пустота, а не ошибка ===")
for empty in ({}, {"stat": []}, {"stat": None}, None):
    assert parse(empty) == {}, empty
print("  ок")

print("\n=== два счётчика одного человека складываются ===")
# Xray отдаёт по счётчику на направление, но при сбросе и повторном опросе они
# могут прийти парой в одном ответе.
data = {"stat": [
    {"name": "user>>>alice>>>traffic>>>uplink", "value": 10},
    {"name": "user>>>alice>>>traffic>>>uplink", "value": 5},
]}
assert parse(data) == {"alice": {"up": 15, "down": 0}}
print("  ок")

print("\nВСЁ ПРОШЛО")

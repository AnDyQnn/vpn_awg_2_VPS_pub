# -*- coding: utf-8 -*-
"""Кнопки клиента с ключом в нажатии — только по своему ключу.

callback_data не секрет: подделать нажатие может любой пользователь бота.
Раньше «Перевыпустить», «Прислать конфиг», «Проверить связь», «Поддержка» и
карточка ключа верили идентификатору из нажатия — узнав чужой, можно было
получить чужой конфиг или перевыпустить чужой ключ.

Тест сам находит в коде клиентские кнопки, несущие ключ, и требует, чтобы
каждая проходила проверку: новая кнопка мимо неё не проскочит.
"""
import ast
import io
import re

SRC = io.open("/app/bot.py", encoding="utf-8").read()
tree = ast.parse(SRC)
ns = {}
picked = [n for n in tree.body
          if (isinstance(n, ast.FunctionDef) and n.name == "key_of_callback")
          or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("_KEY_BUTTONS", "_NOT_KEY")
                                                for t in n.targets))]
exec(compile(ast.Module(body=picked, type_ignores=[]), "bot.py", "exec"), ns)
key_of = ns["key_of_callback"]

print("=== что считается ключом ===")
U = "0a25cc5e-4850-4266-ba33-eeb3c7aea2e4"
for data, want in (("client_download_" + U, U), ("do_client_regen_" + U, U),
                   ("client_regen_" + U, U), ("client_key_manage_" + U, U),
                   ("check_conn_" + U, U), ("support_audit_" + U, U),
                   ("support_ask_" + U, U), ("client_how_" + U, U),
                   ("client_plat_ios_" + U, U),
                   ("client_regen_all", ""), ("do_client_regen_all", ""),
                   ("check_conn_all", ""), ("check_conn_None", ""),
                   ("client_menu", ""), ("client_my_keys", "")):
    got = key_of(data)
    assert got == want, (data, got)
print("ок")

print("\n=== каждая клиентская кнопка с ключом — под проверкой ===")
code = "".join(io.open("/app/%s" % f, encoding="utf-8").read()
               for f in ("handlers_client.py", "bot.py"))
prefixes = set(re.findall(r'callback_data=f"((?:client|check_conn|support|do_client)[a-z_]*_)\{', code))
print("  найдено:", sorted(prefixes))
for p in prefixes:
    if p == "client_sub_":           # проверяет сам обработчик
        continue
    sample = p + ("ios_" if p == "client_plat_" else "") + U
    assert key_of(sample) == U, "кнопка %s не проходит проверку владельца" % p
print("ок")

print("\n=== проверка стоит до обработчиков ===")
guard = SRC.index("uuid_arg = key_of_callback(data)")
for h in ("client_download_handler(", "client_regen_action(", "client_key_manage_handler("):
    assert SRC.index("await " + h) > guard, h
print("ок")
print("\nВСЁ ПРОШЛО")

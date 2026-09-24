# -*- coding: utf-8 -*-
"""Исключения: закрыли категорию, но этот сайт оставили.

Категория — грубый инструмент: «соцсети» закрывают вместе с рабочим чатом и
Вконтакте. Без исключений выбор был между «закрыть всё» и «не закрывать
ничего», и выбиралось второе.

Порядок проверки на узле — разрешения раньше запретов, личное раньше общего.
Здесь проверяется и он, и то, что бот довозит исключения до узла в правильном
виде: узел знает адреса, а не ключи.
"""
import asyncio
import ast
import io
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import filters as F                                # noqa: E402

ok = True
sent = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def node_filters():
    """Настоящий модуль узла, а не его пересказ: правило приоритетов живёт
    там, и проверять надо именно его."""
    src = io.open("/app/node_dnsfilter.py", encoding="utf-8").read()
    mod = {}
    tree = ast.parse(src)
    keep = [n for n in tree.body
            if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef,
                              ast.ClassDef, ast.Assign))]
    exec(compile(ast.Module(body=keep, type_ignores=[]), "node", "exec"), mod)
    return mod


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'al-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Разрешённый','al-1',TRUE)")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Обычный','al-2',TRUE)")
    await db.execute("DELETE FROM filter_allow WHERE domain LIKE '%example'")

    print("=== приоритет проверок на узле ===")
    mod = node_filters()
    flt = mod["Filters"]()
    flt.clients = {"10.0.0.1": ["social"], "10.0.0.2": ["social"]}
    flt.domains = {"social": mod["_parse_list"]("vk.com\nfacebook.com")}
    flt.custom = {"blocked.example"}
    flt.allow_common = set()
    flt.allow_clients = {}

    check("категория закрывает", flt.blocked("10.0.0.1", "vk.com") == "social")
    check("и поддомен тоже", flt.blocked("10.0.0.1", "login.vk.com") == "social",
          "иначе сайт всё равно не откроется")

    flt.allow_clients = {"10.0.0.1": {"vk.com"}}
    check("личное исключение сильнее категории",
          flt.blocked("10.0.0.1", "vk.com") is None)
    check("и распространяется на поддомены",
          flt.blocked("10.0.0.1", "login.vk.com") is None)
    check("у другого человека по-прежнему закрыто",
          flt.blocked("10.0.0.2", "vk.com") == "social",
          "исключение личное, а не общее")

    flt.allow_common = {"facebook.com"}
    check("общее исключение работает всем",
          flt.blocked("10.0.0.2", "facebook.com") is None)

    flt.allow_common = {"blocked.example"}
    check("исключение сильнее и своего списка владельца",
          flt.blocked("10.0.0.2", "blocked.example") is None,
          "разрешение, которое смотрят после запрета, — не разрешение")

    print()
    print("=== бот довозит исключения до узла ===")
    await db.add_filter_allow("VK.com")                       # общее, с заглавными
    await db.add_filter_allow("work.example", "al-1")         # личное

    common, per_uuid = await db.get_all_filter_allow()
    check("общее записано в нижнем регистре", "vk.com" in common, str(common))
    check("личное привязано к ключу",
          per_uuid.get("al-1") == ["work.example"], str(per_uuid))

    async def fake_map():
        return {"al-1": ["10.13.13.21", "10.13.13.149"], "al-2": ["10.13.13.22"]}
    F.peer_addr_map = fake_map

    class Resp:
        status = 200

        async def json(self):
            return {"filtered": 1}

        async def text(self):
            return ""

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class Session:
        def post(self, url, json=None, timeout=None):
            sent.update(json or {})
            return Resp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    F.api_session = lambda **kw: Session()
    await F.apply_filters("проверка")

    check("общие исключения ушли", "vk.com" in (sent.get("allow_common") or []))
    allowed = sent.get("allow_clients") or {}
    check("личное ушло по ОБОИМ адресам человека",
          allowed.get("10.13.13.21") == ["work.example"]
          and allowed.get("10.13.13.149") == ["work.example"],
          "адресов у него два — фильтр должен работать на обоих")
    check("чужому адресу ничего не досталось",
          "10.13.13.22" not in allowed, str(list(allowed)))

    await db.execute("DELETE FROM filter_allow WHERE domain LIKE '%example' "
                     "OR domain='vk.com'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'al-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

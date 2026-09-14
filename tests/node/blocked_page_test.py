# -*- coding: utf-8 -*-
"""Страница отказа — та самая, которую верстали, и с живыми данными.

Владелец увидел на бою не ту страницу: мы рисовали панель с замком на 17 КБ, а
узел отдавал обрезок на 2 КБ, написанный отдельно. Вёрстка лежала рядом и
никогда не была подключена — заметить это можно было только открыв страницу
глазами, чего никто не делал месяц.

Проверяется:
  • отдаётся именно верстанная страница, а не запасная заглушка;
  • в готовой странице не остаётся ни одной незаполненной подстановки —
    владелец увидел бы `__DOMAIN__` вместо адреса;
  • два случая различаются: сайт закрыт фильтром и сервис не входит в доступы;
  • адрес подставляется и обезвреживается;
  • без адреса владельца кнопка «обратиться» убирается, а не висит мёртвой.
"""
import re
import sys

sys.path.insert(0, "/app")

import dnsfilter                                   # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-46s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


dnsfilter.FILTERS.bot_link = "https://t.me/your_vpn_bot"

print("=== отдаётся верстанная страница, а не заглушка ===")
page = dnsfilter._render_block_page("10.13.13.36", None)
check("страница большая, значит настоящая", len(page) > 10000,
      "%d знаков" % len(page))
check("замок на месте", "lockbody" in page)
check("фон со сканером на месте", 'id="fx"' in page)
check("это не аварийная заглушка", "<h1>Закрыто</h1>" not in page)

print()
print("=== подстановки заполнены все до одной ===")
left = sorted(set(re.findall(r"__[A-Z_]+__", page)))
check("незаполненных нет", not left, ", ".join(left) or "—")

print()
print("=== случай «сервис не в доступах» ===")
check("адрес показан", "10.13.13.36" in page)
check("сказано, что сеть исправна", "сеть исправна" in page)
check("сказано про доступы ключа", "открыто вашему ключу" in page)

print()
print("=== случай «сайт закрыт фильтром» — текст другой ===")
filtered = dnsfilter._render_block_page("example.com", "ads")
check("адрес показан", "example.com" in filtered)
check("сказано про фильтр", "фильтр" in filtered)
check("тексты двух случаев различаются", filtered != page)
check("подстановок не осталось",
      not re.findall(r"__[A-Z_]+__", filtered))

print()
print("=== опасный адрес обезврежен ===")
evil = dnsfilter._render_block_page("<script>alert(1)</script>", None)
check("тег не попал в страницу как тег", "<script>alert(1)</script>" not in evil)
check("показан безопасно", "&lt;script&gt;" in evil)

print()
print("=== без адреса владельца кнопка убирается ===")
dnsfilter._page_cache = None
dnsfilter.FILTERS.bot_link = ""
no_link = dnsfilter._render_block_page("10.13.13.36", None)
check("мёртвой кнопки нет", 'class="cta"' not in no_link)
check("страница всё равно целая", len(no_link) > 9000, "%d знаков" % len(no_link))
check("подстановок не осталось", not re.findall(r"__[A-Z_]+__", no_link))

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

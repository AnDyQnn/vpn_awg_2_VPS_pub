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


dnsfilter.FILTERS.bot_link = "https://t.me/VPN_MONITOR_bot"

print("=== отдаётся верстанная страница, а не заглушка ===")
page = dnsfilter._render_block_page("10.13.13.36", None)
check("страница большая, значит настоящая", len(page) > 10000,
      "%d знаков" % len(page))
check("замок на месте", "lockbody" in page,
      "случай про доступы — замок, про фильтр — перечёркнутый глаз")
check("фон со сканером на месте", 'id="fx"' in page)
check("это не аварийная заглушка", "<h1>Закрыто</h1>" not in page)

print()
print("=== страница пригодна для телефона ===")
# Правила под узкий экран были и раньше, но без этой строки браузер телефона
# считает страницу свёрстанной под монитор и ужимает её целиком — media-запросы
# при этом не срабатывают вовсе.
check("есть viewport", 'name="viewport"' in page and "width=device-width" in page)
check("есть doctype", page.lstrip().lower().startswith("<!doctype html>"),
      "без него браузер переходит в режим совместимости")
check("язык страницы указан", 'lang="ru"' in page)
check("правила под узкий экран на месте", "max-width:560px" in page)
check("отступы учитывают вырез экрана", "safe-area-inset" in page)
check("страница не ездит вбок", "overflow-x:hidden" in page)
check("чужой шрифт не задерживает показ",
      'media="print"' in page,
      "страницу видят, когда что-то не открылось — ждать нельзя")

print()
print("=== подстановки заполнены все до одной ===")
left = sorted(set(re.findall(r"__[A-Z_]+__", page)))
check("незаполненных нет", not left, ", ".join(left) or "—")

print()
print("=== случай «сервис не в доступах» ===")
check("адрес показан", "10.13.13.36" in page)
# Тексты задал владелец: короткие и одинаковые на обеих страницах.
check("сказано, кто закрыл", "ограничен администратором" in page)
check("сказано, куда идти", "свяжитесь с поддержкой" in page)
# Номер приходит от обработчика запроса: он знает адрес клиента, а сама
# отрисовка — нет. Без него подстановка просто убирается.
check("без номера страница чистая", "__REF__" not in page)
with_ref = dnsfilter._render_block_page("10.13.13.36", None, "9395-570A")
check("номер показан, когда он есть", "9395-570A" in with_ref,
      "по нему человек и обращается в поддержку")
check("и подписан понятно", "Номер инцидента" in with_ref)

print()
print("=== случай «сайт закрыт фильтром» — текст другой ===")
filtered = dnsfilter._render_block_page("example.com", "ads")
check("адрес показан", "example.com" in filtered)
check("сказано про фильтр", "фильтр" in filtered)
check("категория показана плашкой", 'class="cat"' in filtered,
      "строкой текста она терялась")
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

# -*- coding: utf-8 -*-
"""Пул масок: вход принимает любое имя, человеку достаётся своё и навсегда.

Маска — домен, которым прикрывается вход. Одна на всех означает, что снаружи
трафик тридцати человек выглядит обращением к одному и тому же имени, а
однообразие — примета.

Пул устроен так: `dest` один, имён несколько. Проверено на живом узле, что
`avito.ru:443` отвечает на SNI каждого из пяти поддоменов и отдаёт под каждый
валидный сертификат — он с подстановкой.

Главное, что здесь проверяется: имя выбирается ПО ЧЕЛОВЕКУ, а не случайно. В
уже выданной ссылке имя зашито; если бы оно менялось при каждой пересборке
конфига, все старые ссылки перестали бы подключаться разом.
"""
import sys

sys.path.insert(0, "/app")

import xray                                        # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


print("=== пул у выбранной по умолчанию маски ===")
names = xray.mask_names(xray.DEFAULT_DEST)
print("  ", xray.DEFAULT_DEST, "->", ", ".join(names))
check("имён больше одного", len(names) > 1, "%d" % len(names))
check("сам домен в пуле", xray.DEFAULT_DEST in names,
      "иначе ссылка с ним перестала бы работать")
check("все имена — поддомены его же",
      all(n == xray.DEFAULT_DEST or n.endswith("." + xray.DEFAULT_DEST)
          for n in names),
      "сертификат с подстановкой покрывает только их")

print()
print("=== незнакомый домен не остаётся без имени ===")
check("отдаётся он сам", xray.mask_names("что-то.ru") == ["что-то.ru"])

print()
print("=== человеку достаётся своё имя — и всегда одно и то же ===")
people = ["uuid-%d" % n for n in range(40)]
picks = {p: xray.mask_for(xray.DEFAULT_DEST, p) for p in people}
check("выбор устойчив",
      all(xray.mask_for(xray.DEFAULT_DEST, p) == picks[p] for p in people),
      "иначе выданные ссылки отвалились бы при пересборке конфига")
check("выбранное имя из пула", set(picks.values()) <= set(names))

used = len(set(picks.values()))
print("   на 40 человек задействовано имён:", used, "из", len(names))
check("пул используется, а не одно имя", used > 1, "иначе смысла в нём нет")

print()
print("=== пул из одного имени ведёт себя разумно ===")
single = [d for d in xray.MASK_POOL if len(xray.MASK_POOL[d]) == 1]
if single:
    d = single[0]
    check("отдаётся единственное", xray.mask_for(d, "любой") == d, d)
else:
    print("   таких в списке нет — пропускаю")

print()
print("=== все домены в списке имеют пул и сами в нём есть ===")
for dest, pool in xray.MASK_POOL.items():
    check("%s в своём пуле" % dest, dest in pool, ", ".join(pool))

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

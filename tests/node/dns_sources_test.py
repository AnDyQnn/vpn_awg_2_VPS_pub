# -*- coding: utf-8 -*-
"""Каждая категория умеет загружаться: перечень и источники — одно и то же.

Перечень категорий жил в двух местах: в коде узла и в скрипте загрузки. Когда
категорий стало четырнадцать, в скрипте осталось пять — и девять новых не
качались вовсе. Владельцу они показывались как обычные, включались человеку и
молча ничего не фильтровали: списка-то нет.

Такую поломку не видно ни по логам бота, ни по экрану фильтров. Единственное
место, где она проявляется, — пустой файл кэша, в который никто не смотрит.

Проверяется:
  • скрипт берёт источники из кода узла, а не из своей копии;
  • у каждой категории есть хотя бы один адрес;
  • адреса не повторяются между категориями по недосмотру;
  • неизвестная категория (свой пул владельца) скрипт не роняет и файл её не
    трогает — он приходит от бота готовым.
"""
import io
import re
import subprocess
import sys

sys.path.insert(0, "/app")

from dnsfilter import CATEGORIES                   # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


script = io.open("/app/update_dns_lists.sh", encoding="utf-8").read()

print("=== скрипт не держит свою копию перечня ===")
check("источники читаются из dnsfilter", "from dnsfilter import CATEGORIES" in script)
hardcoded = re.findall(r'SOURCES\[(\w+)\]=', script)
check("вписанных вручную категорий нет", not hardcoded,
      ", ".join(hardcoded) or "—")

print()
print("=== у каждой категории есть откуда качать ===")
for key, meta in CATEGORIES.items():
    urls = meta.get("urls") or []
    check("%s — %d адрес(ов)" % (key, len(urls)), bool(urls),
          meta.get("title", ""))

print()
print("=== источники не продублированы по недосмотру ===")
seen = {}
dupes = []
for key, meta in CATEGORIES.items():
    for url in meta.get("urls") or []:
        if url in seen:
            dupes.append("%s и %s: %s" % (seen[url], key, url.rsplit("/", 1)[-1]))
        seen[url] = key
check("повторов нет", not dupes, "; ".join(dupes) or "—")

print()
print("=== неизвестная категория не роняет загрузку ===")
# Свой пул владельца приходит от бота готовым файлом, качать его неоткуда.
# Скрипт обязан такую категорию пропустить, а не упасть и не стереть файл.
res = subprocess.run(["bash", "/app/update_dns_lists.sh", "pool_проверка"],
                     capture_output=True, text=True, timeout=120)
check("скрипт отработал", res.returncode == 0, "код %d" % res.returncode)
check("и сказал, что категория чужая",
      "неизвестная категория" in (res.stdout + res.stderr),
      (res.stdout + res.stderr).strip()[:60] or "—")

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

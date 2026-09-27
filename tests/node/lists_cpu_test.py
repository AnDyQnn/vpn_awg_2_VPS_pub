# -*- coding: utf-8 -*-
"""Списки категорий не жгут процессор узла.

Что было: каждое переключение категории в боте заново скачивало и разбирало
ВСЕ включённые списки — сотни тысяч строк на каждую галочку, разбор шёл
внутри DNS-сервера. Десяток нажатий — процессор в потолке, DNS не отвечает,
сайты «не открываются».

Проверяется:
  • свежий список (моложе 12 часов) не перекачивается; старый — да;
  • плановое обновление (FORCE=1) качает и свежий;
  • разбор даёт готовый файл, повторная загрузка его не пересобирает;
  • обновлённый список пересобирается.
"""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, "/app")
import dnsfilter  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


CACHE = "/etc/amnezia/amneziawg/cache/dns"
os.makedirs(CACHE, exist_ok=True)

# Подставной curl: записывает, что его звали, и ничего не качает.
fake = tempfile.mkdtemp()
log = os.path.join(fake, "calls.log")
open(os.path.join(fake, "curl"), "w").write("#!/bin/sh\necho \"$@\" >> %s\nexit 1\n" % log)
os.chmod(os.path.join(fake, "curl"), 0o755)
env = dict(os.environ, PATH=fake + ":" + os.environ["PATH"])


def run(cats, force=False):
    if os.path.exists(log):
        os.remove(log)
    e = dict(env, FORCE="1" if force else "0")
    subprocess.run(["bash", "/app/update_dns_lists.sh", cats], env=e,
                   capture_output=True, text=True, timeout=60)
    return open(log).read().count("http") if os.path.exists(log) else 0


print("=== свежий список не перекачивается ===")
path = os.path.join(CACHE, "adult.txt")
open(path, "w").write("0.0.0.0 fresh.example\n" * 300)
check("свежий: скачиваний нет", run("adult") == 0)
old = time.time() - 13 * 3600
os.utime(path, (old, old))
check("старше 12 часов: качаем", run("adult") >= 1)
os.utime(path, None)
check("плановое (FORCE=1): качаем и свежий", run("adult", force=True) >= 1)

print("\n=== разбор — готовым файлом, отдельным процессом ===")
dnsfilter.CACHE_DIR = tempfile.mkdtemp()
p = os.path.join(dnsfilter.CACHE_DIR, "adult.txt")
open(p, "w").write("".join("0.0.0.0 s%d.example\n" % i for i in range(5000)))
f = dnsfilter.Filters()
f.clients = {"10.13.13.7": ["adult"]}
f._load_domains(sync=True)
binp = dnsfilter._bin_path("adult")
check("готовый файл лёг рядом", os.path.exists(binp))
check("категория работает", f.blocked("10.13.13.7", "s42.example") == "adult")
m1 = os.path.getmtime(binp)
time.sleep(1.1)
g = dnsfilter.Filters()
g.clients = {"10.13.13.7": ["adult"]}
g._load_domains(sync=True)
check("повторная загрузка не пересобирает", os.path.getmtime(binp) == m1)
check("и работает", g.blocked("10.13.13.7", "s4999.example") == "adult")

open(p, "a").write("0.0.0.0 later.example\n")
t = time.time() + 5
os.utime(p, (t, t))
g._load_domains(sync=True)
check("обновлённый список пересобран", g.blocked("10.13.13.7", "later.example") == "adult")

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")

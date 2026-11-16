# -*- coding: utf-8 -*-
"""Загрузка списков категорий: зеркало и смена источника.

- «основной|запасной»: основной не ответил — берётся с зеркала, один раз;
- свежий список повторно не качается;
- сменился источник категории (новая версия) — перекачивается сразу, а не
  через полсуток.
"""
import http.server
import os
import subprocess
import tempfile
import threading

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


root = tempfile.mkdtemp()
open(os.path.join(root, "a.txt"), "w").write("\n".join("ad%d.example" % i for i in range(300)))
open(os.path.join(root, "b.txt"), "w").write("\n".join("bd%d.example" % i for i in range(300)))
hits = []


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=root, **k)

    def log_message(self, *a):
        hits.append(self.path)


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d" % port

cache = tempfile.mkdtemp()
src = open("/app/update_dns_lists.sh", encoding="utf-8").read()


def run(urls, force="0"):
    # Источники подменяем: вместо чтения dnsfilter — наша строка.
    s = src.replace('CACHE_DIR="/etc/amnezia/amneziawg/cache/dns"', 'CACHE_DIR="%s"' % cache)
    start = s.index('SOURCES_RAW="$(python3')
    end = s.index('\n)"', start) + 3
    s = s[:start] + 'SOURCES_RAW="tcat %s"' % urls + s[end:]
    p = os.path.join(cache, "run.sh")
    open(p, "w").write(s)
    hits.clear()
    r = subprocess.run(["bash", p, "tcat"], capture_output=True, text=True,
                       env=dict(os.environ, FORCE=force), timeout=60)
    return r.stdout + r.stderr


print("=== основной молчит — берём с зеркала")
out = run("%s/missing.txt|%s/a.txt" % (base, base))
txt = open(os.path.join(cache, "tcat.txt")).read() if os.path.exists(os.path.join(cache, "tcat.txt")) else ""
check("список скачан с зеркала", "ad5.example" in txt, out.strip().splitlines()[-1] if out.strip() else "")
check("скачан один раз, без повторов", txt.count("ad5.example\n") == 1)
check("источник записан рядом", open(os.path.join(cache, "tcat.src")).read() == "%s/missing.txt|%s/a.txt" % (base, base))

print("=== повторный запуск — свежий список не качаем")
run("%s/missing.txt|%s/a.txt" % (base, base))
check("сеть не трогали", not hits, hits)

print("=== источник сменился — качаем сразу")
run("%s/b.txt" % base)
txt = open(os.path.join(cache, "tcat.txt")).read()
check("пришёл новый список", "bd5.example" in txt and "ad5.example" not in txt)

print("=== оба источника недоступны — кэш остаётся")
run("%s/x.txt|%s/y.txt" % (base, base), force="1")
txt = open(os.path.join(cache, "tcat.txt")).read()
check("прошлый список на месте", "bd5.example" in txt)

srv.shutdown()
print("\nВСЁ ПРОШЛО" if ok else "\nЕСТЬ ПРОВАЛЫ")

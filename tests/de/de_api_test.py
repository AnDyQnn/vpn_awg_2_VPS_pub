# -*- coding: utf-8 -*-
# ЗАПУСК: внутри контейнера агента
"""Договор агента Германии: кого пускать, что отвечать, когда всё сломалось.

Агент умеет перенастроить туннель, отдать конфиги и перезагрузить хост. Всё,
что здесь проверяется, уже ломалось на боевом узле хотя бы раз:

  • «жив ли» должен отвечать БЕЗ токена — сторож живёт на самом узле и токена
    не знает. Когда этой ручки не было, сторож решил, что агент мёртв, и
    перезапускал его по кругу;
  • всё остальное без токена отвечать не должно;
  • мастер пускается по адресу в туннеле и без токена — иначе в тот момент,
    когда токен выдаётся впервые, ноды применяют его не одновременно и связь
    рвётся на несколько секунд;
  • состояние туннеля должно отвечать «выключен», а не падать с ошибкой, когда
    интерфейса нет: на ошибку сторож среагирует лечением здорового.
"""
import os
import sys

os.environ["API_TOKEN"] = "secret-for-test"
sys.path.insert(0, "/app")

from fastapi.testclient import TestClient      # noqa: E402
import api                                     # noqa: E402

FLAGS = api.FLAGS_DIR
anon = TestClient(api.app)
master = TestClient(api.app, client=("10.13.13.1", 51820))
stranger = TestClient(api.app, client=("10.13.13.77", 51820))

ok = True


def check(name, got, want):
    global ok
    good = got == want
    ok = ok and good
    print("  %s %-46s %s" % ("•" if good else "ПРОВАЛ:", name,
                             got if good else "%s, ждали %s" % (got, want)))


print("=== «жив ли» отвечает без токена — этим живёт сторож ===")
check("/api/health без токена", anon.get("/api/health").status_code, 200)
check("тело ответа", anon.get("/api/health").json(), {"status": "ok"})

print()
print("=== остальное без токена закрыто ===")
for path in ("/api/system_stats", "/api/wg/status", "/api/logs", "/api/host/deploy_status"):
    check("%s без токена" % path, stranger.get(path).status_code, 401)
check("перезагрузка хоста без токена",
      stranger.post("/api/host/reboot").status_code, 401)

print()
print("=== с токеном пускает ===")
hdr = {"X-Api-Key": "secret-for-test"}
check("/api/wg/status с токеном",
      stranger.get("/api/wg/status", headers=hdr).status_code, 200)

print()
print("=== мастер пускается по адресу в туннеле, без токена ===")
check("/api/wg/status от 10.13.13.1", master.get("/api/wg/status").status_code, 200)
check("чужой адрес в туннеле не пускается",
      stranger.get("/api/wg/status").status_code, 401)

print()
print("=== туннеля нет: отвечаем «выключен», а не падаем ===")
r = master.get("/api/wg/status")
check("код ответа", r.status_code, 200)
check("состояние", r.json().get("status"), "offline")

print()
print("=== аудит: метка ставится, состояние читается ===")
for f in ("do_audit", "audit_report.json", "audit_status"):
    try:
        os.remove(os.path.join(FLAGS, f))
    except OSError:
        pass
check("до запуска", master.get("/api/host/audit_result").json().get("status"), "not_started")
check("запуск аудита", master.post("/api/host/audit").json().get("status"), "success")
check("метка на диске", os.path.exists(os.path.join(FLAGS, "do_audit")), True)

with open(os.path.join(FLAGS, "audit_status"), "w") as f:
    f.write("storage\n")
r = master.get("/api/host/audit_result").json()
check("пока идёт", r.get("status"), "running")
check("на каком этапе", r.get("step"), "storage")

with open(os.path.join(FLAGS, "audit_report.json"), "w") as f:
    f.write('{"host": []}')
check("когда готово", master.get("/api/host/audit_result").json().get("status"), "done")

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

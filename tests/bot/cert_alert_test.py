# -*- coding: utf-8 -*-
"""Сторож сертификата узла: когда тревожить владельца, а когда молчать."""
import json
import os
import sys
import tempfile
import time

sys.path.append("/app")
import handlers_pubsub as hps      # noqa: E402

D = tempfile.mkdtemp()
hps.STATE_FILE = os.path.join(D, "public_sub.json")
hps.CERT_FILE = os.path.join(D, "fullchain.pem")

FAIL = []


def case(name, cert, days, named, state="on", msg="", want_alert=False, want_in=""):
    if cert:
        open(hps.CERT_FILE, "w").write("x")
    elif os.path.exists(hps.CERT_FILE):
        os.remove(hps.CERT_FILE)
    json.dump({"state": state, "msg": msg, "named": named,
               "until": time.time() + days * 86400 if days is not None else 0},
              open(hps.STATE_FILE, "w"))
    got = hps.cert_problem()
    ok = bool(got) == want_alert and (not want_in or (got and want_in in got))
    print(("  ок   " if ok else "  ПЛОХО ") + name + ("" if ok else f" → {got!r}"))
    if not ok:
        FAIL.append(name)


case("сертификата нет — молчим", False, None, False)
case("на адрес, осталось 4 сут. — молчим", True, 4, False)
case("на адрес, осталось 1 сут. — тревога", True, 1, False, want_alert=True, want_in="не продлился")
case("на имя, осталось 60 сут. — молчим", True, 60, True)
case("на имя, осталось 15 сут. — тревога", True, 15, True, want_alert=True, want_in="на имя")
case("продление упало, срок ещё большой — тревога с причиной", True, 40, True,
     state="warning", msg="продлить не вышло: _acme-challenge не найден",
     want_alert=True, want_in="\\_acme")

print("\nВСЁ ПРОШЛО" if not FAIL else f"\nПРОВАЛЫ: {FAIL}")
sys.exit(1 if FAIL else 0)

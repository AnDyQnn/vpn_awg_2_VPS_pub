# -*- coding: utf-8 -*-
"""Резолвер не раздаёт адреса, до которых узел не доедет.

Владелец подключился с телефона: ключ принят, профиль применён, соединения до
узла доходят — и ничего не грузится. В журнале всего два соединения и ровно
ОДИН запрос к нашему DNS, после которого тишина.

Тишина объяснилась ответом. На `youtube.com` наш резолвер отдавал четыре
IPv4-записи и четыре IPv6 — потому что честно пересказывал ответ вышестоящего.
А выход у нас только по четвёрке: у узла нет ни маршрута по умолчанию для
IPv6, ни связи по нему вовсе, и Германия, через которую всё уходит, тоже
доступна только так.

Современный телефон, увидев IPv6-адрес, предпочитает его. Дальше тупик с обеих
сторон: через туннель узел такой адрес не вывезет, мимо туннеля это российская
сеть, где закрыто ровно то, ради чего VPN и поднимали. Снаружи выглядит как
«подключился, и ничего не работает» — и искать причину идут куда угодно, только
не в DNS.

Отвечать надо «имя есть, записей такого типа нет». Это то же самое, что видит
клиент у сайта без IPv6: он спокойно берёт четвёрку. Отказ (NXDOMAIN) здесь
недопустим — клиент примет его за «имени не существует» и не спросит A вовсе.
"""
import struct
import subprocess
import sys

sys.path.insert(0, "/app")

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


import importlib.util                                   # noqa: E402
spec = importlib.util.spec_from_file_location("dnsf", "/app/dnsfilter.py")
dnsf = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(dnsf)
except Exception as e:
    print("ПРОВАЛ: модуль не загрузился: %s" % e)
    sys.exit(1)


def question(name, qtype):
    qn = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    return (struct.pack("!HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
            + qn + struct.pack("!HH", qtype, 1))


def counts(ans):
    """(флаги, число ответов) из заголовка."""
    flags = struct.unpack("!H", ans[2:4])[0]
    return flags, struct.unpack("!H", ans[6:8])[0]


print("=== пустой успех на IPv6, а не отказ ===")
q = question("youtube.com", dnsf.AAAA)
qend = len(q)
ans = dnsf.build_no_records(q, qend)
flags, n = counts(ans)
check("ответ успешный", (flags & 0x000F) == 0,
      "код ответа %d; отказ клиент примет за «имени нет»" % (flags & 0x000F))
check("записей в ответе нет", n == 0, "записей %d" % n)
check("это ответ, а не запрос", bool(flags & 0x8000))
check("вопрос возвращён как был", ans[12:qend] == q[12:qend],
      "иначе клиент не свяжет ответ со своим запросом")
check("идентификатор совпал", ans[0:2] == q[0:2])

print()
print("=== IPv4 при этом отдаётся как раньше ===")
q4 = question("дом.vpn".encode("idna").decode() if False else "home.vpn", 1)
a4 = dnsf.build_a_response(q4, len(q4), 1, "10.13.13.7")
f4, n4 = counts(a4)
check("на A отвечаем адресом", n4 == 1, "записей %d" % n4)
check("адрес тот самый", a4[-4:] == bytes([10, 13, 13, 7]))

print()
print("=== заглушка снимается вместе с появлением IPv6 ===")
src = open("/app/dnsfilter.py", encoding="utf-8").read()
part = src[src.index("# IPv6 мы не отдаём"):][:1800]
check("сказано, почему не отдаём", "нет ни маршрута" in part)
check("сказано, когда снять", "появится настоящий IPv6" in part,
      "иначе заглушка переживёт причину и будет прятать рабочую связь")

print()
print("=== узел и правда без IPv6 (иначе чиним не то) ===")
r = subprocess.run("ip -6 route show default", shell=True,
                   capture_output=True, text=True)
check("маршрута по умолчанию для IPv6 нет", not (r.stdout or "").strip(),
      (r.stdout or "").strip()[:60] or "пусто")

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

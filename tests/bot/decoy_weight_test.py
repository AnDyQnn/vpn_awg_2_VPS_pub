# -*- coding: utf-8 -*-
"""У сайта-заглушки есть вес, и набран он как у настоящего сайта.

Зачем вес вообще. Сайт на полтора килобайта, через который круглые сутки льются
гигабайты, — несуразица, заметная именно при пассивном наблюдении: там смотрят
на соотношение объёма к тому, чем этот объём якобы порождён.

Но вес должен лежать в картинках, а не в самой странице, и это не хитрость, а
то, как устроен любой сайт. Отсюда обе проверки ниже, и вторая важнее первой:

  1. сайт целиком весит около десяти мегабайт;
  2. запрос корня по-прежнему отдаёт полтора килобайта — иначе каждый сканер
     заставлял бы узел с одним ядром отдать десять мегабайт, и мы стали бы
     усилителем для чужих затей.

И картинки должны быть настоящими: подделка из случайных байтов с расширением
.png развалилась бы при первой же проверке, а проверяют именно то, что
выглядит подозрительно.
"""
import os
import struct
import tempfile

os.environ.setdefault("DECOY_ASSET_DIR", tempfile.mkdtemp(prefix="decoy-"))

import decoy  # noqa: E402
import subscription as S  # noqa: E402


class FakeTransport:
    def __init__(self, port):
        self.port = port

    def get_extra_info(self, name):
        return ("127.0.0.1", self.port) if name == "sockname" else None


class FakeReq:
    def __init__(self, path="/", method="GET", headers=None):
        self.transport = FakeTransport(S.DECOY_PORT)
        self.path = path
        self.method = method
        self.headers = headers or {}


print("=== картинки собрались ===")
print("  файлов:", len(decoy.ASSETS))
assert decoy.ASSETS, "ни одной картинки — сайт остался невесомым"
total = sum(len(v[0]) for v in decoy.ASSETS.values())
print(f"  вес сайта: {total / 1048576:.1f} МБ")
assert 7 * 1048576 < total < 16 * 1048576, (
    f"вес {total / 1048576:.1f} МБ — договаривались про десять")

print("\n=== это настоящие PNG, а не мусор с расширением ===")
for name, (body, ctype, _mt) in sorted(decoy.ASSETS.items()):
    assert body[:8] == b"\x89PNG\r\n\x1a\n", f"{name}: это не PNG"
    w, h = struct.unpack(">II", body[16:24])
    assert w > 100 and h > 100, f"{name}: размеры {w}x{h}"
    assert body[-12:-4] == b"\x00\x00\x00\x00IEND"[:4] + b"IEND" or b"IEND" in body[-12:]
    assert ctype == "image/png"
    print(f"  {name}: {w}x{h}, {len(body) / 1048576:.1f} МБ")

print("\n=== ГЛАВНОЕ: корень остался лёгким ===")
# Если сюда уедет весь вес, каждый сканер будет стоить нам десять мегабайт.
r = S.decoy_reply(FakeReq("/"))
size = len(r.body or b"")
print(f"  корень отдаёт: {size} б")
assert size < 16384, (
    f"корень отдаёт {size} б — усилителем становиться нельзя, "
    f"вес должен лежать в картинках")
assert r.status == 200

print("\n=== страница ссылается на картинки ===")
page = (r.body or b"").decode("utf-8")
for name in decoy.ASSETS:
    assert name in page, f"на {name} никто не ссылается — вес недостижим"
print("  все файлы упомянуты в разметке: ок")

print("\n=== файлы отдаются как у живого сайта ===")
name = sorted(decoy.ASSETS)[0]
r = S.decoy_reply(FakeReq(name))
assert r.status == 200, f"файл не отдался: {r.status}"
assert r.content_type == "image/png"
etag = r.headers.get("ETag")
assert etag, "нет метки версии"
assert "max-age" in (r.headers.get("Cache-Control") or ""), "нет кэширования"
print(f"  {name}: 200, {len(r.body) / 1048576:.1f} МБ, метка {etag}")

print("\n=== повторный визит не стоит ничего ===")
r = S.decoy_reply(FakeReq(name, headers={"If-None-Match": etag}))
assert r.status == 304, f"повторный визит дал {r.status}, а не 304"
assert not (r.body or b""), "в ответе «не менялось» пришло тело"
print("  304 без тела: ок")

print("\n=== HEAD отдаёт заголовки без тела ===")
r = S.decoy_reply(FakeReq(name, method="HEAD"))
assert r.status == 200
assert not (r.body or b""), "на HEAD пришло тело"
assert r.headers.get("Content-Length"), "на HEAD нет размера"
print(f"  размер объявлен: {r.headers['Content-Length']} б")

print("\n=== несуществующий файл — обычная 404, а не выдача чего попало ===")
r = S.decoy_reply(FakeReq("/assets/img/нет-такого.png"))
assert r.status == 404, f"получили {r.status}"
print("  404: ок")

print("\n=== выйти за пределы списка нельзя ===")
# Разбора пути по частям нет вовсе, поэтому и выхода наверх быть не может.
for bad in ("/assets/../../etc/passwd", "/assets/img/../../../etc/hosts",
            "/assets/"):
    r = S.decoy_reply(FakeReq(bad))
    assert r.status == 404, f"{bad} дал {r.status}"
print("  попытки выйти наверх дают 404: ок")

print("\n=== картинки переживают перезапуск ===")
# У живого сайта файлы не меняются при каждом перезапуске сервера. Менялись бы —
# это была бы примета сама по себе.
before = {k: (len(v[0]), v[2]) for k, v in decoy.ASSETS.items()}
again = decoy._load_assets()
after = {k: (len(v[0]), v[2]) for k, v in again.items()}
print("  до:", sorted(before.values())[0], " после:", sorted(after.values())[0])
assert before == after, "после перезапуска файлы стали другими"
print("  те же файлы, те же метки времени: ок")

print("\nВСЁ ПРОШЛО")

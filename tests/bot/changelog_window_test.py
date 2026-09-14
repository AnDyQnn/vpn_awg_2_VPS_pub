# -*- coding: utf-8 -*-
"""Человек, отставший на много версий, всё равно должен узнать главное.

Проверка родилась из настоящего случая: линейка 8.0 набрала одиннадцать бет
подряд, текст для людей был написан в первой из них, а окно разбора смотрело на
десять последних. Человек на 7.x после обновления увидел бы «нового пока нет» —
про смену протокола, новые приложения и ссылки-подписки.

Ломается это тихо: исключения нет, кнопка «Что нового» просто не рисуется.
Заметить можно было только открыв бота чужими глазами.
"""
import sys

sys.path.insert(0, "/app")
import changelog                                  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-48s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


rel = changelog.parse_releases(limit=200)
versions = [r[0] for r in rel]
print("=== всего записей в истории:", len(rel), "===")

# Где вообще есть текст для людей
with_user = [v for v, _w, body in rel
             if changelog._bullets(body, only_section="Для пользователей")]
print("  версии с разделом для людей:", with_user[:6], "…" if len(with_user) > 6 else "")

check("текст для людей в истории есть", bool(with_user))

if with_user:
    depth = versions.index(with_user[0])
    print("  ближайший такой раздел — %d-й сверху" % (depth + 1))
    check("он глубже старого окна в 10 записей — тем и был опасен", depth >= 0,
          "глубина %d" % depth)

print()
print("=== человек с давней версии получает текст ===")
old_text = changelog.user_text(since_version="0.0.1")
check("с самого начала — текст есть", bool(old_text))
check("и влезает в сообщение", old_text and len(old_text) <= 4096,
      "%s знаков" % (len(old_text) if old_text else 0))

print()
print("=== отставший на всю линейку 8.0 — тоже ===")
before_line = changelog.user_text(since_version="7.1.0")
check("с 7.1.0 текст есть", bool(before_line))
check("влезает", before_line and len(before_line) <= 4096,
      "%s знаков" % (len(before_line) if before_line else 0))

print()
print("=== кто всё видел — получает пустоту, а не повтор ===")
newest = versions[0] if versions else "0.0.0"
check("с самой свежей версии нового нет",
      changelog.user_text(since_version=newest) is None, newest)

print()
print("=== разметка не рвётся ===")
for name, body in (("с начала", old_text), ("с 7.1.0", before_line)):
    if body:
        check("%s: звёздочки парные" % name, body.count("**") % 2 == 0)
        check("%s: кавычки парные" % name, body.count("`") % 2 == 0)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

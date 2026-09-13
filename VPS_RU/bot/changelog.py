# -*- coding: utf-8 -*-
"""«Что нового»: одна история изменений, два изложения.

Источник один — `CHANGELOG.md` в корне репозитория. Админу показываем последние три
версии целиком: он обновляет систему и должен видеть, что именно приехало. Человеку —
только накопленное с той версии, которую он видел в прошлый раз, и без технических
подробностей: ему важно, что поменялось на практике.

Отдельная кнопка нужна и админу тоже. Если проект кто-то скачает, догадаться, что
список изменений спрятан в клиентском режиме, невозможно.
"""
import os
import re

CHANGELOG_PATH = "/app/CHANGELOG.md"
SHOW_RELEASES = 3          # сколько версий показываем админу

# Разделы, которые человеку ничего не говорят: он не знает, что такое digest образа.
TECH_WORDS = (
    "digest", "iptables", "systemd", "docker", "compose", "api", "endpoint",
    "cron", "sql", "таблиц", "миграц", "контейнер", "демон", "образ",
)


def _read():
    if not os.path.exists(CHANGELOG_PATH):
        return ""
    with open(CHANGELOG_PATH, encoding="utf-8") as f:
        return f.read()


def parse_releases(limit=SHOW_RELEASES):
    """Разбирает файл на версии. Возвращает список: (версия, заголовок, строки тела)."""
    text = _read()
    if not text:
        return []

    releases = []
    current = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(\d+\.\d+\.\d+)\s*(?:—|-)?\s*(.*)$", line.strip())
        if m:
            if current:
                releases.append(current)
            current = (m.group(1), m.group(2).strip(), [])
            continue
        if current is not None:
            if line.startswith("## "):      # «Более ранние изменения» и прочее
                releases.append(current)
                current = None
                continue
            current[2].append(line)
    if current:
        releases.append(current)

    # чистим хвостовые пустые строки и разделители
    out = []
    for ver, when, body in releases[:limit]:
        while body and not body[-1].strip():
            body.pop()
        body = [b for b in body if b.strip() not in ("---", "***")]
        out.append((ver, when, body))
    return out


def admin_text(limit=SHOW_RELEASES):
    """Три последних версии целиком — как в файле, без пересказа."""
    releases = parse_releases(limit)
    if not releases:
        return "📄 История изменений пока пуста."

    parts = ["📄 **Что нового**", ""]
    for ver, when, body in releases:
        parts.append(f"**{ver}**" + (f" · {when}" if when else ""))
        for line in body:
            if line.startswith("### "):
                parts.append(f"_{line[4:].strip()}_")
            else:
                parts.append(line)
        parts.append("")
    return "\n".join(parts).strip()


def _bullets(body, only_section=None):
    """Собирает пункты списка целиком.

    Пункт может занимать несколько строк, и раньше бралась только первая — текст
    обрывался на полуслове. Здесь строки-продолжения приклеиваются к своему пункту.
    """
    out, current, in_section = [], None, only_section is None
    for raw in body:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("### "):
            title = stripped[4:].strip().lower()
            if only_section:
                in_section = title == only_section.lower()
            if current:
                out.append(current)
                current = None
            continue

        if not in_section:
            continue

        if stripped.startswith(("- ", "* ")):
            if current:
                out.append(current)
            current = stripped[2:].strip()
        elif current and stripped:
            current += " " + stripped
        elif not stripped and current:
            out.append(current)
            current = None
    if current:
        out.append(current)
    return out


def _plain(text):
    """Убирает разметку: человеку она ни к чему."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.strip()


def user_text(since_version=None):
    """Для человека: только накопленное с версии, которую он видел в прошлый раз.

    Если в записи есть раздел «Для пользователей» — берём его: это текст, написанный
    специально для людей. Если нет — отбираем пункты, где нет технических слов,
    чтобы человек не читал про digest образов и миграции таблиц.
    """
    releases = parse_releases(limit=10)
    if not releases:
        return None

    fresh = []
    for ver, when, body in releases:
        if since_version and _cmp(ver, since_version) <= 0:
            break
        fresh.append((ver, when, body))
    if not fresh:
        return None

    lines = ["✨ **Что изменилось**", ""]
    for ver, _when, body in fresh:
        items = _bullets(body, only_section="Для пользователей")
        if not items:
            items = [b for b in _bullets(body)
                     if not any(w in b.lower() for w in TECH_WORDS)]
        for item in items:
            lines.append(f"• {_plain(item)}")

    if len(lines) <= 2:
        return None
    lines.append("")
    lines.append(f"Версия: {fresh[0][0]}")
    return "\n".join(lines)


def _cmp(a, b):
    """Сравнение версий по трём числам."""
    pa = [int(x) for x in a.split(".")]
    pb = [int(x) for x in b.split(".")]
    return (pa > pb) - (pa < pb)


def repo_link():
    """Ссылка на репозиторий в конце списка изменений.

    ОСТОРОЖНО: в GIT_REPO может оказаться токен, если кто-то впишет его прямо в адрес.
    Вырезаем учётные данные и хвост .git, иначе токен уедет в рассылку пользователям.
    """
    raw = (os.getenv("GIT_REPO", "") or "").strip()
    if not raw:
        return None
    raw = re.sub(r"://[^/@]*@", "://", raw)     # логин:пароль@
    raw = re.sub(r"\.git$", "", raw)
    return raw if raw.startswith("http") else None

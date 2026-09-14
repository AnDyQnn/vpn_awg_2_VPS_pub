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
        # Суффикс вида -alpha.1 — часть номера: версия, которую катают на бою,
        # должна показываться в боте так же, как обычная.
        m = re.match(r"^##\s+(\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)\s*(?:—|-)?\s*(.*)$",
                     line.strip())
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


def _short(text, limit=95):
    """Первая фраза пункта без разметки.

    В changelog пункт устроен как «суть. Дальше почему именно так» — боту нужна
    только суть. Режем строго по концу предложения: по тире или точке с запятой
    фраза часто теряет смысл на противоположный."""
    s = _plain(text).strip()
    head = s.split(". ")[0]
    if 25 <= len(head) < len(s):
        s = head
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s.rstrip(" .")


def admin_text(limit=SHOW_RELEASES):
    """Три последних версии целиком — как в файле, без пересказа."""
    releases = parse_releases(limit)
    if not releases:
        return "📄 История изменений пока пуста."

    parts = ["📄 **Что нового**", ""]
    budget = 3500          # с запасом под подпись и ссылку на репозиторий
    used = len(parts[0])
    skipped = 0

    for ver, when, body in releases:
        head = f"**{ver}**" + (f" · {when}" if when else "")
        parts.append(head)
        used += len(head)
        for name, items in _by_section(body).items():
            items = [i for i in items if i.strip()]
            if not items:
                continue
            title = f"_{name}_"
            shown = 0
            for item in items:
                line = f"• {_short(item)}"
                # Место кончилось — дальше только считаем, что не поместилось:
                # обрывать текст на полуслове хуже, чем честно сказать сколько.
                if used + len(line) + len(title) > budget:
                    skipped += 1
                    continue
                if shown == 0:
                    parts.append(title)
                    used += len(title)
                parts.append(line)
                used += len(line)
                shown += 1
        parts.append("")

    if skipped:
        parts.append(f"_И ещё {skipped} пунктов — целиком в CHANGELOG.md._")
    return "\n".join(parts).strip()


def _by_section(body):
    """Пункты, разложенные по разделам, в порядке появления."""
    out, current = {}, ""
    for raw in body:
        line = raw.rstrip()
        if line.startswith("### "):
            current = line[4:].strip()
            out.setdefault(current, [])
            continue
        out.setdefault(current, [])
        if line.strip().startswith("- "):
            out[current].append(line.strip()[2:])
        elif out[current] and line.strip() and not line.strip().startswith(">"):
            out[current][-1] += " " + line.strip()
    return out


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
    # Окно должно покрывать всё, что новее виденного человеком, а не
    # фиксированное число записей. Линейка 8.0 набрала одиннадцать бет подряд,
    # и при окне в десять текст для людей, написанный в первой из них, вылетал:
    # человек на 7.x видел «нового пока нет» про смену протокола.
    #
    # Разбор дешёвый — это чтение одного файла, — а отсекаем всё равно по
    # номеру версии, так что лишние записи просто не дойдут до вывода.
    releases = parse_releases(limit=200)
    if not releases:
        return None

    fresh = []
    for ver, when, body in releases:
        if since_version and _cmp(ver, since_version) <= 0:
            break
        fresh.append((ver, when, body))
    if not fresh:
        return None

    # Совсем без ограничения человеку прилетела бы простыня за год. Берём
    # столько записей с текстом для людей, сколько влезает в одно сообщение,
    # начиная со свежих: старое он всё равно уже не помнит.
    fresh = fresh[:20]

    lines = ["✨ **Что изменилось**", ""]
    for ver, _when, body in fresh:
        # Только раздел, написанный для людей. Раньше при его отсутствии брались
        # все пункты, кроме «технических на вид», и человеку прилетало про экраны
        # админки и обходы проверок. Нет раздела — значит для него ничего нового.
        items = _bullets(body, only_section="Для пользователей")
        for item in items:
            lines.append(f"• {_short(item, 120)}")

    if len(lines) <= 2:
        return None
    lines.append("")
    lines.append(f"Версия: {fresh[0][0]}")
    return "\n".join(lines)


def _cmp(a, b):
    """Сравнение версий по трём числам, с поправкой на суффикс.

    На `7.1.0-alpha.1` прежний разбор падал с ValueError, исключение глушилось
    выше по стеку — и кнопка «Что нового» у клиента просто не появлялась.
    Предрелиз считаем МЛАДШЕ одноимённого релиза: 7.1.0-alpha.1 < 7.1.0."""
    def parts(v):
        base, _, suffix = str(v).partition("-")
        nums = []
        for chunk in base.split("."):
            try:
                nums.append(int(chunk))
            except ValueError:
                nums.append(0)
        while len(nums) < 3:
            nums.append(0)
        # релиз без суффикса старше любого предрелиза той же тройки
        return nums[:3], (1, "") if not suffix else (0, suffix)

    na, sa = parts(a)
    nb, sb = parts(b)
    if na != nb:
        return (na > nb) - (na < nb)
    return (sa > sb) - (sa < sb)


def fit(text: str, limit: int = 3900) -> str:
    """Подрезает текст под лимит Telegram, не разрывая разметку.

    Слепое text[:4000] оставляло незакрытую пару ** и сообщение не отправлялось
    вовсе — вместо длинного текста человек получал ошибку."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # отходим до конца последней целой строки
    nl = cut.rfind("\n")
    if nl > limit // 2:
        cut = cut[:nl]
    # и до состояния, когда парные метки снова парные
    for mark in ("**", "`", "__"):
        if cut.count(mark) % 2:
            pos = cut.rfind(mark)
            cut = cut[:pos]
    return cut.rstrip() + "\n\n…"


def repo_markdown():
    """Готовая ссылка для сообщения: подпись без подчёркиваний, адрес в скобках.

    Голый адрес слать нельзя — в имени репозитория подчёркивания, а Markdown
    считает их курсивом и рвёт ссылку на части."""
    url = repo_link()
    return f"[Исходный код на GitHub]({url})" if url else None


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

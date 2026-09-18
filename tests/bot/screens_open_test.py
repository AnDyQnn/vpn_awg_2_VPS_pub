# -*- coding: utf-8 -*-
"""Каждый экран администратора открывается, а не падает.

Владелец нажал «🧹 Фильтры» — и ничего не произошло. Экран падал с
UnboundLocalError: внутри функции переменной дали имя `titles`, совпавшее с
именем функции `titles()`, которую та же функция вызывает выше. Python решает
область видимости при разборе кода, а не при выполнении, — и вызов падал ВСЕГДА,
с первой строки.

Падал молча: бот ловит исключения обработчиков и не показывает их человеку.
Снаружи это выглядит как мёртвая кнопка.

Ни один тест этот экран не открывал — поэтому поломка и жила. Здесь
открываются все экраны, до которых можно дойти кнопкой без аргументов: не
проверяется, ЧТО на них написано, проверяется, что они вообще показываются.

Такая проверка ловит целый класс бед: опечатку в имени, забытый импорт,
переименованное поле базы, тень над функцией. Всё это valid Python, и заметно
только при открытии.
"""
import asyncio
import importlib
import io
import re
import sys
import traceback

sys.path.insert(0, "/app")

from database import db                            # noqa: E402

ok = True
opened = 0
skipped = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-46s %s" % ("•" if cond else "ПРОВАЛ:", name[:46], detail))


# Экраны, которые НЕ открываются, а делают. Их сюда пускать нельзя: проверка
# открытия не должна перезагружать ноды, рассылать людям сообщения или менять
# ключи. У каждого своя проверка, где действие разыграно осознанно.
ACTING = {
    "update_all": "обновляет обе ноды и рассылает людям предупреждение",
    "check_update": "запускает обновление мастера",
    "de_update": "запускает обновление Германии",
    "confirm_reboot": "перезагружает мастер",
    "de_confirm_reboot": "перезагружает Германию",
    "backup": "снимает копию",
    "de_backup": "снимает копию Германии",
    "restore": "разворачивает копию поверх живого",
    "maintenance_warn": "рассылка всем людям",
    "svc_tok_now": "меняет ключ панелей",
    "svc_tok_back": "откатывает ключ панелей",
    "psub_on": "открывает порт наружу",
    "psub_off": "закрывает подписку у всех",
    "bypass_notify_now": "рассылка всем людям",
}


class Msg:
    """Сообщение, каким его видит обработчик.

    Отвечать должно на всё, чем экраны правят себя: иначе неполнота заглушки
    читается как поломка экрана, а это ровно то, от чего мы тут уходим.
    """

    chat_id = 1
    message_id = 1
    text = ""
    reply_markup = None

    async def edit_text(self, *a, **k):
        return self

    async def edit_reply_markup(self, *a, **k):
        return self

    async def edit_caption(self, *a, **k):
        return self

    async def reply_text(self, *a, **k):
        return Msg()

    async def reply_photo(self, *a, **k):
        return Msg()

    async def delete(self, *a, **k):
        return None


class Q:
    """Заглушка кнопки: всё, к чему обработчики обращаются на экране."""

    def __init__(self):
        self.data = ""
        self.message = Msg()
        self.from_user = type("U", (), {"id": 1, "username": "admin"})()

    async def edit_message_text(self, *a, **k):
        return None

    async def edit_message_caption(self, *a, **k):
        return None

    async def edit_message_reply_markup(self, *a, **k):
        return None

    async def answer(self, *a, **k):
        return None

    async def delete_message(self, *a, **k):
        return None


class Bot:
    async def send_message(self, *a, **k):
        return Msg()

    async def send_photo(self, *a, **k):
        return Msg()

    async def send_document(self, *a, **k):
        return Msg()

    async def edit_message_text(self, *a, **k):
        return None

    async def delete_message(self, *a, **k):
        return None


class Upd:
    def __init__(self):
        self.callback_query = Q()
        self.effective_chat = type("C", (), {"id": 1})()
        self.effective_user = type("U", (), {"id": 1, "username": "admin"})()
        self.message = None


class Ctx:
    def __init__(self):
        self.user_data = {}
        self.bot = Bot()
        self.args = []
        self.application = type("A", (), {"bot": Bot()})()


def router_pairs():
    """Пары «кнопка → обработчик» прямо из роутера бота.

    Берём из исходника, а не списком руками: список руками устаревает молча, и
    новый экран в него никто не добавит.
    """
    src = io.open("/app/bot.py", encoding="utf-8").read()
    pat = re.compile(
        r'if data == "([a-z0-9_]+)":\s*await ([a-z_][a-z0-9_]*)\(update, context\)')
    return pat.findall(src)


async def main():
    await db.connect()
    pairs = router_pairs()
    check("роутер разобран", len(pairs) > 20, "экранов без аргументов: %d" % len(pairs))

    bot_mod = importlib.import_module("bot")
    global opened

    print()
    print("=== открываю каждый ===")
    broken = []
    for data, fname in sorted(set(pairs)):
        if data in ACTING:
            skipped.append((data, ACTING[data]))
            continue
        fn = getattr(bot_mod, fname, None)
        if fn is None:
            # Кнопка есть, обработчик написан, а имени в bot.py нет — нажатие
            # падает с NameError. Так и жила кнопка «Список копий»: её
            # забыли внести в список импорта.
            broken.append((data, fname, "имя не импортировано в bot.py"))
            continue
        if not asyncio.iscoroutinefunction(fn):
            skipped.append((data, "не корутина"))
            continue
        upd, ctx = Upd(), Ctx()
        upd.callback_query.data = data
        try:
            await fn(upd, ctx)
            opened += 1
        except Exception as e:
            # Узел в тестах не отвечает — обращения к нему законно не проходят.
            # Нас интересуют поломки самого экрана, а не отсутствие узла.
            text = "".join(traceback.format_exception_only(type(e), e)).strip()
            if isinstance(e, (OSError, ConnectionError)) or "Connect" in text:
                skipped.append((data, "нет узла"))
                continue
            broken.append((data, fname, text))

    for data, fname, text in broken:
        print("  ПРОВАЛ: %-24s %s" % (data, text[:90]))
    check("все экраны открылись", not broken,
          "открыто %d, пропущено %d" % (opened, len(skipped)))

    if skipped:
        print()
        print("  пропущены (не поломка): "
              + ", ".join("%s — %s" % s for s in skipped[:8]))


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

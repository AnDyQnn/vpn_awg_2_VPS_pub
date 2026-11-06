# -*- coding: utf-8 -*-
"""Команды из меню ☰ (/keys /status /support /help) и кнопки на их экранах.

Гоняется на заглушках Telegram. Проверяет не только «не упало», но и то, что
команда ведёт себя как кнопка: сбрасывает незаконченный ввод, убирает за собой
сообщение с командой и прежний экран, а новый экран запоминает как текущий.
"""
import asyncio
import sys
import traceback

# В конец, а не в начало: рядом с проверкой может лежать новый код.
sys.path.append("/app")
from database import db                       # noqa: E402
import bot as B                               # noqa: E402
import handlers_client as hc                  # noqa: E402

TG = 900000777
CHAT = TG


class Msg:
    _n = 1000

    def __init__(self, text=None, kb=None):
        Msg._n += 1
        self.message_id = Msg._n
        self.chat_id = CHAT
        self.text = text
        self.reply_markup = kb
        self.photo = None
        self.document = None

    async def edit_text(self, text=None, reply_markup=None, **kw):
        self.text, self.reply_markup = text, reply_markup
        return self


class Bot:
    def __init__(self):
        self.sent, self.deleted, self.edited = [], [], []

    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        m = Msg(text, reply_markup)
        self.sent.append(m)
        return m

    async def delete_message(self, chat_id=None, message_id=None, **kw):
        self.deleted.append(message_id)
        return True

    async def edit_message_text(self, text=None, chat_id=None, message_id=None, reply_markup=None, **kw):
        self.edited.append((message_id, text))
        m = Msg(text, reply_markup); m.message_id = message_id
        return m

    async def send_chat_action(self, *a, **k):
        return True

    async def get_chat(self, chat_id):
        class C: first_name = "Тест"
        return C()


class User:
    def __init__(self, uid=TG):
        self.id = uid

    first_name = "Тест"
    username = "kc_test"


class Chat:
    def __init__(self, cid=CHAT):
        self.id = cid
    type = "private"


class Query:
    def __init__(self, data, msg, bot):
        self.data, self.message, self._bot = data, msg, bot
        self.from_user = User()
        self.alerts = []

    async def answer(self, text=None, **kw):
        self.alerts.append(text)

    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        self.message.text, self.message.reply_markup = text, reply_markup
        self._bot.edited.append((self.message.message_id, text))
        return self.message


class Upd:
    def __init__(self, bot, msg=None, data=None, uid=TG):
        self.effective_user = User(uid)
        self.effective_chat = Chat(uid)
        self.message = msg
        self.callback_query = Query(data, msg, bot) if data else None


class Ctx:
    def __init__(self):
        self.bot = Bot()
        self.user_data = {}


def kb_rows(m):
    if not m or not m.reply_markup:
        return []
    return [[(b.text, b.callback_data) for b in row] for row in m.reply_markup.inline_keyboard]


FAIL = []


def check(cond, what):
    print(("  ок   " if cond else "  ПЛОХО ") + what)
    if not cond:
        FAIL.append(what)


async def press(ctx, msg, data):
    upd = Upd(ctx.bot, msg, data)
    try:
        await B.button_router(upd, ctx)
        return upd, None
    except Exception as e:
        return upd, e


async def main():
    await db.connect()
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'kc-%'")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('kc-Телефон','kc-1')")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('kc-Ноутбук','kc-2')")
    await db.link_user_telegram("kc-1", TG)
    await db.link_user_telegram("kc-2", TG)
    try:
        for cmd, fn in (("start", B.start), ("keys", hc.cmd_keys), ("status", hc.cmd_status),
                        ("support", hc.cmd_support), ("help", hc.cmd_help)):
            print(f"\n=== /{cmd} ===")
            ctx = Ctx()
            old_screen = Msg("старый экран")
            ctx.user_data["screen_at"] = (CHAT, old_screen.message_id)
            ctx.user_data["state"] = "awaiting_bypass_report"
            cmd_msg = Msg("/" + cmd)
            try:
                await fn(Upd(ctx.bot, cmd_msg), ctx)
            except Exception:
                traceback.print_exc()
                check(False, f"/{cmd} не упала")
                continue
            check(len(ctx.bot.sent) == 1, f"/{cmd} прислала один экран (прислано {len(ctx.bot.sent)})")
            screen = ctx.bot.sent[-1] if ctx.bot.sent else None
            check(ctx.user_data.get("state") is None, f"/{cmd} сбросила незаконченный ввод")
            check(cmd_msg.message_id in ctx.bot.deleted, f"/{cmd} убрала сообщение с командой")
            check(old_screen.message_id in ctx.bot.deleted, f"/{cmd} убрала прежний экран")
            check(screen is not None and ctx.user_data.get("screen_at") == (CHAT, screen.message_id),
                  f"/{cmd} запомнила новый экран как текущий")
            # Каждая кнопка экрана должна куда-то вести, а не в «...».
            for row in kb_rows(screen):
                for text, data in row:
                    if data in ("client_check_all",) or data.startswith(("check_conn_", "support_audit_")):
                        continue        # ходят в узел — проверяем ниже по одной
                    m = Msg(screen.text, screen.reply_markup)
                    upd, err = await press(ctx, m, data)
                    dead = upd.callback_query.alerts == ["..."]
                    check(err is None and not dead, f"/{cmd}: кнопка «{text}» ({data}) работает"
                          + (f" — {type(err).__name__}: {err}" if err else "") + (" — тупик" if dead else ""))

        # Владелец: /help не должен оставлять его главное меню живым рядом.
        print("\n=== /help у владельца ===")
        ctx = Ctx()
        menu = Msg("главное меню")
        B.state_data["active_menus"][int(B.ADMIN_ID)] = menu.message_id
        cmd_msg = Msg("/help")
        await hc.cmd_help(Upd(ctx.bot, cmd_msg, uid=int(B.ADMIN_ID)), ctx)
        check(menu.message_id in ctx.bot.deleted, "прежнее главное меню владельца убрано")
        check(int(B.ADMIN_ID) not in B.state_data["active_menus"], "и снято с перерисовки")
        check(len(ctx.bot.sent) == 1, "экран помощи прислан")

        # Кнопки, ходящие в узел: проверка связи и диагностика.
        print("\n=== кнопки диагностики ===")
        for data in ("check_conn_kc-1", "client_check_all", "support_audit_kc-1"):
            ctx = Ctx()
            m = Msg("экран")
            upd, err = await press(ctx, m, data)
            await asyncio.sleep(6)
            last = (ctx.bot.edited[-1][1] if ctx.bot.edited else "") or ""
            check(err is None, f"«{data}» не упала" + (f" — {type(err).__name__}: {err}" if err else ""))
            print("     последний текст:", last.replace("\n", " ")[:140])
    finally:
        await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
        await db.execute("DELETE FROM users WHERE uuid LIKE 'kc-%'")
        for t in list(B.state_data.get("bg_tasks", ())):
            t.cancel()

    print("\nИТОГ:", "ВСЁ ПРОШЛО" if not FAIL else f"проблем {len(FAIL)}")


asyncio.run(main())

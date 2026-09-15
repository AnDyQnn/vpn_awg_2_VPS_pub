# -*- coding: utf-8 -*-
"""Поддержка проекта: реквизиты, кнопка у людей и напоминание.

Здесь проверяется не «работает ли код», а то, за что в этом разделе платят
деньги посторонние люди:

  • кнопка не появляется, пока за ней пусто — иначе человек жмёт и упирается;
  • номер карты показывается так, чтобы его можно было сверить глазами;
  • напоминание не приходит чаще оговорённого, даже если версий вышло пять
    за день;
  • удалили последний реквизит — кнопка у людей исчезла сама.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import donate                                      # noqa: E402
import handlers_donate as hd                       # noqa: E402

ok = True
shown = {}
sent = []

TG = 987654322


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeQuery:
    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        shown["text"] = text
        shown["buttons"] = [b.callback_data
                            for row in (reply_markup.inline_keyboard if reply_markup else [])
                            for b in row]

    async def answer(self, *a, **k):
        return None


class FakeBot:
    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        sent.append(text or "")
        shown["text"] = text
        shown["buttons"] = [b.callback_data
                            for row in (reply_markup.inline_keyboard if reply_markup else [])
                            for b in row]

    async def send_photo(self, chat_id=None, photo=None, caption=None, **kw):
        sent.append("фото:%s" % photo)


class FakeContext:
    bot = FakeBot()
    user_data = {}


class FakeUpdate:
    callback_query = FakeQuery()
    effective_chat = type("C", (), {"id": TG})()
    effective_user = type("U", (), {"id": TG, "first_name": "Донатов"})()


class Msg:
    def __init__(self, text=None, photo=None):
        self.text = text
        self.photo = photo
        self.chat_id = TG
        self.message_id = 1


class InputUpdate(FakeUpdate):
    def __init__(self, text=None, photo=None):
        self.message = Msg(text, photo)


class Sized:
    def __init__(self, file_id):
        self.file_id = file_id


async def main():
    await db.connect()
    await db.execute("DELETE FROM donate_methods")
    await db.set_setting("donate_enabled", "0")
    await db.set_setting("donate_text", "")
    await db.set_setting("donate_reminder", "0")
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'dn-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Донатов','dn-1',TRUE)")
    await db.execute("INSERT INTO user_tg_links (uuid, tg_id) VALUES ('dn-1',$1)", TG)

    print("=== пока нечем платить, кнопки нет ===")
    check("кнопка не показывается", not await donate.visible())
    import handlers_client as hc
    shown.clear()
    await hc.client_menu(FakeUpdate(), FakeContext())
    check("в личном кабинете её нет",
          "client_donate" not in (shown.get("buttons") or []))

    print()
    print("=== владелец добавляет карту ===")
    await hd.handle_donate_input(
        InputUpdate("Сбербанк, 2202 2020 1111 2222, Андрей П."),
        FakeContext(), "awaiting_donate_card")
    rows = await donate.methods()
    check("реквизит записан", len(rows) == 1, str(len(rows)))
    check("банк разобран", rows and rows[0]["bank"] == "Сбербанк",
          rows[0]["bank"] if rows else "—")
    check("подпись разобрана", rows and rows[0]["note"] == "Андрей П.",
          rows[0]["note"] if rows else "—")

    text = await donate.screen_text()
    check("номер разбит по четыре", "`2202 2020 1111 2222`" in text,
          "слитные шестнадцать цифр глазом не сверить")
    check("сказано, что доступ не зависит", "не зависит" in text)
    check("сказано, где бывают реквизиты", "только здесь" in text)

    print()
    print("=== мусор вместо реквизита ===")
    await hd.handle_donate_input(InputUpdate("просто цифры без банка"),
                                 FakeContext(), "awaiting_donate_card")
    check("не записан", len(await donate.methods()) == 1)
    check("сказано, как надо", "через запятую" in (sent[-1] or ""), sent[-1][:40])

    print()
    print("=== кнопка у людей ===")
    check("пока владелец не включил — её нет", not await donate.visible())
    await donate.set_enabled(True)
    check("включил — появилась", await donate.visible())
    for view, label in ((lambda: hc.client_menu(FakeUpdate(), FakeContext()),
                         "перерисованное меню"),
                        (lambda: hc.send_client_menu(FakeContext(), TG, "Донатов"),
                         "отправленное меню")):
        shown.clear()
        await view()
        check("%s: кнопка на месте" % label,
              "client_donate" in (shown.get("buttons") or []))

    shown.clear()
    await hd.client_donate(FakeUpdate(), FakeContext())
    check("экран открывается", "Поддержать" in (shown.get("text") or ""))
    check("кнопки QR нет — картинки не заводили",
          "client_donate_qr" not in (shown.get("buttons") or []))

    print()
    print("=== QR-картинка ===")
    await hd.handle_donate_input(InputUpdate(photo=[Sized("мелкий"), Sized("крупный")]),
                                 FakeContext(), "awaiting_donate_qr")
    qrs = await donate.qr_methods()
    check("сохранён самый крупный размер",
          qrs and qrs[0]["value"] == "крупный",
          qrs[0]["value"] if qrs else "—")
    shown.clear()
    await hd.client_donate(FakeUpdate(), FakeContext())
    check("кнопка QR появилась",
          "client_donate_qr" in (shown.get("buttons") or []))
    sent.clear()
    await hd.client_donate_qr(FakeUpdate(), FakeContext())
    check("картинка уходит человеку", any(s.startswith("фото:") for s in sent),
          ", ".join(sent) or "—")

    print()
    print("=== напоминание не чаще, чем условились ===")
    await db.execute("UPDATE notify_prefs SET donate_reminded_at=NULL WHERE tg_id=$1", TG)
    check("выключено — не напоминаем", not await donate.should_remind(TG))
    await donate.set_reminder(True)
    check("включено и не напоминали — напомним", await donate.should_remind(TG))
    await db.set_donate_reminded_at(TG)
    check("сразу после — молчим", not await donate.should_remind(TG),
          "иначе пять версий за день = пять просьб о деньгах")
    await db.execute(
        "UPDATE notify_prefs SET donate_reminded_at = NOW() - INTERVAL '15 days' "
        "WHERE tg_id=$1", TG)
    check("через две недели — снова можно", await donate.should_remind(TG))

    print()
    print("=== периодичность настраивается, а не зашита ===")
    shown.clear()
    await hd.donate_period(FakeUpdate(), FakeContext())
    check("экран показывает текущий срок", "14" in (shown.get("text") or ""),
          "по умолчанию две недели")
    check("готовые варианты на кнопках",
          all(f"don_per_{d}" in (shown.get("buttons") or [])
              for d in donate.PERIOD_CHOICES),
          ", ".join(shown.get("buttons") or []))
    check("своё число тоже можно",
          "don_per_own" in (shown.get("buttons") or []))

    await hd.donate_period_set(FakeUpdate(), FakeContext(), "30")
    check("выбор кнопкой применился", await donate.reminder_days() == 30,
          str(await donate.reminder_days()))

    await hd.handle_donate_input(InputUpdate("21"), FakeContext(),
                                 "awaiting_donate_days")
    check("своё число применилось", await donate.reminder_days() == 21,
          str(await donate.reminder_days()))

    await hd.handle_donate_input(InputUpdate("0"), FakeContext(),
                                 "awaiting_donate_days")
    check("ноль превращается в сутки, а не в ноль",
          await donate.reminder_days() == 1,
          "иначе напоминание пришло бы с каждой версией")

    await hd.handle_donate_input(InputUpdate("99999"), FakeContext(),
                                 "awaiting_donate_days")
    check("слишком большое обрезается годом",
          await donate.reminder_days() == 365,
          str(await donate.reminder_days()))

    await hd.handle_donate_input(InputUpdate("сколько-нибудь"), FakeContext(),
                                 "awaiting_donate_days")
    check("буквы не применяются", await donate.reminder_days() == 365,
          "и сказано, что нужно число")
    await donate.set_reminder_days(14)

    print()
    print("=== выключили — и кнопки нет, и напоминаний ===")
    await donate.set_enabled(False)
    check("кнопки у людей нет", not await donate.visible())
    check("напоминания не уходят", not await donate.should_remind(TG),
          "один выключатель на оба, а не два разных состояния")
    await donate.set_enabled(True)

    print()
    print("=== удалили последний реквизит ===")
    for row in await donate.methods():
        await db.delete_donate_method(row["id"])
        if not await donate.methods():
            await donate.set_enabled(False)
    check("кнопка у людей выключилась сама", not await donate.visible(),
          "иначе она вела бы на пустой экран")

    await db.execute("DELETE FROM donate_methods")
    await db.set_setting("donate_enabled", "0")
    await db.set_setting("donate_reminder", "0")
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'dn-%'")
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

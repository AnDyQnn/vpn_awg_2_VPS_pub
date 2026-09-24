# -*- coding: utf-8 -*-
"""Экран «Протоколы» после того, как свой Xray убран.

Вход у узла один — AmneziaWG. Проверяется, что экран:
  • показывает состояние интерфейса, порт, пиров и параметры обфускации;
  • не даёт выключить AmneziaWG — узел остался бы без связи;
  • предлагает поднять интерфейс, если он лёг;
  • не падает, когда узел молчит;
  • ходит к узлу за статусом по новому адресу, а не по прежнему `/xray/status`.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

import handlers_protocols as HP                     # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def fake_show(query, context, text, reply_markup=None, **kw):
    shown["text"] = text
    shown["buttons"] = [b.callback_data for row in reply_markup.inline_keyboard
                        for b in row] if reply_markup else []


class Upd:
    callback_query = object()


HP.show_screen = fake_show

UP = {"awg": {"enabled": True, "up": True, "peers": 29, "port": 51820,
              "online": 12,
              "obfuscation": {"Jc": "4", "Jmin": "40", "Jmax": "70",
                              "S1": "0", "S2": "0", "H1": "1", "H2": "2",
                              "H3": "3", "H4": "4"}}}


async def main():
    print("=== интерфейс поднят ===")

    async def st_up():
        return UP
    HP.status = st_up
    await HP.protocols_menu(Upd(), None)
    text = shown["text"]
    check("назван AmneziaWG", "AmneziaWG" in text)
    check("порт на экране", "51820" in text)
    check("пиры и на связи", "29" in text and "12" in text)
    check("обфускация параметрами", "Jc=4" in text and "Jmax=70" in text)
    check("Xray не упоминается", "Xray" not in text)
    check("выключателя нет", not any("off" in b for b in shown["buttons"]),
          str(shown["buttons"]))
    check("есть выход в администрирование", "svc_menu" in shown["buttons"])

    print()
    print("=== интерфейс лёг ===")
    down = {"awg": dict(UP["awg"], up=False)}

    async def st_down():
        return down
    HP.status = st_down
    await HP.protocols_menu(Upd(), None)
    check("предлагает поднять", "proto_on_awg" in shown["buttons"],
          str(shown["buttons"]))
    check("и говорит, что опущен", "опущен" in shown["text"])

    print()
    print("=== узел молчит ===")

    async def st_err():
        return {"error": "timeout"}
    HP.status = st_err
    await HP.protocols_menu(Upd(), None)
    check("экран открылся", "не ответил" in shown["text"])
    check("строка сводки не падает",
          "не ответил" in HP.status_line({"error": "x"}))
    check("строка сводки при живом узле",
          "работает" in HP.status_line(UP))

    print()
    print("=== адрес статуса на узле ===")
    src = open("/app/handlers_protocols.py", encoding="utf-8").read()
    check("спрашивает /awg/status", "/awg/status" in src)
    check("прежнего /xray/status нет", "/xray/" not in src)


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

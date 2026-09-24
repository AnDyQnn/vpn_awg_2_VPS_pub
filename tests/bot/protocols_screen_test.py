# -*- coding: utf-8 -*-
"""Экран «Протоколы»: AmneziaWG и стек Xray (панель 3X-UI).

Проверяется, что экран:
  • показывает AmneziaWG — интерфейс, порт, пиров, обфускацию — и не даёт его
    выключить: это вход по умолчанию;
  • предлагает поднять интерфейс, если он лёг;
  • при выключенном Xray предлагает включить и говорит, что порты закрыты;
  • при включённом — сводку панели, выключатель и разделы: панель, её бот,
    маска, переезд;
  • не падает, когда узел или панель молчат;
  • ходит к узлу за статусом AmneziaWG по своему адресу.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")

import handlers_protocols as HP                     # noqa: E402
import xui                                          # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-56s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


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


async def st(value):
    return value


async def main():
    os.environ["XRAY_STACK"] = ""
    xui.status = lambda: st({"enabled": False, "panel": False, "inbound": None,
                             "people": 0, "online": 0})

    print("=== AmneziaWG работает, Xray выключен ===")
    HP.status = lambda: st(UP)
    await HP.protocols_menu(Upd(), None)
    text, buttons = shown["text"], shown["buttons"]
    check("назван AmneziaWG", "AmneziaWG" in text)
    check("порт на экране", "51820" in text)
    check("пиры и на связи", "29" in text and "12" in text)
    check("обфускация параметрами", "Jc=4" in text and "Jmax=70" in text)
    check("выключателя AmneziaWG нет", not any("off_awg" in b for b in buttons), str(buttons))
    check("Xray: сказано, что выключен и порты закрыты",
          "Выключен" in text and "443" in text)
    check("Xray: кнопка включить", "xr_on" in buttons, str(buttons))
    check("разделов панели при выключенном нет", "xr_panel" not in buttons)
    check("есть выход в администрирование", "svc_menu" in buttons)

    print()
    print("=== интерфейс лёг ===")
    HP.status = lambda: st({"awg": dict(UP["awg"], up=False)})
    await HP.protocols_menu(Upd(), None)
    check("предлагает поднять", "proto_on_awg" in shown["buttons"], str(shown["buttons"]))
    check("и говорит, что опущен", "опущен" in shown["text"])

    print()
    print("=== Xray включён ===")
    os.environ["XRAY_STACK"] = "xray"
    HP.status = lambda: st(UP)
    xui.status = lambda: st({"enabled": True, "panel": True, "people": 3, "online": 1,
                             "inbound": {"port": 443, "network": "tcp",
                                         "target": "www.ozon.ru:443", "enable": True}})
    await HP.protocols_menu(Upd(), None)
    text, buttons = shown["text"], shown["buttons"]
    check("вход и маска на экране", "443" in text and "www.ozon.ru" in text)
    check("люди и на связи", "Людей: 3" in text and "на связи: 1" in text)
    for b in ("xr_panel", "xr_bot", "xr_mask", "xr_move", "xr_off"):
        check("кнопка " + b, b in buttons)
    check("включить больше не предлагает", "xr_on" not in buttons)

    print()
    print("=== панель молчит ===")
    xui.status = lambda: st({"enabled": True, "panel": False, "people": 3, "online": 0,
                             "inbound": None})
    await HP.protocols_menu(Upd(), None)
    check("говорит, что панель не отвечает", "не отвечает" in shown["text"])
    check("выключатель остался", "xr_off" in shown["buttons"])

    print()
    print("=== узел молчит ===")
    HP.status = lambda: st({"error": "timeout"})
    await HP.protocols_menu(Upd(), None)
    check("экран открылся", "не ответил" in shown["text"])
    check("строка сводки не падает", "не ответил" in HP.status_line({"error": "x"}))
    check("строка сводки называет оба канала",
          "AmneziaWG работает" in HP.status_line(UP) and "Xray включён" in HP.status_line(UP))

    print()
    print("=== адреса на узле ===")
    src = open("/app/handlers_protocols.py", encoding="utf-8").read()
    check("статус AmneziaWG — /awg/status", "/awg/status" in src)
    check("прежнего /xray/status нет", "/xray/status" not in src)


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)

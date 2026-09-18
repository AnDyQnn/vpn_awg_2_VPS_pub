# -*- coding: utf-8 -*-
"""Подписи кнопок берутся из плоского конфига проекта.

Зачем. Переименовать кнопку значило залезть в код: найти нужный
`InlineKeyboardButton` среди восьмисот, поправить строку, собрать образ.
Занятие не для того момента, когда просто видишь, что слово неудачное. А слово
на кнопке — это и есть весь разговор бота с человеком.

Теперь между «вижу, что плохо» и «стало хорошо» стоит одна строка в
`config/buttons.json`:

    {"gen_key": "🔑 Новый ключ"}

Ключ — `callback_data`, то есть адрес нажатия; он постоянный и не зависит от
того, на каком экране кнопка нарисована. Значение — то, что увидит человек.
Файла нет или он пуст — всё как в коде.

Как это применяется ко ВСЕМ кнопкам сразу. Подписи расставлены по двадцати
файлам, и обходить их по одному значит гарантированно забыть половину. Поэтому
подменяем не места вызова, а сам конструктор кнопки: модули делают
`from telegram import InlineKeyboardButton` и получают один и тот же класс.
Поправив его однажды при запуске, мы накрываем и те экраны, которых ещё нет.

Чего конфиг НЕ умеет и не должен. Менять порядок кнопок и переносить их между
экранами. Порядок — это уже раскладка, она живёт в коде рядом с условиями
(«эту строку показываем только если есть Xray»), и плоским словарём её не
выразить. Карта такие правки показывает как предложение — переносить их в код
нужно руками и осознанно.
"""
import io
import json
import os

# Рядом с ботом его кладёт docker-compose: файл лежит в корне проекта, а образ
# собирается из папки bot, поэтому монтируется, а не копируется.
PATH = os.getenv("BUTTON_NAMES", "/app/buttons.json")

_names = {}


def load(path=None):
    """Читает конфиг. Возвращает, сколько подписей задано."""
    global _names
    src = path or PATH
    try:
        with io.open(src, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        _names = {}
        return 0
    except Exception as e:
        # Сломанный конфиг не должен ронять бота: без подписей он живой, без
        # бота не живёт ничего. Но и молчать нельзя — иначе владелец будет
        # думать, что правка применилась.
        print("Подписи кнопок: конфиг не разобран (%s) — работаем как в коде" % e)
        _names = {}
        return 0
    if not isinstance(raw, dict):
        print("Подписи кнопок: ожидался плоский словарь, получено другое")
        _names = {}
        return 0
    # Ключи, начинающиеся с подчёркивания, — пояснения для человека. В JSON
    # комментариев нет, а объяснить, что это за файл, надо прямо в нём.
    _names = {k: v for k, v in raw.items()
              if not k.startswith("_") and isinstance(v, str) and v.strip()}
    return len(_names)


def label_for(callback_data, default):
    """Подпись кнопки: из конфига, если задана, иначе как в коде."""
    if not callback_data:
        return default
    return _names.get(callback_data, default)


def apply():
    """Ставит подмену на конструктор кнопки. Зовётся один раз при запуске."""
    from telegram import InlineKeyboardButton as Btn

    if getattr(Btn, "_names_patched", False):
        return 0
    n = load()
    original = Btn.__init__

    def patched(self, text, *args, **kwargs):
        cd = kwargs.get("callback_data")
        if cd is None and len(args) >= 2:
            # Позиционный вызов: (text, url, callback_data, ...). В проекте так
            # не пишут, но ронять чужой вызов из-за этого незачем.
            cd = args[1]
        original(self, label_for(cd, text), *args, **kwargs)

    Btn.__init__ = patched
    Btn._names_patched = True
    return n

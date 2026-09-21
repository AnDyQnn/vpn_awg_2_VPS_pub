# -*- coding: utf-8 -*-
"""Конфиг, который собрал бот, принимает настоящий Xray.

Зачем это отдельным тестом. Проверки в боте смотрят на структуру: тот ли
порядок правил, там ли адрес, не утёк ли ключ. Всё это может быть стройно, а
Xray конфиг не примет — поле переименовали, версия не та, форма записи другая.
Тогда узел откатится на прежний конфиг, и выглядеть это будет как «кнопка не
работает».

Поэтому конфиг проверяется тем же двоичным файлом, который стоит на узле, и
той же командой, которой узел проверяет его перед применением.

Конфиги сюда кладёт тест бота (tests/bot/cascade_test.py) в общую папку.
Нет файлов — значит тест бота не гоняли; молчать об этом нельзя, иначе
проверка однажды перестанет проверять что-либо и никто не заметит.
"""
import json
import os
import subprocess

XRAY = "/usr/local/bin/xray"
OUT = "/out"
WANT = {
    "xray_plain.json": "узел без своего канала — прежнее поведение",
    "xray_cascade.json": "узел со своим каналом до Германии",
    "xray_bridge.json": "мост на стороне Германии",
}

assert os.path.exists(XRAY), "в образе нет Xray — проверять нечем"
print("версия:", subprocess.run([XRAY, "version"], capture_output=True,
                                text=True).stdout.splitlines()[0])

found = [n for n in WANT if os.path.exists(os.path.join(OUT, n))]
assert found, (
    "нет ни одного собранного конфига в /out — сначала прогоните "
    "tests/run.sh bot cascade_test.py, иначе эта проверка ничего не проверяет")

for name, what in WANT.items():
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        print(f"\n{name}: нет файла — пропускаю ({what})")
        continue

    print(f"\n=== {name} — {what} ===")
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    ins = [i.get("tag") for i in cfg.get("inbounds", [])]
    outs = [o.get("tag") for o in cfg.get("outbounds", [])]
    print("  входы:   ", ins or "нет")
    print("  каналы:  ", outs)

    res = subprocess.run([XRAY, "run", "-test", "-c", path],
                         capture_output=True, text=True, timeout=30)
    tail = (res.stderr or res.stdout or "").strip().splitlines()[-3:]
    for line in tail:
        print("   ", line)
    assert res.returncode == 0, (
        f"{name}: Xray не принял конфиг — на узле он откатился бы на прежний, "
        f"а владелец увидел бы молчащую кнопку")
    print("  принят: ок")

print("\nВСЁ ПРОШЛО")

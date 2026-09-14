# -*- coding: utf-8 -*-
"""Переезд: переписывание конфига и подсчёт отстающих. В прод не уезжает."""
import asyncio

import migration as mg

OLD = """[Interface]
PrivateKey = ABCDEF0123456789abcdef0123456789abcdef012345=
Address = 10.13.13.7/32
DNS = 1.1.1.1, 1.0.0.1
MTU = 1280
Jc = 4
Jmin = 40
Jmax = 70
S1 = 0
S2 = 0
H1 = 1
H2 = 2
H3 = 3
H4 = 4

[Peer]
PublicKey = OLDSERVERKEYoldserverkeyoldserverkeyoldserv=
Endpoint = 212.109.195.138:51820
AllowedIPs = 0.0.0.0/1, 128.0.0.0/2, ::/0
PersistentKeepalive = 25
"""

NEWOBF = {"Jc": 5, "Jmin": 50, "Jmax": 1000, "S1": 88, "S2": 136,
          "H1": 1148549232, "H2": 1584160764, "H3": 1215466561, "H4": 1861193563}
NEWKEY = "NEWSERVERKEYnewserverkeynewserverkeynewserv="


def main():
    out = mg.rewrite_config(OLD, NEWKEY, 51821, NEWOBF)
    print(out)

    # 1. Своё у человека не тронуто
    assert "PrivateKey = ABCDEF0123456789abcdef0123456789abcdef012345=" in out, \
        "приватный ключ клиента менять нельзя"
    assert "Address = 10.13.13.7/32" in out, "адрес в туннеле обязан остаться прежним"
    assert "DNS = 1.1.1.1, 1.0.0.1" in out and "MTU = 1280" in out
    assert "AllowedIPs = 0.0.0.0/1, 128.0.0.0/2, ::/0" in out, \
        "split-tunnel не должен переписываться"
    assert "PersistentKeepalive = 25" in out
    print("своё у клиента не тронуто: ок")

    # 2. Серверное заменено
    assert NEWKEY in out and "OLDSERVERKEY" not in out
    assert "Endpoint = 212.109.195.138:51821" in out, "порт должен смениться, адрес — нет"
    print("ключ сервера и порт заменены, хост тот же: ок")

    # 3. Обфускация новая и ровно по одному разу
    for key, val in NEWOBF.items():
        assert f"{key} = {val}" in out, f"{key} не обновился"
        assert out.count(f"\n{key} = ") == 1, f"{key} встречается дважды"
    assert "H1 = 1\n" not in out and "S1 = 0\n" not in out, "старая обфускация осталась"
    print("обфускация заменена и не задвоилась: ок")

    # 4. Параметров не было вовсе — должны появиться
    bare = OLD.replace("Jc = 4\nJmin = 40\nJmax = 70\nS1 = 0\nS2 = 0\n"
                       "H1 = 1\nH2 = 2\nH3 = 3\nH4 = 4\n", "")
    out2 = mg.rewrite_config(bare, NEWKEY, 51821, NEWOBF)
    for key, val in NEWOBF.items():
        assert f"{key} = {val}" in out2, f"{key} не добавился в конфиг без обфускации"
    assert out2.index("Jc = 5") < out2.index("[Peer]"), \
        "обфускация должна остаться в секции Interface"
    print("в конфиг без обфускации параметры добавляются в нужную секцию: ок")

    # 5. Идемпотентность: повторный прогон ничего не ломает
    out3 = mg.rewrite_config(out, NEWKEY, 51821, NEWOBF)
    assert out3 == out, "повторное переписывание изменило конфиг"
    print("повторный прогон ничего не меняет: ок")

    # 6. Конфиг остаётся разбираемым: одна секция Interface и одна Peer
    assert out.count("[Interface]") == 1 and out.count("[Peer]") == 1
    assert out.startswith("[Interface]"), "конфиг обязан начинаться с [Interface]"
    print("структура конфига цела: ок")

    print("\nВСЁ ПРОШЛО")


main()

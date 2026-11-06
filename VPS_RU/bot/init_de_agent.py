"""Ключ для узла в Германии (DE_AGENT) — один раз, при установке.

Выход 0 — файл конфига лежит в /volumes/DE_AGENT_CONFIG.txt и его можно
везти в Германию. Выход 1 — не вышло; install.sh повторяет, пока узел
поднимается, и громко пишет, если так и не получилось.

Раньше ошибка печаталась, а выход был нулевой: установка шла дальше, файла не
было, и узнавалось это только в Германии, где не с чем подключиться.
"""
import asyncio
import shutil
import sys

from database import db
from utils import CONFIGS_DIR, ROUTING_VERSION
from wireguard_manager import create_peer

DEST = "/volumes/DE_AGENT_CONFIG.txt"
SRC = CONFIGS_DIR / "DE_AGENT.conf"


async def main():
    print("Подключение к базе данных...")
    await db.connect()

    existing = await db.fetch_all("SELECT uuid FROM users WHERE name='DE_AGENT'")
    if existing:
        # Ключ уже заведён (повторный запуск установки или ручной повтор):
        # просто выкладываем его файлом ещё раз.
        if SRC.exists():
            shutil.copy(SRC, DEST)
            print(f"✅ Ключ DE_AGENT уже есть — конфиг выложен в {DEST}.")
            return 0
        print("❌ DE_AGENT есть в базе, но файла конфига "
              f"{SRC} нет. Удалите ключ DE_AGENT в боте и запустите снова.")
        return 1

    print("⏳ Генерация ключа DE_AGENT через API узла...")
    try:
        new_uid, c_path, _q = await create_peer("DE_AGENT", dns_type="classic")
        await db.execute(
            "INSERT INTO users (name, uuid, created_at, routing_version) "
            "VALUES ($1, $2, NOW(), $3)", "DE_AGENT", new_uid, ROUTING_VERSION)
        shutil.copy(c_path, DEST)
        print(f"✅ Ключ DE_AGENT создан и сохранён в {DEST}.")
        return 0
    except Exception as e:
        print(f"❌ Ошибка генерации DE_AGENT: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

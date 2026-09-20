import os
import hashlib
import shutil
import subprocess
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp

from utils import get_moscow_now, WG_API_URL, api_session
from database import db

BACKUP_DIR = Path("/volumes/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR = BACKUP_DIR / "archive"          # здесь лежат копии за прошлые дни
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_FILE = BACKUP_DIR / "backup_latest.tar.gz"
DB_URL = os.getenv("DATABASE_URL")

# Пароль архива. Живёт ТОЛЬКО в .env на хосте и НИКОГДА в базе: попав в базу, он
# оказался бы внутри того самого архива, который защищает — потеряв сервер, ты получил
# бы зашифрованную копию и пароль внутри неё. В архив .env не входит.
BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD", "").strip()

# Сколько копий держим. Раньше копия была ровно одна: файл перезаписывался, а в
# Telegram сообщение редактировалось на месте. Испортился архив — откатываться некуда.
KEEP_DAILY = 7          # ежедневные за неделю
KEEP_WEEKLY = 4         # воскресные за месяц
MIN_ARCHIVE_BYTES = 2048   # меньше — значит собралось что-то пустое


def password_tag():
    """Короткая метка пароля в имени файла. Пароль сменили — старые копии остались
    на старом, и по метке видно, каким из них какой архив открывать."""
    if not BACKUP_PASSWORD:
        return "plain"
    return "p" + hashlib.sha256(BACKUP_PASSWORD.encode()).hexdigest()[:8]


def _encrypt(src: Path) -> Path:
    """Симметричное шифрование стандартным gpg — чтобы архив можно было открыть
    руками одной командой, когда бота уже нет:
        gpg --batch --passphrase '<пароль>' -o backup.tar.gz -d backup.tar.gz.gpg
    """
    dst = Path(str(src) + ".gpg")
    proc = subprocess.run(
        ["gpg", "--batch", "--yes", "--symmetric", "--cipher-algo", "AES256",
         "--passphrase-fd", "0", "-o", str(dst), str(src)],
        input=BACKUP_PASSWORD.encode(), capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Шифрование не удалось: {proc.stderr.decode()[:200]}")
    src.unlink(missing_ok=True)
    return dst


def _decrypt(src: Path) -> Path:
    dst = BACKUP_DIR / "restore_plain.tar.gz"
    proc = subprocess.run(
        ["gpg", "--batch", "--yes", "--passphrase-fd", "0", "-o", str(dst), "-d", str(src)],
        input=BACKUP_PASSWORD.encode(), capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError("Не удалось расшифровать архив — не тот пароль?")
    return dst


def verify_archive(path: Path) -> tuple:
    """Проверка, что архив вообще читается. Раньше не проверялось ничего: могла
    накопиться неделя битых копий, и узнал бы ты об этом в худший момент."""
    try:
        if path.stat().st_size < MIN_ARCHIVE_BYTES:
            return False, f"архив подозрительно мал ({path.stat().st_size} байт)"
        if path.suffix == ".gpg":
            # Зашифрованный архив проверяем расшифровкой в память: без пароля gpg не
            # может даже перечислить содержимое, а «файл на месте и не пустой» —
            # это не проверка. Заодно убеждаемся, что пароль к архиву подходит.
            proc = subprocess.run(
                ["gpg", "--batch", "--passphrase-fd", "0", "--list-packets", str(path)],
                input=BACKUP_PASSWORD.encode(), capture_output=True)
            if proc.returncode != 0:
                return False, "не открывается текущим паролем или повреждён"
            return True, "ок, расшифровывается"
        with tarfile.open(path, "r:gz") as tar:
            names = tar.getnames()
        if not any(n.endswith("db_dump.sql") for n in names):
            return False, "в архиве нет дампа базы"
        return True, f"ок, файлов внутри: {len(names)}"
    except Exception as e:
        return False, f"не читается: {e}"


def _rotate():
    """Оставляем ежедневные за неделю и воскресные за месяц, остальное удаляем.
    Без этого ротация превратила бы диск в свалку — на немецкой ноде его всего 10 ГБ."""
    files = sorted(ARCHIVE_DIR.glob("backup_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    keep, now = set(), datetime.now()
    daily, weekly = 0, 0
    for f in files:
        when = datetime.fromtimestamp(f.stat().st_mtime)
        age_days = (now - when).days
        if age_days <= KEEP_DAILY and daily < KEEP_DAILY:
            keep.add(f)
            daily += 1
        elif when.weekday() == 6 and weekly < KEEP_WEEKLY and age_days <= KEEP_WEEKLY * 7:
            keep.add(f)
            weekly += 1
    removed = 0
    for f in files:
        if f not in keep:
            f.unlink(missing_ok=True)
            removed += 1
    return len(keep), removed


def create_backup():
    """Собирает архив, проверяет его, шифрует (если задан пароль) и чистит старые."""
    timestamp = get_moscow_now().strftime("%Y%m%d_%H%M%S")
    plain = BACKUP_DIR / f"backup_{timestamp}.tar.gz"
    db_dump = BACKUP_DIR / "db_dump.sql"

    try:
        if db_dump.exists():
            db_dump.unlink()
        subprocess.run(f"pg_dump --clean --if-exists -O -x '{DB_URL}' > {db_dump}",
                       shell=True, check=True)
        # Кэш списков фильтрации в архив НЕ идёт, и это не экономия ради
        # экономии. Там лежат публичные списки доменов — на живом узле это
        # двадцать шесть мегабайт в одной только категории «для взрослых», и
        # каждый архив таскал их с собой. Восстанавливать их бессмысленно:
        # узел скачивает списки сам при старте контейнера и дальше раз в
        # двенадцать часов, так что после восстановления они появятся всё
        # равно — но уже сегодняшние, а не из архива недельной давности.
        #
        # Всё остальное из wireguard остаётся: ключ сервера, конфигурации
        # пиров, раскладка имён, правила доступа — это не скачаешь ниоткуда.
        subprocess.run(
            f"tar -czf {plain} --exclude='wireguard/cache' "
            f"-C /volumes wireguard configs backups/db_dump.sql",
            shell=True, check=True)

        ok, why = verify_archive(plain)
        if not ok:
            plain.unlink(missing_ok=True)
            raise RuntimeError(f"Архив не прошёл проверку: {why}")

        final = _encrypt(plain) if BACKUP_PASSWORD else plain

        # свежая копия — под привычным именем, а история — в отдельной папке
        latest = Path(str(BACKUP_FILE) + (".gpg" if BACKUP_PASSWORD else ""))
        for old in BACKUP_DIR.glob("backup_latest.tar.gz*"):
            old.unlink(missing_ok=True)
        shutil.copy(final, latest)
        shutil.move(str(final), ARCHIVE_DIR / f"{final.name.replace('.tar', f'_{password_tag()}.tar')}")

        db_dump.unlink(missing_ok=True)
        _rotate()
        return str(latest)
    except Exception as e:
        print(f"❌ Бэкап не собрался: {e}")
        db_dump.unlink(missing_ok=True)
        plain.unlink(missing_ok=True)
        raise


def list_backups():
    """Список копий с результатом проверки — для экрана бэкапов в админке."""
    out = []
    for f in sorted(ARCHIVE_DIR.glob("backup_*"), key=lambda p: p.stat().st_mtime, reverse=True):
        ok, why = verify_archive(f)
        out.append({
            "name": f.name,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
            "when": datetime.fromtimestamp(f.stat().st_mtime),
            "ok": ok,
            "note": why,
        })
    return out


async def fetch_de_backup(de_url: str, timeout: int = 20):
    """Бэкап немецкой ноды. Ручка у агента была всегда, но по расписанию её никто
    не дёргал — конфиги агента не сохранялись вообще."""
    dst = ARCHIVE_DIR / f"de_agent_{get_moscow_now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
    async with api_session() as session:
        async with session.get(f"{de_url}/backup", timeout=timeout) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Агент ответил {resp.status}")
            dst.write_bytes(await resp.read())
    # держим столько же копий агента, сколько и своих ежедневных
    older = sorted(ARCHIVE_DIR.glob("de_agent_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in older[KEEP_DAILY:]:
        f.unlink(missing_ok=True)
    return str(dst)


async def test_restore(sample: Path = None):
    """Пробное восстановление дампа в отдельную базу. Архив, который читается,
    ещё не значит архив, из которого можно подняться."""
    target = sample or Path(str(BACKUP_FILE) + (".gpg" if BACKUP_PASSWORD else ""))
    if not target.exists():
        return False, "нет свежего архива"

    work = _decrypt(target) if target.suffix == ".gpg" else target
    tmp_dir = BACKUP_DIR / "verify"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(f"tar -xzf {work} -C {tmp_dir} backups/db_dump.sql",
                       shell=True, check=True)
        dump = tmp_dir / "backups" / "db_dump.sql"
        probe = "vpn_restore_probe"
        base_url = DB_URL.rsplit("/", 1)[0]
        subprocess.run(f"psql '{base_url}/postgres' -c 'DROP DATABASE IF EXISTS {probe}'",
                       shell=True, check=True, capture_output=True)
        subprocess.run(f"psql '{base_url}/postgres' -c 'CREATE DATABASE {probe}'",
                       shell=True, check=True, capture_output=True)
        r = subprocess.run(f"psql '{base_url}/{probe}' < {dump}",
                           shell=True, capture_output=True)
        users = subprocess.run(
            f"psql '{base_url}/{probe}' -t -c 'SELECT COUNT(*) FROM users'",
            shell=True, capture_output=True, text=True).stdout.strip()
        subprocess.run(f"psql '{base_url}/postgres' -c 'DROP DATABASE IF EXISTS {probe}'",
                       shell=True, capture_output=True)
        if r.returncode != 0:
            return False, "дамп не накатывается"
        return True, f"дамп восстановился, пользователей в копии: {users or '?'}"
    except Exception as e:
        return False, f"проверка не удалась: {e}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if work != target:
            Path(work).unlink(missing_ok=True)


async def restore_backup(path: str):
    """Восстановление. Перед накатом делаем снимок текущего состояния: раньше
    распаковка шла поверх живых томов, и падение на середине оставляло систему
    в смешанном состоянии без пути назад."""
    src = Path(path)
    print(f"♻️ Восстановление из {src.name}…")

    safety = None
    try:
        safety = ARCHIVE_DIR / f"before_restore_{get_moscow_now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        subprocess.run(f"tar -czf {safety} --exclude='wireguard/cache' "
                       f"-C /volumes wireguard configs",
                       shell=True, check=True)
        print(f"🛟 Снимок до восстановления: {safety.name}")
    except Exception as e:
        print(f"⚠️ Снимок до восстановления не сделан: {e}")

    work = _decrypt(src) if src.suffix == ".gpg" else src
    ok, why = verify_archive(work)
    if not ok:
        raise RuntimeError(f"Архив непригоден: {why}")

    subprocess.run(f"tar -xzf {work} -C /volumes/ --overwrite", shell=True, check=True)

    db_dump = BACKUP_DIR / "db_dump.sql"
    if db_dump.exists():
        print("♻️ Восстанавливаю базу…")
        if db.pool:
            await db.pool.close()
            db.pool = None
        try:
            subprocess.run(f"psql '{DB_URL}' < {db_dump}", shell=True, check=True)
        finally:
            await db.connect()
        db_dump.unlink()
    else:
        print("⚠️ В архиве не найден дамп базы.")

    if work != src:
        Path(work).unlink(missing_ok=True)

    print("♻️ Перезагружаю интерфейсы WireGuard…")
    try:
        async with api_session() as session:
            async with session.post(f"{WG_API_URL}/reload", timeout=10) as resp:
                print("✅ WireGuard перезапущен." if resp.status == 200
                      else f"❌ Ошибка перезапуска: {await resp.text()}")
    except Exception as e:
        print(f"❌ Панель недоступна при восстановлении: {e}")

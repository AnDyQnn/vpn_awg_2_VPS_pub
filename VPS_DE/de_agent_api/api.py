import json
import os
import subprocess
import time
import psutil
import tarfile
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

# --- ДОСТУП К API ---
# Агент умеет перенастроить туннель, отдать конфиги и перезагрузить хост, а порт 8000
# смотрит в туннель — то есть был доступен любому пиру. Закрыто двумя рубежами:
#   1) правила файрвола в run_api.sh (пускают только мастера 10.13.13.1);
#   2) общий токен ниже.
# Токен необязателен: без него агент работает как раньше, чтобы обновление не рвало связь
# мастера с агентом, если .env на одной из нод обновили позже.
API_TOKEN = os.getenv("API_TOKEN", "").strip()
# Предыдущий ключ. Смена идёт не мгновенно: пока новый доезжает до второй ноды,
# на ней ещё старый. Признавая оба, мы убираем окно, в котором ноды спорят о
# том, какой ключ правильный, — и заодно получаем запасной выход.
API_TOKEN_PREV = os.getenv("API_TOKEN_PREV", "").strip()


MASTER_IP = "10.13.13.1"

# Пути, которые отвечают без токена. Здесь только проверка «жив ли» — она не
# отдаёт ничего, чего не видно снаружи по самому факту ответа, зато нужна
# сторожу, который следит за узлом изнутри и токена не знает.
OPEN_PATHS = {"/api/health"}


def verify_token(request: Request):
    if request.url.path in OPEN_PATHS:
        return
    if not API_TOKEN:
        return
    sent = request.headers.get("X-Api-Key", "")
    if sent == API_TOKEN:
        return
    # Прошлый ключ действует, пока новый не разошёлся по обеим нодам.
    if API_TOKEN_PREV and sent == API_TOKEN_PREV:
        return
    # Запросы с адреса мастера принимаем и без токена.
    #
    # Это не послабление: адрес в туннеле привязан к ключу самим WireGuard, подделать
    # его нельзя, а порт и так закрыт файрволом для всех, кроме мастера. Зато снимается
    # проблема очерёдности: когда токен выдаётся впервые, ноды применяют его не
    # одновременно, и без этой поблажки агент начал бы отвергать мастера на те
    # несколько секунд, пока тот пересоздаёт контейнеры.
    client = request.client.host if request.client else ""
    if client == MASTER_IP:
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI(dependencies=[Depends(verify_token)])

if not API_TOKEN:
    print("⚠️  API_TOKEN не задан — агент защищён только правилами файрвола.")

CONF_DIR = "/etc/amnezia/amneziawg"
CONF_FILE = f"{CONF_DIR}/wg0.conf"
FLAGS_DIR = "/volumes/flags"

os.makedirs(CONF_DIR, exist_ok=True)
os.makedirs(FLAGS_DIR, exist_ok=True)

class ConfigData(BaseModel):
    config_text: str

def run_cmd(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode().strip() if e.stderr else str(e)
        raise RuntimeError(err_msg)

# ----------------- УПРАВЛЕНИЕ WIREGUARD -----------------

@app.post("/api/wg/config")
def update_wg_config(data: ConfigData):
    try:
        # ВАЖНО: Удаляем строку DNS, чтобы wg-quick не крашился в Docker (где нет resolvconf)
        cleaned_config = "\n".join([line for line in data.config_text.splitlines() if not line.strip().startswith("DNS")])
        
        with open(CONF_FILE, "w") as f:
            f.write(cleaned_config)
        return {"status": "success", "message": "Config saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ServerChange(BaseModel):
    server_pubkey: str
    port: int
    obfuscation: dict = {}


OBF_KEYS = ("Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4")


def _append_missing(out, seen, obfuscation):
    """Недостающие параметры — в конец секции, до пустых строк."""
    tail = []
    while out and not out[-1].strip():
        tail.append(out.pop())
    for key in OBF_KEYS:
        if key not in seen and key in obfuscation:
            out.append(f"{key} = {obfuscation[key]}")
    out.extend(reversed(tail))


def _rewrite_server(text, server_pubkey, port, obfuscation):
    """Меняет в своём конфиге ровно три вещи: ключ сервера, порт и обфускацию.

    Приватный ключ этого узла и его адрес остаются на месте — иначе мастер
    перестал бы узнавать агента, и переезд превратился бы в переустановку.
    Логика намеренно повторяет ту, что применяется к клиентским конфигам:
    один и тот же смысл должен работать одинаково на обоих концах."""
    out, section, seen = [], "", set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            if section == "Interface":
                _append_missing(out, seen, obfuscation)
            section = stripped.strip("[]")
            out.append(line)
            continue
        key = stripped.split("=")[0].strip()
        if section == "Interface" and key in OBF_KEYS:
            if key in obfuscation:
                out.append(f"{key} = {obfuscation[key]}")
                seen.add(key)
            continue
        if section == "Peer" and key == "PublicKey":
            out.append(f"PublicKey = {server_pubkey}")
            continue
        if section == "Peer" and key == "Endpoint":
            host = stripped.split("=", 1)[1].strip().rsplit(":", 1)[0]
            out.append(f"Endpoint = {host}:{port}")
            continue
        out.append(line)
    if section == "Interface":
        _append_missing(out, seen, obfuscation)
    return "\n".join(out).strip() + "\n"


@app.post("/api/wg/server")
def update_server(data: ServerChange):
    """Переводит агента на новый ключ и порт мастера."""
    try:
        if not os.path.exists(CONF_FILE):
            raise Exception("wg0.conf not found")
        with open(CONF_FILE) as f:
            current = f.read()
        # Копия ДО правки: если новый интерфейс мастера не заработает, агент
        # должен уметь вернуться, а не остаться отрезанным.
        with open(CONF_FILE + ".bak", "w") as f:
            f.write(current)
        with open(CONF_FILE, "w") as f:
            f.write(_rewrite_server(current, data.server_pubkey, data.port,
                                    data.obfuscation or {}))
        return reload_wg()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wg/rollback")
def rollback_server():
    """Возврат к прошлому конфигу — на случай неудачного переезда."""
    try:
        if not os.path.exists(CONF_FILE + ".bak"):
            raise Exception("копии конфига нет")
        with open(CONF_FILE + ".bak") as f:
            prev = f.read()
        with open(CONF_FILE, "w") as f:
            f.write(prev)
        return reload_wg()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wg/reload")
def reload_wg():
    try:
        # Мягко гасим старый интерфейс
        subprocess.run("wg-quick down wg0", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("ip link delete wg0", shell=True, stderr=subprocess.DEVNULL)
        
        if not os.path.exists(CONF_FILE):
            raise Exception("wg0.conf not found. Upload it first.")
        
        # Поднимаем туннель
        run_cmd("wg-quick up wg0")
        
        # Включаем NAT (Маскарадинг) для выпуска трафика из туннеля в интернет Германии
        run_cmd("iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE")

        # MSS clamping: туннель wg0 имеет MTU 1280. Подрезаем MSS в TCP-рукопожатии под
        # реальный PMTU, чтобы полноразмерные пакеты из интернета Германии не терялись на
        # входе в туннель при заблокированном ICMP (фикс «интернет тупит» на крупных
        # передачах — дублирует защиту на RU, закрывая ногу DE↔интернет). Идемпотентно:
        # reload не флашит правила, поэтому добавляем только если правила ещё нет.
        run_cmd("iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null || iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu")

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wg/status")
def wg_status():
    try:
        output = subprocess.check_output("wg show wg0", shell=True).decode().strip()
        return {"status": "online", "details": output}
    except Exception:
        return {"status": "offline", "details": "Interface wg0 is down"}

# ----------------- СИСТЕМНЫЙ МОНИТОРИНГ И УПРАВЛЕНИЕ -----------------

# --- XRAY: ВТОРОЙ КОНЕЦ ЦЕПОЧКИ -------------------------------------------
# Зачем он здесь. Раньше мировой трафик обоих каналов — и амнезии, и Xray —
# уходил из России по одному туннелю: этот узел висел обычным пиром на том
# интерфейсе, где живут клиенты мастера. Два канала были на деле одним, и
# выключение амнезии оставляло Xray без выхода.
#
# Теперь у каждого канала свой путь до Германии и своя маскировка: амнезия
# идёт амнезией, Xray — своим же VLESS. Снаружи второй участок выглядит как
# обычное исходящее HTTPS-соединение сервера к сайту, а не как туннель.
#
# Узел здесь ничего не решает: конфиг целиком собирает мастер, у которого база.
# Дело агента — записать, проверить, запустить и доложить.
XRAY_BIN = "/usr/local/bin/xray"
# Общий том с контейнером моста. Агент сюда только КЛАДЁТ конфиг и ЧИТАЕТ
# состояние; процесс живёт в соседнем контейнере и агенту не подчиняется — в
# этом и смысл разделения.
XRAY_DIR = "/etc/xray"
XRAY_CONF = f"{XRAY_DIR}/xray.json"
XRAY_STATUS = f"{XRAY_DIR}/status.json"
XRAY_LOG = f"{XRAY_DIR}/xray.log"
# Потолок памяти средствами самого рантайма Go. Жёсткий предел по адресному
# пространству тут не работает: Xray резервирует больше гигабайта, а занимает
# десятки мегабайт, и предел просто не дал бы процессу запуститься.
XRAY_MEM_LIMIT = os.getenv("XRAY_MEM_LIMIT", "192MiB")


def xray_state():
    """Состояние моста — из файла, который пишет его контейнер.

    Своего процесса у агента больше нет: мост живёт отдельно и переживает
    перезапуск агента. Узнать о нём можно только тем, что он сам о себе
    записал."""
    try:
        with open(XRAY_STATUS) as f:
            return json.load(f)
    except Exception:
        return {}


def xray_running():
    st = xray_state()
    if not st:
        return False
    # Состояние протухло — контейнер моста не работает вовсе. Иначе упавший
    # контейнер выглядел бы вечно живым по последней записи.
    if time.time() - int(st.get("checked_at") or 0) > 60:
        return False
    return bool(st.get("running"))


def xray_check(path):
    """Проверяет конфиг силами самого Xray, ничего не запуская.

    Проверяем ЗДЕСЬ, до записи в общий том: ошибку генератора надо поймать до
    того, как мост увидит файл, — тогда он даже не станет перезапускаться.
    Вторая такая же проверка есть и у моста: он не обязан верить нам на слово,
    а мы не обязаны надеяться, что он проверит."""
    try:
        res = subprocess.run([XRAY_BIN, "run", "-test", "-c", path],
                             capture_output=True, text=True, timeout=20)
    except Exception as e:
        return False, f"проверка не выполнилась: {e}"
    if res.returncode == 0:
        return True, "конфиг корректен"
    return False, (res.stderr or res.stdout or "").strip()[:400]


class XrayConfig(BaseModel):
    config: dict
    # Порт входа: под него открывается дверь. Мастер знает, какой прислал.
    port: int = 443


@app.post("/api/xray/apply")
def xray_apply(data: XrayConfig):
    """Принимает конфиг от мастера и кладёт его мосту.

    Запускать ничего не нужно: мост в соседнем контейнере сам заметит, что файл
    изменился, проверит его ещё раз и поднимется. Битый конфиг он не возьмёт и
    останется работать на прежнем — поэтому связь не рвётся из-за опечатки в
    генераторе."""
    try:
        os.makedirs(XRAY_DIR, exist_ok=True)
        tmp = XRAY_CONF + ".new"
        with open(tmp, "w") as f:
            json.dump(data.config, f, indent=2)

        ok, why = xray_check(tmp)
        if not ok:
            os.remove(tmp)
            raise HTTPException(status_code=400, detail=f"конфиг не принят: {why}")

        # Подменяем одним движением: мост может читать файл в этот самый миг,
        # и половинчатый конфиг он бы отверг.
        os.replace(tmp, XRAY_CONF)
        xray_port_gate(data.port)

        # Мосту нужно несколько секунд, чтобы заметить и подняться. Ждём не
        # вслепую, а до появления признака — иначе владелец увидит «не
        # работает» на исправной настройке.
        for _ in range(20):
            time.sleep(1)
            if xray_running():
                break
        return {"status": "ok", "running": xray_running(),
                "detail": xray_state().get("error") or ""}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def xray_port_gate(port):
    """Открывает дверь входу Xray.

    Ноль означает «двери не нужно»: у моста нет своего входа, он подключается
    сам. Без этой проверки сюда ушло бы правило с нулевым портом — iptables его
    не примет, а выглядело бы это как сбой применения конфига.

    Правило идемпотентно."""
    try:
        port = int(port)
    except (TypeError, ValueError):
        return
    if port <= 0 or port > 65535:
        return
    try:
        subprocess.run(f"iptables -C INPUT -p tcp --dport {int(port)} -j ACCEPT",
                       shell=True, check=True, capture_output=True)
    except Exception:
        subprocess.run(f"iptables -I INPUT 1 -p tcp --dport {int(port)} -j ACCEPT",
                       shell=True, stderr=subprocess.DEVNULL)


@app.get("/api/xray/status")
def xray_status():
    """Состояние моста. Берётся из файла, который пишет его контейнер."""
    st = xray_state()
    return {
        "installed": os.path.exists(XRAY_BIN),
        "configured": os.path.exists(XRAY_CONF),
        "running": xray_running(),
        "error": st.get("error") or "",
        "checked_at": st.get("checked_at") or 0,
    }


@app.get("/api/xray/keys")
def xray_keys():
    """Пара ключей для маскировки входа. Приватный остаётся здесь, в конфиге;
    наружу уходит только публичный — его мастер вписывает себе в исходящий
    канал."""
    try:
        res = subprocess.run([XRAY_BIN, "x25519"], capture_output=True,
                             text=True, timeout=15)
        priv = pub = ""
        for line in res.stdout.splitlines():
            low = line.lower()
            if "private" in low:
                priv = line.split(":", 1)[1].strip()
            elif "public" in low or "password" in low:
                pub = line.split(":", 1)[1].strip()
        if not priv or not pub:
            raise Exception(res.stdout.strip()[:200] or "пустой ответ")
        return {"private_key": priv, "public_key": pub}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/xray/whoami")
def xray_whoami():
    """Внешний адрес этого узла — тот, с которого он подключается к мастеру.

    Нужен мастеру один раз, при настройке: по нему он потом проверяет, жив ли
    мост. Спрашивать это у агента каждый раз нельзя — агент живёт за туннелем
    амнезии, и тогда отказ амнезии выглядел бы как отказ второго канала.

    Только IPv4: вход мастера слушает четвёртую версию, и адрес шестой версии
    в проверке дал бы вечное «моста нет».
    """
    for src in ("https://ifconfig.me", "https://api.ipify.org",
                "https://ipv4.icanhazip.com"):
        try:
            res = subprocess.run(f"curl -4 -s --max-time 6 {src}", shell=True,
                                 capture_output=True, text=True, timeout=10)
            addr = (res.stdout or "").strip()
            parts = addr.split(".")
            if len(parts) == 4 and all(p.isdigit() for p in parts):
                return {"ip": addr, "source": src}
        except Exception:
            continue
    raise HTTPException(status_code=500,
                        detail="не удалось определить внешний адрес")


@app.post("/api/xray/off")
def xray_off():
    """Выключить мост. Убираем конфиг — мост это заметит и остановится сам.

    Именно убираем, а не останавливаем: своего процесса у агента нет, а
    контейнер моста поднимется заново при любом перезапуске. Без конфига он
    просто ждёт, ничего не делая."""
    try:
        if os.path.exists(XRAY_CONF):
            os.remove(XRAY_CONF)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "running": False}


@app.get("/api/health")
def health():
    """Жив ли агент. Нарочно ничего не считает и никуда не ходит: проверка
    должна отвечать мгновенно даже тогда, когда всё остальное сломалось, —
    иначе сторож примет медленный ответ за смерть и начнёт лечить здоровое."""
    return {"status": "ok"}


@app.get("/api/system_stats")
def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        try: disk = psutil.disk_usage("/hostfs").percent
        except: disk = psutil.disk_usage("/").percent

        # Среднее за минуту и число ядер. Мгновенный процент оставляем — он
        # нужен для дашборда, где человек смотрит «что сейчас». А вот СУДИТЬ по
        # нему нельзя: ночная проверка обновлений или снятие копии поднимают
        # его до сотни на пустом месте, и мастер слал тревогу о перегрузке
        # туда, где нагрузки нет.
        try:
            load1 = os.getloadavg()[0]
            cores = psutil.cpu_count() or 1
        except Exception:
            load1, cores = None, 1

        return {"cpu": cpu, "ram": ram, "disk": disk,
                "load1": load1, "cores": cores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
def get_logs(lines: int = 50):
    try:
        # ИСПРАВЛЕНО: Читаем системные логи хоста через chroot
        log_output = subprocess.check_output(f"chroot /hostfs journalctl -n {lines} --no-pager", shell=True).decode()
        return {"status": "success", "logs": log_output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EnvChange(BaseModel):
    key: str
    value: str


@app.post("/api/host/set_env")
def set_env(data: EnvChange):
    """Записать переменную в .env агента и пересоздать контейнер.

    Нужно, чтобы администратор не лазил по серверам руками: токен панелей должен
    совпадать на обеих нодах, и мастер проставляет его здесь сам. Сама запись — дело
    демона на хосте, контейнер к .env доступа не имеет.

    Разрешены только известные ключи: иначе через эту ручку можно было бы дописать
    в окружение что угодно.
    """
    allowed = {"API_TOKEN", "API_TOKEN_PREV", "BACKUP_PASSWORD"}
    if data.key not in allowed:
        raise HTTPException(status_code=400, detail="Недопустимая переменная")
    try:
        # Своё имя на каждую просьбу: файл был один на всех и перезаписывался,
        # так что две просьбы подряд оставляли только последнюю.
        import secrets
        flag = os.path.join(FLAGS_DIR, "set_env." + secrets.token_hex(6))
        with open(flag, "w") as f:
            f.write(f"{data.key}={data.value}\n")
        os.chmod(flag, 0o600)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/host/env_status")
def env_status():
    """Какие переменные у узла заданы. Только да/нет, без значений.

    Нужно мастеру, чтобы доводить состояние до одинакового самому: раньше он
    отправлял токен и не знал, доехал ли тот. Значения не отдаём — по ним и
    подделывают доступ.
    """
    return {key: bool(os.getenv(key, "").strip())
            for key in ("API_TOKEN", "API_TOKEN_PREV", "BACKUP_PASSWORD")}


@app.post("/api/host/reboot")
def trigger_reboot():
    try:
        with open(f"{FLAGS_DIR}/do_reboot", "w") as f: f.write("reboot_requested")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/host/update")
def trigger_update():
    """Сигнал демону хоста на запуск deploy.sh для Германии"""
    try:
        with open(f"{FLAGS_DIR}/do_update", "w") as f: f.write("update_requested")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/host/deploy_status")
def deploy_status():
    """Метка последнего успешного деплоя (unix-ts + git-hash), которую пишет deploy.sh
    после `docker compose up -d`. RU-бот поллит это после команды обновления, чтобы
    ПОДТВЕРДИТЬ, что DE реально обновилась (ждёт ts новее, чем был до команды)."""
    p = f"{FLAGS_DIR}/deploy_done"
    try:
        if os.path.exists(p):
            with open(p) as f:
                ts, _, h = f.read().strip().partition(" ")
            return {"ts": int(ts) if ts.isdigit() else 0, "hash": h}
    except Exception:
        pass
    return {"ts": 0, "hash": ""}

@app.post("/api/host/audit")
def trigger_audit():
    try:
        with open(f"{FLAGS_DIR}/do_audit", "w") as f: f.write("audit_requested")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/host/audit_result")
def get_audit_result():
    report_file = f"{FLAGS_DIR}/audit_report.json"
    status_file = f"{FLAGS_DIR}/audit_status"
    
    if os.path.exists(report_file):
        with open(report_file, "r") as f: return {"status": "done", "report": f.read()}
    elif os.path.exists(status_file):
        with open(status_file, "r") as f: return {"status": "running", "step": f.read().strip()}
    else:
        return {"status": "not_started"}

@app.get("/api/host/maintenance")
def maintenance_reports():
    """Отчёты недельного обслуживания: проверка хоста и сборщик мусора.

    Сами отчёты пишут скрипты из уборки, раз в неделю. Здесь только чтение:
    агент их не считает и не обновляет, а отдаёт как есть. Разбирать и
    показывать будет мастер — он один умеет писать человеку.

    Отсутствие файла не ошибка: на свежей ноде уборка ещё не отрабатывала.
    """
    out = {}
    for key, name in (("health", "host_health.json"), ("gc", "gc.json")):
        path = f"{FLAGS_DIR}/{name}"
        try:
            with open(path) as f:
                out[key] = json.load(f)
        except (OSError, ValueError):
            out[key] = None
    return out


@app.get("/api/backup")
def download_backup():
    """Архивирует конфигурацию DE агента и отдает файл"""
    try:
        archive_path = "/tmp/de_backup.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            if os.path.exists(CONF_DIR):
                tar.add(CONF_DIR, arcname=os.path.basename(CONF_DIR))
        return FileResponse(path=archive_path, filename="de_agent_backup.tar.gz", media_type="application/gzip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
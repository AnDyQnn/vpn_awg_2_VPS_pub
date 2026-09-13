import os
import subprocess
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


MASTER_IP = "10.13.13.1"


def verify_token(request: Request):
    if not API_TOKEN:
        return
    if request.headers.get("X-Api-Key", "") == API_TOKEN:
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

@app.get("/api/system_stats")
def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        try: disk = psutil.disk_usage("/hostfs").percent
        except: disk = psutil.disk_usage("/").percent

        return {"cpu": cpu, "ram": ram, "disk": disk}
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
    allowed = {"API_TOKEN", "BACKUP_PASSWORD"}
    if data.key not in allowed:
        raise HTTPException(status_code=400, detail="Недопустимая переменная")
    try:
        flag = os.path.join(FLAGS_DIR, "set_env")
        with open(flag, "w") as f:
            f.write(f"{data.key}={data.value}\n")
        os.chmod(flag, 0o600)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
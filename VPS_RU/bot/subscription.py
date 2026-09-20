# -*- coding: utf-8 -*-
"""Раздача подписок: маленький веб-сервер рядом с ботом.

Зачем вообще сервер. Ссылку `vless://` можно просто прислать в Telegram, и
человек её один раз вставит. Но тогда любое изменение — новый список
исключений, переезд на другой адрес, смена маскировки — снова собирает всех
тридцать человек на перевыпуск. Ровно от этого мы и уходим.

Подписка решает это так: клиент сам раз в несколько часов читает личную
ссылку и обновляет профиль. Поэтому ссылка постоянная, а содержимое по ней
собирается каждый раз заново из базы.

Почему сервер живёт у бота, а не на узле: содержимое подписки зависит от базы
(кто приостановлен, у кого какой срок, кому что выдано). Узел базы не видит и
видеть не должен — иначе пришлось бы синхронизировать две правды.
"""
import asyncio
import base64
import json
import os
import re
import ssl
import time

from aiohttp import web

from database import db
import xray

# Порт внутри контейнера. Наружу он выставляется в docker-compose — и только
# если владелец решил включить подписки.
SUB_PORT = int(os.getenv("SUB_PORT", "8080"))

# Сертификат на IP-адрес: лежит рядом, кладёт его scripts/public_sub.sh. Пока
# файлов нет, сервер работает как раньше — открытым текстом на localhost, куда
# снаружи не достучаться.
CERT_DIR = os.getenv("SUB_CERT_DIR", "/volumes/certs")

# Вход через маску: тот самый сайт-заглушка, к которому Reality уводит всех, кто
# не прошёл проверку. Слушает ТОЛЬКО петлю — наружу его показывает Xray.
#
# Почему это один сервер с подпиской, а не два.
#
# Во-первых, так подписка оказывается на 443. Нестандартные порты режут
# мобильные операторы, и человек за таким оператором не получал профиль вовсе —
# а выглядело это как «VPN не работает». Через маску подписка приезжает по
# обычному 443, неотличимо от захода на сайт.
#
# Во-вторых, рубеж у них общий. Отдельный сервер заглушки — это второй TLS,
# второй разбор запроса и второе место, где можно ошибиться, причём на виду у
# всего интернета. Здесь разбор один, проверенный, и он уже умеет отказывать
# молча.
DECOY_PORT = int(os.getenv("DECOY_PORT", "8444"))
DECOY_HOST = "127.0.0.1"


# --- Защита открытого порта -------------------------------------------------
#
# Пока подписка слушала localhost, защищать её было не от кого. Открыв порт
# наружу, мы отдаём процессу бота чужой трафик: теперь любой сканер интернета
# может занять его собой. Поэтому здесь три разных рубежа, и каждый держит своё.
#
# Первый рубеж — не наш: правила файрвола на хосте (см. scripts/public_sub.sh).
# Они режут поток до того, как он доедет до питона, и это единственное место,
# где можно пережить настоящий поток мусора.
#
# Ниже — то, что можно сделать изнутри.

# Токен подписки — 32 знака из secrets.token_urlsafe(24), то есть 192 бита.
# Перебрать его нельзя, и проверка формы нужна не для этого: она отсекает мусор
# до обращения к базе. Чужой запрос не должен стоить нам похода в postgres.
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

# Живой клиент читает подписку раз в двенадцать часов. Тридцать запросов в
# минуту с одного адреса — это уже не клиент.
RATE_WINDOW = 60
RATE_LIMIT = 30

# Промахи с одного адреса. Десять неверных токенов — это перебор или скан, и
# дальше с этим адресом разговаривать незачем: час он получает отказ, не
# доходя до базы.
MISS_LIMIT = 10
BAN_SECONDS = 3600

# Сколько запросов обрабатываем одновременно. Сервер подписок живёт в одном
# процессе с ботом: заняв этот процесс целиком, бота можно уронить, не тронув
# самого бота. Тридцать человек с обновлением раз в полсуток — шестнадцать
# одновременных с большим запасом.
MAX_INFLIGHT = 16

# Сколько адресов помним. Без потолка счётчики сами становятся дырой: скан с
# тысяч адресов набьёт словарь до отказа памяти. Память — такой же ресурс, как
# процессор, и защищать её нужно так же.
TRACK_MAX = 4096

_rate = {}    # адрес -> [когда началось окно, сколько запросов]
_miss = {}    # адрес -> [когда начали считать, до какого времени отказ, промахов]
_inflight = None


def _prune(now):
    """Забываем тех, чей след истёк. Зовётся, когда словари разрослись."""
    for store, alive in ((_rate, RATE_WINDOW), (_miss, BAN_SECONDS)):
        for ip in [k for k, v in store.items() if now - v[0] > alive]:
            store.pop(ip, None)
    # Если и после чистки тесно — значит идёт распределённый скан, и поимённо
    # его уже не удержать. Бросаем счётчики целиком: настоящая стена здесь не
    # мы, а файрвол, а память нужнее.
    if len(_rate) > TRACK_MAX:
        _rate.clear()
    if len(_miss) > TRACK_MAX:
        _miss.clear()


def _too_fast(ip, now):
    """Частит ли этот адрес."""
    slot = _rate.get(ip)
    if not slot or now - slot[0] > RATE_WINDOW:
        _rate[ip] = [now, 1]
        return False
    slot[1] += 1
    return slot[1] > RATE_LIMIT


def _banned(ip, now):
    slot = _miss.get(ip)
    return bool(slot) and slot[1] > now


def _note_miss(ip, now):
    """Промах по токену. Возвращает True, когда адрес только что закрыли."""
    slot = _miss.get(ip)
    if not slot or now - slot[0] > BAN_SECONDS:
        _miss[ip] = [now, 0.0, 1]
        return False
    slot[2] += 1
    if slot[2] >= MISS_LIMIT and slot[1] <= now:
        slot[1] = now + BAN_SECONDS
        return True
    return False


def blocked_now():
    """Сколько адресов сейчас закрыто — для экрана в боте."""
    now = time.time()
    return sum(1 for v in _miss.values() if v[1] > now)


# Пути, которые вход-маска обслуживает по-настоящему. Всё остальное на нём —
# страница-заглушка, одна и та же.
_SUB_PATHS = ("/sub/", "/routing/", "/geo/")


def _is_sub_path(path: str) -> bool:
    return any(path.startswith(x) for x in _SUB_PATHS)


def on_decoy(request) -> bool:
    """Пришёл ли запрос на вход-маску. Отличаем по порту, а не по имени.

    По имени было бы ненадёжно: имя приходит от гостя, а порт — от ядра."""
    try:
        return request.transport.get_extra_info("sockname")[1] == DECOY_PORT
    except Exception:
        return False


_DECOY_STARTED = time.time()
_DECOY_ETAG = None


def _decoy_etag():
    """Метка версии страницы. Считается один раз: страница не меняется."""
    global _DECOY_ETAG
    if _DECOY_ETAG is None:
        import hashlib
        import decoy
        _DECOY_ETAG = '"%s"' % hashlib.sha256(decoy.BODY).hexdigest()[:16]
    return _DECOY_ETAG


def _http_date(ts):
    """Дата в том виде, в каком её пишут веб-серверы."""
    from email.utils import formatdate
    return formatdate(ts, usegmt=True)


def decoy_page(request=None, status=200):
    """Страница, которую видит посторонний.

    Отвечает как живой сайт: 200 на главной, 404 на чепухе, заголовки с датой и
    меткой версии, поддержка HEAD и «если не менялось». Сервер, одинаково
    отвечающий «временно недоступен» на любой запрос, — сам по себе примета.

    При этом внутри она по-прежнему нема: ни чтения с диска по просьбе гостя, ни
    состояния, ни форм. Всё, что она умеет, — это то, что можно против нас
    применить.
    """
    import decoy
    etag = _decoy_etag()
    headers = {
        "Date": _http_date(time.time()),
        "Last-Modified": _http_date(_DECOY_STARTED),
        "ETag": etag,
        "Cache-Control": "public, max-age=3600",
        "Accept-Ranges": "bytes",
        # Ни версии, ни имени движка: это бесплатная подсказка тому, кто ищет,
        # чем нас пробовать.
        "Server": "nginx",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }

    # «У меня уже есть эта версия» — обычный разговор живого сайта с браузером.
    if request is not None and status == 200:
        if (request.headers.get("If-None-Match") or "").find(etag) >= 0:
            return web.Response(status=304, headers=headers)

    body = decoy.BODY if status == 200 else decoy.NOT_FOUND
    if request is not None and request.method == "HEAD":
        headers["Content-Length"] = str(len(body))
        return web.Response(status=status, headers=headers,
                            content_type="text/html", charset="utf-8")
    return web.Response(body=body, status=status, content_type="text/html",
                        charset="utf-8", headers=headers)


def decoy_reply(request):
    """Что ответить гостю, пришедшему не за подпиской.

    Разбор здесь ровно один — путь целиком, без разбора на части. Разбирать
    глубже нечего: у сайта нет ни страниц, ни файлов, а каждая попытка разбора —
    это место, где можно ошибиться на виду у всего интернета.
    """
    import decoy
    # Метод разбираем здесь же: рубеж ниже сюда уже не доберётся, а живой сайт
    # на POST отвечает «метод не поддержан», а не выдачей главной страницы.
    if request.method not in ("GET", "HEAD"):
        return web.Response(status=405,
                            headers={"Allow": "GET, HEAD",
                                     "Date": _http_date(time.time()),
                                     "Server": "nginx"})
    path = request.path
    if path in ("/", "/index.html"):
        return decoy_page(request, 200)
    if path == "/robots.txt":
        return web.Response(
            text=decoy.ROBOTS, content_type="text/plain", charset="utf-8",
            headers={"Date": _http_date(time.time()), "Server": "nginx",
                     "Cache-Control": "public, max-age=86400"})
    if path == "/favicon.ico":
        return web.Response(
            body=decoy.FAVICON, content_type="image/svg+xml",
            headers={"Date": _http_date(time.time()), "Server": "nginx",
                     "Cache-Control": "public, max-age=86400"})
    return decoy_page(request, 404)


@web.middleware
async def guard(request, handler):
    """Общий рубеж: всё, что можно отклонить не думая, отклоняется здесь.

    Отказ всегда один и тот же — 404 и слово. По ответу нельзя отличить
    «слишком часто», «закрыт» и «нет такого токена»: чужому эта разница
    подсказывает, куда давить, а свой всё равно спросит у бота."""
    # Пришедший на вход-маску не по адресу подписки получает страницу сразу,
    # до всех рубежей. Так и задумано: страница у нас одна и та же побайтово,
    # отдать её не стоит ничего — а вот пустить сканеров в общий счётчик
    # означало бы, что достаточно постучаться тысячу раз, и подписка перестанет
    # работать у своих. Reality уводит сюда КАЖДОГО, кто не прошёл проверку,
    # поэтому таких стуков будут тысячи.
    if on_decoy(request) and not _is_sub_path(request.path):
        return decoy_reply(request)

    now = time.time()
    ip = request.remote or "?"

    if len(_rate) > TRACK_MAX or len(_miss) > TRACK_MAX:
        _prune(now)

    # Метод. Ничего, кроме чтения, здесь не бывает, и знать о существовании
    # других методов чужому незачем.
    if request.method not in ("GET", "HEAD"):
        return web.Response(status=404, text="not found")

    if _banned(ip, now) or _too_fast(ip, now):
        return web.Response(status=404, text="not found")

    token = request.match_info.get("token", "")
    if token and not TOKEN_RE.match(token):
        # Форма не та — в базу не идём вовсе.
        _note_miss(ip, now)
        return web.Response(status=404, text="not found")

    global _inflight
    if _inflight is None:
        _inflight = asyncio.Semaphore(MAX_INFLIGHT)
    if _inflight.locked():
        # Очередь занята. Ждать нельзя: ожидание — это и есть то, чем кладут
        # процесс. Отказываем сразу, свой клиент придёт снова.
        return web.Response(status=503, text="busy")
    async with _inflight:
        resp = await handler(request)

    # Своё имя не называем: сканер по нему выбирает, чем бить.
    resp.headers["Server"] = "-"
    return resp

# Как часто клиенту предлагается перечитывать подписку (часы).
#
# Было двенадцать — «изменения доезжают за полдня, а сервер не дёргают
# попусту». Экономия оказалась мнимой: перевыпуск отзывает старый ключ
# немедленно, и до следующего опроса человек сидит без связи. Полдня без VPN
# из-за того, что мы пожалели запросов, — плохая сделка.
#
# Два часа при тридцати людях это меньше четырёхсот запросов в сутки на весь
# узел. Охрана порта пропускает тридцать в минуту с одного адреса, так что
# запас тут четырёхзначный.
UPDATE_INTERVAL_HOURS = 2

# Сколько байт профиля маршрутизации согласны положить в заголовок. Дальше —
# в тело: длинные заголовки режут посредники, и приложение получит обрезанный
# профиль, даже не узнав об этом.
HEADER_LIMIT = 4096

# Чужие запросы на несуществующие токены — это либо опечатка, либо скан.
# Считаем их и сообщаем владельцу не чаще раза в час, чтобы не устроить спам.
_miss_count = 0
_miss_reported = 0.0


async def _userinfo(rec) -> str:
    """Строка для клиента: сколько потрачено и до какого числа действует.

    Приложения показывают это на карточке профиля — человеку не нужно лезть в
    бота, чтобы узнать, когда кончается срок."""
    used_in, used_out = await db.get_traffic_totals(rec["user_uuid"])
    expire = 0
    if rec.get("expires_at"):
        expire = int(rec["expires_at"].timestamp())
    # total=0 значит «без лимита по объёму» — у нас ограничение не по гигабайтам,
    # а по скорости и поведению, поэтому именно ноль, а не выдуманное число.
    return (f"upload={used_in}; download={used_out}; total=0; expire={expire}")


# Страница для человека, открывшего ссылку в браузере.
#
# Приложению по этому адресу отдаётся список профилей в base64 — и человек,
# ткнув в ссылку из Telegram, видел ровно это: гигантскую строку без начала и
# конца. Выглядит как поломка, а на самом деле всё правильно, просто адрес не
# для глаз.
#
# Браузер отличается от приложения одним: он просит html. Приложения этого не
# просят никогда, поэтому подмена их не задевает.
BROWSER_PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ваша ссылка VPN</title>
<style>
  :root { color-scheme: light dark; }
  body { margin:0; min-height:100vh; display:flex; align-items:center;
         justify-content:center; padding:24px;
         font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         background:#0d1117; color:#e6edf3; }
  .card { max-width:520px; width:100%; background:#161b22; border:1px solid #30363d;
          border-radius:14px; padding:24px; }
  h1 { font-size:20px; margin:0 0 12px; }
  p { margin:0 0 14px; color:#9aa4b2; }
  .link { word-break:break-all; background:#0d1117; border:1px solid #30363d;
          border-radius:10px; padding:12px; font-family:ui-monospace,monospace;
          font-size:13px; color:#e6edf3; }
  button { margin-top:14px; width:100%; padding:13px; font-size:16px;
           border:0; border-radius:10px; background:#238636; color:#fff;
           cursor:pointer; }
  button:active { background:#1a6f2b; }
  .ok { color:#3fb950; }
  ol { margin:14px 0 0; padding-left:20px; color:#9aa4b2; }
  li { margin-bottom:6px; }
</style></head><body>
<div class="card">
  <h1>Это ваша ссылка на VPN</h1>
  <p>Её не нужно открывать в браузере — её нужно вставить в приложение.</p>
  <div class="link" id="u">__URL__</div>
  <button id="b">Скопировать ссылку</button>
  <ol>
    <li>Откройте приложение <b>Happ</b>.</li>
    <li>Добавьте подписку и вставьте эту ссылку.</li>
    <li>Включите VPN.</li>
  </ol>
  <p style="margin-top:14px">Дальше всё обновляется само: новые сервера и
  настройки приложение подтянет без вашего участия.</p>
</div>
<script>
document.getElementById('b').onclick = function () {
  var u = document.getElementById('u').textContent;
  var done = function () {
    var b = document.getElementById('b');
    b.textContent = 'Скопировано';
    b.className = 'ok';
    setTimeout(function () { b.textContent = 'Скопировать ссылку'; b.className = ''; }, 1600);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(u).then(done, function () {});
  } else {
    var t = document.createElement('textarea');
    t.value = u; document.body.appendChild(t); t.select();
    try { document.execCommand('copy'); done(); } catch (e) {}
    document.body.removeChild(t);
  }
};
</script>
</body></html>
"""


def _wants_html(request):
    """Пришёл ли запрос из браузера, а не из приложения."""
    return "text/html" in (request.headers.get("Accept", "") or "")


async def handle_sub(request):
    """Отдаёт профиль по личному токену.

    Отказ всегда выглядит одинаково — 404 без пояснений. По ответу нельзя
    отличить «такого токена нет» от «человек приостановлен»: чужому знать
    незачем, а свой всё равно спросит у бота."""
    global _miss_count, _miss_reported
    token = request.match_info.get("token", "")

    rec = await db.get_xray_by_token(token) if token else None
    if not rec or not rec["is_active"]:
        _miss_count += 1
        now = time.time()
        # Считаем промахи и по адресу тоже: когда их с одного места много, это
        # уже не опечатка, и такому адресу мы перестаём отвечать на час.
        shut = _note_miss(request.remote or "?", now)
        if shut or (_miss_count >= 5 and now - _miss_reported > 3600):
            _miss_reported = now
            try:
                where = f" ({request.remote})" if shut else ""
                what = ("адрес закрыт на час, промахов подряд: %d" % MISS_LIMIT
                        if shut else
                        "неизвестных обращений: %d" % _miss_count)
                await db.log_event("Подписки", what + where)
            except Exception:
                pass
            _miss_count = 0
        return web.Response(status=404, text="not found")

    # Сплит едет вместе с подпиской. Профиль с тем же именем приложение
    # обновляет, а не добавляет рядом, — поэтому изменившийся список исключений
    # доезжает до всех сам, без перевыпуска и без действий человека.
    routing, in_body = "", []
    try:
        import happ_routing
        routing = await happ_routing.link(uuid_val=rec["user_uuid"])
        if len(routing) > HEADER_LIMIT:
            # Заголовок такой длины по дороге могут обрезать, и приложение
            # получит мусор вместо профиля. Тогда — строкой в теле: чужой
            # клиент её просто пропустит.
            in_body = [routing]
            routing = ""
    except Exception as e:
        print(f"Подписка: профиль маршрутизации не собрался: {e}")

    # Человеку, открывшему ссылку в браузере, — объяснение и кнопка «копировать».
    # Приложение html не просит, так что его это не касается.
    if _wants_html(request):
        return web.Response(
            body=BROWSER_PAGE.replace("__URL__", str(request.url)).encode(),
            content_type="text/html", charset="utf-8",
            headers={"Cache-Control": "no-store"})

    body = await xray.subscription_body(token, extra=in_body)
    if not body:
        return web.Response(status=404, text="not found")

    name = base64.b64encode((rec.get("name") or "VPN").encode()).decode()
    headers = {
        "profile-update-interval": str(UPDATE_INTERVAL_HOURS),
        "profile-title": f"base64:{name}",
        "subscription-userinfo": await _userinfo(rec),
        # Подписка — личная и всегда свежая: кэшировать её нельзя, иначе
        # отзыв доступа не доедет до клиента.
        "Cache-Control": "no-store",
    }
    if routing:
        headers["routing"] = routing

    # Пришёл и забрал — записываем. Это единственный след того, что подписка
    # доехала: дальше она живёт уже в приложении, и оттуда её не видно.
    now = time.time()
    if now - _sub_seen.get(token, 0) > SUB_LOG_QUIET:
        _sub_seen[token] = now
        if len(_sub_seen) > TRACK_MAX:
            _sub_seen.clear()
        who = rec.get("name") or "ключ без имени"
        where = request.remote or "адрес неизвестен"
        # С профилем или без — разница важная: без него у человека не будет ни
        # сплита, ни нашего DNS, и выглядеть это будет как «VPN не работает».
        what = "с профилем" if (routing or in_body) else "БЕЗ профиля"
        print(f"Подписка: {who} забрал {what}, с {where}", flush=True)
        try:
            await db.log_event("Подписки", f"{who} забрал подписку {what} · {where}")
        except Exception:
            pass

    return web.Response(
        body=body.encode(),
        content_type="text/plain",
        charset="utf-8",
        headers=headers)


async def handle_routing(request):
    """Профиль маршрутизации в чистом виде — для скрипта, а не для приложения.

    Приложение получает профиль вместе с подпиской и ничего больше знать не
    должно. Но на машине, которая настраивается скриптом, приложения нет: там
    нужен сам JSON, чтобы разложить правила своими средствами.

    Адрес тот же личный токен, что и у подписки: отдельного доступа не заводим,
    иначе появится второй секрет с той же силой и своей судьбой.
    """
    token = request.match_info.get("token", "")
    rec = await db.get_xray_by_token(token) if token else None
    if not rec or not rec["is_active"]:
        _note_miss(request.remote or "?", time.time())
        return web.Response(status=404, text="not found")
    try:
        import happ_routing
        profile = await happ_routing.profile(rec["user_uuid"])
    except Exception as e:
        print(f"Профиль по токену: {e}")
        return web.Response(status=500, text="error")

    body = json.dumps(profile, ensure_ascii=False, indent=2)
    return web.Response(
        body=body.encode(),
        content_type="application/json",
        charset="utf-8",
        headers={"Cache-Control": "no-store"})


# --- Гео-файлы для приложения ------------------------------------------------
#
# Приложение тянет geosite.dat и geoip.dat само, и по умолчанию с GitHub —
# который из России не открывается. Без них оно считает профиль маршрутизации
# испорченным целиком: ни сплита, ни нашего DNS, ни фильтров.
#
# Нашим правилам эти файлы не нужны — у нас обычные домены и сети. Но требует
# их приложение, а не мы, поэтому проще отдать: до GitHub узел достаёт, а до
# узла достаёт телефон.
GEO_DIR = os.getenv("SUB_GEO_DIR", "/volumes/geo")
GEO_FILES = ("geosite.dat", "geoip.dat")


def geo_path(name):
    """Путь к гео-файлу, если его можно отдавать. Иначе None.

    Отделено от самой отдачи нарочно: здесь живёт всё, что решает «можно или
    нет», и это единственная часть, которую надо уметь проверить тестом. Сама
    отдача — поток байтов в сокет, её без настоящего сокета не проверишь.
    """
    # Имя берём не из запроса, а сверяем со списком: иначе адрес превращается
    # в способ читать файлы узла.
    if name not in GEO_FILES:
        return None
    path = os.path.join(GEO_DIR, name)
    try:
        if os.path.getsize(path) < 1024:
            return None
    except OSError:
        # Ещё не скачали — молчим так же, как на всё остальное. Приложение
        # попробует снова, а лишних подробностей чужому знать незачем.
        return None
    return path


# Когда последний раз записывали приход за подпиской, по токену.
#
# Запись нужна вот зачем. Трижды за один день разбор упирался в вопрос, на
# который неоткуда было взять ответ: приходил ли клиент за подпиской вообще?
# Без ответа «у человека нет профиля маршрутизации» и «профиль есть, но не
# применяется» выглядят одинаково, а чинить их надо по-разному. Отказы мы
# писали всегда, успехи — ни разу, и получалось, что видно только плохое.
#
# Частоту ограничиваем: приложение обновляется раз в два часа, но при ошибке
# может долбить в цикле, и журнал из этого делать незачем.
_sub_seen = {}
SUB_LOG_QUIET = 600


async def handle_geo(request):
    """Отдаёт гео-файл. Только эти два имени и ничего больше.

    Имя берём не из запроса, а сверяем со списком: иначе адрес превращается в
    способ читать файлы узла.
    """
    path = geo_path(request.match_info.get("name", ""))
    if not path:
        return web.Response(status=404, text="not found")
    # Отдаём кусками руками, а не FileResponse.
    #
    # FileResponse зовёт `loop.sendfile`, а поверх TLS ядерного sendfile нет —
    # asyncio уходит в запасной путь и падает там на ровном месте:
    #
    #     base_events.py _sendfile_fallback > proto.restore()
    #     sslproto.py set_protocol
    #     AttributeError: 'NoneType' object has no attribute '_set_app_protocol'
    #
    # Соединение при этом рвётся посреди передачи. Снаружи это выглядит как
    # «не удалось скачать файл»: человек жмёт «Повторить», получает то же самое
    # и остаётся без гео-файлов — а без них приложение считает профиль
    # маршрутизации испорченным ЦЕЛИКОМ. Не работает ни сплит, ни наш DNS, ни
    # исключения. То есть падение на отдаче одного файла выглядит как «VPN не
    # работает вообще», и искать причину идут куда угодно, только не сюда.
    #
    # Целиком в память тоже нельзя: файлы весят двадцать семь мегабайт на
    # двоих, а памяти на узле два гигабайта на всё. Поэтому поток кусками —
    # ровно то, что FileResponse делал бы без TLS.
    resp = web.StreamResponse(headers={
        "Cache-Control": "public, max-age=3600",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(os.path.getsize(path)),
    })
    await resp.prepare(request)
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                await resp.write(chunk)
        await resp.write_eof()
    except (ConnectionResetError, ConnectionAbortedError, asyncio.CancelledError):
        # Человек ушёл из сети посреди закачки — обычное дело на телефоне, и
        # не повод для строки в журнале.
        pass
    return resp


async def handle_root(request):
    """Корень молчит. На сервере с открытым портом это важнее вежливости:
    страница-приветствие сразу говорит сканеру, что тут есть что искать."""
    return web.Response(status=404, text="not found")


# --- Сертификат и вход снаружи ----------------------------------------------
#
# Здесь два разных входа, и путать их нельзя.
#
# Внутренний (SUB_PORT, 8080) — для тех, кто уже в туннеле. Он открытым текстом
# и это нормально: туннель уже шифрует, а наружу этот порт не публикуется
# вовсе. Он работает всегда, с первой секунды жизни бота.
#
# Внешний (PUBLIC_PORT, 8443) — для интернета, и он существует ТОЛЬКО пока
# рядом лежит действующий сертификат. Нет сертификата — нет и сокета: снаружи
# порт просто молчит, как закрытый. Это и есть вся защита от «случайно отдали
# подписку открытым текстом»: её нельзя отдать, потому что слушать некому.
#
# Настройки у этого нет намеренно. Настройка, которую можно забыть выставить
# или выставить не так, — сама по себе способ однажды открыть порт без
# сертификата. Здесь такого способа нет.
# 2096, а не 8443. Порт 8443 в этой сетевой области уже занят: на нём висит
# HTTPS-страница отказа, и на неё же заворачивается 443 (сам 443 отдан входу
# Xray). Бот делит сеть с узлом, так что занять 8443 значит подраться с ней —
# на живом узле это и случилось, деплой откатился сам.
#
# 2096 выбран не случайно: это общеизвестный запасной порт HTTPS, такой же, как
# уже занятые Xray 2053 и 2083. Снаружи он не выделяется среди чужого трафика.
PUBLIC_PORT = 2096

_ssl_ctx = None
_cert_seen = (0, 0)
_runner = None
_tls_site = None
_decoy_site = None


def decoy_up() -> bool:
    """Поднят ли вход-маска. От этого зависит, можно ли выбрать свой сайт
    маской: Reality уводит к ней каждое рукопожатие, и вход с неподнятой
    заглушкой не работает вообще ни у кого."""
    return _decoy_site is not None


def cert_paths():
    return (os.path.join(CERT_DIR, "fullchain.pem"),
            os.path.join(CERT_DIR, "privkey.pem"))


def cert_ready():
    cert, key = cert_paths()
    try:
        return os.path.getsize(cert) > 0 and os.path.getsize(key) > 0
    except OSError:
        return False


def cert_stamp():
    """Метка файлов сертификата — по ней видно, что его подменили."""
    out = []
    for f in cert_paths():
        try:
            out.append(int(os.stat(f).st_mtime))
        except OSError:
            out.append(0)
    return tuple(out)


def build_ssl():
    """Готовит TLS. Нет файлов — нет и TLS, и внешнего входа тоже нет."""
    global _ssl_ctx, _cert_seen
    if not cert_ready():
        return None
    cert, key = cert_paths()
    ctx = _ssl_ctx or ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(cert, key)
    # Старые версии протокола держать незачем: приложения-клиенты все умеют
    # TLS 1.2, а старьё нужно только тем, кто ищет слабое место.
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    _ssl_ctx, _cert_seen = ctx, cert_stamp()
    return ctx


async def tls_start():
    """Поднять внешний вход. Без сертификата не поднимается — и это главное."""
    global _tls_site
    if _tls_site is not None or _runner is None:
        return False
    ctx = build_ssl()
    if ctx is None:
        return False
    site = web.TCPSite(_runner, "0.0.0.0", PUBLIC_PORT, ssl_context=ctx,
                       backlog=64)
    await site.start()
    _tls_site = site
    print(f"Подписка: внешний вход открыт на {PUBLIC_PORT} по https")
    return True


async def decoy_start():
    """Поднять вход-маску. Тот же сертификат, что у подписки: имя одно."""
    global _decoy_site
    if _decoy_site is not None or _runner is None:
        return False
    ctx = build_ssl()
    if ctx is None:
        return False
    site = web.TCPSite(_runner, DECOY_HOST, DECOY_PORT, ssl_context=ctx,
                       backlog=64)
    await site.start()
    _decoy_site = site
    print(f"Вход-маска: поднят на {DECOY_HOST}:{DECOY_PORT}")
    return True


async def decoy_stop():
    """Снять вход-маску. Отдавать её без сертификата нельзя, а с истёкшим —
    хуже, чем не отдавать вовсе."""
    global _decoy_site
    if _decoy_site is None:
        return False
    await _decoy_site.stop()
    _decoy_site = None
    print("Вход-маска: снят")
    return True


async def tls_stop():
    """Убрать внешний вход. Порт остаётся опубликованным, но слушать некому."""
    global _tls_site, _ssl_ctx
    if _tls_site is None:
        return False
    await _tls_site.stop()
    _tls_site, _ssl_ctx = None, None
    print("Подписка: внешний вход закрыт")
    return True


async def cert_watch():
    """Следит за сертификатом и за тем, есть ли вообще внешний вход.

    Сертификат на IP живёт 160 часов и меняется раз в несколько суток.
    Перечитываем его на месте: SSLContext разрешает подменить цепочку, и новые
    соединения берут уже новый сертификат. Перезапускать ради этого бота
    значило бы рвать все разговоры в Telegram раз в пять дней.

    Здесь же и переключение: сертификат появился — вход открылся, сертификат
    убрали — закрылся. Отдельного тумблера поэтому не нужно, состояние одно и
    видно по файлу."""
    # Первая проверка — скоро, дальше редко.
    #
    # Сертификат появляется как раз тогда, когда бот уже запущен: при первой
    # установке его берут в самом конце, после того как контейнеры подняты. С
    # ровным шагом в десять минут это означало бы, что сразу после установки
    # подписка снаружи молчит без всякой причины, и человек десять минут думает,
    # что она сломана.
    delay = 30
    while True:
        await asyncio.sleep(delay)
        delay = 600
        try:
            if not cert_ready():
                await tls_stop()
                await decoy_stop()
            elif _tls_site is None:
                await tls_start()
                await decoy_start()
            elif cert_stamp() != _cert_seen:
                build_ssl()
                print("Подписка: сертификат перечитан")
                # Вход-маска мог не подняться при старте — например, при первой
                # установке сертификата ещё не было.
                await decoy_start()
        except Exception as e:
            print(f"Подписка: не удалось обновить внешний вход: {e}")


async def start_server():
    """Поднимает сервер подписок. Вызывается один раз при старте бота."""
    global _runner
    # client_max_size — тело запроса. У нас его не бывает вовсе, и четырёх
    # килобайт хватит, чтобы отказ пришёл раньше, чем что-то прочитается.
    app = web.Application(middlewares=[guard], client_max_size=4096)
    app.router.add_get("/sub/{token}", handle_sub)
    # Тот же профиль, но голым JSON: скрипту нужен он, а не ссылка для
    # приложения.
    app.router.add_get("/routing/{token}", handle_routing)
    # Гео-файлы — без токена: их запрашивает приложение до того, как разберётся
    # с подпиской, и секрета в них нет. Это открытые списки.
    app.router.add_get("/geo/{name}", handle_geo)
    app.router.add_get("/", handle_root)
    # Всё остальное — тоже молчание, и через тот же рубеж: без этого чужой путь
    # отвечал бы иначе, чем чужой токен, и по разнице ответов читалась бы карта.
    app.router.add_route("*", "/{tail:.*}", handle_root)

    runner = web.AppRunner(
        app, access_log=None,
        # Держать соединение открытым дольше пятнадцати секунд незачем:
        # клиент читает подписку и уходит. Длинные висящие соединения — это
        # не клиент, а способ занять процесс ничем.
        keepalive_timeout=15,
        # Потолки на строку запроса и на заголовок. Без них длинную строку
        # читают до конца, и её длину выбирает не наша сторона.
        max_line_size=4096, max_field_size=4096)
    await runner.setup()
    _runner = runner

    # Внутренний вход — всегда. Он не публикуется наружу и нужен тем, кто уже
    # в туннеле.
    await web.TCPSite(runner, "0.0.0.0", SUB_PORT, backlog=64).start()
    outside = await tls_start()
    # Вход-маска — через «попробуй»: он второстепенный. Порт может оказаться
    # занят (в этой сетевой области живёт ещё и узел), и тогда исключение
    # поднялось бы сюда и уронило бота в круг перезапусков — ради того, без
    # чего всё прекрасно работает. Не поднялся — скажем и пойдём дальше, а
    # наблюдение за сертификатом попробует снова.
    try:
        masked = await decoy_start()
    except Exception as e:
        masked = False
        print("Вход-маска: не поднялся — %s" % e)
    asyncio.create_task(cert_watch())
    print("Сервер подписок: внутри порт %d, снаружи %s, вход-маска %s"
          % (SUB_PORT, ("порт %d" % PUBLIC_PORT) if outside
             else "закрыто (нет сертификата)",
             ("на %d" % DECOY_PORT) if masked else "не поднят"))
    return runner

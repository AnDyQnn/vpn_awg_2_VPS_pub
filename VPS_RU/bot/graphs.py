import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from database import db
import aiohttp
import time
from utils import get_moscow_now, dt_to_moscow, WG_API_URL, api_session

# Палитра под тёмную тему Gateway Hub (яркие на тёмном, хорошо различимы)
BG      = "#0e1320"
PANEL   = "#121826"
GRID    = "#2b3340"
FG      = "#e6edf3"
MUTED   = "#8b949e"
PALETTE = ["#a371f7", "#58a6ff", "#3fb950", "#d29922", "#f85149",
           "#22d3ee", "#e879f9", "#facc15"]
TOP_N   = 6              # максимум онлайн-сессий цветом, остальные → «Прочие»
ACTIVE_WINDOW_SEC = 300  # «активен/онлайн» = хендшейк не старше 5 минут


def _fmt_mb(mb: float) -> str:
    if mb >= 1024:
        return f"{mb/1024:.2f} ГБ"
    return f"{mb:.1f} МБ"


async def generate_vpn_graph():
    stats = await db.get_stats_24h()
    live_data = {}
    live_hs = {}                       # uuid → последний хендшейк (unix) — для «активен сейчас»
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/peers", timeout=3) as resp:
                if resp.status == 200:
                    peers = await resp.json()
                    for p in peers:
                        uid = p.get('uuid')
                        live_data[uid] = p.get('rx', 0) + p.get('tx', 0)
                        live_hs[uid] = int(p.get('latest_handshake') or 0)
    except Exception as e:
        print(f"Ошибка получения Live-данных: {e}")

    # --- собираем дельты по пользователям (как раньше) ---
    user_plot_data = {}
    prev_totals = {}
    for row in stats:
        uname, uuid_val, t = row['name'], row['user_uuid'], dt_to_moscow(row['last_seen'])
        total_bytes = row['bytes_in'] + row['bytes_out']
        if uuid_val not in user_plot_data:
            user_plot_data[uuid_val] = {'name': uname, 'times': [], 'deltas': [], 'last_total': 0}
            prev_totals[uuid_val] = total_bytes
        else:
            delta = total_bytes - prev_totals[uuid_val]
            if delta < 0:
                delta = total_bytes
            prev_totals[uuid_val] = total_bytes
            user_plot_data[uuid_val]['times'].append(t)
            user_plot_data[uuid_val]['deltas'].append(delta / (1024 * 1024))
            user_plot_data[uuid_val]['last_total'] = total_bytes

    now = get_moscow_now()
    for uuid_val, current_total in live_data.items():
        d = user_plot_data.get(uuid_val)
        if d and len(d['times']) > 0:
            delta = current_total - d['last_total']
            if delta < 0:
                delta = current_total
            d['times'].append(now)
            d['deltas'].append(delta / (1024 * 1024))

    # «активен сейчас» = свежий хендшейк (онлайн). Эти сессии красим цветом — чтобы
    # сразу видеть, кто реально грузит систему; остальные сворачиваются в «Прочие».
    now_ts = time.time()
    for uid, d in user_plot_data.items():
        d['online'] = (now_ts - live_hs.get(uid, 0)) < ACTIVE_WINDOW_SEC

    # --- тёмный стиль ---
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": PANEL,
        "savefig.facecolor": BG, "text.color": FG,
        "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
        "font.size": 10,
    })
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.86, bottom=0.14)

    # ОНЛАЙН-сессии (свежий хендшейк) — красим цветом, отсортированы по трафику.
    # Остальные (офлайн + сверх TOP_N) уходят в «Прочие».
    plotted = [(u, d) for u, d in user_plot_data.items() if d['times']]
    online = sorted([x for x in plotted if x[1].get('online')],
                    key=lambda kv: sum(kv[1]['deltas']), reverse=True)
    offline = [x for x in plotted if not x[1].get('online')]
    total_mb = sum(sum(d['deltas']) for _, d in plotted)

    if not plotted:
        ax.text(0.5, 0.5, "Недостаточно данных для графика\nождём синхронизации (1–5 мин)",
                ha='center', va='center', fontsize=13, color=MUTED, transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    else:
        # стиль осей
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.grid(True, axis='y', color=GRID, linewidth=0.6, alpha=0.5)
        ax.tick_params(length=0)

        shown = online[:TOP_N]                       # цветом — онлайн-сессии
        for i, (uuid_val, d) in enumerate(shown):
            c = PALETTE[i % len(PALETTE)]
            ax.plot(d['times'], d['deltas'], color=c, linewidth=2.2,
                    solid_capstyle='round', label=f"{d['name']}  ·  {_fmt_mb(sum(d['deltas']))}",
                    zorder=3)
            ax.fill_between(d['times'], d['deltas'], color=c, alpha=0.10, zorder=2)

        # «Прочие» — офлайн-сессии + онлайн сверх TOP_N, одной приглушённой линией
        rest = online[TOP_N:] + offline
        if rest:
            rest_mb = sum(sum(d['deltas']) for _, d in rest)
            ax.plot([], [], color=MUTED, linewidth=2.0,
                    label=f"Прочие ({len(rest)})  ·  {_fmt_mb(rest_mb)}")

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(MaxNLocator(8))
        ax.yaxis.set_major_locator(MaxNLocator(6))
        ax.margins(x=0.01)
        ax.set_ylim(bottom=0)
        ax.set_ylabel("Трафик, МБ")

        leg = ax.legend(loc='upper left', frameon=True, fontsize=9,
                        facecolor=PANEL, edgecolor=GRID, labelcolor=FG,
                        framealpha=0.9, borderpad=0.8, labelspacing=0.5)
        leg.set_zorder(5)

    # заголовок + подзаголовок (в одном стиле с приложением)
    fig.text(0.08, 0.945, "Трафик VPN за 24 часа", fontsize=15, fontweight='bold', color=FG)
    fig.text(0.08, 0.905, f"Всего: {_fmt_mb(total_mb)}   ·   обновлено {now.strftime('%H:%M:%S')} МСК   ·   "
                          f"онлайн: {len(online)}", fontsize=10, color=MUTED)

    path = "/volumes/backups/vpn_graph.png"
    fig.savefig(path, facecolor=BG)
    plt.close('all')
    return path


# ---------------------------------------------------------------------------
# НАГРУЗКА: две панели на одной картинке
# ---------------------------------------------------------------------------
# Почему именно две панели, а не две шкалы на одном поле: разные единицы на одной
# картинке читаются плохо и при беглом взгляде врут — глаз сравнивает высоту кривых,
# а они в разных величинах.
#
# И почему пара вообще нужна: узел упирается в ПАКЕТЫ, а не в мегабиты. В момент
# торрента скорость может даже снизиться, а пакеты — стоять в потолке. На одной
# панели это выглядело бы как «нагрузка упала», на двух видно, что сервер задыхается.
NODE_CEILING = 7500      # замеренный потолок узла, клиентских пакетов в секунду


def _fmt_int(n):
    return f"{int(n):,}".replace(",", " ")


async def generate_load_graph(hours=24, uuid=None, title=None, limit_line=None):
    """Скорость и пакеты за период. Без uuid — по всему узлу, с uuid — по одному пиру.

    На персональном графике опорная линия — ЛИМИТ ЭТОГО ЧЕЛОВЕКА, а не потолок узла:
    один пир до общего потолка не дотянется, и такая линия там бессмысленна.
    """
    rows = await db.get_hourly(hours=hours, uuid=uuid)
    path = f"/volumes/backups/load_graph{'_' + uuid[:8] if uuid else ''}.png"

    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
        "text.color": FG, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": MUTED, "font.size": 11,
    })
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.4), dpi=130, sharex=True)
    fig.subplots_adjust(left=.085, right=.975, top=.875, bottom=.08, hspace=.18)

    if not rows:
        for ax in (ax1, ax2):
            ax.text(0.5, 0.5, "Данных пока нет — они копятся с момента включения учёта",
                    ha="center", va="center", color=MUTED, transform=ax.transAxes)
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(False)
    else:
        times = [dt_to_moscow(r["hour"]) for r in rows]
        # час агрегата → средние значения в секунду
        # float() обязателен: SUM по BIGINT приезжает из Postgres как Decimal,
        # а Decimal с float не делится — график падал с ошибкой типов.
        down = [float(r["bytes_in"] or 0) * 8 / 3600 / 1e6 for r in rows]
        up = [float(r["bytes_out"] or 0) * 8 / 3600 / 1e6 for r in rows]
        pps = [(float(r["packets_in"] or 0) + float(r["packets_out"] or 0)) / 3600
               for r in rows]
        peaks = [r["peak_pps"] or 0 for r in rows]

        for ax in (ax1, ax2):
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(GRID)
            ax.grid(True, axis="y", color=GRID, linewidth=.6, alpha=.5)
            ax.tick_params(length=0)
            ax.margins(x=.01)
            ax.yaxis.set_major_locator(MaxNLocator(5))
            # ВАЖНО: нижнюю границу ставим ПОСЛЕ отрисовки. Если сделать это здесь,
            # matplotlib фиксирует пределы на текущих (0..1) и автомасштаб больше
            # не срабатывает — кривая уходит за край картинки.

        ax1.plot(times, down, color=PALETTE[1], lw=2, solid_capstyle="round", label="Приём")
        ax1.fill_between(times, down, color=PALETTE[1], alpha=.10)
        ax1.plot(times, up, color=PALETTE[3], lw=2, solid_capstyle="round", label="Отдача")
        ax1.fill_between(times, up, color=PALETTE[3], alpha=.10)
        ax1.set_ylabel("Скорость, Мбит/с", fontsize=10.5)
        ax1.set_ylim(0, max(max(down), max(up), 0.1) * 1.18)
        leg = ax1.legend(loc="upper left", frameon=True, fontsize=10, facecolor=PANEL,
                         edgecolor=GRID, labelcolor=FG, framealpha=.9, borderpad=.7)
        leg.set_zorder(5)

        ax2.plot(times, pps, color=PALETTE[0], lw=2, solid_capstyle="round", label="В среднем")
        ax2.fill_between(times, pps, color=PALETTE[0], alpha=.10)
        if any(peaks):
            ax2.plot(times, peaks, color=PALETTE[7], lw=1.2, ls=(0, (3, 3)), label="Пик в часе")
        ax2.set_ylabel("Пакеты в секунду", fontsize=10.5)

        ref = limit_line if limit_line else (None if uuid else NODE_CEILING)
        if ref:
            ax2.axhline(ref, color=PALETTE[4], lw=1.4, ls=(0, (5, 4)))
            ax2.text(times[0], ref * .95,
                     ("лимит · " if uuid else "потолок узла · ") + _fmt_int(ref) + " пак/с",
                     fontsize=9.5, color=PALETTE[4], va="top")
            ax2.set_ylim(0, max(ref * 1.25, (max(peaks) or 1) * 1.1,
                                (max(pps) or 1) * 1.1))
        else:
            ax2.set_ylim(0, max(max(pps), max(peaks) or 1, 1) * 1.15)

        leg2 = ax2.legend(loc="upper left", frameon=True, fontsize=10, facecolor=PANEL,
                          edgecolor=GRID, labelcolor=FG, framealpha=.9, borderpad=.7)
        leg2.set_zorder(5)

        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax2.xaxis.set_major_locator(MaxNLocator(8))

    now = get_moscow_now()
    head = title or ("Нагрузка за сутки" if hours <= 24 else f"Нагрузка за {hours} ч")
    fig.text(.085, .945, head, fontsize=15, fontweight="bold", color=FG)
    fig.text(.085, .905,
             f"обновлено {now.strftime('%H:%M')} МСК · "
             f"часовых срезов: {len(rows)}",
             fontsize=10, color=MUTED)

    fig.savefig(path, facecolor=BG)
    plt.close("all")
    return path

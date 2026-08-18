import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from database import db
import aiohttp
import time
from utils import get_moscow_now, dt_to_moscow, WG_API_URL

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
        async with aiohttp.ClientSession() as session:
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

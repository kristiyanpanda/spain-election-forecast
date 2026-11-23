"""Static figures (matplotlib). One consistent palette; every figure stamps the cut-off date.

Text goes through ``electoral.i18n`` (English or Spanish, set with ``i18n.set_lang``).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from electoral import i18n  # noqa: E402
from electoral.i18n import tr  # noqa: E402

COLORS = {
    "PP": "#1f6fb2", "PSOE": "#d7301f", "VOX": "#5aae61", "SUMAR": "#c51b8a", "PODEMOS": "#6a3d9a",
    "SALF": "#8c6d31", "ERC": "#f0a500", "JUNTS": "#20b2aa", "BILDU": "#2ca25f", "PNV": "#238b45",
    "BNG": "#74c476", "CC": "#fdae6b", "UP": "#6a3d9a", "CS": "#ff7f00", "IU": "#b30000",
    "UCD": "#8dd3c7", "CDS": "#fb8072", "MASPAIS": "#c2a5cf", "OTHER": "#999999",
}
BLOC_COLORS = {"left": "#d7301f", "right": "#1f6fb2", "periph_left": "#f0a500",
               "periph_right": "#20b2aa", "other": "#999999"}


INK, MUTED, RULE = "#1e2430", "#5b6473", "#c9ced6"


def _style():
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                         "legend.frameon": False})


def stamp(fig: plt.Figure, cutoff: str, source: str, fontsize: float = 7) -> None:
    from electoral import load_config

    cfg = load_config()
    label = cfg.get(f"provisional_label_{i18n.get_lang()}") or cfg.get("provisional_label")
    fig.text(0.01, 0.005, tr("Data cut-off {cutoff}. {source}", cutoff=i18n.date(cutoff), source=source),
             fontsize=fontsize, color="#555555")
    if label:
        fig.text(0.99, 0.995, label, fontsize=fontsize, color="#b00020", ha="right", va="top", weight="bold")


def _spread(values: list[float], gap: float) -> list[float]:
    """Move label positions apart so that neighbours are at least ``gap`` from each other."""
    order = np.argsort(values)
    out = np.array(values, dtype=float)
    for _ in range(50):
        moved = False
        for a, b in zip(order[:-1], order[1:]):
            d = out[b] - out[a]
            if d < gap - 1e-9:
                out[a] -= (gap - d) / 2
                out[b] += (gap - d) / 2
                moved = True
        if not moved:
            break
    return out.tolist()


def plot_trends(trend: pd.DataFrame, polls: pd.DataFrame, parties: list[str], path: Path,
                cutoff: str, title: str, election_date: str | None = None,
                election_result: dict[str, float] | None = None) -> None:
    """Latent share (median, 50 % and 90 % bands) with raw polls as dots, in two panels.

    Left: the whole cycle since the last election. Right: a zoom on the last months, where the
    dated events of ``config.yaml`` sit close together; there each event line carries its one-word
    name. The party key is a rounded box under the title; values at the cut-off are written at the
    right end of each line.
    """
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter

    from electoral import load_config

    _style()
    evs = [e for e in i18n.events(load_config()) if e["date"] >= trend.date.min()]
    cut = pd.Timestamp(cutoff)
    zoom0 = max(evs[0]["date"] - pd.Timedelta(days=12), cut - pd.Timedelta(days=150)) if evs \
        else cut - pd.Timedelta(days=120)
    parties = [p for p in parties if not trend[trend.party == p].empty]

    fig = plt.figure(figsize=(13, 5.9))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.85, 1], left=0.05, right=0.905, top=0.80, bottom=0.085,
                          wspace=0.035)
    ax = fig.add_subplot(gs[0])
    az = fig.add_subplot(gs[1], sharey=ax)
    top_zoom, top_all, ends = 0.0, 0.0, {}
    for p in parties:
        t = trend[trend.party == p]
        c = COLORS.get(p, "#444444")
        pp = polls[(polls.party == p) & polls.value.notna()]
        for a, size, alpha in ((ax, 6, 0.25), (az, 13, 0.38)):
            a.scatter(pp.fieldwork_end, pp.value, s=size, color=c, alpha=alpha, linewidths=0)
            a.fill_between(t.date, 100 * t.q05, 100 * t.q95, color=c, alpha=0.12, linewidth=0)
            a.fill_between(t.date, 100 * t.q25, 100 * t.q75, color=c, alpha=0.25, linewidth=0)
            a.plot(t.date, 100 * t.q50, color=c, lw=1.8)
        if election_result and p in election_result:
            ax.scatter([pd.Timestamp(election_date)], [100 * election_result[p]], marker="D", s=30,
                       color=c, edgecolor="black", zorder=5, clip_on=False)
        ends[p] = 100 * t.q50.iloc[-1]
        in_zoom = pp[(pp.fieldwork_end >= zoom0) & (pp.fieldwork_end <= cut)].value
        top_zoom = max(top_zoom, in_zoom.max() if len(in_zoom) else 0, 100 * t[t.date >= zoom0].q95.max())
        top_all = max(top_all, pp.value.max() if len(pp) else 0, 100 * t.q95.max())

    # room above the zoomed data for the event names
    ymax = max(top_all * 1.03, top_zoom / 0.78)
    ax.set_ylim(0, ymax)
    ax.set_xlim(trend.date.min() - pd.Timedelta(days=12), cut + pd.Timedelta(days=12))
    az.set_xlim(zoom0, cut + pd.Timedelta(days=4))
    ax.axvspan(zoom0, cut, color="#5b6473", alpha=0.07, linewidth=0)
    ax.annotate(tr("zoom") + " →", (zoom0, ymax), xytext=(-4, -4), textcoords="offset points", ha="right",
                va="top", fontsize=8, color=MUTED)
    for a in (ax, az):
        a.axvline(cut, color="black", lw=0.9, ls="--")
    prev = None
    for e in evs:
        ax.axvline(e["date"], color="#777777", lw=0.6, ls=":")
        az.axvline(e["date"], color="#777777", lw=0.8, ls=":")
        # the name sits left of its line, or right of it when the previous event is too close
        right = prev is not None and (e["date"] - prev).days < 5
        az.annotate(e["short"], (e["date"], ymax), xytext=(3 if right else -3, -4), textcoords="offset points",
                    rotation=90, ha="left" if right else "right", va="top", fontsize=8.5, color=INK,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 0.6})
        prev = e["date"]

    # values at the cut-off, right of the zoom panel
    ys = _spread([ends[p] for p in parties], ymax * 0.047)
    for p, y in zip(parties, ys):
        az.annotate("●", (cut, y), xytext=(10, 0), textcoords="offset points", color=COLORS.get(p, "#444444"),
                    fontsize=8, va="center", annotation_clip=False)
        az.annotate(f"{i18n.name(p, short=True)} {i18n.num(ends[p])}", (cut, y), xytext=(19, 0),
                    textcoords="offset points", color=INK, fontsize=9, va="center", annotation_clip=False)

    ax.set_ylabel(tr("% of valid vote"))
    ax.set_title(tr("Since the July 2023 election"), loc="left", fontsize=9, color=MUTED)
    az.set_title(tr("Zoom: {start} to {end}", start=i18n.date(zoom0, year=False), end=i18n.date(cut)),
                 loc="left", fontsize=9, color=MUTED)
    az.tick_params(labelleft=False)
    fmt = FuncFormatter(lambda x, _: i18n.month_year(mdates.num2date(x), short=True))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(fmt)
    az.xaxis.set_major_locator(mdates.MonthLocator())
    az.xaxis.set_major_formatter(fmt)
    if ymax < 10:   # small shares have decimal ticks: write them in the language's format
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: i18n.num(v)))

    left = ax.get_position().x0
    fig.text(left, 0.965, title, ha="left", va="top", fontsize=12.5, weight="bold", color=INK)
    handles = [plt.Line2D([], [], color=COLORS.get(p, "#444444"), lw=2.6, label=i18n.name(p)) for p in parties]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(left, 0.915), ncol=len(parties), fontsize=9.5,
               frameon=True, fancybox=True, facecolor="#f7f8fa", edgecolor=RULE, borderpad=0.7,
               columnspacing=1.6, handlelength=1.8)
    stamp(fig, cutoff, tr("Line: median of the latent share; bands: 50 % and 90 %; dots: polls; diamonds: 2023 result.")
          + " " + tr("Polls: Wikipedia (CC BY-SA 4.0) and CIS (cis.es); model: logit random walk + house effects."),
          fontsize=7.5)
    fig.savefig(path, bbox_inches="tight", dpi=160)
    plt.close(fig)


def plot_house_effects(he: pd.DataFrame, parties: list[str], path: Path, cutoff: str,
                       min_polls: int = 8) -> None:
    """Dot-and-whisker chart of house effects (pp) for pollsters with at least ``min_polls``."""
    _style()
    keep = he[he.n_polls >= min_polls]
    pollsters = keep.groupby("pollster")["n_polls"].first().sort_values(ascending=False).index.tolist()
    fig, axes = plt.subplots(1, len(parties), figsize=(2.1 * len(parties), 0.32 * len(pollsters) + 1.4),
                             sharey=True)
    for ax, p in zip(np.atleast_1d(axes), parties):
        sub = keep[keep.party == p].set_index("pollster").reindex(pollsters)
        y = np.arange(len(pollsters))
        ax.axvline(0, color="black", lw=0.8)
        ax.hlines(y, sub.q05_pp, sub.q95_pp, color=COLORS.get(p, "#444"), lw=1.2)
        ax.scatter(sub.mean_pp, y, color=COLORS.get(p, "#444"), s=18, zorder=3)
        ax.set_title(i18n.name(p), fontsize=9)
        ax.set_yticks(y)
        ax.set_yticklabels([f"{h} ({int(sub.loc[h, 'n_polls'])})" for h in pollsters], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel(tr("pp vs. average pollster"), fontsize=7)
    fig.suptitle(tr("House effects: how far each pollster sits from the pollster average (90 % interval)"),
                 x=0.01, ha="left", fontsize=10)
    stamp(fig, cutoff, tr("Zero-sum across pollsters per party; number of polls in brackets."))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_seat_distributions(seat_df: pd.DataFrame, parties: list[str], path: Path, cutoff: str,
                            last_seats: dict[str, int] | None = None) -> None:
    _style()
    fig, axes = plt.subplots(1, len(parties), figsize=(2.3 * len(parties), 2.8))
    for ax, p in zip(np.atleast_1d(axes), parties):
        s = seat_df[p]
        ax.hist(s, bins=np.arange(s.min() - 0.5, s.max() + 1.5), color=COLORS.get(p, "#444"), alpha=0.85)
        ax.axvline(s.median(), color="black", lw=1)
        if last_seats and p in last_seats:
            ax.axvline(last_seats[p], color="black", lw=1, ls=":")
        ax.set_title(tr("{party}: {lo}-{hi} (median {med})", party=i18n.name(p, short=True),
                        lo=int(s.quantile(.05)), hi=int(s.quantile(.95)), med=int(s.median())), fontsize=8)
        ax.set_yticks([])
    fig.suptitle(tr("Seat distributions (90 % interval); dotted = 2023 result"), x=0.01, ha="left", fontsize=10)
    stamp(fig, cutoff, tr("Monte Carlo over posterior vote shares and provincial swing noise; D'Hondt in 52 districts."))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_backtest(details: pd.DataFrame, path: Path, cutoff: str, labels: dict[str, str]) -> None:
    """Per election: model 90 % seat interval vs. actual, poll average and last-election baselines."""
    _style()
    cycles = list(dict.fromkeys(details.cycle))
    fig, axes = plt.subplots(1, len(cycles), figsize=(3.6 * len(cycles), 3.6), sharey=False)
    for ax, c in zip(np.atleast_1d(axes), cycles):
        d = details[details.cycle == c]
        d = d[(d.actual_seats > 0) | (d.seats_q50 > 0)].sort_values("actual_seats", ascending=False).head(7)
        x = np.arange(len(d))
        ax.vlines(x, d.seats_q05, d.seats_q95, color="#1f6fb2", lw=6, alpha=0.35, label=tr("model 90 % interval"))
        ax.scatter(x, d.seats_q50, color="#1f6fb2", s=26, zorder=3, label=tr("model median"))
        ax.scatter(x + 0.22, d.seats_poll_avg, marker="^", color="#f0a500", s=26, zorder=3,
                   label=tr("30-day poll average"))
        ax.scatter(x - 0.22, d.seats_last_election, marker="s", color="#999999", s=22, zorder=3,
                   label=tr("last election"))
        ax.scatter(x, d.actual_seats, marker="_", color="black", s=260, lw=2, zorder=4, label=tr("actual"))
        ax.set_xticks(x)
        ax.set_xticklabels(d.party, fontsize=8)
        ax.set_title(tr(labels.get(c, c)), fontsize=9, loc="left")
    np.atleast_1d(axes)[0].set_ylabel(tr("seats"))
    np.atleast_1d(axes)[0].legend(fontsize=7, loc="upper right")
    fig.suptitle(tr("Backtest: forecasts made 30 days before each election vs. the result"), x=0.01, ha="left",
                 fontsize=11)
    stamp(fig, cutoff, tr("Only polls available at the time; anchored on the previous election."))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_bloc_majority(seat_df: pd.DataFrame, blocs: dict[str, list[str]], path: Path, cutoff: str) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(7, 3.2))
    for bloc, members in blocs.items():
        m = [p for p in members if p in seat_df]
        tot = seat_df[m].sum(axis=1)
        share = f"{(tot >= 176).mean():.0%}".replace("%", " %")
        ax.hist(tot, bins=np.arange(tot.min() - 0.5, tot.max() + 1.5), alpha=0.55,
                label=tr("{name}: P(>=176) = {p}", name=tr(bloc), p=share))
    ax.axvline(176, color="black", lw=1)
    ax.text(176, ax.get_ylim()[1] * 0.55, tr(" 176 = absolute majority"), fontsize=8, va="top")
    ax.set_xlabel(tr("seats"))
    ax.set_yticks([])
    ax.legend(fontsize=8, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=1)
    ax.set_title(tr("Bloc seat totals"), loc="left", fontsize=11, pad=34)
    stamp(fig, cutoff, tr("Blocs defined in data/party_map_polls.yaml."))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------- hemicycle
# left-to-right seating order and display names for the Congress chart
HEMICYCLE_ORDER = ["PODEMOS", "SUMAR", "PSOE", "ERC", "BILDU", "BNG", "AA", "CC", "OTHER", "PNV", "JUNTS",
                   "PP", "UPN", "VOX", "SALF"]
HEMICYCLE_NAMES = {"PODEMOS": "Podemos", "SUMAR": "Frente Amplio", "PSOE": "PSOE", "ERC": "ERC",
                   "BILDU": "EH Bildu", "BNG": "BNG", "AA": "Adelante Andalucía", "CC": "CC",
                   "OTHER": "Others", "PNV": "PNV", "JUNTS": "Junts", "PP": "PP", "UPN": "UPN",
                   "VOX": "Vox", "SALF": "SALF"}
# Bildu, PNV and BNG share greens with Vox elsewhere; the seat chart needs them apart
HEMICYCLE_COLORS = {**COLORS, "BILDU": "#a8b820", "PNV": "#1b5e20", "BNG": "#6fa8dc", "AA": "#c9a66b",
                    "UPN": "#3b7ac6"}


def hemicycle_name(party: str) -> str:
    return tr("Others") if party == "OTHER" else HEMICYCLE_NAMES.get(party, party)


def expected_seats(seat_draws: pd.DataFrame, total: int = 350) -> pd.Series:
    """Mean seats per party over the simulations, rounded by largest remainder to sum to ``total``.

    This is a summary for display (no single simulation need look like it), in seating order.
    """
    mean = seat_draws.mean()
    mean = mean * total / mean.sum()
    base = np.floor(mean).astype(int)
    rest = total - base.sum()
    base[(mean - base).sort_values(ascending=False).index[:rest]] += 1
    order = [p for p in HEMICYCLE_ORDER if p in base] + [p for p in base.index if p not in HEMICYCLE_ORDER]
    return base[order][base[order] > 0]


def hemicycle_layout(n: int = 350, rows: int = 12, inner: float = 0.42) -> pd.DataFrame:
    """Seat positions of a semicircular chamber, ordered left to right (x, y, row).

    Each row's capacity is proportional to its radius; seats are then sorted by angle so that
    consecutive seats form wedges spanning all rows, as in the usual parliament diagrams.
    """
    radii = np.linspace(inner, 1.0, rows)
    cap = radii / radii.sum() * n
    k = np.floor(cap).astype(int)
    k[np.argsort(-(cap - k))[: n - k.sum()]] += 1
    pts = []
    for r, m in zip(radii, k):
        ang = np.pi * (1 - (np.arange(m) + 0.5) / m)  # half-step offset: rows do not share angles
        pts += [(a, r) for a in ang]
    df = pd.DataFrame(pts, columns=["angle", "radius"]).sort_values(["angle", "radius"], ascending=[False, True])
    df["x"], df["y"] = df.radius * np.cos(df.angle), df.radius * np.sin(df.angle)
    return df.reset_index(drop=True)


def plot_hemicycle(seats: pd.Series, path: Path, cutoff: str, title: str, subtitle: str,
                   note: str = "") -> None:
    """Congress seat chart: one dot per deputy, parties in seating order, 176-seat marker."""
    _style()
    lay = hemicycle_layout(int(seats.sum()))
    lay["party"] = np.repeat(seats.index.values, seats.values)
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    for p in seats.index:
        d = lay[lay.party == p]
        ax.scatter(d.x, d.y, s=62, color=HEMICYCLE_COLORS.get(p, "#999999"), linewidths=0)
    ax.plot([0, 0], [0.32, 1.06], color="black", lw=0.8, ls="--")
    ax.text(0, 1.08, "176", ha="center", va="bottom", fontsize=8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.08, 1.08)
    ax.set_ylim(-0.04, 1.15)
    handles = [plt.Line2D([], [], marker="o", ls="", color=HEMICYCLE_COLORS.get(p, "#999999"), markersize=8,
                          label=f"{hemicycle_name(p)} {n}")
               for p, n in seats.sort_values(ascending=False, kind="stable").items()]  # legend: most seats first
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), ncol=1, fontsize=9,
              handletextpad=0.3, labelspacing=0.55)
    fig.text(0.02, 0.955, title, ha="left", va="top", fontsize=13, weight="bold")
    fig.text(0.02, 0.905, subtitle, ha="left", va="top", fontsize=8.5, color="#444444", wrap=True)
    stamp(fig, cutoff, note)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

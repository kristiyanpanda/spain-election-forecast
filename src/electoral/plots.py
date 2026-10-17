"""Static figures (matplotlib). One consistent palette; every figure stamps the cut-off date."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

COLORS = {
    "PP": "#1f6fb2", "PSOE": "#d7301f", "VOX": "#5aae61", "SUMAR": "#c51b8a", "PODEMOS": "#6a3d9a",
    "SALF": "#8c6d31", "ERC": "#f0a500", "JUNTS": "#20b2aa", "BILDU": "#2ca25f", "PNV": "#238b45",
    "BNG": "#74c476", "CC": "#fdae6b", "UP": "#6a3d9a", "CS": "#ff7f00", "IU": "#b30000",
    "UCD": "#8dd3c7", "CDS": "#fb8072", "MASPAIS": "#c2a5cf", "OTHER": "#999999",
}
BLOC_COLORS = {"left": "#d7301f", "right": "#1f6fb2", "periph_left": "#f0a500",
               "periph_right": "#20b2aa", "other": "#999999"}


def _style():
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                         "legend.frameon": False})


def stamp(fig: plt.Figure, cutoff: str, source: str) -> None:
    from electoral import load_config

    label = load_config().get("provisional_label")
    fig.text(0.01, 0.005, f"Data cut-off {cutoff}. {source}", fontsize=7, color="#555555")
    if label:
        fig.text(0.99, 0.995, label, fontsize=7, color="#b00020", ha="right", va="top", weight="bold")


def mark_events(ax, events: dict | None, start: pd.Timestamp) -> None:
    """Numbered dotted lines for dated events (config ``events``), keyed in the lower-left corner."""
    if not events:
        return
    ymax = ax.get_ylim()[1]
    key = []
    for i, (day, label) in enumerate(sorted(events.items()), 1):
        d = pd.Timestamp(day)
        if d < start:
            continue
        ax.axvline(d, color="#777777", lw=0.7, ls=":")
        ax.annotate(str(i), (d, ymax), xytext=(-3, -3 - 8 * (i % 2)), textcoords="offset points",
                    ha="right", va="top", fontsize=7, color="#444444", weight="bold")
        key.append(f"{i} {label} ({d.day} {d.strftime('%b')})")
    ax.text(0.01, 0.02, "   ".join(key), transform=ax.transAxes, fontsize=7, color="#444444",
            bbox={"facecolor": "white", "edgecolor": "#cccccc", "boxstyle": "round,pad=0.3"})


def plot_trends(trend: pd.DataFrame, polls: pd.DataFrame, parties: list[str], path: Path,
                cutoff: str, title: str, election_date: str | None = None,
                election_result: dict[str, float] | None = None) -> None:
    """Latent share ribbons (50 % and 90 %) with raw polls as dots, for the listed parties."""
    _style()
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for p in parties:
        tr = trend[trend.party == p]
        if tr.empty:
            continue
        c = COLORS.get(p, "#444444")
        pp = polls[(polls.party == p) & polls.value.notna()]
        ax.scatter(pp.fieldwork_end, pp.value, s=6, color=c, alpha=0.25, linewidths=0)
        ax.fill_between(tr.date, 100 * tr.q05, 100 * tr.q95, color=c, alpha=0.12, linewidth=0)
        ax.fill_between(tr.date, 100 * tr.q25, 100 * tr.q75, color=c, alpha=0.25, linewidth=0)
        ax.plot(tr.date, 100 * tr.q50, color=c, lw=1.6, label=p)
        ax.annotate(f"{p} {100 * tr.q50.iloc[-1]:.1f}", (tr.date.iloc[-1], 100 * tr.q50.iloc[-1]),
                    xytext=(4, 0), textcoords="offset points", color=c, fontsize=8, va="center")
        if election_result and p in election_result:
            ax.scatter([pd.Timestamp(election_date)], [100 * election_result[p]], marker="D", s=28,
                       color=c, edgecolor="black", zorder=5)
    ax.axvline(pd.Timestamp(cutoff), color="black", lw=0.8, ls="--")
    ax.set_ylabel("% of valid vote")
    ax.set_title(title, loc="left", fontsize=11)
    ax.set_xlim(trend.date.min(), trend.date.max() + pd.Timedelta(days=60))
    from electoral import load_config

    mark_events(ax, load_config().get("events"), trend.date.min())
    ax.legend(loc="upper left", ncol=len(parties), fontsize=8)
    stamp(fig, cutoff, "Polls: Wikipedia (CC BY-SA 4.0) and CIS (cis.es); model: logit random walk + house effects.")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
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
        ax.set_title(p, fontsize=9)
        ax.set_yticks(y)
        ax.set_yticklabels([f"{h} ({int(sub.loc[h, 'n_polls'])})" for h in pollsters], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("pp vs. average pollster", fontsize=7)
    fig.suptitle("House effects: how far each pollster sits from the pollster average (90 % interval)",
                 x=0.01, ha="left", fontsize=10)
    stamp(fig, cutoff, "Zero-sum across pollsters per party; number of polls in brackets.")
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
        ax.set_title(f"{p}: {int(s.quantile(.05))}-{int(s.quantile(.95))} (median {int(s.median())})", fontsize=8)
        ax.set_yticks([])
    fig.suptitle("Seat distributions (90 % interval); dotted = 2023 result", x=0.01, ha="left", fontsize=10)
    stamp(fig, cutoff, "Monte Carlo over posterior vote shares and provincial swing noise; D'Hondt in 52 districts.")
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
        ax.vlines(x, d.seats_q05, d.seats_q95, color="#1f6fb2", lw=6, alpha=0.35, label="model 90 % interval")
        ax.scatter(x, d.seats_q50, color="#1f6fb2", s=26, zorder=3, label="model median")
        ax.scatter(x + 0.22, d.seats_poll_avg, marker="^", color="#f0a500", s=26, zorder=3, label="30-day poll average")
        ax.scatter(x - 0.22, d.seats_last_election, marker="s", color="#999999", s=22, zorder=3, label="last election")
        ax.scatter(x, d.actual_seats, marker="_", color="black", s=260, lw=2, zorder=4, label="actual")
        ax.set_xticks(x)
        ax.set_xticklabels(d.party, fontsize=8)
        ax.set_title(labels.get(c, c), fontsize=9, loc="left")
    np.atleast_1d(axes)[0].set_ylabel("seats")
    np.atleast_1d(axes)[0].legend(fontsize=7, loc="upper right")
    fig.suptitle("Backtest: forecasts made 30 days before each election vs. the result", x=0.01, ha="left", fontsize=11)
    stamp(fig, cutoff, "Only polls available at the time; anchored on the previous election.")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_bloc_majority(seat_df: pd.DataFrame, blocs: dict[str, list[str]], path: Path, cutoff: str) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(7, 3.2))
    for name, members in blocs.items():
        m = [p for p in members if p in seat_df]
        tot = seat_df[m].sum(axis=1)
        ax.hist(tot, bins=np.arange(tot.min() - 0.5, tot.max() + 1.5), alpha=0.55,
                label=f"{name}: P(>=176) = {(tot >= 176).mean():.0%}")
    ax.axvline(176, color="black", lw=1)
    ax.text(176, ax.get_ylim()[1] * 0.55, " 176 = absolute majority", fontsize=8, va="top")
    ax.set_xlabel("seats")
    ax.set_yticks([])
    ax.legend(fontsize=8, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=1)
    ax.set_title("Bloc seat totals", loc="left", fontsize=11, pad=34)
    stamp(fig, cutoff, "Blocs defined in data/party_map_polls.yaml.")
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
    fig, ax = plt.subplots(figsize=(8.2, 5.6))
    for p in seats.index:
        d = lay[lay.party == p]
        ax.scatter(d.x, d.y, s=46, color=HEMICYCLE_COLORS.get(p, "#999999"), linewidths=0)
    ax.plot([0, 0], [0.32, 1.06], color="black", lw=0.8, ls="--")
    ax.text(0, 1.08, "176", ha="center", va="bottom", fontsize=8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.08, 1.08)
    ax.set_ylim(-0.28, 1.15)
    handles = [plt.Line2D([], [], marker="o", ls="", color=HEMICYCLE_COLORS.get(p, "#999999"), markersize=8,
                          label=f"{HEMICYCLE_NAMES.get(p, p)} {n}") for p, n in seats.items()]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=5, fontsize=8,
              handletextpad=0.2, columnspacing=1.0)
    fig.text(0.02, 0.955, title, ha="left", va="top", fontsize=13, weight="bold")
    fig.text(0.02, 0.905, subtitle, ha="left", va="top", fontsize=8.5, color="#444444", wrap=True)
    stamp(fig, cutoff, note)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

"""The Congress as it stands against the 29N forecast: party by party and bloc by bloc.

Membership of the XV Legislature's parliamentary groups comes from congreso.es (each deputy's
start and end date in every group, the "Altas y bajas" view of each group's page). After the
dissolution of 6 October 2026 the site only shows the Diputación Permanente as the current
composition, so the chamber is rebuilt from those dates at two moments:

- ``investiture``: 16 November 2023, the day Sánchez was invested with 179 votes;
- ``dissolution``: 5 October 2026, the last day of the full chamber.

Seats are counted by party, not by group: the Mixed Group holds Podemos, BNG, CC, UPN, Compromís
(Més) and two deputies who left their parties (Ábalos, ex-PSOE, until January 2026; Ortega Smith,
ex-Vox, from July 2026). The comparison with the forecast uses the base-case seat draws
(``outputs/seat_draws_29n_split.parquet``); no model is refitted.

Writes ``data/processed/congreso_xv_groups.csv`` (tidy membership), ``outputs/chamber_29n.csv``
(per party), ``outputs/chamber_blocs_29n.csv`` and three figures per language.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from electoral import ROOT, i18n, load_config  # noqa: E402
from electoral.i18n import tr  # noqa: E402

URL = ("https://www.congreso.es/es/grupos/composicion-en-la-legislatura?p_p_id=grupos&p_p_lifecycle=2"
       "&p_p_state=normal&p_p_mode=view&p_p_resource_id=diputadosSearch&p_p_cacheability=cacheLevelPage"
       "&_grupos_idLegislatura=XV&_grupos_mostrarFicha=true&_grupos_gruposView=true&_grupos_idGrupo={gid}")
GROUPS = {201: "PP", 202: "PSOE", 203: "VOX", 204: "SUMAR", 205: "JUNTS", 206: "ERC", 207: "BILDU",
          208: "PNV", 209: "MIXTO"}
SNAPSHOTS = {"investiture": "2023-11-16", "dissolution": "2026-10-05"}

# party of a deputy where the group does not say it (codParlamentario -> party id)
PERSON_PARTY = {
    262: "PODEMOS", 292: "PODEMOS", 33: "PODEMOS", 169: "PODEMOS", 322: "PODEMOS",  # Belarra, Sánchez
    # Serna, Santana, Velarde, Verstrynge: elected on the Sumar list, Mixed Group from 5 Dec 2023
    149: "UPN", 238: "BNG", 38: "CC",          # Catalán, Rego, Valido (Mixed Group from the start)
    164: "SUMAR",                              # Micó (Més-Compromís): Sumar list, Mixed Group from Jul 2025
    111: "PSOE", 110: "PSOE", 62: "PSOE", 171: "PSOE",  # lent to Junts, 28 Aug - 1 Sep 2023
    269: "SUMAR", 332: "SUMAR",                # Comuns deputies lent to ERC, 28 Aug - 4 Sep 2023
}
# deputies who sat in the Mixed Group after leaving their party
DEFECTORS = {(127, "MIXTO"): "EX_PSOE", (325, "MIXTO"): "EX_VOX"}   # Ábalos, Ortega Smith

# the parties that voted yes on 16 Nov 2023, under their 29N ids (SUMAR = Sumar -> Frente Amplio
# lineage incl. Compromís-Front Valencià; PODEMOS ran inside Sumar in 2023)
INVESTITURE_BLOC = ["PSOE", "SUMAR", "PODEMOS", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"]
RIGHT_BLOC = ["PP", "VOX", "UPN", "SALF", "EX_VOX"]
# seating order for the comparison chart: the investiture bloc on the left, the right on the right
ORDER = ["PODEMOS", "SUMAR", "PSOE", "ERC", "BILDU", "BNG", "CC", "PNV", "JUNTS",
         "AA", "OTHER", "EX_PSOE", "SALF", "EX_VOX", "UPN", "PP", "VOX"]
EXTRA_NAMES = {"EX_VOX": "Ortega Smith (ex-Vox)", "EX_PSOE": "Ábalos (ex-PSOE)"}
EXTRA_COLORS = {"EX_VOX": "#a9d3a0", "EX_PSOE": "#f4a582"}

# events of the legislature for the CIS chart (dates checked against the press, see the docs)
EVENTS = {
    "2023-11-16": ("Investiture", "Investidura"),
    "2025-06-12": ("Cerdán report", "Informe Cerdán"),
    "2025-10-27": ("Junts breaks", "Ruptura Junts"),
    "2025-12-21": ("Extremadura", "Extremadura"),
    "2026-05-17": ("Andalucía", "Andalucía"),
    "2026-07-30": ("Ceuta", "Ceuta"),
    "2026-10-05": ("Dissolution", "Disolución"),
}


# ----------------------------------------------------------------------------- data
def fetch(refresh: bool = False) -> pd.DataFrame:
    """Every membership spell of the XV Legislature's groups, cached in data/raw/congreso/."""
    import requests

    cfg = load_config()
    raw = ROOT / "data/raw/congreso"
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for gid, group in GROUPS.items():
        f = raw / f"grupo_{gid}.json"
        if refresh or not f.exists():
            r = requests.post(URL.format(gid=gid), data={"_grupos_tipoAct": "false"}, timeout=60,
                              headers={"User-Agent": "Mozilla/5.0 (spain-election-forecast)"})
            r.raise_for_status()
            f.write_text(r.content.decode("utf-8"), encoding="utf-8")
        for x in json.loads(f.read_text(encoding="utf-8"))["data"]:
            rows.append({"group_id": gid, "group": group, "cod": int(x["codParlamentario"]),
                         "name": x["apellidosNombre"], "start": x["fchAlta"], "end": x["fchBaja"] or None})
    df = pd.DataFrame(rows)
    for c in ("start", "end"):
        df[c] = pd.to_datetime(df[c], format="%d/%m/%Y")
    df["party"] = [DEFECTORS.get((c, g)) or PERSON_PARTY.get(c) or (g if g != "MIXTO" else None)
                   for c, g in zip(df.cod, df.group)]
    if df.party.isna().any():
        raise ValueError(f"Mixed Group deputies without a party: {df[df.party.isna()].name.tolist()}")
    out = ROOT / cfg["paths"]["processed"] / "congreso_xv_groups.csv"
    df.sort_values(["group_id", "name"]).to_csv(out, index=False, date_format="%Y-%m-%d")
    return df


def load_membership() -> pd.DataFrame:
    """The tidy membership table (fetched if it is not there yet)."""
    f = ROOT / load_config()["paths"]["processed"] / "congreso_xv_groups.csv"
    if not f.exists():
        return fetch()
    return pd.read_csv(f, parse_dates=["start", "end"])


def composition(members: pd.DataFrame, day: str, by: str = "party") -> pd.Series:
    """Seats per party (or group) held on ``day``: spells that started by then and had not ended."""
    d = pd.Timestamp(day)
    on = members[(members.start <= d) & (members.end.isna() | (members.end > d))]
    return on.groupby(by).size().sort_values(ascending=False)


def summarise(members: pd.DataFrame, draws: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per party and per bloc: seats at the investiture and the dissolution against the forecast."""
    inv = composition(members, SNAPSHOTS["investiture"])
    dis = composition(members, SNAPSHOTS["dissolution"])
    parties = [p for p in ORDER if p in set(inv.index) | set(dis.index) | set(draws.columns)]
    rows = []
    for p in parties:
        x = draws[p] if p in draws else pd.Series(0, index=draws.index)
        now = int(dis.get(p, 0))
        rows.append({"party": p, "investiture_2023": int(inv.get(p, 0)), "dissolution_2026": now,
                     "forecast_mean": round(float(x.mean()), 2), "forecast_q05": int(x.quantile(0.05)),
                     "forecast_q50": int(x.median()), "forecast_q95": int(x.quantile(0.95)),
                     "change_median": int(x.median()) - now, "p_more": round(float((x > now).mean()), 3),
                     "p_fewer": round(float((x < now).mean()), 3),
                     "bloc": "investiture" if p in INVESTITURE_BLOC else "right" if p in RIGHT_BLOC else "other"})
    per_party = pd.DataFrame(rows)

    def bloc_row(label, members_now, members_29n, cols_inv=None):
        x = draws[[p for p in members_29n if p in draws]].sum(axis=1)
        return {"bloc": label,
                "investiture_2023": int(inv.reindex(cols_inv or members_now).fillna(0).sum()),
                "dissolution_2026": int(dis.reindex(members_now).fillna(0).sum()),
                "forecast_q05": int(x.quantile(0.05)), "forecast_q50": int(x.median()),
                "forecast_q95": int(x.quantile(0.95)), "p_176": round(float((x >= 176).mean()), 3)}

    no_junts = [p for p in INVESTITURE_BLOC if p != "JUNTS"]
    blocs = pd.DataFrame([
        bloc_row("2023 investiture bloc", INVESTITURE_BLOC, INVESTITURE_BLOC),
        bloc_row("2023 investiture bloc + Adelante Andalucía", INVESTITURE_BLOC, INVESTITURE_BLOC + ["AA"]),
        bloc_row("2023 investiture bloc without Junts", no_junts, no_junts),
        bloc_row("PP + Vox (+ UPN, SALF)", RIGHT_BLOC, ["PP", "VOX", "UPN", "SALF"]),
    ])
    return per_party, blocs


# ----------------------------------------------------------------------------- figures
def _name(p: str) -> str:
    from electoral.plots import hemicycle_name

    if p in EXTRA_NAMES:
        return tr(EXTRA_NAMES[p])
    return hemicycle_name(p)


def _color(p: str) -> str:
    from electoral.plots import HEMICYCLE_COLORS

    return EXTRA_COLORS.get(p) or HEMICYCLE_COLORS.get(p, "#999999")


def _hemicycle(ax, seats: pd.Series, title: str, bloc_text: str) -> None:
    """One chamber on ``ax`` with arcs over the investiture bloc (left) and the right bloc."""
    from electoral.plots import hemicycle_layout

    seats = seats[[p for p in ORDER if seats.get(p, 0) > 0]]
    lay = hemicycle_layout(int(seats.sum()))
    lay["party"] = np.repeat(seats.index.values, seats.values)
    for p in seats.index:
        d = lay[lay.party == p]
        ax.scatter(d.x, d.y, s=30, color=_color(p), linewidths=0)
    for members, colour, label_x, ha in ((INVESTITURE_BLOC, "#8c1d18", -1.0, "left"),
                                         (RIGHT_BLOC, "#123f73", 1.0, "right")):
        ang = lay[lay.party.isin(members)].angle
        if ang.empty:
            continue
        lo, hi = ang.min() - 0.006, ang.max() + 0.006
        t = np.linspace(lo, hi, 200)
        ax.plot(1.07 * np.cos(t), 1.07 * np.sin(t), color=colour, lw=2.2, solid_capstyle="butt")
    ax.plot([0, 0], [0.32, 1.1], color="black", lw=0.8, ls="--")
    ax.text(0, 1.12, "176", ha="center", va="bottom", fontsize=8)
    ax.set_title(title, fontsize=11, weight="bold", loc="center", pad=4)
    ax.text(0, -0.05, bloc_text, ha="center", va="top", fontsize=9.5, color="#1e2430")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.12, 1.12)
    ax.set_ylim(-0.14, 1.2)


def plot_comparison(per_party: pd.DataFrame, blocs: pd.DataFrame, draws: pd.DataFrame, path, cfg) -> None:
    """Two chambers side by side: Congress at the dissolution and the expected 29N Congress."""
    from electoral.plots import _style, expected_seats, stamp

    _style()
    now = per_party.set_index("party")["dissolution_2026"]
    exp = expected_seats(draws)
    b = blocs.set_index("bloc")
    inv_now, right_now = b.loc["2023 investiture bloc", "dissolution_2026"], b.loc["PP + Vox (+ UPN, SALF)", "dissolution_2026"]
    inv_exp = int(exp.reindex(INVESTITURE_BLOC).fillna(0).sum())
    right_exp = int(exp.reindex(RIGHT_BLOC).fillna(0).sum())
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))
    _hemicycle(axes[0], now, tr("Congress at the dissolution ({date})", date=i18n.date(SNAPSHOTS["dissolution"])),
               tr("2023 investiture bloc {a}  ·  PP + Vox + UPN + ex-Vox {b}", a=inv_now, b=right_now))
    _hemicycle(axes[1], exp, tr("Forecast Congress, {date}", date=i18n.date(cfg["election_date"])),
               tr("2023 investiture bloc {a}  ·  PP + Vox (+ UPN, SALF) {b}", a=inv_exp, b=right_exp))
    present = [p for p in ORDER if now.get(p, 0) > 0 or exp.get(p, 0) > 0]
    handles = [plt.Line2D([], [], marker="o", ls="", color=_color(p), markersize=7,
                          label=f"{_name(p)} {now.get(p, 0)} → {exp.get(p, 0)}") for p in present]
    handles += [plt.Line2D([], [], color="#8c1d18", lw=2.2, label=tr("arc: 2023 investiture bloc")),
                plt.Line2D([], [], color="#123f73", lw=2.2, label=tr("arc: PP + Vox and allies"))]
    fig.legend(handles=handles, loc="upper center", ncol=6, fontsize=8, bbox_to_anchor=(0.5, 0.2),
               handletextpad=0.3, columnspacing=1.0)
    fig.text(0.01, 0.97, tr("From the Congress that invested Sánchez to the 29 November forecast"),
             ha="left", va="top", fontsize=13, weight="bold")
    fig.text(0.01, 0.92, tr("Left: seats by party on the last day of the full chamber, from each group's "
                             "membership dates on congreso.es. Right: expected seats, base case (mean of "
                             "10,000 simulations, rounded to 350). Legend: dissolution → forecast."),
             ha="left", va="top", fontsize=8.5, color="#444444")
    fig.subplots_adjust(top=0.84, bottom=0.21, wspace=0.04)
    stamp(fig, cfg["cutoff_date"], tr("Congress: congreso.es (groups, XV Legislature). Seats: model forecast, not a result."))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_change(per_party: pd.DataFrame, blocs: pd.DataFrame, path, cfg) -> None:
    """Dumbbells: seats at the dissolution (grey) against the forecast median and 90 % range."""
    from electoral.plots import _style, stamp

    _style()
    pp = per_party[(per_party.dissolution_2026 > 0) | (per_party.forecast_q50 > 0)].copy()
    pp = pp.sort_values(["change_median", "forecast_q50"], ascending=[True, True])
    bl = blocs[blocs.bloc.isin(["2023 investiture bloc", "PP + Vox (+ UPN, SALF)"])].iloc[::-1]
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(9.5, 8.6), gridspec_kw={"height_ratios": [1.1, 5.2]})
    for ax, df, label in ((ax0, bl, "bloc"), (ax1, pp, "party")):
        ys = np.arange(len(df))
        for y, (_, r) in zip(ys, df.iterrows()):
            c = "#8c1d18" if label == "bloc" and r.bloc.startswith("2023") else \
                "#123f73" if label == "bloc" else _color(r.party)
            ax.plot([r.forecast_q05, r.forecast_q95], [y, y], color=c, lw=3, alpha=0.35, solid_capstyle="round")
            ax.plot([r.dissolution_2026, r.forecast_q50], [y, y], color="#9aa1ab", lw=1)
            ax.scatter([r.dissolution_2026], [y], s=36, color="white", edgecolors="#5b6473", zorder=3)
            ax.scatter([r.forecast_q50], [y], s=48, color=c, zorder=4)
            delta = r.forecast_q50 - r.dissolution_2026
            ax.text(max(r.forecast_q95, r.dissolution_2026) + 2, y, f"{delta:+d}", va="center", fontsize=8.5,
                    color="#1e2430", weight="bold")
        names = [tr(r.bloc) for _, r in df.iterrows()] if label == "bloc" else [_name(p) for p in df.party]
        ax.set_yticks(ys, names)
        ax.grid(axis="y", alpha=0)
    ax0.axvline(176, color="black", lw=0.8, ls="--")
    ax0.text(177, 0.5, tr(" 176 = absolute majority"), fontsize=7.5, va="center")
    ax0.set_ylim(-0.6, 1.6)
    ax0.set_xlim(100, 235)
    ax1.set_xlim(-3, 160)
    ax1.set_xlabel(tr("seats"))
    fig.text(0.01, 0.975, tr("Seat by seat: the chamber at the dissolution against the 29 November forecast"),
             ha="left", va="top", fontsize=12.5, weight="bold")
    fig.text(0.01, 0.945, tr("Hollow dot: seats on {date} (congreso.es). Solid dot: forecast median; "
                             "band: 90 % range; number: change in the median.", date=i18n.date(SNAPSHOTS["dissolution"])),
             ha="left", va="top", fontsize=8.5, color="#444444")
    fig.subplots_adjust(top=0.9, hspace=0.12, left=0.26)
    stamp(fig, cfg["cutoff_date"], tr("Congress: congreso.es. Forecast: base case, 10,000 simulations."))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_cis(cis: pd.DataFrame, path, cfg) -> None:
    """CIS over the legislature: the official estimate against our recall-weighted microdata reading."""
    from electoral.plots import COLORS, _style, stamp

    _style()
    d = cis[cis.fieldwork_start >= "2023-08-01"].copy()
    d["date"] = pd.to_datetime(d.fieldwork_start)
    d["micro_SUMAR"] = d.micro_SUMAR.fillna(d.micro_FA + d.micro_FV)
    d["official_SUMAR"] = d.official_SUMAR.fillna(d.official_FA + d.official_FV)
    nat = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "results_national.parquet")
    res = nat[nat.election == "202307"].set_index("party")["share_valid"] * 100
    vote = pd.read_csv(ROOT / cfg["paths"]["outputs"] / "vote_summary_29n.csv", index_col=0)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    for ax, kind, title in ((axes[0], "official", tr("CIS official estimate")),
                            (axes[1], "micro", tr("Same CIS microdata, re-weighted by 2023 recall (likely voters)"))):
        for p in ("PP", "PSOE", "VOX", "SUMAR"):
            s = d[["date", f"{kind}_{p}"]].dropna()
            ax.plot(s.date, s[f"{kind}_{p}"], color=COLORS[p], lw=1.8, marker="o", ms=2.5,
                    label=i18n.name(p, short=True))
            ax.scatter([pd.Timestamp(cfg["last_election"])], [res[p]], marker="D", s=30, color=COLORS[p], zorder=4)
            ax.errorbar([pd.Timestamp(cfg["election_date"])], [vote.loc[p, "q50"] * 100],
                        yerr=[[100 * (vote.loc[p, "q50"] - vote.loc[p, "q05"])], [100 * (vote.loc[p, "q95"] - vote.loc[p, "q50"])]],
                        fmt="s", ms=5, color=COLORS[p], capsize=2, lw=1)
        for n, day in enumerate(EVENTS, 1):
            ax.axvline(pd.Timestamp(day), color="#9aa1ab", lw=0.7, ls=":")
            ax.text(pd.Timestamp(day), 40.4, str(n), fontsize=7.5, color="#5b6473", ha="center", va="bottom",
                    weight="bold")
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: i18n.month_year(mdates.num2date(v), short=True)))
        ax.set_title(title, fontsize=10, loc="left", pad=16)
        ax.set_ylim(0, 40)
        ax.set_xlim(pd.Timestamp("2023-06-15"), pd.Timestamp("2026-12-20"))
    axes[0].set_ylabel(tr("% of valid vote"))
    axes[1].legend(loc="lower left", ncol=4, fontsize=8)
    fig.text(0.01, 0.985, tr("The CIS barometers across the legislature, read two ways"), ha="left", va="top",
             fontsize=13, weight="bold")
    fig.text(0.01, 0.95, tr("Dots: each barometer and pre-election study (cis.es). Diamonds: July 2023 result. "
                             "Squares: model forecast for 29 November with 90 % range. Sumar line from Oct 2026: "
                             "Frente Amplio + Compromís-Front Valencià."), ha="left", va="top", fontsize=8.5,
             color="#444444")
    lang = 1 if i18n.get_lang() == "es" else 0
    fig.text(0.01, 0.915, "   ".join(f"{n} {v[lang]} ({i18n.date(d, short=True)})" for n, (d, v) in
                                   enumerate(EVENTS.items(), 1)), ha="left", va="top", fontsize=8, color="#5b6473")
    fig.subplots_adjust(top=0.82, wspace=0.05)
    stamp(fig, cfg["cutoff_date"], tr("Source: CIS (cis.es), estimates and microdata; re-weighting in src/electoral/cis_microdata.py."))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------- entry point
def main(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    members = fetch(refresh) if refresh else load_membership()
    draws = pd.read_parquet(out / "seat_draws_29n_split.parquet")
    per_party, blocs = summarise(members, draws)
    for day in SNAPSHOTS.values():
        if composition(members, day).sum() != 350:
            raise ValueError(f"the chamber on {day} does not add up to 350")
    per_party.to_csv(out / "chamber_29n.csv", index=False)
    blocs.to_csv(out / "chamber_blocs_29n.csv", index=False)
    cis = pd.read_csv(ROOT / cfg["paths"]["processed"] / "cis_studies.csv")
    before = i18n.get_lang()
    try:
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            figs = i18n.figures_dir(cfg)
            plot_comparison(per_party, blocs, draws, figs / "hemicycle_comparison_29n.png", cfg)
            plot_change(per_party, blocs, figs / "seat_change_29n.png", cfg)
            plot_cis(cis, figs / "cis_legislature.png", cfg)
    finally:
        i18n.set_lang(before)
    return per_party, blocs


if __name__ == "__main__":
    main()

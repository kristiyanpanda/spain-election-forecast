"""Spanish parties since 1977: vote share at every general election, as party lineages.

A lineage follows one party through its changes of name and alliance (AP, CD, Coalición Popular and
PP are one line; so are HB, Amaiur and EH Bildu). Lines start at the party's first election and stop
at its last one; a dotted link joins a party to the one it went into (IU into Unidos Podemos in 2016,
Unidas Podemos into Sumar in 2023). The 29 November 2026 forecast closes the state-wide lines.

Shares are of the valid vote, from the Ministry of the Interior files already used for the backtest
(``electoral.mir``). The canonical families of ``data/party_map_results.yaml`` give every list that
won a seat or 1 % of the vote; smaller runs of a lineage (ERC in 1986 and 1989, the BNG without a
seat, Vox and UPyD in 2015-2016) are added from the same files by their acronym, so that a line does
not break just because the party fell below the threshold. Real gaps stay gaps: HB asked for
abstention in 2000 and Batasuna was banned in 2004 and 2008.

``main`` writes ``data/processed/party_history.csv`` and the static figure
``reports/figures/party_history.png`` (and its Spanish twin); the interactive version for the web
page is ``electoral.report.history_figure``.
"""

from __future__ import annotations

import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from electoral import ROOT, i18n, load_config
from electoral.build_data import ELECTION_DATES
from electoral.plots import COLORS, HEMICYCLE_COLORS, INK, MUTED, RULE, _spread, _style, stamp

OUT = "party_history.csv"
FORECAST_DATE = "2026-11-29"

# id, families in results_national, extra acronyms (regex on the MIR "siglas"), panel, colour
LINEAGES = [
    ("PSOE", ["PSOE"], None, "state"),
    ("PP", ["PP"], None, "state"),
    ("UCD", ["UCD"], None, "state"),
    ("CDS", ["CDS"], None, "state"),
    ("IU", ["IU"], None, "state"),
    ("UP", ["PODEMOS", "UP"], None, "state"),
    ("SUMAR", ["SUMAR"], None, "state"),
    ("UPYD", ["UPYD"], r"^UPyD$", "state"),
    ("CS", ["CS"], None, "state"),
    ("VOX", ["VOX"], r"^VOX$", "state"),
    ("JUNTS", ["JUNTS"], None, "periph"),
    ("PNV", ["PNV"], None, "periph"),
    ("ERC", ["ERC"], r"^ERC$", "periph"),
    ("BILDU", ["BILDU"], None, "periph"),
    ("BNG", ["BNG"], r"^(BNG|BN-PG|BNPG|B-PSG|N.S|BNG-N.S)$", "periph"),
    ("CC", ["CC"], None, "periph"),
]
COLOR = {**COLORS, **HEMICYCLE_COLORS, "UCD": "#2e9e8f", "CDS": "#7fbf3f", "IU": "#b30000", "UP": "#6a3d9a",
         "UPYD": "#e5007d", "CS": "#ff7f00", "SALF": "#8c6d31"}
NAME = {"PSOE": "PSOE", "PP": "AP / PP", "UCD": "UCD", "CDS": "CDS", "IU": "PCE / IU", "UP": "Podemos / UP",
        "SUMAR": "Sumar / Frente Amplio", "UPYD": "UPyD", "CS": "Cs", "VOX": "Vox", "SALF": "SALF",
        "JUNTS": "CiU / Junts", "PNV": "PNV", "ERC": "ERC", "BILDU": "HB / EH Bildu", "BNG": "BNG", "CC": "AIC / CC"}
# the name the lineage ran under, where it is not the lineage's last name
RAN_AS = {
    "PP": {"197706": "AP", "197903": "CD", "198210": "AP-PDP", "198606": "CP"},
    "IU": {"197706": "PCE", "197903": "PCE", "198210": "PCE", "201512": "IU-UP"},
    "UP": {"201512": "Podemos", "201606": "Unidos Podemos", "201904": "Unidas Podemos", "201911": "Unidas Podemos"},
    "SUMAR": {"202307": "Sumar"},
    "JUNTS": {"197706": "PDPC + UDC", **{e: "CiU" for e in ["197903", "198210", "198606", "198910", "199306",
                                                            "199603", "200003", "200403", "200803", "201111"]},
              "201512": "DL", "201606": "CDC", "201904": "JxCat", "201911": "JxCat", "202307": "Junts"},
    "BILDU": {**{e: "HB" for e in ["197903", "198210", "198606", "198910", "199306", "199603"]},
              "201111": "Amaiur", "201512": "EH Bildu", "201606": "EH Bildu", "201904": "EH Bildu",
              "201911": "EH Bildu", "202307": "EH Bildu"},
    "CC": {"198606": "AIC", "198910": "AIC"},
    "ERC": {"197706": "EC"},
    "BNG": {"197706": "BN-PG", "197903": "BN-PG", "198210": "B-PSG", "201512": "Nós", "201606": "BNG-Nós"},
}
# a lineage that went into another: (from, to) drawn as a dotted link from the last point of one to the
# first point of the other after it
LINKS = [("IU", "UP"), ("UP", "SUMAR")]
# lineages that ran in the 29N forecast under the forecast's own id
FORECAST_ID = {"PSOE": "PSOE", "PP": "PP", "SUMAR": "SUMAR", "VOX": "VOX", "UP": "PODEMOS", "SALF": "SALF",
               "JUNTS": "JUNTS", "PNV": "PNV", "ERC": "ERC", "BILDU": "BILDU", "BNG": "BNG", "CC": "CC"}
# heads of government, from taking office
GOVERNMENTS = [("Suárez", "UCD", "1977-06-15"), ("Calvo-Sotelo", "UCD", "1981-02-26"),
               ("González", "PSOE", "1982-12-02"), ("Aznar", "PP", "1996-05-05"),
               ("Zapatero", "PSOE", "2004-04-17"), ("Rajoy", "PP", "2011-12-21"), ("Sánchez", "PSOE", "2018-06-02")]
EVENTS = [
    ("1978-12-06", {"es": "Constitución", "en": "Constitution"}),
    ("1981-02-23", {"es": "23-F", "en": "23-F coup attempt"}),
    ("1986-01-01", {"es": "Entrada en la CEE", "en": "Spain joins the EEC"}),
    ("2004-03-11", {"es": "11-M", "en": "Madrid bombings (11-M)"}),
    ("2008-09-15", {"es": "Crisis financiera", "en": "Financial crisis"}),
    ("2011-05-15", {"es": "15-M", "en": "15-M protests"}),
    ("2011-10-20", {"es": "ETA deja las armas", "en": "ETA ends its violence"}),
    ("2014-01-17", {"es": "Nace Podemos", "en": "Podemos founded"}),
    ("2017-10-01", {"es": "1-O en Cataluña", "en": "Catalan referendum (1-O)"}),
    ("2018-06-01", {"es": "Moción de censura", "en": "No-confidence vote"}),
    ("2020-03-14", {"es": "COVID-19", "en": "COVID-19"}),
]
# what happened to a lineage after its last point (in the key; the point itself gets a cross)
ENDS = {"UCD": {"es": "disuelta en 1983", "en": "dissolved 1983"},
        "CDS": {"es": "sin escaño desde 1993", "en": "no seat after 1993"},
        "IU": {"es": "en Unidos Podemos desde 2016", "en": "in Unidos Podemos from 2016"},
        "UPYD": {"es": "sin escaño desde 2015", "en": "no seat after 2015"},
        "CS": {"es": "no se presentó en 2023", "en": "did not run in 2023"},
        "UP": {"es": "en Sumar en 2023", "en": "inside Sumar in 2023"}}


def build() -> pd.DataFrame:
    """One row per lineage and election: share of the valid vote (%), seats and the name it ran under."""
    from electoral import mir

    cfg = load_config()
    nat = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "results_national.parquet")
    res, tot = mir.build_all(cfg["mir"]["elections"], cfg["mir"]["base_url"], ROOT / cfg["paths"]["raw_mir"])
    valid = tot.groupby("election")["votos_validos"].sum()
    lists = res.groupby(["election", "siglas"], as_index=False)[["votos", "escanos"]].sum()
    lists["share"] = 100 * lists.votos / lists.election.map(valid)
    rows = []
    for lid, fams, extra, panel in LINEAGES:
        for e in sorted(nat.election.unique()):
            got = nat[(nat.election == e) & nat.party.isin(fams)]
            share, seats = 100 * got.share_valid.sum(), int(got.escanos.sum())
            if got.empty and extra:
                x = lists[(lists.election == e) & lists.siglas.str.strip().str.match(extra, flags=re.I)]
                share, seats = x.share.sum(), int(x.escanos.sum())
            if share >= 0.1:
                rows.append({"lineage": lid, "panel": panel, "election": e, "date": ELECTION_DATES[e],
                             "share": round(share, 2), "seats": seats,
                             "ran_as": RAN_AS.get(lid, {}).get(e, NAME[lid].split(" / ")[-1])})
    return pd.DataFrame(rows)


def load(refresh: bool = False) -> pd.DataFrame:
    path = ROOT / load_config()["paths"]["processed"] / OUT
    if refresh or not path.exists():
        build().to_csv(path, index=False)
    return pd.read_csv(path, dtype={"election": str}, parse_dates=["date"])


def forecast() -> pd.DataFrame:
    """29N vote share (median and 90 % interval, in %) and median seats per lineage."""
    out = ROOT / load_config()["paths"]["outputs"]
    v = pd.read_csv(out / "vote_summary_29n.csv", index_col=0)
    s = pd.read_parquet(out / "seat_draws_29n_split.parquet")
    rows = [{"lineage": lid, "q05": 100 * v.loc[fid, "q05"], "q50": 100 * v.loc[fid, "q50"],
             "q95": 100 * v.loc[fid, "q95"], "seats": int(s[fid].median()) if fid in s else 0}
            for lid, fid in FORECAST_ID.items() if fid in v.index]
    return pd.DataFrame(rows).set_index("lineage")


def panel_of(lid: str) -> str:
    return next((p for i, _, _, p in LINEAGES if i == lid), "state")


def segments(hist: pd.DataFrame, lid: str) -> list[pd.DataFrame]:
    """The runs of consecutive elections of a lineage (a missed election breaks the line)."""
    order = sorted(hist.election.unique())
    h = hist[hist.lineage == lid].sort_values("election")
    pos = h.election.map(order.index)
    return [g for _, g in h.groupby((pos.diff() != 1).cumsum())]


def plot(hist: pd.DataFrame, fc: pd.DataFrame, path, lang: str) -> None:
    """Two panels (state-wide and nationalist parties) under a ribbon of governments, with key dates."""
    import matplotlib.dates as mdates

    _style()
    fdate = pd.Timestamp(FORECAST_DATE)
    top, low = 64, 6.8          # room above the data for the names of the key dates and the second key
    fig = plt.figure(figsize=(13, 9))
    gs = fig.add_gridspec(3, 1, height_ratios=[0.045, 1, 0.4], hspace=0.13, left=0.05, right=0.86, top=0.835,
                          bottom=0.065)
    rib, ax, ap = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
    x0, x1 = pd.Timestamp("1976-09-01"), pd.Timestamp("2027-09-01")

    # heads of government
    starts = [pd.Timestamp(d) for _, _, d in GOVERNMENTS] + [fdate]
    for (who, party, _), a, b in zip(GOVERNMENTS, starts[:-1], starts[1:]):
        rib.axvspan(a, b, color=COLOR[party], alpha=0.85, linewidth=0)
        rib.axvline(a, color="white", lw=1)
        short = who if (b - a).days > 1000 else who.split("-")[0][:1] + "."   # Calvo-Sotelo: "C."
        rib.text(a + (b - a) / 2, 0.5, short, ha="center", va="center", fontsize=8.5, color="white", weight="bold")
    rib.set_xlim(x0, x1)
    rib.set_ylim(0, 1)
    rib.set_yticks([])
    rib.tick_params(labelbottom=False, bottom=False)
    rib.grid(False)
    for sp in rib.spines.values():
        sp.set_visible(False)
    rib.set_title(i18n.tr("Head of government"), loc="left", fontsize=9, color=MUTED, pad=3)

    ends = {"state": [], "periph": []}
    for lid, _, _, panel in LINEAGES:
        a = ax if panel == "state" else ap
        c = COLOR[lid]
        for g in segments(hist, lid):
            a.plot(g.date, g.share, color=c, lw=2.1, marker="o", ms=3.6, zorder=3)
        h = hist[hist.lineage == lid].sort_values("date")
        last = h.iloc[-1]
        if lid in fc.index:
            f = fc.loc[lid]
            a.plot([last.date, fdate], [last.share, f.q50], color=c, lw=1.4, ls=(0, (2, 2)))
            a.errorbar([fdate], [f.q50], yerr=[[f.q50 - f.q05], [f.q95 - f.q50]], fmt="o", ms=5, mfc="white",
                       mec=c, mew=1.6, ecolor=c, elinewidth=1.4, capsize=0, zorder=4)
            ends[panel].append((lid, f.q50))
        elif lid in ENDS:
            a.plot([last.date], [last.share], marker="X", ms=8, color=c, mec="white", mew=0.8, zorder=4)
    for src, dst in LINKS:
        a_ = hist[hist.lineage == src].sort_values("date").iloc[-1]
        b_ = hist[hist.lineage == dst].sort_values("date").iloc[0]
        ax.plot([a_.date, b_.date], [a_.share, b_.share], color=COLOR[dst], lw=1.1, ls=":", zorder=2)
    if "SALF" in fc.index:                     # SALF has only the forecast
        f = fc.loc["SALF"]
        ax.errorbar([fdate], [f.q50], yerr=[[f.q50 - f.q05], [f.q95 - f.q50]], fmt="o", ms=5, mfc="white",
                    mec=COLOR["SALF"], mew=1.6, ecolor=COLOR["SALF"], elinewidth=1.4)
        ends["state"].append(("SALF", f.q50))

    for a, ymax in ((ax, top), (ap, low)):
        a.set_xlim(x0, x1)
        a.set_ylim(0, ymax)
        a.axvline(fdate, color="black", lw=0.9, ls="--")
        for d, _ in EVENTS:
            a.axvline(pd.Timestamp(d), color="#777777", lw=0.6, ls=":", zorder=1)
        a.xaxis.set_major_locator(mdates.YearLocator(5, month=1, day=1))
        a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_yticks(range(0, 51, 10))
    ap.set_yticks(range(0, 6))
    ax.tick_params(labelbottom=False)
    prev = None
    for d, lab in EVENTS:
        # the name sits left of its line, or right of it when the previous date is too close
        d = pd.Timestamp(d)
        right = prev is not None and (d - prev).days < 300
        ax.annotate(lab[lang], (d, top), xytext=(2 if right else -2, -3), textcoords="offset points", rotation=90,
                    ha="left" if right else "right", va="top", fontsize=8, color=INK)
        prev = d
    ax.annotate("29-N" if lang == "es" else "29 Nov", (fdate, top), xytext=(-2, -3), textcoords="offset points",
                rotation=90, ha="right", va="top", fontsize=8, weight="bold", color=INK)

    # forecast values right of the panels
    for a, panel, gap in ((ax, "state", top * 0.042), (ap, "periph", low * 0.1)):
        items = ends[panel]
        ys = _spread([y for _, y in items], gap)
        for (lid, y0), y in zip(items, ys):
            a.annotate("●", (fdate, y), xytext=(26, 0), textcoords="offset points", color=COLOR[lid], fontsize=8,
                       va="center", annotation_clip=False)
            a.annotate(f"{NAME[lid]} {i18n.num(y0)}", (fdate, y), xytext=(35, 0), textcoords="offset points",
                       fontsize=8.8, color=INK, va="center", annotation_clip=False)

    ax.set_ylabel(i18n.tr("% of valid vote"))
    ap.set_ylabel(i18n.tr("% of valid vote"))
    ax.set_title(i18n.tr("State-wide parties"), loc="left", fontsize=9, color=MUTED, pad=4)
    ap.set_title(i18n.tr("Nationalist and regional parties"), loc="left", fontsize=9, color=MUTED, pad=4)

    def label(lid: str) -> str:
        return f"{NAME[lid]} ({ENDS[lid][lang]})" if lid in ENDS else NAME[lid]

    left = ax.get_position().x0
    fig.text(left, 0.985, i18n.tr("Spanish parties since 1977: vote share at every general election"),
             ha="left", va="top", fontsize=12.5, weight="bold", color=INK)
    handles = [plt.Line2D([], [], color=COLOR[lid], lw=2.6, label=label(lid))
               for lid, _, _, p in LINEAGES if p == "state"] + \
              [plt.Line2D([], [], color=COLOR["SALF"], lw=0, marker="o", mfc="white", mew=1.6, label="SALF")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(left, 0.955), ncol=4, fontsize=8.8,
               frameon=True, fancybox=True, facecolor="#f7f8fa", edgecolor=RULE, borderpad=0.6, columnspacing=1.4,
               handlelength=1.8)
    handles = [plt.Line2D([], [], color=COLOR[lid], lw=2.6, label=NAME[lid])
               for lid, _, _, p in LINEAGES if p == "periph"]
    ap.legend(handles=handles, loc="upper center", ncol=6, fontsize=8.5, frameon=True, facecolor="white",
              edgecolor=RULE)
    stamp(fig, load_config()["cutoff_date"],
          i18n.tr("Dots: general elections (share of the valid vote, Ministry of the Interior); hollow dot and bar: "
                  "29 Nov forecast, median and 90 % interval; cross: last election of a party that is gone; "
                  "dotted links: a party that went into another.")
          + "\n" + i18n.tr("Gaps: HB called for abstention in 2000; Batasuna was banned in 2004 and 2008."),
          fontsize=7.2)
    fig.savefig(path, bbox_inches="tight", dpi=160)
    plt.close(fig)


def main(refresh: bool = False) -> None:
    hist = load(refresh)
    fc = forecast()
    before = i18n.get_lang()
    try:
        for lang, folder in (("en", ROOT / "reports" / "figures"), ("es", ROOT / i18n.ES_DIR / "figures")):
            i18n.set_lang(lang)
            folder.mkdir(parents=True, exist_ok=True)
            plot(hist, fc, folder / "party_history.png", lang)
            print(f"wrote {folder / 'party_history.png'}")
    finally:
        i18n.set_lang(before)


if __name__ == "__main__":
    main()

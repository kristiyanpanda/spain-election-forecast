"""Phase B entry point: the original dossier's descriptive layer, upgraded and reproducible.

Outputs: data/processed/party_system.csv, bloc_matrix_votes.csv, bloc_matrix_seats.csv,
provincial_enp.csv; figures turnout_enp.png, volatility.png, bloc_matrix.png, provincial_fragmentation.png.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from electoral import ROOT, load_config
from electoral.indices import bloc_matrix, party_system_table, provincial_enp
from electoral.plots import BLOC_COLORS, _style, stamp

SRC = "Source: Ministerio del Interior (results 1977-2023), computed in src/electoral/indices.py."


def main() -> pd.DataFrame:
    cfg = load_config()
    proc = ROOT / cfg["paths"]["processed"]
    figs = ROOT / cfg["paths"]["figures"]
    figs.mkdir(parents=True, exist_ok=True)
    nat = pd.read_parquet(proc / "results_national.parquet")
    res = pd.read_parquet(proc / "results_province.parquet")
    tot = pd.read_parquet(proc / "province_totals.parquet")
    pmap = yaml.safe_load((ROOT / "data/party_map_polls.yaml").read_text(encoding="utf-8"))
    bloc_of = {p: m["bloc"] for p, m in pmap["parties"].items()}

    ps = party_system_table(nat, tot, bloc_of, pmap.get("volatility_lineage"))
    ps.to_csv(proc / "party_system.csv", index=False)
    bmv = bloc_matrix(nat, bloc_of, "share_valid")
    bms = bloc_matrix(nat, bloc_of, "escanos")
    bmv.to_csv(proc / "bloc_matrix_votes.csv")
    bms.to_csv(proc / "bloc_matrix_seats.csv")
    pe = provincial_enp(res, tot)
    pe.to_csv(proc / "provincial_enp.csv", index=False)
    cutoff = cfg["cutoff_date"]
    years = ps["election_date"].dt.year + ps["election_date"].dt.month / 12
    labels = [d.strftime("%b %Y") if el in ("201904", "201911") else d.strftime("%Y")
              for el, d in zip(ps.election, ps.election_date)]

    # --- figure 1: turnout and ENP
    _style()
    fig, ax = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    ax[0].plot(years, 100 * ps.turnout, marker="o", color="#333333")
    ax[0].set_ylabel("turnout, %")
    ax[0].set_title("Turnout and fragmentation in Congreso elections, 1977-2023", loc="left", fontsize=11)
    ax[1].plot(years, ps.enp_votes, marker="o", color="#1f6fb2", label="ENP (votes)")
    ax[1].plot(years, ps.enp_seats, marker="s", color="#d7301f", label="ENP (seats)")
    ax[1].set_ylabel("effective number of parties")
    ax[1].legend(loc="upper left")
    for a in ax:
        a.axvspan(2015.5, 2016.9, color="#f0a500", alpha=0.12)
    ax[1].annotate("2015-16: the two-party system breaks\n(Podemos, Ciudadanos enter)", (2016.0, 5.0),
                   xytext=(2003.5, 5.6), fontsize=8, ha="left", va="top",
                   arrowprops={"arrowstyle": "-", "color": "#999999", "lw": 0.8})
    ax[1].annotate(f"2023: ENP votes {ps.enp_votes.iloc[-1]:.1f}, seats {ps.enp_seats.iloc[-1]:.1f}",
                   (years.iloc[-1], ps.enp_seats.iloc[-1]), xytext=(-150, -25), textcoords="offset points", fontsize=8)
    stamp(fig, cutoff, SRC)
    fig.tight_layout()
    fig.savefig(figs / "turnout_enp.png", bbox_inches="tight")
    plt.close(fig)

    # --- figure 2: volatility split
    v = ps.dropna(subset=["volatility_total"])
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(v))
    ax.bar(x, 100 * v.volatility_between, color="#1f6fb2", label="between blocs")
    ax.bar(x, 100 * v.volatility_within, bottom=100 * v.volatility_between, color="#9ecae1", label="within blocs")
    ax.set_xticks(x)
    ax.set_xticklabels([l for l, el in zip(labels, ps.election) if el in set(v.election)], rotation=45, ha="right")
    ax.set_ylabel("Pedersen volatility, pp")
    ax.legend(loc="upper right")
    imax = int(v.volatility_total.values.argmax())
    ax.annotate(f"max: {100 * v.volatility_total.iloc[imax]:.0f} pp", (x[imax], 100 * v.volatility_total.iloc[imax]),
                xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)
    ax.set_title("Electoral volatility between consecutive elections, split within / between blocs",
                 loc="left", fontsize=11)
    stamp(fig, cutoff, SRC + " Blocs: left, right, peripheral left, peripheral right, other.")
    fig.tight_layout()
    fig.savefig(figs / "volatility.png", bbox_inches="tight")
    plt.close(fig)

    # --- figure 3: bloc matrix (stacked area of vote shares)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.stackplot(years, *[100 * bmv[b].values for b in bmv.columns], labels=list(bmv.columns),
                 colors=[BLOC_COLORS[b] for b in bmv.columns], alpha=0.85)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of valid vote")
    ax.legend(loc="lower left", ncol=5, fontsize=8)
    ax.set_title("Bloc matrix: vote share of the four blocs, 1977-2023", loc="left", fontsize=11)
    stamp(fig, cutoff, SRC)
    fig.tight_layout()
    fig.savefig(figs / "bloc_matrix.png", bbox_inches="tight")
    plt.close(fig)

    # --- figure 4: provincial fragmentation (2023) vs. peripheral share
    p23 = pe[pe.election == "202307"].sort_values("enp_votes", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.scatter(100 * p23.periph_share, p23.enp_votes, color="#20b2aa", s=22)
    lab = pd.concat([p23.head(6), p23.sort_values("periph_share", ascending=False).head(4)]).drop_duplicates("prov")
    for _, r in lab.iterrows():
        ax.annotate(r.province, (100 * r.periph_share, r.enp_votes), xytext=(4, -8 if r.province in ("Girona", "Álava") else 3),
                    textcoords="offset points", fontsize=7)
    ax.set_xlabel("vote share of peripheral (regionalist / nationalist) lists, %")
    ax.set_ylabel("ENP (votes) in the province, 2023")
    ax.set_title("Regional fragmentation, 2023: where the peripheral vote lives", loc="left", fontsize=11)
    stamp(fig, cutoff, SRC)
    fig.tight_layout()
    fig.savefig(figs / "provincial_fragmentation.png", bbox_inches="tight")
    plt.close(fig)

    print(ps.round(3).to_string())
    print((100 * bmv).round(1).to_string())
    return ps


if __name__ == "__main__":
    main()

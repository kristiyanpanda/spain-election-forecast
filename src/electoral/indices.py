"""Descriptive party-system indices (phase B): the original dossier's measures, made reproducible.

* Laakso-Taagepera effective number of parties (votes or seats): N = 1 / sum(p_i^2)
* Pedersen volatility between consecutive elections: V = 0.5 * sum |p_i,t - p_i,t-1|
* Bartolini-Mair split: between-bloc volatility uses bloc totals; within-bloc = total - between
* Bloc matrix: share of votes and seats per bloc per election

All shares are of the valid vote; "OTHER" is a residual category and is included in every sum,
which is the conventional treatment (its changes count as volatility).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def enp(shares) -> float:
    """Effective number of parties. ``shares`` may sum to less than 1; it is renormalised."""
    p = np.asarray(list(shares), dtype=float)
    p = p[p > 0]
    p = p / p.sum()
    return float(1.0 / np.sum(p ** 2))


def pedersen(prev: pd.Series, cur: pd.Series) -> float:
    """Total volatility between two share vectors indexed by party (missing = 0)."""
    idx = prev.index.union(cur.index)
    a, b = prev.reindex(idx).fillna(0.0), cur.reindex(idx).fillna(0.0)
    return float(0.5 * (a - b).abs().sum())


def volatility_split(prev: pd.Series, cur: pd.Series, bloc_of: dict[str, str]) -> dict[str, float]:
    """Total, between-bloc and within-bloc Pedersen volatility."""
    total = pedersen(prev, cur)
    pb = prev.groupby(prev.index.map(lambda p: bloc_of.get(p, "other"))).sum()
    cb = cur.groupby(cur.index.map(lambda p: bloc_of.get(p, "other"))).sum()
    between = pedersen(pb, cb)
    return {"total": total, "between": between, "within": total - between}


def party_system_table(nat: pd.DataFrame, tot: pd.DataFrame, bloc_of: dict[str, str],
                       lineage: dict[str, str] | None = None) -> pd.DataFrame:
    """One row per election: turnout, ENP (votes, seats), volatility (total/between/within).

    ``lineage`` maps party ids to a common lineage id before computing volatility, so that a
    merger or relabelling (Podemos + IU -> Unidos Podemos -> Sumar) is not counted as change.
    """
    rows = []
    prev_share = None
    lineage = lineage or {}
    sums = tot.groupby("election")[["votantes", "censo_escrutinio"]].sum()
    turnout = sums["votantes"] / sums["censo_escrutinio"]
    for el, g in nat.sort_values("election").groupby("election", sort=True):
        share = g.set_index("party")["share_valid"]
        seats = g.set_index("party")["escanos"]
        lin = share.groupby(share.index.map(lambda p: lineage.get(p, p))).sum()
        row = {"election": el, "election_date": g["election_date"].iloc[0], "turnout": float(turnout[el]),
               "enp_votes": enp(share), "enp_seats": enp(seats[seats > 0]),
               "largest_share": float(share.max()), "top2_share": float(share.nlargest(2).sum())}
        if prev_share is not None:
            bloc_lin = {**bloc_of, **{v: bloc_of.get(k, "other") for k, v in lineage.items()}}
            row.update({f"volatility_{k}": v for k, v in volatility_split(prev_share, lin, bloc_lin).items()})
        rows.append(row)
        prev_share = lin
    return pd.DataFrame(rows)


def bloc_matrix(nat: pd.DataFrame, bloc_of: dict[str, str], value: str = "share_valid") -> pd.DataFrame:
    """Elections x blocs table of vote share (default) or seats."""
    df = nat.copy()
    df["bloc"] = df["party"].map(lambda p: bloc_of.get(p, "other"))
    m = df.pivot_table(index="election", columns="bloc", values=value, aggfunc="sum").fillna(0.0)
    order = [b for b in ["left", "right", "periph_left", "periph_right", "other"] if b in m]
    return m[order]


def provincial_enp(res: pd.DataFrame, tot: pd.DataFrame) -> pd.DataFrame:
    """ENP of votes per (election, province), plus the peripheral-bloc vote share."""
    rows = []
    for (el, prov), g in res.groupby(["election", "prov"]):
        s = g.groupby("party")["votos"].sum()
        periph = g[g["bloc"].isin(["periph_left", "periph_right"])]["votos"].sum() / g["votos"].sum()
        rows.append({"election": el, "prov": prov, "enp_votes": enp(s), "periph_share": float(periph)})
    out = pd.DataFrame(rows)
    names = tot.drop_duplicates("prov").set_index("prov")["ambito_nombre"]
    out["province"] = out["prov"].map(names)
    return out

"""Seat projection: national vote-share draws -> provincial shares -> D'Hondt -> seat draws.

Spanish Congress rules (LOREG): 350 seats; 50 provinces are multi-member districts with a 3 %
threshold on the valid vote (blank ballots included) and D'Hondt allocation; Ceuta and Melilla
elect one deputy each by plurality (D'Hondt with one seat).

Swing model (documented choice, see docs/model_choices.md):
* parties tracked by the aggregator: provincial share = 2023 provincial share x (draw national
  share / 2023 national share), i.e. proportional swing;
* entrants without a 2023 provincial footprint use a proxy geography (PODEMOS follows Sumar's
  2023 distribution; SALF is spread uniformly);
* every other list keeps its 2023 provincial share;
* multiplicative log-normal noise per (province, party) with sd calibrated on the last two
  elections' proportional-swing residuals; shares are renormalised so that province totals sum to
  the 2023 non-blank share.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MAJORITY = 176


def dhondt(votes: np.ndarray, seats: int, threshold: float = 0.03, blank: float = 0.0) -> np.ndarray:
    """Allocate ``seats`` by D'Hondt for one district.

    ``votes`` is a 1-D array of votes (or shares) per list; ``blank`` is the blank vote in the same
    unit (it counts towards the threshold base but receives no seats). Ties go to the list with
    more votes, then to the lower index (deterministic).
    """
    v = np.asarray(votes, dtype=float)
    total = v.sum() + blank
    eligible = v / total >= threshold if total > 0 else np.zeros_like(v, bool)
    v = np.where(eligible, v, 0.0)
    out = np.zeros(len(v), dtype=int)
    if seats <= 0 or v.sum() <= 0:
        return out
    quot = v[:, None] / np.arange(1, seats + 1)[None, :]
    flat = quot.ravel()
    # stable ordering: larger quotient first, then larger raw vote, then lower index
    order = np.lexsort((np.repeat(np.arange(len(v)), seats), -np.repeat(v, seats), -flat))
    winners = order[:seats] // seats
    np.add.at(out, winners, 1)
    return out


def dhondt_batch(shares: np.ndarray, seats: int, threshold: float = 0.03,
                 blank: np.ndarray | float = 0.0) -> np.ndarray:
    """Vectorised D'Hondt over draws: ``shares`` is (S, P), returns (S, P) integer seats."""
    S, P = shares.shape
    if seats <= 0:
        return np.zeros((S, P), dtype=int)
    blank = np.broadcast_to(np.asarray(blank, dtype=float), (S,))
    total = shares.sum(axis=1) + blank
    v = np.where(shares / total[:, None] >= threshold, shares, 0.0)
    quot = v[:, :, None] / np.arange(1, seats + 1)[None, None, :]      # (S, P, seats)
    flat = quot.reshape(S, -1)
    top = np.argpartition(-flat, seats - 1, axis=1)[:, :seats]        # ties broken arbitrarily
    party = top // seats
    out = np.zeros((S, P), dtype=int)
    for s in range(S):
        np.add.at(out[s], party[s], 1)
    return out


# ----------------------------------------------------------------------------- swing set-up
def province_baseline(results_province: pd.DataFrame, province_totals: pd.DataFrame,
                      election: str) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Return (shares (prov x party) of the valid vote, blank share per prov, seats per prov)."""
    r = results_province[results_province.election == election]
    t = province_totals[province_totals.election == election].set_index("prov")
    votes = r.pivot_table(index="prov", columns="party", values="votos", aggfunc="sum").fillna(0.0)
    shares = votes.div(t.loc[votes.index, "votos_validos"], axis=0)
    blank = (t["votos_blancos"] / t["votos_validos"]).loc[votes.index]
    seats = t["escanos"].loc[votes.index].astype(int)
    return shares, blank, seats


def calibrate_swing_noise(results_province: pd.DataFrame, province_totals: pd.DataFrame,
                          from_election: str, to_election: str, parties: list[str],
                          min_share: float = 0.01) -> float:
    """Sd of log residuals of the proportional-swing prediction between two elections.

    Residual = log(actual provincial share / predicted), predicted = previous provincial share x
    national ratio; weighted by province size, restricted to parties present in both elections
    and above ``min_share`` in the province.
    """
    s0, _, _ = province_baseline(results_province, province_totals, from_election)
    s1, _, _ = province_baseline(results_province, province_totals, to_election)
    t = province_totals[province_totals.election == to_election].set_index("prov")["votos_validos"]
    common = [p for p in parties if p in s0 and p in s1]
    n0 = results_province[results_province.election == from_election].groupby("party")["votos"].sum()
    n1 = results_province[results_province.election == to_election].groupby("party")["votos"].sum()
    v0 = province_totals[province_totals.election == from_election]["votos_validos"].sum()
    v1 = province_totals[province_totals.election == to_election]["votos_validos"].sum()
    res, w = [], []
    for p in common:
        ratio = (n1[p] / v1) / (n0[p] / v0)
        pred = s0[p] * ratio
        mask = (s0[p] > min_share) & (s1[p] > min_share)
        res.extend(np.log(s1[p][mask] / pred[mask]).values)
        w.extend(t.loc[s1.index[mask]].values)
    res, w = np.array(res), np.array(w)
    return float(np.sqrt(np.average(res ** 2, weights=w)))


def simulate_seats(state_draws: pd.DataFrame, shares0: pd.DataFrame, blank0: pd.Series,
                   seats0: pd.Series, national0: pd.Series, n_sims: int, noise_sd: float,
                   seed: int, proxies: dict[str, str | None] | None = None,
                   threshold: float = 0.03, absorb: dict[str, list[str]] | None = None,
                   noise: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monte Carlo seat simulation.

    state_draws: posterior draws of national shares (rows) for tracked parties (columns).
    shares0/blank0/seats0: previous-election provincial baseline; national0: previous national
    shares per party (all lists, incl. OTHER). proxies: entrant -> party whose geography to borrow
    (None = uniform). absorb: tracked party -> baseline lists it replaces (their summed geography
    is used and their own share is zeroed, e.g. SUMAR absorbs UP + MASPAIS in the 2023 backtest).
    Returns (seat draws (n_sims x all parties), share draws national (n_sims x parties)).
    """
    rng = np.random.default_rng(seed)
    tracked = list(state_draws.columns)
    all_parties = sorted(set(shares0.columns) | set(tracked))
    provs = list(shares0.index)
    S = n_sims
    idx = rng.integers(0, len(state_draws), size=S)
    nat = state_draws.values[idx]                                      # (S, tracked)
    base = shares0.reindex(columns=all_parties, fill_value=0.0).values  # (prov, all)
    prov_share = np.repeat(base[None, :, :], S, axis=0)                # (S, prov, all)
    col = {p: j for j, p in enumerate(all_parties)}
    proxies = proxies or {}
    absorb = absorb or {}

    for k, p in enumerate(tracked):
        j = col[p]
        prev = national0.get(p, 0.0)
        if p in absorb:
            src = [col[q] for q in absorb[p] if q in col]
            geo = base[:, src].sum(axis=1) / sum(national0.get(q, 0.0) for q in absorb[p])
            prov_share[:, :, src] = 0.0
        elif prev > 0.002 and shares0[p].sum() > 0:
            geo = base[:, j] / prev                                    # relative propensity
        else:
            proxy = proxies.get(p)
            geo = (base[:, col[proxy]] / national0[proxy]) if proxy else np.ones(len(provs))
        prov_share[:, :, j] = nat[:, k][:, None] * geo[None, :]
    if not noise:
        noise_sd = 0.0

    noise = rng.normal(-0.5 * noise_sd ** 2, noise_sd, size=prov_share.shape)
    tracked_cols = [col[p] for p in tracked]
    prov_share[:, :, tracked_cols] *= np.exp(noise[:, :, tracked_cols])
    # renormalise so that each province sums to its previous non-blank share
    target = (1.0 - blank0.values)[None, :]
    prov_share *= (target / prov_share.sum(axis=2))[:, :, None]

    seats = np.zeros((S, len(all_parties)), dtype=int)
    for i, pr in enumerate(provs):
        seats += dhondt_batch(prov_share[:, i, :], int(seats0[pr]), threshold, blank0[pr])
    seat_df = pd.DataFrame(seats, columns=all_parties)
    share_df = pd.DataFrame(nat, columns=tracked)
    return seat_df, share_df


def summarise_seats(seat_df: pd.DataFrame, blocs: dict[str, list[str]],
                    thresholds: dict[str, list[int]] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-party seat quantiles and probabilities of bloc majorities / party thresholds."""
    q = seat_df.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).T
    q.columns = ["q05", "q25", "q50", "q75", "q95"]
    q["mean"] = seat_df.mean()
    q = q.sort_values("mean", ascending=False)
    probs = []
    largest = seat_df.idxmax(axis=1)
    for name, members in blocs.items():
        m = [p for p in members if p in seat_df]
        tot = seat_df[m].sum(axis=1)
        probs.append({"event": f"{name} >= {MAJORITY}", "members": "+".join(m),
                      "probability": float((tot >= MAJORITY).mean()),
                      "seats_q05": float(tot.quantile(0.05)), "seats_q50": float(tot.median()),
                      "seats_q95": float(tot.quantile(0.95))})
    for p in ["PP", "PSOE"]:
        if p in seat_df:
            probs.append({"event": f"{p} largest party", "members": p,
                          "probability": float((largest == p).mean())})
            probs.append({"event": f"{p} >= {MAJORITY} alone", "members": p,
                          "probability": float((seat_df[p] >= MAJORITY).mean())})
    for p, ths in (thresholds or {}).items():
        if p in seat_df:
            for th in ths:
                probs.append({"event": f"{p} >= {th} seats", "members": p,
                              "probability": float((seat_df[p] >= th).mean())})
    return q, pd.DataFrame(probs)

"""Phase E: replay the pipeline as-of 30 days before each election since 2016.

For every target election the aggregator is re-fitted using only polls whose fieldwork ended at
least ``lead_days`` before polling day, anchored on the previous election; the latent state at
election week is therefore a random-walk extrapolation. Seats are simulated from the previous
election's provincial baseline. Scores:

* vote MAE (pp) and seat MAE over tracked parties, for the model median;
* CRPS of vote shares (pp, averaged over parties) from the posterior draws;
* 90 % interval coverage for votes and seats;
* Brier score for two events: "PP largest party" and "right bloc >= 176";
* the same for two baselines: the previous election result, and the plain mean of polls in the
  last 30 days before the cut-off (seats via deterministic proportional swing).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from electoral import ROOT, load_config
from electoral.model import fit, prepare, state_draws
from electoral.seats import calibrate_swing_noise, province_baseline, simulate_seats

RIGHT = ["PP", "VOX", "CS", "UPN"]


def crps_from_draws(draws: np.ndarray, actual: float) -> float:
    """Empirical CRPS: E|X - y| - 0.5 E|X - X'| (in the units of draws)."""
    x = np.sort(draws)
    n = len(x)
    term1 = np.abs(x - actual).mean()
    term2 = 2 * np.sum((2 * np.arange(1, n + 1) - n - 1) * x) / (n * n)   # E|X-X'| for sorted x
    return float(term1 - 0.5 * term2)


def score(share_draws: pd.DataFrame, seat_draws: pd.DataFrame, actual_share: pd.Series,
          actual_seats: pd.Series, parties: list[str]) -> dict:
    out = {}
    med = share_draws.median()
    out["vote_mae_pp"] = float((100 * (med[parties] - actual_share[parties]).abs()).mean())
    out["vote_crps_pp"] = float(np.mean([crps_from_draws(100 * share_draws[p].values, 100 * actual_share[p])
                                         for p in parties]))
    lo, hi = share_draws.quantile(0.05), share_draws.quantile(0.95)
    out["vote_cover90"] = float(np.mean([(lo[p] <= actual_share[p] <= hi[p]) for p in parties]))
    sp = [p for p in parties if p in seat_draws]
    smed = seat_draws[sp].median()
    out["seat_mae"] = float((smed - actual_seats.reindex(sp).fillna(0)).abs().mean())
    slo, shi = seat_draws[sp].quantile(0.05), seat_draws[sp].quantile(0.95)
    out["seat_cover90"] = float(np.mean([(slo[p] <= actual_seats.get(p, 0) <= shi[p]) for p in sp]))
    right = [p for p in RIGHT if p in seat_draws]
    p_right = float((seat_draws[right].sum(axis=1) >= 176).mean())
    y_right = float(actual_seats.reindex(right).fillna(0).sum() >= 176)
    p_pp = float((seat_draws.idxmax(axis=1) == "PP").mean())
    y_pp = float(actual_seats.idxmax() == "PP")
    out["p_right_majority"], out["y_right_majority"] = p_right, y_right
    out["p_pp_largest"], out["y_pp_largest"] = p_pp, y_pp
    out["brier"] = float(np.mean([(p_right - y_right) ** 2, (p_pp - y_pp) ** 2]))
    return out


def run_cycle(key: str, spec: dict, cfg: dict, polls: pd.DataFrame, nat: pd.DataFrame,
              res: pd.DataFrame, tot: pd.DataFrame, election_dates: dict) -> tuple[dict, pd.DataFrame]:
    el, prev = spec["election"], spec["previous"]
    e_date, p_date = election_dates[el], election_dates[prev]
    obs_cutoff = e_date - pd.Timedelta(days=cfg["backtest"]["lead_days"])
    parties = spec["parties"]

    prev_nat = nat[nat.election == prev].set_index("party")["share_valid"]
    anchor = {p: float(prev_nat.get(p, np.nan)) for p in parties}
    for target, comps in (spec.get("anchor_sum") or {}).items():
        anchor[target] = float(sum(prev_nat.get(c, 0.0) for c in comps))
    anchor = {p: v for p, v in anchor.items() if not np.isnan(v) and v > 0}

    d = prepare(polls, key, parties, anchor, p_date, e_date, obs_cutoff=obs_cutoff,
                breaks=spec.get("breaks") or None, composites=spec.get("composites") or None)
    idata = fit(d, seed=cfg["seed"], **cfg["backtest"]["sampling"])
    sd = state_draws(idata, d)                                    # election-week extrapolation

    shares0, blank0, seats0 = province_baseline(res, tot, prev)
    elections = cfg["mir"]["elections"]
    i = elections.index(prev)
    noise_sd = float(np.mean([calibrate_swing_noise(res, tot, elections[i - 2], elections[i - 1], parties),
                              calibrate_swing_noise(res, tot, elections[i - 1], prev, parties)]))
    seat_df, share_df = simulate_seats(sd, shares0, blank0, seats0, prev_nat, cfg["backtest"]["n_sims"],
                                       noise_sd, cfg["seed"], spec.get("proxies") or {},
                                       absorb=spec.get("absorb") or {})

    act = nat[nat.election == el].set_index("party")
    actual_share, actual_seats = act["share_valid"], act["escanos"].astype(int)
    rows = []
    rows.append({"cycle": key, "method": "model", **score(share_df, seat_df, actual_share, actual_seats, parties)})

    # baseline 1: previous election result carried forward (deterministic; no intervals)
    prev_share = pd.DataFrame([{p: anchor.get(p, 0.0) for p in parties}] * 2)
    prev_seats, _ = simulate_seats(prev_share, shares0, blank0, seats0, prev_nat, 2, 0.0, cfg["seed"],
                                   spec.get("proxies") or {}, absorb=spec.get("absorb") or {}, noise=False)
    rows.append({"cycle": key, "method": "last_election",
                 **score(prev_share, prev_seats, actual_share, actual_seats, parties)})

    # baseline 2: mean of polls in the 30 days before the observation cut-off, deterministic swing
    recent = d.polls[d.polls.fieldwork_end > obs_cutoff - pd.Timedelta(days=30)]["poll_id"]
    allobs = pd.DataFrame({"t": d.t_idx, "p": [d.parties[i] for i in d.p_idx], "y": d.y,
                           "h": [d.pollsters[i] for i in d.h_idx]})
    last_t = d.polls[d.polls.poll_id.isin(recent)]["t"].min()
    avg = allobs[allobs.t >= last_t].groupby("p")["y"].mean()
    avg_share = pd.DataFrame([{p: float(avg.get(p, anchor.get(p, 0.0))) for p in parties}] * 2)
    avg_seats, _ = simulate_seats(avg_share, shares0, blank0, seats0, prev_nat, 2, 0.0, cfg["seed"],
                                  spec.get("proxies") or {}, absorb=spec.get("absorb") or {}, noise=False)
    rows.append({"cycle": key, "method": "poll_average_30d",
                 **score(avg_share, avg_seats, actual_share, actual_seats, parties)})

    detail = pd.DataFrame({
        "cycle": key, "party": parties,
        "actual_share": [100 * actual_share.get(p, 0) for p in parties],
        "model_q05": [100 * share_df[p].quantile(0.05) for p in parties],
        "model_q50": [100 * share_df[p].median() for p in parties],
        "model_q95": [100 * share_df[p].quantile(0.95) for p in parties],
        "poll_avg": [100 * avg_share[p].iloc[0] for p in parties],
        "last_election": [100 * anchor.get(p, 0.0) for p in parties],
        "actual_seats": [int(actual_seats.get(p, 0)) for p in parties],
        "seats_q05": [seat_df[p].quantile(0.05) if p in seat_df else np.nan for p in parties],
        "seats_q50": [seat_df[p].median() if p in seat_df else np.nan for p in parties],
        "seats_q95": [seat_df[p].quantile(0.95) if p in seat_df else np.nan for p in parties],
        "seats_poll_avg": [avg_seats[p].iloc[0] if p in avg_seats else np.nan for p in parties],
        "seats_last_election": [prev_seats[p].iloc[0] if p in prev_seats else np.nan for p in parties],
    })
    meta = {"cycle": key, "election": el, "obs_cutoff": str(obs_cutoff.date()), "n_polls": int(len(d.polls)),
            "n_pollsters": len(d.pollsters), "noise_sd_log": noise_sd,
            "divergences": int(idata.sample_stats["diverging"].sum()) if "diverging" in idata.sample_stats else 0}
    return {"scores": rows, "meta": meta}, detail


def main(cycles: list[str] | None = None) -> pd.DataFrame:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    proc = ROOT / cfg["paths"]["processed"]
    polls = pd.read_parquet(proc / "polls_long.parquet")
    nat = pd.read_parquet(proc / "results_national.parquet")
    res = pd.read_parquet(proc / "results_province.parquet")
    tot = pd.read_parquet(proc / "province_totals.parquet")
    election_dates = nat.drop_duplicates("election").set_index("election")["election_date"].to_dict()

    scores, details, metas = [], [], []
    for key, spec in cfg["backtest"]["cycles"].items():
        if cycles and key not in cycles:
            continue
        r, detail = run_cycle(key, spec, cfg, polls, nat, res, tot, election_dates)
        scores += r["scores"]
        metas.append(r["meta"])
        details.append(detail)
        print(key, json.dumps(r["meta"]))
        print(pd.DataFrame(r["scores"]).round(3).to_string())
    sc = pd.DataFrame(scores)
    sc.to_csv(out / "backtest_scorecard.csv", index=False)
    pd.concat(details).to_csv(out / "backtest_details.csv", index=False)
    (out / "backtest_meta.json").write_text(json.dumps(metas, indent=2))
    return sc


if __name__ == "__main__":
    main()

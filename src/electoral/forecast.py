"""Phase F: project the latent shares to the legal deadline and re-run the seat simulation.

Two candidate additions to the plain random-walk extrapolation are *tested on the backtest*
before being used (config: none is used unless it helps):

1. Mean reversion toward the previous election result (a "fundamentals" drift): the 30-day
   backtest forecasts are shrunk toward the last result with weight w in {0.1, 0.2, 0.3}; w is
   adopted only if it lowers vote MAE in at least three of the four elections.
2. Election-day error inflation: the backtest residuals (actual - model median) are compared with
   the model's own posterior sd; if the 90 % intervals under-cover, an extra error term, sized
   relative to each party's share (polling error scales with party size), is added on the logit
   scale so that the backtest intervals would have reached nominal coverage.

Outputs: outputs/state_draws_deadline.parquet, forecast_deadline.json, seat_* files with tag
"deadline", figure seats_deadline.png.
"""

from __future__ import annotations

import json

import arviz as az
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm

from electoral import ROOT, load_config
from electoral.project_seats import main as seats_main


def test_mean_reversion(details: pd.DataFrame, weights=(0.1, 0.2, 0.3)) -> dict:
    """Vote MAE of the backtest model median after shrinking toward the last election."""
    out = {}
    for w in (0.0,) + tuple(weights):
        per_cycle = {}
        for c, d in details.groupby("cycle"):
            pred = (1 - w) * d.model_q50 + w * d.last_election
            per_cycle[c] = float((pred - d.actual_share).abs().mean())
        out[w] = per_cycle
    base = out[0.0]
    chosen = 0.0
    for w in weights:
        wins = sum(out[w][c] < base[c] for c in base)
        if wins >= 3 and (chosen == 0.0 or np.mean(list(out[w].values())) < np.mean(list(out[chosen].values()))):
            chosen = w
    return {"mae_by_weight": {str(k): v for k, v in out.items()}, "chosen_weight": chosen}


def test_error_inflation(details: pd.DataFrame, parties_min_share: float = 3.0) -> dict:
    """Extra sd (pp, share scale) so that 90 % intervals would have covered the backtest results.

    Model half-width h = (q95 - q05)/2 ~ 1.645 * s_model; residual r = actual - q50. The required
    total sd s_tot solves P(|r| <= 1.645 s_tot) = 0.9 empirically; extra = sqrt(max(s_tot^2 - s_model^2, 0)).
    Computed on parties above ``parties_min_share`` % where the error matters.
    """
    d = details[details.actual_share >= parties_min_share]
    s_model = ((d.model_q95 - d.model_q05) / (2 * norm.ppf(0.95))).values
    r = (d.actual_share - d.model_q50).values
    cover = float(np.mean(np.abs(r) <= norm.ppf(0.95) * s_model))
    # scale factor k on total sd such that 90 % of |r| <= 1.645 * k * s_model  (k>=1 only)
    z = np.abs(r) / (norm.ppf(0.95) * s_model)
    k = float(max(np.quantile(z, 0.9), 1.0))
    # polling error scales with party size: work in relative terms and find the smallest extra
    # relative sd e such that 90 % of |r_rel| <= 1.645 * sqrt(s_rel^2 + e^2)
    s_rel = s_model / d.model_q50.values
    r_rel = r / d.model_q50.values
    extra_rel = 0.0
    if cover < 0.9:
        for e in np.arange(0.0, 1.0, 0.0025):
            if np.mean(np.abs(r_rel) <= norm.ppf(0.95) * np.sqrt(s_rel ** 2 + e ** 2)) >= 0.9:
                extra_rel = float(e)
                break
    return {"coverage90_backtest": cover, "n_party_elections": int(len(d)), "inflation_factor": k,
            "extra_sd_relative": extra_rel, "rmse_pp": float(np.sqrt(np.mean(r ** 2))),
            "rmse_relative": float(np.sqrt(np.mean(r_rel ** 2)))}


def main(tag: str = "deadline") -> dict:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    rng = np.random.default_rng(cfg["seed"])
    idata = az.from_netcdf(out / "traces" / "next.nc")
    post = idata.posterior.stack(sample=("chain", "draw"))
    pi_T = post["pi"].isel(week=-1).transpose("sample", "party").values          # (S, P)
    sigma = post["sigma_rw"].transpose("sample", "party").values                 # (S, P)
    parties = list(post["party"].values)
    weeks_ahead = int((pd.Timestamp(cfg["legal_deadline"]) - pd.Timestamp(cfg["cutoff_date"])).days // 7)

    details = pd.read_csv(out / "backtest_details.csv")
    rev = test_mean_reversion(details)
    infl = test_error_inflation(details)
    w = rev["chosen_weight"]

    theta = logit(np.clip(pi_T, 1e-5, 1 - 1e-5))
    theta_h = theta + np.sqrt(weeks_ahead) * sigma * rng.standard_normal(theta.shape)
    if infl["inflation_factor"] > 1.0:
        # election-day error proportional to the party's share: a relative error delta in p is
        # delta / (1 - p) on the logit scale
        p = expit(theta_h)
        theta_h = theta_h + rng.standard_normal(theta.shape) * infl["extra_sd_relative"] / (1 - p)
    shares = expit(theta_h)
    if w > 0:
        nat = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "results_national.parquet")
        last = nat[nat.election == "202307"].set_index("party")["share_valid"]
        anchor = np.array([last.get(p, 0.0) for p in parties])
        shares = (1 - w) * shares + w * anchor[None, :]
    draws = pd.DataFrame(shares, columns=parties)
    draws.to_parquet(out / f"state_draws_{tag}.parquet", index=False)

    seat_df, q, probs = seats_main(n_sims=cfg["backtest"]["n_sims"], tag=tag,
                                   state_file=str(out / f"state_draws_{tag}.parquet"), write=False)
    seat_df.to_parquet(out / f"seat_draws_{tag}.parquet", index=False)
    q.to_csv(out / f"seats_summary_{tag}.csv")
    probs.to_csv(out / f"seat_probabilities_{tag}.csv", index=False)
    vote_q = draws.quantile([0.05, 0.5, 0.95]).T
    vote_q.columns = ["q05", "q50", "q95"]
    vote_q.to_csv(out / f"vote_summary_{tag}.csv")
    meta = {"tag": tag, "cutoff_date": cfg["cutoff_date"], "horizon": cfg["legal_deadline"],
            "weeks_ahead": weeks_ahead, "mean_reversion": rev, "error_inflation": infl}
    (out / f"forecast_{tag}.json").write_text(json.dumps(meta, indent=2))
    from electoral.plots import plot_bloc_majority, plot_seat_distributions
    from electoral.project_seats import blocs_from_map
    figs = ROOT / cfg["paths"]["figures"]
    plot_seat_distributions(seat_df, ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF"],
                            figs / f"seats_{tag}.png", cfg["cutoff_date"])
    blocs = blocs_from_map()
    plot_bloc_majority(seat_df, {k: v for k, v in blocs.items() if k in
                       ["Right (PP+Vox+UPN+SALF)", "2023 investiture bloc (above + PNV + Junts)"]},
                       figs / f"bloc_majority_{tag}.png", cfg["cutoff_date"])
    print(json.dumps(meta, indent=2))
    print(q.round(1).to_string())
    print(probs.round(3).to_string())
    decompose_uncertainty(tag)
    return meta



def decompose_uncertainty(tag: str = "deadline") -> pd.DataFrame:
    """Seat sd per party under nested sources of uncertainty (answers 'what drives it?').

    variants: nowcast (posterior at cut-off, no provincial noise) -> + provincial swing noise ->
    + 47 weeks of random-walk drift -> + election-day error. Written to outputs/uncertainty_decomposition.csv.
    """
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    rng = np.random.default_rng(cfg["seed"] + 1)
    idata = az.from_netcdf(out / "traces" / "next.nc")
    post = idata.posterior.stack(sample=("chain", "draw"))
    pi_T = post["pi"].isel(week=-1).transpose("sample", "party").values
    sigma = post["sigma_rw"].transpose("sample", "party").values
    parties = list(post["party"].values)
    W = int((pd.Timestamp(cfg["legal_deadline"]) - pd.Timestamp(cfg["cutoff_date"])).days // 7)
    infl = test_error_inflation(pd.read_csv(out / "backtest_details.csv"))
    theta = logit(np.clip(pi_T, 1e-5, 1 - 1e-5))
    z1, z2 = rng.standard_normal(theta.shape), rng.standard_normal(theta.shape)
    drift = theta + np.sqrt(W) * sigma * z1
    p = expit(drift)
    full = drift + z2 * infl["extra_sd_relative"] / (1 - p)
    variants = {"nowcast_no_swing_noise": (pi_T, False), "nowcast": (pi_T, True),
                "+drift_to_deadline": (expit(drift), True), "+election_day_error": (expit(full), True)}
    from electoral.seats import calibrate_swing_noise, province_baseline, simulate_seats
    from electoral.project_seats import PROXIES
    proc = ROOT / cfg["paths"]["processed"]
    res, tot, nat = (pd.read_parquet(proc / f) for f in ("results_province.parquet", "province_totals.parquet", "results_national.parquet"))
    shares0, blank0, seats0 = province_baseline(res, tot, "202307")
    national0 = nat[nat.election == "202307"].set_index("party")["share_valid"]
    noise_sd = json.loads((out / "swing_calibration.json").read_text())["noise_sd_log"]
    rows = []
    for name, (sh, noise) in variants.items():
        draws = pd.DataFrame(sh, columns=parties)
        seat_df, _ = simulate_seats(draws, shares0, blank0, seats0, national0, 4000, noise_sd, cfg["seed"],
                                    PROXIES, noise=noise)
        right = seat_df[["PP", "VOX", "UPN", "SALF"]].sum(axis=1)
        row = {"variant": name, **{p: float(seat_df[p].std()) for p in ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "JUNTS", "ERC"]},
               "right_bloc_sd": float(right.std()), "p_right_majority": float((right >= 176).mean())}
        rows.append(row)
    df = pd.DataFrame(rows).round(3)
    df.to_csv(out / "uncertainty_decomposition.csv", index=False)
    print(df.to_string())
    return df


if __name__ == "__main__":
    main()

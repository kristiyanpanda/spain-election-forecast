"""Phase D entry point: Monte Carlo seat projection from the aggregator's cut-off state.

Outputs (outputs/):
    seat_draws_next.parquet     n_sims x parties integer seats
    seats_summary_next.csv      per-party seat quantiles
    seat_probabilities_next.csv bloc-majority and threshold probabilities
    swing_calibration.json      provincial swing noise sd and how it was calibrated
reports/figures/: seats_distribution.png, bloc_majority.png
"""

from __future__ import annotations

import json

import pandas as pd
import yaml

from electoral import ROOT, load_config
from electoral.plots import plot_bloc_majority, plot_seat_distributions
from electoral.seats import calibrate_swing_noise, province_baseline, simulate_seats, summarise_seats

PROXIES = {"PODEMOS": "SUMAR", "SALF": None}   # geography borrowed by entrants


def blocs_from_map() -> dict[str, list[str]]:
    pm = yaml.safe_load((ROOT / "data/party_map_polls.yaml").read_text(encoding="utf-8"))["parties"]
    by = {}
    for p, meta in pm.items():
        by.setdefault(meta["bloc"], []).append(p)
    return {
        "Right (PP+Vox+UPN+SALF)": ["PP", "VOX", "UPN", "SALF"],
        "PP+Vox": ["PP", "VOX"],
        "Left + peripheral left (PSOE+Sumar+Podemos+ERC+Bildu+BNG+CC+Compromís)":
            ["PSOE", "SUMAR", "PODEMOS", "ERC", "BILDU", "BNG", "CC", "COMPROMIS"],
        "2023 investiture bloc (above + PNV + Junts)":
            ["PSOE", "SUMAR", "PODEMOS", "ERC", "BILDU", "BNG", "CC", "COMPROMIS", "PNV", "JUNTS"],
        "State-wide left (PSOE+Sumar+Podemos)": ["PSOE", "SUMAR", "PODEMOS"],
    }


def main(n_sims: int = 10_000, tag: str = "next", state_file: str | None = None,
         base_election: str = "202307", write: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    figs = ROOT / cfg["paths"]["figures"]
    proc = ROOT / cfg["paths"]["processed"]
    res = pd.read_parquet(proc / "results_province.parquet")
    tot = pd.read_parquet(proc / "province_totals.parquet")
    nat = pd.read_parquet(proc / "results_national.parquet")
    draws = pd.read_parquet(state_file or out / f"state_draws_{tag}.parquet")

    shares0, blank0, seats0 = province_baseline(res, tot, base_election)
    national0 = nat[nat.election == base_election].set_index("party")["share_valid"]
    elections = cfg["mir"]["elections"]
    i = elections.index(base_election)
    calib = {}
    for a, b in [(elections[i - 2], elections[i - 1]), (elections[i - 1], base_election)]:
        calib[f"{a}->{b}"] = calibrate_swing_noise(res, tot, a, b, [p for p in draws.columns if p in national0])
    noise_sd = float(sum(calib.values()) / len(calib))

    seat_df, share_df = simulate_seats(draws, shares0, blank0, seats0, national0, n_sims, noise_sd,
                                       cfg["seed"], PROXIES)
    blocs = blocs_from_map()
    q, probs = summarise_seats(seat_df, blocs, {"PP": [150, 160, 176], "VOX": [40, 50, 60],
                                                "PSOE": [100, 110, 121], "SUMAR": [10, 20],
                                                "PODEMOS": [1, 4], "SALF": [1]})
    q["cutoff_date"] = cfg["cutoff_date"]
    probs["cutoff_date"] = cfg["cutoff_date"]
    if write:
        seat_df.to_parquet(out / f"seat_draws_{tag}.parquet", index=False)
        q.to_csv(out / f"seats_summary_{tag}.csv")
        probs.to_csv(out / f"seat_probabilities_{tag}.csv", index=False)
        (out / "swing_calibration.json").write_text(json.dumps(
            {"noise_sd_log": noise_sd, "components": calib, "base_election": base_election,
             "n_sims": n_sims, "proxies": PROXIES, "cutoff_date": cfg["cutoff_date"]}, indent=2))
        last = nat[nat.election == base_election].set_index("party")["escanos"].astype(int).to_dict()
        plot_seat_distributions(seat_df, ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF"],
                                figs / "seats_distribution.png", cfg["cutoff_date"], last)
        plot_bloc_majority(seat_df, {k: v for k, v in blocs.items() if k in
                           ["Right (PP+Vox+UPN+SALF)", "2023 investiture bloc (above + PNV + Junts)"]},
                           figs / "bloc_majority.png", cfg["cutoff_date"])
        print(q.round(1).to_string())
        print(probs.round(3).to_string())
        print("swing noise sd (log):", round(noise_sd, 3), calib)
    return seat_df, q, probs


if __name__ == "__main__":
    main()

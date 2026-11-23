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

import numpy as np
import pandas as pd
import yaml

from electoral import ROOT, load_config
from electoral.figures import draw_seats, each_language
from electoral.seats import calibrate_swing_noise, province_baseline, simulate_seats, summarise_seats

def proxies(cfg: dict) -> dict:
    """Geography borrowed by parties without a 2023 provincial footprint (config: seats.proxies)."""
    return dict(cfg["seats"]["proxies"])


def absent(cfg: dict) -> dict:
    """Provinces where a tracked party fields no list (config: seats.absent)."""
    return {p: [str(x).zfill(2) for x in v] for p, v in (cfg["seats"].get("absent") or {}).items()}


def regional_parts(cfg: dict, polls: pd.DataFrame) -> dict:
    """Fraction of a tracked party's national share cast for its list in one region (config
    seats.regional_part), from the polls that publish both figures apart: the median over
    pollsters of each pollster's median ratio in the last ``days``, and the log sd between them."""
    from electoral.model import drop_overlapping_waves

    cutoff = pd.Timestamp(cfg["cutoff_date"])
    out = {}
    for party, spec in (cfg["seats"].get("regional_part") or {}).items():
        x = polls[(polls.cycle == "next") & ~polls.is_election & polls.value.notna()
                  & polls.party.isin([spec["part"], spec["rest"]])
                  & (polls.fieldwork_end > cutoff - pd.Timedelta(f"{spec['days']}D"))
                  & (polls.fieldwork_end <= cutoff)]
        w = drop_overlapping_waves(x).pivot_table(index=["poll_id", "pollster"], columns="party",
                                                  values="value", aggfunc="first")
        if not {spec["part"], spec["rest"]} <= set(w.columns):
            continue
        w = w.dropna(subset=[spec["part"], spec["rest"]])
        ratio = (w[spec["part"]] / (w[spec["part"]] + w[spec["rest"]])).groupby("pollster").median()
        if len(ratio) < spec.get("min_pollsters", 3):
            continue
        out[party] = {"provinces": [str(p).zfill(2) for p in spec["provinces"]],
                      "fraction": float(ratio.median()), "sd_log": float(np.log(ratio).std()),
                      "n_pollsters": int(len(ratio))}
    return out


def scenario_merges(cfg: dict, scenario: str | None) -> list[dict]:
    """Joint lists / coalitions of a party-supply scenario (config: seats.scenarios)."""
    return list(cfg["seats"]["scenarios"][scenario]["merges"]) if scenario else []


def regional_observations(cfg: dict) -> list[dict]:
    """Regional survey estimates for the seat model (data/processed/regional_polls.csv)."""
    path = ROOT / cfg["paths"]["processed"] / "regional_polls.csv"
    if not cfg.get("regional", {}).get("enabled") or not path.exists():
        return []
    r = pd.read_csv(path, dtype={"provinces": str})
    return [{"provinces": row.provinces.split(), "party": row.party, "share": row.share, "sd": row.sd_pp}
            for row in r.itertuples()]


def add_fixed_shares(draws: pd.DataFrame, cfg: dict, polls: pd.DataFrame) -> pd.DataFrame:
    """Append parties kept out of the aggregator (config seats.fixed_shares): each draw gets the
    median of the party's polls in the last ``days`` before the cut-off (non-overlapping waves
    only, as in the aggregator), times log-normal noise."""
    from electoral.model import drop_overlapping_waves

    spec = cfg["seats"].get("fixed_shares") or {}
    if not spec:
        return draws
    rng = np.random.default_rng(cfg["seed"] + 7)
    cutoff = pd.Timestamp(cfg["cutoff_date"])
    out = draws.copy()
    for p, f in spec.items():
        if p in out:
            continue
        x = polls[(polls.cycle == "next") & (polls.party == p) & polls.value.notna()
                  & (polls.fieldwork_end > cutoff - pd.Timedelta(f"{f['days']}D"))
                  & (polls.fieldwork_end <= cutoff)]
        x = drop_overlapping_waves(x)["value"]
        if x.empty:
            continue
        med = float(x.median()) / 100
        out[p] = med * np.exp(rng.normal(-0.5 * f["sd_log"] ** 2, f["sd_log"], size=len(out)))
    return out


def province_weights(tot: pd.DataFrame, election: str) -> pd.Series:
    t = tot[tot.election == election].set_index("prov")["votos_validos"]
    return t / t.sum()


def blocs_from_map() -> dict[str, list[str]]:
    pm = yaml.safe_load((ROOT / "data/party_map_polls.yaml").read_text(encoding="utf-8"))["parties"]
    by = {}
    for p, meta in pm.items():
        by.setdefault(meta["bloc"], []).append(p)
    return {
        "Right (PP+Vox+UPN+SALF)": ["PP", "VOX", "UPN", "SALF"],
        "PP+Vox": ["PP", "VOX"],
        "Left + peripheral left (PSOE+Sumar/FA+Podemos+ERC+Bildu+BNG+CC+Compromís+AA)":
            ["PSOE", "SUMAR", "PODEMOS", "ERC", "BILDU", "BNG", "CC", "COMPROMIS", "AA"],
        "2023 investiture bloc (above + PNV + Junts)":
            ["PSOE", "SUMAR", "PODEMOS", "ERC", "BILDU", "BNG", "CC", "COMPROMIS", "AA", "PNV", "JUNTS"],
        "State-wide left (PSOE+Sumar/FA+Podemos)": ["PSOE", "SUMAR", "PODEMOS"],
    }


def main(n_sims: int = 10_000, tag: str = "next", state_file: str | None = None,
         base_election: str = "202307", write: bool = True,
         scenario: str | None = "split",
         regional: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    proc = ROOT / cfg["paths"]["processed"]
    res = pd.read_parquet(proc / "results_province.parquet")
    tot = pd.read_parquet(proc / "province_totals.parquet")
    nat = pd.read_parquet(proc / "results_national.parquet")
    draws = pd.read_parquet(state_file or out / f"state_draws_{tag}.parquet")
    polls = pd.read_parquet(proc / "polls_long.parquet")
    draws = add_fixed_shares(draws, cfg, polls)
    parts = regional_parts(cfg, polls)

    shares0, blank0, seats0 = province_baseline(res, tot, base_election)
    national0 = nat[nat.election == base_election].set_index("party")["share_valid"]
    elections = cfg["mir"]["elections"]
    i = elections.index(base_election)
    calib = {}
    for a, b in [(elections[i - 2], elections[i - 1]), (elections[i - 1], base_election)]:
        calib[f"{a}->{b}"] = calibrate_swing_noise(res, tot, a, b, [p for p in draws.columns if p in national0])
    noise_sd = float(sum(calib.values()) / len(calib))

    seat_df, share_df = simulate_seats(draws, shares0, blank0, seats0, national0, n_sims, noise_sd,
                                       cfg["seed"], proxies(cfg), merges=scenario_merges(cfg, scenario),
                                       weights=province_weights(tot, base_election),
                                       regional=regional_observations(cfg) if regional else None,
                                       regional_swing_sd=cfg["regional"]["swing_sd_pp"],
                                       absent=absent(cfg), regional_part=parts)
    blocs = blocs_from_map()
    q, probs = summarise_seats(seat_df, blocs, {"PP": [150, 160, 176], "VOX": [40, 50, 60],
                                                "PSOE": [100, 110, 121], "SUMAR": [10, 20],
                                                "PODEMOS": [1, 4], "SALF": [1]})
    q["cutoff_date"] = cfg["cutoff_date"]
    probs["cutoff_date"] = cfg["cutoff_date"]
    q["scenario"] = probs["scenario"] = scenario or "none"
    if write:
        seat_df.to_parquet(out / f"seat_draws_{tag}.parquet", index=False)
        q.to_csv(out / f"seats_summary_{tag}.csv")
        probs.to_csv(out / f"seat_probabilities_{tag}.csv", index=False)
        (out / "swing_calibration.json").write_text(json.dumps(
            {"noise_sd_log": noise_sd, "components": calib, "base_election": base_election,
             "n_sims": n_sims, "proxies": proxies(cfg), "absent": absent(cfg), "regional_part": parts,
             "scenario": scenario,
             "cutoff_date": cfg["cutoff_date"]}, indent=2))
        last = nat[nat.election == base_election].set_index("party")["escanos"].astype(int).to_dict()
        each_language(draw_seats, seat_df, "next", cfg, last)
        print(q.round(1).to_string())
        print(probs.round(3).to_string())
        print("swing noise sd (log):", round(noise_sd, 3), calib)
    return seat_df, q, probs


if __name__ == "__main__":
    main()

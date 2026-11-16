"""Phase C entry point: fit the poll aggregator for the current cycle and write its outputs.

Outputs (outputs/):
    poll_average_daily_next.parquet   daily latent share summary per party (the file other
                                      projects consume; see docs/outputs.md)
    poll_average_daily.csv            same, CSV
    house_effects_next.csv            pollster x party house effects (pp)
    state_draws_next.parquet          posterior draws of the share vector at the cut-off week
    diagnostics_next.json             sampler diagnostics and run metadata
    traces/next.nc                    full posterior (gitignored)
reports/figures/ (and spanish version/figures/): trend_national.png, trend_regional.png,
house_effects.png
"""

from __future__ import annotations

import json

import pandas as pd

from electoral import ROOT, load_config
from electoral.figures import draw_trends, each_language
from electoral.model import fit, prepare, save_run


def main(draws: int | None = None, tune: int | None = None, chains: int | None = None) -> dict:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    polls = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "polls_long.parquet")
    nat = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "results_national.parquet")
    anchor = nat[nat.election == "202307"].set_index("party")["share_valid"].to_dict()

    d = prepare(polls, "next", cfg["model"]["parties"], anchor, cfg["last_election"],
                cfg["cutoff_date"], breaks=cfg["model"]["breaks"], composites=cfg["model"].get("composites"),
                families=cfg["model"].get("house_families"))
    s = dict(cfg["model"]["sampling"])
    s.update({k: v for k, v in {"draws": draws, "tune": tune, "chains": chains}.items() if v})
    idata = fit(d, seed=cfg["seed"], **s)
    diag = save_run(idata, d, out, "next", cfg["cutoff_date"])
    print(json.dumps(diag, indent=2))

    trend = pd.read_parquet(out / "poll_average_daily_next.parquet")
    trend.to_csv(out / "poll_average_daily.csv", index=False)
    each_language(draw_trends, cfg)
    return diag


if __name__ == "__main__":
    main()

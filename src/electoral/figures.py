"""Draw every static figure from the saved outputs, in English and Spanish.

The pipeline phases call the ``draw_*`` functions right after writing their outputs; ``electoral
figures`` re-draws everything without refitting (a change of wording or layout does not need the
sampler). English figures go to ``reports/figures``, Spanish ones to ``spanish version/figures``.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from electoral import ROOT, i18n, load_config
from electoral.i18n import tr

STATEWIDE = ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF"]
REGIONAL = ["ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"]
BLOCS_SHOWN = ["Right (PP+Vox+UPN+SALF)", "2023 investiture bloc (above + PNV + Junts)"]
BACKTEST_LABELS = {"e2016": "June 2016", "e2019apr": "April 2019", "e2019nov": "November 2019",
                   "e2023": "July 2023"}


def each_language(draw: Callable[..., None], *args, **kwargs) -> None:
    """Run a drawing function once per language, leaving the language as it was."""
    before = i18n.get_lang()
    try:
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            draw(*args, **kwargs)
    finally:
        i18n.set_lang(before)


def draw_trends(cfg: dict | None = None) -> None:
    """trend_national.png, trend_regional.png and house_effects.png (aggregator outputs)."""
    from electoral.plots import plot_house_effects, plot_trends

    cfg = cfg or load_config()
    out, figs = ROOT / cfg["paths"]["outputs"], i18n.figures_dir(cfg)
    proc = ROOT / cfg["paths"]["processed"]
    polls = pd.read_parquet(proc / "polls_long.parquet")
    nat = pd.read_parquet(proc / "results_national.parquet")
    anchor = nat[nat.election == "202307"].set_index("party")["share_valid"].to_dict()
    trend = pd.read_parquet(out / "poll_average_daily_next.parquet")
    raw = polls[(polls.cycle == "next") & (~polls.is_election)]
    plot_trends(trend, raw, STATEWIDE, figs / "trend_national.png", cfg["cutoff_date"],
                tr("State-wide parties since the July 2023 election: polls and latent trend"),
                cfg["last_election"], anchor)
    plot_trends(trend, raw, REGIONAL, figs / "trend_regional.png", cfg["cutoff_date"],
                tr("Main regional parties: polls and latent trend"), cfg["last_election"], anchor)
    he = pd.read_csv(out / "house_effects_next.csv")
    plot_house_effects(he, ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS"], figs / "house_effects.png",
                       cfg["cutoff_date"])


def draw_seats(seat_df: pd.DataFrame, tag: str, cfg: dict | None = None, last: dict[str, int] | None = None,
               hemicycle: str | None = None) -> None:
    """Seat histograms and bloc totals for one set of seat draws.

    ``tag`` names the files: ``next`` (cut-off) writes seats_distribution.png and bloc_majority.png;
    ``29n_split`` writes seats_29n_split.png and bloc_majority_29n_split.png. ``hemicycle`` is the
    scenario key when the Congress chart is wanted too.
    """
    from electoral.plots import expected_seats, plot_bloc_majority, plot_hemicycle, plot_seat_distributions
    from electoral.project_seats import blocs_from_map

    cfg = cfg or load_config()
    figs = i18n.figures_dir(cfg)
    blocs = {k: v for k, v in blocs_from_map().items() if k in BLOCS_SHOWN}
    cutoff = cfg["cutoff_date"]
    if tag == "next":
        plot_seat_distributions(seat_df, STATEWIDE, figs / "seats_distribution.png", cutoff, last)
        plot_bloc_majority(seat_df, blocs, figs / "bloc_majority.png", cutoff)
        return
    plot_seat_distributions(seat_df, STATEWIDE, figs / f"seats_{tag}.png", cutoff)
    plot_bloc_majority(seat_df, blocs, figs / f"bloc_majority_{tag}.png", cutoff)
    if hemicycle:
        label = tr(cfg["seats"]["scenarios"][hemicycle]["label"])
        plot_hemicycle(expected_seats(seat_df), figs / f"hemicycle_{tag}.png", cutoff,
                       tr("Forecast Congress, {date}", date=i18n.date(cfg["election_date"])),
                       tr("Expected seats, {scenario}: mean of {n} simulations, rounded to 350.\nOthers: local lists "
                          "(Soria ¡Ya!, Teruel Existe, UPL).", scenario=label[0].lower() + label[1:],
                          n=i18n.thousands(len(seat_df))),
                       tr("Seats: model forecast, not a result."))


def draw_backtest(details: pd.DataFrame, cfg: dict | None = None) -> None:
    from electoral.plots import plot_backtest

    cfg = cfg or load_config()
    plot_backtest(details, i18n.figures_dir(cfg) / "backtest.png", cfg["cutoff_date"], BACKTEST_LABELS)


def main(lang: str = "all", descriptive: bool = True) -> None:
    """Re-draw all figures from the files in outputs/ and data/processed/."""
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    nat = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "results_national.parquet")
    last = nat[nat.election == "202307"].set_index("party")["escanos"].astype(int).to_dict()

    def everything() -> None:
        draw_trends(cfg)
        draw_seats(pd.read_parquet(out / "seat_draws_next.parquet"), "next", cfg, last)
        for scenario in cfg["seats"]["scenarios"]:
            f = out / f"seat_draws_29n_{scenario}.parquet"
            if f.exists():
                draw_seats(pd.read_parquet(f), f"29n_{scenario}", cfg, hemicycle=scenario)
        if (out / "backtest_details.csv").exists():
            draw_backtest(pd.read_csv(out / "backtest_details.csv"), cfg)
        if descriptive:
            from electoral.descriptive import compute, draw

            draw(*compute(cfg), cfg)
        print(f"figures ({i18n.get_lang()}) -> {i18n.figures_dir(cfg)}")

    if lang == "all":
        each_language(everything)
    else:
        i18n.set_lang(lang)
        try:
            everything()
        finally:
            i18n.set_lang("en")


if __name__ == "__main__":
    main()

"""Command-line entry point: `electoral <phase>` (see Makefile)."""

from __future__ import annotations

import typer

app = typer.Typer(help="Spanish general election forecast pipeline.", no_args_is_help=True)


@app.command("build-data")
def build_data() -> None:
    """Phase A: download and tidy official results and polls."""
    from electoral.build_data import main
    main()


@app.command("aggregate")
def aggregate(draws: int = None, tune: int = None, chains: int = None) -> None:  # type: ignore[assignment]
    """Phase C: fit the Bayesian poll aggregator for the current cycle."""
    from electoral.aggregate import main
    main(draws=draws, tune=tune, chains=chains)


@app.command("seats")
def seats(n_sims: int = 10_000) -> None:
    """Phase D: Monte Carlo seat projection from the aggregator's cut-off state."""
    from electoral.project_seats import main
    main(n_sims=n_sims)


@app.command("backtest")
def backtest() -> None:
    """Phase E: replay the pipeline 30 days before 2016, Apr-2019, Nov-2019 and 2023."""
    from electoral.backtest import main
    main()


@app.command("descriptive")
def descriptive() -> None:
    """Phase B: party-system indices and static figures."""
    from electoral.descriptive import main
    main()


@app.command("forecast")
def forecast() -> None:
    """Phase F: projection to the legal deadline (after the backtest)."""
    from electoral.forecast import main
    main()


@app.command("report")
def report() -> None:
    """Phase G: interactive HTML in docs/index.html."""
    from electoral.report import main
    main()


if __name__ == "__main__":
    app()

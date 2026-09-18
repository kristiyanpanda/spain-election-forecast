"""Command-line entry point: `electoral <phase>` (see Makefile)."""

from __future__ import annotations

import typer

app = typer.Typer(help="Spanish general election forecast pipeline.", no_args_is_help=True)


@app.command("build-data")
def build_data() -> None:
    """Phase A: download and tidy official results and polls."""
    from electoral.build_data import main
    main()


if __name__ == "__main__":
    app()

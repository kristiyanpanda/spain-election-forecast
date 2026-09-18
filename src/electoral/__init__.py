"""electoral: Bayesian poll aggregation and seat projection for Spanish general elections."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict:
    """Read config.yaml (dates, seeds, paths, sources) from the repo root."""
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

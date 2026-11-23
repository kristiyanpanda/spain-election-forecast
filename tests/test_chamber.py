"""The Congress rebuilt from congreso.es membership dates matches the votes and counts on record."""

import pandas as pd
import pytest

from electoral import ROOT
from electoral.chamber import INVESTITURE_BLOC, SNAPSHOTS, composition, summarise

MEMBERS = ROOT / "data/processed/congreso_xv_groups.csv"
pytestmark = pytest.mark.skipif(not MEMBERS.exists(), reason="run `electoral chamber` first")


@pytest.fixture(scope="module")
def members():
    return pd.read_csv(MEMBERS, parse_dates=["start", "end"])


def test_both_snapshots_fill_the_350_seats(members):
    for day in SNAPSHOTS.values():
        assert composition(members, day).sum() == 350


def test_investiture_day_reproduces_the_179_to_171_vote(members):
    seats = composition(members, SNAPSHOTS["investiture"])
    assert seats.reindex(INVESTITURE_BLOC).fillna(0).sum() == 179
    assert seats[["PP", "VOX", "UPN"]].sum() == 171


def test_groups_at_the_dissolution_match_congreso_es(members):
    groups = composition(members, SNAPSHOTS["dissolution"], by="group").to_dict()
    assert groups == {"PP": 137, "PSOE": 121, "VOX": 32, "SUMAR": 26, "MIXTO": 9, "JUNTS": 7, "ERC": 7,
                      "BILDU": 6, "PNV": 5}


def test_summary_reads_seat_changes_from_the_draws(members):
    draws = pd.DataFrame({"PP": [120, 130], "PSOE": [110, 120], "VOX": [70, 60], "SUMAR": [10, 10]})
    per_party, blocs = summarise(members, draws)
    vox = per_party.set_index("party").loc["VOX"]
    assert vox.dissolution_2026 == 32 and vox.forecast_q50 == 65 and vox.p_more == 1.0
    assert blocs.set_index("bloc").loc["2023 investiture bloc", "dissolution_2026"] == 179

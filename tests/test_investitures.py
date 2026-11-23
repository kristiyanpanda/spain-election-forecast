"""Every investiture chamber fills 350 seats, reproduces the official vote and matches the election."""

import pandas as pd
import pytest

from electoral import ROOT
from electoral.investitures import INVESTITURES, check, counts

# election whose lists made up the chamber of each investiture
ELECTION = {"aznar_1996": "199603", "aznar_2000": "200003", "zapatero_2004": "200403", "zapatero_2008": "200803",
            "rajoy_2011": "201111", "rajoy_2016": "201606", "sanchez_2018": "201606", "sanchez_2020": "201911"}
# parties that sat apart from the list they were elected on (folded back to compare with the results)
LIST_OF = {"rajoy_2011": {"UPN": "PP", "NC": "CC"},
           "rajoy_2016": {"UPN": "PP", "FAC": "PP", "NC": "PSOE", "COMPROMIS": "UP"},
           "sanchez_2018": {"UPN": "PP", "FAC": "PP", "NC": "PSOE", "COMPROMIS": "UP"},
           "sanchez_2020": {"FAC": "PP", "NC": "CC"}, "aznar_2000": {"ICV": "IU"}}
RESULTS = ROOT / "data/processed/results_national.parquet"


@pytest.mark.parametrize("inv", INVESTITURES, ids=[i["key"] for i in INVESTITURES])
def test_chamber_and_vote_match_the_official_result(inv):
    check(inv)


def test_split_votes_must_add_up():
    assert counts({"a": 68, "n": 15, "x": 1}, 84) == {"a": 68, "n": 15, "x": 1}
    with pytest.raises(ValueError):
        counts({"a": 68, "n": 15}, 84)


@pytest.mark.skipif(not RESULTS.exists(), reason="run the data build first")
@pytest.mark.parametrize("inv", INVESTITURES, ids=[i["key"] for i in INVESTITURES])
def test_seats_match_the_election_lists(inv):
    res = pd.read_parquet(RESULTS)
    res = res[(res.election == ELECTION[inv["key"]]) & (res.escanos > 0)].set_index("party").escanos
    fold = LIST_OF.get(inv["key"], {})
    seats = pd.Series([s for _, s, _ in inv["seats"]], index=[fold.get(p, p) for p, _, _ in inv["seats"]])
    seats = seats.groupby(level=0).sum()
    assert seats.sort_index().to_dict() == res.sort_index().to_dict()

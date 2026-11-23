"""The parties-since-1977 table agrees with the official results it is built from."""

import pandas as pd
import pytest

from electoral import ROOT
from electoral.history import LINEAGES, OUT, segments

HIST = ROOT / "data/processed" / OUT
RESULTS = ROOT / "data/processed/results_national.parquet"
pytestmark = pytest.mark.skipif(not (HIST.exists() and RESULTS.exists()), reason="run `electoral history` first")


@pytest.fixture(scope="module")
def hist():
    return pd.read_csv(HIST, dtype={"election": str}, parse_dates=["date"])


def test_lineages_match_their_families_where_the_results_have_them(hist):
    res = pd.read_parquet(RESULTS)
    for lid, fams, _, _ in LINEAGES:
        got = res[res.party.isin(fams)].groupby("election").share_valid.sum() * 100
        mine = hist[hist.lineage == lid].set_index("election").share
        for e, v in got.items():
            if v >= 0.1:
                assert mine[e] == pytest.approx(v, abs=0.01), (lid, e)


def test_landmarks(hist):
    s = hist.set_index(["lineage", "election"]).share
    assert s["PSOE", "198210"] == pytest.approx(48.1, abs=0.05)
    assert s["UCD", "197903"] == pytest.approx(34.8, abs=0.05)
    assert s["PP", "201111"] == pytest.approx(44.6, abs=0.05)
    assert hist[hist.lineage == "UCD"].election.max() == "198210"
    assert "202307" not in set(hist[hist.lineage == "CS"].election)


def test_real_gaps_stay_gaps(hist):
    # HB/Batasuna: abstention in 2000, banned in 2004 and 2008
    assert not {"200003", "200403", "200803"} & set(hist[hist.lineage == "BILDU"].election)
    assert len(segments(hist, "BILDU")) == 2
    # ERC ran in every election (below 1 % in 1986 and 1989): one unbroken line
    assert len(segments(hist, "ERC")) == 1

import numpy as np
import pandas as pd
import pytest

from electoral import ROOT
from electoral.seats import dhondt, dhondt_batch, province_baseline


def test_dhondt_textbook_example():
    # classic example: 8 seats, A 100k, B 80k, C 30k, D 20k -> 4, 3, 1, 0
    assert dhondt(np.array([100_000, 80_000, 30_000, 20_000]), 8, threshold=0.0).tolist() == [4, 3, 1, 0]


def test_dhondt_threshold_and_single_seat():
    v = np.array([50.0, 30.0, 2.9, 17.1])
    assert dhondt(v, 5, threshold=0.03).tolist() == [3, 1, 0, 1]   # 2.9 % list excluded
    assert dhondt(v, 1).tolist() == [1, 0, 0, 0]                    # Ceuta/Melilla: plurality
    assert dhondt(v, 0).sum() == 0


def test_dhondt_blank_votes_count_for_threshold_only():
    v = np.array([60.0, 37.0, 3.0])
    assert dhondt(v, 10, threshold=0.03, blank=0.0)[2] >= 0
    # with blank ballots the 3.0 list falls under 3 % of the valid vote
    assert dhondt(v, 10, threshold=0.03, blank=2.0)[2] == 0


def test_batch_matches_scalar():
    rng = np.random.default_rng(1)
    shares = rng.dirichlet(np.ones(6) * 2, size=50)
    for seats in (1, 4, 12, 37):
        b = dhondt_batch(shares, seats, 0.03, 0.01)
        for s in range(50):
            assert b[s].tolist() == dhondt(shares[s], seats, 0.03, 0.01).tolist()
        assert (b.sum(axis=1) == seats).all()


@pytest.mark.parametrize("election", ["201911", "202307"])
def test_reproduces_official_seats(election):
    """Join + D'Hondt must reproduce the official seat count exactly, province by province."""
    res = pd.read_parquet(ROOT / "data/processed/results_province.parquet")
    tot = pd.read_parquet(ROOT / "data/processed/province_totals.parquet")
    r = res[res.election == election]
    t = tot[tot.election == election].set_index("prov")
    mism = []
    for prov, g in r.groupby("prov"):
        got = dhondt(g["votos"].values, int(t.loc[prov, "escanos"]), 0.03, float(t.loc[prov, "votos_blancos"]))
        if got.tolist() != g["escanos"].astype(int).tolist():
            mism.append(prov)
    assert mism == []
    shares, blank, seats = province_baseline(res, tot, election)
    assert seats.sum() == 350 and len(shares) == 52
    assert np.allclose(shares.sum(axis=1) + blank, 1.0, atol=1e-6)

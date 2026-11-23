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


def test_merges_move_shares_into_joint_lists():
    from electoral.seats import apply_merges

    provs, col = ["08", "28", "46"], {"PODEMOS": 0, "SUMAR": 1, "ERC": 2}
    base = np.array([[0.04, 0.10, 0.12], [0.03, 0.08, 0.0], [0.05, 0.10, 0.0]])  # prov x party
    share = np.repeat(base[None], 2, axis=0)
    apply_merges(share, [{"provinces": ["46"], "party": "PODEMOS", "into": {"SUMAR": 1.0}},
                         {"provinces": ["08"], "party": "PODEMOS", "into": {"ERC": 0.5, "SUMAR": 0.5}}],
                 provs, col, np.random.default_rng(0))
    assert share[0, 2].tolist() == pytest.approx([0.0, 0.15, 0.0])           # Valencia: joint list
    assert share[0, 0].tolist() == pytest.approx([0.0, 0.12, 0.14])          # Catalonia: split 50/50
    assert share[0, 1].tolist() == pytest.approx([0.03, 0.08, 0.0])          # Madrid untouched


def test_merge_efficiency_applies_to_the_joint_total():
    from electoral.seats import apply_merges

    share = np.array([[[0.04, 0.10]]])                                        # 1 draw, 1 prov
    apply_merges(share, [{"provinces": "all", "party": "PODEMOS", "into": {"SUMAR": 1.0},
                          "efficiency": 0.83}], ["01"], {"PODEMOS": 0, "SUMAR": 1},
                 np.random.default_rng(0))
    assert share[0, 0].tolist() == pytest.approx([0.0, 0.83 * 0.14])


def test_regional_proxy_spreads_a_party_over_its_provinces_only():
    from electoral.seats import simulate_seats

    shares0 = pd.DataFrame({"A": [0.6, 0.6, 0.6]}, index=["04", "41", "28"])
    blank0 = pd.Series(0.0, index=shares0.index)
    seats0 = pd.Series(10, index=shares0.index)
    weights = pd.Series([0.25, 0.25, 0.5], index=shares0.index)
    draws = pd.DataFrame({"A": [0.6], "AA": [0.05]})
    seat_df, _ = simulate_seats(draws, shares0, blank0, seats0, pd.Series({"A": 0.6}), 1, 0.0, 1,
                                proxies={"AA": ["04", "41"]}, noise=False, weights=weights)
    # 5 % nationally, all of it in two provinces holding half the vote -> 10 % there, 0 in Madrid
    assert seat_df.loc[0, "AA"] == 2


def test_forecast_horizon_is_the_snap_election():
    from electoral import load_config
    from electoral.forecast import horizon

    cfg = load_config()
    day, weeks = horizon({**cfg, "cutoff_date": "2026-10-17"})
    assert day == pd.Timestamp("2026-11-29") and weeks == pytest.approx(43 / 7)


def test_hemicycle_layout_and_expected_seats():
    from electoral.plots import expected_seats, hemicycle_layout

    lay = hemicycle_layout(350)
    assert len(lay) == 350 and lay["angle"].is_monotonic_decreasing              # sorted left to right
    draws = pd.DataFrame({"PP": [130.6] * 3, "PSOE": [107.6] * 3, "VOX": [66.4] * 3, "SUMAR": [45.4] * 3})
    seats = expected_seats(draws)
    assert seats.sum() == 350 and list(seats.index) == ["SUMAR", "PSOE", "PP", "VOX"]

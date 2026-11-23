"""Party supply of the 29 Nov 2026 election as it reaches the pipeline: tables that give one figure
for two lists (colspan), the CIS pre-election table, trackers with overlapping fieldwork, level
shifts when polls switch to the registered ballots, and a party with no ballot in some provinces."""

import numpy as np
import pandas as pd
import pytest

from electoral import ROOT, cis, load_config
from electoral.model import apply_composites, drop_overlapping_waves, prepare
from electoral.wiki_polls import parse_tables, tables_to_long

RULES = cis.load_rules(ROOT / "data/party_map_cis.yaml")

SPAN = """
====Voting intention estimates====
=====2026 (with Broad Front)=====
{| class="wikitable"
|-
! rowspan="2"| Polling firm/Commissioner
! rowspan="2"| Fieldwork date
! rowspan="2"| Sample size
! [[File:a.svg|27px|link=People's Party (Spain)|PP]]
! [[File:b.svg|35px|link=Broad Front (Spain)|FA]]
! [[File:c.svg|35px|link=Valencian Front|FV]]
! [[File:d.svg|30px|link=Republican Left of Catalonia|ERC]]
! rowspan="2"| Lead
|-
! style="background:red;"|
! style="background:green;"|
! style="background:orange;"|
! style="background:yellow;"|
|-
| Sigma Dos/El Mundo<ref>{{cite web |title=colspan="3" in a title |url=https://a.b/c}}</ref>
| 3–12 Nov
| 4,620
| {{Party shading/PP}}| '''31.0'''<br/>{{font|size=75%|text=126/132}}
| colspan="2"| 7.3<br/>{{font|size=75%|text=13/15}}
| 2.7<br/>{{font|size=75%|text=8/9}}
| style="background:{{party color|People's Party (Spain)}}; color:white;"| 5.6
|-
| GAD3/Vocento
| 3–5 Nov
| 1,502
| {{Party shading/PP}}| '''31.9'''
| 6.0
| 1.5
| 2.7
| style="background:red; color:white;"| 6.0
|}
"""


def test_one_cell_for_two_lists_is_a_joint_label_and_keeps_columns_aligned():
    long = tables_to_long(parse_tables(SPAN), "next", 2026)
    joint = long[long.row == 0].set_index("party_label")["value"]
    assert joint.to_dict() == {"PP": 31.0, "FA+FV": 7.3, "ERC": 2.7}      # ERC is not read as FV
    apart = long[long.row == 1].set_index("party_label")["value"]
    assert apart.to_dict() == {"PP": 31.9, "FA": 6.0, "FV": 1.5, "ERC": 2.7}


def test_sumar_series_is_frente_amplio_plus_front_valencia():
    rule = load_config()["model"]["composites"]
    polls = pd.DataFrame({"poll_id": ["a", "b", "b", "c"], "party": ["FAFV", "FA", "FV", "SUMAR"],
                          "value": [7.3, 6.0, 1.5, 6.5], "pollster": "X",
                          "fieldwork_end": pd.Timestamp("2026-11-05")})
    out = apply_composites(polls, rule).set_index(["poll_id", "party"])["value"]
    assert out["a", "SUMAR"] == 7.3 and out["b", "SUMAR"] == 7.5 and out["c", "SUMAR"] == 6.5


# the pre-election table of study 3584 as pypdf lays it out: seat ranges, a label wrapped over two lines
PREELECTORAL = """
                    Voto directo en        Margen teórico     Estimación
                      la encuesta            de error*        de voto CIS     Estimación de
       PSOE                  28,7               ±0,4              33,3          134 – 143
       PP                    17,2               ±0,3              25,5           98 – 106
       Frente Amplio          3,3               ±0,2               4,7            7 – 11
       ERC-Podemos**          2,4               ±0,1               3,1           10 – 14
       Compromís: Front       1,2               ±0,1               1,6            4 – 6
       Valencià
       Adelante Andalucía     1,1               ±0,1               1,5            3 – 4
       Podemos                0,8               ±0,1               1,1            0 – 1
       UPC                    0,3               ±0,1               0,4            0 – 2
       Ara Més-Front Ampli    0,2               ±0,04              0,2            0 – 1
       SALF                   1,3               ±0,1               1,4              -
       CC-Municipalistas      0,2               ±0,04              0,2              -
       Primero Canarias
       En blanco              1,5               ±0,1               0,5              -
       Voto nulo              0,8               ±0,1
"""


def test_cis_preelectoral_table_maps_to_the_registered_ballots():
    rows = cis.parse_estimate(PREELECTORAL)
    assert dict(rows)["Compromís: Front"] == 1.6 and dict(rows)["ERC-Podemos"] == 3.1
    est = cis.map_parties(rows, RULES, pd.Timestamp("2026-10-30"))
    assert est["FA"] == pytest.approx(4.7 + 0.4 + 0.2)      # with its lists in Canarias and Baleares
    assert est["FV"] == 1.6 and est["ERC"] == 3.1 and est["AA"] == 1.5 and est["SALF"] == 1.4
    assert est["PODEMOS"] == 1.1 and "UP" not in est        # Podemos alone, not the 2016-23 coalition
    assert est["CC"] == 0.2


def _waves(rows):
    return pd.DataFrame([{"poll_id": i, "cycle": "next", "pollster": h, "is_election": False,
                          "fieldwork_start": pd.Timestamp(a), "fieldwork_end": pd.Timestamp(b),
                          "sample_size": n, "party": "PP", "value": 30.0}
                         for i, (h, a, b, n) in enumerate(rows)])


def test_overlapping_waves_of_one_pollster_are_counted_once():
    df = _waves([("Tracker", "2026-10-26", "2026-11-10", 6500),   # cumulative: superseded
                 ("Tracker", "2026-10-26", "2026-11-12", 7500),   # latest release: kept
                 ("Tracker", "2026-10-10", "2026-10-20", 1000),   # ended before the kept window: kept
                 ("Tracker", "2026-10-15", "2026-10-27", 1000),   # overlaps the kept window: dropped
                 ("Other", "2026-11-01", "2026-11-12", 1000)])    # another pollster: untouched
    assert sorted(drop_overlapping_waves(df)["poll_id"]) == [1, 2, 4]


def test_prepare_uses_non_overlapping_waves_known_at_the_cutoff():
    df = _waves([("Tracker", "2026-10-26", "2026-11-10", 6500),
                 ("Tracker", "2026-10-26", "2026-11-12", 7500)])
    kw = dict(cycle="next", parties=["PP"], anchor={"PP": 0.33}, start_date="2023-07-23",
              end_date="2026-11-14")
    assert list(prepare(df, **kw).polls["poll_id"]) == [1]
    # a backtest cut-off before the second release still sees the first one
    assert list(prepare(df, obs_cutoff="2026-11-11", **kw).polls["poll_id"]) == [0]


def test_a_party_can_have_several_breaks():
    df = _waves([("X", "2026-11-01", "2026-11-05", 1000)])
    d = prepare(df, "next", ["PP", "SUMAR"], {"PP": 0.33, "SUMAR": 0.12}, "2023-07-23", "2026-11-14",
                breaks={"SUMAR": ["2023-12-08", "2026-10-11"], "PP": "2026-10-11", "ERC": "2026-10-11"})
    assert d.breaks == [(1, 19), (1, 168), (0, 168)]              # (party index, week); ERC not tracked


def test_party_absent_from_some_provinces_keeps_its_national_share_elsewhere():
    from electoral.seats import simulate_seats

    shares0 = pd.DataFrame({"A": [0.6, 0.6], "S": [0.1, 0.1]}, index=["08", "28"])
    blank0 = pd.Series(0.0, index=shares0.index)
    seats0 = pd.Series(10, index=shares0.index)
    weights = pd.Series([0.5, 0.5], index=shares0.index)
    draws = pd.DataFrame({"A": [0.6], "S": [0.1], "P": [0.05]})
    kw = dict(n_sims=1, noise_sd=0.0, seed=1, proxies={"P": "S"}, noise=False, weights=weights)
    national0 = pd.Series({"A": 0.6, "S": 0.1})
    everywhere, _ = simulate_seats(draws, shares0, blank0, seats0, national0, **kw)
    assert everywhere.loc[0, "P"] == 0            # 5 % in both provinces: under the last quotient
    only_madrid, _ = simulate_seats(draws, shares0, blank0, seats0, national0, absent={"P": ["08"]}, **kw)
    assert only_madrid.loc[0, "P"] == 1           # the same 5 % nationally is 10 % where it runs


def test_podemos_has_no_ballot_where_it_joined_other_lists():
    absent = load_config()["seats"]["absent"]["PODEMOS"]
    assert set(absent) == {"08", "17", "25", "43", "03", "12", "46", "35", "38", "07"}
    assert "28" not in absent


def test_regional_part_moves_a_fixed_fraction_of_the_share_into_the_region():
    from electoral.seats import simulate_seats

    # S has 10 % everywhere in the baseline; 40 % of its vote is now said to be in Valencia ("46"),
    # which holds 20 % of the national vote
    shares0 = pd.DataFrame({"A": [0.55, 0.55], "S": [0.1, 0.1]}, index=["28", "46"])
    blank0 = pd.Series(0.0, index=shares0.index)
    seats0 = pd.Series(10, index=shares0.index)
    weights = pd.Series([0.8, 0.2], index=shares0.index)
    draws = pd.DataFrame({"A": [0.55], "S": [0.1]})
    kw = dict(n_sims=1, noise_sd=0.0, seed=1, noise=False, weights=weights)
    national0 = pd.Series({"A": 0.55, "S": 0.1})
    base, _ = simulate_seats(draws, shares0, blank0, seats0, national0, **kw)
    assert base.loc[0, "S"] == 2                  # one seat in each province
    part = {"S": {"provinces": ["46"], "fraction": 0.4, "sd_log": 0.0}}
    moved, _ = simulate_seats(draws, shares0, blank0, seats0, national0, regional_part=part, **kw)
    # Valencia: 0.1 x 0.4 / 0.2 = 0.20 against A's 0.55 -> 2 of 10 seats;
    # Madrid: 0.1 x 0.6 / 0.8 = 0.075 against 0.55 -> 1 seat
    assert moved.loc[0, "S"] == 3


def test_regional_part_fraction_comes_from_polls_listing_both_lists():
    from electoral.project_seats import regional_parts

    cfg = {"cutoff_date": "2026-11-14",
           "seats": {"regional_part": {"SUMAR": {"part": "FV", "rest": "FA", "provinces": ["3", "12", "46"],
                                                 "days": 30, "min_pollsters": 2}}}}
    rows = []
    for i, (h, fa, fv) in enumerate([("X", 6.0, 2.0), ("X", 6.0, 2.0), ("Y", 9.0, 1.0), ("Z", 7.0, None)]):
        for party, v in (("FA", fa), ("FV", fv)):
            if v is not None:
                rows.append({"poll_id": i, "cycle": "next", "pollster": h, "is_election": False,
                             "fieldwork_start": pd.Timestamp("2026-11-01") + pd.Timedelta(days=4 * i),
                             "fieldwork_end": pd.Timestamp("2026-11-02") + pd.Timedelta(days=4 * i),
                             "sample_size": 1000.0, "party": party, "value": v})
    out = regional_parts(cfg, pd.DataFrame(rows))["SUMAR"]
    assert out["provinces"] == ["03", "12", "46"] and out["n_pollsters"] == 2   # Z gives no split
    assert out["fraction"] == pytest.approx((0.25 + 0.10) / 2)


def test_series_of_one_family_share_one_vote_in_the_house_effect_centring():
    from electoral.model import centring_weights

    pollsters = ["40dB", "CIS", "CIS (microdata, re-weighted)", "CIS re-est. (Opina 360)", "GAD3"]
    publishes = np.array([[1, 1, 1, 1, 1],        # PP: everyone
                          [1, 1, 0, 0, 1],        # a small party: only the official CIS of its family
                          [0, 0, 0, 0, 1]], dtype=float)
    w = centring_weights(pollsters, publishes, {"CIS": "^CIS"})
    assert w[0].tolist() == pytest.approx([1, 1 / 3, 1 / 3, 1 / 3, 1]) and w[0].sum() == pytest.approx(3)
    assert w[1].tolist() == [1, 1, 0, 0, 1]
    assert w[2].tolist() == [0, 0, 0, 0, 1]
    assert (centring_weights(pollsters, publishes, None) == publishes).all()   # no families: as before


def test_prepare_applies_the_configured_families():
    rows = []
    for i, h in enumerate(["CIS", "CIS re-est. (X)", "GAD3"]):
        rows.append({"poll_id": i, "cycle": "next", "pollster": h, "is_election": False,
                     "fieldwork_start": pd.Timestamp("2026-11-01"), "fieldwork_end": pd.Timestamp("2026-11-05"),
                     "sample_size": 1000.0, "party": "PP", "value": 30.0})
    d = prepare(pd.DataFrame(rows), "next", ["PP"], {"PP": 0.33}, "2023-07-23", "2026-11-14",
                families=load_config()["model"]["house_families"])
    assert dict(zip(d.pollsters, d.centre_w[0])) == {"CIS": 0.5, "CIS re-est. (X)": 0.5, "GAD3": 1.0}

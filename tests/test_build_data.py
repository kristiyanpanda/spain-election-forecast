import pandas as pd
import pytest

from electoral.build_data import assign_pollsters, pollster_id
from electoral.wiki_polls import parse_tables, tables_to_long

# Official CIS row and two re-estimations sharing the fieldwork/sample rowspan; the
# re-estimator comes first, as on Wikipedia.
CIS_SAMPLE = """
====Voting intention estimates====
=====2026=====
{| class="wikitable"
|-
! Polling firm/Commissioner !! Fieldwork date !! Sample size !! Turnout !! PP !! PSOE !! Lead
|-
| CIS {{smaller|(Target Point)}}{{efn|name="AltCIS"|Alt.}}<ref>{{cite web |url=https://a.b}}</ref>
| rowspan="3"| 1–4 Sep
| rowspan="3"| 4,042
|?
| 31.9
| 26.8
| 5.1
|-
| CIS {{smaller|(JM)}}{{efn|name="AltCIS"}}
|?
| 30.0
| 27.0
| 3.0
|-
| CIS<ref name="CISSep26">{{cite web |title=Barómetro |url=https://www.cis.es}}</ref>
|?
| 25.5
| 31.0
| 5.5
|-
| [[Sigma Dos]]/El Mundo
| 7–11 Sep
| 1,200
|?
| 33.7
| 26.8
| 6.9
|}
"""


def test_pollster_id():
    assert pollster_id("CIS (Target Point)") == "CIS re-est. (Target Point)"
    assert pollster_id("CIS  (Ateneo del Dato)") == "CIS re-est. (Ateneo del Dato)"
    assert pollster_id("CIS (JM&A)") == "CIS re-est. (Jaime Miquel)"
    assert pollster_id("CIS") == "CIS"
    assert pollster_id("ElectoPanel/Electomanía") == "EM-Analytics"
    assert pollster_id("Sigma Dos/El Mundo") == "Sigma Dos"


def test_cis_reestimators_split_and_official_cis_dropped():
    long = tables_to_long(parse_tables(CIS_SAMPLE), "next", 2026)
    assert set(long.firm_raw) == {"CIS (Target Point)", "CIS (JM)", "CIS", "Sigma Dos/El Mundo"}
    df, n_cis = assign_pollsters(long)
    assert n_cis == 1
    assert set(df.pollster) == {
        "CIS re-est. (Target Point)", "CIS re-est. (Jaime Miquel)", "Sigma Dos"}
    # the rowspan carries the official CIS fieldwork and sample to the re-estimators
    tp = df[(df.pollster == "CIS re-est. (Target Point)") & (df.party_label == "PP")].iloc[0]
    assert tp.value == 31.9 and tp.sample_size == 4042
    jm = df[(df.pollster == "CIS re-est. (Jaime Miquel)") & (df.party_label == "PSOE")].iloc[0]
    assert jm.value == 27.0 and jm.sample_size == 4042
    # distinct pollsters survive the poll-key de-duplication used in build_polls
    key = ["cycle", "pollster", "commissioner", "fieldwork_start", "fieldwork_end",
           "sample_size", "party_label"]
    assert len(df.drop_duplicates(key)) == len(df)


def test_cycle_of_assigns_the_next_election():
    from electoral.build_data import cycle_of

    assert cycle_of(pd.Timestamp("2016-06-26")) == "e2016"
    assert cycle_of(pd.Timestamp("2019-09-18")) == "e2019nov"
    assert cycle_of(pd.Timestamp("2026-09-04")) == "next"


def test_shared_cis_sample_is_split_across_series():
    from electoral.build_data import assign_sample_groups
    from electoral.model import _impute_n

    studies = pd.DataFrame({"study": ["3577"], "fieldwork_end": [pd.Timestamp("2026-09-04")]})
    df = pd.DataFrame({
        "pollster": ["CIS", "CIS (microdata, re-weighted)", "CIS re-est. (Target Point)",
                     "CIS re-est. (Opina 360)", "Sigma Dos"],
        "fieldwork_end": pd.to_datetime(["2026-09-04", "2026-09-04", "2026-09-04", "2026-10-06",
                                         "2026-09-04"]),
        "sample_size": [4042.0, 4042.0, 4042.0, 5025.0, 1200.0],
        "sample_group": ["CIS-3577", "CIS-3577", "", "", ""],
    })
    out = assign_sample_groups(df, studies)
    assert list(out.sample_group) == ["CIS-3577", "CIS-3577", "CIS-3577", "CIS-2026-10-06", ""]
    assert list(out.n_series) == [3, 3, 3, 1, 1]
    n = _impute_n(out)
    assert n.iloc[:3].sum() == pytest.approx(4042) and n.iloc[4] == 1200

import numpy as np
import pandas as pd

from electoral.model import apply_composites, prepare


def _polls():
    rows = []
    for i, (date, vals) in enumerate([
        ("2016-02-01", {"PP": 28, "PSOE": 21, "PODEMOS": 14, "IU": 4}),
        ("2016-05-20", {"PP": 29, "PSOE": 20, "UP": 22}),
        ("2016-06-10", {"PP": 30, "PSOE": 20, "PODEMOS": 15}),   # IU missing -> no UP obs
    ]):
        for p, v in vals.items():
            rows.append({"poll_id": f"e2016-{i}", "cycle": "e2016", "pollster": "X", "commissioner": "",
                         "fieldwork_start": pd.Timestamp(date), "fieldwork_end": pd.Timestamp(date),
                         "sample_size": 1000.0, "turnout": np.nan, "is_election": False,
                         "party": p, "value": float(v)})
    return pd.DataFrame(rows)


def test_composites_sum_and_fallback():
    df = apply_composites(_polls(), {"UP": {"sum": ["UP"], "fallback": ["PODEMOS", "IU"]}})
    up = df[df.party == "UP"].set_index("poll_id")["value"]
    assert up["e2016-0"] == 18 and up["e2016-1"] == 22 and np.isnan(up["e2016-2"])
    df2 = apply_composites(_polls(), {"UP": {"sum": ["UP"], "fallback": ["PODEMOS", "IU"], "fallback_min": 1}})
    assert df2[df2.party == "UP"].set_index("poll_id")["value"]["e2016-2"] == 15


def test_prepare_grid_and_entrants():
    d = prepare(_polls(), "e2016", ["PP", "PSOE", "UP"], {"PP": 0.287, "PSOE": 0.22},
                "2015-12-20", "2016-06-26", obs_cutoff="2016-05-27",
                composites={"UP": {"sum": ["UP"], "fallback": ["PODEMOS", "IU"]}})
    assert len(d.weeks) == 28 and d.weeks[0] == pd.Timestamp("2015-12-20")
    assert len(d.polls) == 2                      # the June poll is after the observation cut-off
    assert set(d.parties) == {"PP", "PSOE", "UP"}
    assert np.isnan(d.anchor[2]) and d.entry_week[2] == 6   # UP is an entrant, first polled week 6
    assert d.entry_week[0] == 0
    assert (d.n == 1000).all() and d.y.max() < 1

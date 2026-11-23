import numpy as np
import pandas as pd
import pytest

from electoral.regional import ceo_estimate, regional_shares, regional_targets
from electoral.seats import apply_regional


def _results():
    res = pd.DataFrame({"election": "202307", "prov": ["08", "08", "17", "17", "28"],
                        "party": ["ERC", "PSOE", "ERC", "PSOE", "PSOE"],
                        "votos": [100, 300, 60, 40, 500]})
    tot = pd.DataFrame({"election": "202307", "prov": ["08", "17", "28"], "votos_validos": [410, 100, 500],
                        "votos_blancos": [10, 0, 0], "votos_nulos": [5, 0, 0]})
    return res, tot


def test_regional_targets_and_shares():
    res, tot = _results()
    sh = regional_shares(res, tot, ["08", "17"])
    assert sh["ERC"] == pytest.approx(100 * 160 / 510)
    tg = regional_targets(res, tot, ["08", "17"])
    assert tg.sum() == pytest.approx(1.0) and tg["BLANK"] == pytest.approx(10 / 515)


def test_ceo_estimate_reweights_recall_and_moves_alianca_voters():
    rows = ([("ERC", "ERC")] * 4 + [("PSC/PSOE", "PSC/PSOE")] * 4 + [("Aliança Catalana", "PSC/PSOE")] * 2
            + [("No ho sap", "ERC")])
    d = pd.DataFrame({"PONDERA": "1", "INT_CONGRES_VOT": [v for v, _ in rows],
                      "REC_CONGRES_VOT": [r for _, r in rows], "INT_CONGRES_VOT_PROB_0_10": ""})
    targets = pd.Series({"ERC": 0.5, "PSOE": 0.5})
    est = ceo_estimate(d, targets, {"JUNTS": 0.5})
    # recall: 5 ERC vs 6 PSC rows -> weights 5.5/5 and 5.5/6; AC (PSC recallers) half to Junts, half abstain
    w_erc, w_psc = 5.5 / 5, 5.5 / 6
    total = 4 * w_erc + 4 * w_psc + 2 * w_psc * 0.5
    assert est["ERC"] == pytest.approx(100 * 4 * w_erc / total)
    assert est["JUNTS"] == pytest.approx(100 * w_psc / total)


def test_apply_regional_pulls_toward_the_survey_and_keeps_totals():
    rng = np.random.default_rng(0)
    S = 2000
    provs, col = ["08", "17", "28"], {"ERC": 0, "PSOE": 1, "PP": 2}
    share = np.zeros((S, 3, 3))
    share[:, :2, 0] = 0.10 + 0.005 * rng.standard_normal((S, 1))      # ERC ~10 % in Catalonia
    share[:, :, 1] = 0.30
    share[:, :, 2] = 1.0 - share[:, :, 0] - share[:, :, 1]
    weights = pd.Series([0.4, 0.1, 0.5], index=provs)
    obs = [{"provinces": ["08", "17"], "party": "ERC", "share": 16.0, "sd": 2.0}]
    apply_regional(share, obs, provs, col, weights, np.ones(3), swing_sd=2.0)
    erc = share[:, :2, 0].mean()
    # precision-weighted: prior sd sqrt(0.5^2 + 2^2) ~ 2.06, survey sd 2 -> about halfway to 16
    assert 0.125 < erc < 0.135
    assert np.allclose(share.sum(axis=2), 1.0)
    assert np.allclose(share[:, 2, 0], 0.0) and np.allclose(share[:, 2, 1], 0.30)    # Madrid untouched

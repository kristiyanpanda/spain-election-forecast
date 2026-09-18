import numpy as np
import pandas as pd
import pytest

from electoral.indices import enp, pedersen, volatility_split


def test_enp_known_values():
    assert enp([0.5, 0.5]) == pytest.approx(2.0)
    assert enp([0.25] * 4) == pytest.approx(4.0)
    assert enp([0.6, 0.3, 0.1]) == pytest.approx(1 / (0.36 + 0.09 + 0.01))
    assert enp([0.45, 0.45]) == pytest.approx(2.0)     # renormalised when shares sum < 1


def test_pedersen_and_split():
    prev = pd.Series({"PP": 0.45, "PSOE": 0.30, "IU": 0.10, "CIU": 0.05, "OTHER": 0.10})
    cur = pd.Series({"PP": 0.35, "PSOE": 0.30, "IU": 0.05, "CIU": 0.05, "CS": 0.15, "OTHER": 0.10})
    assert pedersen(prev, cur) == pytest.approx(0.5 * (0.10 + 0.05 + 0.15))
    bloc = {"PP": "right", "CS": "right", "PSOE": "left", "IU": "left", "CIU": "periph_right", "OTHER": "other"}
    v = volatility_split(prev, cur, bloc)
    # right bloc 0.45 -> 0.50, left 0.40 -> 0.35 : between = 0.5*(0.05+0.05) = 0.05
    assert v["between"] == pytest.approx(0.05)
    assert v["within"] == pytest.approx(v["total"] - 0.05)
    assert v["total"] >= v["between"] >= 0

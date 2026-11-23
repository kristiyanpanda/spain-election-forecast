import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from electoral import ROOT
from electoral import cis
from electoral import cis_microdata as md

RULES = cis.load_rules(ROOT / "data/party_map_cis.yaml")

# 2016-2018 layout: direct vote and estimate, single-spaced
OLD = """
Barómetro CIS enero 2016
                     Estimación de voto CIS
PP   18,2 28,8
PSOE  14,5 20,5
Podemos  10,2 13,2
IU (Unidad Popular)  3,1 3,7
En Comú Podem  4,2 4,5
CC   -- 0,0
En blanco  2,3 2,5
Voto nulo  0,3
No sabe  14,4
"""

# 2023- layout: PP above PSOE, margin of error and seat ranges, a starred value, then other tables
NEW = """
                       Voto directo     Margen teórico     Estimación de
                        (en % censo)      de error*         voto CIS
      PP                     25,4          ±1,0                31,4          122 – 140
      PSOE                   24,6          ±1,0                31,2          115 – 135
      SUMAR**                12,7          ±0,8                16,4            43 – 50
      PRC                     0,0          ±0,1                 0,1***
      EAJ-PNV                 0,6          ±0,2                   1
      En blanco               1,2          ±0,2                 1,1             -
      Voto nulo               0,8          ±0,2
      No sabe                14,1          ±0,8
                                   PSOE                                        91,2%
"""

# 2021 layout: a label wrapped over three lines, the estimate printed on the first one
WRAPPED = """
             PSOE                                          19,7                                27,6
             VOX                                            8,5                                14,3
             Unidas Podemos
             (En Comú Podem,                                                                   13,6
              En Común-Unidas Podemos)             10,6
             Ciudadanos                                     3,0                                  5,7
             Voto nulo                                      1,1
"""

MUNICIPAL_FIRST = """
ESTIMACIÓN DE VOTO ELECCIONES MUNICIPALES
PSOE  20,0 25,0
PP  20,0 25,0
Voto nulo  1,0
ESTIMACIÓN DE VOTO ELECCIONES GENERALES
PSOE  22,0 32,8
PP  20,0 26,8
Voto nulo  1,0
"""


def test_parse_estimate_old_layout():
    rows = cis.parse_estimate(OLD)
    assert rows[:2] == [("PP", 28.8), ("PSOE", 20.5)]
    assert ("CC", 0.0) in rows and ("En blanco", 2.5) in rows
    assert all(label != "Voto nulo" for label, _ in rows)


def test_parse_estimate_new_layout_skips_margins_and_seats():
    rows = dict(cis.parse_estimate(NEW))
    assert rows == {"PP": 31.4, "PSOE": 31.2, "SUMAR": 16.4, "PRC": 0.1, "EAJ-PNV": 1.0,
                    "En blanco": 1.1}


def test_parse_estimate_wrapped_label_reads_the_estimate_column():
    rows = cis.parse_estimate(WRAPPED)
    assert ("Unidas Podemos (En Comú Podem,", 13.6) in rows
    assert [v for _, v in rows] == [27.6, 14.3, 13.6, 5.7]


def test_parse_estimate_prefers_the_general_election_table():
    assert dict(cis.parse_estimate(MUNICIPAL_FIRST)) == {"PSOE": 32.8, "PP": 26.8}


def test_map_parties_podemos_lineage_by_date():
    pre_pact = cis.map_parties(cis.parse_estimate(OLD), RULES, pd.Timestamp("2016-01-11"))
    assert pre_pact["PODEMOS"] == pytest.approx(13.2 + 4.5) and pre_pact["IU"] == 3.7
    up_era = cis.map_parties([("PSOE", 34.2), ("Podemos", 11.2), ("En Comú Podem", 1.0), ("IU", 3.3),
                              ("Compromís", 0.6)], RULES, pd.Timestamp("2019-09-18"))
    assert up_era == {"PSOE": 34.2, "UP": 15.5, "COMPROMIS": 0.6}
    sumar_era = cis.map_parties([("SUMAR (IU, Compromís, En", 10.6), ("U. Podemos", 6.7)], RULES,
                                pd.Timestamp("2023-04-05"))
    assert sumar_era == {"SUMAR": 10.6, "PODEMOS": 6.7}
    after_nov19 = cis.map_parties([("Más País", 1.3), ("Compromís", 0.7)], RULES, pd.Timestamp("2022-12-14"))
    assert after_nov19 == {"MASPAIS": 2.0}


def test_map_parties_rejects_unknown_labels():
    with pytest.raises(ValueError, match="Unmapped CIS label"):
        cis.map_parties([("Partido Nuevo", 1.0)], RULES, pd.Timestamp("2026-01-01"))


def test_fieldwork_and_sample_from_ficha_tecnica():
    ft = "Fecha de realización:\n Del 28 de febrero al 7 de marzo de 2025 .\nRealizada: 4.018 entrevistas."
    assert cis.parse_fieldwork_es(ft) == (pd.Timestamp("2025-02-28"), pd.Timestamp("2025-03-07"))
    assert cis.parse_sample(ft) == 4018
    assert cis.parse_fieldwork_es("Fecha de realización: Del 1 al 4 de septiembre de 2026.") == (
        pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-04"))
    assert cis.parse_fieldwork_es("Fecha de realización: del 30 marzo al 7 de abril de 2020.")[0] == \
        pd.Timestamp("2020-03-30")
    assert cis.parse_fieldwork_es("Fecha de realización: 26 de abril de 2024.")[1] == pd.Timestamp("2024-04-26")


# ----------------------------------------------------------------------------- microdata
def _zip(header: list[str], rows: list[list[str]], nested: bool = False) -> io.BytesIO:
    body = "\ufeff" + "\n".join(";".join(f'"{c}"' for c in r) for r in [header, *rows])
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("9999_etiq.csv", body.encode("utf-8"))
    if not nested:
        inner.seek(0)
        return inner
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as z:
        z.writestr("9999_csv.zip", inner.getvalue())
    outer.seek(0)
    return outer


def _sample() -> tuple[list[str], list[list[str]]]:
    header = ["PESO: Ponderación", "PROBVOTO: Probabilidad de voto", "INTENCIONGR: Intención",
              "RECUERDO: Participación + Recuerdo de voto en las elecciones generales de 2023",
              "IA_E1_DIA: Día", "IA_E1_MES: Mes", "IA_E1_ANYO: Año"]
    rows = (
        # over-represented PSOE recallers who still vote PSOE
        [["1", "10 Con toda seguridad, iría a votar", "PSOE", "PSOE", "1", "Septiembre", "2026"]] * 6
        # under-represented PP recallers
        + [["1", "10 Con toda seguridad, iría a votar", "PP", "PP", "4", "Septiembre", "2026"]] * 3
        # unlikely voter and an undecided: both left out of the estimate
        + [["1", "3", "VOX", "PP", "2", "Septiembre", "2026"],
           ["1", "10 Con toda seguridad, iría a votar", "No sabe todavía", "No votó", "2", "Septiembre", "2026"]]
    )
    return header, rows


def test_load_labelled_both_header_styles_and_nested_zip(tmp_path: Path):
    header, rows = _sample()
    for i, (hdr, nested) in enumerate([(header, False), ([h.replace(":", "") for h in header], True)]):
        path = tmp_path / f"MD{i}.zip"
        path.write_bytes(_zip(hdr, rows, nested).getvalue())
        df = md.load_labelled(path)
        assert {"PESO", "PROBVOTO", "INTENCIONGR", "RECUERDO"} <= set(df.columns)
        assert md.recall_variable(df) == "RECUERDO" and md.required_missing(df) == []
        assert md.fieldwork(df) == (pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-04"))


def test_reestimate_reweights_recall_and_keeps_likely_voters(tmp_path: Path):
    header, rows = _sample()
    path = tmp_path / "MD.zip"
    path.write_bytes(_zip(header, rows).getvalue())
    df = md.load_labelled(path)
    targets = pd.Series({"PP": 0.5, "PSOE": 0.5})
    raw = md.raw_shares(df)
    est = md.reestimate(df, targets, likely_voter_min=9)
    assert raw["PP"] == pytest.approx(30.0)         # 6 PSOE, 3 PP, 1 VOX unweighted
    # recall groups re-weighted to 50/50: PSOE rows 5/6 each, PP rows 5/4 each; the VOX
    # respondent (PP recall) is an unlikely voter, so PP = 3 x 1.25 / (3 x 1.25 + 5)
    assert est["PP"] == pytest.approx(100 * 3.75 / 8.75)
    assert "VOX" not in est and est.sum() == pytest.approx(100.0)


def test_study_3577_reproduces_the_dossier():
    """Dossier §2.1: PP 30.7 / PSOE 25.8 (needs data/raw/cis/MD3577.zip, see `make data`)."""
    zpath = ROOT / "data/raw/cis/3577/MD3577.zip"
    nat, tot = ROOT / "data/processed/results_national.parquet", ROOT / "data/processed/province_totals.parquet"
    if not zpath.exists():
        pytest.skip("CIS microdata not downloaded")
    targets = md.recall_targets(pd.read_parquet(nat), pd.read_parquet(tot))
    est = md.reestimate(md.load_labelled(zpath), targets)
    assert est["PP"] == pytest.approx(30.7, abs=0.2)
    assert est["PSOE"] == pytest.approx(25.8, abs=0.2)
    assert est["VOX"] == pytest.approx(18.3, abs=0.2)

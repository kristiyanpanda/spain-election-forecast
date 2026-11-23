"""Two-language layer (figures, report page) and the coalition-builder data."""

from __future__ import annotations

import base64
import re

import numpy as np
import pandas as pd
import pytest

from electoral import i18n, load_config


@pytest.fixture(autouse=True)
def _english_afterwards():
    yield
    i18n.set_lang("en")


def test_tr_returns_the_key_in_english_and_the_translation_in_spanish():
    assert i18n.tr("seats") == "seats"
    i18n.set_lang("es")
    assert i18n.tr("seats") == "escaños"
    assert i18n.tr("a string nobody translated") == "a string nobody translated"


def test_translations_keep_the_fields_of_the_english_string():
    fields = lambda s: sorted(re.findall(r"\{(\w+)\}", s))  # noqa: E731
    for en, es in i18n.ES.items():
        assert fields(en) == fields(es), en


def test_numbers_and_dates_follow_the_language():
    assert i18n.num(30.46) == "30.5" and i18n.date("2026-11-14") == "14 November 2026"
    i18n.set_lang("es")
    assert i18n.num(30.46) == "30,5" and i18n.thousands(10000) == "10.000"
    assert i18n.date("2026-11-14") == "14 de noviembre de 2026"
    assert i18n.date("2026-11-14", year=False, short=True) == "14 nov"


def test_events_are_numbered_by_date_with_a_one_word_name_in_both_languages():
    cfg = load_config()
    en = i18n.events(cfg)
    i18n.set_lang("es")
    es = i18n.events(cfg)
    assert [e["n"] for e in en] == list(range(1, len(en) + 1))
    assert [e["date"] for e in en] == sorted(e["date"] for e in en) == [e["date"] for e in es]
    assert all(" " not in e["short"] for e in en + es)
    assert any(a["label"] != b["label"] for a, b in zip(en, es))


def test_events_accept_a_plain_string():
    ev = i18n.events({"events": {"2026-10-05": "Dissolution of the Cortes"}})
    assert ev[0]["label"] == "Dissolution of the Cortes" and ev[0]["short"] == "Dissolution"


def test_set_lang_rejects_unknown_languages():
    with pytest.raises(ValueError):
        i18n.set_lang("fr")


def test_report_text_has_the_same_entries_in_both_languages():
    from electoral.report import TEXT

    assert set(TEXT["en"]) == set(TEXT["es"])
    assert set(TEXT["en"]["prob_events"]) == set(TEXT["es"]["prob_events"])


def test_pactometro_scenario_data_round_trips_the_draws():
    from electoral.pactometro import scenario_data

    rng = np.random.default_rng(0)
    pp = rng.integers(120, 140, 200)
    draws = pd.DataFrame({"VOX": 60, "PP": pp, "PSOE": 350 - 60 - pp, "SALF": 0})
    d = scenario_data(draws)
    ids = [p["id"] for p in d["parties"]]
    assert ids == ["PSOE", "PP", "VOX"]                     # seating order, parties without seats left out
    assert sum(p["seats"] for p in d["parties"]) == 350
    back = np.frombuffer(base64.b64decode(d["draws"]), dtype=np.uint8).reshape(len(draws), len(ids))
    assert (back == draws[ids].to_numpy()).all()


def test_pactometro_fragment_is_the_widget_without_the_page_around_it():
    from electoral.pactometro import FOLDER
    from electoral import ROOT

    template = (ROOT / FOLDER / "template.html").read_text(encoding="utf-8")
    start, end = template.index("<!--PM:START"), template.index("<!--PM:END-->")
    piece = template[template.index("-->", start) + 3:end]
    assert "<body" not in piece and "<html" not in piece and "__DATA__" in piece
    assert piece.count("<script>") == piece.count("</script>") == 1
    # every text key used in the markup exists in both languages of the widget
    import re

    for key in set(re.findall(r'data-t="(\w+)"', piece)):
        assert piece.count(f"\n    {key}: ") + piece.count(f" {key}: ") >= 2, key

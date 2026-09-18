import math

import pandas as pd

from electoral.wiki_polls import _clean_cell, parse_fieldwork, parse_tables, tables_to_long, to_number

SAMPLE = """
====Voting intention estimates====
=====2026=====
{| class="wikitable"
|-
! rowspan="2"| Polling firm/Commissioner
! rowspan="2"| Fieldwork date
! rowspan="2"| Sample size
! rowspan="2"| Turnout
! [[File:Logo.svg|27px|link=People's Party (Spain)|PP]]
! [[File:Logo2.svg|25px|link=Spanish Socialist Workers' Party|PSOE]]
! [[Se Acabó La Fiesta|SALF]]
! rowspan="2"| Lead
|-
! style="background:red;"|
! style="background:blue;"|
! style="background:green;"|
|-
| rowspan="2"| [[Sigma Dos]]/El Mundo<ref>{{cite web |title=x |url=https://a.b/c}}</ref>
| 7–11 Sep
| 1,200
|?
| {{Party shading/PP}}| '''33.7'''<br/>{{font|size=75%|text=135/136}}
| 26.8<br/>{{font|size=75%|text=106}}
| –
| style="background:red; color:white;"| 6.9
|-
| 28 Aug–3 Sep
| ?
| 66
| 31.0
| 27.0
| <1.0
| 4.0
|-
| [[2023 Spanish general election|2023 general election]]
| 23 Jul 2023
| N/A
| 66.6
| 33.1
| 31.7
| –
| 1.4
|}
====Voting preferences====
{| class="wikitable"
|-
! Polling firm/Commissioner !! Fieldwork date !! Sample size !! PP !! PSOE
|-
| Ignored || 1–2 Jan || 500 || 10 || 20
|}
"""


def test_clean_cell_strips_markup():
    assert _clean_cell("{{Party shading/PP}}| '''33.7'''<br/>{{font|text=135}}") == "33.7"
    assert _clean_cell("[[2023 Spanish general election|2023 general election]]") == "2023 general election"
    assert _clean_cell(" rowspan=\"2\"| [[Sigma Dos]]/El Mundo<ref>{{cite web |url=x}}</ref>") == "Sigma Dos/El Mundo"


def test_fieldwork_dates():
    assert parse_fieldwork("7–11 Sep", 2026) == (pd.Timestamp("2026-09-07"), pd.Timestamp("2026-09-11"))
    assert parse_fieldwork("28 Dec–3 Jan", 2025) == (pd.Timestamp("2024-12-28"), pd.Timestamp("2025-01-03"))
    assert parse_fieldwork("23 Jul 2023", None) == (pd.Timestamp("2023-07-23"), pd.Timestamp("2023-07-23"))
    assert parse_fieldwork("30 Aug–5 Sep 2024", None)[0] == pd.Timestamp("2024-08-30")


def test_to_number():
    assert to_number("1,200") == 1200
    assert to_number("33.5–34.0") == 33.75
    assert math.isnan(to_number("?")) and math.isnan(to_number("–")) and math.isnan(to_number("<1.0"))


def test_parse_tables_rowspan_and_scope():
    tables = parse_tables(SAMPLE)
    assert len(tables) == 1  # the 'Voting preferences' table is ignored
    tb = tables[0]
    assert tb.headers == ["Polling firm/Commissioner", "Fieldwork date", "Sample size", "Turnout",
                          "PP", "PSOE", "SALF", "Lead"]
    assert len(tb.rows) == 3
    assert tb.rows[1][0] == "Sigma Dos/El Mundo"  # rowspan carried to second row
    assert tb.rows[1][1] == "28 Aug–3 Sep"
    long = tables_to_long(tables, "next", 2026)
    row = long[(long.row == 0) & (long.party_label == "PP")].iloc[0]
    assert row.value == 33.7 and row.sample_size == 1200 and row.fieldwork_end == pd.Timestamp("2026-09-11")
    assert long[long.row == 2].is_election.all()
    assert long[(long.row == 1) & (long.party_label == "SALF")].value.isna().all()

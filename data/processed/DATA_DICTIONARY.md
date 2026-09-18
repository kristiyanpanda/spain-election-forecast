# Data dictionary

All processed files live in `data/processed/`. Codes and lineage choices are in `data/party_map_*.yaml` and `docs/party_mapping.md`.

## `results_province.parquet`

| column | meaning |
|---|---|
| `election` | election id YYYYMM (e.g. 202307) |
| `election_date` | polling day |
| `election_month` | first day of the election month (kept for ordering) |
| `ccaa` | autonomous community code (Ministry coding) |
| `prov` | INE province code 01-52 (51 Ceuta, 52 Melilla) |
| `cand_code` | Ministry candidatura code (provincial list) |
| `head_nac` | code of the national head list this provincial list belongs to |
| `siglas` | Ministry short name of the provincial list |
| `nombre` | Ministry full name of the provincial list |
| `party` | canonical party family (data/party_map_results.yaml); OTHER if unmapped |
| `bloc` | left / right / periph_left / periph_right / other |
| `votos` | valid votes for the list in the province |
| `escanos` | seats won by the list in the province |

## `results_national.parquet`

| column | meaning |
|---|---|
| `election` | election id |
| `election_date` | polling day |
| `party` | canonical party family |
| `bloc` | bloc |
| `votos` | national valid votes (sum of provinces) |
| `escanos` | national seats |
| `share_valid` | votos / national valid votes (blank included) |

## `province_totals.parquet`

| column | meaning |
|---|---|
| `election` | election id |
| `election_date` | polling day |
| `ccaa` | CCAA code |
| `prov` | province code |
| `ambito_nombre` | province name (Ministry spelling) |
| `censo_escrutinio` | electoral census used at the count |
| `votantes` | ballots cast = valid + null |
| `votos_validos` | valid votes = candidaturas + blank |
| `votos_blancos` | blank votes |
| `votos_nulos` | null votes |
| `votos_candidaturas` | votes for lists |
| `escanos` | seats at stake in the province |
| `turnout` | votantes / censo_escrutinio |

## `polls_long.parquet`

| column | meaning |
|---|---|
| `poll_id` | cycle + running number |
| `cycle` | election the poll precedes: e2016, e2019apr, e2019nov, e2023, next |
| `pollster` | polling firm (before the slash in Wikipedia); ELECTION for actual results rows |
| `commissioner` | media outlet / client (after the slash) |
| `fieldwork_start` | first fieldwork day |
| `fieldwork_end` | last fieldwork day (used as poll date) |
| `sample_size` | n respondents; NaN when Wikipedia shows '?' |
| `turnout` | turnout estimate in % when published |
| `is_election` | True for actual election result rows |
| `party` | canonical party id (data/party_map_polls.yaml) |
| `bloc` | bloc |
| `value` | vote estimate in % of valid vote; NaN when not published ('?') or party not polled ('–') |
| `section` | Wikipedia table section (year or scenario label) |
| `source_page` | Wikipedia page title |
| `cutoff_date` | data cut-off stamped on every row |

## Sources and licences

* **Official results**: Ministerio del Interior, infoelectoral.interior.gob.es, files `02YYYYMM_TOTA.zip`. Reuse under Ley 37/2007 and RD 1495/2011. *Origen de los datos: Ministerio del Interior.*
* **Polls**: English Wikipedia, "Opinion polling for the ... Spanish general election" pages (and the 2019-2022 sub-pages), licence CC BY-SA 4.0. CIS barometers enter through their rows in those tables; *Fuente de los datos: Centro de Investigaciones Sociológicas* for those rows.

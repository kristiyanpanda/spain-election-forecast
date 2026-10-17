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
| `pollster` | polling firm (before the slash in Wikipedia); `CIS` = official CIS estimate and `CIS (microdata, re-weighted)` = our re-estimate, both from cis.es; `CIS re-est. (X)` for X's re-estimation of raw CIS data; ELECTION for actual results rows |
| `commissioner` | media outlet / client (after the slash) |
| `fieldwork_start` | first fieldwork day |
| `fieldwork_end` | last fieldwork day (used as poll date) |
| `sample_size` | n respondents; NaN when Wikipedia shows '?' |
| `n_series` | number of series built from the same survey (CIS: official, our re-estimate, third-party re-estimates); the model divides n by it |
| `sample_group` | CIS-<study> for series sharing one CIS survey, empty otherwise |
| `turnout` | turnout estimate in % when published |
| `is_election` | True for actual election result rows |
| `party` | canonical party id (data/party_map_polls.yaml) |
| `bloc` | bloc |
| `value` | vote estimate in % of valid vote; NaN when not published ('?') or party not polled ('–') |
| `section` | Wikipedia table section (year or scenario label), or `cis.es study <n>` |
| `source_page` | Wikipedia page title, or the cis.es study page |
| `cutoff_date` | data cut-off stamped on every row |

## `cis_studies.csv`

| column | meaning |
|---|---|
| `study` | CIS study number |
| `title` | study title on cis.es |
| `fieldwork_start / fieldwork_end` | fieldwork window (microdata interview dates when available, else the ficha técnica) |
| `sample_size` | interviews completed |
| `fieldwork_source` | where the fieldwork window comes from |
| `official_<PARTY>` | official CIS estimate, % of valid vote (Alaminos-Tezanos model) |
| `micro_<PARTY>` | our re-estimate from the microdata, % of valid vote (PESO, 2023 recall, likely voters); current cycle only |
| `source_url` | cis.es study page |
| `cutoff_date` | data cut-off |

## Sources and licences

* **Official results**: Ministerio del Interior, infoelectoral.interior.gob.es, files `02YYYYMM_TOTA.zip`. Reuse under Ley 37/2007 and RD 1495/2011. *Origen de los datos: Ministerio del Interior.*
* **Polls**: English Wikipedia, "Opinion polling for the ... Spanish general election" pages (and the 2019-2022 sub-pages), licence CC BY-SA 4.0. Official CIS rows are dropped from these tables; third-party re-estimations of raw CIS data are kept as pollsters `CIS re-est. (X)`.
* **CIS**: Centro de Investigaciones Sociológicas, cis.es, licence CC BY 4.0: the 'Estimación de voto' PDF, ficha técnica and microdata of each study (barometers, pre-electoral and flash surveys; list in `config.yaml`). *Fuente de los datos: Centro de Investigaciones Sociológicas.*

# Data quality report

Generated 2026-10-17. Data cut-off: **2026-10-17**.

## Official results (Ministerio del Interior)

Every election must have 52 provinces and 350 seats; `share_mapped` is the share of valid list votes assigned to a named party family (the rest is OTHER).

|   election |   provinces |   seats |   valid_votes |   turnout |   seats_from_lists |   share_mapped |
|-----------:|------------:|--------:|--------------:|----------:|-------------------:|---------------:|
|     197706 |          52 |     350 |    18,324,333 |      78.7 |                350 |           92.7 |
|     197903 |          52 |     350 |    17,990,915 |      67.8 |                350 |           93.3 |
|     198210 |          52 |     350 |    21,050,038 |      79   |                350 |           96.3 |
|     198606 |          52 |     350 |    20,202,919 |      70.2 |                350 |           94.1 |
|     198910 |          52 |     350 |    20,493,682 |      69.6 |                350 |           93.9 |
|     199306 |          52 |     350 |    23,590,805 |      76   |                350 |           96   |
|     199603 |          52 |     350 |    25,046,276 |      77   |                350 |           97.8 |
|     200003 |          52 |     350 |    23,181,290 |      69.3 |                350 |           96.8 |
|     200403 |          52 |     350 |    25,891,299 |      75.3 |                350 |           96.8 |
|     200803 |          52 |     350 |    25,734,863 |      73.9 |                350 |           97   |
|     201111 |          52 |     350 |    24,348,886 |      68.6 |                350 |           96.7 |
|     201512 |          52 |     350 |    25,211,313 |      68.8 |                350 |           96.7 |
|     201606 |          52 |     350 |    24,053,755 |      65.9 |                350 |           98.7 |
|     201904 |          52 |     350 |    26,201,371 |      70.9 |                350 |           97.9 |
|     201911 |          52 |     350 |    24,258,228 |      65   |                350 |           97.8 |
|     202307 |          52 |     350 |    24,688,087 |      66.5 |                350 |           97.5 |

Checks: **all passed**.

2023 national check (official: PP 33.06 %, PSOE 31.68 %, Vox 12.38 %, Sumar 12.33 %):

| party   |   share_valid |   escanos |
|:--------|--------------:|----------:|
| PP      |         33.06 |       137 |
| PSOE    |         31.68 |       121 |
| VOX     |         12.38 |        33 |
| SUMAR   |         12.33 |        31 |
| OTHER   |          2.46 |         0 |
| ERC     |          1.89 |         7 |

## Polls (Wikipedia tables)

| cycle    |   polls | first               | last                |   pollsters | missing_n   |
|:---------|--------:|:--------------------|:--------------------|------------:|:------------|
| e2016    |     147 | 2016-01-11 00:00:00 | 2016-06-26 00:00:00 |          26 | 14.3 %      |
| e2019apr |     390 | 2016-07-01 00:00:00 | 2019-04-28 00:00:00 |          38 | 24.4 %      |
| e2019nov |     159 | 2019-05-14 00:00:00 | 2019-11-10 00:00:00 |          28 | 23.9 %      |
| e2023    |     889 | 2019-11-12 00:00:00 | 2023-07-22 00:00:00 |          40 | 17.7 %      |
| next     |     537 | 2023-07-25 00:00:00 | 2026-10-11 00:00:00 |          36 | 8.4 %       |

Latest poll before the cut-off: **2026-10-11** (SocioMétrica).

Top pollsters (all cycles):

| pollster          |   polls |
|:------------------|--------:|
| EM-Analytics      |     433 |
| InvyMark          |     144 |
| Sigma Dos         |     137 |
| NC Report         |     129 |
| Simple Lógica     |     110 |
| SocioMétrica      |     109 |
| GAD3              |     107 |
| Celeste-Tel       |     103 |
| KeyData           |      78 |
| 40dB              |      70 |
| Metroscopia       |      67 |
| DYM               |      67 |
| GESOP             |      56 |
| Hamalgama Métrica |      56 |
| IMOP              |      55 |

Sum of published party shares per poll (should sit a few points below 100 because small parties and 'others' are omitted):

|               |   count |   mean |   std |   min |   25% |   50% |   75% |   max |
|:--------------|--------:|-------:|------:|------:|------:|------:|------:|------:|
| sum_of_shares |    2122 |   92.9 |   8.5 |     0 |    89 |  95.6 |  97.1 |  99.5 |

19 polls sum below 80 or above 101 (kept, flagged here; see `section`).

Notes from the build:

* Dropped 92 official CIS polls from the Wikipedia tables (official CIS is sourced from cis.es); CIS re-estimations by third parties kept as their own pollsters.
* Dropped 456 duplicated (poll, party) rows across pages.
* Excluded 0 polls with fieldwork ending after the cut-off 2026-10-17.

## Known limitations

* No regional (by autonomous community) general-election polls are used: the Wikipedia sub-national tables cover regional elections. Provincial swing is therefore an explicit modelling assumption (phase D).
* Sample size is missing for some polls (shown as '?' on Wikipedia); the model imputes the pollster's median and, failing that, 1,000.
* Wikipedia editors harmonise pollster releases (e.g. Podemos inside/outside Sumar); we follow their table sections and document the mapping in `docs/party_mapping.md`.
* Party shares refer to the valid vote including blank ballots in official results, while pollsters' bases vary; house effects absorb constant differences.

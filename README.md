# Forecasting the 29 November 2026 Spanish general election

**A Bayesian poll-aggregation and seat-projection model, with a four-election backtest.**

*Versión en español: [`spanish version/README.md`](spanish%20version/README.md).*

> **FINAL — polls to 23 November 2026, the last day the law allows them to be published before the
> 29 November election.** Everything below is conditional on polls published up to the data cut-off,
> **23 November 2026**, six days before polling day. This is the last run before the vote; the 14
> November interim run is archived in `outputs/archive/2026-11-14/`.

The 2023 Congreso election produced PP 137 seats, PSOE 121, Vox 33, Sumar 31. On 5 October 2026 the
Cortes were dissolved and a snap election called for 29 November. This repository turns the public
polling record since 2023 (737 polls from 45 pollsters and CIS-based series, the CIS straight from
cis.es) and the
official results 1977-2023 into a probabilistic forecast for that election. It then checks how the
same pipeline would have done 30 days before the 2016, April 2019, November 2019 and 2023 elections.
It started life as an undergraduate Excel/SPSS dossier on Spanish electoral volatility; the
descriptive part of that dossier is reproduced in `reports/figures/`.

## Headline result

**On 29 November**, the model gives PP 30.7 % of the vote (90 % interval 25.1-36.7), PSOE 29.0 %
(23.7-34.9), Vox 18.5 % (15.1-22.3), the Frente Amplio space (Frente Amplio plus Compromís-Front
Valencià, the Sumar lineage) 6.7 % (5.4-8.1) and Podemos 1.4 % (1.1-1.7) where it has its own list.
**PP + Vox reach a majority in 90 % of simulations; PP is the largest party in 71 %.** The PSOE closed
part of the gap in the last week of the campaign, but not enough to change the bloc arithmetic.
Seats follow the lists proclaimed on 3 November. The **base case** is the left as registered: Frente
Amplio and Podemos apart, with Podemos absent from the ten provinces where it joined other lists. The
**sensitivity** is one Frente Amplio + Podemos list everywhere, keeping 0.83 of the sum as Unidos
Podemos did in 2016.

![Figure 1. Forecast Congress](reports/figures/hemicycle_29n_split.png)
***Figure 1. Forecast Congress, 29 November 2026.*** *Expected seats, base case: each party's mean over
10,000 simulations, rounded so they add up to 350. No single simulation need look exactly like this;
the 90 % ranges are in the table below. PP + Vox reach 191 here. "Frente Amplio" includes
Compromís-Front Valencià. "Others" are local lists (Soria ¡Ya!, Teruel Existe, UPL). Merged-left version:
[`hemicycle_29n_merged.png`](reports/figures/hemicycle_29n_merged.png). In the interactive page
(`docs/index.html`) this chart is a coalition builder: set each party to yes, abstain or no in an
investiture vote and see the count against 176 and the share of simulations in which that pact
succeeds.*

| party | vote at cut-off | seats if held at cut-off, 90 % | seats on 29 Nov, split left (base) | seats on 29 Nov, merged left |
|---|---|---|---|---|
| PP | 30.7 % | 121 - 134 | 127 (105 - 150) | 127 (105 - 150) |
| PSOE | 29.0 % | 108 - 121 | 114 (93 - 136) | 114 (93 - 137) |
| Vox | 18.5 % | 59 - 70 | 64 (49 - 80) | 64 (49 - 81) |
| Frente Amplio + Compromís-Front Valencià | 6.7 % | 7 - 11 | 9 (6 - 14) | 9 (5 - 14) |
| Podemos | 1.4 % | 0 - 1 | 0 (0 - 1) | (in Frente Amplio) |
| ERC | 2.6 % | 8 - 12 | 10 (7 - 13) | 10 (7 - 13) |
| EH Bildu / PNV / Junts | 1.4 / 0.8 / 1.2 % | 6-8 / 4-6 / 3-6 | 7 / 5 / 4 | 7 / 5 / 4 |
| BNG / CC / Adelante Andalucía | 0.9 / 0.3 / about 1.5 % | 2-3 / 0-1 / 0-8 | 2 / 0 / 3 | 2 / 0 / 3 |

| event (29 Nov) | split left | merged left |
|---|---|---|
| PP + Vox (+ UPN, SALF) reach 176 seats | 90 % | 90 % |
| PP largest party | 71 % | 71 % |
| PSOE largest party | 29 % | 29 % |
| 2023 investiture bloc (PSOE, FA, Podemos, ERC, Bildu, BNG, CC, AA, PNV, Junts) reaches 176 | 6 % | 5 % |
| PP alone reaches 176 | < 1 % | < 1 % |

**What changed since the 14 November interim run** (PP 128, PSOE 109, Vox 67; PP + Vox majority 94 %,
PP largest 78 %).
- **The PSOE gained in the last week, mostly at Vox's expense.** At the cut-off the model reads PP
  30.7 / PSOE 29.0 / Vox 18.5, against PP 30.5 / PSOE 27.6 / Vox 19.1 published on 14 November. The
  raw polls say the same: across pollsters, the median of each one's latest release moved from PP
  31.5 / PSOE 26.5 / Vox 18.8 (1-13 Nov) to PP 31.4 / PSOE 28.4 / Vox 18.0 (17-22 Nov). PP held; PSOE
  rose about two points; Vox and the left of PSOE fell. The Sánchez-Feijóo debate (19 Nov) is in the
  middle of that window and the polls after it do not show a reversal.
- **Part of the change is a re-reading, not movement.** With all the data the model now reads 14
  November itself as PP 30.8 / PSOE 28.6 / Vox 18.4. The aggregator is a smoother: later polls inform
  the estimate for earlier weeks, and the releases since 14 November also re-estimate every
  pollster's house effect. Since 14 November as re-read, the movement is PP -0.1, PSOE +0.4, Vox +0.1.
  The two parts were not separated further.
- **The bloc arithmetic moved, but only a little.** PP + Vox fall from 49.6 % to 49.2 % of the vote and
  from a 94 % to a 90 % chance of a majority; the expected right-bloc total is 191 seats. PSOE's chance
  of finishing first rises from 22 % to 29 %. Six days out, these figures rest almost entirely on the
  election-day polling error.
- **The CIS pre-election microdata are now in.** cis.es published the microdata of study 3584 (45,074
  interviews). Our recall-weighted likely-voter re-estimate gives PSOE 29.4 / PP 27.9 / Vox 22.0: like
  the outside re-estimates, PSOE first and Vox far above the official 18.4. It does not move the
  average. A refit without it gives the same shares to one decimal, because the CIS-based series form
  one family whose house effects absorb it.
- **Pollsters still disagree on the gap, not on the bloc.** In the last releases the PP lead runs from
  6.8 points (Hamalgama Métrica) to -2.6 (SW Demoscopia); 40dB, Ipsos, Metroscopia and More in Common
  have it under one point, while most others give 2.5-5. PP + Vox are between 47 and 53 % in all but
  SW Demoscopia (45.7).
- Data plumbing only: the Wikipedia page moved its 2023-24 tables to a sub-page (now fetched too; no
  row lost), and the CIS ballot labels of 29N (Frente Amplio and its joint lists, Compromís-Front
  Valencià, UPN-PP) were added to the microdata mapping. No model code changed, so the backtest and
  its 11.5 % election-day error are those of 14 November. No new CEO wave since 14 October.

## Trend, blocs and backtest

![Figure 2. State-wide parties since the July 2023 election](reports/figures/trend_national.png)
***Figure 2. State-wide parties since the July 2023 election: polls and latent trend.*** *Latent vote
share (median, 50 % and 90 % bands) and every poll. Left: the whole cycle; the shaded strip is the period
enlarged on the right. Right: the last four months, with the dated events: the Ceuta border crisis
(30 Jul), the decrees rejected in Congress (2 Oct), the dissolution (5 Oct), coalitions closed and Colau
announced (17 Oct), the Urda rail crash (28 Oct), lists proclaimed (3 Nov), the start of the campaign
(13 Nov) and the Sánchez-Feijóo debate (19 Nov). The dashed line is the data cut-off. The step in Podemos in mid-October is the switch to the
registered ballots.*

![Figure 3. Bloc seat totals](reports/figures/bloc_majority_29n_split.png)
***Figure 3. Bloc seat totals on 29 November.*** *Seat totals for the two competing blocs, base case
(split left).*

![Figure 4. Backtest](reports/figures/backtest.png)
***Figure 4. Backtest.*** *What the same pipeline would have said 30 days before each of the last four
elections, against the result.*

## Methods

| component | choice | code |
|---|---|---|
| Results | Ministerio del Interior fixed-width files, all 16 elections, 52 provinces; D'Hondt reproduces the official 2019 and 2023 seats exactly (tested) | `mir.py`, `seats.py`, `tests/` |
| Polls | Wikipedia opinion-polling wikitext (CC BY-SA 4.0), rowspan/colspan/reference-aware parser; third-party re-estimations of CIS data kept as their own pollsters; one release per overlapping fieldwork window of a pollster | `wiki_polls.py`, `build_data.py` |
| CIS | straight from cis.es: the official estimate for 99 studies since 2016 (PDFs, all cycles), and our re-estimate from the microdata for the current cycle (CIS weight, 2023 recall, likely voters; not backtested). Series built from one survey share its sample size | `cis.py`, `cis_microdata.py` |
| Party mapping | per-election Ministry codes and poll labels to canonical ids and blocs; Frente Amplio + Compromís-Front Valencià continue the Sumar series | `data/party_map_*.yaml`, `docs/party_mapping.md` |
| Aggregator | weekly logit-scale random walk per party, anchored on the 2023 result; level shifts where the party supply changed; hierarchical house effects centred on publishing pollsters, CIS-based series as one; binomial + excess noise; NUTS (nutpie), 4 x 1,000 draws | `model.py` |
| Seats | proportional swing from 2023 provincial shares + log-normal provincial noise (sd 0.13); regional-poll layer (CEO, Sociómetro, CIS subsamples); 29N ballots as proclaimed (Podemos absent from ten provinces, the Valencian part of the Frente Amplio space set from polls, UPN with PP); 3 % threshold; 10,000 simulations | `seats.py`, `regional.py`, `project_seats.py` |
| Backtest | refit 30 days before 2016, Apr-2019, Nov-2019, 2023 with only earlier polls; regional layer only for Catalonia 2023 (CEO) | `backtest.py` |
| Election day | six days of random-walk drift plus an election-day error calibrated on the backtest (11.5 % of each party's share); mean reversion tested and rejected | `forecast.py` |
| Descriptive | turnout, Laakso-Taagepera ENP, Pedersen volatility split within/between blocs, bloc matrix, provincial fragmentation | `indices.py`, `descriptive.py` |

## Backtest scorecard (mean over the four elections, forecasts made 30 days out)

| method | vote MAE (pp) | vote CRPS (pp) | 90 % vote coverage | seat MAE | 90 % seat coverage | Brier (two events) |
|---|---|---|---|---|---|---|
| **this model** | **1.04** | **0.89** | 40 % | **4.2** | 73 % | **0.06** |
| 30-day poll average | 1.17 | 1.17 | n/a | 4.9 | n/a | 0.12 |
| last election result | 2.59 | 2.59 | n/a | 11.0 | n/a | 0.25 |

The backtest was refitted on 14 November with the two new rules, which apply to every cycle:
overlapping tracker releases count once (10-17 % fewer polls per election) and CIS-based series are
one pollster. The scores barely changed against the 17 October version (vote MAE 1.03, seat MAE 4.2,
Brier 0.05): neither rule buys accuracy in the backtest; they are there because the alternative
double-counts. The regional layer could only be backtested for Catalonia in 2023, where it cut the
2023 seat MAE from 3.5 to 3.1. That gain is in-sample: the layer's error settings were calibrated on
the same election.

In words:

* The model beats both baselines on every point-accuracy score, but the margin over a plain 30-day
  poll average is small. Most of the value is in the house-effect correction and the intervals.
* **The intervals are too narrow.** At 30 days out the 90 % vote intervals covered only 40 % of the
  outcomes. In July 2023 every pollster underestimated PSOE by about 5 pp, and the model gave a 68 %
  chance to a PP + Vox majority that did not happen. Polls share their errors, which is why the
  election-day projection adds an error term (11.5 % of each party's share, the smallest value that
  would have restored 90 % coverage).
* Where it fails: sudden late movements (Vox doubling in the last month of the November 2019
  campaign; Cs collapsing) and any election with a common polling bias.

Full per-election table: `outputs/backtest_scorecard.csv` and `outputs/backtest_details.csv`.

## What drives the uncertainty

Seat standard deviation for PP when sources are added one at a time, base case
(`outputs/uncertainty_decomposition.csv`): the posterior at the cut-off 2.7 seats, plus provincial
swing noise 4.1, plus six days of drift 4.3, plus election-day polling error 13.8. With six days to
go the shared polling error is nearly all of it. For the regional parties near the 3 % district
threshold, provincial swing noise and the regional surveys matter most.

## Descriptive findings (the upgraded dossier)

* Fragmentation peaked in 2019 (effective number of parties 5.8 by votes) and fell back to 4.1 in 2023.
* Volatility is mostly *within* blocs: the two largest shocks (1982, 42 pp; 2015, 32 pp) moved voters
  between parties of the same side. The left/right balance is much more stable than any party's share.
* The peripheral vote is 7 % nationally but 22-54 % in the Basque, Navarrese and Catalan provinces,
  where national polls say least and investitures are decided.

## How to run

Requires [uv](https://docs.astral.sh/uv/) (it fetches Python 3.12). No C compiler needed.

```bash
uv sync --extra dev
make all          # data -> tests -> descriptive -> aggregate -> seats -> backtest -> forecast -> report
```

Individual phases: `uv run electoral build-data | descriptive | aggregate | seats | backtest | forecast | report`.
`uv run electoral figures` re-draws every figure from the saved outputs without refitting. Figures and
the interactive page are written in English (`reports/figures/`, `docs/index.html`) and in Spanish
(`spanish version/`); the wording of both is in `src/electoral/i18n.py` and `report.py`. The coalition
builder of the page is `pactometro/template.html`; `uv run electoral pactometro` writes it as a page of
its own (`pactometro/index.html`) for trying changes.
`build-data` downloads the CIS PDFs and microdata (about 100 studies) and the CEO microdata (about
330 MB) into the gitignored `data/raw/`. The aggregator takes about eight minutes; the backtest about
ten (per-cycle results are cached in `outputs/backtest/`). Seeds, dates, party supply scenarios
and regional settings live in `config.yaml`; every output is stamped with the cut-off.

Outputs for other projects: `outputs/poll_average_daily.csv` (daily latent share per party with
quantiles), documented in `docs/outputs.md`. Interactive version: `docs/index.html`.

## Repository

```
config.yaml            dates, seed, sources, model, party-supply scenarios, regional layer, backtest
data/party_map_*.yaml  party lineage and bloc definitions (edit here to disagree)
data/regional/         regional tables extracted from PDFs, with their URLs
data/processed/        tidy datasets + DATA_DICTIONARY.md + DATA_QUALITY.md + cis_studies.csv + regional_polls.csv
src/electoral/         mir, wiki_polls, cis, cis_microdata, regional, build_data, model, seats, backtest, forecast,
                       plots, figures, i18n (English / Spanish), pactometro, report
tests/                 D'Hondt (incl. exact reproduction of official seats), parsers, CIS, regional layer, model, 29N ballots
outputs/               poll average, house effects, seat draws, scorecard, diagnostics (traces gitignored)
reports/figures/       all figures; docs/methods_note.md is the write-up; docs/index.html the interactive page
docs/context_29N_2026.md  the political context, party supply and sources for the 29N re-run
spanish version/       README.md, index.html and figures/ in Spanish
pactometro/            the coalition builder (template.html) embedded in both interactive pages
```

## Limitations

* **Nothing after 23 November is in the data.** Polls may not be published in the last five days
  (LOREG art. 69.7), so the RTVE eight-way debate of 23 November and anything later reach the model
  only through the election-day error. The last CEO wave ended on 5 October.
* **Who counts as a pollster shapes the PP-PSOE gap.** House effects are centred on the average
  pollster, one vote each, with the eleven CIS-based series as one. That average is a choice: the
  model's PP lead at the cut-off is 1.7 points, the median of the pollsters' last releases is 2.9,
  and a plain average of recent private polls is higher still, because prolific pollsters weigh more
  in it. The majority probability is not very sensitive to this; "largest party" is.
* **Where the Frente Amplio space wins its seats is partly assumed.** Its Valencian part comes from
  the pollsters that list Compromís-Front Valencià apart (about a fifth of the space); the rest keeps
  Sumar's 2023 geography, which probably understates Más Madrid. The model gives the space 9 seats
  where most pollsters give 7 to 12 and the CIS 11 to 17 for a similar vote.
* **Common polling error is the dominant risk** and is handled by an inflation term calibrated on
  four elections (twenty party-election residuals). With six days to go it is nearly all the uncertainty.
  In 2023 every pollster underestimated PSOE by about 5 points; the model does not assume that will
  happen again, in either direction.
* **The regional layer rests on thin evidence.** Its weights were calibrated on one election (Catalonia
  2023, four parties), and the CEO overstated ERC by 5 points then. The Sociómetro asks about the Basque
  Parliament, so its swing since 2024 is assumed to carry over. CC and Navarre have no regional source.
* **Our CIS microdata series is not backtested**, and Adelante Andalucía enters the seat model at its
  recent poll median (about 1.5 %) rather than through the aggregator.
* **No demographic model.** The campaign's fight for young voters is not modelled: polls show them
  leaning right with a large gender gap, voting less and deciding late (`docs/context_29N_2026.md`
  §8.5). Late movement is covered only by the election-day error term.
* **Parties are modelled independently** on the logit scale; the seat model renormalises.
* Turnout is not modelled; shares are of the valid vote.

## Data sources and licences

* Ministerio del Interior, *infoelectoral.interior.gob.es*, files `02YYYYMM_TOTA.zip`. Reuse under
  Ley 37/2007 and RD 1495/2011. *Origen de los datos: Ministerio del Interior.*
* English Wikipedia, "Opinion polling for the [2016 / April 2019 / November 2019 / 2023 / 2026]
  Spanish general election" and the 2019-2022 sub-pages, CC BY-SA 4.0.
* Centro de Investigaciones Sociológicas, cis.es, CC BY 4.0: estimate PDFs, technical sheets and
  microdata. *Fuente de los datos: Centro de Investigaciones Sociológicas.*
* Centre d'Estudis d'Opinió (Generalitat de Catalunya), open microdata of the Baròmetre d'Opinió Política.
* Basque Government, Sociómetro Vasco and the official 2024 Basque Parliament results (euskadi.eus).

## Author

Kristiyan Pandas, [github.com/kristiyanpanda](https://github.com/kristiyanpanda). BA Sociology, MSc Data
Analytics. Interactive version of the results: `docs/index.html`.

## Resumen en español

*Versión completa en español: [`spanish version/README.md`](spanish%20version/README.md); página
interactiva: `spanish version/index.html`.*

**FINAL: encuestas hasta el 23-11-2026, último día en que la ley permite publicarlas antes del 29-N.**
Modelo bayesiano de agregación de encuestas (paseo aleatorio semanal en escala logit, efectos de casa
por encuestadora, anclado en el resultado de 2023), con el CIS tomado directamente de cis.es (estimación
oficial y reestimación propia con microdatos, incluido el preelectoral 3584) y una capa de encuestas
regionales (CEO, Sociómetro, CIS). Proyección de escaños por D'Hondt en las 52 circunscripciones con las
candidaturas proclamadas el 3 de noviembre y 10.000 simulaciones. Con datos hasta el 23-11-2026, el 29 de
noviembre el PP obtendría el 30,7 % del voto y 105-150 escaños (mediana 127), el PSOE el 29,0 % y 93-136
(114) y Vox el 18,5 % y 49-80 (64); PP+Vox superarían los 176 con una probabilidad del 90 % (94 % el
14-N), y el PP sería primera fuerza con un 71 % (78 %). En la última semana de campaña el PSOE ha
recortado distancia, sobre todo a costa de Vox y de su izquierda; la diferencia entre PP y PSOE es de
1,7 puntos. El backtest sobre 2016, abril y noviembre de 2019 y 2023 muestra un error medio de 1,0 puntos
en voto, pero intervalos demasiado estrechos por el sesgo común de las encuestas; por eso la proyección
al día de la elección incorpora un error electoral calibrado, que a seis días de la votación domina la
incertidumbre.

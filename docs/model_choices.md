# Model choices (and what they buy or cost)

A short list of the decisions that shape the numbers. Each is a one-line change in code or
`config.yaml`; the point of writing them down is that a reader can disagree with a specific one.

## Aggregator (`src/electoral/model.py`)

| choice | why | cost |
|---|---|---|
| Weekly latent grid, logit-scale random walk per party | keeps shares in (0,1), small parties get proportionally smaller moves; ~165 weeks x 12 parties is cheap to sample | independent walks ignore that shares must sum to one; the seat model renormalises |
| Anchor at the 2023 result (sd 0.05 on the logit scale) | an election is the one poll without house effect; it pins the level | if the electorate moved in the first weeks after the election the walk has to catch up |
| House effects hierarchical per party, centred on the pollsters that publish that party | "the average pollster is unbiased" is the weakest identifying assumption; centring only over publishing pollsters avoids letting non-publishing pollsters absorb small parties' levels (this bug collapsed regional parties in a first version) | if the whole industry is biased in one direction the model is biased by the same amount; the backtest measures this |
| Series built from the same raw data are one pollster in that average: the official CIS estimate, our microdata re-estimate and the third-party re-estimates of CIS data share one vote (`model.house_families`) | on 14 Nov 2026 ten of 39 series were readings of CIS data and leaned to PSOE; with one vote each they pulled the average by about 0.3 points per main party | which series belong together is a judgement; the family's vote is the mean of its members, so the official estimate (the largest house effect of any series) still weighs in it |
| Noise = binomial(n) + party-specific excess variance | sample size matters but rounding, design effects and differing bases add a floor | polls with missing n get their pollster's median (else 1,000) |
| One free level shift for Sumar on 2023-12-08 | Podemos leaving Sumar is a discontinuity, not drift; without it the walk needs a huge innovation sd | the shift date is fixed by hand from the first poll that lists Podemos separately |
| A second level shift for Sumar/Frente Amplio, and one for Podemos and ERC, in the week of 11 Oct 2026 | from then the tables list the ballots as registered: Podemos only where it has a list, its voters on joint lists counted with Frente Amplio, Front Valencià or ERC. That is a change of definition, not opinion | the date is the week of the first such poll; polls that week under the old definition are slightly misread |
| Frente Amplio series = FA + Compromís-Front Valencià, or the single figure some pollsters give for both | the two lists are one space with Sumar's 2023 geography; a joint figure cannot be split | Compromís's seats are reported inside Frente Amplio, unlike the CIS and most pollsters |
| Only non-overlapping fieldwork windows per pollster, latest release first | daily trackers and cumulative panels re-publish the same respondents; counted as separate polls they would weigh several times and narrow the intervals | earlier releases of a tracker are discarded (72 of 659 current-cycle polls on 14 Nov); applied after the backtest's cut-off so it sees only what existed then |
| Entrants (Podemos, SALF) start from a diffuse prior at week 0 and are only reported from their first poll | no data before entry | the pre-entry path is meaningless and is masked in outputs |
| NUTS via nutpie (numba) | no C compiler needed on Windows; 4 chains x 1000 draws in about five minutes | one more dependency |
| Wikipedia polls, plus CIS straight from cis.es | Wikipedia's CIS rows mixed the official estimate with third-party re-estimates; cis.es gives the official estimate (all cycles) and the microdata, which we re-weight ourselves (current cycle; not backtested) | about 100 PDF layouts to parse; series sharing one CIS survey split its n, so it counts once |

## Seat projection (`src/electoral/seats.py`)

| choice | why | cost |
|---|---|---|
| Proportional swing from 2023 provincial shares | no provincial polls exist for general elections; proportional swing beats uniform swing for small and regional parties | a party growing mostly in one region is mis-allocated |
| Provincial noise: log-normal, sd calibrated on 2019->2023 and Apr->Nov 2019 residuals | the residuals of the same swing rule in the last two transitions are the best available estimate of how wrong it is | the two calibration transitions were unusually different (0.10 vs 0.17 log points); their mean is used |
| Podemos borrows Sumar's 2023 geography; SALF is uniform | Podemos' 2023 votes were inside Sumar; SALF had no 2023 footprint | both are assumptions, and both parties are near the 3 % province threshold where the assumption bites most |
| Untracked lists keep their 2023 share (UPN, CUP, Aliança...) | they are too rarely polled to model | Aliança Catalana could win a seat in Girona or Lleida under some polls; the model cannot see it |
| Regional-poll layer: the region-level share implied by the swing is combined with a regional survey, weighting each by its error, before the coalitions are applied (CEO: ERC, Junts, PSC, Comuns; Sociómetro: PNV, Bildu per territory; CIS subsample: BNG) | national polls under-read parties concentrated in one region (Sep 2026 nowcast: ERC 6-9 seats, CEO 10-11) | errors calibrated on a single check (Catalonia, Jul 2023: CEO RMSE 5.3 pp, swing 7.7 pp; four parties); the CEO overstated ERC by 5 points then; the Sociómetro asks about the Basque Parliament, so its swing since 2024 is assumed to carry over to a general election; CC (18 CIS respondents) and Navarre have no regional source |
| Podemos has no share in the ten provinces where it has no ballot (Catalonia, Valencian provinces, Canarias, Baleares); its polled share is spread over the other 42 with Sumar's 2023 geography | pollsters now ask about the registered lists, so the Podemos figure is its vote where it runs alone; the 17 Oct run instead moved an assumed part of it to Frente Amplio and ERC (50/50 in Catalonia) | relies on pollsters asking by ballot; a pollster still asking for Podemos everywhere overstates it where it runs |
| The Valencian part of the Frente Amplio space is set from the polls that list Compromís-Front Valencià apart (median over pollsters, 19 % of the space on 14 Nov, drawn with the spread between pollsters), not from Sumar's 2023 geography (13 %) | the space is now more Valencian than in 2023, and its seats depend on where its vote sits | seven pollsters publish the split and they disagree (10 % to 23 %); Más Madrid's weight in Madrid is still read from 2023 |
| Coalitions applied per province after the swing (29N base case: UPN into PP in Navarra; sensitivity: one Frente Amplio + Podemos list everywhere) | poll parties and ballot lists differ; the merge is explicit and switchable per scenario | the merged-left sensitivity uses a 0.83 efficiency |
| Adelante Andalucía spread uniformly over Andalusia | no 2023 general-election footprint | its provincial strength (Cádiz, Sevilla) is flattened |
| Renormalise each province to 2023's non-blank total | the twelve tracked parties do not sum to one; the remainder is spread proportionally | mechanical |

## What the intervals mean

The seat distributions answer "if the election were held at the cut-off date": they carry the
posterior uncertainty of the latent shares plus provincial swing noise. They do **not** include
(a) movement between the cut-off and the election, which the election-day projection adds by
extrapolating the random walk, nor (b) a common industry-wide polling error on election day,
which the backtest measures and which is added to the election-day projection only if it improves
calibration (phase F).

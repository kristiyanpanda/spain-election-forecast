# Forecasting the next Spanish general election: a Bayesian poll aggregation and seat projection model

> **Update, 23 November 2026: FINAL run, six days before the 29 November election,** with the polls
> published up to the last day the law allows. Section 14 gives the final results and what changed in
> the last week of the campaign. Section 13 keeps the 14 November interim run, section 12 the
> 17 October run, and sections 6, 8 and 9 the 18 September numbers, as a record.

*Methods and findings note. Data cut-off 2026-09-18. All numbers are produced by the code in this
repository (`make all`); none is typed by hand.*

## 1. Question and scope

The 15th Cortes Generales were elected on 23 July 2023 and the next election must be held by
mid-August 2027. This note asks three questions. (1) If the election were held at the cut-off date,
what is the probability distribution of vote shares and seats per party and bloc, and how does it
change when projected to the legal deadline? (2) How reliable would the same pipeline have been at
the last four elections? (3) Which structural features of the party system drive the uncertainty?

The project modernises an undergraduate analysis of Congreso results 1977-2023 (turnout, effective
number of parties, volatility within and between blocs) built in Excel and SPSS. Everything here is
reproducible from two public sources and one command.

## 2. Data

**Official results.** The Ministerio del Interior publishes every general election since 1977 as
fixed-width files (`02YYYYMM_TOTA.zip`). The parser (`src/electoral/mir.py`) reads the candidatura
table, the per-district totals and the per-district votes, and links every provincial list to its
national head list. A test reproduces the official 2019 and 2023 seat allocations exactly in all 52
districts from the parsed votes, which validates both the parser and the D'Hondt implementation.
Sixteen elections, 52 provinces each, 350 seats each; between 92 and 99 % of the valid vote is
assigned to a named party family and the rest to OTHER (`data/processed/DATA_QUALITY.md`).

**Polls.** English Wikipedia's "Opinion polling for the ... Spanish general election" pages (CC
BY-SA 4.0) are the only open, consistently structured source covering private pollsters and the
CIS together. The wikitext of seven pages (the current cycle, 2023 and its two yearly sub-pages,
Nov-2019, Apr-2019 and 2016) is parsed with a purpose-built table reader that handles row-spanning
cells, multi-line references and seat projections embedded in cells. Result: 2,102 polls from
December 2015 to 11 September 2026, of which 490 belong to the current cycle (25 pollsters; 33 %
of them from one weekly panel, EM-Analytics). Sample size is missing for 9 % of current-cycle polls
and is imputed with the pollster's median. (18 Sep version: CIS entered through its Wikipedia
rows. From 17 Oct the CIS comes straight from cis.es; see section 12.)

**Relabelling.** Spanish party labels change every cycle. Two maps (`data/party_map_*.yaml`)
translate Ministry codes and Wikipedia labels into canonical ids, and `docs/party_mapping.md` lists
the judgement calls: the post-Convergència line (CiU → CDC → PDeCAT → JxCat → Junts) is one family;
Podemos + IU → Unidos Podemos → Sumar is one lineage for volatility purposes but separate series
where they actually competed; Ciudadanos and UPyD are counted in the state-wide right bloc.

## 3. Descriptive layer: what changed in the party system

Three findings from the reproduced dossier (`reports/figures/turnout_enp.png`, `volatility.png`,
`bloc_matrix.png`):

* **Fragmentation is a 2015 phenomenon that has partly reversed.** The effective number of parties
  by votes stayed between 2.7 and 4.3 from 1977 to 2011, jumped to 5.0 in 2015 and 5.8 in both 2019
  elections, and fell back to 4.1 in 2023 (3.4 by seats). Turnout has been in the 65-72 % range
  since 2011, ten points below the 1977-2004 average.
* **Volatility is mostly within blocs.** The two largest shocks, 1982 (42 pp) and 2015 (32 pp),
  moved voters mainly between parties of the same bloc (UCD → AP and PSOE in 1982; PP → Cs and
  PSOE/IU → Podemos in 2015). Between-bloc volatility exceeded 10 pp only in 1982, 2011 and 2015.
  This matters for forecasting: the aggregate left/right balance is far more stable than any single
  party's share, which is why bloc-majority probabilities are more robust than party seat counts.
* **The peripheral vote is geographically concentrated.** In 2023 the regionalist and nationalist
  lists took 7.3 % of the vote nationally but 22-54 % in the Basque, Navarrese and Catalan provinces,
  where the effective number of parties is 4.5-5.6 against 2.8-3.9 elsewhere. Those provinces carry
  the seats that decide investitures, and they are exactly where a national poll says least.

## 4. Poll aggregation model

The aggregator (`src/electoral/model.py`) is a state-space model on a weekly grid from the 2023
election to the cut-off (166 weeks, 12 parties, 4,714 poll-party observations):

* latent share pi[t, p] = invlogit(theta[t, p]); theta follows an independent Gaussian random walk
  per party with party-specific innovation sd (non-centred parameterisation);
* week 0 is anchored on the 2023 result (sd 0.05 on the logit scale); Podemos and SALF, which did not
  exist as separate lists in 2023, start from a diffuse prior and are reported from their first poll;
* one free level shift for Sumar dated 8 December 2023, when Podemos left the group;
* observation y = pi + delta[p, pollster] + noise, with hierarchical house effects centred to zero
  across the pollsters that publish each party, and noise sd = sqrt(pi(1-pi)/n + tau[p]^2);
* NUTS (nutpie), 4 chains x 1,000 draws after 1,000 tuning draws, seed 20260918.

Diagnostics: 0 divergences, maximum R-hat 1.01, minimum bulk ESS 432 (`outputs/diagnostics_next.json`).
House effects are of the expected size and sign (`reports/figures/house_effects.png`): the CIS sits
about 2 pp below the pollster average for PP and 1 pp above for PSOE; InvyMark, DYM and NC Report sit
1.5-2 pp above on PP. The average pollster is assumed unbiased; the backtest (section 7) measures how
costly that assumption is.

A first version used a plain zero-sum constraint on house effects across all pollsters. Pollsters that
never publish a regional party then absorbed that party's level through unconstrained effects and the
regional series collapsed toward zero. Centring only across publishing pollsters fixed it; the episode
is recorded in `docs/model_choices.md` because the bug produced plausible-looking output.

## 5. Seat projection

Vote-share draws are turned into seats (`src/electoral/seats.py`) by proportional swing from each
party's 2023 provincial share, multiplicative log-normal noise per province and party with sd 0.13
(calibrated on the residuals of the same swing rule in the Apr→Nov 2019 and Nov 2019→2023
transitions, 0.10 and 0.17), renormalisation of each province to its 2023 non-blank total, and D'Hondt
with the 3 % threshold in 50 districts plus plurality in Ceuta and Melilla; 10,000 simulations.
Podemos borrows Sumar's 2023 geography, SALF is spread uniformly, and untracked lists (UPN, CUP,
Aliança Catalana...) keep their 2023 shares. There are no provincial polls for general elections, so
the provincial layer is an assumption with calibrated noise, not an estimate.

## 6. Results at the cut-off (18 September version)

At 18 September 2026 the latent shares are PP 32.4 % (90 % interval 31.3-33.4), PSOE 25.9 %
(24.8-27.0), Vox 18.5 % (17.4-19.8), Sumar 6.5 %, Podemos 3.2 %, SALF 1.8 %. The seat simulation
gives PP 130-144, PSOE 99-113, Vox 59-73, Sumar 6-12; PP + Vox (+ UPN and SALF) total 197-211 seats,
so conditional on the model the probability of a right-bloc majority if the election were held now is
above 99 %, and the 2023 investiture bloc (PSOE, Sumar, Podemos, ERC, Bildu, BNG, CC, PNV, Junts)
reaches 137-151. These intervals describe today's opinion, not the election.

## 7. Backtest

The pipeline was replayed 30 days before each of the last four elections with only the polls
available then, anchored on the previous result (`outputs/backtest_scorecard.csv`):

| election | polls used | model vote MAE | poll-average MAE | last-result MAE | model seat MAE | 90 % vote cover |
|---|---|---|---|---|---|---|
| June 2016 | 89 | 1.12 | 1.18 | 1.07 | 5.1 | 56 % |
| April 2019 | 314 | 0.85 | 0.94 | 4.44 | 3.8 | 30 % |
| November 2019 | 72 | 1.23 | 1.44 | 2.02 | 5.3 | 55 % |
| July 2023 | 766 | 1.02 | 1.12 | 2.83 | 3.7 | 18 % |
| **mean** | | **1.06** | 1.17 | 2.59 | **4.5** | **40 %** |

Three conclusions. First, the model is better than both baselines on point accuracy in every election
except 2016, where the "nothing changes" baseline was marginally better because the repeat election six
months after the previous one changed little and polls overstated Unidos Podemos. Second, the gain over
a plain 30-day poll average is modest (0.1 pp of vote, 0.5 seats per party); most of the model's value
is in house-effect correction and in producing intervals at all. Third, and most important, the
intervals are badly under-dispersed: 90 % intervals covered 40 % of vote outcomes and 76 % of seat
outcomes. July 2023 is the clearest case: every pollster had PSOE near 26 % and it took 31.7 %; the
model gave 66 % to a PP + Vox majority that did not happen (Brier 0.22 on that event). Pollsters share
their errors, and a model that treats the average pollster as unbiased inherits the shared error in
full. The seat intervals cover better than the vote intervals because provincial noise adds width that
the vote intervals lack.

## 8. Projection to the legal deadline (18 September version)

Two additions to the plain random-walk extrapolation were tested on the backtest before use
(`outputs/forecast_deadline.json`):

* **Mean reversion toward the previous result** with weights 0.1, 0.2, 0.3 raised the 30-day vote MAE
  in three of four elections (e.g. 2023: 1.02 to 1.20 pp with weight 0.1). It is not used. Whether
  a fundamentals drift helps at an eleven-month horizon cannot be settled with four 30-day
  observations, and the note says so rather than pretending otherwise.
* **Election-day error inflation.** The backtest residuals imply that the model's own uncertainty
  should be roughly three times wider to reach nominal coverage. Because polling error scales with
  party size, the correction is an extra error of 12.3 % of each party's share (the smallest value
  that restores 90 % coverage over the 20 party-elections above 3 %), applied on the logit scale.

With 47 weeks of random-walk drift plus that term, the deadline distribution is PP 25-40 % of the
vote and 107-165 seats, PSOE 20-33 % and 78-134 seats, Vox 13-25 % and 42-92 seats. The probability
of a PP + Vox majority falls from above 99 % to 94 % (95 % with UPN and SALF), PP largest party to
84 %, and the investiture bloc's majority rises from below 1 % to 3 %. That the headline probability
barely moves while every party interval doubles is the substantive finding: the current gap between
the blocs (about 60 seats) is large relative to any plausible polling error, whereas individual seat
counts are not.

## 9. What drives the uncertainty (18 September version)

`forecast.decompose_uncertainty` re-runs the seat simulation with sources of uncertainty switched
on one at a time (`outputs/uncertainty_decomposition.csv`). Standard deviation of seats:

| source added | PP | PSOE | Vox | Sumar | Junts | right bloc | P(right >= 176) |
|---|---|---|---|---|---|---|---|
| posterior of today's shares only | 3.2 | 2.8 | 2.8 | 1.0 | 0.6 | 2.2 | > 99 % |
| + provincial swing noise | 4.4 | 4.3 | 4.1 | 1.7 | 0.9 | 4.2 | > 99 % |
| + eleven months of drift | 11.1 | 11.2 | 11.8 | 4.3 | 1.3 | 10.7 | 99 % |
| + election-day polling error | 17.6 | 17.3 | 15.2 | 5.4 | 1.5 | 16.6 | 95 % |

For the large parties the ranking is election-day error, then drift, then provincial noise; the two
"future" components contribute about six times the variance of today's measurement. For Junts and
the other regional parties the provincial noise is the single largest source in relative terms (it
raises the sd by half, drift and polling error by a quarter each), because they live near the 3 %
district threshold where a small provincial error moves whole seats. Structurally the descriptive
layer explains the robustness of the bloc probability: volatility in Spain is mostly within blocs,
so bloc totals move less than party shares, and the peripheral vote is confined to a handful of
provinces where national polls have the least to say.

## 10. Limitations

* Twenty party-election residuals from four elections are a thin basis for the error-inflation term.
* No provincial polls: the seat layer is an assumption with calibrated noise, and parties concentrated
  in one region are where it bites.
* Untracked lists (UPN, CUP, Aliança Catalana, Adelante Andalucía) keep their 2023 shares.
* One panel (EM-Analytics) supplies a third of the polls in the current cycle; its house effect is
  small but its weight in the trend is large.
* Parties are modelled independently on the logit scale; the seat model renormalises.
* Turnout and the blank vote are held at 2023 levels.

## 11. What I would do differently

* Model shares jointly (a multinomial or Dirichlet observation model) instead of independent logit
  walks, so that a PSOE gain is a loss somewhere.
* Estimate the industry-wide error as a latent common shock with a prior from a longer history of
  elections (Spain has 16), rather than as a post-hoc inflation term.
* Add a turnout model and a blank-vote model; both moved in 2023.
* Use the Spanish-language Wikipedia and pollsters' own releases to cross-check the English tables.
* Replace the fixed Sumar break with a change-point detected from the data.
* Run the backtest at several horizons (7, 30, 90, 365 days) to see how the error inflation should
  grow with lead time instead of assuming it is constant.

## 12. Provisional re-run for 29 November 2026 (data to 17 October)

On 5 October the Cortes were dissolved and an election called for 29 November. The re-run changed
five things; each is a separate commit on the branch `rerun/29n-provisional`.

**CIS from the source.** Wikipedia rows such as "CIS (Target Point)" had been read as CIS. They share a
row span with the official CIS row, so the de-duplication kept whichever came first, usually a
third-party re-estimate: 31 of the 37 current-cycle "CIS" polls were re-estimates. These are now
pollsters of their own ("CIS re-est. (X)"). The official CIS estimate is read from the "Estimación de
voto" PDF of each study on cis.es: 97 studies since January 2016, all cycles, so it also enters the
backtest. All 89 studies that Wikipedia also lists agree within 0.15 pp. A second series re-estimates
each current-cycle barometer from the open microdata: the CIS weight, post-stratification on recalled 2023
vote, and likely voters (9 or 10 on the 0-10 scale). It reproduces the dossier's September figures
(PP 30.6, PSOE 25.7) and is not backtested. Series built from one survey (official, ours, third-party
re-estimates) split its sample size, so a CIS survey counts once. Fitted house effects: the official CIS
-4.8 pp for PP and +3.5 for PSOE, the largest of any pollster; our re-estimate -0.8 and -0.1, close
to the private average.

**Party supply** (`docs/context_29N_2026.md` §7). The Junta Electoral Central had not published the
validated coalitions on 17 October, so they follow press reports. Frente Amplio continues the Sumar
series. Podemos runs apart except in Canarias and the Valencian Community (joint lists). It has no list
in Catalonia, where its polled vote is split 50/50 between ERC and Frente Amplio, the weakest
assumption. UPN joins PP in Navarre, and Aliança Catalana does not run. The sensitivity case merges
Frente Amplio and Podemos everywhere at 0.83 of the sum (sd 0.05), the 2016 Unidos Podemos precedent.
Adelante Andalucía, polled in about 10 % of polls since January 2026, could not be identified by the
aggregator (R-hat 4: 42 of its 61 polls come from one panel). It enters the seat model at its recent poll
median, 0.9 % nationally, with 30 % log-normal noise, spread over Andalusia.

**Regional-poll layer.** National polls under-read concentrated parties. Regional surveys give
estimates of their general-election share in their region:
- the CEO's Congress-vote question in Catalonia (two waves, about 4,000 respondents, 2023 recall);
- the Sociómetro Vasco's Basque-Parliament estimate per territory, relative to the 2024 result and
  applied to the 2023 general share;
- the CIS regional subsample in Galicia (BNG, about 920 respondents).

In each simulation the region-level share implied by the swing is combined with the survey, each
weighted by its error, and the party's provincial shares there are rescaled. The errors come from the
only regional check available: in Catalonia in July 2023 the CEO missed by 5.3 pp (RMSE over four
parties) and national polls plus proportional swing by 7.7 pp. The CEO caught much of the PSC surge
but overstated ERC by 5 points. With these settings the survey gets about two-thirds of the weight.
The CIS subsample for Canarias names CC 18 times, too few, so CC and Navarre keep the national layer.

**Horizon.** Six weeks of random-walk drift instead of 47, plus the election-day error, re-calibrated
on the new backtest at 13.3 % of each party's share. Mean reversion was tested again and rejected.

**Backtest** (mean over the four elections; 18 September values in brackets): vote MAE 1.03 pp (1.06),
CRPS 0.88 (0.91), 90 % vote coverage 40 % (40 %), seat MAE 4.2 (4.5), 90 % seat coverage 73 % (76 %),
Brier 0.05 (0.06). The regional layer enters only for Catalonia 2023 (the CEO wave of March 2023, the
only one finished 30 days before polling day). It lowered the 2023 seat MAE from 3.4 to 3.0, but its
errors were calibrated on that election, so the gain is in-sample.

**Results.** Sampling converged (0 divergences, R-hat 1.00, 601 polls from 36 pollsters).

At the cut-off:

| party | PP | PSOE | Vox | Frente Amplio | Podemos |
|---|---|---|---|---|---|
| vote | 31.1 % (30.1-32.0) | 26.9 % (26.0-27.9) | 18.8 % | 6.6 % | 3.1 % |

On 29 November:

| party | vote, 90 % | seats, split left | seats, merged left |
|---|---|---|---|
| PP | 24.6-38.2 % | 131 (104-157) | 130 (104-156) |
| PSOE | 21.2-33.6 % | 107 (83-133) | 107 (83-133) |
| Vox | 14.8-23.6 % | 66 (48-87) | 66 (48-87) |
| Frente Amplio | 5.1-8.4 % | 11 (7-20) | 14 (7-23) |
| Podemos | 2.3-4.1 % | 1 (0-2) | merged |
| ERC | | 11 (8-13) | 9 (7-13) |

Probabilities on 29 November:
- PP + Vox (+ UPN, SALF) reach 176: 93 % with the split left, 93 % with the merged left.
- PP is the largest party: 80 %.
- The 2023 investiture bloc reaches 176: 4-5 %.

Seat standard deviation for PP, adding sources one at a time:

| source | posterior at the cut-off | + provincial noise | + six weeks of drift | + election-day error |
|---|---|---|---|---|
| PP seat sd | 3.0 | 4.1 | 5.7 | 15.9 |

Six weeks out, the shared polling error is almost all the uncertainty, which is why the 29 November
intervals are barely narrower than the old August 2027 ones.

**Against 18 September.** At the cut-off PP is 1.3 points lower and PSOE 1.0 higher. ERC rises from 6-9
to 9-12 seats, mostly through the CEO layer. Podemos falls to 0-2 seats under the new supply. These
moves mix four weeks of post-dissolution polls with the new CIS treatment, and the two were not
separated. The bloc arithmetic does not depend on how the left runs: merging moves 2-3 seats from ERC
and Podemos to Frente Amplio and changes no majority.

## 13. Interim run, 14 November 2026 (data to 14 November)

The campaign opened on 13 November. The lists were proclaimed in the BOE on 3 November and the CIS
published its pre-election study on 12 November. Context and sources: `docs/context_29N_2026.md` §8.

**Poll tables as ballots.** Since mid-October the Wikipedia table lists the registered ballots:
Frente Amplio (with its joint lists in Canarias and Baleares), Compromís-Front Valencià, ERC (with
Podemos candidates on its Catalan lists) and Podemos where it runs alone. Twenty-nine of the fifty
polls in that section give one figure for Frente Amplio and Front Valencià in a cell that spans both
columns. The parser now reads column spans; without that, every column to the right of such a cell
was shifted by one. The Sumar series is the sum of the two lists, or the joint figure.

**Level shifts.** Asking about ballots changes what the Podemos, Frente Amplio and ERC figures mean.
Podemos is measured only in the 42 districts where it has a list; its voters in Catalonia, the
Valencian provinces, Canarias and Baleares are counted with ERC, Front Valencià and Frente Amplio.
Each of the three series gets a free level shift in the week of 11 October, the week of the first
such poll. The fitted Podemos series drops from 3.2 % to 1.7 % across that week.

**Seats under the proclaimed lists.** The 17 October run moved assumed parts of Podemos's polled vote
into other lists, including a 50/50 split of its Catalan vote between ERC and Frente Amplio. Those
transfers are gone. Podemos has no share in the ten provinces where it has no ballot, and its polled
share is spread over the other 42 with Sumar's 2023 geography. The Valencian part of the Frente Amplio
space comes from the seven pollsters that list Front Valencià apart: 19 % of the space (median over
pollsters, log sd 0.27), against 13 % under Sumar's 2023 geography. Adelante Andalucía now has a
column in the tables and enters at the median of the last 30 days (1.3 %).

**Trackers count once.** Several series re-publish overlapping samples: the 40dB daily tracking, SW
Demoscopia's cumulative sample since 26 October, rolling windows from Sigma Dos and Electomanía, and
SocioMétrica's panel since 1 September. For each pollster the latest release is kept, then the latest
one that ended before every kept window began. That leaves 583 of the 659 current-cycle polls. The
rule is applied after the backtest's observation cut-off, so each backtest sees only the releases that
existed then; it removes 10-17 % of the polls in the four earlier cycles.

**CIS.** The October barometer (3582) enters with both series. The pre-election study (3584; 45,074
interviews, 7-30 October) has no study page or microdata on cis.es yet, so its official estimate is
read from the PDF, with fieldwork and sample size from the press note, and it has no re-estimate of
ours. Two third-party re-estimates of it are in the tables; the three series share its sample size.
Fitted house effects for the official CIS are -5.1 pp for PP and +4.1 for PSOE. Our re-estimate of
the October barometer is PP 28.4 / PSOE 27.6 / Vox 18.6 (September: 30.6 / 25.7 / 18.3).

**CIS-based series as one pollster.** House effects are centred so that the average pollster has
none. Ten of the 39 series in this cycle are readings of CIS raw data: the official estimate, ours and
eight third-party re-estimates. With one vote each they made up a quarter of that average and leaned
to PSOE. They now form a family that shares one vote per party (`model.house_families`); the family's
position is the mean of its members. The same rule applies in the backtest, where April 2019 has
eight such series. Under one vote per series the cut-off read PP 30.2 / PSOE 27.8; it now reads
PP 30.5 / PSOE 27.6.

**Backtest, refitted** with both rules (17 October values in brackets): vote MAE 1.04 pp (1.03), CRPS
0.89 (0.88), 90 % vote coverage 40 % (40 %), seat MAE 4.2 (4.2), 90 % seat coverage 73 % (73 %), Brier
0.06 (0.05). Neither rule buys accuracy in the backtest. The election-day error that restores 90 %
coverage is 11.5 % of each party's share (13.3 %). Mean reversion was tested again and rejected.

**Results.** Sampling converged (0 divergences, R-hat 1.00, 583 polls from 39 series).

At the cut-off:

| party | PP | PSOE | Vox | Frente Amplio + Front Valencià | Podemos | ERC |
|---|---|---|---|---|---|---|
| vote | 30.5 % (29.9-31.2) | 27.6 % (26.8-28.3) | 19.1 % (18.3-19.8) | 7.0 % | 1.6 % | 2.6 % |

On 29 November:

| party | vote, 90 % | seats, split left | seats, merged left |
|---|---|---|---|
| PP | 25.0-36.6 % | 128 (105-151) | 128 (105-151) |
| PSOE | 22.5-33.2 % | 109 (89-131) | 109 (89-131) |
| Vox | 15.6-23.1 % | 67 (52-85) | 68 (52-85) |
| Frente Amplio + Front Valencià | 5.7-8.6 % | 10 (6-16) | 10 (6-17) |
| Podemos | 1.3-2.1 % | 1 (0-1) | merged |
| ERC | 2.2-3.2 % | 10 (7-13) | 10 (7-13) |

Probabilities on 29 November, split left:
- PP + Vox (+ UPN, SALF) reach 176: 94 % (95 % with the merged left).
- PP is the largest party: 78 %; PSOE: 22 %.
- The 2023 investiture bloc reaches 176: 3 %.

Seat standard deviation for PP, adding sources one at a time:

| source | posterior at the cut-off | + provincial noise | + two weeks of drift | + election-day error |
|---|---|---|---|---|
| PP seat sd | 2.9 | 4.0 | 4.5 | 13.8 |

**Against 17 October.** The 17 October run read PP 31.1 / PSOE 26.9 at its cut-off and this one reads
PP 30.5 / PSOE 27.6, so the published gap went from 4.2 to 2.9 points. Little of that is movement in
the last four weeks: with today's polls and rules the model reads 17 October itself as PP 30.6 /
PSOE 27.4 / Vox 19.4. The rest is a re-reading caused by the new studies and pollsters and by the rule
changes above, which were not separated. PP + Vox stay at 49-50 %, the majority probability is
unchanged (93 % to 94 %) and PP's chance of being the largest party goes from 80 % to 78 %.

**Two caveats on that gap.**
1. Where the average pollster sits is a choice. With the CIS-based series as one pollster the gap is
   2.9 points; with one vote per series it is 2.4. A plain average of recent private polls gives PP a
   lead near five points, because prolific pollsters weigh more in it.
2. The model gives the Frente Amplio space 10 seats where the CIS and most pollsters give 11 to 15 for
   a similar vote. Sumar's 2023 geography outside Valencia probably understates Más Madrid. The seats
   it misses go to larger lists of both blocs.

**Not in this run.** The CIS pre-election microdata, any CEO wave after 5 October, and a demographic
model: the campaign's contest for young voters (§8.5 of the dossier) enters only through the polls
and the election-day error.

## 14. Final run, 23 November 2026 (data to 23 November)

The last day polls may be published before the vote (LOREG art. 69.7). Context: the Sánchez-Feijóo
debate on 19 November and the last week of the campaign (`docs/context_29N_2026.md` §9). No model code
changed since §13, so the backtest, its 11.5 % election-day error and the rejection of mean reversion
carry over unchanged.

**Data.** 78 new releases since 14 November, 737 current-cycle polls listed, 610 used after counting
each tracker once, from 43 series (eleven of them CIS-based, counted as one pollster). Two changes in
the plumbing, neither touching the model:
- the Wikipedia page moved its 2023-24 tables to a sub-page, which is now fetched too
  (`wikipedia.pages.next_2023_2024`); every current-cycle row present on 14 November is still there;
- cis.es published the microdata of the pre-election study 3584 (still without a study page), so
  `cis.direct_studies` takes a `microdata_url` and the study gets our re-estimate. Its ballot labels
  (Frente Amplio and its joint lists in Canarias and Baleares, Compromís-Front Valencià, UPN-PP,
  CC-Municipalistas) were added to `cis_microdata.VOTE_LABELS`. The re-estimate is PSOE 29.4 / PP 27.9
  / Vox 22.0 / FA 4.6 / Front Valencià 1.4 / ERC 2.4 / Podemos 1.1.
No new CEO wave (the open-data file is unchanged since 14 October).

**Sensitivity: without the 3584 re-estimate.** A refit dropping that one series-poll gives the same
latent shares to one decimal on both 14 and 23 November. The CIS family's house effects absorb it; a
45,074-interview study does not dominate the average.

**Results.** Sampling converged (0 divergences, R-hat 1.01, minimum bulk ESS 793).

At the cut-off:

| party | PP | PSOE | Vox | Frente Amplio + Front Valencià | Podemos | ERC |
|---|---|---|---|---|---|---|
| vote | 30.7 % (30.1-31.2) | 29.0 % (28.5-29.6) | 18.5 % (17.9-19.0) | 6.7 % (6.4-7.0) | 1.4 % | 2.6 % |

On 29 November:

| party | vote, 90 % | seats, split left | seats, merged left |
|---|---|---|---|
| PP | 25.1-36.7 % | 127 (105-150) | 127 (105-150) |
| PSOE | 23.7-34.9 % | 114 (93-136) | 114 (93-137) |
| Vox | 15.1-22.3 % | 64 (49-80) | 64 (49-81) |
| Frente Amplio + Front Valencià | 5.4-8.1 % | 9 (6-14) | 9 (5-14) |
| Podemos | 1.1-1.7 % | 0 (0-1) | merged |
| ERC | 2.1-3.1 % | 10 (7-13) | 10 (7-13) |

Probabilities on 29 November, split left:
- PP + Vox (+ UPN, SALF) reach 176: 90 % (90 % with the merged left); expected total 191 seats.
- PP is the largest party: 71 %; PSOE: 29 %.
- The 2023 investiture bloc reaches 176: 6 %.

Seat standard deviation for PP, adding sources one at a time:

| source | posterior at the cut-off | + provincial noise | + six days of drift | + election-day error |
|---|---|---|---|---|
| PP seat sd | 2.7 | 4.1 | 4.3 | 13.8 |

**Against 14 November.** The interim run read PP 30.5 / PSOE 27.6 / Vox 19.1; this one reads PP 30.7 /
PSOE 29.0 / Vox 18.5. The raw polls agree on the direction: the median across pollsters of each one's
latest release went from PP 31.5 / PSOE 26.5 / Vox 18.8 (releases ending 1-13 Nov, 17 pollsters) to
PP 31.4 / PSOE 28.4 / Vox 18.0 (17-22 Nov, 20 pollsters). With all the data the model reads 14 November
itself as PP 30.8 / PSOE 28.6 / Vox 18.4: the aggregator smooths, so later polls revise earlier weeks,
and the new releases re-estimate every house effect. Measured from that re-reading, the last nine days
moved PP -0.1, PSOE +0.4, Vox +0.1. The majority probability fell from 94 % to 90 % and PP's chance
of finishing first from 78 % to 71 %.

**Caveats for reading the result.**
1. The PP lead at the cut-off is 1.7 points in the model, 2.9 in the median of the pollsters' last
   releases. The difference comes from centring house effects on the average pollster: the pollsters
   with a near tie (40dB, Ipsos, Metroscopia, More in Common) or a PSOE lead (SW Demoscopia, Cluster17)
   are a large share of the recent field. "Largest party" depends on this choice; the majority much less.
2. The election-day error dominates. It is set so that the backtest's 90 % intervals would have
   covered 90 % of outcomes, from twenty party-election residuals. In 2023 every pollster
   underestimated PSOE by about 5 points; the model assumes no direction for this year's error.
3. Nothing after 23 November is in the data: the RTVE eight-way debate that evening and the last five
   days of the campaign enter only through that error term.

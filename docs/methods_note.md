# Forecasting the next Spanish general election: a Bayesian poll aggregation and seat projection model

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
and is imputed with the pollster's median. CIS barometers enter through their rows in those tables;
CIS's own catalogue was not scraped because it publishes one Excel/PDF per study.

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

## 6. Results at the cut-off

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

## 8. Projection to the legal deadline

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

## 9. What drives the uncertainty

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

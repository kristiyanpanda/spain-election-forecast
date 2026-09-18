# Model choices (and what they buy or cost)

A short list of the decisions that shape the numbers. Each is a one-line change in code or
`config.yaml`; the point of writing them down is that a reader can disagree with a specific one.

## Aggregator (`src/electoral/model.py`)

| choice | why | cost |
|---|---|---|
| Weekly latent grid, logit-scale random walk per party | keeps shares in (0,1), small parties get proportionally smaller moves; ~165 weeks x 12 parties is cheap to sample | independent walks ignore that shares must sum to one; the seat model renormalises |
| Anchor at the 2023 result (sd 0.05 on the logit scale) | an election is the one poll without house effect; it pins the level | if the electorate moved in the first weeks after the election the walk has to catch up |
| House effects hierarchical per party, centred on the pollsters that publish that party | "the average pollster is unbiased" is the weakest identifying assumption; centring only over publishing pollsters avoids letting non-publishing pollsters absorb small parties' levels (this bug collapsed regional parties in a first version) | if the whole industry is biased in one direction the model is biased by the same amount; the backtest measures this |
| Noise = binomial(n) + party-specific excess variance | sample size matters but rounding, design effects and differing bases add a floor | polls with missing n get their pollster's median (else 1,000) |
| One free level shift for Sumar on 2023-12-08 | Podemos leaving Sumar is a discontinuity, not drift; without it the walk needs a huge innovation sd | the shift date is fixed by hand from the first poll that lists Podemos separately |
| Entrants (Podemos, SALF) start from a diffuse prior at week 0 and are only reported from their first poll | no data before entry | the pre-entry path is meaningless and is masked in outputs |
| NUTS via nutpie (numba) | no C compiler needed on Windows; 4 chains x 1000 draws in about five minutes | one more dependency |
| Wikipedia-only polls; CIS through its rows there | CIS publishes one Excel/PDF per barometer; scraping 100+ layouts was outside budget and gains nothing the Wikipedia rows lack | Wikipedia editors decide what counts as a poll; their harmonisation is documented on each page |

## Seat projection (`src/electoral/seats.py`)

| choice | why | cost |
|---|---|---|
| Proportional swing from 2023 provincial shares | no provincial polls exist for general elections; proportional swing beats uniform swing for small and regional parties | a party growing mostly in one region is mis-allocated |
| Provincial noise: log-normal, sd calibrated on 2019->2023 and Apr->Nov 2019 residuals | the residuals of the same swing rule in the last two transitions are the best available estimate of how wrong it is | the two calibration transitions were unusually different (0.10 vs 0.17 log points); their mean is used |
| Podemos borrows Sumar's 2023 geography; SALF is uniform | Podemos' 2023 votes were inside Sumar; SALF had no 2023 footprint | both are assumptions, and both parties are near the 3 % province threshold where the assumption bites most |
| Untracked lists keep their 2023 share (UPN, CUP, Aliança...) | they are too rarely polled to model | Aliança Catalana could win a seat in Girona or Lleida under some polls; the model cannot see it |
| Renormalise each province to 2023's non-blank total | the twelve tracked parties do not sum to one; the remainder is spread proportionally | mechanical |

## What the intervals mean

The seat distributions answer "if the election were held at the cut-off date": they carry the
posterior uncertainty of the latent shares plus provincial swing noise. They do **not** include
(a) movement between the cut-off and the election, which the deadline projection adds by
extrapolating the random walk, nor (b) a common industry-wide polling error on election day,
which the backtest measures and which is added to the deadline projection only if it improves
calibration (phase F).

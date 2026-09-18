# Output files for downstream use

All files are in `outputs/` and carry a `cutoff_date` column or field. Numbers expire: they
describe the state of opinion up to the cut-off, not the election.

## `poll_average_daily_next.parquet` / `poll_average_daily.csv` (main interface)

One row per (date, party): the posterior of the latent vote share from the aggregator.

| column | meaning |
|---|---|
| `date` | calendar day, from the 2023 election to the cut-off |
| `party` | canonical id: PP, PSOE, VOX, SUMAR, PODEMOS, SALF, ERC, JUNTS, BILDU, PNV, BNG, CC |
| `mean` | posterior mean share (0-1) |
| `q05`, `q25`, `q50`, `q75`, `q95` | posterior quantiles |
| `cutoff_date` | data cut-off |

Daily values are linear interpolations of each posterior draw between weekly model nodes
(the random walk is weekly), so within-week uncertainty is slightly understated.
Rows before a party's first poll (Podemos: Dec 2023, SALF: Jun 2024) are omitted.

Example (pandas):

```python
import pandas as pd
avg = pd.read_parquet("outputs/poll_average_daily_next.parquet")
latest = avg[avg.date == avg.date.max()].set_index("party")["q50"]
```

## `house_effects_next.csv`

Pollster x party house effects in percentage points relative to the average pollster that
publishes that party (`mean_pp`, `q05_pp`, `q95_pp`) and the number of polls.

## `state_draws_next.parquet`

Posterior draws (rows) of the national share vector at the cut-off week (columns = parties).
This is the input to the seat projection and to any scenario analysis.

## `seat_draws_next.parquet`, `seats_summary_next.csv`, `seat_probabilities_next.csv`

Monte Carlo seat simulations (10,000 rows, one column per list including untracked ones such as
UPN), per-party seat quantiles, and event probabilities (bloc majorities, largest party,
thresholds).

## `diagnostics_next.json`, `swing_calibration.json`

Sampler diagnostics (divergences, R-hat, ESS) and the provincial swing noise calibration.

"""Bayesian poll aggregator: a state-space model of latent vote shares.

Specification (per election cycle):

* Time is a weekly grid from the previous election (week 0) to ``end_date``.
* Latent share of party p at week t is ``pi[t, p] = invlogit(theta[t, p])``, where theta follows
  an independent Gaussian random walk per party with party-specific innovation sd ``sigma_rw[p]``
  (non-centred parameterisation). Week 0 is anchored on the previous election result; parties
  that did not exist then (entrants) start from a diffuse prior.
* Optional structural breaks (e.g. Podemos leaving Sumar in Dec 2023) add a one-off free jump to
  the named party's theta from the break week on.
* Observation: poll i for party p reports ``y = pi[t_i, p] + delta[p, h_i] + noise``,
  with house effect ``delta[p, h]`` for pollster h (zero-sum across pollsters per party, hierarchical
  scale), and noise sd ``sqrt(pi(1-pi)/n_i + tau[p]^2)``: binomial sampling variance from the
  sample size plus a party-specific excess variance (design effects, rounding, differing bases).
* Weeks after the last observed poll are pure random-walk extrapolation: this is how the model
  produces a forecast for an election 30 days ahead (backtest) or for the legal deadline.

Everything is on the share scale except the random walk, which lives on the logit scale so that
small parties get proportionally smaller innovations and shares stay in (0, 1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt
from scipy.special import expit, logit


@dataclass
class ModelData:
    parties: list[str]
    pollsters: list[str]
    weeks: pd.DatetimeIndex          # week start dates, len T
    y: np.ndarray                    # observed shares (0-1)
    n: np.ndarray                    # effective sample size
    t_idx: np.ndarray                # week index per observation
    p_idx: np.ndarray                # party index per observation
    h_idx: np.ndarray                # pollster index per observation
    anchor: np.ndarray               # share at week 0 per party (nan for entrants)
    entry_week: np.ndarray           # first week with a poll per party
    breaks: list[tuple[int, int]]    # (party index, week index) one-off jumps
    polls: pd.DataFrame              # poll-level table used (for plotting)


def _impute_n(polls: pd.DataFrame) -> pd.Series:
    med = polls.groupby("pollster")["sample_size"].transform("median")
    return polls["sample_size"].fillna(med).fillna(1000.0).clip(lower=200)


def apply_composites(df: pd.DataFrame, composites: dict | None) -> pd.DataFrame:
    """Build composite party observations, e.g. SUMAR = Sumar (+ Podemos) else UP.

    ``composites`` maps target -> {"sum": [ids summed when any present], "fallback": [ids],
    "fallback_min": k}. The fallback sum is used when no "sum" id is published and at least k
    (default: all) fallback ids are. The target series replaces existing rows for that id.
    """
    if not composites:
        return df
    out = df[~df["party"].isin(composites)].copy()
    wide = df.pivot_table(index="poll_id", columns="party", values="value", aggfunc="first")
    meta = df.drop_duplicates("poll_id").set_index("poll_id")
    new = []
    for target, rule in composites.items():
        summed = [c for c in rule.get("sum", []) if c in wide]
        fb = [c for c in rule.get("fallback", []) if c in wide]
        val = wide[summed].sum(axis=1, min_count=1) if summed else pd.Series(np.nan, index=wide.index)
        if fb:
            k = min(rule.get("fallback_min", len(rule.get("fallback", []))), len(fb))
            val = val.fillna(wide[fb].sum(axis=1, min_count=max(k, 1)))
        rows = meta.loc[val.index].copy()
        rows["party"] = target
        rows["value"] = val.values
        new.append(rows.reset_index())
    return pd.concat([out] + new, ignore_index=True)


def prepare(polls_long: pd.DataFrame, cycle: str, parties: list[str], anchor: dict[str, float],
            start_date: str | pd.Timestamp, end_date: str | pd.Timestamp,
            obs_cutoff: str | pd.Timestamp | None = None, breaks: dict[str, str] | None = None,
            composites: dict | None = None, min_polls_per_pollster: int = 1) -> ModelData:
    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    obs_cutoff = pd.Timestamp(obs_cutoff) if obs_cutoff is not None else end
    df = polls_long[(polls_long["cycle"] == cycle) & (~polls_long["is_election"])].copy()
    df = df[~df["pollster"].str.contains("election", case=False)]      # e.g. "2024 EP election" rows
    df = df[(df["fieldwork_end"] > start) & (df["fieldwork_end"] <= obs_cutoff)]
    df = apply_composites(df, composites)
    df = df[df["party"].isin(parties) & df["value"].notna()].copy()
    counts = df.drop_duplicates("poll_id")["pollster"].value_counts()
    df = df[df["pollster"].map(counts) >= min_polls_per_pollster]

    weeks = pd.date_range(start, end + pd.Timedelta(days=6), freq="7D")
    T = len(weeks)
    df["t"] = ((df["fieldwork_end"] - start).dt.days // 7).clip(0, T - 1).astype(int)
    df["n_eff"] = _impute_n(df)
    pollsters = sorted(df["pollster"].unique())
    p_map = {p: i for i, p in enumerate(parties)}
    h_map = {h: i for i, h in enumerate(pollsters)}

    anchor_arr = np.array([anchor.get(p, np.nan) for p in parties], dtype=float)
    entry = np.array([df.loc[df.party == p, "t"].min() if (df.party == p).any() else 0 for p in parties])
    # a party with an anchor is present from week 0 whatever its first poll
    entry = np.where(np.isnan(anchor_arr), entry, 0)

    br = []
    for p, d in (breaks or {}).items():
        if p in p_map:
            w = int((pd.Timestamp(d) - start).days // 7)
            if 0 < w < T:
                br.append((p_map[p], w))

    return ModelData(
        parties=parties, pollsters=pollsters, weeks=weeks,
        y=(df["value"].values / 100.0).astype(float), n=df["n_eff"].values.astype(float),
        t_idx=df["t"].values, p_idx=df["party"].map(p_map).values, h_idx=df["pollster"].map(h_map).values,
        anchor=anchor_arr, entry_week=entry, breaks=br,
        polls=df.drop_duplicates("poll_id")[["poll_id", "pollster", "fieldwork_end", "n_eff", "t"]].copy(),
    )


def build_model(d: ModelData) -> pm.Model:
    T, P, H = len(d.weeks), len(d.parties), len(d.pollsters)
    anchored = ~np.isnan(d.anchor)
    theta0_mu = np.where(anchored, logit(np.clip(np.nan_to_num(d.anchor, nan=0.02), 1e-4, 1 - 1e-4)),
                         logit(0.03))
    theta0_sd = np.where(anchored, 0.05, 1.5)

    coords = {"week": d.weeks, "party": d.parties, "pollster": d.pollsters, "obs": np.arange(len(d.y))}
    with pm.Model(coords=coords) as m:
        sigma_rw = pm.HalfNormal("sigma_rw", sigma=0.08, dims="party")
        theta0 = pm.Normal("theta0", mu=theta0_mu, sigma=theta0_sd, dims="party")
        z = pm.Normal("z", 0.0, 1.0, shape=(T - 1, P))
        theta = theta0 + pt.concatenate([pt.zeros((1, P)), pt.cumsum(z * sigma_rw, axis=0)], axis=0)
        if d.breaks:
            jumps = pm.Normal("jump", 0.0, 0.7, shape=len(d.breaks))
            for k, (pj, wj) in enumerate(d.breaks):
                step = (np.arange(T) >= wj).astype(float)
                theta = pt.set_subtensor(theta[:, pj], theta[:, pj] + jumps[k] * step)
        pi = pm.Deterministic("pi", pm.math.invlogit(theta), dims=("week", "party"))

        # House effects: hierarchical per party, centred to mean zero across the pollsters that
        # actually publish that party (a plain zero-sum over all pollsters would let pollsters
        # that never report a small party absorb its level through unconstrained effects).
        mask = np.zeros((P, H))
        mask[d.p_idx, d.h_idx] = 1.0
        sigma_house = pm.HalfNormal("sigma_house", sigma=0.02, dims="party")
        delta_raw = pm.Normal("delta_raw", 0.0, 1.0, shape=(P, H))
        delta_scaled = delta_raw * sigma_house[:, None] * mask
        centre = (delta_scaled * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1.0)
        delta = pm.Deterministic("delta", (delta_scaled - centre[:, None]) * mask,
                                 dims=("party", "pollster"))
        tau = pm.HalfNormal("tau", sigma=0.01, dims="party")

        mu = pi[d.t_idx, d.p_idx] + delta[d.p_idx, d.h_idx]
        p_obs = pi[d.t_idx, d.p_idx]
        sd = pt.sqrt(p_obs * (1 - p_obs) / d.n + tau[d.p_idx] ** 2)
        pm.Normal("y", mu=mu, sigma=sd, observed=d.y, dims="obs")
    return m


def fit(d: ModelData, seed: int, draws: int = 1000, tune: int = 1000, chains: int = 4,
        target_accept: float = 0.9, cores: int | None = None,
        sampler: str = "nutpie") -> az.InferenceData:
    """Sample with NUTS. ``sampler="nutpie"`` (Rust NUTS on a numba-compiled logp, no C compiler
    needed on Windows) or ``"pymc"`` (default PyMC sampler)."""
    with build_model(d):
        idata = pm.sample(draws=draws, tune=tune, chains=chains, cores=cores or chains,
                          target_accept=target_accept, random_seed=seed, progressbar=False,
                          nuts_sampler=sampler, idata_kwargs={"log_likelihood": False})
    return idata


# ----------------------------------------------------------------------------- summaries
def diagnostics(idata: az.InferenceData) -> dict:
    ss = idata.sample_stats
    div = int(ss["diverging"].sum()) if "diverging" in ss else 0
    summ = az.summary(idata, var_names=["sigma_rw", "sigma_house", "tau", "theta0"], kind="diagnostics")
    return {"divergences": div, "rhat_max": float(summ["r_hat"].max()),
            "ess_bulk_min": float(summ["ess_bulk"].min()),
            "draws": int(idata.posterior.sizes["draw"] * idata.posterior.sizes["chain"])}


def trend_table(idata: az.InferenceData, d: ModelData, daily: bool = True) -> pd.DataFrame:
    """Posterior summary of latent shares per (date, party); daily by linear interpolation
    of each draw between weekly nodes (ignores within-week bridge variance)."""
    pi = idata.posterior["pi"].stack(sample=("chain", "draw")).transpose("sample", "week", "party").values
    S, T, P = pi.shape
    if daily:
        days = pd.date_range(d.weeks[0], d.weeks[-1], freq="D")
        x_old = np.arange(T) * 7.0
        x_new = (days - d.weeks[0]).days.values.astype(float)
        out = np.empty((S, len(days), P))
        for p in range(P):
            out[:, :, p] = np.array([np.interp(x_new, x_old, pi[s, :, p]) for s in range(S)])
        pi, dates = out, days
    else:
        dates = d.weeks
    q = np.quantile(pi, [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)
    recs = []
    for j, p in enumerate(d.parties):
        first = d.weeks[d.entry_week[j]]
        for i, dt in enumerate(dates):
            if dt < first:
                continue
            recs.append({"date": dt, "party": p, "mean": pi[:, i, j].mean(), "q05": q[0, i, j],
                         "q25": q[1, i, j], "q50": q[2, i, j], "q75": q[3, i, j], "q95": q[4, i, j]})
    return pd.DataFrame(recs)


def house_effects_table(idata: az.InferenceData, d: ModelData) -> pd.DataFrame:
    de = idata.posterior["delta"].stack(sample=("chain", "draw"))
    counts = d.polls["pollster"].value_counts()
    recs = []
    for p in d.parties:
        for h in d.pollsters:
            v = de.sel(party=p, pollster=h).values
            recs.append({"party": p, "pollster": h, "n_polls": int(counts.get(h, 0)),
                         "mean_pp": 100 * v.mean(), "q05_pp": 100 * np.quantile(v, 0.05),
                         "q95_pp": 100 * np.quantile(v, 0.95)})
    return pd.DataFrame(recs)


def state_draws(idata: az.InferenceData, d: ModelData, week: int = -1) -> pd.DataFrame:
    """Posterior draws of the share vector at one week (default: last), one column per party."""
    pi = idata.posterior["pi"].isel(week=week).stack(sample=("chain", "draw")).transpose("sample", "party").values
    return pd.DataFrame(pi, columns=d.parties)


def save_run(idata: az.InferenceData, d: ModelData, out_dir: Path, tag: str, cutoff: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "traces").mkdir(exist_ok=True)
    # nutpie stores nested dict attrs that netCDF cannot serialise
    for group in idata.groups():
        ds = getattr(idata, group)
        ds.attrs = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in ds.attrs.items()}
    idata.attrs = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in idata.attrs.items()}
    idata.to_netcdf(out_dir / "traces" / f"{tag}.nc")
    tr = trend_table(idata, d, daily=True)
    tr = tr[tr.date <= pd.Timestamp(cutoff)]        # the weekly grid may overshoot the cut-off by a few days
    tr["cutoff_date"] = cutoff
    tr.to_parquet(out_dir / f"poll_average_daily_{tag}.parquet", index=False)
    he = house_effects_table(idata, d)
    he.to_csv(out_dir / f"house_effects_{tag}.csv", index=False)
    sd = state_draws(idata, d)
    sd.to_parquet(out_dir / f"state_draws_{tag}.parquet", index=False)
    diag = diagnostics(idata)
    diag.update({"tag": tag, "cutoff_date": cutoff, "n_polls": int(len(d.polls)), "n_obs": int(len(d.y)),
                 "n_pollsters": len(d.pollsters), "weeks": int(len(d.weeks)),
                 "last_poll": str(d.polls.fieldwork_end.max().date())})
    (out_dir / f"diagnostics_{tag}.json").write_text(json.dumps(diag, indent=2))
    return diag

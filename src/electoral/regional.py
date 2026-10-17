"""Regional-poll layer for peripheral parties (dossier docs/context_29N_2026.md §2.2).

National polls under-read parties whose vote is concentrated in one region. This module turns
regional surveys into estimates of a party's *general-election* share in its region, written to
``data/processed/regional_polls.csv``. The seat model then pulls its proportional-swing provincial
shares toward them (:func:`electoral.seats.apply_regional`).

Sources and how each becomes a general-election share:

* **Catalonia - CEO** (Centre d'Estudis d'Opinió, Generalitat de Catalunya; open microdata of the
  face-to-face Baròmetre d'Opinió Política). Congress vote intention (``INT_CONGRES_VOT``),
  post-stratified on recalled 2023 Congress vote to the official Catalan result, as for the CIS
  microdata. Aliança Catalana is not running on 29N: its voters are moved 23 % to Junts and 22 % to
  Vox, the rest abstain (CEO second-preference figures quoted in the dossier).
* **Basque Country - Sociómetro Vasco** (Basque Government). It estimates the Basque Parliament
  vote, not Congress. The ratio of that estimate to the 2024 Basque election result, per territory,
  is applied to the party's 2023 general-election share there (relative swing since the last
  election of each kind). The table is extracted from the PDF into ``data/regional/sociometro.csv``.
* **Galicia and Canarias - CIS regional subsamples.** The CIS microdata of the barometers in the
  pooling window, restricted to the region and re-weighted with the regional 2023 recall
  (:mod:`electoral.cis_microdata`).

Navarre has no regional source used here (the Sociómetro covers only the Basque Autonomous
Community; the CIS subsample is about 600 respondents over six months).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from electoral import cis_microdata as md

CATALONIA = ["08", "17", "25", "43"]

CEO_URL = "https://documents.dadesobertes.gencat.cat/ceo/docs/microdades_anonimitzades_bop_presencial.csv"
CEO_COLS = ["PONDERA", "REO", "BOP_NUM", "DATA_INI", "DATA_FIN", "PROVINCIA", "INT_CONGRES_VOT",
            "INT_CONGRES_VOT_PROB_0_10", "REC_CONGRES_VOT"]
CEO_LABELS = {
    "PSC/PSOE": "PSOE", "ERC": "ERC", "Junts per Catalunya": "JUNTS", "VOX": "VOX", "PP": "PP",
    "Sumar - En Comú Podem": "SUMAR", "En Comú Podem": "SUMAR", "Podemos": "PODEMOS", "CUP": "CUP",
    "Aliança Catalana": "ALIANCA", "En blanc": "BLANK", "Nul": "NULL",
}
CEO_NOT_VALID = {"No ho sap", "No votaria", "No contesta", "No podria votar", "Nul", ""}
CEO_RECALL_SKIP = {"No ho sap", "No contesta", "No va votar", "No podia votar", ""}


# ----------------------------------------------------------------------------- targets
def regional_targets(results_province: pd.DataFrame, province_totals: pd.DataFrame,
                     provinces: list[str], election: str = "202307") -> pd.Series:
    """Official vote shares in a region per recall category (lists, OTHER, BLANK, NULL)."""
    r = results_province[(results_province.election == election) & results_province.prov.isin(provinces)]
    t = province_totals[(province_totals.election == election) & province_totals.prov.isin(provinces)]
    s = r.groupby("party")["votos"].sum()
    s["BLANK"], s["NULL"] = t["votos_blancos"].sum(), t["votos_nulos"].sum()
    return s / s.sum()


def regional_shares(results_province: pd.DataFrame, province_totals: pd.DataFrame,
                    provinces: list[str], election: str = "202307") -> pd.Series:
    """Official % of the valid vote (blank included) per party in a set of provinces."""
    r = results_province[(results_province.election == election) & results_province.prov.isin(provinces)]
    valid = province_totals[(province_totals.election == election)
                            & province_totals.prov.isin(provinces)]["votos_validos"].sum()
    return 100 * r.groupby("party")["votos"].sum() / valid


# ----------------------------------------------------------------------------- CEO
def load_ceo(raw_dir: Path) -> pd.DataFrame:
    """The CEO face-to-face BOP microdata, Congress-vote columns only (cached as parquet)."""
    cache = raw_dir / "bop_presencial_congres.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    src = raw_dir / "microdades_anonimitzades_bop_presencial.csv"
    if not src.exists():
        import requests

        r = requests.get(CEO_URL, headers={"User-Agent": "spain-election-forecast/0.1"}, timeout=300)
        r.raise_for_status()
        raw_dir.mkdir(parents=True, exist_ok=True)
        src.write_bytes(r.content)
    d = pd.read_csv(src, sep=";", encoding="cp1252", usecols=CEO_COLS, dtype=str).fillna("")
    for c in d.columns:
        d[c] = d[c].str.strip()
    d["fieldwork_start"] = pd.to_datetime(d["DATA_INI"], format="%m/%d/%Y", errors="coerce")
    d["fieldwork_end"] = pd.to_datetime(d["DATA_FIN"], format="%m/%d/%Y", errors="coerce")
    d.to_parquet(cache, index=False)
    return d


def ceo_estimate(d: pd.DataFrame, targets: pd.Series, alianca_to: dict[str, float],
                 likely_voter_min: int = 9, recall_labels: dict[str, str] | None = None) -> pd.Series:
    """Congress vote, % of the valid vote in Catalonia, from a set of CEO respondents.

    ``recall_labels`` overrides the recall coding (the CEO harmonises labels across elections, so
    "Sumar - En Comú Podem" recalled in 2023 waves means the Nov 2019 En Comú Podem list).
    """
    rl = {**CEO_LABELS, **(recall_labels or {})}
    w0 = pd.to_numeric(d["PONDERA"].str.replace(",", "."), errors="coerce").fillna(0.0).astype(float)
    rec = d["REC_CONGRES_VOT"].map(lambda s: None if s in CEO_RECALL_SKIP else rl.get(s, "OTHER"))
    rec = rec.where(rec.isna() | rec.isin(targets.index), "OTHER")
    m = rec.notna()
    cur = w0[m].groupby(rec[m]).sum() / w0[m].sum()
    tgt = targets[cur.index] / targets[cur.index].sum()
    w = w0.copy()
    w[m] = w0[m] * rec[m].map(tgt / cur).astype(float)
    w[m] *= w0[m].sum() / w[m].sum()

    vote = d["INT_CONGRES_VOT"]
    ok = ~vote.isin(CEO_NOT_VALID)
    prob = pd.to_numeric(d["INT_CONGRES_VOT_PROB_0_10"].str.extract(r"^(\d+)")[0], errors="coerce")
    if prob[ok].notna().mean() > 0.5:  # the likely-voter question is not asked in every wave
        ok &= prob >= likely_voter_min
    party = vote[ok].map(lambda s: CEO_LABELS.get(s, "OTHER"))
    s = w[ok].groupby(party).sum()
    if "ALIANCA" in s:  # not running on 29N
        ac = s.pop("ALIANCA")
        for p, f in alianca_to.items():
            s[p] = s.get(p, 0.0) + f * ac
    s = s.drop(labels=["NULL"], errors="ignore")
    return 100 * s / s.sum()


# ----------------------------------------------------------------------------- observations
def _obs(region: str, provinces: list[str], shares: pd.Series, parties: list[str], n: float,
         tau: float, source: str, start, end, method: str) -> list[dict]:
    out = []
    for p in parties:
        v = float(shares.get(p, 0.0))
        sd = float(np.sqrt(v * (100 - v) / max(n, 1) + tau ** 2))
        out.append({"region": region, "provinces": " ".join(provinces), "party": p, "share": round(v, 2),
                     "n": int(n), "tau_pp": tau, "sd_pp": round(sd, 2), "source": source,
                     "fieldwork_start": start, "fieldwork_end": end, "method": method})
    return out


def build_regional_polls(cfg: dict, root: Path, res: pd.DataFrame, tot: pd.DataFrame,
                         cis_studies: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """All regional observations at the cut-off (one row per region x party)."""
    rc = cfg["regional"]
    cutoff = pd.Timestamp(cfg["cutoff_date"])
    since = cutoff - pd.DateOffset(months=rc["window_months"])
    rows, notes = [], []

    # Catalonia: CEO
    ceo = load_ceo(root / cfg["paths"]["raw_ceo"])
    ceo = ceo[(ceo["fieldwork_end"] > since) & (ceo["fieldwork_end"] <= cutoff)
              & (ceo["INT_CONGRES_VOT"] != "")]
    waves = sorted(ceo["BOP_NUM"].unique())
    if len(ceo):
        est = ceo_estimate(ceo, regional_targets(res, tot, CATALONIA), rc["ceo"]["alianca_to"])
        rows += _obs("Catalonia", CATALONIA, est, rc["ceo"]["parties"], len(ceo), rc["tau_pp"]["direct"],
                     f"CEO BOP ({', '.join(waves)})", ceo["fieldwork_start"].min(), ceo["fieldwork_end"].max(),
                     "Congress vote, 2023 recall")
    notes.append(f"CEO: {len(waves)} face-to-face barometer waves in the window, {len(ceo)} respondents.")

    # Basque Country: Sociómetro relative swing, per territory
    sv = pd.read_csv(root / "data/regional/sociometro.csv", dtype={"prov": str})
    sv = sv[(pd.to_datetime(sv["fieldwork_end"]) > cutoff - pd.DateOffset(months=rc["sociometro_max_age_months"]))
            & sv["party"].isin(rc["sociometro_parties"])]
    sv = sv[sv["study"] == sv["study"].iloc[-1]] if len(sv) else sv  # latest wave only
    for (prov, terr), g in sv.groupby(["prov", "territory"]):
        gen23 = regional_shares(res, tot, [prov])
        implied = pd.Series({r.party: gen23.get(r.party, 0.0) * r.estimate_pct / r.basque2024_pct
                             for r in g.itertuples()})
        rows += _obs(terr, [prov], implied, list(g["party"]), g["n"].iloc[0], rc["tau_pp"]["cross_election"],
                     f"Sociómetro Vasco {g['study'].iloc[0]}", g["fieldwork_start"].iloc[0],
                     g["fieldwork_end"].iloc[0], "Basque Parliament estimate / 2024 result x 2023 general share")

    # Galicia and Canarias: pooled CIS regional subsamples
    raw_cis = root / cfg["paths"]["raw_cis"]
    studies = cis_studies[(cis_studies["fieldwork_end"] > since) & (cis_studies["fieldwork_end"] <= cutoff)]
    frames = []
    for s in studies["study"]:
        z = raw_cis / str(s) / f"MD{s}.zip"
        if z.exists():
            d = md.load_labelled(z)
            if not md.required_missing(d):
                frames.append(d.assign(_study=str(s)))
    for region, spec in rc["cis_subsamples"].items():
        provs = [str(p).zfill(2) for p in spec["provinces"]]
        sub = [f[f["CCAA"].str.startswith(spec["ccaa_label"])] for f in frames]
        sub = [f for f in sub if len(f)]
        if not sub:
            notes.append(f"{region}: no CIS microdata in the window.")
            continue
        tg = regional_targets(res, tot, provs)
        # re-weight each barometer on its own, then pool weighting by respondents
        ests = [(md.reestimate(f, tg, cfg["cis"]["likely_voter_min"]), len(f)) for f in sub]
        n = sum(k for _, k in ests)
        est = sum(e.reindex(tg.index.union(e.index), fill_value=0.0) * k for e, k in ests) / n
        named = pd.concat(sub)["INTENCIONGR"].str.strip().map(lambda x: md.VOTE_LABELS.get(x, "OTHER"))
        parties = [p for p in spec["parties"] if (named == p).sum() >= rc["min_party_respondents"]]
        for p in sorted(set(spec["parties"]) - set(parties)):
            notes.append(f"{region}: only {(named == p).sum()} CIS respondents name {p}; "
                         "too few, the national layer is kept.")
        rows += _obs(region, provs, est, parties, n, rc["tau_pp"]["direct"],
                     f"CIS microdata, {len(sub)} barometers", studies["fieldwork_start"].min(),
                     studies["fieldwork_end"].max(), "Congress vote, regional 2023 recall")
        notes.append(f"{region}: {n} CIS respondents pooled from {len(sub)} barometers.")
    out = pd.DataFrame(rows)
    out["cutoff_date"] = cfg["cutoff_date"]
    return out, notes


# ----------------------------------------------------------------------------- 2023 check
def check_2023(cfg: dict, root: Path, res: pd.DataFrame, tot: pd.DataFrame,
               details: pd.DataFrame) -> pd.DataFrame:
    """Catalonia in July 2023: CEO pre-election waves vs national polls + proportional swing.

    CEO: the 2023 waves before the election (recall = Nov 2019), re-weighted to the Nov 2019
    Catalan result. Swing: the backtest's national model median 30 days out x the party's 2019
    Catalan / national ratio (Sumar takes the summed geography of UP, Más País and Compromís,
    as in the backtest).
    """
    ceo = load_ceo(root / cfg["paths"]["raw_ceo"])
    ceo = ceo[(ceo["fieldwork_end"] > pd.Timestamp("2022-11-10")) & (ceo["fieldwork_end"] < pd.Timestamp("2023-07-23"))
              & (ceo["INT_CONGRES_VOT"] != "")].copy()
    tg = regional_targets(res, tot, CATALONIA, "201911")
    est = ceo_estimate(ceo, tg, {}, recall_labels={"Sumar - En Comú Podem": "UP", "C's": "CS",
                                                   "Ciutadans/Ciudadanos": "CS"})
    actual = regional_shares(res, tot, CATALONIA, "202307")
    cat19 = regional_shares(res, tot, CATALONIA, "201911")
    nat19 = res[res.election == "201911"].groupby("party")["votos"].sum() / \
        tot[tot.election == "201911"]["votos_validos"].sum() * 100
    nat_pred = details[details.cycle == "e2023"].set_index("party")["model_q50"]
    absorb = {"SUMAR": ["UP", "MASPAIS", "COMPROMIS"]}
    rows = []
    for p in cfg["regional"]["ceo"]["parties"]:
        src = absorb.get(p, [p])
        ratio = sum(cat19.get(q, 0.0) for q in src) / sum(nat19.get(q, 0.0) for q in src)
        rows.append({"party": p, "actual_2023": round(actual.get(p, 0.0), 1),
                     "ceo_feb_jun_2023": round(est.get(p, 0.0), 1),
                     "national_swing": round(nat_pred.get(p, float("nan")) * ratio, 1)})
    out = pd.DataFrame(rows)
    out["ceo_error"] = (out.ceo_feb_jun_2023 - out.actual_2023).round(1)
    out["swing_error"] = (out.national_swing - out.actual_2023).round(1)
    out["ceo_waves"] = ", ".join(sorted(ceo["BOP_NUM"].unique()))
    return out


def ceo_observations(cfg: dict, root: Path, res: pd.DataFrame, tot: pd.DataFrame, start, end,
                     base_election: str, recall_labels: dict[str, str] | None = None) -> list[dict]:
    """CEO Catalonia observations for the seat model from waves ending in (start, end].

    Used by the backtest: only waves finished before its observation cut-off, recall re-weighted to
    the previous election (``base_election``).
    """
    ceo = load_ceo(root / cfg["paths"]["raw_ceo"])
    ceo = ceo[(ceo["fieldwork_end"] > pd.Timestamp(start)) & (ceo["fieldwork_end"] <= pd.Timestamp(end))
              & (ceo["INT_CONGRES_VOT"] != "")]
    if ceo.empty:
        return []
    rc = cfg["regional"]
    est = ceo_estimate(ceo, regional_targets(res, tot, CATALONIA, base_election), {},
                       recall_labels=recall_labels)
    obs = _obs("Catalonia", CATALONIA, est, rc["ceo"]["parties"], len(ceo), rc["tau_pp"]["direct"],
               "CEO", ceo["fieldwork_start"].min(), ceo["fieldwork_end"].max(), "backtest")
    return [{"provinces": CATALONIA, "party": o["party"], "share": o["share"], "sd": o["sd_pp"]} for o in obs]

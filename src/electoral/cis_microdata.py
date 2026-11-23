"""Our re-estimate of CIS barometers from the open microdata (series "CIS (microdata, re-weighted)").

Method (dossier docs/context_29N_2026.md §2.1; reproduces study 3577 at PP 30.7 / PSOE 25.7):

1. start from CIS's own weight ``PESO``;
2. post-stratify on recalled 2023 vote (``RECUERDO``) so that, among respondents who recall a
   list, blank or null vote, the weighted recall matches the official 2023 result. Non-voters,
   the too-young and refusals keep their weight (abstention is not a target: recalled turnout is
   known to be inflated and the likely-voter filter handles it);
3. keep likely voters: ``PROBVOTO`` >= ``cis.likely_voter_min`` (9 on the 0-10 scale);
4. vote intention ``INTENCIONGR`` as % of the valid vote (lists + blank), leaving out
   undecided, would-not-vote, null and no answer.

The CIS publishes these microdata openly (CC BY 4.0); the official estimate is a different
model (Alaminos-Tezanos) and enters the aggregator as its own series.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from electoral.cis import MES_NUM

# INTENCIONGR / RECUERDO labels -> canonical party id (data/party_map_polls.yaml)
VOTE_LABELS = {
    "PSOE": "PSOE", "PP": "PP", "VOX": "VOX", "Sumar": "SUMAR", "SUMAR": "SUMAR",
    "Podemos": "PODEMOS", "Se Acabó la Fiesta": "SALF", "ERC": "ERC", "Junts": "JUNTS",
    "EH Bildu": "BILDU", "EAJ-PNV": "PNV", "BNG": "BNG", "CCa": "CC", "UPN": "UPN",
    "Adelante Andalucía": "AA", "PACMA": "PACMA", "CUP": "CUP", "Aliança Catalana": "ALIANCA",
    "En blanco": "BLANK", "Voto nulo": "NULL", "Nulo": "NULL",
    # ballots as registered for 29 Nov 2026 (pre-election study 3584): Frente Amplio and its joint
    # lists in Canarias (UPC) and Baleares (Ara Més) are FA, as in the poll tables; PP runs with UPN
    # in Navarra
    "Frente Amplio (CHA-FA en Aragón y Comuns-FA en Cataluña)": "FA", "Frente Amplio": "FA",
    "UPC (Unidad del Pueblo Canario)": "FA", "Ara Més-Front Ampli": "FA",
    "Compromís: Front Valencià": "FV", "UPN-PP": "PP",
    "Coalición Canaria-Municipalistas Primero Canarias": "CC", "Se Acabó La Fiesta": "SALF",
}
NOT_VALID = {"No sabe todavía", "No votaría", "N.C.", "N.S.", "Voto nulo", "Nulo", "Ninguno",
             "No votará", "No sabe", "No contesta"}
RECALL_SKIP = {"No votó", "N.C.", "N.R.", "No tenía edad", "No tenía derecho a voto",
               "No recuerda", "N.S."}


# ----------------------------------------------------------------------------- loading
def _csv_member(zf: zipfile.ZipFile, suffix: str) -> io.BytesIO | None:
    """Open ``<n>_<suffix>.csv`` directly or inside the nested ``<n>_csv.zip`` (2024 studies)."""
    for name in zf.namelist():
        if name.lower().endswith(f"_{suffix}.csv"):
            return io.BytesIO(zf.read(name))
    for name in zf.namelist():
        if name.lower().endswith("_csv.zip"):
            return _csv_member(zipfile.ZipFile(io.BytesIO(zf.read(name))), suffix)
    return None


def _code(header: str) -> str:
    """'PESO: Ponderación ...' or 'PESO Ponderación ...' -> 'PESO'."""
    return re.split(r"[:\s]", header.strip().lstrip("\ufeff"), maxsplit=1)[0]


def load_labelled(zip_path: Path) -> pd.DataFrame:
    """Labelled microdata (``*_etiq.csv``) with columns renamed to their variable codes.

    The variable descriptions are kept in ``df.attrs["labels"]`` (code -> description).
    """
    zf = zipfile.ZipFile(zip_path)
    buf = _csv_member(zf, "etiq")
    if buf is None:
        raise FileNotFoundError(f"no *_etiq.csv in {zip_path.name}")
    text = buf.read().decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    codes = [_code(h) for h in rows[0]]
    df = pd.DataFrame(rows[1:], columns=codes)
    df = df.loc[:, ~df.columns.duplicated()]
    df.attrs["labels"] = {c: h.strip().lstrip("\ufeff")[len(c):].lstrip(": ")
                         for c, h in zip(codes, rows[0])}
    return df


def recall_variable(df: pd.DataFrame) -> str | None:
    """Turnout + recalled vote in the 2023 general election: RECUERDO (RECUERDO1 in study 3420,
    where RECUERDO is the 2019 recall)."""
    labels = df.attrs.get("labels", {})
    for c in df.columns:
        if re.fullmatch(r"RECUERDO\d*", c) and "2023" in labels.get(c, ""):
            return c
    return None


def weight_variable(df: pd.DataFrame) -> str | None:
    """CIS's weight: PESO; PESOCCAA where PESO is absent (study 3528)."""
    return next((c for c in ("PESO", "PESOCCAA") if c in df.columns), None)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(".", "", regex=False)
                         .str.replace(",", ".", regex=False), errors="coerce")


def fieldwork(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """First and last interview day from the paradata (IA_E1_DIA/MES/ANYO), when present."""
    if not {"IA_E1_DIA", "IA_E1_MES", "IA_E1_ANYO"} <= set(df.columns):
        return pd.NaT, pd.NaT
    month = df["IA_E1_MES"].str.strip().str.lower().map(MES_NUM)
    month = month.fillna(_num(df["IA_E1_MES"]))
    d = pd.to_datetime(pd.DataFrame({"year": _num(df["IA_E1_ANYO"]), "month": month,
                                     "day": _num(df["IA_E1_DIA"])}), errors="coerce").dropna()
    return (d.min(), d.max()) if len(d) else (pd.NaT, pd.NaT)


# ----------------------------------------------------------------------------- re-weighting
def recall_targets(results_national: pd.DataFrame, province_totals: pd.DataFrame,
                   election: str = "202307") -> pd.Series:
    """Official 2023 votes per recall category (lists, OTHER, BLANK, NULL), as shares."""
    nat = results_national[results_national["election"] == election].groupby("party")["votos"].sum()
    tot = province_totals[province_totals["election"] == election]
    t = nat.copy()
    t["BLANK"] = tot["votos_blancos"].sum()
    t["NULL"] = tot["votos_nulos"].sum()
    return t / t.sum()


def reestimate(df: pd.DataFrame, targets: pd.Series, likely_voter_min: int = 9) -> pd.Series:
    """Vote intention, % of valid vote, per canonical party (BLANK and OTHER included)."""
    w0 = _num(df[weight_variable(df)]).fillna(0.0).astype(float)
    recall = df[recall_variable(df)].str.strip()
    rec = recall.map(lambda s: VOTE_LABELS.get(s, None if s in RECALL_SKIP else "OTHER"))
    rec = rec.where(rec.isna() | rec.isin(targets.index), "OTHER")  # e.g. PACMA counts as OTHER
    m = rec.notna()
    cur = w0[m].groupby(rec[m]).sum()
    cur = cur / cur.sum()
    tgt = targets[cur.index] / targets[cur.index].sum()
    w = w0.copy()
    w[m] = w0[m] * rec[m].map(tgt / cur).astype(float)
    w[m] *= w0[m].sum() / w[m].sum()  # the recall group keeps its weight mass

    prob = pd.to_numeric(df["PROBVOTO"].str.extract(r"^(\d+)")[0], errors="coerce")
    vote = df["INTENCIONGR"].str.strip()
    ok = (prob >= likely_voter_min) & ~vote.isin(NOT_VALID) & (vote != "")
    party = vote[ok].map(lambda s: VOTE_LABELS.get(s, "OTHER"))
    s = w[ok].groupby(party).sum()
    s = s.drop(labels=["NULL"], errors="ignore")
    return 100 * s / s.sum()


def raw_shares(df: pd.DataFrame) -> pd.Series:
    """Unadjusted intention with PESO only, % of valid vote (for diagnostics)."""
    w0 = _num(df[weight_variable(df)]).fillna(0.0)
    vote = df["INTENCIONGR"].str.strip()
    ok = ~vote.isin(NOT_VALID) & (vote != "")
    s = w0[ok].groupby(vote[ok].map(lambda x: VOTE_LABELS.get(x, "OTHER"))).sum()
    return 100 * s / s.sum()


def required_missing(df: pd.DataFrame) -> list[str]:
    miss = [c for c in ("PROBVOTO", "INTENCIONGR") if c not in df.columns]
    if weight_variable(df) is None:
        miss.append("PESO")
    if recall_variable(df) is None:
        miss.append("RECUERDO (2023)")
    return miss


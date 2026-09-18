"""Download and parse official Congreso results from the Ministerio del Interior.

Source: https://infoelectoral.interior.gob.es (Área de descargas, ficheros "TOTA").
Reuse: Ley 37/2007 / RD 1495/2011. Attribution: "Origen de los datos: Ministerio del Interior".

Each ZIP ``02YYYYMM_TOTA.zip`` holds fixed-width, latin-1 DAT files. The record layouts
below are transcribed from the Ministry's ``FICHEROS.doc`` shipped inside every ZIP:

* ``03`` candidaturas  (232 chars): election id, candidatura code, siglas, name, heads
* ``07`` datos comunes (172 chars): census, turnout, blank/null votes per ámbito
* ``08`` candidaturas por ámbito (33 chars): votes and seats per candidatura per ámbito

Ámbito key: (ccaa, provincia, distrito). Province ``99`` = national total,
distrito ``9`` = whole province.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

USER_AGENT = "spain-election-forecast/0.1 (research; github portfolio)"

# (field name, width). Order matters.
LAYOUT_03 = [
    ("tipo", 2), ("anio", 4), ("mes", 2), ("cand_code", 6), ("siglas", 50),
    ("nombre", 150), ("head_prov", 6), ("head_ccaa", 6), ("head_nac", 6),
]
LAYOUT_07 = [
    ("tipo", 2), ("anio", 4), ("mes", 2), ("vuelta", 1), ("ccaa", 2), ("prov", 2),
    ("distrito", 1), ("ambito_nombre", 50), ("poblacion", 8), ("mesas", 5),
    ("censo_ine", 8), ("censo_escrutinio", 8), ("censo_cere", 8), ("votantes_cere", 8),
    ("avance1", 8), ("avance2", 8), ("votos_blancos", 8), ("votos_nulos", 8),
    ("votos_candidaturas", 8), ("escanos", 6), ("votos_si", 8), ("votos_no", 8),
    ("oficial", 1),
]
LAYOUT_08 = [
    ("tipo", 2), ("anio", 4), ("mes", 2), ("vuelta", 1), ("ccaa", 2), ("prov", 2),
    ("distrito", 1), ("cand_code", 6), ("votos", 8), ("escanos", 5),
]


def zip_url(base_url: str, election: str) -> str:
    return f"{base_url}/02{election}_TOTA.zip"


def download(election: str, base_url: str, dest: Path, force: bool = False) -> Path:
    """Download one election ZIP (about 150 KB) unless it is already cached."""
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"02{election}_TOTA.zip"
    if out.exists() and not force:
        return out
    r = requests.get(zip_url(base_url, election), timeout=120, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    if r.headers.get("content-type", "").split(";")[0] != "application/zip":
        raise RuntimeError(f"Unexpected content-type for {election}: {r.headers.get('content-type')}")
    out.write_bytes(r.content)
    return out


def _read_fixed(raw: bytes, layout: list[tuple[str, int]]) -> pd.DataFrame:
    width = sum(w for _, w in layout)
    text = raw.decode("latin-1")
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if len(line) < width:
            line = line.ljust(width)
        pos, rec = 0, {}
        for name, w in layout:
            rec[name] = line[pos:pos + w].strip()
            pos += w
        rows.append(rec)
    return pd.DataFrame(rows)


def parse_zip(path: Path) -> dict[str, pd.DataFrame]:
    """Return the three tables of one ZIP as DataFrames with typed numeric columns."""
    with zipfile.ZipFile(path) as z:
        names = {n[:2]: n for n in z.namelist() if n.upper().endswith(".DAT")}
        cand = _read_fixed(z.read(names["03"]), LAYOUT_03)
        common = _read_fixed(z.read(names["07"]), LAYOUT_07)
        votes = _read_fixed(z.read(names["08"]), LAYOUT_08)
    for col in ("poblacion", "mesas", "censo_ine", "censo_escrutinio", "censo_cere",
                "votantes_cere", "avance1", "avance2", "votos_blancos", "votos_nulos",
                "votos_candidaturas", "escanos"):
        common[col] = pd.to_numeric(common[col], errors="coerce").fillna(0).astype("int64")
    for col in ("votos", "escanos"):
        votes[col] = pd.to_numeric(votes[col], errors="coerce").fillna(0).astype("int64")
    return {"candidaturas": cand, "common": common, "votes": votes}


def tidy_election(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build (results_by_province, province_totals) for one election.

    results_by_province: one row per (election, prov, candidatura) with votes, seats,
    siglas and the *national* head candidatura code (used to merge provincial
    variants of the same national list, e.g. PSC -> PSOE).
    province_totals: one row per province with census, valid votes, turnout, seats.
    """
    t = parse_zip(path)
    cand, common, votes = t["candidaturas"], t["common"], t["votes"]
    election = cand["anio"].iloc[0] + cand["mes"].iloc[0]
    date = pd.Timestamp(f"{cand['anio'].iloc[0]}-{cand['mes'].iloc[0]}-01")

    prov_votes = votes[(votes["prov"] != "99") & (votes["distrito"] == "9")].copy()
    prov_votes = prov_votes.merge(
        cand[["cand_code", "siglas", "nombre", "head_nac"]], on="cand_code", how="left"
    )
    prov_votes["election"] = election
    prov_votes["election_month"] = date

    totals = common[(common["prov"] != "99") & (common["distrito"] == "9")].copy()
    totals["election"] = election
    totals["election_month"] = date
    totals["votos_validos"] = totals["votos_blancos"] + totals["votos_candidaturas"]
    totals["votantes"] = totals["votos_validos"] + totals["votos_nulos"]
    totals["turnout"] = totals["votantes"] / totals["censo_escrutinio"]

    cols_v = ["election", "election_month", "ccaa", "prov", "cand_code", "head_nac",
              "siglas", "nombre", "votos", "escanos"]
    cols_t = ["election", "election_month", "ccaa", "prov", "ambito_nombre", "censo_escrutinio",
              "votantes", "votos_validos", "votos_blancos", "votos_nulos",
              "votos_candidaturas", "escanos", "turnout"]
    return prov_votes[cols_v], totals[cols_t]


def build_all(elections: list[str], base_url: str, raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    res, tot = [], []
    for e in elections:
        p = download(e, base_url, raw_dir)
        r, t = tidy_election(p)
        res.append(r)
        tot.append(t)
    results = pd.concat(res, ignore_index=True)
    totals = pd.concat(tot, ignore_index=True)
    return results, totals

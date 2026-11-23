"""Official CIS vote estimates and microdata, straight from cis.es.

Source: Centro de Investigaciones Sociológicas (https://www.cis.es), licence CC BY 4.0.
*Fuente de los datos: Centro de Investigaciones Sociológicas.*

Each study page carries schema.org JSON-LD listing its files ("Estimación de voto" PDF,
"Ficha técnica" PDF, "Fichero datos" microdata zip). Barometer pages are found by slug
(``barometro-de-<mes>-<año>``); other studies with a general-election estimate
(pre-electoral macro-barometers, flash surveys) are listed in ``config.yaml``. A study whose
page is not up yet but whose estimate PDF is (``cis.direct_studies``: the Oct 2026 pre-election
survey) is read from that PDF, with fieldwork and sample size taken from the config.

Two series come out of this module:

* ``CIS`` - the official estimate published by CIS (all cycles, enters the backtest);
* ``CIS (microdata, re-weighted)`` - our re-estimate of the same survey from the microdata
  (current cycle only, not backtested); see :mod:`electoral.cis_microdata`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import requests
import yaml

USER_AGENT = "spain-election-forecast/0.1 (research; github portfolio)"
BASE = "https://www.cis.es/es/estudios/"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MES_NUM = {m: i for i, m in enumerate(MESES, 1)}
NOV_2019 = pd.Timestamp("2019-11-10")
UP_PACT = pd.Timestamp("2016-05-09")  # Podemos-IU pact: Unidos Podemos from the June 2016 election


# ----------------------------------------------------------------------------- catalogue
def barometer_slugs(first_month: str, last: pd.Timestamp) -> list[str]:
    months = pd.period_range(pd.Period(first_month, "M"), last.to_period("M"), freq="M")
    return [f"barometro-de-{MESES[p.month - 1]}-{p.year}" for p in months]


def _get(url: str, timeout: int = 60) -> requests.Response:
    return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)


def study_page(slug: str, cache_dir: Path, force: bool = False,
               recheck_missing: bool = False) -> dict | None:
    """Study metadata from the page's JSON-LD; None when the page does not exist.

    A page cached as missing is asked for again when ``recheck_missing`` (recent barometers: the
    page of the month in course appears a few days after the cut-off of an earlier run).
    """
    cache = cache_dir / f"{slug}.json"
    if cache.exists() and not force:
        meta = json.loads(cache.read_text(encoding="utf-8"))
        if meta or not recheck_missing:
            return meta or None
    r = _get(BASE + slug)
    meta: dict = {}
    if r.status_code == 200:
        graph = []
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S):
            j = json.loads(block)
            graph += j.get("@graph", [j])
        rep = next((g for g in graph if g.get("@type") == "Report"), {})
        ds = next((g for g in graph if g.get("@type") == "Dataset"), {})
        meta = {"slug": slug, "study": rep.get("identifier") or ds.get("identifier"),
                "title": rep.get("name"), "published": rep.get("datePublished"),
                "files": {d["name"]: d["contentUrl"] for d in ds.get("distribution", [])}}
    elif r.status_code != 404:
        r.raise_for_status()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta or None


def _file(files: dict, *prefixes: str) -> str | None:
    for name, url in files.items():
        if any(name.lower().startswith(p) for p in prefixes):
            return url
    return None


def catalogue(cfg: dict, raw_dir: Path, force: bool = False) -> tuple[pd.DataFrame, list[str]]:
    """One row per study page found; also returns the slugs that do not exist."""
    cutoff = pd.Timestamp(cfg["cutoff_date"])
    barometers = barometer_slugs(cfg["cis"]["first_month"], cutoff)
    slugs = barometers + list(cfg["cis"]["extra_studies"])
    recent = set(barometers[-3:])
    rows, missing = [], []
    for slug in slugs:
        meta = study_page(slug, raw_dir / "pages", force=force, recheck_missing=slug in recent)
        if meta is None:
            missing.append(slug)
            continue
        f = meta["files"]
        rows.append({"slug": slug, "study": meta["study"], "title": meta["title"],
                     "published": pd.Timestamp(meta["published"]) if meta["published"] else pd.NaT,
                     "estimate_url": _file(f, "estimación", "estimacion"),
                     "ficha_url": _file(f, "ficha"), "microdata_url": _file(f, "fichero datos")})
    seen = {str(r["study"]) for r in rows}
    for d in cfg["cis"].get("direct_studies") or []:
        if str(d["study"]) in seen or pd.Timestamp(d["published"]) > cutoff:
            continue  # its study page has been catalogued, or it came out after the cut-off
        rows.append({"slug": None, "study": str(d["study"]), "title": d["title"],
                     "published": pd.Timestamp(d["published"]), "estimate_url": d["estimate_url"],
                     "ficha_url": d.get("ficha_url"), "microdata_url": d.get("microdata_url")})
    return pd.DataFrame(rows), missing


def download(url: str, dest: Path, force: bool = False) -> Path:
    if dest.exists() and not force:
        return dest
    r = _get(url, timeout=120)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    return "\n".join(p.extract_text(extraction_mode="layout") for p in PdfReader(path).pages)


# ----------------------------------------------------------------------------- ficha técnica
def _num_es(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def parse_fieldwork_es(text: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """'Fecha de realización: Del 28 de febrero al 7 de marzo de 2025.' -> (2025-02-28, 2025-03-07)."""
    m = re.search(r"Fecha de realizaci[oó]n\s*:(.{0,160})", text, re.S | re.I)
    if not m:
        return pd.NaT, pd.NaT
    s = " ".join(m.group(1).split()).lower()
    rng = re.search(r"del (\d{1,2})(?: de)?(?: ([a-z]+))?(?: de (\d{4}))? al (\d{1,2}) de ([a-z]+) de (\d{4})", s)
    if rng:
        d1, m1, y1, d2, m2, y2 = rng.groups()
        end = pd.Timestamp(int(y2), MES_NUM[m2], int(d2))
        mon1 = MES_NUM[m1] if m1 else end.month
        yr1 = int(y1) if y1 else (end.year - 1 if mon1 > end.month else end.year)
        return pd.Timestamp(yr1, mon1, int(d1)), end
    one = re.search(r"(\d{1,2}) de ([a-z]+) de (\d{4})", s)
    if one:
        d = pd.Timestamp(int(one.group(3)), MES_NUM[one.group(2)], int(one.group(1)))
        return d, d
    return pd.NaT, pd.NaT


def parse_sample(text: str) -> float:
    m = re.search(r"Realizada\s*:\s*([\d.]+)\s*entrevistas", text, re.I)
    return _num_es(m.group(1)) if m else float("nan")


# ----------------------------------------------------------------------------- estimate table
_SEATS = re.compile(r"\b\d{1,3}\s*[–-]\s*\d{1,3}\b(?!,)")       # seat ranges such as 122 – 140
_TOKEN = re.compile(r"^(±?\d+(?:,\d+)?%?\**|--|–|-)$")
_END = re.compile(r"^(voto nulo|abstenci|\(?[“\"]?no votar|no sabe|no lo tiene|no contesta)", re.I)


_FOOTNOTE = re.compile(r"\s*(\(\d\)|\*+)$")


def _clean_label(label: str) -> str:
    """'PSOE (2)' -> 'PSOE'; 'SUMAR**' -> 'SUMAR'; 'Unidos Podemos(3)' -> 'Unidos Podemos'."""
    while _FOOTNOTE.search(label):
        label = _FOOTNOTE.sub("", label)
    return label.strip()


def _split_row(line: str) -> tuple[str, list[tuple[str, int]]] | None:
    """'  PP   25,4  ±1,0  31,4  122 – 140' -> ('PP', [('25,4', col), ('31,4', col)]).

    Values come with the column where they end, margins (±) and seat ranges are dropped.
    """
    clean = _SEATS.sub(lambda m: " " * len(m.group()), line)
    toks = [(m.group(), m.end()) for m in re.finditer(r"\S+", clean)]
    i = len(toks)
    while i > 0 and _TOKEN.match(toks[i - 1][0]):
        i -= 1
    if i == 0 or i == len(toks):
        return None
    vals = [(t, e) for t, e in toks[i:] if not t.startswith("±") and t not in ("–", "-")]
    return " ".join(t for t, _ in toks[:i]), vals


def _open(fragment: str) -> bool:
    """A label fragment continued on the next line: 'SUMAR (IU, Compromís, En'."""
    return fragment.count("(") > fragment.count(")") or fragment.endswith((",", "-"))


def parse_estimate(text: str) -> list[tuple[str, float]]:
    """Official CIS estimate (% of valid vote) per table row, from an 'Estimación de voto' PDF.

    The table lists direct vote, sometimes a margin (±) or a second direct-vote column, then the
    estimate, sometimes followed by seats. The estimate is the last share column of the PSOE row;
    rows with fewer values (a label wrapped over two lines) take the value printed in that column.
    Rows are returned as printed (sub-rows such as confluences included); the table ends at
    'Voto nulo'.
    """
    general = re.search(r"ESTIMACI[ÓO]N DE VOTO ELECCIONES GENERALES", text)
    if general:  # macro-surveys for local elections print the municipal table first (3382)
        text = text[general.start():]
    lines = text.splitlines()
    rows = [_split_row(ln) for ln in lines]
    psoe = next((i for i, r in enumerate(rows)
                 if r and _clean_label(r[0]) == "PSOE" and any("," in t for t, _ in r[1])), None)
    if psoe is None:
        return []
    k = len(rows[psoe][1])
    est_col = rows[psoe][1][-1][1]
    start = psoe  # the table starts at the first of the consecutive rows that end at PSOE
    while start > 0 and (rows[start - 1] is not None or not lines[start - 1].strip()):
        start -= 1
    out: list[tuple[str, float]] = []
    prev_text = ""
    for line, row in zip(lines[start:], rows[start:]):
        if row is None:
            frag = line.strip()
            if frag:
                joins = prev_text and (frag.startswith("(") or _open(prev_text))
                prev_text = f"{prev_text} {frag}" if joins else frag
            continue
        label, vals = row
        if _END.match(label):
            break
        label = _clean_label(label)
        if prev_text and (label.startswith("(") or _open(prev_text)):
            label = f"{prev_text} {label}"
        prev_text = ""
        if len(vals) >= k:
            v = vals[k - 1][0]
        else:
            near = [t for t, e in vals if abs(e - est_col) <= 4]
            if not near:
                continue  # the direct-vote half of a wrapped row
            v = near[0]
        v = v.rstrip("%*")
        out.append((label, 0.0 if v == "--" else _num_es(v)))
    return out


# ----------------------------------------------------------------------------- party mapping
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\s\-–]", "", s.lower())


def load_rules(path: Path) -> list[tuple[str, str]]:
    return [(_norm(p), party) for p, party in yaml.safe_load(path.read_text(encoding="utf-8"))["rules"]]


def map_parties(rows: list[tuple[str, float]], rules: list[tuple[str, str]],
                fieldwork_end: pd.Timestamp) -> dict[str, float]:
    """Sum table rows into canonical parties (OTHER and BLANK kept for the sum check)."""
    mapped = []
    for label, v in rows:
        party = next((p for pre, p in rules if _norm(label).startswith(pre)), None)
        if party is None:
            raise ValueError(f"Unmapped CIS label {label!r}: add it to data/party_map_cis.yaml")
        if _norm(label).startswith("enmarea") and fieldwork_end.year >= 2019:
            party = "OTHER"  # ran alone in 2019
        if party == "COMPROMIS":
            if fieldwork_end.year < 2019:
                party = "CONFLUENCE"  # Compromís-Podemos (2015-2016 coalition)
            elif fieldwork_end > NOV_2019:
                party = "MASPAIS"  # Más País-Compromís joint list (Nov 2019), as in the Wikipedia feed
        mapped.append((party, v))
    has_sumar = any(p in ("SUMAR", "FA") for p, _ in mapped)   # Sumar or its successor list
    up_era = fieldwork_end >= UP_PACT and not has_sumar
    out: dict[str, float] = {}
    for p, v in mapped:
        if up_era and p in ("PODEMOS", "IU", "CONFLUENCE"):
            p = "UP"
        elif not up_era and p in ("UP", "CONFLUENCE"):
            p = "PODEMOS"
        out[p] = round(out.get(p, 0.0) + v, 2)
    return out


# ----------------------------------------------------------------------------- series
def _study_fieldwork(study: str, ft_text: str | None, md_dates: tuple | None,
                     overrides: dict) -> tuple[pd.Timestamp, pd.Timestamp, str]:
    if study in overrides:
        a, b = overrides[study]
        return pd.Timestamp(a), pd.Timestamp(b), "config override"
    if md_dates and pd.notna(md_dates[0]):
        return md_dates[0], md_dates[1], "microdata interview dates"
    a, b = parse_fieldwork_es(ft_text or "")
    return a, b, "ficha técnica"


def build_series(cfg: dict, root: Path, targets: pd.Series | None) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Official CIS estimates (all cycles) and our microdata re-estimates (current cycle).

    Returns (long rows: one per study x series x party, per-study table, notes).
    """
    from electoral import cis_microdata as md

    raw = root / cfg["paths"]["raw_cis"]
    ccfg = cfg["cis"]
    overrides = {str(k): v for k, v in (ccfg.get("fieldwork_overrides") or {}).items()}
    direct = {str(d["study"]): d for d in ccfg.get("direct_studies") or []}
    overrides.update({k: d["fieldwork"] for k, d in direct.items() if k not in overrides})
    rules = load_rules(root / "data/party_map_cis.yaml")
    cat, missing = catalogue(cfg, raw)
    notes = [f"cis.es pages not found (no such study): {', '.join(missing)}."]
    md_from = pd.Timestamp(ccfg["microdata_from"])
    recs, table, problems = [], [], []
    for r in cat.itertuples():
        if not r.estimate_url:
            continue  # quarterly-estimate era: barometer without an estimate
        est_pdf = download(r.estimate_url, raw / r.study / f"estimacion_{r.study}.pdf")
        ft_text = pdf_text(download(r.ficha_url, raw / r.study / f"FT{r.study}.pdf")) if r.ficha_url else None
        try:
            rows = parse_estimate(pdf_text(est_pdf))
        except Exception as e:  # noqa: BLE001 - e.g. an HTML page served as the estimate "PDF"
            rows, err = [], str(e)[:60]
        else:
            err = "no estimate table found"
        sample = parse_sample(ft_text or "")
        if pd.isna(sample) and r.study in direct:
            sample = float(direct[r.study]["sample_size"])
        dfm = None
        if r.microdata_url and pd.notna(r.published) and r.published >= md_from:
            dfm = md.load_labelled(download(r.microdata_url, raw / r.study / f"MD{r.study}.zip"))
            sample = float(len(dfm))
        start, end, fw_src = _study_fieldwork(r.study, ft_text, md.fieldwork(dfm) if dfm is not None else None,
                                              overrides)
        base = {"study": r.study, "title": r.title, "fieldwork_start": start, "fieldwork_end": end,
                "sample_size": sample, "source_url": BASE + r.slug if r.slug else r.estimate_url,
                "fieldwork_source": fw_src}
        row = dict(base)
        if not rows:
            problems.append(f"{r.study} ({r.title}): official estimate not usable ({err})")
        else:
            off = map_parties(rows, rules, end)
            total = sum(off.values())
            if not 98.0 <= total <= 102.5:
                problems.append(f"{r.study}: official estimate rows sum to {total:.1f}")
            for p, v in off.items():
                if p not in ("OTHER", "BLANK"):
                    recs.append({**base, "pollster": "CIS", "party": p, "value": v})
            row.update({f"official_{p}": v for p, v in off.items()})
        if dfm is not None and end >= md_from and targets is not None:
            miss = md.required_missing(dfm)
            if miss:
                problems.append(f"{r.study} ({r.title}): microdata lack {', '.join(miss)}; no re-estimate")
            else:
                est = md.reestimate(dfm, targets, ccfg["likely_voter_min"])
                for p, v in est.items():
                    if p not in ("OTHER", "BLANK"):
                        recs.append({**base, "pollster": "CIS (microdata, re-weighted)", "party": p,
                                     "value": round(float(v), 2)})
                row.update({f"micro_{p}": round(float(v), 2) for p, v in est.items()})
        table.append(row)
    notes += problems
    return pd.DataFrame(recs), pd.DataFrame(table), notes

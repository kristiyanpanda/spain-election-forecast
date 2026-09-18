"""Fetch and parse the Wikipedia "Opinion polling for the ... Spanish general election" tables.

Source: English Wikipedia, licence CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).
We fetch the raw wikitext (``action=raw``) rather than rendered HTML: the markup is stable,
carries the year in section headings, and lets us drop seat projections cleanly.

Only the "Voting intention estimates" tables are parsed. Hypothetical-scenario tables
(e.g. "Sumar+Podemos"), voting preferences and victory likelihood tables are ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests

USER_AGENT = "spain-election-forecast/0.1 (research; github portfolio)"
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
META_COLS = ["Polling firm/Commissioner", "Fieldwork date", "Sample size", "Turnout", "Lead"]


def fetch_wikitext(title: str, dest: Path, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return dest
    r = requests.get(
        "https://en.wikipedia.org/w/index.php",
        params={"title": title, "action": "raw"},
        headers={"User-Agent": USER_AGENT}, timeout=60,
    )
    r.raise_for_status()
    dest.write_text(r.text, encoding="utf-8")
    return dest


# ----------------------------------------------------------------------------- wikitext utils
def _strip_templates(s: str) -> str:
    """Remove {{...}} blocks, handling nesting."""
    out, depth, i = [], 0, 0
    while i < len(s):
        if s.startswith("{{", i):
            depth += 1
            i += 2
        elif s.startswith("}}", i) and depth > 0:
            depth -= 1
            i += 2
        else:
            if depth == 0:
                out.append(s[i])
            i += 1
    return "".join(out)


def _clean_cell(raw: str) -> str:
    s = re.sub(r"<ref[^>]*/>", "", raw)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = _strip_templates(s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)  # links first: they contain '|'
    # attribute separator: `style="..."| value`, `rowspan="2"| value`
    if "|" in s:
        s = s.rsplit("|", 1)[1]
    s = s.split("<br")[0]
    s = re.sub(r"<small>.*?</small>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("'''", "").replace("''", "")
    return s.strip()


def _rowspan(raw: str) -> int:
    m = re.search(r'rowspan\s*=\s*"?(\d+)', raw)
    return int(m.group(1)) if m else 1


def _header_label(raw: str) -> str:
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", raw, flags=re.S)
    if "|" in _strip_templates(s.split("[[")[0]):
        s = s.split("|", 1)[1] if "[[" not in s.split("|", 1)[0] else s
    # [[File:x.svg|27px|link=Page|Label]] -> Label ; [[Page|Label]] -> Label ; [[Page]] -> Page
    m = re.search(r"\[\[File:[^\]]*?link=([^|\]]+)(?:\|([^\]]*))?\]\]", s)
    if m:
        return (m.group(2) or m.group(1)).strip()
    m = re.search(r"\[\[([^|\]]+)(?:\|([^\]]*))?\]\]", s)
    if m:
        return (m.group(2) or m.group(1)).strip()
    return _clean_cell(s)


@dataclass
class Table:
    section: str
    headers: list[str]
    rows: list[list[str]] = field(default_factory=list)


def parse_tables(wikitext: str) -> list[Table]:
    """Parse every voting-intention table into (section label, headers, rows of clean text)."""
    # Main pages: tables live under "====Voting intention estimates====" (optionally split
    # into year sub-sections). Yearly sub-pages: tables sit directly under "===2022===".
    stop = re.compile(r"^=+\s*(Voting preferences|Victory|Hypothetical|Senate|Sub-national|"
                      r"Leadership|See also|Notes|References)", re.M | re.I)
    m = re.search(r"^====\s*Voting intention estimates\s*====\s*$", wikitext, re.M)
    body = wikitext[m.end():] if m else wikitext
    n = stop.search(body)
    body = body[: n.start()] if n else body

    tables, section = [], "Voting intention estimates"
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("=="):
            section = line.strip("= ").strip()
        if line.startswith("{|"):
            i, tb = _parse_one_table(lines, i + 1, section)
            if re.match(r"^\d{4}\b", section) or section == "Voting intention estimates":
                tables.append(tb)
            continue
        i += 1
    return tables


def _split_cells(line: str, sep: str) -> list[str]:
    return [c for c in re.split(re.escape(sep), line[1:])]


def _parse_one_table(lines: list[str], i: int, section: str) -> tuple[int, Table]:
    header_rows: list[list[str]] = []
    raw_rows: list[list[str]] = []
    cur: list[str] | None = None
    cur_is_header = False

    def _open(cell: str) -> bool:
        """True while a cell has an unclosed <ref> or {{ }}: following lines belong to it."""
        refs_open = len(re.findall(r"<ref(?![^>]*/>)", cell)) - cell.count("</ref>")
        return refs_open > 0 or cell.count("{{") > cell.count("}}")

    while i < len(lines):
        line = lines[i]
        if cur and _open(cur[-1]):
            cur[-1] += "\n" + line
            i += 1
            continue
        if line.startswith("|}"):
            i += 1
            break
        if line.startswith("|-"):
            if cur is not None:
                (header_rows if cur_is_header else raw_rows).append(cur)
            cur, cur_is_header = [], False
        elif line.startswith("!"):
            if cur is None:
                cur = []
            cur_is_header = True
            cur.extend(_split_cells(line, "!!"))
        elif line.startswith("|"):
            if cur is None:
                cur = []
            cur.extend(_split_cells(line, "||"))
        elif cur is not None and cur:
            cur[-1] += "\n" + line  # continuation of a multi-line cell (refs)
        i += 1
    if cur:
        (header_rows if cur_is_header else raw_rows).append(cur)

    headers = [_header_label(h) for h in header_rows[0]] if header_rows else []
    ncol = len(headers)

    # expand rowspans
    pending: dict[int, tuple[str, int]] = {}
    rows = []
    for raw in raw_rows:
        row, k = [], 0
        for col in range(ncol):
            if col in pending:
                val, left = pending[col]
                row.append(val)
                if left - 1 > 0:
                    pending[col] = (val, left - 1)
                else:
                    del pending[col]
                continue
            if k < len(raw):
                cell = raw[k]
                k += 1
                val = _clean_cell(cell)
                rs = _rowspan(cell)
                if rs > 1:
                    pending[col] = (val, rs - 1)
                row.append(val)
            else:
                row.append("")
        if any(row):
            rows.append(row)
    return i, Table(section, headers, rows)


# ----------------------------------------------------------------------------- typing helpers
_DATE_TOKEN = re.compile(r"(\d{1,2})?\s*([A-Z][a-z]{2})?\s*(\d{4})?")


def parse_fieldwork(text: str, section_year: int | None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """'7–11 Sep' + 2026 -> (2026-09-07, 2026-09-11); '28 Jul–3 Aug 2024'; '10 Nov 2019'."""
    t = text.replace("−", "–").replace("-", "–").replace("—", "–").strip()
    parts = [p.strip() for p in t.split("–")]
    end = _DATE_TOKEN.match(parts[-1])
    ed, em, ey = end.group(1), end.group(2), end.group(3)
    ey = int(ey) if ey else section_year
    if em is None or ed is None or ey is None:
        return pd.NaT, pd.NaT
    end_ts = pd.Timestamp(year=ey, month=MONTHS[em], day=int(ed))
    if len(parts) == 1:
        return end_ts, end_ts
    st = _DATE_TOKEN.match(parts[0])
    sd, sm, sy = st.group(1), st.group(2), st.group(3)
    sm = MONTHS[sm] if sm else end_ts.month
    sy = int(sy) if sy else (end_ts.year - 1 if sm > end_ts.month else end_ts.year)
    start_ts = pd.Timestamp(year=sy, month=sm, day=int(sd)) if sd else end_ts
    return start_ts, end_ts


def to_number(s: str) -> float:
    s = s.replace(",", "").replace("~", "").strip()
    if s.startswith("<") or s.startswith(">"):
        return float("nan")  # bounds such as "<1.0" carry no point estimate
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)$", s)  # "33.5–34.0"
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    m = re.match(r"^\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else float("nan")


def tables_to_long(tables: list[Table], cycle: str, default_year: int | None = None) -> pd.DataFrame:
    """Return one row per (poll, party column) with raw header label kept for mapping.

    ``default_year`` is used for fieldwork dates without a year when the table sits in a
    section that is not named after a year (e.g. the single-table Nov-2019 page).
    """
    recs = []
    for tb in tables:
        year = int(tb.section[:4]) if re.match(r"^\d{4}\b", tb.section) else default_year
        idx = {h: j for j, h in enumerate(tb.headers)}
        needed = ["Polling firm/Commissioner", "Fieldwork date", "Sample size"]
        if not all(h in idx for h in needed):
            continue
        parties = [h for h in tb.headers if h not in META_COLS]
        for r_i, row in enumerate(tb.rows):
            firm = row[idx["Polling firm/Commissioner"]]
            start, end = parse_fieldwork(row[idx["Fieldwork date"]], year)
            sample = to_number(row[idx["Sample size"]]) if row[idx["Sample size"]] else float("nan")
            turnout = to_number(row[idx["Turnout"]]) if "Turnout" in idx else float("nan")
            is_election = bool(re.search(r"general election", firm, re.I))
            for p in parties:
                recs.append({
                    "cycle": cycle, "section": tb.section, "row": r_i,
                    "firm_raw": firm, "fieldwork_start": start, "fieldwork_end": end,
                    "sample_size": sample, "turnout": turnout, "is_election": is_election,
                    "party_label": p, "value": to_number(row[idx[p]]),
                    "cell_raw": row[idx[p]],
                })
    return pd.DataFrame(recs)

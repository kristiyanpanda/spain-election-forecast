"""Phase A entry point: build tidy datasets, the data dictionary and the data-quality report.

Outputs (data/processed/):
    results_province.parquet   votes and seats per (election, province, national list)
    results_national.parquet   votes, share of valid vote and seats per (election, party)
    province_totals.parquet    census, turnout, blank/null votes and seats per (election, province)
    polls_long.parquet         one row per (poll, party) for all cycles since Dec 2015
    polls_wide.csv             same, one row per poll (human-readable)
    DATA_DICTIONARY.md, DATA_QUALITY.md
"""

from __future__ import annotations

import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from electoral import ROOT, load_config
from electoral import mir, wiki_polls

# Wikipedia page key -> election cycle the polls belong to (sub-pages merged)
CYCLE_OF = {
    "next": "next", "e2023": "e2023", "e2023_2022": "e2023", "e2023_2019_2021": "e2023",
    "e2019nov": "e2019nov", "e2019apr": "e2019apr", "e2016": "e2016",
}
DEFAULT_YEAR = {"next": 2026, "e2023": 2023, "e2023_2022": 2022, "e2023_2019_2021": 2021,
                "e2019nov": 2019, "e2019apr": 2019, "e2016": 2016}
# Same organisation under two names in the tables (ElectoPanel is Electomanía's panel,
# rebranded EM-Analytics in 2023). Pollster ids are otherwise the name before the slash.
POLLSTER_ALIAS = {"ElectoPanel": "EM-Analytics"}


def norm_label(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return (s.lower().replace("–", "-").replace("—", "-").replace("−", "-")
            .replace(" ", "").replace("'", "").replace("’", ""))


def load_maps() -> tuple[dict, dict, dict]:
    pm = yaml.safe_load((ROOT / "data/party_map_polls.yaml").read_text(encoding="utf-8"))
    rm = yaml.safe_load((ROOT / "data/party_map_results.yaml").read_text(encoding="utf-8"))
    labels = {norm_label(k): v for k, v in pm["labels"].items()}
    return labels, pm["parties"], rm


# ----------------------------------------------------------------------------- results
def build_results(cfg: dict, parties: dict, rmap: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_dir = ROOT / cfg["paths"]["raw_mir"]
    res, tot = mir.build_all(cfg["mir"]["elections"], cfg["mir"]["base_url"], raw_dir)
    res["party"] = [rmap.get(e, {}).get(h, "OTHER") for e, h in zip(res["election"], res["head_nac"])]
    res["bloc"] = res["party"].map(lambda p: parties[p]["bloc"])
    res["election_date"] = res["election"].map(ELECTION_DATES)
    tot["election_date"] = tot["election"].map(ELECTION_DATES)

    valid = tot.groupby("election")["votos_validos"].sum()
    nat = (res.groupby(["election", "party", "bloc"], as_index=False)
              .agg(votos=("votos", "sum"), escanos=("escanos", "sum")))
    nat["share_valid"] = nat["votos"] / nat["election"].map(valid)
    nat["election_date"] = nat["election"].map(ELECTION_DATES)
    nat = nat.sort_values(["election", "votos"], ascending=[True, False]).reset_index(drop=True)
    return res, tot, nat


ELECTION_DATES = {
    "197706": "1977-06-15", "197903": "1979-03-01", "198210": "1982-10-28", "198606": "1986-06-22",
    "198910": "1989-10-29", "199306": "1993-06-06", "199603": "1996-03-03", "200003": "2000-03-12",
    "200403": "2004-03-14", "200803": "2008-03-09", "201111": "2011-11-20", "201512": "2015-12-20",
    "201606": "2016-06-26", "201904": "2019-04-28", "201911": "2019-11-10", "202307": "2023-07-23",
}
ELECTION_DATES = {k: pd.Timestamp(v) for k, v in ELECTION_DATES.items()}


# ----------------------------------------------------------------------------- polls
def build_polls(cfg: dict, labels: dict, parties: dict) -> tuple[pd.DataFrame, list[str]]:
    raw_dir = ROOT / cfg["paths"]["raw_polls"]
    pages = dict(cfg["wikipedia"]["pages"])
    frames, notes = [], []
    for key, title in pages.items():
        path = wiki_polls.fetch_wikitext(title, raw_dir / f"{key}.wikitext")
        tables = wiki_polls.parse_tables(path.read_text(encoding="utf-8"))
        df = wiki_polls.tables_to_long(tables, key, DEFAULT_YEAR.get(key))
        df["source_page"] = title
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)

    unknown = sorted(set(df["party_label"]) - {k for k in df["party_label"] if norm_label(k) in labels})
    if unknown:
        raise ValueError(f"Unmapped party labels in Wikipedia tables: {unknown}")
    df["party"] = df["party_label"].map(lambda s: labels[norm_label(s)])
    df["cycle"] = df["cycle"].map(CYCLE_OF)

    firm = df["firm_raw"].str.split("/", n=1)
    df["pollster"] = firm.str[0].str.strip().replace(POLLSTER_ALIAS)
    df["commissioner"] = firm.str[1].str.strip().fillna("")
    df.loc[df["is_election"], "pollster"] = "ELECTION"

    # a poll is identified by pollster + fieldwork window + sample; duplicates across pages
    # (election rows repeated on every page, same poll in overlapping sub-pages) are dropped
    key_cols = ["cycle", "pollster", "commissioner", "fieldwork_start", "fieldwork_end", "sample_size", "party"]
    before = len(df)
    df = df.drop_duplicates(key_cols)
    notes.append(f"Dropped {before - len(df)} duplicated (poll, party) rows across pages.")

    # same party appearing twice in one poll (e.g. both 'Podemos' and 'Unidos Podemos' columns
    # in the 2016 table): keep the non-missing one, else the first
    df = df.sort_values("value", na_position="last").drop_duplicates(key_cols[:-1] + ["party"])

    polls = df.drop_duplicates(key_cols[:-1]).copy()
    polls = polls.sort_values(["cycle", "fieldwork_end"]).reset_index(drop=True)
    polls["poll_id"] = [f"{c}-{i:04d}" for i, c in enumerate(polls["cycle"])]
    df = df.merge(polls[key_cols[:-1] + ["poll_id"]], on=key_cols[:-1], how="left")

    cutoff = pd.Timestamp(cfg["cutoff_date"])
    n_after = df.loc[df["fieldwork_end"] > cutoff, "poll_id"].nunique()
    df = df[df["fieldwork_end"] <= cutoff]
    notes.append(f"Excluded {n_after} polls with fieldwork ending after the cut-off {cutoff.date()}.")
    df["bloc"] = df["party"].map(lambda p: parties[p]["bloc"])
    df["cutoff_date"] = cutoff
    cols = ["poll_id", "cycle", "pollster", "commissioner", "fieldwork_start", "fieldwork_end",
            "sample_size", "turnout", "is_election", "party", "bloc", "value", "section",
            "source_page", "cutoff_date"]
    return df[cols].sort_values(["cycle", "fieldwork_end", "poll_id"]).reset_index(drop=True), notes


# ----------------------------------------------------------------------------- reports
DICTIONARY = {
    "results_province.parquet": {
        "election": "election id YYYYMM (e.g. 202307)",
        "election_date": "polling day",
        "election_month": "first day of the election month (kept for ordering)",
        "ccaa": "autonomous community code (Ministry coding)",
        "prov": "INE province code 01-52 (51 Ceuta, 52 Melilla)",
        "cand_code": "Ministry candidatura code (provincial list)",
        "head_nac": "code of the national head list this provincial list belongs to",
        "siglas": "Ministry short name of the provincial list",
        "nombre": "Ministry full name of the provincial list",
        "party": "canonical party family (data/party_map_results.yaml); OTHER if unmapped",
        "bloc": "left / right / periph_left / periph_right / other",
        "votos": "valid votes for the list in the province",
        "escanos": "seats won by the list in the province",
    },
    "results_national.parquet": {
        "election": "election id", "election_date": "polling day", "party": "canonical party family",
        "bloc": "bloc", "votos": "national valid votes (sum of provinces)",
        "escanos": "national seats", "share_valid": "votos / national valid votes (blank included)",
    },
    "province_totals.parquet": {
        "election": "election id", "election_date": "polling day", "ccaa": "CCAA code",
        "prov": "province code", "ambito_nombre": "province name (Ministry spelling)",
        "censo_escrutinio": "electoral census used at the count",
        "votantes": "ballots cast = valid + null", "votos_validos": "valid votes = candidaturas + blank",
        "votos_blancos": "blank votes", "votos_nulos": "null votes",
        "votos_candidaturas": "votes for lists", "escanos": "seats at stake in the province",
        "turnout": "votantes / censo_escrutinio",
    },
    "polls_long.parquet": {
        "poll_id": "cycle + running number", "cycle": "election the poll precedes: e2016, e2019apr, e2019nov, e2023, next",
        "pollster": "polling firm (before the slash in Wikipedia); ELECTION for actual results rows",
        "commissioner": "media outlet / client (after the slash)",
        "fieldwork_start": "first fieldwork day", "fieldwork_end": "last fieldwork day (used as poll date)",
        "sample_size": "n respondents; NaN when Wikipedia shows '?'",
        "turnout": "turnout estimate in % when published", "is_election": "True for actual election result rows",
        "party": "canonical party id (data/party_map_polls.yaml)", "bloc": "bloc",
        "value": "vote estimate in % of valid vote; NaN when not published ('?') or party not polled ('–')",
        "section": "Wikipedia table section (year or scenario label)", "source_page": "Wikipedia page title",
        "cutoff_date": "data cut-off stamped on every row",
    },
}


def write_dictionary(path: Path) -> None:
    lines = ["# Data dictionary", "",
             "All processed files live in `data/processed/`. Codes and lineage choices are in "
             "`data/party_map_*.yaml` and `docs/party_mapping.md`.", ""]
    for fname, cols in DICTIONARY.items():
        lines += [f"## `{fname}`", "", "| column | meaning |", "|---|---|"]
        lines += [f"| `{c}` | {d} |" for c, d in cols.items()]
        lines.append("")
    lines += ["## Sources and licences", "",
              "* **Official results**: Ministerio del Interior, infoelectoral.interior.gob.es, files "
              "`02YYYYMM_TOTA.zip`. Reuse under Ley 37/2007 and RD 1495/2011. "
              "*Origen de los datos: Ministerio del Interior.*",
              "* **Polls**: English Wikipedia, \"Opinion polling for the ... Spanish general election\" "
              "pages (and the 2019-2022 sub-pages), licence CC BY-SA 4.0. CIS barometers enter through "
              "their rows in those tables; *Fuente de los datos: Centro de Investigaciones Sociológicas* "
              "for those rows.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_quality(path: Path, cfg: dict, res: pd.DataFrame, tot: pd.DataFrame, nat: pd.DataFrame,
                  polls: pd.DataFrame, notes: list[str]) -> None:
    cutoff = cfg["cutoff_date"]
    L = [f"# Data quality report", "", f"Generated {date.today().isoformat()}. Data cut-off: **{cutoff}**.", ""]

    L += ["## Official results (Ministerio del Interior)", ""]
    chk = tot.groupby("election").agg(provinces=("prov", "nunique"), seats=("escanos", "sum"),
                                      valid_votes=("votos_validos", "sum"), turnout=("turnout", "mean"))
    chk["seats_from_lists"] = res.groupby("election")["escanos"].sum()
    chk["share_mapped"] = res[res.party != "OTHER"].groupby("election")["votos"].sum() / res.groupby("election")["votos"].sum()
    chk["valid_votes"] = chk["valid_votes"].map("{:,}".format)
    chk["turnout"] = (100 * chk["turnout"]).round(1)
    chk["share_mapped"] = (100 * chk["share_mapped"]).round(1)
    L += ["Every election must have 52 provinces and 350 seats; `share_mapped` is the share of valid "
          "list votes assigned to a named party family (the rest is OTHER).", "",
          chk.to_markdown(), ""]
    bad = chk[(chk.provinces != 52) | (chk.seats != 350) | (chk.seats_from_lists != 350)]
    L += ["Checks: " + ("**all passed**." if bad.empty else f"**FAILED** for {list(bad.index)}."), ""]
    L += ["2023 national check (official: PP 33.06 %, PSOE 31.68 %, Vox 12.38 %, Sumar 12.33 %):", ""]
    n23 = nat[nat.election == "202307"].head(6)[["party", "share_valid", "escanos"]].copy()
    n23["share_valid"] = (100 * n23["share_valid"]).round(2)
    L += [n23.to_markdown(index=False), ""]

    L += ["## Polls (Wikipedia tables)", ""]
    p = polls.drop_duplicates("poll_id")
    real = p[~p.is_election]
    summ = real.groupby("cycle").agg(polls=("poll_id", "size"), first=("fieldwork_end", "min"),
                                     last=("fieldwork_end", "max"), pollsters=("pollster", "nunique"),
                                     missing_n=("sample_size", lambda s: s.isna().mean()))
    summ["missing_n"] = (100 * summ["missing_n"]).round(1).astype(str) + " %"
    L += [summ.to_markdown(), ""]
    L += [f"Latest poll before the cut-off: **{real.fieldwork_end.max().date()}** "
          f"({real.sort_values('fieldwork_end').iloc[-1]['pollster']}).", ""]
    L += ["Top pollsters (all cycles):", "", real.pollster.value_counts().head(15).to_frame("polls").to_markdown(), ""]
    sums = polls[~polls.is_election].groupby("poll_id")["value"].sum()
    L += ["Sum of published party shares per poll (should sit a few points below 100 because small "
          "parties and 'others' are omitted):", "",
          sums.describe().round(1).to_frame("sum_of_shares").T.to_markdown(), ""]
    odd = sums[(sums < 80) | (sums > 101)]
    L += [f"{len(odd)} polls sum below 80 or above 101 (kept, flagged here; see `section`).", ""]
    L += ["Notes from the build:", ""] + [f"* {n}" for n in notes] + [""]
    L += ["## Known limitations", "",
          "* No regional (by autonomous community) general-election polls are used: the Wikipedia "
          "sub-national tables cover regional elections. Provincial swing is therefore an explicit "
          "modelling assumption (phase D).",
          "* Sample size is missing for some polls (shown as '?' on Wikipedia); the model imputes the "
          "pollster's median and, failing that, 1,000.",
          "* Wikipedia editors harmonise pollster releases (e.g. Podemos inside/outside Sumar); we "
          "follow their table sections and document the mapping in `docs/party_mapping.md`.",
          "* Party shares refer to the valid vote including blank ballots in official results, while "
          "pollsters' bases vary; house effects absorb constant differences.", ""]
    path.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    cfg = load_config()
    labels, parties, rmap = load_maps()
    out = ROOT / cfg["paths"]["processed"]
    out.mkdir(parents=True, exist_ok=True)

    res, tot, nat = build_results(cfg, parties, rmap)
    res.to_parquet(out / "results_province.parquet", index=False)
    tot.to_parquet(out / "province_totals.parquet", index=False)
    nat.to_parquet(out / "results_national.parquet", index=False)
    nat.to_csv(out / "results_national.csv", index=False)

    polls, notes = build_polls(cfg, labels, parties)
    polls.to_parquet(out / "polls_long.parquet", index=False)
    wide = polls.pivot_table(index=["poll_id", "cycle", "pollster", "commissioner", "fieldwork_start",
                                    "fieldwork_end", "sample_size", "turnout", "is_election"],
                             columns="party", values="value", aggfunc="first").reset_index()
    wide.to_csv(out / "polls_wide.csv", index=False)

    write_dictionary(out / "DATA_DICTIONARY.md")
    write_quality(out / "DATA_QUALITY.md", cfg, res, tot, nat, polls, notes)
    print(f"results: {len(res)} province rows, {len(nat)} national rows; polls: {polls.poll_id.nunique()} polls, "
          f"{len(polls)} rows. Written to {out}")


if __name__ == "__main__":
    main()

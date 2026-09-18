"""Phase G: one self-contained interactive HTML page (Plotly) in docs/index.html.

Sections: headline numbers, latent vote-share trends with 90 % bands and raw polls (toggle
parties), seat distributions at the cut-off and at the legal deadline, probability tables, the
backtest scorecard, and an author/method footer. Author details come from ``config.yaml``.
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from electoral import ROOT, load_config
from electoral.plots import COLORS

FONT = "Calibri, Carlito, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

CSS = """
:root { --ink:#1e2430; --muted:#5b6473; --line:#c9ced6; --head:#eef1f5; --accent:#1f6fb2; --band:#f7f8fa; }
* { box-sizing: border-box; }
body { font-family: %(font)s; font-size: 16px; line-height: 1.5; color: var(--ink); background: #fff;
       max-width: 1180px; margin: 0 auto; padding: 24px 20px 48px; }
h1 { font-size: 30px; font-weight: 600; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 21px; font-weight: 600; margin: 34px 0 10px; border-bottom: 2px solid var(--accent); padding-bottom: 4px; }
h3 { font-size: 17px; font-weight: 600; margin: 18px 0 8px; }
.subtitle { color: var(--muted); margin: 0 0 14px; font-size: 17px; }
.byline { font-size: 15px; color: var(--muted); margin-bottom: 18px; }
.byline a { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; }
.byline a:hover { border-bottom-color: var(--accent); }
.note { background: #fff8e6; border: 1px solid #f0d58c; border-left: 5px solid #e0a800; padding: 10px 14px; border-radius: 4px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 16px 0 6px; }
.card { border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; background: var(--band); }
.card .k { font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.card .v { font-size: 26px; font-weight: 600; margin-top: 2px; }
.card .s { font-size: 13px; color: var(--muted); }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 28px; }
.cols > div { min-width: 0; overflow-x: auto; }
table { border-collapse: collapse; width: 100%%; font-size: 15px; margin: 8px 0 18px; border: 1px solid var(--line); }
th, td { border: 1px solid var(--line); padding: 6px 10px; text-align: left; vertical-align: top; }
th { background: var(--head); font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
tbody tr:nth-child(even) td { background: var(--band); }
tr.hl td { font-weight: 600; }
.small { font-size: 13px; color: var(--muted); }
footer { margin-top: 36px; padding-top: 14px; border-top: 1px solid var(--line); font-size: 14px; color: var(--muted); }
footer a { color: var(--accent); text-decoration: none; }
"""


def _hex_rgba(h: str, a: float) -> str:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def _pct(p: float) -> str:
    if p > 0.995:
        return "> 99 %"
    if p < 0.005:
        return "< 1 %"
    return f"{100 * p:.0f} %"


def _table(headers: list[tuple[str, bool]], rows: list[list], highlight: set[int] | None = None) -> str:
    th = "".join(f"<th class='{'num' if n else ''}'>{h}</th>" for h, n in headers)
    body = []
    for i, r in enumerate(rows):
        cls = " class='hl'" if highlight and i in highlight else ""
        tds = "".join(f"<td class='{'num' if headers[j][1] else ''}'>{c}</td>" for j, c in enumerate(r))
        body.append(f"<tr{cls}>{tds}</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def main() -> None:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    cutoff, deadline = cfg["cutoff_date"], cfg["legal_deadline"]
    author = cfg.get("author", {})
    trend = pd.read_parquet(out / "poll_average_daily_next.parquet")
    trend = trend[trend.date.dt.dayofweek == pd.Timestamp(cutoff).dayofweek].round(4)   # weekly nodes keep the page light
    polls = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "polls_long.parquet")
    polls = polls[(polls.cycle == "next") & (~polls.is_election) & polls.value.notna()]
    seats_now = pd.read_parquet(out / "seat_draws_next.parquet")
    seats_dl = pd.read_parquet(out / "seat_draws_deadline.parquet")
    probs_now = pd.read_csv(out / "seat_probabilities_next.csv")
    probs_dl = pd.read_csv(out / "seat_probabilities_deadline.csv")
    vote_dl = pd.read_csv(out / "vote_summary_deadline.csv", index_col=0)
    diag = json.loads((out / "diagnostics_next.json").read_text())
    score = pd.read_csv(out / "backtest_scorecard.csv")
    fc = json.loads((out / "forecast_deadline.json").read_text())

    parties = [p for p in ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"]
               if p in set(trend.party)]
    # "now" = the cut-off state used by the seat simulation (same draws as the README numbers)
    sd_now = pd.read_parquet(out / "state_draws_next.parquet")
    last = sd_now.quantile([0.05, 0.5, 0.95]).T
    last.columns = ["q05", "q50", "q95"]

    # ---------------------------------------------------------------- figure
    fig = make_subplots(rows=2, cols=2, specs=[[{"colspan": 2}, None], [{}, {}]],
                        subplot_titles=("Latent vote share (median, 50 % and 90 % bands) and every poll",
                                        f"Seats if the election were held at the cut-off ({cutoff})",
                                        f"Seats projected to the legal deadline ({deadline})"),
                        vertical_spacing=0.14, row_heights=[0.6, 0.4])
    for p in parties:
        c = COLORS.get(p, "#444444")
        t = trend[trend.party == p]
        vis = True if p in ("PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF") else "legendonly"
        pp = polls[polls.party == p]
        fig.add_trace(go.Scatter(x=pp.fieldwork_end, y=pp.value, mode="markers", name=f"{p} polls",
                                 marker={"color": _hex_rgba(c, 0.35), "size": 5}, legendgroup=p,
                                 showlegend=False, visible=vis,
                                 hovertemplate="%{text}<br>%{x|%d %b %Y}: %{y:.1f} %<extra></extra>",
                                 text=pp.pollster), row=1, col=1)
        fig.add_trace(go.Scatter(x=pd.concat([t.date, t.date[::-1]]), y=100 * pd.concat([t.q95, t.q05[::-1]]),
                                 fill="toself", fillcolor=_hex_rgba(c, 0.12), line={"width": 0},
                                 legendgroup=p, showlegend=False, hoverinfo="skip", visible=vis), row=1, col=1)
        fig.add_trace(go.Scatter(x=t.date, y=100 * t.q50, mode="lines", name=p, line={"color": c, "width": 2},
                                 legendgroup=p, visible=vis,
                                 hovertemplate=p + " %{x|%d %b %Y}: %{y:.1f} %<extra></extra>"), row=1, col=1)
    fig.add_vline(x=pd.Timestamp(cutoff).timestamp() * 1000, line={"dash": "dash", "color": "black", "width": 1}, row=1, col=1)
    for col, sd in ((1, seats_now), (2, seats_dl)):
        for p in ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "ERC", "JUNTS", "BILDU", "PNV"]:
            q = sd[p].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).values   # summary stats only: keeps the HTML small
            fig.add_trace(go.Box(name=p, x=[p], q1=[q[1]], median=[q[2]], q3=[q[3]], lowerfence=[q[0]], upperfence=[q[4]],
                                 marker={"color": COLORS.get(p, "#444")}, showlegend=False,
                                 hovertemplate=p + ": %{y} seats<extra></extra>"), row=2, col=col)
        fig.add_hline(y=176, line={"color": "black", "width": 1}, row=2, col=col)
    fig.update_yaxes(title_text="% of valid vote", row=1, col=1)
    fig.update_yaxes(title_text="seats", row=2, col=1)
    fig.update_layout(height=880, template="plotly_white", font={"family": FONT, "size": 14, "color": "#1e2430"},
                      legend={"orientation": "h", "y": 1.07}, margin={"l": 60, "r": 30, "t": 60, "b": 40})

    # ---------------------------------------------------------------- tables
    def seat_row(sd: pd.DataFrame, p: str) -> str:
        return f"{int(sd[p].quantile(.05))} - {int(sd[p].quantile(.95))}"

    party_rows = []
    for p in parties:
        party_rows.append([p, f"{100 * last.loc[p, 'q50']:.1f}", f"{100 * last.loc[p, 'q05']:.1f} - {100 * last.loc[p, 'q95']:.1f}",
                           f"{int(seats_now[p].median())}", seat_row(seats_now, p),
                           f"{100 * vote_dl.loc[p, 'q05']:.1f} - {100 * vote_dl.loc[p, 'q95']:.1f}", seat_row(seats_dl, p)])
    party_table = _table([("party", False), ("vote now, median", True), ("vote now, 90 %", True),
                          ("seats now, median", True), ("seats now, 90 %", True),
                          (f"vote at deadline, 90 %", True), ("seats at deadline, 90 %", True)], party_rows)

    pn = probs_now.set_index("event")["probability"]
    pd_ = probs_dl.set_index("event")["probability"]
    events = [("Right (PP+Vox+UPN+SALF) >= 176", "PP + Vox (+ UPN, SALF) reach 176 seats"),
              ("PP+Vox >= 176", "PP + Vox alone reach 176"),
              ("PP largest party", "PP is the largest party"),
              ("2023 investiture bloc (above + PNV + Junts) >= 176", "2023 investiture bloc (PSOE, Sumar, Podemos, ERC, Bildu, BNG, CC, PNV, Junts) reaches 176"),
              ("Left + peripheral left (PSOE+Sumar+Podemos+ERC+Bildu+BNG+CC+Compromís) >= 176", "Left + peripheral left without PNV and Junts reaches 176"),
              ("PP >= 176 alone", "PP alone reaches 176"),
              ("VOX >= 50 seats", "Vox above 50 seats"), ("PSOE >= 100 seats", "PSOE above 100 seats"),
              ("PSOE >= 121 seats", "PSOE keeps its 121 seats or more"), ("SUMAR >= 10 seats", "Sumar at 10 seats or more"),
              ("PODEMOS >= 1 seats", "Podemos wins at least one seat"), ("SALF >= 1 seats", "SALF wins at least one seat")]
    prob_rows = [[label, _pct(pn.get(k, float("nan"))), _pct(pd_.get(k, float("nan")))] for k, label in events if k in pn]
    prob_table = _table([("event", False), (f"if held now", True), (f"projected to {deadline[:7]}", True)], prob_rows, {0})

    sc = score.groupby("method")[["vote_mae_pp", "vote_crps_pp", "vote_cover90", "seat_mae", "seat_cover90", "brier"]].mean()
    order = [("model", "this model"), ("poll_average_30d", "30-day poll average"), ("last_election", "last election result")]
    sc_rows = []
    for key, label in order:
        r = sc.loc[key]
        cov_v = f"{100 * r.vote_cover90:.0f} %" if key == "model" else "n/a"
        cov_s = f"{100 * r.seat_cover90:.0f} %" if key == "model" else "n/a"
        sc_rows.append([label, f"{r.vote_mae_pp:.2f}", f"{r.vote_crps_pp:.2f}", cov_v, f"{r.seat_mae:.1f}", cov_s, f"{r.brier:.2f}"])
    sc_table = _table([("method", False), ("vote MAE (pp)", True), ("vote CRPS (pp)", True), ("90 % vote coverage", True),
                       ("seat MAE", True), ("90 % seat coverage", True), ("Brier", True)], sc_rows, {0})

    n_polls, n_pollsters = diag["n_polls"], diag["n_pollsters"]
    right_now, right_dl = pn.get("Right (PP+Vox+UPN+SALF) >= 176"), pd_.get("Right (PP+Vox+UPN+SALF) >= 176")
    cards = f"""
<div class="cards">
 <div class="card"><div class="k">PP vote now</div><div class="v">{100 * last.loc['PP', 'q50']:.1f} %</div><div class="s">90 %: {100 * last.loc['PP', 'q05']:.1f} - {100 * last.loc['PP', 'q95']:.1f}</div></div>
 <div class="card"><div class="k">PSOE vote now</div><div class="v">{100 * last.loc['PSOE', 'q50']:.1f} %</div><div class="s">90 %: {100 * last.loc['PSOE', 'q05']:.1f} - {100 * last.loc['PSOE', 'q95']:.1f}</div></div>
 <div class="card"><div class="k">Vox vote now</div><div class="v">{100 * last.loc['VOX', 'q50']:.1f} %</div><div class="s">90 %: {100 * last.loc['VOX', 'q05']:.1f} - {100 * last.loc['VOX', 'q95']:.1f}</div></div>
 <div class="card"><div class="k">PP + Vox majority</div><div class="v">{_pct(right_now)}</div><div class="s">if held now; {_pct(right_dl)} at the deadline</div></div>
 <div class="card"><div class="k">Backtest vote error</div><div class="v">{sc.loc['model', 'vote_mae_pp']:.2f} pp</div><div class="s">mean absolute error, 4 elections, 30 days out</div></div>
</div>"""

    gh = author.get("github")
    links = f"<a href='{gh}' target='_blank' rel='noopener'>GitHub</a>" if gh else ""
    byline = f"<div class='byline'>By <b>{author.get('name', '')}</b>" + (f" · {links}" if links else "") + \
             f" · data cut-off {cutoff} · last poll {diag['last_poll']}</div>"

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spanish general election forecast</title><style>{CSS % {'font': FONT}}</style></head><body>
<h1>Forecasting the next Spanish general election</h1>
<p class="subtitle">A Bayesian poll-aggregation and seat-projection model with a four-election backtest</p>
{byline}
<p class="note"><b>Numbers expire.</b> Everything on this page is conditional on the {n_polls} polls from {n_pollsters} pollsters
published up to <b>{cutoff}</b>. The election must be held by mid-August 2027. These are model probabilities, not predictions
of the result; the backtest below shows how wrong the same method has been before.</p>
{cards}
<h2>Vote shares and seats</h2>
{fig.to_html(full_html=False, include_plotlyjs="cdn")}
<p class="small">Click a party in the legend to show or hide it; regional parties are hidden by default. The boxes show the
median, the 50 % and the 90 % intervals of 10,000 seat simulations. The horizontal line is the 176-seat majority.</p>
<h2>Summary tables</h2>
<h3>Per party</h3>
{party_table}
<div class="cols">
<div><h3>Probabilities</h3>{prob_table}</div>
<div><h3>Backtest scorecard (mean over 2016, Apr 2019, Nov 2019, 2023)</h3>{sc_table}
<p class="small">Forecasts made 30 days before each election with only the polls available then. The model beats both
baselines on point accuracy, but its 90 % vote intervals covered only {100 * sc.loc['model', 'vote_cover90']:.0f} % of outcomes
(July 2023: every pollster underestimated PSOE by about 5 points). The deadline projection therefore adds an
election-day error of {100 * fc['error_inflation']['extra_sd_relative']:.0f} % of each party's share, the smallest value that would have restored
90 % coverage; mean reversion toward the last result was tested and rejected.</p></div>
</div>
<h2>Method in one paragraph</h2>
<p>Official results 1977-2023 come from the Ministerio del Interior; polls from the Wikipedia opinion-polling tables
(CC BY-SA 4.0), with CIS barometers entering through their rows there. The aggregator is a state-space model on a weekly
grid: each party's share follows a random walk on the logit scale, anchored on the July 2023 result, with hierarchical
house effects per pollster and a noise term that combines sample size with a party-specific excess variance. Seats are
simulated by proportional swing from each party's 2023 provincial share, calibrated provincial noise and D'Hondt in the
52 districts (3 % threshold; Ceuta and Melilla by plurality). Sampling: NUTS, 4 chains x 1,000 draws, {diag['divergences']}
divergences, R-hat {diag['rhat_max']:.2f}.</p>
<footer>{author.get('name', '')}{(' · ' + links) if links else ''} · Sources: Ministerio del Interior (results, reuse under Ley 37/2007),
Wikipedia (polls, CC BY-SA 4.0), CIS (via Wikipedia). Generated by <code>electoral report</code>; full code, tests, data
dictionary and methods note in the repository.</footer>
</body></html>"""
    docs = ROOT / "docs"
    (docs / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {docs / 'index.html'} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()

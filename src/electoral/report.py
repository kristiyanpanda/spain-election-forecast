"""Phase G: one self-contained interactive HTML page (Plotly) in docs/index.html.

Panels: latent vote-share trends with 90 % bands and raw polls (toggle parties), seat
distributions at the cut-off and at the legal deadline, and the probability table.
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from electoral import ROOT, load_config
from electoral.plots import COLORS


def _hex_rgba(h: str, a: float) -> str:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def main() -> None:
    cfg = load_config()
    out = ROOT / cfg["paths"]["outputs"]
    cutoff = cfg["cutoff_date"]
    trend = pd.read_parquet(out / "poll_average_daily_next.parquet")
    trend = trend[trend.date.dt.dayofweek == pd.Timestamp(cutoff).dayofweek]   # weekly nodes keep the page light
    trend = trend.round(4)
    polls = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "polls_long.parquet")
    polls = polls[(polls.cycle == "next") & (~polls.is_election) & polls.value.notna()]
    seats_now = pd.read_parquet(out / "seat_draws_next.parquet")
    seats_dl = pd.read_parquet(out / "seat_draws_deadline.parquet") if (out / "seat_draws_deadline.parquet").exists() else None
    probs_now = pd.read_csv(out / "seat_probabilities_next.csv")
    probs_dl = pd.read_csv(out / "seat_probabilities_deadline.csv") if (out / "seat_probabilities_deadline.csv").exists() else None
    diag = json.loads((out / "diagnostics_next.json").read_text())

    parties = [p for p in ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"]
               if p in set(trend.party)]

    fig = make_subplots(rows=2, cols=2, specs=[[{"colspan": 2}, None], [{}, {}]],
                        subplot_titles=("Latent vote share (median, 50 % and 90 % bands) and polls",
                                        f"Seats if the election were held at the cut-off ({cutoff})",
                                        f"Seats projected to the legal deadline ({cfg['legal_deadline']})"),
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
        if sd is None:
            continue
        for p in ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "ERC", "JUNTS", "BILDU", "PNV"]:
            if p in sd:
                q = sd[p].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).values   # summary stats only: keeps the HTML small
                fig.add_trace(go.Box(name=p, q1=[q[1]], median=[q[2]], q3=[q[3]], lowerfence=[q[0]],
                                     upperfence=[q[4]], marker={"color": COLORS.get(p, "#444")},
                                     showlegend=False, hovertemplate=p + ": %{y} seats<extra></extra>"),
                              row=2, col=col)
        fig.add_hline(y=176, line={"color": "black", "width": 1}, row=2, col=col)

    fig.update_yaxes(title_text="% of valid vote", row=1, col=1)
    fig.update_yaxes(title_text="seats", row=2, col=1)
    fig.update_layout(height=900, template="plotly_white", legend={"orientation": "h", "y": 1.06},
                      margin={"l": 60, "r": 30, "t": 90, "b": 40},
                      title={"text": "Forecasting the next Spanish general election: poll aggregate and seat projection",
                             "x": 0.01})

    def table(df: pd.DataFrame, title: str) -> str:
        rows = "".join(f"<tr><td>{r.event}</td><td style='text-align:right'>{100 * r.probability:.0f} %</td></tr>"
                       for r in df.itertuples())
        return f"<h3>{title}</h3><table><tr><th>event</th><th>probability</th></tr>{rows}</table>"

    tables = table(probs_now, f"Probabilities if held at the cut-off ({cutoff})")
    if probs_dl is not None:
        tables += table(probs_dl, f"Probabilities projected to the legal deadline ({cfg['legal_deadline']})")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Spanish election forecast</title>
<style>body{{font-family:Segoe UI,Helvetica,Arial,sans-serif;max-width:1200px;margin:20px auto;padding:0 16px;color:#222}}
table{{border-collapse:collapse;font-size:14px;margin-bottom:24px}}td,th{{border-bottom:1px solid #ddd;padding:4px 10px;text-align:left}}
.note{{background:#fff8e1;border-left:4px solid #f0a500;padding:8px 12px;font-size:14px}}
.cols{{display:flex;gap:40px;flex-wrap:wrap}}</style></head><body>
<p class="note"><b>Numbers expire.</b> Data cut-off <b>{cutoff}</b>; last poll {diag['last_poll']}; {diag['n_polls']} polls from
{diag['n_pollsters']} pollsters. These are probabilities conditional on the model, not predictions of the result.
Sources: Ministerio del Interior (results), Wikipedia opinion-polling tables (CC BY-SA 4.0), CIS via those tables.</p>
{fig.to_html(full_html=False, include_plotlyjs="cdn")}
<div class="cols">{tables}</div>
<p style="font-size:12px;color:#666">Generated by <code>electoral report</code>. Model and limitations: see the repository README and docs/.</p>
</body></html>"""
    docs = ROOT / "docs"
    (docs / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {docs / 'index.html'} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()

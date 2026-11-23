"""Phase G: one self-contained interactive HTML page (Plotly), in English and Spanish.

English: ``docs/index.html``; Spanish: ``docs/es/index.html`` (copy in ``spanish version/``). Sections: headline numbers,
the Congress chart with its coalition builder (figure 1, ``electoral.pactometro``), latent vote-share trends with 90 % bands, raw polls and numbered
events (figure 2), seat ranges on election day under the base (split left) and sensitivity (merged
left) party supply (figure 3), probability tables, the backtest scorecard, and an author/method
footer. Author details, the provisional label and the events come from ``config.yaml``; the wording
of each language is in ``TEXT`` below and in ``electoral.i18n``.
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs_version
from plotly.subplots import make_subplots

from electoral import ROOT, i18n, load_config
from electoral.i18n import num, tr
from electoral.pactometro import fragment as pactometro_fragment
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
h3.fig { margin: 22px 0 2px; }
h3.fig span { color: var(--accent); margin-right: 4px; }
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
th.num { white-space: normal; }
table.tight td:first-child { white-space: nowrap; }
tbody tr:nth-child(even) td { background: var(--band); }
tr.hl td { font-weight: 600; }
.small { font-size: 13px; color: var(--muted); }
.key { display: flex; flex-wrap: wrap; gap: 4px 18px; align-items: center; border: 1px solid var(--line); border-radius: 10px;
       background: var(--band); padding: 8px 14px; margin: 2px 0 8px; font-size: 14px; }
.key .t { font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; font-size: 12px; }
.key .n { display: inline-block; min-width: 20px; height: 20px; line-height: 18px; text-align: center; border: 1px solid #777;
          border-radius: 10px; font-weight: 600; font-size: 12px; margin-right: 5px; background: #fff; }
.key .d { color: var(--muted); }
footer { margin-top: 36px; padding-top: 14px; border-top: 1px solid var(--line); font-size: 14px; color: var(--muted); }
footer a { color: var(--accent); text-decoration: none; }
"""

# Plotly's Spanish locale, registered inline so the page needs no second download
PLOTLY_ES = {
    "moduleType": "locale", "name": "es",
    "dictionary": {"Autoscale": "Autoescalar", "Box Select": "Selección rectangular", "Lasso Select": "Selección de lazo",
                   "Download plot as a png": "Descargar el gráfico como png", "Pan": "Desplazar", "Zoom": "Ampliar",
                   "Zoom in": "Acercar", "Zoom out": "Alejar", "Reset axes": "Restablecer ejes",
                   "Double-click to zoom back out": "Doble clic para volver a la vista inicial",
                   "Double-click on legend to isolate one trace": "Doble clic en la leyenda para aislar una serie",
                   "Toggle Spike Lines": "Mostrar u ocultar líneas guía",
                   "Show closest data on hover": "Mostrar el dato más cercano",
                   "Compare data on hover": "Comparar datos al pasar el cursor"},
    "format": {"days": ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"],
               "shortDays": ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
               "months": i18n.MONTHS["es"], "shortMonths": i18n.MONTHS_SHORT["es"],
               "date": "%d/%m/%Y", "decimal": ",", "thousands": "."},
}

# wording of the page; {fields} are filled in build()
TEXT = {
    "en": {
        "html_lang": "en",
        "page_title": "Spanish general election forecast",
        "h1": "Forecasting the {election} Spanish general election",
        "subtitle": "A Bayesian poll-aggregation and seat-projection model with a four-election backtest",
        "byline": "By <b>{author}</b>{links} · data cut-off {cutoff} · last poll {last_poll} · "
                  "<a href='es/index.html'>Versión en español</a>",
        "note": "<b>{provisional}.</b> Everything on this page is conditional on the {n_polls} polls from {n_pollsters} "
                "pollsters published up to <b>{cutoff}</b>, {ahead} before polling day. These are model "
                "probabilities, not predictions of the result; the backtest below shows how wrong the same method has "
                "been before.",
        "card_vote": "{party} vote, {h}", "card_major": "PP + Vox (+UPN, SALF) majority",
        "card_major_s": "split left; {p} if the left merges", "card_bt": "Backtest vote error",
        "card_bt_s": "mean absolute error, 4 elections, 30 days out",
        "h2_congress": "The Congress on {h_long}",
        "figure": "Figure",
        "fig1": "Expected seats in the Congress on {h_long}, and who could govern",
        "h2_votes": "Vote shares and seats",
        "fig2": "Vote share since the July 2023 election: every poll and the latent trend",
        "fig2_cap": "Lines: median of the latent vote share, with its 90 % band; dots: every poll. Click a party in the "
                    "legend to show or hide it; regional parties are hidden by default. The numbers on the horizontal "
                    "axis mark the events in the key; the dashed line is the data cut-off. Drag to zoom in, or use the "
                    "buttons above the chart; double-click to go back.",
        "events": "Events",
        "fig3": "Seats on {h_long} under the two party-supply scenarios",
        "fig3_cap": "Boxes: median, 50 % and 90 % intervals of 10,000 seat simulations. The horizontal line is the "
                    "176-seat majority.",
        "h2_history": "The parties since 1977",
        "fig4": "Vote share of every party at the general elections since 1977, and the {h_long} forecast",
        "fig4_cap": "Dots: general elections, share of the valid vote (Ministry of the Interior). A line runs from a "
                    "party's first election to its last, through its changes of name (AP and PP, HB and EH Bildu, CiU "
                    "and Junts); a cross marks the last election of a party that is gone, and a dotted link a party "
                    "that went into another (IU into Unidos Podemos, Unidas Podemos into Sumar). The hollow dots on "
                    "the right are the {h} forecast with its 90 % interval. The band on top shows who governed; the "
                    "numbers under the axis mark the dates in the key. Click a party in the legend to hide it; drag to "
                    "zoom in, double-click to go back.",
        "gov": "Head of government", "panel_state": "State-wide parties",
        "panel_periph": "Nationalist and regional parties", "seats_w": "seats", "fc_w": "forecast",
        "h2_tables": "Summary tables", "h3_party": "Per party", "h3_prob": "Probabilities",
        "prob_note": "≥ 176: an absolute majority of seats. 2023 investiture bloc: PSOE, Sumar / Frente Amplio, Podemos, "
                     "ERC, EH Bildu, BNG, CC, Adelante Andalucía, PNV and Junts. Left + peripheral left: the same "
                     "without PNV and Junts. Split and merged refer to the left's lists on {h}.",
        "h3_score": "Backtest scorecard (mean over 2016, Apr 2019, Nov 2019, 2023)",
        "score_note": "Forecasts made 30 days before each election with only the polls available then. The model's 90 % "
                      "vote intervals covered {cover} % of outcomes, so the election-day projection adds an error of "
                      "{infl} % of each party's share, the smallest value that would have restored 90 % coverage; mean "
                      "reversion toward the last result was tested ({reversion}). The regional-poll layer enters the "
                      "backtest only for Catalonia in 2023 (CEO), the one case with regional data.",
        "adopted": "adopted", "rejected": "rejected",
        "h2_method": "Method in one paragraph",
        "method": "Official results 1977-2023 come from the Ministerio del Interior; polls from the Wikipedia "
                  "opinion-polling tables (CC BY-SA 4.0); CIS straight from cis.es: its official estimate as one series, "
                  "and our re-estimate from its microdata (2023 recall, likely voters) as another, with series built "
                  "from the same survey sharing its sample size. A pollster's releases with overlapping fieldwork "
                  "(daily trackers, cumulative panels) count once. The aggregator is a state-space model on a weekly "
                  "grid: each party's share follows a random walk on the logit scale, anchored on the July 2023 result, "
                  "with hierarchical house effects per pollster and a noise term that combines sample size with a "
                  "party-specific excess variance. Seats are simulated by proportional swing from each party's 2023 "
                  "provincial share and calibrated provincial noise. Regional surveys (CEO in Catalonia, the Basque "
                  "Sociómetro, CIS subsamples in Galicia) then pull the peripheral parties' regional shares toward "
                  "them. The 29N ballots follow the lists proclaimed on 3 November: Frente Amplio here includes "
                  "Compromís-Front Valencià and its joint lists in Canarias and Baleares; Podemos has no share in the "
                  "ten provinces where it has no list (Catalonia, where its candidates run with ERC, the Valencian "
                  "provinces, Canarias and Baleares); UPN runs with PP. D'Hondt is applied in the 52 districts (3 % "
                  "threshold; Ceuta and Melilla by plurality). Sampling: NUTS, 4 chains x 1,000 draws, {divergences} "
                  "divergences, R-hat {rhat}.",
        "footer": "{author}{links} · Sources: Ministerio del Interior (results, reuse under Ley 37/2007), Wikipedia "
                  "(polls, CC BY-SA 4.0), CIS (cis.es, CC BY 4.0), CEO (Generalitat de Catalunya), Basque Government "
                  "(Sociómetro). Generated by <code>electoral report</code>; full code, tests, data dictionary and "
                  "methods note in the repository.",
        "th_party": ["party", "vote at cut-off, median", "vote on {h}, 90 %", "seats, split left (base)",
                     "seats, merged left"],
        "th_prob": ["event", "at cut-off", "{h}, split", "{h}, merged"],
        "th_score": ["method", "vote MAE (pp)", "vote CRPS (pp)", "90 % vote coverage", "seat MAE",
                     "90 % seat coverage", "Brier"],
        "methods": ["this model", "30-day poll average", "last election result"], "na": "n/a",
        "prob_events": {
            "Right (PP+Vox+UPN+SALF) >= 176": "PP + Vox (+ UPN, SALF) ≥ 176",
            "PP+Vox >= 176": "PP + Vox ≥ 176",
            "PP largest party": "PP largest party",
            "2023 investiture bloc (above + PNV + Junts) >= 176": "2023 investiture bloc ≥ 176",
            "Left + peripheral left (PSOE+Sumar/FA+Podemos+ERC+Bildu+BNG+CC+Compromís+AA) >= 176":
                "Left + peripheral left ≥ 176",
            "PP >= 176 alone": "PP ≥ 176", "VOX >= 50 seats": "Vox ≥ 50", "PSOE >= 100 seats": "PSOE ≥ 100",
            "PSOE >= 121 seats": "PSOE ≥ 121 (its 2023 seats)", "SUMAR >= 10 seats": "Frente Amplio ≥ 10",
            "PODEMOS >= 1 seats": "Podemos ≥ 1", "SALF >= 1 seats": "SALF ≥ 1"},
        "polls": "polls", "seat_axis": "seats", "seats_on": "{scenario}",
        "hover_seats": "{p}: %{{y}} seats",
        "range": ["3 months", "1 year", "All"],
    },
    "es": {
        "html_lang": "es",
        "page_title": "Previsión de las elecciones generales en España",
        "h1": "Previsión de las elecciones generales del {election}",
        "subtitle": "Modelo bayesiano de agregación de encuestas y proyección de escaños, con backtest sobre cuatro "
                    "elecciones",
        "byline": "Por <b>{author}</b>{links} · datos hasta el {cutoff} · última encuesta: {last_poll} · "
                  "<a href='../index.html'>English version</a>",
        "note": "<b>{provisional}.</b> Todo lo que aparece en esta página depende de las {n_polls} encuestas de "
                "{n_pollsters} encuestadoras publicadas hasta el <b>{cutoff}</b>, {ahead} antes de la "
                "votación. Son probabilidades del modelo, no predicciones del resultado; el backtest de más abajo "
                "muestra cuánto se ha equivocado antes este mismo método.",
        "card_vote": "Voto {party}, {h}", "card_major": "Mayoría de PP + Vox (+UPN, SALF)",
        "card_major_s": "listas separadas; {p} con lista única de la izquierda", "card_bt": "Error de voto en el backtest",
        "card_bt_s": "error absoluto medio, 4 elecciones, a 30 días",
        "h2_congress": "El Congreso el {h_long}",
        "figure": "Figura",
        "fig1": "Escaños esperados en el Congreso el {h_long}, y quién podría gobernar",
        "h2_votes": "Voto y escaños",
        "fig2": "Estimación de voto desde las elecciones de julio de 2023: todas las encuestas y la tendencia latente",
        "fig2_cap": "Líneas: mediana de la estimación de voto, con su banda del 90 %; puntos: cada encuesta. Pulsa un "
                    "partido en la leyenda para mostrarlo u ocultarlo; los partidos de ámbito autonómico están ocultos "
                    "al abrir la página. Los números del eje horizontal señalan los acontecimientos de la leyenda; la "
                    "línea discontinua es el cierre de datos. Arrastra para ampliar o usa los botones de encima del "
                    "gráfico; con doble clic se vuelve a la vista inicial.",
        "events": "Acontecimientos",
        "fig3": "Escaños el {h_long} en los dos escenarios de oferta electoral",
        "fig3_cap": "Cajas: mediana e intervalos del 50 % y del 90 % de 10.000 simulaciones de escaños. La línea "
                    "horizontal es la mayoría absoluta de 176 escaños.",
        "h2_history": "Los partidos desde 1977",
        "fig4": "Voto de cada partido en las elecciones generales desde 1977 y previsión del {h_long}",
        "fig4_cap": "Puntos: elecciones generales, % del voto válido (Ministerio del Interior). Cada línea va de la "
                    "primera elección de un partido a la última, a través de sus cambios de nombre (AP y PP, HB y EH "
                    "Bildu, CiU y Junts); un aspa marca la última elección de un partido desaparecido y un enlace "
                    "punteado, un partido que se integró en otro (IU en Unidos Podemos, Unidas Podemos en Sumar). Los "
                    "círculos huecos de la derecha son la previsión del 29-N con su intervalo del 90 %. La franja de "
                    "arriba indica quién gobernaba; los números bajo el eje marcan las fechas de la clave. Pulsa un "
                    "partido en la leyenda para ocultarlo; arrastra para ampliar y haz doble clic para volver.",
        "gov": "Presidente del Gobierno", "panel_state": "Partidos de ámbito estatal",
        "panel_periph": "Partidos nacionalistas y regionalistas", "seats_w": "escaños", "fc_w": "previsión",
        "h2_tables": "Tablas resumen", "h3_party": "Por partido", "h3_prob": "Probabilidades",
        "prob_note": "≥ 176: mayoría absoluta de escaños. Bloque de la investidura de 2023: PSOE, Sumar / Frente "
                     "Amplio, Podemos, ERC, EH Bildu, BNG, CC, Adelante Andalucía, PNV y Junts. Izquierda + izquierda "
                     "periférica: los mismos sin PNV ni Junts. «Separadas» y «única» se refieren a las listas de la "
                     "izquierda el {h}.",
        "h3_score": "Resultados del backtest (media de 2016, abril de 2019, noviembre de 2019 y 2023)",
        "score_note": "Previsiones hechas 30 días antes de cada elección solo con las encuestas disponibles entonces. "
                      "Los intervalos de voto del 90 % del modelo cubrieron el {cover} % de los resultados, por lo que "
                      "la proyección al día de la votación añade un error del {infl} % del voto de cada partido, el "
                      "valor más pequeño que habría devuelto la cobertura al 90 %; se probó la reversión a la media "
                      "hacia el último resultado ({reversion}). La capa de encuestas regionales solo entra en el "
                      "backtest para Cataluña en 2023 (CEO), el único caso con datos regionales.",
        "adopted": "adoptada", "rejected": "descartada",
        "h2_method": "El método en un párrafo",
        "method": "Los resultados oficiales de 1977-2023 proceden del Ministerio del Interior; las encuestas, de las "
                  "tablas de sondeos de Wikipedia (CC BY-SA 4.0); el CIS, directamente de cis.es: su estimación oficial "
                  "como una serie y nuestra reestimación a partir de sus microdatos (recuerdo de voto de 2023, "
                  "votantes probables) como otra, y las series construidas con una misma encuesta se reparten su "
                  "tamaño muestral. Las publicaciones de una encuestadora con trabajo de campo solapado (trackings "
                  "diarios, paneles acumulados) cuentan una sola vez. El agregador es un modelo de espacio de estados "
                  "sobre una rejilla semanal: el voto de cada partido sigue un paseo aleatorio en escala logit, "
                  "anclado en el resultado de julio de 2023, con efectos de casa jerárquicos por encuestadora y un "
                  "término de ruido que combina el tamaño muestral con una varianza adicional propia de cada partido. "
                  "Los escaños se simulan con una variación proporcional sobre el voto provincial de cada partido en "
                  "2023 y un ruido provincial calibrado. Las encuestas regionales (CEO en Cataluña, Sociómetro Vasco, "
                  "submuestras del CIS en Galicia) acercan después a sus datos el voto regional de los partidos "
                  "periféricos. Las papeletas del 29-N siguen las candidaturas proclamadas el 3 de noviembre: Frente "
                  "Amplio incluye aquí a Compromís-Front Valencià y sus listas conjuntas en Canarias y Baleares; "
                  "Podemos no tiene voto en las diez provincias donde no presenta lista (Cataluña, donde sus "
                  "candidatos van con ERC, las provincias valencianas, Canarias y Baleares); UPN concurre con el PP. "
                  "Se aplica D'Hondt en las 52 circunscripciones (barrera del 3 %; Ceuta y Melilla, por mayoría "
                  "simple). Muestreo: NUTS, 4 cadenas x 1.000 extracciones, {divergences} divergencias, R-hat {rhat}.",
        "footer": "{author}{links} · Fuentes: Ministerio del Interior (resultados, reutilización según la Ley 37/2007), "
                  "Wikipedia (encuestas, CC BY-SA 4.0), CIS (cis.es, CC BY 4.0), CEO (Generalitat de Catalunya), "
                  "Gobierno Vasco (Sociómetro). Generado con <code>electoral report</code>; el código completo, los "
                  "tests, el diccionario de datos y la nota metodológica (en inglés) están en el repositorio.",
        "th_party": ["partido", "voto al cierre de datos, mediana", "voto el {h}, 90 %",
                     "escaños, listas separadas (base)", "escaños, lista única"],
        "th_prob": ["suceso", "al cierre de datos", "{h}, separadas", "{h}, única"],
        "th_score": ["método", "EAM de voto (pp)", "CRPS de voto (pp)", "cobertura del 90 %, voto", "EAM de escaños",
                     "cobertura del 90 %, escaños", "Brier"],
        "methods": ["este modelo", "media de encuestas de 30 días", "resultado de la elección anterior"], "na": "n. d.",
        "prob_events": {
            "Right (PP+Vox+UPN+SALF) >= 176": "PP + Vox (+ UPN, SALF) ≥ 176",
            "PP+Vox >= 176": "PP + Vox ≥ 176",
            "PP largest party": "PP, primera fuerza",
            "2023 investiture bloc (above + PNV + Junts) >= 176": "Bloque de la investidura de 2023 ≥ 176",
            "Left + peripheral left (PSOE+Sumar/FA+Podemos+ERC+Bildu+BNG+CC+Compromís+AA) >= 176":
                "Izquierda + izquierda periférica ≥ 176",
            "PP >= 176 alone": "PP ≥ 176", "VOX >= 50 seats": "Vox ≥ 50", "PSOE >= 100 seats": "PSOE ≥ 100",
            "PSOE >= 121 seats": "PSOE ≥ 121 (sus escaños de 2023)", "SUMAR >= 10 seats": "Frente Amplio ≥ 10",
            "PODEMOS >= 1 seats": "Podemos ≥ 1", "SALF >= 1 seats": "SALF ≥ 1"},
        "polls": "encuestas", "seat_axis": "escaños", "seats_on": "{scenario}",
        "hover_seats": "{p}: %{{y}} escaños",
        "range": ["3 meses", "1 año", "Todo"],
    },
}



def _ahead(weeks: float, lang: str) -> str:
    """'six days' / 'seis días' under two weeks, else 'about N weeks' / 'unas N semanas'."""
    days = round(weeks * 7)
    if days < 14:
        en = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
              "eleven", "twelve", "thirteen"]
        es = ["cero", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
              "once", "doce", "trece"]
        return (f"{en[days]} day{'s' if days != 1 else ''}" if lang == "en"
                else f"{es[days]} día{'s' if days != 1 else ''}")
    return f"about {weeks:.0f} weeks" if lang == "en" else f"unas {weeks:.0f} semanas"

def _hex_rgba(h: str, a: float) -> str:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def _pct(p: float) -> str:
    if p > 0.995:
        return "&gt; 99 %"
    if p < 0.005:
        return "&lt; 1 %"
    return f"{100 * p:.0f} %"


def _table(headers: list[tuple[str, bool]], rows: list[list], highlight: set[int] | None = None,
           cls: str = "") -> str:
    th = "".join(f"<th class='{'num' if n else ''}'>{h}</th>" for h, n in headers)
    body = []
    for i, r in enumerate(rows):
        hl = " class='hl'" if highlight and i in highlight else ""
        tds = "".join(f"<td class='{'num' if headers[j][1] else ''}'>{c}</td>" for j, c in enumerate(r))
        body.append(f"<tr{hl}>{tds}</tr>")
    return f"<table class='{cls}'><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _layout(fig: go.Figure, **kw) -> go.Figure:
    fig.update_layout(template="plotly_white", font={"family": FONT, "size": 14, "color": "#1e2430"},
                      separators=",." if i18n.get_lang() == "es" else ".,", **kw)
    return fig


def _to_html(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"locale": i18n.get_lang(), "displaylogo": False})


def trend_figure(trend: pd.DataFrame, polls: pd.DataFrame, parties: list[str], cutoff: str, events: list[dict],
                 T: dict) -> go.Figure:
    """Latent share with its 90 % band and every poll; events as numbered lines on the x axis."""
    fig = go.Figure()
    for p in parties:
        c = COLORS.get(p, "#444444")
        t = trend[trend.party == p]
        vis = True if p in ("PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF") else "legendonly"
        pp = polls[polls.party == p]
        nm = i18n.name(p)
        fig.add_trace(go.Scatter(x=pp.fieldwork_end, y=pp.value, mode="markers", name=f"{nm} {T['polls']}",
                                 marker={"color": _hex_rgba(c, 0.35), "size": 5}, legendgroup=p,
                                 showlegend=False, visible=vis,
                                 hovertemplate="%{text}<br>%{x|%d %b %Y}: %{y:.1f} %<extra></extra>",
                                 text=pp.pollster))
        fig.add_trace(go.Scatter(x=pd.concat([t.date, t.date[::-1]]), y=100 * pd.concat([t.q95, t.q05[::-1]]),
                                 fill="toself", fillcolor=_hex_rgba(c, 0.12), line={"width": 0},
                                 legendgroup=p, showlegend=False, hoverinfo="skip", visible=vis))
        fig.add_trace(go.Scatter(x=t.date, y=100 * t.q50, mode="lines", name=nm, line={"color": c, "width": 2},
                                 legendgroup=p, visible=vis,
                                 hovertemplate=nm + " %{x|%d %b %Y}: %{y:.1f} %<extra></extra>"))
    fig.add_vline(x=pd.Timestamp(cutoff).timestamp() * 1000, line={"dash": "dash", "color": "black", "width": 1})
    # events: a dotted line each and its number in a strip under the axis line, on three rows so that
    # neighbours a few days apart stay readable; the names are in the HTML key under the chart
    prev_x, row = None, 0
    for e in events:
        fig.add_vline(x=e["date"].timestamp() * 1000, line={"dash": "dot", "color": "#777", "width": 1})
        row = (row + 1) % 3 if prev_x is not None and (e["date"] - prev_x).days < 40 else 0
        fig.add_annotation(x=e["date"], y=-0.012 - 0.05 * row, xref="x", yref="paper", text=f"<b>{e['n']}</b>",
                           showarrow=False, yanchor="top", xanchor="center", font={"size": 12, "color": "#1e2430"},
                           bgcolor="#ffffff", bordercolor="#777777", borderwidth=1, borderpad=1,
                           hovertext=f"{e['n']} · {e['label']} ({i18n.date(e['date'], short=True)})")
        prev_x = e["date"]
    r3, r12, rall = T["range"]
    fig.update_xaxes(ticks="outside", ticklen=66, tickcolor="rgba(0,0,0,0)", showline=True, linecolor="#1e2430",
                     range=[trend.date.min() - pd.Timedelta(days=20), pd.Timestamp(cutoff) + pd.Timedelta(days=25)],
                     rangeselector={"buttons": [{"count": 3, "step": "month", "stepmode": "backward", "label": r3},
                                                {"count": 1, "step": "year", "stepmode": "backward", "label": r12},
                                                {"step": "all", "label": rall}],
                                    "x": 1, "xanchor": "right", "y": 1.12, "yanchor": "bottom"})
    fig.update_yaxes(title_text=tr("% of valid vote"), rangemode="tozero")
    return _layout(fig, height=560, legend={"orientation": "h", "x": 0, "xanchor": "left", "y": 1.02,
                                            "yanchor": "bottom", "bgcolor": "#f7f8fa", "bordercolor": "#c9ced6",
                                            "borderwidth": 1},
                   margin={"l": 60, "r": 30, "t": 90, "b": 60})


def seats_figure(scenarios: list[tuple[str, pd.DataFrame]], T: dict) -> go.Figure:
    """Seat ranges per party (median, 50 % and 90 % intervals), one panel per scenario."""
    fig = make_subplots(rows=1, cols=len(scenarios), subplot_titles=[s for s, _ in scenarios], shared_yaxes=True,
                        horizontal_spacing=0.04)
    for col, (_, sd) in enumerate(scenarios, 1):
        for p in ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "ERC", "JUNTS", "BILDU", "PNV"]:
            q = sd[p].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).values   # summary stats only: keeps the HTML small
            nm = i18n.name(p, short=True)
            fig.add_trace(go.Box(name=nm, x=[nm], q1=[q[1]], median=[q[2]], q3=[q[3]], lowerfence=[q[0]],
                                 upperfence=[q[4]], marker={"color": COLORS.get(p, "#444")}, showlegend=False,
                                 hovertemplate=T["hover_seats"].format(p=nm) + "<extra></extra>"), row=1, col=col)
        fig.add_hline(y=176, line={"color": "black", "width": 1}, row=1, col=col)
    fig.update_yaxes(title_text=T["seat_axis"], row=1, col=1)
    return _layout(fig, height=400, margin={"l": 60, "r": 30, "t": 40, "b": 40})


def history_figure(T: dict, h: str) -> tuple[go.Figure, str]:
    """Parties since 1977 (``electoral.history``) as an interactive chart, and the HTML key of its dates."""
    from electoral import history as H

    lang = i18n.get_lang()
    hist, fc = H.load(), H.forecast()
    fdate = pd.Timestamp(H.FORECAST_DATE)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.07,
                        subplot_titles=[T["panel_state"], T["panel_periph"]])
    pct = lambda v: i18n.num(v)  # noqa: E731
    lineages = [(lid, panel) for lid, _, _, panel in H.LINEAGES] + [("SALF", "state")]
    for lid, panel in lineages:
        row, c, nm = (1 if panel == "state" else 2), H.COLOR[lid], H.NAME[lid]
        legend = nm + (f" ({H.ENDS[lid][lang]})" if lid in H.ENDS else "")
        first = True
        for g in (H.segments(hist, lid) if lid in set(hist.lineage) else []):
            text = [f"<b>{nm}</b> · {d.year} ({r}): {pct(v)} % · {n} {T['seats_w']}"
                    for d, r, v, n in zip(g.date, g.ran_as, g.share, g.seats)]
            fig.add_trace(go.Scatter(x=g.date, y=g.share, mode="lines+markers", name=legend, legendgroup=lid,
                                     showlegend=first, line={"color": c, "width": 2.4}, marker={"size": 6},
                                     text=text, hovertemplate="%{text}<extra></extra>"), row=row, col=1)
            first = False
        h_ = hist[hist.lineage == lid].sort_values("date")
        if lid in fc.index:
            f = fc.loc[lid]
            if len(h_):
                fig.add_trace(go.Scatter(x=[h_.date.iloc[-1], fdate], y=[h_.share.iloc[-1], f.q50], mode="lines",
                                         line={"color": c, "width": 1.6, "dash": "dash"}, legendgroup=lid,
                                         showlegend=False, hoverinfo="skip"), row=row, col=1)
            fig.add_trace(go.Scatter(
                x=[fdate], y=[f.q50], mode="markers", name=legend, legendgroup=lid, showlegend=first,
                marker={"size": 9, "color": "white", "line": {"color": c, "width": 2}},
                error_y={"type": "data", "symmetric": False, "array": [f.q95 - f.q50], "arrayminus": [f.q50 - f.q05],
                         "color": c, "thickness": 1.6, "width": 0},
                text=[f"<b>{nm}</b> · {h} ({T['fc_w']}): {pct(f.q50)} % (90 %: {pct(f.q05)}-{pct(f.q95)}) · "
                      f"{int(f.seats)} {T['seats_w']}"], hovertemplate="%{text}<extra></extra>"), row=row, col=1)
        elif lid in H.ENDS and len(h_):
            last = h_.iloc[-1]
            fig.add_trace(go.Scatter(x=[last.date], y=[last.share], mode="markers", legendgroup=lid, showlegend=False,
                                     marker={"symbol": "x", "size": 11, "color": c, "line": {"color": "white", "width": 1}},
                                     hoverinfo="skip"), row=row, col=1)
    for src, dst in H.LINKS:
        a = hist[hist.lineage == src].sort_values("date").iloc[-1]
        b = hist[hist.lineage == dst].sort_values("date").iloc[0]
        fig.add_trace(go.Scatter(x=[a.date, b.date], y=[a.share, b.share], mode="lines", legendgroup=dst,
                                 showlegend=False, line={"color": H.COLOR[dst], "width": 1.3, "dash": "dot"},
                                 hoverinfo="skip"), row=1, col=1)
    # heads of government: a band of coloured blocks over the top panel
    starts = [pd.Timestamp(d) for _, _, d in H.GOVERNMENTS] + [fdate]
    for (who, party, _), a, b in zip(H.GOVERNMENTS, starts[:-1], starts[1:]):
        fig.add_shape(type="rect", xref="x", yref="paper", x0=a, x1=b, y0=1.06, y1=1.11,
                      fillcolor=H.COLOR[party], opacity=0.85, line={"color": "white", "width": 1})
        fig.add_annotation(x=a + (b - a) / 2, y=1.085, xref="x", yref="paper", showarrow=False, yanchor="middle",
                           text=f"<b>{who if (b - a).days > 1000 else who[0] + '.'}</b>", font={"color": "white", "size": 12},
                           hovertext=f"{who} ({party}), {i18n.date(a, short=True)}")
    fig.add_annotation(x=0, y=1.115, xref="paper", yref="paper", showarrow=False, xanchor="left", yanchor="bottom",
                       text=T["gov"], font={"size": 12, "color": "#5b6473"})
    # key dates: a dotted line each, and its number under the bottom axis (names in the HTML key)
    key = []
    for n, (d, lab) in enumerate(H.EVENTS, 1):
        d = pd.Timestamp(d)
        fig.add_vline(x=d.timestamp() * 1000, line={"dash": "dot", "color": "#777", "width": 1})
        fig.add_annotation(x=d, y=-0.03 - (0.045 if n > 1 and (d - pd.Timestamp(H.EVENTS[n - 2][0])).days < 300 else 0),
                           xref="x", yref="paper", text=f"<b>{n}</b>", showarrow=False, yanchor="top",
                           font={"size": 12, "color": "#1e2430"}, bgcolor="#ffffff", bordercolor="#777777",
                           borderwidth=1, borderpad=1, hovertext=f"{n} · {lab[lang]} ({i18n.date(d, short=True)})")
        key.append(f"<span><span class='n'>{n}</span>{lab[lang]} <span class='d'>· {i18n.date(d, short=True)}</span></span>")
    fig.add_vline(x=fdate.timestamp() * 1000, line={"dash": "dash", "color": "black", "width": 1})
    fig.update_xaxes(range=[pd.Timestamp("1976-09-01"), pd.Timestamp("2027-09-01")], showline=True,
                     linecolor="#1e2430", dtick="M60", tickformat="%Y")
    fig.update_xaxes(ticks="outside", ticklen=48, tickcolor="rgba(0,0,0,0)", row=2, col=1)
    fig.update_yaxes(title_text=tr("% of valid vote"), rangemode="tozero")
    fig.update_yaxes(range=[0, 51], row=1, col=1)
    fig.update_yaxes(range=[0, 5.8], row=2, col=1)
    for a in fig.layout.annotations[:2]:          # the panel titles, left-aligned
        a.update(x=0, xanchor="left", font={"size": 13, "color": "#5b6473"})
    fig = _layout(fig, height=760, hovermode="closest",
                  legend={"orientation": "h", "x": 0, "xanchor": "left", "y": 1.155, "yanchor": "bottom",
                          "bgcolor": "#f7f8fa", "bordercolor": "#c9ced6", "borderwidth": 1, "font": {"size": 12}},
                  margin={"l": 60, "r": 30, "t": 205, "b": 70})
    return fig, f"<div class='key'><span class='t'>{T['events']}</span>{''.join(key)}</div>"


def build(cfg: dict) -> str:
    """The page in the current language (``i18n.set_lang``), as an HTML string."""
    lang = i18n.get_lang()
    T = TEXT[lang]
    out = ROOT / cfg["paths"]["outputs"]
    cutoff = cfg["cutoff_date"]
    fc = json.loads((out / "forecast_29n.json").read_text())
    h = i18n.date(fc["horizon"], year=False, short=True) if lang == "en" else "29-N"
    h_long = i18n.date(fc["horizon"])
    provisional = cfg.get(f"provisional_label_{lang}") or cfg.get("provisional_label", "")
    scen = {k: tr(v["label"]) for k, v in cfg["seats"]["scenarios"].items()}
    author = cfg.get("author", {})
    trend = pd.read_parquet(out / "poll_average_daily_next.parquet")
    trend = trend[trend.date.dt.dayofweek == pd.Timestamp(cutoff).dayofweek].round(4)   # weekly nodes keep the page light
    polls = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "polls_long.parquet")
    polls = polls[(polls.cycle == "next") & (~polls.is_election) & polls.value.notna()]
    seats_dl = pd.read_parquet(out / "seat_draws_29n_split.parquet")
    seats_mg = pd.read_parquet(out / "seat_draws_29n_merged.parquet")
    probs_now = pd.read_csv(out / "seat_probabilities_next.csv")
    probs_dl = pd.read_csv(out / "seat_probabilities_29n_split.csv")
    probs_mg = pd.read_csv(out / "seat_probabilities_29n_merged.csv")
    vote_dl = pd.read_csv(out / "vote_summary_29n.csv", index_col=0)
    diag = json.loads((out / "diagnostics_next.json").read_text())
    score = pd.read_csv(out / "backtest_scorecard.csv")

    parties = [p for p in ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC", "AA"]
               if p in set(trend.party)]
    # "now" = the cut-off state used by the seat simulation (same draws as the README numbers)
    sd_now = pd.read_parquet(out / "state_draws_next.parquet")
    last = sd_now.quantile([0.05, 0.5, 0.95]).T
    last.columns = ["q05", "q50", "q95"]

    # ---------------------------------------------------------------- figures
    events = i18n.events(cfg)
    hemi = pactometro_fragment(cfg, lang)
    fig_trend = trend_figure(trend, polls, parties, cutoff, events, T)
    fig_seats = seats_figure([(scen["split"], seats_dl), (scen["merged"], seats_mg)], T)
    fig_hist, key_hist = history_figure(T, h)
    key = "".join(f"<span><span class='n'>{e['n']}</span>{e['label']} <span class='d'>· "
                  f"{i18n.date(e['date'], short=True)}</span></span>" for e in events)
    key = f"<div class='key'><span class='t'>{T['events']}</span>{key}</div>"

    def figure_title(n: int, key_: str) -> str:
        return f"<h3 class='fig'><span>{T['figure']} {n}.</span> {T[key_].format(h_long=h_long)}</h3>"

    # ---------------------------------------------------------------- tables
    def seat_row(sd: pd.DataFrame, p: str) -> str:
        return f"{int(sd[p].quantile(.05))} - {int(sd[p].quantile(.95))}"

    party_rows = []
    for p in parties:
        party_rows.append([i18n.name(p), num(100 * last.loc[p, "q50"]),
                           f"{num(100 * vote_dl.loc[p, 'q50'])} ({num(100 * vote_dl.loc[p, 'q05'])} - "
                           f"{num(100 * vote_dl.loc[p, 'q95'])})",
                           f"{int(seats_dl[p].median())} ({seat_row(seats_dl, p)})",
                           f"{int(seats_mg[p].median())} ({seat_row(seats_mg, p)})"])
    party_table = _table([(c.format(h=h), i > 0) for i, c in enumerate(T["th_party"])], party_rows)

    pn = probs_now.set_index("event")["probability"]
    pd_ = probs_dl.set_index("event")["probability"]
    pm = probs_mg.set_index("event")["probability"]
    prob_rows = [[label, _pct(pn.get(k, float("nan"))), _pct(pd_.get(k, float("nan"))), _pct(pm.get(k, float("nan")))]
                 for k, label in T["prob_events"].items() if k in pd_]
    prob_table = _table([(c.format(h=h), i > 0) for i, c in enumerate(T["th_prob"])], prob_rows, {0}, cls="tight")

    sc = score.groupby("method")[["vote_mae_pp", "vote_crps_pp", "vote_cover90", "seat_mae", "seat_cover90", "brier"]].mean()
    order = list(zip(["model", "poll_average_30d", "last_election"], T["methods"]))
    sc_rows = []
    for key_, label in order:
        r = sc.loc[key_]
        cov_v = f"{100 * r.vote_cover90:.0f} %" if key_ == "model" else T["na"]
        cov_s = f"{100 * r.seat_cover90:.0f} %" if key_ == "model" else T["na"]
        sc_rows.append([label, num(r.vote_mae_pp, 2), num(r.vote_crps_pp, 2), cov_v, num(r.seat_mae), cov_s,
                        num(r.brier, 2)])
    sc_table = _table([(c, i > 0) for i, c in enumerate(T["th_score"])], sc_rows, {0})

    right_dl, right_mg = pd_.get("Right (PP+Vox+UPN+SALF) >= 176"), pm.get("Right (PP+Vox+UPN+SALF) >= 176")

    def vote_card(p: str) -> str:
        r = vote_dl.loc[p]
        return (f"<div class='card'><div class='k'>{T['card_vote'].format(party=i18n.name(p), h=h)}</div>"
                f"<div class='v'>{num(100 * r.q50)} %</div>"
                f"<div class='s'>90 %: {num(100 * r.q05)} - {num(100 * r.q95)}</div></div>")

    cards = f"""<div class="cards">
 {vote_card('PP')}{vote_card('PSOE')}{vote_card('VOX')}
 <div class="card"><div class="k">{T['card_major']}</div><div class="v">{_pct(right_dl)}</div><div class="s">{T['card_major_s'].format(p=_pct(right_mg))}</div></div>
 <div class="card"><div class="k">{T['card_bt']}</div><div class="v">{num(sc.loc['model', 'vote_mae_pp'], 2)} pp</div><div class="s">{T['card_bt_s']}</div></div>
</div>"""

    gh = author.get("github")
    links = f" · <a href='{gh}' target='_blank' rel='noopener'>GitHub</a>" if gh else ""
    fill = {"author": author.get("name", ""), "links": links, "cutoff": i18n.date(cutoff),
            "last_poll": i18n.date(diag["last_poll"]), "election": h_long, "h": h, "h_long": h_long,
            "provisional": provisional, "n_polls": diag["n_polls"], "n_pollsters": diag["n_pollsters"],
            "weeks": f"{fc['weeks_ahead']:.0f}", "ahead": _ahead(fc["weeks_ahead"], lang), "cover": f"{100 * sc.loc['model', 'vote_cover90']:.0f}",
            "infl": f"{100 * fc['error_inflation']['extra_sd_relative']:.0f}",
            "reversion": T["adopted"] if fc["mean_reversion"]["chosen_weight"] else T["rejected"],
            "divergences": diag["divergences"], "rhat": num(diag["rhat_max"], 2)}
    own = ("hover_seats", "card_vote", "card_major_s", "seats_on")   # filled where they are used
    t = {k: v.format(**fill) for k, v in T.items() if isinstance(v, str) and k not in own}

    locale = f"<script>Plotly.register({json.dumps(PLOTLY_ES, ensure_ascii=False)});</script>" if lang == "es" else ""
    return f"""<!DOCTYPE html><html lang="{T['html_lang']}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t['page_title']}</title><style>{CSS % {'font': FONT}}</style>
<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js" charset="utf-8"></script>{locale}</head><body>
<h1>{t['h1']}</h1>
<p class="subtitle">{t['subtitle']}</p>
<div class='byline'>{t['byline']}</div>
<p class="note" style="border-left-color:#b00020">{t['note']}</p>
{cards}
<h2>{t['h2_congress']}</h2>
{figure_title(1, 'fig1')}
{hemi}
<h2>{t['h2_votes']}</h2>
{figure_title(2, 'fig2')}
{_to_html(fig_trend)}
{key}
<p class="small">{t['fig2_cap']}</p>
{figure_title(3, 'fig3')}
{_to_html(fig_seats)}
<p class="small">{t['fig3_cap']}</p>
<h2>{t['h2_history']}</h2>
{figure_title(4, 'fig4')}
{_to_html(fig_hist)}
{key_hist}
<p class="small">{t['fig4_cap']}</p>
<h2>{t['h2_tables']}</h2>
<h3>{t['h3_party']}</h3>
{party_table}
<div class="cols">
<div><h3>{t['h3_prob']}</h3>{prob_table}
<p class="small">{t['prob_note']}</p></div>
<div><h3>{t['h3_score']}</h3>{sc_table}
<p class="small">{t['score_note']}</p></div>
</div>
<h2>{t['h2_method']}</h2>
<p>{t['method']}</p>
<footer>{t['footer']}</footer>
</body></html>"""


def main(lang: str = "all") -> None:
    cfg = load_config()
    for code in (i18n.LANGS if lang == "all" else (lang,)):
        i18n.set_lang(code)
        try:
            html = build(cfg)
        finally:
            i18n.set_lang("en")
        # docs/ is served by GitHub Pages: English at the root, Spanish under es/
        targets = [(ROOT / "docs" / "index.html", html)] if code == "en" else [
            (ROOT / "docs" / "es" / "index.html", html),
            # copy next to the Spanish README; its language link goes back to docs/
            (ROOT / i18n.ES_DIR / "index.html",
             html.replace("<a href='../index.html'>English version</a>",
                          "<a href='../docs/index.html'>English version</a>")),
        ]
        for path, text in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()

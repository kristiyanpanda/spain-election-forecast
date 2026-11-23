"""Two languages for figures and the report page: English (default) and Spanish.

English strings are the keys: ``tr("seats")`` returns ``"escaños"`` when the language is ``es``
and the string itself otherwise, so the code reads the same as before. Numbers use a decimal
comma in Spanish (``num``). Spanish outputs go to their own folder (``out_dir``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from electoral import ROOT

LANGS = ("en", "es")
_lang = "en"

ES_DIR = "spanish version"          # folder with the Spanish README, page and figures

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
           "octubre", "noviembre", "diciembre"],
}
MONTHS_SHORT = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
}

# display names of the canonical party ids (the same in both languages unless listed in ES_NAMES)
NAMES = {"PP": "PP", "PSOE": "PSOE", "VOX": "Vox", "SUMAR": "Sumar / Frente Amplio", "PODEMOS": "Podemos",
         "SALF": "SALF", "ERC": "ERC", "JUNTS": "Junts", "BILDU": "EH Bildu", "PNV": "PNV", "BNG": "BNG",
         "CC": "CC", "AA": "Adelante Andalucía", "UPN": "UPN", "OTHER": "Others", "UP": "Unidos Podemos",
         "CS": "Cs", "IU": "IU"}
ES_NAMES = {"OTHER": "Otros"}
SHORT_NAMES = {"SUMAR": "Frente Amplio"}      # where space is tight (labels at the end of a line)

ES = {
    # ------------------------------------------------------------------ stamps and common axes
    "Data cut-off {cutoff}. {source}": "Datos hasta el {cutoff}. {source}",
    "% of valid vote": "% del voto válido",
    "seats": "escaños",
    # ------------------------------------------------------------------ trend charts
    "State-wide parties since the July 2023 election: polls and latent trend":
        "Partidos de ámbito estatal desde las elecciones de julio de 2023: encuestas y tendencia latente",
    "Main regional parties: polls and latent trend":
        "Principales partidos de ámbito autonómico: encuestas y tendencia latente",
    "Since the July 2023 election": "Desde las elecciones de julio de 2023",
    "Zoom: {start} to {end}": "Ampliación: del {start} al {end}",
    "zoom": "ampliación",
    "cut-off": "cierre de datos",
    "Polls: Wikipedia (CC BY-SA 4.0) and CIS (cis.es); model: logit random walk + house effects.":
        "Encuestas: Wikipedia (CC BY-SA 4.0) y CIS (cis.es); modelo: paseo aleatorio logit + efectos de casa.",
    # ------------------------------------------------------------------ parties since 1977 (electoral.history)
    "Head of government": "Presidente del Gobierno",
    "State-wide parties": "Partidos de ámbito estatal",
    "Nationalist and regional parties": "Partidos nacionalistas y regionalistas",
    "Spanish parties since 1977: vote share at every general election":
        "Los partidos en España desde 1977: voto en cada elección general",
    "Dots: general elections (share of the valid vote, Ministry of the Interior); hollow dot and bar: 29 Nov forecast, "
    "median and 90 % interval; cross: last election of a party that is gone; dotted links: a party that went into "
    "another.":
        "Puntos: elecciones generales (% del voto válido, Ministerio del Interior); círculo hueco y barra: previsión "
        "del 29-N, mediana e intervalo del 90 %; aspa: última elección de un partido desaparecido; enlaces "
        "punteados: un partido que se integró en otro.",
    "Gaps: HB called for abstention in 2000; Batasuna was banned in 2004 and 2008.":
        "Huecos: HB pidió la abstención en 2000; Batasuna estaba ilegalizada en 2004 y 2008.",
    "Line: median of the latent share; bands: 50 % and 90 %; dots: polls; diamonds: 2023 result.":
        "Línea: mediana de la estimación; bandas: 50 % y 90 %; puntos: encuestas; rombos: resultado de 2023.",
    # ------------------------------------------------------------------ house effects
    "pp vs. average pollster": "pp respecto a la encuestadora media",
    "House effects: how far each pollster sits from the pollster average (90 % interval)":
        "Efectos de casa: distancia de cada encuestadora a la media de encuestadoras (intervalo del 90 %)",
    "Zero-sum across pollsters per party; number of polls in brackets.":
        "Suma cero entre encuestadoras para cada partido; número de encuestas entre paréntesis.",
    # ------------------------------------------------------------------ seat distributions
    "{party}: {lo}-{hi} (median {med})": "{party}: {lo}-{hi} (mediana {med})",
    "Seat distributions (90 % interval); dotted = 2023 result":
        "Distribución de escaños (intervalo del 90 %); línea de puntos = resultado de 2023",
    "Monte Carlo over posterior vote shares and provincial swing noise; D'Hondt in 52 districts.":
        "Monte Carlo sobre el voto estimado y el ruido provincial; D'Hondt en 52 circunscripciones.",
    # ------------------------------------------------------------------ backtest
    "model 90 % interval": "intervalo del 90 % del modelo",
    "model median": "mediana del modelo",
    "30-day poll average": "media de encuestas de 30 días",
    "last election": "elección anterior",
    "actual": "resultado",
    "Backtest: forecasts made 30 days before each election vs. the result":
        "Backtest: previsiones hechas 30 días antes de cada elección frente al resultado",
    "Only polls available at the time; anchored on the previous election.":
        "Solo con las encuestas disponibles entonces; anclado en la elección anterior.",
    "June 2016": "Junio de 2016", "April 2019": "Abril de 2019", "November 2019": "Noviembre de 2019",
    "July 2023": "Julio de 2023",
    # ------------------------------------------------------------------ blocs
    "Right (PP+Vox+UPN+SALF)": "Derecha (PP+Vox+UPN+SALF)",
    "2023 investiture bloc (above + PNV + Junts)": "Bloque de la investidura de 2023",
    "{name}: P(>=176) = {p}": "{name}: P(≥176) = {p}",
    " 176 = absolute majority": " 176 = mayoría absoluta",
    "Others": "Otros",
    "Bloc seat totals": "Escaños por bloque",
    "Blocs defined in data/party_map_polls.yaml.": "Bloques definidos en data/party_map_polls.yaml.",
    # ------------------------------------------------------------------ hemicycle
    "Forecast Congress, {date}": "Congreso previsto, {date}",
    "Expected seats, {scenario}: mean of {n} simulations, rounded to 350.\nOthers: local lists "
    "(Soria ¡Ya!, Teruel Existe, UPL).":
        "Escaños esperados, {scenario}: media de {n} simulaciones, redondeada a 350.\nOtros: candidaturas "
        "locales (Soria ¡Ya!, Teruel Existe, UPL).",
    "Seats: model forecast, not a result.": "Escaños: previsión del modelo, no un resultado.",
    "Split left (base case)": "Izquierda en listas separadas (caso base)",
    "Merged left (sensitivity)": "Izquierda en lista única (sensibilidad)",
    # ------------------------------------------------------------------ descriptive figures
    "Source: Ministerio del Interior (results 1977-2023), computed in src/electoral/indices.py.":
        "Fuente: Ministerio del Interior (resultados 1977-2023), calculado en src/electoral/indices.py.",
    "turnout, %": "participación, %",
    "Turnout and fragmentation in Congreso elections, 1977-2023":
        "Participación y fragmentación en las elecciones al Congreso, 1977-2023",
    "ENP (votes)": "NEP (votos)", "ENP (seats)": "NEP (escaños)",
    "effective number of parties": "número efectivo de partidos",
    "2015-16: the two-party system breaks\n(Podemos, Ciudadanos enter)":
        "2015-16: se rompe el bipartidismo\n(entran Podemos y Ciudadanos)",
    "2023: ENP votes {v}, seats {s}": "2023: NEP votos {v}, escaños {s}",
    "between blocs": "entre bloques", "within blocs": "dentro de los bloques",
    "Pedersen volatility, pp": "volatilidad de Pedersen, pp",
    "max: {v} pp": "máx.: {v} pp",
    "Electoral volatility between consecutive elections, split within / between blocs":
        "Volatilidad electoral entre elecciones consecutivas, dentro de los bloques y entre ellos",
    " Blocs: left, right, peripheral left, peripheral right, other.":
        " Bloques: izquierda, derecha, izquierda periférica, derecha periférica, otros.",
    "Bloc matrix: vote share of the four blocs, 1977-2023":
        "Matriz de bloques: voto de los cuatro bloques, 1977-2023",
    "left": "izquierda", "right": "derecha", "periph_left": "izquierda periférica",
    "periph_right": "derecha periférica", "other": "otros",
    "vote share of peripheral (regionalist / nationalist) lists, %":
        "voto a candidaturas periféricas (regionalistas / nacionalistas), %",
    "ENP (votes) in the province, 2023": "NEP (votos) en la provincia, 2023",
    "Regional fragmentation, 2023: where the peripheral vote lives":
        "Fragmentación territorial, 2023: dónde está el voto periférico",
    # ------------------------------------------------------------------ chamber comparison (chamber.py)
    "Congress at the dissolution ({date})": "El Congreso en la disolución ({date})",
    "2023 investiture bloc {a}  ·  PP + Vox + UPN + ex-Vox {b}":
        "Bloque de investidura de 2023: {a}  ·  PP + Vox + UPN + ex-Vox: {b}",
    "2023 investiture bloc {a}  ·  PP + Vox (+ UPN, SALF) {b}":
        "Bloque de investidura de 2023: {a}  ·  PP + Vox (+ UPN, SALF): {b}",
    "arc: 2023 investiture bloc": "arco: bloque de investidura de 2023",
    "arc: PP + Vox and allies": "arco: PP + Vox y aliados",
    "From the Congress that invested Sánchez to the 29 November forecast":
        "Del Congreso que invistió a Sánchez a la previsión del 29 de noviembre",
    "Left: seats by party on the last day of the full chamber, from each group's membership dates on "
    "congreso.es. Right: expected seats, base case (mean of 10,000 simulations, rounded to 350). "
    "Legend: dissolution → forecast.":
        "Izquierda: escaños por partido el último día del pleno completo, según las altas y bajas de cada "
        "grupo en congreso.es. Derecha: escaños esperados, caso base (media de 10.000 simulaciones, "
        "redondeada a 350). Leyenda: disolución → previsión.",
    "Congress: congreso.es (groups, XV Legislature). Seats: model forecast, not a result.":
        "Congreso: congreso.es (grupos, XV Legislatura). Escaños: previsión del modelo, no un resultado.",
    "2023 investiture bloc": "Bloque de investidura de 2023",
    "2023 investiture bloc + Adelante Andalucía": "Bloque de investidura de 2023 + Adelante Andalucía",
    "2023 investiture bloc without Junts": "Bloque de investidura de 2023 sin Junts",
    "Seat by seat: the chamber at the dissolution against the 29 November forecast":
        "Escaño a escaño: la cámara en la disolución frente a la previsión del 29 de noviembre",
    "Hollow dot: seats on {date} (congreso.es). Solid dot: forecast median; band: 90 % range; number: "
    "change in the median.":
        "Punto hueco: escaños el {date} (congreso.es). Punto lleno: mediana prevista; banda: rango del "
        "90 %; número: cambio en la mediana.",
    "Congress: congreso.es. Forecast: base case, 10,000 simulations.":
        "Congreso: congreso.es. Previsión: caso base, 10.000 simulaciones.",
    "CIS official estimate": "Estimación oficial del CIS",
    "Same CIS microdata, re-weighted by 2023 recall (likely voters)":
        "Los mismos microdatos del CIS, reponderados por recuerdo de 2023 (votantes probables)",
    "The CIS barometers across the legislature, read two ways":
        "Los barómetros del CIS a lo largo de la legislatura, leídos de dos maneras",
    "Dots: each barometer and pre-election study (cis.es). Diamonds: July 2023 result. Squares: model "
    "forecast for 29 November with 90 % range. Sumar line from Oct 2026: Frente Amplio + "
    "Compromís-Front Valencià.":
        "Puntos: cada barómetro y el preelectoral (cis.es). Rombos: resultado de julio de 2023. "
        "Cuadrados: previsión del modelo para el 29 de noviembre con rango del 90 %. Línea de Sumar desde "
        "octubre de 2026: Frente Amplio + Compromís-Front Valencià.",
    "Source: CIS (cis.es), estimates and microdata; re-weighting in src/electoral/cis_microdata.py.":
        "Fuente: CIS (cis.es), estimaciones y microdatos; reponderación en src/electoral/cis_microdata.py.",
}


def set_lang(lang: str) -> None:
    global _lang
    if lang not in LANGS:
        raise ValueError(f"language must be one of {LANGS}, got {lang!r}")
    _lang = lang


def get_lang() -> str:
    return _lang


def tr(text: str, **fmt) -> str:
    """Translate an English string (the key) into the current language and fill ``{fields}``."""
    out = ES.get(text, text) if _lang == "es" else text
    return out.format(**fmt) if fmt else out


def num(x: float, decimals: int = 1) -> str:
    """Number with a decimal comma in Spanish, a point in English."""
    s = f"{x:.{decimals}f}"
    return s.replace(".", ",") if _lang == "es" else s


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".") if _lang == "es" else f"{n:,}"


def name(party: str, short: bool = False) -> str:
    if short and party in SHORT_NAMES:
        return SHORT_NAMES[party]
    if _lang == "es" and party in ES_NAMES:
        return ES_NAMES[party]
    return NAMES.get(party, party)


def month(m: int, short: bool = False) -> str:
    return (MONTHS_SHORT if short else MONTHS)[_lang][m - 1]


def date(d, year: bool = True, short: bool = False) -> str:
    """'14 November 2026' / '14 de noviembre de 2026' (short: '14 Nov 2026' / '14 nov 2026')."""
    d = pd.Timestamp(d)
    if _lang == "es":
        if short:
            return f"{d.day} {month(d.month, True)}" + (f" {d.year}" if year else "")
        return f"{d.day} de {month(d.month)}" + (f" de {d.year}" if year else "")
    return f"{d.day} {month(d.month, short)}" + (f" {d.year}" if year else "")


def month_year(d, short: bool = False) -> str:
    d = pd.Timestamp(d)
    if _lang == "es" and not short:
        return f"{month(d.month)} de {d.year}"
    return f"{month(d.month, short)} {d.year}"


def events(cfg: dict) -> list[dict]:
    """Dated events of ``config.yaml`` in the current language, numbered in date order.

    Each config entry is ``date: {en: ..., es: ..., short_en: ..., short_es: ...}`` (a plain string
    is taken as the English label). ``short`` is the one-word name used on the static chart.
    """
    out = []
    for i, (day, ev) in enumerate(sorted((cfg.get("events") or {}).items()), 1):
        if isinstance(ev, str):
            ev = {"en": ev}
        label = ev.get(_lang, ev["en"])
        short = ev.get(f"short_{_lang}", ev.get("short_en", label.split()[0].strip(",")))
        out.append({"n": i, "date": pd.Timestamp(day), "label": label, "short": short})
    return out


def figures_dir(cfg: dict) -> Path:
    """Where the current language's figures go: ``reports/figures`` or ``spanish version/figures``."""
    d = ROOT / cfg["paths"]["figures"] if _lang == "en" else ROOT / ES_DIR / "figures"
    d.mkdir(parents=True, exist_ok=True)
    return d

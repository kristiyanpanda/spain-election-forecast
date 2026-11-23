"""Interactive Congress chart with a coalition builder (the "pactómetro").

The reader sets each party's vote in an investiture (yes, abstain, no); the widget counts the votes
on the expected seats and, over the same seat simulations as the forecast, the share in which that
pact reaches 176 seats and the share in which it has more yes than no votes.

The widget is ``pactometro/template.html`` with the data written in place of ``__DATA__``: per
party-supply scenario, the parties in seating order (expected seats, 5 %, 50 % and 95 % quantiles)
and the seat draws as base64 bytes (one byte per party and simulation). ``fragment`` returns it
for embedding (figure 1 of the report pages, in the page's language); ``main`` writes the
stand-alone ``pactometro/index.html``, which has a language switch and is handy for trying changes.
"""

from __future__ import annotations

import base64
import json

import numpy as np
import pandas as pd

from electoral import ROOT, i18n, load_config
from electoral.plots import HEMICYCLE_COLORS, HEMICYCLE_ORDER, expected_seats, hemicycle_layout, hemicycle_name

FOLDER = "pactometro"


def scenario_data(seat_draws: pd.DataFrame) -> dict:
    """Parties in seating order with their expected seats and quantiles, plus the encoded draws."""
    cols = [p for p in HEMICYCLE_ORDER if p in seat_draws and seat_draws[p].max() > 0]
    cols += [p for p in seat_draws if p not in HEMICYCLE_ORDER and seat_draws[p].max() > 0]
    exp = expected_seats(seat_draws)
    q = seat_draws[cols].quantile([0.05, 0.5, 0.95])
    parties = [{"id": p, "seats": int(exp.get(p, 0)), "q05": int(q.loc[0.05, p]), "q50": int(q.loc[0.5, p]),
                "q95": int(q.loc[0.95, p])} for p in cols]
    values = seat_draws[cols].to_numpy()
    if values.max() > 255:
        raise ValueError("a party has more than 255 seats in a simulation: one byte is not enough")
    return {"parties": parties, "draws": base64.b64encode(values.astype(np.uint8).tobytes()).decode("ascii")}


# Real chambers the reader can switch to (the "moment" selector). The forecast and the chamber at the
# dissolution sit on their own buttons; every successful investiture since 1996 goes in a drop-down
# menu. Seats of 2023 and 2026 come from the congreso.es membership dates (electoral.chamber), counted
# by the party of each deputy's list; the older ones from electoral.investitures. Investitures carry
# the vote as it was cast. ``compare`` names the moment whose seats each party's change is measured
# against (the previous investiture, for the drop-down).
SANCHEZ_2023 = {
    "key": "sanchez_2023", "date": "2023-11-16", "who": "Pedro Sánchez", "party": "PSOE", "ballot": 1,
    "result": {"y": 179, "n": 171, "a": 0, "x": 0},
    "yes": ["PSOE", "SUMAR", "PODEMOS", "ERC", "JUNTS", "BILDU", "PNV", "BNG", "CC"],
    "names": {"SUMAR": "Sumar"},
    "detail": {"es": "Elecciones del 23 de julio de 2023. Feijóo fracasó en septiembre (172 síes) y Sánchez fue "
                     "investido en primera votación el 16 de noviembre con 179 síes (PSOE, Sumar con Podemos dentro, "
                     "ERC, Junts, EH Bildu, PNV, BNG y CC) y 171 noes (PP, Vox y UPN). Es el bloque de la investidura "
                     "de 2023. Escaños de congreso.es.",
               "en": "Election of 23 July 2023. Feijóo failed in September (172 yes) and Sánchez was invested on the "
                     "first vote on 16 November with 179 yes (PSOE, Sumar with Podemos inside it, ERC, Junts, EH "
                     "Bildu, PNV, BNG and CC) and 171 no (PP, Vox and UPN). This is the 2023 investiture bloc. Seats "
                     "from congreso.es."}}
DISSOLUTION = {
    "key": "dissolution_2026", "date": "2026-10-05", "compare": "sanchez_2023", "names": {"SUMAR": "Sumar"},
    "short": {"es": "Al disolverse · oct 2026", "en": "At dissolution · Oct 2026"},
    "ref": {"es": "la disolución", "en": "the dissolution"},
    "detail": {"es": "El Congreso real el 5 de octubre de 2026, último día antes de la disolución. Desde la investidura, "
                     "Podemos (4) y Més-Compromís (1) habían pasado al Grupo Mixto, Ortega Smith había dejado Vox (julio "
                     "de 2026) y Junts había roto el pacto de investidura (27-10-2025). El escaño de Lilith Verstrynge "
                     "(Podemos), que dimitió en enero de 2024, pasó a Candela López, de Sumar: Podemos baja a 4 y Sumar "
                     "sube a 27. Sobre el papel el bloque de 2023 seguía en 179; sin Junts, en 172. Cambios frente a la "
                     "investidura de Sánchez de 2023.",
               "en": "The real Congress on 5 October 2026, the last day before the dissolution. Since the investiture, "
                     "Podemos (4) and Més-Compromís (1) had moved to the Mixed Group, Ortega Smith had left Vox (July "
                     "2026) and Junts had broken the investiture pact (27 Oct 2025). The seat of Lilith Verstrynge "
                     "(Podemos), who resigned in January 2024, went to Candela López of Sumar: Podemos down to 4, Sumar "
                     "up to 27. On paper the 2023 bloc still had 179; without Junts, 172. Changes are against the 2023 "
                     "Sánchez investiture."}}
FORECAST_MOMENT = {"key": "forecast", "compare": "dissolution_2026",
                   "short": {"es": "29-N · Previsión", "en": "29 Nov · Forecast"},
                   "detail": {"es": "Previsión del modelo para el 29 de noviembre de 2026: escaños esperados (media de "
                                    "las simulaciones) y probabilidades sobre las {n} simulaciones. Cambios frente a la "
                                    "disolución; Frente Amplio se compara con los 27 escaños de Sumar.",
                              "en": "The model's forecast for 29 November 2026: expected seats (mean of the "
                                    "simulations) and probabilities over the {n} simulations. Changes are against the "
                                    "dissolution; Frente Amplio is compared with Sumar's 27 seats."}}


def _surname(who: str) -> str:
    return {"José Luis Rodríguez Zapatero": "Zapatero"}.get(who, who.split()[-1])


def _labels(m: dict) -> dict:
    """Button text and the phrase used in "+3 against {ref}" for an investiture."""
    year, s = m["date"][:4], _surname(m["who"])
    if m["ballot"] == "censure":
        return {"short": {"es": f"{year} · {s} (moción de censura)", "en": f"{year} · {s} (no-confidence vote)"},
                "ref": {"es": f"la moción de censura de {year}", "en": f"the {year} no-confidence vote"}}
    return {"short": {"es": f"{year} · {s}", "en": f"{year} · {s}"},
            "ref": {"es": f"la investidura de {s} ({year})", "en": f"{s}'s {year} investiture"}}


def _ordered(seats: dict[str, int]) -> list[dict]:
    from electoral.investitures import ORDER

    ids = [p for p in ORDER if p in seats] + [p for p in seats if p not in ORDER]
    return [{"id": p, "seats": int(seats[p])} for p in ids]


def moments_data() -> list[dict]:
    """The forecast, the chamber at the dissolution and every investiture since 1996 (oldest first)."""
    from electoral import investitures
    from electoral.chamber import composition, load_membership

    members = load_membership()
    real = lambda day: composition(members, day)  # noqa: E731
    out = [{**FORECAST_MOMENT, "kind": "forecast", "group": "main"}]
    seats = real(DISSOLUTION["date"])
    if seats.sum() != 350:
        raise ValueError(f"the chamber on {DISSOLUTION['date']} has {seats.sum()} seats")
    out.append({**DISSOLUTION, "kind": "real", "group": "main", "vote": {}, "parties": _ordered(seats.to_dict())})

    seats23 = real(SANCHEZ_2023["date"])
    inv23 = {**{k: v for k, v in SANCHEZ_2023.items() if k != "yes"},
             "seats": [(p, int(s), "y" if p in SANCHEZ_2023["yes"] else "n") for p, s in seats23.items()]}
    previous = None
    for inv in investitures.INVESTITURES + [inv23]:
        investitures.check(inv)
        m = {k: v for k, v in inv.items() if k != "seats"}
        out.append({**m, **_labels(inv), "kind": "real", "group": "inv", "compare": previous,
                    "names": inv.get("names", {}), "vote": {p: v for p, _, v in inv["seats"]},
                    "parties": _ordered({p: s for p, s, _ in inv["seats"]})})
        previous = inv["key"]
    return out


def page_data(cfg: dict, default_lang: str = "es", embedded: bool = False) -> dict:
    out = ROOT / cfg["paths"]["outputs"]
    scenarios, n_sims, ids = {}, 0, []
    for key, spec in cfg["seats"]["scenarios"].items():
        draws = pd.read_parquet(out / f"seat_draws_29n_{key}.parquet")
        n_sims = len(draws)
        scenarios[key] = scenario_data(draws)
        ids += [p["id"] for p in scenarios[key]["parties"]]
    from electoral import investitures
    from electoral.chamber import EXTRA_COLORS, EXTRA_NAMES

    colors = {**HEMICYCLE_COLORS, **investitures.COLORS, **EXTRA_COLORS}
    extra_names = {**investitures.NAMES, **EXTRA_NAMES}

    moments = moments_data()
    ids += [p["id"] for m in moments for p in m.get("parties", [])]
    lay = hemicycle_layout(350)
    data = {"default_lang": default_lang, "embedded": embedded, "n_sims": n_sims, "scenarios": scenarios,
            "moments": moments,
            "layout": [[round(float(x), 4), round(float(y), 4)] for x, y in zip(lay.x, lay.y)],
            "colors": {p: colors.get(p, "#999999") for p in dict.fromkeys(ids)},
            "names": {}, "cutoff": {}, "provisional": {}}
    before = i18n.get_lang()
    try:
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            data["names"][lang] = {p: extra_names[p] if p in extra_names else hemicycle_name(p)
                                   for p in dict.fromkeys(ids)}
            data["cutoff"][lang] = i18n.date(cfg["cutoff_date"])
            data["provisional"][lang] = cfg.get(f"provisional_label_{lang}") or cfg.get("provisional_label", "")
            for key, spec in cfg["seats"]["scenarios"].items():
                scenarios[key].setdefault("label", {})[lang] = i18n.tr(spec["label"])
    finally:
        i18n.set_lang(before)
    return data


def _fill(template: str, data: dict) -> str:
    # "</" must not appear inside a <script> block
    return template.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))


def fragment(cfg: dict, lang: str) -> str:
    """The widget alone (style, markup, script) for embedding in a page written in ``lang``."""
    template = (ROOT / FOLDER / "template.html").read_text(encoding="utf-8")
    start, end = template.index("<!--PM:START"), template.index("<!--PM:END-->")
    piece = template[template.index("-->", start) + 3:end]
    return _fill(piece, page_data(cfg, lang, embedded=True))


def main(default_lang: str = "es") -> None:
    cfg = load_config()
    folder = ROOT / FOLDER
    template = (folder / "template.html").read_text(encoding="utf-8")
    html = _fill(template, page_data(cfg, default_lang))
    (folder / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {folder / 'index.html'} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()

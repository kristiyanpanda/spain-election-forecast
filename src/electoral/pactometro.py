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


def page_data(cfg: dict, default_lang: str = "es", embedded: bool = False) -> dict:
    out = ROOT / cfg["paths"]["outputs"]
    scenarios, n_sims, ids = {}, 0, []
    for key, spec in cfg["seats"]["scenarios"].items():
        draws = pd.read_parquet(out / f"seat_draws_29n_{key}.parquet")
        n_sims = len(draws)
        scenarios[key] = scenario_data(draws)
        ids += [p["id"] for p in scenarios[key]["parties"]]
    lay = hemicycle_layout(350)
    data = {"default_lang": default_lang, "embedded": embedded, "n_sims": n_sims, "scenarios": scenarios,
            "layout": [[round(float(x), 4), round(float(y), 4)] for x, y in zip(lay.x, lay.y)],
            "colors": {p: HEMICYCLE_COLORS.get(p, "#999999") for p in dict.fromkeys(ids)},
            "names": {}, "cutoff": {}, "provisional": {}}
    before = i18n.get_lang()
    try:
        for lang in i18n.LANGS:
            i18n.set_lang(lang)
            data["names"][lang] = {p: hemicycle_name(p) for p in dict.fromkeys(ids)}
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

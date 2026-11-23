"""The Congress at every successful investiture since 1996, with the vote as it was cast.

One entry per government actually formed: Aznar (1996, 2000), Zapatero (2004, 2008), Rajoy (2011,
2016), Sánchez's 2018 motion of no confidence (a successful motion counts as an investiture under
article 114.2 of the Constitution) and Sánchez (2020). Failed or proposed candidacies are left out.
The 2023 investiture comes from the congreso.es membership dates instead (``electoral.chamber``).

Sources: the totals of every ballot are those of the Congress's investiture archive
(congreso.es, "Sesiones de investidura 1979-2019"); the vote of each party is the ballot table of
the English Wikipedia article on each election or government formation; seats per list match
``data/processed/results_national.csv``. ``check`` makes sure each chamber fills 350 seats and its
votes add up to the official result.

Each seat entry is (id, seats, vote): ``vote`` is "y", "a", "n" or "x" (absent), or a dict of
counts for a party that split. Ids are party families so that seats can be compared across
elections; ``names`` gives the name a family went by at that moment (CiU, HB, Amaiur ...).
"""

from __future__ import annotations

# names and colours of the parties that are not in the 2026 forecast
NAMES = {"IU": "IU", "ICV": "ICV", "CHA": "CHA", "EA": "EA", "NABAI": "Nafarroa Bai", "PA": "PA",
         "UV": "Unió Valenciana", "UPYD": "UPyD", "CS": "Cs", "UP": "Unidas Podemos", "COMPROMIS": "Compromís",
         "MASPAIS": "Más País", "CUP": "CUP", "TE": "Teruel Existe", "PRC": "PRC", "FAC": "Foro", "NC": "NC"}
COLORS = {"IU": "#b30000", "ICV": "#8c1d40", "CHA": "#e6550d", "EA": "#9acd32", "NABAI": "#e7298a",
          "PA": "#66c2a5", "UV": "#feb24c", "UPYD": "#e5007d", "CS": "#ff7f00", "UP": "#6a3d9a",
          "COMPROMIS": "#b35806", "MASPAIS": "#c2a5cf", "CUP": "#f5e000", "TE": "#7f7f00", "PRC": "#9bbb59",
          "FAC": "#0868ac", "NC": "#ffd966"}
# left to right in the chamber drawing
ORDER = ["CUP", "PODEMOS", "UP", "SUMAR", "IU", "ICV", "MASPAIS", "COMPROMIS", "CHA", "PSOE", "NC", "EX_PSOE",
         "ERC", "BILDU", "EA", "NABAI", "BNG", "PA", "AA", "TE", "PRC", "CC", "UV", "OTHER", "PNV", "JUNTS",
         "UPYD", "CS", "PP", "FAC", "UPN", "EX_VOX", "VOX", "SALF"]

INVESTITURES = [
    {"key": "aznar_1996", "date": "1996-05-04", "who": "José María Aznar", "party": "PP", "ballot": 1,
     "result": {"y": 181, "n": 166, "a": 1, "x": 2},
     "seats": [("PP", 156, "y"), ("JUNTS", 16, "y"), ("PNV", 5, "y"), ("CC", 4, "y"), ("PSOE", 141, "n"),
               ("IU", 21, "n"), ("BNG", 2, "n"), ("ERC", 1, "n"), ("EA", 1, "n"), ("UV", 1, "a"),
               ("BILDU", 2, "x")],
     "names": {"JUNTS": "CiU", "IU": "IU-IC", "BILDU": "HB"},
     "detail": {"es": "Elecciones del 3 de marzo de 1996. Aznar fue investido en primera votación el 4 de mayo con "
                      "181 síes (PP, CiU, PNV y CC, tras los pactos del Majestic), 166 noes y 1 abstención (UV). Los "
                      "2 diputados de HB no ocuparon su escaño.",
                "en": "Election of 3 March 1996. Aznar was invested on the first vote on 4 May with 181 yes (PP, CiU, "
                      "PNV and CC, after the Majestic pacts), 166 no and 1 abstention (UV). HB's 2 deputies never "
                      "took their seats."}},
    {"key": "aznar_2000", "date": "2000-04-26", "who": "José María Aznar", "party": "PP", "ballot": 1,
     "result": {"y": 202, "n": 148, "a": 0, "x": 0},
     "seats": [("PP", 183, "y"), ("JUNTS", 15, "y"), ("CC", 4, "y"), ("PSOE", 125, "n"), ("IU", 8, "n"),
               ("PNV", 7, "n"), ("BNG", 3, "n"), ("PA", 1, "n"), ("ERC", 1, "n"), ("ICV", 1, "n"), ("EA", 1, "n"),
               ("CHA", 1, "n")],
     "names": {"JUNTS": "CiU"},
     "detail": {"es": "Elecciones del 12 de marzo de 2000: mayoría absoluta del PP (183). Aznar fue investido en "
                      "primera votación el 26 de abril con 202 síes (PP, CiU y CC) y 148 noes, sin abstenciones.",
                "en": "Election of 12 March 2000: an absolute majority for the PP (183). Aznar was invested on the "
                      "first vote on 26 April with 202 yes (PP, CiU and CC) and 148 no, with no abstentions."}},
    {"key": "zapatero_2004", "date": "2004-04-16", "who": "José Luis Rodríguez Zapatero", "party": "PSOE",
     "ballot": 1, "result": {"y": 183, "n": 148, "a": 19, "x": 0},
     "seats": [("PSOE", 164, "y"), ("ERC", 8, "y"), ("IU", 5, "y"), ("CC", 3, "y"), ("BNG", 2, "y"),
               ("CHA", 1, "y"), ("PP", 148, "n"), ("JUNTS", 10, "a"), ("PNV", 7, "a"), ("EA", 1, "a"),
               ("NABAI", 1, "a")],
     "names": {"JUNTS": "CiU", "IU": "IU-ICV"},
     "detail": {"es": "Elecciones del 14 de marzo de 2004, tres días después del 11-M. Zapatero fue investido en "
                      "primera votación el 16 de abril con 183 síes (PSOE, ERC, IU-ICV, CC, BNG y CHA), 148 noes "
                      "(PP) y 19 abstenciones (CiU, PNV, EA y Nafarroa Bai).",
                "en": "Election of 14 March 2004, three days after the Madrid train bombings. Zapatero was invested on "
                      "the first vote on 16 April with 183 yes (PSOE, ERC, IU-ICV, CC, BNG and CHA), 148 no (PP) "
                      "and 19 abstentions (CiU, PNV, EA and Nafarroa Bai)."}},
    {"key": "zapatero_2008", "date": "2008-04-11", "who": "José Luis Rodríguez Zapatero", "party": "PSOE",
     "ballot": 2, "result": {"y": 169, "n": 158, "a": 23, "x": 0},
     "seats": [("PSOE", 169, "y"), ("PP", 154, "n"), ("ERC", 3, "n"), ("UPYD", 1, "n"), ("JUNTS", 10, "a"),
               ("PNV", 6, "a"), ("IU", 2, "a"), ("BNG", 2, "a"), ("CC", 2, "a"), ("NABAI", 1, "a")],
     "names": {"JUNTS": "CiU", "IU": "IU-ICV"},
     "detail": {"es": "Elecciones del 9 de marzo de 2008. Zapatero se quedó en 168 síes en la primera votación (9 de "
                      "abril) y fue investido en la segunda, el 11 de abril, con 169 síes (solo el PSOE), 158 noes "
                      "(PP, ERC y UPyD) y 23 abstenciones (CiU, PNV, IU-ICV, BNG, CC y Nafarroa Bai).",
                "en": "Election of 9 March 2008. Zapatero got 168 yes on the first vote (9 April) and was invested on "
                      "the second, on 11 April, with 169 yes (the PSOE alone), 158 no (PP, ERC and UPyD) and 23 "
                      "abstentions (CiU, PNV, IU-ICV, BNG, CC and Nafarroa Bai)."}},
    {"key": "rajoy_2011", "date": "2011-12-20", "who": "Mariano Rajoy", "party": "PP", "ballot": 1,
     "result": {"y": 187, "n": 149, "a": 14, "x": 0},
     "seats": [("PP", 185, "y"), ("FAC", 1, "y"), ("UPN", 1, "y"), ("PSOE", 110, "n"), ("JUNTS", 16, "n"),
               ("IU", 11, "n"), ("UPYD", 5, "n"), ("ERC", 3, "n"), ("BNG", 2, "n"), ("COMPROMIS", 1, "n"),
               ("NABAI", 1, "n"), ("BILDU", 7, "a"), ("PNV", 5, "a"), ("CC", 1, "a"), ("NC", 1, "a")],
     "names": {"JUNTS": "CiU", "IU": "IU-ICV-CHA", "BILDU": "Amaiur", "NABAI": "Geroa Bai"},
     "detail": {"es": "Elecciones del 20 de noviembre de 2011: mayoría absoluta del PP (186 con UPN). Rajoy fue "
                      "investido en primera votación el 20 de diciembre con 187 síes (PP, UPN y Foro), 149 noes y 14 "
                      "abstenciones (Amaiur, PNV, CC y NC).",
                "en": "Election of 20 November 2011: an absolute majority for the PP (186 with UPN). Rajoy was "
                      "invested on the first vote on 20 December with 187 yes (PP, UPN and Foro), 149 no and 14 "
                      "abstentions (Amaiur, PNV, CC and NC)."}},
    {"key": "rajoy_2016", "date": "2016-10-29", "who": "Mariano Rajoy", "party": "PP", "ballot": 2,
     "result": {"y": 170, "n": 111, "a": 68, "x": 1},
     "seats": [("PP", 134, "y"), ("CS", 32, "y"), ("UPN", 2, "y"), ("FAC", 1, "y"), ("CC", 1, "y"),
               ("PSOE", 84, {"a": 68, "n": 15, "x": 1}), ("UP", 67, "n"), ("COMPROMIS", 4, "n"), ("ERC", 9, "n"),
               ("JUNTS", 8, "n"), ("PNV", 5, "n"), ("BILDU", 2, "n"), ("NC", 1, "n")],
     "names": {"JUNTS": "CDC (PDeCAT)", "UP": "Unidos Podemos"},
     "detail": {"es": "Tras las elecciones de diciembre de 2015 (sin investidura) y las del 26 de junio de 2016, Rajoy "
                      "perdió la votación de septiembre y fue investido en la segunda votación del 29 de octubre: 170 "
                      "síes (PP, Cs, UPN, Foro y CC), 111 noes y 68 abstenciones. El PSOE se partió: 68 abstenciones "
                      "y 15 noes; Pedro Sánchez había dejado su escaño horas antes.",
                "en": "After the December 2015 election (no investiture) and the one on 26 June 2016, Rajoy lost the "
                      "September vote and was invested on the second ballot on 29 October: 170 yes (PP, Cs, UPN, "
                      "Foro and CC), 111 no and 68 abstentions. The PSOE split: 68 abstentions and 15 no; Pedro "
                      "Sánchez had given up his seat hours before."}},
    {"key": "sanchez_2018", "date": "2018-06-01", "who": "Pedro Sánchez", "party": "PSOE", "ballot": "censure",
     "result": {"y": 180, "n": 169, "a": 1, "x": 0},
     "seats": [("PSOE", 84, "y"), ("UP", 67, "y"), ("ERC", 9, "y"), ("JUNTS", 8, "y"), ("PNV", 5, "y"),
               ("COMPROMIS", 4, "y"), ("BILDU", 2, "y"), ("NC", 1, "y"), ("PP", 134, "n"), ("CS", 32, "n"),
               ("UPN", 2, "n"), ("FAC", 1, "n"), ("CC", 1, "a")],
     "names": {"JUNTS": "PDeCAT", "UP": "Unidos Podemos"},
     "detail": {"es": "Moción de censura contra Rajoy, una semana después de la sentencia del caso Gürtel. Salió "
                      "adelante el 1 de junio de 2018 con 180 síes (PSOE, Unidos Podemos, ERC, PDeCAT, PNV, Compromís, "
                      "EH Bildu y NC), 169 noes y 1 abstención (CC). Por el artículo 114.2 de la Constitución, Sánchez "
                      "quedó investido. Es el mismo Congreso de 2016.",
                "en": "Motion of no confidence in Rajoy, a week after the Gürtel ruling. It passed on 1 June 2018 with "
                      "180 yes (PSOE, Unidos Podemos, ERC, PDeCAT, PNV, Compromís, EH Bildu and NC), 169 no and 1 "
                      "abstention (CC). Under article 114.2 of the Constitution, Sánchez was thereby invested. It is "
                      "the same Congress as in 2016."}},
    {"key": "sanchez_2020", "date": "2020-01-07", "who": "Pedro Sánchez", "party": "PSOE", "ballot": 2,
     "result": {"y": 167, "n": 165, "a": 18, "x": 0},
     "seats": [("PSOE", 120, "y"), ("UP", 35, "y"), ("PNV", 6, "y"), ("MASPAIS", 2, "y"), ("COMPROMIS", 1, "y"),
               ("NC", 1, "y"), ("BNG", 1, "y"), ("TE", 1, "y"), ("PP", 88, "n"), ("VOX", 52, "n"), ("CS", 10, "n"),
               ("JUNTS", 8, "n"), ("CUP", 2, "n"), ("UPN", 2, "n"), ("CC", 1, "n"), ("PRC", 1, "n"), ("FAC", 1, "n"),
               ("ERC", 13, "a"), ("BILDU", 5, "a")],
     "names": {"JUNTS": "JxCat", "UPN": "UPN (Navarra Suma)"},
     "detail": {"es": "Tras las elecciones de abril de 2019 (investidura fallida en julio) y las del 10 de noviembre, "
                      "Sánchez fue investido en la segunda votación del 7 de enero de 2020 con 167 síes (PSOE, Unidas "
                      "Podemos, PNV, Más País, Compromís, NC, BNG y Teruel Existe), 165 noes y 18 abstenciones (ERC y "
                      "EH Bildu): el margen más estrecho de todas las investiduras.",
                "en": "After the April 2019 election (failed investiture in July) and the one on 10 November, Sánchez "
                      "was invested on the second ballot on 7 January 2020 with 167 yes (PSOE, Unidas Podemos, PNV, "
                      "Más País, Compromís, NC, BNG and Teruel Existe), 165 no and 18 abstentions (ERC and EH Bildu): "
                      "the narrowest margin of any investiture."}},
]


def counts(vote, seats: int) -> dict:
    """Seats per vote ("y", "a", "n", "x") of one entry."""
    c = dict(vote) if isinstance(vote, dict) else {vote: seats}
    if sum(c.values()) != seats:
        raise ValueError(f"split vote {vote} does not add up to {seats} seats")
    return c


def check(inv: dict) -> None:
    """The chamber fills 350 seats and its votes give the official result."""
    total = sum(s for _, s, _ in inv["seats"])
    if total != 350:
        raise ValueError(f"{inv['key']}: {total} seats")
    got = {"y": 0, "a": 0, "n": 0, "x": 0}
    for _, s, v in inv["seats"]:
        for k, c in counts(v, s).items():
            got[k] += c
    if got != {k: inv["result"].get(k, 0) for k in got}:
        raise ValueError(f"{inv['key']}: votes {got} differ from the official {inv['result']}")

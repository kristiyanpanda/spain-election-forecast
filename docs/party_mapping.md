# Party mapping and coalition relabelling

Spanish party labels change almost every cycle. This note records how the pipeline maps
Ministry lists and Wikipedia poll columns to a small set of canonical ids, and which choices
are judgement calls. The machine-readable versions are `data/party_map_results.yaml`
(per-election Ministry codes) and `data/party_map_polls.yaml` (Wikipedia column labels).

## Canonical ids used in the forecast (2023 cycle onwards)

| id | what it contains | notes |
|---|---|---|
| PP | Partido Popular | AP / Coalición Popular before 1989 in the historical series |
| PSOE | PSOE incl. PSC (Catalonia) | PSC lists carry the PSOE national head code in the Ministry files |
| VOX | Vox | first seats in Apr-2019 |
| SUMAR | Sumar platform | Podemos ran *inside* Sumar in Jul-2023; left the group in Dec-2023 |
| PODEMOS | Podemos on its own | polled separately since late 2023; 2015 stand-alone list in the historical series |
| ERC | Esquerra Republicana | ERC-CatSí (2015-16), ERC-Sobiranistes (2019) |
| JUNTS | post-Convergència line | CiU (1979-2011) → CDC/DiL (2015-16) → PDeCAT (2016-18) → JxCat (2019) → Junts (2023-) |
| BILDU | EH Bildu | HB (1979-93) → EH → Amaiur (2011) → EH Bildu; the abertzale-left lineage |
| PNV | EAJ-PNV | |
| BNG | Bloque Nacionalista Galego | |
| CC | Coalición Canaria | AIC (1986-89), CC-PNC, CC-NC-PNC, CCa |
| UPN | UPN | ran as Navarra Suma (NA+, with PP and Cs) in both 2019 elections |
| CS | Ciudadanos | 2015-2023, no seats in 2023, no longer polled |
| UP | Unidos/Unidas Podemos | 2016-2023: Podemos + IU + confluences (ECP, En Marea, Compromís-Podemos in 2016) |
| SALF, ALIANCA, AA, CUP, TE, EV, MASPAIS, COMPROMIS, PRC, PACMA | smaller lists | kept as-is where polled; folded into OTHER for modelling if fewer than 5 % of polls report them |

## Blocs

Four blocs plus "other", chosen to reproduce the bloc matrix of the original dossier and to make
the 176-seat questions meaningful:

* **left**: PSOE, PCE/IU, Podemos/UP, Sumar, Más País, PSP
* **right**: UCD, AP/PP, CDS, Cs, UPyD, Vox, SALF, Unión Nacional
* **periph_left**: ERC, HB/Bildu, EE, EA, BNG, CUP, Compromís, PA, CHA, Nafarroa Bai, Adelante Andalucía, UPC
* **periph_right**: CiU/Junts, PNV, CC, PAR, UV, CG, Foro Asturias, UPN/NA+, PRC, Aliança Catalana
* **other**: PACMA, Teruel Existe, España Vaciada, unclassified lists

Judgement calls worth knowing: Ciudadanos and UPyD are counted in the state-wide right bloc
(they never supported a left investiture); Compromís sits in the peripheral left even in Nov-2019,
when it ran with Más País; Teruel Existe is "other" although it voted for a left investiture in 2020.
Changing a bloc is one line in `data/party_map_polls.yaml`.

## Handling entries, exits and relabelling in the aggregator (phase C)

1. **Sumar / Podemos split (Dec 2023).** The 2023 election anchor is Sumar = 12.33 % with Podemos
   inside. From the first poll that lists Podemos separately, the model tracks SUMAR and PODEMOS as
   two series; before that date Podemos' latent share is fixed at zero and Sumar carries the total.
   Polls that report only a joint figure after the split are treated as observations of SUMAR+PODEMOS.
2. **New parties (SALF from Jun 2024, Aliança from 2025).** Latent share starts at zero at the
   previous election and is only informed by polls that list them; missing cells (–) are treated as
   "not asked", not as zero.
3. **Historical cycles for the backtest.** 2016: Podemos and IU polled separately until they merged as
   Unidos Podemos (May 2016); before the merger the model uses PODEMOS + IU as the UP observation.
   Apr-2019 and Nov-2019: Cs, UP, Vox, Más País all present; NA+ observed as UPN.
4. **Regional confluences** (ECP, En Marea, Compromís-Podemos) are always folded into the
   Podemos/UP family so that poll and result series match.
5. **Missing cells.** "?" means polled but not published; "–" means not listed. Both are missing
   observations; the model does not impute them.

## What the Ministry files call things

The Ministry assigns a new candidatura code in every election; a provincial list points to its
national head through the "cabecera nacional" field. `party_map_results.yaml` maps those head codes.
Lists that neither won a seat nor reached 1 % nationally are OTHER, which keeps 92-99 % of the
valid vote named in every election (see `data/processed/DATA_QUALITY.md`).

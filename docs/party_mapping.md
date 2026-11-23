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
| SUMAR | Sumar platform, then Frente Amplio | Podemos ran *inside* Sumar in Jul-2023; left the group in Dec-2023; from 17 Oct 2026 the series continues as Frente Amplio |
| FA | Frente Amplio | poll label only: polls listing FA feed the SUMAR series (`model.composites` in `config.yaml`) |
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
| AA | Adelante Andalucía | tracked for 29N (about 10 % of polls since Jan 2026); seats spread over Andalusia's provinces |
| SALF, ALIANCA, CUP, TE, EV, MASPAIS, COMPROMIS, PRC, PACMA | smaller lists | kept as-is where polled; folded into OTHER for modelling if fewer than 5 % of polls report them |

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

## Party supply on 29 Nov 2026 (lists proclaimed in the BOE of 3 Nov)

Since mid-October the poll tables list the ballots as registered, and so does the CIS pre-election
study (3584). The full table and sources are in `docs/context_29N_2026.md` §7 and §8.

| ballot | in the tables | in the model |
|---|---|---|
| Frente Amplio, with Unidad del Pueblo Canario (Canarias) and Ara Més-Front Ampli (Baleares, with Podemos since 26 Oct) | `FA` | SUMAR series |
| Compromís-Front Valencià (Compromís, EUPV, Podem, ERPV) | `FV`, or one figure with FA (`FA+FV`, id `FAFV`) | SUMAR series (FA + FV) |
| ERC, with Podemos candidates on its Catalan lists ("ERC-Podemos" in the CIS) | `ERC` | ERC |
| Podemos, own list in 42 districts | `Podemos` | PODEMOS, no share in the ten provinces without a list (`seats.absent`) |
| UPN-PP in Navarra | PP | UPN's 2023 share joins PP's there |

* **Base case, split left:** the table above. The 17 Oct run moved an assumed part of Podemos's
  polled vote to Frente Amplio (Canarias, Valencia) and to ERC and Frente Amplio (Catalonia, 50/50).
  That is no longer needed: the polls measure those voters where they now are. A level shift in the
  week of 11 Oct 2026 lets the Frente Amplio, Podemos and ERC series absorb the change of definition.
  Aliança Catalana is not running.
* **Sensitivity, merged left:** one FA + Podemos list everywhere, keeping 0.83 (sd 0.05) of the sum,
  as Unidos Podemos did in 2016.

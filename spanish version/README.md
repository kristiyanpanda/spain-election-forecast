# Previsión de las elecciones generales del 29 de noviembre de 2026

**Modelo bayesiano de agregación de encuestas y proyección de escaños, con un backtest sobre cuatro elecciones.**

*English version: [`README.md`](../README.md).*

> **PROVISIONAL — encuestas hasta el 14 de noviembre de 2026; la versión final usará las encuestas
> publicadas hasta el 23 de noviembre, último día que permite la ley.** Todo lo que sigue depende de las
> encuestas publicadas hasta el cierre de datos, el **14 de noviembre de 2026**, un día después del inicio
> de la campaña y dos semanas antes de la votación. Para actualizarlo, basta con volver a ejecutar `make all`.

Las elecciones al Congreso de 2023 dieron 137 escaños al PP, 121 al PSOE, 33 a Vox y 31 a Sumar. El 5 de
octubre de 2026 se disolvieron las Cortes y se convocaron elecciones anticipadas para el 29 de noviembre.
Este repositorio convierte el registro público de encuestas desde 2023 (659 encuestas de 40 encuestadoras
y series basadas en el CIS, con el CIS tomado directamente de cis.es) y los resultados oficiales de
1977-2023 en una previsión probabilística de esas elecciones. Después comprueba cómo habría funcionado el
mismo procedimiento 30 días antes de las elecciones de 2016, abril de 2019, noviembre de 2019 y 2023.
Nació como un trabajo de grado en Excel y SPSS sobre la volatilidad electoral en España; la parte
descriptiva de aquel trabajo se reproduce en `figures/`.

## Resultado principal

**El 29 de noviembre**, el modelo da al PP el 30,5 % del voto (intervalo del 90 %: 25,0-36,6), al PSOE el
27,5 % (22,5-33,2), a Vox el 19,0 % (15,6-23,1), al espacio del Frente Amplio (Frente Amplio más
Compromís-Front Valencià, la línea que viene de Sumar) el 6,9 % (5,7-8,6) y a Podemos el 1,6 % (1,3-2,1)
donde presenta lista propia. Los escaños siguen las candidaturas proclamadas el 3 de noviembre. El **caso
base** es la izquierda tal como se ha registrado: Frente Amplio y Podemos por separado, con Podemos
ausente de las diez provincias donde se integró en otras listas. El análisis de **sensibilidad** es una
lista única de Frente Amplio y Podemos en todas las provincias, que conserva 0,83 de la suma, como
Unidos Podemos en 2016.

![Figura 1. Congreso previsto](figures/hemicycle_29n_split.png)
***Figura 1. Congreso previsto, 29 de noviembre de 2026.*** *Escaños esperados, caso base: la media de
cada partido en 10.000 simulaciones, redondeada para que sumen 350. Ninguna simulación tiene por qué ser
exactamente así; los intervalos del 90 % están en la tabla de abajo. PP y Vox suman aquí 196. «Frente
Amplio» incluye a Compromís-Front Valencià. «Otros» son candidaturas locales (Soria ¡Ya!, Teruel Existe,
UPL). Versión con lista única de la izquierda:
[`hemicycle_29n_merged.png`](figures/hemicycle_29n_merged.png). En la página interactiva (`index.html`)
este gráfico es un pactómetro: se marca el voto de cada partido en una investidura (sí, abstención o no)
y se ve el recuento frente a los 176 y en qué proporción de las simulaciones sale adelante ese pacto.*

| partido | voto al cierre de datos | escaños si se votara al cierre, 90 % | escaños el 29-N, listas separadas (base) | escaños el 29-N, lista única |
|---|---|---|---|---|
| PP | 30,5 % | 122 - 135 | 128 (105 - 151) | 128 (105 - 151) |
| PSOE | 27,6 % | 103 - 116 | 109 (89 - 131) | 109 (89 - 131) |
| Vox | 19,1 % | 62 - 74 | 67 (52 - 85) | 68 (52 - 85) |
| Frente Amplio + Compromís-Front Valencià | 7,0 % | 8 - 13 | 10 (6 - 16) | 10 (6 - 17) |
| Podemos | 1,6 % | 0 - 1 | 1 (0 - 1) | (en Frente Amplio) |
| ERC | 2,6 % | 8 - 12 | 10 (7 - 13) | 10 (7 - 13) |
| EH Bildu / PNV / Junts | 1,4 / 0,9 / 1,3 % | 6-8 / 4-6 / 3-6 | 7 / 5 / 5 | 7 / 5 / 5 |
| BNG / CC / Adelante Andalucía | 0,9 / 0,4 / en torno a 1,3 % | 1-2 / 1 / 0-5 | 2 / 1 / 1 | 2 / 1 / 1 |

| suceso (29-N) | listas separadas | lista única |
|---|---|---|
| PP + Vox (+ UPN, SALF) alcanzan 176 escaños | 94 % | 95 % |
| PP, primera fuerza | 78 % | 78 % |
| PSOE, primera fuerza | 22 % | 22 % |
| El bloque de la investidura de 2023 (PSOE, FA, Podemos, ERC, Bildu, BNG, CC, AA, PNV, Junts) alcanza 176 | 3 % | 3 % |
| El PP alcanza 176 en solitario | < 1 % | < 1 % |

**Qué ha cambiado desde la versión del 17 de octubre** (PP 131, PSOE 107, Vox 66; mayoría de PP + Vox, 93 %).
- **La distancia publicada entre PP y PSOE es menor, pero poco de eso es movimiento de las últimas cuatro
  semanas.** La versión del 17 de octubre leía PP 31,1 / PSOE 26,9 en su cierre; esta lee PP 30,5 /
  PSOE 27,6. Con las encuestas y las reglas de hoy, el modelo lee el propio 17 de octubre como PP 30,6 /
  PSOE 27,4, de modo que el cambio desde entonces es PP -0,1, PSOE +0,2, Vox -0,3. El resto es una
  relectura: los nuevos estudios y encuestadoras, y los cambios de reglas que se explican abajo, movieron
  la referencia respecto a la que se miden los efectos de casa. No se han separado las dos cosas.
- **La aritmética de bloques no se ha movido.** PP y Vox suman el 49,6 % del voto y tienen un 94 % de
  probabilidad de mayoría; el PP es primera fuerza en el 78 % de las simulaciones (80 % antes). A dos
  semanas de la votación, estas cifras dependen casi por completo del error de las encuestas el día de la
  elección, no de la deriva.
- **El estudio preelectoral del CIS** (45.074 entrevistas, PSOE 33,3 / PP 25,5) entra con su efecto de
  casa habitual (-5,1 para el PP, +4,1 para el PSOE), así que su estimación oficial mueve poco la media.
  Los datos brutos sí se movieron: nuestra propia lectura del barómetro de octubre, ponderada por recuerdo
  de voto, es PP 28,4 / PSOE 27,6, frente a PP 30,6 / PSOE 25,7 en septiembre, y dos reestimaciones
  externas del preelectoral ponen primero al PSOE.
- **Las series basadas en el CIS cuentan como una sola encuestadora.** Diez de las 39 series son lecturas
  de los datos brutos del CIS (la estimación oficial, la nuestra y ocho reestimaciones de terceros). Ahora
  comparten un solo voto al centrar los efectos de casa. Con un voto cada una, el cierre daba PP 30,2 /
  PSOE 27,8.
- **Las encuestadoras discrepan más que en octubre**: la ventaja del PP va de 7,7 puntos (Data10) a -2,9
  (SW Demoscopia, una firma nueva sin historial). El tracking diario de 40dB la deja en 1,3.
- **La oferta electoral, tal como se ha proclamado.** Las encuestas preguntan ya por las candidaturas
  registradas. Podemos se mide solo donde se presenta en solitario (del 3,1 % al 1,6 %, la mayor parte de
  la caída es un cambio de definición) y obtiene 0-1 escaños; desaparece la suposición del 50/50 sobre sus
  votantes catalanes. ERC marca un 2,6 % con Podemos en sus listas.
- **Los trackings cuentan una sola vez.** Las publicaciones diarias y acumuladas de una misma
  encuestadora con trabajo de campo solapado ya no son encuestas distintas (659 registradas, 583 usadas).
- El error del día de la elección se ha recalibrado con el backtest reajustado: 11,5 % del voto de cada
  partido (13,3 % antes).

## Tendencia, bloques y backtest

![Figura 2. Partidos de ámbito estatal desde las elecciones de julio de 2023](figures/trend_national.png)
***Figura 2. Partidos de ámbito estatal desde las elecciones de julio de 2023: encuestas y tendencia
latente.*** *Estimación de voto (mediana, bandas del 50 % y del 90 %) y todas las encuestas. Izquierda:
el ciclo completo; la franja sombreada es el periodo ampliado a la derecha. Derecha: los últimos cuatro
meses, con los acontecimientos fechados: la crisis fronteriza de Ceuta (30 de julio), el rechazo de los
decretos en el Congreso (2 de octubre), la disolución (5 de octubre), el cierre de coaliciones y el
anuncio de Colau (17 de octubre), el accidente ferroviario de Urda (28 de octubre), la proclamación de
candidaturas (3 de noviembre) y el inicio de la campaña (13 de noviembre). La línea discontinua es el
cierre de datos. El escalón de Podemos a mediados de octubre es el paso a las papeletas registradas.*

![Figura 3. Escaños por bloque](figures/bloc_majority_29n_split.png)
***Figura 3. Escaños por bloque el 29 de noviembre.*** *Suma de escaños de los dos bloques en
competencia, caso base (listas separadas en la izquierda).*

![Figura 4. Backtest](figures/backtest.png)
***Figura 4. Backtest.*** *Lo que habría dicho el mismo procedimiento 30 días antes de cada una de las
cuatro últimas elecciones, frente al resultado.*

## Métodos

| componente | decisión | código |
|---|---|---|
| Resultados | Ficheros de ancho fijo del Ministerio del Interior, las 16 elecciones, 52 provincias; D'Hondt reproduce exactamente los escaños oficiales de 2019 y 2023 (comprobado con tests) | `mir.py`, `seats.py`, `tests/` |
| Encuestas | Wikitexto de las tablas de sondeos de Wikipedia (CC BY-SA 4.0), con un lector que entiende celdas combinadas y referencias; las reestimaciones de terceros con datos del CIS se mantienen como encuestadoras propias; una publicación por ventana de trabajo de campo solapada de cada encuestadora | `wiki_polls.py`, `build_data.py` |
| CIS | directamente de cis.es: la estimación oficial de 99 estudios desde 2016 (PDF, todos los ciclos) y nuestra reestimación con los microdatos para el ciclo actual (peso del CIS, recuerdo de 2023, votantes probables; sin backtest). Las series construidas con una misma encuesta se reparten su tamaño muestral | `cis.py`, `cis_microdata.py` |
| Correspondencia de partidos | códigos del Ministerio y etiquetas de las encuestas, por elección, a identificadores canónicos y bloques; Frente Amplio + Compromís-Front Valencià continúan la serie de Sumar | `data/party_map_*.yaml`, `docs/party_mapping.md` |
| Agregador | paseo aleatorio semanal en escala logit para cada partido, anclado en el resultado de 2023; saltos de nivel donde cambió la oferta electoral; efectos de casa jerárquicos centrados en las encuestadoras que publican, con las series del CIS como una sola; ruido binomial más un exceso; NUTS (nutpie), 4 x 1.000 extracciones | `model.py` |
| Escaños | variación proporcional sobre el voto provincial de 2023 más ruido provincial log-normal (sd 0,13); capa de encuestas regionales (CEO, Sociómetro, submuestras del CIS); papeletas del 29-N tal como se han proclamado (Podemos ausente de diez provincias, la parte valenciana del espacio del Frente Amplio fijada con encuestas, UPN con el PP); barrera del 3 %; 10.000 simulaciones | `seats.py`, `regional.py`, `project_seats.py` |
| Backtest | reajuste 30 días antes de 2016, abril de 2019, noviembre de 2019 y 2023 solo con las encuestas anteriores; capa regional solo para Cataluña en 2023 (CEO) | `backtest.py` |
| Día de la elección | 2 semanas de deriva del paseo aleatorio más un error del día de la elección calibrado con el backtest (11,5 % del voto de cada partido); la reversión a la media se probó y se descartó | `forecast.py` |
| Descriptivo | participación, número efectivo de partidos de Laakso-Taagepera, volatilidad de Pedersen dentro de los bloques y entre ellos, matriz de bloques, fragmentación provincial | `indices.py`, `descriptive.py` |

## Resultados del backtest (media de las cuatro elecciones, previsiones a 30 días)

| método | EAM de voto (pp) | CRPS de voto (pp) | cobertura del 90 %, voto | EAM de escaños | cobertura del 90 %, escaños | Brier (dos sucesos) |
|---|---|---|---|---|---|---|
| **este modelo** | **1,04** | **0,89** | 40 % | **4,2** | 73 % | **0,06** |
| media de encuestas de 30 días | 1,17 | 1,17 | n. d. | 4,9 | n. d. | 0,12 |
| resultado de la elección anterior | 2,59 | 2,59 | n. d. | 11,0 | n. d. | 0,25 |

EAM: error absoluto medio. El backtest se reajustó el 14 de noviembre con las dos reglas nuevas, que se
aplican a todos los ciclos: los trackings solapados cuentan una vez (entre un 10 y un 17 % menos de
encuestas por elección) y las series del CIS son una sola encuestadora. Las puntuaciones apenas cambiaron
respecto a la versión del 17 de octubre (EAM de voto 1,03; EAM de escaños 4,2; Brier 0,05): ninguna de
las dos reglas mejora la precisión en el backtest; están porque la alternativa cuenta dos veces lo mismo.
La capa regional solo pudo probarse para Cataluña en 2023, donde redujo el EAM de escaños de 2023 de 3,5
a 3,1. Esa mejora es dentro de la muestra: los errores de la capa se calibraron con esa misma elección.

En palabras:

* El modelo supera a las dos referencias en todas las medidas de precisión, pero el margen sobre una
  simple media de encuestas de 30 días es pequeño. Casi todo el valor está en la corrección de los
  efectos de casa y en los intervalos.
* **Los intervalos son demasiado estrechos.** A 30 días, los intervalos de voto del 90 % solo cubrieron
  el 40 % de los resultados. En julio de 2023 todas las encuestadoras infraestimaron al PSOE en unos
  5 puntos, y el modelo daba un 68 % a una mayoría de PP + Vox que no se produjo. Las encuestas
  comparten sus errores; por eso la proyección al día de la elección añade un término de error (11,5 %
  del voto de cada partido, el valor más pequeño que habría devuelto la cobertura al 90 %).
* Dónde falla: en los movimientos bruscos de última hora (Vox doblando su voto en el último mes de la
  campaña de noviembre de 2019; el hundimiento de Cs) y en cualquier elección con un sesgo común de las
  encuestas.

Tabla completa por elección: `outputs/backtest_scorecard.csv` y `outputs/backtest_details.csv`.

## De dónde viene la incertidumbre

Desviación típica de los escaños del PP al añadir las fuentes de una en una, caso base
(`outputs/uncertainty_decomposition.csv`): la estimación al cierre de datos, 2,9 escaños; más el ruido
provincial, 4,0; más dos semanas de deriva, 4,5; más el error de las encuestas el día de la elección,
13,8. A dos semanas de la votación, el error compartido de las encuestas lo es casi todo. Para los
partidos de ámbito autonómico cercanos a la barrera del 3 % en su circunscripción pesan más el ruido
provincial y las encuestas regionales.

## Resultados descriptivos (el trabajo original, actualizado)

* La fragmentación tocó techo en 2019 (número efectivo de partidos de 5,8 en votos) y bajó a 4,1 en 2023.
* La volatilidad es sobre todo *interna* a los bloques: los dos mayores vuelcos (1982, 42 pp; 2015, 32 pp)
  movieron votantes entre partidos del mismo lado. El equilibrio entre izquierda y derecha es mucho más
  estable que el voto de cualquier partido.
* El voto periférico es el 7 % en el conjunto de España, pero entre el 22 y el 54 % en las provincias
  vascas, navarra y catalanas, donde las encuestas nacionales dicen menos y donde se deciden las
  investiduras.

## Cómo ejecutarlo

Requiere [uv](https://docs.astral.sh/uv/) (descarga Python 3.12). No hace falta compilador de C.

```bash
uv sync --extra dev
make all          # datos -> tests -> descriptivo -> agregador -> escaños -> backtest -> previsión -> página
```

Fases sueltas: `uv run electoral build-data | descriptive | aggregate | seats | backtest | forecast | report`.
`uv run electoral figures` vuelve a dibujar todas las figuras a partir de los resultados guardados, sin
reajustar el modelo. Las figuras y la página interactiva se escriben en inglés (`reports/figures/`,
`docs/index.html`) y en español (esta carpeta); los textos de ambos idiomas están en
`src/electoral/i18n.py` y `report.py`. El pactómetro de la página es `pactometro/template.html`;
`uv run electoral pactometro` lo escribe como página independiente (`pactometro/index.html`) para probar
cambios. `build-data` descarga los PDF y microdatos del CIS (unos 100
estudios) y los microdatos del CEO (unos 330 MB) en `data/raw/`, que git ignora. El agregador tarda unos
ocho minutos; el backtest, unos diez (los resultados de cada ciclo se guardan en `outputs/backtest/`).
Las semillas, las fechas, los escenarios de oferta electoral y los ajustes regionales están en
`config.yaml`; todos los resultados llevan la fecha de cierre de datos.

Resultados para otros proyectos: `outputs/poll_average_daily.csv` (estimación diaria de voto por partido,
con cuantiles), documentado en `docs/outputs.md`. Versión interactiva: `index.html` en esta carpeta.

## Repositorio

```
config.yaml            fechas, semilla, fuentes, modelo, escenarios de oferta electoral, capa regional, backtest
data/party_map_*.yaml  genealogía de partidos y definición de bloques (se edita aquí para discrepar)
data/regional/         tablas regionales extraídas de PDF, con sus URL
data/processed/        datos ordenados + DATA_DICTIONARY.md + DATA_QUALITY.md + cis_studies.csv + regional_polls.csv
src/electoral/         mir, wiki_polls, cis, cis_microdata, regional, build_data, model, seats, backtest, forecast,
                       plots, figures, i18n (inglés / español), pactometro, report
tests/                 D'Hondt (con la reproducción exacta de los escaños oficiales), lectores, CIS, capa regional,
                       modelo, papeletas del 29-N
outputs/               media de encuestas, efectos de casa, simulaciones de escaños, backtest, diagnósticos
reports/figures/       todas las figuras en inglés; docs/methods_note.md es la nota metodológica (en inglés);
                       docs/index.html, la página interactiva en inglés
docs/context_29N_2026.md  contexto político, oferta electoral y fuentes de la actualización del 29-N (en inglés)
spanish version/       este README, index.html y figures/ en español
pactometro/            el pactómetro (template.html) que se inserta en las dos páginas interactivas
```

## Limitaciones

* **Versión provisional.** La versión final usará las encuestas publicadas hasta el 23 de noviembre.
  Todavía falta aquí: los microdatos del estudio preelectoral del CIS (no estaban en cis.es el 14 de
  noviembre, así que entra solo como estimación oficial) y cualquier oleada del CEO posterior al 5 de
  octubre.
* **Quién cuenta como encuestadora condiciona la distancia entre PP y PSOE.** Los efectos de casa se
  centran en la encuestadora media, un voto cada una, con las diez series del CIS como una sola. Esa
  media es una decisión: con un voto por serie la distancia es de 2,4 puntos en lugar de 2,9, y una
  media simple de las encuestas privadas recientes da al PP unos cinco, porque en ella pesan más las
  encuestadoras que más publican. La probabilidad de mayoría no es sensible a esto; la de «primera
  fuerza», sí.
* **Dónde gana sus escaños el espacio del Frente Amplio es en parte una suposición.** Su parte valenciana
  sale de las siete encuestadoras que publican Compromís-Front Valencià por separado (entre el 10 y el
  23 % del espacio); el resto conserva la geografía de Sumar en 2023, que probablemente infravalora a Más
  Madrid. El modelo da al espacio 10 escaños donde el CIS y la mayoría de las encuestadoras le dan entre
  11 y 15 con un voto parecido.
* **El error común de las encuestas es el riesgo dominante** y se trata con un término de inflación
  calibrado con cuatro elecciones (veinte residuos partido-elección). A dos semanas de la votación es
  casi toda la incertidumbre.
* **La capa regional se apoya en poca evidencia.** Sus pesos se calibraron con una sola elección
  (Cataluña 2023, cuatro partidos), y entonces el CEO sobrestimó a ERC en 5 puntos. El Sociómetro
  pregunta por el Parlamento Vasco, así que se supone que su variación desde 2024 se traslada a unas
  generales. CC y Navarra no tienen fuente regional.
* **Nuestra serie con microdatos del CIS no tiene backtest**, y Adelante Andalucía entra en el modelo de
  escaños con la mediana de sus encuestas recientes (en torno al 1,3 %) y no a través del agregador.
* **No hay modelo demográfico.** La disputa de la campaña por el voto joven no está modelizada: las
  encuestas muestran a los jóvenes inclinados a la derecha con una gran brecha de género, votando menos y
  decidiendo tarde (`docs/context_29N_2026.md`, §8.5). El movimiento de última hora solo queda cubierto
  por el término de error del día de la elección.
* **Los partidos se modelizan de forma independiente** en escala logit; el modelo de escaños renormaliza.
* No se modeliza la participación; los porcentajes son sobre voto válido.

## Fuentes de datos y licencias

* Ministerio del Interior, *infoelectoral.interior.gob.es*, ficheros `02YYYYMM_TOTA.zip`. Reutilización
  según la Ley 37/2007 y el RD 1495/2011. *Origen de los datos: Ministerio del Interior.*
* Wikipedia en inglés, «Opinion polling for the [2016 / April 2019 / November 2019 / 2023 / 2026]
  Spanish general election» y las subpáginas de 2019-2022, CC BY-SA 4.0.
* Centro de Investigaciones Sociológicas, cis.es, CC BY 4.0: PDF de estimación, fichas técnicas y
  microdatos. *Fuente de los datos: Centro de Investigaciones Sociológicas.*
* Centre d'Estudis d'Opinió (Generalitat de Catalunya), microdatos abiertos del Baròmetre d'Opinió Política.
* Gobierno Vasco, Sociómetro Vasco y resultados oficiales de las elecciones al Parlamento Vasco de 2024
  (euskadi.eus).

## Autor

Kristiyan Pandas, [github.com/kristiyanpanda](https://github.com/kristiyanpanda). Grado en Sociología,
máster en Analítica de Datos. Versión interactiva de los resultados: `index.html` en esta carpeta.

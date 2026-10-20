# VT08 — Arquitecto A R6: objetivos H1 físicos «untouched» a C3 y revisión B sin PnL

**Fecha:** 2026-10-15 · **PR A:** #765 DRAFT · **PR B:** #764 DRAFT · **Issues:** A #762 / B #763 · **Estado:** `SOURCE_TARGET_LEVEL_CENSUS_ONLY / NOT_CERTIFIED`.

## 1. Trabajo ejecutado verdaderamente sobre los cinco mercados

**GitHub Actions REAL [#38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669), SUCCESS 5/5, 11 adversarial tests + Ruff PASS por job.** Fuente física: el catálogo A R4, auditado independientemente por B R7 **88.276/88.276 bar-IDs PASS** [#38748150948](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948), se cruza con todos los M15 originales de los cinco mercados.

Código nuevo `src/qore/infrastructure/trader_lab/vt08_a_h1_untouched_high_source_witness_v1.py`, pruebas `tests/infrastructure/trader_lab/test_vt08_a_h1_untouched_high_source_witness_v1.py`, workflow `.github/workflows/vt08-a-h1-untouched-target-native-source-census.yml`. HEAD verificado del workflow R6: `4ee9930a576f8185299fb4f7e376191511fb0ed7`.

**Fuente TTrades verificable:** [How to Set Price Targets Using the Fractal Model, May 23 2026](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/). El autor indica *previous higher-timeframe highs* para bullish y que se prefieren niveles *untouched*. El autor NO ofrece una regla global de desempate para varios highs anteriores y mezcla swings y candle extremes. Este R6 usa **todos los máximos de velas H1 cerradas**, no intenta etiquetar cada máximo como «swing relevante» TTrades.

Mecanismo:
1. Leer **M15 físico completo**, market/SHA autenticado; construir cada H1 solamente con **4 M15 contiguas y cerradas**, reloj UTC exacto.
2. Desde que H1.close está disponible, ese H1.high es un nivel *physically observed*. Si una M15 posterior tiene `high >= level`, el nivel se considera tomado (no untouched). Se aplica mientras ese segmento de M15 no tiene huecos.
3. **Con cualquier discontinuidad M15**, reset de todos los niveles activos; por lo tanto nunca se afirma «untouched» cruzando tramos no observados (incluye periodos normales de cierre de mercado que aparecen como gap; NO identificar todos como error del broker).
4. Para cada C3.open congelada, avanzar solo barras cuyo `closed_at <= C3.open`. Se cotejan las dos M15 constituyentes de C2 contra barras nativas RAW, SHA bar-ID/market/fuentes y `available_at`. **No leer ninguna M15 posterior** ni precio de salida.
5. Reportar TODAS las posibles `H1.high` disponibles como fuentes con `origin_h1_closed_at`, **cuatro `source_m15_bar_ids`**, distancia temporal y flag *above C2.close* para diagnóstico; NO seleccionar una automáticamente, NO usar entradas sintéticas, stops, target exit, profit, spread, sizing o reranking por RR.
6. Resultado `author_target_relevance_verified=false`, `author_target_selected=false`, `source_complete_entries=0` y `profit_factor=null`. `C2.close` es referencia geométrica, NO precio ASK ejecutable en C3.

## 2. Resultados exhaustivos de los 2.657 contextos

| Mercado | Total C2 candidatos | Ningún H1 high observado | Solo un H1 high | Varios H1 highs | Al menos uno > C2.close | Saltos de fuente que resetean |
|---|---:|---:|---:|---:|---:|---:|
| EURJPY | 538 | 0 | 46 | 492 | 538 | 239 |
| USDCHF | 518 | 0 | 50 | 468 | 518 | 240 |
| NZDUSD | 550 | 0 | 36 | 514 | 550 | 243 |
| CADJPY | 516 | 0 | 51 | 465 | 516 | 239 |
| USDCAD | 535 | 0 | 37 | 498 | 535 | 241 |
| **TOTAL** | **2.657** | **0** | **220** | **2.437** | **2.657** | **1.202** |

**Lectura correcta:** ~91.7% de estos contextos poseen MÁS DE UN nivel físico anterior H1 aún sin tocar desde su formación dentro del segmento gap-free. Elegir `nearest`, `highest`, `best-RR` o `reached-in-future` sería **inventar una regla de desempate D**, no fidelidad al autor. Los 220 casos de nivel único tampoco implican 220 señales ni 220 órdenes: falta swing relevante, POI, PS/CISD, breaker, stop y validación de target HTF para la familia concreta. El flag `above C2.close` NO verifica `entry_price` ASK.

**Artefactos JSON Actions, 30 días, con SHA256 del contenido canónico**:
- EURJPY: artifact `11986412364`, `c756b54cf0fe5c7067521c5a9aead942afd9d64c800f915eb2690cfae7e148e1`.
- USDCHF: artifact `11986418212`, `542ed612a3e46c7c00e937ecab5dd33859284ca786c48a2324f8b4c0fdc1a55b`.
- NZDUSD: artifact `11986702568`, `dc56b20075cec2b3347bd61e6df9488c3c8a8bd2d1d394abbc5238140c16962b`.
- CADJPY: artifact `11985834667`, `8ed517ce4c8f66d6e8e42456a85fe73287e03a063da48c6cfdc123187d2cf32d`.
- USDCAD: artifact `11986488122`, `f1d40dc4330828666a60533c053de24715e54e93e4aa544a99a5df1c3ed911e6`.

Se contaron **92.626 H1 completas** y **82.493 niveles H1 retirados por un touch observado**, en 5 historiales. Esos niveles no son 92.626 setups ni trades. Los resets no demuestran corrupción; son una cuarentena precautoria de intervalos sin serie M15 continua.

## 3. Revisión independiente solicitada a B

Para cerrar el componente de «target untouched» B debe:
- Descargar 5 artefactos del [run #38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669), reejecutar un **algoritmo independiente** contra archivos M15 originales; corroborar por caso que la H1 comenzó en hora entera, se compuso de cuatro M15 y que ningún M15 posterior en el segmento gap-free tocó/superó el high antes de C3.
- Examinar casos de nivel único y casos múltiples, incluyendo controles negativos touch exacto, H1 rota por gap, nivel en C3 no disponible y cross-market. **No usar el algoritmo A como oráculo**.
- Adjudicar qué highs requieren confirmación fractal/relevant swing o si un high de la última H1 cerrada es objetivo TTrades plausible en esta familia; documentar cómo se resuelve competencia de múltiples highs con pruebas textuales/video del autor. Cuando no haya especificación, mantener `AMBIGUOUS_D`; un ranking QORE-C debe etiquetarse como otra estrategia y requerir nuevo prerregistro.
- No mezclar los targets H1 de esta auditoría con TP `2R` del viejo B01, el CE LIMIT del acelerador o salidas posteriores. No inferir fills o PF del catálogo.
- Mantener las barreras B R7 contra cross-market SHA y las 27 `CAUSAL_FIELDS` en modo fail-closed mientras fuente semántica siga incompleta.

## 4. Certificación y gobernanza

**NOT_CERTIFIED:** 0 author-complete signals, 0 cognitive admissions genuinas, 0 broker fills con salida, `PF/DD/Sortino/Sharpe=NOT_MEASURED`, OOS 7Y sellado, sin sizing/compounding/leverage, sin cambios a VPS/DEMO/LIVE, sin merges. La priorización de los 220 casos de target único para review B no autoriza seleccionar solo operaciones ganadoras ni omitir los 2.437 ambiguos en el cálculo posterior de densidad / fallos del método.

**Próximo P0 de A:** swing relevante válido previo a C2 y breaker real con identidades de barras, revisión ciega B y source-rule exacto. Solo cuando la metodología A+B tenga reconocimiento independiente y BID/ASK+fees homogéneos para un histórico representativo deben ejecutarse los Gates económicos preregistrados.

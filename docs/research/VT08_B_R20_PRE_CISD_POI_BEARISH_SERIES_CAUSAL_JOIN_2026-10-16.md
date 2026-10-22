# VT08 B R20 — POI H1→serie opuesta M3→CISD: auditoría causal independiente

**Fecha:** 2026-10-16 · **Arquitecto B:** `agent/vt08-5m-cognition-replay-20261010` · PR #764 DRAFT. **Estado:** `PHYSICAL_M3_POI_RUN_CAUSAL_JOIN_PASS / SOURCE_POI_SIGNIFICANCE_D / VT08_NOT_CERTIFIED`. **Mandato Owner:** programa único VT08 actual con TTrades + cognitiva VT08; QORE-alpha está excluido totalmente, sin importar estrategias ni usar sizing, ni holdout 7Y, ni LIVE/DEMO/VPS.

## Objetivo no redundante respecto R18/R19

R18 había registrado **165** FVG alcistas H1 con primer contacto M3 cerrado ANTES de la **vela CISD**, pero eso NO implica que las velas opuestas **que formaron el Protected Swing** hayan movido el precio hacia el FVG. [TTrades, Let The Wick Form, Trade The Body (29-ago-2026)](https://ttrades.com/let-the-wick-form-trade-the-body-stop-getting-stopped-out/) y [Protected Swings in Trading (06-ago-2025)](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/) requieren el `important level` y posterior cierre por la serie de velas que originó el mínimo. [Ideal Formation (27-jun-2026)](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/) advierte no confundir simple cierre C2/C3 con PS auténtico en POI significativo.

**B R20 sí reconstruye todo el enlace temporal físico**: R18 originales HTF H1/M15 + R19 muestra pre-PnL sellada + R14 run M3 independently verified + A R3 congelado + raw cTrader M3 SHA y `source_bar_id`. Clasifica PRIMER contacto FVG H1 respecto al inicio de la serie de M3 bajistas que termina en CISD, y además comprueba SI HUBO contacto posterior **durante la serie**, y si al menos una vela M3 contiene simultáneamente `low < C1.low` (barrido) y contacto con zona FVG. No infiere orden de ticks dentro de esa vela, ni POI relevante ni Protected Swing auténtico.

## Código, adversarios y original pin

- Código `src/qore/infrastructure/trader_lab/vt08_b_r20_poi_opposing_run_causal_join_v1.py`.
- Tests `tests/infrastructure/trader_lab/test_vt08_b_r20_poi_opposing_run_causal_join_v1.py`.
- CI `.github/workflows/vt08-b-r20-poi-opposing-m3-source-join.yml`.
- **[GitHub Actions FINAL #38975212429](https://github.com/mezas3238-hue/qore-core/actions/runs/38975212429)**, **5/5 SUCCESS** + Ruff + 14 pruebas adversariales por mercado = **70 PASS**. La primera corrida [#38974979724](https://github.com/mezas3238-hue/qore-core/actions/runs/38974979724) falló por Ruff import/long line, solucionado sin debilitar verificaciones; [#38975045620](https://github.com/mezas3238-hue/qore-core/actions/runs/38975045620) 5/5 SUCCESS sobre conteo inicial; corrida final añadió conteos direccionales, validó no suponer tick order, y pasó 5/5.
- Descarga de artefactos fijos:
  - R3 A original `#38715560333`, `vt08-a-frozen-m30m3-firstfail-MARKET-394116f13449fc310d7fbc5f0b5f60aa1bb247d4`.
  - Original M3 cTrader `#35941643396`, `qore-vt08-m3-fractal-MARKET-bc1379d7661aac202495ec67afdd3098473ba723`.
  - R18 final `#38902918264` `vt08-b-r18-pre-cisd-poi-MARKET-9349cc84ee245c68291db60b4613411453061c94`.
  - R19 final `#38903529731` `vt08-b-r19-blind-poi-MARKET-e999e127be84a1ebb9d3e8b1d13e110cfa2cb51a`.
- R18/R19 objetos íntegros verificados contra SHA256 por mercado previamente congelados, y 2.657 individuales cotejados con R14 reconstrucción RAW. **Ningún PnL, outcomes, sizing, órdenes ni fill.**
- Fichas R19 107/107 enriquecidas SIN cambiar la selección por seed ni los estados de firmas `A=null/B=null`. Campos nuevos: `opposing_series_opened_at_utc`, primera interacción respecto a ese instante, `bearish_series_fvg_touch_bar_ids`, `bearish_series_sweep_bar_ids`, coincidencia en vela M3, `same_m3_bar_event_order_proven_by_ticks=false`, y `author_validated_swing/PS=false`. Si `first_touch` R18 difiere en precio, bar ID o cutoff del raw M3, falla el job completo.

## Resultado íntegro, 5 mercados, 2.657 eventos

| Mercado | Casos | FVG H1 bullish previos | 1er contacto antes run | 1er contacto durante run | Antes run, luego RETOUCH durante run | Bullish FVG tocado durante run | Coincidencia M3 sweep+touch |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURJPY | 538 | 52 | 17 | 14 | 15 | 29 | 29 |
| USDCHF | 518 | 59 | 23 | 13 | 18 | 31 | 31 |
| NZDUSD | 550 | 59 | 19 | 14 | 15 | 29 | 29 |
| CADJPY | 516 | 59 | 18 | 15 | 11 | 26 | 26 |
| USDCAD | 535 | 61 | 18 | 14 | 14 | 28 | 28 |
| **TOTAL** | **2.657** | **290** | **95** | **70** | **73** | **143** | **143** |

**Descomposición inmutable de 290 FVG bullish:** primer contacto antes del inicio de bearish run 95 (73 de ellos vuelven a tocar durante la run, **22 nunca retocan durante la run**); primer contacto dentro de run 70; primer contacto en la barra de CISD 4 (INTRABAR UNKNOWN), primer contacto después de CISD 12, no tocados en C2 109. El conjunto de 143 `bearish_series_touched_fvg` contiene los 70 primeros contactos durante run + 73 retouches tras un contacto previo. Dentro de los 143, contacto FVG y sweep de C1.low ocurrieron en una **misma barra M3**; esto **NO prueba** si primero ocurrió el sweep o el contacto dentro de esa vela. La estructura original de la serie M3 bearish/cierre sobre nivel está independiente verificada por R14, pero no es un `Protected Swing source-complete` por sí sola. `C1.low` no se ha seleccionado como `important level` legítimo por autor para cada caso.

**No confundir 143 con trades.** Este universo **no excluye** POI tipo low/high fuera del FVG, POI más antiguos ni de otra TF, y el target/stop/PS/EQ siguen no adjudicados. Seguir conservando 2.657 denominador original. El estrato de 143 muestra únicamente compatibilidad física más próxima a la narración cualitativa de TTrades para el POI H1 FVG **de las tres H1 completas PRE-C2**.

**SHA256 de informes finales R20 sin modificación:**
- EURJPY `4408333b40703a383119e83b04cbaa1164dc21948ba3673b92ceafdc5e82f706`
- USDCHF `74fc303ed9269014131f163bf8d44e44f4ae2285af78c3695935d1fd6ac7ae16`
- NZDUSD `b8956e81ab20429284f359cd2af99bb71afda8bb27fe2523c990ab9005377114`
- CADJPY `f001dd4263a02c8a8c72cbc5295319955800c94608f47bcc0ca27b9d2d418440`
- USDCAD `17381f63e6a0bdb78a7b55bdf122052411a1aeca1417c778cd312680d36f61e3`

## Cierre siguiente paso real: adjudicación semántica y bloqueo

1. **Arquitecto A**: revisar PRIMERAMENTE 107 fichas blind R19+R20 junto con estratificación de los **143** físicamente enlazados: para cada caso identificar source swing externo válido, si FVG era aún POI importante o había sido invalidado previamente, si la serie `down-close` descrita por el autor de verdad creó ESE extremo, adjudicar protected swing, e identificar POI alternativo high/low donde falta FVG. Registrar `source_url+section`, `bar_ids/level/available_at`, clasificación A/B/D y firma A **real**, NO la etiqueta de la fuente como si fuera una firma. No retener solo casos favorables.
2. **Arquitecto B**: revisar independientemente fuente M3/M15 sin depender del productor A, registrar desacuerdos, distinguir mismo M3 de ticks (UNKNOWN), y abstener ante D. No certificar por “143 tocados” o `fvg_bearish_run_touched=true`; no se permite elegir low/H1 por beneficio futuro.
3. **A+B**: tras el swing/POI/PS REAL, elegir EQ C2 condicional, breaker y stop bajo EQ+breaker del Example1, target untouched, 27 campos cognitivos `CAUSAL_FIELDS` con hashes firmados. El manejo de D debe ser `WAIT/ABSTAIN`.
4. **Auditor económico futuro**: congelar Gates, obtener histórico BID/ASK+costes y revisar OOS sin abrir 7Y sellado antes de autorización. PF/DD/Sharpe/Sortino no evaluables ahora.

**Estado:** `R20_SOURCE_PHYSICAL_5OF5_PASS`; `AUTHOR_COMPLETE_ENTRIES=0`; `REAL_COGNITIVE_ADMISSIONS=0`; `BROKER_FILLS=0`; `GATES=NOT_EVALUABLE`; `QORE_ALPHA_EXCLUDED`; VT08 **NO CERTIFICADO**.

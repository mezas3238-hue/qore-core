# VT08 B R11 — CISD M3 proxy versus cierre HTF M30 C2, censo físico exhaustivo
**Fecha:** 15-oct-2026 · **Rama B:** `agent/vt08-5m-cognition-replay-20261010` / PR #764 DRAFT · Coordinación A #762 / B #763.
**Veredicto:** `R11_CAUSAL_CLOCK_PASS / ORIGINAL_TTRADES_TEMPORAL_ORDER_UNADJUDICATED_D / VT08_NO_CERTIFICADO`.

## Ejecución y alcance REAL
[GitHub Actions R11 #38789768406](https://github.com/mezas3238-hue/qore-core/actions/runs/38789768406): **5/5 SUCCESS**, `head_sha=cd2deee6dd60e3325ceb447747d6aa03488ad288`; Ruff, **12 tests adversariales × 5 = 60 ejecuciones**; cTrader **M3 auténtico** y R3 de A inmovilizado por SHA/run (`38715560333`), no snapshots de PnL, no run del productor A, cero OOS/holdout.

Código fuente B independiente: `src/qore/infrastructure/trader_lab/vt08_b_r11_cisd_after_htf_close_chronology_v1.py`; tests `tests/infrastructure/trader_lab/test_vt08_b_r11_cisd_after_htf_close_chronology_v1.py`; workflow `.github/workflows/vt08-b-r11-independent-m3-cisd-htf-closure-chronology.yml`.

## Resultado principal: cronología de 2.657 casos M30 C2→M3 CISD

| Mercado | C2 con M3 PS proxy único | M3 confirmó ANTES del cierre C2 | M3 confirmó EXACTAMENTE al cierre C2 | M3 confirmó DESPUÉS del cierre C2 |
|---|---:|---:|---:|---:|
| EURJPY | 538 | 507 | 31 | 0 |
| USDCHF | 518 | 483 | 35 | 0 |
| NZDUSD | 550 | 519 | 31 | 0 |
| CADJPY | 516 | 481 | 35 | 0 |
| USDCAD | 535 | 514 | 21 | 0 |
| **TOTAL** | **2.657** | **2.504** | **153** | **0** |

**2.504/2.657 = 94,2%** del M3 `cisd_confirmed_at` geométrico precede el cierre de SU PROPIA C2 M30. **153/2.657 = 5,8%** coincide en instante de C2.close, no es un paso secuencial demostrado *después*. **Ningún** M3 de esta subfamilia se confirmó `> C2.close` porque por construcción A buscó dentro de C2. Una propuesta de entrada C3.open no convierte retroactivamente el M3 CISD interno en un LTF post-cierre.

Los 2.657 recibos preservan `source_bar_id` físico recomputado directamente de los nativos M3 cTrader con raw SHA, OHLC, reloj de 3 min y `available_at`; el timestamp CISD comunicado por A se exigió igual al cierre de una de las diez M3 físicas de C2. Un evento no puede superar su `C3.open=C2.close`. `C1.close=C2.open` sí precede siempre a la M3 CISD; **eso no demuestra** que C1 fuese la vela HTF de confirmación requerida por TTrades. Las 10 M3 de C2 fueron comprobadas físicamente para cada evento, NO la validez semántica del detector PS/CISD A.

**Distribución de minutos que anteceden C2.close (sumas de 5 mercados):**

| Minutos antes C2.close | Casos |
|---:|---:|
| 0 | 153 |
| 3 | 219 |
| 6 | 246 |
| 9 | 228 |
| 12 | 285 |
| 15 | 251 |
| 18 | 259 |
| 21 | 350 |
| 24 | 666 |
| **Total** | **2.657** |

Fuente: salida JSON de los cinco jobs Actions R11. Estos tiempos no son outcomes, ni densidades ejecutables; solo clases de disponibilidad física.

## Implicación concreta para metodología y cognitiva
El texto primario [How CISD Confirms Swing Points (TTrades, 10-Jan-2026)](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) expone el orden **higher-timeframe closure → lower-timeframe CISD → continuation**. No determina por sí solo cuál vela HTF debe ser esa confirmación para la familia congelada M30 C2/3. Por tanto:
- **R11 NO invalida automáticamente 2.657**, porque quizá el cierre HTF relevante fue C1 u otra estructura superior ya disponible.
- **R11 SÍ refuta** la afirmación *«las 2.657 confirmaciones M3 ocurrieron después de su propia C2.close»*. No puede autorizarse esa lectura causal.
- Pedir a A **source-first y sin PnL** por ID: `htf_confirming_candle_id`, tipo C2/C3/otra, `closed_at`, `ltf_cisd_confirmed_at`, evidencia específica de excepción intrabar si existe, exacta URL/sección y clasificación A/B/C/D. Si no hay autoridad fuente para HTF anterior, `AUTHOR_TEMPORAL_SEQUENCE_D` y `SOURCE_COMPLETE=false`. Una decisión nueva que exija post-C2 CISD cambia la familia: nuevo source identity y nuevo prerregistro, no recodificar silenciosamente el censo existente.
- B cotejará las fichas de A con R11; no se acepta `CandidateEvent SOURCE_COMPLETE` ni los 27 `CAUSAL_FIELDS` a partir de PS geométrico interno. R10 (inventario completo 2.657) ya mantiene 71.739 pares campo-evento sin recibos fuente, cero admisiones, 0 fills.
- No ajustar cronología o seleccionar los 153 de igualdad por PnL: el instante igual sigue sin demostrar secuencia posterior y **todos** 2.657 quedan en el denominador.

**El prototipo viejo QORE M30/M3 económicamente falsado NO se rehabilita** con esta prueba. R11 sólo establece un hecho temporal nuevo, verificable y potencialmente decisivo para la fidelidad al autor.

## Gate y prohibiciones
`R11_PHYSICAL_CAUSAL_ORDER=PASS` · `AUTHOR_TIMING=UNADJUDICATED_D` · `C0_COGNITION=BLOCKED` · `X0_BIDASK=NOT_EVALUABLE` · `PF/DD/Sharpe/Sortino=NOT_MEASURED`. A/B manifest `None`. Sin sizing, no 7Y sellado, no VPS/LIVE/DEMO operativo, no órdenes y sin merge. Los runs rojos de QA inicial #38789689915 por regla de nombre Ruff no se ocultan: se corrigió sin relajar verificador y el run #38789768406 está verde.


## Addendum de corrección metodológica — B R20, 16-oct-2026

**R11 mantiene sus 2.504/153/0 relojes físicamente exactos, pero NO impone una secuencia cronológica poscierre como regla TTrades.** La fuente original [CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) indica que el CISD LTF se examina **dentro de la misma vela HTF C2/C3** una vez la vela cerró, mientras [Fractal Model Playbook](https://ttrades.com/fractal-model-playbook-aligning-daily-hourly-and-5-minute-charts/) lo confirma para C2. El orden textual de revisión no establece que el cierre físico del M3 CISD deba ser posterior a C2.close.

El [R20 independiente](VT08_B_R20_NATIVE_2657_C1_LOW_SWEEP_CISD_CAUSAL_ORDER_AND_TTRADES_INTRAC2_RULE_2026-10-16.md), [Actions #38902326551](https://github.com/mezas3238-hue/qore-core/actions/runs/38902326551) **6/6 SUCCESS**, reconstruyó desde las barras originales **2.657/2.657 barridos C1.low observables ANTES de CISD M3**, con C2.close disponible en C3.open. **Causalidad física PASS** para esos tres hitos; `POI_IMPORTANCE`, `PS_AUTHOR`, `BREAKERS`, `SWING`, `EQ`, `TARGET` todavía D; 0 entradas fuente completas. Nunca invalide/seleccione los 2.504 por una regla poscierre supuesta.

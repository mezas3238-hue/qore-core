# VT08 Arquitecto A — R5: EQ condicional físico y matriz source-first de breaker/target

**Fecha:** 2026-10-15 · **Rama A:** `agent/vt08-5m-methodology-source-20261010` · **PR A:** #765 draft · **B:** PR #764 / Issue #763 · **Estado:** `PARTIAL_AUTHOR_RULE_ARITHMETIC_READY / NOT_CERTIFIED`.

## 1. Trabajo físico REAL ejecutado hoy (no backtest)

[GitHub Actions #38747954308](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308) **SUCCESS 5/5**, 9 tests adversariales y Ruff PASS por job; prueba de cinco mercados sobre las capturas físicas CANÓNICAS A→B de [#38740699499](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499) y sus hashes por mercado. Código `src/qore/infrastructure/trader_lab/vt08_a_source_conditional_eq_review_v1.py`, tests `test_vt08_a_source_conditional_eq_review_v1.py` y nuevo workflow `.github/workflows/vt08-a-c2-conditional-eq-author-source-review-v1.yml` (commit del workflow `57a6fa70f8a14ff26a6249b39d1f3e4725aa0a4c`). Ningún evento se seleccionó por resultado.

| Mercado | EQ condicional revisable | H1 previo incompleto | Artifact ID | SHA256 salida JSON canónica |
|---|---:|---:|---:|---|
| EURJPY | 538 | 0 | [11978559213](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308/artifacts/11978559213) | `83ddd6e749643a2a0d09c8c85c03bba88a824c4fd13da13dc653ec96e2f8137e` |
| USDCHF | 518 | 0 | [11978808610](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308/artifacts/11978808610) | `56624a9806426a02067fff7fe4d5b80a320f5426a0e2b7d9a92b5d5cc55d7f7c` |
| NZDUSD | 550 | 0 | [11979097884](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308/artifacts/11979097884) | `c3655a24d904819f96b53f19375a862c2333f97e48aa820e0f858a415e3b87d6` |
| CADJPY | 516 | 1 | [11979147756](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308/artifacts/11979147756) | `88ce9cb565d4519f5656c27b84309313080b04879fffbb84dc8bec68754e9192` |
| USDCAD | 535 | 0 | [11978868854](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308/artifacts/11978868854) | `4e4a3bfc450a69b30a43c102ca9ecef8df85acc4af834049c31cfc9a0f3e3cc3` |
| **Total** | **2.657** | **1** | 5/5 PASS | — |

SHA de salida calculado sobre JSON canónico compacto, no sobre bytes ZIP. Los ejemplos contienen **ambas expresiones aritméticas**: `EQ_FULL=(C2.H+C2.L)/2` y `EQ_CLOSE_TO_LOW=(C2.C+C2.L)/2`. El primero es aplicable **CONDICIONALMENTE** cuando B haya validado un **swing bullish conocido pre-C2** y el cierre bullish con él, como sucede geométricamente con el cuerpo bullish de la C2 de esta familia. El segundo solo es aplicable si ese mismo C2 cerrase **en contra** de un swing bullish auténtico; **no debe seleccionarse simplemente porque produce stop/TP favorables**. El contrato no elige ninguno como EQ TTrades real: `eq_selection_authorized=false`.

Se comparan OHLC C2 desde 10 M3 Y 2 M15; IDs/SHA de barras, grupo H1 anterior, mercado del feed, `available_at` y `decision_at=C3.open`. Tests rechazan bytes/bar IDs alterados, mezcla de mercados, C2 sin cierre, contexto H1 mal trazado, duplicados y falsos certificados. La única ventana CADJPY sin H1 física anterior permanece **NO evaluable semánticamente**, sin imputar.

## 2. Adjudicación AUTOR escrita vs decisión discrecional D

### 2.1 Swing relevante PRE-C2 — principal bloqueo

[Fuente original Relevant Swings, 21-Mar-2026](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/): swing básico por pivot izquierda/derecha, **relevance = extremo significativo con valid separation**; el propio autor advierte que **no existe fórmula numérica estricta de separación**. La ventana de tres HTF velas incluye la actual pero no permite conocer sus máximos futuros. Un simple mínimo de 3 H1 previamente cerradas es contexto verificado C-QORE, NO swing autor seleccionado.

**Precondición de A:** por evento registrar `relevant_swing_id`, `swing_direction=BULLISH`, `source_timeframe`, `left/right closed bar IDs`, `candidate_qualified_at <= C2.open`, `separation_explained`, `liquidity_extreme_context` y decisión ciega explícita `AUTHOR_VALID / AUTHOR_INVALID / AMBIGUOUS_D`. No determinar relevancia a través de ATR/wick%/pivot automático sin llamarlo heurística C. Si no se logra, `NO_ESPECIFICABLE` para ensayo económico.

### 2.2 EQ C2 — expresión resuelta, selector NO

[Fuente EQ, 10-Oct-2026](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/), apartados *When C2 Closes Against/With the Swing Point*: C2 a favor swing bullish usa rango entero; C2 en contra de bullish usa cierre→mínimo. El nivel solo es autorizado si referencia swing válida estaba observable **antes** de C2.open. C2 OHLC completo solo se usa a C2.close = C3.open. El código aporta precio y ID físico verificables, NO atestación de swing; incluso en C2 con cuerpo alcista el `eq_swing_identity_author_adjudicated` permanece false.

### 2.3 Breaker auténtico — no confundir geometría 4 velas

[Fuente Breaker Blocks Simplified, 05-Jul-2025](https://ttrades.com/breaker-blocks-simplified/), bullish `LOW → HIGH → LOWER LOW → HIGHER HIGH`, con zona de una o varias velas **up-close** dentro del leg antes del lower low. [Continuation Breaker, 03-Aug-2025](https://ttrades.com/trading-breaker-blocks-for-continuations/): higher high es confirmación causal; la entrada por retest de una *continuation breaker* es OTRO modelo, no cambia la única entrada POS congelada.

**B debe exigir bar IDs de cada cuatro hitos ordenados, sus `confirmed_at`, bar IDs de up-close constituyentes, bounds de zona y `breaker_low`, con todos confirmados <= C3.open.** Dos breaks geométricos o dos zonas plausibles sin selector del autor -> `AMBIGUOUS_D`; no escoger el mínimo del PS-only, no generar stop hasta resolver identidad. No inventar condición de "4 M3 consecutivas".

### 2.4 Stop / FVG / target

[Timeframe Alignment Example 1, 30-Jul-2025](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/): el stop del long debe estar por debajo de **EQ M30 Y low del breaker**, dejando espacio para el FVG inferior cuando se forme la continuación. La expresión `SL < min(EQ, breaker_low)` es una condición **necesaria**, pero exige previamente un breaker auténtico, EQ válido y un plan definido para FVG. No fijar tick buffer/broker por PnL.

[Price Targets, 23-May-2026](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/): en bullish targets son highs anteriores HTF **untouched**, no niveles consumidos. Para cada candidato de target se requiere `origin_bar_id`, `known_at`, `untouched_test_cutoff=C3.open` y verificación continua en la serie hasta el cutoff; existencia de 12 barras H1 anteriores por sí sola **NO** basta para demostrar untouched. Si hay varios highs auténticos, orden/desempate sigue `D`; no elegir éxito ex post, ni un TP 2R fijo QORE.

## 3. Paquete para doble adjudicación B (ningún PnL)

Una fila por cada uno de los **2.657 casos**, llave fija `(market,c2_opened_at_utc,decision_at_utc)` y SHA de fuente, que los revisores independientes deben analizar sin leer resultados ni eventos posteriores a la decisión:

```json
{
  "review_schema": "VT08_A_B_BLIND_AUTHOR_SEMANTIC_REVIEW_DRAFT_V1",
  "source_case_id": "MERCADO|C2_UTC",
  "reference_swing": {"status": "AMBIGUOUS_D", "bar_ids": [], "qualified_at": null, "reviewer_rationale": null},
  "poi": {"status": "AMBIGUOUS_D", "bar_ids": [], "qualified_at": null, "reviewer_rationale": null},
  "cisd_ps": {"status": "AMBIGUOUS_D", "series_bar_ids": [], "ps_bar_ids": [], "confirmed_at": null},
  "eq": {"status": "BLOCKED_ON_SWING", "physically_calculated_value": null, "regime": null},
  "breaker": {"status": "AMBIGUOUS_D", "four_milestone_ids": [], "up_close_zone_bar_ids": [], "confirmed_at": null},
  "stop": {"status": "NOT_DEFINED", "broker_tick_proof": null},
  "target": {"status": "AMBIGUOUS_D", "source_high_ids": [], "untouched_evidence_ids": []},
  "rater1": null,
  "rater2": null,
  "adjudication": null,
  "methodology_valid": false,
  "cognitive_ready": false,
  "authorized_trades": 0
}
```

**Campos vacíos por diseño:** la tabla no simula respuestas de reviewers, no transforma automáticamente semántica discrecional en regla A. B debe publicar desacuerdos antes de manifiesto firmado; auditar por separado cada campo de los 27+ de Situation con su valor, bar-ID/SHA/availability (un hash formalmente correcto no prueba relevancia).

## 4. Resultado y ruta de certificación

- Nuevo entregable **reproducible y parcial**: 2.657 expresiones EQ condicionadas a la referencia del autor y C2 física, 5 mercados nativos, un H1 incompleto.
- **No resuelto:** auténtico swing y POI pre-C2; breaker-low/source-bar selection; target untouched; PS/CISD semánticos; integridad cognitiva end-to-end; homologación BID/ASK+fees y OOS; umbrales Sharpe/Sortino/robustez congelados por Owner.
- Economía: `0 source-complete`, `0 cognitive admissions`, `0 verified fills`, `PF/DD/Sharpe/Sortino NOT_MEASURED`. No inventar certificación por CI.
- No sizing/leverage/compounding, no 7Y holdout, no VPS/DEMO/LIVE, no merge. Las ramas #765 y #764 siguen en investigación.

**A/B siguiente tarea inmediata:** revisión independiente de la identidad del swing por parte de B, y de POI/Breaker/Target en los ejemplos de los cinco mercados, no más search sobre PnL geométrico.

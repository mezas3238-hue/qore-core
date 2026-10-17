# VT08 — R20: resolución documental de CISD intravela y cronología causal M3 desde barras reales

**16 de octubre de 2026** · Arquitecto B · `mezas3238-hue/qore-core` · rama `agent/vt08-5m-cognition-replay-20261010` · PR #764 DRAFT / A #765 DRAFT.

**Resultado:** `R20_NATIVE_SWEEP_TO_CISD_PHYSICAL_PASS` / `HTF_C2_AND_LTF_M3_BOTH_AVAILABLE_AT_C3_PASS` / `AUTHOR_IMPORTANT_POI_PS_VALIDITY_PENDING_D` / `VT08_NOT_CERTIFIED`.

## 1. Resolución de ambigüedad REAL al revisar el autor, sin reoptimización

**Artículo fuente exacto del autor:** [How Change in the State of Delivery (CISD) Confirms Swing Points, 10 enero 2026](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/), secciones **How I Use CISD With Swing Points** y **Valid Candle 2 Closure With CISD**, explica revisar el CISD **dentro de esa vela HTF C2/C3** tras tener el cierre confirmado; **The Fractal Nature of the Model** dice “HTF closure first → LTF CISD → continuation”. Las dos frases no obligan a inventar que **el cierre físico M3 del CISD** suceda después del cierre cronológico HTF de C2: la secuencia describe la *validación/revisión as-of*, no que el CISD físico, reconocido retrospectivamente en las velas internas, tenga que esperar a C3.

**Corroboración primaria independiente por otra publicación del MISMO autor:** [Fractal Model Playbook, 11 agosto 2025](https://ttrades.com/fractal-model-playbook-aligning-daily-hourly-and-5-minute-charts/), sección **Step Three**, instruye explícitamente localizar CISD de **Candle 2 (hourly) en 5-minute**. [Positional Entries, 8 agosto 2026](https://ttrades.com/positional-entries-enter-before-the-expansion/) establece que al abrir C3 el **Fractal Model** anterior debe estar completo y el protected swing formado; no otorga automáticamente la validez de cada PS proxy.

**RECTIFICACIÓN respecto de B R11:** R11 constató correctamente 2.504 CISD M3 dentro de C2 antes de su cierre y 153 exactamente al cierre. El riesgo lógico era usar esos tiempos para invalidar los 2.504 por una presunta regla de ocurrencia física `cisd.closed_at > c2.closed_at`. Esa presunta regla **NO DEBE IMPONERSE COMO TTRADES**. R20 formaliza que **HTF_C2_CLOSE as-of C3** y **M3_CISD_EXISTS_INSIDE_C2 as-of C3** son dos comprobaciones separadas. *La fuente no hace source-author-complete por sí sola*: high/low relevante, POI, PS, breaker/SL, EQ y objetivo siguen D.

## 2. Nuevo ensayo originario, 100% sin PnL

**CI VERIFICADO:** [GitHub Actions R20 #38902326551](https://github.com/mezas3238-hue/qore-core/actions/runs/38902326551) **SUCCESS 6/6 jobs**, HEAD `e5d06672860b11513cfad5c281b65f125b0a08e4`; 14 casos de tests adversariales + Ruff y cinco trabajos reales cTrader M3. Reutiliza originales inmovilizados A R3 run #38715560333, A R7 run #38765076497 y cTrader M3 run #35941643396 por artifact + SHA; conserva 2.657 casos, sin consulta a fills/PnL/outcomes ni 7Y.

**Independiente B:** `src/qore/infrastructure/trader_lab/vt08_b_r20_intrac2_cisd_sweep_causal_order_v1.py` no importa el productor de A: compara cada barra C1 (10 M3) y C2 (10 M3) contra **bytes del original M3**, source SHA/ID, OHLC, UTC, closed_at y available_at. Reconstruye `C1.low` y el primer cierre M3 en C2 con `low < C1.low`; coteja que el M3 declarado CISD por A sea cierre real de una de las diez M3 y que `C3.open=C2.close`. También rechaza falsa metodología completa, barras futuras, duplicados, ambigüedad de clocks y universe drift. La **semántica del important level** no se deduce del hecho OHLC.

| Mercado | Precursores R3 | C1.low barrido observable ANTES del CISD M3 | Barrido en misma M3 del CISD | Barrido posterior al CISD | CISD antes de C2.close | CISD en C2.close |
|---|---:|---:|---:|---:|---:|---:|
| EURJPY | 538 | 538 | 0 | 0 | 507 | 31 |
| USDCHF | 518 | 518 | 0 | 0 | 483 | 35 |
| NZDUSD | 550 | 550 | 0 | 0 | 519 | 31 |
| CADJPY | 516 | 516 | 0 | 0 | 481 | 35 |
| USDCAD | 535 | 535 | 0 | 0 | 514 | 21 |
| **TOTAL** | **2.657** | **2.657** | **0** | **0** | **2.504** | **153** |

**Este resultado prueba exclusivamente que el mínimo de C1 es un nivel físico barrido causalmente antes del cierre CISD M3** y que el cierre C2 está disponible al instante de entrada posicional propuesto `C3.open`. NO prueba que C1.low sea el `important level` correcto del autor: un low cualquiera del gráfico no basta. NO prueba que la serie M3 opuesta, por válida geométricamente, pertenezca causalmente a un POI relevante o que el breaker M30 Example 1 exista.

## 3. 46 expedientes de revisión mejorados sin autorevisión falsa

Los 46 expedientes outcome-blind de R19 recibieron una segunda capa física R20 con bar ID real del primer M3 que barrió C1.low, `first_sweep.available_at`, bar ID M3 del CISD y `cisd.closed_at` confirmado. Para cada uno siguen constando **ambas firmas `A/B=None`** hasta obtener revisiones auténticamente independientes. Per-market R20 artifacts `vt08-b-r20-native-causal-review-{MARKET}-{COMMIT}`, 30 días de retención. Sus índices cubren **los 2.657**, sin selección ganadora.

**Siguiente adjudicación que sí desbloquearía operaciones potenciales:** en cada caso determinar si el nivel de C1.low es importante/POI bajo una regla escrita A; si es el `important level` que generó esa serie opposing M3; si protected swing válido, relevant HTF swing, EQ régimen, breaker low/stop y untouched target identificables antes de C3. Los A/B reviews deben tener source URLs y segmentos precisos, `bar_ids`, hora available_at, clasificación A/B/C/D y disenso D. La inferencia POI=C1.low automático está prohibida.

## 4. Límites inalterados

`A_B_MANIFEST=None`, `AUTHOR_COMPLETE_0`, `COGNITIVE_ADMISSIONS_0`, `BROKER_FILLS_0`; PF/DD/Sortino, OOS y Monte Carlo **NOT EVALUABLE**; QORE-alpha completamente excluido. No sizing, VPS, LIVE/DEMO operacional, merge ni tocar holdout sellado. La aprobación de un PR/CI no equivale a un modelo rentable.

**Código/tests/workflow:** `src/qore/infrastructure/trader_lab/vt08_b_r20_intrac2_cisd_sweep_causal_order_v1.py`, `tests/infrastructure/trader_lab/test_vt08_b_r20_intrac2_cisd_sweep_causal_order_v1.py`, `.github/workflows/vt08-b-r20-intrac2-cisd-sweep-native-chronology.yml`.

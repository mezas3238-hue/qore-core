# QORE Scalper A1 — Inputs cognitivos de nueve mercados desde M1 provider-native

**Fecha:** 10-oct-2026 | A1 cognitiva, PR #758 | Sin VPS, no live, no merge. Auditoría de hechos, no optimización retrospectiva de señales.

## Qué se ha conseguido realmente

A1 ya tenía 2.876 oportunidades V49 y 2.822 instantes de decisión distintos de los nueve mercados. Los nueve libros de observaciones M1 físicas sin interpolar están archivados en [#38080367716](https://github.com/mezas3238-hue/qore-core/actions/runs/38080367716), commit `435e2369f1ed94d7130d328115d2402dcd4e5b84`: 2.791 instantes con vela M1 exacta cerrada en 9/9 activos y 31 instantes con 8/9 o 7/9.

La nueva ejecución [#38091052695 — **SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38091052695) **consume esos libros históricos REALES** y crea, por cada instante, los objetos tipados ya existentes que el auténtico Master Frame requiere:
- **25.398 `CapitalizerMarketPerceptionSnapshot`** (2.822 × 9, fuente real cerrada en tiempo de decisión).
- **25.398 `CapitalizerRegimeHypothesis`** (2.822 × 9), estrictamente `UNKNOWN` y `UNRESOLVED`, sin inventar family`id` ni mercado-trend.
- **101.592 pares de `CapitalizerCrossMarketEdge`** (2.822 × 36), todos `UNKNOWN`. Ser contemporáneas no prueba relación causal; correlación no autoriza relación del grafo.
- **2.822 conjuntos `A1NineMarketNativeCognitiveInputs`** con mismo `observed_at` y nueve símbolos, todos ordenados y sin duplicados/futuro.
- **2.791** conjuntos con M1 exacto 9/9; **31** conservan sus datos físicos M1 incompletos explícitos.
- **0** oportunidades fuente filtradas; cardinalidad original 2.876/2.876 conservada para posterior enlace por ID.

### Por qué todavía no se marca GOOD ni régimen SUPPORTED

El único dato efectivamente obtenido en estos artefactos es **M1 OHLC/close original con manifest provider-native, sello de tiempo y completitud**. Nunca recibimos directamente:
- cotizaciones **BID/ASK** tick-as-of ni latencia/frescura de cotización,
- prueba independiente de reloj/ventana de sesión NY, 
- microestructura completa/ejecución de broker,
- clasificación de régimen *ganada* por estudio per-market,
- causa dirigida por pares/cross-market graph,
- estado de cartera/ledger/posiciones y memoria causal en cada timestamp.

El contrato actual `assess_perception_integrity` requiere las seis banderas; el código nuevo fija correctamente `quote_fresh=False`, `microstructure_complete=False` y `session_clock_valid=False` hasta tener esos artefactos. Por eso **25.398 percepciones están `BAD`**, en el sentido de «el contrato de integridad completo no puede certificarse con un OHLC», **NO** «25.398 velas dañadas o trades erróneos». Las 25.398 hypotheses tienen `CapitalizerKnowledgeState.UNKNOWN` y estado `UNRESOLVED`. Los 101.592 edges son `UNKNOWN`. Nunca se hacen pasar por `GOOD`, `KNOWN` o causa demostrada.

**Archivo nuevo:** `src/qore/infrastructure/trader_lab/capitalizer_a1_native_nine_market_epistemic_inputs_v1.py`: `build_epistemic_inputs` → `A1NineMarketNativeCognitiveInputs`. Se importa directamente `CapitalizerMarketPerceptionSnapshot`, `CapitalizerRegimeHypothesis`, `CapitalizerCrossMarketCausalGraph` y sus evaluadores canónicos, **NO estructuras simuladas A1**. `audit_pinned_nine_market_inputs` une nueve libros por reloj, rechaza duplicados, desorden y mezclas de instantes. Escribe JSONL per-barrier y resumen. Ninguna orden, PF/DD, permiso live, `CapitalizerGlobalWorldModel` falso ni `build_master_cognitive_frame` supuestamente ejecutado.

**Tests:** `tests/infrastructure/trader_lab/test_capitalizer_a1_native_nine_market_epistemic_inputs_v1.py`, real M1 exacto, un mercado incompleto, market repetido/timestamp distinto, quotes falsos, régimen no resuelto y rechazo de falsificar `full_cognitive_frame_executed`. [Workflow reproducible](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/.github/workflows/qore-scalper-a1-real-nine-market-epistemic-inputs-v1.yml), pin por SHA de origen y `actions/download-artifact`. **Ruff/Mypy + 4 tests PASS; censo 2822 y 2876, 2791/31, 25398, 101592 todo reconciliado** en #38091052695. Descargable como artifact del mismo workflow.

## Bloqueos y continuación que sí conducen al PF/DD del cerebro completo

**A1 — Siguiente rama operativa P0:** 1) reloj sesión NY verificado por fuente y day rollover/DST; 2) datos físicos BID/ASK y microestructura o mantener degraded/n/a sin inventar; 3) regímenes nine-market deducidos con pruebas causal-only de M1/H1/M15, pre-registrados y contrastados fuera de muestra; 4) factores/cross-market sólo si existen testigos de fuente y precedencia temporal; 5) `CapitalizerGlobalWorldModel` real con `session_ledgers`, `loss_memory`, `open_positions` elegidos y asentados en orden; 6) pasar `A1NineMarketNativeCognitiveInputs` a cada `A1MultiHypothesisBarrier` junto al mundo real y `CapitalizerCognitivePressureFacts`; invocar realmente `replay_multi_hypothesis_evidence` / `run_sensorized_master_frame_paper` en TODAS las 2.876 oportunidades y medir PF/DD/retención frente V49, sin fabricar ninguna percepción.

**A2 — Fuente/semántica pendiente:** de 2.876 opportunities, M1 protected structure recomputado 2.375/2.876 con 490 segundos pivotes nuevos; **501** siguen sin acreditación del observador QORE (342 SWEEP sin triple-pivot). 12 M15 y 124 H1 sin witness independiente. No vetar los 381 discrepancias CISD: la abstención anterior empeoró PF/DD. Necesitamos evidencia autor-fiel por source ID, no hard gate.

**Estado:** integración de los OBJETOS DE ENTRADA REAL de percepción/régimen/grafo contra fuente nativa `SUCCESS`. **NO es un replay del full Brain**, por lo tanto PF cognitivo, DD cognitivo, Sharpe/Sortino y certificación siguen pendientes. No hay merges ni cambios en el Trader V49 original o VPS.

# VT08 CRT tres fuentes — G-M3: 139 confirmaciones reales reconocidas, autoridad DENEGADA

**15-OCT-2026** · QORE CORE `mezas3238-hue/qore-core` · PR #626 DRAFT. **No sizing, capital, broker, demo/live, VPS, orders ni merge.**

## Evidencia reproducible

- **Fuente causal V3** ya congelada: [metodología V3](VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE_PREREG_2026-10-15.md); [source lab #38749028744](https://github.com/mezas3238-hue/qore-core/actions/runs/38749028744), 61 casos AUDUSD y 78 USDJPY, provenientes del histórico M5 original 296.372 velas ya consumidas, **no OOS**.
- **Nuevo puente V3→G-M3 cognitiva:** `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v3_gm3_cognitive_replay.py`. Reconstruye el censo V3 desde el Atlas SHA-referenciado, usa `CrtPureCausalObservation` con reloj conocido antes o al cierre M15, `CrtPureSituationModel`, `assess_metacognition`/ `reason()` con `hypothesis_stage=CONFIRMED`, evento identificado, confirmación completa, destino disponible. **NO** usa outcomes M5 posteriores ni PnL.
- **Gates no cerrados:** `strategy_identity_ready=False` por política tri-source QORE V3 sin los siete contratos y firmas independientes. El motor debe devolver `ABSTAIN` razonado, nunca capital ni señal broker. El `supporting_evidence` incluye `CRT_CONFIRMATION_COMPLETE`, el `auditable_why` incluye `CRT_SOURCE_STRATEGY_NOT_CLOSED`.
- **Tests adversariales:** `tests/infrastructure/trader_lab/test_vt08_crt_three_source_v3_gm3_cognitive_replay.py`: reject Btc frozen, falsificación de fuente/revisor, payload future/PnL/lotaje, reloj pre-C3, post H4, M15 incompleta; WAIT no puede presentarse como confirmación positiva.
- **CI [#38750815066](https://github.com/mezas3238-hue/qore-core/actions/runs/38750815066)**, commit `ba690eceea76a899ecb91aa549411471382b9ba4`: **quality, AUDUSD, USDJPY = 3/3 SUCCESS**. Artifacts auditoría cognitiva AUDUSD **#11980952529**, USDJPY **#11981706027**. Ambos ZIP descargados, SHA256SUMS **3/3 PASS cada uno**, reconciliación 139/139 case IDs.
- **Resultado:** 61/61 reconocimiento en AUDUSD; 78/78 en USDJPY. **ABSTAIN 139/139, 0 EXECUTE**, `GM1/GM2/GM3/GM4 PASS=False`, `GM5=False`, `GLOBAL=False`, sizing=False.

## Diagnóstico metodológico y significado

La prueba demuestra que la cognitiva **sí sabe procesar una confirmación causal positiva** en lugar de limitarse a 48 fichas fuente-open sin señal. También demuestra que rechaza convertirla en orden por el estado abierto de los contratos. **Esto es una prueba de seguridad y percepción cognitiva, NO un PASS de G-M3 ni fidelidad de método certificada.**

Para cerrar G-M3 de forma genuina: reconciliar con adjudicación independiente del QORE CRT compuesto (RomeoTPT + SpeculatorFL + TraderFlameseN), probar escenarios positivos y negativos con DOL, timing, PD array e invalidación causal fuente-autorizados, memorias aisladas y lifecycle entero; ejecutar contradicciones/oposición/cancelación/rearm; firma separada G-M4 y G-M5. No tratar ABSTAIN perfecto como edge.

## Economía, hipótesis descartadas y próximo punto de decisión

V1 54 candidatos; V2 745 (115 DOL primero / 538 invalidaciones primeras); V3 139 (23 DOL primero / 69 invalidaciones primeras). Todos provienen de datos *development* ya explorados y el recorrido de primer toque **no corresponde a fills, PF ni retornos**. Ajustar V3 por esas cifras contaminaría de nuevo el experimento. Para trader integral faltan BID/ASK+fills/costes reales, PF/DD/Sharpe/Sortino/expectancy, OOS no consultado, WFO, Monte Carlo, estrés y Risk/CIBO independiente. **Ningún sizing de VT08, incluso en simulación.** Si se requiere DD patrimonial, Risk/CIBO externo define política y ejecuta, no el trader.

**Mandato Owner vigente:** tres fuentes, no fidelidad exclusiva a Romeo, no certificados falsos. PR #626 DRAFT/unmerged.

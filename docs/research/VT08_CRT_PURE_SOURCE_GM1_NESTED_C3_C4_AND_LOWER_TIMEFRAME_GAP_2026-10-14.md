# VT08 CRT PURE — G-M1 SOURCE P0: confusión entre N1 M15 detector y CRT conformacional original

**Fecha:** 14-OCT-2026 · PR #626 DRAFT. Acta de corrección de identidad metodológica, separada de resultados estadísticos. NO MERGE.

## Fuentes primarias y secundarias verificadas

**Tier A — RomeoTPT original:** [post Romeo Model #1 / OTE](https://t.me/s/officialRomeotpt/6184) recomienda centrarse en Model #1 y OTE. [Romeo old CRTH](https://t.me/s/officialRomeotpt/6615) ilustra reacción tras penetrar el high antiguo. El expediente QORE [MODEL1-SOURCE-CLOSURE-001](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md) tiene relación autorizada **H4 CRT -> M15 Model #1**, stab old high/low, source candle direccional y confirmación body-close, stop estructural. **Nada de esa fuente verificada autoriza automáticamente equiparar la máquina N1 de tres M15 a Model #1.**

**Tier B — SpeculatorFL:** [thread de selección de CRT del 25-MAY-2024](https://threadreaderapp.com/scrolly/1794311615535518154) distingue:
- CRT *confirmacional*: después de terminar la segunda vela/confirmar el CRT, operar en la tercera (o velas posteriores, según su aclaración de la conclusión). El criterio de confirmación no está especificado en términos de `micro-C3.close > micro-C1.midpoint`.
- CRT avanzado: entrar en segunda/tercera sin confirmación; no extrapolarlo al modelo conservador.
- CRT micro/anidado: se observa un **LTF candle que confirma HTF**, que deviene referencia CRT inferior y que se refina en **una temporalidad aún menor** para ejecutar. Enumera confluencia HTF PD array, timing, inside bars, timing del purge. Es **su doctrina secundaria**, no fuente de ejecución de Romeo.
- [Hilo general del 28-APR-2024](https://threadreaderapp.com/thread/1784493604473618604.html) confirma el concepto de CRT anidado, pero no avala automáticamente el contrato N1.

**Tier B — TraderFlameseN:** [thread CRT del 13-MAY-2024](https://threadreaderapp.com/thread/1790141530461622525.html) confirma, con alta dependencia textual de SpeculatorFL, las nociones macro/micro, timeframes y selección; no autoriza por sí mismo todos los filtros N1.

## Discrepancia concreta, demostrada por timestamps de N2

**El N1 exploratorio de QORE hace:**

`micro-C1_M15` -> `micro-C2_M15 sweep+return` -> `micro-C3_M15 CLOSE beyond own micro-C1 midpoint` -> `next M15 open`.

Eso significa que la primera apertura M15 después de la observación ocurre en la **CUARTA vela M15 (micro-C4)**, no en micro-C3. La máquina fuente Tier B espera normalmente **confirmación tras la segunda y actividad durante la tercera** (y admite posteriores cuando existe una metodología de continuación). N1 **NO validó un trigger dentro de C3 con M5**, no tiene `bulky LTF source candle` con definición original, no tiene `further LTF entry` y no ha source-adjudicado el nuevo DOL/target ni la invalidación. Por tanto:

- Cambiar el nombre N1 a “Confirmational CRT autenticado” estaría **PROHIBIDO**. N1 sigue **QORE_N1_OBSERVATIONAL_THREE_M15**.
- La fecha `prospective_next_m15_opened_at` del JSONL es **RELOJ CAUSAL**, **NO entrada source-authorized**. Un M5 intra-C3 podría ser un objeto distinto para investigar, pero NO inventar su regla numérica sin fuente y pre-registro.
- Que el micro-C3 cierre más allá del propio midpoint implica que **el midpoint ya está detrás**: no puede usarse por defecto como TP adelante. Algunos extremos también fueron tocados antes de C4. DOL está **OPEN**, no seleccionar arbitrariamente un target más lejano.
- No se permite mezclar `Romeo H4→M15 Model #1` con `SpeculatorFL H4→M15→M5` y llamarlo «un mismo modelo»: serían familias con estados y validaciones separadas.

## Evidencia del caso N2 y el costo de no resolver la fuente

[Resultado N2 completo](VT08_CRT_PURE_N2_57_CONTEXTS_CAUSAL_SOURCE_AND_OVERLAP_RESULT_2026-10-14.md): 57 H4, 64 N1 sintéticos, 51 repiten sweep del extremo del H4 C1, 40 cierran en lado incompatible con la tesis antigua, 42 agotaron por wick el extremo opuesto propio y 64 superaron midpoint propio antes de C4; 37 de 57 H4 presentan otra N1 en dirección opuesta. Son **flags de investigación**, no pruebas de invalidez del método original.

## Bloqueos de certificación y siguiente contrato fuente-first

1. `G-M1/N1_METHOD_EQUIVALENCE`: **FAIL_SOURCE_UNSUPPORTED** hasta demostrar que una secuencia C1/C2/C3 en M15 como la codificada coincide con CRT confirmacional de fuente Tier A o B, incluyendo secuencia exacta de confirmación.
2. `G-M2/NESTED_LADDER`: **OPEN**. Si se toma explícitamente doctrina B: HTF H4 CRT -> candidato/bulky M15 -> lower M5 (datos M5 originales ya disponibles), con identidad/tiempo de cada nivel; sin umbral cuantitativo inventado para bulky.
3. `G-M3/MICRO_ENTRY`: **OPEN**. Definir evento M5 y estado causal antes de la entrada, no reutilizar close C3 como fill, ni mezclar Advanced sin contrato.
4. `G-M4/DOL_AND_INVALIDATION`: **OPEN**. Identificar objetivo aún pendiente, propiedad del nivel antiguo, contradicción macro y micro. Si target original tocado o las tesis se contradicen ⇒ ABSTAIN a falta de regla adjudicada.
5. `G-M5/REPLAY_ECONOMIC`: **NOT_STARTED** para N1/N2. No usar 939/64/57 como trades, y no simular PnL para dar apariencia de certificación. Primero adjudicar metodología, luego evaluación causal y ejecutabilidad BID/ASK de una familia claramente distinta en muestra realmente disponible.

**Decisión formal:** `N1,N2 = RESEARCH-ONLY`; `SOURCE_FIDELITY_NOT_CERTIFIED`; `NO_N3_ECONOMIC_REPLAY_UNTIL_METHOD_GATE`. No se cambia el código original R2-C, ni se inventa un sizing del Trader. No merge, no LIVE/DEMO órdenes, no VPS ni FundedNext LIVE, BTCUSD congelado, CIBO/QORE Risk exclusivo para sizing.

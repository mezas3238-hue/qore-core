# VT08 5M — AUDITORÍA COMPLEMENTARIA DE FIDELIDAD TTrades: DOS C3 DISTINTOS + BIAS EQ

Fecha 2026-10-10. Arquitecto A. [#762](https://github.com/mezas3238-hue/qore-core/issues/762), [#763](https://github.com/mezas3238-hue/qore-core/issues/763), PR [#765](https://github.com/mezas3238-hue/qore-core/pull/765). Documentación SOURCE versus CANDIDATE; no operación ni nuevo PF. **Ninguna regla ambigua se promueve al core.**

## 1. Error de taxonomía que puede destruir la densidad

TTrades usa el vocabulario "Candle 3" en **DOS cadenas mecánicas diferentes**, separadas por contexto/fecha de lección:

A. **C3 Continuation AFTER completed C2 reversal (Sept 6 2025)**: https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/ — C2 con wick grande y retorno cerca de open, close back in range; dejar C2 cerrar, operar dirección de sesgo en C3 tras POI (FVG, high, low), CISD y PS en LTF. No se da percentil/umbral objetivo universal de wick grande. Bundle `C3_AFTER_C2_REVERSAL_POI_CONTINUATION`, el primer censo FVG limitado es `C3_FVG_RETEST_M15_SHAPE_V1`.

B. **C3 reversal CLOSURE when C2 FAILS its closure (Dec 3 2025)**: https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/ — C2 puede no barrer C1 ni revertir; C3 close por encima/debajo cuerpo de C2 confirma reversión después; el autor describe como siguiente expansión **C4**, no entrada antes de finalizar C3. Se propone bundle distinto `C3_CLOSURE_TO_C4` para investigación *posterior a reconstrucción temporal*. No mezclar con la continuación C3 de Sept, aunque ambas se llamen C3. Si el bot usa la etiqueta `C3` para ambas, el riesgo de lookahead es grave: la C3 closure completa **no es conocida dentro de C3**.

**Dato crítico:** El funnel B01 `C2_CLOSE_NOT_INSIDE_REFERENCE=3987` es una primera causa de rechazo en el positional B01, y **NO** puede ser reasignado a 3987 entradas C3. El bundle B (C3 closure→C4) podría clasificar estructuras de las que algunos provienen, pero faltan C3 posterior, POI, CISD, riesgo/targets y autorización Owner de candelarios.

## 2. Sesgo: el helper B01 no reproduce todas las formas autor descritas

El helper congelado `src/qore/infrastructure/traders/vt08_b01_r3_8.py:344-364`:
- Side long si última daily source close > previous daily high.
- Side short si última daily close < previous low.
- Alternativas reversión por sweep/close dentro; si overlap/both/no confluencia -> None.

Es una **formulación QORE de dos source-days cerrados**. TTrades publicó un **modelo de daily bias separado** (13 Dec 2025), https://ttrades.com/easy-daily-bias-a-mechanical-trading-framework/ :
- reversión previa a high/low del día anterior con wick + CISD;
- continuación tras cierre direccional, retest de EQ **50% del rango previo** con no cierre LTF contrario a EQ, luego expansión hacia extremo previo;
- no basta `last close > previous high` como fuente universal de continuación.

Con ello, `BIAS_UNRESOLVED` del B01 no es `TTrades forbids trading`. Tampoco se libera directamente a LONG/SHORT. Se necesita un **source-day-EQ context + as-of LTF confirmation producer** que emita estados múltiples y timestamps, sin presuponer un bias nuevo a partir de futuros C2/C3.

La [auditoría causal real A source-day 5M](https://github.com/mezas3238-hue/qore-core/actions/runs/38078585235) ha entregado prueba de barras M15, valores, SHA y cierres para bias QORE congelado. Esa prueba atestigua **cuándo** se conocía el bias antiguo; **no certifica** que su regla numérica sea plenamente fiel al autor. El arquitecto B debe separar `ASOF_ATTESTED` de `SOURCE_RULE_VALIDATED`.

## 3. Fuente posterior como contexto, NO modificación retroactiva de original

- Wick / target contextual: https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/ ; el target autor mencionado es liquidez previa / open / extensión según tipo wick, no fixed 2R en todos los casos.
- Fuente PDF de Equilibrium publicada Oct 10 2026 https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/ — apoyo contextual para calcular EQ, **no** autoridad retroactiva del video Sept 2025.
- Fuente adicional de internal/external liquidity https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/ — POIs FVG/swing y destino external liquidity, pero su gobierno/lifecycle depende del contexto.
- Video primario original, transcripción/fotogramas/hashes pendientes; los blogs no son prueba de una definición numérica no escrita.

## 4. Matriz de autoridad y plan de implementación incremental (pre-PnL)

| Bundle | Regla demostrada por autor | Ambigüedad | Estado |
|---|---|---|---|
| B01 positional C2 completed open | C2 sweep/close/reversal + PS | QORE open-fill 2R / fixed H4 | Solo narrow máquina; volumen 488 candidatos; old PF falla |
| C2 reversal intracycle | formar wick + CISD + PS antes expansión | "shallow", targets y fill OHLC exactos | 1514 trades **hipotéticos**, PF/DD falsados; NO promover |
| C3 after deep-wick C2 | POI + CISD + PS tras C2 complete | profundidad numérica wick / prioridad POI | **CENSO shape-only**; nunca PnL ni CandidateEvent |
| C3 closure → C4 | C2 failed→C3 engulf/close→C4 | confirmación de POI, LTF entry/SL/TP, unión Owner | Nuevo `C3_CLOSURE_TO_C4` solo para futura forma/handoff |
| Daily EQ continuation | Bias direccional + EQ hold + estructura LTF | EQ exacta por fuente y reloj, falsos cruces | Modelo causal por desarrollar, NO reemplazar `resolve_bias` sin contraste |

## 5. Integración A/B

A entrega `vt08_5m_source_bias_asof_attestation_v1.py`, con (re)generación de 5 mercados 1095D, ambas velas source-day, constituent-M15 content hash y cutoff real. Arquitecto B mantiene gate en `cognitive_ready=False` hasta **todos** los valores y relojes verificables de Situation, source family completa y firma manifest. Una atestación no debe relabel C3 shape-only ni C2 experiment falsificado como "SOURCE_COMPLETE".

**Siguiente P0:** fijar `C3_CLOSURE_TO_C4` outcome-blind sin mezclar con `C3_AFTER_C2_REVERSAL`, construir EQ LTF causal sin precios futuros, y formar casos fuente auditables; solo después plantear nuevas identidades fuente para economics pre-registrado.

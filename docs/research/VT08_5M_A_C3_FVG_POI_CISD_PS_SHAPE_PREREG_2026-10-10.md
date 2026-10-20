# VT08 P0-A — PRERREGISTRO C3 POI–CISD–PS: CENSO DE GEOMETRÍA, NO FILLS

**Fecha 2026-10-10.** Antes de calcular números C3 o mirar PnL se congela esta investigación `C3_FVG_RETEST_M15_SHAPE_V1`, usando solo los 1095D M15 consumidos run 35934924907, cinco pares y Owner 01/05/09 NY. PR #765, issue #762. Ningún trade, PF, DD o fake fill se atribuye a C3 en esta fase.

## Fuente original

1. https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/ : C3 de continuación tras C2 reversión, gran wick C2, C2 close dentro del rango anterior, LTF CISD, POI FVG/high/low, protected swing y confirmación múltiple.
2. https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/ : deep opposing run C2 = esperar expansión C3, shallow C2 = C2 expansión intraciclo; Forex 01/05/09 NY.
3. https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/ : cierre CISD que protege swing estructural y stop invalidación.

El autor **no fija** una relación exacta, objetiva y universal `large_wick/C2_range` para autorizar C3. Sin esa política, la clasificación de wick es **WICK_DEPTH_NOT_SOURCE_CALIBRATED**, y aunque POI + CISD + PS sean visibles **NO** se declara SOURCE_COMPLETE ni se lanza PnL.

## Hipótesis censal congelada

- C1 referencia H4 = dos H4 antes del Owner anchor, C2 H4 terminada inmediatamente antes; exige C2 sweep único del nivel C1 opuesto a bias y C2 close estrictamente dentro de C1, igual al baseline, a fin de medir C3 estrecho causal y no degradar veracidad.
- Bias: dos últimas barras diarias QORE 17NY completas y disponibles a apertura de C3; mismo `resolve_bias` frozen; output temporal será atestado aparte mediante `VT08_5M_SOURCE_BIAS_PROVENANCE_V1`.
- Se cataloga C2 PS confirmed after sweep C1 y C2 FVG del lado del bias (3 velas M15 C2, gap estándar left.high<right.low para long / right.high<left.low para short), confirmado antes de apertura C3. **Un FVG formado en C2 NO es automáticamente un POI prioritario de TTrades**; eso requiere adjudicación fuente. Se informa `C2_ANY_SIDED_FVG` y `C2_ACTIVE_SIDED_FVG` usando invalidación hasta C3-open, cada uno por separado.
- C3 dentro del H4 Owner: contar primera vela M15 cerrada que entra en un FVG activo de C2 (POI touch) y PS de C3 confirmado **después** del cierre de ese touch con `protected_swings_in_candle2` usando como nivel `FVG.upper` para long y `FVG.lower` para short **QORE geometry proxy**; valor FVG visible antes, sin mirar barras posteriores para declarar en tiempo t.
- Contar niveles escalonados: anchors C2 reversal+bias, con PS C2, C2 FVG, C3 touch, C3 PS post-POI, filas caso con hash y times. Un evento se identifica por anchor+POI+series origin+confirmation en orden cronológico; duplicados de POI deben contabilizarse; no selección ex-post de ganador.
- El primer event por mercado y NY-day es únicamente **SHAPE_NOT_TRADE**, no altera el bloqueo `one filled trade/NY-day`.
- La fuente no determina aún umbral de wick, prioridad entre múltiples POIs, fill BID/ASK, SL-offset, TP contextual, expiración de posiciones, fuente horaria y confluencia SMT. No se auto-habilita CandidateEvent V1, no PnL, no cognitiva en esta prueba.
- Pruebas negativas: C2 sin sweep, cierre fuera de C1, bias contradictorio, POI no alcanzado, PS confirmado antes POI, pre-anchor future timestamps y pares fuera del universo. C3 structural finding jamás cuenta como trade ni como éxito de edge.

**Criterio de salida:** censo por mercado/año y razón con hashes, cero fuga temporal; preparar adjudicación de wick con video fuente y originador as-of P0. Preregistered report siempre conserva conteos incluso si cero.

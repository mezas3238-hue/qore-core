# QORE Scalper A2 — Veredicto V50-G real 9/9 y preservación de edge por identidad

**Fecha:** 2026-10-10. **Arquitecto B:** metodología, PR #759 / issue #757. **Arquitecto A1:** cognitiva, PR #758 / issue #756. **Origen:** PR #623.  
**ESTADO: RECHAZADO PARA CERTIFICACIÓN**, experimentos históricos reproducibles en GitHub; NO VPS, NO LIVE, NO merge, NO cambio de políticas.

## Fuentes exactas y paridad causal

1. **M1 nativo de los nueve mercados** de GitHub Actions [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`, sin interpolación ni sintéticos según manifests.
2. **V49 control** [run #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), workflow SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`, 11/11 jobs GREEN; [matriz #11670728222](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695/artifacts/11670728222).
3. **V50-G** [run #38053723674](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674), workflow SHA `cb897be93821fcb238c4a16a419dfff2814ec0f4`, 11/11 jobs SUCCESS. Usa misma V49 source (incl. parche causal de target H1 B) y superpone únicamente tres módulos observacionales V50-G del commit A1 **PINNED** `4ab7c1ad72876f15e2f24923927d9140406d85a3`, NO la cognitiva completa actual del PR #758. Artifact matriz/waterfall [#11671738173](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674/artifacts/11671738173).
4. **Reconciliación por source-ID**, sin aproximaciones ni ocultar trades: [run #38057558313](https://github.com/mezas3238-hue/qore-core/actions/runs/38057558313) SUCCESS, incluye los nueve V49 control ledgers y los nueve V50-G report/trades/source trace. Se exige mismo universo de **2,876 oportunidades**. La auditoría por identidad no ejecuta gates: cero pérdidas causadas por el *auditor*.
5. **MFE/MAE original por barras nativas M1:** [run #38057290884](https://github.com/mezas3238-hue/qore-core/actions/runs/38057290884) 11/11 SUCCESS; documento metodológico [MFE MAE V49](QORE_SCALPER_A2_V49_NATIVE_M1_MFE_MAE_FORENSICS_2026-10-10.md).

## Resultados económicos observados, GROSS, SIN costes físicos FundedNext

| Brazo / control | N after MAX3 | Wins | PF bruto | Resultado R | Max DD R |
|---|---:|---:|---:|---:|---:|
| V49 structural control | 2,020 | 1,167 | **0.664463** | **-233.26933R** | **236.13428R** |
| V50-G GEOMETRY_ONLY | 220 | 87 | **1.095856** | **+11.70663R** | **20.328945R** |
| V50-G COGNITIVE_GEOMETRY | **94** | **42** | **1.594861** | **+29.66318R** | **9.00000R** |

**Importante:** el brazo de V50-G no reproduce el Master Cognitive Frame de A1; usa `PARTIAL_V50_BRIDGE_ONLY` y memoria vacía por candidato. El resultado bruto positivo no establece edge sostenible, no es evaluación de costes de cuenta y sigue violando frecuencia/densidad Owner. V50-G histórico previo de 90 operaciones fue rechazado; este ensayo causal produce 94, por encima de 90 pero no arregla la destrucción de ganadores.

## Resultado por source ID — veto matemático definitivo

| Métrica | COGNITIVE_GEOMETRY | GEOMETRY_ONLY | Owner minimum |
|---|---:|---:|---:|
| Baseline V49 positive winning IDs | 1,167 | 1,167 | — |
| Original winners STILL positive in V50-G | **37** | **62** | **934** |
| Original winner count preservation | **3.1705%** | **5.3128%** | **≥80%** |
| Baseline positive winning R = 461.9427618 | — | — | — |
| Preserved ORIGINAL V49 winning R corresponding to the still-positive IDs | **14.05109R** | **23.62519R** | **≥415.74849R** |
| Preserved ORIGINAL winner-R ratio | **3.0417%** | **5.1143%** | **≥90%** |
| Actual V50-G R realized on those same winning source IDs | 72.11775R | 111.11651R | separate metric, not preservation |
| V50 winners NOT among V49-selected baseline | 5 | 25 | diagnostic |

**Advertencia de denominadores:** `candidate_realized_winner_mass_ratio` de V50-G sobre baseline R (15.61% / 24.05%) puede resultar grande por cambio de la geometría del stop, pero **no debe sustituir** la masa original ganadora conservada (3.04% / 5.11%). Un nuevo payoff law sobre 37 ganadores del baseline no equivale a preservar 934 ganadores originales. La comparación se calculó por SHA-256 causal `source_opportunity_id`, nunca por aproximaciones estadísticas.

### Ruta exacta de pérdidas del universo de oportunidad

En la matriz de 9 mercados SOURCE total 2,876:
- `GEOMETRY_NOT_READY` = **2,655** oportunidades (92.32% del source).
- `GEOMETRY_READY` = 221 oportunidades (7.68%).
- `COGNITIVE_DENIED_GIVEN_GEOMETRY_READY` = **127** (57.47% de 221).
- `COGNITIVE_ALLOWED` = 94.
- `GEOMETRY_ONLY` pasa de 221 a 220 después de MAX3 (solo 1 recorte).
- `COGNITIVE_GEOMETRY` = 94 antes/después MAX3 (0 recortes).

**Causa proximal dominante de la caída de densidad:** restricción `GEOMETRY_NOT_READY`, NO MAX3. El rol de las restricciones individuales (minimum execution noise 4×, geometry stop, max execution noise 8×, geometry target, etc.) requiere el waterfall de **reason codes** de la misma traza; A2 no presume que todas sean fuentes TTrades, ni elimina arbitrariamente validaciones económicas.

`source-ID` matching 9/9 SUCCESS demuestra **invalidez 0 en este lote**, no cero probabilidad de invalidaciones en otras ramas/futuros artefactos.

## Contraste con nueva auditoría DeepSeek post-V49

- **CONFIRMED:** V49 negativo bruto y asimetría de R; selección MAX3 no es la causa agregada (856 excluidas PF0.598<0.664).
- **CORRECTED:** el win rate del simulador ≠ hit rate direccional H1; el lector de identidad post-replay no bloquea operaciones.
- **MFE/MAE realmente calculado** desde native M1: mean PRE-exit MFE 0.34364R / MAE 0.46553R; 609 stops de -1R, 1,030 targets, 381 session exits. Las 137 session-exit ganadoras lograron MFE previo mean ~0.744R y realized mean ~0.424R, pero ello NO demuestra un trailing ejecutable ni autoriza pasar a optimización retrospectiva.
- **H5/H6/H7:** por ahora son hipótesis parcialmente informadas. H5 para `SESSION_EXIT` merece ablation preregistrada; H6 solo con stop M1 legítimo y misma identidad puede probarse; H7 no equivale a «el autor reporta 0.5R ganancia típica».
- **V50-G RECHAZADO** por incumplimiento extremo de identidad, frecuencia, DD≤6R, y costes físicos no modelados. Su PF positivo no compensa.
- **No tocar la arquitectura H1→M15→M1; no Daily/H4 gates; no introducir MSS+FVG+OB AND; reentradas con POI/evento causal distinto; preservar ruta Sweep+CISD y FVG+CISD del TTrades original hasta probar fuentes/callers.**

## Próximos trabajos y coordinación A1 / A2

1. A2: descomponer `GEOMETRY_NOT_READY` (2655 casos) por `geometry_reasons`, sesión, mercado y trigger, con trazas exactas y etiquetas `QORE_ENGINEERING_RULE/SOURCE_EXPLICIT`. Recalibrar el lenguaje: "mayoría rechazada" no equivale automáticamente a "filtro incorrecto". 
2. A1: diferenciar rama V50-G de su implementación Master Frame real 9/9 con memoria prequential, outcome-blind and settled-only; evitar usar MFE/MAE o PF futuros como admisión. Implementar WHY y group parent+POI para cada trade e integración estricta entre ramas, sin merges sin aprobación.
3. A2+A1: preregistrar brazos de stop protected swing M15 vs refined M1, H1 target already-swept causal audit, session exits, MFE/MAE; no ajustar in-sample a posteriori y luego declarar OOS.
4. Certificar únicamente si 9/9 dataset iguales, retención ≥934 winners/≥415.75R original mass, PF/OOS/física bid-ask, Drawdown ≤6R Owner, Sharpe/Sortino/MC, fuente TTrades e integridad causal. Las pruebas de ingeniería exitosas no sustituyen estas barreras.

**VEREDICTO FINAL: V49 ECONOMICS FAIL; V50-G PF IMPROVED BUT RETENTION/SOLVENCY FAIL; SCALPER NOT CERTIFIABLE / NO LIVE / NO VPS / NO MERGE.**

## CAUSA INMEDIATA DE LOS 2,782 RECHAZOS — descomposición exacta por reason-code

**Corrida forense adicional:** [GitHub Actions #38057731321](https://github.com/mezas3238-hue/qore-core/actions/runs/38057731321) SUCCESS, lee el waterfall de 9/9 del mismo V50-G sin modificarlo ni seleccionar trades por outcomes. Suma de ocurrencias `geometry_reason_occurrences` = 2,655, suma `bridge_reason_occurrences_on_geometry_ready` = 127, con cardinalidad exacta en este caso (cada reject con una razón).

| Etapa | Reason code | Oportunidades | Interpretación, NO política aprobada |
|---|---|---:|---|
| Geometry | `M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE` | **2,371** | Motor de geometría interpreta stop M1 de ejecución dentro del ruido de corto plazo; filtro basado en escala M1 QORE, **no** exigencia universal demostrada de TTrades |
| Geometry | `M1_EXECUTION_INVALIDATION_UNAVAILABLE` | **272** | No se construyó un nivel causal M1 de invalidación para esa oportunidad en el selector V50-G, aunque el candidato V49 tiene protected swing M15 |
| Geometry | `M1_EXECUTION_STOP_TOO_WIDE_FOR_SCALP` | **10** | Invalidez M1 demasiado lejana según criterio ingenieril de geometría; no confundir 4–8× stop/local M1 range con 4–8R reward/risk |
| Geometry | `NO_CAUSAL_H1_DESTINATION_LADDER` | 1 | Sin escalera de objetivo estructural H1 causal en el detector |
| Geometry | `NO_H1_DESTINATION_AT_OR_ABOVE_1R_WITH_EXECUTION_STOP` | 1 | Objetivo H1 disponible pero la regla V50-G exige ≥1R desde el stop de ejecución M1; es regla económica del modelo, no source literal |
| **TOTAL GEOMETRY** | | **2,655** | 92.32% del universo 2,876 no pasa geometría |
| Cognition after geometry READY | `H1_CONTEXT_STALE` | **99** | Contexto H1 considerado caducado por TTL de puente cognitivo |
| Cognition after geometry READY | `M15_SETUP_EXECUTION_WINDOW_STALE` | **23** | M15 confirmado pero considerado fuera de ventana por reglas de timeout |
| Cognition after geometry READY | `SESSION_RUNWAY_EXHAUSTING` | **5** | Sesión avanzada y ventana restante insuficiente según regla del puente |
| **TOTAL COGNITION after READY** | | **127** | De 221 READY, sólo 94 sobreviven |

**Hallazgo P0 principal:** 2,371 rechazos por `M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE`, **82.44% de todas las oportunidades V49 (2,876)** y **89.30% de los rechazados geométricos**. Es **la causa cuantitativamente dominante** de la caída de frecuencia, no un AND MSS+FVG+OB, ni MAX3, ni 90-trade statistics. En adición, las reglas de «staleness» H1 y M15 representan 122 de 127 rechazos cognitivos.

**Acción ordenada de ingeniería, SIN aflojar seguridad hoy:** reconstruir con trazas `m1_invalidating_swing`, `recent_m1_range`, `stop_distance`, `execution_stop_noise`, timestamp y protected swing M15 para cada uno de los 2,371 rechazados. Distinguir casos con protected swing M1 válido pero <4× M1 recent range, casos realmente sin invalidación, y alternativas metodológicamente respaldadas (stop protegido M15 como estructura vs refinado M1) mediante A/B congelado en GitHub, manteniendo capital/riesgo/solvencia y first-come MAX3. Para los 99 H1 stale, distinguir TTL artificial QORE de invalidación por swing/tesis real, sin usar `h1_state_until` futuro. NO activar señales a ciegas.

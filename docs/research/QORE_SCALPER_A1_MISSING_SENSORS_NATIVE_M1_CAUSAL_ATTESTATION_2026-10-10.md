# Trader Scalper A1 — Validación causal de sensores anteriormente NOT_AVAILABLE

**Fecha:** 2026-10-10 | A1 Cognitiva PR #758 | A2 Metodología PR #759 | PR maestro #623 | Exclusivo investigación GitHub (no VPS, no LIVE, no MERGE).

## Resultado histórico medido (9 mercados, 2876 oportunidades originales)

[GitHub Actions — 11/11 SUCCESS #38081283448](https://github.com/mezas3238-hue/qore-core/actions/runs/38081283448), SHA **`8e9e05cd9c885adf69420ddf17e89f45122d7c5b`**, artefactos inmutables por mercado + matriz final, usa V49 originales [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695) y provider-native M1 [#35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334).

El panel A2 históricamente informó **NOT_AVAILABLE=2876** en 4 campos. Se han reobservado tres señales usando únicamente velas nativas **cerradas antes o exactamente al instante M1 de decisión**, sin leer resultados, sin introducir vetos y preservando **2876/2876** `source_opportunity_id`.

| Sensor | Revalidado desde M1 nativo | No atestado |
|---|---:|---:|
| `ACTUAL_M15_STRUCTURE_REVALIDATION` | **2864 / 2876 (99.58%)** | **12** |
| `H1_TARGET_ROOM_R` | **2752 / 2876 (95.69%)** | **124** |
| `M1_PROTECTED_SWING_ATTESTATION` | **1244 / 2876 (43.25%)** | **1632** |
| `FULL_COGNITIVE_MASTER_FRAME` | **0 / 2876** | **2876** |

**Importante:** El cuarto NO es una propiedad de vela: sólo puede marcarse probado después de evaluar el verdadero `build_master_cognitive_frame` con nueve percepciones, regímenes, cross-market graph, session-ledger y source-method evidence. Es correcto que **permanezca NOT_AVAILABLE=2876** en el nuevo atlas de atestaciones *de mercado*; no es un defecto de M1.

## Desglose por mercado (mismo source ID, no trade filter)

| Mercado | Originales | M15 verificado | M1 protegido verificado | H1 target verificado |
|---|---:|---:|---:|---:|
| AUDJPY | 282 | 281 | 135 | 254 |
| AUDUSD | 275 | 273 | 124 | 250 |
| EURUSD | 332 | 332 | 137 | 327 |
| GBPJPY | 300 | 300 | 120 | 277 |
| GBPUSD | 329 | 328 | 149 | 320 |
| NAS100 | 361 | 361 | 129 | 357 |
| USDCAD | 320 | 316 | 142 | 314 |
| USDJPY | 297 | 294 | 139 | 280 |
| XAUUSD | 380 | 379 | 169 | 373 |
| **Total** | **2876** | **2864** | **1244** | **2752** |

## Qué se ha comprobado técnicamente

En `src/qore/infrastructure/trader_lab/capitalizer_a1_source_sensor_independent_attestation_v1.py`:

1. **M15** — Reagrega provider-native M1 a barras completas (15/15 velas) ya cerradas, reobserva el CISD estructural y verifica **ambos** el timestamp original de cierre M15 y el mismo protected swing de V49. No atesta 12 casos por falta de testigo bajo la prueba estricta. El resultado no niega la validez de la fuente cuando ésta empleaba una agregación parcial 11/15; no se introducen rechazos.
2. **H1 objetivo** — Sólo acepta H1 verdaderamente completo (60/60 velas nativas) y ya cerrado; exige que el precio original de destino haya sido un extremo real H1 anterior al M1 y que **no se haya tocado** desde aquel cierre. La distancia al objetivo se expresa en R usando el stop original, sin calcular el resultado de la operación ni seguir el precio futuro. 124 casos continúan no acreditados, pero esto NO prueba que la oportunidad del autor sea errónea.
3. **M1 protegido** — Exige confirmación CISD estructural del swing en el cierre **exacto** de la entrada V49, observada desde el M15 ya declarado con barras M1 cerradas. **No equipara el extremo del sweep ni una FVG en formación a un protected swing confirmado**. El observador reutiliza el método estructural V48 para revalidación, no es una certificación independiente de fidelidad al vídeo del autor. 1632 casos quedan pendientes para el arquitecto B: diferencia de ruta, CISD previa, FVG retrace, pivote y timing.
4. **Master Frame** — No puede deducirse de OHLC, por tanto jamás se eleva a OBSERVED por este módulo. La ejecución total es responsabilidad de A1, ya conectada a Trader PAPER en tests pero aún no sobre el verdadero censo nueve-mercado con regímenes y estado de cartera atestados.

**Limitación de independencia:** La fuente V49 y esta reconstrucción utilizan primitivas estructurales TTrades/V48 del mismo código base; se trata de una **recomputación causal contra el libro original de señales**, no de una segunda certificación por interpretación independiente del material audiovisual del autor. Los datos de velas son reales y anteriores a la decisión; por eso el resultado sí sirve como evidencia para resolver `NOT_AVAILABLE` en el puente A1, **no** para proclamar certificación de autor.

## Integración real con Master Frame sin inventar hechos

El nuevo `capitalizer_a1_validated_sensor_overlay_v1.py` recibe `A1SourceSensorAttestation` por **exacto ID fuente y `decision_at`**, confronta el valor y timestamp original con el witness nativo, y solo entonces produce un **nuevo** `EntrySensorFrame` A1 con los tres campos marcados `OBSERVED` donde corresponda. El panel sombra A2 original y señales V49 no se modifican. Si la evidencia falta, el campo permanece `NOT_AVAILABLE`; si no coincide fuente o contiene futuro, fallo explícito. **FULL_COGNITIVE_MASTER_FRAME nunca puede elevarse por este overlay.**

`run_sensorized_master_frame_paper(..., independent_source_witnesses=...)` es la vía opt-in conectada al Trader PAPER real; envía el `EntrySensorFrame` enriquecido al puente `bind_scalper_sensors_into_master_context` y de allí al Master Frame A1. Contabiliza las filas con prueba y campos elevadas para observabilidad. Requiere todo el censo por source ID, pero **no exige OBSERVED en cada uno**: NO introduce filtro nuevo por las 12 + 124 + 1632 observaciones no acreditadas, ni por las **381** discrepancias CISD preexistentes.

Regresiones cubren M15/M1/H1 controlados, H1 parcial 59/60 prohibido, sensor de vela futura, trade close fuente divergente, procedencia M15 divergente, H1 sin witness, fuente ajena, `FULL_COGNITIVE_MASTER_FRAME` falsificado y conexión al `Master Frame → Trader PAPER` con fuente integrada.

## Lo que queda por resolver

- **A2 metodólogo:** revisión fiel de todos los **1632 swings M1 no atestados**, clasificarlos por familia / causa cronológica y distinguir `SWEEP_CISD` (extremo barrido) de `FVG_RETRACE_CISD` (swing realmente protegido). Nada de abstención en masa, no convertir mismatch CISD en veto: antes produjo 1910 trades / DD 252.10R peor que V49.
- **A2 + A1:** investigar individualmente las **12 pruebas M15** no acreditadas (posible agregación parcial M15 fuente) y las **124 H1** (H1 incompletos, toque previo, target original vs H1 estricto). No reinterpretar etiquetas N/A como trades inválidos.
- **A1 cognitiva:** llevar los witness por source ID al constructor de verdaderos snapshots mundo/precepción/9 regímenes/correlaciones y **memoria sólo de operaciones elegidas y asentadas**, con QORE Risk y fills físicos independientes. Ejecutar entonces AB real en 2876 oportunidades, comparando PF/DD/Sharpe/Sortino con V49 sin filtrar ganadores.
- **Certificación:** sigue estrictamente bloqueada. Los resultados de arriba **son frecuencias de testigos estructurales**, nunca win rate, PF, drawdown, resultado de un replay full-frame ni permiso para producción.

**Tests/código económico:** quality [#38081283430](https://github.com/mezas3238-hue/qore-core/actions/runs/38081283430) GREEN (Ruff, Mypy 1,642 archivos, 57 tests) para auditoría fuente. Integración overlay/runner bajo CI nueva [workflow source attestation](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/.github/workflows/qore-scalper-a1-source-sensor-independent-nine-market-attestation.yml); usar **resultado final exacto HEAD** de ese run, no asumir GREEN mientras esté en ejecución.

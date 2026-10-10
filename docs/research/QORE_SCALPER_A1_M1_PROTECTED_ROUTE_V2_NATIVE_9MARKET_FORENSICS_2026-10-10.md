# QORE Scalper A1 — Validación causal M1 V2 de los 1.632 sensores pendientes

**Fecha:** 2026-10-10 | GitHub only | A1 Cognitiva PR #758 (DRAFT) | Arquitecto B Metodología PR #759 (DRAFT) | PR maestro #623 (no merge, no VPS ni live).

## Ejecución y evidencia real (no simulación de métricas)

[**QORE Scalper A1 Real M1 Protected-Swing Route Forensics V2 Nine Markets — Actions #38083508578 — 11/11 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38083508578)

**Inputs inmovilizados:** V49 source opportunities originales 9/9 [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), 2.876 source IDs originales y M1 `provider_native_m1=true`, read-only, noninterpolated [#35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334). Por fuente sólo barras M1 `closed_at <= original.m1_trigger_confirmed_at` posteriores a la tesis M15, sin outcomes, posiciones, comisiones, órdenes o velas futuras. El código corre `observe_first_structural_cisd`, `observe_first_m1_cisd` y `observe_first_m1_fvg_cisd_continuation` sobre ese horizonte, no utiliza un sensor CISD parcial como veto.

**Total 2.876 / 2.876 source IDs, 9 mercados; original 1.244 protected-swing `OBSERVED` previos reconciliados exactamente.**

| Clase de swing M1 | FVG_RETRACE_CISD | LIQUIDITY_SWEEP_CISD | Total |
|---|---:|---:|---:|
| Protected pivot confirmado **en la vela de entrada** | 681 | 563 | **1.244** |
| Primer protected pivot confirmado **antes** de entrada y **sin tocar desde la confirmación** | 434 | 207 | **641** |
| Primer pivot confirmado previamente, pero **vulnerado antes de la entrada** | 394 | 253 | **647** |
| Sin primer testigo structural protegido reobservado | 2 | 342 | **344** |
| **Total** | **1.511** | **1.365** | **2.876** |

**Resultado:** nuevo censo estructural causal investigativo **1.885 / 2.876 = 65,5%** si se cuentan los 641 pivotes **previos todavía intactos**. Eran **1.244/2.876 = 43,3%** en el estándar anterior `confirmado exclusivamente al cierre de entrada`. Quedan 991 sin acreditar bajo la V2: 647 con *primer* protected pivot previo vulnerado y 344 sin el primer pivot confirmado. **No significa 991 señales malas, ni supone pérdida comercial.** Un CISD posterior, otra estructura alternativa o semántica TTrades diferente pueden explicar casos: A2 debe determinarlo bajo fuente autor-fiel antes de usar en política.

### Hallazgo de consistencia del código fuente

La ruta completa **correspondiente a la familia original V49** fue confirmada **exactamente a la vela fuente para 2.876/2.876** por los observadores originales, evaluados otra vez con las mismas M1 nativas. Es una **reproducción interna de V49** — no una verificación independiente del método original del autor. Tampoco contradice la auditoría A2 que halló **381 discrepancias con su sensor shadow**: distintos observadores/ventanas pueden devolver distintos primeros CISD; el sensor shadow original NO debe ser promovido sin reconciliación A2. No se aplicó abstención frente a esos 381.

### Seguridad y límites del testigo previo (641)

Un pivot puede seguir protegido cuando su confirmación fue **antes** del `m1_trigger_confirmed_at`: para LONG ninguna vela nativa M1 con `confirmed_at < closed_at <= decision_at` puede tener `low <= pivot.low`; para SHORT ninguna puede tener `high >= pivot.high`. Además el pivot debe seguir en el lado correcto del close de entrada. Se exige prueba `source_opportunity_id`, `decision_at`, `confirmed_at`, `swing_price`. El sistema **no toca la entrada o el stop de fuente** ni presume que ese pivote sea automáticamente la ruta ejecutable TTrades. Es evidencia adversarial de contexto y será sometida a revisión de B.

**Código:** `src/qore/infrastructure/trader_lab/capitalizer_a1_m1_protected_route_forensics_v2.py`; **tests:** `tests/infrastructure/trader_lab/test_capitalizer_a1_m1_protected_route_forensics_v2.py`; **workflow:** `.github/workflows/qore-scalper-a1-m1-protected-route-forensics-v2.yml`. Los nueve libros JSONL `scalper-a1-m1-protection-family-review.jsonl` por mercado y matriz consolidada están archivados en ese run como artefactos. Incluyen TODOS los IDs y timestamps, además de familia, clase y status previo. El paso `causal_fidelity` corrió Ruff/Mypy/pytest y pasó. `aggregate` prueba identidad original, 1244 strict baseline, cobertura 2876 y 0 veto.

## Acciones pendientes para reconciliación y conexión completa

**A2 metodología:** auditar primero las **647** fuentes con primer pivot vulnerado y las **344** sin primer pivot, desglosando casos `SWEEP_CISD` y `FVG_RETRACE_CISD`, y evaluar si hay segundos pivotes realmente confirmados, FVG primero/otro y diferencias del observador A2. Revisar los 641 candidatos previos intactos contra reglas originales del autor. Prohibido elevar automáticamente su status a *author-certified* o convertir `NOT_AVAILABLE` en filtro de trade. También quedan por estudiar los 12 M15 y 124 H1 testigos anteriores ausentes.

**A1 cognitiva:** en el próximo port de evaluación, transportar estas cuatro clases como **tokens diagnósticos adversariales** con fuente comprobada, pero **no afirmar** `M1_PROTECTED_SWING_ATTESTATION:OBSERVED` sobre casos previos hasta que la semántica del autor sea confirmada. La validación anterior ya conecta M15/H1/M1 contemporáneo `OBSERVED` al Master Frame mediante `capitalizer_a1_validated_sensor_overlay_v1.py`. El siguiente paso es completar el **real nine-market world/perception/regime/cross-market/session-ledger as-of** y ejecutar full Master Frame PAPER sobre todos los 2876 source IDs; el PF/DD cognitivo no existe hasta entonces.

**Estado:** nuevas 641 pruebas causales de pivote previo intacto en investigación, **sin recortes de oportunidades**, sin risk authorization, sin claims de PF/DD nuevo, sin órdenes, sin certificación, sin merge ni VPS/live.

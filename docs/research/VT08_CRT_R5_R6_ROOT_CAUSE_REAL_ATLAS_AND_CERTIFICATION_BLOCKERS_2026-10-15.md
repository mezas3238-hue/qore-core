# VT08 CRT — R5+R6: diagnóstico definitivo de 108 WAIT y 5 UNKNOWN sobre Atlas M5 original

**Fecha:** 15 oct 2026. **Estado:** reproducción de investigación verificada en GitHub; NO certificación G-M1/2/3/4/5/Global. **No cambio de V1/V2/V3 ni de G-M4**. Owner autoriza metodología CRT QORE combinada RomeoTPT + SpeculatorFL + TraderFlameseN; las reglas exactas propuestas deben pasar revisión. Está prohibido sizing en VT08; CIBO/QORE Risk es única autoridad patrimonial. Sin órdenes, demo, live, VPS, broker ni merge.

## Preregistros y reproducibilidad verificables

1. **R5 preregistrado ANTES del análisis:** [G2/G7 R5 causal WAIT / blind pack](VT08_CRT_G2_G7_R5_CAUSAL_TRIAGE_AND_BLIND_PACK_PREREG_2026-10-15.md), commit **62e1706ec61b5becbd79c350dd797719290b47e7**.
2. **R5 real:** GitHub Actions [#38819759238](https://github.com/mezas3238-hue/qore-core/actions/runs/38819759238) SUCCESS sobre SHA **c81dd07d7b04852094c5e7f04c7d7b695ed7df73**. Ruff/mypy/pytest 20 PASS, AUDUSD y USDJPY matrix SUCCESS. Original M5 148,171 + 148,201 = 296,372, original SHA-backed CIBO Atlas12 run #35166210458.
3. **R6 preregistrado ANTES del replay de causas:** [G-M4 cinco UNKNOWN](VT08_CRT_R6_GM4_FIVE_UNKNOWN_GAP_AND_BARRIER_TRIAGE_PREREG_2026-10-15.md), commit **baa36d32993ec51beb12ddc1d323f07a7732d790**.
4. **R6 real:** [GitHub Actions #38820419577](https://github.com/mezas3238-hue/qore-core/actions/runs/38820419577) SUCCESS sobre SHA **3c49b9ebe501475b80eb77dd2072c4eb95713f0f**, strict Ruff + mypy, **28/28 pytest PASS**, ambas matrix reales SUCCESS. Añade diagnóstico ex-post independiente de UNKNOWN, no reclasifica los originales ni altera el ledger de decisiones.

Código de investigación R5+R6: src/qore/infrastructure/trader_lab/vt08_crt_g2_g7_real_atlas_pit_bridge.py + vt08_crt_gm4_unknown_root_forensics.py. Workflow: .github/workflows/vt08-crt-g2-g7-real-atlas-pit-audit.yml. Adversariales: tests/infrastructure/trader_lab/test_vt08_crt_g2_g7_real_atlas_pit_bridge.py y test_vt08_crt_gm4_unknown_root_forensics.py.

## Descubrimiento prioritario: un número pequeño de UNKNOWN propaga 108 WAIT

| Métrica | AUDUSD | USDJPY | TOTAL |
|---|---:|---:|---:|
| V3+G-M4 fuentes reconciliadas | 61 | 78 | **139** |
| G7 WAIT explicado ex-post por UNKNOWN anteriores | 43 | 65 | **108** |
| G7 WAIT exclusivamente por terminal conocido después | 0 | 0 | **0** |
| G7 PROVISIONAL, sin autoridad | 18 | 13 | **31** |
| Casos GM4 con terminal todavía UNKNOWN | 2 | 3 | **5** |
| Incidencias acumuladas de UNKNOWN previos censurados en todos los WAIT | 49 | 135 | **184** |

El criterio G7 **ALL PRIOR TERMINAL** implica que una sola tesis anterior sin terminación verificada bloquea TODOS los posteriores source events hasta resolverla. Los 108 WAIT no representan 108 fallos metodológicos independientes ni 108 pérdidas económicas; se originan en el arrastre por los 5 UNKNOWN. El número 184 cuenta repeticiones de UNKNOWN previos a través de las decisiones, **no 184 casos distintos**.

Primeros UNKNOWN que disparan la propagación observados en el run: AUDUSD source_event_id **bfc66b2457f3e3ec93ae** y USDJPY source_event_id **9572d855b2dedc8fecb2**. Se han segregado rigurosamente los diagnósticos de la decisión inicial: el summary permite investigación *ex post*, el JSONL de decisiones solo conoce terminales disponibles al instante. Los resultados futuros NO habilitan rearm retrospectivamente. No relajar G7 a partir de PnL ni antes de aprobación independiente.

## Cinco UNKNOWN originales: causa de origen revalidada con raw M5

| Motivo G-M4 congelado | AUDUSD | USDJPY | TOTAL | Observación |
|---|---:|---:|---:|---|
| UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER | 1 | 1 | **2** | Open M5 de decisión **ya más allá de la invalidación estructural** |
| UNKNOWN_MISSING_M5_BEFORE_TERMINAL | 1 | 2 | **3** | Existe al menos un timestamp M5 original faltante antes de observar terminal |
| TOTAL STILL UNKNOWN | 2 | 3 | **5** | **Ninguno reclasificado como terminal probado** |

El R6 comprueba las dos primeras geometrías contra M5 real (subtipo **ALREADY_BEYOND_INVALIDATION**, 1 por mercado) y localiza para las otras tres **la primera M5 faltante**, si hay barra previa y la siguiente M5 disponible dentro de C3. Los cinco registros de diagnóstico ex-post figuran separados en gm4-unknown-expost-forensics.jsonl. **No rellenar velas, no inferir barreras tocadas durante huecos, ni declarar “expiró por reloj” donde no se probó trayectoria.**

Posible desbloqueo **metodológico**, NO aplicado: el método puede definir como **ABSTAIN no viable en el propio reloj de decisión** aquellos 2 estados de precio observado fuera de invalidación, con evidencia fuente y firma independiente. Eso no equivale a cambiar el histórico G-M4 ni a crear entrada. Los otros 3 requieren **recuperación verificable del M5 faltante desde fuente lícita y compatible** o censura permanente; por sí solo un feed distinto no reconstituye el original sin identidad/timezone/hash y soporte de procedencia. Resolver si G7 exige realmente TODOS los padres anteriores o solo un lineage activo previamente probado debe decidirse ANTES de nuevo OOS; jamás escoger por mejora de densidad/PnL.

## G2 — 36 conflictos con expediente revisable libre de outcomes

R5+R6 conserva 36 casos con segundo candidato H4 C0 de referencia frente a C1 (AUDUSD **16**, USDJPY **20**; 14 opuestos y 22 del mismo sentido). C0/C1/C2 son **OHLC H4 totalmente cerradas antes de decisión**, con ID blind_case_id estable, reloj, digest de evidencia, pero **sin C3, G-M4 outcome, PnL, sizing, fill, autorización ni futuro** en **g2-c0-c1-blind-predecision-cases.jsonl**. Cada candidato carece de firma: selected_reference=null, owner_approval=false, independent_reviewer_adjudicated=false. Requiere revisión humana ciega a resultados. Pack acotado a C0/C1, **no sustituye inventario exhaustivo** de old CRTH/CRTL; G2 WAIT en los 139 es honesto.

## Artefactos originales R5/R6 con cadena SHA / caducidad GitHub

**R5:** [Run #38819759238](https://github.com/mezas3238-hue/qore-core/actions/runs/38819759238):
- AUDUSD artifact **12012312946**, ZIP SHA256 e0d6fae35c5b9c045558154cd690ef50a8fe43b8676dc37e60680df30b595e39.
- USDJPY artifact **12011224480**, ZIP SHA256 47c2869d577c107efe8d0b38a2e0d19f7667e995c2c626728f965d847b1796de.

**R6:** [Run #38820419577](https://github.com/mezas3238-hue/qore-core/actions/runs/38820419577):
- AUDUSD artifact **12012303958**, ZIP SHA256 2eefb39cb52edcb4949cee9d47d3240b4469c2e9b62cb0043b5d1229ea2e117b.
- USDJPY artifact **12012024816**, ZIP SHA256 bf063422553a4d4a25511e93aeafc9293c0a8eb34298fdf1a10b1e28307985f9.

R5 nominal expires_at 2027-01-13T22:50:06Z; R6 nominal expires_at 2027-01-13T22:56:14Z. Artefactos temporales, no bóveda definitiva. Los originales Atlas vencen antes (2026-12-16; issue #837). Todos estos ZIP tienen sums internos con source commit, decisional JSONL, predecision blind casebook y en R6 5 forensic casebooks separados.

## Camino mínimo restante para certificación (sin artificios)

**P0-1 metodología G1–G7:** G2 inventario PIT exhaustivo y prioridad adjudicada; G7 semántica de terminación/event lineage, rechazo de autorrearm y política sobre UNKNOWN. Firmas GitHub Owner y auditor INDEPENDIENTE atadas a versión/hash, issue #976; 0 reviews no permite PASS.

**P0-2 G-M4:** valorar causalidad de los 2 ya fuera de invalidación como no viable al decidir (sin considerar trade) y gestionar 3 gaps por fuente realmente verificable o censura; no fabricar terminal ni cerrarlo automáticamente.

**P0-3 cognitiva:** G-M2 48 first-look ciegos reales adjudicados por revisor independiente; G-M3 prueba adversarial y verdad externa, G-M4 integración con Risk/CIBO y ledger temporal auténtico. Solo con sus PASS legítimos puede emitirse G-M5; no más tests autorreferenciales llamados aprobación.

**P0-4 económico GLOBAL:** los V2/V3 históricos de desarrollo mostraron trayectoria adversa, no equity ni fills; no hay edge rentable probado, ni BID/ASK real ejecutado, ni nueva OOS virgen. PF/Sortino/Sharpe, costes, stress/WFO/Monte Carlo y DD patrimonial a cargo exclusivo de CIBO Risk. **VT08 sizing categóricamente prohibido**, incluso lotes o 1R ficticios.

**Cert truth:** G-M1..4 PARTIAL; G-M5 NOT ISSUED; GLOBAL NOT CERTIFIED. PR #626 sigue DRAFT, NO MERGE, NO órdenes/demo/live/VPS.

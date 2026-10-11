# Scalper A2 — Auditoría ejecutable de llamadas y procedencia metodológica (2026-10-10)

**Arquitecto:** A2 Metodología, issue #757, PR draft #759. **Cross-review:** A1 Cognitiva, issue #756, PR draft #758.  
**Punto de partida:** PR #623, arquitectura H1→M15→M1, nueve mercados, tres sesiones.  
**Código instrumentador:** `src/qore/infrastructure/trader_lab/capitalizer_scalper_caller_audit_v1.py`, exclusivamente auditoría estática sin autoridad de admisión, sizing, trading ni certificación.  
**HEAD ejecutado:** `9ae8960441df3bfc0f68508f8c543c90be3701c5`  
**GitHub Actions:** [#38047691581](https://github.com/mezas3238-hue/qore-core/actions/runs/38047691581) **SUCCESS** — ambos jobs, Ruff global, Mypy src/tests, regresiones método/causalidad y tests V53/V54.  
**Evidencia cruda:** [artefacto JSON + log #11668167114](https://github.com/mezas3238-hue/qore-core/actions/runs/38047691581/artifacts/11668167114).

## 1. Metodología de reproducción

La tarea GitHub Actions `Static caller census for QORE source gates` analiza con Python AST todos los `.py` dentro de `src`, resuelve imports absolutos y alias explícitos, detecta llamadas por nombre y `module.function()`, y recorre un grafo de llamadas desde `build_market_capacity` (V49) y `build_market` (V50-G). **No ejecuta el replay, no incorpora datos de precios y no infiere rentabilidad.**

Resultado reproducido: **790 módulos, 90.129 llamadas examinadas, 88.439 referencias sintácticas resolubles, 144 marcadores dinámicos**. No interpretar las referencias como 88.439 decisiones ejecutadas: son nodos de AST.

**Frontera epistemológica:** un `NO_STATIC_CALLER_FOUND_RUNTIME_UNRESOLVED` no significa DEAD ni prueba de que no exista alguna llamada dinámica, indirección por instancia, import runtime, plugin o variante en otra rama. `REACHABLE_FROM_SELECTED_RESEARCH_ENTRYPOINT` prueba conexión sintáctica, no que una condición gobierne una señal concreta en runtime. El censo solo contiene el HEAD de la rama B auditada: A1 añadió por separado `evaluate_full_frame_research_batch` en su rama #758, no incluida en la B. Es incorrecto utilizar este informe para afirmar que el adaptador A1 carece de callers.

## 2. Resultados materiales con archivos y líneas

| ID | Call target | Hallazgo en branch B | Clasificación / decisión |
|---|---|---|---|
| CALL-001 | `capitalizer_dual_source_entry_acceptance_v1.assess_dual_source_entry` (super-AND MSS+FVG+OB) | **0 direct calls** en los 790 módulos. | `NO_STATIC_CALLER_FOUND_RUNTIME_UNRESOLVED`. No es prueba de dead code, pero **no** se le puede atribuir reducción V50-G a 90 trades. |
| CALL-002 | `capitalizer_source_strategy_grammar_v2.assess_source_strategy` | 1 caller, `capitalizer_source_trader_engine_v2.py:227` | `STATIC_CALLER_FOUND_OUTSIDE_SELECTED_ENTRYPOINT`. Contrato distinto del V49 HF. |
| CALL-003 | `capitalizer_source_trader_engine_v2.assess_source_trader_engine` | 2 callers: `capitalizer_source_trader_pipeline_v2.py:90` (fractal) y `:145` (FTM). | `STATIC_CALLER_FOUND_OUTSIDE_SELECTED_ENTRYPOINT`; no convertir `FTM` en gate de todos los scalps. |
| CALL-004 | `capitalizer_high_frequency_capacity_census_v49._earliest_m1_trigger` | `capitalizer_high_frequency_capacity_census_v49.py:413` desde `build_market_capacity`; también `capitalizer_v50_m1_rearm_capacity.py:331`. | V49 source y re-arm utilizan el selector de alternativas. |
| CALL-005 | `observe_first_m1_cisd` | `capitalizer_high_frequency_capacity_census_v49.py:262`, también V48 legacy census. | Ruta source `LIQUIDITY_SWEEP_CISD` respaldada, no requiere super-AND MSS+FVG+OB para observar CISD. |
| CALL-006 | `observe_first_m1_fvg_cisd_continuation` | `capitalizer_high_frequency_capacity_census_v49.py:281`, también V48 census. | Ruta source `FVG_RETRACE_CISD`, alternativa y no conjunta con CALL-005. |
| CALL-007 | `capitalizer_master_cognitive_frame.build_master_cognitive_frame` y `capitalizer_v50_master_cognitive_adapter.adapt_v50_to_master_context` | 0 llamadas directas en HEAD B. | A1 bridge V50-G completo **no demostrado**; el adaptador A1 real está en rama separada y necesita auditoría independiente. |
| CALL-008 | `h1_state_until` | Un READ de atributo: `capitalizer_v53_winner_preserving_rearm_economics.py:230` en `_attempt_opportunity`, copiando `attempt.h1_state_until` a un nuevo `V49Opportunity`. | **METADATA_PROPAGATION, FUTURE_LEAK_NOT_DEMONSTRATED**: hace falta trazar consumidores del objeto reconstruido. A1 verificará que cognitive predecision nunca conoce una señal H1 opuesta futura. |

## 3. Interpretación de segundo arquitecto — qué cambia y qué no

- La hipótesis previa «el super-AND MSS+FVG+OB provoca 90 trades» **carece de evidencia causal** en V49/V50-G. El contrato existe en el código, pero su efecto vivo no está demostrado; no lo eliminamos a ciegas ni atribuimos métricas.
- El source V49 tiene dos familias alternativas comprobadas también por `test_capitalizer_v49_source_alternative_contract.py` en Green Actions; aún faltan waterfalls **por oportunidad real** para cuantificar qué gate posterior transforma población de V49 en 90 operaciones V50-G.
- El `h1_state_until` tiene al menos un camino de traslado entre dataclasses en V53; su sola copia no es prueba de lookahead. Debe instrumentarse `as_of` al entrar al Master Frame.
- Para el siguiente replay B solicita un `gate_event` por oportunidad original, con `source_id`, `parent_h1_id`, `m15_id`, `m1_event_id`, `decision_at`, `route`, `gate_id`, `gate_result`, `reason_codes` y `closed_only`. A1 añade `component_invoked`, `memory_asof`, `metacognitive_reason`, `execution`, `settled_after`; jamás usar outcome futuro para filtrar entradas.
- Medir denominadores en los nueve mercados con la **misma población original**, recuperando densidad sin obligar cuotas, winner count ≥80%, winner R ≥90%; medir PF neto, DD, Sharpe, Sortino, OOS, costes y MC. El rechazo Owner del V50-G de 90 trades permanece.

## 4. Pendientes antes de certificar

**A2:** waterfall de admisión V49→V50-G→V50-R/V51/V53/V54 con razones y timestamps reales; procedencia source por cada guard ejecutado, no solo por módulo; validar comparabilidad de población y rutas Asia/London/NY/FTM; considerar cross-review de cambios cognitivos antes de integrar.  
**A1:** frame real 9 mercados conectado al source stream, memoria prequential seleccionada/settled-only, evidencia WHY por módulo, exhaustiva temporalidad H1 expiry, causal A/B sin futuro, densidad/winner preservation.  
**Ambos:** no fusionar PR #623/#758/#759, no VPS ni LIVE, no certificados, hasta evidencia científica completa y aprobación del Owner.

**VEREDICTO:** STATIC CALLER PROVENANCE AUDITED + GITHUB QUALITY GREEN; **LIVE CALLER / REPLAY WATERFALL / FULL COGNITION / SOURCE FIDELITY / PROFITABILITY NOT CERTIFIED**.

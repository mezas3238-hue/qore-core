# SCALPER — Auditoría técnica de continuidad y coordinación dual (2026-10-10)

**Base auditada:** PR #623, rama `agent/qore-capitalizer-cognitive-v1-001`, SHA `535a2054d43c259e09b9a7e8eb3d54d21a503b4c`.  
**Origen canónico:** `docs/research/QORE_CAPITALIZER_COGNITIVE_SCALPER_MASTER_HANDOFF_2026-10-10.md`.  
**Alcance:** revisión estática del código y documentos de GitHub + cotejo con fuentes primarias TTrades publicadas. No se ejecutó replay, CI ni GitHub Actions en esta auditoría. No se consultó VPS.  
**Veredicto:** **NO CERTIFICADO / COGNITIVE_INTEGRATION_UNPROVEN / SOURCE_FIDELITY_OPEN / ECONOMICS_NOT_PROMOTABLE**. Cualquier resultado citado más abajo procede de artefactos identificados en el handoff, no de una ejecución nueva.

## A. Auditoría: hallazgos reproducibles

| ID | Severidad | Evidencia revisada | Hallazgo | Salida exigida |
|---|---|---|---|---|
| AUD-C01 | P0 | `capitalizer_v50_cognitive_geometry_economics.py::build_market` | El ensayo V50-G llama `build_v50_cognitive_snapshot` con `CapitalizerExperienceMemory()` **nuevo por oportunidad** y `metacognitive_readiness=WELL_SUPPORTED` constante. No prueba memoria acumulativa causal ni metacognición completa. | Auditoría de linaje de memoria; replay con estado temporal persistente/aislado por mercado y periodo, sin resultados futuros, y ablations |
| AUD-C02 | P0 | `capitalizer_v50_master_cognitive_adapter.py` frente a `capitalizer_v50_cognitive_geometry_economics.py` | El adaptador al Master Frame **existe**, pero la función auditada V50-G no invoca al `build_master_cognitive_frame`. No atribuir el PF de V50-G al Master Brain completo. | Trazas de invocación de todas las capas del frame y test de integración end-to-end |
| AUD-C03 | P0 | `capitalizer_v50_cognitive_hf_bridge.py::assess_v50_cognitive_candidate` | La admisión usa familias exactas de estado, frescura, ruido, destino y un memory lookup. El valor económico de cada módulo avanzado debe demostrarse, no deducirse de su mera existencia. | Censo por componente, WHY, decision delta y ablación de cada influencia sobre el mismo flujo de oportunidades |
| AUD-C04 | P0 | `capitalizer_v50_m1_rearm_capacity.py::_portfolio_ready`; `capitalizer_v51_multi_era_repair.py` | Cinco workflows siguen reportados como bloqueados por Ruff/Mypy en el handoff (V50-R, V51, V53, V54-A, V54-B). | Corregir solo defectos de calidad antes de alterar semántica; verificar nuevas Actions |
| AUD-M01 | P0 | `capitalizer_high_frequency_identity_v49.py`, TTrades generic | QORE congela **H1→M15→M1** y prohíbe Daily/H4 como compuertas; TTrades generic emplea Daily como contexto, H1 bias, M15 swing y M1 entry. | Declarar especialización QORE, no fidelidad literal total |
| AUD-M02 | P0 | `capitalizer_source_strategy_grammar_v2.py`, `capitalizer_dual_source_entry_acceptance_v1.py` y `capitalizer_high_frequency_decision_graph_v49.py` | Existen contratos con **gramáticas distintas**: dual-source M1 exige MSS+FVG+OB en AND, mientras V49 define alternativas de M1. No se ha probado una sola ruta canónica equivalente en todos los ensayos. | Inventario de callers y grafo exacto de admisión real por ruta; retirar etiquetas engañosas de 'source faithful' |
| AUD-M03 | P0 | TTrades Asia y London vs identidad V49 | La ruta literal Asia del autor admite entrada posicional o 4H→15M, y London se articula Daily→4H→15M. El H1→M15→M1 universal de QORE es distinto. | Clasificar rutas `QORE_ADAPTATION` o abrir rediseño explícitamente aprobado; no reintroducir Daily/H4 silenciosamente |
| AUD-M04 | P0 | TTrades NY Manipulation, FTM | FVG y OB aparecen como **alternativas de refinamiento**, y FTM no es standalone. No imponer una superintersección de reglas ajenas a la ruta. | Matriz por sesión/ruta: obligatorio vs opcional, con fuente y posición exacta |
| AUD-M05 | P0 | `capitalizer_scalper_certification_standard_v2.py::CertificationEvidence` + `evaluate_certification` | El estándar financiero V2 consultado **no contiene un campo/gate `author_fidelity_audit_passed`**. Un documento que lo exige no basta para bloquear una aprobación programática. | Añadir gate de fidelidad fail-closed con pruebas sin alterar los gates económicos |
| AUD-M06 | P0 | PR #623 + handoff §11 | Contrato del Owner establece drawdown operativo objetivo 3–5R y techo duro de aceptación **6R**, mientras V2 permite DD OOS <=10R. Son umbrales de propósito diferente; el techo Owner no debe omitirse. | Gate de aceptación Owner explícito y independiente del límite V2; arbitrar regla y pruebas |
| AUD-S01 | P0 | Handoff §8 + comment 6096131385 | V50-G 90 trades, PF 1.53459, +26.1231R, DD 9R, corrida 36788519476: **rechazado** por densidad (no es candidato); winner count/R no medidos. | Mantener solo como diagnóstico, recuperar flujo HF conservando winners |
| AUD-S02 | P0 | `capitalizer_scalper_certification_standard_v2.py` + handoff | PF/Sharpe/Sortino/DD aislados no certifican: faltan evidencia independiente/prospectiva, costes, MC, clustering, MAE/MFE, antileakage, densidad y aprobaciones. | Una batería congelada de decisión con firma de artefactos y cadena causal |

## B. Prueba primaria de fidelidad metodológica (primeras filas del ledger)

Cada fila es **inicial y no exhaustiva**; el Arquitecto B debe extenderla a *todas* las reglas ejecutables. Los pasajes citados son del cuerpo web del autor; los timestamps de videos requieren investigación adicional.

| Rule ID | Route | Código QORE | Autor / URL / posición textual | Clase | Veredicto | Acción |
|---|---|---|---|---|---|---|
| TTR-G01 | Generic | `capitalizer_high_frequency_identity_v49.py` | TTrades, [Scalping Model](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/), sección **The Core Concept**, estructura Daily→H1→M15→M1 | SOURCE_EXPLICIT | PARTIAL | Registrar Daily omitido como adaptación QORE |
| TTR-G02 | Generic | `capitalizer_high_frequency_decision_graph_v49.py` | Misma fuente, **Establishing Hourly Bias** y **Finding the Fifteen Minute Swing Point** | SOURCE_EXPLICIT | MATCH/PARTIAL según detección | Exigir evidencia H1 candle closure + M15 swing, sin inventar condiciones |
| TTR-G03 | Generic | `capitalizer_v50_cognitive_opportunity.py` | Misma fuente, **Entry**: M1 ejecuta; FVG/CISD/protected swing como comportamientos, stop estructural y objetivo HTF | SOURCE_EXPLICIT | PARTIAL | Matriz de familias M1; separar tesis stop M15 de ejecución stop M1 como QORE |
| TTR-A01 | Asia literal | `capitalizer_high_frequency_identity_v49.py` | TTrades, [How to Trade Asia](https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/), **Option One/Option Two** | SOURCE_EXPLICIT | CONFLICT | No afirmar fidelidad literal; preservar modelo QORE hasta decisión del Owner |
| TTR-L01 | London literal | mismo | TTrades, [How to Trade London](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/), **Start With A Daily Bias / Use The 4 Hour Candle / Confirm The Swing On The 15 Minute** | SOURCE_EXPLICIT | CONFLICT | Identidad propia o bifurcación explícita; sin tocar código congelado |
| TTR-N01 | New York Manipulation | `capitalizer_dual_source_entry_acceptance_v1.py` | TTrades, [NY Manipulation](https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/), **How to Recognize It on Charts** y **Entry Models** | SOURCE_EXPLICIT | CONFLICT si AND universal | FVG/OB/otra técnica como alternativas dentro de esa ruta |
| TTR-F01 | FTM | `capitalizer_source_strategy_grammar_v2.py` | TTrades, [Failure to Manipulate](https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/), **Trade the Continuation / Pair It With Higher Timeframe Bias** | SOURCE_EXPLICIT | PARTIAL | Continuación estructural con HTF, no breakout ciego |
| ICT-001 | ICT ancestor | `capitalizer_dual_source_entry_acceptance_v1.py` | ICT / Michael J. Huddleston, [2022 Mentorship Episode 2](https://www.youtube.com/watch?v=tmeCWULSTHc) | UNRESOLVED | UNRESOLVED | Vincular cada requisito ICT a timestamp exacto antes de atribución |

Clasificaciones autorizadas: `SOURCE_EXPLICIT`, `SOURCE_STRONGLY_IMPLIED`, `INTERPRETATION`, `QORE_ENGINEERING_RULE`, `UNRESOLVED`. Veredictos: `MATCH`, `PARTIAL`, `CONFLICT`, `UNRESOLVED`. Debe agregarse para cada fila **obligatorio vs alternativa**, path/símbolo del caller, evidencia temporal y test.

## C. Dos arquitectos: propiedad exclusiva y colaboración

### Arquitecto A — COGNITIVA (otro arquitecto, issue/branch separados)

Responsabilidad exclusiva: Master Brain/Frame, World Model, Market/Session Brain, percepción, atención, régimen, memoria y metacognición, causalidad/exposure, adversarial, oportunidad, salida/posición y puente V50. Reparar P0 V50-R y V51 **sin modificar economía ni metodología**. A debe:

1. reconstruir el grafo real de llamadas (no solo clases presentes) y producir `component → input causal → decisión → WHY → test → evidence`;
2. verificar secuencialidad temporal y memoria prequential auténtica vs objetos recreados, sin contaminación por resultado futuro;
3. instrumentar traza determinista de `WAIT / ABSTAIN / PASS_TO_STRATEGY`, no autoridad de ejecución;
4. implementar prueba con Master Frame completo y ablaciones comparables, sin reescribir ruta ni aumentar filtrado ciego;
5. integrar re-arm M1 con parent H1/M15, thesis intacta, MAX3 y winner mass;
6. entregar cobertura de 9 mercados/3 sesiones y reportar los efectos económicos solo cuando exista paridad metodológica y quality GREEN.

### Arquitecto B — METODOLOGÍA (arquitecto actual)

Responsabilidad exclusiva: fidelidad TTrades/ICT, ledger completo, grafo de rutas y alternativas, semántica H1/M15/M1, stops/targets causales, source→replay parity, calidad de harness V53/V54-A/V54-B, gates de fidelidad y certificación. B debe:

1. atar cada regla activa a source/article section o video timestamp sin mezclar autores;
2. separar fuente genérica de Asia/London/NY/FTM; conflicto no se elimina con etiqueta ficticia;
3. demostrar `source engine → oportunidad → canonical fill → stop/target → lifecycle → ledger` y si V49/V50 son investigación QORE o método exacto;
4. corregir los harness V53/V54-A/V54-B solo en calidad antes de nuevas hipótesis;
5. introducir gate de fidelidad fail-closed e identificar contrato de DD Owner <=6R;
6. ensayar optimización del PF/DD sin perder masa ganadora ni densidad high-frequency.

### Contrato de intercambio obligatorio

`ScalperCausalDecisionTrace v1` será una especificación compartida, no una garantía actual de implementación. Por **cada** oportunidad:
`symbol, session, operating_date, source_route, author_source_rule_ids, parent_h1_state_id, m15_setup_id, m1_trigger_id, evidence_timestamps, decision_at, thesis_stop, execution_stop, target_id/price/source, cognitive_component_versions, evidence_provenance, memory_prestate_digest, cognitive_disposition, WHY, downstream_decision, max3_slot_state, post_decision_outcome_sealed`.

- Arquitecto B suministra hechos *pre-decision* y ruta; A no puede alterar los hechos de autor para ganar PF.
- Arquitecto A devuelve cognición causal/traza/WHY; B no puede sustituirla por `WELL_SUPPORTED` fijo o memoria vacía sin declarar aislamiento explícito.
- Ambos revisan tests del otro y publican diferencias con SHA/Actions/artifacts/seed/data fingerprint.
- Resultados futuros y realized R son exclusivamente de fase posterior al cierre de la decisión.
- La fase de certificación se inicia solo cuando **ambas firmas técnicas** dicen `SOURCE_ROUTE_RESOLVED` y `COGNITIVE_PATH_REAL`, con CI verde.

## D. Orden de construcción y gates

**P0 calidad:** arreglar 5 bloqueos vigentes de harness, recuperar QORE CI; no afirmar que están reparados hasta nuevos runs.  
**P1 causalidad:** registrar todas las rutas/callers y activar/verificar full cognitive trace por oportunidad; ejecutar pruebas unitarias y de integración.  
**P2 estrategia/economía:** una única población de oportunidades y comparable A/B; winner count >=80%; winner-R >=90%; recuperar densidad materialmente mayor a 90; sin nuevo umbral numérico fabricado.  
**P3 certificación:** PF OOS era >=1.50, combined >=1.70, Sharpe >=1.50, Sortino >=2.00, expectancy>0, payoff>=1.20 salvo excepción formal, DD OOS <=10R, **Owner acceptance <=6R**, MC P(positivo)>=90% y p95 DD<=15R, post-cost PF>1 y expectancy>0; además anti-leakage, estabilidad, costes en los entornos requeridos, evidencia fresh independiente/prospectiva, RISK/CIBO/validación.

La aprobación económica nunca equivale a fidelidad de autor; ambas puertas son necesarias. Todas las ventanas históricas usadas para diagnosis quedan consumidas y no son una prueba fresh final.

**GOBERNANZA:** GitHub únicamente; PR #623 DRAFT y sin merge. No VPS (ni lectura), LIVE, capital, órdenes MT5 ni despliegue. Un issue/branch de un arquitecto no crea automáticamente una sesión/worker autónomo; el segundo arquitecto debe abrir su rama/tarea desde GitHub y publicar trabajo verificable.
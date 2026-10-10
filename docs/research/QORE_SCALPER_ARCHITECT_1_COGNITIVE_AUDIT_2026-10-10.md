# QORE Scalper — Arquitecto 1: auditoría cognitiva y reparación P0

**Fecha:** 2026-10-10  
**Rama:** `agent/scalper-architect-1-cognitive-cert-20261010`  
**Base congelada para separación de arquitectos:** `535a2054d43c259e09b9a7e8eb3d54d21a503b4c`  
**PR matriz:** #623 (DRAFT; NO MERGE)  
**Issue propietario:** #754 — Arquitecto Cognitivo  
**Issue revisión cruzada:** #755 — Arquitecto Metodológico  
**Gobernanza:** SOLO GITHUB; NO VPS / LIVE / capital / producción / merge.

## 1. Alcance de auditoría y estado real

El commit de entrada contiene documentación de continuidad, no aprobación de metodología ni de certificación. Inspección realizada sobre fuentes Python y ejecuciones de GitHub Actions. Los bloqueos del **corrected-core** son fallas de calidad antes de la ejecución económica; la mera reparación de calidad NO valida los resultados.

| Workflow | Run previo | Evidencia de bloqueo |
|---|---:|---|
| V50-R capacity | [36788519468](https://github.com/mezas3238-hue/qore-core/actions/runs/36788519468) | Mypy L599/L601, reutilización `key` con tuple de distinta aridad |
| V51 multi-era | [36788519475](https://github.com/mezas3238-hue/qore-core/actions/runs/36788519475) | Mypy L129 `Any` devuelto como dict; L580 `item` inferido con tipo incompatible |
| V53 economics | [36788519495](https://github.com/mezas3238-hue/qore-core/actions/runs/36788519495) | Ruff I001: import alias privado debe ir en grupo separado |
| V54-A stop ladder | [36788519508](https://github.com/mezas3238-hue/qore-core/actions/runs/36788519508) | Mypy L363/L365, variable `key` reutilizada con tuple de distinta aridad |
| V54-B partial runner | [36788519463](https://github.com/mezas3238-hue/qore-core/actions/runs/36788519463) | Ruff I001: importar `_session_bars` separado de `_replay` alias |
| Global QORE CI | [36788524350](https://github.com/mezas3238-hue/qore-core/actions/runs/36788524350) | Ruff I001 en V53 y V54-B |

### Correcciones realizadas en rama A1 — sin rediseño económico

- `capitalizer_v50_m1_rearm_capacity.py`: `session_key` diferencia llave de sesión (tuple2) y `_setup_key` (tuple5). MAX3 intacto.
- `capitalizer_v51_multi_era_repair.py`: JSON debe representar objeto con claves string (validación fail-closed); `geometry_item` evita reuso tipado de `item`. Comparadores económicos y datos no modificados.
- `capitalizer_v53_winner_preserving_rearm_economics.py`: isort/Ruff ordena el alias `_replay` en grupo separado.
- `capitalizer_v54_causal_m1_stop_ladder_rescue.py`: `session_key` evita colisión de tipos; prioridad cronológica y MAX3 intactos.
- `capitalizer_v54_structural_partial_runner.py`: isort/Ruff agrupa alias `_replay` aparte.

**Validación pendiente:** GitHub Actions sobre nueva rama/PR; documentar runs y conclusiones antes de declarar Quality GREEN.

## 2. Cognitiva auditada: inventario operacional

| Capa | Implementación | Decisión esperada y comprobación |
|---|---|---|
| Percepción/cronología | `capitalizer_perception_integrity.py` | Sólo M1 cerrado, timestamps/DST, quotes/provenance; rechazar futuro |
| Modelo global | `capitalizer_global_world_model.py` | Snapshot completo nueve mercados, sesión, ledger, exposición |
| Master Brain/Frame | `capitalizer_master_brain.py`; `capitalizer_master_cognitive_frame.py` | Evaluación pre-estrategia con metacognición, adversarial y arbitraje; demostrar llamada por oportunidad |
| Brains especializados | `capitalizer_context_brains.py`; `capitalizer_market_brain_registry.py` | Identidad de mercado, hipótesis, fase de sesión |
| Atención/Regímenes/Journey | `capitalizer_attention.py`, `capitalizer_regime_intelligence.py`, `capitalizer_session_journey_intelligence.py` | Datos causales de situación, sin mutación retrospectiva |
| Memoria y conocimiento | `capitalizer_memory.py`, `capitalizer_experience_memory.py`, `capitalizer_v50_prequential_cognitive_memory.py` | Sólo trades cerrados en pasado; bloquear outcomes de candidatos no ejecutados |
| Supervisión/antagonismo | `capitalizer_adversarial_reasoning_v2.py`, `capitalizer_cross_market_causality.py`, `capitalizer_exposure_graph.py` | Reglas pre-trade, evitar falsas correlaciones y fuga de resultados |
| Presión y soberanía | `capitalizer_cognitive_pressure.py`, `capitalizer_decision_sovereignty.py` | PASS/WAIT/ABSTAIN transparentes; jamás tamaño de riesgo propio |
| HF cognition | `capitalizer_v50_cognitive_hf_bridge.py`, `capitalizer_v50_master_cognitive_adapter.py` | Cada señal H1/M15/M1 se evalúa sin resultados terminales; reportar disposiciones |
| Stop/target/geometry | `capitalizer_v50_target_stop_intelligence.py`, `capitalizer_v50_cognitive_geometry_specialist.py` | M1 confirmado e intacto dentro del M15; target H1 ya conocido; sin widening |
| Re-arm/lifecycle | V50-R / V53 / V54-A / V54-B | Misma tesis parental; capacidad y economics separados; lifecycle aislado |

**Riesgo de integración que requiere prueba explícita:** inventariar una clase cognitiva no demuestra que sus decisiones lleguen al replay ni que modifiquen la población admisible. Instrumentar un ledger `source_opportunity_id → cognitive_frame_evaluated → disposition → execution_geometry → competition → executed_or_wait`, con timestamps y motivos; comparar contra bypass deliberado. Identificar módulos sólo documentales o no invocados.

## 3. Auditoría causal (inspección de código)

`capitalizer_high_frequency_capacity_census_v49.py` implementa `_all_m15_setups` sobre un estado H1 persistente y `_earliest_m1_trigger` con dos familias **alternativas**, `LIQUIDITY_SWEEP_CISD` y `FVG_RETRACE_CISD`. `_portfolio_max3` mantiene cupo cronológico por sesión/fecha.

`capitalizer_v50_target_stop_intelligence.py:build_dual_invalidation` exige:
1. pivot M1 de tres barras confirmado antes/en decision;
2. lado correcto respecto de entrada;
3. stop M1 estrictamente dentro de la invalidación de tesis M15;
4. pivot no tocado/cruzado desde confirmación hasta entrada;
5. sin pivot íntegro, no existe stop ejecutable.

La revisión de código **no** reemplaza tests causales, conjuntos independientes ni matriz económica.

## 4. Secuencia experimental y autoridad

1. P0 CI/quality en GitHub hasta GREEN (Ruff/Mypy/pytest completos). No alterar R, stop, target, criterios de admisión ni session bucket.
2. Cerrar V50-R sólo capacidad/densidad 9/9; contar oportunidades originales, oportunidades M1 intentadas, READY de primera/later, invalidación y consumo MAX3.
3. V51 (2014–2016) en 9 mercados; *datos consumidos* por investigación, no fresh OOS.
4. V53: replay económico del re-arm, preservar tesis parental, medir winner count >=80% y winner-R >=90% contra baseline, y población suficiente.
5. V54-A: capacidad de pivote alternativo en misma entrada, **no** inferir PF de capacity.
6. V54-B: A/B de lifecycle en población congelada V50-G; no presentar ganador de 90 trades como estrategia certificable.
7. Integración A/B sin retune únicamente después de cerrar ensayos individuales y recibir visto bueno A2 sobre metodología.
8. Congelar candidato, documentar fingerprints; ejecutar validación externa/prospectiva y totalidad de Certification Standard V2.

## 5. Baselines y no-promoción

- V50-G corrected-core run `36788519476`: 90 operaciones, PF 1.53458998595, +26.12311835R, expectancy +0.29025687R, DD 9R. **RECHAZADO por el Owner como arquitectura final por densidad insuficiente**.
- No etiquetar como mejora si PF resulta de eliminar la mayor parte de las operaciones ganadoras.
- Gating numérico final: PF >=1.50 por era OOS; >=1.70 combinado; Sharpe >=1.50, Sortino >=2.00, DD <=10R, payoff >=1.20 (salvo excepción justificada), MC positive >=90%, p95 DD <=15R, postcost positive, winner count >=80%, winner-R >=90%.
- El recuento original de 1,332/año no es gate rígido; tampoco es aceptable el survivor de 90 trades.
- Falta medir payoffs/Sharpe/Sortino correctos, clustering, MAE/MFE, riesgo de costes, Monte Carlo, estabilidad, leakage y validación independiente/prospectiva.

## 6. Entregables para revisión cruzada

- Artefacto quality (cada workflow; SHA, run_id, conclusión y tests).
- Grafo real de llamadas cognitivas (no sólo clases existentes) y matriz de disposiciones por candidato.
- Ledger causal y análisis de fugas.
- Tabla por símbolo/sesión/era de PF, PnL en R, DD, edge, density, ganadores originales/preservados; coste realista.
- Comparación separada de V50-R / V53 / V54-A / V54-B sin cherry-picking.
- Solicitud escrita al A2 en #755 para validar cada trigger, re-arm, invalidez y ruta fuente. A2 debe devolver verdict MATCH/PARTIAL/CONFLICT/UNRESOLVED en el ledger.
- A1 revisa cualquier cambio propuesto por A2 por causalidad, density, loss recall y protección de edges.
- Conclusiones cruzadas quedan enlazadas en #754, #755 y PR #623.

**Estado actual: quality fixes comprometidos; VALIDACIÓN PENDIENTE. SIN CERTIFICACIÓN / SIN DEPLOYMENT.**

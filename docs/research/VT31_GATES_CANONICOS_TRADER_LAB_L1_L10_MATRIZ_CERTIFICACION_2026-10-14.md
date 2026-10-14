# VT31 — MATRIZ MAESTRA DE GATES OFICIALES QORE CORE · 2026-10-14

**Estado:** `NOT_CERTIFIED / NOT_DEMO_ELIGIBLE` · investigación documentada · sin MERGE a `main`, sin LIVE/REAL, VPS, FundedNext real, nuevas órdenes ni sizing propio de VT31. **Esta auditoría no concede ni simula certificación.**

## 1. Autoridad canónica y precedencia

1. [Issue #473 — QORE-TRADER-LAB-001](https://github.com/mezas3238-hue/qore-core/issues/473): **L1–L10** y obligación adicional de caracterización profunda, Operating/Non-Operating Envelope e hipótesis con *fresh holdout*.
2. [Documento canónico QORE-TRADER-LAB-001](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md): identidad de candidato, evidencia inmutable, secuencia de promoción.
3. **Código de autoridad ejecutable:** [`src/qore/infrastructure/trader_lab/lifecycle.py`](https://github.com/mezas3238-hue/qore-core/blob/main/src/qore/infrastructure/trader_lab/lifecycle.py) (`MANDATORY_STAGES` = 9 etapas); [`stage_evidence.py`](https://github.com/mezas3238-hue/qore-core/blob/main/src/qore/infrastructure/trader_lab/stage_evidence.py) (evidence kind y binding); [`promotion.py`](https://github.com/mezas3238-hue/qore-core/blob/main/src/qore/infrastructure/trader_lab/promotion.py) (requiere adicional `ECONOMIC_EVALUATION` para `DEMO_ELIGIBLE`).
4. [Issue #469 — DEMO económico](https://github.com/mezas3238-hue/qore-core/issues/469) y [#472 — fills y PnL](https://github.com/mezas3238-hue/qore-core/issues/472): métricas netas, atribución CIBO/trader, comparativo A/B y consentimiento semántico de datos.
5. [Issue #468 — certificación de entornos](https://github.com/mezas3238-hue/qore-core/issues/468): `LAB_CERTIFIED != DEMO_CERTIFIED != LIVE_AUTHORIZED`; autorización posterior en etapas A–F y Roof de producción separada.
6. **Gates específicos metodológicos VT31 M0–M7** / G3/Issue #897 e Issue #900 siguen siendo **requisitos técnicos complementarios**, no sustituyen los L1–L10; aprobar un ensayo M4/M5 no equivale a superar L2, L7 ni L10.
7. **Calidad de integración QORE:** [#473](https://github.com/mezas3238-hue/qore-core/issues/473) y [#468](https://github.com/mezas3238-hue/qore-core/issues/468): tests normales/adversariales, Ruff repositorio completo, mypy, pytest/coverage, freeze SHA, DeepSeek Expert + IA + DeepSeek Coder + IA + FINAL IA, revisión protegida y QG posterior. **CI parcial verde no demuestra esta cadena.**

## 2. Matriz obligatoria L1–L10 para una ÚNICA versión de VT31

| Gate oficial | Prueba exigida por #473 / código | Evidencia obtenida al 14-OCT-2026 | Dictamen |
|---|---|---|---|
| **L1 — METHODOLOGY FREEZE / RESEARCH** | especialidad, identidad/version exacta de Trader+config, fuente doctrinal, entradas/salidas y `TraderLabCandidateBinding` reproducible; freeze ANTES validación | PR #932–#935 preregs y formalizaciones parciales; ICT general y TTrades están en perfiles distintos; G3 r1.3 **no firmado**, TTrades OB/Breaker no atribuidos autoralmente; no se demostró candidata única frozen Trader Lab | **INCOMPLETE** |
| **L2 — REPLAY** | replay original completo, causal, sin lookahead, orden→ACK→fills→cierre cuando se afirma economía, hash y evidencia de run vinculada a candidata | 3Y NAS100 1.059.784 M1 verificados; censo de 775 días, 128 contextos COG, 119 primeros FVG QORE; son testigos **source-only, 0 trades / 0 ACK**; no replay integral de candidata L1 congelada | **INCOMPLETE** |
| **L3 — FAST_FORWARD** | equivalencia exacta accelerated-versus-normal en mismo motor/estado/secuencia `available_at`, factor y reproducibilidad sin fuga | Trader Lab dispone infraestructura acelerada, pero no existe evidencia de paridad de VT31 nuevo exact-version | **NOT_EVIDENCED** |
| **L4 — OOS** | partición realmente no usada para elegir método/parametría, freeze previo, resultados sin retuning; cambios tras analizarla requieren *fresh untouched holdout* | base 3Y ya consumida en investigación; no se conoce evaluación OOS válida para esta nueva versión TTrades | **BLOCKED / NOT_EVIDENCED** |
| **L5 — STRESS / ADVERSARIAL** | shock de volatilidad, spread/slippage, gaps, desconexión, stale/missing data, perturbaciones de secuencia, regímenes y periodos sin señal | 179/179 tests de familia metodológica y fuente en último run #38634407465 (DST, 9/10 pt, no future, FVG 11AM, secuencias ambiguas), **pero no estrés económico/operacional completo** | **PARTIAL** |
| **L6 — MONTE_CARLO** | experimento preinscrito: dependencia, semilla, número de simulaciones, costes y tolerancias; robustez y riesgo de ruina sobre trades reales simulados con evidencia | ningún MC válido sobre *fills netos* de este candidato, pues aún no existen trades/adjudicación | **NOT_RUN / BLOCKED** |
| **L7 — ECONOMIC EVALUATION** | resultado neto atribuible: PnL, expectancy, profit factor, win/loss, drawdown, fees/spread/slippage, tamaño de muestra/horizonte/regímenes; Sharpe/Sortino si semántica suficiente | 119 fuentes FVG: 61 `TOUCH_NOT_FILL`, 31 secuencias ambigüas same-M1 y 27 expiraciones; **0 órdenes/0 fills/0 PF-DD**. USTEC BID/ASK 30h sin homologación NAS100 ni 3Y/outside-window hasta 15:55 | **BLOCKED** |
| **L8 — RISK REVIEW** | autoridad Risk externa autenticada vinculada a versión/candidato y drawdown/cola/ruina, non-bypassable controls | no existe prueba válida de aprobación Risk del candidato exacto | **EXTERNAL_EVIDENCE_DEPENDENT** |
| **L9 — CIBO REVIEW** | evaluación CIBO de especialidad, régimen, deterioro y adecuación, con autoridad distinta de promoción | no existe dictamen autenticado CIBO sobre esta versión y su económico todavía desconocido; CIBO no puede promover por sí solo | **EXTERNAL_EVIDENCE_DEPENDENT** |
| **L10 — INDEPENDENT VALIDATION** | aprobador independiente autentica y comprueba TODO paquete y promoción a versión `DEMO_ELIGIBLE` | no se emitió aprobación independiente; además G3 exige dos firmas COG+OPS reales Issue #897, que están pendientes | **EXTERNAL_EVIDENCE_DEPENDENT** |

**Precisión contractual:** el código `TraderLabStage` tiene 9 etapas (RESEARCH, REPLAY, FAST_FORWARD, OOS, STRESS, MONTE_CARLO, RISK_REVIEW, CIBO_REVIEW, INDEPENDENT_VALIDATION). El Issue #473 usa diez etiquetas L1–L10 porque **L7 ECONOMIC EVALUATION es requisito adicional de promoción**, ver `promotion.py::evaluate_demo_eligibility(economic_evidence=...)`. **No omitir L7 porque no figure entre los 9 estados enumerados**. El `SPECIALIZATION` es un prerequisito del freeze L1.

## 3. Gates transversales de certificación profunda de Trader Lab

El [Issue #473](https://github.com/mezas3238-hue/qore-core/issues/473) también exige por candidata/version:
- *Competence map* por mercado, dirección, sesión, hora, regímenes y condiciones de volatilidad, con incertidumbre y muestra estadística.
- *Operating Envelope* y *Non-Operating Envelope*: situaciones de edge soportado, degradación, negativo y abstención, sin fabricar robustez.
- *Causal loss autopsy*, falsos negativos/no señales, motivos de abstención y conversión oportunidad→oferta→fill→salida.
- Estabilidad por segmentos cronológicos, drift, concentración de DD/pérdidas y robustez vecina de parámetros sin elegir el mejor vecino después.
- Evidencia original 3Y ya consumida: nuevos hallazgos son **exploratorios**. Cambios materiales generan **otra versión**, preregistro y nuevo *fresh previously unseen holdout* para afirmar capacidad validada.

**Estado transversal VT31:** `CHARACTERIZATION_INCOMPLETE`; la fuente M1 y conteos de densidad avanzaron, pero **no hay ledger neto** ni mapas de pérdidas/drawdown/posterior-regime; no se puede afirmar edge, Sharpe, Sortino ni certificación.

## 4. Métricas y umbrales cuantitativos

El programa #469 exige reporte neto de **expectancy, profit factor, max drawdown, win/loss, Sharpe/Sortino cuando suficientes, MAE/MFE donde existan, turnover, costes, desempeño por instrumento/regimen, Risk rejects, tamaño y periodo**, y benchmark A `TRADERS_RISK_ONLY` frente a B `CIBO_MANAGED_TRADERS_RISK` sobre **la misma cohorte/versiones**. Ninguna de estas estadísticas puede inferirse de contactos CE en OHLC.

**No se halló un suelo universal inmutable numérico de PF, Sharpe y Sortino dentro de la normativa canónica #473/#469 o `QORE-TRADER-LAB-001.md`.** Los umbrales/criterios deben ser versionados/preregistrados antes de mirar resultados; **no inventar `PF>=X` o `Sharpe>=Y` y no seleccionar números a posteriori**. Las referencias históricas del Issue #727 a objetivo ~450 operaciones /3 años y drawdown puro <=6R son objetivos específicos de su coordinación y deben comprobarse contra la **versión nueva**, no convierten 119 fuentes en trades ni sustituyen los criterios de promoción.

## 5. Evidencia disponible y límite causal de la ronda VT31

- [PR #932 M2 DOL ICT](https://github.com/mezas3238-hue/qore-core/pull/932) · [PR #933 productor COG TTrades](https://github.com/mezas3238-hue/qore-core/pull/933) · [PR #934 censo M1](https://github.com/mezas3238-hue/qore-core/pull/934) · [PR #935 M4/M5 FVG+path](https://github.com/mezas3238-hue/qore-core/pull/935). **Todas DRAFT y apiladas**; no merge autorizado.
- [CI fuente M4/M5 #38634407465](https://github.com/mezas3238-hue/qore-core/actions/runs/38634407465): **179/179 pruebas** en SHA `2c4c521e242ac44ed7cdfb7bb83e55ba5d062236`; **119 FVG fuente / 0 trades**, no se puede promulgar L2–L10 por tests unitarios.
- [PR #901 G5 USTEC BID/ASK](https://github.com/mezas3238-hue/qore-core/pull/901): **483.103 actualizaciones BID/ASK en 30h**, coincidencia high/low/close en 1800 M1 de fuente NAS100 con BID USTEC, 11 discrepancias OPEN y 2 quotes cruzadas; **contrato NAS100↔USTEC no homologado**, faltan cobertura multi-año y tiempo hasta 15:55. Fuente [Issue #857](https://github.com/mezas3238-hue/qore-core/issues/857), [#900](https://github.com/mezas3238-hue/qore-core/issues/900).
- [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897): doble firma COG y OPS **independientes**, sobre hash exacto G3 r1.3; una sola cuenta no puede fingir dos aprobadores. Además L8–L10 requieren autoridad gobernada verificable, no autodeclaraciones.
- **Metodología**: los 128 contextos y 119 FVG son **proxy QORE** inspirado en TTrades NYAM, no equivalen a doctrina completa de TTrades ni a fills. No mezclar con ICT-general #930 sin revisión.

## 6. Secuencia de continuidad que sí respeta todos los Gates

**Primero L1**: certificar por fuentes cada regla TTrades M1+H1, entradas FVG/OB/Breaker y stop/exit, fijar exacta versión `TraderLabCandidateBinding`, artefactos y parámetros, resolver G3 firma verdadera. Dejar #935 sólo como diagnóstico de origen y no usarlo como decisión económica.

**Después L2/L3**: implementar replay integral del modelo congelado con fuente/broker homologados y paridad Fast-Forward del mismo motor/orden causal; no asumir fills a CE de M1. Requiere QORE Risk/CIBO/QDLE únicamente dentro de sus responsabilidades, trader **sin sizing propio**.

**Luego L4/L5/L6/L7**: usar OOS realmente intocado (sin reutilizar las velas analizadas), stress completo, MC preregistrado y evaluación económica de fills netos sin mentir sobre 31 same-M1 conflictos ni spreads; si el escenario económico no es identificable, dictamen explícito `INSUFFICIENT_EVIDENCE` / `BLOCKED`, no PASS.

**Finalmente L8/L9/L10**: auditores externos respectivos deben emitir evidencias autenticadas Risk, CIBO e Independiente para la misma versión e instrumentación. Comprobar calidad QG. Solo entonces el programa `promotion.py` podrá valorar `DEMO_ELIGIBLE` con `ECONOMIC_EVALUATION` válida.

**Después de `DEMO_ELIGIBLE` siguen Stage C DEMO CERTIFIED, Stage D LIVE READINESS, Stage E BOUNDED LIVE y Stage F EXPANSION del Issue #468.** Ni CERTIFIED Lab ni DEMO autorizan por sí mismos dinero real; **orden actual del Owner prohíbe LIVE / merge**.

**Resultado de esta auditoría: `VT31_OFFICIAL_TRADER_LAB_GATES_UNSATISFIED`, sin autorizar ejecución; tareas verificables y responsables de evidencia identificados, no certificación otorgada.**

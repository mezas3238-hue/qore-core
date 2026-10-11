# Trader Scalper — A2 V49 → V50-G causal admission waterfall, research-only

**Fecha:** 2026-10-10 | **Responsable:** Architect B / Metodología, PR #759, issue #757  
**Coordinación cognitiva:** Architect A, PR #758, issue #756; parent PR #623.  
**Estado:** implemented and fixture-CI validated, **NOT run on nine-market historical data**, **NOT CERTIFIED**, GitHub-only, NO VPS/LIVE/merge.

## 1. Qué se ha construido

- Módulo ejecutable: `src/qore/infrastructure/trader_lab/capitalizer_scalper_v49_v50_g_waterfall_v1.py`, commit inicial `45569528e6b69f531413affaadb605deee6c79ca`.
- Pruebas fail-closed con **datos de prueba sintéticos**, nunca interpretados como un replay: `tests/infrastructure/trader_lab/test_capitalizer_scalper_v49_v50_g_waterfall_v1.py`, commit inicial `f82b99ebdad523e0b4ec3cc02a223060c6456d0b`.
- Integrado a la CI branch-only `.github/workflows/qore-scalper-methodology-audit.yml`, commit `d3eda5cf09c52a3bb01093619262b5aa8762c9b3`.
- Correcciones de estilo Ruff en B: `59d8a903f8d775a2bea62009a3969ca0d0e17a13` y `98eff5bc301a52706a634445c86057285dd8f9db`.
- **GitHub Actions verificó:** [run 38052164023](https://github.com/mezas3238-hue/qore-core/actions/runs/38052164023) HEAD `98eff5bc301a52706a634445c86057285dd8f9db`: methodology_quality **SUCCESS**, full_quality **SUCCESS**; Ruff repo, Mypy src/tests, pytest regresiones metodología y V53/V54 **PASS**.

## 2. Fuentes de datos necesarias (no suministradas por el repo)

Para medir el resultado verdadero, el CLI necesita **9 ficheros de oportunidades V49, 9 informes de mercado V50-G, 9 ledgers de trades V50-G y 9 trazas cognitivas V50-G de A1** (una traza por oportunidad, incluidas las rechazadas por geometría). El Git tree del HEAD B no contiene los ficheros brutos históricos M1, esos artefactos V49 o los ledgers/trace V50-G de nueve mercados. Se debe ejecutar el pipeline sobre los artefactos históricos canónicos dentro de un GitHub Actions job autorizado con los datasets disponibles, jamás inventar denominadores ni repetir una muestra ficticia.

V50-G/trace fueron instrumentados **en PR #758**, rama independiente, por A1. Este lector A2 es independiente y **no modifica** ningún gate de V50-G ni la cognitiva de A1. La paridad entre source-ID A2 y A1 se fija por las doce propiedades ya observables de la oportunidad; explícitamente excluye `h1_state_until` por el riesgo de mirar una expiración H1 futura.

## 3. Waterfall lógico, con denominadores

Cada mercado produce:

| Etapa | Denominador/cálculo | Atribución |
|---|---|---|
| SOURCE | Número exacto de eventos V49 | No debe colapsarse con MAX3 |
| GEOMETRY_READY | `geometry_decision == READY` | Atribuye rechazos a causas geométricas observadas, no a “MSS+FVG+OB” inexistentes en ese grafo |
| COGNITIVE_ALLOWED_WHEN_READY | Subconjunto READY con `policy_cognitive_geometry_eligible` de la traza A1 | Razones cognitivas que ocurren **después** de que geometría esté READY |
| EXECUTABLE_BY_POLICY_BEFORE_MAX3 | Trades en libro V50-G por política | Falta de velas de sesión y/o política; cotejo con `missing_session_bars` exacto |
| EXECUTABLE_BY_POLICY_AFTER_MAX3 | Reproducción determinista de `_portfolio` V50-G sobre TODOS los libros de nueve mercados | Cuantifica recorte inter-mercados de MAX3 sin afirmar que ese límite sea del autor |
| WINNER_DENSITY / ECONOMICS | **No calculado por este auditor** | Reservado a replay económico neto con bid/ask, comisiones, igualdad de ID y perfiles de ejecución |

No sustraer recuentos de `cognitive_dispositions` marginales del recuento geométrico: son dimensiones superpuestas. Solo el **join por source ID** da el subconjunto causal READY∩COGNITIVE_ALLOWED. La salida separa `geometry_reason_occurrences` de `bridge_reason_occurrences_on_geometry_ready`; son ocurrencias de motivos, no oportunidades disjuntas.

## 4. Identidad y seguridad causal

- Utiliza la misma huella SHA-256 de A1 `source_opportunity_id` derivada de símbolo/sesión/día, activación y base H1, setup M15, disparador M1, precio de decisión, swing protegido y target H1.
- Verifica `source_h1_from <= source_m15_confirmed_at <= source_m1_confirmed_at == observed_at`, timestamps tz-aware, matches de mercado/sesión/familia, conjunto idéntico de identidades y trazas por cada fuente.
- Falla en **fuente duplicada**, A1 trace missing, source ID ajeno, report/ledger/trace inconsistentes, conteo erróneo, afirmaciones de Master Frame que V50-G jamás ejecutó, hindsight visible al candidato o bandera cognitiva que acepta algo geométricamente rechazado.
- Nunca escribe `h1_state_until`, trade exit/outcome, R realizado ni ningún campo de conocimiento futuro en la salida por oportunidad. No debe utilizarse `source_opportunity_id` para unir a otro estado con metadata prospectiva como si fuese observable.
- Modo defecto exige las trazas A1; `--allow-report-only` permite conteos globales legacy pero marca cobertura falsa y motivos no adjudicables. Nunca se permite report-only como certificación causal de WHY.
- Aplica de forma determinista el MAX3 **global por (session, operating_date)** a los trades hipotéticos ya simulados, por cada política, y compara antes/después sin modificar la capacidad source.

## 5. Ejecución reproducible — solo cuando existan ledgers reales

```bash
python -m qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 \
  path/to/v49/capacity-ledgers \
  path/to/v50-g/market-reports-trades-traces \
  path/to/output/waterfall
```

Genera `scalper-v49-v50-g-waterfall.json` con 9 mercados y `scalper-v49-v50-g-source-gates.jsonl` con una fila causal/WHY por oportunidad. En ausencia de los datos no intenta generar JSON falsamente representativo.

## 6. Resultados hasta el momento y obligaciones futuras

**Demostrado:** el módulo reconcilia fuente → geometría → cognitiva → libro por política → MAX3 en pruebas sintéticas con identidades individuales, motivos, paridad aritmética, rechazo de leaks e inconsistencias. CI completa repo en verde.

**NO demostrado:** cantidades verdaderas 9/9, causa económica de los históricos 90 trades, pérdida precisa de ganadores, R y PF / DD corregidos, tasas por mercado/sesión, memory/World Model/Master Frame en directo, rentabilidad con costes o autor-fidelidad íntegra.

**P0 A1+A2 siguiente:** obtener de GitHub Actions o un dataset aprobado las nueve fuentes V49 y los 9 market outputs/trace V50-G del **mismo código/dataset/periodo**; verificar SOURCE_ID parity, numeradores y denominadores por familia; hacer replay completo con precios cerrados, spread, comisiones y stops. El A1 frame real + memoria prequential y 9-market synchronizer es otro brazo preregistrado; no confundir la traza parcial V50-G con el Master Frame. Mantener el objetivo de preservación ≥80% ganadores y ≥90% realized winner R, densidad HF y DD ≤6R Owner, sin retunar admisión para fabricar PF.

**Frontera:** replay AUDIT ONLY; NO source changes, no sizing, no costos inventados, NO LIVE / VPS / fusionar PRs. 

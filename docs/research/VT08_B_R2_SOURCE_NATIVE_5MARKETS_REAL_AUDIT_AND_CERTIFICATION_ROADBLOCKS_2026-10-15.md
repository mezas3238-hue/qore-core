# QORE CORE — VT08 Arquitecto B, R2: pruebas de admisión cognitiva + fuente M3/M15 real
**Fecha:** 2026-10-15 | **Rama:** `agent/vt08-5m-cognition-replay-20261010` | **PR:** #764 DRAFT | **Coordinación:** A issue #762 / B issue #763 | **No merge / sizing / VPS / LIVE / 7Y sellado**.

## I. Resultado EJECUTADO (no solo plan)
1. **P0 anti-bypass cognitivo:** gate B default rechaza `evaluate(situation)` sin provenance. `fixture_mode=True` habilita **solo** simulación sintética (separada de `evaluate_provenanced`). Los accesos directos `record_fill/record_terminal/evaluate_position` default rechazan creación de eventos económicos sin interfaces independientes verificadas. La ruta fixture no autoriza órdenes ni cantidades. Commits `939030ca...`, `1bcb4576...`, `cbf7aa84...`; regresión CI [#38708938183](https://github.com/mezas3238-hue/qore-core/actions/runs/38708938183): **208 passed, 3 skipped, 3 A-frozen passed**, Ruff/Mypy PASS.
2. **P0 separación SOURCE vs QORE:** `inspect_architect_a_candidate` bloquea `A_B:NON_SOURCE_CONTAINMENT_BUNDLE` si `entry_basis/stop_basis/target_basis/filled_lifecycle` están ausentes, UNVERIFIED o contienen `QORE_CONTAINMENT`; el antiguo B01 contenía H4_OPEN exact, PS-only stop, 2R target, next H4 lifecycle (contenciones, NO fuente autor completa). Pruebas adversariales comprueban que ni SHA ficticio puede promoverlos. CI [#38709747707](https://github.com/mezas3238-hue/qore-core/actions/runs/38709747707): **226 passed, 3 skipped** + **3 A-frozen passed**, Ruff PASS, Mypy PASS (14 módulos).
3. **P0 auditoría B sobre DATOS REALES nativos:** A publicó recibos derivados de raw cTrader M3+M15 en [run #38709570234](https://github.com/mezas3238-hue/qore-core/actions/runs/38709570234), code SHA `a63fc1618e4cd8c3a3358aa8cd43a93e4fb06b23`. B implementó verificador **INDEPENDIENTE sin importar código A**: `src/qore/infrastructure/trader_lab/vt08_5m_b_independent_raw_receipts_v1.py`; 14 tests adversariales propios; código de QA real `.github/workflows/vt08-b-independent-native-raw-receipt-audit.yml`.
4. **B leyó raws físicos originales (sin estrategia/PNL):** M15 original Actions [#35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907) y M3 original [#35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396), artefactos descargados por la CI B. Re-hashea los archivos reales completos, vuelve a parsear barras de cada muestra, comprueba SHA del bar, perfil y orden, igualdad OHLC M3/M15→M30, relojes NY/UTC/available_at, no hay señales/fills/PNL falsos.
5. **CI REAL B [#38710007621](https://github.com/mezas3238-hue/qore-core/actions/runs/38710007621) — SUCCESS 5/5:** EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD; **24 ventanas auténticas de muestra por mercado**, **120 ventanas totales**, **1.200 barras M3 + 240 barras M15** contra los originales. Los **14 tests** y Ruff/Mypy pasan en cada uno de los cinco jobs. [CI optimizada posterior #38710263808](https://github.com/mezas3238-hue/qore-core/actions/runs/38710263808) SUCCESS 5/5 con cache de parse por SHA real, sin relajar digest.
6. **Censo A que NO es cobertura B total:** cada mercado reclama **2.330 anchor windows observadas**, completitud 2.328 en EURJPY/USDCHF/CADJPY/USDCAD y 2.327 en NZDUSD, 2 o 3 incompletas reales respectivamente. B validó específicamente 24 recibos/mercado y la custodia de archivos; **NO afirma que los otros ~2.300 recibos/mercado hayan sido re-verificados bar a bar**. Por tanto no convertir el censo A de 11.650 anchors observadas ni 11.639 completas alegadas en trades, source-complete, ni cifras auditadas exhaustivas por B.
7. **Registro de fallos CI no omitidos:** CI previa #38709909362 falló Mypy sobre `object` iterable, reparado y vuelta a ejecutar con datos reales; se corrigió sin cambiar outcome. Otros errores previos fueron formateo Ruff. El número de tests no significa PnL ni fuente metodológica validada.

## II. Evidencia y alcance EXACTO de cada resultado
| Frente | Evidencia B | Resultado real | Límite |
|---|---|---|---|
| Ingreso sintético vs real | `evaluate` requiere fixture_mode; `evaluate_provenanced` solo ruta real | anti-bypass comprobado | Manifest A/B REAL = None |
| No maquillaje SOURCE | `A_B:NON_SOURCE_CONTAINMENT_BUNDLE` | rechazadas reglas QORE como TTrades fuente | A aún debe adjudicar texto fuente D y entregar bundle |
| M3/M15 raw → 24 receipts x 5 | GH run B #38710007621 y #38710263808 | **5/5 PASS** | 120 ventanas, no censo total, sin método, broker ni PnL |
| Cognitiva con fuente REAL | Esperando A CandidateEvents, 27+ fields, raw semántico | **0** source-auth admitted | tests fixture 226 verdes NO llenan el vacío |
| Economía | BID/ASK bid/ask, fees, fill/terminal y gates temporales | **NO MEDIDA** para VT08 A+B | sizing PROHIBIDO |
| 7Y OOS | Sin abrir | Custodia mantenida | ningún holdout evaluado ni optimizado |

## III. Hallazgos relevantes contra A
El contrato A B01 puede declarar `methodology_status=SOURCE_COMPLETE_EXECUTABLE` pese a usar `H4_OPEN_EXACT_FILL_QORE_CONTAINMENT`, `PROTECTED_SWING_NO_OFFSET_QORE_CONTAINMENT`, `FIXED_2R_QORE_CONTAINMENT`, `CLOSE_NEXT_H4_QORE_CONTAINMENT`. B ahora rechaza esa inconsistencia **aunque en futuro se ponga un hash de manifiesto**.

La auditoría de raws permite avanzar hacia valores de `source_bar_id` auténticos. **A no debe promover 24 ventanas intactas ni las 11.639 completas del censo a patrones TTrades, POIs relevantes o fills**. Además falta una especificación traducible para relevant swing PRE C2, POI/tiebreak, breaker-low, target untouched y EQ régimen sin lookahead. Un verificador ciego no puede inferir relevancia cualitativa de diez barras OHLC.

## IV. Trabajos de Arquitecto B que siguen abiertos, por dependencia
1. **Field-binding verdadero** para cada uno de CAUSAL_FIELDS, con raw bar_id, sha, semantic source authority y availability; cotejar Situation values contra raws, no solo timestamps. Falta CandidateEvent válido de A.
2. **Relojes/M3 fuente autor y revision ciega B**, nunca usar código A como oráculo de metodología. SOURCE_A genuino requiere ejemplos primarios y revisión a dos firmas.
3. **WAL durable/idempotencia/concurrencia/restart:** no implementado en este corte. RAM research ledger no es production grade. Durante esta ronda se eligió cerrar anti-bypass primero.
4. **Cognitive behavior end-to-end** sobre cada auténtico candidate → WAIT/ABSTAIN/EXECUTE → fill físico → cada barra in-trade → terminal externo. El default de fill/position queda deliberadamente bloqueado hasta que exista un ingreso externo autenticable (evita introducir fills falsos).
5. **Científico C/Trader Lab:** same candidates, A-only vs A+B, BID/ASK histórico, fees y stop-first sólo como sensibilidad cuando OHLC no puede decidir orden; returns netos en R iguales, PF/DD/Sharpe/Sortino, OOS/MC/WFO/stress. No usar sizing, lotaje, leverage, compounding o CIBO para aprobar.
6. **Gates Owner por versión:** legado VT08 PF>=1.80, DD<=6R, MC p95<=15R y P(terminal positivo)>=0.90 vs ensayo #787 cerrado PFnet>1.15/100 fills, sin trasladar a nuevos Gates sin acta. Congelar umbrales Sharpe, Sortino, densidad y DD% antes del OOS; no importar QORE-alpha.

## V. Dictamen técnico correcto
**Verificado:** infraestructura cognitiva sintética refuerza anti-bypass; datos RAW M3/M15 contrastados por B en 120 ventanas, 5/5 PASS. `APPROVED_A_B_MANIFEST_SHA256=None` permanece. **No certificado:** metodología fuente, cognitiva con eventos fuente auténticos ni rentabilidad. No existe razonamiento científico que permita concluir edge desde 120 muestras de barras.

No hay merge, no VPS, no producción, DEMO ni LIVE, no lectura del holdout 7Y, no sizing. Las mejoras se custodian exclusivamente en PR #764 y la coordinación A/B se mantiene por issues.

# QORE-alpha V1 — ADENDA DE HANDOFF MAESTRO: GATES OFICIALES DE CERTIFICACIÓN DE QORE CORE

**Fecha de corte:** 14 de octubre de 2026. **Repositorio fuente de verdad:** `mezas3238-hue/qore-core`. **Rama:** `research/qore-alpha-96-frozen-20261011`; [PR #797](https://github.com/mezas3238-hue/qore-core/pull/797) DRAFT/UNMERGED; [issue #798](https://github.com/mezas3238-hue/qore-core/issues/798). **Destinatario:** arquitecto sucesor / auditor de certificación. **Uso:** investigación, sin merge, VPS, LIVE, cuenta real ni acceso al holdout sellado 7Y. No usar lotaje/sizing del Trader para conseguir rentabilidad: el dimensionamiento de volumen corresponde a la autoridad CIBO/QDLE aguas abajo, por separado. El análisis económico del Trader puede utilizar unidad fija 1R/riesgo de referencia declarado para expresar DD, pero NO optimizar lotes/capital por Trader como estrategia.

**Rectificación explícita solicitada por el Owner:** El screening de `96 variantes` y sus umbrales PF/DD/WR es **sólo la puerta de descubrimiento científico QORE-alpha**. **NO ES la certificación de QORE Core.** Un candidato que pase Train/Validate/Test/Paper sigue sometido a los gates del **Trader Lab**, revisión económica completa (incluyendo **Profit Factor, Max Drawdown, Sharpe, Sortino**, cuando sean estadísticamente significativos), OOS virgen, stress, Monte Carlo, Risk, CIBO, validación independiente, certificación DEMO y autorizaciones externas. No declarar al Trader `CERTIFIED` por un PF favorable, por CI verde, por un resumen o por pasar los 96.

## 1. Jerarquía de autoridad — documentación y código VERIFICADOS en GitHub

1. **[Issue #473 — QORE-TRADER-LAB-001](https://github.com/mezas3238-hue/qore-core/issues/473)**: regula `RESEARCH→REPLAY/BACKTEST→FAST_FORWARD→OOS→STRESS/ADVERSARIAL→MONTE_CARLO→ECONOMIC_EVALUATION→RISK_REVIEW→CIBO_REVIEW→INDEPENDENT_VALIDATION`. Explicita no-seed-hunting, ausencia de futuro, selección/OOS, Monte Carlo obligatorio, economía neta con costes y `INSUFFICIENT_EVIDENCE` para poca muestra. **Después de la selección por investigación exige un holdout genuinamente nuevo**; un OOS ya consumido para caracterización NO vuelve a ser evidencia virgen.
2. **[Issue #469 — QORE-DEMO-PROFITABILITY-MVP-001](https://github.com/mezas3238-hue/qore-core/issues/469)**, `Phase 7/8`: evidencia de PnL realizado/no realizado, spread, comisión/fees, slippage, carry cuando aplique, notional/exposición, equity y DD, atribución Trader/CIBO. **Métricas mínimas explícitas:** PnL NETO, expectativa por operación, Profit Factor, distribución win/loss, Max Drawdown, **Sharpe y Sortino cuando sean estadísticamente significativos**, MAE/MFE cuando disponibles, rotación/cost drag, estabilidad por Trader, instrumento y régimen, rechazos Risk/causas, degradación de slippage, tamaño muestral y horizonte. **Benchmark A/B obligatorio:** `TRADERS_RISK_ONLY` contra `CIBO_MANAGED_TRADERS_RISK` para mismas versiones/configs; medir aporte de CIBO, no atribuirle edge no demostrado.
3. **[Issue #468 — QORE-TRADER-LAB-CIBO-CERTIFICATION-001](https://github.com/mezas3238-hue/qore-core/issues/468)**: fases `LAB TRAINING→LAB CERTIFIED→DEMO CERTIFIED→LIVE READINESS GATE→LIMITED LIVE AUTHORIZATION→EVIDENCE-BASED EXPANSION`; disciplina explícita `LAB_CERTIFIED != DEMO_CERTIFIED != LIVE_AUTHORIZED`. Para LAB/DEMO exige identidad y versión exactas, adherencia a reglas Risk, protección stop, drawdown, modo degradado, reconciliación, violaciones, historial de remediaciones, rendimiento con procedencia y firma de autoridad. LIVE separado con kill switch, idempotencia, límites, account/provider binding, logs y certificación externa.
4. **[docs/architecture/QORE-TRADER-LAB-001.md](../../docs/architecture/QORE-TRADER-LAB-001.md)**: `CODE_GREEN != DEMO_ELIGIBLE`, `BACKTEST_PROFITABLE != DEMO_ELIGIBLE`. La secuencia requerida se implementa en `src/qore/infrastructure/trader_lab/lifecycle.py`, `promotion.py` y `governed_gate.py`; las pruebas localmente falsificadas o un booleano `APPROVED` de texto NO sustituyen pruebas emitidas por la autoridad externa Risk/CIBO/Independent Validation.
5. **Cálculo QORE ya disponible**:
   - `src/qore/infrastructure/research_periodic_sharpe.py`: Sharpe **por periodo**, tasa libre de riesgo en el mismo periodo, **sin anualización automática**.
   - `src/qore/infrastructure/research_periodic_sortino.py`: Sortino por periodo y **MAR** explícito, sin inflación automática por anualización.
   - `src/qore/infrastructure/research_periodic_hac_sharpe.py` y `research_periodic_hac_risk.py`: evidencia de Sharpe/volatilidad ajustada por dependencia temporal; no convertir tests descriptivos en p-values sin protocolo.
   - `src/qore/infrastructure/trader_lab/robustness.py`: Monte Carlo con semillas, familias y umbrales fijados por anticipado; no inventa edge.
   - `src/qore/infrastructure/trader_lab/economic_binding.py`: `ECONOMIC_EVALUATION` ligado a instrumento/candidato/lineage, no promoción unilateral.

**ATENCIÓN, umbrales numéricos oficiales:** En las autoridades normativas citadas **#468, #469, #473 y QORE-TRADER-LAB-001** confirmé explícitamente qué métricas y etapas son obligatorias, **pero NO localicé allí una tabla institucional universal que imponga un valor numérico mínimo de Sharpe/Sortino/PF para cada Trader**. No atribuir a esas fuentes valores inventados (p.ej. `Sharpe>=1.5`, `Sortino>=2`, `PF>=1.5`) ni declarar CERTIFIED hasta que el próximo arquitecto identifique **ruta exacta, commit, órgano firmante y versión** de la política numérica aplicable. Si existe en otro issue/rama de GitHub, **leerla, citarla y respetarla**; no rebajarla al umbral de screening. El riesgo/broker puede imponer DD distinto: la regla de screening `DD<20%` **NO reemplaza** los límites de certificación de cuenta/Trader/portafolio.

## 2. Matriz operativa — qué está y qué falta para certificación QORE-alpha

| Dimensión / evidencia | Screening v1 de 96 | Certificación Core y estado actual |
|---|---|---|
| Identidad exacta, versiones, SHA | Manifest `QALPHA-V001…V096` congelado con SHA contenido `4332e07f4a8fbdf1125ecd004a70c4216b8ea1a60e954847eedfe3b362184891` | **PENDIENTE** elegir 1 candidato, emitir binding Trader Lab, firma y trazabilidad de cada etapa |
| Profit Factor | Train bruto `>1.40`; Validate bruto `>1.30`; test interno bruto `>=1.20`; paper neto `>1.20` | **SIN MEDIR.** Certificación exige PF **NETO verificable**, además del umbral específico gobernado, si existe. Screening no acredita mínimo oficial |
| Máximo Drawdown | `<20%` en Train/Validate, con política de riesgo `0.1%` simulada para cálculo DD | **SIN MEDIR.** Exige DD en equity con capital y horizonte declarados, controles de simultaneidad y estrés/tail. No confundir drawdown en R con porcentaje. No habilitar al Trader a cambiar lotes |
| Sharpe | No gate numérico del screening 96 | **PENDIENTE.** Producir retornos de equity con frecuencia explícita, tasa sin riesgo, medición neta, N/IC y dependencia; si muestra no soporta cifra, emitir `INSUFFICIENT_EVIDENCE` |
| Sortino | No gate numérico del screening 96 | **PENDIENTE.** Producir sobre misma periodicidad con MAR explícito; no computar Sharpe/Sortino sobre señales geométricas ni simular capital de CIBO |
| Expectancy, WR, trades, costes | N Train>=50, Validate>=25, `|WR_tr-WR_val|<=15pp` | **PENDIENTE.** Net expectancy, distribución ganancias/pérdidas, sesgo de no-fill, BID/ASK real o conservador con procedencia, slippage, comisiones, persistencia y estabilidad por régimen |
| Robustez y dependencia | Evitar 97ª y no overfit, 1 winner | **PENDIENTE.** Replay, fast forward, OOS virgen, stress, Monte Carlo preregistrado; múltiples pruebas 96 no se corrigen estadísticamente solo elevando PF |
| Datos ejecución | M5 2022/23 de 5 mercados 5/5 SHA verificados | **BLOQUEADO** M1/M3 genuino antes 2023-09 para los cinco y costes BID/ASK/fees; M5 no genera M3 exacta |
| Benchmark CIBO | No forma parte de screening bruto del método | **PENDIENTE.** A: Trader+Risk; B: mismas versiones Trader+Risk+CIBO; separar contribuciones. Riesgo/lotaje CIBO/QDLE, no optimización a cargo del Trader |
| Verificación externa | Contratos local CI PASS, manifest congelado | **PENDIENTE.** Evidencia auténtica emitida por Risk, CIBO, validador independiente y pruebas trader demo operacional |
| LIVE/real | Paper prospectivo 3 meses requisito adicional de propuesta v1 | **NO AUTORIZADO.** Paper y LAB/DEMO no conceden por sí mismos permiso LIVE o VPS ni capital |

### Obligación de reportar todas las métricas por cada una de las fases válidas

Una vez que EXISTAN fills/costes, registrar una hoja económica inmutable por candidato y partición que incluya: `run_id, candidate_version, config_sha, source_data_sha, execution_feed_sha, instrument, segment, sample_start/end, observation_frequency, trade_count, fill_count, no_fill_count, gross_pnl, net_pnl, spread, commissions, slippage, net_profit_factor, max_drawdown_pct, max_drawdown_R, sharpe_per_period, sortino_per_period, sharpe_policy, sortino_MAR, N/insufficient_reason, expectancy_net_R, win_rate, gross_profit, gross_loss, MAE_MFE, turnover, tail_stress, monte_carlo_receipt, OOS_freshness, reviewer, gate_status, timestamp`. Campos numéricos sin fundamento deben ser **NULL+motivo**, NUNCA ceros inventados; ninguna cifra de test antiguo VT08 se presenta como PnL del candidato QORE-alpha.

El **punto de aprobación al Trader Lab** consume esas métricas MÁS firmas; no es correcto crear una función local `certify_if_pf`. CIBO administra riesgo/exposición; no se cambia la estrategia con `sizing` para fabricar un PF o salvar drawdown.

## 3. Qué tiene que hacer el próximo arquitecto (P0→P4)

**P0. Matriz normativa completa**: inspeccionar las ramas/issues de política de certificación hasta localizar los **límites NUMÉRICOS vigentes** de PF, DD, Sharpe y Sortino —si están definidos—, con ruta GitHub, commit, versión y autoridad que aplica a QORE-alpha. Crear expediente formal `OFFICIAL_TRADER_CERTIFICATION_THRESHOLDS_WITH_SOURCE`, nunca inferir mínimo de un ejemplo de test o de un escenario individual. Cualquier conflicto de límites se eleva a Risk/Owner, no se elige el favorable.

**P1. Datos**: continuar piloto Dukascopy M1 BID/ASK preregistrado el 2026-10-13 sobre `2022-01-04` para los cinco, sin resultado PnL. Verificar qué datos son fuente original y qué queda sin cubrir; M5 2022 5/5 ya está resuelto. No usar holdout reservado de VT08, no alterar cut de Train.

**P2. Motor económico exacto de 96**: solo después de M3/M1 autentico y coste documentado, construir runner determinista que emite fills causales y net PnL; usar Trader Lab/ultra-fast. Pruebas anti-leak, DST, broker side BID/ASK, abort por faltante, 97ª bloqueada. Freeze y hashes antes de ver outputs económicos.

**P3. Pipeline económico + robustez**: Train y Validate → un ganador → Test interno sellado hasta lock → paper prospectivo tres meses. Sobre candidato sobreviviente producir expediente PF net, DD, Sharpe, Sortino, expectativa, costos, OOS verdaderamente virgen, stress/Monte Carlo y resultado de dependencia/intervalos; pasar revisión Risk, CIBO, independiente. No seleccionar método con máximo Sharpe visto a posteriori: serían variantes añadidas no preregistradas.

**P4. Certificación / cierre**: documentar gate por gate `PASS/FAIL/INSUFFICIENT_EVIDENCE/NOT_RUN`, quien firma, y evidencia. Si ningún candidato cumple gate de screening → STOP estas 96 y no fingir certificación. Si sobrevive screening pero falla un gate Core → **TRADER NOT CERTIFIED**, independientemente del PF. En ningún caso activar LIVE/VPS/merge sin instrucción Owner.

## 4. Trazabilidad de esta adenda y documentación preexistente

Handoffs maestros que se mantienen **sin sobrescribir resultados congelados**:
- [QORE_ALPHA_V1_HANDOFF_MAESTRO_2026-10-13.md](QORE_ALPHA_V1_HANDOFF_MAESTRO_2026-10-13.md)
- [QORE_ALPHA_V1_HANDOFF_MAESTRO_ARQUITECTO_2026-10-13.md](QORE_ALPHA_V1_HANDOFF_MAESTRO_ARQUITECTO_2026-10-13.md)

**Contratos oficiales vivos:** [#469](https://github.com/mezas3238-hue/qore-core/issues/469) economía/Sharpe/Sortino/PF/DD y A/B; [#473](https://github.com/mezas3238-hue/qore-core/issues/473) Trader Lab OOS/stress/Monte Carlo; [#468](https://github.com/mezas3238-hue/qore-core/issues/468) LAB→DEMO→LIVE; [QORE-TRADER-LAB-001](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md) documentación implementada. Estas autoridades no se alteran por el preregistro cuantitativo v1.

**Veredicto al 14-oct-2026:** `M5_2022_2023_5/5_SHA_GREEN; M3_2022_AUTH_NOT_PROVEN; BID_ASK_FEES_NOT_PROVEN; 96_FROZEN; 0_OF_96_ECONOMICALLY_TESTED; CORE_CERTIFICATION_ZERO_OF_GATES_PASSED; NO_LIVE`. El estado `0_OF_96_ECONOMICALLY_TESTED` **no implica** `0_OF_96_PROFITABLE`. El último piloto Dukascopy estaba **prerregistrado y no aparece certificación de muestra en la presente rama**; verificar futuras Actions y PRs antes de afirmar su estado mundial.

**ÚNICO CRITERIO DE ÉXITO:** candidato con evidencia económica neta positiva/robusta y certificación QORE Core COMPLETA, no solo un resultado de screening. Sin fuente suficiente, entregar BLOQUEADO con evidencia exacta.

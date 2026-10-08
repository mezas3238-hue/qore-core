# QDLE P0 — INVALIDACIÓN DE CONCLUSIONES FINANCIERAS Y AUDITORÍA DE CÁLCULOS

**Prioridad:** P0; investigación y certificación RECHAZADA.
**Código fuente del reporte previo:** `scripts/qdle_3368_dual_ledger_replay.py`; replay [#37831818976](https://github.com/mezas3238-hue/qore-core/actions/runs/37831818976).
**Fuente:** 3.368 señales del manifiesto sellado 2019-07—2022-06, contratos MT5 capturados en octubre 2026.
**Autoridad de riesgo deseada:** `0.05 × capital económico causal QORE`, inicialmente USD3 sobre USD60; USD2.000 de broker solo para margen.

## Hallazgos reproducidos sobre escenario broker .01 / sin regla de proveedor confirmada

| Verificación | Resultado |
|---|---:|
| Señales | 3.368 |
| Propuestas con lotaje | 2.113 |
| Sin lote | 1.255 |
| Riesgo previsto para el stop >5% NAV QORE | 0 |
| **Pérdidas simuladas efectivas >5% NAV al abrir** | **272** |
| **Pérdidas simuladas >presupuesto total de stop + comisión inicial** | **777** |
| **Peor pérdida simulada individual como % del NAV al abrir** | **18,57%** |
| Excesos >5% asociados a resultado estructural R inferior a -1 | **272/272** |
| Comisiones iniciales Forex $7/lote que no cuadran | 0 |
| Propuestas NDX100 con comisión **DESCONOCIDA** modelada $0 | **306** |
| PnL neto research, obtenido de recibos estructurales no MT5 | -USD50,16 |
| Comisión de apertura modelada (total) | USD479,16 |
| Swaps modelados UTC no comprobados | -USD154,67 |
| Drawdown de NAV sobre cierres (sin MTM) | **97,53%** |

### Qué NO está mal, y qué SÍ lo está

El dimensionamiento de **riesgo inicial reservado** (no más de 5%) y la aritmética **USD7/lote de apertura Forex** se reconciliaron correctamente en el artefacto anterior. **Eso no valida el modelo financiero**: el replay emplea resultados `gross_structural_outcome_r` que llegan a pérdidas mayores que 1R y swaps/costes posteriores; se desborda el límite inicial en 272 resultados y el stop previsto en 777. No se puede prometer pérdida máxima real del 5% sin modelar ejecución, gaps, spread y slippage; tampoco puede inventarse truncamiento de pérdidas a -1R para maquillar el DD.

**Falla temporal de fuente:** el simulador vuelve a fechar observaciones MT5 de 2026 (`QDLESymbol.as_of`, `BrokerValuation.as_of`) como si provinieran del período 2019–2022. No se permite etiquetar ese flujo como snapshot de broker histórico/actual autenticado.

**Falla en los cuatro motores:** el replay inyecta `sizing_cap_usd=risk_budget` y `cibo_compound_cap_usd=risk_budget`; el presupuesto de Portafolio y margen de Leverage se calculan dentro del propio harness, no mediante decisiones autónomas del cuarteto. Por eso las cifras 1.953 de Sizing/Compuesto son empates de topes programados, **no aportaciones económicas independientes**. No cabe afirmar `ganancia de Sizing` ni `profit de CIBO Compuesto` antes de construir cuatro ablations causales.

**Tarifas/margen:** FX comisiones observadas USD7/lote en apertura, pero cierre no verificado; XAUUSD 0,0016% con base no comprobada; índice NDX100 sin comisión visible (se tomó cero); spreads flotantes sin datos cuantitativos; swaps aplicados con hora UTC no verificada. Margen de 2026 estático con cuenta USD2.000 no demuestra margen libre real de cada tick.

**Riesgo de la cuenta:** `broker_equity = 2000 + NAV_QORE - 60` ignora PnL flotante, eventual margen neteado y condiciones exactas del proveedor. Sin MTM no se mide peak-to-trough intratrade ni verdadero stopout. El DD cercano al 97,53% solo identifica que el experimento fracasa gravemente bajo sus supuestos, no un DD auténtico validado.

## Reparación inmediata aplicada al circuito de investigación

Se incorpora la rutina `scripts/qdle_3368_financial_truth_gate.py` a `.github/workflows/qdle-3368-dual-capital-replay.yml` para que cada escenario reporte: reservas, comisiones, exceso de presupuesto, discrepancias PnL y **`financial_certification: REJECTED`**, aun cuando las 3.368 entradas sean procesadas sin excepciones técnicas. Todo claim real de ganancias queda bloqueado hasta resolver los defectos.

**Siguientes acciones:** 1) captar señales y quotes actuales en modo solo lectura vía `qore-vps-control`; 2) extraer tarifas reales completas y `order_calc_profit/order_calc_margin` de MT5, más política específica FundedNext; 3) emitir cuatro decisiones económicas AUTÓNOMAS por `trade_id`, con ablation de cada una; 4) simular stop-loss, spread/slippage, margen/MTM/stopout y conciliación de todas las operaciones; 5) repetir y exigir DD 20–25% como meta de investigación, sin forzar ganancias.

**Control de seguridad:** PR #735 DRAFT. NO desplegar ni enviar `order_send` en cuenta FundedNext basado en esta simulación.

**Veredicto:** `AUDIT_INTEGRITY=PASS`, `FINANCIAL_CERTIFICATION=REJECTED`, `LIVE_TRADING_AUTHORIZATION=NO`.

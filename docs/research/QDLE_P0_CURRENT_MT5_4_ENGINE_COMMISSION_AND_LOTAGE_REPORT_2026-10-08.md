# QDLE P0 — INFORME COMISIONES, LOTAJE Y LOS 4 MOTORES CON FICHAS MT5 ACTUALES

> **P0 — INVALIDACIÓN DE CERTIFICACIÓN FINANCIERA (2026-10-08).** La auditoría posterior detectó **272/2113 pérdidas simuladas superiores al 5% del capital QORE inicial de la entrada**, 777 pérdidas superiores al stop reservado y 306 propuestas NDX100 con comisión desconocida representada como cero. Los cuatro motores NO se ejecutaron independientemente. **CI SUCCESS NO equivale a finanzas verificadas.** Ver [dictamen canónico](QDLE_P0_FINANCIAL_CALCULATION_INVALIDATION_AND_REPAIR_2026-10-08.md). No usar PnL, DD, ni bindings previos como certificación o resultados actuales de mercado.


**Fecha:** 2026-10-08.
**Referencia reproducible:** [QDLE 3368 Current-Contract Replay #37831818976](https://github.com/mezas3238-hue/qore-core/actions/runs/37831818976), SHA `3e86cbe563ad64c1ab85757a6f6b1cb9cc039e17`, CI **SUCCESS**, artefacto `qdle-3368-dual-capital-RESEARCH-37831818976` (3 reportes JSON completos).
**Código:** `scripts/qdle_3368_dual_ledger_replay.py` + kernel QDLE. PR #735 DRAFT, NO LIVE.

## Alcance preciso

- **Usar reglas de símbolo, lotes, margen, comisiones y swaps de las capturas MT5 de octubre 2026**. Las **3.368 señales históricas** se usan como geometrías/escenarios de ensayo, **no** se afirma haber simulado nuevos precios de mercado 2026 ni haber ejecutado 3.368 trades auténticos.
- **FundedNext MT5 broker** USD2.000 nominal inicial para estimación de margen. **Capital QORE** USD60 inicial; **5% dinámico sobre QORE**, no sobre USD2.000 del broker; un único presupuesto económico por entrada. QDLE cuantiza cada señal y reserva.
- **Cuatro módulos:** Sizing y CIBO Compuesto aportan el mismo tope 5% en el harness; Portafolio Compuesto aporta riesgo/fondos QORE no reservados; Adaptive Leverage permite lotes sujetos a margen disponible MT5 y máximo del símbolo. **No se conectó una secuencia de decisiones autónomas independientes de cada motor:** los contadores solo miden topes QDLE, NO contribución causal de PnL individual.
- Riesgo/stop monetario, margen aproximado, comisiones observadas e hipótesis de swaps se calculan **por operación**. Se registra binding/tie y no financiable; no se simula fill real.

## Símbolos y costes MT5 observados

| Símbolo | Contrato por lote | Mín / máx / step | Margen BUY USD / 0.01 aprox. | Comisión apertura |
| --- | ---: | --- | ---: | --- |
| AUDJPY | 100000 | .01/40/.01 | 23.19 | USD7/lote |
| EURUSD | 100000 | .01/40/.01 | 37.35 | USD7/lote |
| GBPJPY | 100000 | .01/40/.01 | 44.07 | USD7/lote |
| GBPUSD | 100000 | .01/40/.01 | 44.08 | USD7/lote |
| XAUUSD | 100 | .01/50/.01 | 536.37 | pantalla 0.0016% por lote (base no verificada; proxy % nocional) |
| NDX100 (NAS100) | 10 | .01/40/.01 | 614.82 | **no visible**, proxy coste cero *optimista* |

Comisión de cierre no establecida; spread flotante no observado; swaps de la pantalla de 2026 incluidos como sensibilidad con hora de rollover **UTC supuesta**, triples miércoles Forex/XAUUSD, viernes NDX100. No usar USD7/lote de Forex como coste universal.

## Resultado comparativo

| Métrica | Mínimo Trader + stress $120 | Broker .01 + stress $120 | Broker .01 + límite proveedor no probado |
| --- | ---: | ---: | ---: |
| Señales originales auditadas | 3368 | 3368 | 3368 |
| Propuestas de lote financiables QDLE research | **697** | **1628** | **2113** |
| No financiables / bloqueadas | 2671 | 1740 | 1255 |
| QORE NAV último evento (USD) | 5.50 | 125.05 **al corte** | 9.84 |
| PnL estructural neto proxy (USD) | -54.50 | +65.05 **no realizable tras breach** | -50.16 |
| Max DD sobre cierres únicamente | 92.86% | 87.75% | 97.53% |
| Comisiones apertura proxy USD | 93.87 | 380.97 | 479.16 |
| Swaps netos proxy USD | -25.88 | -127.45 | -154.67 |
| Salida simulada por proveedor | No | Sí, 2021-05-05 21:00 UTC | No modelado |

**Atención:** trailing USD120 es **escenario de estrés no verificado**, no regla afirmada de la cuenta real. Bajo ese supuesto, con broker .01 la cuenta queda detenida y **1.276 señales posteriores se bloquean**: QORE USD125.05 es únicamente contabilidad al evento de corte, NO saldo de liquidación. Sin una regla auténtica de proveedor, el caso sin limitador *tampoco* demuestra solvencia. DD intratrade no medido.

### Atribución medible a cada módulo (harness QDLE, no decisión independiente)

| Indicador | Trader + stress | Broker .01 + stress | Broker .01 sin regla |
| --- | ---: | ---: | ---: |
| Sizing: vincula con empate de límite 5% | 694 | 1494 | 1953 |
| CIBO Compuesto: vincula con el MISMO 5% | 694 | 1494 | 1953 |
| Adaptive Leverage: margen es vinculante en propuestas | 5 | 180 | 215 |
| Portafolio Compuesto: fondos fuente son vinculantes | 0 | 0 | 0 |

**Estos números no son ganancias generadas**. En casi todos los casos Sizing/CIBO Compuesto empatados con `REQUESTED_USD`; retirar uno de dos topes idénticos no permite atribuirle rentabilidad exclusiva. Portafolio entrega capacidad de fuente pero nunca es el limitador final; Adaptive Leverage restringe lotes por margen en cientos de eventos. Las ganancias individuales de cuatro motores **NO SON DETERMINABLES** sin decisiones autónomas y experimentos de ablación.

**Importante:** El artefacto precedente `four-engine-cooperation.json` en el paquete fuente reporta llamadas 3368 en cada módulo, cero bindings finales de Sizing y cero salidas activas de CIBO Compuesto, y que Portafolio/Leverage emitieron superficies idénticas en 3368 decisiones; **esa instrumentación pertenece al otro replay**, y NO equivale a contribución en dólares del actual.

## Valores por símbolo auditados

Cada JSON contiene 3368 decisiones con `four_engine_caps_usd`, `leverage_margin_budget_usd`, `leverage_max_lots`, `bound_modules`, `fees_entry_usd_proxy`, `swap_usd_proxy`, `realized_pnl_usd_proxy`, `stop_loss_usd_per_lot`, `planned_stop_usd`, `margin_usd`, `lots` y `reason`.

Para reporte por operación, descargar artefacto de run 37831818976 y agrupar por símbolo, trader y `bound_modules`. NO atribuir resultado R como fill MT5.

## Faltantes del informe definitivo de producción actual

1. **Tarifa NDX100** y base de comisión porcentual XAUUSD, cargos de cierre, precio Bid/Ask y slippage por señal.
2. **Saldo/equity/margen libre actuales VPS y reglas de la cuenta** verificados por fuente read-only, no foto de 2026 para asumir saldo corriente.
3. Capturar **decisiones independientes reales** de Sizing, CIBO Compuesto, Adaptive Leverage, Portafolio Compuesto en cada `trade_id` junto con reservas y PnL, y efectuar ablations 4x con mismas señales/costes.
4. Conciliación de fills, flotación intratrade y stopout con valores del terminal; QDLE es autoridad de lotaje y no envía órdenes.

**Veredicto:** el análisis de comisiones/lotaje/margen con fichas actuales de seis símbolos se hizo y tiene instrumento económico auditable, pero no hay base para prometer ganancias actuales ni atribuir profit a módulos que todavía no operan autónomamente en esta simulación. No activar LIVE.

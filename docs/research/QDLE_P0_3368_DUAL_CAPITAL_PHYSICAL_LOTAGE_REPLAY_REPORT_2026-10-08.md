# QDLE P0 — REPLAY 3.368 SEÑALES CON MOTOR REAL DE LOTAJE (INVESTIGACIÓN)

**Fecha:** 2026-10-08
**Workflow:** [QDLE 3368 Dual Capital Research Replay #37830200266](https://github.com/mezas3238-hue/qore-core/actions/runs/37830200266) — **SUCCESS**
**Código exact-SHA ensayado:** `5481bfd22cb9ec23f7953fc97f39a652ab03b313`
**Artefacto de informes completos:** GitHub Actions run #37830200266 → `qdle-3368-dual-capital-RESEARCH-37830200266`.
**Fuente causal fijada:** archivo GitHub artifact 11451743578, SHA-256 `d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`.
**Estado:** Investigación con costes observados 2026 y resultados R estructurales de archivo, **NO** replay de fills auténticos MT5 2019–2022, **NO CERTIFICADO**, **NO LIVE**.

## Misión y arquitectura realmente ejecutada

- **3.368/3.368** señales históricas únicas (2019-07 a 2022-06) sin descartes silenciosos.
- Capital económico QORE inicial USD **60** (base dinámica de riesgo) **SEPARADO** de USD **2.000** nominales de cuenta FundedNext (para margen). Por entrada, `risk_budget_usd = 0.05 * qore_trading_capital_usd`, con 5% constante y USD variables según NAV; no 5% de equity broker.
- **Motor QDLE central usado en CADA intento** mediante `QDLE.reserve_for_trader()`: stop monetario/lote, fee, margen broker por lote, min/max/step MT5, topes conjuntas de los cuatro módulos Sizing/CIBO Compuesto/Adaptive Leverage/Portafolio, reservas SQLite. Cuenta y símbolos por eventos causales.
- Las entradas se reordenaron según `settlement_outcome_research_only.entry_at`, distinto de `market_decision_at`; en especial, el NAS100 histórico tenía órdenes límite con retrasos. Se valora presupuesto **al tiempo de hipotética entrada**, sin usar R futuro para dimensionamiento. El R estructural se aplica solo al registro de salida, como proxy, **NO** fill MT5.
- Comisión Forex USD 7/lote **al abrir**, debitada al evento de entrada; XAUUSD 0,0016% modelada sobre nocional (base **no demostrada**), NDX100 comisión desconocida representada 0 (optimista). Swaps de fotografías MT5 de 2026, convertidos a USD mediante tick/valor por activo; horario de rollover asumido medianoche UTC, triple miércoles FX/oro y viernes NDX100. Las condiciones del bróker históricas son desconocidas.
- Hipótesis de pérdida máxima proveedor: **trailing USD 120** de equity cerrado broker desde máximo observado (sensibilidad del 6% inicial de USD 2.000, **programa y regla real no verificados**). **Detiene nuevas entradas tras la primera brecha**; no se permite generar ganancias de operaciones posteriores en una cuenta parada. No se recrea liquidación MTM intratrade: faltan ticks/precios/deals.

## Dos políticas de lotaje (simulación research)

| Métrica | Mínimo histórico del Trader | Mínimo broker 0.01 |
|---|---:|---:|
| 3.368 señales registradas | 3.368 | 3.368 |
| Propuestas de tamaño QDLE financiables (research) | **697** | **1.628** |
| Sin lote o bloqueadas después de stop | 2.671 | 1.740 |
| Capital interno QORE inicial | USD 60 | USD 60 |
| Capital QORE al cierre o **momento del stop** | **USD 5,50** | **USD 125,05** |
| PnL research sobre USD60 | **-USD54,50** | **+USD65,05** |
| Max DD medido **solo sobre capital cerrado** | **92,86%** | **87,75%** |
| Profit Factor de resultados research | **0,845** | **1,030** |
| Coste proxy comisiones al abrir | USD93,87 | USD380,97 |
| Swap neto proxy | -USD25,88 | -USD127,45 |
| Límite trailing proxy USD120 activado | **NO** | **SÍ** |
| Primera brecha detectada | — | **2021-05-05 21:00 UTC** |
| Señales siguientes BLOQUEADAS | 0 | **1.276** |
| Propuestas que tienen broker ticket REAL | **0** | **0** |

**ADVERTENCIA:** el `USD 125,05` del caso broker 0,01 es un valor de **capital económico modelado al DETENERSE el replay en el breach**; NO representa cuenta superviviente, fondos retirables, liquidación ni resultado a junio 2022. La cuenta hipotética se detiene prematuramente. El DD intratrade verdadero puede ser MAYOR que los DD reportados.

### Propuestas con lotaje por símbolo

| Activo | Señales | Trader mínimo | Broker 0,01 |
|---|---:|---:|---:|
| AUDJPY | 673 | 183 | 389 |
| EURUSD | 495 | 186 | 277 |
| GBPJPY | 618 | 138 | 270 |
| GBPUSD | 606 | 137 | 296 |
| XAUUSD | 492 | 53 | 149 |
| NAS100 histórico → NDX100 snapshot | 484 | 0 | 247 |

El histórico identifica NAS100 como `USTEC` y mínimo `0.1` lote; el contrato actual observado en MT5 indica `NDX100`, contrato 10 y mínimo `0.01`. **La equivalencia de ejecución NO está confirmada**. La diferencia explica parte del cambio de densidad entre políticas.

### Diagnóstico de bloqueos

- Mínimo del Trader: **2.646** sin lote por presupuesto de riesgo del 5% insuficiente; **25** por restricción de margen.
- Broker 0,01: **464** sin lote por 5% insuficiente; **1.276** bloqueadas automáticamente después del límite de proveedor estimado.
- Los contadores implican **NO FINANCIABLE/NO EJECUTADA**, no autorización para rechazarlas como señales cognitivas, ni registro ficticio 1x.

## Por qué NO puedo llamarlo broker-real completo aun con las capturas

1. Las pantallas tienen min/max/step, contrato, comisión mostrada, swaps y margen estimado a octubre de 2026. **No** aportan las cotizaciones Bid/Ask históricas del 2019–2022, comisiones de cierre, slippage, gaps, fill parcial, niveles de conversión ni margen de aquel periodo. El supuesto `order_calc_margin()` del pasado no se puede reconstruir exactamente con una foto actual.
2. El manifiesto solo aporta resultados estructurales R de laboratorio y horarios de entrada/salida research. **No** hay series tick/MTM ni confirmaciones auténticas de deals MT5.
3. Se desconoce el programa/reglamento específico de la cuenta FundedNext: el trailing USD120 es sensibilidad, no certificación del programa, y puede haber límites diarios o de pérdida flotante más estrictos.
4. XAUUSD (comisión 0,0016%) requiere base real del porcentaje; NDX100 carece de tarifa de comisión en captura. Estos costes quedan explícitamente NO CONFIRMADOS.
5. Los cuatro módulos económicos no aportan una serie independiente de decisiones históricas reales a este dataset; se aplican techos monetarios comunes al 5%, sin demostrar el valor marginal de cada uno.

## Veredicto y siguiente actividad P0

**QDLE integrado al replay y cuantizando cada intento: SÍ.** CI reproducible y 3.368/3.368 señales conservadas: SÍ. **Simulación MT5 histórico broker-exacta / 3.368 fills auténticos:** NO. **DD meta ideal ≤20%, tolerable ≤25%:** NO PASÓ.

Para lograr simulación tan realista como permita la evidencia: obtener desde `vps-vrix` vía `qore-vps-control` las especificaciones de servidor y las reglas del programa (lectura), y recuperar un histórico de Bid/Ask/ticks, comisiones de cierre, ejecución y precios para alimentar QDLE con valoraciones a cada evento, márgenes del momento, mark-to-market continuo, stopout efectivo y ledger PnL causal. No enviar `order_send` real ni fusionar PR DRAFT por este resultado.

**Archivo ejecutor:** `scripts/qdle_3368_dual_ledger_replay.py`. **Workflow:** `.github/workflows/qdle-3368-dual-capital-replay.yml`. **Rama:** `agent/qdle-independent-engine-p0-20261008-001` · **PR:** #735.

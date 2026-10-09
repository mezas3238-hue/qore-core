# Trader Lab — CIBO Native MAX → QDLE Stellar Instant → Market Atlas M5: replay 3.368
**Fecha:** 2026-10-09 · **Estado:** RESEARCH PAPER SUCCESS, NO CERTIFICACIÓN, NO LIVE.
**Ejecución:** [GitHub Actions #37949977967](https://github.com/mezas3238-hue/qore-core/actions/runs/37949977967) — SUCCESS
**Código base ensayado:** `ae84d4566d385aa24c56e595d3dbf2e586d87b63`
**Artefacto JSON con TODAS las decisiones y trades:** [#11626195451](https://github.com/mezas3238-hue/qore-core/actions/runs/37949977967/artifacts/11626195451), `trader-lab-cibo-qdle-spread-3368.json`.
**Ejecutor:** `scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py`
**Workflow:** `.github/workflows/cibo-trader-lab-native-qdle-market-atlas-3368.yml`.

## 0. ALCANCE CIENTÍFICO — no confundir MODELO con realidad

Este **SÍ ES un ensayo de gestión de posiciones con resultados financieros simulados**, no solo el cálculo de QDLE. CIBO Native MAX aporta el modo BANK/MEDIUM/ATTACK y la política de salida sellados; QDLE **actualizado** calcula lote físico por señal usando un NAV de caja mutable, fuente/reservas concurrentes, grid, comisión Stellar Instant y márgenes de investigación; el gestor paper evalúa cierres en **Market Atlas M5 2019–2022**. La investigación ejecuta 3.368 intenciones, no reproduce 3.368 fills reales.

**NO son P&L, profit factor, drawdown ni saldo broker reales de CIBO.** Las seis series son OHLC M5 de Market Atlas y NO conservan BID/ASK históricos observados por FundedNext. Al OHLC se inyectan spreads **CONSTANTES** vistos en dos capturas MT5 de octubre de 2026. La conversión JPY/USD usa un USDJPY fijo 158,337 de la captura 2026, NO tipos de cambio históricos. Se asume fill de papel en la primera apertura M5 hasta 5 minutos después de la señal, incluso para órdenes históricas LIMIT; no hay confirmación real de ejecución. Tampoco se reconstruyeron los swaps de la cuenta ni un mark-to-market completo de posiciones abiertas. Las 4 autorizaciones económicas son cotas de la evidencia de cuatro motores previa, reescaladas al NAV paper de cada señal; **no son nuevos cuatro votos cognitivos independientes hechos con ese NAV**. Esta distinción impide tratar el resultado como certificación de cartera FundedNext.

### Tarifas y spread asumidos (actualización QDLE, ninguna tarifa LEGACY)
| Instrumento | Spread observado puntual fijado en TODO el replay | Comisión Stellar Instant contabilizada |
|---|---:|---|
| AUDJPY | 0,014 JPY = 1,4 pips | $7 por lote al abrir, $0 cerrar |
| EURUSD | 0,00000 = 0 pips en captura puntual | $7 por lote al abrir, $0 cerrar |
| GBPJPY | 0,023 JPY = 2,3 pips | $7 por lote al abrir, $0 cerrar |
| GBPUSD | 0,00000 = 0 pips en captura puntual | $7 por lote al abrir, $0 cerrar |
| XAUUSD | $0,38 por onza | 0,0016% del nocional de apertura |
| NDX100 | 1,60 puntos | $0 |
Un valor 0 en EURUSD/GBPUSD NO significa «spread 0 histórico»; esta hipótesis es *optimista* y no apta para live. El historial MT5 real del usuario mostró $0,07 de comisión por 0,01 lote en EURUSD/GBPJPY/AUDJPY/XAUUSD y $0 en NDX100, corroborando una muestra de tarifas del escenario actualizado.

## 1. RESULTADOS BRUTOS DE TRADER LAB — 3.368 señales

| Métrica paper | Resultado observado en run CI |
|---|---:|
| Señales Native MAX recibidas/validadas | **3.368** |
| Rechazos de geometría heredada antes de solicitud física | **20** |
| QDLE respondió sin lote físico al NAV/cartera simulados | **2.809** |
| QDLE propuso lote positivo en este escenario cronológico | **539** |
| Aperturas paper contabilizadas | **539** |
| Cierres paper concluidos | **537** |
| Posiciones paper ABIERTAS sin terminal de precio completo | **2** |
| Aperturas broker MT5 verificadas | **0** |
| Capital QORE inicial de investigación | **$60,00** |
| **Caja paper tras eventos conocidos** (no NAV final con posiciones abiertas) | **$9,08037928** |
| **P&L neto de los 537 cierres paper** | **−$50,77962072** |
| Cargos OPEN paper incluidos en las 539 aperturas | $41,78370064 |
| Volumen ejecutado paper acumulado (NO concurrente) | 7,01 lotes |
| **PF de los 537 cierres paper** | **0,716659** |
| **DD máximo sobre balance/caja paper** | **85,197246%** |
| Win rate de 537 trades cerrados | **37,243948%** (200 ganancias, 334 pérdidas, 3 flat) |
| DD intratrade de toda la cartera / NAV y PF reales | **NO CERTIFICABLES** |

**Conciliación de caja:** $60,00 inicial + (−$50,77962072 de NET realizado en 537 posiciones cerradas) − $0,14 de comisiones de apertura de las dos posiciones aún abiertas = **$9,08037928**. Las comisiones de las 537 posiciones cerradas están incluidas en su NET; no descontarlas dos veces.

**Diferencia frente al QDLE quote-only anterior de 2.102:** el escenario de Trader Lab reevalúa el presupuesto financiero según cambia el **NAV paper**, y conserva riesgo/margen de posiciones concurrentes; los 2.102 son cotizaciones independientes con NAV fijo $60, no 2.102 aperturas. La diferencia tampoco es una demostración de ejecución broker; el fill en Trader Lab se modela mediante OHLC M5. Este run incorpora un anclaje EURUSD/GBPUSD de spread 0 de captura, favorable al sistema, por lo que no es un stress test realista de spread.

## 2. Descomposición por modo CIBO

| Modo | Señales | Paper aperturas | Paper cierres | Sin lote QDLE | P&L neto de cierres | PF de cierres |
|---|---:|---:|---:|---:|---:|---:|
| BANK | 2.031 | 259 | 259 | 1.765 | −$26,7762 | 0,5357 |
| MEDIUM | 520 | 50 | 50 | 466 | −$6,5742 | 0,5342 |
| ATTACK | 817 | 230 | 228 | 578 | −$17,4293 | 0,8378 |
| **Total** | **3.368** | **539** | **537** | **2.809** | **−$50,7796** | **0,7167** |

20 señales adicionales presentan geometría de entrada/stop/objetivo no apta bajo la convención transversal de fill paper antes de QDLE; se documentan **SIN omitirlas**. La suma de lotes con salida no debe convertirse automáticamente en capital del sistema certificado.

## 3. Descomposición por activo — CIERRES paper

| Instrumento | Cierres paper | Resultado neto paper USD | PF de cierres | Comisiones OPEN en posiciones cerradas |
|---|---:|---:|---:|---:|
| AUDJPY | 203 | −2,8935 | 0,9517 | $18,9700 |
| EURUSD | 95 | −4,3750 | 0,7259 | $8,8900 |
| GBPJPY | 87 | −12,8749 | 0,6737 | $8,1200 |
| GBPUSD | 58 | −5,7400 | 0,6865 | $5,5300 |
| NDX100 | 89 | **−24,1025** | **0,4562** | $0,0000 |
| XAUUSD | 5 | −0,7937 | 0,3610 | $0,1337 |
| **TOTAL** | **537** | **−50,7796** | **0,7167** | **$41,6437** |

El mayor deterioro absoluto es NDX100, a pesar de su comisión $0: su contribución negativa es una evidencia de riesgo/movimiento/precio **en esta hipótesis** y NO un fallo automáticamente atribuible al tarifario.

## 4. Descomposición temporal de cierres por año de apertura paper
| Año de apertura | Operaciones paper cerradas | NET paper |
|---|---:|---:|
| 2019 | 235 | −$26,7311 |
| 2020 | 215 | −$6,5278 |
| 2021 | 78 | −$16,3291 |
| 2022 | 9 | −$1,1916 |
| **Total** | **537** | **−$50,7796** |

## 5. Ejecución y evidencia causal
- MARKET ATLAS seis particiones símbolos/sello ZIP originales: AUDJPY artefacto 10476530915, EURUSD 10475354631, GBPJPY 10475453293, GBPUSD 10475449182, NAS100 origen de NDX100 10476153072, XAUUSD 10476557530. Todos los archivos archivados 2019/2020/2021/2022 pasaron checksum en el workflow.
- Las decisiones CIBO Native MAX originales proceden del artefacto **solo QDLE actualizado** `11624832575` del [run #37947609981](https://github.com/mezas3238-hue/qore-core/actions/runs/37947609981); el control antiguo NO se utilizó.
- QDLE es el motor físico real en `qore_dynamic_lot_engine.py`, usado en un SQLite autónomo PAPER por oportunidad sin enviar órdenes; NAV de cada apertura y presupuesto nativo BANK/MEDIUM/ATTACK son dinámicos, comisiones y márgenes se reservan con el precio paper.
- CIBO sale mediante `cibo_managed_exit_replay.py` con TP/SL, stop-first de misma barra, parciales sujeto a grid, break-even, trailing y cierre defensivo cuando lo determina su plan sellado. Las trayectorias son el bar OHLC histórico más spread congelado, y no reconstruyen el orden intrabar de ticks.
- Todas las posiciones abiertas sin evidencia de cierre terminal mantienen riesgo en reserva. **Dos posiciones siguen abiertas** por interrupciones de secuencia de barras. El balance $9,08 es caja con comisiones abiertas debitadas, NO NAV marcado a mercado.
- PF/DD win rate se denominan siempre `shadow_projected_*` para no confundirlos con medida live. `full_cibo_managed_final_nav_usd=null`, `full_cibo_managed_drawdown_pct=null`, `full_cibo_managed_profit_factor=null`. No se toma P&L de Trader CONTROL como salida CIBO.

## 6. Hallazgos y próxima investigación
1. **Prioridad A:** medir/diagnosticar pérdidas NDX100 por stop vs defensa, índices y época, y después BANK. Verificar diferencia de precio M5 proveedor vs símbolo FundedNext real, contract size y conversión cross.
2. **Prioridad B:** aumentar la integridad temporal de los dos trades sin cierre en huecos de mercado; no liquidar al precio arbitrario de viernes ni forzar TP/SL por outcome Trader.
3. **Prioridad C:** ejecutar sensibilidades de spread no cero EURUSD/GBPUSD, spread 2× y 3×, USDJPY por época, swap, slippage y márgenes por broker histórico.
4. **Prioridad D:** regenerar realmente los cuatro votos económicos con NAV/cuenta secuencial en vez de reescalar límites emitidos a NAV60; investigar 20 señales de geometría antes de QDLE; mejorar además el cálculo de DD sobre **equity MTM** en abiertos.
5. **Prioridad E:** comparar coste/beneficio de protección y DD una vez completada la medición de cartera, sin deshabilitar red de seguridad del broker. **Resultado actual es NEGATIVO en este escenario y excede ampliamente el objetivo 20–25% DD.**

**No uso LIVE ni orden SEND, y no reconozco rentabilidad financiera certificada.**

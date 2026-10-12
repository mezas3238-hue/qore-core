# QORE Native — PRE-REGISTRO H3: reversión cross-sectional 5 sesiones × 33 mercados

**Congelado el 12/10/2026, ANTES de ejecutar outcomes H3 de esta hipótesis. Una sola prueba; no optimizar.**

## Justificación y límites de transferencia

Referencia: Bruce Lehmann, *Fads, Martingales and Market Efficiency*, Quarterly Journal of Economics 105(1), 1990, pp 1-28, DOI https://doi.org/10.2307/2937816. Reversión semanal documentada en acciones. QORE prueba **transferencia**, NO una réplica de aquel universo bursátil: 33 series de broker cTrader DEMO, 28 FX (7 majors + 21 cruces), 3 índices y 2 metales; no acciones individuales, sin market cap, sin carry FX ni futures exceso de retorno, sin stops. Queda expresamente prohibido inferir que esta literatura predice rentabilidad en QORE.

**Pruebas económicas anteriores y dependencias:** H1 TSMOM20 [PR #877](https://github.com/mezas3238-hue/qore-core/pull/877) DIAG Sharpe -0.272 y H2 TSMOM252 vol20 [PR #880](https://github.com/mezas3238-hue/qore-core/pull/880) DIAG Sharpe +0.077. H3 no es un holdout genuinamente nuevo y se escoge DESPUÉS de ver H1/H2: inferencia positiva debe penalizar investigación adaptativa, nunca EDGE_CERTIFIED con estos datos.

## Señal y portfolio fija

1. Roster **exacto 33**: 28 FX, 3 índices, 2 metales, sin selección por PnL. 12 G0 Atlas original #35166210458 y 21 G0 IC Markets DEMO #38193802541, 11 hashes RAW anuales por mercado, no descargar nuevos datos bróker. Se permite reutilizar SOLO el lector SHA/UTC de H1; no sus retornos económicos.
2. Precios diarios *UTC*, no candles D1 certificados del broker: fecha hábil lunes-viernes con al menos 12 barras M5, cierre=último M5 close de esa fecha, ejecución proxy=primera apertura M5 de la fecha que sea >=00:10 UTC y por lo menos 5 minutos después de cierre disponible de última barra previa. No BID/ASK real, tampoco resultado broker NET.
3. Un único calendario **común, intersección** de las fechas D1 válidas de los 33 símbolos, orden creciente. No rankear instrumentos con series temporalmente distintas. Todo día común requiere precios válidos de los 33; reportar número de fechas excluidas respecto al conjunto unión, concentración sectorial, gaps.
4. En fecha de decisión índice global `j` conocida al OPEN de la sesión: `r5_s = CLOSE_s[j−1]/CLOSE_s[j−6] − 1` (6 sesiones completadas para calcular cinco retornos). Falla con *cualquier* data de `j` o posterior. Ordenar 33 por r5 ascendente, desempatar por ticker ascendente. **Long 6** de menor retorno; **short 6** de mayor retorno (20% redondeado hacia abajo = 6), 21 neutrales. Exposición en precio normalizada: long +1/12 cada uno (long leg +0,5 bruto); short −1/12 (short leg −0,5 bruto). Gross=1.0, net=0, dólar-neutral nominal no factor-neutral ni volatilidad-neutral. No normalización de volatilidad ni ranking sectorial, porque violaría la formulación propuesta.
5. **Hold 5 sesiones comunes** no superpuestas: rebalancear índices de cada tramo DEV/DIAG `j=0,5,10,…`; si al inicio de DEV falta lookback de seis cierres, quedarse en CASH y no mover el calendario. El primer rebalance del DIAG puede usar cierres DEV anteriores ya conocidos, sin usar el resultado del futuro. Rebalanceos parciales/cambios de signo pagan `0.0001 × sum_s abs(weight_new_s-weight_previous_s)`, incluyendo entrada y salida y liquidación al fin de cada periodo. No rebalanceo diario. Supuesto costo 1 bp *por lado de peso nocional*. No apalancamiento neto extra.
6. Retorno diario *mark to market*: la exposición existente de la jornada anterior produce `sum_s position_s × (OPEN_s[j]/OPEN_s[j−1] − 1)` atribuido a fecha `j`; tras calcularlo, se ejecuta el rebalanceo simulado al `OPEN_s[j]` descontando el turnover. El primer día de DEV/DIAG inicia neutral. Máximo gap entre fechas comunes consecutivas **7 días** o FAIL sin imputar retorno. Liquidación final incluida una vez en la última fecha, sin lookahead.
7. Benchmark cash 0, + correlación con **SP500 CFD original**, no SPX cash; estrategia neutra gross1, equity curve parte NAV=1 en cada tramo, 252 días laborables anuales incluyendo fechas sin observaciones con cash=0; no tratar valor 0 como horario broker certificado.

## Ventanas congeladas y embargo

- DEV desde **2016-09-17** hasta **2021-12-31** (2022-01-01 exclusivo).
- DIAG desde **2022-01-01** hasta **2024-09-16** (2024-09-17 exclusivo).
- HOLDOUT desde **2024-09-17** hasta **2026-09-17**, sellado, no calcular OHLC económico ni ingresos de ese periodo (SHA originales sí se comprueban por integridad).

## Resultados obligatorios, independientemente del signo

Sharpe neto **de costo hipotético**, `sqrt252 × mean / std_muestral`, Rf0; retorno geométrico anualizado 252; drawdown máximo NAV, total rebalanceos, costos totales expresados como bp de capital, turnover total de nocional, número de fechas comunes y descartadas, conteo 6+6 por cesta, retorno/coste por familia 28FX/3índices/2metales como **diagnóstico solamente**, correlación con SP500 CFD, datos de pruebas sintéticas, SHA commit exacto y artifact. **No presentar 12.053 operaciones como observaciones conocidas**: la cantidad será medida, y separar rebalanceos, cambios de posición y días de posición.

Veredicto SIN ajuste: DIAG Sharpe ≤0 → `NO_POSITIVE_SUPPORT`; 0 < Sharpe ≤0,5 → `WEAK_EXPLORATORY_ONLY`; >0,5 → `PROMISING_EXPLORATORY_NOT_CERTIFIED`. DIAG es etapa ya expuesta a hipótesis previas; nunca validación totalmente nueva, 0/3 traders certificados hasta prueba fresca independiente con costes reales. No rescatar con horizonte 3/10d, quintiles distintos, weighting vol, sector-adjusted, costos menores o escoger sólo FX/índices tras observar PnL.

**STOP fail-closed** por falta SHA, fuente anómala, lookahead, indisponibilidad del calendario común o menos de 33 mercados. Source G0 read-only. No órdenes ni mutaciones de VPS, CIBO, Shared, MT5, QDLE, LIVE. Mantener PR investigación DRAFT.

# QORE Native — H-TOM-1: ÚNICO EXAMEN ECONÓMICO DEL TURN-OF-MONTH US EQUITY INDEX

**PREREGISTRO PREVIO A MIRAR CUALQUIER RESULTADO H-TOM-1.** Un solo examen, no optimización ni sweep. El usuario ordena trabajar con los datos existentes y poner fin a la cadena de censos sin tesis económica.

## Mecanismo y evidencia contraria

Hipótesis: flujos de aportes/rebalanceos y diferimiento de riesgo vinculados al fin de mes pueden causar un aumento del índice en la transición mensual. **Quién pagaría:** demandantes de exposición de cartera, no instituciones secretas; los arbitrajistas pueden destruir ese diferencial. Motivación reciente **contradictoria**: Han, Han & Tian, *The disappearing turn-of-month effect*, Finance Research Letters 71 (2025) concluyen desaparición después de 2001, DOI 10.1016/j.frl.2024.106461. *Infrequent rebalancing, risk deferral, and equity returns at the turn of the month*, Journal of International Financial Markets, Institutions & Money 109 (junio 2026), DOI 10.1016/j.intfin.2026.102309 encuentra un patrón internacional reciente. **Ningún paper acredita una ventaja de CFD IC Markets QORE**.

Esta familia **no** es CFTC Z, FX London fix RESET, carry, NAS100 cash-open sweep/continuation, ni ICT. No cambiar el mecanismo si el resultado es negativo.

## Datos económicos congelados

- Tres activos de cohorte ORIGINAL12 CIBO DEMO: **SP500** (PRIMARY, provider US500), **US30** y **NAS100** (provider USTEC), cada uno con RAW_M5_LEDGER 2016–2026 del original productor GitHub Actions run **35166210458**. Reusar SHA y auditor `qore_native_existing12_m5_g0_v1` y agregación SHA `47f5763d7ea2c10dd32fa40a84d7480c8124f1a512b623c1299ef2ba7b8c51c2`. NO usar fuentes de otra cuenta ni recodificar símbolos.
- **Embargo estricto de precio OHLC desde 2024-09-17 00:00 UTC**, NO leer valores futuros; 2024-09-17+ solo se pueden saltar las filas, no calcular ningún otro precio. Desde 2016-09-17 inclusive se usa histórico existente; DEV meses completos **noviembre 2016–agosto 2022**, DIAG meses completos **octubre 2022–agosto 2024**; septiembre 2022 excluido entero para no filtrar entre ventanas. Para primer mes DEV, se necesita último día de OCT 2016 como entrada. Para DIAG, último día SEP 2022 como entrada, **pero septiembre 2022 sigue sin evaluarse como mes de outcome**. Igual para EIA/Futures reserva 2022-24 distinta que NO se consulta.
- Los periodos de 2016–2024 de QORE Native ya se utilizaron por otras hipótesis: **DEV/DIAG NO constituyen nuevo holdout virgen**; solo decisión exploratoria previa a siguiente certificación.
- Los datos M5 OHLC de CFD no incluyen BID/ASK histórico válido en cada operación, precio de ejecución, swaps, comisión, costes de financiación ni ajuste de dividendos auditado; la hipótesis neta realmente ejecutable permanece `NET_BLOCKED`.

## Regla fija, sin decisiones después de PnL

- Zona del reloj: `America/New_York` con DST IANA. Solo datos M5 alineados y en sesión cash US **09:30–15:55 NY**. A cada fecha se exige **>=60** de 78 velas cash M5 (no inventar mercado abierto cuando hay cierre extraordinario). Una sesión existe solo si tiene barra **15:55 NY** con precios íntegros; si no, se excluye la fecha del calendario de sesión. Rechazar pares de barras con fecha UTC/NY incoherente, duplicados, apertura no positiva. Horarios de NYSE reconstruidos desde velas históricos, NO proveniencia PIT de calendario verificada: limitación conocida.
- Entrada ToM **compra teórica al OPEN de la M5 15:55 hora NY** del **último día operable del mes anterior**; salida **al OPEN de la M5 15:55 hora NY** de la **tercera sesión cash del mes actual** (índice ordinal 3, indexado 1). La orden teórica es calendario previsible, pero la entrada es un precio de referencia OPEN, **NO fill ask**.
- Control emparejado, por **mismo instrumento y mismo mes**: comprar al OPEN M5 15:55 de la **décima sesión cash del mes actual**, vender al OPEN M5 15:55 de la **decimotercera sesión cash del mes actual**. Ambos intervalos separan tres sesiones, minimiza diferencias de duración, no elimina factores de rentabilidad.
- `TOM_gross_bps = 10000 * (exit-reference_entry) / entry`. Lo mismo para control 10→13; delta = TOM−control. Prohibido utilizar el high/low futuro para definir entrada o stops, ni precio de cierre que se sepa después. No usar señales de vela ni mirar los retornos antes de elegir fechas. Retornos de índice CFD, no USD PnL de contratos.
- Cada mes completo necesita al menos 13 sesiones cash RTH verificadas y el último cash día del mes anterior. Si falta precio o hay discontinuidad enorme de calendario entre sesiones (>= 7 días), mes etiquetado `MISSING_CALENDAR` y excluido simétricamente; no completar con fechas sintéticas. Un mes=una observación por símbolo; tres índices del mismo mes **NO** se cuentan como muestras independientes.
- Sin selección posterior del mejor instrumento: SP500 PRIMARY. US30 y NAS100 REPLICATION deben reportarse completos, incluidos resultados negativos.

## Test estadístico y económico BINARIO por adelantado

- Por mercado y periodo se reporta `n_months`, `mean_TOM_gross_bps`, `mean_midmonth_control_gross_bps`, `mean_paired_excess_bps`, proporción de meses TOM positivo, estrés neto **hipotético** con coste RT fijo de 5/10/20 bps; **no** computar PF/Sharpe/Sortino/DD net (no son trades ejecutados, no hay costes verificados).
- DEV debe tener **>=40 meses**, DIAG >=**16 meses** en CADA uno de los 3 índices. Si menos: `INCONCLUSIVE_COVERAGE` y detener.
- H-TOM-1 exige SP500 **en ambas ventanas**: media TOM bruta **> +15 bps**, media exceso pareado vs control **> +15 bps**, y límite inferior del **bootstrap one-sided 95%** del exceso pareado **>0**. Bootstrap determinista circular de bloques consecutivos de 3 meses, **4.000 repeticiones**, semilla `20261013` fijada, por periodo (no elegir bloque ex post). La estadística pertenece a los meses, no a 24M velas independientes. Esto proporciona una evaluación de incertidumbre exploratoria, NO un p-value confirmatorio de OOS nuevo.
- Replicación: **US30 y NAS100** deben mostrar **exceso pareado > +5bps** en DEV y DIAG, sin escoger el más fuerte ni ajustar por mercado; quedan diagnósticos de familia muy correlacionada.
- Si falta cobertura suficiente: `INCONCLUSIVE_COVERAGE`; con cobertura y falla de cualquier gate anterior: `NO_SUPPORT_UNDER_PREREG`; si todos pasan: `PRELIMINARY_GROSS_ASSOCIATION_ONLY_NOT_EXECUTABLE`. **Ninguno** implica edge NET rentable ni autoriza LIVE/DEMO. Un resultado negativo cierra H-TOM-1 en QORE sin acortar ventanas, cambiar horarios, elegir otro día del mes o relajar umbrales.
- La pregunta de rentabilidad económicamente real requiere bid/ask, comisiones, rollover de 3 días, swap, slippage, valor por contrato y calendario PIT de cierre; no imputar costes de fuente corta ni decir >15bps cubre un coste que no conocemos.

## Control de un solo examen y STOP

Prereg documento se fija en commit Git **anterior** a todo runner que mire precios. Exigir ancestry + mismo Git blob, firmar source SHA y artefacto. No LIVE/VPS/MT5/FundedNext/CIBO/Shared/QDLE; no merges sin orden. No leer 2024-09-17+ ni condicionar políticas por los resultados de #832/#836. Al terminar ONE RUN, dictamen `GO_ONLY_FOR_NEW_INDEPENDENT_SOURCE_RESEARCH` si preliminar, o `CLOSE` si NO_SUPPORT, o `BLOCKED` si cobertura insuficiente. No segunda ronda retunada.

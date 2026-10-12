# QORE Native — H5 ÚNICA PRUEBA FX policy-rate differential, 28 pares, coste 2bp/side

**PREREGISTRO CONGELADO el 12 octubre 2026 ANTES de ejecutar retornos económicos de H5. No retunear al ver resultados.**

## Aceptación de la crítica y nomenclatura

Investigamos una **proxy de carry basada en ocho tasas de política monetaria**, no forwards negociables, ni carry con swap broker certificado. Usar velas spot/CFD para clasificar con tasas **no convierte** el PnL en retorno excess forward ni incluye financiación automática. La hipótesis real es: *una cesta de los 6 pares con diferencial de política mayor, contra los 6 de menor diferencial, gana sobre spot y su carry teórico, a horizonte mensual*.

Datos oficiales uniformes: **BIS, WS_CBPOL**, 8 países/área, series mensuales `M.AU,M.CA,M.CH,M.XM,M.GB,M.JP,M.NZ,M.US` de [BIS Central bank policy rates](https://data.bis.org/topics/CBPOL). Corresponden a las monedas AUD,CAD,CHF,EUR,GBP,JPY,NZD,USD. Hay soporte oficial para la transición de instrumentos nacionales, a diferencia de la serie suiza 3M LIBOR. Documentación BIS advierte ajustes/historia empalmada y lag en anuncios. **Los datos presentes se descargan en 2026, se presume conocidas las decisiones públicas en su momento, pero NO se afirma vintage PIT auditado, ni inmutabilidad de toda serie publicada por BIS**.

Para evitar inferir decisiones del mismo cierre de mes, el primer día de negociación de calendario común del mes **m** toma la tasa mensual del BIS para el **mes m−2**, es decir dos meses de lag conservador. Por ejemplo primera sesión de junio de 2023 usa abril 2023. Esto NO elimina por sí mismo backfill histórico de BIS; hallazgos siempre exploratorios. No optimizar el lag 1 vs 2 vs 3 después del resultado. Si no hay exactamente tasa conocida de cualquiera de las 8 monedas en el mes m−2, periodo falla cerrado (no imputar) y NO cambiar universo para rescatar.

## Mercado y regla de operación

- Instrumentos G0 originales **28 FX** (7 majors, 21 cruces) del mismo lector y SHA de 11 particiones anuales usado por H1/H2/H3. No elegir seis activos por beneficios previos; ordenarlos por diferencial macro de tasas. La cesta son 12 pares con exposiciones cambiarias altamente dependientes, no 12 ni 28 apuestas independientes.
- Calendario diario común de **28** series válidas UTC de M5, mínimo 12 barras por fecha; `close` solo para validar fuentes, retorno `entry_open` a `entry_open` del día siguiente. Entrada en primer M5 abierto >= 00:10 UTC, tras último cierre del día previo + margen de cinco minutos. La completitud del día se reconoce ex post, **riesgo de selección causal de días**: no certificar aún con Sharpe alto.
- En la primera sesión común de cada mes, calcular `d_s = rate_policy_3M? NO: BIS policy monthly annual rate(BASE) - annual rate(QUOTE)`, expresado en **puntos porcentuales anuales**, no en bps. Orden descendente por diferencial `(d_s, symbol)`; **long top 6** high differential, **short bottom 6** low differential. Empate alfabético ascendente. Peso por posición ±1/12, gross1.0, net 0 nominal. Mantener hasta siguiente mes (sin rebalanceo semanal), conservar cero exposiciones en pares restantes.
- El primer día de cada era DEV/DIAG parte flat, independentemente del último rebalance anterior. La primera decisión con datos válidos abre 6+6 y cada primera sesión de mes se recalcula. Dev 2016-09-17..2021-12-31, DIAG 2022-01-01..2024-09-16. Holdout desde 2024-09-17 (sellado) NO consultar retornos ni tasas posteriores a 2024-08.
- Coste **0.0002 × sum_s abs(nueva_ponderacion_s−anterior_s)** para cada cambio y liquidación final (2bp por lado de nocional transado). No falsas 12,053 órdenes, reportar número real de rebalanceos y cambios de posición. Contabilidad diario `sum weight_s × (open_today/open_yesterday −1)` antes del rebalance al open. Primer día por era PnL cero.
- Producir por separado: (**A**) PnL de spot después del coste 2bp (sin añadir diferencial al patrimonio). (**B**) **idealización** spot+acumulación diaria `sum_s weight_s × (rate_base - rate_quote)/100/365 × elapsed_calendar_days`, para exposición de sesión previa. La tasa es política rezagada, no overnight funding efectivamente cobrado, broker swap ni forward premium; **no añadirlo a un PnL broker**, no etiquetar `NET`. Período >7 días común sin precios => abortar. No imputar precios ni cross currency conversion.
- Benchmark correlation SP500 CFD (no SPX) opcional si fuente existe, pero no bloquear análisis FX por benchmark. Reportar métricas de ambos A/B, costes, rebalanceos, concentración de moneda base/quote, exposiciones netas, fechas comunes, datos y versión de fuentes exactos y SHA; puntos abiertos limitan valor predictivo/negociable.

## Reglas de decisión

`DIAG Sharpe de A (spot-only after assumed 2bp) <=0` => `NO_POSITIVE_SPOT_SUPPORT`; `0 < Sharpe <=0.5` => `WEAK_SPOT_ONLY`; `Sharpe >0.5` => `PROMISING_SPOT_ONLY_NOT_CERTIFIED`. Reportar B como **contrafactual financiado ideal, no derecho a promoción aunque resulte alto**. Se reporta DEV y DIAG, CAGR, max DD, net/cost, correlación, total turnover y basket cost breakdown. No optimizar 2bp, lag, composición, split ni elegir pesos por volatilidad después de ver cifras. TSMOM H1/H2 y XS H3 ya vieron DIAG, por tanto H5 sigue **selección adaptativa** y DIAG no es holdout nuevo independiente.

## Protección y falla

Si el endpoint BIS falla o devuelve país incorrecto, tasa no finita, cobertura desigual o interrupción de series, **reporte BLOCKED_SOURCE** y detener sin completar cartera ni inventar valores. Las fuentes raw descargadas únicamente en runner read-only y excluidas de artifacts públicos; manifiesto SHA y métricas agregadas sí. Si hay un problema material de especificación o de bug de costo, corregir como defecto PRE-ECONOMIC o invalidar test y repetir de manera identificada, NUNCA buscar Sharpe favorable.

**Sin lectura de holdout desde 2024-09-17. No órdenes, VPS, MT5, CIBO, Shared, QDLE o LIVE. 0/3 traders QORE Native certificados hasta muestra económica independiente + BID/ASK/swaps reales.**

Referencia principal para series: [BIS CBPOL](https://data.bis.org/topics/CBPOL) y [documentación](https://www.bis.org/statistics/cbpol/cbpol_doc.pdf). Literatura original de FX carry usa yields/forwards y retorna excesos financiados: **esta no es réplica exacta**.

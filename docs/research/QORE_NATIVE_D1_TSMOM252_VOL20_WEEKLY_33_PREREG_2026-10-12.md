# QORE Native — preregistro económico de UNA prueba TSMOM de 12 meses, vol-scaled, semanal

**Congelado el 12/10/2026, antes de ejecutar resultados económicos de esta nueva especificación.**
**La prueba de 20 días [PR #877](https://github.com/mezas3238-hue/qore-core/pull/877) ya es conocimiento previo y terminó Sharpe DEV −0,092, DIAG −0,272.** Esta segunda hipótesis está motivada por la literatura previa al experimento, no por escoger parámetros al optimizar PnL.

## Mecanismo y alcance

Referencia: [Moskowitz, Ooi y Pedersen (2012), *Time Series Momentum*, Journal of Financial Economics, DOI 10.1016/j.jfineco.2011.11.003](https://doi.org/10.1016/j.jfineco.2011.11.003). Estudia momentum temporal a 1–12 meses en **58 contratos líquidos de futuros/forwards**, incluyendo equity indices, commodities, divisas y deuda soberana, con escalado por volatilidad. **El test presente NO es una reproducción exacta del paper**: usa CFD/FX de broker, 33 mercados concentrados en 28 FX (7 majors y 21 cruces), carece de bonos y commodities diversificadas, reequilibra semanalmente y trabaja con proxies de apertura M5. Las series de precios FX no son *excess returns* financiados con carry; los CFDs omiten swap/roll/funding. Un Sharpe positivo NO será edge certificado.

**Una sola regla congelada:** en la primera jornada admisible de cada semana ISO de cada símbolo, calcular dirección igual al signo del cierre de la sesión completada anterior dividido entre el cierre 252 sesiones completadas antes, menos uno. `signal[t] = sign(C[t−1]/C[t−253]−1)`. Sin filtro de intensidad ni selección de símbolos. El objetivo de riesgo por instrumento es **10% anual** ex ante, estimando `sigma20[t]` como desviación muestral de los 20 retornos diarios *close-to-close* estrictamente anteriores a t; `notional[t] = signal[t] × min(3.0, 0.10/(sqrt(252) × sigma20[t]))`. Factor de apalancamiento máximo 3 por instrumento, definido preventivamente. Si sigma no es finita o no positiva, no se toma exposición; no se sustituye por parámetros ajustados.

**Rebalanceo semanal**, nunca diario: primer día válido de la semana del símbolo después de tener 253 sesiones de historial, y se mantiene notional constante hasta próxima decisión semanal. Todas las jornadas intermedias computan PnL sobre retorno de apertura a apertura y exposición fijada ex ante. No reescalar intrase- mana. El notional se lleva a cero en frontera DEV→DIAG y al fin de DIAG. Coste **0,0001 × |notional_nuevo − notional_viejo|** por lado transado, inclusive rebalanceos parciales; no cargar coste diario sin cambio, pero sí costo de cierre al finalizar periodo. No comisiones históricas reales ni financiación.

## Calendario, fuente y ejecución

- Exactamente los 33 originales G0 SHA de [PR #829](https://github.com/mezas3238-hue/qore-core/pull/829) usados por [PR #877](https://github.com/mezas3238-hue/qore-core/pull/877); 12 Atlas DEMO y 21 IC Markets DEMO, artefactos en GitHub Actions. SHA de RAW M5 por las 11 particiones anuales verificadas, sin descargas nuevas del broker. Se reutiliza **solo** el lector de barras y catálogo de fuentes del experimento previo, no sus señales ni sus resultados de PnL.
- Definición D1 = sesión de fecha **UTC**, con al menos 12 M5; `entry_open` = primera apertura M5 a partir de 00:10 UTC; `close` = último cierre M5 del día. No confundir D1 reconstruido con vela D1 broker.
- Última barra del día previo considerada disponible cinco minutos después de su `opened_at`. Añadir cinco minutos de prudencia antes de la primera apertura admisible. Las entradas/salidas se marcan usando apertura de barra: **proxy de fill**, no ejecución real.
- Si hay hueco entre fechas consecutivas de un mismo símbolo >7 días, abortar evaluación de ese símbolo en lugar de contabilizar retornos inexistentes. Si faltan jornadas normales, valorar desde la última apertura válida hasta la siguiente; no imputar barras.
- **DEV**: 2016-09-17 hasta 2021-12-31 inclusive. **DIAG**: 2022-01-01 hasta 2024-09-16 inclusive (diagnóstico anteriormente expuesto). **Holdout sellado:** 2024-09-17 hasta 2026-09-17, verificar solo SHA anual del bruto y no leer OHLC, PnL o retomar tuning a partir de ese tramo. No afirmar walk-forward 2022–2026.
- Capital: participación fija **1/33 por instrumento**, exposiciones risk-scaled aplicadas dentro de cada participación, sin renormalizar cuando un activo está en efectivo. Se computa retorno diario de la cartera por las fechas laborables, datos faltantes sin observación equivalen a parte de capital sin rendimiento. El capital hipotético admite apalancamiento hasta 3× por mercado; sin llamadas de margen o cierre forzado modelados.
- Benchmark: efectivo al 0%, y correlación con **SP500 CFD** misma fuente, **no SPX cash**. Correlación de índices no homólogos, y panel mayoritariamente de pares FX, impide trasladar hallazgos directamente a la cartera MOP.

## Salida obligatoria antes de cualquier juicio

Para DEV y DIAG, Sharpe `sqrt(252) × mean / sample_std` del retorno diario de capital (RF0); retorno geométrico anualizado de NAV con 252 jornadas; máximo drawdown intraperiodo; posiciones mercado-día; rebalanceos y turnover abs notional; correlación diaria con SP500 CFD; desglose predefinido por **28 FX**, **3 índices**, **2 metales** como diagnóstico **no apto para escoger ganadores**; los 33 símbolos y muestras con menos datos reportados sin excluirlos del panel. No optimizar nada ni cambiar cap, calendario, señal o anualización tras observar resultados.

**Veredicto preregistrado:** `DIAG Sharpe <= 0`: `NO_POSITIVE_SUPPORT`. `0 < DIAG Sharpe <= 0.5`: `WEAK_EXPLORATORY_ONLY`. `DIAG Sharpe > 0.5`: `PROMISING_EXPLORATORY_ONLY`, jamás `EDGE_CERTIFIED` hasta nueva validación independiente y costes reales. En todos los casos no tocar holdout ni reoptimizar 252/20/cap3/10% a la vista de PnL; 0/3 Traders certificados. Registro explícito si todos los objetivos fallan, sin sustituir hipótesis por reversión 5d.

## Auditoría de integridad previa a interpretar resultados

- 33/33 archivos fuentes SHA 11 años, atribución original 12+21; no saltar mercados que pierdan dinero.
- Tests con series sintéticas demuestran señales sin futuro, decisión semanal y sin cambio intrase-mana, coste turnover de notional, efecto de cap, embargo, cash para falta de posición, separación DEV/DIAG.
- STOP/FAIL si falla identidad, SHA, pricing, timestamps, cap o guardas de embargo.
- Mantener investigaciones DRAFT, sin escritura de precios originales en repo público; no órdenes, VPS, MT5, CIBO, Shared, QDLE, LIVE, ni modificar E1.

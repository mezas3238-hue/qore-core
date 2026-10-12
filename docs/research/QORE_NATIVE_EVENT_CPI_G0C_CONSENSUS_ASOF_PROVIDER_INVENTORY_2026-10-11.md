# QORE EVENT-MACRO CPI — G0C inventario de consenso as-of y límites de costes (SIN DATOS IMPORTADOS)

**2026-10-11.** Inventario documental posterior al G0 calendario/timestamps, **sin consultar valores de forecasts, sorpresas CPI ni OHLC**. No cambia las 119 fechas ni la prueba G0. Estado `CONSENSUS_PROVIDER_CAPABILITY_IDENTIFIED_ACCESS_NOT_VERIFIED`.

## Fuente posible de expectativas antes del dato CPI

[Trading Economics — Economic Calendar Point-in-Time API](https://docs.tradingeconomics.com/economic_calendar/point-in-time/) documenta capacidad de consultar calendario histórico e información de eventos en representación temporal; su [esquema oficial](https://docs.tradingeconomics.com/economic_calendar/schema/) contiene campos `Date, Country, Event, Reference, Actual, Forecast, TEForecast, Previous, LastUpdate, Revised, DateSpan`. [API de calendarios](https://tradingeconomics.com/calendar/api) explica que `Forecast` es un consenso de economistas y `TEForecast` un pronóstico propio, conceptos **no intercambiables**.

**Disponibilidad técnica documentada ≠ licencia, acceso efectivo, completitud CPI ni snapshot previo validado.** Ninguna credencial, forecast ni consenso de Trading Economics está actualmente autorizado/verificado en este estudio. No usar sus ejemplos como fuentes de CPI. Requiere una cuenta/licencia válida y cotejar:
1. Qué campos de CPI **headline MoM y core MoM** existen efectivamente para cada uno de los **119 eventos**, si fueron poblados antes de 08:30 ET.
2. Si el API permite obtener la imagen **T−1 día** y **T−5 minutos** de cada anuncio, con timestamp UTC recuperable y hash, sin usar información filtrada tras publicación. **Un único `LastUpdate` posterior al anuncio no prueba consenso as-of**. El campo `Actual` tras release jamás puede usarse como feature anterior.
3. Identidad y escala de consenso: headline MoM/core MoM, estacionalidad, unidades y referencia mensual exacta; revisions del pasado no sustituyen primeras publicaciones.
4. Cobertura por fechas/años, duplicados, campos omitidos, sesgo por indisponibilidad, términos de licencia y permiso de guardar snapshots derivados en GitHub.

**No solicitar tokens en chats/issues.** Si el propietario conecta un proveedor autorizado, se habilitará investigación en un flujo aparte, sin mostrar secretos y tras congelar contrato de extracción. Si no está disponible, `CONSENSUS_ASOF_UNVERIFIED`; alternativas de hipótesis que no requieren consenso necesitarán un **mecanismo independiente preregistrado**, no señal basada en sorpresa inventada.

## Coste de capturar anuncio

El censo G0 muestra que 113 de 119 releases calendarizados tenían 71/71 timestamps nativos en NAS100/USTEC; **no** documenta BID/ASK, latencia, precio de ejecución ni volumen negociable a las 08:30. Se requiere inventario real de:
- cTrader broker **DEMO vs LIVE**, contrato/lot-size/min-stop/margen, min tick, spreads pre/post CPI, comisiones y swaps;
- fills reales comparables, o reconstrucción conservadora y explícitamente marcada como **simulación no validada**;
- apertura posible a partir de instante posterior al embargo y recepción de señal, evitando entrada en precio de vela 08:30 aún en formación.

G0 no autoriza backtest económico ni live. 113 anuncios con feed completo representan **113 eventos independientes nominales**, no 3.49M muestras; incluso más cerca de 100 tras variables CPI, calendario y fuentes as-of faltantes. Cualquier afirmación `30 bps de movimiento = 30 bps de edge` permanece prohibida.

## Elección responsable

`EVENT_G0_SOURCE_COVERAGE_PASS` solo para calendario retro + timestamp M1. Requisitos `G0B_RELEASE_CONFIRMATION`, `G0C_CONSENSUS_ASOF`, `G0D_COST`, `POWER_PREDECLARED` abiertos; `G1_ECONOMICS_BLOCKED`.

No negociar ni copiar datos, descargar originales sensibles, alterar carpetas CIBO/VPS/MT5/Shared. Actualizar documentación en GitHub únicamente.

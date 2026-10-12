# QORE Native G1 — Forense exploratorio de episodios bid=ask desde Protobuf original

**2026-10-12; exploratorio POST-HOC, NO preregistro ex ante**. Antes de redactar el análisis se inspeccionaron resúmenes y registros del source de [PR #859](https://github.com/mezas3238-hue/qore-core/pull/859). La población de cinco activos se había escogido deliberadamente para buscar spreads cero. Ninguna proporción publicada aquí será presentada como una validación estadística independiente, ni sugiere rentabilidad.

## Objetivo técnico de las comprobaciones reproducibles

Reusar exactamente el archivo ORIGINAL BID/ASK con fields de Protobuf de 5 símbolos ×2 ventanas (source run #38288411671, artifact #11764163362, ZIP SHA256 `b4eb9e66d76bcd439d4db8f2b8707afa06fe2d211a275c8af8b8605714b58684`) y **exigir primero** la redecodificación independiente exacta de [PR #860](https://github.com/mezas3238-hue/qore-core/pull/860) antes de cualquier clasificación nueva.

Clasificar por símbolo y por cada ventana, sobre instantes únicos de actualización de cualquier lado, con `last-known as-of` de 5s:
- `zero_same_millisecond`: BID y ASK comparten milisegundo y precio nativo entero. Recuento de cero a mismo-ms ya cotejado: 5.371/6.640.
- `positive_same_millisecond`: ambos lados comparten milisegundo pero ASK>BID, control de que las actualizaciones sincronizadas por sí mismas no implican cero.
- `zero_bid_older / zero_ask_older`: el lado antiguo por reloj es BID o ASK, sin inventar orden de recepción dentro de 1ms.
- `zero_episode_max_consecutive_source_instants` y número de episodios; medidas de **clustering de fuente**, NO persistencia de spread negociable en tiempo de reloj.
- `same_ms_same_price / same_ms_positive_price` entre eventos nativos exactos cuando ambos lados actualizan en mismo ms.
- Partición y paridad contra contadores de QA original por mercado (`positive/zero/stale/missing/crossed`); **ningún** zero admite coste 0.
- Protección contra empates mismo-ms con valores distintos y contra adelantarse a actualizaciones futuras.

**Hecho externo contrastado:** Spotware indica que BID y ASK son feeds independientes, pueden actualizar juntos y frecuentemente cambian por separado. cTrader Open API devuelve quote type por petición, valores enteros ×1e5, redondeo a digits del contrato, con límite `hasMore` y una semana máximo por request. Esto justifica reconciliar últimos valores recibidos por tiempo, pero **no demuestra que BID=ASK esté disponible para ejecutar órdenes al coste 0**. Documentación:
- https://help.ctrader.com/open-api/symbol-data/
- https://community.ctrader.com/forum/connect-api-support/24165/ (respuesta Spotware de 18–19 oct 2024).

Resultado esperado = artefacto de QA descriptiva con SHA, sin datos brutos ni cuentas/tokens, sin PF, Sharpe, Sortino, trading, optimización ni merge a LIVE. Gates `ZERO_SOURCE_INTERPRETATION_P0_OPEN`, `HISTORICAL_NET_BLOCKED`, `CERTIFIED_0_OF_3`. La pregunta económica continúa sin resolver, requiriendo contrato original y evidencia de quotes realmente ejecutables. 

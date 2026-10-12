# QORE / VT31 — Evidencia visual puntual MT5 NDX100 BID/ASK (2026-10-12)

**Tipo**: imagen compartida por usuario en la conversación el 2026-10-12. **Clase probatoria**: UNA observación gráfica (snapshot), NO serie histórica, NO ejecución, NO broker ACK, NO fixture de tres años. No almacenar el screenshot de usuario ni datos de la cuenta en GitHub; sólo los campos mínimos pertinentes para revisión del contrato de cotización.

## Lo que puede leerse directamente de la imagen

- Pantalla de MetaTrader 5: Cotizaciones; símbolo mostrado **NDX100**.
- Bid mostrado **30853.00**, Ask mostrado **30854.60**.
- Diferencia **Ask - Bid = 1.60 puntos del índice**.
- Precisión visual de los precios del símbolo: **dos decimales**. Indicador de spread de la interfaz: **160** (unidad de visualización MT5; puede corresponder a 0.01 por punto de plataforma, **NO** afirmar sin contrato broker tick_size/tick_value).
- La fila NDX100 muestra **16:07:11**; pantalla del teléfono muestra **10:07**. **No se ha certificado la zona horaria del servidor ni la fecha exacta de la cotización de la fila** a partir de una captura estática.
- El nombre **NDX100** del símbolo MT5 mostrado **NO es prueba de equivalencia de fuente/precios/contrato con el NAS100** utilizado por el replay histórico `VT31_NAS100_OWNER_3Y_BASE_001`.
- No se puede afirmar si esos BID/ASK habrían existido ni qué spread hubo durante 2023-10-01 a 2026-10-01. No convertir 1.60 en spread constante retrospectivo.

## Uso correcto en el estudio comparativo A/B

El ensayo [replay A/B 3Y CI 38040127136](https://github.com/mezas3238-hue/qore-core/actions/runs/38040127136) es **research price-only OHLC M1**, 2,140 candidatos M1 fuente exactamente pareados. La rama B mostró 789 solapamientos CE M1 vs 301 A; **B no superó preregistro** por 670/2140 = 31.31% indeterminados. **NO** existe fill comprobado para esas observaciones.

Para evaluar el CE al lado correcto, se necesita una línea cronológica de *quotes* BID/ASK con fecha+huso verificados y su procedencia broker:
- Compra / LONG: una orden **buy limit** a precio CE sólo podría activarse cuando el **Ask** alcanzara CE o menos, sujeto a reglas reales de ejecución y confirmación de servidor.
- Venta / SHORT: una orden **sell limit** a CE sólo podría activarse cuando el **Bid** alcanzara CE o más, igualmente pendiente de confirmación.
- Posición LONG abierta se cierra contra BID; SHORT contra ASK, observando SL/TP y rechazos/latencia, slippage, tamaño tick/contrato.
- La vela OHLC M1 del NAS100 puede mostrar CE tocado sin mostrar ni **Ask** ni **Bid** del NDX100 y sin dar orden temporal intravela de target/stop/cancelación. **No inferir real orders, profit factor, drawdown, win rate de un snapshot**.

## Prerequisitos para Arquitecto OPS — entrega verificable, nunca datos inventados

1. Mapear equivalencia de **NDX100 MT5 ↔ NAS100 fuente**: nombre broker/servidor, contract specification, Digits, Point, TickSize, TickValue, moneda de ganancia, lot min/step/max, stops/freeze levels, sesiones y tipo del instrumento, timezone DST, horario de trading, si la fuente M1 NAS100 es del mismo proveedor y su correspondencia a precios BID/ASK.
2. Obtener historial real de cotizaciones **Bid, Ask, timestamp (preferentemente UTC + milisegundos), símbolo, broker/provenance** para la ventana pedida: identificar comienzo/fin, brechas, duplicados, horarios NY y días de noticias; evaluar retención histórica **antes de reclamar acceso a tres años**.
3. Capturar **paper/sandbox quote-feed** desde una conexión MT5 autorizada sólo para registro sin órdenes, con hashing, registro de latencia, eventos de sesión y conciliación M1; que no dependa de una captura manual cada minuto.
4. En ensayo A/B con fuente y símbolo compatibles, emitir `quote_bid <= quote_ask`, spread no negativo, saltos horarios/DST, quote freshness, expiración al final de ventana, OMS quote/ACK separado, cancel/ACK carrera, fills sólo por `ExternalExecutionAck`. Si no hay real historical ticks, **mantener 619 eventos ambiguos sin reinterpretarlos**.
5. Mantener **VT31 uno solo** (Londres y NY), Cognition/OPS producción sin cambios, riesgo CIBO/QDLE 0, Fresh Holdout SEALED y LIVE prohibido hasta certificación. No publicar ninguna información de cuenta visible en la captura de pantalla.

**Resultado disponible hoy:** cotización BID 30853.00 / ASK 30854.60, spread observado 1.60. **Histórico Bid/Ask probado de tres años: 0**. **Fills reales corroborados por la imagen: 0**. **Equivalencia del instrumento NAS100/NDX100: PENDIENTE.**

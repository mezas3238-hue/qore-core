# V34.12X — IC Markets TradingView vs IC Markets cTrader DEMO

**Corte 05-nov-2026 | Owner: ambas plataformas son IC Markets.**
**Estado: INVESTIGACIÓN. QA / READ ONLY / NO LIVE / NO MERGE / NO ALERTAS REALES / NO ÓRDENES.**

## Hallazgo arquitectónico
Que los 2 gráficos indiquen IC Markets hace plausible que exista parentesco entre los feeds, pero **NO demuestra identidad exacta de velas**. Cada proveedor/cuenta puede entregar máximos/mínimos, timestamps o sesiones distintos, particularmente M5 +1/+2 min en ciertos símbolos IC y H4 NY/DST. El indicador soberano V34.12X sí utiliza 34 símbolos con prefijo IC, pero su fuente visual puede diferir de la cuenta DEMO del VPS.

**Existe infraestructura reutilizable en QORE Core:**
- `src/qore/infrastructure/ctrader_open_api_client.py`: sesión autenticada Open API y cuenta DEMO.
- `src/qore/infrastructure/ctrader_open_api_market_data_client.py`: petición `ProtoOAGetTrendbarsReq`, M5, comprobación cuenta/symbol ID, formato relativo cTrader, fecha UTC en minutos.
- `src/qore/infrastructure/ctrader_demo_market_data.py`: validación de vela M5 *exacta* y reconstrucción OHLC.
- Esta ruta anterior procesa intervalos individuales con los contratos actuales; **todavía no se ha extraído una población batch 600×34 ni producido evidencia real comparada**. No confundir infraestructura disponible con integración operativa.

## Nuevo laboratorio creado — sin acceso a cuentas
- Comparador: `tools/crt_feed_parity/compare_ic_m5.py`
- Tests: `tests/research/test_crt_ic_m5_parity.py`
- Workflow CI: `.github/workflows/crt-ic-m5-candle-parity.yml`
- Solo recibe **dos CSV de velas M5 CERRADAS** por mercado y genera un JSON; no llama a TradingView ni a cTrader, no necesita claves, no emite alertas, no opera.
- Bloquea fechados sin zona horaria, símbolos impropios, orígenes cambiados, brókers falsos, OHLC inválidos, timestamps duplicados y velas sin cerrar.
- Compara **timestamps UTC exactos y OHLC con Decimal sin tolerancia oculta**. Reporta velas faltantes, diferencia de fase +0..+4m, discrepancias de OHLC y magnitud.
- Requiere 600 coincidencias por defecto; el resultado más favorable es **`SAMPLE_MATCH_ONLY`**, nunca «CERTIFIED», ya que no compara todavía reglas de CRT, MSS, FVG o detección en vivo. El JSON SIEMPRE devuelve `authorized_to_emit_v34_12x_alerts=false`.

## CSV de evidencia — contrato fijo

Cabecera exacta:
`origin,tv_symbol,broker,server,open_time_utc,open,high,low,close,closed`

Ejemplo ilustrativo de formato, NO es dato real de mercado:
`TRADINGVIEW_IC,IC:EURUSD,IC MARKETS,TV_IC_DATA,2026-11-05T10:00:00Z,1.10000,1.10100,1.09950,1.10050,true`
`CTRADER_IC_DEMO,IC:EURUSD,IC MARKETS,IC_CTRADER_DEMO_SERVER,2026-11-05T10:00:00Z,1.10000,1.10100,1.09950,1.10050,true`

La fila de cada fuente va en su propio archivo CSV; el campo `server` tiene que reflejar el ID real de feed/servidor (nunca mezclar varios). Los ejemplos NO se deben usar para certificar nada. La hora debe ser ISO-8601 con zona horaria UTC y la vela ha de estar cerrada.

Ejecución local:
`python -m tools.crt_feed_parity.compare_ic_m5 --tv tradingview-eurusd.csv --ctrader ctrader-eurusd.csv --symbol EURUSD --output parity-eurusd.json`

Código de salida 0 indica solo que la muestra coincide; 1 divergencia/insuficiencia; 2 estructura inválida.

## Plan mínimo para evidencia REAL y bloqueo actual
1. **VPS**: conectar el dispositivo autorizado vps-vrix de Desktop Commander (se observó OFFLINE, no se puede afirmar conexión al feed). No leer/escribir credenciales en chats o documentos.
2. **cTrader IC Markets DEMO**: confirmar servidor exacto, ID/símbolo de cada uno de los 34 instrumentos, número de dígitos y disponibilidad; usar el Open API existente exclusivamente en DEMO y exportar 600 velas M5 históricas **ya cerradas**, para un mismo periodo UTC. Respetar el límite oficial 5 solicitudes históricas/s/conexión.
3. **TradingView IC**: obtener una muestra autorizada del mismo `IC:EURUSD`, luego `IC:GBPUSD`, `IC:USDCAD`, `IC:BTCUSD`, `IC:XAUUSD`; idealmente CSV mediante **Download chart data** si la cuenta/interfaz lo permite. No inferir datos completos de screenshots; no usar scraping o credenciales fuera de las APIs autorizadas.
4. Ejecutar comparador; registrar resultado por mercado. Si algún proveedor difiere, **no atribuir a V34.12X** eventos de cTrader.
5. Incluso si 600 OHLC coinciden, ejecutar un segundo gate obligatorio de **paridad de señales**: 7 familias CRT, reconstrucción de H4 por 48 M5 consecutivas, C1/C2/C3, MSS M5/M15 propios, pivotes, PDH/PDL y FVG, fase de feed, historia y NY DST. Diferencia funcional: detener emisión.
6. **Solo después** conectar cTrader DEMO → Railway → QORE Mobile + widget, TTL 4 horas y avisos con tono/vibración elegibles. Señales observacionales/QA, no órdenes.

## Documentación oficial verificada
- cTrader Open API históricos + trendbars relativos: https://help.ctrader.com/open-api/es/symbol-data/
- cTrader intervalos/open times: https://help.ctrader.com/ctrader-algo/references/MarketData/Bars/Bars/
- TradingView exportación, cuando esté disponible: https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/
- IC Markets sobre integración cTrader y TradingView: https://www.icmarkets-global.com/es/help-resources/help-centre

**Recordatorio:** el laboratorio nuevo no demuestra que la fuente de TradingView y cTrader sea idéntica. Ninguna notificación real está activada.

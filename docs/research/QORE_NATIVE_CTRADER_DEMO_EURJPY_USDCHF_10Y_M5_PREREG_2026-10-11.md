# QORE Native — captura histórica cTrader DEMO de EURJPY y USDCHF

Fecha de prerregistro: **2026-10-11**. Research only. Esta nueva colección **NO** sustituye ni modifica los 12 originales del [CIBO Atlas 10Y, run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458). Iniciativa del propietario: descargar **EURJPY y USDCHF desde cTrader DEMO** para incorporar dos mercados adicionales al laboratorio de QORE.

## Fuente y ventana congeladas ANTES de descargar
- Cuenta: **única cuenta explícitamente DEMO** devuelta por `ctrader_demo_account_discovery`, con `isLive=false`. Si el ID en secrets difiere, fail closed.
- API: `demo.ctraderapi.com:5035`, SDK oficial de cTrader; lectura `ProtoOASymbolsListReq` → `ProtoOASymbolByIdReq` → `ProtoOAGetTrendbarsReq`; sin capacidad de envío de órdenes desde este script.
- Mapeo exacto a solicitar: EURJPY→EURJPY, USDCHF→USDCHF. Si falta, está disabled o símbolo no coincide exactamente, fallar, sin elegir sustitutos.
- **Timeframe:** M5 *provider-native* (no M1 ni reagrupación); rango `2016-09-17T00:00:00Z` hasta `2026-09-17T00:00:00Z` exclusivo, para alinear con los 12 mercados Atlas. El proveedor podría retornar menos años y se registrará la cobertura real, jamás se fingirán 10 años completos.
- Ventanas de siete días con `fromTimestamp` / `toTimestamp` *sin count*, corrección ya validada por el [Atlas 10Y](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458). No interpolar, forward-fill, crear velas sintéticas o saltar paquetes discordantes.
- Se reutiliza el algoritmo previamente verificado de lectura, manifiestos de partición, hashes SHA256, clasificación de duplicates/contradictions, y desglose de huecos, con identidad propia **QORE_NATIVE_CTRADER_DEMO_FOREX_M5_10Y_V1**. El consumidor base se cambia **solo en la memoria del proceso de investigación**, no en el repositorio original.
- Artefactos separados por símbolo, retenidos en Actions, con bytes brutos M5, SHA de particiones, manifiesto global, timestamps UTC y metadatos de proveedor. Retención de 90 días: copiar evidencia verificable a un archivo autorizado antes de vencimiento, sin commitear velas masivas ni secretos en git.

## Gates
- Quality: tests de símbolos exactos, ausencia de capacidades de trading, extensión isolada, rango fijo; Ruff/Pytest. 
- Per_symbol: revisar secrets sin imprimirlos; seleccionar/validar única cuenta DEMO y resolver símbolos por ID de esa cuenta; descargar 10Y M5; subir artefactos incluso si hay fallo parcial; el gate FAIL si fuente corrupta o manifest ausente.
- Si secrets/cuenta/API no disponibles, el resultado es **DOWNLOAD_BLOCKED**, no success.
- Si el cTrader DEMO devuelve sólo algunos años, informar ventana observada; no inferir error ni completar historia sintética.
- Si no hay M1 para los símbolos, seguirá bloqueado cualquier experimento que exija M1; este registro sólo acredita **M5**.
- No etiquetar esta fuente como OOS virgen: el periodo histórico coincide con datos de otras investigaciones; procedencia nueva ≠ periodo independentemente no visto.
- No se ejecutará ninguna señal, operación, monetización, PF, Sharpe o DD. No activar VPS, MT5, QDLE ni cuentas live. Condiciones broker IC Markets quedan pendientes de vinculación a cuenta/servidor; usar cTrader DEMO no basta para afirmar un broker específico.

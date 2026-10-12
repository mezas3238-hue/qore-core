# QORE Native G1 — fotografía solo lectura de contrato ACTUAL de los 12 símbolos originales

**Fecha 2026-10-12; experimento de metadata, no estudio económico.** Tras la prueba original de [PR #869](https://github.com/mezas3238-hue/qore-core/pull/869) (12/12 nombres+symbol IDs iguales en G0/G1), se congela *antes de solicitar nuevas especificaciones* una consulta cTrader DEMO **sólo de SymbolList y SymbolById para los 12 nombres de proveedor y IDs siguientes**:

`AUDJPY:11; AUDUSD:5; EURUSD:1; GBPJPY:7; GBPUSD:2; NAS100→USTEC:10014; SP500→US500:10013; US30:10015; USDCAD:8; USDJPY:4; XAGUSD:42; XAUUSD:41`.

Solo una cuenta explícitamente autenticada y comprobada `ICMARKETS_CTRADER_DEMO` con account `isLive=false`. No nombres aproximados, no fallbacks, no mezcla OAuth, no refresh, y cliente estrictamente limitado a Auth/SymbolsList/SymbolById: **nunca GetTickDataReq, GetTrendbarsReq, NewOrder, ModifyOrder, CancelOrder, SpotSubscribe, refresh**. Reporte no incluye tokens, IDs de cuenta ni nombres de persona.

## Campos y límites

Registrar `source_asof_utc`, `symbolId`, `symbolName`, `digits`, `pipPosition`, `lotSize`, `minVolume`, `stepVolume` y campos opcionales *brutos* `maxVolume`, `commission`, `commissionType`, `swapLong`, `swapShort`, `swapCalculationType`, `swapPeriod`, `baseAssetId`, `quoteAssetId`, `measurementUnits`, `tradingMode` si están presentes en el protobuf oficial del SDK; jamás inventar 0 si un campo está ausente. Faltar una propiedad opcional no autoriza imputación ni interpreta la unidad. Mantener los enteros nativos raw sin calcular comisión round-trip o swap monetario.

Coincidir `digits,pipPosition` con metadatos G0 solo acredita *compatibilidad de precisión*; `lotSize/minVolume` actuales no son prueba de sus valores históricos (2016–2026). Una especificación actual NO acredita cuenta original CIBO ni precios/fees históricos, ejecución, valor por punto, comisiones según tier/tamaño ni FX de conversión. **Nadie debe usar la fotografía para NET o certificación.** Esperar `CURRENT_BROKER_SPECS_SOURCE_CAPTURED_NOT_HISTORICALLY_EQUIVALENT`, contract gate BLOCKED, NET false y certified 0/3. Si un símbolo no existe exactamente, falla en vez de sustituirlo. El Github Action publica sólo metadata (Git repo es público; no precios comerciales, ni datos de la cuenta). Antes de ejecutar acción, probar controles sintéticos no pedidos/cuentas LIVE/IDs erróneos.

Protecciones: sin órdenes, sin VPS/MT5/LIVE/CIBO/Shared/QDLE. CIBO G0 histórico y costes #857, cero source #856, archivo licenciado #837 permanecen P0.

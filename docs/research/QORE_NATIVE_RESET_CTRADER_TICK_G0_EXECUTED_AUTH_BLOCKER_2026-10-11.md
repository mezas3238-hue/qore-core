# QORE RESET — cTrader DEMO native EURUSD ticks G0: ejecución y bloqueo real de autorización

Fecha **2026-10-11**. Directiva Owner: **datos solo de cTrader**. Fuente permitida: cTrader Open API de la cuenta DEMO original, sin Dukascopy ni sustitutos. Este reporte documenta una ejecución REAL de conectividad/captura, NO un resultado económico.

## Trabajo publicado

[PR #803](https://github.com/mezas3238-hue/qore-core/pull/803), rama `research/qore-native-reset-ctrader-tick-source-g0-20261011`. Prerregistro de cobertura/fechas anterior al primer acceso de red: `docs/research/QORE_NATIVE_RESET_CTRADER_DEMO_TICK_G0_PREREG_2026-10-11.md`, commit `4eda5ffcec4230193418de2507c9c7812f3efdde`. Módulo `src/qore/infrastructure/trader_lab/qore_native_reset_ctrader_tick_g0_v1.py`, tests y CI `.github/workflows/qore-native-reset-ctrader-demo-ticks-g0.yml`.

La API oficial [historical tick data](https://help.ctrader.com/open-api/symbol-data/) permite `ProtoOAGetTickDataReq` por `ctidTraderAccountId`, `symbolId`, `type BID/ASK`, `fromTimestamp`, `toTimestamp`; un máximo de **7 días por request**. Tick response newest-first con primera epoch-ms absoluta, siguientes diferencias ms y bandera de truncamiento `hasMore`. El módulo no es un convertidor M5→tick; analiza bytes/ticks que regrese **cTrader exclusivamente**.

## Ejecución de prueba

- [GitHub Actions #38177511169](https://github.com/mezas3238-hue/qore-core/actions/runs/38177511169), código `8ce45c5e675b3076fe2b1cba565930a8b2946956`.
- **code_gate SUCCESS**: Ruff PASS, pytest **9/9 PASS** (intervalos Europe/London con DST, fechas 2016–2026 congeladas, decode newest-first y escala 1e5, hasMore con partición sin pérdida, sello fail-closed si misma ms/limit, prohibición de órdenes y proveedores externos).
- **ctrader_ticks FAIL** en fase real de account-list: aplicación cTrader DEMO **se autenticó correctamente**, pero el servidor rechazó `ProtoOAGetAccountListByAccessTokenReq` usando el token inyectado por secretos Actions (`QORE_CTRADER_DEMO_ACCESS_TOKEN || QORE_CTRADER_ACCESS_TOKEN`). Archivo de audibilidad [artifact #11716900601](https://github.com/mezas3238-hue/qore-core/actions/runs/38177511169/artifacts/11716900601), manifest `SOURCE_G0_AUTH_OR_PROVIDER_BLOCKED`.
- **Ninguna** petición `ProtoOAGetTickDataReq` se envió. **CERO ticks de cTrader descargados**, y no se ha verificado cobertura histórica de fixing en 2016–2026. El símbolo original proveniente de CIBO fue recuperado desde [run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) para cotejar ID sin ejecutar otra captura M5.
- No faltan necesariamente client ID/secret: app-auth pasó. `QORE_CTRADER_DEMO_ACCOUNT_ID` apareció vacío en el job, pero la lógica puede descubrir la única cuenta DEMO si el access token autoriza account-list; **no fue la barrera observada**.
- A diferencia de la ruta Atlas anterior, esta ruta **NO invoca refreshToken**, porque el viejo Core lo actualiza solamente en RAM, con riesgo de rotación/invalidación si el secreto persistente de Actions no se actualiza. Intentos anteriores M5 [#38172092086](https://github.com/mezas3238-hue/qore-core/actions/runs/38172092086) y [#38172295246](https://github.com/mezas3238-hue/qore-core/actions/runs/38172295246) intentaron refresh con el par guardado y recibieron `cTrader access token invalid and refresh failed`. Repetir ciegamente ese refresh no es reparación.

## Qué distingue esto del material de GitHub que ya existe

El histórico CIBO de EURUSD en Actions es **M5 (745.458 velas)**, no una secuencia de timestamps tick nativos por BID y ASK. Para estudiar `±15min` al fixing con ticks, se necesita que la API autorice la consulta. Tener archivos M5 en GitHub permite reutilizarlos sin OAuth, **pero no hace posible construir retroactivamente tick real**.

## Disposición vinculante

`SOURCE_G0_AUTH_BLOCKED` → `G2_TICK_NOT_RUN`; RESET G1 original `DEV_GROSS_NO_SUPPORT` intacto. No abrir DRIVE/RELATIVE por esta puerta.

La reparación apropiada es **localizar el dueño de credenciales cTrader actualmente vigente dentro de Core** y conectar un *secret resolver* autorizado a GitHub Actions, o rehabilitar **una sola vez** el grant de la aplicación DEMO si el refresh vigente ya se perdió. El usuario no debe publicar secretos ni cuentas en issues/chat. GitHub App no permite leer los valores de los Secrets ni inventar un access token. Una vez exista una sesión autenticada, el job descargará **BID/ASK nativos cTrader**, auditará `hasMore`, hashes y cobertura; no se seleccionarán resultados económicos.

No VPS, no LIVE, no MT5, no QDLE, no Shared, no CIBO production, cero señales/traders autorizados. NO DEMO trade orders.

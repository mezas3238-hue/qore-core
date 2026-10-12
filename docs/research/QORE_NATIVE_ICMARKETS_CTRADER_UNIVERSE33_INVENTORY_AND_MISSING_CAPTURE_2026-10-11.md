# QORE Native — inventario verificable y ampliación IC Markets cTrader (33 instrumentos)

**Directiva Owner:** investigar índices, metales, majors y minors/crosses; conservar originales existentes y descargar sólo faltantes desde cTrader **IC Markets**. **Estado al redactar:** `RESEARCH_ONLY / NEW_CAPTURE_NOT_YET_CONFIRMED / SOURCE_BROKER_ACCOUNT_PENDING`. Nunca VPS, MT5, trading ni promoción.

## 1. Definición del cupo inicial y alcance

El **cupo inicial finito de 33 instrumentos** proviene de [Issue #574](https://github.com/mezas3238-hue/qore-core/issues/574) (3 índices + 2 metales + 7 mayores FX + 21 crosses menores FX). **NO significa que IC Markets cTrader ofrezca solamente estos símbolos**: la lista total de índices/metales del broker depende del servidor, tipo de cuenta y catálogo. Hasta recibir el catálogo autenticado no es lícito afirmar que este cupo es exhaustivo de todos los CFD/índices/metales de IC Markets. Una eventual fase **V2** para más índices/metales debe congelar una nueva lista, no manipular V1 por retornos.

**Cupo índice:** NAS100, SP500, US30.  
**Metales:** XAUUSD, XAGUSD.  
**7 majors:** EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD.  
**21 cruces/minors:** EURGBP, EURJPY, EURCHF, EURCAD, EURAUD, EURNZD, GBPJPY, GBPCHF, GBPCAD, GBPAUD, GBPNZD, AUDJPY, AUDCAD, AUDCHF, AUDNZD, CADJPY, CADCHF, CHFJPY, NZDJPY, NZDCAD, NZDCHF.

## 2. Fuentes realmente conservadas en GitHub

Se comprobó en GitHub **existencia/no-expiración de artefactos**, con los hashes/identidades originales documentados. No se declara cuenta IC Markets exacta de origen de todos los archivos; la etiqueta DEMO y símbolos históricos del consumidor CIBO **no bastan para eso**.

| Familia | M5 diez años, ya disponible | M1 diez años, ya disponible | M5 parcial siete años |
|---|---|---|---|
| Índices | NAS100, SP500, US30 | NAS100 | — |
| Metales | XAUUSD, XAGUSD | XAUUSD | — |
| FX mayores | EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD | los mismos 5 | USDCHF |
| FX menores | AUDJPY, GBPJPY | AUDJPY, GBPJPY | EURJPY |
| **Totales** | **12** | **9** | **2** |

**Origen M5/12:** [Actions run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), commit `ab782b8e9f890f86a2b6500070f0556b4b685e3d`, 12 artefactos por instrumento (XAGUSD/SP500/US30 incluidos), horizonte objetivo 2016-09-17 → 2026-09-17. Datos provistos históricamente por cTrader DEMO; no se cambia fuente.

**Origen M1/9:** [Actions #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), commit `18c338aedd5013ce65a6cb6408ffbc2e904a6217`, nueve artefactos nativos M1 históricos para 2016-09-17 → 2026-09-17, sin sintetizar M1 desde M5.

**Origen M5/7Y EURJPY/USDCHF:** [Actions #36079229139](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139), artefactos EURJPY `#10840979795`, USDCHF `#10840849959`, primer M5 2019-09-27 y último hacia 2026-09-25. [Auditoría 3/3](https://github.com/mezas3238-hue/qore-core/actions/runs/38173077639) corroboró metadata DEMO; datos están parcialmente **reservados para VT08** y no pueden usarse como OOS QORE Native nuevo. Los 7 años no son equivalentes a diez años ni constituyen M1 diez años.

## 3. Brechas concretas sin descargas redundantes

**M5 10Y, 21 capturas o extensiones pendientes**:
- Majors (2): `NZDUSD` (no está en las fuentes archivadas inspeccionadas), `USDCHF` (extensión 7→10Y, SIN destruir el 7Y).
- Crosses (19): `EURGBP EURJPY EURCHF EURCAD EURAUD EURNZD GBPCHF GBPCAD GBPAUD GBPNZD AUDCAD AUDCHF AUDNZD CADJPY CADCHF CHFJPY NZDJPY NZDCAD NZDCHF` (`EURJPY` 7Y, otros 18 no archivados en los tres conjuntos verificados).

**M1 10Y, 24 instrumentos sin artefacto equivalente**: `SP500 US30 XAGUSD USDCHF NZDUSD EURGBP EURJPY EURCHF EURCAD EURAUD EURNZD GBPCHF GBPCAD GBPAUD GBPNZD AUDCAD AUDCHF AUDNZD CADJPY CADCHF CHFJPY NZDJPY NZDCAD NZDCHF`.

**M5 no encontrado en los tres orígenes verificados:** 19. Es estado de *estos orígenes de GitHub*, NO afirma que Core jamás haya guardado una copia en otra rama/retención.

La nueva workflow captura primero la brecha M5. La extensión M1 de los 24 se realizará como segundo trabajo **no autorizado aún** hasta resolver fuente/credenciales/capacidad; por tanto no se informa M1 inexistente en el mercado.

## 4. Recuperación estricta desde IC Markets DEMO — GitHub only

Código:
- [Inventario automatizado](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-universe-33-icmarkets-ctrader-capture-20261011/src/qore/infrastructure/trader_lab/qore_native_universe_33_source_registry_v1.py).
- [Catalog gate sin renovar OAuth](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-universe-33-icmarkets-ctrader-capture-20261011/src/qore/infrastructure/trader_lab/qore_native_icmarkets_catalog_preflight_v1.py).
- [Descargador M5 original por ventanas 7d](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-universe-33-icmarkets-ctrader-capture-20261011/src/qore/infrastructure/trader_lab/qore_native_icmarkets_missing_m5_capture_v1.py).
- [Workflow fuente→DEMObroker→21 instrumentos](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-universe-33-icmarkets-ctrader-capture-20261011/.github/workflows/qore-native-icmarkets-33-universe-m5-missing-capture.yml).

**Puerta IC Markets innegociable:** (a) exactamente un grant completo (DEMO o alias genérico, nunca mezcla), (b) TLS oficial DEMO, (c) `ProtoOAGetAccountListByAccessTokenReq` sin refresh, (d) cuenta explícitamente `isLive=false`, **brokerTitleShort contiene IC Markets**, único match, (e) permiso VIEW=0 o TRADE=1 de cuenta, pero CERO mensajes de órdenes, (f) `ProtoOASymbolsListReq` con `symbolName` **exactamente** igual al símbolo a descargar y `symbolId` válido, (g) respuesta de tendencia provider-native 10Y con manifiestos originales, sin rellenos, SHA-256 y controles de account/data.

**Notas de seguridad:** la cuenta IC Markets no debe deducirse de un cTrader Demo genérico, ni transferir credenciales de otro broker. Los alias históricos `NAS100=USTEC`, `SP500=US500` no deben imponerse a una cuenta nueva sin catálogo. El workflow desactiva el refresh de tokens desde el código, para no invalidar secretos persistidos en GitHub Actions, y ejecuta matrices secuencialmente, nunca negociando. Los datos crudos van a artifacts, no a commits Git; no entrar a VPS o MT5.

**Bloqueo conocido antes del nuevo intento:** [informe autenticación previo](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-ctrader-demo-eurjpy-usdchf-m5-20261011/docs/research/QORE_NATIVE_CTRADER_CORE_EXISTING_7Y_AND_AUTH_LIFECYCLE_ADJUDICATION_2026-10-11.md): attempts [#38172092086](https://github.com/mezas3238-hue/qore-core/actions/runs/38172092086) y [#38172295246](https://github.com/mezas3238-hue/qore-core/actions/runs/38172295246) fallaron **antes de descargar** por token invalidado/refresh. La nueva ruta no intenta renovar tokens porque el refresh previo se hacía únicamente en memoria, sin vault persistente; hacerlo podría invalidar otros workflows de Core. Si esta puerta falla, reportar `AUTH_BLOCKED` y mantener `0_NEW_CAPTURE` — sin simular éxito ni reclamar ausencia de símbolos.

## 5. Programa de datos vs estrategia

Este es **source-only**, no un grid de 33 pruebas de edge. Incluir 33 activos NO multiplica los falsos positivos sin control: futuras pruebas requieren hipótesis económica predefinida, agrupación FX por moneda compartida, controles por clase, multiplicidad y holdout independiente. La cobertura de instrumentos y la certificación de estrategias son trabajos diferentes.

**Aprobación para crear archivos históricos read-only en GitHub: sí (directiva Owner). Promoción a Trader, PAPER, VPS, órdenes y LIVE: NO.**


## 6. RESULTADO DE LA CAPTURA SOLICITADA — EJECUTADO Y BLOQUEADO POR TOKEN

**Evidencia final de GitHub Actions:** [run #38191796877](https://github.com/mezas3238-hue/qore-core/actions/runs/38191796877), commit probado `043151189b73483b0dc7a886c812265e81d767e2`.

- `offline_inventory_contract=SUCCESS`: catálogo QORE de 33 generado, pruebas sintéticas y Ruff correctas.
- `broker_catalog_gate=FAILURE`: el informe seguro (sin credenciales) y los logs dieron exactamente `CTRADER_ACCESS_TOKEN_INVALID_NO_REFRESH_ATTEMPTED`. El antiguo access token presente en GitHub Actions fue rechazado por cTrader al solicitar la lista de cuentas; el código **NO solicitó una renovación** para no invalidar credenciales por refresh sin persistencia.
- `capture_missing_m5=SKIPPED` por dependencia correcta del gate. **0/21 archivos M5 nuevos**, **0/24 archivos M1 nuevos**. No se conoce catálogo real ni asociación confirmada con broker IC Markets: ambos deben permanecer `UNVERIFIED`.
- No se exige volver a copiar M5 de los doce del Atlas o EURJPY/USDCHF 7Y: todos los artefactos anteriores permanecen intactos.

**P0 para permitir descargas reales:** recuperar/reautorizar un grant cTrader de la **cuenta IC Markets DEMO exacta** con permiso `accounts`/view y actualizar el secreto correspondiente bajo GitHub Actions/vault con rotación **atómica y persistente** del access+refresh; no revelar datos secretos en Issue, PR ni chat. Después una ejecución nueva podrá obtener `brokerTitleShort` y el catálogo nativo y, solo si demuestra IC Markets DEMO, habilitar el trabajo de captura. Sin ese paso, repetir el workflow por fuerza bruta NO resuelve el bloqueo.

**Prueba de honestidad:** `CAPTURE_BLOCKED_AUTH` ≠ `ICMARKETS_SYMBOL_UNAVAILABLE`. El rechazo no permite concluir que NZDUSD ni los cruces no existan en el broker. No afirmar un dato descargado que no fue realmente recibido.


## 7. Retest después de restablecer OAuth — fuente validada; lectura histórica en ejecución

El Owner actualizó credenciales en GitHub. En el reintento [#38191796877](https://github.com/mezas3238-hue/qore-core/actions/runs/38191796877), la autorización de aplicación y access token pasó: se superó `CTRADER_ACCESS_TOKEN_INVALID_NO_REFRESH_ATTEMPTED`, pero el campo OPCIONAL `brokerTitleShort` de la respuesta account-list no vino informado. La documentación oficial de Spotware lo enumera como campo opcional. **Se añadió verificación alternativa segura vía `ProtoOATraderReq → trader.brokerName` de la cuenta previamente autenticada**, manteniendo IC Markets DEMO como requisito obligatorio.

[CI #38193509746](https://github.com/mezas3238-hue/qore-core/actions/runs/38193509746) confirmó `offline_inventory_contract=SUCCESS` y `broker_catalog_gate=SUCCESS`. **IC Markets DEMO y catálogo sí quedaron verificados**. Los primeros intentos EURJPY/USDCHF/NZDUSD del download heredado fallaron por otra incompatibilidad que ya conocía el equipo: `cTrader token lacks trading permission or account evidence`, porque el cliente operativo CIBO exige permiso TRADE incluso para leer históricos. Esa política de producción **NO debe cambiarse** para este trabajo.

**Corrección aislada:** se creó un adaptador `_ReadOnlyIcMarketsHistoryClient` solamente en el lector histórico QORE Native, admitiendo `SCOPE_VIEW=0` o `SCOPE_TRADE=1` para cuentas explícitamente DEMO y rechazando refresh; no se ha permitido envío de órdenes ni modificado el SDK operativo común. Se agregaron tests de rechazo de scope inválido y refresh, y el workflow cancela ejecuciones obsoletas para no volver a descargar el mismo símbolo.

**CI vigente del adaptador:** [run #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), commit `e0ca5a13c866a19d8505c68cffc473598984b340`. Hasta verificar cada artefacto/M5 real el conteo de capturas nuevas certificadas permanece en **cero**. No atribuir una nueva falla de captura al OAuth ya rehabilitado.

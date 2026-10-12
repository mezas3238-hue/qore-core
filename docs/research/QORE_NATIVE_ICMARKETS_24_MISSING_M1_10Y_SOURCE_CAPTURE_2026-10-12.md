# QORE Native — captura 24 M1 nativas (IC Markets cTrader DEMO)

**Fecha:** 2026-10-12 · **Programa:** [#789](https://github.com/mezas3238-hue/qore-core/issues/789) · [#812](https://github.com/mezas3238-hue/qore-core/issues/812) · [M5 33/33 CI #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541). **Misión:** equiparar la cobertura nativa M1 a los 33 instrumentos del cupo V1, sin trading, VPS ni OOS declaradamente virgen.

## Fotografía previa verificable

El M5 10Y de los **33** está guardado en 12 archivos CIBO del Atlas + **21 nuevas capturas reales IC Markets DEMO** ([workflow 23/23 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), 21 artefactos no expirados al 12-oct-2026).

El M1 10Y de **9** originales existe en [Capitalizer CIBO Native #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), commit fuente `18c338aedd5013ce65a6cb6408ffbc2e904a6217`: AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, USDCAD, USDJPY, NAS100/USTEC, XAUUSD. Son archivos históricos **ya estudiados**, no fold OOS fresco.

**24 M1 ausentes de esos artefactos M1:** SP500, US30, XAGUSD, USDCHF, NZDUSD, EURGBP, EURJPY, EURCHF, EURCAD, EURAUD, EURNZD, GBPCHF, GBPCAD, GBPAUD, GBPNZD, AUDCAD, AUDCHF, AUDNZD, CADJPY, CADCHF, CHFJPY, NZDJPY, NZDCAD, NZDCHF.

## Contrato de captura pre-resultados

1. **Identidad nueva:** `QORE_NATIVE_ICMARKETS_DEMO_24_MISSING_NATIVE_M1_10Y_V1`, horario UTC `[2016-09-17T00:00Z, 2026-09-17T00:00Z)`. El objetivo significa **ventana de petición**, NO minutos de calendario 100% disponibles. No relleno, interpolación ni reconstrucción desde M5.
2. **Fuente sin ambigüedad:** cuenta IC Markets cTrader DEMO autenticada, identificador efímero y brokerName proveniente de [preflight](../research/QORE_NATIVE_ICMARKETS_CTRADER_UNIVERSE33_INVENTORY_AND_MISSING_CAPTURE_2026-10-11.md). Solo permisos de lectura, sin trading, sin refresh de token en RAM, sin secretos en GitHub artifacts.
3. **Resolución:** `ProtoOAGetTrendbarsReq period=1`, ventana ≤2 días exacta (2.880 minutos), sin `count`, timestamp UTC nativo y OHLC relativo al proveedor. Dedupe del mismo minuto solo si payloads idénticos; OHLC contradictorio aborta. Guardar JSONL por año más digest SHA256, manifiesto SHA y metadatos de proveedor.
4. **Mapeo:** símbolo y provider exactos para 23 activos. Excepción **SP500→US500** basada en proveedor histórico del mismo Atlas CIBO 10Y, pero solo si el catálogo del account IC Markets DEMO actual contiene `US500` habilitado e identidad `symbolId` real. **Prohibido** inferir un alias tras resultados.
5. **Gates antes de guardado válido:** exactamente 24 símbolos faltantes (nunca sobrescribir los 9), un símbolo único por job, ID de fuente concordante, `retained_m1>0`, 11 particiones anuales por periodo solicitado, comprobación SHA de CADA año y el manifiesto, `synthetic_m1=false`, sin autorización de LIVE/DEMO transaccional/CIBO/Shared/QDLE/MT5.
6. **Pilot conservador y diverso:** SP500, XAGUSD y NZDUSD primero para adjudicar alias de índice, horarios de metales y FX. Despliegue 21 restantes en un nuevo commit y run **solo después de GREEN verificable del piloto**. No duplicar capturas ya completadas.
7. **Retención:** GitHub Actions artifact configurado a 90 días. Esto **NO cumple durabilidad indefinida**. Antes del vencimiento hay que copiar 33×M5 y 33×M1 al almacén canónico con versión, permisos, digest por archivo y política de retención; prohibido reportar que el proyecto tiene 10 años almacenados permanentemente solo porque un run es SUCCESS.

## Auditoría

Los archivos heredados del consumidor Capitalizer fueron copiados/aislados en `src/qore/infrastructure/trader_lab/qore_native_icmarkets_missing_m1_capture_v1.py`, no se cambiaron nombres de funciones del CIBO original en producción. Autenticación M1 reutiliza la clase `_ReadOnlyIcMarketsHistoryClient` exclusiva de investigación desarrollada tras el fallo con `SCOPE_VIEW=0` en la captura M5. La identidad exacta de fuente se comprueba de nuevo **por cada símbolo**, no se asume por aprobación de job anterior.

Workflow [QORE Native IC Markets 24 Missing Native M1](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-icmarkets-universe33-m1-capture-20261012/.github/workflows/qore-native-icmarkets-24-missing-m1-capture.yml) con captura piloto tras Ruff y pruebas unitarias. Run primer piloto [#38262534602](https://github.com/mezas3238-hue/qore-core/actions/runs/38262534602), congelado en commit `07a5d897703641ccf8317688f6abcdfb55b5766f` antes de recuperar velas del nuevo ensayo.

**Cualquier volumen o comportamiento de retorno que luego se abra es evidencia consumida, NO holdout OOS virgen ni criterio de selección ex post.**

## Estado inicial

`M5_33_OF_33_ARCHIVED`; `M1_9_OF_33_PREVIOUSLY_ARCHIVED`; `M1_24_NEW_REQUESTED`; `PILOT_3_IN_GITHUB_CI`; `FULL_21_NEEDS_GREEN_PILOT`; `NO_LIVE`; `NO_NEW_EDGE_EVIDENCE`.

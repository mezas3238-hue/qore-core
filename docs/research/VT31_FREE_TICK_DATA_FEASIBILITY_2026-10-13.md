# VT31 / NAS100 — G5 factibilidad gratuita de BID/ASK histórico con cTrader Open API

**13 octubre 2026 · Investigación de disponibilidad; NO reconstrucción V1, NO replay, NO PnL, NO autorización LIVE.**

## Resultado resumido — test de acceso real, NO resultado económico

- **CI de la primera sonda que consulta broker**: [GitHub Actions #38374410345 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38374410345), commit de prueba `64e7c22b997d727bbb938f2875e131bb1f27c173`, artifact `11800358236`. **11/11 tests sintéticos PASS**, Ruff+compile PASS, SHA256 manifest PASS.
- **Resultado observado contra cTrader DEMO efectivamente conectado**: `BLOCKED_EXACT_SYMBOL_ABSENT_OR_AMBIGUOUS`. La lista de símbolos habilitados de **esta cuenta** no contiene `NAS100`. Una exploración limitada a nombres habilitados que coinciden con `NAS|NDX|US.?100|TECH.?100` devolvió **lista vacía**. **No se descargó ninguna cotización BID/ASK real de NAS100**, ni siquiera un intervalo de 15 minutos. Esta ausencia es un hecho de esa cuenta/token, **NO prueba que el broker IC Markets u otros carezcan de NAS100**, ni que no pueda llamarse de otra forma.
- El token existente da acceso de consulta a cuenta DEMO pero **no tiene `SCOPE_TRADE`**. El SDK cliente original QORE rechazaba `SCOPE_VIEW` incluso para datos. En carril experimental se añadió cliente **`read_only=True`** con dos garantías: acepta `SCOPE_VIEW` en cuenta DEMO validada; prohíbe por allowlist **todos los mensajes de escritura**, incluidos new/cancel/amend/close. **El modo normal trading sigue exigiendo `SCOPE_TRADE`; no se rebajó el gate del cliente operativo.** Se permite descubrir una sola DEMO con `QORE_VT31_READ_ONLY_SCOPE=true` opt-in aislado; el default del descubridor no cambió. No habilita live.
- **Resultado de estrategia**: `EDGE_ECONOMIC_NOT_IDENTIFIED`, **NO `NO_EDGE`**. Se necesitaba exactamente cotejar datos históricos BID/ASK del mismo broker/símbolo. No se logró con ese entorno.

## Evidencia negativa previa que SÍ existe

La prueba preregistrada antes del resultado sobre la antigua cohorte de **2.140 oportunidades**, usando el siguiente M1 Open y **15 minutos predefinidos** (no LIMIT CE ni fills), produjo **−1,919664 puntos medios BRUTOS por señal**, y **−3,519664 puntos con coste HIPOTÉTICO fijo 1,60** (transferido de una imagen NDX100, NO verificado como spread NAS100). Los horizontes exploratorios 5, 30 y 60 min también presentan media bruta negativa. CI OPS #38310949637/#38311120068 y [informe original](VT31_EDGE_DIRECTIONAL_PREREGISTERED_3Y_RESULT_2026-10-12.md). **Esto debilita la tesis de edge direccional al cierre FVG**, pero NO es el ensayo del protocolo G3 V1 (reentrada CE LIMIT + C2 stop). No invertir automáticamente dirección ni escoger ventana/horizonte por rentabilidad observada.

Dataset fuente original: **1.059.784 M1 OHLC desarrollo 2023-10-01 a 2026-10-01**, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. Una M1 OHLC **no identifica** ejecución real: 619 old-B conflictos same-M1 pendientes y 51 invalid protected swing B se mantienen archivados, sin recodificación ni aproximación como rentabilidad V1. La única muestra MT5 NDX100 publicada como metadatos corresponde a un trade aislado, no series BID/ASK ni prueba de equivalencia de símbolo.

## API oficial y condiciones

- Fuente oficial: [cTrader Open API · Attain symbol data](https://help.ctrader.com/open-api/symbol-data/). `ProtoOAGetTickDataReq` necesita `ctidTraderAccountId`, `symbolId`, `type` BID (1) o ASK (2), ventana UTC en milisegundos. **Límite de UNA SEMANA POR PETICIÓN**, no necesariamente límite de antigüedad almacenada. `hasMore` exige paginación; no interpretar primer bloque como cobertura completa.
- Fuente oficial: [mensajes `ProtoOAGetTickDataRes`](https://help.ctrader.com/open-api/messages/). Los ticks se devuelven **newest-first**, tiempo absoluto en primer registro y deltas para los anteriores; el lector verifica orden/tiempos, cuenta/símbolo y rechaza valores corruptos.
- Sonda propuesta pre-G3: cuatro intervalos **15 min** del 10-oct-2023, 8-oct-2024, 7-oct-2025, 15-sep-2026, cada uno BID y ASK, sin disponer ni inferir fills; **el programa no adquiere 3 años de ticks, no compra datos, no envía ninguna orden**. Aun con 8 segmentos devueltos sin huecos, estado `PILOT_BOTH_SIDES_PRESENT_NONCERTIFIED`: muestra puntual, no cobertura total.

## Bloqueos G5 medibles

| Dimensión | Evidencia al 13-10-2026 | Dictamen |
|---|---|---|
| Fuente 3Y OHLC NAS100 | Sí (1.059.784 M1, SHA congelado) | Fuente exploratoria, NO fills |
| Existencia símbolo NAS100 exacto en DEMO conectado | NO — `BLOCKED_EXACT_SYMBOL_ABSENT_OR_AMBIGUOUS` | **BLOQUEO G5** |
| Otro símbolo índice compatible en listado habilitado | Ningún nombre coincidente con patrones observados; búsqueda limitada | No inferir equivalencia |
| BID/ASK NAS100 2023–2026 con cronología completa | No verificado; 0 muestras adquiridas | **NO IDENTIFICADO** |
| Mismo broker/símbolo/contrato que la M1 congelada | No certificado; nombre no basta | **BLOQUEO G5** |
| Tick_size, rejilla/origen, tick_value/lote/moneda, fees | Sin `symbol_info` oficial reconciliado | **BLOQUEO G5** |
| OMS/ACK, LIMIT CE, C2 SL, salida 15:55 | Nuevas reglas V1 no integradas/firmadas | **BLOQUEO G6** |
| Prueba direccional preregistrada a 15min | −1,919664 pts brutos sobre 2.140 *antiguos* | Desfavorable, no edge CE |
| Holdout y LIVE | Sellado / prohibido | SIN CAMBIOS |

## Próximo protocolo sin coste (no habilitado aún)

1. **Conseguir acceso DEMO y permisos de sólo lectura en una cuenta de broker que cotice el NAS100 exacto**, o una designación de nombre y contrato respaldada por documentación primaria. Es una tarea de datos, no pedir $125 ni operar real. No inferir equivalencia NAS100/NDX100/US100 por correlación o nombre. La variable GitHub `QORE_VT31_CTRADER_SYMBOL` selecciona el símbolo literal para **sonda**, no certifica equivalencia.
2. Repetir una única sonda BID/ASK de muestras 2023–2026; si no existe tick 2023, documentar retention-gap no fabricarlo. Si `hasMore`, paginar con límite estricto y hash de cada archivo en carril nuevo aprobado. Cobertura de las **3 ventanas Silver Bullet con posiciones extendidas hasta 15:55 NY**, misma timezone y USD/DST, sin sesgo de selección.
3. **Sólo** con los **dos signoffs independientes** COG/OPS sobre pareja G3 r1.3 **doc=`a446afa17ed6e411b8f0b6fc182b103a78959a97` + code=`78d4cdac0e09d1a6eef37b99c505ffc5098031fc`**, llevar a PR nuevo la **implementación integral** C2_FULL_WICK, 1 tick, mínimo 2 ticks, primer FVG, CE LIMIT, OMS/cancel/ACK, sin 2ª entrada, time-exit y su propia revisión adversarial. Ni el probe de datos ni 11 tests habilitan replay.
4. Preregistrar costes, slippage, no-fills, política de UNKNOWN y muestra de confirmación independiente. **Evaluación sobre 3Y ya usado será exploratoria**, no prueba OOS. Edge real sólo si net expectancy y PF/DD/robustez sobre operaciones económicamente identificadas supera gates Core y luego aguanta holdout autorizado.

**Criterio de parada honesto:** mientras G3 no esté firmado y la fuente exacta BID/ASK no esté acreditada, declarar `DATA_INSUFFICIENT_TO_DETERMINE_VT31_CE_EDGE`; no declarar ganancias ni certificar, tampoco falsación general de ICT Silver Bullet.

**Frontera de código:** investigación independiente en `agent/vt31-g5-free-ctrader-tick-availability-20261013`. La edición de `ctrader_open_api_client.py` y `ctrader_demo_account_discovery.py` existe **sólo en la rama aislada** y requiere revisión de seguridad/compatibilidad antes de merge; no toca PR #896, sus SHA, main, trading LIVE, VPS, OMS ni la fuente 3Y.

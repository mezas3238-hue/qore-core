# Londres Issue #777 — T0 BID/ASK tick: dos ensayos reales, resultados y bloqueo de broker

**Fecha:** 2026-10-11 · **Estado:** `EXTERNAL_TICK_PARTIAL_EVIDENCE / BROKER_EXECUTION_UNRESOLVED` · **Solo EURUSD y GBPUSD / Londres**.

Esta auditoría es ejecutada, no una lista de tareas. No altera ninguna señal L1/L2, V49, DCVC, stop, target, VPS o producción. **No se han recalculado PF ni rendimientos certificados.**

## 1. Fuentes originales congeladas y control reproducible

- Estudio London L1/L2 original [Issue #775](https://github.com/mezas3238-hue/qore-core/issues/775), [PR #776](https://github.com/mezas3238-hue/qore-core/pull/776), [run final #38146670174](https://github.com/mezas3238-hue/qore-core/actions/runs/38146670174), código original SHA `8f358f80bcc18ff9bafea75a95d111404de57537`; 358 señales, **34 velas M1 dual-touch**: EURUSD 18 (L1=11, L2=7), GBPUSD 16 (L1=8, L2=8).
- [PR #778](https://github.com/mezas3238-hue/qore-core/pull/778) contiene código fuente `src/qore/infrastructure/trader_lab/qore_london_tick_t0_probe_v1.py`, pruebas sin red y workflow `qore-london-t0-public-bidask-tick-probe.yml`. Contrato test de `.bi5` big-endian 20-byte, UTC milliseconds, ask/bid, validación `bid <= ask`, timestamp monotónico, SHA256 de archivo y resolución por precio-side (LONG sale BID; SHORT sale ASK). **Seis pruebas / seis aprobadas** y Ruff sin errores, reproducido en ambos runs.
- Fuente tick externa: **Dukascopy legacy public** `https://www.dukascopy.com/datafeed/{PAIR}/{YYYY}/{MM-1}/{DD}/{HH}h_ticks.bi5` (formato histórico). **No es el feed original del M1 congelado ni una confirmación de broker, ni ejecución/orden/deal**. Se guarda evidencia identificadora y métricas de las horas consultadas, no archivos binarios redistribuidos.

## 2. Ejecución #1: prueba acotada sobre 4 casos — evidencia disponible

[Actions #38148314083, SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38148314083), [artefacto #11705585862](https://github.com/mezas3238-hue/qore-core/actions/runs/38148314083/artifacts/11705585862), commit `6bd835a9c11d8e04f872db844dc5a1517ab8ab66`.

Se eligieron los **dos primeros casos dual-touch cronológicos por par**, no seleccionados según resultado económico. Cuatro de cuatro horas históricas respondieron con ticks válidos (además dos horas de fixture independiente):

| Símbolo | Fecha UTC | Trigger | Resultado primer contacto OBSERVADO en quotes externos | Spread mediano/hora | Stop original |
|---|---|---|---|---:|---:|
| EURUSD | 2025-10-07 | L2 | STOP observado primero | 0,35 pips | 0,2 pips |
| EURUSD | 2025-11-11 | L2 | TARGET observado primero | 0,30 pips | 1,1 pips |
| GBPUSD | 2025-11-27 | L2 | STOP observado primero | 0,50 pips | 0,5 pips |
| GBPUSD | 2025-12-01 | L2 | STOP observado primero | 0,70 pips | 1,8 pips |

Los SHA256 de cada fichero y los tiempos exactos de ticks están en el artefacto JSON. **3 STOP y 1 TARGET observados en fuente externa**, no fills broker. La coincidencia original entre M1 y quote externa NO ha sido certificada.

## 3. Ejecución #2: intento exhaustivo de los 34 — fuente HTTP limitada

[Actions #38148719772, SUCCESS del código/ejecución](https://github.com/mezas3238-hue/qore-core/actions/runs/38148719772), [artefacto #11706525596](https://github.com/mezas3238-hue/qore-core/actions/runs/38148719772/artifacts/11706525596), código SHA `48c92112650e712554239ace493d18e662f0edaa`.

Se auditaron **los 34 casos congelados**: 18 EURUSD y 16 GBPUSD; 36 consultas distintas a source-hour contando dos fixtures independientes. La descarga pública devolvió **3/34 horas quote válidas** y **31/34 sin archivo recuperable EN ESTE RUN**, con errores HTTP **503 Service Unavailable** y algunos timeouts. La fixture también obtuvo 503 en ambos pares. **HTTP 503 NO significa que los datos históricos no existan**: significa que el servidor no respondió satisfactoriamente durante esta ejecución. El job es SUCCESS porque reportó explícitamente los errores, sin imputar quotes ni inventar fills.

Tres casos adicionales y distintos de los cuatro iniciales:

| Símbolo | Fecha UTC | Trigger | Resultado primero en quotes externos | Spread mediano/hora | Stop original |
|---|---|---|---|---:|---:|
| EURUSD | 2026-04-24 | L2 | STOP observado primero | 0,30 pips | 0,1 pips |
| EURUSD | 2026-05-29 | L1 | STOP observado primero | 0,30 pips | 0,7 pips |
| GBPUSD | 2026-04-21 | L2 | STOP observado primero | 0,70 pips | 0,3 pips |

**Unión de las dos ejecuciones:** evidencia quote externa verificable para **7 casos distintos de 34** (EURUSD 4, GBPUSD 3): **6 STOP primero / 1 TARGET primero OBSERVADO**, y **27 restantes sin ticks recuperados en las dos pasadas**. No combinar los dos runs como si el endpoint tuviera disponibilidad estable; la segunda ejecución no consiguió rescatar cuatro casos válidos de la primera por 503.

En **4 de estos 7 casos**, el **spread mediano de la hora en el feed EXTERNO iguala o excede la distancia del stop original** (ejemplos extremos EUR 0,1 pips stop vs 0,3 spread, GBP 0,3 vs 0,7). Esto es **evidencia orientativa sobre escalas**, NO coste transaccional real medido ni slippage. Datos condicionados a siete casos originalmente ambiguos: no inferir distribución de costes de las 358 operaciones.

## 4. Limitaciones que deben permanecer explícitas

1. **Cross-provider:** los ticks Dukascopy no prueban que esas barreras fueran tocadas en idéntico orden por el proveedor del M1 original ni por FundedNext/MT5/cTrader. Incluso cuando la secuencia externa toca STOP/TARGET, el resultado **no se incorpora a P&L V49/L1/L2**.
2. **Sin ejecución física:** no hay broker Bid/Ask histórico verificable para la cohorte, ni latencia ni tickets de fills/deals para estimar slippage. No asignar PF, WR, esperanza ni rentabilidad física.
3. **Datos parciales de descarga:** 503 y timeouts de segunda pasada son problemas de acceso/rate limits potenciales, no prueba de no existencia ni huecos reales en la cotización histórica.
4. **Muestra no representativa:** se examina deliberadamente el subconjunto dual-touch, y primero cuatro casos cronológicos; no inferir comportamiento de todos los días ni de L1/L2 completos.
5. **Calidad temporal:** mili-segundos y BID/ASK fueron validados para los ficheros recuperados; el primer tick registrado de la vela no prueba fill en el instante de orden.

## 5. Veredicto de pruebas y siguiente gate estrictamente condicionado

- **`T0_CODE_AND_PUBLIC_QUOTE_PROBE_PASS_PARTIAL`**: al menos siete archivos distintos de dos FX majors decodificados; tests offline PASS; SHA y archivo; ratios spread/stop medidos **externamente**.
- **`T0_LONDON_FULL_HISTORICAL_QUOTE_COVERAGE_NOT_PROVEN`**: 27 ambigüedades sin archivo actual recuperado (servidor 503).
- **`T1_PHYSICAL_BROKER_REPLAY_BLOCKED`**: ninguna evidencia de los precios BID/ASK del broker de ejecución y sus transacciones; ticks externos no equivalen a fills.
- No rehacer L1/L2 ni cambiar stops/rango por estos datos. Para avanzar en el histórico con tick externo debe usarse una fuente con descarga limitada/estable y hashes, siempre con etiqueta cross-provider. Para certificar economía física, se requieren **cotizaciones/recibos del broker aplicable**, no un simple cambio del endpoint gratuito.

**Estado de Scalper/estrategia de Londres: NO CERTIFICADOS.** GitHub-only; VPS y producción intactos.

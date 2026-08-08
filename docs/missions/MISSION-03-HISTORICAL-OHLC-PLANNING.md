# QORE-HISTORICAL-OHLC-PLANNING-001 — Deterministic Historical Window Planner

## Estado

**PREPARED OFFLINE — NO NETWORK EXECUTION**

Base:

```text
main @ eb45c9ac6d92cfb564cdbba875049a646d5f6474
MISSION-03 — QORE Real Market Operational Activation
```

Este trabajo es auxiliar. No modifica la secuencia oficial de MISSION-03 y no declara iniciado ni completado `QORE-MARKET-DATA-CERTIFICATION-001`.

La activación operacional del feed continúa esperando una ejecución autenticada real contra OANDA Practice.

## Objetivo

Preparar de forma provider-neutral la división de una ventana histórica OHLC en requests canónicos unitarios, de modo que cuando el proveedor externo vuelva a estar disponible cada intervalo pueda recorrer la ruta existente sin crear un segundo decoder ni una segunda ruta de ingestión.

Componente:

```text
src/qore/infrastructure/historical_market_data.py
```

## Flujo preparado

```text
HistoricalOhlcWindow
    → HistoricalOhlcPlanningPolicy
    → plan_historical_ohlc_requests(...)
    → HistoricalOhlcRequestPlan
    → tuple[OhlcRequest, ...]
```

Posteriormente, bajo una autorización operacional separada, cada `OhlcRequest` podrá recorrer:

```text
OandaPracticeMarketDataRequestFactory
    → approved Practice transport
    → OandaPracticeMarketDataDecoder
    → ExternalOhlcPayload
    → MarketDataIngestionFlow
    → OhlcSnapshot
    → market-data certification checks
```

El planner no ejecuta esa segunda parte.

## HistoricalOhlcWindow

La ventana declara explícitamente:

- instrumento canónico;
- timeframe canónico;
- `opened_at` timezone-aware;
- `closed_at` timezone-aware.

Debe satisfacer:

- `closed_at > opened_at`;
- duración expresable en segundos enteros;
- duración exactamente divisible por el timeframe.

`interval_count` se deriva determinísticamente de la ventana y no depende de reloj del sistema ni del proveedor.

## HistoricalOhlcPlanningPolicy

La policy contiene únicamente:

```text
maximum_intervals
```

Debe ser un `int` positivo estricto; `bool` no es válido.

El límite es deliberadamente caller-owned. Este componente no hardcodea límites actuales de OANDA ni convierte una capability documentada del proveedor en autorización de consumo.

Si una ventana excede la policy, la planificación falla cerrada antes de producir un plan parcial.

## HistoricalOhlcRequestPlan

El plan final contiene un tuple estable de `OhlcRequest` existentes.

Valida que:

- la cantidad de requests sea exactamente `interval_count`;
- ningún request exceda la policy;
- todos compartan instrument y timeframe con la ventana;
- todos estén en orden temporal ascendente;
- los intervalos sean contiguos;
- no existan overlaps ni huecos dentro del plan;
- el primer request comience en `window.opened_at`;
- el último termine exactamente en `window.closed_at`.

Esto convierte la futura adquisición histórica en una serie de unidades canónicas ya soportadas por el decoder/ingestion existentes.

## Razón para requests unitarios

El decoder OANDA Practice actual está deliberadamente compuesto alrededor de un `OhlcRequest` y una candle completa por respuesta canónica.

La preparación mantiene esa frontera en vez de introducir ahora:

- batching provider-specific;
- un decoder histórico paralelo;
- una segunda normalización;
- un loop de red oculto.

La iteración sobre el plan, si llega a autorizarse, pertenecerá a una composición operacional explícita posterior y deberá respetar policies de rate limit, timeout, resilience y observability vigentes en ese momento.

## Tests determinísticos

La suite cubre:

- una hora M15 → cuatro requests exactos y contiguos;
- treinta minutos M5 → seis requests en orden estable;
- reproducibilidad de `logical_values()`;
- timestamps naive bloqueados;
- ventanas no divisibles por el timeframe bloqueadas;
- microsegundos no representables como segundos enteros bloqueados;
- policy `bool`/cero/negativa bloqueada;
- exceso de `maximum_intervals` bloqueado antes de plan parcial;
- plan manual no contiguo bloqueado;
- tipos runtime incorrectos bloqueados mediante `Failure` tipado.

## Lo que NO demuestra

Este trabajo no demuestra:

- que OANDA esté disponible;
- que exista autenticación válida;
- que una cuenta Practice esté desbloqueada;
- que datos históricos hayan sido descargados;
- calidad de datos históricos reales;
- freshness/ordering/gaps reales del proveedor;
- reconnect o recovery operacional;
- certificación de market data.

## Fronteras preservadas

No se introduce:

- network IO;
- secreto alguno;
- Production OANDA;
- ejecución de retries/reconnect;
- loops de red;
- `sleep`;
- scheduler;
- threads;
- órdenes;
- capital real;
- corrective trading;
- cambios a `EventBus`, `RuntimePlan`, `RuntimeSnapshot` o `RuntimeHealth`.

Cuando OANDA Practice vuelva a estar disponible, este planner podrá utilizarse como input determinístico de adquisición histórica autorizada sin modificar el Core ni la única ruta canónica de market data.
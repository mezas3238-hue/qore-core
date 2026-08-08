# QORE-MARKET-DATA-CERTIFICATION-PREP-001 — Deterministic Certification Preparation

## Estado

**PREPARED OFFLINE — NOT OPERATIONALLY CERTIFIED**

Base de trabajo:

```text
MISSION-03 — QORE Real Market Operational Activation
main @ 6fb841bc08813ced392b59b2d95013e227c6d3e7
```

Este trabajo es preparatorio y no modifica la secuencia oficial de MISSION-03.

En particular:

```text
QORE-LIVE-MARKET-FEED-ACTIVATION-001
    sigue pendiente de evidencia externa real OANDA Practice

QORE-MARKET-DATA-CERTIFICATION-001
    permanece bloqueado y NO se declara iniciado ni completado
```

La razón de esta preparación es permitir avanzar validación determinística mientras la dependencia externa OANDA Practice no está disponible temporalmente, sin rebajar el gate que exige market data real.

## Objetivo

Preparar los contratos de validación de secuencias que la certificación operacional utilizará después de recibir snapshots canónicos reales.

El componente agregado es:

```text
src/qore/infrastructure/market_data_certification_preparation.py
```

Opera exclusivamente sobre:

```text
QuoteSnapshot
OhlcSnapshot
```

No acepta payloads provider-specific ni crea una segunda ruta de normalización.

La ruta preservada sigue siendo:

```text
provider wire payload
    → provider decoder
    → ExternalQuotePayload / ExternalOhlcPayload
    → MarketDataIngestionFlow
    → QuoteSnapshot / OhlcSnapshot
    → certification preparation checks
```

## Contratos preparados

### Policy explícita

`MarketDataCertificationPreparationPolicy` declara de forma tipada:

- `expected_source`;
- `required_symbols`;
- `required_timeframes`;
- `max_quote_age`;
- `maximum_ohlc_gap_intervals`.

Los símbolos y timeframes deben ser únicos y usar orden estable. La source debe pertenecer al namespace `market-data`.

No existe un reloj implícito. `evaluated_at` siempre es explícito y timezone-aware.

### Quote checks

La preparación detecta:

- source mismatch;
- symbol fuera de policy;
- snapshot ID duplicado;
- timestamp duplicado por instrumento;
- timestamps fuera de orden;
- timestamps futuros respecto de `evaluated_at`;
- quotes stale respecto de `max_quote_age`;
- symbol requerido sin quote.

Los contratos `QuoteSnapshot` existentes continúan siendo responsables de:

- precios positivos y finitos;
- `bid <= ask`;
- timestamps timezone-aware;
- instrument y source canónicos.

### OHLC checks

La preparación detecta:

- source mismatch;
- symbol fuera de policy;
- timeframe fuera de policy;
- snapshot ID duplicado;
- intervalo duplicado;
- series fuera de orden;
- overlaps;
- gaps por encima de la tolerancia explícita;
- combinación requerida symbol/timeframe ausente.

Los contratos `OhlcSnapshot` existentes continúan siendo responsables de:

- intervalo exacto igual al timeframe;
- precios positivos y finitos;
- `low <= high`;
- `open` y `close` dentro de `low/high`;
- timestamps timezone-aware.

## Semántica de gaps

`maximum_ohlc_gap_intervals` es deliberadamente explícito.

Ejemplos:

```text
0 → exige continuidad exacta entre closed_at y el siguiente opened_at
1 → permite exactamente un intervalo ausente
```

La futura certificación operacional deberá definir la policy adecuada para la ventana real evaluada. Este trabajo no codifica implícitamente calendario de mercado, fines de semana o mantenimiento del proveedor.

## Resultado

`MarketDataCertificationPreparationReport` contiene:

- policy evaluada;
- `evaluated_at`;
- cantidad de quotes;
- cantidad de OHLC snapshots;
- findings tipados en orden determinista;
- propiedad `is_prepared`.

`is_prepared=True` significa exclusivamente:

```text
no se encontraron problemas en los checks determinísticos solicitados
```

No significa:

```text
provider connected
OANDA authenticated
real market data received
operational certification passed
QORE-MARKET-DATA-CERTIFICATION-001 completed
```

## Cobertura determinística

Los tests preparan escenarios para:

- ventana limpia reproducible;
- stale/future quote;
- duplicate quote ID;
- duplicate quote timestamp;
- quote ordering;
- OHLC gap;
- OHLC overlap;
- OHLC ordering;
- duplicate OHLC ID/interval;
- missing series;
- source mismatch;
- symbol mismatch;
- timeframe mismatch;
- policy gap tolerance explícita;
- policy inválida;
- rechazo de inputs no canónicos;
- rechazo de tiempo naive.

La normalización provider-specific y los rechazos de wire payload permanecen en la suite OANDA existente. Este preparador no sustituye esos tests.

## Lo que queda reservado para evidencia real

Cuando OANDA Practice vuelva a estar disponible se debe ejecutar el workflow ya integrado:

```text
QORE OANDA Practice Market Feed Probe
```

Solo después de un run exitoso y de auditar el artifact sanitizado podrá cerrarse operacionalmente `QORE-LIVE-MARKET-FEED-ACTIVATION-001`.

Entonces podrá abrirse formalmente:

```text
QORE-MARKET-DATA-CERTIFICATION-001
```

La certificación real deberá combinar al menos:

1. evidencia autenticada de provider/environment Practice;
2. snapshots producidos por la ruta canónica;
3. checks preparados aquí sobre ventanas reales;
4. freshness y ordering reales;
5. duplicates/gaps reales;
6. malformed payload containment;
7. comportamiento de connectivity/reconnect que corresponda al runtime autorizado;
8. evidencia sanitizada sin account ID completo, token ni Authorization material.

## Fronteras preservadas

Este trabajo no introduce:

- llamadas de red;
- secretos;
- Production OANDA;
- retries;
- reconnect ejecutable;
- loops;
- `sleep`;
- scheduler;
- threads;
- órdenes;
- capital real;
- corrective trading;
- cambios al Core object graph;
- cambios a `EventBus`, `RuntimePlan`, `RuntimeSnapshot` o `RuntimeHealth`.

El resultado puede mergearse y permanecer disponible en `main` mientras OANDA está bloqueado. Cuando la dependencia externa vuelva, no será necesario rehacer estos contratos.
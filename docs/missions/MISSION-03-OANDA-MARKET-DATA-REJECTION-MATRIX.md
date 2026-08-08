# QORE-OANDA-MARKET-DATA-REJECTION-MATRIX-001 — Deterministic Wire Rejection Preparation

## Estado

**PREPARED OFFLINE — NOT OPERATIONAL EVIDENCE**

Base:

```text
main @ 6d8c20ec80c5e2c98bf58bcee349e1dbc084269f
MISSION-03 — QORE Real Market Operational Activation
```

Este trabajo es auxiliar y no altera la secuencia oficial de entregables.

`QORE-LIVE-MARKET-FEED-ACTIVATION-001` continúa pendiente del run real OANDA Practice y `QORE-MARKET-DATA-CERTIFICATION-001` continúa formalmente bloqueado hasta que exista evidencia operacional autenticada.

## Objetivo

Endurecer de forma determinística el decoder OANDA Practice ya integrado, demostrando que payloads wire anómalos fallan cerrado antes de convertirse en payloads provider-neutral o snapshots canónicos.

No se añade una segunda implementación del decoder. La matriz prueba directamente:

```text
OandaPracticeMarketDataDecoder
```

## Quote rejection matrix

La suite verifica rechazo de:

- JSON inválido;
- root que no sea objeto JSON string-keyed;
- `prices` que no sea array;
- más de una entrada del instrumento solicitado;
- precio no explícitamente tradeable;
- timestamp sin timezone;
- bids vacíos;
- asks vacíos;
- book cruzado con `best bid > best ask`.

## OHLC rejection matrix

La suite verifica rechazo de:

- instrument distinto del solicitado;
- granularity distinta del timeframe solicitado;
- cero candles;
- múltiples candles en el boundary unitario actual;
- candle incompleta;
- timestamp sin timezone;
- inicio que no coincide exactamente con el intervalo solicitado;
- midpoint ausente/no objeto;
- valores midpoint no positivos o no finitos.

## Separación de responsabilidades

El decoder OANDA valida el wire contract provider-specific.

Después:

```text
ExternalQuotePayload / ExternalOhlcPayload
    → MarketDataIngestionFlow
    → QuoteSnapshot / OhlcSnapshot
```

Las relaciones canónicas adicionales —por ejemplo `low <= open/close <= high`, intervalo exacto y precios positivos finitos— permanecen responsabilidad de los contratos e ingestion existentes.

La matriz no duplica esas invariantes.

## Seguridad

Se incluye un caso específico que introduce un marker sensible dentro del wire payload y comprueba que el error público del decoder no reproduce dicho contenido ni en `str(error)` ni en `repr(error)`.

Esto prepara la futura auditoría de secret/data leakage sin utilizar ningún token real.

## Lo que este trabajo NO demuestra

No demuestra:

- conectividad Internet;
- autenticación OANDA;
- validez de una cuenta Practice;
- disponibilidad actual del proveedor;
- datos de mercado reales;
- freshness operacional;
- reconnect real;
- heartbeat;
- certificación operacional.

Tampoco introduce:

- network IO;
- credenciales;
- Production endpoints;
- órdenes;
- retries;
- loops de red;
- scheduler;
- threads;
- capital real.

## Uso posterior

Cuando OANDA Practice vuelva a estar disponible, la futura certificación combinará:

1. run real autenticado del Practice probe;
2. artifact sanitizado;
3. decoder rejection matrix de este documento;
4. `MarketDataCertificationPreparationReport` sobre snapshots canónicos reales;
5. checks operacionales de freshness, ordering, gaps, connectivity y recovery autorizados.

Hasta entonces, este artefacto permanece como preparación determinística únicamente.
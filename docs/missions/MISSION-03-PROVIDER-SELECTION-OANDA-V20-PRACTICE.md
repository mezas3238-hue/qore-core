# QORE-PROVIDER-SELECTION-001 — Test Provider Selection & Capability Profile

## Estado

**APPROVED**

Base verificada de selección:

```text
main @ 962fb75612098cd9e044bec224a2cd2008e4e6f3
```

Misión:

```text
MISSION-03 — QORE Real Market Operational Activation
```

## Decisión

El primer proveedor operacional TEST/DEMO autorizado para MISSION-03 es:

```text
Provider: OANDA
API: v20 REST API
Environment: fxTrade Practice
Canonical provider key: oanda-v20
Operational environment: DEMO
```

La selección fue aprobada explícitamente por el propietario del proyecto. No deriva de preferencias históricas, de IC Markets, MetaTrader 5 ni de ninguna inferencia del Core.

Esta decisión autoriza únicamente la construcción de composición provider-specific para **OANDA v20 fxTrade Practice** bajo las fronteras de MISSION-03. No autoriza fxTrade production, cuentas live, capital real ni credenciales productivas.

## Razón arquitectónica

OANDA v20 fxTrade Practice encaja con la frontera ya construida por QORE porque ofrece una superficie HTTPS/JSON separada para testing, market data, account identity, order lifecycle y transaction history sin requerir una segunda ruta de market data o una segunda ruta de ejecución.

La selección favorece la reutilización de:

- `ExternalTransportBoundary` y transporte HTTPS concreto;
- secret resolution boundary existente;
- `ControlledLiveMarketDataFlow` / `MarketDataIngestionFlow`;
- payloads canónicos de market data existentes;
- `MarketTestAccountIdentity`;
- `ExecutionBoundary`;
- `AuthorizedTestExecutionAdapter`;
- pre-trade governance y execution safety switch;
- market-test account/instrument/quantity guard;
- idempotency existente;
- reconciliation y observability existentes.

Provider-specific code deberá permanecer en infraestructura externa y nunca convertirse en dependencia de Core, Domain o Governance.

## Separación de environments

OANDA documenta endpoints distintos para Practice y Production.

### REST

```text
Practice:   https://api-fxpractice.oanda.com
Production: https://api-fxtrade.oanda.com
```

### Streaming

```text
Practice:   https://stream-fxpractice.oanda.com
Production: https://stream-fxtrade.oanda.com
```

Para MISSION-03 únicamente los endpoints `fxpractice` son autorizables.

Cualquier configuración que contenga un endpoint `fxtrade` productivo debe fallar cerrado antes de resolver secretos o realizar network IO.

## Capability profile

### Market data — SUPPORTED

OANDA v20 expone pricing por cuenta e instrumentos y un pricing stream.

QORE podrá obtener como mínimo:

- instrument identity;
- bid ladder;
- ask ladder;
- provider timestamp;
- tradeability status;
- pricing freshness mediante timestamps;
- heartbeat en el stream;
- candlestick data cuando se requiera certificación OHLC.

La normalización seguirá siendo:

```text
OANDA wire payload
    → provider-specific decoder
    → existing provider-neutral payload
    → MarketDataIngestionFlow
    → canonical QORE snapshot
```

No se autoriza un segundo normalization path.

### TEST/DEMO environment — SUPPORTED

`fxTrade Practice` es el environment seleccionado.

Dentro de QORE deberá mapearse exclusivamente a:

```text
MarketRuntimeEnvironment.DEMO
```

No se permite mapear Practice a `PRODUCTION` ni aceptar una clasificación ambigua.

### Symbols / instruments — SUPPORTED

La API usa nombres de instrumentos provider-specific, por ejemplo:

```text
EUR_USD
GBP_USD
```

El mapping entre identidad OANDA y `ExecutionInstrument` / instrumentos canónicos de QORE debe ser explícito, allowlisted y determinista.

Ningún symbol provider-specific debe incorporarse como constante al Core.

### Execution API — SUPPORTED

OANDA v20 ofrece endpoints de órdenes y lifecycle de trading.

MISSION-03 solo podrá utilizarlos detrás de:

```text
ExecutionBoundary
    → AuthorizedTestExecutionAdapter
    → TestExecutionGatewayBoundary
    → OANDA Practice gateway
```

No se autoriza una API de ejecución paralela.

### Account identity — SUPPORTED

La API identifica cuentas mediante `accountID` y permite listar las cuentas autorizadas para el token.

El ID externo deberá vincularse a:

```text
MarketTestAccountIdentity(
    provider_key="oanda-v20",
    account_ref=<sanitized stable account reference>,
    environment=MarketRuntimeEnvironment.DEMO,
)
```

El `account_ref` no es material secreto, pero debe permanecer separado de credenciales.

### Authentication — SUPPORTED WITH SECRET BOUNDARY

OANDA v20 utiliza personal access token presentado como Bearer token.

El token se considera secret material.

Debe existir únicamente detrás de los secret boundaries existentes y nunca aparecer en:

- repository content;
- `repr`;
- `str`;
- logs;
- telemetry;
- evidence;
- metadata pública;
- exceptions públicas;
- `logical_values()`.

MISSION-03 solo autoriza un token asociado al entorno Practice/DEMO aprobado.

### Order lifecycle — SUPPORTED

La superficie v20 incluye orders, trades, positions y transactions.

La composición operacional deberá convertir acknowledgements y estados provider-specific a los receipts/status canónicos existentes sin ampliar el Core con estados OANDA.

### Execution acknowledgements — SUPPORTED

Responses de ejecución incluyen identidad/transacciones provider-specific que pueden utilizarse como provider execution reference sanitizada.

QORE debe mantener su propia identidad/idempotency canónica y no delegar idempotencia al proveedor por inferencia.

### Reconciliation — SUPPORTED

OANDA expone estado de cuenta y transaction history/transaction identifiers suficientes para construir reconciliación provider-specific contra los receipts canónicos.

Reconciliation divergente permanece fail-closed y nunca dispara corrective trading automático.

### Timestamps — SUPPORTED

Los recursos de pricing/transactions exponen DateTime provider timestamps.

El decoder debe exigir timestamps parseables y timezone-aware antes de producir contratos QORE.

No se sustituye el reloj determinista de QORE por tiempo implícito del sistema.

### Rate limits — EXPLICITLY GOVERNED

La documentación de OANDA v20 declara para REST un límite de 120 requests por segundo y para Streaming un máximo de 20 streams activos, además de un límite de nuevas conexiones de 2 por segundo.

Estas cifras son capability profile del proveedor, no autorización para consumir ese máximo.

Las policies operacionales de QORE deberán definir límites más conservadores y explícitos cuando corresponda.

### Reconnect semantics — SUPPORTED, EXECUTION DEFERRED

OANDA recomienda conexiones persistentes y el pricing stream emite heartbeats periódicos.

MISSION-03 continuará tratando retry/reconnect como declarativo hasta que un entregable posterior autorice y pruebe explícitamente el runtime operacional correspondiente.

No se introducen loops, `sleep`, scheduler o threads ocultos en este entregable.

## Riesgos identificados

### Token scope

Un personal access token puede autorizar acceso a múltiples subcuentas asociadas al usuario.

Mitigación obligatoria:

- account allowlist explícita en QORE;
- environment Practice obligatorio;
- no inferir autorización por el alcance del token;
- bloquear account mismatch antes de ejecución.

### Endpoint confusion

Practice y Production tienen hostnames similares.

Mitigación obligatoria:

- configuración tipada;
- allowlist exacta de Practice;
- rechazo explícito de `api-fxtrade.oanda.com` y `stream-fxtrade.oanda.com`;
- validación antes de secret resolution/network IO.

### Provider-specific identifiers

Symbols, account IDs y transaction IDs son externos.

Mitigación obligatoria:

- adapters provider-specific fuera del Core;
- mappings explícitos;
- no incorporar identificadores OANDA a contratos de Domain/Core.

### Ambiguous execution outcome

Timeout o desconexión después de una submission puede dejar outcome incierto.

Mitigación obligatoria:

- no resubmit automático;
- reconciliar primero;
- mantener idempotency de QORE;
- contener incertidumbre;
- nunca corrective trading automático.

## Criterios de aceptación de la selección

La selección se considera aprobada porque:

- existe un environment Practice separado del production endpoint;
- market data real está disponible;
- execution API TEST/DEMO está disponible;
- existe account identity verificable;
- existe order/transaction lifecycle suficiente para receipts y reconciliation;
- authentication puede mantenerse detrás de secret boundaries;
- rate limits y connectivity constraints son documentables;
- la superficie HTTPS/JSON puede componerse con las boundaries actuales;
- no exige modificar `CoreApplication`, `RuntimePlan`, `RuntimeSnapshot`, `RuntimeHealth` ni `EventBus`;
- no exige abrir capital real ni credenciales productivas.

## Fronteras cerradas

Esta selección no autoriza:

- `api-fxtrade.oanda.com`;
- `stream-fxtrade.oanda.com`;
- live/production OANDA accounts;
- capital real;
- depósitos o retiros;
- credenciales productivas;
- autonomous CIBO execution;
- bypass de governance/safety;
- direct broker access desde CIBO;
- QORE Mobile o CEO Widget;
- corrective trading automático.

## Consecuencia para el siguiente entregable

`QORE-PROVIDER-CONFIG-001` puede definir ahora configuración tipada para OANDA Practice:

- provider identity;
- environment;
- REST endpoint;
- streaming endpoint;
- account reference;
- allowed symbols;
- declared capabilities;
- request/connection timeouts;
- provider limits/policy limits;
- secret reference separada del material secreto.

Ninguna credencial será activada dentro de `QORE-PROVIDER-CONFIG-001`.

## Fuentes primarias verificadas

- OANDA v20 Development Guide: `https://developer.oanda.com/rest-live-v20/development-guide/`
- OANDA v20 Introduction: `https://developer.oanda.com/rest-live-v20/introduction/`
- OANDA v20 Authentication: `https://developer.oanda.com/rest-live-v20/authentication/`
- OANDA v20 Pricing endpoints: `https://developer.oanda.com/rest-live-v20/pricing-ep/`
- OANDA v20 Account endpoints: `https://developer.oanda.com/rest-live-v20/account-ep/`
- OANDA v20 Transaction endpoints: `https://developer.oanda.com/rest-live-v20/transaction-ep/`

Las fuentes externas describen capabilities del proveedor. Las fronteras y autorizaciones efectivas de QORE siguen definidas exclusivamente por este repositorio.

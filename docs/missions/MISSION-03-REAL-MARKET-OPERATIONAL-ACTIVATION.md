# MISSION-03 — QORE Real Market Operational Activation

## Estado

**ACTIVE**

Base inicial verificada:

```text
main @ 0d66353c1a57ae97a56ba9ea33ab88a58b9baf67
```

MISSION-03 comienza después del cierre formal de MISSION-02 — QORE Real Market Test Mode. El cierre de MISSION-02 permanece como baseline arquitectónico estable: esta misión no redefine sus contratos ni convierte capacidad network-capable o validación determinista en evidencia de conectividad operacional previa.

## Reconciliación al abrir la misión

Antes de abrir MISSION-03 se verificó el estado de `main`, commits recientes, PR #113, PRs abiertos, issues abiertos y documentación de misión. En la base indicada:

- `main` es idéntico al merge commit de PR #113;
- `docs/missions/MISSION-02-REAL-MARKET-TEST-MODE.md` declara MISSION-02 `COMPLETED`;
- no existe una MISSION-03 oficial previa en el repositorio;
- no existen PRs abiertos que definan una dirección posterior;
- no existen issues abiertos que definan una dirección posterior;
- no se identificó un roadmap o ADR posterior que sustituya la activación operacional TEST/DEMO como siguiente frontera.

Si una decisión posterior es integrada mientras MISSION-03 está activa, el repositorio y `main` vigentes prevalecen y la misión debe reconciliarse antes de continuar.

## Por qué es una nueva misión

MISSION-02 validó capacidad arquitectónica y un flujo completo reproducible sin exigir Internet, credenciales externas ni una cuenta real de proveedor. MISSION-03 abre una frontera diferente: componer las boundaries ya existentes con un proveedor TEST/DEMO concreto y obtener evidencia operacional externa real sin habilitar producción.

La distinción es obligatoria:

```text
network-capable
      !=
operationally connected to a real external provider
```

Y también:

```text
TEST/DEMO execution works
      !=
PRODUCTION authorization
```

## Objetivo

Transformar la capacidad validada por MISSION-02 en una instalación operacional autorizada contra un proveedor TEST/DEMO real, preservando el Core provider-free y manteniendo capital productivo explícitamente bloqueado.

Flujo objetivo:

```text
Real external TEST/DEMO provider
        │
        ├── real market data
        │
        ▼
Concrete transport / provider adapter
        │
        ▼
Canonical ingestion / normalization
        │
        ▼
QORE decision runtime
        │
        ▼
Governance / risk / safety
        │
        ▼
Supervised CIBO boundary
        │
        ▼
Authorized TEST/DEMO account
        │
        ▼
ExecutionBoundary
        │
        ▼
Provider execution gateway
        │
        ▼
Receipt / observation / reconciliation
        │
        ▼
Sanitized operational evidence
```

## Cambio deliberado de frontera

MISSION-03 autoriza únicamente la activación operacional externa de las capabilities TEST/DEMO ya gobernadas por MISSION-02.

La autorización está limitada a:

- seleccionar y documentar un proveedor concreto con entorno TEST/DEMO adecuado;
- configurar endpoints, capabilities, account references, symbols, timeouts y límites fuera del Core;
- resolver credenciales únicamente TEST/DEMO mediante secret boundaries existentes;
- conectar market data real al flujo canónico existente;
- vincular una cuenta real TEST/DEMO a `MarketTestAccountIdentity`;
- ejecutar órdenes únicamente mediante el `ExecutionBoundary` y el adapter TEST/DEMO existentes;
- obtener receipts, observabilidad, reconciliación y evidence sanitizados;
- validar fallos reales o controladamente reproducibles sin corrective trading automático.

## Fronteras que permanecen cerradas

MISSION-03 **no** autoriza:

- cuentas LIVE/PRODUCTION;
- capital real;
- real-money trading;
- credenciales productivas;
- deposits o withdrawals;
- autonomous portfolio execution;
- CIBO autónomo enviando órdenes reales;
- acceso directo de CIBO a broker, gateway, credentials, submit o cancel;
- corrective trading automático;
- public trading API;
- QORE Mobile;
- CEO Widget;
- deployment productivo automático;
- modificación implícita de `RuntimePlan`, `RuntimeSnapshot`, `RuntimeHealth` o `EventBus` del Core;
- interpretar el cierre de esta misión como autorización productiva.

La apertura futura de capital real requiere una misión independiente y un gate explícito de `PRODUCTION AUTHORIZATION`.

## Invariantes obligatorios

- El repositorio continúa siendo la fuente única de verdad.
- `CoreApplication` permanece provider-free.
- Ninguna dependencia desde Core, Domain o Governance apunta a providers/adapters concretos.
- La infraestructura externa se compone fuera del object graph interno del Core.
- `EventBus`, `RuntimePlan`, `RuntimeSnapshot` y `RuntimeHealth` no se modifican como efecto secundario de infraestructura.
- `dataclass(frozen=True, slots=True)` para contratos de valor cuando corresponda.
- `Protocol` para boundaries inyectables.
- `Result / Success / Failure` y errores tipados en cruces externos.
- Timestamps explícitos y timezone-aware.
- Sin `datetime.now()` dentro de contratos/boundaries deterministas.
- Sin `uuid4()` como generación implícita de identidad.
- Sin global mutable state.
- Metadata inmutable, sanitizada y determinista.
- Orden estable/determinista.
- Validación runtime explícita.
- `bool` e `int` se tratan estrictamente cuando una policy lo requiera.
- `logical_values()` permanecen deterministas y libres de material secreto.
- Secret material nunca aparece en repr, logs, telemetry, evidence, metadata pública o logical values.
- Retry/reconnect permanece declarativo salvo autorización explícita de runtime en un entregable posterior.
- No se introducen loops, `sleep`, scheduler o threads ocultos.
- Reconciliation divergente nunca dispara corrective trading automático.
- La incertidumbre de environment, account, provider state o execution outcome falla cerrado.

## Contratos de MISSION-02 que deben reutilizarse

MISSION-03 parte de los contratos existentes y no crea rutas paralelas para capacidades ya resueltas:

- `MarketRuntimeEnvironment`;
- `MarketTestAccountIdentity`;
- `MarketTestEnvironmentPolicy`;
- `MarketTestEnvironmentAuthorization`;
- `ControlledLiveMarketDataFlow` y `MarketDataIngestionFlow`;
- `ConcreteJsonMarketDataRequestFactory` / `ConcreteJsonMarketDataDecoder` cuando el proveedor seleccionado sea compatible, o adapters provider-specific que continúen produciendo los payloads canónicos existentes;
- `ExecutionBoundary`;
- `AuthorizedTestExecutionAdapter`;
- `TestExecutionGatewayBoundary`;
- pre-trade authorization y execution safety switch existentes;
- market-test account/instrument/quantity safety guard;
- idempotency existente;
- real-market decision runtime;
- supervised CIBO boundary;
- market-test observability evidence;
- market-test resilience decisions;
- reconciliation existente.

Provider-specific composition puede añadir implementaciones concretas detrás de estas boundaries, pero no puede crear un segundo flujo de market data ni una segunda ruta de órdenes.

## Gate especial de selección de proveedor

Ningún proveedor queda seleccionado por preferencia histórica ni por inferencia.

`QORE-PROVIDER-SELECTION-001` debe evaluar y documentar explícitamente, como mínimo:

- market data y modelo de timestamps;
- disponibilidad y aislamiento de TEST/DEMO;
- symbols/instruments;
- execution API;
- account identity;
- order lifecycle;
- authentication;
- rate limits;
- timeout semantics;
- reconnect semantics;
- execution acknowledgements;
- cancellation/status semantics;
- reconciliation capability;
- capacidad para mantener PRODUCTION inequívocamente bloqueado.

No se incorpora un provider-specific adapter operacional antes de que esa selección quede aprobada en el repositorio.

## Secuencia oficial de entregables

```text
1.  QORE-MISSION03-DOCS-001
    Operational Activation Architecture, Scope, Boundaries & Deliverables

2.  QORE-PROVIDER-SELECTION-001
    Test Provider Selection & Capability Profile

3.  QORE-PROVIDER-CONFIG-001
    Provider Runtime Configuration

4.  QORE-TEST-SECRETS-ACTIVATION-001
    Test Credential Activation

5.  QORE-LIVE-MARKET-FEED-ACTIVATION-001
    Real Market Feed Activation

6.  QORE-MARKET-DATA-CERTIFICATION-001
    Market Data Operational Certification

7.  QORE-DEMO-ACCOUNT-ACTIVATION-001
    Authorized Demo/Test Account Activation

8.  QORE-DEMO-EXECUTION-ACTIVATION-001
    Operational Test Execution

9.  QORE-OPERATIONAL-SAFETY-CERTIFICATION-001
    Operational Safety Certification

10. QORE-CIBO-OPERATIONAL-SUPERVISION-001
    CIBO Operational Supervision

11. QORE-OPERATIONAL-OBSERVABILITY-001
    Operational Observability

12. QORE-OPERATIONAL-RESILIENCE-001
    Operational Failure & Recovery

13. QORE-REAL-MARKET-OPERATIONAL-E2E-001
    Operational End-to-End Validation

14. QORE-MISSION03-CLOSURE-001
    Mission 03 Closure Review
```

Esta secuencia solo puede cambiar mediante un cambio arquitectónico explícito integrado al repositorio.

## Criterios por frontera

### Provider selection

Debe existir una capability profile verificable y una decisión explícita. No se asume IC Markets, MetaTrader 5 ni ningún broker/protocolo específico.

### Configuration and secrets

Configuración observable y secretos permanecen separados. Solo TEST/DEMO puede resolverse; cualquier indicio de credencial productiva bloquea la activación.

### Market data

El flujo obligatorio es:

```text
provider
  → transport
  → decoder
  → ingestion/normalization
  → canonical market data
```

La certificación operacional debe cubrir symbols, bid, ask, spread representation, timestamps, timezone, freshness, ordering, duplicates, reconnect, gaps, malformed payloads y canonical normalization.

### Account and execution

La cuenta debe estar representada por `MarketTestAccountIdentity` y autorizada exclusivamente como TEST/DEMO. La ejecución debe reutilizar `ExecutionBoundary`, pre-trade governance, safety switch, environment/account/instrument/quantity guards e idempotency.

Cualquier rechazo previo al gateway debe producir cero submissions externos.

### CIBO supervision

La supervisión debe ser explícita, expirable, TEST/DEMO-bound y fail-closed. CIBO participa únicamente en la surface de decisión existente y no recibe broker/gateway/credential access.

### Observability

La evidencia operacional debe cubrir al menos connectivity, feed health/freshness, heartbeat, latency, decisions, supervision, safety, order lifecycle, execution receipt, reconciliation, provider status y environment, siempre sanitizada.

### Resilience

Se validan disconnect, reconnect, timeout, throttling, provider unavailable, stale market data, partial failure, execution rejection, ambiguous response y reconciliation divergence.

No se permiten duplicación de órdenes ni corrective trading automático.

## Quality Gate

Cada entregable funcional debe pasar el pipeline existente sin rebajar checks:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

CI determinista continúa siendo obligatorio. Las certificaciones operacionales pueden producir evidence externa adicional, pero no sustituyen el Quality Gate del repositorio.

Si CI falla, el error debe corregirse sobre la misma rama y todos los gates deben volver a pasar antes del merge.

## Criterio de cierre

MISSION-03 solo puede marcarse `COMPLETED` cuando exista evidencia operacional reproducible de que:

- un proveedor TEST/DEMO concreto fue seleccionado y configurado explícitamente;
- market data externo real atraviesa el flujo canónico sin un segundo normalization path;
- la cuenta externa está inequívocamente clasificada TEST/DEMO;
- ejecución externa TEST/DEMO utiliza la ruta canónica gobernada;
- idempotency evita duplicación;
- environment/account/instrument/quantity/kill-switch failures bloquean antes del gateway cuando corresponde;
- provider failures quedan contenidos;
- ambiguous execution no induce resubmit ni corrective trading automático;
- reconciliation divergence queda contenida;
- CIBO permanece supervisado y sin acceso directo al provider;
- evidence/observability permanecen sanitizados y libres de secretos;
- `EventBus`, `RuntimePlan`, `RuntimeSnapshot` y `RuntimeHealth` permanecen intactos;
- PRODUCTION continúa bloqueado;
- ninguna evidencia de esta misión se interpreta como autorización de capital real.

## Resultado esperado

Al cerrar MISSION-03, QORE debe haber demostrado una activación operacional externa real y reproducible en TEST/DEMO sobre las boundaries ya gobernadas, sin alterar la identidad del Core y sin abrir ninguna frontera productiva.

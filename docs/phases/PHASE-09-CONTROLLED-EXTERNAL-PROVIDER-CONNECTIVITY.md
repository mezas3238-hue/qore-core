# PHASE-09 — Controlled External Provider Connectivity

## Estado

**ACTIVE**

PHASE-09 comienza únicamente después del cierre formal de PHASE-08 — Supervised Provider Runtime Readiness.

Base inicial verificada:

```text
main @ 400dd6263632918dd2483db87d8baf5444b4bd7d
```

## Objetivo

Permitir que la infraestructura externa supervisada de QORE pueda cruzar, de forma explícita y fail-closed, la frontera desde harnesses deterministas hacia conectividad read-only real o network-capable, sin habilitar ejecución de trading, order routing, posiciones reales ni mutación del Core.

La fase preserva el modelo construido hasta PHASE-08:

```text
CoreApplication
        │
        └── permanece provider-free

ExternalProviderRuntimePlan
        │
        ├── connectivity contracts
        ├── transport boundary
        ├── supervised secret resolution
        ├── lifecycle / activation
        ├── resilience / observability
        ├── read-only provider adapter
        │
        ▼
Supervised external runtime
        │
        ▼
canonical read-only ports
```

## Cambio deliberado de frontera respecto de PHASE-08

PHASE-08 prohibía network IO productivo y resolución de valores secretos productivos. PHASE-09 relaja esas dos prohibiciones exclusivamente dentro de infraestructura externa concreta y bajo estas condiciones:

- la conectividad es explícita, opt-in y read-only;
- Core, Domain, Functional Governance y Specialized Governance no realizan IO ni resuelven secretos;
- ningún valor secreto se almacena en contratos, metadata, health, logs, errores o snapshots;
- la resolución de secretos ocurre a través de una boundary inyectada y únicamente en el último punto de composición que la necesita;
- la activación permanece fail-closed;
- timeout, retry, rate-limit y reconnect permanecen gobernados por policy;
- los tests no requieren red real ni secretos reales;
- la composición determinista/fake sigue siendo de primera clase;
- ningún adapter de PHASE-09 puede escribir órdenes, posiciones o fondos.

## Principios preservados

- El repositorio es la fuente única de verdad.
- El `RuntimePlan` del Core no registra adapters externos.
- El `ExternalProviderRuntimePlan` permanece separado del Core.
- No existen imports inversos desde Core/Domain/Governance hacia adapters concretos.
- `dataclass(frozen=True, slots=True)`, `Protocol`, `Result / Success / Failure` y errores tipados siguen siendo la base de contratos.
- Timestamps y trace metadata son explícitos y timezone-aware.
- No se introduce `datetime.now()` ni `uuid4()` como dependencia implícita de runtime.
- Metadata y snapshots son inmutables y deterministas.
- Bool no se acepta silenciosamente como int cuando una policy requiere enteros estrictos.
- Network-capable implementations deben depender de boundaries inyectables para ser probables sin red.

## Fuera de alcance

PHASE-09 no implementa:

- order execution;
- order routing;
- buy/sell;
- gestión de posiciones reales;
- account funding o withdrawals;
- portfolio execution;
- CIBO ejecutando trades;
- MT5 trading live;
- broker-specific trading commands;
- QORE Mobile o Widget del CEO;
- API pública REST/gRPC/WebSocket;
- exposición de secretos;
- almacenamiento de credenciales en repositorio;
- mutación automática del `RuntimePlan` del Core.

## Entregables

### QORE-PHASE09-DOCS-001 — Define PHASE-09 Scope

Define alcance, cambio deliberado de frontera, entregables, quality gate y condición de cierre.

### QORE-PROVIDER-CONNECTIVITY-001 — External Provider Connectivity Contracts

Contratos provider-neutral para endpoint identity, connectivity mode, request intent read-only, connection state y failures tipados.

### QORE-TRANSPORT-BOUNDARY-001 — External Transport Boundary

Boundary estructural para transporte request/response con timeout explícito, headers sanitizados, payload bytes y errores tipados. Ningún provider concreto queda embebido en el contrato.

### QORE-SECRET-RESOLUTION-INTEGRATION-001 — Supervised Secret Resolution Integration

Integra resolución de `SecretReference` mediante resolver inyectado, con scope explícito, material efímero y prohibición de exposición en metadata/health/errors.

### QORE-READONLY-PROVIDER-ADAPTER-001 — Read-Only Provider Adapter

Adapter provider-neutral read-only que compone connectivity + transport + secret resolution + lifecycle/activation/resilience/observability sin capability de escritura de trading.

### QORE-LIVE-MARKET-DATA-001 — Controlled Live Market Data Flow

Flujo externo read-only desde payload provider hacia normalización canónica y `MarketDataPort`, conservando trace metadata y failures tipados. Los tests usan transporte determinista.

### QORE-CONNECTIVITY-OBSERVABILITY-001 — Live Connectivity Observability

Snapshots sanitizados de conexión, latencia declarada por caller/transport, estado y error category, sin secret values ni raw sensitive payloads.

### QORE-CONNECTIVITY-RESILIENCE-001 — Controlled Reconnect & Failure Policy

Policy determinista para reconnect eligibility, retry budget, timeout/rate-limit outcomes y circuit state sin `sleep` ni scheduler implícito.

### QORE-SUPERVISED-LIVE-RUNTIME-E2E-001 — Read-Only Live Runtime E2E

Composición E2E por encima de un `CoreApplication` preservado, demostrando que un provider read-only puede exponer canonical market-data port únicamente cuando todas las policies permiten activación.

### QORE-PHASE09-CLOSURE-001 — Phase 09 Closure Review

Auditoría transversal de dependencias, exposición de secretos, capabilities, IO, determinismo, tests, CI y preservación del Core.

## Secuencia obligatoria

```text
QORE-PHASE09-DOCS-001
→ QORE-PROVIDER-CONNECTIVITY-001
→ QORE-TRANSPORT-BOUNDARY-001
→ QORE-SECRET-RESOLUTION-INTEGRATION-001
→ QORE-READONLY-PROVIDER-ADAPTER-001
→ QORE-LIVE-MARKET-DATA-001
→ QORE-CONNECTIVITY-OBSERVABILITY-001
→ QORE-CONNECTIVITY-RESILIENCE-001
→ QORE-SUPERVISED-LIVE-RUNTIME-E2E-001
→ QORE-PHASE09-CLOSURE-001
```

## Quality Gate

Cada entregable se integra únicamente con:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Además:

- Mypy strict permanece habilitado;
- no se rebajan checks ni coverage para cerrar la fase;
- tests de conectividad no dependen de Internet;
- failures cruzan boundaries como errores tipados;
- secret material no aparece en `repr`, metadata, health, logical values o mensajes de error;
- blocked/degraded providers no exponen ports cuando la policy lo prohíbe;
- no hay trading execution.

## Condición de cierre

PHASE-09 queda `COMPLETED` únicamente cuando todos los entregables anteriores hayan sido integrados mediante PRs con CI verde y una revisión de cierre confirme que QORE puede componer conectividad externa read-only supervisada sin romper el aislamiento del Core, sin exponer secretos y sin habilitar ejecución de trading.

## Forward roadmap

Después de PHASE-09, la línea de trabajo prevista queda fijada como:

```text
PHASE-10 — Production Infrastructure & Operational Readiness
PHASE-11 — Controlled Trading Execution Boundary
PHASE-12 — End-to-End Trading Runtime & Safety Validation
PHASE-13 — QORE Core Production Closure
```

Estas fases deben conservar el mismo workflow protegido y solo podrán ampliar capacidades mediante cambios explícitos de frontera documentados en cada fase.

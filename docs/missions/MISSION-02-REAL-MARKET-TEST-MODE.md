# MISSION-02 — QORE Real Market Test Mode

## Estado

**ACTIVE**

Base inicial verificada:

```text
main @ f02ffb4fb90e90488002bd12a804a6c287ecebed
```

MISSION-02 comienza después del cierre formal de QORE Core PHASE-01..PHASE-13. El Core cerrado se considera baseline estable y no se amplía implícitamente para habilitar esta misión.

## Objetivo

Cumplir el primer objetivo operativo declarado por el repositorio: ejecutar QORE en condiciones reales de mercado, con datos reales y decisiones reales del ecosistema, permitiendo ejecución únicamente en un entorno autorizado de prueba/demo y manteniendo bloqueado todo capital productivo.

Flujo objetivo:

```text
Real Market Data
      │
      ▼
Concrete HTTPS Transport
      │
      ▼
Canonical Ingestion / Normalization
      │
      ▼
QORE Decision Runtime
      │
      ▼
Pre-Trade Governance + Safety Guard
      │
      ▼
Authorized TEST/DEMO Execution Adapter
      │
      ▼
Receipt / Observation / Reconciliation
      │
      ▼
Operational Evidence
```

## Cambio de frontera

MISSION-02 autoriza por primera vez implementaciones concretas de infraestructura capaces de realizar network IO real y conectar con entornos externos, únicamente bajo fronteras inyectables y fail-closed.

La autorización está limitada a:

- market-data read sobre HTTPS;
- resolución de configuración y secretos mediante boundaries existentes;
- cuentas y endpoints explícitamente clasificados TEST o DEMO;
- ejecución de trading únicamente contra un entorno no productivo autorizado;
- observabilidad, reconciliación y evidencia operacional sanitizadas.

## Fronteras que permanecen cerradas

MISSION-02 **no** autoriza:

- cuentas LIVE/PRODUCTION;
- capital real;
- deposits o withdrawals;
- real-money order routing;
- credenciales productivas;
- CIBO autónomo sin supervisión;
- corrective trading automático;
- portfolio execution autónoma;
- QORE Mobile;
- CEO Widget;
- public trading API;
- deployment automático;
- modificación implícita del RuntimePlan, RuntimeSnapshot, RuntimeHealth o EventBus del Core.

## Invariantes obligatorios

- El repositorio continúa siendo la fuente única de verdad.
- `CoreApplication` permanece provider-free.
- Ninguna dependencia desde Core/Domain/Governance apunta a adapters concretos.
- `dataclass(frozen=True, slots=True)` para contratos de valor.
- `Protocol` para boundaries inyectables.
- `Result / Success / Failure` y errores tipados en cruces externos.
- Timestamps explícitos y timezone-aware.
- Sin `datetime.now()` ni `uuid4()` implícitos en boundaries.
- Sin global mutable state.
- Identidades/idempotency explícitas.
- Secret material fuera de repr, logs, evidence y logical values.
- Retry/reconnect declarativos; sin loops/sleep/scheduler ocultos.
- Cualquier ambigüedad de environment o account mode falla cerrado.
- La ejecución TEST/DEMO reutiliza la semántica canónica de `ExecutionBoundary`; no crea una segunda ruta de órdenes.

## Secuencia oficial de entregables

```text
1.  QORE-MISSION02-DOCS-001
    Define Real Market Test Mode Scope, Boundary & Deliverables

2.  QORE-MARKET-TEST-ENVIRONMENT-001
    Market Test Environment Contracts

3.  QORE-CONCRETE-TRANSPORT-001
    Concrete HTTPS External Transport

4.  QORE-REAL-MARKET-DATA-PROVIDER-001
    Concrete Real Market Data Adapter

5.  QORE-TEST-EXECUTION-ADAPTER-001
    Authorized TEST/DEMO Execution Adapter

6.  QORE-MARKET-TEST-SAFETY-GUARD-001
    Test Account & Capital Boundary

7.  QORE-REAL-MARKET-DECISION-RUNTIME-001
    Real Market Decision Runtime

8.  QORE-CIBO-SUPERVISED-RUNTIME-001
    CIBO Supervised Test Runtime Boundary

9.  QORE-MARKET-TEST-OBSERVABILITY-001
    Market Test Observability Evidence

10. QORE-MARKET-TEST-RESILIENCE-001
    Market Test Failure & Recovery Policy

11. QORE-REAL-MARKET-TEST-E2E-001
    Real Market Test End-to-End Validation

12. QORE-MISSION02-CLOSURE-001
    Mission 02 Closure Review
```

## Quality Gate

Cada entregable funcional debe pasar el pipeline existente sin rebajar checks:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Los tests de red y provider se mantienen deterministas mediante boundaries/fakes; el código puede ser network-capable, pero CI no requiere Internet ni credenciales.

## Criterio de cierre

MISSION-02 solo puede marcarse `COMPLETED` cuando exista evidencia reproducible de que:

- la separación TEST/DEMO vs PRODUCTION es fail-closed;
- market data real puede atravesar el flujo canónico mediante transporte concreto;
- una orden autorizada puede alcanzar exclusivamente un adapter TEST/DEMO;
- replay/idempotency no duplica ejecución;
- kill switch o environment no autorizado producen cero submissions externos;
- failures de transporte/provider quedan contenidos;
- reconciliation divergente no genera corrective trading;
- CIBO solo puede actuar mediante una boundary supervisada;
- observability/evidence no expone secretos;
- EventBus, RuntimePlan, RuntimeSnapshot y RuntimeHealth del Core permanecen invariantes;
- ningún camino productivo queda habilitado.

La autorización de capital real requerirá una misión futura independiente y no puede inferirse del cierre exitoso de MISSION-02.

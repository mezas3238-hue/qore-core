# MISSION-02 — QORE Real Market Test Mode

## Estado

**COMPLETED**

Base inicial verificada:

```text
main @ f02ffb4fb90e90488002bd12a804a6c287ecebed
```

Baseline funcional previo al cierre:

```text
main @ 8dfcf2a81f47828a469a02375ce4bf6b57746d35
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

## Evidencia de cierre

La secuencia funcional quedó integrada de forma incremental sobre `main`:

```text
QORE-MISSION02-DOCS-001                 PR #102  merge 1dbbfb0ed2e3c0f99454d8d9864d7e37ef589138
QORE-MARKET-TEST-ENVIRONMENT-001        PR #103  merge 52099693db39b2c9064fc6cde6e6acf85509d538
QORE-CONCRETE-TRANSPORT-001             PR #104  merge 0350f887e392c5f1dc49277268de0ac9619f2e9c
QORE-REAL-MARKET-DATA-PROVIDER-001      PR #105  merge 46a2718b016f1485258735c166a46c8e2c7ac9c4
QORE-TEST-EXECUTION-ADAPTER-001         PR #106  merge 104eeb21608057955bcd39382ac18614bafc244e
QORE-MARKET-TEST-SAFETY-GUARD-001       PR #107  merge c1b51a215130817d94c50c2035427199b5d41d3f
QORE-REAL-MARKET-DECISION-RUNTIME-001   PR #108  merge d5c9cc71c8e94e6f5249955cea8cfa3f19f45fe7
QORE-CIBO-SUPERVISED-RUNTIME-001        PR #109  merge 2daa4b5a39db33348581c20f56b894e263d34e36
QORE-MARKET-TEST-OBSERVABILITY-001      PR #110  merge b27ad088380548bdddbfac656934cf6868b10e22
QORE-MARKET-TEST-RESILIENCE-001         PR #111  merge 0a00ce536a0afed4b50a484e8e1ffaf81e69727c
QORE-REAL-MARKET-TEST-E2E-001           PR #112  merge 8dfcf2a81f47828a469a02375ce4bf6b57746d35
```

El E2E final exige evidencia completa y determinista para:

- aislamiento del Core;
- separación de environments;
- flujo canónico de market data;
- ejecución TEST/DEMO;
- idempotencia;
- bloqueo previo a ejecución;
- containment de fallos;
- seguridad de reconciliación;
- supervisión de CIBO;
- observabilidad segura respecto de secretos;
- ausencia de habilitación productiva.

El cierre valida la **capacidad y las fronteras de MISSION-02 mediante el Quality Gate determinista**. No afirma que CI haya usado credenciales externas ni que una cuenta productiva o capital real haya sido conectado. La activación operacional contra un proveedor TEST/DEMO concreto continúa requiriendo composición/configuración externa autorizada; no modifica las garantías de que PRODUCTION permanece bloqueado por esta misión.

## Criterio de cierre

MISSION-02 se considera `COMPLETED` porque existe evidencia reproducible de que:

- la separación TEST/DEMO vs PRODUCTION es fail-closed;
- market data puede atravesar el flujo canónico mediante transporte HTTPS concreto y adapters inyectables;
- una orden autorizada puede alcanzar exclusivamente un adapter TEST/DEMO;
- replay/idempotency no duplica ejecución;
- kill switch o environment no autorizado producen cero submissions externos;
- failures de transporte/provider quedan contenidos mediante decisiones declarativas;
- reconciliation divergente no genera corrective trading;
- CIBO solo puede actuar mediante una boundary supervisada y expirable;
- observability/evidence no expone secretos;
- EventBus, RuntimePlan, RuntimeSnapshot y RuntimeHealth del Core permanecen invariantes;
- ningún camino productivo queda habilitado.

La autorización de capital real requerirá una misión futura independiente y no puede inferirse del cierre exitoso de MISSION-02.

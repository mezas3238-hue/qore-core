# PHASE-11 — Controlled Trading Execution Boundary

## Estado

**ACTIVE**

PHASE-11 comienza después del cierre formal de PHASE-10 — Production Infrastructure & Operational Readiness.

Base inicial verificada:

```text
main @ deb76cf16d24036bb6202008138640d027a2fd76
```

## Objetivo

Introducir por primera vez semántica de ejecución de trading dentro de una frontera explícita, fail-closed, provider-neutral y verificable, sin conectar QORE a un broker real ni habilitar operaciones con dinero real.

```text
Governed intent
    │
    ▼
OrderIntent
    │
    ▼
PreTradeSafetyGate
    │
    ├── authorization
    ├── kill switch
    ├── quantity / price invariants
    └── idempotency
    │
    ▼
ExecutionBoundary
    │
    └── deterministic sandbox adapter
    │
    ▼
ExecutionReceipt
    │
    ▼
Reconciliation
```

## Cambio deliberado de frontera respecto de PHASE-10

PHASE-10 prohibía cualquier order execution. PHASE-11 permite **representar y ejecutar de forma controlada dentro de un adapter sandbox/determinista** intents de trading, únicamente bajo estas condiciones:

- ninguna ejecución puede ocurrir sin autorización pre-trade explícita;
- un kill switch fail-closed puede bloquear toda ejecución;
- cada intent y submit requieren identidad/idempotency explícitas;
- quantity/prices usan aritmética decimal y validación estricta;
- execution boundary es provider-neutral;
- la implementación de referencia es sandbox/in-memory y no toca broker, exchange o cuenta real;
- receipts y reconciliation son inmutables y trazables;
- Core/Domain/Governance no importan adapters concretos;
- no se almacena secret material en intents, receipts o audit observable;
- no hay retry/sleep implícito;
- real-money connectivity sigue fuera de alcance.

## Principios preservados

- `dataclass(frozen=True, slots=True)` para intents, decisions, receipts y snapshots.
- `Protocol` para side-effect boundaries.
- `Result / Success / Failure` y errores tipados.
- timestamps timezone-aware explícitos.
- no `datetime.now()` ni `uuid4()` implícitos.
- no global mutable state.
- Decimal para quantity/price.
- bool-vs-int estricto.
- stable deterministic ordering / logical values.
- fail-closed ante identity mismatch, authorization ausente o kill switch bloqueado.

## Fuera de alcance

- broker real;
- MT5 live;
- real-money order routing;
- account credentials productivas;
- withdrawals/deposits;
- portfolio autonomous execution;
- CIBO enviando órdenes reales;
- public trading API;
- QORE Mobile / CEO Widget;
- strategy generation o recomendaciones de compra/venta.

## Entregables

### QORE-PHASE11-DOCS-001 — Define PHASE-11 Scope

Define el cambio de frontera, secuencia, safety invariants, Quality Gate y cierre.

### QORE-ORDER-INTENT-001 — Canonical Order Intent Contracts

Contratos inmutables para instrument, side, order type, Decimal quantity/price, intent identity, idempotency y trace metadata.

### QORE-PRETRADE-SAFETY-001 — Pre-Trade Authorization & Kill Switch

Decision contract para APPROVED/BLOCKED, policy identity, approval expiry explícita y global execution switch fail-closed. Produce un `AuthorizedOrderIntent` únicamente cuando todos los gates pasan.

### QORE-EXECUTION-BOUNDARY-001 — Provider-Neutral Execution Boundary

Protocol de submit/cancel-status-query controlado y reference sandbox adapter determinista. Submit es idempotente y nunca realiza IO de broker real.

### QORE-EXECUTION-RECONCILIATION-001 — Execution Reconciliation Contracts

Compara expected execution receipts con provider/sandbox observations, produce MATCHED/DIVERGED/MISSING/UNEXPECTED y nunca corrige posiciones automáticamente.

### QORE-CONTROLLED-EXECUTION-E2E-001 — Controlled Execution E2E

Compone intent → authorization → sandbox execution → receipt → reconciliation por encima de un `CoreApplication` preservado. Kill switch bloqueado debe impedir submit.

### QORE-PHASE11-CLOSURE-001 — Phase 11 Closure Review

Auditoría transversal de execution safety, idempotencia, reconciliation, Core isolation, secret safety, CI y ausencia de real-money connectivity.

## Secuencia obligatoria

```text
QORE-PHASE11-DOCS-001
→ QORE-ORDER-INTENT-001
→ QORE-PRETRADE-SAFETY-001
→ QORE-EXECUTION-BOUNDARY-001
→ QORE-EXECUTION-RECONCILIATION-001
→ QORE-CONTROLLED-EXECUTION-E2E-001
→ QORE-PHASE11-CLOSURE-001
```

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Además:

- no lint/type suppressions;
- no network/broker dependency in tests;
- no secret material observable;
- submit must be idempotent;
- blocked/expired authorization never reaches execution adapter;
- kill switch CLOSED/BLOCKED prevents execution;
- reconciliation has no automatic corrective side effects;
- Core remains unchanged.

## Condición de cierre

PHASE-11 queda `COMPLETED` únicamente cuando todos los entregables sean integrados con CI verde y el cierre demuestre una frontera de ejecución sandbox controlada, trazable e idempotente, sin conectividad real-money.

## Forward roadmap

```text
PHASE-12 — End-to-End Trading Runtime & Safety Validation
PHASE-13 — QORE Core Production Closure
```

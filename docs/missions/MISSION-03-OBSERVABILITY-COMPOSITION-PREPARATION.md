# QORE-OBSERVABILITY-COMPOSITION-PREPARATION-001 — Gate #11 Typed Observability Composition

## Estado

**OFFLINE PREPARATION — OPERATIONAL OBSERVABILITY REMAINS OPEN**

Este entregable compone las superficies tipadas existentes de MISSION-03 en el bundle canónico `MarketTestObservabilityEvidence` sin activar OANDA, resolver secretos ni declarar observabilidad operacional.

## Superficies reutilizadas

No se crean nuevas categorías ni un segundo modelo de health.

La composición reutiliza:

- `QuoteSnapshot`;
- `RealMarketDecisionOutcome`;
- `CiboOperationalSupervisionRecord`;
- `OperationalSafetyCertificationPreparationEvidence`;
- `ExecutionReceipt` contenido en la decisión;
- `ExecutionReconciliationSnapshot`;
- `MarketTestObservation`;
- `build_market_test_observability_evidence()`.

Las categorías canónicas siguen siendo exactamente:

```text
market_data
decision
supervision
safety
execution
reconciliation
```

## Coherencia cruzada fail-closed

`Mission03ObservabilityCycle` exige que:

1. supervision y quote usen el mismo `MarketDataSnapshotId`;
2. supervision y quote usen el mismo instrument;
3. la decisión supervisada no anteceda al quote;
4. un ciclo sin `RealMarketDecisionOutcome` sólo sea válido si supervision quedó `BLOCKED` o `FAILED`;
5. un ciclo bloqueado no lleve reconciliation;
6. una decisión NO_ACTION tenga supervision NO_ACTION y ninguna reconciliation;
7. una decisión SUBMITTED tenga supervision DELEGATED;
8. el `OrderIntentId` supervisado coincida con el intent de la decisión;
9. una decisión SUBMITTED tenga reconciliation;
10. `reconciliation.expected` sea exactamente el `ExecutionReceipt` de esa decisión.

Una contradicción entre superficies produce `Failure`/validation error antes de generar observaciones.

## Mapping de estados

### Market data

Un `QuoteSnapshot` canónico válido produce `HEALTHY` con referencia al snapshot exacto.

### Decision

- NO_ACTION -> `HEALTHY`, mensaje explícito `decision.no-action`;
- SUBMITTED -> `HEALTHY`, referencia al `OrderIntentId`;
- supervision bloqueada/fallida sin outcome -> `BLOCKED`.

### Supervision

- NO_ACTION / DELEGATED -> `HEALTHY`;
- BLOCKED / FAILED -> `BLOCKED`.

### Safety

La preparación Gate #9 sólo puede contribuir:

- PREPARED -> `HEALTHY`;
- BLOCKED -> `BLOCKED`.

Esto no convierte la preparación de Gate #9 en certificación operacional.

### Execution

- upstream bloqueado -> `BLOCKED` y cero ejecución esperada;
- NO_ACTION -> `HEALTHY` con `execution.not-required-no-action`;
- receipt ACCEPTED -> `HEALTHY`;
- receipt CANCELLED -> `DEGRADED`.

### Reconciliation

- upstream bloqueado -> `BLOCKED`;
- NO_ACTION -> `HEALTHY` con `reconciliation.not-required-no-action`;
- MATCHED -> `HEALTHY`;
- DIVERGED / MISSING / UNEXPECTED -> `BLOCKED`.

El aggregate state sigue siendo calculado únicamente por la función existente `build_market_test_observability_evidence()`.

## NO_ACTION no desaparece

Un ciclo NO_ACTION continúa generando las seis categorías requeridas.

Execution y reconciliation se marcan explícitamente como `not-required`, no como datos ausentes. Esto evita confundir una decisión legítima de no operar con pérdida de telemetry.

## Evidencia bloqueada

Un bloqueo upstream también produce las seis categorías. Decision, supervision, execution y reconciliation quedan `BLOCKED`, manteniendo visible dónde terminó la cadena sin inventar órdenes o receipts.

## Prohibición de falsa observabilidad operacional

`Mission03ObservabilityPreparationEvidence.operationally_observed` es siempre:

```text
false
```

CI, fixtures y dry-runs pueden demostrar que la composición es determinística y completa, pero no pueden cerrar Gate #11.

## Frontera de secretos

La composición usa únicamente valores sanitizados/canónicos ya disponibles en sus inputs.

No recibe:

- OANDA token;
- Authorization header;
- account credential;
- broker client;
- provider client;
- raw provider payload.

## Secuencia MISSION-03

```text
#5  Live Market Feed Activation      -> pendiente de cuenta/token + evidencia real
#6  Market Data Certification        -> cierre operacional pendiente
#7  Demo Account Activation          -> cierre operacional pendiente
#8  Demo Execution Activation        -> cierre operacional pendiente
#9  Operational Safety Certification -> cierre operacional pendiente
#10 CIBO Operational Supervision     -> preparación offline disponible
#11 Observability                    -> este entregable prepara composición
```

No se salta ningún cierre operacional.

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No se autorizan suppressions ni debilitamiento de checks.

## Fronteras cerradas

Permanecen **CLOSED**:

- OANDA live/Production;
- productive credentials;
- real capital;
- autonomous real-money execution;
- automatic retry/resubmit;
- corrective trading;
- direct provider access from CIBO;
- Risk/Portfolio/Capital Protection bypass.

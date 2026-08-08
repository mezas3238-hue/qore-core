# QORE-OPERATIONAL-SAFETY-CERTIFICATION-PREPARATION-001 — Gate #9 Evidence Matrix

## Estado

**PREPARATION ONLY — OPERATIONAL SAFETY CERTIFICATION REMAINS OPEN**

Este entregable define el contrato sanitizado y fail-closed que permitirá empaquetar la evidencia de `QORE-OPERATIONAL-SAFETY-CERTIFICATION-001` cuando la secuencia operacional MISSION-03 llegue realmente al Gate #9.

No ejecuta una operación OANDA, no consume credenciales y no certifica el sistema operacionalmente.

## Motivo

QORE ya contiene mecanismos independientes para:

- pre-trade authorization;
- safety switch;
- TEST/DEMO environment authorization;
- account/instrument/quantity guards;
- idempotency;
- execution reconciliation;
- failure containment;
- trading safety evidence.

Gate #9 necesita una matriz explícita que impida declarar seguridad operacional omitiendo alguno de esos controles o confundiendo evidencia de CI con evidencia externa real.

## Matriz obligatoria

El contrato requiere exactamente una evidencia para cada check y en orden canónico:

```text
authorization
test-demo-environment
account-guard
instrument-guard
quantity-guard
kill-switch
idempotency
provider-failure-containment
ambiguous-execution-containment
reconciliation-containment
secret-sanitization
production-blocked
no-automatic-corrective-trading
```

Un check ausente o duplicado produce `Failure`.

## Estados de preparación

Cada check tiene únicamente:

```text
PASS
FAIL
```

El bundle de preparación tiene únicamente:

```text
PREPARED
BLOCKED
```

`PREPARED` significa exclusivamente que la matriz determinística de preparación está completa y todos sus checks fueron marcados PASS por la fuente de evidencia suministrada.

No significa que Gate #9 esté cerrado.

## Prohibición de falsa certificación

`OperationalSafetyCertificationPreparationEvidence.operationally_certified` devuelve siempre:

```text
false
```

El payload público serializado también contiene explícitamente:

```json
"operationally_certified": false
```

Por diseño este artefacto nunca puede producir un estado `CERTIFIED`.

Una futura certificación operacional deberá existir como un entregable separado, consumir evidencia real generada después de Gate #8 y verificar su procedencia operacional.

## Binding del provider

La preparación está vinculada al provider ya seleccionado por MISSION-03:

```text
provider    = oanda-v20
environment = demo
```

No acepta `production` ni otro provider dentro de este contrato.

## Identidad de cuenta sanitizada

La evidencia pública no acepta account ID completo.

Sólo acepta:

```text
sha256:<24 hex chars>
```

Esto permite correlacionar evidencia sin publicar el identificador externo completo de la cuenta Practice.

## Evidence refs

Cada check requiere al menos un `OperationalSafetyEvidenceRef` opaco y sanitizado.

Los refs:

- usan sintaxis lowercase canónica;
- se deduplican fail-closed;
- se ordenan determinísticamente;
- rechazan fragmentos sensibles como bearer/password/token assignments.

La evidencia futura puede referenciar artifacts, audit records o runs sanitizados sin incrustar secretos.

## Cronología

Cada record tiene `observed_at` timezone-aware.

El bundle tiene `evaluated_at` timezone-aware.

Ningún record puede postdatar la evaluación.

No existe clock implícito.

## Relación con mecanismos existentes

Este contrato no reemplaza ni reimplementa:

```text
TradingSafetyEvidenceBundle
ExecutionReconciliationSnapshot
ExecutionContainmentSnapshot
MarketTestEnvironmentAuthorization
MarketTestSafetyPolicy
AuthorizedTestExecutionAdapter
ExecutionSafetySwitchSnapshot
```

La futura generación de records debe derivar evidencia de esas fronteras y de la ejecución OANDA Practice real.

## Evidencia offline versus evidencia operacional

Durante la fase actual sin cuenta/token OANDA Practice pueden construirse dry-runs y fixtures para verificar:

- completitud de la matriz;
- orden determinista;
- fail-closed por missing/duplicate checks;
- sanitización;
- bloqueo de Production;
- ausencia de falsa claim de certificación.

Esos resultados sirven únicamente como preparación.

Gate #9 sólo podrá cerrarse después de que Gate #8 produzca evidencia de ejecución externa TEST/DEMO real y se reproduzcan operacionalmente los escenarios de seguridad requeridos.

## Secuencia preservada

```text
#5 Live Market Feed Activation       -> pendiente de cuenta/token + evidencia real
#6 Market Data Certification         -> cierre operacional pendiente
#7 Demo Account Activation           -> cierre operacional pendiente
#8 Demo Execution Activation         -> cierre operacional pendiente
#9 Operational Safety Certification  -> este entregable prepara su evidencia
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

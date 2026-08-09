# QORE-MISSION03-CLOSURE-PREPARATION-001 — Gate #14 Mission Closure Contract

## Estado

**OFFLINE PREPARATION — MISSION-03 REMAINS OPEN**

Este entregable define el último contrato fail-closed de MISSION-03: la misión no puede ser elegible para cierre hasta que todos los Gates operacionales #5-#13 estén completados, en orden y con evidencia sanitizada.

El artefacto de preparación nunca cierra la misión por sí mismo.

## Matriz de cierre

La matriz contiene exactamente:

```text
#5  Live Market Feed
#6  Market Data Certification
#7  Demo Account Activation
#8  Demo Execution Activation
#9  Operational Safety Certification
#10 CIBO Operational Supervision
#11 Observability
#12 Resilience
#13 Real-Market Operational E2E
```

Cada Gate tiene:

- un `completed` booleano estricto;
- cero o más refs de evidencia operacional sanitizada.

La regla es exacta:

```text
completed = true  -> evidence_refs obligatorio y no vacío
completed = false -> evidence_refs debe estar vacío
```

Esto evita adjuntar evidencia diagnóstica o de preparación y presentarla como evidencia de cierre operacional.

## Secuencia estricta

Los Gates completados deben formar un prefijo exacto de #5-#13.

No se permite, por ejemplo:

```text
#5 complete
#6 open
#7 complete
```

Una brecha produce `Failure`.

## Estados de preparación de cierre

El bundle produce únicamente:

```text
BLOCKED
ELIGIBLE
```

`ELIGIBLE` requiere que #5-#13 estén todos completados y cada Gate conserve evidencia operacional.

Incluso en ese estado:

```text
mission_closed = false
```

`ELIGIBLE` significa únicamente que una futura acción explícita de cierre puede evaluarse.

## Estado actual

Sin cuenta/token OANDA Practice y sin evidencia operacional de Gate #5, la secuencia permanece abierta desde #5.

Por tanto el estado actual esperado de este contrato es:

```text
closure_preparation_status = blocked
closure_attempt_permitted  = false
mission_closed              = false
```

Los blocker codes identifican cada Gate todavía no completado.

## Evidencia operacional versus preparación

Los PRs y CIs offline de Gates #7-#13 demuestran implementación/preparación, no cierre operacional.

Una referencia aceptable para `Mission03OperationalGateEvidenceRef` deberá apuntar en el futuro a evidencia operacional real sanitizada de cada Gate.

No debe apuntar a fixtures como sustituto de una ejecución externa.

## Secret boundary

Los refs de cierre son opacos y rechazan fragmentos sensibles como:

- bearer;
- Authorization;
- password assignments;
- token assignments;
- secret assignments.

El contrato nunca recibe el token OANDA ni el account ID completo.

## No cierre implícito

Este entregable no introduce:

- cron automático de cierre;
- transición oculta de estado;
- merge como equivalente a certificación;
- CI verde como equivalente a evidencia OANDA;
- auto-approval;
- Production authorization.

El cierre final, cuando corresponda, deberá ser explícito, auditable y posterior a evidencia operacional completa #5-#13.

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

## Resultado de la fase offline

Cuando este contrato esté mergeado y verde, MISSION-03 habrá agotado el trabajo de preparación que puede completarse de forma segura sin cuenta/token OANDA Practice. El siguiente avance auténtico será necesariamente operacional y comenzará retomando Gate #5 cuando los dos bindings externos existan.

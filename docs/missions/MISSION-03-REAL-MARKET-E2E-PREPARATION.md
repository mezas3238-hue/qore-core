# QORE-REAL-MARKET-E2E-PREPARATION-001 — Gate #13 Offline Harness

## Estado

**OFFLINE PREPARATION — OPERATIONAL E2E REMAINS BLOCKED BY EXTERNAL PREREQUISITES**

Este entregable define la matriz fail-closed que separa dos conceptos que no deben confundirse:

```text
offline preparation ready
                !=
operational real-market E2E completed
```

No realiza llamadas a OANDA y no puede cerrar Gate #13.

## Cobertura

La matriz contiene exactamente, una sola vez y en orden canónico:

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

Cada Gate tiene un estado de preparación:

```text
READY
NOT_READY
```

y al menos una referencia de evidencia sanitizada.

Un Gate ausente o duplicado produce `Failure`.

## Estado externo separado

`Mission03ExternalPrerequisiteState` contiene únicamente información no secreta:

- si la cuenta OANDA Practice ha sido provisionada;
- si el token Practice ha sido provisionado;
- qué Gates operacionales #5-#12 han sido completados.

No contiene:

- account ID;
- token;
- Authorization header;
- secret material;
- raw provider payload.

Los flags de provisioning son booleanos estrictos.

## Secuencia operacional estricta

Los Gates operacionales completados deben formar un prefijo exacto de:

```text
#5 -> #6 -> #7 -> #8 -> #9 -> #10 -> #11 -> #12
```

No se permite declarar #7 completado sin #6, ni #12 sin todos sus predecesores.

Tampoco se permite declarar Gate #13 completado dentro de un artefacto de preparación.

Si existe cualquier Gate operacional completado, cuenta y token Practice deben estar provisionados.

## Estado actual esperado

Mientras no existan cuenta ni token OANDA Practice:

```text
practice_account_provisioned = false
practice_token_provisioned   = false
completed_operational_gates  = ()
```

La preparación offline puede llegar a `READY`, pero:

```text
operational_e2e_attempt_permitted = false
operationally_completed           = false
```

Los blocker codes exponen explícitamente:

- cuenta Practice no provisionada;
- token Practice no provisionado;
- evidencia operacional faltante para los Gates #5-#12.

## Cuando existan las credenciales

Provisionar cuenta/token no cierra ningún Gate automáticamente.

Después del provisioning todavía debe completarse en orden la evidencia operacional real de #5-#12.

Sólo cuando:

1. toda la preparación #5-#13 esté READY;
2. cuenta Practice esté provisionada;
3. token Practice esté provisionado;
4. #5-#12 estén operacionalmente completados en orden;

el harness podrá indicar:

```text
operational_e2e_attempt_permitted = true
```

Eso significa únicamente que puede intentarse Gate #13.

Incluso entonces este artefacto mantiene:

```text
operationally_completed = false
```

El cierre real de #13 deberá producir evidencia externa nueva y separada.

## Evidencia sanitizada

Cada `Mission03E2EEvidenceRef` es opaco, lowercase y no puede contener fragmentos sensibles de bearer/password/token/authorization.

El payload público es determinístico y sólo expone estado de preparación, flags de provisioning, Gates completados/faltantes y blocker codes.

## No simulación de OANDA

Los fixtures de CI verifican únicamente:

- completitud de la matriz;
- orden de Gates;
- fail-closed ante gaps;
- separación de preparación/operación;
- strict bool;
- sanitización;
- imposibilidad de falsa claim de cierre.

Ningún fixture se considera una respuesta real de OANDA.

## Relación con Gates preparados

Gate #13 consume conceptualmente las preparaciones ya implementadas para:

- account verification;
- market-data certification;
- execution codec/gateway;
- operational safety;
- CIBO supervision;
- observability;
- resilience.

No duplica sus reglas internas: únicamente gobierna la secuencia y la disponibilidad de sus evidencias.

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

## Consecuencia

Una vez que este harness offline sea verde, cualquier trabajo restante de cierre operacional MISSION-03 dependerá de provisioning/evidencia externa real. La ausencia actual de cuenta/token debe seguir tratándose como un bloqueo operacional legítimo, no como permiso para simular evidencia.

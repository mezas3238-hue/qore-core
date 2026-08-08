# QORE-CIBO-OPERATIONAL-SUPERVISION-PREPARATION-001 — Observed Supervision Evidence

## Estado

**OFFLINE PREPARATION — OPERATIONAL CIBO SUPERVISION REMAINS OPEN**

Este entregable prepara evidencia determinística para el Gate #10 de MISSION-03 sin activar CIBO contra un provider real ni modificar su autoridad.

## Base reutilizada

QORE ya contiene:

```text
CiboSupervisionAuthorization
SupervisedCiboDecisionBoundary
RealMarketDecisionBoundary
MarketTestEnvironmentAuthorization
```

La autorización existente continúa siendo la fuente de verdad para permitir o bloquear una decisión CIBO.

Este entregable no crea una segunda autorización.

## Hueco cerrado

Antes de este entregable la frontera supervisada podía:

- bloquear por ausencia/expiración de supervisión;
- delegar una decisión;
- devolver NO_ACTION;
- propagar un failure del delegate.

Pero esos outcomes no producían un receipt de supervisión específico por intento.

Gate #10 necesita evidencia auditable sin convertir a CIBO en cliente del provider ni exponer razonamiento privado.

## ObservedSupervisedCiboDecisionBoundary

La nueva frontera mantiene exactamente la firma:

```text
RealMarketDecisionBoundary.decide(context, metadata)
```

Por tanto puede sustituir estructuralmente a cualquier decision boundary existente sin cambiar `RealMarketDecisionRuntime`.

Internamente:

```text
Observed boundary
  -> SupervisedCiboDecisionBoundary
      -> existing delegate
  -> sanitized supervision record
  -> original Result returned
```

## Outcomes cerrados

Cada intento válido produce uno de:

```text
BLOCKED
NO_ACTION
DELEGATED
FAILED
```

Y uno de los reason codes cerrados:

```text
supervision.blocked
decision.no-action
decision.delegated
delegate.failed
```

El texto arbitrario del error del delegate nunca se copia al record.

Esto evita que tokens, payloads provider o detalles sensibles incluidos accidentalmente en una excepción contaminen la evidencia pública.

## Evidencia enlazada

Cada record enlaza explícitamente:

- attempt fingerprint determinístico;
- supervisor id;
- provider seleccionado `oanda-v20`;
- environment TEST/DEMO;
- account fingerprint, no account ID completo;
- `MarketDataSnapshotId` exacto;
- instrument canónico;
- `CorrelationId` exacto;
- decision timestamp;
- supervision expiry;
- outcome;
- reason code;
- `OrderIntentId` únicamente si hubo DELEGATED.

No existe clock ni UUID implícito.

El attempt ref se deriva determinísticamente de:

```text
correlation id + market snapshot id + decided_at
```

## NO_ACTION es evidencia

`NO_ACTION` no desaparece del trail.

Una decisión supervisada que legítimamente no genera intent conserva un record explícito `NO_ACTION` sin order intent ni execution receipt.

Esto mantiene el principio QORE:

```text
NO ACTION también se audita
```

## Bloqueo fail-closed

Si `SupervisedCiboDecisionBoundary` bloquea por policy/expiry, el delegate no se ejecuta y el record queda `BLOCKED`.

Si el delegate falla, el record queda `FAILED` con código cerrado `delegate.failed` y el `Failure` original se propaga al caller.

Si la creación de evidencia no pudiera validar sus invariantes, la frontera devuelve `Failure` en lugar de permitir que una decisión continúe sin evidencia válida.

## No provider access

El record y el wrapper no contienen:

- broker client;
- OANDA client;
- execution gateway;
- credential activation;
- token;
- Authorization header;
- account credential.

CIBO continúa recibiendo exclusivamente contexto canónico de mercado y metadata.

## Relación con observabilidad

`MarketTestObservationCategory.SUPERVISION` continúa siendo la categoría agregada de observabilidad.

Estos records proporcionan el detalle por intento que una futura composición de Gate #11 podrá resumir en esa categoría sin exponer CIBO internals ni chain-of-thought.

## Estado operacional

Nada de este PR cierra Gate #10.

El cierre futuro requiere que Gates #5–#9 hayan sido completados en orden y que CIBO opere bajo una ventana supervisada real TEST/DEMO, produciendo evidence operacional reproducible.

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
- direct provider access from CIBO;
- automatic retry/resubmit;
- corrective trading;
- Risk/Portfolio/Capital Protection bypass.

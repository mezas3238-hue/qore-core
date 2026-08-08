# QORE-OANDA-PRACTICE-EVIDENCE-AUDIT-001 — Sanitized Artifact Audit Preparation

## Estado

**PREPARED OFFLINE — REAL ARTIFACT STILL REQUIRED**

Base:

```text
main @ d21c1b7b012526f6f6f47914bac81cfd81e8ef25
MISSION-03 — QORE Real Market Operational Activation
```

Este componente prepara la auditoría determinística del artifact que producirá el workflow real `QORE OANDA Practice Market Feed Probe` cuando la cuenta externa vuelva a estar disponible.

No constituye evidencia real por sí mismo y no modifica la secuencia oficial de la misión.

## Objetivo

Evitar que el futuro cierre operacional dependa de una inspección ad hoc del JSON producido por el probe.

Componente:

```text
src/qore/infrastructure/oanda_practice_evidence_audit.py
```

El auditor recibe:

- bytes exactos del artifact sanitizado;
- una policy con `expected_run_key`;
- `expected_instrument`;
- `maximum_observation_age`;
- `audited_at` explícito y timezone-aware.

## Public schema allowlist

El artifact aceptable debe contener exactamente:

```text
account_fingerprint
ask
bid
endpoint_host
environment
instrument
observed_at
provider_key
run_key
schema
snapshot_id
status
```

Cualquier campo adicional bloquea la auditoría.

Por tanto no pueden incorporarse al artifact aceptado campos como:

```text
authorization
account_id
token
secret
```

La validación no imprime los nombres de campos inesperados para evitar reflejar contenido arbitrario controlado externamente en mensajes públicos de error.

## Invariantes de identidad

El auditor exige:

```text
schema = qore.oanda-practice.market-feed-evidence.v1
status = success
provider_key = oanda-v20
environment = demo
endpoint_host = api-fxpractice.oanda.com
instrument = valor exacto esperado por la audit policy
run_key = valor exacto esperado por la audit policy
```

El `account_fingerprint` debe mantener la forma sanitizada:

```text
sha256:<24 hex chars>
```

Nunca se acepta el account ID completo como sustituto del fingerprint.

## Invariantes temporales

`observed_at` debe ser:

- ISO-8601 parseable;
- timezone-aware;
- no futuro respecto de `audited_at`;
- no más antiguo que `maximum_observation_age`.

No se usa `datetime.now()` ni ningún reloj implícito.

La edad aceptable se define por policy en el momento de la auditoría operacional real.

## Invariantes de precio

`bid` y `ask` deben ser números JSON floating-point y finitos.

Después se reconstruye `OandaPracticeOperationalEvidence`, reutilizando sus invariantes Practice-only y de quote válido.

El auditor rechaza además constantes JSON no finitas como `NaN` o `Infinity`, incluso si un parser permisivo pudiera aceptarlas.

## Resultado

Un artifact válido produce:

```text
OandaPracticeEvidenceAuditReport
```

con:

- policy;
- evidencia tipada;
- `audited_at`;
- `observation_age`;
- `logical_values()` deterministas.

Este report significa únicamente:

```text
el artifact sanitizado cumple el contrato de evidencia del probe
```

No significa por sí solo:

```text
QORE-MARKET-DATA-CERTIFICATION-001 completed
execution activated
Production authorized
capital real authorized
```

## Tests preparados

La suite cubre:

- artifact válido y reproducible;
- schema incorrecto;
- status distinto de success;
- run mismatch;
- instrument mismatch;
- account ID no sanitizado;
- snapshot UUID inválido;
- timestamp naive;
- provider incorrecto;
- environment production;
- endpoint production;
- crossed bid/ask;
- campos extra;
- campos `authorization`, `account_id` y `token`;
- contenido sensible inesperado no reflejado por errores;
- `NaN` en JSON;
- evidencia futura;
- evidencia stale;
- policy inválida;
- `audited_at` naive.

## Uso cuando OANDA se desbloquee

La secuencia futura será:

```text
1. provisionar Actions secrets fuera del chat/repositorio
2. ejecutar manualmente QORE OANDA Practice Market Feed Probe desde main
3. obtener artifact sanitizado
4. auditar artifact con este boundary
5. verificar logs para ausencia de secret leakage
6. si todo es válido, cerrar operacionalmente QORE-LIVE-MARKET-FEED-ACTIVATION-001
7. abrir formalmente QORE-MARKET-DATA-CERTIFICATION-001
```

La auditoría del artifact no sustituye la inspección de los logs del run real ni la evidencia de que GitHub Actions realmente realizó la conexión externa.

## Fronteras preservadas

No se introduce:

- network IO;
- secretos;
- Production access;
- órdenes;
- retries/reconnect;
- loops;
- `sleep`;
- scheduler;
- threads;
- corrective trading;
- capital real;
- cambios a `EventBus`, `RuntimePlan`, `RuntimeSnapshot` o `RuntimeHealth`.

Este componente puede permanecer en `main` listo para consumir la futura evidencia real, sin afirmar que dicha evidencia existe antes de tiempo.
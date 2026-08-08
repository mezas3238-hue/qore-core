# QORE-OANDA-EXECUTION-CODEC-001 — OANDA Practice Execution Codec Preparation

## Estado

**OFFLINE PREPARATION — EXTERNAL DEMO EXECUTION REMAINS CLOSED**

Este entregable prepara la traducción determinística entre la ejecución canónica ya gobernada por QORE y el wire model de OANDA v20 Practice.

No realiza network IO, no resuelve credenciales y no implementa un gateway operativo.

## Posición en MISSION-03

La secuencia operacional no cambia:

```text
#5 Live Market Feed Activation       -> bloqueado hasta cuenta/token Practice
#6 Market Data Certification         -> cierre operacional pendiente de #5
#7 Demo Account Activation           -> preparación offline disponible; cierre pendiente
#8 Demo Execution Activation         -> este codec es preparación offline
#9 Operational Safety Certification  -> no cerrado
```

Preparar #8 no autoriza ejecutarlo fuera de orden.

## Frontera canónica reutilizada

El codec no crea un segundo modelo de trading.

Entrada obligatoria:

```text
ExecutionSubmission
  -> AuthorizedOrderIntent
  -> PreTradeAuthorization
  -> ExecutionSafetySwitch
```

La futura llamada externa seguirá estando detrás de:

```text
MarketTestEnvironmentAuthorization
  -> MarketTestSafetyPolicy
  -> SafetyGuardedTestExecutionBoundary
  -> AuthorizedTestExecutionAdapter
  -> TestExecutionGatewayBoundary
```

## Plan de creación de orden

`build_oanda_practice_order_create_plan(...)` transforma una `ExecutionSubmission` ya autorizada en un plan secret-free.

Para MARKET:

```text
type         = MARKET
timeInForce  = FOK
positionFill = DEFAULT
```

Para LIMIT:

```text
type         = LIMIT
timeInForce  = GTC
positionFill = DEFAULT
price        = canonical limit price
```

La dirección se expresa exclusivamente mediante el signo de `units`:

- BUY -> units positivas;
- SELL -> units negativas.

El instrumento debe estar en el allowlist de la `OandaPracticeRuntimeConfiguration` y la configuración debe declarar capability `ORDERS`.

El plan apunta solamente a:

```text
https://api-fxpractice.oanda.com
/v3/accounts/{practice-account}/orders
```

No contiene bearer token ni Authorization header.

## Lifecycle provider-specific

La frontera provider-neutral `ExecutionReceipt.ACCEPTED` representa el acknowledgement del submit y no se expande en este entregable.

La evidencia OANDA conserva además un disposition explícito:

```text
PENDING
FILLED
CANCELLED
```

Esto evita perder la diferencia entre:

- una limit order creada y pendiente;
- una market order inmediatamente filled;
- una orden inmediatamente cancelada por el provider.

Un outcome `CANCELLED` durante creación **no** puede convertirse en un gateway receipt `ACCEPTED`.

## Validación de respuesta de creación

Una respuesta sólo se acepta cuando:

- HTTP status es 201;
- `orderCreateTransaction` existe;
- account, instrument, signed units, type, time-in-force y position-fill coinciden con el plan;
- LIMIT conserva el precio canónico;
- timestamps son timezone-aware;
- `relatedTransactionIDs` es explícito, no vacío y sin duplicados;
- create/terminal transaction ids pertenecen a `relatedTransactionIDs`;
- `lastTransactionID` coincide con el transaction terminal;
- fill y cancel no aparecen simultáneamente;
- un fill referencia exactamente el order creado y conserva instrument/units;
- cualquier terminal transaction no antecede al create transaction;
- el outcome no antecede al `ExecutionSubmission` canónico.

Errores HTTP/provider se convierten en errores tipados sanitizados sin echo de payload arbitrario.

## Cancelación explícita

La preparación incluye decoder de una futura cancelación explícita.

Se exige:

- HTTP 200;
- `orderCancelTransaction` presente;
- account exacta;
- `orderID` idéntico al provider execution ref conocido por QORE;
- type `ORDER_CANCEL`;
- reason `CLIENT_REQUEST`;
- timestamp aware;
- transaction incluido en `relatedTransactionIDs`;
- `lastTransactionID` igual al transaction de cancelación.

Sólo entonces se proyecta un `TestExecutionGatewayReceipt` con status canónico `CANCELLED`.

## Idempotencia

Este codec no introduce un idempotency mechanism paralelo.

La autoridad sigue siendo la `ExecutionIdempotencyKey` de QORE y la deduplicación del `AuthorizedTestExecutionAdapter`.

No se ejecuta retry, resubmit ni corrective trading desde el codec.

## Transporte write permanece cerrado

El `ExternalTransportRequest` existente sigue siendo read-only por diseño y **no se modifica**.

Este entregable no añade POST/PUT a esa surface, no construye un bearer transport write-capable y no abre una ruta externa ejecutable.

Una futura implementación del gateway Practice requerirá un entregable explícito separado, TEST/DEMO-only, con secret boundary y failure containment propios.

## Evidencia y secretos

Los valores sanitizados sustituyen el account ref por un fingerprint estable.

Nunca deben aparecer en evidence/logical public values:

- Practice token;
- Authorization header;
- secret reference material;
- password;
- credential productiva.

## Criterio operacional futuro de #8

Este entregable no es evidencia suficiente para cerrar `QORE-DEMO-EXECUTION-ACTIVATION-001`.

El cierre futuro necesitará, después de #5–#7:

- account DEMO real autorizada;
- pre-trade/switch/environment/safety guards reales;
- un submit OANDA Practice real bounded;
- lifecycle provider evidence sanitizada;
- canonical execution receipt;
- idempotency evidence;
- reconciliation;
- failure containment;
- cero secret leakage.

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No se autorizan suppressions ni debilitamiento de checks.

## Fronteras que permanecen CLOSED

- OANDA live/Production;
- productive credentials;
- real capital;
- autonomous real-money execution;
- retry/resubmit automático;
- corrective trading;
- Risk/Portfolio/Capital Protection bypass.

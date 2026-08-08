# QORE-OANDA-PRACTICE-EXECUTION-GATEWAY-BOUNDARY-001 — Offline Practice Gateway Composition

## Estado

**OFFLINE PREPARATION READY — NETWORK-CAPABLE EXECUTION TRANSPORT REMAINS CLOSED**

Este entregable compone el codec OANDA Practice ya preparado con la frontera provider-neutral `TestExecutionGatewayBoundary`, pero mantiene la capacidad de escritura de red fuera del repositorio operativo actual.

No existe cuenta/token OANDA Practice provisionado y los Gates #5–#8 continúan abiertos operacionalmente.

## Objetivo

Preparar la capa que, en una activación futura, quedará detrás de la ruta gobernada:

```text
ExecutionSubmission
  -> PreTradeAuthorization
  -> ExecutionSafetySwitch
  -> MarketTestEnvironmentAuthorization
  -> MarketTestSafetyPolicy
  -> SafetyGuardedTestExecutionBoundary
  -> AuthorizedTestExecutionAdapter
  -> OandaPracticeExecutionGateway
  -> OandaPracticeExecutionTransportBoundary
  -> future authenticated Practice write transport
```

La implementación actual llega únicamente hasta el `Protocol` de transporte.

## Separación del transporte read-only

`ExternalTransportRequest` y `ConcreteBearerHttpsExternalTransport` existentes continúan siendo read-only.

Este entregable no:

- añade `POST`, `PUT`, `PATCH` o `DELETE` a `ExternalTransportMethod`;
- modifica `https_transport.py`;
- construye un network client write-capable;
- resuelve `SecretMaterial`;
- lee GitHub Actions secrets;
- ejecuta órdenes OANDA.

La futura capacidad de escritura deberá implementarse mediante un boundary separado y explícitamente Practice-only.

## OandaPracticeExecutionTransportBoundary

El nuevo Protocol representa un transporte **ya autenticado externamente** y enlazado a una `OandaPracticeRuntimeConfiguration` exacta.

Expone únicamente:

```text
create_order(plan, metadata)
cancel_order(plan, metadata)
```

Cada operación representa como máximo una llamada provider. El Protocol no define retry, sleep, scheduler, reconnect loop, resubmit ni corrective trading.

El bearer token no forma parte de su firma pública.

## OandaPracticeExecutionGateway

El gateway implementa estructuralmente `TestExecutionGatewayBoundary`.

### Submit

Antes del transporte exige:

1. account exactamente igual a la account de la configuración Practice;
2. `ExecutionSubmission` canónica válida;
3. plan OANDA derivado por `build_oanda_practice_order_create_plan()`;
4. metadata tomada del `OrderIntent` original.

Después realiza exactamente una llamada `create_order` al transporte inyectado.

Si el transporte falla, el payload es ambiguo, el lifecycle no es aceptable o el codec falla, el gateway devuelve `Failure` y no reintenta.

Sólo después de un provider outcome aceptable:

- proyecta `TestExecutionGatewayReceipt`;
- conserva metadata de correlación por provider execution ref;
- conserva el `OandaPracticeExecutionOutcome` sanitizable.

Un provider execution ref duplicado falla cerrado.

## Cancelación correlacionada

`TestExecutionGatewayBoundary.cancel()` no transporta metadata explícita. Para preservar la cadena de evidencia, el gateway guarda el `ExternalRequestMetadata` del submit exitoso asociado al provider execution ref.

Una cancelación sólo puede alcanzar el transporte cuando:

- la account coincide con la configuración;
- el provider ref usa sintaxis OANDA numérica;
- `cancelled_at` es timezone-aware;
- el provider ref fue observado previamente por esta instancia mediante submit exitoso.

Un provider ref desconocido produce `ExecutionBoundaryNotFoundError` y cero llamadas externas.

El cancel reutiliza exactamente el metadata de correlación del submit original.

## OandaPracticeOrderCancelPlan

La cancelación se representa con un valor inmutable, secret-free y determinístico que incluye:

- account TEST/DEMO;
- endpoint Practice exacto;
- path exacto `/v3/accounts/{account}/orders/{provider-ref}/cancel`;
- timeout explícito;
- provider execution ref;
- request timestamp timezone-aware.

Su vista sanitizada sustituye el account ref por fingerprint.

## Idempotencia y no duplicación

Este gateway no inventa una segunda estrategia de idempotencia.

La autoridad permanece en:

```text
ExecutionIdempotencyKey
  -> AuthorizedTestExecutionAdapter
```

Los tests componen el gateway real con:

```text
SafetyGuardedTestExecutionBoundary
  -> AuthorizedTestExecutionAdapter
  -> OandaPracticeExecutionGateway
  -> fake transport
```

y verifican que el replay exacto de una submission genera una sola llamada de transporte.

## Failure containment

Los tests verifican que:

- account incorrecta bloquea antes del transporte;
- provider unavailable produce una sola llamada y cero retry;
- payload ambiguo produce una sola llamada y cero outcome local;
- cancel desconocido bloquea antes del transporte;
- cancel transport failure no se reintenta;
- cancellation receipt que antecede al request falla cerrado.

No se realiza resubmit automático después de una respuesta ambigua.

## Secret boundary

El diseño es compatible con `OandaPracticeCredentialActivation`, pero no consume su `SecretMaterial`.

Una futura implementación concreta del transporte deberá recibir el material únicamente en el último boundary secret-aware y deberá mantenerlo fuera de:

- request plans;
- metadata;
- logs;
- telemetry;
- evidence;
- repr;
- logical values;
- exceptions.

## Estado operacional

Nada de este entregable constituye evidencia operacional de Gate #8.

La ejecución externa real continúa prohibida hasta completar secuencialmente:

```text
#5 Live Market Feed Activation
#6 Market Data Certification
#7 Demo Account Activation
#8 Demo Execution Activation
```

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
- write-capable network transport;
- automatic retry/resubmit;
- corrective trading;
- Risk/Portfolio/Capital Protection bypass.

# QORE-RESILIENCE-POLICY-PREPARATION-001 — Gate #12 Practice Policy Pack

## Estado

**OFFLINE PREPARATION — OPERATIONAL RESILIENCE REMAINS OPEN**

Este entregable compone los contratos genéricos de `adapter_resilience` en una política explícita para las operaciones OANDA Practice autorizadas por MISSION-03.

No implementa retry loops, sleep, scheduler, circuit-breaker runtime ni llamadas externas.

## Operaciones cubiertas

La policy pack contiene exactamente una política para:

```text
market-read
account-read
order-create
order-cancel
```

No se permiten operaciones implícitas ni ausencia de una de estas superficies.

## Timeout

Cada operación recibe un `AdapterTimeoutPolicy` derivado del `rest_timeout` explícito de `OandaPracticeRuntimeConfiguration`.

No existe timeout oculto ni default runtime fuera de la configuración aprobada.

## Retry

La preparación actual usa:

```text
max_attempts = 1
retryable_failures = ()
delay_schedule = ()
```

para las cuatro operaciones.

Por tanto:

```text
automatic_retries_enabled = false
```

### Side effects

`order-create` y `order-cancel` están marcadas como operaciones con side effects.

Estas operaciones fallan validación si una policy intenta habilitar retry automático.

Esto preserva la regla:

```text
respuesta ambigua != permiso para repetir una orden
```

Un future cambio de retries de lectura requerirá un cambio explícito de policy, tests, PR y CI; no se habilita de forma invisible en este entregable.

## Rate limit

Cada operación recibe `AdapterRateLimitPolicy` derivada de:

```text
OandaPracticeOperationalLimits.rest_requests_per_second
```

con una ventana explícita de 1000 ms y burst capacity igual al límite configurado.

La policy declara el límite; no implementa sleeps ni throttling oculto.

## Capabilities requeridas

La composición sólo existe si la configuración Practice incluye:

- ACCOUNT;
- PRICING;
- ORDERS.

Si falta una capability, el builder devuelve `Failure`.

## Provider/environment

La policy pack está cerrada a:

```text
provider    = oanda-v20
environment = demo
```

No acepta Production.

## Reutilización de contratos

Este entregable no crea modelos paralelos de retry/timeout/rate-limit.

Reutiliza exactamente:

- `AdapterTimeoutPolicy`;
- `AdapterRetryPolicy`;
- `AdapterRateLimitPolicy`;
- `AdapterRetryDelay`.

## No runtime behavior

La policy pack es inmutable y determinística.

No contiene:

- network client;
- retry executor;
- timer;
- sleep;
- scheduler;
- thread;
- reconnect loop;
- automatic resubmit;
- corrective trading.

## Prohibición de falsa resiliencia operacional

`Mission03ResiliencePolicyPack.operationally_resilient` devuelve siempre:

```text
false
```

CI demuestra la corrección del contrato, no el comportamiento del proveedor real.

Gate #12 sólo podrá cerrarse después de que la secuencia operacional #5–#11 haya sido completada y puedan observarse fallos/latencias reales TEST/DEMO sin violar seguridad.

## Secuencia MISSION-03

```text
#5  Live Market Feed Activation      -> pendiente de cuenta/token + evidencia real
#6  Market Data Certification        -> cierre operacional pendiente
#7  Demo Account Activation          -> cierre operacional pendiente
#8  Demo Execution Activation        -> cierre operacional pendiente
#9  Operational Safety Certification -> cierre operacional pendiente
#10 CIBO Operational Supervision     -> cierre operacional pendiente
#11 Observability                    -> preparación offline disponible
#12 Resilience                       -> este entregable prepara policy
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
- automatic retry/resubmit;
- corrective trading;
- direct provider access from CIBO;
- Risk/Portfolio/Capital Protection bypass.

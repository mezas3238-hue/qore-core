# PHASE-08 — Supervised Provider Runtime Readiness

## Estado

**COMPLETED**

PHASE-08 comenzó después del cierre formal de PHASE-07 — External Provider Integration Readiness y queda cerrada por `QORE-PHASE08-CLOSURE-001` una vez que este cambio documental supera su propio Quality Gate y se integra mediante merge protegido.

Base inicial de la fase:

```text
main @ acc229d982171e2b27e08fa3dc689ee86cb89340
```

Base verificada para el cierre:

```text
main @ 8aa0510774a6b6b889a831511a57b83076eb61f3
```

La base de cierre corresponde al merge protegido de `QORE-SUPERVISED-RUNTIME-E2E-001` (PR #63).

## Objetivo

Preparar QORE para operar proveedores externos bajo un runtime supervisado, explícito, determinista, reversible y fail-closed, sin convertir esa preparación en ejecución de trading ni en conectividad live obligatoria.

PHASE-07 dejó definidos los contratos de provider, configuración, secretos, observabilidad, resiliencia y harnesses deterministas. PHASE-08 completó la capa de supervisión operativa:

```text
provider configuration
→ activation policy
→ external runtime plan
→ adapter lifecycle
→ supervised provider harness
→ health / observability / resilience aggregation
→ canonical infrastructure ports
→ supervised end-to-end composition above the Core
```

El resultado permite preparar futuros adapters reales bajo control explícito antes de cualquier conectividad live o ejecución real.

## Principios preservados

- El repositorio es la fuente única de verdad.
- El Core permanece libre de adapters concretos.
- Domain, Runtime, Functional Governance y Specialized Governance no importan providers ni adapters concretos.
- La composición de infraestructura es explícita y opt-in.
- El `RuntimePlan` del Core no registra adapters externos automáticamente.
- La supervisión de providers externos vive por encima del Core o en fronteras de infraestructura explícitas.
- El lifecycle externo es declarativo, determinista y reversible.
- Timestamps, correlation, causation, identifiers y transition reasons son explícitos.
- Ningún lifecycle contract usa reloj global implícito.
- Ningún contrato resuelve secretos productivos por sí mismo.
- Ninguna política activa un adapter sin configuración válida, capability checks y referencias explícitas requeridas.
- Degradaciones y fallos externos se expresan mediante `Failure` tipado, health degradado o readiness no disponible.
- La activación es fail-closed por defecto.
- Los harnesses siguen siendo deterministas y no requieren adapters live.

## Fuera de alcance preservado

PHASE-08 no implementó:

- ejecución real de órdenes;
- order routing de broker/exchange;
- MT5 trading o conexión MT5 live;
- gestión de posiciones reales;
- account funding o withdrawals;
- credenciales productivas en repositorio;
- resolución de valores secretos productivos;
- conexión obligatoria a broker/provider live;
- automatización de entradas/salidas de trading;
- cambios autónomos de Optimization sobre configuración productiva;
- QORE Mobile o Widget del CEO;
- UI pública;
- REST/gRPC/WebSocket públicos de QORE;
- scheduler productivo externo;
- infraestructura distribuida productiva obligatoria;
- network IO productivo;
- filesystem IO productivo;
- SQL o Redis productivos;
- `sleep` como mecanismo de runtime;
- mutación automática de `RuntimePlan` del Core.

## Frontera de arquitectura final

PHASE-08 introdujo readiness de runtime externo supervisado por encima del Core.

Fronteras canónicas incorporadas:

```text
qore.infrastructure.adapter_lifecycle
qore.infrastructure.activation_policy
qore.infrastructure.provider_runtime
qore.infrastructure.external_health
qore.infrastructure.supervised_provider_harness
qore.infrastructure.supervised_runtime
```

Continúa prohibido:

```text
qore.core -> concrete provider adapters
qore.domain -> concrete provider adapters
qore.governance -> concrete adapters
qore.specialized_governance -> concrete adapters
RuntimePlan -> automatic provider adapter registration
provider runtime -> order execution
provider runtime -> secret value exposure
```

La composición E2E recibe un `CoreApplication` existente únicamente para preservar y comprobar su identidad operacional; no registra el runtime externo dentro del Core.

## Entregables completados

### QORE-PHASE08-DOCS-001 — Define PHASE-08 Scope

**COMPLETED**

```text
PR #57
head:  2b61eccb9de7647e0ccdde290bbf78cd8dbc4b4f
merge: b483414770643b3ef12e089d27b69e5c426b810b
QORE CI #269: PASS
Ruff: PASS
Mypy: PASS
Pytest: PASS
```

Definió el alcance, frontera, entregables, fuera de alcance, Quality Gate y condición de cierre de PHASE-08.

### QORE-ADAPTER-LIFECYCLE-001 — External Adapter Lifecycle Contracts

**COMPLETED**

```text
PR #58
head:  718763344b4274743b7f18e372c36d9c728bf615
merge: c709f5d9fb0f0fa51d70cdea21a65572758007ed
QORE CI #271: PASS
Ruff: PASS
Mypy: PASS
Pytest: PASS
```

Integró lifecycle externo con estados cerrados, transiciones explícitas, razones tipadas, actor/correlation/causation, timestamps inyectados y errores tipados, sin reloj global implícito ni efectos productivos.

### QORE-ACTIVATION-POLICY-001 — Provider Activation Policy Contracts

**COMPLETED**

```text
PR #59
head:  70b935feefb4e68c1562b02f6f2d03f3d1eda848
merge: 11f86238abe0c50b98bceb157f5f9a6f6f703d06
QORE CI #273: PASS
Ruff: PASS
Mypy: PASS
Pytest: PASS
```

Integró políticas de activación fail-closed con decisiones `allowed`, `blocked` y `degraded`, capability checks, referencias de secretos sin resolución y señales de lifecycle/observability/resilience.

### QORE-PROVIDER-RUNTIME-PLAN-001 — External Provider Runtime Plan Contracts

**COMPLETED**

```text
PR #60
head:  c900c67cc7d76520c92a96e3a9d05cccd2713342
merge: ccbc5a11621d585a3e1dea6075ae3f7a694cef20
QORE CI #276: PASS
Ruff: PASS
Mypy: PASS
Pytest: PASS
```

Integró un plan de runtime externo separado del `RuntimePlan` del Core, con orden dependency-first estable y rechazo tipado de duplicados, dependencias desconocidas y ciclos.

### QORE-EXTERNAL-HEALTH-AGGREGATION-001 — External Provider Health Aggregation

**COMPLETED**

```text
PR #61
head:  ebb8780ee4a2e7a88eb9408fd159075ac385ee62
merge: f86094b22189a5f9c1147942c268def12d0ec785
QORE CI #279: PASS
Ruff: PASS
Mypy: PASS
Pytest: PASS
```

Integró health/readiness provider-neutral con estados `ready`, `degraded`, `unavailable` y `blocked`, issues sanitizados y rollup desde activation policy, lifecycle, observability y resilience.

### QORE-SUPERVISED-PROVIDER-HARNESS-001 — Supervised Provider Runtime Harness

**COMPLETED**

```text
PR #62
head:  986169ffdff0fc40dc2e6f967632d7a5009aa75d
merge: 4b0e7cffbaac1ce0f2f77f5ac2df6a3920238232
QORE CI #285: PASS
Ruff: PASS
Mypy: PASS
Pytest: PASS
```

Integró la composición supervisada sobre `ReadOnlyMarketDataProviderHarness` y `PersistenceBackendHarness`, lifecycle explícito por source, activation policy antes de ports, health externo y propagación de `Failure` tipado.

### QORE-SUPERVISED-RUNTIME-E2E-001 — Supervised Runtime End-to-End Composition

**COMPLETED**

```text
PR #63
head:  e8de9533655726b44cc6badc156eba20392e1402
merge: 8aa0510774a6b6b889a831511a57b83076eb61f3
QORE CI #289: PASS
Ruff: PASS
Mypy: PASS
Pytest: PASS
```

Integró `qore.infrastructure.supervised_runtime` y demostró composición E2E de market data + persistence sobre un único `CoreApplication` preservado. El `ExternalProviderRuntimePlan` conserva identidad propia y permanece separado del `RuntimePlan` del Core. Policies bloqueadas/degradadas no exponen ports; failures de identidad, lifecycle y harness subyacente se propagan tipadamente.

### QORE-PHASE08-CLOSURE-001 — Phase 08 Closure Review

**COMPLETED WHEN MERGED**

Este documento constituye la revisión transversal de cierre. Su estado `COMPLETED` se vuelve oficial únicamente al integrarse este cambio mediante PR protegido con Quality Gate verde y confirmación posterior de `main`.

## Evidencia transversal de cierre

### 1. Aislamiento de archivos y dependencias

La revisión de changed files de PR #57–#63 confirma:

```text
PR #57 -> docs/phases/PHASE-08-SUPERVISED-PROVIDER-RUNTIME-READINESS.md
PR #58 -> qore.infrastructure adapter_lifecycle + tests + exports
PR #59 -> qore.infrastructure activation_policy + tests + exports
PR #60 -> qore.infrastructure provider_runtime + tests + exports
PR #61 -> qore.infrastructure external_health + tests + exports
PR #62 -> qore.infrastructure supervised_provider_harness + tests + exports
PR #63 -> qore.infrastructure supervised_runtime + tests + exports
```

No hubo cambios de PHASE-08 en:

```text
src/qore/core
src/qore/domain
src/qore/governance
src/qore/specialized_governance
```

Por tanto, la fase no introdujo una dependencia inversa desde Core/Domain/Governance hacia providers concretos o hacia el supervised runtime.

### 2. Core y RuntimePlan preservados

La composición E2E de PR #63 prueba explícitamente que permanecen intactos:

- identidad del `EventBus`;
- `RuntimeSnapshot`;
- `RuntimeHealth`;
- `RuntimePlan` del Core;
- composición provider-free de Functional Governance;
- composición provider-free de Specialized Governance.

El runtime externo se representa mediante `ExternalProviderRuntimePlan` y no se registra como componente interno del Core.

### 3. Sin trading execution ni conectividad live obligatoria

La revisión transversal confirma que PHASE-08 no añadió:

- order execution;
- order routing;
- broker live;
- MT5 live;
- apertura/cierre de posiciones;
- scheduler de trading;
- APIs públicas de ejecución.

Los harnesses y composiciones son deterministas y pueden ejercitarse completamente sin un provider live.

### 4. Secret boundary preservado

PHASE-08 consume referencias declarativas cuando una policy las requiere, pero no resuelve valores secretos productivos ni incorpora credenciales al runtime supervisado. Health/issues y metadata permanecen sanitizados.

### 5. Sin IO productivo obligatorio

La fase no introdujo backend productivo de monitoreo, network IO, filesystem IO productivo, SQL productivo, Redis productivo ni `sleep`. Los harnesses de referencia usados por tests son deterministas e in-memory.

### 6. Determinismo y validación runtime

Se preservaron:

- `dataclass(frozen=True, slots=True)` en contratos de estado;
- `Protocol` para boundaries estructurales;
- `Result` / `Success` / `Failure`;
- errores tipados;
- timestamps explícitos y timezone-aware;
- ausencia de `datetime.now()` y `uuid4()` en la nueva composición;
- metadata segura e inmutable;
- ordering estable;
- validación runtime y rechazo de bypasses.

### 7. Quality Gate histórico verificado

Los heads finales de implementación de PHASE-08 tienen QORE CI real verde:

```text
#57 -> QORE CI #269 -> Ruff PASS / Mypy PASS / Pytest PASS
#58 -> QORE CI #271 -> Ruff PASS / Mypy PASS / Pytest PASS
#59 -> QORE CI #273 -> Ruff PASS / Mypy PASS / Pytest PASS
#60 -> QORE CI #276 -> Ruff PASS / Mypy PASS / Pytest PASS
#61 -> QORE CI #279 -> Ruff PASS / Mypy PASS / Pytest PASS
#62 -> QORE CI #285 -> Ruff PASS / Mypy PASS / Pytest PASS
#63 -> QORE CI #289 -> Ruff PASS / Mypy PASS / Pytest PASS
```

La revisión de cierre no rebaja `strict = true`, no desactiva checks y no añade excepciones para maquillar el Quality Gate.

## Criterios de aceptación globales

Los PR de PHASE-08 se integran únicamente con código de salida 0 para el Quality Gate configurado en el repositorio, incluyendo:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Además se mantiene:

- Mypy strict;
- tests deterministas;
- contratos públicos con validación runtime;
- errores tipados y propagación de `Failure`;
- activación externa allowed/blocked/degraded;
- lifecycle con transición válida e inválida;
- referencias de secretos sin exposición de valores;
- harnesses sin IO productivo obligatorio;
- Runtime, Functional Governance y Specialized Governance aislados de providers concretos.

## Quality Gate de cierre

`QORE-PHASE08-CLOSURE-001` solo puede integrarse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan reviews pendientes;
- no existan review threads pendientes;
- el PR sea mergeable;
- el CI pertenezca al head final;
- el merge protegido use ese head exacto;
- `main` sea confirmado idéntico al merge commit.

Hasta que esas condiciones se cumplan en GitHub, la marca `COMPLETED` de esta rama no constituye por sí sola el cierre oficial de la fase.

## Condición de cierre

Una vez mergeado `QORE-PHASE08-CLOSURE-001` bajo el Quality Gate anterior, PHASE-08 queda oficialmente cerrada porque todos sus entregables están integrados y la revisión transversal confirma que QORE puede supervisar providers externos bajo lifecycle, activation policy, external runtime plan, health aggregation y composición E2E sin romper la independencia del Core ni habilitar ejecución real de trading.

## Resultado final

PHASE-08 entrega una capa de runtime externo supervisado con:

- lifecycle determinista;
- políticas de activación fail-closed;
- plan externo separado del Core;
- health aggregation provider-neutral;
- harness supervisado sobre market data y persistence;
- composición E2E explícita por encima del Core;
- ports expuestos únicamente cuando la supervisión los permite;
- failures tipados para degradación, bloqueo, identity mismatch, lifecycle ausente y harness no disponible;
- Core/RuntimePlan preservados;
- cero trading execution y cero dependencia live obligatoria.

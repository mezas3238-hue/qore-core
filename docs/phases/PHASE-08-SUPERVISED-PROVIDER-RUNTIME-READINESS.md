# PHASE-08 — Supervised Provider Runtime Readiness

## Estado

**ACTIVE**

PHASE-08 comienza después del cierre formal de PHASE-07 — External Provider Integration Readiness.

Base inicial de trabajo:

```text
main @ acc229d982171e2b27e08fa3dc689ee86cb89340
```

## Objetivo

Preparar QORE para operar proveedores externos bajo un runtime supervisado, explícito y reversible, sin convertir todavía esa preparación en ejecución de trading ni en conectividad live obligatoria.

PHASE-07 dejó definidos los contratos de provider, configuración, secretos, observabilidad, resiliencia y harnesses deterministas. PHASE-08 toma esa frontera y añade una capa de supervisión operativa:

```text
provider configuration
→ activation policy
→ external runtime plan
→ adapter lifecycle
→ supervised provider harness
→ health / observability / resilience aggregation
→ canonical application ports
```

El objetivo es que futuros adapters reales puedan activarse de forma controlada, auditada y fail-closed. No se busca enviar órdenes, operar cuentas reales, abrir posiciones, conectar MT5 ni exponer APIs públicas.

## Principios

- El repositorio sigue siendo la fuente única de verdad.
- El Core permanece libre de adapters concretos.
- Domain, Runtime, Functional Governance y Specialized Governance no importan providers ni adapters concretos.
- La composición de infraestructura sigue siendo explícita y opt-in.
- El `RuntimePlan` del Core no registra adapters externos automáticamente.
- La supervisión de providers externos vive por encima del Core o en fronteras de infraestructura explícitas.
- Todo lifecycle externo debe ser declarativo, determinista y reversible.
- Todo timestamp, correlation, causation, identifier y transition reason debe ser explícito.
- Ningún lifecycle contract puede usar reloj global implícito.
- Ningún contrato puede resolver secretos productivos por sí mismo.
- Ninguna política puede activar un adapter sin una configuración válida, capability checks y secret references explícitas.
- Toda degradación externa se expresa como `Failure` tipado, health degradado o readiness no disponible.
- Todo modo de activación debe ser fail-closed por defecto.
- Los harnesses siguen siendo deterministas antes de cualquier adapter live.

## Fuera de alcance

PHASE-08 no implementa:

- ejecución real de órdenes;
- order routing de broker/exchange;
- MT5 trading;
- gestión de posiciones reales;
- account funding o withdrawals;
- credenciales productivas en repositorio;
- conexión obligatoria a broker live;
- automatización de entradas/salidas de trading;
- cambios autónomos de Optimization sobre configuración productiva;
- QORE Mobile o Widget del CEO;
- UI pública;
- REST/gRPC/WebSocket públicos de QORE;
- scheduler productivo externo;
- infraestructura distribuida productiva obligatoria;
- mutación automática de `RuntimePlan` del Core.

## Frontera de arquitectura

PHASE-08 introduce readiness de runtime externo supervisado por encima de PHASE-07, no dentro del Core.

Permitido:

```text
qore.infrastructure.adapter_lifecycle
qore.infrastructure.provider_runtime
qore.infrastructure.activation_policy
qore.infrastructure.external_health
qore.infrastructure.supervised_provider_harness
qore.infrastructure.supervised_provider_readiness
```

No permitido:

```text
qore.core -> provider adapters
qore.domain -> provider adapters
qore.governance -> concrete adapters
qore.specialized_governance -> concrete adapters
RuntimePlan -> automatic provider adapter registration
provider runtime -> order execution
provider runtime -> secret value exposure
```

La nueva frontera debe poder observar y supervisar adapters externos sin convertirlos en componentes internos del Core.

## Entregables

### QORE-PHASE08-DOCS-001 — Define PHASE-08 Scope

Estado: definido, pendiente de implementación.

Crear la definición oficial de PHASE-08 con alcance, frontera, entregables, fuera de alcance, Quality Gate y condición de cierre.

Alcance mínimo:

- documento de fase en `docs/phases`;
- estado inicial `ACTIVE`;
- base SHA explícita;
- entregables definidos;
- restricciones preservadas desde PHASE-07;
- no cambios funcionales.

### QORE-ADAPTER-LIFECYCLE-001 — External Adapter Lifecycle Contracts

Estado: definido, pendiente de implementación.

Definir contratos de lifecycle externo para adapters gobernados.

Alcance mínimo:

- estados cerrados de lifecycle: `declared`, `configured`, `initialized`, `started`, `degraded`, `stopped`, `failed` o equivalentes;
- transiciones explícitas con timestamp inyectado por caller;
- razones tipadas de transición;
- actor/correlation/causation explícitos;
- errores tipados para transición inválida;
- cero reloj global implícito;
- cero sleep, red o IO real;
- pruebas de validación runtime y transición determinista.

### QORE-ACTIVATION-POLICY-001 — Provider Activation Policy Contracts

Estado: definido, pendiente de implementación.

Definir políticas de activación fail-closed para providers externos.

Alcance mínimo:

- modos cerrados de activación: `disabled`, `dry_run`, `simulation`, `read_only` o equivalentes;
- capability checks contra `ProviderDescriptor`;
- validación de configuración externa;
- requisitos explícitos de secret references, sin valores sensibles;
- compatibilidad con observability/resilience readiness;
- decisión tipada: allowed/blocked/degraded;
- errores tipados de política;
- pruebas de bloqueo por configuración inválida, secretos ausentes, capability mismatch y degraded provider.

### QORE-PROVIDER-RUNTIME-PLAN-001 — External Provider Runtime Plan Contracts

Estado: definido, pendiente de implementación.

Crear un plan de runtime externo separado del `RuntimePlan` del Core.

Alcance mínimo:

- `ExternalRuntimePlan` o equivalente canónico;
- componentes externos declarativos, no componentes del Core;
- orden de activación estable;
- dependencias explícitas entre providers/adapters;
- validación de duplicates y cycles simples;
- no mutar `CoreApplication.runtime_plan`;
- no registrar adapters en el `RuntimePlan` del Core;
- pruebas de orden estable, aislamiento y rechazo de bypasses.

### QORE-EXTERNAL-HEALTH-AGGREGATION-001 — External Provider Health Aggregation

Estado: definido, pendiente de implementación.

Agregar health/readiness externo desde lifecycle, observability, resilience y activation policy.

Alcance mínimo:

- snapshot agregado provider-neutral;
- readiness global cerrado: ready/degraded/unavailable/blocked;
- degradaciones y errores sanitizados;
- timestamps explícitos;
- source/provider/adapter identity preservada;
- no backend productivo de monitoreo;
- no payload sensible;
- tests de ready, degraded, unavailable y blocked.

### QORE-SUPERVISED-PROVIDER-HARNESS-001 — Supervised Provider Runtime Harness

Estado: definido, pendiente de implementación.

Crear un harness determinista que simule supervisión runtime de los harnesses de Market Data y Persistence ya integrados.

Alcance mínimo:

- composición sobre `ReadOnlyMarketDataProviderHarness` y `PersistenceBackendHarness`;
- lifecycle transitions explícitas;
- activation policy aplicada antes de exponer ports;
- health aggregation sin backend externo;
- failure propagation end-to-end;
- no conexión live obligatoria;
- no secretos productivos;
- no red/filesystem/SQL/Redis productivo;
- tests de start/stop/degraded/blocked/unavailable.

### QORE-SUPERVISED-RUNTIME-E2E-001 — Supervised Runtime End-to-End Composition

Estado: definido, pendiente de implementación.

Demostrar el recorrido E2E de runtime externo supervisado:

```text
provider config
→ activation policy
→ external runtime plan
→ supervised provider harness
→ health aggregation
→ canonical infrastructure ports
→ application-level consumption
```

Alcance mínimo:

- composición explícita por encima del Core;
- un solo `CoreApplication` preservado;
- `EventBus` preservado;
- `RuntimeSnapshot`, `RuntimeHealth` y `RuntimePlan` del Core intactos;
- Functional Governance y Specialized Governance siguen funcionando sin provider runtime;
- `Failure` propagation end-to-end;
- no trading execution;
- pruebas de aislamiento entre composiciones.

### QORE-PHASE08-CLOSURE-001 — Phase 08 Closure Review

Estado: definido, pendiente de implementación.

Cerrar PHASE-08 únicamente después de revisión transversal.

Auditar:

- no imports inversos hacia providers o supervised runtime;
- no secretos expuestos;
- no red obligatoria en tests;
- no filesystem/SQL/Redis productivo obligatorio;
- no ejecución de trading;
- no mutación de `RuntimePlan` del Core;
- no generación implícita de UUID/timestamps;
- lifecycle determinista y reversible;
- activation policy fail-closed;
- compatibilidad completa de PHASE-04/05/06/07;
- Quality Gate verde en el head final.

## Criterios de aceptación globales

Todos los PR de PHASE-08 deben terminar con código de salida 0 para:

```bash
python --version
pip install -e ".[dev]"
python -c "import qore; print(qore.__name__)"
pytest
ruff check .
mypy src tests
```

Además:

- Mypy permanece en `strict = true`.
- Las pruebas son deterministas.
- Todo contrato público tiene pruebas de validación runtime.
- Toda frontera prueba errores tipados y propagación de `Failure`.
- Toda activación externa prueba allowed/blocked/degraded.
- Todo lifecycle prueba transición válida e inválida.
- Toda referencia a secreto prueba no exposición.
- Todo harness supervisado prueba ausencia de IO productivo obligatorio.
- Los cambios de composición vuelven a probar Runtime, Functional Governance y Specialized Governance.

## Quality Gate

Cada PR solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera de alcance;
- el head revisado sea exactamente el head mergeado;
- la revisión semántica confirme que no se introdujo ejecución de trading;
- la revisión semántica confirme que no se introdujo dependencia inversa hacia providers o supervised runtime;
- la revisión semántica confirme que no se filtraron secretos;
- la revisión semántica confirme que el `RuntimePlan` del Core no fue mutado.

## Condición de cierre

PHASE-08 se marcará `COMPLETED` únicamente cuando todos sus entregables estén integrados y una revisión transversal confirme que QORE puede supervisar providers externos bajo lifecycle, activation policy, external runtime plan y health aggregation, sin romper la independencia del Core ni habilitar ejecución real de trading.

## Resultado esperado

Al cerrar PHASE-08, QORE debe disponer de una capa de runtime externo supervisado: lifecycle determinista, políticas de activación fail-closed, plan externo separado del Core, health aggregation y harnesses supervisados que permitan preparar adapters reales con seguridad antes de conectividad live o ejecución real.

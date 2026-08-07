# PHASE-02 — Core Runtime Contracts

## Estado

**COMPLETED**

PHASE-02 quedó cerrada después de integrar y revisar transversalmente RUNTIME-001, RUNTIME-002, RUNTIME-003, RUNTIME-004 y RUNTIME-005. El cierre confirma una única ruta oficial de ejecución desde `bootstrap()` hasta lifecycle, supervisor, snapshot y health/readiness.

## Objetivo

Convertir la fundación mínima de QORE en un runtime determinista, extensible y explícitamente gobernado por contratos, sin introducir lógica de negocio ni dependencias de infraestructura.

PHASE-02 establece identidad de ejecución, composición de componentes, lifecycle ordenado, introspección inmutable, health/readiness derivados y una única ruta oficial de ejecución desde el composition root.

## Principios cumplidos

- Determinismo antes que conveniencia.
- Contratos explícitos antes que acoplamiento implícito.
- Inmutabilidad por defecto.
- Sin estado global mutable.
- Sin service locator arbitrario.
- Sin efectos externos dentro del Core.
- Errores controlados mediante tipos del Kernel y `Result`.
- `RuntimeSnapshot` como fuente de verdad observable del runtime.
- Health/readiness como proyección pura del snapshot.
- Una única ruta oficial de start/stop para una aplicación bootstrapeada.
- Compatibilidad preservada con PHASE-01 y con `bootstrap()` Genesis.

## Fuera de alcance preservado

Esta fase no implementa trading, Traders Virtuales, CIBO, Portfolio Manager, Risk Engine, Validation Lab, Statistics, Knowledge, Optimization, market data, news APIs, persistencia, logging/auditoría externos, métricas, tracing, telemetry, adapters de broker/exchange, asincronía distribuida ni QORE Mobile.

## Entregables integrados

### QORE-CORE-RUNTIME-001 — Runtime Context & Execution Contracts

Estado: integrado.

- `RuntimeContext` inmutable.
- Identidad y versionado explícitos de ejecución.
- `RuntimeComponent` estructural.
- Registro/resolución tipados.
- Eventos `runtime started`, `runtime stopped`, `runtime failed`.
- Reloj inyectado.
- Fallos propagados mediante `Result`.

### QORE-CORE-RUNTIME-002 — Component Graph & Ordered Lifecycle

Estado: integrado.

- `RuntimeComponentSpec` y `RuntimePlan` inmutables.
- Validación de duplicados, dependencias inexistentes y ciclos.
- Orden topológico estable.
- `RuntimeSupervisor` con start/stop deterministas.
- Stop inverso al orden efectivo de start.
- Rollback ante fallo de start.
- Conservación explícita de componentes residuales.

### QORE-CORE-RUNTIME-003 — Runtime State & Introspection Contracts

Estado: integrado.

- `RuntimeStatus`: `STOPPED`, `RUNNING`, `DEGRADED`.
- `RuntimeComponentStatus`: `INACTIVE`, `ACTIVE`, `RESIDUAL`.
- `RuntimeComponentSnapshot` y `RuntimeSnapshot` inmutables.
- `RuntimeSupervisor.snapshot()` como lectura pura.
- Invariantes que rechazan snapshots contradictorios.
- Estado residual representado explícitamente y con orden estable.

### QORE-CORE-RUNTIME-004 — Runtime Health & Readiness Contracts

Estado: integrado.

- `RuntimeHealthStatus`: `HEALTHY`, `DEGRADED`, `UNHEALTHY`.
- `RuntimeReadiness`: `READY`, `NOT_READY`.
- Motivos estructurados de health/readiness.
- `RuntimeHealthSnapshot` inmutable con invariantes propias.
- `evaluate_runtime_health(snapshot)` como proyección pura y determinista.
- `STOPPED -> UNHEALTHY + NOT_READY`.
- `RUNNING -> HEALTHY + READY`.
- `DEGRADED -> DEGRADED + NOT_READY`.
- Residuales reportados como degradados y bloqueantes.

### QORE-CORE-RUNTIME-005 — Runtime Composition & Application Integration

Estado: integrado.

La revisión transversal posterior a RUNTIME-004 detectó y corrigió el último hueco fundacional: `RuntimeSupervisor` existía como contrato independiente pero no formaba parte del composition root oficial.

RUNTIME-005 cerró esa brecha:

- `bootstrap(Configuration)` construye un `RuntimePlan` oficial.
- `CoreEngine` aparece una sola vez en ese plan como `core-engine`.
- `bootstrap(Configuration)` construye un `RuntimeSupervisor` oficial.
- `CoreApplication` expone `runtime_plan` y `runtime_supervisor`.
- `CoreApplication.runtime_snapshot()` produce la lectura oficial del estado actual.
- `CoreApplication.runtime_health()` deriva health/readiness desde ese snapshot.
- `ApplicationLifecycle` delega start/stop al supervisor cuando está compuesto por bootstrap.
- No existe doble ejecución de `CoreEngine`.
- `ApplicationLifecycle(engine)` directo conserva compatibilidad histórica.
- Un fallo durante start conserva el error original y mantiene la semántica de rollback/residuales del supervisor.
- Un fallo al publicar `RuntimeStartedEvent` intenta rollback por la misma ruta oficial y conserva el fallo de publicación como error principal.
- Una aplicación sin `RuntimeContext` sigue teniendo supervisor/snapshot/health, pero no emite eventos de runtime.
- Una aplicación con `RuntimeContext` y clock conserva eventos deterministas.

## Invariantes finales de PHASE-02

1. `bootstrap()` sin argumentos conserva exactamente la identidad Genesis.
2. Toda `CoreApplication` construida con `Configuration` tiene `RuntimePlan` y `RuntimeSupervisor` oficiales.
3. `ApplicationLifecycle` es la máquina de estados de aplicación y `RuntimeSupervisor` es el ejecutor del plan; no compiten entre sí.
4. El `CoreEngine` se inicia y detiene una sola vez por transición supervisada.
5. Tras bootstrap, el runtime oficial está `STOPPED` y deriva `UNHEALTHY + NOT_READY`.
6. Tras start exitoso, está `RUNNING` y deriva `HEALTHY + READY`.
7. Tras stop exitoso, vuelve a `STOPPED` y deriva `UNHEALTHY + NOT_READY`.
8. Estado residual se representa como `DEGRADED` y deriva `DEGRADED + NOT_READY`.
9. Snapshot y health son proyecciones de solo lectura, inmutables y deterministas.
10. No se introducen conexiones externas, reloj global, UUID implícito, threads, asyncio ni dominio de trading.

## Quality Gate final

El último entregable de la fase, PR #8 (`QORE-CORE-RUNTIME-005 — Runtime Composition & Application Integration`), fue revisado sobre su head exacto antes de merge y cumplió:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- QORE CI Run #66 = SUCCESS;
- cero hilos de revisión pendientes;
- cero reviews pendientes;
- head revisado = head mergeado;
- revisión semántica transversal = PASS.

## Resultado de cierre

PHASE-02 cumple su objetivo. QORE posee ahora un runtime base capaz de representar una ejecución, componer componentes, gobernar su ciclo de vida por una única ruta oficial, exponer estado mediante snapshots inmutables y derivar health/readiness deterministas.

Las siguientes fases pueden construir observabilidad externa, servicios de dominio y superficies de control sobre estos contratos sin reabrir responsabilidades fundacionales del runtime ni contaminar el Core con infraestructura o lógica de trading.

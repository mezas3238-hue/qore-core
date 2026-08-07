# PHASE-02 — Core Runtime Contracts

## Estado

En cierre. RUNTIME-001, RUNTIME-002, RUNTIME-003 y RUNTIME-004 están integrados. RUNTIME-005 es el último entregable requerido por la revisión transversal para cerrar la fase sin dejar dos rutas paralelas de ejecución.

## Objetivo

Convertir la fundación mínima de QORE en un runtime determinista, extensible y explícitamente gobernado por contratos, sin introducir lógica de negocio ni dependencias de infraestructura.

PHASE-02 establece identidad de ejecución, composición de componentes, lifecycle ordenado, introspección inmutable, health/readiness derivados y una única ruta oficial de ejecución desde el composition root.

## Principios

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

## Fuera de alcance

Esta fase no implementa trading, Traders Virtuales, CIBO, Portfolio Manager, Risk Engine, Validation Lab, Statistics, Knowledge, Optimization, market data, news APIs, persistencia, logging/auditoría externos, métricas, tracing, telemetry, adapters de broker/exchange, asincronía distribuida ni QORE Mobile.

## Entregables

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

Estado: definido, pendiente de implementación.

#### Motivo

La revisión transversal posterior a RUNTIME-004 detectó que los contratos del supervisor existen y funcionan, pero el composition root oficial todavía construye `CoreEngine` y `ApplicationLifecycle` sin integrar `RuntimePlan`/`RuntimeSupervisor`. Eso deja dos rutas paralelas de ejecución y evita que una `CoreApplication` bootstrapeada sea la fuente oficial de snapshot y health.

#### Objetivo

Cerrar la composición de PHASE-02 haciendo que toda `CoreApplication` construida con `Configuration` posea un `RuntimePlan` y un `RuntimeSupervisor` oficiales, y que `ApplicationLifecycle` coordine start/stop a través de ese supervisor sin duplicar la ejecución de `CoreEngine`.

#### Alcance

- El composition root debe construir un `RuntimePlan` explícito cuyo componente mínimo sea `CoreEngine`.
- El composition root debe construir un `RuntimeSupervisor` asociado al `RuntimeContext` opcional ya suministrado.
- `CoreApplication` debe exponer `runtime_plan` y `runtime_supervisor` como referencias oficiales de composición.
- `CoreApplication` debe ofrecer acceso de solo lectura al `RuntimeSnapshot` actual y a su `RuntimeHealthSnapshot` derivado, sin caché mutable.
- `ApplicationLifecycle` debe aceptar un `RuntimeSupervisor` opcional.
- Cuando exista supervisor, `ApplicationLifecycle.start()` debe delegar el arranque al supervisor y no llamar además a `CoreEngine.start()`.
- Cuando exista supervisor, `ApplicationLifecycle.stop()` debe delegar la parada al supervisor y no llamar además a `CoreEngine.stop()`.
- El uso directo histórico de `ApplicationLifecycle(engine)` sin supervisor debe conservar su comportamiento actual.
- Si el arranque del supervisor falla, lifecycle debe entrar en `ERROR`, preservar el error original y el supervisor debe conservar cualquier residual según RUNTIME-002.
- Si falla la publicación de `RuntimeStartedEvent` después de un arranque exitoso, lifecycle debe intentar rollback mediante la misma ruta oficial de ejecución y preservar como error principal el fallo de publicación.
- `bootstrap()` sin argumentos debe seguir devolviendo exactamente `CoreIdentity` Genesis.
- `bootstrap(Configuration)` debe producir una aplicación con runtime oficial aun cuando no exista `RuntimeContext`; en ese caso no se emiten eventos de runtime, pero sí existen supervisor/snapshot/health.
- `bootstrap(Configuration, runtime_context=..., clock=...)` debe conservar eventos deterministas y usar el mismo supervisor oficial.

#### Invariantes

1. Una aplicación bootstrapeada no puede tener dos caminos independientes de start/stop para el mismo `CoreEngine`.
2. `CoreEngine` debe aparecer una sola vez en el plan oficial y su nombre debe coincidir con `component_name`.
3. Tras `bootstrap(Configuration)`, el snapshot inicial debe ser `STOPPED` y health `UNHEALTHY + NOT_READY`.
4. Tras `app.lifecycle.start()`, el supervisor debe estar `RUNNING`, el snapshot debe ser `RUNNING` y health `HEALTHY + READY`.
5. Tras `app.lifecycle.stop()`, el supervisor debe volver a `STOPPED` y health a `UNHEALTHY + NOT_READY`.
6. Snapshot y health obtenidos desde `CoreApplication` deben ser nuevas proyecciones de solo lectura, sin mutar supervisor ni componentes.
7. No se introducen conexiones externas, reloj global, UUID implícito, threads, asyncio ni dominio de trading.
8. La compatibilidad de `bootstrap()` Genesis y de `ApplicationLifecycle(engine)` directo es obligatoria.

#### Pruebas obligatorias

- `bootstrap -> snapshot -> health` antes de start.
- `bootstrap -> start -> snapshot -> health`.
- `bootstrap -> start -> stop -> snapshot -> health`.
- Verificación de que `CoreEngine.start/stop` se invoca exactamente una vez mediante la ruta supervisada.
- Fallo de start del componente con lifecycle `ERROR` y error original preservado.
- Fallo de `RuntimeStartedEvent` con rollback de la ejecución ya iniciada.
- Aplicación sin `RuntimeContext` con supervisor funcional pero sin eventos de runtime.
- Aplicación con `RuntimeContext` y clock con eventos deterministas.
- Compatibilidad de `ApplicationLifecycle(engine)` directo.
- Ruff, Mypy strict y Pytest completamente verdes.

## Restricciones arquitectónicas

1. El Runtime no importa dominio de trading.
2. El Runtime no crea conexiones externas.
3. El Runtime no depende de reloj global ni genera timestamps/UUID implícitos.
4. No usa singletons ni registros globales mutables.
5. Contextos, planes, snapshots y proyecciones de health permanecen inmutables.
6. Todo fallo operacional representable usa `Result` cuando el contrato existente lo requiere.
7. La composición del Core permanece explícita.
8. `bootstrap()` Genesis no puede romperse.
9. Introspección y health/readiness son operaciones puras.
10. La aplicación bootstrapeada tiene una sola autoridad de ejecución: `ApplicationLifecycle` como máquina de estados delegando en `RuntimeSupervisor` como ejecutor del plan.

## Quality Gate

Cada PR de PHASE-02 solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera de alcance;
- el head revisado sea exactamente el head mergeado.

## Condición de cierre

PHASE-02 se marcará `COMPLETED` únicamente después de integrar RUNTIME-005, ejecutar su Quality Gate y repetir una revisión transversal que confirme que `bootstrap`, lifecycle, supervisor, snapshot y health forman una única ruta coherente de ejecución.

## Resultado esperado

Al cerrar esta fase, QORE poseerá un runtime base capaz de representar una ejecución, componer componentes, gobernar su ciclo de vida por una única ruta oficial, exponer su estado interno mediante snapshots inmutables y derivar health/readiness deterministas, listo para fases posteriores sin contaminar el Core con infraestructura ni lógica de trading.

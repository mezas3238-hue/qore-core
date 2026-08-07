# PHASE-02 — Core Runtime Contracts

## Objetivo

Convertir la fundación mínima de QORE en un runtime determinista, extensible y explícitamente gobernado por contratos, sin introducir todavía lógica de negocio ni dependencias de infraestructura.

Esta fase debe establecer cómo se identifica una ejecución, cómo se compone el Core, cómo se registran y resuelven componentes, cómo se representan los eventos internos de lifecycle, cómo se propagan los errores de forma uniforme mediante `Result`, cómo se consulta el estado interno del runtime sin exponer estado mutable y cómo se deriva de ese estado una señal interna de health/readiness sin infraestructura externa.

## Principios

- Determinismo antes que conveniencia.
- Contratos explícitos antes que acoplamiento implícito.
- Inmutabilidad por defecto en objetos de contexto y configuración.
- Sin estado global mutable.
- Sin service locator arbitrario.
- Sin efectos externos dentro del Core.
- Errores controlados mediante tipos del Kernel y `Result`.
- Estado observable mediante snapshots inmutables, no mediante acceso a internals mutables.
- Health y readiness derivados del estado oficial del runtime, nunca mantenidos como una segunda fuente de verdad.
- Compatibilidad preservada con PHASE-01.

## Fuera de alcance

Esta fase no implementa:

- trading ni lógica de estrategia;
- Traders Virtuales;
- CIBO;
- Portfolio Manager;
- Risk Engine;
- Validation Lab;
- Statistics, Knowledge u Optimization;
- market data;
- news APIs;
- persistencia;
- logging o auditoría externos;
- métricas, tracing o telemetry externos;
- adapters de broker, exchange o infraestructura;
- asincronía distribuida;
- QORE Mobile.

## Entregables

### QORE-CORE-RUNTIME-001 — Runtime Context & Execution Contracts

Estado: integrado.

Introduce los contratos mínimos necesarios para representar y gobernar una ejecución del Core:

- `RuntimeContext` inmutable;
- identidad explícita de ejecución;
- versionado mínimo del runtime;
- `RuntimeComponent` como contrato estructural;
- registro y resolución tipados;
- eventos `runtime started`, `runtime stopped` y `runtime failed`;
- reloj inyectado;
- propagación de fallos mediante `Result`;
- compatibilidad con PHASE-01.

### QORE-CORE-RUNTIME-002 — Component Graph & Ordered Lifecycle

Estado: integrado.

Convierte los componentes individuales del runtime en una composición explícita y determinista:

- `RuntimeComponentSpec` inmutable con dependencias explícitas;
- `RuntimePlan` declarativo e inmutable;
- validación de nombres duplicados y dependencias inexistentes;
- rechazo de ciclos antes de ejecutar componentes;
- orden topológico estable y reproducible;
- `RuntimeSupervisor` con arranque y parada deterministas;
- parada en orden inverso al arranque efectivo;
- rollback de componentes ya iniciados ante fallo de `start`;
- preservación del error original durante rollback;
- conservación explícita de componentes residuales que no pudieron detenerse;
- sin paralelismo, threads, asyncio ni efectos externos.

### QORE-CORE-RUNTIME-003 — Runtime State & Introspection Contracts

Estado: integrado.

Introduce introspección inmutable y determinista del runtime:

- `RuntimeStatus` con `STOPPED`, `RUNNING` y `DEGRADED`;
- `RuntimeComponentStatus` con `INACTIVE`, `ACTIVE` y `RESIDUAL`;
- `RuntimeComponentSnapshot` y `RuntimeSnapshot` inmutables;
- `RuntimeSupervisor.snapshot()` como operación de lectura pura;
- orden declarativo estable para componentes;
- orden efectivo de arranque para componentes activos;
- representación explícita de componentes residuales;
- invariantes que rechazan snapshots contradictorios;
- preservación opcional de `RuntimeContext` sin generación implícita;
- cobertura determinista de construcción, start, stop, rollback limpio, rollback incompleto y stop incompleto.

### QORE-CORE-RUNTIME-004 — Runtime Health & Readiness Contracts

Estado: definido, pendiente de implementación.

#### Objetivo

Introducir un contrato puro, inmutable y determinista que derive la condición operativa del runtime a partir de `RuntimeSnapshot`, sin mantener estado adicional y sin introducir health checks externos, red, logging, métricas ni infraestructura.

Este entregable establece la frontera entre **estado del runtime** e **interpretación operativa del estado**. `RuntimeSnapshot` continúa siendo la fuente de verdad; health y readiness son únicamente una proyección derivada.

#### Alcance

- `RuntimeHealthStatus` como enum explícito con estados mínimos:
  - `HEALTHY`;
  - `DEGRADED`;
  - `UNHEALTHY`.
- `RuntimeReadiness` como enum explícito con estados mínimos:
  - `READY`;
  - `NOT_READY`.
- `RuntimeHealthReason` o contrato equivalente, inmutable y estructurado, para explicar por qué un runtime no está listo o está degradado.
- `RuntimeHealthSnapshot` inmutable con, como mínimo:
  - health agregado;
  - readiness agregado;
  - motivos estructurados;
  - nombres de componentes bloqueantes;
  - nombres de componentes degradados;
  - referencia o copia inmutable del estado base necesario para trazabilidad lógica, sin duplicar estado mutable.
- función o servicio puro de derivación, por ejemplo `evaluate_runtime_health(snapshot)` o contrato equivalente.
- La derivación no puede mutar `RuntimeSnapshot`, `RuntimeSupervisor` ni ningún componente.
- No puede existir caché mutable ni estado interno persistente en el evaluador.
- Dos evaluaciones del mismo `RuntimeSnapshot` deben producir valores equivalentes.

#### Semántica mínima obligatoria

1. `RuntimeStatus.STOPPED`:
   - health = `UNHEALTHY`;
   - readiness = `NOT_READY`;
   - ningún componente puede marcarse como degradado si no existe residual;
   - debe existir un motivo estructurado que indique que el runtime está detenido.
2. `RuntimeStatus.RUNNING` sin residuales:
   - health = `HEALTHY`;
   - readiness = `READY`;
   - no existen componentes bloqueantes ni degradados.
3. `RuntimeStatus.DEGRADED`:
   - health = `DEGRADED`;
   - readiness = `NOT_READY`;
   - los componentes residuales deben aparecer como degradados y bloqueantes.
4. Un `RuntimeSnapshot` válido nunca puede producir combinaciones contradictorias como `HEALTHY + NOT_READY` o `UNHEALTHY + READY` bajo las reglas de RUNTIME-004.
5. `RuntimeHealthSnapshot` debe validar sus propias invariantes para impedir construcción manual contradictoria.
6. La readiness representa capacidad del runtime para aceptar trabajo del Core, no conectividad de infraestructura externa.

#### Reglas e invariantes

1. `RuntimeSnapshot` es la única fuente de verdad de entrada.
2. Health/readiness no pueden mantener una segunda máquina de estados independiente.
3. Toda salida debe ser inmutable.
4. La evaluación debe ser pura y determinista.
5. No se permiten timestamps implícitos, UUIDs nuevos ni uso de reloj global.
6. No se permiten llamadas a `start()`, `stop()`, event handlers ni efectos colaterales durante la evaluación.
7. Los nombres de componentes bloqueantes/degradados deben proceder exclusivamente de componentes declarados en el snapshot.
8. El orden de componentes reportados debe ser estable y documentado.
9. `READY` solo es válido cuando el runtime se encuentra en ejecución normal.
10. `DEGRADED` siempre implica `NOT_READY` durante PHASE-02.
11. `UNHEALTHY` siempre implica `NOT_READY` durante PHASE-02.
12. La incorporación de health/readiness no puede modificar la semántica pública de `RuntimeSupervisor`, `ApplicationLifecycle` ni `bootstrap()`.

#### Fuera de alcance específico de RUNTIME-004

- heartbeat temporal;
- latencia;
- health checks de broker;
- health checks de base de datos;
- health checks de APIs o red;
- disponibilidad de market data;
- logging;
- Prometheus;
- OpenTelemetry;
- tracing;
- persistencia histórica;
- alertas;
- REST/HTTP endpoints;
- dashboard;
- Widget del CEO;
- comandos remotos;
- CIBO;
- lógica de trading.

Estos consumidores y fuentes externas de health podrán construirse en fases posteriores sobre este contrato interno.

#### Criterios de aceptación específicos

Además del Quality Gate global de PHASE-02:

- un snapshot `STOPPED` debe derivar `UNHEALTHY + NOT_READY`;
- un snapshot `RUNNING` válido debe derivar `HEALTHY + READY`;
- un snapshot `DEGRADED` debe derivar `DEGRADED + NOT_READY`;
- los residuales deben aparecer de forma determinista como componentes degradados y bloqueantes;
- una evaluación repetida del mismo snapshot debe comparar por valor como equivalente;
- la evaluación no debe producir efectos sobre supervisor, componentes o event bus;
- `RuntimeHealthSnapshot` debe rechazar combinaciones contradictorias;
- deben existir pruebas explícitas para plan vacío detenido y plan vacío en ejecución;
- Ruff, Mypy strict y Pytest deben pasar completamente.

#### Condición de cierre de PHASE-02

PHASE-02 podrá declararse `completed` cuando RUNTIME-004 esté integrado y su Quality Gate haya pasado completamente, siempre que una revisión final confirme que no queda ninguna capacidad fundacional pendiente dentro del alcance definido para Core Runtime Contracts.

## Restricciones arquitectónicas

1. El Runtime no puede importar módulos de dominio de trading.
2. El Runtime no puede crear conexiones externas.
3. El Runtime no puede depender de reloj global ni generar timestamps implícitos no inyectados.
4. El Runtime no puede usar singletons ni registros globales mutables.
5. Los objetos de contexto, planes declarativos, snapshots y proyecciones de health deben ser inmutables.
6. Todo fallo operacional representable debe retornar `Result` cuando el contrato existente de QORE lo requiera.
7. La composición del Core debe permanecer explícita.
8. Ningún cambio puede romper `bootstrap()` sin argumentos introducido en Genesis.
9. La introspección debe ser una operación de lectura pura.
10. Health/readiness deben ser proyecciones puras de `RuntimeSnapshot`.

## Criterios de aceptación

Todos son obligatorios y deben terminar con código de salida 0:

```bash
python --version
pip install -e ".[dev]"
python -c "import qore; print(qore.__name__)"
pytest
ruff check .
mypy src tests
```

Además:

- `mypy` debe ejecutarse con `strict = true`.
- Las nuevas pruebas deben ser deterministas.
- Debe demostrarse que no se introduce ninguna dependencia de infraestructura o dominio de trading.
- El CI de GitHub Actions debe terminar completamente en verde antes de merge.

## Quality Gate

Cada PR de PHASE-02 solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera del alcance de esta fase;
- el head revisado sea exactamente el head que se mergea.

## Resultado esperado

Al cerrar esta fase, QORE debe poseer un runtime base capaz de representar una ejecución, componer componentes, gobernar su ciclo de vida, exponer su estado interno mediante contratos inmutables y derivar su condición operativa interna mediante health/readiness deterministas, listo para que fases posteriores incorporen observabilidad externa, servicios de dominio y superficies de control sin contaminar el Core con infraestructura ni lógica de trading.

# PHASE-02 — Core Runtime Contracts

## Objetivo

Convertir la fundación mínima de QORE en un runtime determinista, extensible y explícitamente gobernado por contratos, sin introducir todavía lógica de negocio ni dependencias de infraestructura.

Esta fase debe establecer cómo se identifica una ejecución, cómo se compone el Core, cómo se registran y resuelven componentes, cómo se representan los eventos internos de lifecycle, cómo se propagan los errores de forma uniforme mediante `Result` y cómo se consulta el estado interno del runtime sin exponer estado mutable.

## Principios

- Determinismo antes que conveniencia.
- Contratos explícitos antes que acoplamiento implícito.
- Inmutabilidad por defecto en objetos de contexto y configuración.
- Sin estado global mutable.
- Sin service locator arbitrario.
- Sin efectos externos dentro del Core.
- Errores controlados mediante tipos del Kernel y `Result`.
- Estado observable mediante snapshots inmutables, no mediante acceso a internals mutables.
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

Estado: definido, pendiente de implementación.

#### Objetivo

Introducir un modelo de lectura inmutable y determinista del estado del runtime para que cualquier capa futura pueda conocer la condición de una ejecución y de sus componentes sin acceder a listas internas del supervisor, sin mutar el runtime y sin depender de infraestructura de observabilidad.

Este entregable establece la frontera entre **control del runtime** e **introspección del runtime**. El supervisor conserva la autoridad sobre `start`/`stop`; los snapshots solo describen el estado ya existente.

#### Alcance

- `RuntimeStatus` como enum explícito del estado agregado del supervisor.
- Estados mínimos obligatorios:
  - `STOPPED`: no existen componentes activos;
  - `RUNNING`: el plan está completamente iniciado;
  - `DEGRADED`: el runtime no está en ejecución normal pero conserva uno o más componentes residuales activos tras un fallo de parada o rollback.
- `RuntimeComponentStatus` como enum mínimo para describir cada componente declarado:
  - `INACTIVE`;
  - `ACTIVE`;
  - `RESIDUAL`.
- `RuntimeComponentSnapshot` inmutable con:
  - `component_name`;
  - estado del componente;
  - dependencias declaradas.
- `RuntimeSnapshot` inmutable con:
  - `RuntimeContext` cuando el runtime posea contexto de ejecución;
  - estado agregado `RuntimeStatus`;
  - componentes en orden declarativo o resuelto, de forma documentada y estable;
  - nombres de componentes activos en orden de arranque efectivo;
  - nombres de componentes residuales;
  - indicador derivado de si el runtime está limpio para un nuevo arranque.
- `RuntimeSupervisor.snapshot(...)` o contrato equivalente de lectura pura que genere un snapshot nuevo en cada consulta.
- Ningún snapshot puede devolver referencias mutables a las estructuras internas del supervisor.
- El snapshot debe reflejar de forma determinista los estados después de:
  - construcción;
  - arranque exitoso;
  - parada exitosa;
  - fallo de arranque con rollback exitoso;
  - fallo de arranque con rollback incompleto;
  - fallo de parada con componentes residuales.
- Pruebas explícitas de inmutabilidad, aislamiento del estado interno y estabilidad del orden.

#### Reglas e invariantes

1. `RuntimeSnapshot` y `RuntimeComponentSnapshot` deben ser objetos inmutables.
2. La introspección no puede ejecutar `start`, `stop`, handlers ni ningún otro efecto.
3. Consultar un snapshot repetidamente sin cambios de runtime debe producir valores equivalentes.
4. `STOPPED` implica cero componentes activos y cero residuales.
5. `RUNNING` implica que el supervisor está en ejecución normal y que no existen residuales.
6. `DEGRADED` implica al menos un componente residual que no pudo detenerse correctamente.
7. Un componente residual debe distinguirse de un componente activo perteneciente a una ejecución normal.
8. Los snapshots no pueden inferir timestamps ni crear IDs.
9. Si se incluye `RuntimeContext`, debe ser el contexto ya suministrado por composición; nunca se genera dentro de la introspección.
10. Ninguna API de introspección puede exponer la lista mutable `_active` ni otra colección interna del supervisor.
11. El orden de componentes en el snapshot debe ser estable y probado.
12. La incorporación de introspección no puede cambiar la semántica de `RuntimePlan.start/stop`, `RuntimeSupervisor`, `ApplicationLifecycle` ni `bootstrap()`.

#### Fuera de alcance específico de RUNTIME-003

- heartbeat;
- latencia;
- health checks de red, broker, base de datos o APIs;
- logging;
- métricas Prometheus/OpenTelemetry;
- tracing;
- persistencia histórica de snapshots;
- alertas;
- dashboard o Widget del CEO;
- comandos remotos;
- lógica de trading.

Estos consumidores podrán construirse después sobre el contrato de introspección sin contaminar el Core.

#### Criterios de aceptación específicos

Además del Quality Gate global de PHASE-02:

- un supervisor recién construido debe producir un snapshot `STOPPED`;
- un arranque exitoso debe producir un snapshot `RUNNING` con todos los componentes activos en orden determinista;
- una parada exitosa debe volver a `STOPPED`;
- un rollback exitoso tras fallo de arranque debe terminar en `STOPPED`;
- un rollback incompleto debe producir `DEGRADED` y enumerar únicamente los residuales reales;
- una parada incompleta debe producir `DEGRADED`;
- modificar una colección obtenida desde el snapshot, cuando el tipo lo permita externamente, nunca puede modificar el supervisor;
- dos snapshots consecutivos sin transición deben comparar por valor de forma equivalente;
- Ruff, Mypy strict y Pytest deben pasar completamente.

## Restricciones arquitectónicas

1. El Runtime no puede importar módulos de dominio de trading.
2. El Runtime no puede crear conexiones externas.
3. El Runtime no puede depender de reloj global ni generar timestamps implícitos no inyectados.
4. El Runtime no puede usar singletons ni registros globales mutables.
5. Los objetos de contexto, planes declarativos y snapshots deben ser inmutables.
6. Todo fallo operacional representable debe retornar `Result` cuando el contrato existente de QORE lo requiera.
7. La composición del Core debe permanecer explícita.
8. Ningún cambio puede romper `bootstrap()` sin argumentos introducido en Genesis.
9. La introspección debe ser una operación de lectura pura.

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

Al cerrar esta fase, QORE debe poseer un runtime base capaz de representar una ejecución, componer componentes, gobernar su ciclo de vida y exponer su estado interno mediante contratos inmutables y deterministas, listo para que fases posteriores incorporen observabilidad, servicios de dominio y superficies de control sin contaminar el Core con infraestructura ni lógica de trading.

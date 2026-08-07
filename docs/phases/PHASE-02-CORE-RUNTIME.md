# PHASE-02 — Core Runtime Contracts

## Objetivo

Convertir la fundación mínima de QORE en un runtime determinista, extensible y explícitamente gobernado por contratos, sin introducir todavía lógica de negocio ni dependencias de infraestructura.

Esta fase debe establecer cómo se identifica una ejecución, cómo se compone el Core, cómo se registran y resuelven componentes, cómo se representan los eventos internos de lifecycle y cómo se propagan los errores de forma uniforme mediante `Result`.

## Principios

- Determinismo antes que conveniencia.
- Contratos explícitos antes que acoplamiento implícito.
- Inmutabilidad por defecto en objetos de contexto y configuración.
- Sin estado global mutable.
- Sin service locator arbitrario.
- Sin efectos externos dentro del Core.
- Errores controlados mediante tipos del Kernel y `Result`.
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

Objetivo: convertir los componentes individuales del runtime en una composición explícita y determinista, sin introducir lógica de dominio.

#### Alcance

- `RuntimeComponentSpec` inmutable con nombre de componente y dependencias explícitas.
- `RuntimePlan` inmutable que representa la composición declarada de una ejecución.
- Validación de nombres duplicados.
- Validación de dependencias inexistentes.
- Rechazo de ciclos de dependencias.
- Resolución determinista del orden de arranque mediante orden topológico estable.
- Orden de parada exactamente inverso al orden de arranque efectivo.
- `RuntimeSupervisor` para ejecutar `start` y `stop` sobre el plan.
- Rollback determinista de componentes ya iniciados si un componente falla al arrancar.
- Preservación del error original de arranque como resultado del fallo.
- Sin paralelismo, threads, asyncio ni efectos externos.
- Pruebas deterministas de orden, ciclos, dependencias, rollback e idempotencia operacional permitida por el contrato.

#### Reglas

1. Un componente solo puede depender de componentes presentes en el mismo `RuntimePlan`.
2. Dos componentes no pueden compartir el mismo `component_name`.
3. Un plan cíclico es inválido y debe fallar antes de ejecutar ningún componente.
4. El orden entre componentes independientes debe ser estable y reproducible según su orden de declaración.
5. Si `start()` falla en un componente, el supervisor debe detener en orden inverso únicamente los componentes que ya habían arrancado con éxito.
6. Un fallo durante rollback no puede sustituir el error original que causó el fallo de arranque.
7. `stop()` debe ejecutarse en orden inverso al último arranque exitoso.
8. El supervisor no puede crear identidades, timestamps ni dependencias implícitas.
9. `QORE-CORE-RUNTIME-002` no modifica la semántica pública de `bootstrap()` introducida por `RUNTIME-001`.

## Restricciones arquitectónicas

1. El Runtime no puede importar módulos de dominio de trading.
2. El Runtime no puede crear conexiones externas.
3. El Runtime no puede depender de reloj global ni generar timestamps implícitos no inyectados.
4. El Runtime no puede usar singletons ni registros globales mutables.
5. Los objetos de contexto y planes declarativos deben ser inmutables.
6. Todo fallo operacional representable debe retornar `Result` cuando el contrato existente de QORE lo requiera.
7. La composición del Core debe permanecer explícita.
8. Ningún cambio puede romper `bootstrap()` sin argumentos introducido en Genesis.

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

Al cerrar esta fase, QORE debe poseer un runtime base capaz de representar una ejecución, componer componentes y gobernar su ciclo de vida de forma determinista, tipada y extensible, listo para que fases posteriores incorporen servicios de dominio sin contaminar el Core con infraestructura ni lógica de trading.

# PHASE-03 — Core Domain & Event Architecture

## Estado

**ACTIVE**

PHASE-03 comienza después del cierre formal de PHASE-02 — Core Runtime Contracts. Esta fase construye el núcleo de dominio y la arquitectura dirigida por eventos sobre el runtime ya estabilizado, sin reabrir responsabilidades fundacionales del Runtime ni introducir infraestructura externa o lógica de trading.

## Objetivo

Establecer los contratos de dominio, comandos, agregados, repositorios, message bus, módulos y composición necesarios para que las fases posteriores incorporen capacidades funcionales de QORE de forma desacoplada, determinista y tipada.

PHASE-03 debe crear una frontera explícita entre:

- Kernel;
- Runtime;
- Domain;
- Application;
- futuras capas de infraestructura.

El resultado debe permitir incorporar posteriormente CIO, CIBO, Portfolio Manager, Risk, Traders Virtuales y demás módulos sin acoplarlos a infraestructura ni romper el Runtime.

## Principios

- Domain-first, infrastructure-last.
- Eventos y comandos explícitos, inmutables y versionados.
- Determinismo antes que conveniencia.
- Sin estado global mutable.
- Sin side effects en contratos de dominio.
- Sin dependencias de broker, base de datos, red o UI.
- `Result` y errores tipados para fallos representables.
- Correlation/causation explícitas; nunca inferidas globalmente.
- Ningún contrato de PHASE-03 puede romper PHASE-01 o PHASE-02.
- La composición debe seguir siendo explícita desde el composition root.

## Fuera de alcance

PHASE-03 no implementa:

- estrategias de trading;
- señales;
- ejecución de órdenes;
- brokers/exchanges;
- market data;
- news APIs;
- CIO;
- CIBO;
- Portfolio Manager;
- Risk Engine;
- Traders Virtuales;
- Validation Lab;
- Statistics, Knowledge u Optimization;
- persistencia real;
- PostgreSQL, Redis o cualquier base de datos;
- Kafka, RabbitMQ u otros brokers de mensajería;
- REST, gRPC o WebSocket;
- logging/auditoría externos;
- Prometheus/OpenTelemetry;
- QORE Mobile;
- Widget del CEO.

## Entregables

### QORE-DOMAIN-001 — Domain Event Contracts

Estado: definido, pendiente de implementación.

#### Objetivo

Crear el contrato oficial de eventos de dominio de QORE sobre el Kernel existente, separando claramente eventos de Runtime y eventos de negocio, y estableciendo metadata de correlación, causalidad, categoría y versión sin generar identidad o tiempo de forma implícita.

#### Alcance

- `DomainEventId` o contrato equivalente basado en identidad explícita.
- `DomainEventVersion` validado y explícito.
- `DomainEventCategory` como clasificación estructurada.
- `CorrelationId` explícito.
- `CausationId` opcional y explícito.
- `DomainEventMetadata` inmutable.
- contrato base de evento de dominio compatible con el Kernel existente sin romper `DomainEvent` publicado en PHASE-01.
- timestamp siempre explícito o suministrado por composición; nunca reloj global.
- reglas de compatibilidad entre runtime events y domain events sin mezclarlos semánticamente.
- igualdad y serialización lógica deterministas a nivel de valores, sin implementar transporte externo.

#### Invariantes

1. Ningún evento crea UUIDs o timestamps implícitamente.
2. `event_name`, categoría y versión no pueden ser vacíos.
3. `correlation_id` es obligatorio para eventos de dominio PHASE-03.
4. `causation_id` puede ser ausente, pero si existe debe ser válido.
5. Metadata es inmutable.
6. Eventos de Runtime continúan representando lifecycle y no deben reclasificarse como eventos de negocio.
7. La incorporación de estos contratos no rompe los eventos ya usados por PHASE-02.

#### Pruebas obligatorias

- construcción válida e inmutable;
- rechazo de nombres/categorías/versiones inválidos;
- correlation/causation explícitas;
- timestamp explícito;
- compatibilidad con Kernel `DomainEvent`;
- compatibilidad con Runtime Events existentes;
- determinismo por valor;
- Ruff, Mypy strict y Pytest completamente verdes.

### QORE-DOMAIN-002 — Command Contracts

Estado: definido, pendiente de implementación.

Introducirá contratos inmutables de `Command`, identidad/correlation/causation de comando, `CommandHandler`, `CommandResult`, validación, errores uniformes e idempotency key explícita cuando corresponda. No ejecutará infraestructura ni colas externas.

### QORE-DOMAIN-003 — Aggregate Contracts

Estado: definido, pendiente de implementación.

Introducirá `AggregateRoot`, `Entity`, `ValueObject`, versionado del agregado, invariantes de dominio, acumulación controlada de eventos y contratos de Domain Service sin persistencia ni lógica específica de trading.

### QORE-DOMAIN-004 — Repository Contracts

Estado: definido, pendiente de implementación.

Definirá únicamente puertos/contratos de `Repository`, `UnitOfWork`, `SnapshotStore` y `EventStore` o equivalentes, sin implementar base de datos, filesystem, cache o red.

### QORE-DOMAIN-005 — Message Bus

Estado: definido, pendiente de implementación.

Construirá un message bus interno y determinista sobre contratos del Core:

- Event Dispatcher;
- Command Dispatcher;
- Handler Registry;
- orden estable de handlers;
- middleware pipeline explícito;
- políticas de retry únicamente como contratos/decisiones puras, sin timers o infraestructura externa;
- propagación uniforme de errores.

### QORE-DOMAIN-006 — Module Architecture

Estado: definido, pendiente de implementación.

Definirá la estructura oficial de módulos funcionales para fases posteriores, con fronteras mínimas:

- `api`;
- `application`;
- `domain`;
- `contracts`;
- `services`;
- `events`;
- `commands`.

No implementará todavía CIO, CIBO, Portfolio, Risk ni trading.

### QORE-DOMAIN-007 — Domain Composition Root

Estado: definido, pendiente de implementación.

Definirá cómo los módulos de dominio se registran en la composición oficial del Core sin modificar las responsabilidades internas del Runtime. Deberá preservar una sola ruta oficial de composición y lifecycle introducida por PHASE-02.

## Restricciones arquitectónicas

1. Domain no puede importar adapters de infraestructura.
2. Domain no puede abrir conexiones externas.
3. Domain no puede depender de reloj global, UUID global ni singletons.
4. Runtime no puede depender de módulos funcionales concretos de dominio.
5. Kernel permanece por debajo de Runtime y Domain.
6. Los contratos nuevos son inmutables por defecto.
7. Eventos y comandos deben transportar identidad/contexto explícitos.
8. Repositorios y event stores son puertos; sus implementaciones quedan fuera de esta fase.
9. Message Bus de PHASE-03 es interno/in-process y determinista; no es un broker distribuido.
10. Ningún entregable puede introducir lógica de trading.
11. `bootstrap()` Genesis y el composition root de PHASE-02 deben permanecer compatibles.
12. Toda extensión del composition root debe ser aditiva y cubierta por pruebas end-to-end.

## Criterios de aceptación globales

Todos los PR de PHASE-03 deben terminar con código de salida 0 para:

```bash
python --version
pip install -e ".[dev]"
python -c "import qore; print(qore.__name__)"
pytest
ruff check .
mypy src tests
```

Además:

- Mypy debe continuar en `strict = true`.
- Las pruebas deben ser deterministas.
- No se permiten dependencias nuevas de infraestructura sin una fase explícita que las autorice.
- Todo contrato público nuevo debe tener pruebas de invariantes y compatibilidad.
- Debe preservarse el Quality Gate de PHASE-02 para cambios que toquen composition root o runtime boundaries.

## Quality Gate

Cada PR de PHASE-03 solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera de alcance;
- el head revisado sea exactamente el head mergeado;
- una revisión semántica confirme que no se filtra infraestructura hacia Domain;
- cualquier cambio en composition root preserve la ruta oficial de ejecución de PHASE-02.

## Condición de cierre

PHASE-03 se marcará `COMPLETED` únicamente cuando DOMAIN-001 a DOMAIN-007 estén integrados y una revisión transversal confirme que QORE posee contratos de dominio, comandos, agregados, repositorios, message bus y composición modular suficientes para comenzar módulos funcionales sin introducir infraestructura ni lógica de trading en el Core base.

## Resultado esperado

Al cerrar PHASE-03, QORE debe poseer una arquitectura de dominio y eventos completamente tipada, inmutable y determinista, preparada para alojar módulos funcionales futuros sobre el Runtime estable de PHASE-02, sin acoplamiento a infraestructura externa ni a superficies de presentación.

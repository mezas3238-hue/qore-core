# PHASE-03 — Core Domain & Event Architecture

## Estado

**COMPLETED**

PHASE-03 comenzó después del cierre formal de PHASE-02 — Core Runtime Contracts y queda cerrada tras integrar DOMAIN-001 a DOMAIN-007, completar el hardening transversal de composición y verificar el Quality Gate final. La fase establece el núcleo de dominio y la arquitectura dirigida por eventos sobre el Runtime estabilizado, sin reabrir responsabilidades fundacionales del Runtime ni introducir infraestructura externa o lógica de trading.

## Objetivo

Establecer los contratos de dominio, comandos, agregados, repositorios, message bus, módulos y composición necesarios para que las fases posteriores incorporen capacidades funcionales de QORE de forma desacoplada, determinista y tipada.

PHASE-03 crea una frontera explícita entre:

- Kernel;
- Runtime;
- Domain;
- Application;
- futuras capas de infraestructura.

El resultado permite incorporar posteriormente módulos funcionales sin acoplarlos a infraestructura ni romper el Runtime.

## Principios

- Domain-first, infrastructure-last.
- Eventos y comandos explícitos, inmutables y versionados.
- Determinismo antes que conveniencia.
- Sin estado global mutable.
- Sin side effects en contratos de dominio.
- Sin dependencias de broker, base de datos, red o UI.
- `Result` y errores tipados para fallos representables.
- Correlation/causation explícitas; nunca inferidas globalmente.
- Ningún contrato de PHASE-03 rompe PHASE-01 o PHASE-02.
- La composición sigue siendo explícita desde el composition root oficial.

## Fuera de alcance

PHASE-03 no implementa:

- estrategias de trading;
- señales;
- ejecución de órdenes;
- brokers/exchanges;
- market data;
- news APIs;
- módulos funcionales concretos;
- persistencia real;
- PostgreSQL, Redis o cualquier base de datos;
- Kafka, RabbitMQ u otros brokers de mensajería;
- REST, gRPC o WebSocket;
- logging/auditoría externos;
- Prometheus/OpenTelemetry;
- superficies móviles o de presentación.

## Entregables

### QORE-DOMAIN-001 — Domain Event Contracts

Estado: **COMPLETED — integrado en `main` mediante PR #9.**

Implementa identidad, versión y categoría explícitas de eventos de negocio, correlation/causation, metadata inmutable y determinista, timestamp explícito y compatibilidad con el `DomainEvent` del Kernel sin reclasificar eventos de Runtime como eventos de negocio.

### QORE-DOMAIN-002 — Command Contracts

Estado: **COMPLETED — integrado en `main` mediante PR #10.**

Implementa `CommandId`, `CommandName`, timestamp explícito, metadata inmutable, correlation/causation, idempotency key opcional, `CommandResult` sobre el `Result` oficial del Kernel, `CommandHandler` tipado y errores uniformes de validación.

### QORE-DOMAIN-003 — Aggregate Contracts

Estado: **COMPLETED — integrado en `main` mediante PR #11.**

Implementa `EntityId`, identidad estable de entidades, `AggregateVersion`, `AggregateRoot`, acumulación y drenaje controlado de eventos, invariantes explícitas y contratos estructurales de Value Object y Domain Service. La identidad hashable de entidad queda inmutable tras construcción.

### QORE-DOMAIN-004 — Repository Contracts

Estado: **COMPLETED — integrado en `main` mediante PR #12.**

Define exclusivamente puertos tipados de `Repository`, `UnitOfWork`, `SnapshotStore` y `EventStore`, incluyendo snapshots inmutables y control explícito de versión, sin implementar persistencia, filesystem, cache o red.

### QORE-DOMAIN-005 — Message Bus

Estado: **COMPLETED — integrado en `main` mediante PR #13.**

Implementa `HandlerRegistry` y `MessageBus` internos, síncronos y deterministas, un command handler por tipo concreto, múltiples event handlers en orden estable, pipeline de middleware con entrada/salida correctamente finalizada, normalización de errores y contratos puros de retry sin temporización ni infraestructura externa.

### QORE-DOMAIN-006 — Module Architecture

Estado: **COMPLETED — integrado en `main` mediante PR #14.**

Formaliza `ModuleName`, `ModuleVersion`, `ModuleDescriptor`, `DomainModule` y las fronteras canónicas obligatorias:

- `api`;
- `application`;
- `domain`;
- `contracts`;
- `services`;
- `events`;
- `commands`.

Los descriptors son inmutables y las capas requeridas tienen orden canónico validado.

### QORE-DOMAIN-007 — Domain Composition Root

Estado: **COMPLETED — integrado en `main` mediante PR #15.**

Implementa `ModuleCatalog`, `DomainComposition` y `compose_domain()`, integra la composición de dominio de forma aditiva en `CoreApplication` y `bootstrap()`, conserva la compatibilidad Genesis y mantiene los módulos de dominio fuera del `RuntimePlan` y del lifecycle del Runtime. La identidad/descriptors del catálogo se capturan al componer para impedir mutación retroactiva de la topología.

### Hardening transversal de PHASE-03

Estado: **COMPLETED — integrado en `main` mediante PR #16.**

La revisión DOMAIN-001…007 detectó que un módulo podía pertenecer al catálogo sin una ruta oficial para aportar handlers durante la composición. Se añadió `ComposableDomainModule`, cuyo `register_handlers()` contribuye al único `HandlerRegistry` dentro del composition root oficial. Los fallos representables o excepciones durante ese registro abortan la composición mediante `ModuleRegistrationError`; no se expone un bus parcialmente compuesto ni se crea una segunda etapa mutable después de `bootstrap()`.

## Restricciones arquitectónicas verificadas

1. Domain no importa adapters de infraestructura.
2. Domain no abre conexiones externas.
3. Domain no depende de reloj global, UUID global ni singletons.
4. Runtime no depende de módulos funcionales concretos de dominio.
5. Kernel permanece por debajo de Runtime y Domain.
6. Los contratos nuevos son inmutables por defecto.
7. Eventos y comandos transportan identidad/contexto explícitos.
8. Repositorios y event stores son puertos; no existen implementaciones de persistencia en esta fase.
9. Message Bus es interno/in-process y determinista; no es un broker distribuido.
10. No se introdujo lógica de trading.
11. `bootstrap()` Genesis y la ruta oficial de composición/lifecycle de PHASE-02 permanecen compatibles.
12. La extensión del composition root es aditiva y está cubierta por pruebas end-to-end.
13. Los módulos componibles registran handlers dentro del único composition root oficial, antes de exponer `DomainComposition`.

## Criterios de aceptación globales

Los entregables y el hardening transversal fueron sometidos al Quality Gate del repositorio:

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
- No se añadieron dependencias de infraestructura.
- Los contratos públicos nuevos tienen pruebas de invariantes y compatibilidad.
- Los cambios que tocaron composition root preservaron las fronteras de PHASE-02.

## Evidencia de integración y Quality Gate

- DOMAIN-001 — PR #9 — integrado.
- DOMAIN-002 — PR #10 — integrado.
- DOMAIN-003 — PR #11 — integrado.
- DOMAIN-004 — PR #12 — integrado.
- DOMAIN-005 — PR #13 — integrado.
- DOMAIN-006 — PR #14 — integrado.
- DOMAIN-007 — PR #15 — integrado.
- Hardening transversal — PR #16 — integrado.
- DOMAIN-007 final: Run #104 — Ruff PASS, Mypy strict PASS, Pytest PASS.
- Hardening transversal final: Run #107 — Ruff PASS, Mypy strict PASS, Pytest PASS.
- PRs de cierre técnico sin hilos de revisión pendientes en el head mergeado.

## Revisión transversal DOMAIN-001…007

La revisión conjunta confirma una cadena arquitectónica coherente:

1. Los eventos de negocio tienen identidad, tiempo, versión, correlación y causalidad explícitos.
2. Los comandos comparten el mismo contexto causal y retornan `Result` tipado.
3. Los agregados poseen identidad estable, versionado monotónico e historial pendiente de eventos controlado.
4. La persistencia queda detrás de puertos explícitos y no contamina Domain.
5. El Message Bus conecta comandos/eventos con handlers en orden determinista y con errores uniformes.
6. La arquitectura modular define una frontera estándar para módulos funcionales posteriores.
7. El Domain Composition Root cataloga módulos, registra sus handlers y construye un único bus dentro de `bootstrap()`, sin introducir módulos de dominio en el Runtime lifecycle.

No se detectan huecos arquitectónicos bloqueantes para comenzar fases de módulos funcionales sobre esta base. Cualquier persistencia, mensajería distribuida, integración externa o lógica de trading deberá entrar en fases posteriores y respetar estos puertos y fronteras.

## Quality Gate

PHASE-03 se considera cerrada únicamente porque sus PRs técnicos cumplieron:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- sin hilos de revisión sin resolver en los heads finales;
- sin cambios fuera de alcance;
- head revisado igual al head mergeado;
- revisión semántica sin filtración de infraestructura hacia Domain;
- composición oficial única compatible con PHASE-02.

## Condición de cierre

**SATISFECHA.** DOMAIN-001 a DOMAIN-007 están integrados, el hardening transversal está integrado y la revisión conjunta confirma contratos suficientes de eventos, comandos, agregados, repositorios, message bus y composición modular para comenzar módulos funcionales sin introducir infraestructura ni lógica de trading en el Core base.

## Resultado final

PHASE-03 deja a QORE con una arquitectura de dominio y eventos tipada, inmutable y determinista, preparada para alojar módulos funcionales futuros sobre el Runtime estable de PHASE-02, con una sola ruta oficial de composición y sin acoplamiento a infraestructura externa o superficies de presentación.

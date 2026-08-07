# PHASE-04 — Core Governance & Functional Modules

## Estado

**ACTIVE**

PHASE-04 comienza sobre el `main` que cierra formalmente PHASE-03 — Core Domain & Event Architecture. Esta fase introduce los primeros módulos funcionales reales de QORE sobre los contratos de dominio, message bus, arquitectura modular y composition root ya estabilizados.

## Objetivo

Construir la primera capa funcional de gobierno y coordinación del ecosistema QORE sin introducir todavía infraestructura externa, conectividad de broker, market data, persistencia real ni ejecución de trading.

PHASE-04 debe demostrar que la arquitectura de PHASE-03 puede alojar módulos funcionales reales manteniendo:

- composición única mediante `bootstrap()`;
- registro de handlers dentro del composition root oficial;
- aislamiento del Runtime;
- contratos inmutables y deterministas;
- decisiones y resultados explícitos;
- ausencia de estado global mutable;
- ausencia de side effects externos.

## Principios

- Los módulos funcionales se construyen sobre `ComposableDomainModule`.
- Ningún módulo funcional entra en `RuntimePlan` por existir como módulo de dominio.
- Toda interacción entre módulos usa Commands, BusinessDomainEvents o contratos de dominio explícitos.
- Ningún módulo crea UUIDs o timestamps implícitamente.
- Las decisiones deben ser trazables por identidad, correlation y causation.
- Risk puede bloquear o degradar una decisión, pero no ejecuta órdenes ni conecta brokers en esta fase.
- Portfolio Manager representa intención/estado de asignación, no posiciones reales de broker.
- CIO y CIBO se introducen como módulos de gobierno/coordination, sin infraestructura ni IA externa.
- PHASE-04 no reabre responsabilidades de Kernel, Runtime o Domain Foundation salvo regresión demostrada.

## Fuera de alcance

PHASE-04 no implementa:

- estrategias concretas de trading;
- señales de entrada/salida de mercado;
- ejecución de órdenes;
- brokers/exchanges;
- MT5;
- TradingView;
- market data en vivo;
- news APIs;
- persistencia real;
- PostgreSQL, Redis o filesystem de producción;
- Kafka, RabbitMQ u otros brokers distribuidos;
- REST, gRPC o WebSocket;
- QORE Mobile;
- Widget del CEO;
- modelos externos/LLM;
- Validation Lab completo;
- Statistics, Knowledge u Optimization completos;
- Traders Virtuales especializados.

## Entregables

### QORE-MODULE-001 — Functional Decision Contracts

Estado: definido, pendiente de implementación.

#### Objetivo

Crear los contratos funcionales comunes que usarán CIO, CIBO, Portfolio Manager y Risk para producir, revisar y encadenar decisiones sin acoplarse entre sí ni a infraestructura.

#### Alcance

- `DecisionId` explícito.
- `DecisionType` o clasificación equivalente validada.
- `DecisionStatus` explícito y cerrado.
- `DecisionPriority` explícita.
- `DecisionMetadata` inmutable con correlation/causation.
- `DecisionReason` estructurado.
- `FunctionalDecision` inmutable.
- `DecisionOutcome` o equivalente para aprobación, rechazo, bloqueo o degradación.
- representación lógica determinista.
- cero UUID/timestamp implícitos.

#### Invariantes

1. Toda decisión tiene identidad explícita.
2. Toda decisión tiene correlation explícita.
3. Causation puede ser ausente, pero nunca inferida globalmente.
4. Metadata y reasons son profundamente inmutables.
5. Un outcome no puede representar estados contradictorios.
6. La evaluación de una decisión no ejecuta side effects externos.
7. Los contratos son independientes de CIO/CIBO/Portfolio/Risk concretos.

### QORE-CIO-001 — CIO Module Foundation

Estado: definido, pendiente de implementación.

Creará el módulo CIO mínimo como `ComposableDomainModule`, con descriptor, comandos/eventos propios y handlers deterministas. Su responsabilidad será producir/coordinar decisiones de alto nivel sobre información ya suministrada como contratos explícitos, sin acceder a fuentes externas.

### QORE-CIBO-001 — CIBO Module Foundation

Estado: definido, pendiente de implementación.

Creará el módulo CIBO mínimo como `ComposableDomainModule`, con fronteras y handlers propios. No ejecutará infraestructura ni trading; operará únicamente sobre mensajes y decisiones internas explícitas.

### QORE-PORTFOLIO-001 — Portfolio Manager Foundation

Estado: definido, pendiente de implementación.

Definirá intención de asignación y estado lógico de portfolio mediante Value Objects, Commands, Events y handlers internos. No representará saldos reales de broker ni posiciones externas.

### QORE-RISK-001 — Risk Governance Foundation

Estado: definido, pendiente de implementación.

Definirá reglas y resultados de gobierno de riesgo sobre decisiones internas: aprobación, bloqueo o degradación explícita. No calculará todavía riesgo desde feeds reales ni ejecutará órdenes.

### QORE-GOVERNANCE-001 — Cross-Module Decision Flow

Estado: definido, pendiente de implementación.

Conectará CIO, CIBO, Portfolio Manager y Risk mediante MessageBus y contratos de PHASE-04, manteniendo orden determinista y trazabilidad correlation/causation. No habrá llamadas directas entre módulos que eviten el bus oficial cuando la interacción sea un mensaje de dominio.

### QORE-GOVERNANCE-002 — Functional Modules Composition & End-to-End Flow

Estado: definido, pendiente de implementación.

Integrará los módulos funcionales aprobados en `bootstrap()` mediante la composición oficial de PHASE-03 y añadirá pruebas end-to-end de composición, dispatch, decisión, revisión de riesgo y resultado final, preservando Runtime y Genesis.

## Restricciones arquitectónicas

1. Cada módulo funcional debe satisfacer `ComposableDomainModule`.
2. Cada módulo registra handlers únicamente durante la composición oficial.
3. Ningún módulo puede mutar `RuntimePlan` como efecto de su composición.
4. Ningún módulo puede importar adapters de infraestructura.
5. Ningún módulo puede abrir conexiones externas.
6. Ningún módulo puede usar reloj global ni generación global de UUIDs.
7. Los handlers deben devolver `Result`/errores tipados cuando el fallo sea representable.
8. Las decisiones compartidas deben vivir en contratos comunes, no duplicarse por módulo.
9. Risk no puede ejecutar la decisión que evalúa.
10. Portfolio Manager no puede representar una posición externa como verdad sin un adapter futuro explícito.
11. CIO/CIBO no pueden depender de modelos externos en esta fase.
12. `bootstrap()` Genesis, PHASE-02 Runtime y PHASE-03 Domain Composition deben permanecer compatibles.

## Criterios de aceptación globales

Todos los PR de PHASE-04 deben terminar con código de salida 0 para:

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
- No se permiten dependencias nuevas de infraestructura.
- Todo contrato público nuevo debe tener pruebas de invariantes e inmutabilidad.
- Todo módulo funcional debe tener pruebas de descriptor, composición y registro de handlers.
- Todo flujo transversal debe probar correlation/causation y orden estable.
- Los cambios que toquen `bootstrap()` deben volver a ejecutar pruebas de Genesis, Runtime y Domain Composition.

## Quality Gate

Cada PR de PHASE-04 solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera de alcance;
- el head revisado sea exactamente el head mergeado;
- una revisión semántica confirme ausencia de infraestructura/trading accidental;
- una revisión de fronteras confirme que Runtime no depende de módulos funcionales concretos;
- cualquier cambio al composition root preserve una única ruta oficial de composición.

## Condición de cierre

PHASE-04 se marcará `COMPLETED` únicamente cuando QORE-MODULE-001, CIO-001, CIBO-001, PORTFOLIO-001, RISK-001, GOVERNANCE-001 y GOVERNANCE-002 estén integrados y una revisión transversal confirme que los primeros módulos funcionales pueden componerse, intercambiar decisiones y aplicar gobierno de riesgo de forma determinista sin infraestructura externa ni ejecución de trading.

## Resultado esperado

Al cerrar PHASE-04, QORE debe poseer una primera capa funcional de gobierno compuesta por módulos reales, sobre el Runtime y Domain Core ya estabilizados, preparada para que fases posteriores incorporen Traders Virtuales especializados, Validation Lab, Statistics, Knowledge, Optimization e infraestructura externa sin romper las fronteras del Core.

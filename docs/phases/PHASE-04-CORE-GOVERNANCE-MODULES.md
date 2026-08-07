# PHASE-04 — Core Governance & Functional Modules

## Estado

**COMPLETED**

PHASE-04 comenzó sobre el `main` que cerró formalmente PHASE-03 — Core Domain & Event Architecture. La fase introdujo los primeros módulos funcionales reales de QORE sobre los contratos de dominio, message bus, arquitectura modular y composition root ya estabilizados.

## Objetivo

Construir la primera capa funcional de gobierno y coordinación del ecosistema QORE sin introducir todavía infraestructura externa, conectividad de broker, market data, persistencia real ni ejecución de trading.

PHASE-04 demuestra que la arquitectura de PHASE-03 puede alojar módulos funcionales reales manteniendo:

- composición única mediante el `bootstrap()` oficial y un composition root funcional por encima del Core;
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
- Las decisiones son trazables por identidad, correlation y causation.
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

Estado: **COMPLETED — integrado en `main` mediante PR #18**.

#### Objetivo

Crear los contratos funcionales comunes que usan CIO, CIBO, Portfolio Manager y Risk para producir, revisar y encadenar decisiones sin acoplarse entre sí ni a infraestructura.

#### Alcance integrado

- `DecisionId` explícito.
- `DecisionType` validado.
- `DecisionStatus` explícito y cerrado.
- `DecisionPriority` explícita.
- `DecisionMetadata` inmutable con correlation/causation.
- `DecisionReason` estructurado.
- `FunctionalDecision` inmutable.
- `DecisionOutcome` para aprobación, rechazo, bloqueo o degradación.
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

Estado: **COMPLETED — integrado en `main` mediante PR #19**.

CIO quedó implementado como `ComposableDomainModule`, con descriptor, command, handler y evento propios. Produce decisiones de alto nivel exclusivamente desde información suministrada como contratos explícitos, sin fuentes externas ni IA. La auditoría transversal reforzó además que `CioDecisionProducedEvent` preserve tanto correlation como causation de la decisión representada.

### QORE-CIBO-001 — CIBO Module Foundation

Estado: **COMPLETED — integrado en `main` mediante PR #20**.

CIBO quedó implementado como `ComposableDomainModule`, revisa decisiones funcionales resueltas y deriva su nueva decisión manteniendo correlation y causation explícitas. La auditoría transversal reforzó que el command de CIBO rechace una causation que no apunte a la decisión fuente.

### QORE-PORTFOLIO-001 — Portfolio Manager Foundation

Estado: **COMPLETED — integrado en `main` mediante PR #21**.

Portfolio Manager representa únicamente intención lógica de asignación mediante `AllocationIntent` y targets expresados en basis points. No representa saldos ni posiciones de broker. La auditoría transversal reforzó la unicidad causal entre la decisión fuente y `AllocationIntentId`.

### QORE-RISK-001 — Risk Governance Foundation

Estado: **COMPLETED — integrado en `main` mediante PR #22**.

Risk Governance evalúa `AllocationIntent` mediante una política determinista de concentración y produce resultados `APPROVED`, `DEGRADED` o `BLOCKED`. No consume feeds externos y no ejecuta órdenes.

### QORE-GOVERNANCE-001 — Cross-Module Decision Flow

Estado: **COMPLETED — integrado en `main` mediante PR #23**.

El flujo CIO → CIBO → Portfolio → Risk usa exclusivamente el `MessageBus` oficial. Mantiene orden determinista, correlation común y causation encadenada. Los errores representables se propagan mediante `Failure` y ninguna etapa posterior se ejecuta después de un fallo. La auditoría transversal reforzó que el orquestador valide los resultados reales devueltos por cada handler —identidad, correlation, causation, estado y outcome— antes de permitir avanzar al siguiente gate.

### QORE-GOVERNANCE-002 — Functional Modules Composition & End-to-End Flow

Estado: **COMPLETED — integrado en `main` mediante PR #24**.

`compose_functional_governance()` constituye el composition root funcional oficial por encima de `CoreApplication`: crea CIO+CIBO+Portfolio+Risk, los entrega al `bootstrap()` oficial y expone `CrossModuleDecisionFlow` sobre el `MessageBus` compuesto. El Core no depende de módulos funcionales concretos. La composición preserva también la vía determinista `RuntimeContext + Clock`, Genesis y el aislamiento del `RuntimePlan`.

## Hardening transversal de cierre

La revisión completa de MODULE-001 + CIO-001 + CIBO-001 + PORTFOLIO-001 + RISK-001 + GOVERNANCE-001 + GOVERNANCE-002 detectó y corrigió cuatro huecos antes de cerrar la fase. Las correcciones se integraron mediante **PR #25**:

1. CIBO exige `command.metadata.causation_id == source_decision.decision_id`.
2. Portfolio impide que `AllocationIntentId` reutilice el UUID de la decisión que lo causa.
3. `CioDecisionProducedEvent` exige que su causation coincida con la causation de la decisión representada.
4. `CrossModuleDecisionFlow` valida los resultados reales de CIO, CIBO, Portfolio y Risk antes de avanzar, sin confiar únicamente en el plan solicitado ni en la implementación concreta de un handler registrado.

La regresión inicial del hardening reveló que las pruebas antiguas de CIBO construían commands causalmente incompletos. Esas pruebas se alinearon con el contrato reforzado y el repositorio completo volvió a pasar el Quality Gate.

## Evidencia de integración

- MODULE-001 — PR #18 — merge `21d06e4b251d30465d4104cdda5137bc53ee41f2`.
- CIO-001 — PR #19 — merge `0ae0eadace8719f923976a7a38f38d645f963b3e`.
- CIBO-001 — PR #20 — merge `aa1cd4648899ad99baf2da9050140aba9cee7671`.
- PORTFOLIO-001 — PR #21 — merge `f0f502d6fdc6f39cbd681db8571f9477991599b0`.
- RISK-001 — PR #22 — merge `66dbf1c5011f79a9ab221d451cba755fcafe75de`.
- GOVERNANCE-001 — PR #23 — merge `849cc5c864d379976a8c295e66fd15f66e7676de`.
- GOVERNANCE-002 — PR #24 — merge `6ef473d7bd23951241269d2cbcdeb32af9171735`.
- Hardening transversal — PR #25 — merge `e56281eca4c7a2dbf44872c947ddd03d74e2447a`.

## Restricciones arquitectónicas verificadas

1. Cada módulo funcional satisface `ComposableDomainModule`.
2. Cada módulo registra handlers únicamente durante la composición oficial.
3. Ningún módulo muta `RuntimePlan` como efecto de su composición o ejecución funcional.
4. Ningún módulo importa adapters de infraestructura.
5. Ningún módulo abre conexiones externas.
6. Ningún módulo usa reloj global ni generación global de UUIDs.
7. Los handlers devuelven `Result`/errores tipados cuando el fallo es representable.
8. Las decisiones compartidas viven en contratos comunes, no duplicadas por módulo.
9. Risk no ejecuta la decisión que evalúa.
10. Portfolio Manager no representa posiciones externas como verdad.
11. CIO/CIBO no dependen de modelos externos.
12. `bootstrap()` Genesis, PHASE-02 Runtime y PHASE-03 Domain Composition permanecen compatibles.

## Criterios de aceptación globales

Todos los cambios de PHASE-04 fueron sometidos a:

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
- Los contratos públicos nuevos tienen pruebas de invariantes/inmutabilidad según su responsabilidad.
- Los módulos funcionales tienen pruebas de descriptor, composición y registro de handlers.
- Los flujos transversales prueban correlation/causation y orden estable.
- Los cambios de composición preservan Genesis, Runtime y Domain Composition.

## Quality Gate final

La auditoría transversal terminó con **QORE CI Run #149** en verde sobre el head revisado del PR #25:

- Ruff = PASS.
- Mypy strict = PASS.
- Pytest = PASS.
- Sin hilos de revisión pendientes.
- Sin reviews pendientes.
- Sin infraestructura/trading accidental.
- Runtime no depende de módulos funcionales concretos.
- La ruta oficial de composición permanece única: `compose_functional_governance()` delega en `bootstrap()` y no crea un segundo Core.

## Condición de cierre

La condición de cierre se considera satisfecha: QORE-MODULE-001, CIO-001, CIBO-001, PORTFOLIO-001, RISK-001, GOVERNANCE-001 y GOVERNANCE-002 están integrados, la revisión transversal fue ejecutada y los huecos encontrados fueron corregidos y validados.

## Resultado alcanzado

QORE posee una primera capa funcional de gobierno compuesta por módulos reales sobre el Runtime y Domain Core estabilizados. CIO produce decisiones explícitas; CIBO las revisa; Portfolio las proyecta a intención lógica de asignación; Risk aplica gobierno determinista; y Governance coordina/comparte la cadena mediante MessageBus con trazabilidad de identidad, correlation y causation.

PHASE-04 queda preparada para que fases posteriores incorporen Traders Virtuales especializados, Validation Lab, Statistics, Knowledge, Optimization e infraestructura externa sin romper las fronteras del Core.

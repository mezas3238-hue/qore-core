# PHASE-05 — Specialized Intelligence & Validation Services

## Estado

**ACTIVE**

PHASE-05 comienza sobre el `main` que cierra formalmente PHASE-04 — Core Governance & Functional Modules.

## Objetivo

Introducir la primera capa de servicios especializados de QORE sobre el gobierno funcional ya estabilizado, manteniendo contratos deterministas, composición explícita y aislamiento respecto de infraestructura externa.

PHASE-05 debe demostrar que servicios especializados pueden analizar, validar, medir, aprender y proponer mejoras sobre decisiones y flujos internos sin abrir conexiones externas, ejecutar órdenes ni asumir persistencia real.

## Principios

- Los servicios especializados se construyen sobre contratos comunes y módulos componibles.
- Ningún servicio especializado entra en `RuntimePlan` por existir como módulo de dominio.
- Toda identidad, timestamp, correlation y causation se suministra explícitamente.
- Ningún servicio genera side effects externos.
- Ningún servicio ejecuta órdenes ni modifica brokers/exchanges.
- Los resultados especializados son inmutables, trazables y deterministas.
- Validation, Statistics, Knowledge y Optimization no pueden convertirse en fuentes ocultas de verdad global mutable.
- Los Traders Virtuales producen análisis/intenciones especializadas, no órdenes ejecutables.
- PHASE-05 no reabre Kernel, Runtime, Domain Foundation ni PHASE-04 Governance salvo regresión demostrada.

## Fuera de alcance

PHASE-05 no implementa:

- broker/exchange connectivity;
- MT5;
- TradingView;
- market data en vivo;
- news APIs;
- ejecución de órdenes;
- posiciones reales de broker;
- persistencia real;
- PostgreSQL, Redis o filesystem de producción;
- Kafka, RabbitMQ u otros brokers externos;
- REST, gRPC o WebSocket;
- modelos externos/LLM;
- aprendizaje autónomo sobre datos externos;
- optimización que cambie configuración productiva por sí sola;
- UI, QORE Mobile o Widget del CEO.

## Entregables

### QORE-SPECIALIST-001 — Specialist Analysis Contracts

Estado: definido, pendiente de implementación.

Crear contratos comunes para resultados especializados antes de introducir módulos concretos.

Alcance mínimo:

- `SpecialistAnalysisId` explícito;
- `SpecialistKind` validado;
- `SpecialistAnalysisStatus` cerrado;
- `SpecialistConfidence` determinista y sin floats no finitos;
- `SpecialistReason` estructurado;
- metadata inmutable con correlation/causation;
- `SpecialistAnalysis` inmutable;
- representación lógica estable;
- cero UUID/timestamp implícitos.

### QORE-TRADER-001 — Virtual Trader Foundation

Estado: definido, pendiente de implementación.

Introducir el contrato/módulo base de Trader Virtual especializado. Producirá análisis o propuestas internas a partir de inputs explícitos; no producirá órdenes ejecutables ni accederá a market data externo.

### QORE-VALIDATION-001 — Validation Lab Foundation

Estado: definido, pendiente de implementación.

Introducir validación determinista de decisiones/análisis internos mediante reglas explícitas, resultados trazables y `Result` tipado. No habrá backtesting externo ni datasets reales en esta fase.

### QORE-STATISTICS-001 — Statistics Service Foundation

Estado: definido, pendiente de implementación.

Introducir contratos y proyecciones estadísticas puras sobre snapshots suministrados explícitamente. No habrá base de datos ni ingestión externa.

### QORE-KNOWLEDGE-001 — Knowledge Service Foundation

Estado: definido, pendiente de implementación.

Introducir conocimiento interno como snapshots/entries inmutables y explícitos. No habrá vector DB, embeddings externos, scraping ni memoria global mutable.

### QORE-OPTIMIZATION-001 — Optimization Service Foundation

Estado: definido, pendiente de implementación.

Introducir propuestas de optimización deterministas sobre inputs internos explícitos. Optimization puede recomendar cambios, pero no aplicarlos automáticamente.

### QORE-SPECIALIZED-GOVERNANCE-001 — Specialized Services Decision Flow

Estado: definido, pendiente de implementación.

Conectar Trader Virtual → Validation → Statistics/Knowledge → Optimization mediante MessageBus/contratos explícitos, preservando correlation/causation y sin llamadas laterales ocultas.

### QORE-SPECIALIZED-GOVERNANCE-002 — Specialized Services Composition & End-to-End Flow

Estado: definido, pendiente de implementación.

Crear un composition root especializado por encima del Core/Functional Governance ya existentes, integrar los servicios aprobados mediante la composición oficial y demostrar un flujo end-to-end determinista sin alterar Runtime ni introducir infraestructura.

## Restricciones arquitectónicas

1. Todo módulo especializado debe ser componible mediante los contratos de PHASE-03.
2. Los módulos especializados se registran solo durante la composición oficial.
3. Ningún módulo especializado puede mutar `RuntimePlan`.
4. Ningún módulo especializado puede importar adapters de infraestructura.
5. Ningún módulo especializado puede usar reloj global ni generación global de UUIDs.
6. Los resultados compartidos viven en contratos comunes, no duplicados por servicio.
7. Validation no ejecuta la decisión que valida.
8. Statistics no persiste ni ingiere fuentes externas.
9. Knowledge no usa almacenamiento externo ni modelos externos.
10. Optimization no aplica automáticamente sus recomendaciones.
11. Virtual Trader no emite una orden ejecutable ni conecta broker.
12. PHASE-04 Functional Governance debe permanecer compatible y aislada.

## Criterios de aceptación globales

Todos los PR de PHASE-05 deben terminar con código de salida 0 para:

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
- Todo contrato público nuevo tiene pruebas de invariantes e inmutabilidad.
- Toda frontera especializada prueba correlation/causation.
- Todo módulo tiene pruebas de descriptor, composición y registro de handlers.
- Todo flujo transversal prueba orden estable y propagación de `Failure`.
- Los cambios de composición deben volver a probar Runtime y Functional Governance.

## Quality Gate

Cada PR solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera de alcance;
- el head revisado sea exactamente el head mergeado;
- la revisión semántica confirme ausencia de infraestructura, ejecución y estado global mutable;
- Runtime y PHASE-04 Governance permanezcan desacoplados de módulos especializados concretos.

## Condición de cierre

PHASE-05 se marcará `COMPLETED` únicamente cuando SPECIALIST-001, TRADER-001, VALIDATION-001, STATISTICS-001, KNOWLEDGE-001, OPTIMIZATION-001, SPECIALIZED-GOVERNANCE-001 y SPECIALIZED-GOVERNANCE-002 estén integrados y una revisión transversal confirme que los servicios especializados pueden componerse y colaborar de forma determinista sin infraestructura externa ni ejecución de trading.

## Resultado esperado

Al cerrar PHASE-05, QORE debe disponer de una capa especializada capaz de producir análisis, validar, medir, representar conocimiento y proponer optimizaciones sobre el Core funcional existente, lista para que fases posteriores incorporen adapters de datos/infraestructura y ejecución bajo fronteras explícitas.

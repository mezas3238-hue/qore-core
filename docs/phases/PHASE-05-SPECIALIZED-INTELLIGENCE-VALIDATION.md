# PHASE-05 — Specialized Intelligence & Validation Services

## Estado

**COMPLETED**

PHASE-05 queda cerrada formalmente sobre el `main` que integra la capa especializada completa, su composición con PHASE-04 y el hardening transversal de integridad de evidencia.

## Objetivo

Introducir la primera capa de servicios especializados de QORE sobre el gobierno funcional ya estabilizado, manteniendo contratos deterministas, composición explícita y aislamiento respecto de infraestructura externa.

PHASE-05 demuestra que servicios especializados pueden analizar, validar, medir, representar conocimiento y proponer mejoras sobre decisiones y flujos internos sin abrir conexiones externas, ejecutar órdenes ni asumir persistencia real.

## Principios verificados

- Los servicios especializados se construyen sobre contratos comunes y módulos componibles.
- Ningún servicio especializado entra en `RuntimePlan` por existir como módulo de dominio.
- Toda identidad, timestamp, correlation y causation se suministra explícitamente.
- Ningún servicio genera side effects externos.
- Ningún servicio ejecuta órdenes ni modifica brokers/exchanges.
- Los resultados especializados son inmutables, trazables y deterministas.
- Validation, Statistics, Knowledge y Optimization no son fuentes ocultas de verdad global mutable.
- Los Traders Virtuales producen análisis especializados, no órdenes ejecutables.
- La cadena de evidencia retiene fuentes completas desde `SpecialistAnalysis` hasta `OptimizationProposal`.
- PHASE-04 Functional Governance permanece compatible, componible y aislada del Runtime.

## Fuera de alcance preservado

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

## Entregables completados

### QORE-SPECIALIST-001 — Specialist Analysis Contracts

Estado: **COMPLETED** — PR #27.

Contratos comunes de análisis especializado con identidad, kind, lifecycle, confidence finita, razones estructuradas, metadata inmutable, correlation/causation explícitas y representación lógica estable.

### QORE-TRADER-001 — Virtual Trader Foundation

Estado: **COMPLETED** — PR #28.

Trader Virtual componible que transforma decisiones funcionales resueltas en `SpecialistAnalysis` deterministas sin market data externo, broker ni órdenes ejecutables.

### QORE-VALIDATION-001 — Validation Lab Foundation

Estado: **COMPLETED** — PR #29, endurecido transversalmente por PR #35.

Validation evalúa análisis completados mediante políticas explícitas y produce `ValidationAssessment` trazables. El assessment conserva el `SpecialistAnalysis` fuente completo y exige que confidence, correlation y causation coincidan exactamente con la evidencia validada.

### QORE-STATISTICS-001 — Statistics Service Foundation

Estado: **COMPLETED** — PR #30, endurecido transversalmente por PR #35.

Statistics produce snapshots descriptivos deterministas sobre assessments explícitos. `StatisticsSnapshot` conserva los `ValidationAssessment` fuente completos y exige que counts, pass rate y mean confidence sean una proyección exacta de ellos.

### QORE-KNOWLEDGE-001 — Knowledge Service Foundation

Estado: **COMPLETED** — PR #31.

Knowledge conserva el `StatisticsSnapshot` completo y solo representa métricas que coinciden exactamente con su evidencia fuente. No hay memoria global mutable, embeddings ni almacenamiento externo.

### QORE-OPTIMIZATION-001 — Optimization Service Foundation

Estado: **COMPLETED** — PR #32.

Optimization produce propuestas deterministas `KEEP`/`ADJUST` a partir de `KnowledgeRecord` explícitos. Recomienda cambios pero no los aplica automáticamente.

### QORE-SPECIALIZED-GOVERNANCE-001 — Specialized Services Decision Flow

Estado: **COMPLETED** — PR #33.

Flujo oficial por MessageBus:

`FunctionalDecision → Virtual Trader → Validation → Statistics → Knowledge → Optimization`

Un verdict `FAILED` de Validation se conserva como evidencia válida y continúa por el pipeline; solo un `Failure` técnico/de contrato detiene etapas posteriores.

### QORE-SPECIALIZED-GOVERNANCE-002 — Specialized Services Composition & End-to-End Flow

Estado: **COMPLETED** — PR #34.

Composition root especializado por encima de Core y Functional Governance usando un solo `bootstrap()`, un solo Core y un solo MessageBus. Registra en orden estable los cuatro módulos de PHASE-04 y los cinco servicios especializados de PHASE-05, expone ambos flujos y demuestra el recorrido funcional→especializado end-to-end sin alterar Runtime.

## Auditoría transversal de cierre

La revisión conjunta de SPECIALIST-001 + TRADER-001 + VALIDATION-001 + STATISTICS-001 + KNOWLEDGE-001 + OPTIMIZATION-001 + SPECIALIZED-GOVERNANCE-001 + SPECIALIZED-GOVERNANCE-002 detectó y corrigió dos huecos de integridad de evidencia antes del cierre formal:

1. `ValidationAssessment` conservaba solo `source_analysis_id`, permitiendo construir directamente un assessment cuya confidence no coincidiera con el análisis que afirmaba validar.
2. `StatisticsSnapshot` conservaba solo IDs de assessments, permitiendo construir directamente métricas internamente coherentes pero no derivadas de la evidencia declarada.

El PR #35 corrigió ambos puntos:

- `ValidationAssessment` retiene el `SpecialistAnalysis` completo y deriva `source_analysis_id` desde él.
- `StatisticsSnapshot` retiene todos los `ValidationAssessment` fuente y deriva `source_assessment_ids` desde ellos.
- confidence, correlation, causation, verdict, counts, pass rate y mean confidence quedan verificadas contra la evidencia completa.
- Knowledge y Optimization permanecen alineados con esa cadena de evidencia retenida.

El hardening transversal pasó QORE CI Run #184 con Ruff, Mypy strict y Pytest en verde antes de mergearse en `main` como `934d6885ad8a4be361310498bce3487d720d40c4`.

## Evidencia de integración

- PR #27 — QORE-SPECIALIST-001 — merge `8030a18b959e40da05db8fe9fcde6c3341243409`.
- PR #28 — QORE-TRADER-001 — merge `0d31c1262a38805b1c162dc591e7c2bdd1c62aaf`.
- PR #29 — QORE-VALIDATION-001 — merge `5e75556b91db54c0f9e582d821a59667a0b7188c`.
- PR #30 — QORE-STATISTICS-001 — merge `dfbd0d299bd4705fff47f160432f80cd2537c848`.
- PR #31 — QORE-KNOWLEDGE-001 — merge `2f0125d8e129c7ca3b07c3bbdc2b90862ae7dc4d`.
- PR #32 — QORE-OPTIMIZATION-001 — merge `48711667dbcc69f743cd469b8477be0835301f61`.
- PR #33 — QORE-SPECIALIZED-GOVERNANCE-001 — merge `d79ea2fa6cf407ccda0e79bcfbb6b537071a04ea`.
- PR #34 — QORE-SPECIALIZED-GOVERNANCE-002 — merge `d980df07b6330ce48ae27a314e715ceec63d5ab8`.
- PR #35 — PHASE-05 transversal evidence integrity hardening — merge `934d6885ad8a4be361310498bce3487d720d40c4`.

## Restricciones arquitectónicas verificadas

1. Todo módulo especializado es componible mediante los contratos de PHASE-03.
2. Los módulos especializados se registran solo durante la composición oficial.
3. Ningún módulo especializado muta `RuntimePlan`.
4. Ningún módulo especializado importa adapters de infraestructura.
5. Ningún módulo especializado usa reloj global ni generación global de UUIDs.
6. Los resultados compartidos viven en contratos comunes.
7. Validation no ejecuta la decisión que valida.
8. Statistics no persiste ni ingiere fuentes externas.
9. Knowledge no usa almacenamiento externo ni modelos externos.
10. Optimization no aplica automáticamente sus recomendaciones.
11. Virtual Trader no emite órdenes ejecutables ni conecta broker.
12. PHASE-04 Functional Governance permanece compatible y aislada.

## Quality Gate

Todos los cambios de cierre mantienen código de salida 0 para:

```bash
python --version
pip install -e ".[dev]"
python -c "import qore; print(qore.__name__)"
pytest
ruff check .
mypy src tests
```

Mypy permanece en `strict = true`, las pruebas son deterministas y Runtime/Functional Governance continúan desacoplados de infraestructura y ejecución.

## Condición de cierre

**SATISFECHA.**

SPECIALIST-001, TRADER-001, VALIDATION-001, STATISTICS-001, KNOWLEDGE-001, OPTIMIZATION-001, SPECIALIZED-GOVERNANCE-001 y SPECIALIZED-GOVERNANCE-002 están integrados. La auditoría transversal confirmó y endureció la colaboración determinista, la trazabilidad y la integridad de evidencia sin infraestructura externa ni ejecución de trading.

## Resultado final

QORE dispone de una capa especializada capaz de producir análisis, validar, medir, representar conocimiento y proponer optimizaciones sobre el Core funcional existente. La composición oficial enlaza PHASE-04 y PHASE-05 en un único Core/MessageBus, mantiene Runtime intacto y deja la arquitectura preparada para fases posteriores de adapters de datos, infraestructura y ejecución bajo fronteras explícitas.

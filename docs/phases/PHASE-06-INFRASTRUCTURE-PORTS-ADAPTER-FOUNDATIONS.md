# PHASE-06 — Infrastructure Ports & Adapter Foundations

## Estado

**COMPLETED**

PHASE-06 introdujo las fronteras oficiales entre QORE y la infraestructura externa sin contaminar Kernel, Runtime, Domain, Functional Governance ni Specialized Governance con detalles de proveedores, red, almacenamiento o ejecución.

La fase demuestra que QORE puede expresar dependencias externas mediante puertos tipados, implementar adapters de referencia deterministas, normalizar datos externos y componer infraestructura por encima del Core sin alterar las invariantes cerradas en PHASE-01 a PHASE-05.

PHASE-06 prepara Market Data, persistencia e integración externa futura, pero no habilita ejecución real de órdenes ni conectividad de broker/exchange.

## Principios preservados

- Los contratos de negocio dependen de puertos, nunca de adapters concretos.
- Los adapters dependen de los puertos y del Core, no al revés.
- Ningún adapter introduce estado global mutable.
- Toda entrada externa de Market Data se normaliza antes de cruzar hacia consumo canónico.
- Toda identidad, timestamp, correlation y causation sigue siendo explícita.
- Los adapters de referencia son deterministas y testeables sin red.
- RuntimePlan no incorpora adapters por el solo hecho de existir.
- Functional Governance y Specialized Governance permanecen ejecutables sin infraestructura externa.
- La composición de infraestructura se realiza por encima del Core mediante raíces explícitas.

## Fuera de alcance preservado

PHASE-06 no implementa:

- ejecución real de órdenes;
- broker/exchange order routing;
- MT5 trading;
- posiciones reales de broker;
- account funding o withdrawals;
- live credentials o secrets de producción;
- REST/gRPC/WebSocket públicos de QORE;
- Kafka, RabbitMQ u otros brokers distribuidos de producción;
- PostgreSQL/Redis productivos;
- market data live obligatorio;
- news feeds live obligatorios;
- UI, QORE Mobile o Widget del CEO;
- cambios autónomos de Optimization sobre configuración productiva.

## Entregables completados

### QORE-PORTS-001 — External Integration Port Contracts

Estado: **COMPLETED**

PR: #37  
Merge commit: `16543f12dbb42fd348db18faa73148346b82c5ce`

Se creó el lenguaje común para dependencias externas:

- identidad explícita de adapter/source;
- estado cerrado de disponibilidad;
- health/result tipados;
- contratos `Protocol` para ports externos;
- errores de frontera tipados;
- metadata/correlation explícita;
- cero IO o implementación concreta.

### QORE-MARKETDATA-001 — Market Data Port & Canonical Snapshot Contracts

Estado: **COMPLETED**

PR: #38  
Merge commit: `b17fe8415c629139fccde71c107daacd6ae1aede`

Se definieron contratos canónicos para datos de mercado suministrados externamente:

- instrumento canónico;
- timestamps/source explícitos;
- snapshots `QuoteSnapshot` y `OhlcSnapshot` inmutables;
- validación de precios, intervalos y namespace de source;
- port de Market Data provider-neutral;
- cero conexión live obligatoria.

### QORE-PERSISTENCE-001 — Persistence Port Contracts

Estado: **COMPLETED**

PR: #39  
Merge commit: `207bd9d464e01dde56301a8b42a08ec552c62861`

Se definieron contratos de persistencia para snapshots/resultados internos sin base de datos productiva:

- claves y versions explícitas;
- `StoredRecord`, `LoadPersistenceRequest`, `SavePersistenceRequest`;
- presencia/ausencia representada por `Success(record | None)`;
- conflictos representados por `Failure(PersistenceConflictError)`;
- caller expresa intención de escritura y el adapter confirma el registro persistido;
- sin SQL, Redis o filesystem productivo.

### QORE-ADAPTERS-001 — Deterministic Reference Adapters

Estado: **COMPLETED**

PR: #40  
Merge commit: `8d46dc9a6cd3af4e107f7b0492c67cff1fb3410f`

Se implementaron adapters de referencia in-memory para Market Data y Persistence:

- estado encapsulado por instancia;
- sin estado global mutable;
- defensive copy para valores persistidos;
- orden y lookup deterministas;
- sin reloj global;
- sin UUID implícito;
- sin red ni filesystem;
- pruebas de aislamiento entre instancias.

### QORE-INGESTION-001 — External Data Normalization Flow

Estado: **COMPLETED**

PR: #41  
Merge commit: `40d4f0e1c24c11ecbf80e2d095a487d8e6c287e9`

Se introdujo el flujo de normalización externa:

- payloads provider-neutral explícitos;
- `ExternalMarketDataPayloadPort`;
- `MarketDataIngestionFlow`;
- normalización determinista hacia `QuoteSnapshot` y `OhlcSnapshot`;
- rechazo de payloads inválidos;
- trazabilidad source → snapshot canónico;
- propagación de `Failure`;
- cero llamadas directas desde Domain hacia adapters concretos.

### QORE-INFRA-GOVERNANCE-001 — Adapter Boundary Composition

Estado: **COMPLETED**

PR: #44  
Merge commit: `7110fd1f39a8eee9af680ea5db4e752092a14187`

Se creó una raíz explícita de composición por encima del Core:

- `ReferenceInfrastructureConfiguration`;
- `InfrastructurePorts`;
- `ReferenceInfrastructureAdapters`;
- `ReferenceInfrastructureComposition`;
- `compose_reference_infrastructure`;
- adapters concretos retenidos fuera del Core;
- consumo por ports tipados;
- compatibilidad de Functional Governance y Specialized Governance sin infraestructura.

### QORE-INFRA-GOVERNANCE-002 — Infrastructure End-to-End Composition

Estado: **COMPLETED**

PR: #45  
Merge commit: `c09f1a9459d0eb4fc059a4a36774505101f4292e`

Se demostró el recorrido end-to-end determinista:

```text
reference external payload adapter
→ MarketDataIngestionFlow
→ canonical QuoteSnapshot/OhlcSnapshot
→ ReferenceInfrastructureComposition
→ canonical MarketDataPort + PersistencePort
```

Incluye:

- `ReferenceQuoteIngestionRequest`;
- `ReferenceOhlcIngestionRequest`;
- `ReferenceInfrastructureEndToEndConfiguration`;
- `ReferenceInfrastructureEndToEndComposition`;
- `compose_reference_infrastructure_end_to_end`;
- propagación de errores de normalización como `Failure` tipado;
- RuntimeSnapshot, RuntimeHealth y RuntimePlan intactos;
- compatibilidad PHASE-04/05 sin infraestructura externa.

## Revisión transversal de cierre

Estado: **COMPLETED**

La revisión transversal confirmó:

1. Kernel, Runtime y Domain Foundation no importan adapters concretos.
2. Functional y Specialized modules no importan adapters concretos.
3. Los ports viven en capas estables y no dependen de proveedores.
4. Los adapters concretos viven fuera de los contratos de dominio.
5. Ningún adapter de PHASE-06 genera UUID/timestamp implícitamente.
6. Ningún adapter muta RuntimePlan.
7. Los adapters de referencia no usan red, filesystem ni procesos externos.
8. Persistence no se convierte en source of truth mutable del dominio.
9. Market Data externo se normaliza antes de consumo canónico.
10. No se implementa ejecución de trading.
11. PHASE-04 y PHASE-05 siguen funcionando sin configurar infraestructura.
12. La composición de infraestructura usa un Core existente y preserva el MessageBus del Core.
13. La frontera E2E se mantiene por encima del Core y expone consumo por ports canónicos.
14. Source, correlation, causation, timestamps y snapshot IDs siguen siendo explícitos.
15. No se detectó necesidad de hardening adicional antes del cierre documental.

## Evidencia de Quality Gate

Cada entregable fue integrado mediante PR y Quality Gate real de GitHub Actions.

Evidencia final de los últimos entregables:

- QORE-INGESTION-001: QORE CI #218 PASS.
- QORE-INFRA-GOVERNANCE-001: QORE CI #234 PASS.
- QORE-INFRA-GOVERNANCE-002: QORE CI #236 PASS.

El cierre documental de PHASE-06 también debe pasar:

```bash
python --version
pip install -e ".[dev]"
python -c "import qore; print(qore.__name__)"
pytest
ruff check .
mypy src tests
```

## Condición de cierre

PHASE-06 queda completada cuando este documento se integre en `main` con Quality Gate verde.

Al cerrar PHASE-06, QORE dispone de:

- fronteras de infraestructura estables;
- Market Data canónico;
- contratos de persistencia;
- adapters de referencia deterministas;
- flujo de normalización externa;
- composición explícita por encima del Core;
- integración end-to-end determinista;
- compatibilidad preservada con PHASE-04 y PHASE-05;
- ausencia de ejecución real de trading o infraestructura productiva fuera de alcance.

## Resultado

PHASE-06 deja preparado el sistema para adapters live y ejecución en fases posteriores bajo contratos explícitos, sin romper las fronteras cerradas previamente.

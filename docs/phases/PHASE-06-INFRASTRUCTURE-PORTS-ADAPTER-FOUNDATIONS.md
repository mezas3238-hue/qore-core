# PHASE-06 — Infrastructure Ports & Adapter Foundations

## Estado

**ACTIVE**

PHASE-06 comienza sobre el `main` que cierra formalmente PHASE-05 — Specialized Intelligence & Validation Services.

## Objetivo

Introducir las fronteras oficiales entre QORE y la infraestructura externa sin contaminar Kernel, Runtime, Domain, Functional Governance ni Specialized Governance con detalles de proveedores, red, almacenamiento o ejecución.

PHASE-06 debe demostrar que QORE puede expresar dependencias externas mediante puertos tipados, implementar adapters de referencia deterministas y componerlos por encima del Core sin alterar las invariantes cerradas en PHASE-01 a PHASE-05.

Esta fase prepara Market Data, persistencia e integración externa futura, pero no habilita todavía ejecución real de órdenes ni conectividad de broker/exchange.

## Principios

- Los contratos de negocio dependen de puertos, nunca de adapters concretos.
- Los adapters dependen de los puertos y del Core, no al revés.
- Ningún adapter puede introducir estado global mutable.
- Toda entrada externa debe normalizarse antes de cruzar al dominio.
- Toda identidad, timestamp, correlation y causation siguen siendo explícitos.
- Los adapters de referencia deben ser deterministas y completamente testeables sin red.
- RuntimePlan no incorpora adapters por el solo hecho de existir.
- Functional Governance y Specialized Governance deben permanecer ejecutables sin infraestructura externa.
- La composición de infraestructura se realiza por encima del Core mediante una raíz explícita.

## Fuera de alcance

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

## Entregables

### QORE-PORTS-001 — External Integration Port Contracts

Estado: definido, pendiente de implementación.

Crear el lenguaje común para dependencias externas antes de introducir adapters concretos.

Alcance mínimo:

- identidad explícita de adapter/source;
- estado cerrado de disponibilidad;
- health/result tipados;
- contratos `Protocol` para ports externos;
- errores de frontera tipados;
- metadata/correlation explícita donde corresponda;
- cero IO o implementación concreta en este entregable.

### QORE-MARKETDATA-001 — Market Data Port & Canonical Snapshot Contracts

Estado: definido, pendiente de implementación.

Definir contratos canónicos para datos de mercado suministrados externamente y un port de lectura/ingestión desacoplado del proveedor.

Alcance mínimo:

- instrumento canónico;
- timestamp/source explícitos;
- OHLC/quote snapshot inmutable;
- validación de precios/orden temporal;
- port de Market Data;
- cero conexión live obligatoria.

### QORE-PERSISTENCE-001 — Persistence Port Contracts

Estado: definido, pendiente de implementación.

Definir puertos de persistencia para snapshots/resultados internos sin introducir una base de datos productiva.

Alcance mínimo:

- contratos de repository/store tipados;
- claves/versions explícitas;
- resultados de lectura/escritura tipados;
- ausencia/presencia representada sin excepciones laterales;
- sin SQL, Redis o filesystem productivo.

### QORE-ADAPTERS-001 — Deterministic Reference Adapters

Estado: definido, pendiente de implementación.

Implementar adapters de referencia in-memory para los puertos aprobados de Market Data y Persistence.

Alcance mínimo:

- estado encapsulado por instancia;
- defensive copy/inmutabilidad;
- orden estable;
- sin reloj/UUID global;
- sin red ni filesystem;
- pruebas de aislamiento entre instancias.

### QORE-INGESTION-001 — External Data Normalization Flow

Estado: definido, pendiente de implementación.

Introducir el flujo que transforma input de adapter en contratos canónicos antes de entregar información al dominio o a servicios especializados.

Alcance mínimo:

- normalización determinista;
- rechazo de payloads inválidos;
- trazabilidad source → canonical snapshot;
- propagación de `Failure`;
- cero llamadas directas desde dominio a adapters concretos.

### QORE-INFRA-GOVERNANCE-001 — Adapter Boundary Composition

Estado: definido, pendiente de implementación.

Crear una composición explícita de ports y reference adapters por encima del Core, preservando la inversión de dependencias y sin alterar `CoreApplication`.

### QORE-INFRA-GOVERNANCE-002 — Infrastructure End-to-End Composition

Estado: definido, pendiente de implementación.

Demostrar un recorrido end-to-end determinista desde un adapter de referencia → normalización → contratos canónicos → consumo por la aplicación compuesta, manteniendo PHASE-04/05 compatibles y Runtime intacto.

## Restricciones arquitectónicas

1. Kernel, Runtime y Domain Foundation no importan adapters concretos.
2. Functional y Specialized modules no importan adapters concretos.
3. Los ports viven en capas estables y no dependen de proveedores.
4. Los adapters concretos viven fuera de los contratos de dominio.
5. Ningún adapter genera UUID/timestamp implícitamente salvo que un futuro contrato lo autorice de forma explícita; PHASE-06 no lo autoriza.
6. Ningún adapter puede mutar RuntimePlan.
7. Los adapters de referencia no usan red, filesystem ni procesos externos.
8. Persistence no se convierte en source of truth mutable del dominio.
9. Market Data externo debe normalizarse antes de entrar en decisiones/análisis.
10. No se implementa ejecución de trading en esta fase.
11. PHASE-04 y PHASE-05 deben seguir funcionando sin configurar infraestructura.
12. La composición de infraestructura usa un único Core y un único MessageBus cuando corresponda.

## Criterios de aceptación globales

Todos los PR de PHASE-06 deben terminar con código de salida 0 para:

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
- Todo port público tiene pruebas de contrato.
- Todo adapter tiene pruebas de aislamiento y ausencia de estado global mutable.
- Toda frontera prueba errores tipados y propagación de `Failure`.
- Toda normalización prueba payloads válidos e inválidos.
- Los cambios de composición vuelven a probar Runtime, Functional Governance y Specialized Governance.

## Quality Gate

Cada PR solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera de alcance;
- el head revisado sea exactamente el head mergeado;
- la revisión semántica confirme que no se introdujo ejecución de trading ni dependencia inversa hacia adapters;
- PHASE-04 y PHASE-05 permanezcan compatibles y desacopladas de infraestructura concreta.

## Condición de cierre

PHASE-06 se marcará `COMPLETED` únicamente cuando PORTS-001, MARKETDATA-001, PERSISTENCE-001, ADAPTERS-001, INGESTION-001, INFRA-GOVERNANCE-001 e INFRA-GOVERNANCE-002 estén integrados y una revisión transversal confirme que QORE puede consumir infraestructura mediante ports/adapters deterministas sin romper las fronteras cerradas previamente.

## Resultado esperado

Al cerrar PHASE-06, QORE debe disponer de fronteras de infraestructura estables, Market Data canónico, contratos de persistencia, adapters de referencia e integración end-to-end determinista, dejando preparado el sistema para adapters live y ejecución en fases posteriores bajo contratos explícitos.

# PHASE-07 — External Provider Integration Readiness

## Estado

**ACTIVE**

PHASE-07 comienza después del cierre formal de PHASE-06 — Infrastructure Ports & Adapter Foundations.

Base inicial de trabajo:

```text
main @ 9e07375624eec74f84dcec3a04453af99bcf1b82
```

## Objetivo

Preparar QORE para integraciones externas reales bajo contratos explícitos, sin habilitar todavía ejecución de trading ni acoplar el Core a proveedores concretos.

PHASE-07 toma las fronteras estables de PHASE-06 — ports, snapshots canónicos, persistencia, adapters de referencia, ingestión y composición end-to-end — y añade una capa de readiness para proveedores externos:

```text
provider configuration
→ provider boundary governance
→ provider adapter harness
→ normalization / canonical contracts
→ composed application ports
```

El objetivo no es operar cuentas reales, enviar órdenes ni conectar credenciales productivas. El objetivo es dejar preparada la frontera para que futuros adapters live puedan integrarse de forma gobernada, testeable, observable y reversible.

## Principios

- El repositorio sigue siendo la fuente única de verdad.
- El Core permanece libre de adapters concretos.
- Domain, Runtime, Functional Governance y Specialized Governance no importan proveedores ni adapters concretos.
- Toda integración externa cruza por ports aprobados.
- Toda entrada externa de Market Data se normaliza antes de consumo canónico.
- Toda identidad, timestamp, correlation, causation y snapshot ID sigue siendo explícito.
- Ningún adapter puede generar UUID o timestamps implícitos sin contrato explícito.
- Ningún adapter puede mutar RuntimePlan.
- La configuración de proveedores es explícita, validable y no contiene secretos en claro.
- Los secretos se representan únicamente como referencias o handles seguros, nunca como valores productivos dentro del Core.
- Las integraciones nuevas deben tener harness determinista y dobles de prueba antes de cualquier implementación real.
- Toda degradación externa debe expresarse como `Failure` tipado o health degradado, nunca como excepción lateral no gobernada.

## Fuera de alcance

PHASE-07 no implementa:

- ejecución real de órdenes;
- order routing de broker/exchange;
- MT5 trading;
- gestión de posiciones reales;
- account funding o withdrawals;
- credenciales productivas en repositorio;
- conexión obligatoria a broker live;
- automatización de entradas/salidas de trading;
- cambios autónomos de Optimization sobre configuración productiva;
- QORE Mobile o Widget del CEO;
- UI pública;
- REST/gRPC/WebSocket públicos de QORE;
- infraestructura distribuida productiva obligatoria.

## Frontera de arquitectura

PHASE-07 introduce readiness externa por encima de PHASE-06, no dentro del Core.

Permitido:

```text
qore.infrastructure.provider_*
qore.infrastructure.*_configuration
qore.infrastructure.*_observability
qore.infrastructure.*_resilience
qore.infrastructure.*_harness
```

No permitido:

```text
qore.core -> provider adapters
qore.domain -> provider adapters
qore.governance -> concrete adapters
qore.specialized_governance -> concrete adapters
RuntimePlan -> automatic infrastructure registration
```

La composición debe seguir siendo explícita y opt-in.

## Entregables

### QORE-PROVIDER-BOUNDARY-001 — Provider Adapter Governance Contracts

Estado: definido, pendiente de implementación.

Definir contratos de gobernanza para providers externos sin introducir providers concretos todavía.

Alcance mínimo:

- `ProviderId` o equivalente canónico;
- descriptor de proveedor independiente de adapter/source;
- estado de habilitación explícito;
- contrato de capacidades provider-neutral;
- errores tipados de frontera provider;
- validaciones runtime para bypasses;
- cero red, cero credenciales y cero IO concreto.

### QORE-ADAPTER-CONFIG-001 — External Adapter Configuration Contracts

Estado: definido, pendiente de implementación.

Definir configuración validable para adapters externos sin acoplarla al Core ni a secretos productivos.

Alcance mínimo:

- configuración inmutable por adapter;
- separación entre configuración pública y secretos;
- flags explícitos de modo `disabled`, `simulation`, `read_only` o equivalentes;
- validación de provider/source/port namespaces;
- no usar variables de entorno directamente desde contratos;
- no cargar archivos de configuración productivos desde el Core.

### QORE-SECRETS-BOUNDARY-001 — Secret Reference Boundary

Estado: definido, pendiente de implementación.

Crear una frontera de referencias a secretos sin almacenar ni exponer valores sensibles.

Alcance mínimo:

- `SecretRef` o equivalente canónico;
- política de no revelar valores;
- validaciones contra strings vacíos o valores inline sospechosos;
- contratos para resolución futura sin implementación productiva obligatoria;
- errores tipados para secreto ausente, denegado o inválido;
- pruebas de no filtrado en `repr`, `str`, logical values o errores.

### QORE-ADAPTER-OBSERVABILITY-001 — Adapter Observability Contracts

Estado: definido, pendiente de implementación.

Definir contratos de observabilidad para adapters externos sin introducir un backend de monitoreo productivo.

Alcance mínimo:

- snapshot de estado observable de adapter;
- health extendido o métricas provider-neutral;
- latencia recibida de caller o medición explícita inyectada, no reloj global implícito;
- últimos errores tipados sin payload sensible;
- readiness/degraded/unavailable claramente expresado;
- pruebas de determinismo y privacidad.

### QORE-ADAPTER-RESILIENCE-001 — Retry, Timeout & Rate Limit Policy Contracts

Estado: definido, pendiente de implementación.

Definir políticas declarativas de resiliencia sin ejecutar red real.

Alcance mínimo:

- contratos de timeout explícito;
- retry policy inmutable;
- rate limit policy provider-neutral;
- circuit-breaker state como contrato observable, si aplica;
- errores tipados por timeout, throttling y unavailable;
- cero sleep real en pruebas;
- cero backoff basado en reloj global.

### QORE-MARKETDATA-PROVIDER-HARNESS-001 — Read-Only Market Data Provider Harness

Estado: definido, pendiente de implementación.

Preparar un harness de Market Data externo de solo lectura que demuestre cómo un provider futuro alimentará el flujo de ingestión sin saltarse contratos canónicos.

Alcance mínimo:

- adapter/harness determinista de payloads provider-like;
- configuración explícita de provider;
- sin conexión live obligatoria;
- sin credenciales productivas;
- normalización mediante `MarketDataIngestionFlow`;
- consumo final por `MarketDataPort` canónico;
- tests de payload válido, payload inválido, unavailable, throttled y source mismatch.

### QORE-PERSISTENCE-BACKEND-HARNESS-001 — Persistence Backend Readiness Harness

Estado: definido, pendiente de implementación.

Preparar un harness de persistencia externa sin convertir persistencia en source of truth mutable del Domain.

Alcance mínimo:

- configuración explícita de backend;
- adapter/harness determinista;
- semántica de version/conflict preservada;
- ausencia como `Success(None)`;
- conflictos como `Failure(PersistenceConflictError)` o subtipo aprobado;
- no SQL/Redis/filesystem productivo obligatorio;
- defensive copy o serialización determinista controlada;
- tests de aislamiento entre instancias.

### QORE-PROVIDER-E2E-READINESS-001 — Provider Readiness End-to-End Composition

Estado: definido, pendiente de implementación.

Demostrar un recorrido end-to-end de readiness:

```text
provider config
→ provider harness
→ external payload
→ ingestion
→ canonical snapshots
→ composed infrastructure ports
→ application-level consumption
```

Alcance mínimo:

- composición explícita por encima del Core;
- un solo Core y MessageBus preservado;
- RuntimeSnapshot, RuntimeHealth y RuntimePlan intactos;
- Functional Governance y Specialized Governance siguen funcionando sin provider config;
- Failure propagation end-to-end;
- sin trading execution.

### QORE-PHASE07-CLOSURE-001 — Phase 07 Closure Review

Estado: definido, pendiente de implementación.

Cerrar PHASE-07 únicamente después de revisión transversal.

Auditar:

- no imports inversos hacia providers;
- no secretos expuestos;
- no red obligatoria en tests;
- no filesystem/SQL/Redis productivo obligatorio;
- no ejecución de trading;
- no mutación de RuntimePlan;
- no generación implícita de UUID/timestamps;
- compatibilidad completa de PHASE-04/05/06;
- Quality Gate verde en el head final.

## Criterios de aceptación globales

Todos los PR de PHASE-07 deben terminar con código de salida 0 para:

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
- Todo contrato público tiene pruebas de validación runtime.
- Toda frontera prueba errores tipados y propagación de `Failure`.
- Toda configuración prueba valores válidos e inválidos.
- Toda referencia a secreto prueba no exposición.
- Todo harness externo prueba ausencia de IO productivo obligatorio.
- Los cambios de composición vuelven a probar Runtime, Functional Governance y Specialized Governance.

## Quality Gate

Cada PR solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera de alcance;
- el head revisado sea exactamente el head mergeado;
- la revisión semántica confirme que no se introdujo ejecución de trading;
- la revisión semántica confirme que no se introdujo dependencia inversa hacia providers;
- la revisión semántica confirme que no se filtraron secretos.

## Condición de cierre

PHASE-07 se marcará `COMPLETED` únicamente cuando todos sus entregables estén integrados y una revisión transversal confirme que QORE está preparado para integrar providers externos bajo contratos gobernados, sin romper la independencia del Core ni habilitar ejecución real de trading.

## Resultado esperado

Al cerrar PHASE-07, QORE debe disponer de una frontera robusta para providers externos: configuración explícita, referencias seguras a secretos, observabilidad, resiliencia declarativa y harnesses deterministas que permitan validar adapters futuros antes de conectividad live o ejecución real.

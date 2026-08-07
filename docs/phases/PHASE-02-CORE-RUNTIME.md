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

## Entregable inicial

### QORE-CORE-RUNTIME-001 — Runtime Context & Execution Contracts

Debe introducir únicamente los contratos mínimos necesarios para representar y gobernar una ejecución del Core.

### Alcance

- `RuntimeContext` inmutable.
- Identidad explícita de ejecución.
- Versionado mínimo del runtime.
- Contrato explícito para componentes del Core.
- Registro y resolución tipados de componentes.
- Reglas de idempotencia por identidad donde corresponda.
- Eventos internos del lifecycle:
  - runtime started;
  - runtime stopped;
  - runtime failed.
- Propagación determinista de fallos mediante `Result`.
- Integración con `ApplicationLifecycle` sin romper su API actual.
- Pruebas de invariantes, transiciones y compatibilidad con PHASE-01.

## Restricciones arquitectónicas

1. El Runtime no puede importar módulos de dominio de trading.
2. El Runtime no puede crear conexiones externas.
3. El Runtime no puede depender de reloj global ni generar timestamps implícitos no inyectados.
4. El Runtime no puede usar singletons ni registros globales mutables.
5. Los objetos de contexto deben ser inmutables.
6. Todo fallo operacional representable debe retornar `Result` cuando el contrato existente de QORE lo requiera.
7. La composición del Core debe permanecer explícita desde `bootstrap`.
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
- Debe existir cobertura explícita para los eventos de lifecycle y la propagación de errores.
- Debe demostrarse que no se introduce ninguna dependencia de infraestructura o dominio de trading.
- El CI de GitHub Actions debe terminar completamente en verde antes de merge.

## Quality Gate

El PR de `QORE-CORE-RUNTIME-001` solo puede mergearse cuando:

- Ruff = PASS;
- Mypy strict = PASS;
- Pytest = PASS;
- no existan hilos de revisión sin resolver;
- no existan cambios fuera del alcance de esta fase;
- el head revisado sea exactamente el head que se mergea.

## Resultado esperado

Al cerrar esta fase, QORE debe poseer un runtime base capaz de representar una ejecución y su ciclo de vida de forma determinista, tipada y extensible, listo para que fases posteriores incorporen servicios de dominio sin contaminar el Core con infraestructura ni lógica de trading.

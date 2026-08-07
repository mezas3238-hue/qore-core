# PHASE-01 — Core Foundation

## Objetivo

Demostrar que QORE posee una fundación ejecutable, instalable, importable, tipada, testeable y reproducible antes de introducir lógica de negocio.

## Fuera de alcance

Esta fase no implementa trading, Traders Virtuales, CIBO, DeepSeek, Portfolio, Risk Engine, Laboratory, market data, news APIs, adapters ni QORE Mobile.

## Entregables

- Paquete Python `qore` con bootstrap mínimo.
- Suite mínima de pruebas.
- Ruff y Mypy en configuración estricta.
- GitHub Actions como evidencia de ejecución en entorno limpio.
- Constitución fundacional de QORE.

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

La fase permanece bloqueada mientras cualquiera de estos criterios falle o no exista evidencia de ejecución.

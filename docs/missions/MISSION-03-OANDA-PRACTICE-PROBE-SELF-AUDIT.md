# MISSION-03 — OANDA Practice Probe Self-Audit

## Estado

**AUXILIARY OPERATIONAL PREPARATION — REAL EVIDENCE STILL REQUIRED**

Este trabajo endurece el workflow manual `QORE OANDA Practice Market Feed Probe` para que una ejecución real exitosa no publique evidencia únicamente porque el probe produjo un archivo. El archivo sanitizado debe pasar además el auditor determinístico ya integrado antes de que GitHub Actions lo suba como artifact.

No crea evidencia externa por sí mismo y no modifica el estado operacional de `QORE-LIVE-MARKET-FEED-ACTIVATION-001`.

## Flujo endurecido

```text
manual workflow_dispatch
        |
        v
Practice-only secret bindings
        |
        v
one real read-only OANDA Practice quote
        |
        v
sanitized evidence JSON
        |
        v
explicit audit timestamp
        |
        v
OandaPracticeEvidenceAuditPolicy
        |
        v
exact-schema / Practice / identity / freshness audit
        |
        +-- failure --> workflow fails; no artifact upload
        |
        v
upload audited sanitized artifact
```

## CLI de auditoría

`qore.infrastructure.oanda_practice_evidence_audit_cli` es únicamente una composition surface de archivo local sobre `audit_oanda_practice_operational_evidence`.

Recibe explícitamente:

- path del artifact sanitizado;
- run key esperado;
- instrumento esperado;
- `audited_at` timezone-aware;
- máximo de edad de observación en segundos.

No resuelve secrets, no realiza red y no conoce account IDs reales.

## Policy del workflow

El workflow usa una ventana explícita de auditoría de `300` segundos.

Ese valor es una policy interna del workflow para aceptar solamente evidencia reciente producida por la misma ejecución. No representa un límite documentado de OANDA ni una definición universal de market-data freshness.

El auditor exige además:

- schema exacto `qore.oanda-practice.market-feed-evidence.v1`;
- `status=success`;
- run key idéntico a `${{ github.run_id }}-${{ github.run_attempt }}`;
- instrumento idéntico al input cerrado `EUR_USD` o `GBP_USD`;
- provider `oanda-v20`;
- environment `demo`;
- endpoint `api-fxpractice.oanda.com`;
- account identity únicamente como fingerprint sanitizado;
- snapshot UUID válido;
- timestamp aware y no futuro;
- bid/ask JSON float finitos, positivos y no cruzados;
- ausencia de cualquier campo público extra.

## Fail-closed upload

`actions/upload-artifact` se ejecuta después del paso de auditoría.

Por lo tanto, cualquiera de estos estados bloquea el artifact:

- probe fallido;
- JSON ausente o ilegible;
- schema inesperado;
- campos adicionales;
- run/instrument mismatch;
- indicio de Production;
- full account ID, token o authorization agregado al objeto público;
- timestamp futuro o demasiado antiguo;
- quote inválida.

El auditor no imprime valores arbitrarios rechazados. Los errores son mensajes cerrados y sanitizados.

## Fronteras preservadas

- Workflow sigue siendo `workflow_dispatch` únicamente.
- Production no se convierte en input.
- Solo OANDA Practice permanece autorizado.
- No se añaden órdenes.
- No se añade capital real.
- No se añade retry/reconnect ejecutable.
- No se añaden loops, scheduler, threads o `sleep`.
- No se modifica Core, Domain o Governance.
- El token y account ID permanecen únicamente en GitHub Actions secrets/runtime environment del probe.
- El CLI de auditoría nunca recibe secret material.

## Qué cambia cuando OANDA vuelva

Después de provisionar externamente los dos bindings autorizados y ejecutar manualmente el workflow desde `main`, un run exitoso ahora significará que:

1. el probe real completó la ruta Practice read-only;
2. el JSON sanitizado fue producido;
3. el mismo artifact pasó el auditor determinístico con identidad/freshness exactas;
4. solo entonces GitHub lo publicó como artifact auditable.

Esto reduce trabajo manual posterior, pero sigue siendo obligatorio inspeccionar el run real y su artifact antes de cerrar operacionalmente el entregable #5.

## Quality Gate

La implementación debe mantener:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Un CI determinístico verde valida el mecanismo de self-audit; no sustituye la futura llamada externa real a OANDA Practice.

# QORE CIBO P0 — checkpoint de unificación física del libro PAPER

**Fecha:** 2026-10-09 · **Rama implantada:** `agent/cibo-p0-fresh-paper-economic-votes-20261009` (PR #748, DRAFT) · **Destino integrador:** #745 · **Bloqueador de rama alternativa:** #746.

## Decisión arquitectónica: canonical PaperQDLE, NO dos libros

Se adopta como **única autoridad de reservas PAPER** `src/qore/infrastructure/qdle_paper_book.py::PaperQDLE` con `QDLE(research_paper_mode=True)` **solo en la llamada interna del adapter**, no como una segunda API pública. El constructor genérico directo `QDLE(..., research_paper_mode=True)` ahora falla deliberadamente. El competidor de PR #746 **NO puede mergearse sin migrar su runner/tests a la clase canónica**. PR #745 todavía no incorpora estos commits; trabajo de rama, **NO integración cerrada**.

### Bug demostrado y reparado

Antes del cambio: `HELD -> PAPER_FILLED` quitaba la posición de la consulta de reservas QDLE `HELD/SENDING/FILL_UNRECONCILED`. Un snapshot posterior podía representar el riesgo PAPEL tanto fuera como dentro del ledger; no había una restricción agregada del 5% sobre todas las operaciones PAPER, solamente 5% por nueva entrada. Eso falsea exposición, financiación y miembros de la cohorte.

Después del cambio:
1. `PAPER_FILLED` está incluido en la consulta atómica de held `risk`, `margin` y salud del QDLE.
2. **Techo total** research `remaining_risk=min(NAV*0.05 - sum(risk_HELD_or_PAPER_FILLED),unreserved_source - holds)` fail-closed, sin traspasar el 5%.
3. `PaperQDLE.publish_account` exige estado **bruto** (NAV, free source, margen) antes de las reservas PAPER; posiciones sintéticas no se incluyen adicionalmente como tickets MT5. El runner ha dejado de pre-restar posiciones PAPER en el snapshot. Los cuatro votos económicos siguen observando los abiertos, pero QDLE no vuelve a descontarlos.
4. Marcador permanente `meta.canonical_research_paper_authority` impide reabrir la SQLite con un QDLE broker; marca ajena del PR #746 `meta.research_paper_database` prohíbe automigración y exige import explícito auditado. Broker QDLE con reservas existentes o snapshots previos tampoco se reclasifica como PAPER.
5. `paper_fill` y `paper_settle` aceptan reintentos EXACTAMENTE idénticos y rechazan variaciones. `BEGIN IMMEDIATE` serializa las reservas entre instancias/procesos.
6. El runner exporta copia backup SQLite `cibo-p0-canonical-paper-3368.sqlite` con SHA256 y digest de auditoría de eventos, no solamente métricas finales.
7. `bisect_left` M5 posterior a decisión deja `FUTURE_M5_OPEN_NOT_OBSERVED_AT_TRADER_DECISION` en QDLE sin fingir lote ni precio predecisión. La cohorte queda explícitamente **no comparable** con la antigua de 540 si cambia el universo financiado; workflow preserva expediente de exclusión.

### Evidencia de CI (investigación)

- [Canonical PAPER 5% account gate run #37990184756](https://github.com/mezas3238-hue/qore-core/actions/runs/37990184756) — **SUCCESS**, incluye fuente y pruebas broker/live.
- [Canonical PAPER extended gate #37990274745](https://github.com/mezas3238-hue/qore-core/actions/runs/37990274745) — **SUCCESS**, con constructor canónico y prohibición de reapertura broker.
- [Canonical PAPER current gate #37990673286](https://github.com/mezas3238-hue/qore-core/actions/runs/37990673286) — **SUCCESS**, más pruebas incompatibilidad de base #746 y snapshots LIVE, SHA auditado en GitHub del run; comprobar commit SHA antes de atribuir prueba a otro HEAD.
- [Four-arm ATR 5% contract #37990673292](https://github.com/mezas3238-hue/qore-core/actions/runs/37990673292) — **SUCCESS** para primitivas y proof preflight, **NO** es full four-arm replay.
- Ninguno de estos tests demuestra rentabilidad, bid/ask histórico, M1 auténtico de VT31, USDJPY histórico, ni full MTM DD. No inventar esos indicadores.

### Pasos pendientes INTEGRADOR #745 — **obligatorios para certificar una autoridad única**

1. Fusionar cambios de `qore_dynamic_lot_engine.py`, `qdle_paper_book.py`, `test_qdle_paper_book.py` del branch #748, sin perder cambios nuevos de A3 ni el contrato broker/live. Revisar y ejecutar suites enteras exact SHA.
2. Unificar al mismo `PaperQDLE` los scripts y tests del PR #746 actualmente basados en `QDLE(research_paper_mode=True)`; los nombres de estado PAPER deben mapearse de manera explícita, NO mezclar `PAPER_OPEN` y `PAPER_FILLED` como dos holds independientes. Después, retirar el modo autónomo del script alterno o declararlo legacy **NO EXECUTABLE**.
3. Publicar una única fábrica de cuenta y `ledger_authority_version`, única SQLite por cuenta/run, un único agregado `reserved_stop_risk` y una única fuente de snapshot bruto por epoch. Traer los tests exactos de #746 que prueban trazabilidad de los 3.368 fingerprints.
4. Restablecer ATR14 nativo por TF original (M1 VT31), USDJPY por señal, cotizaciones causales, costes históricos autentificables; ejecutar la matriz A-X/A-Y/B-X/B-Y con mismo SHA y clasificación de $20 NDX como sensibilidad.
5. Confirmar stdout/artifacts **del nuevo exact HEAD**, SHA ZIP y origen de datos; ningún replay antiguo 540/246 debe tratarse como un brazo de la nueva matriz. No publicar PF/DD nuevo cuando faltan marks para MTM.

**Certificación vigente:** `ONE_CANONICAL_PAPER_BOOK_IMPLEMENTED_ON_PR748_ONLY / INTEGRATOR_MERGE_PENDING / FOUR_ARM_REPLAY_NOT_EXECUTED / 0_BROKER_FILLS / NO_LIVE / VPS_UNTOUCHED`.

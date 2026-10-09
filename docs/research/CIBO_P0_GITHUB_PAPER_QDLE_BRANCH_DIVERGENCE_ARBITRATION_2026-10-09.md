# CIBO P0 — Resolución obligatoria de divergencia QDLE PAPER entre PR #745 y #746

Fecha 2026-10-09. **GitHub + Trader Lab exclusivamente; NO VPS, NO LIVE.** Este documento registra un bloqueo nuevo detectado al comparar ramas activas, no afirma haber certificado un replay.

## Estado de ramas realmente inspeccionadas
- Integrador **PR #745**: `agent/cibo-sovereign-integration-p0-20261008`, HEAD observado `d790f8ac690ee25f331a3dc1e32a2cb1f2c75470`.
- Reparación experimental **PR #746**: `agent/cibo-p0-trader-lab-universal-gates-20261009`, desde `ba4ac149...`. Comparación al momento: 33 commits ahead / 6 behind respecto del integrador, con conflicto funcional en runner y lifecycle de QDLE. Reconfirmar HEAD antes de merge.
- Nunca cherry-pick ciego: verificar cambios de ambos lados y conservar tests de A1, A2, A3.

## Duplicidad funcional que debe RESOLVERSE, no mantenerse

**Alternativa A (PR #746):**
- `src/qore/infrastructure/qore_dynamic_lot_engine.py`: `research_paper_mode=True` explícito, bloqueo de apertura LIVE sobre la DB y transiciones `HELD -> PAPER_OPEN -> PAPER_SETTLED` o `HELD -> PAPER_ABORTED`, con `paper_events` idempotentes.
- La consulta de riesgo/margen del propio QDLE incluye `PAPER_OPEN` entre las reservas aún comprometidas; `PaperQdleSession.publish_snapshot` no descuenta una segunda vez exposiciones que ya siguen retenidas.
- `paper_unassessable` registra NO_NAV, NO_ATLAS, geometría y futuro M5 no observable, sin representar esos casos como cotizaciones de lote físico.
- Runner emite 3368 expedientes, libro contable auditado, exporta SQLite PAPER y SHA; no usa APIs de deals MT5 para simular fills.

**Alternativa B (rama base actual PR #745):**
- Módulo independiente `src/qore/infrastructure/qdle_paper_book.py::PaperQDLE(QDLE)`, con tabla `paper_trades`, `paper_unassessable`, y override de métodos LIVE del broker.
- Tras paper_fill cambia el estado a `PAPER_FILLED` y el QDLE físico original no incluye ese estado entre las reservas `HELD/SENDING/FILL_UNRECONCILED`; por tanto depende de que TODOS los snapshots externos reduzcan exactamente riesgo y margen de posiciones paper activas.
- Los fixtures de `tests/infrastructure/test_qdle_paper_book.py` restan una cantidad fija `$3` de riesgo y `$6` de margen por trade activo; esos valores son SOLO sintéticos y no prueban seguimiento del riesgo real `QDLEResult.total_risk_usd` / margen real.
- `paper_fill`, `paper_settle` y `paper_cancel` no son idempotentes exact-once: repetidos pueden fallar; hace falta política explícita de retry/crash si se elige este diseño.
- El override de `arm_for_live_send` protege instancias de `PaperQDLE`, pero una instancia ordinaria `QDLE` apuntando a la misma ruta SQLite no comprueba un marcador PAPER irreversible. Aislamiento operacional requiere refuerzo.

## Contrato canónico de unificación (propuesta P0)
1. **Una cuenta y UN libro** de reservas/posiciones P0 por experimento, jamás duplicar un estado `PAPER_OPEN/PAPER_FILLED` en dos tablas que actúan independientemente sobre riesgo.
2. Elegir una autoridad única. Recomendación de ingeniería: mantener estados PAPER como pendientes en cálculo atómico de riesgo/margen dentro de `QDLE`, con marcador irremovible de DB research-only, o demostrar formalmente equivalencia de la contabilidad externa de alternativa B antes de adoptar B.
3. Una misma señal `request_id`, lot físico y timestamp deben tener exactamente un `qdle_reservation` y uno de: unassessable (NO QUOTE), unfundable/blocked, paper_no_fill, paper_open, paper_settled o paper_open_unresolved.
4. `paper_fill` jamás debe invocar `acknowledge_fill`, `reconcile_fill`, `record_broker_settlement`; tampoco escribir tickets MT5 ficticios.
5. Tests: (a) 20+ trades simultáneos con coste y margen reales diferentes, (b) cierre/liberación exacta entre señales, (c) reinicio y retry idempotente, (d) 3368 IDs universales, (e) veto LIVE incluso al reabrir DB con clase equivocada, (f) modificación de estado económico entre dos señales cambia lote, (g) datos de M5 futuros NO llegan a predecisión.
6. La certificación económica sigue BLOQUEADA: aún se reutilizan decisiones Native MAX antiguas y `four_engine_caps_usd * NAV/60`; CIBO/4 motores no se re-ejecutan por evento. La fuente M5 2019-22 con spread fijo 2026 no es BID/ASK broker observado ni acredita PF/DD MTM.

## Protocolo de merge
- No resolver borrando indiscriminadamente QDLE de A3 o sustituyéndolo por un wrapper que fabrique lotes.
- Mantener #745 y #746 en DRAFT, comparar la implementación de `scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py` en ambos HEAD actuales.
- Decidir un único lifecycle PAPER en #739, migrar tests de la otra rama conservando coverage, ejecutar suites QDLE y workflow 3368 exact-SHA, inspeccionar JSON + SQLite y firmar conciliación con la cuenta QORE.
- Sólo entonces integrar A1 Native MAX por contexto y A2 cuatro votos frescos, ejecutar nuevamente en Trader Lab, y reportar PF/DD/NAV PAPER completos o `null` con limitaciones; no activar LIVE.

**Evidencia existente de CI separada:** Gate de recibos del PR #746 7/7 PASS en [run 37953966681](https://github.com/mezas3238-hue/qore-core/actions/runs/37953966681) para SHA anterior `5e67b289...`. NO equivale a certificado del nuevo ledger ni replay integral; el workflow 3368 último todavía carece de run/artifact inspeccionado desde GitHub en esta revisión.

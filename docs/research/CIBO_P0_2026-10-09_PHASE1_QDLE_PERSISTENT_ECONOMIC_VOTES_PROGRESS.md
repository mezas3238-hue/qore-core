# CIBO P0 — progreso técnico verificable (fase 1: QDLE persistente + motores)

**Fecha:** 2026-10-09. **PR:** #747 DRAFT/NO LIVE, base rama
`agent/cibo-sovereign-integration-p0-20261008`, HEAD de partida
`ba4ac149ef3085ec33b8c55bf1576afa2d3b987c`.
Handoff fuente:
`docs/research/CIBO_MASTER_P0_HANDOFF_2026-10-09_TRADER_LAB_3368_FULL_COGNITION_QDLE_REPAIR.md`.
**No emitir órdenes, no despliegue al VPS, no certificar trading con esta rama.**

## Aplicado

1. `src/qore/infrastructure/qore_dynamic_lot_engine.py`: dos APIs exclusivas de investigación,
   `reject_research_unquotable` y `finish_research_reservation` con misma SQLite,
   idempotencia, accounting de solicitudes 0 lot, causal release por evento.
   La ruta requiere `RESEARCH_` y los tres strict/finance LIVE apagados.
   Los eventos `RESEARCH_PAPER_TERMINAL` NO son broker fill ni settlement.
2. `scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py`: instancia QDLE
   una sola vez para el replay, cuenta con epoch creciente y posición/reserva
   retenida hasta el cierre PAPER o PATH_INVALID. No se suman manualmente
   `active` al riesgo de QDLE, que conserva HELD en la única base.
   Registra `UNQUOTABLE_RESEARCH` para las cuatro condiciones prequote.
   Falla explícitamente ante error interno del motor, evitando un silent drop.
3. Cuatro votos genuinos de los módulos nativos desde el nuevo
   `FourMotorObservation` por oportunidad físicamente cotizable;
   retiro PAPER aislado de haircut 3 pérdidas, margin 80% y cuotas
   15%/7.5%/10% previas. Producción conserva exactamente los defaults.
4. Los recibos broker de 2019-2022 se etiquetan como
   `research_proxy_only=True` y `broker_*_complete=False`:
   **NO existe evidencia histórica autenticada** de esas tarifas,
   spreads, cross JPY ni fills.
5. `tests/infrastructure/test_cibo_p0_research_qdle_persistence.py`:
   idempotencia, rechazo por geometría, exclusión de LIVE, un solo
   balance de reservas, 4 motor policy ablation.
6. CI `cibo-p0-research-qdle-ledger-tests.yml`:
   **PASS** run #37954299485 en commit `325329c117a12490ebb54eebd4673c13b44bdbe6`
   (compilación, tests de esta fase, four-motor tests y replay unitario).
7. Workflow de replay 3368 RESEARCH lanzado desde feature
   `cibo-trader-lab-p0-persistent-qdle-3368.yml`: run #37954501697.
   **No afirmar resultados hasta verificar conclusion SUCCESS y artefacto.**

## Estado estricto de gates

- AC01 (set 3368/3368): validación del script; falta verificar nuevo artifact.
- AC02: **FAILED**. CIBO Native MAX continúa heredado de decisiones previas.
  Requiere reconstruir `CiboEconomicConsultationReceipt` y ejecutar
  `build_native_max_cognitive_episode` en el timestamp causal por señal.
- AC03: **PARTIAL**. Se ejecutan 4 motores nativos por señal cotizable,
  pero los prequote no producen todavía 4 votos. Las observaciones dependen
  de NAV cash y no MTM, con input broker proxy.
- AC04: **PARTIAL**. Una fila de QDLE por señal incluyendo condiciones
  UNQUOTABLE; falta verificación de run integral.
- AC05: **PARTIAL**. Una SQLite y deducción/release de HELD;
  no hay `reconcile_fill` broker porque por contrato NO hay deals reales.
- AC06: **FAILED**. BANK/MEDIUM/ATTACK y políticas de salida aún son presets.
- AC07: **FAILED**. Gestión `replay_cibo_managed_position` heredada;
  no es episodio cognitivo en cada vela.
- AC08: **PARTIAL/NO CERTIFICATION**. Capital cash QORE y broker paper
  separados, sin una curva de NAV/equity MTM global.
- AC09: **FAILED para evidencia histórica real**. Fixed spread 2026 sobre M5 2019-22.
- AC10: **PARTIAL**. CI unitaria PASS, replay full no certificado.
- AC11: **PARTIAL**. Rechazos prequote auditados; forensics globales restantes.
- AC12: **FAILED**. PR #747 y #745 siguen DRAFT/NO LIVE.

## Riesgos técnicos pendientes incluso en esta fase

- El runner todavía conoce la primera vela M5 elegible al asignar entrada a
  la señal: falta scheduler global causal de órdenes y observaciones.
- Se registra apertura PAPER al momento previsto de decisión para la contabilidad
  económica, con fee del fill modelado; hay que reorganizar eventos cuando el
  fill simulado ocurra más tarde. No rotular como ejecución histórica.
- Cuando no hay salida terminal, la reserva permanece HELD, la cuenta carece de
  MTM y el NAV final certificado permanece null.
- Los datos de `cibo_max_native_management_mode` y `cibo_max_native_proposed_exit_management`
  se siguen leyendo del JSON viejo; cambiarlos exige pipeline nuevo, no
  renombrar las salidas.
- Mínimo de 0.01 lot, coste all-in, presupuesto 5% QORE NAV dinámico y
  margen broker siguen innegociables, sin inventar 3368 fills.

## Continuación coordinada

**A1 #737:** reconstruir episodios CIBO MAX con evidencia predecisión y
posición/PNL cash+MTM; política de gestión por cada cierre de M5, next-open.
Control contrafactual de FUTURO; 3368 decisiones genuinas y verificables.

**A2 #738:** cuatro votos incluso para geometría no cotizable como *denial*
con razón tipada, ligar snapshots causal NAV MTM/fees; no falsificar 4
votos físicos si falta bid/ask. Aportar roles y scopes auténticos.

**A3 #739:** QDLE paper ledger persistente + reservas como base; reconciliar
fill PAPER y cuota por evento con audit de MTM y margin; ninguna
permisión de orden LIVE ni fake broker ticket.

**Integración #745:** implementar scheduler UTC global y tratar gaps,
replay con insumos sellados; contrastar nueva curva vs baseline 539/537,
PF .716659 y DD CASH 85.197246% solo a igualdad de metodología,
**sin confundir DD cash con DD equity ni capital final con NAV real**.

**DoD siguiente fase:** AC01-12 con evidencias de workflow + artifact
SHA; 3368 CIBO recalc, 4×3368 votos justificados y 3368 QDLE receipts.
No declarar «terminado» por un CI de unit tests.

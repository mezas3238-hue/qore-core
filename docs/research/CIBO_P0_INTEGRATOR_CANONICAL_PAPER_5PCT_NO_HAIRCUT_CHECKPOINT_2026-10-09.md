# QORE CORE — P0 Integrador: libro PAPER canónico, riesgo total 5% y eliminación del haircut

**Fecha:** 2026-10-09 · **Integrador:** PR #745 · Rama `agent/cibo-sovereign-integration-p0-20261008` · Estado `DRAFT / PAPER / NO LIVE`.

## Resultado REAL del trabajo incorporado al integrador

La autoridad PAPER elegida en el PR #748 fue **trasladada directamente a código del integrador PR #745**. NO se fusionó el PR #748 completo; solo se incorporaron sus correcciones probadas, además de adaptar el runner de #745:
- `src/qore/infrastructure/qore_dynamic_lot_engine.py`
- `src/qore/infrastructure/qdle_paper_book.py`
- `tests/infrastructure/test_qdle_paper_book.py`
- `scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py`
- `src/qore/infrastructure/cibo_compound_capital.py`
- `tests/infrastructure/test_cibo_p0_no_loss_streak_haircut_integrator.py`
- `.github/workflows/cibo-p0-canonical-paper-5pct-ledger-gate.yml`
- `.github/workflows/cibo-trader-lab-native-qdle-market-atlas-3368.yml`

### Bug 1 — reservas desaparecían después del PAPER fill
Antes: se contaban `HELD/SENDING/FILL_UNRECONCILED`, pero NO `PAPER_FILLED`. Una operación PAPER abierta podía dejar de reservar el riesgo y margen dentro de QDLE. Ahora `PAPER_FILLED` permanece en la **misma** consulta SQLite del libro `PaperQDLE`. La financiación de nuevas entradas utiliza `max(0, NAV*5% - sum(held stop risk))` como límite **agregado del portafolio**. `BEGIN IMMEDIATE` mantiene atomicidad en concurrencia; el fill/settle se reintenta idempotentemente. El constructor de QDLE normal/broker no puede reabrir el archivo PAPER persistido y un segundo `QDLE(research_paper_mode=True)` no puede iniciar autoridad paralela. Marcas incompatibles de #746 precisan migración expresa y auditada.

### Bug 2 — doble resta de posiciones
El runner de #745 ya NO pre-reduce NAV y margen por reservas de posiciones PAPER, ni presenta tickets simulados como posiciones auténticas MT5. Publica snapshot económico bruto al único ledger QDLE; QDLE resta una sola vez todas las reservas `HELD` y `PAPER_FILLED`. Se conservan los datos de posición PAPER para la gestión de la cartera, pero NO como cobertura broker real.

### Bug 3 — precio M5 futuro en decisión anterior
El runner mantenía `first = bars[bisect_left(M5.opened_at, signal_decision_at)]`, valorando `first.open` **con as_of=signal_decision_at** incluso si esa vela M5 todavía no había empezado. El integrador ahora emite `FUTURE_M5_OPEN_NOT_OBSERVED_AT_TRADER_DECISION` y `PAPER_UNASSESSABLE_NO_PHYSICAL_QUOTE` por señal; ningún futuro OPEN entra en la cotización de un evento anterior. **Esto NO reconstruye un fill M1 auténtico**: requiere ticks/bid-ask históricos causales, timestamp de precio y revaluación antes del fill. El antiguo PF con cotizaciones adelantadas **no puede reutilizarse como resultado del runner reparado**.

### Bug 4 — haircut heredado
`propose_p0_compound_vote` en el integrador todavía tenía `THREE_SETTLED_LOSSES_HAIR_CUT`: después de tres pérdidas aplicaba un factor 0,5 al presupuesto. La rama #745 ahora elimina esa regla. Las pérdidas reales siguen reduciendo NAV mediante cashflows conciliados; reservas, pérdidas flotantes y capital protegido siguen teniendo plena vigencia. Test explícito verifica que racha y no racha con **mismo NAV** generan el **mismo** presupuesto.

### Evidencia de CI VERIFICADA (no rentabilidad)
- [GitHub Actions #37992661808 — canonical PAPER + no-haircut](https://github.com/mezas3238-hue/qore-core/actions/runs/37992661808): **SUCCESS** en SHA integrador `b342b80f73cf9b451a3455b5b7864816dc6783be`:
  - **10 pruebas** persistencia PAPER, reservas, concurrencia, reinicio, LIVE aislamiento: OK.
  - **3 pruebas** retirada de recorte por tres pérdidas, NAV real y capital protegido: OK.
  - **17 pruebas** QDLE broker/regresión: OK.
  - Total **30/30** en las pruebas ejecutadas por este gate. No significa que todas las suites de Core estén certificadas.
- El runner de 3.368 de #745 está instrumentado para exportar `cibo-p0-canonical-paper-3368.sqlite`, SHA256 y hash de auditoría de eventos **cuando se complete un replay nuevo**. No afirmar existencia ni valores del artifact hasta inspeccionar GitHub Actions del SHA nuevo.
- El workflow histórico de 3.368 aún usa M5 y comisiones/snapshot 2026 como **escenario RESEARCH PROXY**, no datos reales 2019–22. `full_cibo_managed_drawdown_pct` continúa nulo.

## Estado del arbitraje e implementación cuatro escenarios

- **#745** contiene ahora la única autoridad seleccionada `PaperQDLE_V1_SINGLE_RESERVATION_BOOK` y el gate de 5% agregado probado.
- **#746** sigue DRAFT y SU código alternativo no se ha migrado/retirado; **no merge** hasta adaptar su runner a `PaperQDLE` y validar exhaustivamente diferencias de `paper_events`, `paper_unassessable` y estados. No borrar observaciones o eventos, ni fabricar conversiones de ledger.
- **#748** contiene contrato **A-X/A-Y/B-X/B-Y** (BANK 1,25% vs hasta 5%; NDX0 vs NDX20 estrés), multiplicadores ATR nativos, tests de volumen/coste y evidencia gate. La preparación pasó CI, pero **NO se han ejecutado cuatro replays completos sobre las 3.368 señales**. No confundir resultados históricos 540/246 con variantes de la nueva matriz.
- Próximos gates: migración de #746 al mismo adapter, fuentes nativas M1/H1/H4/M15 con ATR14 cerrado, USDJPY histórico por oportunidad JPY, verdaderos bid/ask/contrato/tarifa histórica y directivas Native MAX renovadas; luego una agenda global con posiciones y DD sobre equity MTM y matriz cuatro escenarios. Si falta dato exigido, `NO_RESULT_CERTIFIED` y causa, nunca proxy presentado como real.

## Límites duros

**Nunca VPS; nunca MT5 LIVE; broker fills reales = 0; ninguna comisión histórica reclamada; ninguna rentabilidad nueva demostrada; no incrementar presupuesto ni introducir filtros derivados del desenlace.** PF previo de 0,716/0,621 sigue siendo únicamente de cohortes antiguas diferentes. El PF del integrador corregido solo puede afirmarse después de comprobar nuevo artifact exact-SHA.

**Status:** `CANONICAL_LEDGER_PORTED_TO_INTEGRATOR_AND_30_TESTS_PASS / #746_ALTERNATIVE_PENDING_MIGRATION / NEW_3368_REPLAY_NOT_YET_VALIDATED / FOUR_ARM_FINANCIAL_CI_NOT_DONE / NO_LIVE`.

## PRE-REPLAY SCIENTIFIC READINESS — 3368 SOURCE FORENSICS / NATIVE M1 (Oct 9, 2026)

### Ahora implementado en el integrador #745
- `config/research/cibo_p0_four_arm_atr_5pct_3368_2026-10-09.json`: cuatro combinaciones exactas A-X, A-Y, B-X, B-Y; BANK A=1,25%, BANK B=hasta5% NAV dinámico, NDX Y=$20/lote estrictamente **sensibilidad no broker real**, mínimo/grilla física 0,01.
- `scripts/cibo_p0_atr_four_arm_physical_budget.py`: política de lotaje para los cuatro brazos y techo de riesgo del 5% **después de descontar la comisión al abrir**, corregido con prueba de redondeo 0,03→0,02 lotes.
- `src/qore/infrastructure/cibo_p0_native_causal_market.py`: NativeBar M1/M15/H1/H4, Wilder ATR14 de velas nativas completamente cerradas, quote BID/ASK observable en o antes de T (nunca futura M5 OPEN), USDJPY del instante original para JPY. NO se afirma que un hash textual autentique fuente broker.
- `scripts/cibo_p0_native_3368_evidence_gate.py`: preflight del manifiesto sellado, identidad por fingerprint, Trader, año, símbolo y temporalidad; admite el futuro paquete `qore.cibo.p0.native-broker-evidence-by-signal.v1` y emite el motivo de falta por operación, siempre PAPER y cero broker fills.

### Evidencia ACTUAL verificada por GitHub Actions
- **[Manifiesto 3368 real, evidencia source gate #37997029969](https://github.com/mezas3238-hue/qore-core/actions/runs/37997029969): SUCCESS**, ZIP original SHA256 verificado, 8 pruebas unitarias PASS, archivo de resultados artifact **11647398006** `cibo-p0-3368-true-source-evidence-readiness-37997029969`.
- Población ORIGINAL exacta: **3368** señales, siete emisores. TF nativas **H1=2229, H4=493, M1=484 (VT31), M15=162**.
- `NO_CAUSAL_EVIDENCE_PACK_FOR_SIGNAL=3368` porque **esa ejecución NO suministró paquete histórico de bid/ask nativo, USDJPY y comisiones broker**, no porque CIBO haya rechazado financiar 3368 entradas. Esto es un resultado de **disponibilidad de evidencias, NO de estrategia**. `full_replay_ready=false`, `broker_fills=0`.
- **[Native M1/ATR14/USDJPY causal #37997030056](https://github.com/mezas3238-hue/qore-core/actions/runs/37997030056): SUCCESS** (10 tests).
- **[Cuatro brazos riesgo/costes preflight #37997030027](https://github.com/mezas3238-hue/qore-core/actions/runs/37997030027): SUCCESS**, política únicamente; no es un replay.
- **[Canonical QDLE ledger #37997030020](https://github.com/mezas3238-hue/qore-core/actions/runs/37997030020): SUCCESS**.
- CI integrada GEN-C1/C2/C3 y puente soberano pasó tras corregir las expectativas antiguas del handicap `THREE_SETTLED_LOSSES_HAIR_CUT`. Persisten **FAIL** en `Zero Open Work Gate` y `Legacy Stack Quarantine`, prohibido certificar Core entero.
- PR **#746** recibió código migrado desde `QDLE(research_paper_mode=True)` a `PaperQDLE`, conservando los 3368 expedientes y formato separado de `PAPER_UNASSESSABLE`. Su test independiente es draft **PR #749**; revisar estado PASS exact-SHA y reconciliar conflictos de merge antes de declararlo integrado.

### Lo que impide afirmar "listo para los cuatro replays financieros"
1. Datos **genuinos** 2019–2022 de tick/bid/ask en época M1 VT31 y todos los símbolos; no usar M5 con spread de 2026 como sustituto de esa decisión.
2. ATR14 nativo H1/H4/M15/M1 con suficiente histórico de velas cerradas, para los 3368 fingerprints; ahora existe el motor causal pero NO el paquete completo de datos.
3. USDJPY histórico as-of para GBPJPY y AUDJPY, no el screenshot 2026.
4. Tarifas y acuerdos de comisión de la cuenta real conforme período, más slippage/swap/margen/intrabar y marcas MTM para DD equity. `NDX $20` solo brazo de estrés contrafactual.
5. El runner global 3368×4 con selector Native MAX/four motors nuevos, salida parcial/trailing física y libro único, más baterías científicas y reporte anual aún requiere integrar fuentes. En particular **ningún PF/DD nuevo de los cuatro escenarios está calculado**.
6. PR #746 todavía DRAFT/conflictivo contra #745; no ejecutar dos libros competidores.

**Estado vigente**: `CANONICAL_LEDGER_AND_4ARM_CONTRACT_PRESENT_IN_INTEGRATOR / NATIVE_CAUSAL_PRIMITIVES_TESTED / REAL_3368_MANIFEST_AUDITED / HISTORICAL_BROKER_DATA_PACK_NOT_SUPPLIED / 4ARM_FINANCIAL_REPLAY_NOT_CERTIFIED / NO_LIVE / NO_VPS`.

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
  - Total **30/30** en ese SHA anterior; el SHA posterior con comisión inmediata ejecutó **31/31**, detallado debajo. No significa que todas las suites de Core estén certificadas.
- El runner de 3.368 de #745 está instrumentado para exportar `cibo-p0-canonical-paper-3368.sqlite`, SHA256 y hash de auditoría de eventos **cuando se complete un replay nuevo**. No afirmar existencia ni valores del artifact hasta inspeccionar GitHub Actions del SHA nuevo.
- El workflow histórico de 3.368 aún usa M5 y comisiones/snapshot 2026 como **escenario RESEARCH PROXY**, no datos reales 2019–22. `full_cibo_managed_drawdown_pct` continúa nulo.

### P0 adicional — techo de riesgo después de comisión de apertura (2026-10-09)

El requisito 5% también se preserva **después** de que el broker debita la comisión OPEN: si un lote `0.03` cabe justo en el NAV anterior, pero su comisión reduce inmediatamente el NAV, QDLE reduce a `0.02` si es necesario. Para PAPER, se limita el volumen por `(5% NAV - total_held_risk)/(stop_loss_usd_per_lot + all_in_costs_per_lot + 5% fee_usd_per_lot)`. Esto hace que `sum(open all-in stop risk) <= 5% NAV_after_immediate_fee` en la admisión, con la grilla física. No se tocó autorización broker/LIVE.

**CI exact-SHA [#37992942627](https://github.com/mezas3238-hue/qore-core/actions/runs/37992942627) SUCCESS** sobre `b8ba8b9938ed61d99caf78f9cd2dc2d23c4e9db9`:
- 11 pruebas PAPER (incluida comisión inmediata), OK.
- 3 pruebas sin haircut heredado, OK.
- 17 pruebas QDLE/regresión broker, OK.
- Total 31/31 en este gate. Esta métrica cuenta tests unitarios; no es certificación del mercado ni full replay.

## Estado del arbitraje e implementación cuatro escenarios

- **#745** contiene ahora la única autoridad seleccionada `PaperQDLE_V1_SINGLE_RESERVATION_BOOK` y el gate de 5% agregado probado.
- **#746** sigue DRAFT y SU código alternativo no se ha migrado/retirado; **no merge** hasta adaptar su runner a `PaperQDLE` y validar exhaustivamente diferencias de `paper_events`, `paper_unassessable` y estados. No borrar observaciones o eventos, ni fabricar conversiones de ledger.
- **#748** contiene contrato **A-X/A-Y/B-X/B-Y** (BANK 1,25% vs hasta 5%; NDX0 vs NDX20 estrés), multiplicadores ATR nativos, tests de volumen/coste y evidencia gate. La preparación pasó CI, pero **NO se han ejecutado cuatro replays completos sobre las 3.368 señales**. No confundir resultados históricos 540/246 con variantes de la nueva matriz.
- Próximos gates: migración de #746 al mismo adapter, fuentes nativas M1/H1/H4/M15 con ATR14 cerrado, USDJPY histórico por oportunidad JPY, verdaderos bid/ask/contrato/tarifa histórica y directivas Native MAX renovadas; luego una agenda global con posiciones y DD sobre equity MTM y matriz cuatro escenarios. Si falta dato exigido, `NO_RESULT_CERTIFIED` y causa, nunca proxy presentado como real.

## Límites duros

**Nunca VPS; nunca MT5 LIVE; broker fills reales = 0; ninguna comisión histórica reclamada; ninguna rentabilidad nueva demostrada; no incrementar presupuesto ni introducir filtros derivados del desenlace.** PF previo de 0,716/0,621 sigue siendo únicamente de cohortes antiguas diferentes. El PF del integrador corregido solo puede afirmarse después de comprobar nuevo artifact exact-SHA.

**Status:** `CANONICAL_LEDGER_PORTED_TO_INTEGRATOR_AND_30_TESTS_PASS / #746_ALTERNATIVE_PENDING_MIGRATION / NEW_3368_REPLAY_NOT_YET_VALIDATED / FOUR_ARM_FINANCIAL_CI_NOT_DONE / NO_LIVE`.

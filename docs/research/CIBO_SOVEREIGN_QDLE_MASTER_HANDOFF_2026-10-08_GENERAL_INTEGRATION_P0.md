
# QORE CORE — HANDOFF MAESTRO P0: CIBO SOBERANO + 4 MOTORES + QDLE + INTEGRACIÓN GENERAL

**Fecha del corte:** 2026-10-08 Paraguay / 2026-10-09 UTC.  
**Repositorio:** mezas3238-hue/qore-core.  
**Branch de publicación:** `agent/cibo-architect-3-qdle-mt5-physical-20261008`.  
**Documento de continuidad CANÓNICO de integración general:** `docs/research/CIBO_SOVEREIGN_QDLE_MASTER_HANDOFF_2026-10-08_GENERAL_INTEGRATION_P0.md`.  
**PR QDLE:** #741 DRAFT; **PR económico:** #744 DRAFT; **PR original:** #735 DRAFT.  
**SEMAFORO:** MÓDULOS AISLADOS PROBADOS; **INTEGRACIÓN REAL CIBO→MOTORES→QDLE PENDIENTE**, CI GLOBAL RED, `financial_certification=REJECTED`, NO LIVE, NO VPS, NO ORDER_SEND.

> **ORDEN P0 DEL PROPIETARIO AL SIGUIENTE ARQUITECTO:** La siguiente misión ya no es demostrar que QDLE calcula un lote aislado. Debes **RESOLVER LA INTEGRACIÓN GENERAL**: unir director cognitivo CIBO, cuatro motores económicos, tesorería Bank/Medium/Attack, QDLE y gateway en una cadena de señales, posiciones, gestión, fondos y salidas; reparar CI global; hacer un replay genuino, causal y financiero de la misma política que usa CIBO. No declarar trabajo terminado ni resultados de rentabilidad con mocks o módulos independientes.

---

## 1. Estado GitHub verificado ANTES DE PUBLICAR EL HANDOFF

| Equipo | Rama | HEAD de código leído |
|---|---|---|
| A1 director CIBO, Issue #737 | `agent/cibo-architect-1-cognitive-trade-ops-20261008` | `019275d2dc364671a5cd50556aa1e33a3c6709c3` |
| A2 motores económicos, Issue #738, PR #744 | `agent/cibo-architect-2-four-economic-motors-20261008` | `3ee510da076436d31982d98e9c7670888df48dca` |
| A3 lotaje QDLE, Issue #739, PR #741 | `agent/cibo-architect-3-qdle-mt5-physical-20261008` | `9854f169380517ddc95753bd689b0d3b8b0567ea` |
| Research causal CIBO | `agent/cibo-causal-expectation-leakage-fix-001` | `c035f68d093d6123caa4187f70279a04d03ad7d4` |
| PR #735 QDLE original | head `df10bf9d3def78a69c02dfc1292de49a0027529f` | base rama research CIBO; DRAFT |
| PR #744 A2 | head `3ee510da076436d31982d98e9c7670888df48dca` | base `agent/qdle-independent-engine-p0-20261008-001`; DRAFT |
| PR #741 A3 | head `9854f169380517ddc95753bd689b0d3b8b0567ea` | base `agent/qdle-independent-engine-p0-20261008-001`; DRAFT |

**Importante:** La HEAD de A3 AVANZARÁ cuando se cree este documento y el puntero de continuidad. Las cifras de arriba son la fotografía verificada PREHANDOFF. Releer HEAD antes de fusionar; no usar dos bases de PR como si fueran la misma. No hacer force-push ni cherry-pick ciego.

**Enlaces de coordinación:** [#737 CIBO](https://github.com/mezas3238-hue/qore-core/issues/737), [#738 motores](https://github.com/mezas3238-hue/qore-core/issues/738), [#739 QDLE](https://github.com/mezas3238-hue/qore-core/issues/739), [PR #735](https://github.com/mezas3238-hue/qore-core/pull/735), [PR #741](https://github.com/mezas3238-hue/qore-core/pull/741), [PR #744](https://github.com/mezas3238-hue/qore-core/pull/744).

### Documentos de lectura obligatoria para el sucesor

- [Handoff original, tres arquitectos](QORE_CIBO_THREE_ARCHITECT_MASTER_HANDOFF_2026-10-08.md).
- [Contrato formal CIBO→motores→QDLE](QDLE_CIBO_SOVEREIGN_FORMAL_AUTHORITY_CONTRACT_P0_2026-10-08.md).
- [A1 Director cognitivo](CIBO_ARCHITECT_1_CAUSAL_TRADE_OPS_P0_2026-10-08.md).
- [A2 Cuatro motores económicos](CIBO_ARCHITECT_2_FOUR_MOTOR_SHADOW_IMPLEMENTATION_2026-10-08.md).
- [A3 Trabajos de física, fees, tests y replay](QDLE_ARCHITECT_3_EXECUTION_HANDOFF_2026-10-08.md).
- [Handoff del motor QDLE anterior y hallazgos H8](QDLE_P0_MASTER_CONTINUITY_HANDOFF_2026-10-08.md).
- [Contrato comisión OPEN efectivamente debitada](QDLE_P0_OPENING_COMMISSION_BROKER_DEBIT_CONTRACT_2026-10-08.md), elaborado por A1 en su rama: verificar existencia al reconciliar ramas.

---

## 2. Principios INNEGOCIABLES y diagrama de autoridad

`Trader -> señal (ID, símbolo, BUY/SELL, entry, stop inicial, TP, tiempo)`  
`CIBO Soberano -> dirección cognitiva, política de vida, presupuestos y autorizaciones`  
`CIBO Compuesto -> capital QORE realizado/conciliado; Sizing -> límite riesgo USD`  
`Portafolio Compuesto -> asignación de fondos por Trader/fuente/correlación`  
`Adaptive Leverage -> margen y máximo volumen real autorizado`  
`QDLE -> único cálculo y reserva ATÓMICA de LOTES físicos, SL+fees+buffer+margen/grid`  
`Gateway del Trader + QORE Risk + FundedNext -> order_check y envío SOLO autorizado`  
`MT5 deal/fill -> comisión OPEN real -> gestión CIBO -> parcial/trailing/SL/exit -> CLOSE fee real -> cashflow reconciliado -> nuevo NAV/5%.`

**No son tres bots separados ni modos excluyentes:** BANK, MEDIUM y ATTACK son asignaciones económicas/estilos que pueden coexistir según CIBO. No imponer presets arbitrarios de SL, riesgo 0,5/1,5/3%, ATR, DD 5/10% o número de Traders por saldo copiando analogías de Scherman: cualquier regla debe ser una política propia razonada de CIBO y validada OOS. Los Traders generan señales y ejecutan vía gateway; CIBO administra y dirige la vida de la posición. Shared suministra razón/contexto cognitivo superior, pero no puede saltar los controles.

**Responsabilidades únicas:** CIBO Compuesto actualiza NAV propio solo con operaciones/fees realizados y conciliados, incluyendo pérdidas; Portafolio Compuesto asigna capital de trabajo Bank/Medium/Attack y exposición; Sizing calcula riesgo permitido en USD, no volumen final; Adaptive Leverage calcula capacidad margin/lote techo; **QDLE es el ÚNICO que cuantiza lotaje real**. QDLE NO selecciona operaciones, no inventa asignaciones, no modifica SL/TP estratégico, no cobra comisiones de broker que no constan en deals y NO manda `order_send`. Si se financia 0.01 lot, se registra capacidad. Si no se financia, se registra la señal y `UNFUNDABLE` con motivo: no convertir señal recibida en orden/fill falso ni forzar lote 0.01. No confundir "CIBO gestiona TODAS las entradas" con "el broker ejecuta físicamente todas".

### Dos capitales y regla dinámica 5%

- **QORE propio:** USD60 iniciales, variable con NAV económico conciliado. Máxima pérdida planificada por nueva señal `5% × NAV_QORE_actual`; al iniciar USD3, NAV100→USD5, NAV40→USD2. 5% es techo, NO cuota a consumir. Pérdida flotante y riesgo agregado pueden limitar más; no reinvertir ganancias flotantes no liquidadas.
- **FundedNext MT5:** USD2000 nominales de la cuenta de investigación como base BROKER/MARGEN, pendientes de verificación de saldo y reglas actuales, NO capital QORE para 5%. No dividir por USD2000 para autorizar riesgo QORE.
- **Cálculo QDLE:** `stop_loss_usd_per_lot = abs(order_calc_profit(side, 1 lote, entry, stop))` con contrato y conversión verdaderos; `cost_per_lot = SL + comisión OPEN esperada + comisión CLOSE esperada + buffer spread/slippage/overnight cuando proceda`; `risk_usd = min(0.05*NAV_QORE, autorización CIBO, cap Sizing, cap compuesto, fondo no reservado, QORE risk restante)`. Convertir por división a lotes y cuantizar hacia ABAJO en rejilla MT5. Aplicar por separado limite broker, máximo Adaptive Leverage y margen disponible / margen por lote, proveedor y posiciones existentes. No comparar USD de margen con USD de pérdida al SL ni sumar cuatro presupuestos de 5%.
- **EURUSD ejemplo estricto:** 10 pips = $100 stop por lote, $7 OPEN + $7 CLOSE = $14 por lote (supuesto de ensayo); con NAV $60 riesgo máximo $3: `floor(3/114, 0.01) = 0.02 lote`; $2 stop + $0.28 fees = **$2.28** total. 0.03 lote arriesga $3.42 y no cabe. $14 no es tarifa verificada multiinstrumento.
- **Comisión reservada NO es comisión COBRADA:** fee de apertura se debita según deal real MT5 por lotes parciales, idempotente, con moneda y timestamp; CLOSE real por operación, swaps/spread/slippage y NAV QORE correctos; evitar contabilizar el total reservado como efectivo pagado y volver a cobrarlo después.

---

## 3. Trabajos ejecutados, por arquitecto: probado vs aún pendiente

### A1 CIBO cognitivo

Hecho: `src/qore/infrastructure/cibo_trade_ops_director.py`, contrato para proponer gestión/razón de operaciones, pruebas sintéticas incluyendo 3368 IDs ficticios, **17 pruebas locales**; [run A1 #37859298325 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/37859298325), código `019275d2dc364671a5cd50556aa1e33a3c6709c3`. El módulo no determina lotaje físico ni tiene order_send. A1 trasladó valoración contrato, lotaje, swaps, comisión física MT5, tick/pip y broker checks a A3.

Pendiente: conectar realmente Shared/sensores cognitivos/Trader Manager, no solo hacer interface SHADOW. Exportar **la secuencia causal por señal** de razonamiento/admisión/SL/TP/cambios de stop, trailing, parciales, reversión, salida y resultado; persistencia durable, temporalidad y evidencia por operación. A1 NO ha aportado dataset genuino 3368 decisiones completas a QDLE. No se ha probado cerebro CIBO operando las 3368 con gestión física y cuatro decisiones monetarias.

### A2 Cuatro motores + shadow compound

Hecho: motores nativos `propose_p0_sizing_vote`, `propose_p0_compound_vote`, `propose_p0_adaptive_leverage_vote`, `propose_p0_portfolio_vote` en `cibo_account_sizing_authority.py`, `cibo_compound_capital.py`, `cibo_marginal_leverage_utility.py`, `cibo_core_compound_portfolio.py`. También `cibo_four_motor_policy.py`, `cibo_four_motor_qdle_proposal.py` y `cibo_four_motor_ablation.py`, evidencias causales, campos de límites específicos, firmas individuales de productor en pruebas, cinco brazos de capacidad shadow y testing de casos bloqueantes. Modules GEN-C1 ledger, GEN-C2 capital protected, GEN-C3 portfolio, GEN-C5 compounding, GEN-C6 internal capital market, CMA y CE2I probados en HEAD A2. [CI motores #37862455663 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455663), HEAD `3ee510da...`.

Pendiente: asignaciones causales reales Bank/Medium/Attack emitidas por CIBO, fondos por Trader, transferencias de banco/colchón justificadas, riesgo agregado y correlación, manejo de reservas/floating loss, 4 firmas reales con 4 secrets separados, reloj/identity coherente, ablations de PNL con misma secuencia. Los límites de ensayo A2 (15% stops agregado, 7.5% cluster, 10% Trader, 80% margin, 3 pérdidas consecutivas) son candidatos INVESTIGACIÓN, no regla soberana automática ni licencia para sobrepasar los 5% por entrada. **No son 4 veces 5% que se suman**.

### A3 QDLE + broker + replay

Hecho: `qore_dynamic_lot_engine.py` transacciones SQLite/atomic reservations, stale epoch, identidad, límites físicos; `cibo_physical_lot_sizing.py` cálculo USD→lotes; `qdle_cibo_bridge.py`, `qdle_cibo_authority.py` instrucciones CIBO y recibo `CiboLotageAuditReceipt`, `cibo_four_motor_qdle_proposal.py`, gateway no-send, fee schedule `covers_open_and_close`, parciales/restart/deals idempotentes en tests. Tests nav60/100/150/200/300/500/1000 y distintos stops Bank/Medium/Attack, tarifas símbolo específicas, min lot, margin, no target forzado. [CI A3 #37869646486 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/37869646486): **126 unittest + 3 gateway pytest**, exact SHA `dd77d0b2f05e1d5f4f7c0e67c148ae2dbc60912a`.

A3 hizo puente opcional `scripts/qdle_3368_dual_ledger_replay.py --motor-policy independent_four_motors --cibo-instructions PATH`: exige 3368 IDs completos y sin duplicar, fondos SOVEREIGN_BANK y PORTFOLIO_CUSHION iniciales y transferencias respaldadas, CIBO risk/autorización fuente, cierre gestionado cuando hay riesgo positivo; audita `decisions[].cibo_qdle_audit`, lotaje, comisiones OPEN/CLOSE y evento. Esto es base de integración pero el verdadero **upstream CIBO aún NO lo alimenta**.

[CI A3 obediencia #37869785409 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/37869785409): 3368 señales auténticas como IDs sellados, pero políticas CIBO **EXPRESAMENTE SINTÉTICAS**: con autorización 0 -> 0 operaciones, NAV60, Bank30/Cushion30; con una sola autorización EURUSD -> 1 operación hipotética 0.01 lot, OPEN fee $0.07, CLOSE fee $0.07, cierre ficticio +1R, NAV simulada $60.95 y Bank30/Cushion30.95. Demuestra "QDLE no se autofinancia y cumple CIBO", **no simula 3368 decisiones cognitivas CIBO genuinas**. 0 operaciones reales MT5.

[Replay A3 research #37869941748 GREEN técnicamente](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941748), SHA de código `9854f169...`, mantiene `financial_certification=REJECTED`. Otro experimento con cuatro votos económicos generados de cashbook simulado, SIN CIBO genuino, en 3368 señales produjo 329 financiables / 3039 no financiables, NAV simulado $60→$9.032083, DD de capital cerrado 87.299%, PF proxy~0.7405, con FX 7+7 y NDX $20/lote asumido. **Estos $9 NO SON el resultado de CIBO + QDLE**; no compararlos directamente a ganancias históricas CIBO. No usar provider trailing hipotético como regla FundedNext ni llamar al replay "operaciones ejecutadas".

Pendiente A3: fichas actuales reales de MT5/FundedNext para AUDJPY/EURUSD/GBPJPY/GBPUSD/NAS100 o NDX100/XAUUSD; comisión OPEN real por deal, CLOSE real, swap, spread, fórmula de XAU y fee NDX desconocida, quote/tick_value_loss, contrato divisas JPY→USD, volume_min/max/step/limit, margin, provider floors, order_calc_profit/margin/check, fills parciales y lifecycle reconciliados en broker. Sin acceso/credenciales verificados, no suponer vivo VPS. La aprobación LIVE sigue DRAFT/NO LIVE.

---

## 4. Diagnóstico de fallos reales: por qué no funciona integración general

### P0.1 Ausencia de CIBO completo en la ruta real
El **mayor bloqueo**. A1 produce contrato SHADOW, A2 cuatro outputs SHADOW, A3 lotaje para inputs. No existe la cadena causal CIBO→4 productores→QDLE→posición/ciclo/exit→NAV basada en **las decisiones auténticas de CIBO por las 3368 señales**. La ejecución independiente de A3 en `independent_four_motors` sin `--cibo-instructions` sólo usa topes generados por un modelo de investigación y no respeta la estrategia completa. **No sustituir con entrada fija de banco ni inventar salida estructural de Trader**. Probar integración con contrafactuales idénticos pero no afirmar PnL hasta upstream real.

### P0.2 Branch drift entre A2 y A3: fallos de código ya resueltos en otra rama
En HEAD A3 se importaron COPIAS de módulos de A2 antes de sus últimas correcciones; no hubo merge canónico. [CE2I A3 FAIL #37869941777](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941777): `mypy` acusa `by_factor` definido dos veces en `cibo_ce2i_advanced_capital_tools.py` (~líneas 512 y 577); fue corregido en HEAD A2 (ver [#37862455706 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455706)). [GEN-C5 A3 FAIL #37869941775](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941775): `ruff F401` por import `GENC5_SHADOW_POLICY_FROZEN_AT` no usado en `cibo_sequential_compounding_shadow_store.py`; fue corregido en A2 (ver [#37862455715 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455715)). **Integrador debe traer diffs A2 correctos preservando código A3**, no parchear dos símbolos y asumir fusionado.

### P0.3 Legacy Stack Quarantine ROJO
[A3 #37869941819](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941819) y [A1 #37859298310](https://github.com/mezas3238-hue/qore-core/actions/runs/37859298310): test `test_cibo_legacy_stack_quarantine.py::test_legacy_stack_is_quarantined_from_current_runtime` falla `productive_runtime_import_detected=True`. Casos señalados: `cibo_native_max_cognitive_episode.py` consume `cibo_cognitive_*`, `cibo_native_maximum_intelligence.py` consume `cibo_executive_brain`, `cibo_reasoned_sovereign_capital_runtime.py` legacy, etc. A1 y arquitecto integrador deben remplazar consumidores productivos con versión canónica sin romper facultades cognitivas. **No apagar test/allowlist, no engañar detector AST renombrando imports**.

### P0.4 Zero Open Work Gate ROJO
[A3 #37869941833](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941833), [A2 #37862455707](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455707): informes STRICT y PRE_EXAM generados pero assertion de cierre falla. En JSON de log STRICT estaban abiertos `FRESH_OOS`, `FINAL_INTEGRATED_CIBO_EXAM` y `WORLD_CUP_MAXIMUM_CAPABILITY_EXAM`; PRE_EXAM conserva `FRESH_OOS`. Se detecta lista extensa `orphan_candidate_paths` en scripts/modules/tests CIBO. Analizar artefactos reales, categorizar orphans, resolver dependencias y justificar cada cierre; NO cambiar `pass=true` a mano ni borrar tareas deliberadamente.

### P0.5 OOS/Phase20/Fresh source bloqueado
[A2 Phase20 #37862455708 FAIL](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455708): tres errores en collection con `CiboCapitalManagementError: V2 candidate overlaps confirmed burn` desde `cibo_phase22_holdout_v2_source_receipt.py`. El sistema está protegiendo contra reutilizar muestra quemada: se necesita fuente OOS independiente y receipt de procedencia. **No relajar ni desactivar ese control.**

### P0.6 Riesgo/costes/financiación en datos históricos NO certificados
Antigua curva de CIBO alrededor de **$670,926 y DD35.24%** fue **invalidada/no certificada por H8** (banco negativo, funding físico/loss leak). Otro research observó 272 pérdidas simuladas >5% del NAV de entrada, 777 >stop reservado y 306 NDX con fees desconocidas tratadas como 0, **en diferente política/escenario histórico**: investigar causas, NO copiar estos contadores como métricas del replay actual. La ruta A3 con 329 operaciones hipotéticas no reproduce la gestión CIBO. La discrepancia de 3368 entradas vs operaciones financiables/ejecutadas requiere **contabilidad de SIGNAL, APPROVED, UNFUNDABLE, SENT, PARTIAL, FILLED, CLOSED** por ID; no presumir 3368 fills. DD de NAV cerrado no representa DD intratrade (MTM, gaps, provider trailing).

### P0.7 Débito real apertura por deal vs reserva previa
El contrato A1 exige `QDLE_BROKER_OPEN_FEE_RECEIPT` con `deal_id`, hora, lotes parcial filled, comisión/moneda/conversión USD, monto debitado, QORE NAV antes/después y sello; `open_fee_estimate`, `exit_fee_reserve`, `actual_open_fee`, `actual_close_fee` en campos diferentes y durable. QDLE ya puede reservar ida/vuelta de la comisión y simular OPEN/CLOSE, pero **no existe aún certificación de cobros reales de MT5**. No contarlos por duplicado al settlement/restart. Leer datos broker actual (solo lectura) y autenticar proveedor. No inferir cuota XAU o NDX si no demostrada.

---

## 5. Contrato operativo que el siguiente integrador debe conectar

**Mínimo de un evento de señal por oportunidad (todo causal)**:  
`signal_id, strategy/trader, account_sequence, observed_at, provenance hash; entry/side/stop/TP originales de Trader; CIBO_reason + source_lane Bank/Cushion + allocated_working_capital_usd + authorized_all_in_risk_usd + source_receipt; four votes Sizing USD risk, Compound USD risk/NAV, Portfolio USD capital, Leverage lot/margin ceiling + individual signer receipt; broker order_calc_profit_stop_usd_per_lot, broker margin_per_lot_usd, fee_OPEN_reserve, fee_CLOSE_reserve, buffer, grid min/max/step/limit + quote_as_of; QDLE quote lots/stop/cost/margin/unfundable reasons; gateway SEND/PARTIAL/FILL/REJECT receipts (or NULL); CIBO management moves/partial/exit by timestamp; broker open/close deals and fees REAL when available; realized NAV and open reserve updates.`

Ruta existente: `scripts/qdle_3368_dual_ledger_replay.py --manifest MANIFEST --motor-policy independent_four_motors --cibo-instructions CIBO_RESEARCH_CAUSAL_JSON --min-policy broker_grid --ndx-roundtrip-fee-proxy-usd-per-lot 20 --provider-trailing-usd disabled --swap-proxy off --output REPORT`. El último NDX fee es **sensibilidad sintética declarada, NO comisión FundedNext**; `provider-trailing-usd disabled` significa proveedor NO modelado; `swap-proxy off` significa swap omitido. NO CERTIFICAR con estas opciones.

Formato `qore.cibo.qdle-authoritative-economic-input.v1`: `initial_bank_usd + initial_cushion_usd = USD60` al arranque si esa distribución es la de CIBO; `capital_transfers[]` con fuente/destino/as_of/monto y evidence_sha256; `instructions[]` conteniendo **exactamente los 3368 IDs** originales, Trader/símbolo/BUY SELL/entry/stop/source/allocated_source_funds_usd/authorized_all_in_risk_usd/maximum_requested_lots/sequence/issued_at/evidence; `managed_settlement_receipts[]` para toda señal con autorización positiva con exit_at, R outcome y evidence. Una sola cifra final R no puede reemplazar un ledger real de trailing/partials si CIBO intervino varias veces; completar eventos de gestión en fase de integración. No inventar SHA con etiquetas de fake para aparentar recibos reales.

### Reproducción de fuentes exactas
` .github/workflows/qdle-3368-dual-capital-replay.yml ` y `.github/workflows/qdle-cibo-authority-negative-control.yml` recuperan GitHub artifact de dataset pinned **ID 11451743578**, zip SHA256 `d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`, archivo `walk-forward-manifest.json`, 3368 señales únicas. Dataset 2019–2022 con economics/screenshot 2026 no equivale automáticamente a replay live del broker. No fabricar fills/MT5 deals.

---

## 6. Plan de trabajo OBLIGATORIO al siguiente arquitecto integrador

### FASE 0 — Reconciliar ownership, commits y CI global (P0 inmediato)
1. Leer este documento + 6 documentos enlazados, ramas A1/A2/A3, PR #735/#741/#744. Verificar HEAD exactos y ancestro común, diff per file, conflictos; construir rama INTEGRACIÓN propia, no sobreescribir ramas propietarias. Escoger A1 dueño cognitiva, A2 dueño productores monetarios, A3 dueño broker/lotes/gateway.
2. Incorporar fixes canónicos de A2 a rama integrada; eliminar incoherencias del copy de A2 en A3 sin perder contratos QDLE; correr CE2I y GEN-C5 + suites unitarias A1/A2/A3.
3. Reparar Legacy Stack Quarantine con tests de comportamiento equivalentes, Zero Open inventario orphan/workstreams reales; no silenciar gates. Resolver OOS Phase20 únicamente con nuevo dataset no contaminado, no relajar burn detector. Priorizar saneamiento que bloquea la integración.

### FASE 1 — Completar productor CIBO real y cuatro votos causales (BLOQUEO CENTRAL)
4. A1 implementar stream durable de *toda* señal Trader y CIBO: evaluación cognitiva/regimen/Shared, dirección, permiso de gestión, stop inicial, cambios, parciales y salida; máximo todos los 3368 IDs con identidad original, tiempos y motivos (si faltan datos, marcar NO_EVIDENCE explícito).
5. A2 producir en cada epoch NAV-QORE reconciliado y asignación Bank/Medium/Attack/Bank-Cushion por Trader/posición, HMAC individual de cuatro motores, margen/correlación y reservas (sin techo compartido ficticio). Portafolio asigna capital de trabajo, no autorización automática de perderlo.
6. Integrador implementar una cola duradera única, no tres bots: SIGNAL -> CIBO -> 4 VOTES -> QDLE -> FUNDED/UNFUNDABLE -> simulated gateway -> partial/fill -> CIBO MANAGES -> settlement -> QORE NAV next epoch. Comprobar nonlookahead, concurrency, idempotence, no source auto-loan, no margin double spent.

### FASE 2 — Completar broker MT5 y ledger de apertura/cierre
7. A3 verificar con MT5 REAL **solo lectura** la cuenta y seis activos AUDJPY, EURUSD, GBPJPY, GBPUSD, NAS100/NDX100 y XAUUSD, valor por tick/lot, contratos, alias, fees OPEN/CLOSE, swaps, Bid/Ask, min/max/step/volume_limit, order_calc_profit/margin/check y provider floor/daily/trailing. No afirmar tarifas con screens antiguas. Cuenta QORE USD60 y broker USD2000 separados.
8. Cerrar open fee receipt por deal real, reopen/restart/partial, comisiones abiertas/cerradas, currency conversion; no inventar 0 para unknown, ni double count costo previamente reservado. Probar fail-closed cuando 0.01 lote no cabe en riesgo o margen.

### FASE 3 — REPLAY verdadero, mismo presupuesto y gestión
9. Congelar manifest de 3368 + snapshots temporales y OOS independiente. Ejecutar **idéntico** baseline CIBO con economía física, CIBO+4+QDLE, control más 4 ablations una a una, misma muestra/entry/exit/fees/provider assumptions; cotejar por ID. No usar CIBO antiguo 670k ni QDLE 9.03 como mismo baseline.
10. Reporte obligatorio: signal_count 3368, CIBO decision_count, QDLE quote_count, funded/unfundable por motivo/símbolo/Trader, send/partial/fill/close (reales solo con MT5 deal), cantidades lotes y riesgo all-in, fee apertura/cierre, swaps, gross losses, PnL net, PF, máximo DD cerrado **e intratrade**, correlación, margen, floor breaches, timeline cashbook y ganancias atribuidas por ablation (sin sumar deltas doble).
11. Identificar grandes pérdidas, episodios de DD, gaps, fees e inhabilitaciones; si el sistema es insolvente/no financiable, decirlo. Solo después fijar un nuevo techo de rendimiento realista; objetivo de investigación del propietario DD ideal 20%, tolerable hasta 25% **sin degradar un techo validado**. El techo histórico invalidado no es válido para reivindicar paridad.

### FASE 4 — Certificación y autorización LIVE SEPARADA
12. Preparar batería científica: OOS fresh de verdad, walk-forward y 3 años holdout si fuentes lo permiten, estrés slippage/spread/swap/fees, proveedor/MTM, stopout, gaps, señales y broker errores, crash/restart; reportar cualquier limitación.
13. Solo con CI **GLOBAL** verde, cuentas/feed/firmas/deals verificables, claves separadas, QORE Risk y provider presend, owner explícitamente autorizando: planificar dry-run SHADOW y revisión de VPS. Hasta entonces **PRs DRAFT, NO LIVE, NO ORDER_SEND**.

---

## 7. CI EVIDENCIADA: qué pasó y qué NO está cerrado

| Evidencia | GitHub Actions | Estado |
|---|---|---|
| Director A1 contrato | [#37859298325](https://github.com/mezas3238-hue/qore-core/actions/runs/37859298325) | PASS aislado, SHADOW |
| Cuatro motores A2 | [#37862455663](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455663) | PASS aislado, SHADOW |
| QDLE física/grids | [#37869646486](https://github.com/mezas3238-hue/qore-core/actions/runs/37869646486) | 126 unittest +3 gateway PASS |
| QDLE CIBO sintético sobre 3368 IDs | [#37869785409](https://github.com/mezas3238-hue/qore-core/actions/runs/37869785409) | PASS 0/1 financiables artificialmente, NO prueba PNL |
| Replay QDLE research HEAD A3 | [#37869941748](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941748) | PASS técnico; FINANCIAL_CERTIFICATION REJECTED |
| Legacy Quarantine A3 | [#37869941819](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941819) | **FAIL** productive_runtime_import_detected |
| Zero Open A3 | [#37869941833](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941833) | **FAIL** workstreams/orphans |
| CE2I A3 | [#37869941777](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941777) | **FAIL** duplicate by_factor |
| GEN-C5 A3 | [#37869941775](https://github.com/mezas3238-hue/qore-core/actions/runs/37869941775) | **FAIL** unused imported symbol |
| CE2I A2, GEN-C5 A2 | [#37862455706](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455706) / [#37862455715](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455715) | PASS en A2, no reconciliados en A3 |
| Phase20/holdout fuente A2 | [#37862455708](https://github.com/mezas3238-hue/qore-core/actions/runs/37862455708) | **FAIL** V2 overlaps confirmed burn |

**No falsear estas luces.** Un módulo local GREEN no significa sistema global GREEN. No clasificar las 3368 oportunidades originales como 3368 fills físicos reales, ni un DD al cierre como DD real intratrade.

---

## 8. ACEPTACIÓN OBLIGATORIA DEL SIGUIENTE TURNO

- **AC01 — Integración de ramas:** commits y diffs A1/A2/A3 reconciliados con owner y CI exact SHA; no pérdidas de fix.
- **AC02 — CIBO propietario:** 3368 IDs originales con decisiones causales/management/outcome o faltantes documentados; no "decisiones QDLE".
- **AC03 — Votos 4 motores:** cuatro outputs por señal/epoch, cada uno con cap en su unidad y firma/verificación independiente; no 4 veces 5%.
- **AC04 — Dinero real:** NAV QORE realizado dinámico, fondos Bank/Cushion segregados, comisión real OPEN/CLOSE cuando existan deals; USD2000 broker separado.
- **AC05 — Lotaje real:** QDLE solo calcula; stop+coste+buffer+risk+broker min/step/margin; no lote mínimo si no cabe y reason-code UNFUNDABLE.
- **AC06 — Operaciones y salidas:** gateway único y CIBO gestiona stops/parciales/trailing/close; ninguna operación MT5 "ejecutada" sin deal.
- **AC07 — CI general:** legacy quarantine, Zero Open y CE2I/C5 reparados correctamente; OOS clean source, no gates desactivados.
- **AC08 — Replay:** 3368 señales trazadas, comparativa homogénea, DD cerrado/MTM, PF/net/gross/fee por Trader/motor/símbolo, ablations, financiera certificada SOLO si fuentes permiten.
- **AC09 — Audit:** reproducir manifest hash, SHA de código, CI, artifacts, fuentes broker y recibos, conteo de brechas, errores/restarts/costos.
- **AC10 — Operación:** DRAFT, NO LIVE hasta dictamen completo y orden explícita del dueño; nada de trading silencioso.

**CRITERIO DE NO TERMINACIÓN:** Si solo están resueltos ejemplos EURUSD, 0/1 autorizaciones sintéticas, 329/3368 simulados, CIBO aislado o un workflow local, la integración general **NO está terminada**.

---

## 9. Próxima acción INMEDIATA del nuevo arquitecto

1. Leer este documento y handoffs A1/A2/A3. Anunciar rama de integración con HEAD de los 3.
2. Reparar **branch drift** CE2I/GEN-C5 mediante port real de A2, reproducir Quarantine y Zero Open sin desactivar nada.
3. Construir **export verdadero de órdenes CIBO** y alimentar QDLE con recibos económico-gestionados de A1/A2, sobre la misma cronología; si no hay señal de CIBO real, registrar bloqueo y reparar el productor (NO mock).
4. Hacer el replay de 3368 usando esas entradas, calcular lotes, comisiones, DD intratrade y costos según observación; documentar discrepancia 3368 propuestas vs cuántas viables, con reason codes.
5. Actualizar este handoff, issues #737/#738/#739 y PR #741 por lote: **Hallazgo → Cambio → SHA → Tests/run/artifacts → Métricas válidas y límites → Pendiente concreto**.

**Conclusión de corte:** Arquitectura definida, interfaces físicas y pruebas de obediencia implementadas; CIBO real y QDLE todavía NO trabajan integrados end-to-end, CI general tiene varias fallas y los replays financieros no están certificados. **La siguiente misión P0 es subsanar ESA INTEGRACIÓN GENERAL antes de proclamar resultados.**

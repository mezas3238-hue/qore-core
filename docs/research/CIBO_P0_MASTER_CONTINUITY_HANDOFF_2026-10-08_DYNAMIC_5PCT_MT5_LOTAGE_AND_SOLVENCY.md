# QORE CORE — HANDOFF MAESTRO CANÓNICO P0 · CIBO 5% DINÁMICO / LOTAJES MT5 / SOLVENCIA Y REPLAY

**Fecha:** 2026-10-08  
**Repositorio:** `mezas3238-hue/qore-core`  
**RAMA VIGENTE DE INVESTIGACIÓN:** `agent/cibo-p0-dynamic-equity-5pct-lotage-002`  
**Rama base histórica de CIBO:** `agent/cibo-causal-expectation-leakage-fix-001`  
**Branch previo del motor MT5:** `agent/cibo-p0-fundednext-real-mt5-lotage-financing-001`  
**Estado formal:** CÓDIGO EXPERIMENTAL + **50/50 PRUEBAS UNITARIAS/INTEGRACIÓN PASADAS**, todavía **NO CERTIFICADO broker-real**, **NO APTO PARA DESPLIEGUE LIVE**.  
**VEREDICTO DEL HANDOFF:** Continúa en esta rama, no reactives curvas antiguas como broker-executables. Este documento es el **override canónico más reciente** para el trabajo P0 económico de CIBO.

## 0. DIRECTIVA SOBERANA FINAL DEL USUARIO (PREVALECE SOBRE TODO VALOR FIJO PREVIO)

**EL RIESGO POR CADA ENTRADA NO ES USD 3 FIJOS. ES EL CINCO POR CIENTO (5%) DINÁMICO DEL CAPITAL DE LA CUENTA EN EL MOMENTO CAUSAL DE LA NUEVA ENTRADA.**  
USD 3 era solamente la representación de 5% del capital **inicial** de USD 60. NO congelar esos USD 3 conforme aumenta el capital. Si la cuenta disminuye, el 5% también disminuye.

| Capital causal de referencia | Presupuesto de riesgo 5% para nueva entrada |
|---:|---:|
| USD 60 | USD 3 |
| USD 100 | USD 5 |
| USD 200 | USD 10 |
| USD 1.000 | USD 50 |
| USD 10.000 | USD 500 |
| USD 60 después de pérdidas -> USD 40 | USD 2 |

**Cálculo por entrada:** `risk_target_usd = 0.05 * min(latest_account_equity_usd, latest_realized_balance_usd)`. El `min` evita incrementar el tamaño sobre beneficios flotantes sin liquidar, pero sí reduce riesgo inmediatamente cuando la equity cae. Balance/equity deben ser del mismo instante causal y misma cuenta, actualizados antes de autorizar cada señal. **No congelar el balance inicial ni reutilizar la equity de la operación anterior.** Esta política de base de riesgo conservadora debe revisarse con el dueño sin confundirla con el 5% nominal.

**5% es el presupuesto objetivo / máximo AL STOP, incluido coste previsto de ejecución, no una garantía de pérdida exacta.** Volumen se ajusta hacia abajo al `volume_step` legal, nunca al alza para conseguir exactamente el 5%. Si no hay lotaje financiable, la señal permanece en la auditoría, pero debe etiquetarse **NO FINANCIABLE / NO EJECUTADA**, jamás inventar fill 1x. El Trader es soberano de su señal, CIBO de su finanza; el volumen se autoriza *ANTES* del envío al MT5.

**OTROS LÍMITES ECONÓMICOS TAMBIÉN DINÁMICOS:** límites de riesgo total abierto (valor actual investigación: 15% del mismo capital causal), riesgo por símbolo (10%), Trader (10%) y grupo correlacionado (15%). Se descuentan las exposiciones abiertas, reservas y margen consumido. Los porcentajes son salvaguardas preliminares de investigación, no parámetros de una cuenta FundedNext certificados. No permitir que 4 motores gasten el mismo capital. Ninguno de los porcentajes agregados implica que tres operaciones 5% sean siempre financiables.

La anterior fase **USD 3 fijo** queda declarada **SUPERADA** como regla canónica (solo puede existir mediante `RiskPolicy(per_entry_usd=Decimal("3"))` como **cap adicional opt-in para comparación de laboratorio**, nunca producción predeterminada). **El histórico 3.071/3.368 calculables a USD 3 FIJOS NO es el resultado de 5% dinámico** y debe recomputarse.

## 1. ARQUITECTURA FINANCIERA DEFINIDA POR EL USUARIO

**Trader -> Pre-send CIBO economic coordination -> central QDLE / MT5 monetary lot calculator -> broker valid volume/margin check -> Trader sends signal order -> real MT5 receipt -> CIBO monitors and settles -> financial reconciliation**.

- **Sizing:** recibe riesgo objetivo `5% * causal account`, símbolo Core/broker, BUY/SELL, precio real, Stop Loss y valor monetario de pérdida por volumen calculado con `order_calc_profit`, comisiones + slippage. Determina lotaje teórico y el mayor paso broker válido sin superar presupuesto.
- **CIBO Compuesto (CIBO Compound):** decide dinero líquido realizado y reinvertible sin tomar ganancias flotantes como nuevas reservas. Define capacidad financiable real desde BANK en MEDIUM. Lleva generaciones y depósitos del compound sin alterar arbitrariamente risk%.
- **Portafolio Compuesto:** riesgo simultáneo por cartera/símbolo/Trader/grupo y margen reservado; coordina cushion de ATTACK, doble gasto, reservas atómicas e idempotencia. Reconcilia y libera reservas solo después de operación/acreditación verificadas.
- **Adaptive Leverage:** consulta margen real `order_calc_margin`, `margin_free`, `margin_level`, restricciones específicas de cuenta e instrumento. Leverage experimental 100/1000/10000x **no** es leverage FundedNext ni volumen real.
- **QDLE, motor único de lotaje:** servicio compartido para todos los módulos, no 4 lotajes independientes que se suman. El menor volumen que respete TODAS las autorizaciones y límites es el único volumen que el Trader puede solicitar. Tiene que estar permanentemente disponible con estado transaccional y recuperación tras reinicio antes de certificación real.

**No rechazo cognitivo de la señal por CIBO.** Una señal no financiable sigue existiendo para estadísticas/densidad del Trader, pero **no existe trade ejecutado si MT5 no confirmó su fill**. No se permite fingir volumen retroactivamente una vez ejecutada.

## 2. ACTIVOS Y FUNDAMENTOS FÍSICOS DE FUNDEDNEXT

Seis símbolos: `AUDJPY`, `EURUSD`, `GBPJPY`, `GBPUSD`, `NAS100` (nombre público de FundedNext `NDX100` que DEBE cotejarse en servidor), y `XAUUSD`.

Referencias oficiales, nunca equivalentes por sí solas a USD stop:
- Forex 1 lote=100,000 unidades de divisa base (AUD/EUR/GBP); EURUSD/GBPUSD aprox USD10 por pip y 1 lote; AUDJPY/GBPJPY aprox JPY1,000 por pip y 1 lote, convertido por tipo de cambio causal vía servidor.
- Índice NAS100/NDX100: referencia contrato 10 unidades por lote, aprox USD10 por punto/lote; **no suponer mínimo ni margen**.
- XAUUSD referencia 100 oz/lote; USD100 por USD1 de movimiento/lote; sus comisiones son % del nominal al abrir.
- Página oficial de contratos: https://help.fundednext.com/en/articles/8020350-what-is-the-contract-size-of-the-instruments
- Reglas públicas Stellar Instant: https://fundednext.com/general-rules/cfds/symbols-and-conditions (Forex 1:30, índices 1:5, commodities 1:7.5 de referencia; confirmar modalidad exacta).
- Comisiones Stellar Instant públicas: https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account (Forex USD 7 por lote al abrir según FAQ; índices 0; oro/metales 0.0016% nominal al abrir). Revisar contradicciones de páginas generales y tarifario ACTUAL de cuenta concreta.

**TODAVÍA NO EXISTE tabla REAL certificada de `volume_min/max/step`, `tick_value`, `tick_size`, contrato, comisiones y margen de los 6 símbolos del servidor MT5 de la cuenta.** El dispositivo autorizado `vps-vrix` se comprobó **OFFLINE** (último estado observado, puede cambiar). NO inventar la tabla ni certificar 3.071 ejecuciones con estos datos.

## 3. CORRECCIONES YA IMPLEMENTADAS EN LA RAMA VIGENTE

### A. Motor monetario MT5 (P0 y política 5% actualizada)
`src/qore/infrastructure/trader_lab/cibo_fundednext_mt5_lotage_p0.py`
- Recibe cliente MT5 inyectable (para mock/pruebas o cuenta autenticada). `symbol_info`, `symbol_info_tick`, `account_info`, `order_calc_profit`, `order_calc_margin` son fuente de PnL a SL y margen en divisa de cuenta USD.
- Usa Bid/Ask correcto para BUY/SELL, Stop Loss adverso, coste de apertura y slippage estimado, grid `min/step/max`, lotaje máximo compatible mediante búsqueda discreta; valida equity, margen libre, margen level, estado permitido, tick reciente/visible, y riesgo conjunto de cartera.
- Nuevos valores predeterminados **DYNAMIC 5%**: `per_entry_risk_fraction=Decimal("0.05")`, portfolio 0.15, symbol 0.10, Trader 0.10, group 0.15; `per_entry_usd=None` (NO USD3 fijo). `policy_version="stellar-instant-p0-dynamic-5pct-account-v2"`.
- Cada `Quote` emite `risk_base_usd`, `dynamic_risk_target_usd`, `effective_risk_budget_usd`, volumen, riesgo a SL, comisiones, margen antes/después, política/identificador; se debe persistir por trade en ledger real.
- `AtomicPortfolioReservations` usa RLock, trade_id único y reserva no duplicable; `source_available_usd` reduce presupuesto al líquido del wallet autorizado. Incluir cartera real reconstruida al iniciar; actualmente solo protege reservas en memoria.

### B. Cuarteto coordinado — 5% compuesto, sin congelar USD3
`src/qore/infrastructure/trader_lab/cibo_four_motor_fundednext_p0.py`
- Calcula costo/capacidad por las 4 responsabilidades: **SIZING, CIBO_COMPOUND, COMPOUND_PORTFOLIO, ADAPTIVE_LEVERAGE**.
- Corrección clave: `authorize` YA NO usa `min(self.policy.per_entry_usd,cash)` sobre USD3 fijo ni sobrescribe `per_entry_usd` como presupuesto monetario estático. Entrega `source_available_usd=cash` y deja al motor resolver `0.05 * causal risk base` antes de límites financieros. Sensor Sizing `authorized_usd` reporta el presupuesto 5% dinámico.
- Reinvierte ganancias realizadas solo después de confirmación de cierre; no ATTACK con banco soberano. Control de DD y fondos soberanos, sin relleno de volumen no permitido.
- **Default `complete_broker_positions_reconciled=False` -> `can_submit_to_broker=False`: NO APTO LIVE** hasta recuperación de TODAS las posiciones MT5, tarifas y reservas (no basta con simular ACK).

### C. Interfaz Trader/CIBO previa al envío
`src/qore/infrastructure/trader_lab/cibo_trader_presend_mt5_p0.py`
- El Trader conserva señal/dirección/precios; obtiene el lote que CIBO puede autorizar.
- `prepare_trader_order` genera **request NO enviado**, y comprobador post-ack valida deal, volumen y precio. Mismatch o slippage -> recalcular, no inventar precio/fill.
- Investigación aislada; **NO CONECTADO al gateway de órdenes real**.

### D. Probe REAL del VPS de FundedNext
`scripts/cibo_p0_mt5_specs_readonly_probe.py`: para ejecutar una vez que VPS y terminal MT5 estén conectados a la cuenta correcta. Recolecta contrato/tick/min/step/max y margen por minlot de seis símbolos, sin exponer credenciales ni enviar órdenes. Requiere verificar alias NAS100→NDX100; aún NO EJECUTADO contra cuenta.

### E. Auditoría histórica 3 años — RESULTADO OBSOLETO RESPECTO A RIESGO DINÁMICO
`scripts/cibo_p0_three_year_offline_lotage_audit.py`, workflow `.github/workflows/cibo-p0-offline-3368-fundednext-stop-risk-audit.yml`, GitHub Actions **37809999723 SUCCESS** (fuente/manifest 2019–2022, 3368 señales).
- Riesgo antiguo **USD3 ESTÁTICO**: 3.071 señales con lote teórico y 297 sin lote por mínimo/riesgo/costes del manifest histórico. Por símbolo AUDJPY 651/673; EURUSD 494/495; GBPJPY 589/618; GBPUSD 570/606; NAS100 459/484; XAUUSD 308/492.
- A USD2.95 ESTÁTICO, ~3060 calculables / 308 no. Es un **estudio offline de lotaje** que usa estimaciones de precio/costos con posible conservadurismo/doble cuenta de spread; **NO ES EL NUEVO REPLAY DE 5% dinámico**.
- **NINGUNA de esas 3071 se ha certificado como fill MT5 ni se ha recalculado PnL/capital/DD** para lote financieramente ejecutable. El siguiente arquitecto DEBE lanzar un nuevo replay causal al 5% (no reutilizar esos resultados).

### F. Tests de FundedNext y motor económico, ahora 5% dinámico
`tests/trader_lab/test_cibo_fundednext_mt5_lotage_p0.py`: pasos min/max, BUY/SELL, JPY→USD, EURUSD, GBPUSD, NAS100, XAUUSD, comisión oro variable, costes/slippage, 5% sobre cuentas USD60/100/1000, subida y bajada de equity, ganancias flotantes no aplicables, cambio por drawdown, límites agregados proporcionales.
`tests/trader_lab/test_cibo_four_motor_fundednext_p0.py`: 4 recibos económicos, banco vs cushion, no doble gasto, trade_id repetido, cierres acreditados, y NUEVAS pruebas de compuesto dinámico después de +USD1000 y -USD1000 realizados.
`tests/trader_lab/test_cibo_trader_presend_mt5_p0.py`: 7 pruebas Trader pre-send, rechazo real broker vs señal, mismatch en volumen/precio, ticket, 5% dinámico hasta gateway (no se envía orden).

**ÚLTIMA EVIDENCIA VERIFICADA (P0 V2 dinámico): GitHub Actions run [37814146300](https://github.com/mezas3238-hue/qore-core/actions/runs/37814146300), commit probado `75b27af709ac279e3db4fbe4fe178e30cb8958da`: `SUCCESS` — 43 pruebas del grupo central + 7 de gateway = **50/50 PASS**.** Una primera ejecución de la nueva suite falló por comparación de slippage entre políticas distintas; se corrigió el TEST para usar idéntico cap comparativo y la siguiente ejecución **SUCCESS**. No ocultar este diagnóstico. Workflow: `.github/workflows/cibo-p0-fundednext-mt5-lotage-solvency.yml`.

## 4. POR QUÉ EL ANTERIOR CAPITAL FUE TAN BAJO / POR QUÉ NO EXISTE AÚN GANANCIA REAL DE ESTE CAMBIO

- El CIBO previo multiplicaba 1x/2x/3x sin convertir sistemáticamente cada operación a pérdida monetaria del SL y volumen legal. P.ej. riesgo inicial en NAS100 modelo 1x ~USD0.295; objetivo real para inicio USD60 era USD3, sujeto a costos/margen.
- H27 mostró **2237/3368** entradas bajo USD3 fijo en 3 años; mes inicial 82/84, primer año 922/1109. H28 tuvo adaptador sólo investigación, H29 no consiguió cambiar el multiplicador efectivo. **Los datos no demuestran que la nueva versión del motor haya producido ganancias**.
- H21 nominal con 3368 recibos: USD60 → USD3589.26, DD34.3537%; H30 y H31 laboratorio 4-motor con 1x fallback: H30 USD2705.99 y **piso soberano violado USD74**; H31 USD2997.39, piso 0, DD34.35% y 1124 entradas que el filtro de reserva declaraba no financiables como mínimas, aunque mantenía recibos 1x. **TODOS son ledgers de investigación sin certificación broker-real.**
- Los techos extremos de hasta ~USD670k y DD ~35% son del motor legacy con multiplicadores 10000x y **NO son capital broker-ejecutable certificado**. **No borrar curva antigua**: conservar para contraste/auditoría, pero NO promocionar.
- H8 demostró posición base obligatoria USD4.5200 requeridos vs USD4.215535 disponible y banco negativo, según `docs/research/CIBO_H8_REAL_CAPITAL_SOLVENCY_BLOCKER_2026-10-08.md` + OVERRIDE en `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`.

## 5. EL NUEVO TRABAJO URGENTE (ORDEN Y GATES INNEGOCIABLES)

**P0.1 — Restaurar fuente REAL de broker:**
- Verificar VPS conectado, terminal MT5 de cuenta FundedNext Stellar Instant correcto y broker/símbolo real para seis mercados.
- Ejecutar el probe SOLO lectura, capturar `volume_min/max/step`, `tick_size/value_profit/value_loss`, precios, `order_calc_profit`, `order_calc_margin`, account equity/balance/free margin/used margin/leverage, comisiones reales. Sin credenciales en logs.
- Comprobar mapeo NAS100↔NDX100; cuando el broker no permita mínimo (sobre todo XAUUSD) marcar razón exacta no financiable.

**P0.2 — Conectar QDLE único con Trader/MT5 sin fingir fills:**
- Una reserva ATÓMICA por `trade_id`; idempotencia/reintentos, persistir en crash/restart, reconciliar TODOS los tickets vivos. Cálculo a 5% de la cuenta *en ese instante*, no riesgo fijo USD3.
- `order_check` (si disponible) + `order_send` únicamente por gateway Trader autorizado; CIBO entrega volumen antes de envío.
- Validar ejecución/volumen/precio real (partial fills, rechazo, SL parcial, comisiones, swaps, slippage). Reserva se libera al conciliar realmente, no al presumir cierre.
- Reemplazar `broker_execution_proven:bool` manual por validación de deals firmes en history/positions y control de margin stop-out.

**P0.3 — Replay 3 AÑOS EFECTIVO, 5% DINÁMICO CADA SEÑAL:**
- Fuente única causal de 3368 señales 2019-07—2022-06 con costo/tick/margen real reconstruible y posiciones simultáneas; los 6 mercados en cross-check.
- Capital inicial USD60; antes de CADA entrada calcular `risk_target_usd = .05 * min(causal_equity, realized_balance)` y lotes permitidos por SL, broker volumen grid, costes adversos, costo de margen, cartera global y reserva soberana; no ingresar ficticiamente 1x.
- Si no financiable, registrar **señal preservada, orden no ejecutada**, razón y restricciones físicas. Cuántas de las 3368 *ejecutadas* solo después de confirmación broker/replay causal, no repetir 3071.
- PnL USD real de volumen ejecutado y salida original administrada por CIBO; volumen no autoriza inventar nuevos stops/TP para embellecer profit; mark-to-market DD, comisiones, margen, stop-out, saldo/equity efectivo, reversiones parciales y exposición simultánea.
- Reportes por 1/3/6/12/36 meses, beneficio neto, bruto ganador/perdedor, PF, capital final, peor DD, bank floor breaches, recuentos signal/approved/actual fill, peligros de USD60/minlot, evidencias de cuatro motores e impactos de cada uno (ablation).
- Prueba comparativa histórica baseline + USD3 fijo como SOLO control experimental vs nueva 5% dinámica; **no aceptar ganancias como reales antes de reproducir financiación broker-equivalente**.

**P0.4 — Batería científica / certificación y objetivos:**
- Hard gate: cero fuga causal/outcome, cero cash ficticio, cero banco negativo, cero doble gasto, ninguna ejecución sin lote legal/margen, 3368/3368 señales registradas, drawdown **ideal ≤20%**, máximo tolerable **25%**, optimizar ALTURA VERDADERA del techo solo después de solvencia.
- Stress BUY/SELL, SL corto/medio/largo, USDJPY variable, NAS100/XAUUSD, 5% en equity crecida/reducida, seis activos, comisiones actuales, spread/slippage, varios Traders correlacionados, DD abrupto, duplicados, restart, MT5 caído, reject/partial fills.
- Mantener HOLDOUT sellado y comparaciones STRICT PARETO solo entre carteras broker-equivalentes, NO comparar capital ficticio 10000x frente a 5% físicamente financiado.

## 6. REGISTROS MÍNIMOS Y VALIDEZ DE ENTREGABLES

Por cada decisión se requiere: `signal_fingerprint`, Trader, core/broker symbol, fecha/hora de snapshot, balance, equity, riesgo objetivo .05*base, presupuesto autorizado finalmente, BUY/SELL, entrada bid/ask, SL/TP, stop risk por lote desde MT5, theoretical lots, broker min/max/step, legal lots, fees/spread/slip, margin requerida y libre antes/después, exposición global/agrupada, las cuatro `MotorDecision`, reserva, número de ticket MT5/deal, volumen realmente ejecutado, comisión efectiva, salida y capital realizado, delta PnL esperado/real y estado `NO_FINANCIABLE | ENVIADA | RECHAZADA | PARCIAL | EJECUTADA | CERRADA`.

**Estados de entregables:** A motor central implementado como investigación; B 6 fichas MT5 real PENDIENTE (VPS offline); C coordinación cuarteto implementada en investigación (aún sin runtime del Trader); D **50 pruebas automatizadas PASS**; E replay económico después de 5% **NO ejecutado**; F reporte detallado del modelo USD3 fijo existe, **NO válido para 5% dinámico**; G nueva ganancia/PnL/DD **NO demostrado**; H handoff maestro presente.

**Ni CI SUCCESS ni 3368 señales auditadas significan 3368 trades financiados, ni ganancias verdaderas, ni rendimiento certificado.** FundedNext usa cuenta financiada simulada/virtual según sus términos; hablar con precisión de lotes MT5 admitidos sin garantizar resultado real.

## 7. COMANDO / UBICACIONES PARA EL SIGUIENTE ARQUITECTO

```text
Repository: mezas3238-hue/qore-core
Current experimental branch: agent/cibo-p0-dynamic-equity-5pct-lotage-002
Read FIRST: docs/research/CIBO_P0_MASTER_CONTINUITY_HANDOFF_2026-10-08_DYNAMIC_5PCT_MT5_LOTAGE_AND_SOLVENCY.md
Prior P0 handoff (historical, fixed-dollar policy superseded): docs/research/CIBO_P0_FUNDEDNEXT_MT5_REAL_LOTAGE_MASTER_HANDOFF_2026-10-08.md
Canonical old ceiling+H8 solvency warning: docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md
H8: docs/research/CIBO_H8_REAL_CAPITAL_SOLVENCY_BLOCKER_2026-10-08.md
Test gate: https://github.com/mezas3238-hue/qore-core/actions/runs/37814146300 (SUCCESS, 50 tests)
Static-only 3yr diagnostic: https://github.com/mezas3238-hue/qore-core/actions/runs/37809999723 (SUCCESS input audit, NOT 5% replay)
Immediate task: REAL MT5 symbol/account specs -> broker-history position/transaction reconciliation -> 3368-signal 5%-dynamic causal full replay -> risk/funding/PnL/DD audit -> repair/replay loop.
```

**DECISIÓN VIGENTE:** preserva la autoridad Trader + CIBO, 5% dinámico, cuatro motores colaborando con libro único y motor lotaje MT5, el trabajo previo y el H8; **NO desplegar variante research, NO aceptar USD3 fijo ni curvas 10000x como ejecutables.** Trabajar → implementar → probar → diagnosticar → reparar → volver a replay. 

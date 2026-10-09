# P0 — QDLE: revisión por instrumento de comisiones, valor tick/pip y recotización causal de las 3.368 señales
**2026-10-09 · PR [#745](https://github.com/mezas3238-hue/qore-core/pull/745) · Branch `agent/cibo-sovereign-integration-p0-20261008` · estado: INVALIDACIÓN DE CERTIFICACIÓN ECONÓMICA, hipótesis y ensayo controlado de sensibilidad; NO broker-LIVE**

## 1. Dictamen reproducible: qué sucedió, qué NO
Replay [#37937821428](https://github.com/mezas3238-hue/qore-core/actions/runs/37937821428) (SUCCESS), reporte `QDLE_3368_REPORT_SUMMARY`: 3368 instrucciones originales de CIBO Soberano Native MAX, 1961 QDLE lotes positivos, 1407 sin lote; cero fills y por tanto cero comisiones **pagadas** y NAV no modificado. **Esto NO implica que QDLE omitiera comisiones en el *dimensionamiento*.** En `scripts/qdle_3368_dual_ledger_replay.py` se calculan `fee` por símbolo y se proporcionan al motor QDLE mediante `QDLESymbol.fee_usd_per_lot` para FX/NDX o `QDLEIntent.slippage_usd_per_lot` para XAU; en `src/qore/infrastructure/qore_dynamic_lot_engine.py` el riesgo incluye `stop_loss_per_lot_usd + provider_cost_usd_per_lot`. **Pero estas tarifas contienen hipótesis no verificadas**, por lo cual `1961` no son entradas financieramente certificadas en la cuenta FundedNext ni una métrica segura para LIVE.

**Error material demostrado:** el workflow `.github/workflows/cibo-p0-native-max-manager-qdle-3368.yml` invoca **`--ndx-roundtrip-fee-proxy-usd-per-lot 20`** en ambos brazos. La documentación anterior decía NDX **sin comisión visible**, no `0 confirmado`; el CEO comunica que es 0. Reconciliar con evidencia account-specific antes de afirmar tarifa real. Recalcular la sensibilidad NDX = 0 como escenario de la afirmación del usuario, *sin* cambiar a ciegas el gateway LIVE ni registrar cero como `BROKER_ROUND_TRIP_VERIFIED`.

## 2. Matriz provisional de precios y tarifas — separar declaraciones de pruebas
| Activo canónico | Contrato/valor declarados | Tarifa solicitada por CEO | Lo que actualmente ejecuta el replay | Criterio para certificar |
|---|---|---|---|---|
| EURUSD | 100.000 USD nocional base/lote; 1 pip=0,0001 → USD10/pip/lote | USD7 OPEN + USD7 CLOSE | USD14 roundtrip/lote | Contrato de comisión por cara en la cuenta y timestamp, deals históricos, spread |
| GBPUSD | 100.000/lote; USD10/pip/lote | USD7 + USD7 | USD14 roundtrip/lote | Igual |
| GBPJPY | 100.000 GBP/lote; 1 pip=0,01 JPY → **1000 JPY/pip/lote**, USD variable | USD7 + USD7 | USD14/lote y `stop_loss_per_volume` USD obtenido del manifiesto, no de USDJPY histórico MT5 validado | USDJPY causal de conversión, `order_calc_profit` para comparar y lado ejecutable |
| AUDJPY | 100.000 AUD/lote; 1000 JPY/pip/lote, USD variable | USD7 + USD7 | Igual que GBPJPY | Igual |
| XAUUSD | contrato 100 oz/lote; tick=0,01 USD → USD1/tick/lote | 0,0016 % del nocional por tramo **según interpretación provisional** | `entry * 100 * 0.000016 * 2` USD/lote roundtrip, con base de tarifa/tramo NO verificada | Confirmar si base 0,0016% = precio, nocional, comisión por lado o total, mínimo, currency; deal OPEN y CLOSE |
| NDX100/alias NAS100 | contrato mostrado 10 USD por punto/lote; tick 0,01 → USD0,10/tick/lote; **NO** USD10/tick de 0,01 | USD0 comisión declarado por CEO | USD20 roundtrip/lote, parámetro explícito **arbitrario de sensibilidad** | Historial real con comisión, fees, contrato/alias y documento de tarifa de cuenta |

**Los precios y contratos extraídos de capturas MT5 octubre 2026 no son metadatos históricos verificados de 2019–2022.** Si MT5 actual devuelve un tick-value distinto, privilegiar los metadatos observados y volver a documentar el cálculo.

## 3. APIs MT5 correctas; prohibido inventar propiedades
- `SYMBOL_COMMISSION` **no es un identificador estándar listado en el enum `ENUM_SYMBOL_INFO_DOUBLE`** y no existe propiedad universal `symbol_info().commission` de Python MT5. No programar `SymbolInfoDouble(SYMBOL_COMMISSION)` como requisito porque fallará o sería dependencia no estándar de un proveedor. Referencias: https://www.mql5.com/en/docs/marketinformation/symbolinfodouble y https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py
- Lectura de microestructura: `mt5.symbol_info(symbol)` → `trade_contract_size`, `trade_tick_size`, `trade_tick_value_profit`, `trade_tick_value_loss`, `volume_min/max/step`, `currency_profit`, `trade_stops_level`; `mt5.symbol_info_tick(symbol)` → BID/ASK/hora; `mt5.order_calc_profit` para P&L de SL según sentido/volumen/precio, `mt5.order_calc_margin` para margen. Snapshot con sello causal y tipo de cuenta.
- Comisiones: tarifa explícita contractual por instrumento y cuenta corroborada con `mt5.history_deals_get` (campos `commission`, `fee`, `swap` de entradas y salidas), agregación por `position_id` y lado OPEN/CLOSE; historial **solo** valida transacciones que efectivamente tuvieron lugar. Comprobar fees separados incluso cuando `commission = 0`. Donde no hubo operaciones, pedir tabla de tarifas verificable del broker; NO deducir «0» de pantalla sin cifra.
- `scripts/qdle_mt5_metadata_publisher.py` ya exige `--verified-fees` explícito; `scripts/qdle_mt5_read_only_inventory.py` marca la comisión `REQUIRES_ACCOUNT_SPECIFIC_VERIFICATION`. Esto es correcto. No alterarlo para inventar garantía LIVE.
- Spread: BUY entra ASK, cierra BID; SELL entra BID, cierra ASK. **No sumar spread una segunda vez** si P&L al stop ya utiliza precios ejecutables bid/ask. Si solo se tiene mid, modelar spread separadamente con fuente y escenario; ni usar spread=0 implícito como real.
- Swap: coste de permanencia depende de direction/símbolo, *rollover* y tasas actualizadas; para sizing de riesgo reservar buffer basado en máximo horizonte o escenario declarado; si faltan datos, `UNKNOWN_COST`/sensibilidad en vez de coste histórico 0 verificado.

## 4. Fórmula de lotaje requerida (sin doble comisión ni falsa certeza)
```text
gross_stop_loss_USD_per_lot =
    abs(order_calc_profit(account, symbol, side, 1.0 lot, executable_entry, executable_stop))
    OR verified contract/tick-value conversion for the same side + epoch

open_commission_USD_per_lot   = tariff.open(symbol, account, entry_notional, at)
close_commission_USD_per_lot  = tariff.close(symbol, account, stop_notional, at)
other_buffer_USD_per_lot     = expected adverse slippage + gap reserve + extra fees +
                               defensible swap reserve (no double-count spread)
all_in_stop_USD_per_lot      = gross_stop_loss + open_commission + close_commission + other_buffer
mode_budget_USD             = current reconciled QORE_NAV × native_mode_fraction
effective_budget_USD        = min(mode_budget, source_available, four motor *valid* caps,
                                  portfolio concurrent risk capacity, sovereign 5% NAV)
raw_lots                    = effective_budget_USD / all_in_stop_USD_per_lot
lots                        = FLOOR_TO_BROKER_STEP(raw_lots), bound by broker max,
                              margin/free_margin, positional limits; never round UP
if lots < broker_min_lot:   UNFUNDABLE (with exact binding reason)
reserve_risk_USD            = lots × all_in_stop_USD_per_lot
assert reserve_risk_USD <= effective_budget_USD
```
El 5% es límite soberano global por nueva intención, **no** petición obligatoria para los tres modos. Riesgo actual de modo de investigación: BANK 1,25%, MEDIUM 2,50%, ATTACK 5,00%. QORE NAV inicial USD60 → presupuesto USD0,75 / USD1,50 / USD3,00. El perfil por modo no es atribuible a distancia de SL sin auditar estos diferentes presupuestos. El motor debe también hacer `order_check` solo READ/NO-SEND si el proveedor soporta consulta sin orden, jamás `order_send` para validar experimento.

## 5. Reprocesamiento controlado y comparación de las 3.368 (entrega obligatoria)
- Congelar **mismas** 3368 señales, sellos Native MAX, 3 modos, cuenta proxy NAV $60, 4 motores y QDLE; manifest/hash, commit y parámetros identificados. Dos brazos solo difieren en `NDX roundtrip fee per lot = 20` (viejo) vs `0` (declaración del CEO sin verificación de tarifa); conservar EUR/GBP FX14, XAU 0,0016% notional por cara (hipótesis) y JPY proxy original, para obtener **delta atribuible solo a NDX**.
- Adicionalmente comparar XAU tarifas por cara frente total y 1/2 escenarios de swap/spread si hay datos confiables; no etiquetar sensibilidades como tarifa real.
- Reporte exigido por símbolo y modo: señales, lot quote >0, sin lote, volúmenes positivos agregados, riesgo al SL+fees, `commission_open_estimated_per_lot`, `commission_close_estimated_per_lot`, FX conversion timestamp/provenance, `minimum_grid_all_in_cost_usd`, `budget_usd`, `binding_constraint`, `fee_verified`; incluir **cambio de conjunto** (ganadas/perdidas) y cambio de lote por `signal_fingerprint`, sin reordenar ni omitir.
- Comparación debe afirmar `NAV/PF/DD gestionados = null`, `real_broker_fills=0` para ambos hasta que se construya motor de gestión de salidas con bid/ask y ledger.
- **No promover** número de financiables de un escenario proxy a `VALID_REAL_BROKER` aunque NDX=0 produzca mayor cantidad. Certificación requiere full tariff + spread/buffer/swap/rates contemporáneos por señal y solvencia de cartera.

## 6. Gate P0: pruebas de aceptación exigidas antes de certificar
1. EUR/GBPUSD USD14/lote roundtrip usados íntegramente en denominador; BUY y SELL y comisiones apertura/cierre por separado. Test mínimo de lote 0,01 con NAV60 por modo.
2. AUDJPY/GBPJPY `1000/ USDJPY(t)` USD/pip/lote si quote JPY/ USD, validando `order_calc_profit` de MT5 (en función de cuenta y bid/ask actual).
3. XAU100oz 0,0016% nocional con ambas patas y distintos precios notional, **pero solo** si contrato verifica la base, dirección, lado y comisiones mínimas; de lo contrario `UNVERIFIED_PERCENT_FEE`.
4. NDX fee real 0 **solo** con evidencia; comparar 0 vs 20 como sensibilidad. Diferenciar USD10/punto de USD0,10/tick de 0,01. La pantalla donde comisión NO ES VISIBLE no demuestra cero.
5. Rechazo del lote mínimo si `SL_loss+fees+buffer` no cabe, sin inventar 0,005 lote ni recortar riesgo.
6. Evitar double counting del spread/fees, no confundir `fees_cost_quote` con `fees_paid=0` y no confundir fines del escáner con fills.
7. Rechazar `BROKER_FEE_VERIFIED` sin prueba de tarifa vigente para esa cuenta; `LIVE` prohibido en tests.
8. CI, archivo JSON de 3368 por señal y tabla comparativa con `research_only`, `financial_certification=REJECTED` hasta evidencia completa.

## 7. Acciones concretas en PR #745
**P0-A:** capturar inventario MT5 read-only y tabla roundtrip por cuenta; verificar especialmente NDX y base porcentual XAU. **P0-B:** implementar servicio `SymbolCostSchedule` explícito por fuente/época con comisiones por pata y valoración cross FX, pruebas. **P0-C:** rerun idéntico 3368 para sensibilidad NDX 0/20; tratar NDX0 como `CEO_DECLARED_UNVERIFIED`; comparar deltas por símbolo/ID. **P0-D:** rerun definitivo tras evidencia tarifaria completa y spread/market path; después acoplar posición/ledger conforme a [especificación P0 de ciclo de vida](CIBO_P0_EXECUTION_MANAGED_LIFECYCLE_REPLAY_SPEC_2026-10-09.md).

**Decisión:** cifras viejas `1961` y `1407` permanecen **válidas únicamente como cómputos de su escenario proxy identificado**, **INVALIDADAS para inferencia de financiabilidad con coste real**, no borradas del historial técnico. No confundir «0 comisión pagada» con «0 comisión reservada». No asumir que un SL más corto eleva riesgo de un **mismo** lote; la distinta asignación de presupuesto por modo es causalmente relevante.

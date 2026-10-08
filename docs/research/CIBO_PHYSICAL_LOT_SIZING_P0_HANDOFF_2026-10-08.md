# CIBO — P0: LOTAJE POR RIESGO MONETARIO REAL (2026-10-08)

**Estado: implementado el calculador puro y la interfaz Trader->CIBO; NO integrado aún en el replay histórico ni certificado en broker.** Esta nota es un handoff de investigación, no prueba de rendimiento financiero.

## Autoridad y origen

- Repositorio: `mezas3238-hue/qore-core`.
- Rama aislada: `agent/cibo-lot-sizing-physical-risk-20261008-001`; se origina en el HEAD canónico `c035f68d093d6123caa4187f70279a04d03ad7d4`.
- No se modificó ni se fusionó la rama de investigación financiera H8 de otro arquitecto.
- H8 es una prioridad más alta que cualquier objetivo de DD: `docs/research/CIBO_H8_REAL_CAPITAL_SOLVENCY_BLOCKER_2026-10-08.md`. Los antiguos capitales USD ~670k/DD 35–36% NO tienen validez como beneficio broker-ejecutable; hubo banco soberano negativo y órdenes obligatorias sin financiación suficiente.
- Los 3.368 intentos de entrada deben seguir auditándose. Si una entrada física no cabe en el mínimo del broker, replay FAIL; jamás inventar un lote, préstamo o fill.

## Cuello de botella comprobado en código actual

`src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py` construye cada candidato a partir de `minimum_seed_volume`, y utiliza `stop_risk_per_multiplier_usd = minimum_volume * stop_loss_per_volume` y un `multiplier` entero. MEDIUM restringe el multiplicador por presupuestos monetarios; la expresión `max(1, min(...))` puede forzar 1x aun cuando alguno de los límites propone 0. El fallback de una ATTACK sobrecapacidad a MEDIUM tampoco implica que la entrada 1x esté realmente financiada. H8 documentó fallas de este tipo.

Esto NO es un algoritmo general de lotaje a precisión de paso del broker. Tampoco prueba que USD3 de presupuesto se gasten efectivamente en cada operación: riesgo y lotes cambian con el SL, fees, riesgo disponible, margen, mínimo y paso.

## Código ya agregado

- `src/qore/infrastructure/cibo_physical_lot_sizing.py`:
  - `stop_loss_usd_per_lot`: entrada, SL, tick size y tick value **USD por lote confirmado por broker**;
  - `CiboLotSizingInput`, `compute_cibo_lot_sizing`: un solo núcleo Decimal 100-dígitos y `ROUND_FLOOR` a pasos reales de lote;
  - límites independientes `REQUESTED_USD`, `SIZING`, `CIBO_COMPOUND`, `QORE_RISK`, `ADAPTIVE_LEVERAGE_MARGIN`, `ADAPTIVE_LEVERAGE_MAX`, `BROKER_MAX` y fuente bancaria física;
  - `source_lane=SOVEREIGN_BANK` para MEDIUM, `PORTFOLIO_CUSHION` para ATTACK; nunca exigir cushion para el bootstrap MEDIUM, ni pedir un préstamo implícito de cushion cuando faltan fondos en banco;
  - `quote_cibo_trader_opportunity_lots`: adaptador concreto desde `TraderOpportunityEnvelope`, incluyendo `minimum_execution_steps` del método.
- `tests/infrastructure/test_cibo_physical_lot_sizing.py`: calculadora de USD3, SL variable, fee dentro del riesgo, paso y mínimo broker, caps independientes, segregación bancaria, margen, adaptador Trader.
- `.github/workflows/cibo-physical-lot-sizing-unit.yml`: test aislado CI con Python 3.12 en rama investigadora.

## Fórmula contractual y ejemplos

Para un presupuesto de pérdida **total** de USD3, usar
`per_lot_total_loss = abs(entry - SL) / tick_size * tick_value_USD_per_lot + cost_and_slippage_buffer_USD_per_lot`.

`lots_raw = min(requested_usd / per_lot_total_loss, sizing_cap_usd / per_lot_total_loss, cibo_compound_cap_usd / per_lot_total_loss, qore_cap_usd / per_lot_total_loss, selected_actual_cash_source_usd / per_lot_total_loss, available_margin_usd / margin_per_lot, leverage_max_lots, broker_max_lots)`.

Luego usar `ROUND_FLOOR(lots_raw / lot_step) * lot_step` y **jamás redondear hacia arriba para alcanzar artificialmente USD3**.

Si costo 0 y pérdida al SL por 1 lote es USD300 / 150 / 30 / 15, se proponen 0.01 / 0.02 / 0.10 / 0.20 lotes, respectivamente, siempre que TODAS las restricciones estén satisfechas. Con fees, se eligen menos lotes; el riesgo al stop + fees queda <=USD3 ex ante. El resultado puede ser USD2.95 o USD2.97, no necesariamente USD3 exactos.

Si volumen resultante cae por debajo del mínimo físico exigido, emitir `UNFUNDABLE_BROKER_MINIMUM` con 0 lotes **de propuesta** y fail-closed en replay; CIBO no tiene potestad para negar una señal del Trader, pero el sistema no puede contabilizar fills imposibles. El volumen de orden debe calcularse **antes de transmitir la ejecución al broker**, aunque el Trader conserve la autoridad de la señal. CIBO administra la posición después del fill.

## P0 restante antes de aceptar un replay de tres años

1. Conectar el núcleo del calculador y adaptador al pipeline real de `cibo_three_mode_capital_lab.py` y a la ejecución del sistema sin suplantar el hard gate H8. No basta con que el núcleo esté publicado.
2. Eliminar expresiones `max(1, min(...))` que sobrepasen presupuesto/cash; sustituir el multiplicador como cantidad comercial por **volumen real lot-step** preservando, si hace falta, multiplicadores sólo como señal de intensidad *económica*.
3. Verificar símbolos, contratos, tick value USD actualizado, divisa de cuenta, commission+spread+slippage, margen por lote, límites por símbolo, mínimo y paso. No asumir que todo símbolo usa valor por pip de Forex.
4. Cada decisión debe escribir sensores `risk_target_usd`, `sizing_lots`, `compound_lots`, `portfolio_source_lots`, `leverage_margin_lots`, `final_broker_lots`, `stop_usd`, `fees_usd`, `all_in_stop_usd`, `source_lane`, `binding_cap`, `equity/margin_before`, y *fill actual* separado.
5. Ejecutar 3.368 intentos/36 meses con base USD60 y fondeo H8 real; contabilizar `FUNDED` vs `UNFUNDABLE`, lotaje vs pérdida presupuestada, bank floor, cushion, margen broker, stop-out, equity mark-to-market y órdenes de liquidación intrabar. Si hay una imposible, no afirmar 3.368 ejecutadas.
6. Solo después reconstruir el techo real y atacar DD <=25% (ideal 20%), sin degradar techo validado. Batería final de costos, aleatorización, OOS, stress, sensibilidad y ablation del cuarteto.

**Estado de certificación: NO CERTIFICADO. Estado de lot-sizer: módulo puro y adaptador con unit CI, integración productiva y replay pendientes.**

# P0 — Contrato de comisión de APERTURA descontada por MT5 — QDLE, Arquitecto 3

**Instrucción del propietario (2026-10-08):** QDLE también debe **calcular y registrar** la comisión que el broker descuenta **al abrir** cada operación. Este documento es la petición de interfaz del Arquitecto 1 a Arquitecto 3 (#739), **no una modificación del motor del Arquitecto 3**. CIBO no lleva un cálculo paralelo de tarifas ni lotaje. Estado inicial: DISEÑO CONTRACTUAL / NO LIVE / SIN CERTIFICACIÓN.

## Brecha de código observada en rama 3

En `src/qore/infrastructure/qdle_mt5_read_only.py`, `VerifiedFee` exige `covers_open_and_close=True` pero entrega solo `usd_per_lot` **agregado de ida y vuelta**. En `src/qore/infrastructure/qore_dynamic_lot_engine.py`, `QDLESymbol.fee_usd_per_lot` se combina con el riesgo al stop y slippage para reservar fondos y revalidar antes de enviar. La conciliación de fill y `record_broker_settlement` no tiene un evento/importe separado para la **comisión efectivamente debitada en la apertura** de cada deal. El total reservado no es una comisión ya pagada.

**No declarar que la comisión de apertura se descontó** solo porque `provider_cost_usd` fue reservado. Son hechos contables distintos: `EXPECTED_OPEN_FEE` (estimada), `ACTUAL_OPEN_FEE` (broker observado), `EXPECTED_CLOSE_FEE` (reserva futura), `ACTUAL_CLOSE_FEE` (broker observado).

## Autoridad y flujo

1. **Fuente de tarifa:** QDLE identifica por cuenta, servidor, símbolo exacto, tramo de volumen, lado, tipo de orden, moneda, fecha efectiva, forma de cobro (por lote, por nominal, mínimo/ticket, redondeo) y si se cobra en apertura, cierre o anticipadamente para ambas patas. La evidencia real debe ser broker-native/acuerdo verificado; una captura no certifica roundtrip.
2. **Antes de autorizar la orden:** QDLE calcula estimaciones separadas `open_fee_estimated_usd`, `close_fee_reserved_usd`, spread/ejecución y stop-loss; suma los componentes pertinentes del riesgo all-in una sola vez. Nunca abre si el coste de cierre obligatorio es desconocido para modo LIVE; mantiene rechazo explícito `FEE_SCHEDULE_INCOMPLETE`.
3. **Al confirmar apertura:** a partir de `history_deals_get` / recibo de deal realmente autenticado de MT5, QDLE toma `commission` con su signo y moneda, otros costes que reporte el bróker por separado, `deal_id`, `position_id`, `order_id`, `volume`, `time`, cuenta, servidor y secuencia. Normaliza a USD usando evidencia de conversión correspondiente a la fecha. Registra `ACTUAL_OPEN_FEE` como débito una sola vez por deal (o por componente con ID inequívoco), conservando la referencia original. Si una comisión de ida+vuelta se carga íntegramente en apertura, no volver a inventar cobro al cierre.
4. **Impacto del libro QORE:** después de confirmar el débito real, refleja el coste atribuido en NAV y riesgo disponible QORE **una sola vez**. La foto de balance/equity FundedNext de USD2.000 es un libro broker distinto de NAV QORE USD60; no volver a restar automáticamente al broker una comisión que su balance ya incorpora. Conciliar el débito con `account_info` y el ledger QORE; reservas iniciales no son pérdidas realizadas.
5. **Fills parciales:** registrar cada deal ejecutado según sus lotes reales (no el tamaño de orden). Admitir comisión proporcional **solo cuando el contrato del broker lo establezca**: puede haber mínimos por ticket, redondeo o cargo anticipado. Cancelaciones y rechazos sin fill no generan comisiones ficticias; si broker acredita un cargo excepcional sin fill, exigir movimiento monetario auténtico.
6. **Cierre:** conciliar `ACTUAL_CLOSE_FEE` y `realized_net_pnl_usd` con la convención de `deal.profit`, `deal.commission`, `deal.swap`, `deal.fee`. Evitar dos veces el mismo fee tanto al publicar un evento de cargo como al acreditar net PnL. Reconciliar parcial close y posiciones agrupadas netting/hedging.
7. **CIBO:** recibe snapshots de `fee_estimated`, `fee_paid`, `reserved_close_fee`, riesgo antes/después y posición actualizada con procedencia; CIBO razona sobre mantener/reducir/cerrar, pero no recalcula ni cobra tarifas; Trader gateway ejecuta bajo gates.

## Evidencia de capturas y faltantes

- Forex EURUSD/GBPJPY/AUDJPY/GBPUSD: pantallas disponibles indican **USD 7 por 1 lote en sección «transacciones de entrada»**. Solo uso **observado/no autenticado** como tarifa inicial provisional de ensayo; no equivale a `USD7 roundtrip`. Ejemplo puramente aritmético de apertura con `USD7/lote`: 0,01 lote → USD0,07; 0,10 → USD0,70; 1,00 → USD7,00. Verificar precio real y descuentos ledger broker.
- XAUUSD: `0,0016%` “en USD por lote”, **base nocional y fórmula/cargos de cierre sin confirmar**; no fingir comisión numérica.
- NDX100: **tarifa de comisión no visible**, no sustituir `None` por USD0.
- Swaps, spreads, deslizamiento y conversiones USD son costes diferentes; no etiquetar como comisión de apertura.

## DoD pruebas mínimas Arquitecto 3 / QA

- Volumen 0,01 / 0,10 / 1,00 bajo tarifa por lote demostrada; verificar `open_fee_estimate` y evento `ACTUAL_OPEN_FEE` con recibo broker simulado y representación original.
- Partial fills (ej. dos deals de 0,01) con fee distinto por ticket/mínimos; sin cargo en tramo sin fill ni dos cargos al retransmitir el mismo `deal_id`.
- Comisión de apertura superior/inferior a estimación, comisión en moneda != USD, comisión cobrada por adelantado en roundtrip, comisión de cierre separada, refund/reversal y refund idempotente.
- `fee`/comisión UNKNOWN (NDX) y XAU fórmula desconocida: LIVE FAIL-CLOSED; REPLAY permitido **solo** con etiqueta assumption/proxy, nunca certificado.
- Riesgo presupuestado por entrada = min(5% NAV QORE causal, cuatro motores, riesgo proveedor y fondos), incluyendo pérdidas-stop+fees+slippage según convención sin doble cómputo.
- Reinicios/resend, duplicados de deals, same-order partial fills, netting/hedging y resultados ambiguos no deben crear o desaparecer deuda.
- Comparación contable de NAV QORE con broker statement: `gross_profit + commission + swap + fee` con signos broker y conversión; ninguna doble resta con `realized_net_pnl_usd`.
- Publicar tests exact-SHA en rama 3 e informe de reconciliación por `request_id` y `deal_id`; exigir revisión cruzada 1/2/3 antes de integrar. Prohibidos `order_send`, fondos reales y certificación LIVE sin aprobación expresa.

## Contrato candidato de recibo (no implementado todavía)

```text
QDLE_BROKER_OPEN_FEE_RECEIPT:
  request_id, broker_account_id, broker_server, symbol, order_id, deal_id,
  position_id, side, filled_volume_lots, executed_at, broker_posted_at,
  fee_raw_signed, fee_currency, fee_usd_signed, conversion_source_as_of,
  tariff_reference, fee_charge_timing,
  opening_fee_estimate_usd, discrepancy_usd,
  qore_capital_sequence_before, qore_capital_sequence_after,
  fee_booked_once, provenance_digest, broker_authentication
```

La recepción posterior por CIBO solo actualiza el estado cognitivo; no se usa para recrear saldo ni abre una operación. **Todas las implementaciones y cálculos de comisión pertenecen a QDLE (#739).**

# P0 — Comisión de FundedNext Stellar Instant verificada en fuentes oficiales (09-10-2026)

**Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core) · **PR:** [#745](https://github.com/mezas3238-hue/qore-core/pull/745) · **Estado:** fuentes públicas verificadas / comisión particular de la cuenta MT5 PENDIENTE de conciliación read-only · **NO LIVE**.

## Fuentes primarias consultadas
1. [FundedNext — «¿Cuáles son los cargos de commission para la Cuenta Instantánea Stellar?»](https://help.fundednext.com/es/articles/11641300-cuales-son-los-cargos-de-commission-para-la-cuenta-instantanea-stellar): forex $7/lot, commodities 0,0016 % sobre precio de apertura, índices $0/lot; se factura **al abrir y no al cerrar**; MT4/MT5 iguales; versión en inglés https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account
2. [FundedNext — cálculo de comisiones de metales por nocional](https://help.fundednext.com/es/articles/10701368-cuales-son-los-cargos-de-commission-para-los-stellar-challenges-y-las-fundednext-accounts): `lot_size × contract_size × open_price × 0.0016%`. Ejemplo oficial XAUUSD 1 lote, 100 oz, precio $4466.22 → ~$7.14.
3. [FundedNext — Reglas generales CFDs / Symbols & Conditions](https://fundednext.com/general-rules/cfds/symbols-and-conditions): describe `Commission charged per side`, Stellar Instant `$7 on Forex and Oil`, metal `0.0016%`; **contradice** página específica Stellar Instant que dice que solo hay cargo en apertura y ninguno en cierre. Debe resolverse con histórico MT5 y términos account-specific; no fingir que la discordancia no existe.

**Fecha/nota:** el artículo específico está agrupado en «Product Update: 12th January, 2026» y muestra la fecha con formato `12/01/2026` en inglés; algunas traducciones indican `01/12/2026` ambiguamente. No resolver vigencia del contrato concreto mediante traducción de fecha; verificar la cuenta y programa al capturar tarifas.

## Tabla de comisiones por cuenta/modelo «Stellar Instant», solo fuente específica
| Símbolo | Clase | Comisión oficial anunciada al abrir (por 1 lote) | Comisión al cerrar según página Stellar Instant | Aplicación QDLE bajo política Stellar-specific |
|---|---|---|---|---|
| EURUSD | Forex | $7 | $0 | `7 USD/lot` apertura, `0` cierre |
| GBPUSD | Forex | $7 | $0 | idem |
| GBPJPY | Forex | $7 | $0 | idem; USD/pip variable aparte |
| AUDJPY | Forex | $7 | $0 | idem; USD/pip variable aparte |
| XAUUSD | Metal | `0.000016 × contract_size × executable_entry × lots` | $0 | contrato de 100 oz/lote en capturas; **confirmar especificación de cuenta y tarifa** |
| NDX100 | Índice | $0 | $0 | **no** introducir $20/lot sin fundamento |

No confundirse: **0 USD realmente pagados en un replay sin fills NO demuestra 0 USD coste estimado para lotaje**. Tampoco demuestra que el precio de cada símbolo del manifiesto 2019–2022 sea el precio de mercado de ejecución actual.

### Ejemplos de comisión, SIN spread/slippage
- EURUSD 0,01 lote: página Stellar específica **$0,07 al abrir** y $0 al cierre; supuesto antiguo usado por QDLE $0,14 ida y vuelta. **Si** aplica regla general `$7 por lado`, serían $0,14 roundtrip en vez de $0,07. Hasta broker-confirmación, ejecutar **ambos escenarios**, sin certificar `$0,07` como tarifa cuenta concreta.
- XAUUSD 1 lote a 4466,22 USD/oz y 100 oz/lote: comisión OPEN = 4466,22 × 100 × 0,000016 = **$7,145952** (redondeada a $7,14 por FundedNext); para 0,01 lote ~$0,07146; **NO** multiplicar por dos bajo modelo solo apertura. Escenario general por lado (si es aplicable) costaría ~$14,291904 por lote.
- NDX100 1 lote: 0 USD según ambas fuentes para índices (reglas generales no listan comisión índice); el replay #37937821428 **usó un fee hipotético explícito $20/lot**, así que el contador `1961` se calculó con un gravamen NDX innecesario según tarifa oficial publicada. NDX100 debe validarse con su símbolo exacto y cuenta, no con alias supuesto NAS100.

## Hallazgo contra el código actual
Archivo `scripts/qdle_3368_dual_ledger_replay.py`, política `independent_four_motors`:
- EURUSD/GBPUSD/AUDJPY/GBPJPY `fee=14` por lote roundtrip (asume $7 OPEN + $7 CLOSE).
- XAUUSD `fee=entry × 100 × 0.000016 × 2` por lote roundtrip (asume dos cargos sobre el mismo precio).
- NDX100 `fee=--ndx-roundtrip-fee-proxy-usd-per-lot 20` inyectado en `.github/workflows/cibo-p0-native-max-manager-qdle-3368.yml`.
- En el motor `src/qore/infrastructure/qore_dynamic_lot_engine.py` la comisión **sí entra** en `provider_cost_usd_per_lot` cuando se calcula la pérdida all-in reservada. Informe `fees_paid=0` significa **NO FILL**, no `fee_cost_not_accounted`.

**Por tanto:** #37937821428 pasó el contrato de 3368 instrucciones/3368 QDLE pero **NO la validez de comisiones de cuenta**. `1961` y `1407` siguen siendo contadores de *ese escenario de costes supuesto*, no financieramente definitivos.

## Acciones P0 prioritarias
1. Mantener referencias originales y no borrar el reporte previo. En replay científico repetir con **dos esquemas tarifarios** y mismo input/digests:
   - `FUNDEDNEXT_STELLAR_INSTANT_HELP_OPEN_ONLY`: FX 7 OPEN, 0 CLOSE; XAU 0.0016% del nocional OPEN, 0 CLOSE; NDX 0 ambas.
   - `FUNDEDNEXT_GENERAL_RULES_PER_SIDE_SENSITIVITY`: FX 7 OPEN + 7 CLOSE; XAU 0.0016% OPEN + CLOSE (notional cada pata); NDX 0 ambas.
2. Una tercera comparación idéntica con `LEGACY_REPLAY_PROXY`: FX 14 RT, XAU dos patas al precio de apertura, NDX20 RT. Entregar delta de lotes positivos, rechazos, total lots, y razones contra los 3368 `signal_fingerprint`, modo, símbolo y binding.
3. La verdad de *tarifas reales de la cuenta del usuario* se obtiene con historial de `MT5 history_deals_get` con `commission, fee, swap, entry, symbol, volume, position_id`, detalles comerciales contractuales de cuenta FundedNext, y screenshot del instante de cargo. `mt5.symbol_info` aporta tick, pip/contract grid pero no expone una propiedad estándar `commission`. No hay `SYMBOL_COMMISSION` estándar universal. Cuando no haya deals históricos, no inferir fee efectivo de un campo vacío.
4. Recalcular conversión JPY por época con `order_calc_profit` o USDJPY ejecutable disponible en la época; conservar incertidumbre en costos por spread, swap y datos históricos faltantes. No aplicar spread dos veces si entrada ASK/salida BID (o viceversa) ya lo incorporan.
5. Hasta la conciliación con proveedor, declarar `financial_certification=REJECTED`, `actual_account_fee_verified=false`, `managed_final_NAV/DD/PF=null`, `real_mt5_fills=0`, `no_live_authorization=true`.

## Resultado pendiente
Este documento **no ejecuta** nuevo replay y **no modifica** tarifas del servidor LIVE. Su función es fijar fuentes primarias y especificar exactamente la comparación y la incertidumbre que debe resolver el siguiente cambio de QDLE.

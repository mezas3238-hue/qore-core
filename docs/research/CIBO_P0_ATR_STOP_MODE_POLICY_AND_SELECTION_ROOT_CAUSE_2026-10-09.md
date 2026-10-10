# CIBO P0 — Política formal experimental de SL por ATR y causalidad de selección

> **OVERRIDE CEO P0 (2026-10-09): DOCUMENTO HISTÓRICO DE LA ARQUITECTURA SELECTOR / NO ES DIRECTIVA OPERATIVA.** El flujo válido es *Trader decide → CIBO recibe y administra todas las señales → QDLE determina factibilidad física*. Mantener este estudio para explicar por qué Native MAX bloqueó 3.357 señales; no ejecutar sus recomendaciones de aflojar/optimizar filtros ni usar su cohorte de 200 como programa prioritario. Directiva vigente: [CIBO P0 PARADIGM OVERRIDE](CIBO_P0_PARADIGM_OVERRIDE_2026-10-09_TRADER_EXECUTION_MANAGEMENT_QDLE.md).


**Estado:** PROPUESTA EXPERIMENTAL / NO LIVE / no certifica ventaja; owner: CIBO Soberano + cuatro motores + QDLE.  
**Repositorio:** `mezas3238-hue/qore-core` · **PR:** #745 · **Referencia científica:** [Trader Lab Fast corregido #37878805062](https://github.com/mezas3238-hue/qore-core/actions/runs/37878805062) · **Subject:** `da64fb6fdafacd426fd09cd75dce559c13649692`.

## 1. Diagnóstico correcto: selección vs asequibilidad del SL

Fuente: manifest original sellado **3.368 señales 2019–2022**, artifact `11451743578` ZIP SHA256 `d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`, más decisión Native CIBO en artifact `11588089131` (ZIP SHA256 `eebf6de43da63aadc200a3783109246188d46e0fcdd7da127f07eff815d6cec6`). No confundir con un nuevo holdout OOS.

- 3.368/3.368 decisiones CIBO Native: **1.804 COGNITIVE_BLOCK, 1.553 CAPITAL_BLOCK, 11 RISK_REVIEW_READY / ALLOW**. 11 autorizadas = **0,3266%** de la población; **3.357** quedaron sin solicitud de riesgo.
- De las 11 autorizadas, **9 financiadas en el replay proxy QDLE** (5 NAS100, 2 AUDJPY, 2 GBPJPY); 2 quedaron bajo el mínimo financiero del presupuesto *solicitado* por CIBO. Ninguna autorización para EURUSD, GBPUSD o XAUUSD: no fue QDLE el causante de su cero cobertura.
- En *sensibilidad de coste mínimo aislada*: un lote `0.01` con SL original del Trader, USD60 inicial, techo `USD3` y fees de investigación aplicados en `scripts/qdle_3368_dual_ledger_replay.py` es asequible en **3.068/3.368 = 91,09%** de las señales. **300** no caben. No implica broker fill ni fondos/margen libres durante todo el replay; en NAS100 el mínimo metodológico original puede ser mayor a 0.01 y aquí se evalúa solo el `broker_grid` de investigación.
- Las 11 autorizaciones Native originales tienen SL de coste <= USD3 para broker-min `0.01` bajo sensibilidad inicial; los dos no financiables fallan **REQUESTED_USD** porque la asignación CIBO individual es más pequeña que el coste del mínimo, no porque necesariamente requieran un SL más estrecho.
- Por ello **la hipótesis «99,7% rechazado porque el SL del Trader no cabe en USD3» queda refutada por esta fuente**. La causa primaria observable es selección política/cognitiva/económica pre-QDLE. Cambiar solo SL con las mismas 11 autorizaciones no puede resolver 3.357 bloques.

### Censo por símbolo (sensibilidad inicial de precio y coste, NO simulación de estrategia nueva)

| Símbolo | Señales | 0.01 lot SL original + fees <= USD3 | COGNITIVE_BLOCK | CAPITAL_BLOCK | ALLOW | QDLE fundable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AUDJPY | 673 | 649 | 189 | 480 | 4 | 2 |
| EURUSD | 495 | 494 | 436 | 59 | 0 | 0 |
| GBPJPY | 618 | 589 | 256 | 360 | 2 | 2 |
| GBPUSD | 606 | 568 | 441 | 165 | 0 | 0 |
| NAS100→NDX100* | 484 | 454 | 265 | 214 | 5 | 5 |
| XAUUSD | 492 | 314 | 217 | 275 | 0 | 0 |
| **Total** | **3.368** | **3.068** | **1.804** | **1.553** | **11** | **9** |

*El mapeo NAS100↔NDX100 y el `USD20/lote` de comisión NDX son supuestos proxy no certificados. Para FX la sensibilidad usada es USD7 OPEN + USD7 CLOSE/lote; XAU se modela con 0,0016% de nocional por lado. USDJPY/JPY conversion de la fuente histórica permanece proxy; no se usa la etiqueta «pip» en XAU sin definir precio/tick exacto.*

## 2. Política ATR propuesta: tabla de multiplicadores exactos para ablation, no cifras validadas

**Objetivo:** `SL_distance_in_symbol_price = multiplier(mode, instrument, timeframe) × ATR14_in_symbol_price`. Punto de partida para investigación, a comparar contra el SL estructural nativo del Trader, no un mandato de estrechamiento automático. `ATR14` de Wilder sobre **14 velas completamente cerradas** de la misma temporalidad al `market_decision_at` causal, con calentamiento y verificación de horas servidor/UTC.

| Símbolo | Timeframe manifest | BANK | MEDIUM | ATTACK | Origen |
| --- | --- | ---: | ---: | ---: | --- |
| AUDJPY | M15 | 0.50× | 1.00× | 1.50× | Hipótesis |
| AUDJPY | H1 | 0.50× | 1.00× | 1.75× | Hipótesis |
| AUDJPY | H4 | 0.50× | 1.00× | 2.00× | Hipótesis |
| EURUSD | H1 | 0.50× | 1.00× | 1.50× | Hipótesis |
| EURUSD | H4 | 0.50× | 1.00× | 1.75× | Hipótesis |
| GBPJPY | M15 | 0.50× | 1.00× | 1.75× | Hipótesis |
| GBPJPY | H1 | 0.50× | 1.00× | 2.00× | Hipótesis |
| GBPJPY | H4 | 0.50× | 1.00× | 2.00× | Hipótesis |
| GBPUSD | M15 | 0.50× | 1.00× | 1.50× | Hipótesis |
| GBPUSD | H1 | 0.50× | 1.00× | 1.75× | Hipótesis |
| GBPUSD | H4 | 0.50× | 1.00× | 2.00× | Hipótesis |
| NAS100/NDX100 | M1 | 0.50× | 1.00× | 2.00× | Hipótesis; proteger ruido/spread |
| XAUUSD | H1 | 0.50× | 1.00× | 2.00× | Hipótesis; pip/tick broker explícito |
| XAUUSD | H4 | 0.50× | 1.00× | 2.00× | Hipótesis |

**No hay multiplicadores «óptimos» conocidos:** estos son valores iniciales basados en la propuesta CEO `BANK=0.5, MEDIUM=1.0, ATTACK=1.5–2.0`. Versionar la tabla e investigar cada símbolo/timeframe; un resultado positivo en fuente quemada no valida despliegue.

### Orden exacto de decisiones

1. Recibir `TraderOpportunityEnvelope`: señal/side, intended entry, original stop, invalidación estructural, timestamp, timeframe, trader/symbol y evidencias.
2. CIBO comprueba causa de admisión; **no fuerza ALLOW por ser barato**. Debe producir reason codes verificables `COGNITIVE_BLOCK`, `CAPITAL_BLOCK`, `RISK_REVIEW_READY` y subcausas. Comparar baseline vs contrafactual para cada una de las 3.368.
3. Recibir barras verificadas y generar ATR14 **al último close <= decision_at**; sin ATR o barras suficientes: `ATR_MISSING/STALE`, usar SL original **sin afirmar normalización** (nunca inferir ATR usando hindsight).
4. CIBO selecciona `BANK/MEDIUM/ATTACK`, ratio de la tabla; calcula precio candidato `BUY: entry - m×ATR`, `SELL: entry + m×ATR`. Redondear stop **hacia afuera** al tick; nunca un stop entre el precio y el mínimo del broker.
5. Validar `min_stop_distance`, spread/latencia, volatilidad, estructura y verdadero nivel de invalidación: si ATR-stop deja sin protección a la tesis o introduce salida prematura, **REJECT_SHADOW_INVALID_STRUCTURE**; no modificar silenciosamente ni el stop ni el resultado Trader.
6. Congelar el SL en un recibo `CIBO_ATR_STOP_SHADOW` con `policy_version`, `ATR`, `ATR_source_sha256`, timeframe y `last_bar_closed_at`, `signal_decision_at`, modo, geometry, stop_original, stop_normalized, tradability, binding constraints y reason codes.
7. Cuatro motores evalúan límites de USD/margen y NAV; **QDLE es la única autoridad del lote real cuantizado**: `loss_per_lot = broker_order_calc_profit_loss_at_SL + OPEN_fee + CLOSE_fee + spread/slippage_buffer + other_losses`; `risk_budget <= 0.05 × QORE_NAV_reconciled`; presupuesto individual CIBO, source Bank/Cushion, free margin, exposure reservation, broker stops y lote mínimo prevalecen. Si `0.01` no cabe, `UNFUNDABLE`, nunca forzarlo.
8. Reprice/touch/cancel: un cambio de SL después de aprobación invalida recibo y reserva anterior; recalcular causally o rechazar. No se deben computar ganadores/perdedores con el `gross_structural_outcome_r` congelado cuando cambia el stop.

### Cálculo de ejemplo (solo EURUSD bajo fee proxy USD14/lot RT)

`ATR14=12 pips`: BANK `6pip -> (USD60+USD14)*0.01=USD0.74/min_lot`, lote máximo por USD3 `0.04` si los demás cap permiten; MEDIUM `12pip -> USD134/lot -> 0.02`; ATTACK `1.75×ATR=21pip -> USD224/lot -> 0.01`. Esto es **factibilidad**, no predicción de rendimiento; spread, stops broker y estructura podrían invalidar BANK.

Para XAUUSD expresar distancia en **dólares por onza y tamaño de contrato**, no equivaler pips de oro con forex. Margen broker y comisiones se obtienen de `order_calc_margin`, `order_calc_profit`, `symbol_info`/deals en modo read-only si están disponibles; en replay histórico usar captura causal de proveedor o escenarios etiquetados.

## 3. Diseño del ensayo — cuatro brazos, igual fuente sin leakage

- **A Control / Native old stop:** 3.368 señales; separar 1804 cognitive, 1553 capital, 11 autor, 9 QDLE. Capital/fees/closed DD PF del **proxy** existente: USD60→USD62.4853883138, DD cerrado 6.096644741%, PF 1.5638375, USD3.48 comisión; no comparación directa con techo CIBO de otra política.
- **B Stop-normalization-shadow, selección Native congelada:** medir cuántas de 11 aprobadas pasan lote mínimo y si su SL normalizado es estructuralmente válido; sin cambiar subcausas de 3357 bloqueadas. El límite superior de nuevas autorizaciones sigue siendo 11.
- **C Shadow economic selection re-evaluation:** investigar `COGNITIVE_BLOCK` vs `CAPITAL_BLOCK` con razones reales, causal prior, calificación de volatilidad y expectativa neta, cuantificar admisiones hipotéticas que pasan los **mismos gates financieros**. No permitir `ALLOW_ALL`, bypass de cognition, préstamo implícito Bank/Cushion o uso de resultados futuros.
- **D Causal full replay físico con SL/TP reconstruidos y gestión CIBO:** requiere barras suficientes (M1/M15/H1/H4), spread/sesión, intrabar stop-hit arbitration conservadora, gaps, order type fill proof, salida/partials, fees al abrir/cerrar y MTM intratrade. Reproducir costo, NAV, DD intra/closed, profit factor, volumen, total bank/cushion, razones por señal y 6 instrumentos. Si datos faltan, informe `RESEARCH_INCOMPLETE`, no inventar trades.

**Invariantes para P0:** 3.368 IDs únicos y estables; same decision_at timeline; no ATR de velas abiertas ni futuros; no seleccionar multiplicadores según R pasado y atribuir causalidad; 5% NAV dinámico; lot grid; fees OPEN/CLOSE; no stops dentro de invalidación; no default broker fee 0 desconocida; no MT5 order_send; datos no vinculados al broker se rotulan research; certificar solo tras fresh OOS no consumido.

### Criterios de aceptación

1. Recibos previos ATR y reason codes por **3.368 señales**; al menos `missing_ATR`, `unfinanceable_original_stop`, `unfinanceable_normalized_stop`, `invalid_structure`, `cognitive_rejection`, `capital_rejection`, `risk_approved`, `broker_margin_rejected`, `fee_exceeded`.
2. Comparación A/B/C con mismas señales y clocks, más un reporte separado para D solo si el path de mercado es verificable.
3. Tasa de admisión y de financiamiento por símbolo/trader/modo/timeframe; abstenciones sin inventar ATR, comisiones, equity, posición ni resultados.
4. Perfil de pérdidas reales del replay causal y DD MTM; no usar DD de saldo cerrado como sustituto sin avisar.
5. Tests de tick rounding away, short vs long, ATR disponible antes de decisión, ATR missing/stale, fees/all-in, signo y stop-distance, correlación, NAV 5%, no órdenes LIVE, plus regresión decimal anterior.
6. Comparar también mutaciones con control `ORIGINAL_STOP_UNCHANGED`; conservar solo variantes que mejoren métricas *sin* leakage ni degradar floor legítimamente verificado.

### Acción inmediata

La **primera tarea de ingeniería** es un `ATR predecision evidence adapter` sobre Atlas cerrado por temporalidad y **explicar subcausas** de `COGNITIVE_BLOCK (1804)` y `CAPITAL_BLOCK (1553)`. El manifest actual no incluye un campo ATR causal por señal; es incorrecto usar el SL original dividido por multiplicador como si fuera ATR histórico. Hasta tener las barras no es honesto reportar «PF/DD ATR normalizado» a partir del R heredado.

**Autoridad CEO:** libre ejecutar este diseño en replay OFFLINE aun con certificación global roja; no se desactivan gates de coherencia/solvencia/causalidad y nunca se implica permiso LIVE.

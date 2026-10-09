# P0 — CONTRATO FORMAL CIBO SOBERANO → CUATRO MOTORES → QDLE → GATEWAY

**Estado:** código integrado en rama Arquitecto 3; test/replay offline; **no LIVE, no MT5 order_send, no certificación de rentabilidad**. Documento de aceptación de #738 (motores), #739 (QDLE), #737 (CIBO) y PR #741; referencia para coordinar PR #735. No altera ownership de ramas ajenas.

## 1. Principios no negociables

1. **El Trader genera la oportunidad**: `signal_id`, `trader_id`, símbolo exacto, BUY/SELL, entry, SL/TP, geometría/sesión, timestamp de decisión. Ninguna cifra financiera del futuro modifica la decisión pasada.
2. **CIBO Soberano gobierna**: decide el destino de la señal y la fuente de capital del Trader (Bank/Medium/Attack), qué capital de trabajo se asigna a cada uno, riesgo máximo por señal y gestión posterior (SL/trailing/parciales/exit con autorización y trazas). No lo sustituye un modo fijo universal, ni lo gobierna QDLE.
3. **CIBO Compuesto** actualiza el NAV económico QORE a partir de PnL *realizado y conciliado*, restando gastos/fees/swaps. Pérdidas flotantes reducen capacidad, ganancias flotantes no aumentan presupuesto realizado.
4. **Portafolio Compuesto** asigna fondos por Trader/fuente, preserva protected floor, evita doble gasto, limita correlación y riesgo agregado. Los presupuestos de fuente NO son sinónimo de riesgo permitido ni se transfieren entre fondos tácitamente.
5. **Sizing** emite riesgo aprobado por operación en USD, opcionalmente menor que 5%. **Adaptive Leverage** emite máximo volumen broker en lotes y margen USD con evidencia verificable; no sustituye un multiplicador abstracto por volumen físico.
6. **QDLE exclusivamente transforma decisiones en lotaje** con stop-risk, tarifas del instrumento, spread/ejecución si valorables, swaps si aplica, rejilla del broker y capacidad de margen real. No cambia ni genera señales, stops, presupuestos, fuente de capital o gestión. No equivale al gateway y **no llama `order_send`**.
7. **El gateway del Trader autorizado** puede pasar las validaciones de QORE Risk/FundedNext y ejecutar; un `RESERVED_FOR_TRADER` no es fill. Sin ticket+deal+reconciliación no existe operación MT5 certificada.
8. El 5% es **máximo de pérdida planificada all-in por nueva señal** sobre NAV causal QORE, no cuota fija ni objetivo de llenarlo: `R_max = 0.05 × NAV_QORE_reconciliado`. Ejemplos NAV 60→3, 100→5, 150→7.5, 1000→50. Con un cap menor de CIBO/4 motores se usa **el menor**. No equivale a garantía de pérdida final (gaps, slippage, swaps, spread pueden exceder el SL).

## 2. Entrada tipada de investigación

`CiboEconomicInstruction` (`src/qore/infrastructure/qdle_cibo_authority.py`) es decisión upstream, **no autoridad live autenticada por sí misma**:

| Campo | Unidad | Autoridad |
|---|---|---|
| `signal_id`, `trader_id`, `symbol`, `side` | identidad BUY/SELL | Trader/CIBO, sin sustituciones |
| `entry_price`, `stop_price` | precio del símbolo | Trader; QDLE los conserva |
| `source_lane` | SOVEREIGN_BANK/PORTFOLIO_CUSHION | CIBO y Portafolio |
| `allocated_source_funds_usd` | USD capital de trabajo | Portafolio/CIBO |
| `authorized_all_in_risk_usd` | USD riesgo máximo al SL + costes | CIBO/Sizing |
| `maximum_requested_lots` | lotes *techo opcional* | decisión upstream, nunca autoridad de fill |
| `issued_at`, `account_sequence`, `evidence_sha256` | epoch/procedencia | controles de causalidad |

Las **cuatro** propuestas nativas `FourMotorProposal` comparten `FourMotorObservation` con broker quote fresca, fuente causal y NAV realizado: `SIZING.approved_risk_usd`, `CIBO_COMPOUND.approved_risk_usd`, `PORTFOLIO_COMPOUND.approved_source_funds_usd`, `ADAPTIVE_LEVERAGE.approved_max_lots` + `.approved_margin_usd`. Falta una propuesta o difiere señal, timestamp, cuenta, fuente o símbolo: **rechazar**. LIVE exige productores autenticados por sus claves independientes + treasury/MT5 legítimos (no bastan hashes ficticios).

## 3. Cálculo físico, sin doble contabilidad

El motor valora `loss_per_lot_usd = abs(PnL(entry→SL, 1 lote))` con contrato, divisa, tick y Bid/Ask verificables mediante `order_calc_profit` cuando corresponda. No asumir USD10/pip fuera de EURUSD ni reemplazar `NAS100` y `NDX100` sin verificar. Se forma:

```
allowed_loss_usd = min(
    NAV_QORE_reconciliado * 0.05,
    CIBO.authorized_all_in_risk_usd,
    Sizing.approved_risk_usd,
    CIBO_Compuesto.approved_risk_usd,
    Portafolio.approved_source_funds_usd,
    tesorería_source_no_reservada,
    riesgo_QORE_restante,
    margen/broker_provider_floor expresados en sus unidades propias
)
loss_per_lot_all_in = stop_loss_usd_per_lot
                   + fee_open_and_close_usd_per_lot
                   + allowed_execution_buffer_usd_per_lot
continuous_lots = allowed_loss_usd / loss_per_lot_all_in
lots = min(
    floor_to_broker_grid(continuous_lots),
    floor_to_broker_grid(Leverage.approved_max_lots),
    floor_to_broker_grid(available_margin_usd / broker_margin_usd_per_lot),
    broker_max_and_directional_lots, optional_CIBO_volume_ceiling
)
```

**Dimensiones:** margen USD nunca se usa como *riesgo al SL* y lote máximo nunca como dólares; se aplica cada restricción en su dimensión antes de tomar la mínima física. Lo anterior describe relaciones, no una sola fórmula que divida margen entre stop loss.

**Rejilla:** `min_lot`, `max_lot`, `step`, límite direccional, reglas provider y order_check exactos de MT5; redondeo siempre hacia abajo; jamás subir a mínimo broker si no entra en todos los límites. Si `lots < min_lot` → `UNFUNDABLE` y auditar la restricción, **no descartar silenciosamente la señal**. Cada reserva debe ser atómica entre Traders para no usar dos veces riesgo y margen.

**Costes:** el `fee_usd_per_lot` del contrato QDLE representa **total esperado ida+vuelta**, no sólo apertura. Separar **comisión reservada total**, **débito real de apertura después del fill** y **débito real del cierre después del exit**, con IDs de deal únicos, más swap/spread/slippage cuando hay evidencia. En escenarios EURUSD con `$7 OPEN + $7 CLOSE`, se usa `$14/lot` **sólo como sensibilidad documentada**; NO aplicarlo a XAU, JPY, NAS100, NDX100 sin tarifa y conversión autenticadas. El camino LIVE bloquea costes incompletos.

## 4. Salida y auditoría obligatoria

`build_cibo_directed_qdle_intent` crea `QDLEIntent` restringido, sin elegir Trader o estrategia. `QDLE.reserve_for_trader` entrega `QDLEResult` con estado, lotes, pérdida al SL, coste all-in reservado, riesgo total, margen y binding constraints. `audit_cibo_qdle_lotage` valida ese resultado contra CIBO y las cuatro propuestas, retornando `CiboLotageAuditReceipt`:

- Señal/Trader/símbolo/lado/fuente/epoch y digest de fuentes, capital NAV QORE y límite 5%.
- Presupuesto CIBO, capital de trabajo asignado (separados), entrada/SL originales, lotes y broker grid.
- Stop USD, costes ida/vuelta USD, riesgo all-in USD, margen USD, razones de aprobación/no financiabilidad.
- `real_mt5_fill_proven=False` **siempre** en este recibo de investigación; sólo MT5 broker settlement autenticado prueba fill.

`UNFUNDABLE` en cero lotes y `RESERVED_FOR_TRADER` positivo son los únicos estados aceptados en el reporte de presupuesto previo al envío; ambos conservan todas las señales para auditoría. Riesgo o coste fuera del cap, cuenta/epoch equivocada, lote no perteneciente al grid, lote >preferencia CIBO, evidencia incompleta, falta de fondo y margen inválido → bloquear.

## 5. Casos de aceptación (replay/unittest determinístico)

EURUSD, USD 10 por pip/lote, comisión **total hipotética** USD14/lote, min/step 0.01, margen suficiente:

| NAV QORE | Stop pips | Max riesgo 5% | Lotes | All-in stop USD |
|---:|---:|---:|---:|---:|
| 60 | 10 | 3 | 0.02 | 2.28 |
| 60 | 18 | 3 | 0.01 | 1.94 |
| 60 | 25 | 3 | 0.01 | 2.64 |
| 150 | 10 | 7.50 | 0.06 | 6.84 |
| 150 | 18 | 7.50 | 0.03 | 5.82 |
| 150 | 25 | 7.50 | 0.02 | 5.28 |

Con stop 20 pips: NAV 60→0.01, 100→0.02, 150→0.03, 200→0.04, 300→0.07, 500→0.11, 1000→0.23. Otras pruebas: NAV actualizado **por cashflow realizado**, $50 asignados a ATTACK ≠ $50 autorizados de riesgo, menos de mínimo → `UNFUNDABLE`, margen insuficiente → `UNFUNDABLE`, comisión XAU del símbolo distinta a EURUSD, manipulación de budget/grid/coste/epoch rechazada. Ningún valor fijo de Bank/Medium/Attack sustituye decisiones de CIBO.

## 6. Replay, criterios de entrega y límites

- CI de física, gateway no-send, test de 4 motores, test de autoridad CIBO, y replay sobre fuente sellada de **3.368 señales**.
- El control `--cibo-instructions` admite presupuestos/transferencias/settlements predefinidos con 3.368 IDs, sin inventar lotes ni PnL. Los ejemplos negativos (0 decisiones financiadas) y positivos (una operación EURUSD ficticia con salida 1R) sólo verifican **OBEDIENCIA**, no rendimiento.
- Un replay real de CIBO requiere **decisiones cognitivas y gestión causal de salida** de A1, y asignaciones bancarias/correlación/4 votos autenticados de A2. El viejo $670k/DD35% y la simulación QDLE $9,03 NO son equivalentes ni están certificados broker; no compararlos como si fueran la misma política.
- **No deploy, no VPS, no order_send**, PR #741 DRAFT hasta revisión cruzada, comisiones/volúmenes FundedNext actuales, stops/fills auténticos y DD intratrade + batería científica.

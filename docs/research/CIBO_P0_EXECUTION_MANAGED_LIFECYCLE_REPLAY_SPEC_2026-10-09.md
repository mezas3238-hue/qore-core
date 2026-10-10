# QORE Core · CIBO Soberano Native MAX + QDLE — Especificación P0 del replay ejecutable y NAV conciliado
**Fecha:** 2026-10-09 · **Rama:** `agent/cibo-sovereign-integration-p0-20261008` · **PR:** [#745](https://github.com/mezas3238-hue/qore-core/pull/745) · **Clasificación:** diseño vinculante P0, **NO implementación ni autorización de LIVE**.

## 0. Resultado verificable de partida; qué NO se debe reclamar
Fuente: [FULL FRESH Native MAX + QDLE #37937821428 (SUCCESS)](https://github.com/mezas3238-hue/qore-core/actions/runs/37937821428), artefacto `cibo-max-native-3368-qdle-replay-37937821428` (ID 11621741615), 2026-10-09. Las 3.368 señales tienen instrucción `NativeSovereignModeInstruction` originada en cognitiva Native MAX (no solo mapeador post hoc); las 3.368 llegan a QDLE.

| Modo | Instrucciones CIBO → QDLE | QDLE devuelve lote físico > 0 | No financiables con el proxy |
| --- | ---: | ---: | ---: |
| BANK | 2.031 | 870 | 1.161 |
| MEDIUM | 520 | 274 | 246 |
| ATTACK | 817 | 817 | 0 |
| **Total** | **3.368** | **1.961** | **1.407** |

Volumen propuesto agregado: 31,63 lotes (cuatro motores) / 31,93 (paper experimental sin topes estratégicos). Esto suma propuestas históricas y **NO representa exposición simultánea, fills, notional ejecutado ni resultado financiero**. `cibo_managed_exit_receipts_consumed=0`, `real_fundednext_fills=0`, P&L/DD/PF gestionados `null`, capital inicial QORE 60 USD y NAV sin cambios 60 USD **por ausencia de settlements**, no por resultado 0. Las comisiones OPEN/CLOSE **pagadas** son 0; el motor únicamente estimó costes para dimensionamiento. El brazo 'sin límites' sigue sujetándose a grid, margen, coste all-in y riesgo QORE ≤5 %.

**Corrección conceptual obligatoria:** estos contadores NO prueban que «BANK falla por SL corto y lotes demasiado grandes». El riesgo de **un mínimo 0,01 lote** normalmente *disminuye* cuando el SL se acorta, si precio, símbolo, comisión y márgenes permanecen iguales; la menor cuota de BANK (1,25 % NAV vs MEDIUM 2,5 % vs ATTACK 5 %) es un factor diferente y material. Ejemplo ilustrativo QORE NAV $60: BANK $0,75, MEDIUM $1,50, ATTACK $3,00. A tarifa FX supuesto $14/lote ida-vuelta, comisión de 0,01 lotes = $0,14, dejando respectivamente $0,61/$1,36/$2,86 de presupuesto para pérdida al stop y demás costes. La causalidad concreta se debe auditar por señal (`effective_risk_usd`, `minimum_grid_risk_usd`, `stop_distance`, `fee`, `binding_constraint`, `broker_margin`); porcentajes de financiabilidad **no identifican** por sí solos qué componente los causa. No asumir que ATTACK conserva financiación 100 % con nuevo NAV, cartera simultánea y costes verdaderos.

## 1. Arquitectura y autoridad única
```text
Trader señal SELLADA + ticks/barras ejecutables de su instante
    ↓
CIBO Native MAX: análisis causal y decisión soberana de modo,
                 entrada/salida y plan de gestión; conserva evidencia
    ↓
Sizing + CIBO Compuesto + Adaptive Leverage + Portafolio Compuesto
    ↓
QDLE ÚNICO: lotes, pérdida SL, apertura+cierre, swap/buffer, margen,
            disponibilidad de fuente, cuenta/broker grid, reservas atómicas
    ↓
SIMULADOR DE EJECUCIÓN PAPER: fill de entrada por bid/ask real del instante
    ↓
GESTOR CIBO: SL/TP, parcial, break-even, trailing, salida defensiva
    ↓
EVENTOS DE FILL/FEES/REALIZED P&L + MARK-TO-MARKET
    ↓
LEDGER ÚNICO: QORE NAV, balance, equity, broker margin, 4 motores,
               presupuesto de riesgo dinámico en cada nueva señal
    ↺ siguiente evento causal de las 3.368
```
CIBO elige política, órdenes administrativas e intención económica. QDLE **nunca delega** el volumen. El simulador paper no puede fabricar fills para propuestas no financiables. La ejecución en broker real requiere contrato separado, autorización externa y certificación independiente; no se incluye en este P0.

**Contrato 5 %:** por cada propuesta `all_in_risk_usd = lots × (loss_to_executable_stop_per_lot + roundtrip_commission_per_lot + conservative_cost_buffers_per_lot) ≤ QORE_NAV_at_decision × native_mode_fraction`; también ≤ disponibilidad disponible tras posiciones/reservas/fuentes. El límite global soberano nunca excede 5 % del NAV, pero BANK 1,25 % y MEDIUM 2,5 % pueden reducirlo. Si `min_lot` incumple presupuesto, devolver `UNFUNDABLE_MIN_GRID` sin alterar la señal ni abrir lote ficticio. No tratar el coste de swap futuro sin datos como 0 realizado; distinguir reserva de estimación y swap observado.

## 2. Reutilizar motores existentes (no duplicar)
| Componente existente | Estado verdadero | Conexión exigida |
| --- | --- | --- |
| `src/qore/infrastructure/cibo_native_mode_authority.py` | Emite y verifica BANK/MEDIUM/ATTACK nativo sellado; define política de salida experimental | Cada operación preserva `decision_digest` + `signal_fingerprint` |
| `src/qore/infrastructure/cibo_native_sovereign_qdle.py` | QDLE shadow, presupuesto Native MAX, cuatro motores; 0 broker SEND | Conectar el quote al ejecutor PAPER tipado |
| `src/qore/infrastructure/qore_dynamic_lot_engine.py` | Motor físico con reservas, recibos, libro y reconciliación | Instantánea broker pre-evento, rechazo exacto, idempotencia, concurrencia |
| `src/qore/infrastructure/cibo_managed_exit_replay.py` | **Ya implementado y probado aisladamente:** bid/ask OHLC, parciales, BE, trailing, defensa, SL/TP, gap, stop-first; status `SHADOW_SETTLED` o `NEEDS_PRICE_PATH` | Integrar a cartera cronológica; separar comisiones al fill; convertir su resultado a eventos sin doble cargo |
| `scripts/cibo_p0_native_managed_exit_path_audit.py` | Une barras por señal, genera auditoría **solo subconjunto**, explícitamente no ledger NAV global | Reusar validación/procedencia; ampliar cobertura y no reconocer P&L incompleto |
| `scripts/qdle_3368_dual_ledger_replay.py` | 3.368 cotizaciones, no settlers, resultados financieros gestionados nulos | Reutilizar parser/evidencias, pero ejecutar NUEVO brazo secuencial, nunca mutar el reporte quote-only |
| `tests/infrastructure/test_cibo_managed_exit_replay.py` | Casos aislados existentes pasan en CI anterior | Extender por integración E2E y treasury/contabilidad |

La fase P0 siguiente es **la integración temporal/contable**, no empezar desde cero un motor de salidas inexistente.

## 3. Evidencia de mercado obligatoria y fail closed
1. `signal_fingerprint`, `trader_id`, `symbol` canónico y símbolo MT5 exacto, `side`, `signal_at`, `cibo_decided_at`, `mode_digest`, geometry SL/TP y `quote_timestamp` en UTC tz-aware.
2. Dataset **histórico real**, fuente y checksum SHA256 por segmento de precio; `bid` y `ask` por tick o OHLC ejecutable no sintetizado desde MID; timestamp, zona, precisión, session/trading status; metadatos de contrato, currency, tick value y spread. Separar `BROKER_HISTORICAL_BID_ASK_RESEARCH_UNVERIFIED` de `SYNTHETIC_TEST_FIXTURE`: un fixture jamás certifica beneficios históricos.
3. Para el intento de apertura: precio ejecutable `ask` para BUY, `bid` para SELL **después** de la decisión; no utilizar `intended_entry` como fill si no es ejecutable en la trayectoria. Guardar retraso causal y reglas deterministas de slippage/latencia; si no hay precio en ventana permitida → `NO_EXECUTABLE_ENTRY`.
4. Tras fill debe haber trayectoria consecutiva hasta salida final o fin de observación; faltas/solapamientos/datos anómalos → `NEEDS_PRICE_PATH` o `INCOMPLETE_POSITION`, P&L correspondiente desconocido; no estimar TP/SL a partir de R histórico Trader.
5. Datos económicos históricos por instrumento, hora y tipo de cuenta: `commission_open`, `commission_close`, swap, cambio divisa, tick/contract value, stop/freeze level, lot grid, max volume, margin; todo con `as_of` y fuente. Capturas MT5 **2026** son proxies, no tarifas verificadas para 2019–2022. Sin comisiones verificadas, etiquetar `COST_PROXY`, publicar sensibilidades y **NO** `CERTIFIED`.
6. Simultaneidad: ordenar (timestamp UTC, prioridad de eventos definida, signal ID determinístico). Causalidad: los fills y fees conocidos a tiempo t afectan las siguientes decisiones, nunca la cognitiva predecisión con eventos posteriores.

**Regla de publicación:** si no existe evidencia bid/ask histórica completa para las operaciones consideradas, mantener salida `PARTIAL_COVERAGE_RESEARCH`; NAV/DD/PF completo = `null`, y reportar explícitamente muestra cubierta/no cubierta, sin atribuir al conjunto el resultado del subconjunto.

## 4. Máquina de estados de la operación, con causalidad temporal
```text
SIGNAL_RECEIVED → CIBO_COGNITION_COMMITTED → ECONOMIC_MOTORS_COMMITTED
→ QDLE_QUOTED | QDLE_UNFUNDABLE
→ PAPER_ORDER_SUBMITTED → PAPER_FILLED | PAPER_REJECTED | PAPER_EXPIRED
→ POSITION_OPEN → (PARTIAL_FILL, STOP_AMENDED, MARK, FEE, SWAP)* 
→ POSITION_CLOSED → CIBO_SETTLEMENT_POSTED → QORE_NAV_RECONCILED
```
Transiciones invariantes:
- No `PAPER_FILLED` sin quote positivo vigente, mismo `signal_fingerprint`, digest CIBO y reserva QDLE. Un resultado de `reserve_for_trader` **no** es un fill. Las propuestas expiradas se liberan y no se contabilizan como operación.
- Dirección BUY: entrada ASK, salida BID, SL/TP activados por BID. SELL: entrada BID, salida ASK, SL/TP activados por ASK. El stop puede tener ejecución peor en gap; nunca garantizar precio SL si la apertura cruza adversamente. Spread/ejecución no son ganancias implícitas.
- Para barras OHLC de orden intrabar desconocido, conservar convenio adverso `STOP_FIRST`; las acciones cognitivas calculadas al cierre de barra solo entran en vigor en la siguiente apertura, con timestamp registrado; ticks permiten orden observado, no reconstruido.
- Parciales únicamente si volumen de cierre y remanente cumplen grid y min lot; si no, `PARTIAL_SKIPPED_BROKER_GRID`, no redondear el restante a una posición imposible. Una misma cantidad nunca se liquida dos veces.
- TP, SL, BE, trailing, defensa son decisiones/órdenes CIBO evidenciadas. La política nativa inicial no equivale a decisión posterior efectiva de CIBO: registrar `decision_at`, `observed_up_to`, `action_effective_at` y razón.
- Solo cerrar posición cuando `remaining_lots == 0` con evidencia válida de precio y fee. Una posición que sigue abierta participa en equity MTM; no se inventa settlement al final de archivo.

## 5. Libro único de eventos y fórmulas económicas
Dos libros **separados pero conciliables**:
- **Broker ledger**: balance, equity, free margin, posiciones, crédito, comisiones, swaps y movimientos de caja observados del broker; instantáneas y event IDs.
- **QORE capital ledger**: capital económico propietario, fuentes Bank/Cushion, NAV, commitments/reservas, realized/unrealized; nunca equiparar USD2.000 broker deposit con USD60 presupuesto QORE; ni copiar P&L de control Trader.

Evento canónico inmutable: `event_id`, `signal_fingerprint`, `position_id`, `event_type`, `effective_at`, `observed_at`, `source_sha256`, `native_mode_digest`, `qdle_quote_id`, `broker_spec_digest`, `currency`, `lots_delta`, `cash_delta_usd`, `fee_open_usd`, `fee_close_usd`, `swap_usd`, `mark_bid`, `mark_ask`, `sequence`, `simulation_kind`. Dedupe por `event_id` y `position_id + broker-deal-id` si existe; monotonic event sequence; hash chain antes/después del NAV.

- BUY gross realized = `(exit_bid - entry_ask) × USD_pnl_per_unit_per_lot × closed_lots`.
- SELL gross realized = `(entry_bid - exit_ask) × USD_pnl_per_unit_per_lot × closed_lots`.
- `net_realized = gross_realized - commissions_at_fills - swap_debits + swap_credits - other_fees`; comisiones de apertura se debitán **cuando se abre**, cierre al cerrar/parcial; no volver a debitar `roundtrip_commission` usado previamente solo como **reserva de riesgo**.
- `NAV_QORE(t) = capital_inicial + realized_net_cumulative + unrealized_net_MTM(t) + external_net_transfers_verificados(t)`, según política documentada de atribución; `cash_balance_QORE` también explícito. El riesgo de nuevas entradas usa NAV reconciliado **en ese instante**, menos exposición y reservas conforme a política de presupuesto/fuente.
- `equity_MTM(t)` usa BID para liquidación de BUY y ASK para SELL y costes de cierre esperados revelados como estimación; incluir open-trade drawdown, no solo closed NAV. `max_drawdown = max_t[(running_peak_equity(t)-equity(t))/running_peak_equity(t)] × 100`. Informar además DD sobre balance cerrado como métrica secundaria con nombre distinto.
- PF = ganancias netas positivas de posiciones **cerradas** / valor absoluto de pérdidas netas negativas; declarar tratamiento de trades con net 0 y PF indefinido cuando denominador = 0. Win rate = cierres con net >0 / cierres totales. Reportar total `P&L` por modo, activo, Trader y cartera, reconciliado con suma cashflows. No computar PF o win rate de solo cotizaciones.
- El valor por tick/contrato y conversiones multi-moneda deben ser trazables a cada época y broker, no usar multiplicadores 10.000× abstractos ni ganancias del Trader CONTROL para justificar management.

## 6. Feed → replay de cartera: pseudoflujo obligatorio
1. Congelar input: SHA-256 de 3.368 oportunidades originales, código/commit, cognitiva, políticas, condiciones broker históricas, trayectorias, comisiones; manifest experimental sin leaks.
2. Formar una cola global de eventos ordenados por tiempo: nuevas oportunidades, ticks/barras, fills simulados, modificaciones de stops, tarifas, swaps, expiraciones, cierres y reconciliaciones.
3. En cada timestamp, primero procesar eventos efectivos y observables hasta ese instante; actualizar posiciones, fees, margen, cash/equity y fuentes; obtener `QORE_NAV_at_decision` conciliado.
4. Ejecutar cognitiva CIBO causualmente solo con información observada ≤ hora de decisión (si reutiliza sellos Native MAX antiguos, identificarlos como recibos de escenario y **no atribuir a una nueva reevaluación sobre NAV modificado**). CIBO asigna modo y acciones.
5. Solicitar cuatro votos/autoridades y QDLE sobre NAV actual; mantener `UNFUNDABLE` si riesgo all-in, min lot, margen, cuenta stale, grid o fuente lo impiden; nunca forzar el lote.
6. Conectar cotización con precio bid/ask futuro causal para el **fill PAPER** y abrir. Descontar comisión OPEN, reservar coste CLOSE y gestionar todos los abiertos en paralelo, con decisiones/acciones progresivas del CIBO.
7. Al parcial o salida total, generar un único conjunto idempotente de `FILL`, `FEE`, `REALIZED`, `POSITION_UPDATED`, `CAPITAL_RECONCILED`; liberar reservas y notificar a los cuatro motores para la próxima oportunidad.
8. Al finalizar, posiciones todavía abiertas → marcada MTM con datos válidos y reportar abiertas; operaciones con faltantes → `INCOMPLETE`/no certificación. Publicar métricas solo con cobertura/calidad suficientes, de modo trazable.

## 7. Condiciones mínimas de aceptación y suite CI P0
**A. Verdad histórica/cobertura:** exactamente 3.368 identidades únicas; tasa `Native-issued modes/QDLE accounted = 3.368/3.368`. Toda operación PAPER de lote positivo tiene `entry_bid_ask_evidence`, `exit_path` (o queda OPEN/INCOMPLETE explícita). Sellos/digests y reloj verificados, fuente declarada; ninguna señal inventada o omitida.

**B. Física y fuente:** todas las aperturas satisfacen QDLE con 5 % NAV vigente y BANK/MEDIUM/ATTACK fracción correspondiente, SL+roundtrip+buffer, margen disponible, riesgo global concurrente, broker min/max/step, moneda, límites de instrumento. Matrices de prueba 0,01 lote; pérdidas grandes por gap pueden **exceder** presupuesto previsto sin demostrar que QDLE dimensionó mal: informar breach realizado y mecanismo de gap, jamás suavizarlo.

**C. Gestión:** tests BUY y SELL, TP/SL en misma barra (stop-first), gaps adversos, parciales rechazados por grid, BE, trailing, cierre defensivo, múltiples posiciones simultáneas, empate de timestamps, invalidación y expiración de quote, duplicados de fees, swap overnight y conversión FX. Control anti-leakage sin convertir `Trader gross_structural_outcome_r` en settlement.

**D. Contabilidad y resultados:** conservar invariantes `NAV_post - NAV_pre == validated_cash_and_MTM_delta`, comisiones OPEN en apertura y CLOSE en cierre, fee estimate ≠ fee debited; `sum(closed_trade_net) + unrealized` concilia con estado capital, comisiones y swaps; sin exposiciones negativas, sin reservas duplicadas; reproducibilidad SHA256/seed y pruebas de orden de eventos.

**E. Bandera de completitud/certificación:** si faltan tracks históricos de cualquier operación incluida, reporte `COVERAGE_INCOMPLETE` con indicadores de cobertura; no generar `managed_final_NAV`, `managed_full_DD`, `managed_full_PF` globales aparentemente verdaderos. Dataset sintético puede probar *ingeniería* pero nunca certificar la *rentabilidad* de 3.368 entradas. Separar `PAPER_RECONSTRUCTED`, `BROKER_OBSERVED` y `LIVE_VERIFIED`. P0 de investigación no otorga autorización LIVE.

**F. KPI esperado cuando exista evidencia completa:** capital inicial/final, P&L bruto y neto, OPEN+CLOSE commissions debitadas y estimadas, swap, win rate, PF, DD closed/MTM, MAE/MFE, por modo/Trader/símbolo, 3368 intake, lot quotes, unfinanceable por causa, fills, parciales, closes, posiciones abiertas, violaciones broker y de presupuesto, resumen JSON auditable.

## 8. Paquetes de trabajo para el siguiente arquitecto (orden de dependencia)
| Orden | Cambio | Responsable / bloqueo |
| --- | --- | --- |
| P0-1 | Inventario, cobertura y checksums de ticks/bid/ask 2019–2022 para seis símbolos; mapeo exacto de zonas y epoch pricing | **Bloqueador externo**; no inferir de Trader-R |
| P0-2 | Tipar `PaperExecutionFill`/`PositionEvent`/`CiboSettlement`; convertir el simulador `cibo_managed_exit_replay.py` a eventos de fills y gestión conservando semántica actual | Motor ejecución |
| P0-3 | Ledger global QORE/Broker idempotente, capital disponible, comisiones split, swap, cartera MTM | Economía + QDLE |
| P0-4 | Scheduler causal de 3.368 señales y todos los abiertos, política Native MAX y 4 motores con NAV del brazo gestor | Integración CIBO |
| P0-5 | Suites de integración y CI: dataset sintético **solo ingeniería** + evidencia histórica si está disponible; lectura y artefactos con `null` explícitos si falta | Validación |
| P0-6 | Batería científica fresca OOS, DD, PF, stress spread/gap y conciliación con cuenta FundedNext MT5 en READ ONLY | Certificación antes de posible LIVE |

## 9. No negociables
- **No** volver a usar `THREE_SETTLED_LOSSES_HAIR_CUT` basado en operaciones del Trader CONTROL como si fueran cashflows gestionados por CIBO. Las decisiones económicas deben tener autoría de CIBO y proveniencia cronológica.
- **No** quitar grid del broker, necesidad de presupuesto all-in, condiciones de margen ni límites contractuales. Los topes estratégicos investigados PAPER deben distinguirse de reglas del proveedor.
- **No** declarar los 1.961 quotes como órdenes ejecutadas; los 3.368 modos como 3.368 aperturas; comisiones estimadas como pagadas; o NAV=$60 como rentabilidad flat.
- **No** afirmar que un SL corto causa rechazo de BANK basándose exclusivamente en tabla agregada: publicar antes auditoría discriminante de costes, fracciones, lot grid y margen por modo.

**Estado de esta especificación:** documenta un trabajo P0 **pendiente**, con un motor aislado existente de cierres causales y pipeline de lotaje ya verificado; no constituye su implementación ni su ensayo integrado de cashflow.

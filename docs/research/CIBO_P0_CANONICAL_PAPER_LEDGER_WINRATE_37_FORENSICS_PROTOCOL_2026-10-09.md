# QORE CORE · P0 — UNA autoridad PAPER antes de diagnosticar el 37% de win rate
**Fecha:** 2026-10-09 · **PR receptor:** #746 → #745 · **Entorno:** GitHub Actions / Trader Lab exclusivamente · **Prohibido:** VPS, broker LIVE, MT5 order_send.

## Decisión de prioridad
La infraestructura financiera NO se considera reparada mientras coexistan dos implementaciones independientes de reservas PAPER. **Orden obligatorio: P0-A autoridad única → P0-B nuevo replay exact-SHA → P0-C diagnóstico MFE/MAE/SL→TP → P0-D evaluación cognitiva Native MAX.** Ningún PF, win rate, DD o saldo se proclama comparable antes de A/B. El objetivo NO es maximizar entradas ni modificar agresividad para encubrir pérdidas: primero identificar el edge neto y los errores causales por tipo de señal.

## P0-A — Arbitraje y unificación física
Las dos ramas inspeccionadas el 9 de octubre divergen:
- #745 `src/qore/infrastructure/qdle_paper_book.py::PaperQDLE` con estados `PAPER_FILLED`, instantáneas externas de posiciones/riesgo y métodos broker vetados.
- #746 `QDLE(research_paper_mode=True)` con estados `PAPER_OPEN`, riesgo/margen pendientes atómicamente en SQLite y marcador de base de datos exclusiva research.
- Ambas rutas NO son intercambiables y no deben registrar la misma cartera. Ver [arbitraje detallado](CIBO_P0_GITHUB_PAPER_QDLE_BRANCH_DIVERGENCE_ARBITRATION_2026-10-09.md).

**Contrato del integrador:** escoger UNA implementación canónica, retirar/relegar claramente la otra a `LEGACY_NOT_CALLED`, una sola fábrica/instancia por `simulation_run_id/account_id`, un único `request_id` por señal y un único cálculo de `risk_held`, `margin_held`, `free_source` y `NAV` en cada epoch. Una posición PAPER abierta debe reducir presupuesto de próximas señales exactamente una vez, tanto después de reinicio como en dos procesos concurrentes. Sólo se libera reserva por `PAPER_SETTLE`/NO_FILL causal idempotente, nunca por expectativa de TP o por ausencia de precio. Un expediente `UNASSESSABLE` por geometría/dato inválido **no** prueba un lotaje mínimo físicamente evaluado. Las llamadas `acknowledge_fill`/broker-deal real están prohibidas en replay. La DB PAPER no puede volverse LIVE por instanciar la clase equivocada.

**Gates de aceptación A:**
1. `3368 == len(unique_input_fingerprints) == len(output_signals)`; para cada señal, estado: `UNASSESSABLE`, `QDLE_UNFUNDABLE`, `NO_FILL`, `PAPER_OPEN`, `PAPER_SETTLED` o error explícito; ningún descarte silencioso.
2. `sum(risk_held)` y `sum(margin_held)` coinciden con la contabilidad de una sola DB. Reservas idempotentes, reinicio, dos operaciones simultáneas, márgenes diferentes, fill parcial, cierre y no-fill. Si la física no puede probarse, la simulación **FAIL**, no adoptar su curva.
3. Igual `input_sha256`, `market_data_sha256`, `fee_schedule_sha256`, `settings_sha256`, `code_commit`, `ledger_schema_version` y orden temporal para comparar runs. Si cambió cualquiera de estas dimensiones, la diferencia de PF no identifica causalmente un solo cambio.
4. 0 operaciones LIVE y 0 validaciones ficticias de broker; riesgo all-in por apertura `<= 0.05 * QORE_NAV(t)` y margen/grid/fee vigente. No imponer filtros estratégicos heredados como `THREE_SETTLED_LOSSES_HAIR_CUT` o umbrales globales arbitarios sin evaluación explícita de CIBO.
5. Prueba diferencial en el MISMO conjunto congelado: código con libro A vs B (sólo si ambos son financieramente consistentes) vs libro canónico; reportar divergencia por señal en `lots, risk_held, margin, open/close, cash`. Los replays previos sin `ledger_authority+ledger_sha` se catalogan `NON_COMPARABLE`.

## P0-B — Replay canónico sin look-ahead y sin falsas certificaciones
- Replay nuevo **exact SHA** sobre las 3.368 señales. La cuenta QORE inicia en USD60 y su tope es 5% dinámico del NAV actual, incluyendo stop, roundtrip y buffers; broker USD2000 constituye cuenta/margen distinta.
- Todos los eventos se ordenan por timestamp observable, **no por su desenlace**. En cualquier decisión T se permiten únicamente OHLC barras cerradas `closed_at <= T` o ticks realmente observados `timestamp <= T`. La apertura futura M5 puede utilizarse como fill PAPER posterior, NUNCA como precio predecisión. Si los datos pre-T son insuficientes, recibo `UNASSESSABLE_NO_CAUSAL_QUOTE`.
- Cotejar `opened`, `settled`, `open_incomplete`, `unassessable`, `unfundable`, `rejected`; `opened >= settled`. Mantener 3368 expedientes completos. Guardar JSON, SQLite, checksum, costos, slippage, spread, dirección y snapshot del NAV por operación.
- El precedente documentado del handoff fue **539 abiertas / 537 cerradas**, no 540 cerradas. La cifra del 37% debe recalcularse con el set de cierres del *nuevo* replay, e identificar si 37% representa exactamente `wins / (wins+losses+breakeven)` o un redondeo. No comparar con el 2019–22 si el input/costos no son idénticos.
- Los datos Market Atlas son OHLC M5 con spreads fijos extrapolados de octubre de 2026: sin histórico broker BID/ASK verificable, `historical_broker_certified=false`. La falta de marcas intermedias impide reconstruir secuencia intrabar exacta. **STOP-FIRST** ante SL/TP en una misma vela; preservar etiqueta `INTRABAR_ORDER_UNKNOWN`.
- Grabar PF y win rate netos solo para cierres efectivamente simulados, comisiones/cashflow OPEN/CLOSE contados una vez. DD principal `max running_peak(equity MTM) - equity MTM`; si faltan precios de cartera abierta, `full_MTM_DD=null`. El DD solo-caja es un indicador secundario y no equivalente.
- **Criterio de verdad:** nunca afirmar que corregir look-ahead mejoró o empeoró PF sin la comparación exacta del mismo dataset. Un sesgo puede ser favorable o desfavorable.

## P0-C — Explicación científica del 37%, NO optimización de filtros
Auditar **cada** posición cerrada del nuevo replay, con estados separados `COVERED/INCOMPLETE/AMBIGUOUS`. Guardar por `signal_fingerprint`:
- `symbol`, `Trader`, `mode`, dirección, hora de señal/decisión/fill y fin, versión de libro, lotes, NAV, entrada **ASK BUY/BID SELL**, SL original y móvil, TP, causa exacta de salida, comisión OPEN+CLOSE+swap, ganancia bruta/neta, `win/net_loss/breakeven`.
- `MFE` máximo avance favorable **hasta salida**, `MAE` máxima excursión contraria **hasta salida**, distancia en precio, múltiplos `R` del stop original (y USD a volumen efectivo); comparar ganadoras/perdedoras con medias, medianas, P25/P75/P90 y colas, **no solo promedios**.
- En M5 sin secuencia intrabar, publicar `mfe_r_lower_bound`, `mfe_r_upper_bound`, `mae_r_lower_bound`, `mae_r_upper_bound` (la vela terminal pudo tocar extremos DESPUÉS del stop). Reportar cobertura, no fabricar “MFE exacto antes del SL”. Cuando existan ticks broker cronológicos se podrán computar valores exactos; no mezclar con OHLC.
- Causa de salida: `STOP_FIRST_OR_SL_ONLY`, `GAP_OPEN_STOP`, `OPEN_GAP_AFTER_STOP_UPDATE`, `TAKE_PROFIT`, `GAP_OPEN_TARGET`, `DEFENSIVE_CLOSE_NEXT_OPEN`, parcial, BE/trailing, timeout/incompleto; desagregar win rate/PF y magnitudes por causa, símbolo, Trader, sesión y modo.
- `SL luego TP`: SOLO observación **POST-SALIDA**, desde el primer bar completo posterior a la vela de stop; ventanas 1h/4h/24h (o parámetros explicitados). Si el mismo OHLC tocó SL y TP, registrar `INTRABAR_AMBIGUOUS`, jamás sostener que tocó uno antes del otro. Si falta trayectoria continua hasta ventana, marcar `UNKNOWN_COVERAGE`. Registrar sí/no solo en ventanas con cobertura completa o con toque posterior inequívoco.
- Duración de trade (minutos) total y estratificada ganadoras/perdedoras, exposición simultánea, sesión, spread, gap, comisiones USD y costo/R. Detectar asimetría de perdedoras tempranas vs ganadoras lentas y SL→TP sin ajustar regla basada en resultados futuros.
- Modelo de breakeven antes de optimizar: `p_break_even = average_net_loss_abs / (average_net_win + average_net_loss_abs)` para medias de netos reales; PF `sum(net positive)/abs(sum(net negative))`; comparar `win_rate` con `p_break_even` y muestras out-of-sample. Calcular Wilson/IC bootstrap por cohorte, tamaño muestral y sensibilidad a spreads/fees, evitando sobreajuste.

### Tablero P0-C obligatorio
| Corte | Salida |
|---|---|
| Universo | `signals=3368`, `opened`, `closed`, `unresolved`, `unfundable`, `unassessable`, sin duplicados |
| Beneficio neto | `win_rate_pct`, `profit_factor`, `avg_win_usd`, `avg_loss_usd`, `breakeven_win_rate_pct`, `net_expectancy_usd` |
| Geometría | `MFE_R_lower/upper mean,p50,p75,p90`, `MAE_R_lower/upper mean,p50,p75,p90` por resultado, símbolo/Trader |
| SL→TP posterior | `n_stop`, `post_stop_hit_TP_1h/4h/24h`, `NO`, `UNKNOWN`, `AMBIGUOUS_same_bar`; denominador visible |
| Tiempo | `duration_minutes_mean/p50/p90` para ganadoras/perdedoras, por motivo de salida |
| Calidad | `price_path_covered_count`, `tick_exact_count`, `OHLC_bound_count`, `missing_path_count`, `source_sha`, `ledger_sha`, `code_sha` |

## P0-D — Recién después, CIBO Native MAX
Reinvocar cognitiva usando solamente evidencia causal validada, no el resultado final del trade; reevaluar cuatro motores, riesgo físico QDLE, y posterior gestión de la posición. La auditoría histórica MAE/MFE sirve para **investigación y diseño**, NUNCA como feature de la misma señal pasada. Separar calibración en muestra de validación temporal estricta y OOS congelada, con todos los costos; comparar edge A/B e impacto por motivo. El 37% de aciertos **no prueba por sí mismo ausencia de edge**: depende del payoff por operación y costos. PF < 1 sobre conjunto representativo sí indica pérdida neta histórica en ese conjunto.

## Política de publicación de conclusiones
- Sin una autoridad PAPER canónica: **REJECTED_LEDGER_DIVERGENCE**.
- Con autoridad única pero ausencia de trayectoria/fees: **PARTIAL_COVERAGE_RESEARCH** y globales completos = `null` cuando corresponda.
- Sin recibos Native MAX y cuatro motores frescos: **NOT_CIBO_CAUSAL_CERTIFIED**.
- Con M5/proxy 2026: **SHADOW_SYNTHETIC_BIDASK**, nunca `REAL_HISTORICAL_BROKER_PNL`.
- Publicar el mismo artefacto completo (incluido errores), checksums, denominadores, y controles de reproducibilidad antes de toda afirmación de PF/DD/win rate mejorado.

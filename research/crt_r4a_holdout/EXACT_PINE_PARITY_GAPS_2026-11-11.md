# QORE CRT R4-A — mapa de diferencias entre el Pine original y replay exploratorio

Fecha 2026-11-11 · Auditoría técnica de código · **QA / NO LIVE / NO MERGE / NO VPS**

## Fuentes inmutables

- Pine R4-A SHA Git blob `693e3f49719e86e2ea0702f7b355af33bd0c4c7c`, `mezas3238-hue/qore-deepseek-reviewer`, archivo `crt-radar-pro/qa-integrated-34/QORE_CRT_34_R4_AB_400_M5_AUTO_BUFFER_QA.pine`.
- Trader experimental `research/crt_r4a_holdout/archived_2y_strategy_proxy.py` y medición real 33 mercados [run #43094233453](https://github.com/mezas3238-hue/qore-core/actions/runs/43094233453).
- **No se permite copiar etiquetas “MSS CONFIRMED”, “HOLDOUT PASS” o “PF neto” de la aproximación al detector original.**

## Diferencias concretas auditadas

| Regla | Pine R4-A original | Proxy Python actual | Resultado |
|---|---|---|---|
| Barra observable | `time[1]`, `time_close[1]`, `high[1]`, `low[1]`, `close[1]`; continuidad `time_close[2]` [Pine L547–560] | Listas históricas M5 en orden, sin replicar completamente semántica de estado Pine en toda la serie | **NO PARITY** |
| H4 de proveedor | `f_forex_metal_crt_h4_ny`, `f_index_crt_h4_ny`, BTC propio; fase M5 por símbolo `qaNativeSourcePhaseMin` [L944–951] | Agrupador NY heredado de PR #1004; no homologa cada desfase M5 ni feed TradingView | **NO PARITY** |
| Pivote M5 | `ta.pivothigh(high,left5,right5)`, `ta.pivotlow`, y swing confirmado retrospectivo `lastHigh5At = time[right5+1]` [L719–723, L2030–2035] | Aproximación mediante extremo de las últimas 8 M5 previas a barrida en `mss5_within` | **DISTINTO** |
| Pivote M15 | M15 reconstruida de **tres M5 cerradas**, pivote estricto L/R, extremos previos a la barrida `lastHigh15At/lastLow15At` [L1010–1045] | Aproximación a partir de 9 barras M5 previas, que **no equivale a swing M15 confirmado** | **DISTINTO** |
| 2C + MSS15 | `c2StrictSweep`, pivote M15 congelado pre-sweep, MSS tras barrida, M15 continuo con fase precisa; entrada `outPhase==2, outValid, CRT_2C_RETURN, verifiedM15At` [L1035–1044, L1930–1974, L2101–2120] | `sweep_info` geométrico H4, `mss15_c2_c3` con pivote de 9 M5 | **NO CERTIFICADO** |
| TRUE3C + MSS5 | C2 H4 interior, C3 barrida unilateral, C3 cerrado y fuente propia de pivote confirmado; sin doble sweep; `qaTrue3CConfirmed` [L1342–1370, L1806–1829, L1990–1997] | `candidates` + `mss5_within` aproximado; no comparte la máquina de estados completa | **NO CERTIFICADO** |
| Momento ejecutable | `max(cierre C2 o C3 H4, cierre MSS de la misma estructura)` después de preservar `time[1]` y `barstate.islast` | `Candidate.available_at` aproximado; sin cotización ejecutable posterior validada contra feed | **VALIDAR** |
| SL, TP, fill | El Pine es **indicador**, no contiene algoritmo de trading / orden de broker | Entradas 50 % cuerpo C2/C3, ATR14/0.25 buffer, TP C1, expiración 12h, OHLC mids, sin Bid/Ask | **HIPÓTESIS EXÓGENA** |
| Costos y riesgo | Sin PnL ni sizing del indicador | R bruto sobre OHLC, sin spreads/comisiones/slippage/swap ni cartera | **NO PF NETO / NO CAPITAL** |
| BTC | Fuente IC:BTCUSD con reglas BTC H4 propias | No hay artefacto original de BTC en run 35166210458 / 38193802541 | **33/34** |

Las líneas son referencias del Pine fijado en SHA. El port exacto necesitará también reproduccir `session.isfirstbar[1]`, `session.islastbar[1]`, la invalidación por doble barrida, la ventana de antigüedad de pivote, segmentos M5, continuidad DST y el ciclo de reseteos de C1.

## Dictamen sobre 2024–2025

**PERÍODO UTILIZADO / BURNED PARA INVESTIGACIÓN CRT.** La ejecución #43094233453 examinó operaciones de estos modelos aproximados y se reportaron PF/R brutos positivos y negativos. Por ello el manifiesto del trader declara `window_consumed_for_crt_research=true` y `runner.py` impide presentarlo después como holdout intacto, aunque se manipulara una bandera de atestación. Los resultados permanecen válidos solo como exploración retrospectiva.

## Orden de cierre técnico verificable

1. Portar `f_engine()` y sus UDT solo en el modelo de investigación, manteniendo el Pine R4-A inmutable; reproducir M5 previas cerradas, pivotes confirmados L/R en M5 y M15, estructura NY y las 7 categorías. Primero lograr **mismos eventos y timestamps en un feed**, no optimizar PF.
2. Exponer ledger causal separado de snapshots de `barstate.islast`: `event_id, symbol, model, side, c1_at, sweep_at, ratified_at, mss_at, available_at, c1_high, c1_low, sweep_high, sweep_low, mss_pivot`.
3. Ejecución `parity_gate.py` = igualdad exacta de eventos y precios en **mismo feed** con `0` falsos positivos, `0` ausentes y `0` señales anticipadas.
4. Importar bid/ask real, comisiones por contrato, swaps y pruebas conservadoras de SL/TP mismo intervalo; simulación con sizing y correlación 34 mercados. Si no existe archivo, marcar **NO COST CERTIFICATION**.
5. Conseguir BTCUSD con compatibilidad de proveedor o reconocer **33/34**; sin imponerle velas de Coinbase arbitrariamente al `IC:BTCUSD`.
6. Pre-registrar un nuevo período de **24 meses no consumidos**, sin reoptimizar contra 2024–2025. Si no se demuestra independencia, el resultado es **REPLAY RETROSPECTIVO / NO HOLDOUT VIRGEN**.

**Estado actual:** reales 33/34 replay exploratorio ejecutado, paridad completa `f_engine()` no construida; no posible certificar rentabilidad ni arriesgar capital.

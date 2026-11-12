# QORE CRT R4-A — evidencia individual de las siete familias

**Corte 12 de noviembre de 2026 UTC. Investigación, NO LIVE, NO VPS, NO MERGE.**

## Ejecución fuente

- GitHub Actions **SUCCESS** [#43132808359](https://github.com/mezas3238-hue/qore-core/actions/runs/43132808359), base de código fuente `21e7d521cc0ef665cf102514c2a65f74b482aa3a`.
- Artifact de la ejecución: `qore-crt-r4a-seven-family-33-market-causal-events-no-pnl`, ID `13905847539`, expira 2026-12-12.
- ZIP íntegro descargado y auditado: SHA-256 `ab05bd0aef112d8d58f3335c073e016cbf96f2459fac78225decbf77166c657c`.
- `all_events.jsonl` SHA-256 `fdb52b1bacb042fb087234a5766b14452879915b839a67c099c5cee41e483296`, **23.919 eventos**.
- Archivos en el ZIP: `summary.json`, `summary.md`, `all_events.jsonl` y 33 `events_by_symbol/<SYMBOL>.jsonl`. Cada cinta por símbolo fue reconciliada por SHA, identidad, proveedor y familia.
- M5 originales: **4.890.804**; **33/34 símbolos**, con **21 IC Markets DEMO** y **12 Atlas NO homologados**; falta BTCUSD.

## Conciliación exacta por familia (eventos, NO operaciones)

| Familia | Identidades individuales |
|---|---:|
| F1 — CRT 2C MSS15 C2 | 4.266 |
| F2 — CRT 2C MSS15 C3 | 7.966 |
| F3 — TRUE 3C MSS5 | 1.748 |
| F4 — Inside Return MSS propio | 554 |
| F5 — Multi4 MSS propio | 647 |
| F6 — Multi-N MSS propio | 369 |
| F7 — Retest M15 vinculado a CRT padre | 8.369 |
| **Total de observaciones potencialmente superpuestas** | **23.919** |

**Controles adicionales auditados:** 23.919 identidades únicas por símbolo/familia, 8.369 retests con padre concreto dentro de la misma cinta combinada, SHA de `all_events.jsonl` igual al declarado en `summary.json`. Un retest no toma prestado un MSS de una estructura diferente. El ledger conserva las 7 categorías independientes de investigación.

## Descubrimiento crítico: unidades de precio del archivo original

Las barras de la fuente cTrader son **enteros nativos relativos** (`low_relative`, `delta_open`, `delta_high`, `delta_close`), reconstruidos exactamente desde el manifiesto de origen. Por contrato oficial de cTrader, **precio cotizado = valor relativo / 100000**, redondeado a los `Digits` del símbolo.

Fuente técnica oficial: https://help.ctrader.com/open-api/symbol-data/

Ejemplos **solo de decodificación de unidades**, NO precios para operaciones ni confirmación de Digits del broker:
- AUDCAD: `90577` en unidades nativas equivale a `0.90577` antes de redondeo a Digits.
- USDJPY: `14167200` equivale a `141.67200` antes de redondeo.
- XAUUSD: `203466000` equivale a `2034.66000` antes de redondeo.
- USTEC: `1656000000` equivale a `16560.00000` antes de redondeo.

**No inferir Digits, TickSize, multiplicador de contrato, moneda de PnL, swaps o bid/ask a partir del símbolo.** `ctrader_native_price_units.py` conserva el número fuente y permite conversión Decimal únicamente con metadatos explícitos de proveedor (`provider_symbol_id`, `digits`, `tick_size`, hash de origen), rechaza incongruencias de tick y nunca marca la operación certificada. Para los 12 Atlas sigue faltando equivalencia con IC Markets.

## Qué falta para backtest económico y certificación

1. Congelar H4 completo de cada evento: `setup_open/setup_close`, extrema de la vela de barrida propia (Multi4 requiere C2a), ATR causal y período de cálculo. El ledger de hoy **no** llena estos campos con suposiciones.
2. Proveedor autenticado: `Digits`, `TickSize`, instrumento canónico, multiplicador, unidades y moneda de cuenta. Coincidencia exacta de feed con IC Markets/TradingView.
3. Cotizaciones históricas bid/ask y costos efectivos con timestamps. Las barras M5 OHLC nativas NO son una cinta bid/ask.
4. Replay de entradas/SL/TP, slippage, spreads, swaps, fees, desenlaces, sin solapamientos ni lookahead; transformar a R y a moneda de cuenta con tasas de FX y especificación contractual verificadas.
5. Identidad de evento contra `f_engine()` Pine por símbolo/fase/DST: todavía NO hay 0 discrepancias certificado.
6. BTCUSD y validación real de 34/34 instrumentos.
7. Holdout verdaderamente nuevo de 24 meses, posterior al congelamiento del modelo: **2024–2025 ya consumido para desarrollo**.

**Conclusión científica:** se completó el registro auditado de 23.919 eventos causales en 33 fuentes. **Cero operaciones históricas económicas certificadas, cero órdenes broker, PF neto/DD/PnL no disponibles, 24 meses OOS no examinados.** El artefacto es una base reproducible para preparar los insumos de simulación, no evidencia de rentabilidad.

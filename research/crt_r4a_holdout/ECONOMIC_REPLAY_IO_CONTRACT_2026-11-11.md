# QORE CRT R4-A — contrato del replay económico experimental

Corte: 11 de noviembre de 2026. **QA / NO LIVE / NO DEMO BROKER ORDERS / NO VPS / NO MERGE.**

## Propósito y límites

Esta interfaz ejecuta **una prueba de órdenes simuladas** con siete familias CRT a partir de señales *ya confirmadas*, geometría propia congelada, cotizaciones **bid/ask M5 reales aportadas como archivo** y costos suministrados expresamente. **No genera señales faltantes a partir del resumen 23.919, no inventa bid/ask desde M5 medio, no demuestra paridad con Pine ni certifica fondos.** El archivo original por instrumento/proveedor no está incorporado a esta rama.

Módulos:
- `economic_replay.py`: contratos `FrozenResearchSignal`, `QuoteEvidence`; seis barreras de identidad/tiempo/cartera; ledger por señal y métricas de las siete familias.
- `economic_replay_io.py`: CLI que requiere manifiesto, entradas, cotizaciones, costos y swap, con SHA256 en los cuatro insumos; publica JSON reproducible.
- `paper_quote_execution.py`: simulador de una sola orden, límite/M15 referencia, bid/ask, SL/TP, comisión/slippage/swap, interrupciones M5, sin API de broker.

La unidad económica actual es **precio cotizado × cantidad introducida**, NO USD de cuenta ni beneficio certificado. No sumar instrumentos de distintas monedas sin conversión de divisas y especificación de contrato; cartera multiactivo sigue pendiente. Los parámetros de entrada/SL/TP son hipótesis de investigación todavía no congeladas contra un verdadero OOS.

## Invocación local (solo cuando existan datos auténticos)

```bash
python -m research.crt_r4a_holdout.economic_replay_io \
  --manifest qa-private/manifest.json \
  --signals qa-private/signals.json \
  --quotes qa-private/bidask_m5.csv \
  --costs qa-private/costs.json \
  --swaps qa-private/swaps.csv \
  --quantity 1 \
  --out qa-reports/seven_family_economic_experiment.json
```

`manifest.json` incluye `symbol`, `provider_cohort`, `source_pine_blob` = `693e3f49719e86e2ea0702f7b355af33bd0c4c7c` y `sha256` con cuatro hashes exactos `signals`, `quotes`, `costs`, `swaps` de los archivos correspondientes. SHA confirma reproducibilidad local, **no certifica origen de broker**.

`signals.json`: array de elementos `symbol`, `provider_cohort`, `family` (literal `Family.value`), `source_event_id`, `direction` (1/-1), `mss_at`, `ratified_at`, `available_at` (ISO con offset), `source_pine_blob`, `atr_h4`, `price_tick`, `geometry` con `c1_high`, `c1_low`, `setup_open`, `setup_close`, `sweep_high`, `sweep_low` **de la misma estructura**. Para F7 también `retest_high`, `retest_low`, `retest_close`, `retest_closed_at` de su propia M15.

`bidask_m5.csv` usa encabezados `opened_at,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close` con precios Decimal y hora UTC/offset. **No reutilizar cierres medios como bid/ask**, ni mezclar atlas/IC sin homologación. `costs.json` requiere `commission_per_unit_per_side_quote`, `adverse_slippage_price` con cifras positivas explícitas; `swaps.csv` requiere `charged_at,quote_amount_per_unit`, sin asumir que ausencia de filas significa swap verdadero cero.

`economic_replay_io` devuelve ledger por evento, resultado por familia, conciliación global y flags invariablemente NO CERTIFICADO: Pine parity=false, provider identity independently certified=false, account currency PnL=false, holdout=false, broker orders=0.

## Qué falta para pasar de experimental a candidato certificable

1. Exportador de cada evento del motor histórico R4-A con OHLC H4/M15, ATR y mss propios congelados. Los agregados sin OHLC/pivotes completos NO bastan.
2. Cotizaciones históricas bid/ask auténticas, esquema de contratos, swap, comisión, spread y moneda por instrumento de IC Markets, con verificación independiente.
3. Matriz 34/34 BTCUSD incluida, y homologación de 12 fuentes Atlas.
4. Port exacto `f_engine()`, paridad 0 diferencias contra Pine, causalidad DST/fase, y pruebas de resiliencia a datos incompletos.
5. Cartera multiactivo con límites de exposición/riesgo, separación TRAIN/OOS y holdout nuevo de 24 meses nunca examinado. **2024-2025 está BURNED y solo puede usarse como investigación retrospectiva.**

No transformar las 23.919 detecciones en trades sin los campos y archivos anteriores. El motor se detiene ante ausencia o discrepancia de datos, no convierte dependencias en ganancias simuladas.


**Política de conflictos experimental:** señales opuestas simultáneas se bloquean; una orden límite pendiente reserva slot por símbolo hasta su expiración; posiciones abiertas hasta salida; empates mismo lado siguen orden fijo de `Family`. La política no es una instrucción broker ni certifica Pine.

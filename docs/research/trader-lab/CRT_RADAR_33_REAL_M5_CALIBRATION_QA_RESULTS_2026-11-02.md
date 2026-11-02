# QORE Trader Lab — CRT RADAR PRO: auditoría real de calibración 33/34

**Fecha: 2026-11-02 | Estado: CALIBRATION_ONLY | No es holdout ni un resultado de rentabilidad.**

**Fuente directa:** [GitHub Actions run #41383370607](https://github.com/mezas3238-hue/qore-core/actions/runs/41383370607) en `agent/crt-radar-trader-lab-34-preflight-20261101`. **33/33 jobs SUCCESS**. Se leyeron M5 reales de **33 archivos originales**, 12 Atlas cTrader DEMO (broker exacto no demostrado) y 21 IC Markets DEMO (catálogo validado). BTCUSD, fuente #34, no está entre esos ZIP y **NO se ensayó con precios reales**.

## Alcance verificable
- Período de calibración **2026-08-01T00:00Z hasta 2026-09-17T00:00Z**. Son históricos utilizados previamente en investigación, **NO un holdout virgen**.
- En cada job se descargó el archivo únicamente al runner efímero del propio QORE Core y se comprobó `RAW_M5_LEDGER/2026.jsonl` contra SHA-256 original de `PARTITION_MANIFEST/2026.sha256`; se eliminaron copias temporales y no se publicaron velas, credenciales ni precios.
- Lectura en unidades enteras nativas del proveedor; H4 reconstruida a partir de M5 cerrado, NY FX 01/05/21 e índices 02/06/22, con 48 M5 contiguas, barrida unilateral y retorno de C2. C3 es **solo seguimiento diagnóstico** sin invalidar el extremo C2. No son operaciones ni confirmaciones MSS M15.
- Alias históricos explícitos: `NAS100→USTEC`, `SP500→US500`. No se ha certificado equivalencia con `OANDA:NAS100USD`, `IC:US500` ni cualquier feed de TradingView.

## Resultado agregado real

| Medida | Calibración histórica |
|---|---:|
| Archivos M5 originales con SHA válido | **33/33** |
| M5 del período realmente procesadas | **312.461** |
| C1 H4 elegibles contabilizadas | **3267** |
| Eventos 2C estructurales históricos | **998** |
| Seguimientos 3C diagnósticos | **821** |
| Mercados con al menos un 2C histórico | **33/33** |
| Mercados con al menos un 3C diagnóstico | **33/33** |
| Bloques H4 incompletos/rechazados | **283** |
| Bloques con discontinuidad M5 interna | **85** |
| Holdout virgen certificado | **0/34** |
| MSS M15, Inside, Multi4/Multi-N, FVG y alertas Android | **No evaluados aquí** |

Una estructura 2C puede dar también un seguimiento 3C. No sumar los números como si fueran trades independientes ni estimar rentabilidad a partir de ellos.

## Resultados por instrumento

| Fuente | Cohorte | M5 procesadas | C1 H4 | 2C | 3C diagnóstico | H4 rechazadas | Bloques M5 discontinuos |
|---|---|---:|---:|---:|---:|---:|---:|
| AUDCAD | IC Markets DEMO | 9537 | 99 | 43 | 40 | 3 | 3 |
| AUDCHF | IC Markets DEMO | 9537 | 99 | 28 | 22 | 4 | 3 |
| AUDJPY | Atlas DEMO | 9538 | 99 | 38 | 29 | 3 | 1 |
| AUDNZD | IC Markets DEMO | 9540 | 99 | 36 | 32 | 1 | 0 |
| AUDUSD | Atlas DEMO | 9529 | 99 | 33 | 27 | 10 | 10 |
| CADCHF | IC Markets DEMO | 9539 | 99 | 29 | 26 | 2 | 1 |
| CADJPY | IC Markets DEMO | 9536 | 99 | 30 | 24 | 3 | 1 |
| CHFJPY | IC Markets DEMO | 9540 | 99 | 33 | 29 | 1 | 0 |
| EURAUD | IC Markets DEMO | 9540 | 99 | 30 | 30 | 1 | 0 |
| EURCAD | IC Markets DEMO | 9540 | 99 | 33 | 30 | 1 | 0 |
| EURCHF | IC Markets DEMO | 9539 | 99 | 16 | 14 | 2 | 1 |
| EURGBP | IC Markets DEMO | 9537 | 99 | 31 | 23 | 4 | 3 |
| EURJPY | IC Markets DEMO | 9540 | 99 | 28 | 21 | 1 | 0 |
| EURNZD | IC Markets DEMO | 9540 | 99 | 30 | 26 | 1 | 0 |
| EURUSD | Atlas DEMO | 9534 | 99 | 32 | 26 | 6 | 5 |
| GBPAUD | IC Markets DEMO | 9540 | 99 | 26 | 21 | 1 | 0 |
| GBPCAD | IC Markets DEMO | 9540 | 99 | 31 | 26 | 1 | 0 |
| GBPCHF | IC Markets DEMO | 9540 | 99 | 21 | 17 | 1 | 0 |
| GBPJPY | Atlas DEMO | 9538 | 99 | 31 | 28 | 3 | 1 |
| GBPNZD | IC Markets DEMO | 9540 | 99 | 33 | 28 | 1 | 0 |
| GBPUSD | Atlas DEMO | 9526 | 99 | 32 | 29 | 10 | 10 |
| NAS100 | Atlas DEMO | 9084 | 99 | 27 | 11 | 34 | 0 |
| NZDCAD | IC Markets DEMO | 9537 | 99 | 40 | 37 | 3 | 3 |
| NZDCHF | IC Markets DEMO | 9538 | 99 | 32 | 30 | 3 | 2 |
| NZDJPY | IC Markets DEMO | 9539 | 99 | 38 | 34 | 2 | 1 |
| NZDUSD | IC Markets DEMO | 9532 | 99 | 32 | 28 | 7 | 7 |
| SP500 | Atlas DEMO | 9078 | 99 | 27 | 17 | 34 | 0 |
| US30 | Atlas DEMO | 9084 | 99 | 31 | 12 | 34 | 0 |
| USDCAD | Atlas DEMO | 9525 | 99 | 25 | 23 | 14 | 14 |
| USDCHF | IC Markets DEMO | 9520 | 99 | 22 | 18 | 16 | 15 |
| USDJPY | Atlas DEMO | 9531 | 99 | 24 | 20 | 6 | 4 |
| XAGUSD | Atlas DEMO | 9101 | 99 | 31 | 24 | 35 | 0 |
| XAUUSD | Atlas DEMO | 9102 | 99 | 25 | 19 | 35 | 0 |

## Qué nos enseña frente a la captura de TradingView
La V34.10v que el usuario probó mostró `RESP:34 SD:0 HIST:8` dentro del tramo M5 disponible y con los proveedores configurados en TradingView. En esta prueba **más larga**, la detección estructural QA ha registrado al menos un 2C en todos los archivos no-BTC. Hay **diferencias importantes de ventana temporal, método y proveedor**, de modo que no se pueden extrapolar coincidencias directas a Pine. Sí justifica aislar y medir los `calc_bars_count=1500`, datos parciales, horarios y disponibilidad de H4 antes de modificar las reglas.

## Siguientes puertas obligatorias
1. Validar una fuente BTCUSD M5 compatible con COINBASE:BTCUSD y la procedencia exacta de los Atlas 12 antes de cualquier paridad.
2. Hacer replay de **los mismos OHLC de cada proveedor** con el motor `f_engine()` real, verificando 2C, 3C, Inside, Multi4, Multi-N, MSS M5/M15 causal, FVG H1/H4, PDH/PDL, DST y no-repaint. Este prescreen simplificado NO demuestra las siete familias catalogadas.
3. Prerregistrar un holdout real no utilizado previamente y congelar SHA del motor/datos y umbrales de aprobación antes de consultar resultados.
4. Probar límites de recursos de Pine en 34 contextos, compilación TradingView y Android FCM sin dependencia de alertas TradingView; no ejecutar órdenes.

**RELEASE = BLOCKED.** Los PRs permanecen DRAFT sin merge y sin LIVE.

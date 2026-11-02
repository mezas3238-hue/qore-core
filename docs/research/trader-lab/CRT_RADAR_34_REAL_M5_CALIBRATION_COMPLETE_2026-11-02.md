# CRT RADAR PRO — 34/34 mercados: calibración M5 real completada

**Fecha 2026-11-02 · RESEARCH CALIBRATION ONLY · 0/34 holdout externo certificado · NO LIVE / NO FCM / NO ÓRDENES**

## Recibos verificables
- **33/33 fuentes M5 originales:** [GitHub Actions run #41383370607](https://github.com/mezas3238-hue/qore-core/actions/runs/41383370607), 33 jobs SUCCESS (12 Atlas cTrader DEMO, broker exacto NO acreditado; 21 IC Markets DEMO). SHA256 de cada partición original `RAW_M5_LEDGER/2026.jsonl` verificado contra manifiesto. Resultados completos por instrumento: [tabla de 33](https://github.com/mezas3238-hue/qore-core/blob/agent/crt-radar-trader-lab-34-preflight-20261101/docs/research/trader-lab/CRT_RADAR_33_REAL_M5_CALIBRATION_QA_RESULTS_2026-11-02.md).
- **BTCUSD desde Coinbase Exchange público:** [GitHub Actions run #41384028916](https://github.com/mezas3238-hue/qore-core/actions/runs/41384028916), SUCCESS, código `scripts/crt_radar_coinbase_btc_m5_prescreen.py`, sin API key, órdenes o upload de raw. El proveedor se identifica `COINBASE_EXCHANGE_PUBLIC_BTC-USD`, NO `IC:BTCUSD`.
- Coinbase público retornó **13.536 M5** mediante **47 consultas de un día**, digest del contenido de calibración `sha256:f221ebbc0aedd46e0a1413e2f36838252b1421d8bb27c8c38e9d51fde062874d`. No se ha archivado un ZIP original de Coinbase ni se ha certificado paridad de candles con TradingView.

Todas las lecturas se limitaron a **2026-08-01T00:00:00Z a 2026-09-17T00:00:00Z**, período de calibración distinto del gráfico del usuario de 1–2 de noviembre. **Los históricos de cTrader ya se utilizaron en otros proyectos y NO pueden considerarse holdout nuevo.**

## Totales (detector estructural independiente, NO Pine exacto)

| Métrica | 33 archivos cTrader | BTC Coinbase | Total |
|---|---:|---:|---:|
| Mercados procesados | 33 | 1 | **34** |
| Velas M5 | 312.461 | 13.536 | **325.997** |
| H4 NY aptas para C1 | 3.267 | 141 | **3.408** |
| Detectores históricos 2C | 998 | 42 | **1.040** |
| C3 seguimiento diagnóstico | 821 | 30 | **851** |
| Bloques H4 rechazados | 283 | 2 | **285** |
| Bloques con discontinuidad M5 | 85 | 0 | **85** |
| Al menos un patrón 2C en calibración | 33/33 | 1/1 | **34/34** |

**NO sumar 2C+3C como operaciones:** el mismo ciclo puede transformarse en 3C. No se calculó rentabilidad, precisión de entradas, win-rate, MSS, FVG, PDH/PDL, emisiones Android ni señales en vivo.

## Lo que confirma esta fase
1. El laboratorio de GitHub puede leer M5 históricos reales de **los 34 símbolos**, manteniendo cada fuente identificada; en los primeros 33 hay SHA original por partición y en Coinbase un digest de resultados de consulta pública.
2. Un motor estructural **simplificado** de C1 H4 + barrida/retorno unilateral de C2 encuentra muestras positivas 2C para todos los instrumentos durante la ventana más larga. **No garantiza** que la implementación completa `f_engine()` de Pine confirme lo mismo.
3. Los **26 instrumentos** que anteriormente no figuraban en la auditoría histórica limitada de TradingView requieren un diagnóstico de `calc_bars_count=1500`, ventana efectiva, origen OHLC, DST, sesiones y persistencia del C1. No se debe relajar el filtro para fabricar CRT.
4. Si la futura pantalla del usuario permanece sin señales, eso podría ser correcto cuando no hay CRT H4 vigente + MSS M15 causal. Que el laboratorio haya encontrado historia en agosto/septiembre **no obliga a mostrar esos símbolos en noviembre**.

## Bloqueos de salida
- **Paridad de detector:** probar exactamente el código Pine V34.10w `f_engine()` frente a una traducción temporalmente equivalente usando la MISMA serie M5 del mismo proveedor. Las siete categorías del catálogo NO están ratificadas: 2C/3C QA no equivale a certificar Inside, Multi4, Multi-N, retest ni familias de entrada.
- **Paridad de proveedores:** QORE Atlas `NAS100→USTEC`, `SP500→US500` no se convierte automáticamente en OANDA:NAS100USD/IC:US500. Los 12 Atlas mantienen broker exacto desconocido. Coinbase Exchange BTC-USD no está certificado como equivalente candle por candle a COINBASE:BTCUSD.
- **Holdout sin fuga:** dataset independiente no examinado, licencias y derechos de uso, origen/ventanas certificados, código SHA fijo y resultados de falsación; `0/34` holdout real homologado.
- **Recursos y compilación:** TradingView 34 requests/limites Pine v6, no-repaint real, y backend Android FCM E2E sin órdenes.

**Estado RELEASE: BLOQUEADO.** Conservar PRs en DRAFT, no merge ni LIVE; próximos pasos son paridad de motor completo, holdout verdaderamente independiente y pruebas Android push.

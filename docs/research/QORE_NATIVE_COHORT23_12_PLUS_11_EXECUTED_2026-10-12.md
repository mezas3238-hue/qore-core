# QORE Native — EJECUCIÓN COMPLETA: cohorte 23 = 12 originales + 11 nuevos

**Fecha 2026-10-12, GitHub UTC. Estado: `G0_23_OF_23_M5_SOURCE_SHA_VERIFIED_ECONOMICS_NOT_AUTHORIZED`.**

## Evidencia auditada (NO resultados económicos)

- [PR #821](https://github.com/mezas3238-hue/qore-core/pull/821), rama `research/qore-native-cohort23-union-source-g0-20261012`.
- [GitHub Actions exact-head #38202227551](https://github.com/mezas3238-hue/qore-core/actions/runs/38202227551), **13/13 jobs SUCCESS** (1 contrato/test + 11 archivos nuevos SHA originales + 1 unión).
- Código ejecutado **`cb9a21f77131b07db2da964ba123bd8c282ded23`**. El commit documental posterior no altera este código ni los datos auditados.
- [Artefacto UNIFICADO #11725797331](https://github.com/mezas3238-hue/qore-core/actions/runs/38202227551/artifacts/11725797331): `qore-native-cohort23-unified-manifest.json` + manifest SHA256 + `OUTPUT_SHA256SUMS.txt`; SHA256 ZIP reportado por GitHub upload `2964701fb50eb554d6448e8f869c5f4ddb56d8b5a5c4bed756ee9e0afe0aae9d`. El SHA del contenido manifest está en su testigo `.sha256` y el `OUTPUT_SHA256SUMS.txt`.
- Resumen del job de unión, extraído de log: `{"cohort_count":23,"identity":"QORE_NATIVE_COHORT_23_12_PLUS_11_M5_SOURCE_G0_V1","m5_bars":16924567,"no_pnl":true,"no_trade":true,"status":"G0_23_OF_23_M5_SOURCE_SHA_VERIFIED_ECONOMICS_NOT_AUTHORIZED","symbol":null}`.

## Recuento conciliado

| Subconjunto | Instrumentos | Velas originales M5 | Verificación |
|---|---:|---:|---|
| Original CIBO cTrader DEMO, producer [#35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) | 12 | 8,726,985 | [G0 #816](https://github.com/mezas3238-hue/qore-core/pull/816) y [G0B 14/14](https://github.com/mezas3238-hue/qore-core/actions/runs/38201368296), cada annual RAW SHA |
| Primer lote nuevo IC Markets DEMO, capture [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) | 11 | 8,197,582 | 11/11 manifest + año RAW/quality SHA, M5 UTC, recuento fuente |
| **TOTAL COHORTE QORE NATIVE** | **23** | **16,924,567** | **13/13 jobs SUCCESS** |

### Los 11 nuevos, prueba por símbolo

| Activo | M5 provider-native | Control |
|---|---:|---|
| USDCHF | 744,755 | PASS RAW SHA 11 years |
| NZDUSD | 744,980 | PASS RAW SHA 11 years |
| EURGBP | 745,331 | PASS RAW SHA 11 years |
| EURJPY | 745,509 | PASS RAW SHA 11 years |
| EURCHF | 745,092 | PASS RAW SHA 11 years |
| EURCAD | 744,886 | PASS RAW SHA 11 years |
| EURAUD | 745,503 | PASS RAW SHA 11 years |
| EURNZD | 745,327 | PASS RAW SHA 11 years |
| GBPCHF | 745,370 | PASS RAW SHA 11 years |
| GBPCAD | 745,397 | PASS RAW SHA 11 years |
| GBPAUD | 745,432 | PASS RAW SHA 11 years |
| **Total** | **8,197,582** | **11/11 SHA PASS** |

### 12 originales ya disponibles

`AUDJPY AUDUSD EURUSD GBPJPY GBPUSD NAS100 SP500 US30 USDCAD USDJPY XAGUSD XAUUSD`

### Integración técnica

No se alteraron los archivos de fuente ni se mezclaron series o precios de cuentas distintas. El manifiesto único incluye las 23 identidades, cuenta de velas por símbolo, provenance run/HEAD, los 11 `raw_sha256_by_year` de cada nuevo y la referencia al testigo SHA independiente del conjunto 12 ya auditado. Es la **unión lógica reproducible** necesaria para el laboratorio. Los históricos RAW permanecen como 23 artefactos de los producers y deben descargarse de sus runs; no se añadieron ~17 millones de barras directamente al repo.

**La captura #38193802541 siguió trabajando en paralelo** y publicó también GBPNZD después del corte de primeros 11. Como no forma parte del conjunto explicitamente solicitado y congelado por el propietario, no se ha forzado dentro del batch 23 ni certificado en esta auditoría; el siguiente lote debe auditarlo y los otros 9 una vez existan (actualizar estado real antes de anunciar cantidad). No relanzar descargas ni mezcla de IDs.

## Restricciones y siguiente ensayo científico

- **Histórico BID/ASK no disponible:** esto ya no bloquea el G0 o la investigación de edge **bruto**. Se permite investigación de señales OHLC M5 pre-registrada y **sensibilidad explícita de costes de escenarios**, incluyendo coste de break-even, nunca declarar ejecución neta comprobada si spreads/SL/commission/slippage desconocidos.
- No asumir igualdad de cuenta/broker entre source CIBO DEMO y source IC Markets DEMO; el primer grupo no acredita origen del mismo bróker. Conservar bandas y segmentar por procedencia en los análisis.
- No usar UTC 288/288 como vela broker D1 certificada; reconstrucción sesión/cambio horario es otra puerta. No trades alrededor de eventos macro en Native según [política #814](https://github.com/mezas3238-hue/qore-core/pull/814).
- Una única hipótesis NORMAL-REGIME, H4/D1 con control pareado, pruebas causal/no lookahead, split temporal, riesgo, n efectivo, costes supuestos declarados y análisis de stress, prereg antes de mirar PnL. No comparar 23 mercados y elegir el mejor a posteriori.
- 0/3 traders certificados, no órdenes, ni VPS/MT5/CIBO/Shared/QDLE/LIVE, no merge main.

**Dictamen:** el trabajo de **JUNTAR 12+11 PARA INVESTIGACIÓN** está **EJECUTADO Y TESTIFICADO EN GITHUB**. Rentabilidad y resultados netos **NO EVALUADOS**.

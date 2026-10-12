# QORE Native — Unión ejecutable de los 12 originales + primeros 11 cTrader IC Markets M5

**12 octubre 2026 — investigación GitHub, sin precios analizados ni trading.** Petición Owner: unir los 11 nuevos con los 12 ya disponibles en Core.

## Qué significa "juntar"

Crear **un único índice lógico del universo investigable de 23 mercados**, manteniendo las 23 series originales en sus artifacts inmutables y sus 23 procedencias identificadas (no se concatena una cotización AUDJPY con EURUSD o brokers distintos). La unión se admite SOLO si el sistema verifica hashes y todo el rango, IDs, fechas, calendario de timestamp M5, origen, manifiestos RAW y calidad de cada símbolo. No inferir que el bróker de los primeros 12 sea la misma cuenta IC Markets DEMO de los 11; no extrapolar BID/ASK ausente.

### 12 archivos originales ya auditados

**AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, NAS100 (USTEC), SP500 (US500), US30, USDCAD, USDJPY, XAGUSD, XAUUSD.**

Original 10Y M5 producer [Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458); integridad/G0 [PR #816](https://github.com/mezas3238-hue/qore-core/pull/816); G0B rehash/clock [run #38201368296](https://github.com/mezas3238-hue/qore-core/actions/runs/38201368296), 14/14 PASS y **8.726.985** barras M5, SHA original 132 años. El indexador de 23 exige el hash del `qore-native-g0b-aggregate.json` y commit exacto del código G0B antes de aceptarlos.

### 11 archivos nuevos bajo prueba estricta

**USDCHF, NZDUSD, EURGBP, EURJPY, EURCHF, EURCAD, EURAUD, EURNZD, GBPCHF, GBPCAD, GBPAUD.**

Original cTrader IC Markets DEMO capture run [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541); productor HEAD `e0ca5a13c866a19d8505c68cffc473598984b340`, captura 7 días por ventana M5, 2016-09-17 a 2026-09-17 exclusivo; 11 archivos originalmente visibles en Actions con los nombres `qore-native-icmarkets-10Y-provider-M5-{SYMBOL}-{HEAD}`.

**G0 de cada uno:** verificar el SHA256 del manifiesto capturado `SOURCE_SHA256SUMS.txt`, el `MANIFEST_SHA256SUMS.txt` del productor, los 11 `PARTITION_MANIFEST/{year}.sha256` y los SHA256 de RAW M5 y QUALITY, identidad exacta y símbolo/bróker declarado del run, flags `read_only`, ventana histórica UTC, 5min, orden/duplicados, recuento de cada partición frente a `retained_bars`. Un job PASS de descarga sin esta auditoría **no** autoriza el instrumento.

**12.º nuevo artefacto GBPNZD:** quedó publicado después del primer listado de 11 del propietario; queda **fuera de esta cohorte 23 congelada** para evitar cambiar silenciosamente el universo solicitado. Se integrará por siguiente lote/auditoría después de verificar SHA. Los restantes 9 continúan en captura, no se detienen ni reinician.

### Origen y diferencias económicas

`SOURCE_A = CIBO_DEMO_12`, `SOURCE_B = ICMARKETS_DEMO_NEW11`. Los originales pueden tener alias USTEC/US500; nuevos FX exactos. No declarar que sus spread/horarios/contract specs sean equivalentes o que existan precios ejecutables BID/ASK. **El corpus M5 OHLC bruto puede usarse para ensayos exploratorios causalmente pre-registrados, con escenarios de costes hipotéticos, NO para certificar rentabilidad NET real.** Si no existe BID/ASK, calcular break-even/maximum tolerable cost y escenarios conservadores por símbolo, con supuestos etiquetados; nunca usar 0 spread como neto.

### Estados y guardrails

1. Antes de CI: **12/12 auditados + 11 archivos nuevos publicados**, pero unión **NO CERTIFICADA**.
2. Si Actions pasa todos: `G0_23_OF_23_M5_SOURCE_SHA_VERIFIED_ECONOMICS_NOT_AUTHORIZED`, con index JSON y `OUTPUT_SHA256SUMS.txt`; los once nuevos se vuelven G0 verified. No equivalencia broker validada ni H4/D1 nativos.
3. Si falla un símbolo/hashes/presencia: `PARTIAL`, no catalogar 23/23 y no volverlo "PASS" falseando calendario.
4. Gate de economía sin BID/ASK: investigación gross y sensibilidad coste hipotética permitida solo con nuevo prereg y metodología; declarar umbral de coste que elimina edge, control baseline/holdout, cluster n, PF/Sharpe/Sortino y DD gross claramente etiquetados. No promoverlo a LIVE/PAPER sin autoridad.
5. No escanear PnL ni escoger activos por retornos en G0, y no introducir los otros 10 de la adquisición sin nueva cohorte congelada y testigo. Todo exclusivamente GitHub research; **VPS/MT5/CIBO/Shared/QDLE/producción intactos**.

**Archivos:** `src/qore/infrastructure/trader_lab/qore_native_cohort23_m5_source_union_v1.py`, `tests/infrastructure/trader_lab/test_qore_native_cohort23_m5_source_union_v1.py`, `.github/workflows/qore-native-cohort23-m5-source-union.yml`.

**Workflow:** CI contrato → matriz 11 SHA verified source only → descarga aggregate original 12 firmado → combination exact 23 → `qore-native-cohort23-unified-manifest.json`. No historial BID/ASK inventado, no ejecución de noticias conforme [#814](https://github.com/mezas3238-hue/qore-core/pull/814), 0/3 traders nativos certificados.

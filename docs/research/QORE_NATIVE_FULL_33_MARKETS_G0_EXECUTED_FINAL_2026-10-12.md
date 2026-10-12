# QORE Native — 33/33 Mercados G0 SHA ejecutado, censo de las 4 familias

**Fecha GitHub UTC: 2026-10-12. ESTADO FINAL `G0_33_OF_33_PROVIDER_M5_SHA_VERIFIED_NO_ECONOMICS`.**

## Verificación REAL y reproducible

- [PR de investigación #829](https://github.com/mezas3238-hue/qore-core/pull/829), rama `research/qore-native-final33-tail-ready-g0-20261012`. DRAFT, no merge producción.
- [GitHub Actions captura original #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), HEAD productor `e0ca5a13c866a19d8505c68cffc473598984b340`, **21/21 jobs de mercados completados SUCCESS**. Las 12 primeras proceden de captura distinta Atlas original [#35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458).
- [GitHub Actions auditoría final #38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960), **6/6 SUCCESS**: contrato de fuente/censo, preflight de 3 artefactos, 3 verificaciones independientes originales RAW+quality SHA anuales y publicación del manifiesto/censo. Código exactamente ejecutado HEAD `dba0e0c3b61e430d3ed51abab562ebd92060a0ff`; no confundir commits documentales posteriores con código probado.
- [Artefacto único final #11727643288](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960/artifacts/11727643288): `qore-native-complete33-source-m5.json`, testigo SHA256, `OUTPUT_SHA256SUMS.txt`, `exact-code-head-sha.txt`; también `census/qore-native-33-market-families-source-only.json` y su `.sha256`.
- **SHA256 del manifiesto final** `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. **SHA256 del censo familias** `d38548e485ad09846396359eb141661af49dee5ca20210faac04ef4c863fec8f`. Ambos hashes fueron comprobados sobre el contenido original del artefacto GitHub.
- Manifiesto padre 30 SHA congelado `96b6709022905215d582abdc20edb452c7766dd42fd945e76144de8a29d29283`, parent 22.141.699 M5. Integración lógica sin reescribir 30 series anteriores.

## Fuente 33 — números comprobados directamente desde el artifact JSON

| Origen | Activos | M5 nativo original recontado |
|---|---:|---:|
| CIBO/Atlas cTrader DEMO originales | 12 | 8.726.985 |
| Captura nueva IC Markets cTrader DEMO | 21 | 15.650.435 |
| **Unión G0 SHA 33** | **33** | **24.377.420** |

| Últimos tres | Barras M5 SHA validadas | Evidencia GitHub |
|---|---:|---|
| NZDJPY | 745.313 | [witness run final](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960) |
| NZDCAD | 745.234 | [witness run final](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960) |
| NZDCHF | 745.174 | [witness run final](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960) |
| **Último bloque 3** | **2.235.721** | 3/3 raw+quality SHA/pass |

El auditor validó cada fuente contra `SOURCE_SHA256SUMS.txt`, manifiestos y **11 particiones anuales** de `RAW_M5_LEDGER` y `DATA_QUALITY_LEDGER`, cronología de timestamp alineada 5min, original source/canonical/provider identity, órdenes de partición, ventanas y recuentos. No se utilizó OHLC para seleccionar mercados ni recuperar señales.

### Clasificación completa — todos los mercados, no una lista optimizada

| Familia fija | Activos | M5 |
|---|---:|---:|
| Índices NAS100/SP500/US30 | 3 | 2.095.377 |
| Metales XAUUSD/XAGUSD | 2 | 1.414.232 |
| FX mayores AUDUSD/EURUSD/GBPUSD/NZDUSD/USDCAD/USDCHF/USDJPY | 7 | 5.216.165 |
| FX cruces no USD | 21 | 15.651.646 |
| **TOTAL** | **33** | **24.377.420** |

El censo `qore_native_market33_source_census_v1.py` impone 3+2+7+21 sin solapamientos, verifica que las 21 nuevas tengan hashes raw por año 2016–2026, que las 12 originales sumen 8.726.985 y que los 33 sumen 24.377.420. Rechaza procedencia no reconocida y NO infiere sesiones broker D1/H4 ni identidad de cuenta original vs nueva.

## Distinciones de investigación y certificación

- **Integridad de fuente G0 PASS 33/33**: capacidad de investigación market-wide con historiales M5 íntegros dentro del contrato de fuente; no implica calendario de sesiones realmente abierto o ausencia de cortes del feed.
- **Realismo G1 net BLOCKED**: no hay histórico BID/ASK comparable, spreads variables, comisiones/financiación/deslizamiento/fills y stops broker verificados. Costo roundtrip hipotético con OHLC no es rendimiento neto real. 12 originales DEMO no demostrados misma cuenta/broker que los 21 nuevos; todos mantienen fuente diferenciada.
- **NO-NEWS compliance no certificada**: calendario macro histórico conocido-as-of y reglas operacionales pre-news aún sin testigos. No usar resultados gross pre-news para permitir órdenes durante alto impacto (política #814).
- **Tres experimentos económicos distintos NO_SUPPORT**: EURUSD H4 persistencia [#822](https://github.com/mezas3238-hue/qore-core/pull/822), XAUUSD H4 reversión [#825](https://github.com/mezas3238-hue/qore-core/pull/825), NAS100 cash-open drive [#827](https://github.com/mezas3238-hue/qore-core/pull/827). Pre-registro previo a outcomes en las tres, intervalos pareados no sostienen ventaja. Ninguna justificación para probar 33 mercados y elegir un mejor PnL post-hoc.

## Siguiente misión del arquitecto científico

1. **Congelar el universo 33 y fuente SHA**: no ampliar ni sustituir mercados por PnL. Mantener este `G0_33/33` como testigo, no modificar original RAW ni el holdout 2024–2026 previamente embargado en los tres ensayos.
2. **Tratar las 33 fuentes** en un solo ensayo *de panel* pre-registrado si aparece un mecanismo económicamente motivado distinto de los tres que fallaron. Definir y publicar ANTES de abrir retornos: regla causal común, clases y horarios admisibles, benchmark simultáneo pareado, muestras mínimas, costes RT hipotéticos, control de dependencia por fechas entre activos y multiplicidad en familias. Reportar 33/33 resultados incluida ausencia de señales, sin seleccionar ganador.
3. **Datos de costes reales y noticias PIT**: planificar forward PAPER con BID/ASK observado + spread/commission/slippage, verificación de libro bróker, horario y DST; calendario macro con fecha publicación histórica conocida as-of. Sin ello, jamás declarar PF/DD/Sharpe/Sortino NET o trader certificado.
4. **Puerta de traders nativos**: 0/3 certificados. Shared/CIBO pueden apoyar la cognitiva una vez exista señal robusta, no suplir falta de edge con filtros retrospectivos.
5. Las ramas de PR 816,820,821,823,824,826,828,829 están interconectadas por base/commit; no fusionar líneas a `main` ni tocar producción sin auditoría y autorización separada.

**Estado final:** 33/33 fuente G0 ✅, 24.377.420 M5 ✅, censo 4 familias ✅, tres hipótesis económicas NO_SUPPORT ❌, costes netos reales no acreditados ⚠️, 0/3 Traders certificados. 0 nuevas órdenes, ningún cambio VPS/MT5/CIBO/Shared/QDLE/LIVE.
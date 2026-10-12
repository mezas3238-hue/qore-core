# QORE Native H4 — ocho fuentes reales de tasas interbancarias, proxy 3 meses, NO forward 1 mes

**12 de octubre de 2026 · Investigación de fuente para desbloquear carry; no cambiar H4/forward a posteriori.**

## Hallazgo y fuente observable

Hay ocho series mensuales FRED/OCDE **3 meses o 90 días, tasas interbancarias de mercado, porcentaje anual**, para las ocho monedas subyacentes a los 28 pares FX originales:

| Moneda | OECD/FRED ID | URL oficial |
|---|---|---|
| AUD | IR3TIB01AUM156N | https://fred.stlouisfed.org/series/IR3TIB01AUM156N |
| CAD | IR3TIB01CAM156N | https://fred.stlouisfed.org/series/IR3TIB01CAM156N |
| CHF | IR3TIB01CHM156N | https://fred.stlouisfed.org/series/IR3TIB01CHM156N |
| EUR | IR3TIB01EZM156N | https://fred.stlouisfed.org/series/IR3TIB01EZM156N |
| GBP | IR3TIB01GBM156N | https://fred.stlouisfed.org/series/IR3TIB01GBM156N |
| JPY | IR3TIB01JPM156N | https://fred.stlouisfed.org/series/IR3TIB01JPM156N |
| NZD | IR3TIB01NZM156N | https://fred.stlouisfed.org/series/IR3TIB01NZM156N |
| USD | IR3TIB01USM156N | https://fred.stlouisfed.org/series/IR3TIB01USM156N |

Fuentes originales según series: OECD Main Economic Indicators, accesibles en FRED (St. Louis Fed). Pueden tener revisiones; FRED advierte la situación. Se debe distinguir **fecha de observación** (e.g. 2019-02-01) de **fecha de publicación/disponibilidad histórica** (no acreditada por CSV actual). La existencia de 104 puntos mensuales 2016-01...2024-08 **no constituye** 104 puntos conocidos en sus meses ni prueba de forward. EUR id EA19, no necesariamente homólogo de otros conjuntos europeos.

## Qué hace esta nueva ejecución y qué NO

- Github Actions visita URL oficial HTTPS FRED, **ocho IDs exactos whitelist**; solo solicita ventana 2016-01 a 2024-08. Puede retener bytes brevemente EN MEMORIA CI para calcular SHA de respuesta y contar meses, pero **NO publica ni serializa valores de tasas** en repo/artifacts públicos, por licencias y datos posiblemente protegidos.
- Parser hace fail-closed ante CSV diferente, HTML/bloqueo, header de serie equivocado, meses duplicados/fuera de orden, NaN/no-finitos, serie faltante. De cada moneda emite solo ID, URL, hash SHA de los bytes, 104 meses esperados, meses completos/missing, primera y última fecha, no rates y no PnL.
- Fuente revisada 2026 significa **PIT NO PROBADO**, aunque las fechas de observación sean de 2016, y usar 2 meses de lag arbitrario NO arregla revisiones históricas si no se demuestran sus vintages. El dataset tampoco es 1-month forward, ni financiación ejecutable, ni BID/ASK.
- El 1M forward y costos reales de [PR #883](https://github.com/mezas3238-hue/qore-core/pull/883) / [issue P0 #884](https://github.com/mezas3238-hue/qore-core/issues/884) siguen siendo la vía canónica H4. **No se hace estudio económico** con tres meses a espaldas del preregistro H4.
- Para convertir las series de tres meses en posible nuevo test separado, habrá que documentar vintages históricos ALFRED/OCDE (fecha de primera publicación + revisión, y disponibilidad a cada mes de trading) y congelar por adelantado una hipótesis **3M interest-rate proxy** distinta; sus resultados nunca pueden confundirse con forward quotes.
- Todos los estudios H1/H2/H3 anteriores diagnósticos, H1 -0,272, H2 +0,077, H3 -0,507, intactos; no alterar la regla según cuáles meses tengan tasa favorable. Holdout económico desde 2024-09-17 reservado, 0/3 traders certificados. No MT5, VPS, Shared, CIBO, QDLE, LIVE, ejecución real.

## Gate cuantitativo y publicación

Pruebas independientes sintéticas sobre parser en `tests/infrastructure/trader_lab/test_qore_native_h4_oecd8_fred_3m_source_audit_v1.py`, y trabajo read-only en workflow `.github/workflows/qore-native-h4-oecd8-3m-source-coverage.yml`.

Si el fetch real funciona, condición de interés mínimo: **8/8 monedas cubiertas** con 104 observaciones en el rango. AUN ASÍ resultado científico para edge carry seguirá `BLOCKED_NO_AUTHENTIC_PIT_ONE_MONTH_FORWARD` (y H4 original no ejecutado). La auditoría podría ayudar a reducir costos de adquisición del *proxy* a tres meses, pero nunca demuestra rentabilidad por sí sola.

**Bibliografía útil:** [FRED datos](https://fred.stlouisfed.org/help/data/downloading/using-the-download-data-link/), [ALFRED New Zealand vintages](https://alfred.stlouisfed.org/series?seid=IR3TIB01NZM156N), [CME CIP](https://www.cmegroup.com/articles/whitepapers/covered-interest-parity-implied-forward-foreign-exchange-swaps-cross-currency-basis-and-cme-estr-futures.html).

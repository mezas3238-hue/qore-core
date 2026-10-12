# QORE Native H4 — resultado económico NO ejecutado; datos ALFRED as-of auditados y PIT incompleto

**12 octubre 2026. Informe de cierre de ronda de fuente. No hay PnL ni Sharpe H4.**

## Qué cambió realmente

Se verificaron ocho series oficiales OCDE/FRED 3M monthly para 8 monedas con un total de **831/832 slots retrospectivos** 2016-01 a 2024-08, la ausencia USD `2020-04-01` (valor `.`) comprobada también en [FRED tabla original](https://fred.stlouisfed.org/data/IR3TIB01USM156N). Sin embargo, un panel con datos existentes en 2026 **NO** implica que esos valores ya estuvieran publicados en su mes. Se auditó ahora la disponibilidad de **dos vintages históricos auténticos** por moneda a través del CSV público del gráfico ALFRED (headers exactamente `SERIES_20191231` y `SERIES_20231229`, rechazando cualquier sustitución por vintage actual) y se observó:

| Divisa | Último mes conocido **2019-12-31** según ALFRED | Último mes conocido **2023-12-29** según ALFRED |
|---|---|---|
| AUD | 2019-11 | 2023-11 |
| CAD | 2019-11 | 2023-11 |
| CHF | 2019-11 | **2021-12** |
| EUR | 2019-09 | 2023-11 |
| GBP | 2019-11 | 2023-11 |
| JPY | 2019-10 | 2023-10 |
| NZD | 2019-09 | 2023-11 |
| USD | 2019-11 | 2023-11 |

**Consecuencia científica importante:** en la **serie específica IR3TIB01CHM156N**, los datos del periodo 2022–2023 aparentemente presentes hoy NO aparecían en el vintage archivado ALFRED disponible el 2023-12-29. No se puede ordenar correctamente un carry contemporáneo de ocho monedas con este panel usando esa serie como si hubiera estado vigente. No afirmar que los mercados suizos no tuviesen tasas: **solo la serie de referencia exacta se observa rezagada**. **Evento estructural documentado por autoridad suiza:** el CHF LIBOR se descontinuó a finales de 2021 y SARON lo sustituyó. Lo confirman el [SNB en discurso de 31 de marzo de 2022](https://www.snb.ch/en/publications/communication/speeches/2022/ref_20220331_amrtmo) y su [glosario oficial](https://www.snb.ch/en/services-events/digital-services/glossary). Esto es **consistente** con el último dato CHF visible 2021-12 en el vintage ALFRED de diciembre 2023, pero NO acredita la mecánica exacta del backfill de OCDE/FRED o la equivalencia de curvas. [SNB data portal](https://data.snb.ch/en/topics/snb/cube/snbgwdzid?dimSel=D0&fromDate=2022-05-27&toDate=2022-07-01) da series históricas de SARON overnight y SNB policy rate; **SARON overnight/compounded in arrears NO es quote 3M LIBOR ex ante, ni forward 1M ejecutable**, por tanto mezclarlo sin nueva definición sería otro cambio de hipótesis.

Una tasa de 2026 asignada retrospectivamente a 2022 sería lookahead, y aplicar un lag fijo de un mes al CSV actual NO repara revisiones y tramos largos de ausencia.

## Evidencia firmada, cumplimiento y fuentes

1. **[GitHub Actions fuente OCDE/FRED #38321986085](https://github.com/mezas3238-hue/qore-core/actions/runs/38321986085)** SUCCESS, código HEAD `9110092f99da29e2edba6d0a3a3c7db9e7d2539e`, tests sintéticos 10/10; **[artifact #11779640095](https://github.com/mezas3238-hue/qore-core/actions/runs/38321986085/artifacts/11779640095)** SHA256 ZIP `6877291b408a540616ea43515bfaf966f606e0a265235f3256ffb1ba77ef4f56`, expira **2026-11-11 23:24:50Z**.
2. **[GitHub Actions ALFRED vintage #38322179597](https://github.com/mezas3238-hue/qore-core/actions/runs/38322179597)** SUCCESS, código HEAD `6284d08f2eab7ca5f8bc43f583627668c6b1789e`, tests sintéticos 6/6, **8/8 series vintage verificadas** y última fecha de observación por vintage; **[artifact #11779685249](https://github.com/mezas3238-hue/qore-core/actions/runs/38322179597/artifacts/11779685249)** SHA256 ZIP `a59939bf8b4bc0e59010b6e2dc8ef868e5822754f5466128e97b27a2faee8fc7`, expira **2026-11-11 23:27:08Z**.
3. [Ayuda de ALFRED sobre vintages](https://alfred.stlouisfed.org/help/downloaddata) establece semántica: la fecha vintage representa los datos efectivamente disponibles ese día; test usó headers vintage y no valores actuales. Los dos cortes NO certifican cada uno de los 104 meses, y no se usaron para calcular retornos ni pesos.
4. Proveniencia [OCDE/FRED ocho series](QORE_NATIVE_H4_EIGHT_CURRENCY_OECD_3M_FRED_SOURCE_CANDIDATE_2026-10-12.md), sin exportar valores RAW con licencia ni precios M5. ALFRED entrega CSV HTTPS, se calculó SHA256 temporal de bytes; reporte artefactos sólo almacena fechas, counts, IDs y hash.

## Estado e instrucción accionable, distinta de probar parámetros nuevos

- **H4 verdadero: carry forward descontado 1 mes BID/ASK, 28 pares:** sigue `BLOCKED_NO_AUTHENTIC_PIT_CARRY_SOURCE`, [PR #883](https://github.com/mezas3238-hue/qore-core/pull/883), [issue #884](https://github.com/mezas3238-hue/qore-core/issues/884). Nada de Sharpe, 0/3 traders certificados.
- **H4b eventual proxy tasa 3 meses**: FRED/OCDE 2026 retrospectivo `831/832` meses, pero **PIT histórico 8/8 no demostrado** (CHF lag hasta 2021-12 en vintage dic 2023). Requiere datos suizos contemporáneos de referencia compatible/benchmark específico, sus vintages y resto de 104 meses comprobados, además de prereg separado de 3M. Nunca "usar 3M como 1M forward" ni asumir swap broker=interbank.
- **Opción alternativa más directa:** adquirir ocho cotizaciones USD FX forward 1M con vintages y cobertura as-of, derivar 28 cruces siempre que triángulo de forwards y bid/ask de cruces se trate correctamente, o tasa funding con convenciones/timing homogéneas. Esto reduce potencial compra de 28 instrumentos a 7 quotes USD-foreign **solo si están respaldados por fuente y contrato exactos**; triangulación puede crear precios sintéticos no ejecutables, etiqueta obligatoria.
- No se abrió ningún mercado ni retorno de **2024-09-17+**; solo se consultó tasa histórica hasta 2024-08. Nada de CIBO, Shared, VPS, MT5, LIVE, QDLE. Nada de tuning tras ver Sharpe. **0/3 certificados**.

**Conclusión:** se convirtió un vago "faltan datos" en una fuente económica concreta con control de versiones históricas y una discontinuidad precisa por resolver, sin simular un edge que no puede valorarse.

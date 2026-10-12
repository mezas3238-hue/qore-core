# H4 QORE Native — fuentes OCDE/FRED de tasas 3M, ejecución REAL y hallazgo puntual

**12/10/2026. Nuevas fuentes verificadas, ninguna señal carry o PnL económico calculados.**

- [PR #885](https://github.com/mezas3238-hue/qore-core/pull/885) DRAFT. Fuente: [OECD Main Economic Indicators via FRED](QORE_NATIVE_H4_EIGHT_CURRENCY_OECD_3M_FRED_SOURCE_CANDIDATE_2026-10-12.md), 8 series reales 3M interbank mensual.
- **[GitHub Actions #38321986085](https://github.com/mezas3238-hue/qore-core/actions/runs/38321986085)** `COMPLETED SUCCESS`, HEAD real `9110092f99da29e2edba6d0a3a3c7db9e7d2539e`; test sintético **10/10 PASS** y 8 HTTP GET reales FRED por allowlist correctos. Datos de tasa RAW no se publicaron.
- Periodo consultado 2016-01-01 → 2024-08-01 inclusive: **104 observaciones mensuales esperadas por serie**, 832 slots para 8 monedas.
- Resultado real 2016-01..2024-08: AUD 104, CAD 104, CHF 104, EUR 104, GBP 104, JPY 104, NZD 104, **USD 103**, faltando **2020-04-01** = `.`. Por tanto **831/832 valores** y **103/104 meses con cobertura simultánea 8/8**; no rellenar abril 2020 ni elegir otro USD arbitrario. Falta documentada también en [tabla FRED oficial USD](https://fred.stlouisfed.org/data/IR3TIB01USM156N), dato ausente `2020-04-01 | .`, por lo que no es un error de descarga. Coverage report contiene fechas exactas y SHA de bytes recibidos, no valores.
- Tres corridas preliminares de CI observaron consistentemente cobertura 7/8, siempre USD abril 2020; no verificar económicamente ni ajustar PnL a la vista del dato.

## Gates aún BLOQUEADOS, sin exagerar

La fuente sirve para probar que **existen observaciones históricas mensuales 3M para 8 monedas**. No son forwards BID/ASK 1M de la regla original H4, no son permutas de un contrato CIBO/IC Markets, ni se acreditan versiones conocidas en su fecha t. Datos retrospectivos FRED pueden revisarse en años posteriores. No atribuir vintage historical/causal aunque se aplique lag arbitrario. El próximo paso **cuantificable** es obtener ALFRED vintages 2016–2024, con header por vintage y disponibilidad de observaciones en fecha real (sin usar cifras revisadas), sin exportar tasas RAW. Esto abre un posible **H4b nuevo proxy de diferenciales interbancarios 3M** que requiere *preregistro separado* y cash carry modelado; jamás sustitución silenciosa de H4 1M forward.

**Estados:** H4 authentic forward `BLOCKED_NO_AUTHENTIC_PIT_CARRY_SOURCE`; 3M SOURCE COVERAGE `7_OF_8_COMPLETE_ONE_MISSING_USD_2020_04`; 3M PIT `NOT_YET_VERIFIED`; NET `NO`; Sharpe `null`; 0/3 traders; holdout 2024-09-17+ NO leído, no producción.

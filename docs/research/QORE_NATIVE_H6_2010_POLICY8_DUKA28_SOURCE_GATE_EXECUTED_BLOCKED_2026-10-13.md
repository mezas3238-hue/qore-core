# QORE Native H6 — prueba única de viabilidad 2010–2015 EJECUTADA; SIN backtest por fuentes insuficientes

**Ejecutado 13 octubre de 2026 UTC, con política explícita de no retune y el holdout desde 2024-09-17 cerrado.**

## Registros auditables

- [PR #888](https://github.com/mezas3238-hue/qore-core/pull/888), rama de investigación `research/qore-native-h6-risk-scaled-carry-2010-preflight-20261012`.
- [Preregistro H6 ANTES de explorar las fuentes](QORE_NATIVE_H6_RISK_SCALED_CARRY_2010_EXTENSION_PREREG_SOURCE_FIRST_2026-10-12.md), commit `b1d4eae2014dd484282f60f4a9c88c7defbadaeb`: señal ocho políticas BIS m−2, long6/short6 28FX, 2bp lado, global vol20 de los siete USD majors, target 10% sobre RMS vol20 y cap gross×2, Sortino mensual MAR0, bootstrap moving blocks de seis meses 10k y tail-risk/máx DD, fuente homogénea, NO acceso a holdout.
- [Actions #38326759354](https://github.com/mezas3238-hue/qore-core/actions/runs/38326759354) **COMPLETED SUCCESS 2/2**: synthetic guard **10/10 tests PASS** y exactamente una ronda de proveedor **source-only**. HEAD ejecutado **`2fff071bc3cc8683a87af13b447f8a60c52a455d`**.
- [Artifact #11781480034](https://github.com/mezas3238-hue/qore-core/actions/runs/38326759354/artifacts/11781480034), ZIP SHA256 **`a53cd7e10ba36c57538a00257cf14e2b55dc23cb698cd0f57ef58b511e71b211`**, vence **2026-11-12T00:24:43Z**. Contiene JSON con IDs, fechas de cobertura, conteo de fuentes, causas de error genéricas, SHAs de muestras; NO valores de FX ni tasas BID/ASK o PnL.

## Cobertura real BIS ocho políticas 2010–2015

Intervalo obligatorio para el test pretendido: tasas mensuales **mayo 2010–diciembre 2015**, 68 meses, incluye dos meses de precalentamiento para una decisión en julio 2010. Fuente oficial BIS `WS_CBPOL`, tasa de política mensual ex post publicada actualmente, todavía no acreditada vintage as-of.

| Divisa | Cobertura mensual | Primera | Última | Hueco observado |
|---|---:|---|---|---|
| AUD | 68/68 | 2010-05 | 2015-12 | Ninguno |
| CAD | 68/68 | 2010-05 | 2015-12 | Ninguno |
| CHF | 68/68 | 2010-05 | 2015-12 | Ninguno |
| EUR | 68/68 | 2010-05 | 2015-12 | Ninguno |
| GBP | 68/68 | 2010-05 | 2015-12 | Ninguno |
| **JPY** | **36/68** | **2010-05** | **2013-04** | **2013-05 hasta 2015-12: 32 meses ausentes** |
| NZD | 68/68 | 2010-05 | 2015-12 | Ninguno |
| USD | 68/68 | 2010-05 | 2015-12 | Ninguno |

Nota adicional de H5: en 2016 la misma serie `M.JP` retornó únicamente desde **septiembre 2016**. En conjunto la fuente exacta BIS JPY usada en H5 NO garantiza 2013-05..2016-08. No afirmar que el Banco de Japón careciera de políticas o indicadores alternativos: el dataset de policy rate se ve interrumpido. [BIS explica series históricas empalmadas y cambios de régimen de policy instrument](https://data.bis.org/topics/CBPOL). Rellenar retrospectivamente con otro instrumento o con 2026 crearían una nueva definición/posible lookahead; requeriría definición y pruebas separadas preeconómicas.

## Muestra externa FX 2010 y 2015

Preflight concreto de **dos horas de muestras** Dukascopy BID/ASK comprimidas, sin descargar décadas ni tocar datos posteriores al embargo. Fechas martes **2010-06-15 12:00 UTC** y **2015-06-16 12:00 UTC**, cada una con 28 symbols, protocolo .bi5/LZMA y 20 bytes/tick, sha256 y conteos. Solo **27/56** validaciones:
- 2010-06-15: **14/28** muestras pasan el comprobador;
- 2015-06-16: **13/28** muestras pasan;
- 29 de 56 dan `SAMPLE_UNAVAILABLE` / `ValueError` genérico. **No discrimina 404, rate limit, redirección, fallo LZMA o verdadera falta de ticks**: NO usarlo para afirmar que los 29 mercados no tienen histórico. Existe evidencia de 27 archivos accesibles/parseables; no cobertura homogénea completa.
- Muestras individuales NO acreditan 28 activos continuos todos los meses/días 2010-2024, datos del broker original ni licencia de derivados para distribución. RAW nunca depositado en GitHub.

## Decisión estricta, sin otro cambio de hipótesis

**Resultado de gate `H6_DATA_CONDITION_NOT_MET`.** No hay un solo backtest H6; ninguna métrica Sortino o Sharpe económica fue calculada, ningún H5 fue reoptimizado, no se leyó holdout 2024-09-17+.

Condiciones para H6:
1. **JP policy 2013-05→2016-08**, tasas históricas oficiales con benchmark/convención y fuente suficientemente respaldada, sin rellenar huecos con 2026 o resultado de spot futuro.
2. **28 pares FX en toda 2010-07→2024-09-16** con única procedencia o puente históricamente homologado de proveedor; al menos BID/ASK y fuente/licencia; las 27 muestras válidas no bastan para descargar full-series.
3. PnL financiado **broker NET no acreditado** por H5 ni H6; un posible Sortino B de interés idealizado no prueba carry monetizable. 2010–2015 es historia añadida por atrás, NO 2024–2026 holdout nuevo; 2016–2024 ya se usó para H1–H5.

**Decisión de recursos:** detener aquí la línea H6 como ejecución económica hasta que exista un paquete único verificable con las ocho políticas y 28 pares para este tramo. No convertir el siguiente turno en otra ronda de variantes; sólo desbloquear el P0 concreto de cobertura si se decide continuar la adquisición de datos. **0/3 traders QORE Native certificados.** No producción, CIBO, Shared, MT5, VPS, QDLE ni LIVE.

Referencias académicas: [Brunnermeier–Nagel–Pedersen, Currency Crashes (NBER)](https://www.nber.org/papers/w14473) sobre cola negativa; [Pezier–White adjusted Sharpe](https://search.r-project.org/CRAN/refmans/PerformanceAnalytics/html/AdjustedSharpeRatio.html) corrige sesgo y curtosis; Sortino al alza no equivale automáticamente a mejor riesgo de crash. La SE Sharpe anual `sqrt(12/33)≈0.603` para H5 es aproximación con meses IID, no intervalo robusto.

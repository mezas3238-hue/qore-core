# DCVC — primera ejecución científica A/B (Audit 01): dictamen negativo de selección

**Emitido:** 2026-10-11. **Fuentes:** prerregistro existente antes de resultados `d0ef43ec066475ea377a95a82bc05dafc4109d3f`; GitHub Actions [#38107014488](https://github.com/mezas3238-hue/qore-core/actions/runs/38107014488) **11/11 SUCCESS**, commit del código del replay `9d1f073960d4a422a40f8c982ec312f115f95af7`; artefacto científico completo [#11690128444](https://github.com/mezas3238-hue/qore-core/actions/runs/38107014488/artifacts/11690128444). El documento actual sigue siendo investigación: **NO LIVE / NO VPS / NO MERGE / NO CERTIFIED**.

## Reproducción exacta de línea de base antes de evaluar B

Se consolidaron `2876/2876` fuentes de V49 sobre 9 símbolos M1 provider-native y se reconstruyó sin modificaciones `MAX3=2020` con `1167` ganadoras, PF bruto `0.6644630742216047176`, DD `236.13428435633587R`, total `-233.26932707637R`, expectativa `-0.11547986488929R`. Fuente histórica pin run 38053946695, SHA e356e7a52541e99533b25ecfef0ab9c4e9ce03c0. Control reprodujo y ninguna entrada/stop/target congelados se modificó.

## Resultado agregado de selección causal prequential

| Métrica bruto (SIN broker costes) | A V49 | B DCVC |
|---|---:|---:|
| N ejecuciones | 2020 | 266 |
| PF | 0.664463 | 0.851825 |
| DD máximo R | 236.1343 | 19.9324 |
| Gross profit R | 461.9428 | 63.5193 |
| Gross loss R | -695.2121 | -74.5686 |
| R neto bruto | -233.2693 | -11.0492 |
| Expectancy bruto R/trade | -0.11548 | -0.04154 |
| Win rate | 57.77% | 66.17% |
| Máxima racha perdedora | 8 | 8 |

B acepta solamente **13.17%** de las ejecuciones A (reduce frecuencia **86.83%**). El DD cae ~91.56% nominal, pero **la mayor parte de esta caída no prueba un edge por sí sola**: hubo muchas menos operaciones. A escalado a exposición equivalente por fracción N_B/N_A (heurística sin modelar sincronización/fills): DD `31.09491R`. B da `19.93244R`; diferencia todavía favorable en la muestra, pero **no es una prueba independiente/confirmatoria**.

La retención es inadmisible según guardrail Owner: solo **170/1167 ganadoras originales = 14.57%**, suma de beneficio original retenido **61.7819606R de 461.9427618R = 13.37%**; límites mínimos 934 IDs (80%) y 415.74849R (90%). El PF bruto B sigue **menor que 1**, además de expectativa negativa. **Hipótesis de ventaja explotable general NO CONFIRMADA; variante B actual NO PROMOVIBLE.**

## Sensibilidad de costes supuestos, NO BID/ASK físico

| Coste fijo supuesto R/trade | PF A | PF B | DD B | Esperanza B |
|---|---:|---:|---:|---:|
| 0 | 0.66446 | 0.85182 | 19.9324R | -0.04154R |
| 0.025 | 0.60416 | 0.76975 | 23.0384R | -0.06654R |
| 0.05 | 0.54821 | 0.69322 | 27.2930R | -0.09154R |
| 0.10 | 0.44977 | 0.55874 | 39.1142R | -0.14154R |

**Nunca presentar estos supuestos como spreads/comisiones medidos:** provider OHLC M1 no es un feed sincronizado bid/ask+broker+slippage.

## Muestra cronológica y advertencia de pseudo-test ya consultado

- TRAIN: A n1213 PF 0.70928/exp -0.09691R; B n188 PF 0.79805/exp -0.05859R.
- VALIDATION: A n396 PF 0.57339/exp -0.15958R; B n32 PF 0.70291/exp -0.08866R.
- PSEUDO_TEST_CONSUMED: A n411 PF 0.63202/exp -0.12778R; B **n46 PF 1.26738/exp +0.06091R**. Es una submuestra pequeña y **NO** un holdout independiente; los datos de 2025/2026 ya informaron la arquitectura de QORE. **No seleccionar régimen ni umbral basándose en estos 46 resultados**.

Los 100 placebos aleatorios igualaron el número de B por sesión/fecha pero sus números de plazas B son posthoc: comparación *diagnóstica*, no selección live. Con costo supuesto 0.025R: PF placebo [0.3882, 0.7578], promedio `0.58324`; DD R [24.80,67.63], promedio `41.56R`. Estas cifras no reemplazan bootstrap dependiente y no demuestran superioridad OOS.

## Diferencia fuente e incertidumbre

`regimes_unknown=184` de 2876 oportunidades; en los 266 B ejecutados, 181 corresponden a `UNKNOWN`, contexto sin 241 minutos continuos completos. Es primordial: el resultado B está dominado por **un mecanismo de fallback informativo** en vez de evidencia positiva para regímenes aprendidos. B no implementa M30→M3 CISD ni estructura 30M autoral; H1→M15→M1 V49 sigue igual y tiene sus ambigüedades metodológicas. `C` **BLOCKED** por falta de contexto histórico completo as-of del Master Frame, cartera y BID/ASK reales; cero PF/DD cognitivo medido.

## Veredicto y tareas antes de nueva variante

**NEGATIVO / NO PROMOVER.** DCVC v0.1 no demuestra ventaja condicional robusta: PF bruto<1, expectativa negativa, destruye >=85% de frecuencia y solo retiene ~14% ganadores fuente. El pseudo-test puede sugerir hipótesis a explorar, pero no certifica.

Mantener algoritmo de esta ronda **congelado**. Priorizar (1) completar bootstrap de bloques por día y revisión de placebos; (2) verificar fuga de calendario/fuente H1, cobertura M1 y razones `UNKNOWN`; (3) conseguir bid/ask comisiones reales; (4) construir universo verdaderamente causal first-online y M30→M3 independiente con fuentes TTrades; (5) conectar C Full Master Frame sin reemplazarlo por proxy; (6) conseguir OOS prospectivo no usado. **NO ajustar los 0.35/1.0/0.025/60/20 para hacer bonito PF** en esta cohorte.

Artefacto de nueve mercados: [Run #38107014488](https://github.com/mezas3238-hue/qore-core/actions/runs/38107014488). Este dictamen no altera trading ni producción.

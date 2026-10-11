# DCVC AUDIT02 — GATE 1 exposición equivalente y GATE 2 anatomía de las 266 decisiones

**Fecha de cierre:** 2026-10-11. **Estado:** STOP / DCVC v0.1 NO PROMOVIBLE; hipótesis de ventaja condicional general NO REFUTADA. **Estudio retrospectivo EXPLORATORIO, no certificación.** Congelación antes del ensayo: [protocolo Gate1/2](QORE_SCALPER_DCVC_GATE1_GATE2_FROZEN_EXPOSURE_NULL_PROTOCOL_2026-10-11.md), commit `376de22b5407f535f46d7962a7b0b10b01c63ad4`. Relectura inmutable del A/B `38107014488` y `9d1f073960d4a422a40f8c982ec312f115f95af7`, sin tocar el detector.

**Evidencia GitHub:** [Actions #38108374819, SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38108374819), SHA `ed20800f861ffe63e8fb015d7e491373d7106480`, artefacto completo [#11691080220](https://github.com/mezas3238-hue/qore-core/actions/runs/38108374819/artifacts/11691080220). ZIP contiene `dcvc-gate1-gate2-scientific-results.json`, distribuciones de cada una de las 5000 selecciones aleatorias y 2876 filas de decisiones as-of verificadas.

## GATE 1 — Test contra distribución nula de exposición igual

**Población congelada:** 2876 identidades, A 2020 trades, B 266 trades y MAX3 idénticos. Mismo payoff histórico V49 source-anchored; **no regeneración H1/M15/M1 first-online**, no BID/ASK físico. Se extrajeron 2000 muestras de 266 oportunidades uniformemente aleatorias del conjunto de 2876, con límite <=3 por sesión/fecha. La selección por semilla NO lee outcomes ni copia los conteos diarios retrospectivos de B. Es placebo **offline**: la condición final exactamente N=266 de un universo retrospectivo conocido NO equivale a una política ejecutable en tiempo real. Se mantiene como evaluación EXPLORATORIA.

**Todos los valores de la tabla incorporan costo SUPUESTO, nunca físico, de 0.025R/trade.**

| Métrica | B original v0.1 | Media placebo global N=266 | Percentil 2.5–97.5 placebo | p unilateral bruto | p Holm ajustado (tres métricas) |
|---|---:|---:|---:|---:|---:|
| PF | 0.76975 | 0.58969 | 0.41761 – 0.81671 | 0.04898 | **0.10495** |
| Esperanza R/trade | -0.06654R | -0.14415R | -0.22551 – -0.05573R | 0.03998 | **0.10495** |
| DD R | 23.03844R | 41.37626R | 21.90166 – 61.34675R | 0.03498 | **0.10495** |

p calculado con corrección `(mejor_igual+1)/(N_sim+1)`; PF/esperanza cola alta, DD cola baja. Bonferroni-Holm familywise alpha 0.05. **Ninguna métrica supera el gate ajustado**; los p no ajustados <0.05 son pista exploratoria y NO resultado estadístico confirmatorio. La distribución aleatoria NO respeta por sí misma autocorrelación diaria, por lo que NO debe confundirse con el bootstrap de bloques de Audit01b, cuyo DD ajustado por exposición tiene intervalo que incluye 0.

### Controles de sensibilidad

- **A-first3-266**, 2000 semillas sobre solo las 2020 de A (sin remplazo/relleno por nuevas fuentes): medias de PF 0.60656, esperanza -0.14186R, DD 40.20394R; p ajustados para los tres objetivos **0.12594**.
- **B-symbol/session-marginals**, 1000 semillas con el número de B por símbolo/sesión conocido retrospectivamente (diagnóstico posthoc, no placebo principal): medias PF 0.58817, esperanza -0.14447R, DD 41.28784R; p ajustados **0.11089**.
- **A full 2020:** PF con coste supuesto 0.60416, DD 286.5093R; **B full 266:** PF con coste supuesto 0.76975, DD 23.03844R. Comparar solo DD absolutos sería engañoso; A escalado a 266/2020 por unidad de riesgo no es una cartera real. Bootstrap previo de cinco días `38107458602`: intervalo B−A en DD ajustado por exposición **[-28.7799,+0.0433]R**: incluye cero.

**Dictamen gate 1:** B favorecido débilmente por tres puntajes brutos en la misma historia consumida, pero NO significativo tras control de familia, y absoluto PF <1 y expectativa negativa. No autorizar promoción.

## Potencia de detección bajo efecto hipotético

Simulación predeclarada de 1000 aleatorizaciones válidas más, shift uniforme a R/trade bajo hipótesis sintética, no evidencia de ventaja real. Umbral unilateral de esperanza al 5%: **-0.07386R/trade** con coste hipotético 0.025R.

| Incremento *artificial* de R por trade | Potencia estimada para superar umbral |
|---:|---:|
| +0.05R | 32.0% |
| +0.10R | 75.8% |
| +0.20R | 100.0% |
| +0.30R | 100.0% |

El primer paso de la malla que supera 80% es **+0.20R**. No leerlo como MDE poblacional preciso (una malla de valores no permite interpolación robusta, y el método no modela shocks/correlación de fechas ni variantes de payoff). **INSUFFICIENT_POWER_FOR_SMALL_EFFECTS**: esta prueba no puede negar una mejora verdadera de +0.05R y su potencia a +0.10R sigue bajo 80%. No corresponde etiquetar la hipótesis universal `EDGE_FALSIFIED`.

## GATE 2 — Reejecución idéntica del razonador v0.1

Reglas originales `DCVCState.admit()`, mismas 2876 decisiones, la misma ordenación y liquidaciones B `exit_at < decision_at`. Los 2876 IDs y **todas** las selecciones/rechazos/estimadores y las 266 ejecuciones coinciden exactamente con el ledger original. **No se ha editado el componente v0.1**.

| Motivo de decisión efectivamente EJECUTADA | Trades B | PF con coste asumido 0.025R | Esperanza asumida R/trade |
|---|---:|---:|---:|
| COLD_START_PASS | 60 | 0.39524 | -0.23801R |
| UNKNOWN_INFORMATIONAL_PASS | 177 | 1.01951 | +0.00502R |
| UNDERPOWERED_INFORMATIONAL_PASS | 29 | 0.44475 | -0.14849R |
| FROZEN_POSTERIOR_EXPECTANCY con estimación positiva | **0** | N/D | N/D |
| **TOTAL** | **266** | **0.76975** | **-0.06654R** |

Ojo: las **181 ejecuciones UNKNOWN** por característica incluyen **177 con motivo efectivo UNKNOWN y 4 en COLD_START**, debido a la precedencia de reglas. En los 2876 intentos originales, 77 recibieron COLD_START, 180 UNKNOWN, 30 UNDERPOWERED y 2589 entraron en comparación FROZEN_POSTERIOR_EXPECTANCY; 21 pases sin evidencia quedaron sin cupo MAX3. **Ninguna** operación que alcanzó la regla de posterior positivo fue seleccionada; las 2589 decisiones de esa etapa no produjeron trade. El componente en v0.1 es de facto **fallback permisivo + bloqueo muy agresivo** de los regímenes con datos, no detector demostrado de ventaja positiva.

**Valor económico por motivo:** UNKNOWN_PASS 177 operaciones tiene PF 1.0195 y esperanza +0.0050R *bajo costes supuestos*; una mejora ínfima, no confiable, dominada por condiciones de cobertura/horario y que desaparecería bajo un diferencial adicional de ejecución de >0.005R en promedio. NO elevar la etiqueta UNKNOWN a regla de trading ni optimizar basándose en esto.

## A∩B y efecto de reemplazo de cupos

| Cohorte | N | PF coste supuesto 0.025R | Esperanza R/trade |
|---|---:|---:|---:|
| A∩B / A-only veto sin rellenar | **252** | 0.77689 | -0.06562 |
| B\\A / B rellena fuentes posteriores | **14** | 0.57722 | -0.08305 |
| A\\B / originales descartadas | **1768** | 0.58424 | -0.15115 |

El **relleno sólo aporta 14/266 (5.3%)**; en esta muestra es económicamente negativo y **no explica la mayoría** de la selectividad observada. La comparación A-only veto reutiliza la trayectoria de aprendizaje B para saber qué vetar: no representa una nueva cognitiva entrenada en un escenario sin refill.

Original A ganó 1167 operaciones; 170 de estas permanecen dentro de B (14.57%), y solo 266 posiciones totales hacen matemáticamente imposible preservar 80% de 1167 wins. Es pérdida de frecuencia/coverage primero, no un incumplimiento independiente del win rate condicionado al N.

## STOP-GATE del arquitecto

**CERRAR DCVC v0.1 PARA PROMOCIÓN, NO REAJUSTAR.** Razones:
1. PF agregado con coste supuesto = **0.76975** e **esperanza = -0.06654R**, antes incluso de BID/ASK broker/slippage físicos.
2. N266 vs A2020, destruye 86.83% de operaciones y 85.43% ganadoras originales.
3. CERO trades elegidos por evidencia positiva del posterior de régimen; todos COLD/UNKNOWN/UNDERPOWERED.
4. Holm 3 métricas p **0.105**, DD exposición equivalente aún inconcluso por bloques.
5. Histórico consultado, potencia para efectos pequeños insuficiente; no OOS independiente.

**No afirmar que todos los edges de Scalper sean imposibles.** Conservamos el hallazgo débil de discriminación in-sample como hipótesis no confirmada; nuevo trabajo que implique reglas DCVC requiere cohorte NUEVA + preregistro separado. Gate3 `UNKNOWN` puede estudiarse como diagnóstico de calidad/cobertura causal, **no** como optimización posterior v0.1; Gate4 costes físicos y Gate5 cognitiva real continúan sujetos a la evidencia y recursos. **TTrades M30→M3 es modelo metodológico independiente y NO se descarta porque falle este gate.**

**Sin VPS / producción / LIVE / MERGE / certificación.**

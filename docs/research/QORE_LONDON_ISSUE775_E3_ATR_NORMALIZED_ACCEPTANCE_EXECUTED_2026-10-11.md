# QORE — Londres E3: ¿la divergencia EURUSD/GBPUSD desaparece al normalizar aceptación por volatilidad?

**Fecha:** 2026-10-11 · **Estado:** `E3_EXECUTED_4_OF_4_SUCCESS / EXPLORATORY / NOT_CERTIFIED`.

**Enlaces de evidencia:** [E3 GitHub Actions #38153593288 — 4/4 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38153593288), [aggregate original JSON #11707821510](https://github.com/mezas3238-hue/qore-core/actions/runs/38153593288/artifacts/11707821510), [EURUSD E3 row-ledger #11707548302](https://github.com/mezas3238-hue/qore-core/actions/runs/38153593288/artifacts/11707548302), [GBPUSD E3 row-ledger #11706974510](https://github.com/mezas3238-hue/qore-core/actions/runs/38153593288/artifacts/11706974510). [PR #782, borrador](https://github.com/mezas3238-hue/qore-core/pull/782). Código ejecutado SHA `45516e1ea7ba54f1a13f9e81a877abe906c6c480`, [PRERREGISTRO E3](https://github.com/mezas3238-hue/qore-core/blob/research/london-eurgbp-acceptance-atr-e3-20261011/docs/research/QORE_LONDON_E3_ATR_NORMALIZED_ACCEPTANCE_PREREG_2026-10-11.md) commit `ff25c671d3dfba53ced15e2944208b8566c0dfc2`, publicado ANTES de registrar el código o consultar los outcomes E3.

## 1. Correcciones metodológicas respecto al dictamen anterior

1. El cambio de la interacción +22,38 pp sobre cohorte original a +14,42 pp sobre submuestra con H4 E2 reconstruible es **cambio de composición/selección por disponibilidad**, NO "36% de señal causado por gaps" ni "36% del efecto vive allí". La reducción relativa de los estimadores es `(22.38-14.42)/22.38 ≈35.6%`; no constituye descomposición aditiva ni causal de componentes.
2. Sobre LOS MISMOS 282 casos con H4 E2, estandarizar por H4 cambia +14,42 a +14,33 pp (~0,10 pp): la tendencia H4 proxy no explica ese contraste específico dentro de tal submuestra. **Sin concluir que H4 no importa** o que las horas de Londres tienen un feed defectuoso.
3. `RECLAIM_INSIDE` = cierre del checkpoint dentro del Asia low..high. `ACCEPTED_OUTSIDE` ORIGINAL = tres cierres consecutivos fuera del rango. E3 cambia únicamente **la definición de aceptación**: no confundir esos dos estados.
4. Bootstrap de bloques compartidos por fecha es control de dependencia intradía/de pares, no replicación independiente ni garantía de cobertura de regímenes; serie histórica ya consultada.

## 2. Diseño congelado de la prueba E3

Dos activos: EURUSD y GBPUSD; mismo ledger inmutable de [source-only #38150980682](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682), **261 jornadas NY por par, 227 EUR/231 GBP checkpoints válidos**, los mismos outcomes +60m, mismas reglas `REVERSAL` / `CONTINUATION` = ±0,25 **rango asiático** a partir del cierre checkpoint tras 11 M1 desde primer raid. No altera outcomes ni timestamps.

`ATR14_M15_ASIA`: reconstruido a partir de las 240/240 M1 nativas observadas de Asia 20:00–00:00 NY; 16 velas M15 internas, último 14 true ranges con precio cierre M15 previo, **todo conocido ANTES de primer raid Londres**. Nuevo estado `ACCEPTED_ATR_0P5`: cierre del checkpoint al menos **0,50× ATR14 M15** más allá del Asia high/low (en el lado del primer raid), con independencia de tres cierres consecutivos. `RECLAIM_INSIDE` permanece literalmente igual, `OUTSIDE_WEAK` se contabiliza explícitamente. Ninguna optimización de 0,5ATR post-outcome. Se preserva `OPPOSITE_OUTSIDE`, si aparece.

## 3. Resultados por mercado

| Estado a checkpoint | EURUSD n/REVERSAL | GBPUSD n/REVERSAL |
|---|---:|---:|
| `RECLAIM_INSIDE` (sin cambios) | **38/94 = 40,43%** | **22/92 = 23,91%** |
| `ACCEPTED_ATR_0P5` nuevo | **35/88 =39,77%** | **42/98 =42,86%** |
| `OUTSIDE_WEAK` (descriptivo) | 8/45 =17,78% | 15/40 =37,50% |
| `OPPOSITE_OUTSIDE` | 0/0 | 1/1 (descriptivo, n ínfimo) |

Diferencia de tasas `REVERSAL | RECLAIM` menos `REVERSAL | ACCEPTED_ATR`:
- **EURUSD: +0,6528 pp** (prácticamente cero).
- **GBPUSD: −18,9441 pp**.
- **Interacción EUR−GBP: +19,5969 pp**. Bootstrap conjunto de fechas NY en bloques de 5 días con 2.000 repeticiones y seed fija 77520261013: **IC95 [+3,2075,+35,6730] pp**, proporción I<=0 entre réplicas **0,005**. Este CI histórico NO es replicación OOS ni evidencia de edge invertible en mercado.

La interacción antes de E3 era +22,3803 pp (mismos pares pero OTRO conjunto de estados), cae 2,7834 pp bajo el nuevo diagnóstico de ATR (~12,4% relativo al estimador original), **no desaparece**. No declarar que las definiciones son estadísticamente equivalentes ni que esto prueba causalidad de volatilidad: al cambiar ACCEPTED cambia el denominador de los grupos y la composición.

### 3.1 Transición original → E3 (control de libertad de selección)

| Origen | EURUSD nuevo ACCEPTED_ATR | EURUSD OUTSIDE_WEAK | GBPUSD nuevo ACCEPTED_ATR | GBPUSD OUTSIDE_WEAK |
|---|---:|---:|---:|---:|
| `ACCEPTED_OUTSIDE` (3 cierres) | 83 | 32 | 96 | 27 |
| `OUTSIDE_UNCONFIRMED` | 5 | 13 | 2 | 13 |

Todos los RECLAIM antiguos permanecieron en RECLAIM (EUR94, GBP92); EUR 0 y GBP 1 OPPOSITE. **No borrar los OUTSIDE_WEAK para afirmar frecuencia de señal**. Cohorte nuevo contraste `RECLAIM vs ACCEPTED_ATR`: EUR 94+88=182; GBP 92+98=190; total **372**. El resto de los 458 se registra como grupo débil/opuesto; no es trade descartado por resultados.

### 3.2 Escala relativa

Medianas ATR14 M15 de Asia en grupo `ACCEPTED_ATR` son **EUR 3,77 pips** y **GBP 4,59 pips** (aproximadas del M1 nativo); rangos Asia medianos EUR **15,7 pips**, GBP **18,4 pips**. Una misma norma de `0,5 ATR` no equivale a imponer la misma distancia absoluta en ambos símbolos.

## 4. Composición de jornadas con H4 E2 no reconstruible

Este es un reanálisis del CONTRASTE ORIGINAL `RECLAIM vs 3 cierres fuera` separado por H4 E2:

| H4 E2 cobertura | EUR RECLAIM rev | EUR ACCEPTED rev | GBP RECLAIM rev | GBP ACCEPTED rev | Interacción |
|---|---:|---:|---:|---:|---:|
| H4 E2 reconstruible | 24/60 | 31/76 | 19/65 | 36/81 | **+14,42 pp** |
| H4 E2 desconocida | 14/34 | 9/39 | 3/27 | 14/42 | **+40,32 pp** |

- Bootstrap de 2.000 fechas compartidas por bloques 5 para H4 conocida: CI95 **[−4,42,+32,90] pp**.
- Bootstrap en H4 E2 desconocida: CI95 **[+15,97,+62,96] pp**. Este es un contraste seleccionado por missingness, NO prueba de mala calidad de las M1 del primer raid, ni diagnóstico de que un grupo contiene más feriados/rollover: analizar sus timestamps y cobertura antes de adjudicar causa.
- E2 H4 conocido cubre 305/458 checkpoints, y H4 desconocido 153/458. Dentro de estados originales R/A: conocido **282/424** y desconocido **142/424**. El número de H4 desconocidas no revela por sí solo dónde ocurrió la ausencia de M1.
- No se ha testeado formalmente con prerregistro independiente la diferencia de interacciones entre grupos de missingness ni se ha demostrado un mecanismo de missing-not-at-random. **La diferencia descriptiva es suficientemente grande para elevar la auditoría de procedencia, no para llamarla causa.**

## 5. Dictamen, STOP/GO

**Resultado esencial:** la normalización por **ATR14 M15 0,5×** de la aceptación del rango **no elimina** la divergencia de EUR y GBP en este histórico; el contraste permanece +19,60 pp con CI bootstrap positivo. En EUR el estado RECLAIM vs aceptación normalizada casi no discrimina; en GBP la discrepancia de tasas continúa, **pero no equivale a rentabilidad ni a dirección operable**.

**Resultado limitante:** el histórico está reutilizado, la selección por cobertura H4 altera la estimación del efecto original, y datos H4 faltantes muestran interacciones mayores. La definición autoral TTrades CISD/MSS no ha sido certificada. Ningún hallazgo permite afirmar causalidad, confirmar condición RECLAIM entre pares, ni optimizar thresholds ahora.

**STOP construcción de trader / filtros SMT condicionales a RECLAIM**. SMT (divergencia de extremos sincronizados entre EURUSD/GBPUSD) sigue siendo concepto independiente: el hecho de que casi todas las jornadas tengan *algún* barrido no revela su frecuencia dentro de una ventana sincronizada de 5–15 minutos. Antes de SMT económico se requiere un censo descriptivo con timestamps comunes, un nuevo prerregistro de definición y evaluación explícita de potencia, con *holdout no inspeccionado*. No empezar por escenarios 10–25 casos inventados.

**Solo GitHub / Trader Lab.** Sin operación live, VPS/MT5, modificaciones en V49/DCVC/Master Frame o certificación.

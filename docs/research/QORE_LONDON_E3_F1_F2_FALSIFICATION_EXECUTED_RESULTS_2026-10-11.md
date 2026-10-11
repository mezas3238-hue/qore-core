# QORE Londres — E3 falsación F1/F2 ejecutada (EURUSD + GBPUSD)

**Fecha:** 2026-10-11 · **Resultado del gate: `STOP_NO_PROMOTION`**. [Workflow #38156402305, SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38156402305), [artefacto JSON con los 53 bloques y todos sus IC #11708259260](https://github.com/mezas3238-hue/qore-core/actions/runs/38156402305/artifacts/11708259260), [PR #783](https://github.com/mezas3238-hue/qore-core/pull/783). Código exacto que produjo resultados SHA `a40e18317cf1e0f3ffa12f46785de59ed1c0ed35`. [Prerregistro F1/F2 previo al cálculo, commit `d8d660faf57ca1036e73626f34cd611ab42be70d`](https://github.com/mezas3238-hue/qore-core/blob/research/london-e3-f1-f2-falsification-20261011/docs/research/QORE_LONDON_E3_F1_F2_FALSIFICATION_PREREG_2026-10-11.md).

## 1. Reproducción exacta de fuente congelada
- Dos artefactos E3 source-only de [run #38153593288](https://github.com/mezas3238-hue/qore-core/actions/runs/38153593288), SHA productor `45516e1ea7ba54f1a13f9e81a877abe906c6c480`.
- 261 jornadas NY por par (522 identidades inmutables), 227 EUR y 231 GBP checkpoints válidos (**458**); outcomes y estados originales idénticos, no se rehacen ni optimizan.
- Contraste `I=(EUR P(REV|RECLAIM)−P(REV|ACCEPTED_ATR_0P5))−(GBP idem)`. Fuente E3 full: EUR 38/94 vs 35/88; GBP 22/92 vs 42/98. Todos los outcome NEUTRAL/CONTINUATION cuentan como NO REVERSAL; OUTSIDE_WEAK / OPPOSITE se conservan en censo pero no se convierten retrospectivamente en señales.
- Bootstrap circular por **cinco jornadas NY compartidas** (ambos pares en idéntica fecha), 2.000 repeticiones F1 por cohorte; 53 leave-block-out con 1.000 cada uno tanto en FULL como KNOWN; semilla 77520261014 y derivaciones predefinidas. Todos 2.000/2.000 baseline válidos; fuente histórica previamente explorada, no OOS.

## 2. F1 — ¿queda señal en jornadas con H4 E2 reconstruible?

| E3 estado normalizado por ATR | I estimada | IC95 bootstrap compartido | N por celdas (EUR RECLAIM / EUR ACCEPTED; GBP RECLAIM / GBP ACCEPTED) |
|---|---:|---|---|
| FULL | **+19,5969 pp** | [+3,4472, +34,9095] pp | 94/88; 92/98 |
| H4_E2_KNOWN | **+15,2200 pp** | **[−5,4012, +34,4663] pp** | 60/66; 65/64 |
| H4_E2_UNKNOWN | **+33,5413 pp** | [+4,3666, +62,4526] pp | 34/22; 27/34 |

**Dictamen F1: `F1_FAIL_PROMOTION_CI_CROSSES_ZERO`.** En cohorte E2 H4 reconstruible, IC incluye 0 y el preregistro lo marca como **fallo de robustez para promoción**. El estimador +15,22pp sigue positivo y no cae >=50% respecto al E3 full (+19,60pp): **NO es efecto cero demostrado ni `F1_COLLAPSE` de magnitud**. El grupo H4 UNKNOWN conserva I mayor (+33,54pp); esto es una advertencia de missingness/heterogeneidad, **NO prueba de que las M1 del raid estén rotas**. Los 126+129=255 casos R/A H4 known se reparten cuatro celdas, y 56+61=117 H4 unknown; son cohortes distintas. H4 _no disponible_ no equivale a H4 _sesgo negativo_ ni a pérdida de causalidad.

## 3. F2 — leave-one-five-date-block-out

Ordenar 261 fechas NY y partir en **53 bloques no solapados**: 52 × cinco jornadas y un bloque residual de una fecha. Para cada bloque se quitaron todas sus fechas de **ambos pares**, recalculando I y su IC95 bootstrap conjunto con **1.000 réplicas**; testigos exactos del ledger y los 53 × 2 resultados están en JSON. No se eligieron bloques a partir de resultados económicos.

| Escenario | Intervalo de estimaciones I al retirar uno | Bloques con I<=0 | Bloques con IC95 cruzando 0 | Bloques con reducción I >=50% |
|---|---|---:|---:|---:|
| E3 FULL | **[+17,5824,+22,4684] pp** | 0/53 | **0/53** | 0/53 |
| E3 H4_E2_KNOWN | **[+12,2504,+18,7250] pp** | 0/53 | **53/53** | 0/53 |

**La interacción full NO depende de un único bloque atípico bajo esta perturbación**. La submuestra H4 conocida ya tenía un IC full-baseline que incluía cero: **53/53 ICs LOBO cruzan cero, no debe interpretarse como 53 nuevas refutaciones independientes ni concentración en fechas específicas**; es falta de precisión de la cohorte reducida bajo remuestreo.

**Estrés adicional predefinido:** escoger determinísticamente los **dos bloques cuya eliminación individual más reduce I FULL**: índices #49 y #10, con fechas **19–25 ago 2026** y **19–25 nov 2025** (días NY de mercado enumerados en JSON). Al excluir los diez días simultáneamente:
- FULL: **I=+15,8276pp**, IC95 [+0,8173,+31,5175]pp (2.000 bootstrap).
- H4_E2_KNOWN: **I=+12,0402pp**, IC95 [−9,3307,+31,4977]pp.
- Ninguno invierte el signo; ningún colapso de 50% dentro del propio escenario. El estrés selecciona adversarialmente los dos bloques (según criterio predeterminado), **NO constituye experimento externo independiente**.

**Dictamen F2 preregistrado: `F2_FAIL_STRICT_PROMOTION`** porque **todas** las 53 corridas H4 known incluyen 0, aun cuando **FULL supera 53/53**. El criterio es de **promoción deliberadamente conservador**, no de "efecto cero", no una comparación con benchmark aleatorio externo ni prueba de estrategia rentable.

## 4. Interpretación corregida y decisión

1. **Confirmado sobre este histórico exclusivamente:** E3 no es neutralizado por redefinir aceptación con 0,5 ATR14 M15; F2 no identifica uno o dos bloques como la causa única. Las fechas compartidas controlan el remuestreo de dependencia entre EUR/GBP, pero no crean datos OOS ni cubren todos los regímenes macroeconómicos.
2. **No demostrado:** que divergencia RECLAIM/ACCEPTED sea una propiedad estable entre EURUSD/GBPUSD; F1 no ofrece IC exclusivamente positivo bajo cobertura H4. Missingness importa; **sus mecanismos reales no están adjudicados**.
3. **Falsación operativa:** RECLAIM/ACCEPTED para construir un trader Londres **NO PROMOVER**. Cerrar este intento de clasificación para producción; no hacer otro umbral/normalización sobre el mismo histórico para rescatarlo. **No equivale a falsar SMT** (divergencia de extremos sincronizados es un fenómeno diferente), que continúa *sin test* y no se desarrolla en este gate.
4. Si se quiere investigar SMT más adelante, preregistrar sus ventanas/definición **antes de medir frecuencia**, censar la base rate real y potencia, sin condicionarlo por este clasificador sin certificar. TTrades autor-CISD continúa sin certificado, y no se modifican V49/DCVC, Master Frame, VPS, MT5 ni live.
5. El respaldo reproducible es el **artefacto JSON**: contiene los 53 bloques, N y reversals por celda, CI por bloque, dos eliminaciones adversas, semillas, fórmulas y gates. El informe no oculta resultados negativos ni pretende añadir un nuevo edge.

**Estado final:** `RECLAIM_ACCEPTED_PROMOTION=STOP_NO_PROMOTION`; trader Londres y Scalper **NO CERTIFICADOS**.

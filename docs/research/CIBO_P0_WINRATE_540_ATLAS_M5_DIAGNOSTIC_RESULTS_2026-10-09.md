# Resultados P0 — Prueba A y descomposición de 540 aperturas PAPER

**Fecha:** 2026-10-09  
**Run GitHub Actions:** [#37976407778](https://github.com/mezas3238-hue/qore-core/actions/runs/37976407778) — SUCCESS  
**SHA de runner probado:** `a339e57738297e183b78a54679f7b7906895010f`  
**Artifact:** `11639046921`, incluye `trader-lab-cibo-qdle-spread-3368.json` y `cibo-p0-winrate-frozen-540-diagnostic.json`.  
**Código:** `scripts/cibo_trader_lab_p0_winrate_540_diagnostic.py`; tests `tests/infrastructure/test_cibo_trader_lab_p0_winrate_diagnostic.py`.  
**Protocolo de aceptación:** `docs/research/CIBO_P0_WINRATE_37PF0716_DIAGNOSTIC_PROTOCOL_540_2026-10-09.md`.

## Hallazgo principal: fixed SL/TP mejora algo, pero no salva la estrategia

Tomando LAS MISMAS señales, entry y lots, sin movimientos de SL/TP, defensiva ni parciales:

| Variante PAPER, lote congelado | Comparables con la gestión original | Win rate variante | PF variante | PnL variante USD | Válidas bajo solicitud económica original |
|---|---:|---:|---:|---:|---:|
| A: SL inicial económico + TP inicial, ambos fijos | 537 | 39,11% | 0,7851 | -44,9278 | 537 |
| A: SL inicial estructural + TP inicial, ambos fijos | 537 | 39,11% | 0,7851 | -44,9278 | 537 |
| SL 0,5 ATR14 previo + TP original | 515 | 10,87% | 0,4105 | -98,8733 | 479 |
| SL 1,0 ATR14 previo + TP original | 515 | 25,24% | 0,6484 | -87,6193 | 423 |
| SL 1,5 ATR14 previo + TP original | 508 | 34,65% | 0,7967 | -59,3694 | 384 |
| SL económico original + TP 1 ATR14 previo | 517 | 52,80% | 0,4588 | -85,3447 | 517 |
| SL económico original + TP 2 ATR14 previo | 517 | 42,75% | 0,6738 | -64,7399 | 517 |
| SL económico original + TP 3 ATR14 previo | 517 | 35,78% | 0,7839 | -48,1531 | 517 |

**Estas cohortes NO tienen idéntico número de liquidaciones entre brazos:** los n son `managed SETTLED ∩ variant SETTLED`. Las 2 posiciones sin salida original y los brazos sin recorrido M5 terminal NO entran a métricas de operaciones liquidadas. Nunca extrapolar -44,93 vs -51,17 como comparación directa: sobre las 537 *pareadas*, el managed original perdió **-$52,5196**, PF **0,70915**; variante A perdió **-$44,9278**, PF **0,78510**. Mejora de **$7,5918**, pero **sigue perdiendo**.

El SL inicial económico es exactamente el mismo SL inicial estructural en **540/540** operaciones seleccionadas. **No hay diferencia de geometría inicial entre esos dos brazos**, y no puede adjudicarse a un «SL económico más corto» sin evidencia nueva.

**Ejemplo que invalida la obsesión por >50% winrate:** TP 1 ATR acierta **52,8%** y deja PF **0,4588** / -$85,34 en 517 casos. Aumentar aciertos reduciendo tamaño de ganancia destruye expectativa: evaluar PF+payoff+costes, no solo tasa de acierto.

## Descomposición de pérdida gestionada y efecto contrafactual de remover gestión

537 operaciones cerradas tanto en A como en managed:

| Grupo mutuamente exclusivo de acciones reportadas | n | PnL original managed | PnL con A fijo | Beneficio A−managed |
|---|---:|---:|---:|---:|
| Parcial ejecutado | 21 | +$21,409 | +$12,242 | **−$9,168** |
| Stop protector actualizado, sin parcial ejecutado | 68 | +$42,522 | +$58,955 | **+$16,434** |
| Señal de defensiva (sin parcial ni modificación stop de grupos previos) | 145 | −$61,926 | −$61,601 | **+$0,326** |
| Ninguna gestión especial | 303 | −$54,524 | −$54,524 | $0,000 |

**Interpretación:** en la cohorte actual los cierres defensivos explican -$61 de pérdidas, pero eliminarlos NO da +$61: el fijo sobre esos 145 casos solo recupera ~$0,33, pues muchos tocarían SL después. El principal efecto diferencial de políticas en A parece venir de actualizaciones de stop protector (más de +$16 a favor de A), mientras que las salidas parciales aportaron +$9 a favor de la gestión. **Hay que estudiar los stops protectores por su propio mérito, no quitar todas las defensivas indiscriminadamente.**

No es una ablation exacta de un solo módulo: A apaga TODA la gestión. Estas categorías explican correlaciones retrospectivas; la siguiente batería de ablación debe aislar stop protector, defensivo y parcial uno por uno con ruta causal y sin mirar el futuro.

## Las cinco métricas solicitadas — lo realmente medido

- **SL primero, luego TP posterior:** en el benchmark fijo hubo **316 primeras salidas por SL/gap de stop**; 191 de esas tocaron el TP original más tarde dentro de 24 horas en el recorrido observable, 50 no lo tocaron dentro de 24 horas con ruta completa y 75 no tienen 24 horas completas de datos consecutivos. **Es contrafactual a posteriori, no evidencia de que ampliar SL sea viable**, y no autoriza usar información futura para gestionar.
- **>=0,5×TP antes de salir:** 162 casos entre los **359 con al menos una vela M5 completa estrictamente ANTERIOR a la vela de salida**, ≈45,13%. Otros 179 cierres gestionados no cuentan con una vela completa anterior a la salida o son censurados; no deben imputarse como ceros. No usar el extremo de la última vela de salida, pues no se conoce orden intrabar.
- **MFE media observada, solo 359 medibles:** 0,382 veces la distancia al TP original; mediana 0,432. Es una cota basada en OHLC antes de salida, no tick.
- **MAE media observada, solo 359 medibles:** movimiento contrario de 0,487 veces la distancia al SL inicial; mediana 0,480. Sin vela completa previa no se infiere MAE cero.
- **Duración por resultado:** 200 ganadoras, media **59,525 min**, mediana 25; 335 perdedoras, media **30,060 min**, mediana 10; 3 flat, media 15, mediana 20. Perdedoras viven menos, pero tiempo no prueba origen del daño.

ATR14 previo disponible **520/540**; 20 no tienen cadena mínima de barras M5 consecutivas para estimar ATR sin mirar el futuro.

## Capas de riesgo: estos escenarios NO son nuevas operaciones financiables

El grid de SL congeló el mismo lote, que NO es un permiso operativo para usar un SL distinto. Solo 479/515, 423/515 y 384/508 trades pareados de SL 0,5/1,0/1,5 ATR respectivamente entran bajo su presupuesto original de riesgo solicitado. Para valorar rendimiento financieramente realizable QDLE debe redimensionar nuevos lotes por escenario (y volver a reconciliar capital, margen, comisiones), modificando cohorte y exposición, **después** del análisis causal, con brazo de sensibilidad separado.

No hay recotización ni comisión real 2019-2022: M5 MID sintético con spread fijo de screenshots de octubre de 2026; JPY conversiones 2026. No hay MTM portfolio DD ni autenticación de broker.

## Evaluación de las hipótesis y decisión

1. **H1 sin edge:** no descartada; bajo A fijo el PF sigue siendo 0,785. Se requiere prueba independiente OOS temporal, distinta fuente si procede.
2. **H2 SL demasiado corto:** se observa frecuencia de recuperación posterior en hindsight, pero ampliar a 1,5 ATR **no es rentable** ni siempre viable al mismo lote; no se ha demostrado causa dominadora. Una reentrada después del barrido debería estudiarse como NUEVA señal causal, no reinterpretar futuro.
3. **H3 TP inalcanzable:** reducir el TP a 1 ATR sube winrate pero empeora mucho PF. No demostrado que TP menor remedie el problema; 3 ATR mejora vs 1/2 ATR pero aún pierde.
4. **H4 temporalidad:** falta reconstruir señales NUEVAS H1/H4; no confundir remuestreo M5 con señales temporales certificadas.
5. **H5 spread/régimen:** todavía no hay bid/ask histórico autentificado, no es posible atribución de causa a spread. Probar sensibilidades preespecificadas y obtener data con autenticidad.

**Nueva prioridad concreta:** correr ablaciones separadas por módulo de salida (protector, defensa, parcial) sobre la cohorte 540 con mismo fill, una sola intervención por brazo; perfilar NDX100 y 2019/2021 con tamaños razonables; después investigar señales/edge con cortes fuera de muestra. **No ampliar volumen ni riesgo y no crear señales por el simple deseo de elevar el winrate.**

**Estado:** `RESEARCH_DIAGNOSIS_ONLY_NO_CERTIFIED_EDGE`. PR #748 sigue DRAFT, NO LIVE; VPS intacto.

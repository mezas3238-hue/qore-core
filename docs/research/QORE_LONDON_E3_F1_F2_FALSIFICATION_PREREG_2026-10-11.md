# QORE Londres — E3 falsación F1/F2 PRERREGISTRO

**Congelado antes de cualquier cálculo F1/F2**. Fecha 2026-10-11; solo EURUSD/GBPUSD, sesión Londres. Código/ficheros en la rama `research/london-e3-f1-f2-falsification-20261011`, sin tocar fuente de #782 ni producción. Esta investigación sigue siendo **exploratoria, sin cohorte OOS**; ningún test retrospectivo puede certificar una nueva señal.

## Fuente inmutable y censo

Consumir los artefactos originales E3 [run #38153593288](https://github.com/mezas3238-hue/qore-core/actions/runs/38153593288), SHA productor `45516e1ea7ba54f1a13f9e81a877abe906c6c480`: `issue775-LONDON-E3-EURUSD-<sha>` y `issue775-LONDON-E3-GBPUSD-<sha>`; cada artefacto contiene `qore-london-E3-<symbol>-joined-states.jsonl`. Conciliar exactamente **261 NY dates** por par, **227 EURUSD +231 GBPUSD** checkpoints válidos, desenlaces `terminal_60` originales a umbral ±0,25 AsiaRange y checkpoint fijo 11 velas M1; **E3 RECLAIM EUR 94 (38 REV), GBP 92 (22 REV); E3 ACCEPTED_ATR_0P5 EUR 88 (35 REV), GBP 98 (42 REV)**. No recalcular ni modificar estas 458 etiquetas. Rechazar duplicados, símbolos inesperados, falta de testigos E2-H4.

**Estimando** `I = [P(REV|RECLAIM,EUR)-P(REV|ACCEPTED_ATR_0P5,EUR)] - [P(REV|RECLAIM,GBP)-P(REV|ACCEPTED_ATR_0P5,GBP)]`. Todos los neutral/continuation cuentan como NO REVERSAL, no se esconden. Fuera de la comparación quedan estados OUTSIDE_WEAK y OPPOSITE, pero se conservan en censo y remuestreo. Base E3 full `I ≈+0.195969`, IC95 [+0.0321,+0.3567] como testigo; semilla E3 77520261013.

## F1 — E3 solo en jornadas con H4 E2 reconstruible

`H4_E2_KNOWN` = en cada fila estado `H4_ALIGNED_WITH_RAID` o `H4_OPPOSED_TO_RAID` de evidencia causal E2 ya congelada. Todas las demás `H4_E2_UNKNOWN`; **UNKNOWN ≠ velas de Londres rotas**, no atribuir causa de missingness. No recalcular H4, no permitir H4 posterior al raid, ningún nuevo filtro por retorno.

Presentar por separado I_FULL, I_KNOWN e I_UNKNOWN con 4 conteos por celda y por grupo, N elegibles y N total, deltas frente FULL; IC95 percentile bootstrap circular de **2.000 remuestreos de bloques de cinco fechas NY COMPARTIDAS** para ambas divisas, semilla `77520261014`. Remuestrear **las 261 fechas completas como unidad compartida**, conservando UNKNOWN/neutral/días sin setup; calcular la interacción sobre subgrupos después de seleccionar días, no remuestrear trades independientes. Celdas vacías en replicación => ignorar con contador; con menos de 95% válidas => INCONCLUSIVE. No interpretación de p-value confirmatorio.

**Regla F1 de no promoción predefinida**: si el IC95 de I_KNOWN incluye 0, **F1_FAIL_PROMOTION** (robustez no demostrada en cohorte con H4 disponible); si I_KNOWN <=0 o |I_KNOWN| <0,50*|I_FULL|, **F1_COLLAPSE**; aun si no sucede, solo `F1_SURVIVES_HISTORICAL`, sin certificación ni prueba de independencia. **Un CI que incluya 0 NO prueba efecto cero ni prueba que UNKNOWN sea corrupto.**

## F2 — sensibilidad a retirar cada bloque cronológico de cinco fechas, **sin elegir después la ventana**

Ordenar las 261 fechas NY civiles únicas del ledger, formar bloques consecutivos NO superpuestos de cinco fechas (52 completos + 1 residual de una fecha = **53 bloques**, publicar la composición). Ningún diseño basado en rentabilidad. Para **CADA bloque** quitar sus fechas en EUR y GBP SIMULTÁNEAMENTE y recalcular:
- `I_FULL_LOBO`, `I_KNOWN_LOBO`;
- IC95 bootstrap circular sobre las fechas restantes con **1.000 replicaciones por escenario/bloque**, seed determinista `77520261014 + block_index*101 + scenario_offset`, fechas compartidas, longitud block=5. Mismo I y estados E3 congelados.
- publicar los **53** bloques, por símbolo/estado sus N y reversals después de quitar, efecto, cambio Δ vs baseline de MISMA cohorte, intervalos, válido/total.
- **Regla de fragilidad fuerte**: si un solo bloque produce inversión de signo I_LOBO<=0 **o** magnitud <50% de referencia y CI incluye 0, marcar `F2_SINGLE_BLOCK_COLLAPSE`. Si 1-2 bloques específicos hacen colapsar, marcar `F2_CONCENTRATION_RISK`; para comprobar dos bloques, seleccionar ex ante por algoritmo las **dos eliminaciones individuales que más reducen el efecto de I** (minimum effect, desempate índice menor), quitar juntos y recalcular con 2.000 replicaciones. No afirmar que elegir el par más adverso equivale a preregistro de hipótesis independiente; es *stress forense*.
- **Regla estricta de promoción**: para llamar `F2_SURVIVES_STRICT`, TODOS los 53 efectos I_FULL_LOBO e I_KNOWN_LOBO deben conservar signo positivo **y** sus IC95 deben excluir 0. Si falla siquiera un CI, marcar `F2_FAIL_STRICT_PROMOTION` y no construir clasificador. Este criterio conservador puede penalizar estudios de potencia limitada, pero sirve como gate de no-promoción, no como refutación científica del fenómeno.
- publicar mínimo/max I, recuento CI cruzan cero por escenario, bloques de mayor impacto y stress de par más adverso, sin esconder n pequeño. Informe de potencia no inferible con estos datos; fuente reutilizada.

## Decisión ex ante

F1 o F2 no superados => **CERRAR LA PROMOCIÓN RECLAIM/ACCEPTED hacia un trader** y etiquetar `EXPLORATORY_UNROBUST`; **NO** decir que el concepto SMT fue refutado, porque SMT extremo no depende de RECLAIM por definición. No abrir SMT en esta ronda. Si ambos superados => `HISTORICAL_ROBUST_ONLY`, todavía exige replicación real OOS y validación de ejecución antes de señales, no PF optimizado. Ninguna cuarta normalización ni umbral post hoc, ningún broker/VPS/MT5/live, no tocar V49/DCVC/Master Frame.

# QORE — Issue #775 / Londres: EURUSD y GBPUSD, barrido de Asia L1/L2
## AUDIT01 — EJECUTADO, NEGATIVO EN ESCENARIO STOP_FIRST, NO CERTIFICADO

**Fecha:** 2026-10-11. **Experimento aislado:** [PR #776](https://github.com/mezas3238-hue/qore-core/pull/776), rama `research/scalper-london-asia-sweep-first-online-m1-20261011`. [Run final #38146670174](https://github.com/mezas3238-hue/qore-core/actions/runs/38146670174): **4/4 SUCCESS** (9 pruebas de contrato + EURUSD + GBPUSD + consolidación). SHA del código ensayado: `8f358f80bcc18ff9bafea75a95d111404de57537`. [Artefacto agregado #11704768546](https://github.com/mezas3238-hue/qore-core/actions/runs/38146670174/artifacts/11704768546), [EURUSD #11705087498](https://github.com/mezas3238-hue/qore-core/actions/runs/38146670174/artifacts/11705087498), [GBPUSD #11704678014](https://github.com/mezas3238-hue/qore-core/actions/runs/38146670174/artifacts/11704678014).

### Frontera de honestidad

Prerregistro congelado ANTES de análisis, SHA `8c5122a1e4c82c3fbdab2a09a6d25d0fe81fcde4` (primer branch aislado; copiado sin cambios desde ese commit a rama de Trader Lab M1-ready), [texto original aquí](https://github.com/mezas3238-hue/qore-core/blob/research/scalper-london-asia-sweep-first-online-m1-20261011/docs/research/QORE_ISSUE775_LONDON_EURUSD_GBPUSD_SWEEP_FIRST_ONLINE_PREREG_2026-10-11.md). Fuentes: native M1 inmutable GH #35548099334, SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`, ventana 2025-09-17–2026-09-17, **histórico ya consultado**, no OOS confirmado. Ninguna consulta a salidas de V49/DCVC, ninguna modificación de MT5/VPS/producción, costes 0.025R o 0.05R **HIPOTÉTICOS**, no BID/ASK físico.

Ámbito: SOLO Londres, EURUSD y GBPUSD; UTC corregida por DST Europe/London. Asia range **00:00–07:59 UK** con 480 M1/480 obligatorias, primer breach del Asia high/low entre **08:00 y 11:00** UK. Dos modelos rivales mutuamente excluyentes: L1 sweep+reclaim para REVERSIÓN, L2 break+2 cierres fuera para CONTINUACIÓN. Entrada siguiente M1 open, STOP y TARGET ±1R, sin trailing/BE, límite de tiempo 16:00 UK, STOP_FIRST en doble contacto M1. 4 pruebas prespecificadas (2 pares × 2 modelos), 2.000 muestras de signo aleatorio por jornada, ajuste BH FDR Londres q=.10. No adjudicar manipulación institucional por el mero toque de high/low.

### 1. Frecuencia de primera ruptura: hipótesis del usuario parcialmente constatada

| Mercado | Jornadas M1 presentes | Asia completo | Sin primera ruptura 08–11 | Con primer contacto Asia high/low | Señales válidas |
|---|---:|---:|---:|---:|---:|
| EURUSD | 261 | 206 | 36 | **169/206 (82,0%)** | 162 |
| GBPUSD | 261 | 222 | 25 | **197/222 (88,7%)** | 196 |
| Total | 522 | 428 | 61 | **366/428 (85,5%)** | **358** |

EURUSD: 55 días Asia incompleta, 1 hueco Londres antes del primer posible barrido, 7 intentos con riesgo geométrico inválido; señal válida 162 = 101 L1 + 61 L2. GBPUSD: 39 Asia incompleta, 1 riesgo inválido; señal válida 196 = 106 L1 + 90 L2. Los 8 intentos INVALID_RISK NO son operaciones ejecutadas ni censuradas: identificados en primer aggregate y corregidos sin cambiar selección válida, entradas, outcomes ni preregistro. **Los 366 son primeros contactos observados, NO 366 barridos institucionales demostrados.** No se midió cuán “considerable” fue la expansión del rango: no reclamarla.

### 2. Economía del modelo (original vs signo placebo)

| Pareja + trigger | Trades ejecutables y resueltas | PF bruto | PF coste supuesto 0.025R | E por trade 0.025R | WR bruto | IC95 E 0.025R por jornada | BH q |
|---|---:|---:|---:|---:|---:|---|---:|
| EURUSD L1 SWEEP_RECLAIM | 101 | 0,836 | **0,796** | **−0,1141R** | 45,54% | [−0,3121R,+0,1037R] | 0,9345 |
| EURUSD L2 BREAK_HOLD | 61 | 0,694 | **0,661** | **−0,2053R** | 40,98% | [−0,4357R,+0,0250R] | 0,9845 |
| GBPUSD L1 SWEEP_RECLAIM | 106 | 0,963 | **0,916** | **−0,0439R** | 49,06% | [−0,2325R,+0,1448R] | 0,9345 |
| GBPUSD L2 BREAK_HOLD | 90 | 0,552 | **0,525** | **−0,3139R** | 35,56% | [−0,5139R,−0,0917R] | 0,9845 |

**Todas 358/358 señales clasificadas SIGNAL_CONFIRMED resultaron resueltas** en el replay final; **0 censuradas entre señales ejecutadas**. El corte de datos incompletos en Asia se declara aparte, no se cuenta como trade perdido. BH q=.10: **0/4 supervivientes**. Random-sign P nominal positivo unilateral: 0,4673 / 0,7486 / 0,3108 / 0,9845, respectivamente. No confundir estos p de placebo de dirección, que comparten las mismas entradas y barreras, con una validación de TIMING independiente. La estructura no tiene BID/ASK broker físico ni latencia. Stop-width mediano aproximado: EURUSD L1 1,1 pip, EURUSD L2 1,5 pip, GBPUSD L1 1,5 pip, GBPUSD L2 2,0 pips: el coste uniforme 0,025R NO es una medición de spread/slippage proporcional a stops tan cortos.

### 3. Hallazgo limitante P0: alta ambigüedad de stop/target dentro de M1

| Celda | Dual-touch STOP_FIRST | % | E neta con coste supuesto STOP_FIRST | Cota SUPERIOR ficticia si todas fueran TARGET_FIRST |
|---|---:|---:|---:|---:|
| EURUSD L1 | 11/101 | 10,9% | −0,1141R | **+0,1037R** |
| EURUSD L2 | 7/61 | 11,5% | −0,2053R | **+0,0242R** |
| GBPUSD L1 | 8/106 | 7,5% | −0,0439R | **+0,1071R** |
| GBPUSD L2 | 8/90 | 8,9% | −0,3139R | −0,1361R |

34/358 = **9,5%** de operaciones con ambas barreras dentro de la MISMA vela M1. La cota superior se deriva post hoc de `E_STOP_FIRST + 2 * dual_touch/N` bajo el escenario idealizado de +1 vs −1 para todas las ambigüedades; **NO constituye una simulación de ejecución, estrategia alternativa, ni autorización para usar TARGET_FIRST**. Con M1 OHLC no puede adjudicarse qué orden cronológico tocaron stop y target. Tres de las cuatro celdas cambian el **signo** de su esperanza en la cota ficticia, por lo que el resultado negativo conservador está correctamente documentado, pero la verdadera economía intrabar requiere datos tick/BIDASK si se quisiera certificar una estrategia de stops tan estrechos.

### 4. Interpretación y dictamen

- El usuario tenía una hipótesis comprobable sobre la **frecuencia de tocar Asia high/low** durante Londres: observamos primer contacto en **82% EURUSD y 89% GBPUSD** entre jornadas con Asia completo; no se probó frecuencia literal de `manipulación` ni magnitud de desplazamiento posterior.
- **Ninguna de las cuatro reglas originales específicas presenta esperanza positiva bajo STOP_FIRST y coste hipotético 0,025R.** GBPUSD L1 se aproxima a cero bruto pero no demuestra ventaja. Las bandas de incertidumbre para tres celdas incluyen cero y el cuarto resultado es negativo incluso en su IC descriptivo.
- **NO** concluir que `los barridos de Londres nunca funcionan`, que no hay edge en otros triggers/CISD/familias de sesión, ni que el mercado no se expande. Se probó solo una definición causal minimalista L1/L2, no la metodología del autor TTrades, ni una ejecución tick.
- **Decisión:** `STOP_FOR_PROMOTION / NEGATIVE_OBSERVED_ON_FIXED_RULES / UNDERPOWERED_OR_INTRABAR_UNRESOLVED_FOR_GENERAL_EDGE`. No tunear umbrales, no convertir el control espejo en trader, no expandir universo sobre el mismo periodo para rescatar resultados. Si se investiga otra hipótesis más específica de barrido de Asia, exigir nuevo prerregistro y cohorte fuera de muestra + feed bid/ask/ticks o una política auditable para resolver los 34 conflictos antes de afirmar viabilidad física.

**Seguimiento:** el programa completo de nueve celdas por tres sesiones continúa independiente en [Issue #775](https://github.com/mezas3238-hue/qore-core/issues/775). Esta prueba cubre SOLO las 2 celdas de Londres (cuatro tests de dos triggers). Sin certificar trader ni desplegar nada.

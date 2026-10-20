# VT08 — VEREDICTO DE VIABILIDAD ECONÓMICA INICIAL: NO-GO PROTOTIPO QORE M30→M3

**Fecha 2026-10-11**, arquitecto metodológico A; PR #765 / issue A #762, B #763, parent #634. Propósito del Owner: terminar con recuento de geometrías y determinar si la metodología genera beneficios. **No hemos probado aún el TTrades ORIGINAL con fidelidad; sí hemos sometido un PROTOTIPO QORE congelado a un test económico outcome-blind.**

## 1. Dictamen en una oración

**NO-GO** para el prototipo M30→M3 QORE con stop exclusivamente Protected Swing (C), target opposite C1 (C), y entrada positional vs CISD-level limit (C): ambos pierden dinero en el agregado **incluso SIN costes**, y empeoran al aplicar costes hipotéticos. **No se sigue** que el método original de TTrades sea perdedor: no están integrados POI significativo autor, swing de EQ validado, breaker correcto y stop específico fuente ni BID/ASK físico. **Demostrar TTrades rentable sigue PENDIENTE**.

## 2. Pre-registro + fuente real

[PRE-REG](VT08_A_M30M3_ECONOMIC_FALSIFICATION_ONE_PER_DAY_PREREG_2026-10-11.md) commit `4d0bc77abf0863b860d6b549632e2f372e05d02d`, antes de medir PnL. Se evita seleccionar `first CLEAN retest after closure` porque requeriría saber futuro: la muestra se fija usando **primera madre M30/M3 confirmada al abrir C3 de cada NY day por cada mercado**, para **ambas técnicas contrafactuales** sobre idéntico universo. Un mother por par/día, sin buscar el de mayor RR/PnL.

M3 nativo cTrader DEMO histórico fuente #35941643396 y M15 independiente #35934924907, cinco FX EURJPY/USDCHF/NZDUSD/CADJPY/USDCAD, universo 1095d. Sólo Owner 01–13 NY H4 interval hours, M30 intracycle; **no 7Y sealed ni VPS**.

Reglas simulación proposicional (NO broker):
- Modalidad A **POSITIONAL**: C3 M30 first-M3.open, SL en PS QORE, target en extremo C1 opuesto; seguimiento sólo 10 M3 closed, stop/target o salida close C3; STOP-FIRST si ambos tocados en la misma M3.
- Modalidad B **CISD LIMIT**: al abrir C3 predeclara limit en precio CISD previo, sólo si mejora relación distancia a stop, expiry al cierre C3. Sin touch: NO FILL/0R, target/stop previo sin touch: NO FILL; si limit/SL/TP coincide en primera M3 touched, worst case **-1R** y se marca ambigüedad (no afirmar fill real); tras touch stop/target o expiración.
- Fricciones experimentales C 0, 0.05, 0.10, 0.20R POR fill contrafactual; no son spreads/comisiones medidos.
- Economic expectancy POR first mother incluye NO FILL 0R para evitar el sesgo condicional 'touched only'. No optimización por performance, no thresholds elegidos ex-post. Las familias se simulan paralelamente en investigación pero jamás abrir 2 trades reales de la misma madre.

**Código:** `src/qore/infrastructure/trader_lab/vt08_5m_m30m3_economic_proxy_falsification_v1.py`, 10 tests `tests/infrastructure/trader_lab/test_vt08_5m_m30m3_economic_proxy_falsification_v1.py`, CI `.github/workflows/vt08-a-m30m3-economic-proxy-falsification-1095d-v1.yml`.

**GitHub CI [run #38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903)**: **SUCCESS 6 jobs** (5 markets + combinado cronológico), tested SHA `7b6fd2213576222a602ded6f22e5fb6efb14658c`, Ruff green, 10 tests adversariales por mercado = 50 PASS, 5 economic source backtests + combined sum temporal.

## 3. Resultados principales en 3.561 señales madres (1 per NY market-day)

| Métrica agregada 5 pares | Positional COST=0 | Positional COST=0.10R | Limit CISD COST=0 | Limit CISD COST=0.10R |
|---|---:|---:|---:|---:|
| Mother setups fijados antes del C3 | 3561 | 3561 | 3561 | 3561 |
| Hypothetical fills | 3561 | 3561 | 1818 | 1818 |
| No fills | 0 | 0 | 1743 | 1743 |
| **PF** | **0.9642** | **0.7808** | **0.8950** | **0.7729** |
| **Expectancy R por señal madre** | **-0.01715** | **-0.11715** | **-0.03676** | **-0.08782** |
| Net R sum | -61.06R | -417.16R | -130.91R | -312.71R |
| Max drawdown secuencial en R suma agnóstica a capital | 102.62R | 425.29R | 134.21R | 315.31R |
| Win rate entre fills netos | 45.35% | 42.94% | 28.60% | 27.78% |

**Atención:** DD se mide en R de una secuencia conjunta entre pares, no es % de cuenta ni CIBO capital/portfolio. El 'costo 0.10R' es un test de sensibilidad, NO comisión histórica. Los fills y SL/TP son **reconstrucción OHLC**, ambigüedad intrabar marcada conservadoramente; sin BID/ASK/tick no se afirma ejecución física.

### Mercado individual: PF bajo 0.10R escenario costo hipotético

| Mercado | Primeras madres por NY day | Positional PF 0R | Positional PF 0.10R | Limit PF 0R | Limit PF 0.10R |
|---|---:|---:|---:|---:|---:|
| EURJPY | 722 | 0.828 | 0.669 | 0.802 | 0.693 |
| USDCHF | 692 | 1.034 | 0.839 | 0.952 | 0.827 |
| NZDUSD | 723 | 1.096 | 0.887 | 1.078 | 0.931 |
| CADJPY | 712 | 0.868 | 0.694 | 0.751 | 0.644 |
| USDCAD | 712 | 1.013 | 0.829 | 0.908 | 0.785 |
| **TOTAL** | **3561** | **0.964** | **0.781** | **0.895** | **0.773** |

No PF de una modalidad alcanzó preregistro GO de PF net 1.2 y net positive expectancy incluso en mercado individual, antes de costes apenas NZDUSD 1.096 pos, el resto alrededor o debajo de 1.0. Un escenario 0.05R también fue negativo agregado (pos PF 0.8674, limit PF 0.8309), 0.20R peor (pos PF 0.6339, limit PF 0.6723).

## 4. Veredicto explícito y presupuesto de investigación

1. **RECHAZAR PROTOTIPO QORE PS-only C1-target como estrategia RENTABLE:** incluso coste cero en agregado PF <1 y net expectancy negativa; dado que spread/comisiones físicas nunca mejoran resultados, el prototipo tal como se ha simulado carece de evidencia de edge.
2. **NO afirmar que TTrades original funciona ni que no funciona:** el prototipo carece de POI HTF/significancia, swing reference EQ/ breaker auténtico, stop original y selección contextual/daily. No asignar 3561 trades a metodología de autor, son simulaciones de **shapes**.
3. **DEJAR DE LLAMAR "DENSIDAD RECUPERADA" a 8982/3542/8979**. El número que importa es **source-author-executable trades con PnL y costos**, aún 0. M30→M3 ofrece cobertura geométrica, **no edge demostrado**.
4. **STOP nuevas ramas/umbral wick/8 M15/ POI proxy optimizados** que solo construyen más shapes. Única ruta con criterio de parada: definir y verificar **UN modelo completo original fuente A** (p.ej. M30→M3 bullish reversal) usando ejemplos/lecturas primarias, un POI significativo, swing EQ previo, breaker/PS y timestamps de entrada y salida. Si la fuente no permite formalización causal, declarar ese modelo NO VERIFICABLE y no invertir más en densidad exploratoria.
5. Repetir el test con **configuración autora congelada y BID/ASK de mercado real**, comisiones, y periodo temporal de desarrollo + validación independiente, sin reoptimizar según 3561 outputs. Si no se dispone de evidence POI/bidask/modelo completo, declarar **NO-GO OPERATIVO / metodología no demostrada**.
6. El Owner quiere una decisión, no más informes de geometría: prohibido presentar PF de QORE como performance del autor, o escalar más cifras antes de cerrar viabilidad. Cognitiva y VPS no se activan en modelo negativo/no certificado. 7Y holdout SELLADO.

## 5. Evidencia reproducible y hashes

- Combined artifact `11710147076` SHA256 `bc2fdfdc3537d61ad5e3704bd68833552e4ed56cf91c117ed3f07011babf123c` (5 mercados cronológicos)
- EURJPY `11710236942` sha256 `d6989696ba595758486b68e9b8a8cd2c83b1b9c555e9b1cf4faee3df4d5859a9`
- USDCHF `11710481451` sha256 `a6f98af81e8503f31852acefb4c160122c315bda4b6d20d2aaeb7cba9b723221`
- NZDUSD `11710661311` sha256 `8ecfb925ac3c0e2faff2fa34b4fa19dbd691cec8270555a6ac4aee208633f470`
- CADJPY `11710201078` sha256 `22749bdb0f2eb562dd8862a2f8ba2213a94c664155a61fd56c55b60328c097b6`
- USDCAD `11710231009` sha256 `1ed720123d29800b8c88f7f4fa418ed43ab85cd6ba914aa5a8ceb5790b4bac8d`.

**Output labels:** all records `author_TTrades_methodology_full=False`, `source_PoI_and_EQ_breaker_validated=False`, `broker_execution_physical=False`, `cognition_full_used=False`. Clear no-go only for tested proxy.

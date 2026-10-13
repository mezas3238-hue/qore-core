# QORE-Alpha 2 — G1A 33 mercados, dictamen económico ejecutado y auditoría de falsación

**2026-10-12. Fuente ejecutada GitHub:** [G1A Run #38270999595](https://github.com/mezas3238-hue/qore-core/actions/runs/38270999595), exact-head `b406be34e16e61b7b4c042f31f95cf38a45f4e07`, 35/35 jobs GREEN: preflight, 12 Atlas originales, 21 IC Markets DEMO y agregación. [Artefacto original #11757391132](https://github.com/mezas3238-hue/qore-core/actions/runs/38270999595/artifacts/11757391132), archivo `alpha2-g1a-paired-33-first-gross-panel.json`. PR [#840](https://github.com/mezas3238-hue/qore-core/pull/840), issue [#838](https://github.com/mezas3238-hue/qore-core/issues/838). No mezclar esta ejecución con otras versiones.

## 1. Integridad científica y coste real

- PREOUTCOME metodología PATR v0.1 commit `a369914550ed0b1da23b40b35b91fb23dde61346`; G1A reglas de stop/target/censura, entrada M5 y control pareado congeladas PRE-GROSS commit `6ee8848f03719e8a0d6626f038d6ad8ec5fc33c7`. Los intentos anteriores de CI fueron rechazados **antes** de precios por lint y no generaron PnL.
- Universo fuente íntegro `33/33`, SHA del original G0 `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`; 33 workers con auditoría SHA de once años por símbolo. 224 señales congeladas SHA `604702839117423c08057e9348a97b0899c2db92f1e1d6daf92d9480e6217f22`, [run fuente #38268654596](https://github.com/mezas3238-hue/qore-core/actions/runs/38268654596).
- GROSS OHLC M5 original: **NO** son órdenes, BID/ASK, spread negociable, comisión, swap, PnL NET ni drawdown de una cartera. Macro noticias no filtradas con calendario PIT; prohibido trasladar estas señales a otros traders/VPS/MT5/LIVE. Año 2024-09-17 en adelante quedó fuera del acceso a OHLC y no adquiere automáticamente estatus fresh si otros proyectos lo inspeccionaron.
- Runner: Trader Lab SHA-verified extraction de H4 en 33 jobs paralelos y replay incremental O(T*N²). `fast_forward.py` existente es un *certificador de aceleración de cronología*, no un ejecutor económico; la aceleración implementada para Alpha2 no suplanta ni altera el componente compartido.

## 2. Economía observada — resultado exacto de log de agregado

| Cohorte | Señales | Pareadas observables | No pareadas/censuradas | Retorno PATR promedio GROSS (bps) | Diferencia PATR-control GROSS (bps) | Sample Gate |
|---|---:|---:|---:|---:|---:|---|
| DEVELOPMENT (2016-09-17 a 2022-09-17) | 163 | 130 | 33 | −0,1674348441 | −0,7287646443 | **FAIL** (requiere ≥150 trades/52 semanas) |
| DIAGNOSTIC (2022-09-17 a 2024-09-17) | 61 | 46 | 15 | −3,4236609365 | 0,0000000000 | **FAIL** (requiere ≥50 trades/26 semanas) |
| **Total** | **224** | **176** | **48** | **NO USAR PROMEDIO GLOBAL PARA GATES** | **NO DISCRIMINATIVO** | FAIL |

**Veredicto automático:** `UNDERPOWERED`. Junto con retorno bruto negativo en ambas eras, la versión **NO APORTA EVIDENCIA POSITIVA** para PATR v0.1. Esto NO falsifica toda estrategia intermercado ni certifica `NO_EDGE` universal; los criterios predefinidos no pasan, y tampoco existe economía neta broker. No hay razones para enviar órdenes.

## 3. Hallazgo lógico previo a outcomes: comparador prácticamente tautológico

La propia definición de señal PATR selecciona casos `0 <= sign(P)*r_i(t) <= 0.25*|P|`. Para `r_i(t) ≠ 0` implica `sign(r_i(t)) = sign(P)`. El control firmado como `sign(r_i(t))` opera entonces la **misma dirección**, con el mismo stop, target y fill de referencia. El contraste PATR contra control **no puede medir el efecto incremental de transmisiones entre mercados** en esos eventos. En los casos de retorno cero, el control utiliza `sign(r_i(t-1))` y puede diferir, pero ese subcaso no resuelve la tautología global. Se registró esta limitación en PR #840 mientras corrían los jobs, ANTES de leer el resultado G1A.

**Implicación:** el delta observado, incluido el 0,000 del diagnóstico, no proporciona una prueba independiente de mecanismo. No intentar usar su p-value o bootstrap como certificación positiva o rechazo concluyente de PATR. El retorno bruto absoluto sí es observable en su alcance de precio proxy y negativo en ambas eras.

## 4. Bloqueos y orden de investigación

1. **Cerrar W1**: status `SOURCE_SUCCESS / SIGNALS_REPRODUCED / FIRST_GROSS_UNDERPOWERED_AND_NEGATIVE / COMPARATOR_NONDISCRIMINATIVE / NET_BLOCKED / 0_CERTIFIED`. Congelar código, SHA, artefactos y criterios. No retune de 0.55 correlación/7 donantes/0.90 sigma/0.25 retardo/stop1.25/target2R/12h basado en este dataset consumido.
2. **Anatomía de censura sin filtrar PnL**: lectura posthoc del artefacto G1A para contar brechas M5 vs desaparición de trades, YEAR×MARKET×FAMILY, stop/target, dobles toques y simultaneidad; nunca retirar celdas malas.
3. **Replanteo W2 con mecanismo causal realmente distinto**: no copiar las siete familias Native y no conservar PATR con un filtro oportunista. Antes de leer más outcomes especificar datos necesarios, coste y fuente alternativa, control independiente y potencia. Si W2 usa el mismo histórico 2016-2024, es desarrollo CONSUMIDO, no OOS.
4. **Infraestructura NET**: obtener, sin credenciales en archivos, BID/ASK histórico o forward del MISMO instrumento/cuenta, broker session/PIT macro, swap/slippage, ejecución adversa stop, costes en 33; `UNKNOWN` bloquea la certificación, no sustituir por 0 ni por un coste supuesto.
5. **UTC-001**: años/folds/fresh OOS deben pasar todos PF≥1.50, E≥0.15R, Sharpe≥1.50, Sortino≥2, payoff≥1.50, observed DD≤6R, MC positive≥90%, MC p95DD≤15R, netPF>1 y net E>0; también integridad causal, pérdidas en cluster, retención winners, MAE/MFE, risk review y CIBO review; ningún promedio compensa años fallidos.
6. **Conservar originalidad científica**: código reutilizable de Trader Lab sí, metodología ajena no. No afirmar originalidad absoluta de matemáticas generales; original es el programa de hipótesis falsables y la implementación propia.

**Prohibido** integrar PATR con Shared/CIBO, paper o Live. Toda investigación y nuevos runs GitHub DRAFT; cero cambios VPS y producción.

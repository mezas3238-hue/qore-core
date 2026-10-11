# QORE NATIVE — tesis fundacional de la fuente económica de edge
## Respuesta escrita a «¿Por qué nos pagaría el mercado?» — investigación, no certificación

**Fecha:** 2026-10-11. **Programa:** [#789](https://github.com/mezas3238-hue/qore-core/issues/789). **Rama:** `research/qore-native-economic-edge-source-thesis-20261011`. **Padres:** [handoff PR #795](https://github.com/mezas3238-hue/qore-core/pull/795), [G0B PR #796](https://github.com/mezas3238-hue/qore-core/pull/796). **Modalidad:** DECLARACIÓN DE HIPÓTESIS, *NO* hallazgo estadístico, motor, P&L, señal o aprobación PAPER/LIVE.

## 1. Respuesta obligatoria, escrita antes de diseñar reglas económicas

**Fuente de ventaja seleccionada (categoría principal): #2, persistencia de conductas económicas repetidas.**

> QORE pretende estudiar si **demandas relativamente inelásticas de ejecución y cobertura, que ocurren en calendarios o ventanas predecibles**, producen **presión de precio temporal** que, una vez agotada, revierte, y si el movimiento remanente es capturable *después* de que toda información utilizada por la señal sea conocida y de pagar fricciones reales de ejecución. La primera hipótesis económica será la reversión posterior a presión alrededor del **benchmark FX de las 16:00 Europe/London**, no «el precio hizo un barrido, por tanto hubo cazadores de stops».

**Por qué podría persistir:** una parte de la demanda de negociación viene de obligaciones de valorar carteras, cubrir divisas, atender clientes y cumplir benchmarks/mandatos; el coste de ejecución y el acceso a liquidez son fricciones, no simples patrones gráficos. El calendario se repite y el flujo puede desbalancear la liquidez. Sin embargo, intermediarios pueden anticiparlo, cambiar su conducta y eliminar la oportunidad; **persistencia de actividad no equivale a persistencia de P&L**.

**Quién pagaría y por qué:** la contraparte que exige ejecución/transformación de riesgo dentro de una ventana paga implícitamente coste de impacto/liquidez; el hipotético trader QORE ofrecería capacidad de riesgo a un precio temporalmente distorsionado, pero únicamente si puede esperar a la señal, operar con spread/slippage razonables y deshacer posición antes de que otros arbitrajistas eliminen el diferencial. No afirmamos que QORE tenga acceso privilegiado al flujo ni que domine al intermediario.

**Evidencia externa que MOTIVA (no acredita P&L QORE):**
- FCA, Evans/O'Neill/Rime/Saakvitne, *Fixing the Fix? Assessing the Effectiveness of the 4pm Fix*, FCA Occasional Paper 46, 2018, portal actualizado 2026: https://www.fca.org.uk/publications/occasional-papers/occasional-paper-no-46-fixing-fix-assessing-effectiveness-4pm-fix . Reporta microestructura y aumento de spreads/impacto tras reforma; *riesgo para la capturabilidad*.
- *Did the reform fix the London fix problem?*, examen de dinámica y reversión post-fix tras reforma 2015: https://www.sciencedirect.com/science/article/pii/S0261560617302024 . No generalizar sin réplica nueva.
- Melvin/Prins, *Equity hedging and exchange rates at the London 4 p.m. fix*, 2015: https://www.sciencedirect.com/science/article/pii/S1386418114000779 . Coberturas asociadas a benchmark, especialmente al cierre mensual.
- LSEG WMR, fuente del benchmark y metodología actual: https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks .
- Tóth/Palit/Lillo/Farmer, *Why is equity order flow so persistent?*, JEDC 2015: https://doi.org/10.1016/j.jedc.2014.10.007 . Hallazgo en **acciones**, NO prueba trasladable automáticamente a spot FX/CFD.

**Importante sobre epistemología:** «información/ejecución/persistencia/prima» son una taxonomía útil, **no un teorema exhaustivo**; y un modelo de IA sí puede contribuir a la búsqueda de relaciones predictivas mediante herramientas de análisis, pero sin datos exclusivos, sin rigor OOS y sin costes no puede garantizar alpha. No se da por demostrado que una metodología de terceros sea rentable por su fama.

## 2. Priorización, sin confundir tres etiquetas con tres edges

| Candidato | Fuente causal a investigar | Razón por la que un participante podría pagar | Riesgo de ser mera narrativa | Estado |
|---|---|---|---|---|
| **RESET / PRIORIDAD 1** | Cobertura/rebalanceo y flujo benchmark FX 16:00 Londres | Demanda temporal inelástica que altera el precio y posteriormente deja de impactar | Arbitraje/preposicionamiento y spreads eliminan reversión *operable*; retorno horario normal | `SOURCE_HYPOTHESIS_WRITTEN; NO_EDGE_PROVEN` |
| **DRIVE / PRIORIDAD 2** | Fraccionamiento de metaórdenes y ajuste gradual de portafolios | Demanda en la misma dirección persiste después de intervalo ya observado | OHLC M1 no observa quién compra, macro-news confunde continuación; evidencia de acciones no prueba NAS100 CFD/FX | `SOURCE_HYPOTHESIS_WRITTEN; NO_EDGE_PROVEN` |
| **RELATIVE / PRIORIDAD 3** | Latencia heterogénea para incorporar shocks comunes y límites a arbitraje/cobertura | Residual temporalmente desalineado converge antes de que se arbitre por completo | Correlación USD no implica cointegración, beta cambia, ejecución simultánea doble puede consumir todo diferencial | `MECHANISM_SPECULATIVE; NO_EDGE_PROVEN` |

**No imponer una narrativa única a los tres.** «Persistencia conductual» es solo familia amplia. G5 exigirá comprobar si son de verdad factores distintos. Si RELATIVE carece de agente/mecanismo identificable y no derrota controles estrictos, **STOP**; no promover por ser el tercer miembro de una cartera aspiracional. Estado legítimo 0, 1, 2 o 3 candidatos.

**No copiar ICT/TTrades, V49, stop-sweep ni SMT:** puede existir geometría de precios similar; la fuente económica y reglas deben derivarse de una hipótesis registrable independiente. Precio OHLC jamás acredita órdenes de stop ejecutadas ni «manipulación institucional».

## 3. Primer contraste propuesto: RESET-LONDON-FIX-G1 (DISEÑO, NO PRERREGISTRO ECONÓMICO APROBADO)

**Pregunta:** ¿Desplazamiento confirmado ANTES del fixing londinense predice una **reversión posterior efectivamente ejecutable** mayor que la del mismo horario sin presión, neta de spread+comisión+slippage? El mecanismo de presión es hipotético y no observable directamente por OHLC.

**Principal símbolo propuesto:** EURUSD (G0 y G0B observan cobertura nominal de datos en este símbolo). **Replicaciones:** GBPUSD y USDJPY; nunca elegir el mejor ex post. **Anchor de investigación:** 16:00 Europe/London con zoneinfo/IANA — GMT invierno, BST verano. **Diseño temporal ilustrativo para fijar antes de abrir outcomes:** medir la presión *solo hasta* 15:57 Londres y observar eventual reversión desde el primer instante operable después del fin de la ventana del benchmark, por ejemplo 16:05 hasta 16:30, sin high/low futuro. El fixing WMR puede usar una ventana propia; el minuto 16:05 **no se declara elegible** hasta cotejar la metodología vigente y los contratos broker. Este esquema es **propuesta**, no estrategia autorizada.

**Contrastes nulos:** retorno direccional neutral de mismo activo/hora/volatilidad; dirección aleatoria preregistrada; placebo de otra hora, y control de final de mes vs resto. Incertidumbre por fechas, no tratar trades adyacentes como observaciones independientes. Una señal por fecha para hipótesis primaria, sin elegir el target óptimo tras estudiar retornos. **Endpoint primario por congelar:** diferencial de esperanza neta de costes contra baseline en unidades consistentes; PF, DD y ratios de cartera quedan para G3/G4 con sizing fijo.

**Falsación verificable:** STOP si retorno condicional no mejora controles en margen económico prefijado; si gran parte del efecto ocurre antes de que QORE pueda entrar; si depende de meses extremos/feriados o spread; si no sobrevive +1 vela de latencia, mayor coste y periodo no inspeccionado. Si el estudio carece de potencia, dictaminar `INCONCLUSIVE` y no ajustar features post hoc. No generar más variantes para rescatar un negativo sin nueva hipótesis/prereg y corrección de múltiples ensayos.

**Bloqueos ANTES de un verdadero G1 predictivo:** confirmar instrumento/proveedor, horario efectivo FX y calendario (G0B es un reloj NOMINAL, [reporte](../research/QORE_NATIVE_G0B_NINE_MARKET_CLOCK_CENSUS_EXECUTED_2026-10-11.md)), política prereg de días censurados, cotizaciones bid/ask y comisiones del broker, spreads/slippage durante fixing, y adquirir periodo genuinamente no inspeccionado para confirmación. G0 2025-09 a 2026-09 fue explorado previamente y solo puede respaldar DEV, nunca nuevo holdout. 3 años de OHLC para EURJPY y USDCHF **no están acreditados** en las nueve fuentes G0.

## 4. Adjudicación de la propuesta externa «barrido EURJPY/USDCHF de Londres»

Se conserva como **sugerencia externa no probada**, no como experimento QORE autorizado. Tiene cuatro discordancias verificables:
1. **Fuente:** G0 incluye nueve símbolos, pero **NO EURJPY ni USDCHF**; el periodo comprobado es un año 2025-09→2026-09, no tres años. Buscar años/símbolos nuevos con SHA antes de hacer promesas de replay.
2. **Reloj:** «08:00–09:00 GMT» es hora fija UTC, mientras «08:00–09:00 Londres» cambia al entrar BST. Debe escogerse y congelarse **una** convención causal.
3. **Riesgo/beneficio:** stop 1,5×ATR(14) y cierre al open de sesión **NO constituyen mecánicamente un target 1R**; la recompensa depende de distancia real y costes. Especificar invalidez, orden de fill, target y R ex ante.
4. **Evidencia:** 50 trades y PF >1,30 sin IC, potencia, multicomparaciones, supuestos de coste y OOS no prueban edge; tampoco las velas M15 de reversión prueban existencia de stops. En ausencia de ejecución real de ambas puntas, P&L sigue supuesto.

No mezclar este candidato con la línea de TTrades-Londres ni con RESET-FIX: agentes, hora, comportamiento y fuente causal difieren. Podrá investigarse como **nueva hipótesis** con sus datos y su propio presupuesto, si el programa lo autoriza explícitamente.

## 5. Contrato de disciplina y autoridad de Core

1. **Fuente primero → fenómeno → endpoint → feature causal → solo después motor.** Registrar hipótesis primaria, controles, MDE, calendario, data-as-of, costos, replicaciones y reglas STOP antes de calcular forward returns.
2. **G0/G0B** sólo comprueban disponibilidad de información. Ningún dato de PF, Sharpe, Sortino o DD de los nuevos traders existe aquí. No fabricar ninguna «primera ganancia» por extrapolación de literatura.
3. Cualquier hallazgo exploratorio debe sobrevivir *walk-forward* con embargo, multiplicidad, OOS auténtico, stress 1×/1,5×/2× costes, monotonicidad de timing y PAPER futuro. Si el holdout no existe: `OOS_BLOCKED`.
4. El tamaño de ensayo PAPER (p. ej. 0,1% propuesto externamente) no es autorización. **No operar real**; presupuesto posterior requiere aprobación explícita y Shared/CIBO/QDLE de Core.
5. Las cognitivas propias se diseñan solo al superar motor simple determinista causal. Ninguna IA convierte ruido en ventaja económica mediante «razonar» sobre el mismo PnL observado.
6. DeepSeek puede ser revisor adversarial de mecanismos y diseños, con interrogantes publicados en GitHub, pero **no afirmar consulta efectuada** sin testigo.

## 6. Veredicto actual y próximos entregables

**DECISIÓN:** fuente económica primaria de QORE NATIVE = **flujos obligados, programados o fraccionados por participantes con limitaciones de ejecución**, categoría persistencia de comportamiento. Primer mecanismo específico: **posible reversión neta tras presión en el fixing FX Londres (RESET)**. DRIVE y RELATIVE son hipótesis separadas en espera, no «demostraciones» derivadas del éxito de RESET.

**ESTADO:** `SOURCE_DEFINED_HYPOTHESIS_ONLY`. `G0B_OBSERVABILITY_PASS_BROKER_UNVERIFIED`. `G1_NO_PREDICTIVE_TEST`. `0/3_CERTIFIED`. `NO_VPS_NO_MT5_NO_LIVE`.

**Orden de trabajo concreto:** (a) certificar proveedor, horario/holiday y costes del FX fixing; (b) corregir anomalías G0B con razones testificadas, sin borrar fechas ex post; (c) congelar prerregistro individual RESET G1, potencia y endpoint, luego ejecutar sólo discovery DEV; (d) en paralelo escribir mecanismos independientes falsificables DRIVE/RELATIVE sin outcomes; (e) preservar un OOS verdaderamente no inspeccionado antes de proclamar rentabilidad.

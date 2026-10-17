# VT08 FINAL #1 — ADJUDICACIÓN AUDITOR, CONTRATO 3 VEREDICTOS Y ESTADO PRE-TRIAL

**2026-10-11 · PR #765 · Issue decisorio #787 · A #762 · Verificador B #763.**
Esta es una **actualización del contrato de validación de reglas**, NO una nueva optimización ni un segundo ensayo económico. El umbral GO >1.15, >=100 fills físicos, cinco mercados y una sola familia no cambiaron.

## A verificado (exactamente qué dice fuente)

1. [Relevant Swings, 21-mar-2026](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/), secciones *Understanding Valid Separation* y *Fractal Lookback Window*: relevant swings merecen separación visual y el autor afirma explícitamente que **NO existe fórmula numérica estricta de separación**. **A escrita para negación del threshold**. Detector universal de relevancia con umbral ATR/pips es **C-QORE**, no fiel A. Fuente sugiere mirar tres velas HTF incluyendo la actual, pero los extremos de una vela NO cerrada no se pueden conocer en retrospectiva; sólo snapshots as-of de ese instante y nunca su high final.
2. [Timeframe Alignment, 30-jul-2025](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/), sección *Example 1 – 30M to 3M Intraday Reversal*: M30→M3 bullish C2 closure tras low sweep, CISD M3 y posicional al abrir siguiente candle, stop debajo EQ 30M **Y** breaker low. **A regla**. No es A la selección concreta de swing EQ y breaker low sin identidad autor.
3. [Positional Entries, 08-ago-2026](https://ttrades.com/positional-entries-enter-before-the-expansion/): exige C2/C3 HTF closure + CISD LTF + protected swing válido PRE-entrada; nearest PS no siempre correcto; elegir el alineado con delivery, criterio aún cualitativo D.
4. [Breaker Blocks Simplified, 05-jul-2025](https://ttrades.com/breaker-blocks-simplified/): bullish low→high→lower low→higher high, zona con series (o vela) up-close; stop beyond zone **o** swing de confirmación como técnicas descritas. **Estas dos alternativas del artículo general NO autorizan** elegir qué low específico equivale al breaker del ejemplo M30M3 sin proveer serie y timestamp.
5. [How to Set Price Targets, 23-may-2026](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/): target long previos highs HTF o swing highs **untouched**; si ya barridos, ya no target válido. **No impone criterio total de prioridad** si hay varios high HTF untouched, selector sigue D.

### Corrección lógica de la supuesta "jerarquía" del stop

Para el ejemplo LONG, "stop BELOW EQ AND BELOW breaker low" es la desigualdad exacta `stop < min(eq_m30, breaker_low)`. Si se conoce broker tick y hay confianza en ambos niveles, para SL BUY sell-side se exige `stop <= min(EQ,breaker_low)-tick`. **No existe ambigüedad matemática sobre cuál cota domina** (el nivel MENOR), sí existe D sobre qué EQ y qué breaker son los auténticos, y el tick/side/buffer de broker es **formalización de ejecución QORE C**.

## Tres finales, sin doble interpretación

- **GO** (resultado de test económico autor-fiel): dataset independiente, causalidad POI/CISD/PS/stop/target ya firmada A+B, broker bid/ask y comisiones verificadas, 5 markets fixed, >=100 fills, PF net estrictamente >1.15, net expectancy positive. **No implica permiso LIVE** ni rentabilidad garantizada, informa únicamente la familia única ensayada.
- **NO_GO**: mismos requisitos verificados, >=100 fills, PF net <=1.15 o expectancy net <=0. **Resultado válido sobre la familia concreta** y cierra VT08 OPERATIVO sin iterar; no demuestra que toda rama del autor pierda.
- **NO_EVALUABLE**: prerequisito crítico D, falta de historial de ejecución física, independencia/validación o <100 fills. **Resultado de limitación del ensayo**, no prueba de ganancia ni pérdida del método. Si ocurre después de cerrar el único intento de formalización, cierre operativo por no demostración, pero NO_G0 económico sería afirmación falsa.
- **ESTADO ACTUAL: PENDING_SOURCE_NOT_FINAL**, mientras A/B continúan adjudicando fuentes: NO anunciar NO_EVALUABLE definitivo sin cerrar formalmente intento de fuente. Ni PF ni 7Y accesados.

## Puerta objetiva código + pruebas

`src/qore/infrastructure/trader_lab/vt08_a_final1_three_verdict_author_fidelity_gate_v1.py` implementa source-rule receipts separados de selector causal. Requiere una recibo identificado/clock as-of SHA para cada precondición:
`HTF_BIAS_KNOWN_PRE_C2`, `RELEVANT_SWING_REFERENCE_PRE_C2`, `RELEVANT_POI_PRE_C2`, `C2_CLOSURE_AND_M3_CISD_PS_ASOF`, `C2_EQ_REGIME_CONFIRMED`, `BREAKER_LOW_AUTHENTICATED`, `STOP_BELOW_BOTH_EQ_AND_BREAKER`, `EXTERNAL_TARGET_UNTOUCHED_ASOF`, `C3_POSITIONAL_OPEN_AND_ORDER_CLOCK`.

Asegura que reference swing, POI y HTF bias were known-at **no después de C2.open**, el clock de nueva C3.open == C2.open+30m y que ninguna fuente posterior puede atribuirse a C3.open. Audita dos raters independientes para un criterio discrecional ex-ante en snapshot sin resultados futuros; esa decisión se etiqueta **C-QORE revisión ciega**, no se transfigura en fórmula del autor A. El mero formato correcto de hash o un flag de raters nunca autentica por sí solo la independencia: el reviewer B debe comprobar la *firma externa y la materialización de fuentes*, y confrontar receipts con M3 broker y snapshots. No confundir tests de contratos con datos de mercado reales.

La validación económica consume resultados sólo si este contrato fuente está completo y dataset/fees/manifiesto A+B también están completos. El contrato funciona como **barrera documental research-only**: GO sintético en tests es comportamiento unitario, NO autenticación económica y ninguna rutina autoriza LIVE ni apertura de holdout.

## Qué sigue exactamente sin descubrir otro proxy

**Issue #787**: para C2 bullish M30/M3, identificar causalmente (a) swing PRE-C2 relevant valid context/EQ-reference; (b) POI desde HTF source con respuesta/reacción; (c) breaker true-low y series up-close; (d) target prior HTF high untouched y desempate; (e) broker-specific bidask fees as-of, partición independiente autorizada. Todo ello **sin alterar una sola señal por su PnL**.

Si no existe un selector fuente que el auditor B pueda reproducir sin mirar adelante, formalizar `NO_EVALUABLE` tras cierre documentado de fuente, dejar 7Y sellado y cerrar. Si se completa, UNA validación congelada, no varias rondas. La vieja prueba QORE M30M3 de 3561 madres permanece **NO-GO para QORE PS-only**, no es resultado de esta familia.

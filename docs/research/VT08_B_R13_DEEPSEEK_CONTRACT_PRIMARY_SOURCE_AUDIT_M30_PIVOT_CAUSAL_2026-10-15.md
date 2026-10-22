# VT08 B R13 — Adjudicación independiente del contrato DeepSeek + prueba nativa de pivote M30 causal
**Fecha:** 15-oct-2026. **PR B:** [#764](https://github.com/mezas3238-hue/qore-core/pull/764) (DRAFT). **PR A:** [#765](https://github.com/mezas3238-hue/qore-core/pull/765) (DRAFT). **No merge, no PnL, no 7Y, no sizing.**
**Ejecución nueva:** [R13 GitHub Actions #38797170701](https://github.com/mezas3238-hue/qore-core/actions/runs/38797170701), **5/5 SUCCESS, 7 pruebas adversariales por mercado (35), Ruff PASS, 2.657/2.657 casos físicos completos**, codigo/test commit `3a63c9d690af63d7e517dab462a506a68b4603c0`.

## 1. Propósito — no convertir una opinión de DeepSeek en autoridad automática

Se recibió el texto de un auditor tercero («Contrato Técnico de Reglas TTrades para VT08») con ocho respuestas, clasificadas A/B/D, y el supuesto de que no queda ambigüedad cronológica. **No es un contrato OWNER firmado**, y «cita correcta» NO equivale a «cada uno de los 2.657 candidatos satisface la cita». Aquí se separan: (a) **interpretación de fuente**, (b) **hecho causal de datos originales**, y (c) **admisión semántica individual**. Al usar citas textuales del tercero se verificaron de nuevo las seis páginas TTrades, no se usaron sus conclusiones como reglas por defecto.

### Adjudicación de las 8 proposiciones frente a las fuentes originales

| # | Dictamen del tercero | Resultado de revisión B | Decisión para contrato VT08 |
|---|---|---|---|
| 1 | CISD intrabar y validación retrospectiva al cierre HTF: A | **Respaldado como procedimiento descrito**: autor indica comprobar CISD «inside that higher time frame candle» cuando existe C2/C3 closure. La secuencia resumida «HTF closure first» no obliga a que **se forme** después: puede expresar orden de revisión. | **SOURCE_A texto / SOURCE_B lectura de reloj**. Verificar *C2 CANDLE válida + CISD auténtico* por ID. R12 reporta 2.657 coincidencias físicas disponibles a C3.open, no 2.657 autor-confirmadas. |
| 2 | Entrada C3.open «válida»: A | **Condicional, no absoluta**. Positional Entries requiere modelo fractal **ya completo**, un protected swing **preexistente** y stop que proteja EQ; además coherencia con sesgo, POI y risk/reward. El mero par geométrico R3+R12 no prueba esas condiciones. | **SOURCE_A posibilidad condicional; por caso D aún pendiente**. No abrir fills ni habilitar COG por la hora únicamente. |
| 3 | Protected swing = pivote simple + CISD: A | **Sobre-simplificación**. Artículo CISD exige C2/C3 HTF closure y cambio LTF. Positional Entries exige protected swing lógico con EQ; Relevant Swings distingue pivote geométrico de relevance/separation. El autor NO da contrato universal «todo PS = M30 pivote de tres + M3 CISD». | **D definición/selección completa**, no usar pivote M30 como veto sobre el PS LTF. Este es el motivo de la nueva prueba R13 física. |
| 4 | Breaker no universal: B | **Correcto para positional entries en general**: el artículo Positional Entries no impone breaker en todas. **PERO** Example 1 de 30M→3M describe stop bajo EQ **y** breaker low; ese texto es fuente relevante **para la familia basada en ese ejemplo**. No borrar la condición sin adjudicar familia y congelar nueva hipótesis sin PnL. | **SOURCE_B no universal / D pertinencia al subtipo VT08**. Registrar explícitamente `breaker_requirement_status` por familia. |
| 5 | M30 es HTF y M3 LTF: A | **Correcto para el par estructura/entrada, no todo el sesgo**: Timeframe Alignment distingue tres niveles (bias, structure, entry); H1 puede ser sesgo/contexto si lo justifica una pareja, no debe sustituir la **vela C2 M30 confirmante**. | **A M30→M3 estructura/entrada; D sesgo superior específico**. Las pruebas R7/R9/R10 de H1 son solo contexto hasta fuente aplicable. |
| 6 | 3 velas HTF siempre cerradas para swing relevante: A | **Mezcla dos artículos/reglas diferentes**. Relevant Swings define **pivote geométrico** de 3 barras centro/izquierda/derecha (confirmación estricta de la geometría necesita conocer derecha); **pero** su «fractal lookback» pide mirar **3 HTF incluyendo la actual** para niveles relevantes. No obliga a que **todas** las HTF del lookback estén cerradas para observar máximos/mínimos parciales. Provisional ≠ confirmado. | **A geometría / A lookback / B corte temporal**, nunca usar el proxy R7 (3 H1 cerradas) como exclusión TTrades automática. |
| 7 | Selección EQ, POI, stop, target: D | **Parcial**: EQ **sí** tiene regla determinista una vez definido swing/dirección y vela de C2/C3: C2 con swing rango completo; contra swing close→extremo; C3 rango entero. Lo D es **seleccionar swing relevante, POI, protected swing, SL entre alternativas y target/tie**. | **A fórmulas EQ condicionadas + D entradas/selección**. No elegir rama EQ por PnL. |
| 8 | Reglas A automatizables y D discrecionales | **La fórmula geométrica puede programarse, pero interpretación del patrón y valid separation del autor no queda automáticamente probada.** Automatizar detección de proxies ≠ certificar metodología ni cognitiva. | **A/B operación física, D semantic individual**. Revisión independiente A/B con recibos 27 campos antes de evaluar economía. |

### Enlaces de fuentes y secciones comprobadas

1. [CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/), «How I Use CISD With Swing Points», «Valid Candle 2 Closure With CISD», «The Fractal Nature of the Model», «Final Takeaway». **Cierre M30 válido y CISD dentro de esa M30**, ambos como condición necesaria.
2. [Positional Entries — Enter Before The Expansion](https://ttrades.com/positional-entries-enter-before-the-expansion/), «The Fractal Model Comes First», «The Protected Swing Determines the Stop Loss», «Not Every Protected Swing Is the Right One» y «Risk-to-Reward Still Matters». **Entrada al open solo como posibilidad CON modelo ya completo**.
3. [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/), «What Is a Swing Point», «Understanding Valid Separation», «The Fractal Lookback Window». **No mezclar pivote 3 barras cerrado con lookback 3 HTF incluyendo actual**; separación no tiene umbral autor universal.
4. [EQ Fractal Model](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/), «When Candle 2 Closes Against/With the Swing Point» y «The Mechanical Process». **La rama no es arbitraria tras seleccionar swing válido y vela**.
5. [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/), «Stop Loss Placement», «Key Takeaways». Dos stops específicos en el modelo breaker.
6. [Timeframe Alignment](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/), «Understanding the Three Layers», «Time Frame Pairings», «Example 1 — 30M to 3M Intraday Reversal». Distingue bias/estructura/entry y cita **breaker low+EQ** para ese ejemplo.

## 2. NUEVA prueba R13 (corre el dato real, no es inferencia sobre un gráfico)

**Código:** `src/qore/infrastructure/trader_lab/vt08_b_r13_m30_swept_pivot_temporal_v1.py`  
**Tests:** `tests/infrastructure/trader_lab/test_vt08_b_r13_m30_swept_pivot_temporal_v1.py`  
**Workflow:** `.github/workflows/vt08-b-r13-m30-threebar-pivot-causal.yml`  
**CI verificado:** [#38797170701](https://github.com/mezas3238-hue/qore-core/actions/runs/38797170701), cinco jobs verdes, 35 tests adversariales, fuentes originales fuente SHA (A R3 38715560333, M3 cTrader 35941643396, M15 cTrader 35934924907) pinned, nada post C3.open.

Se reconstruyeron sin importar detector A **C0, C1, C2 M30** desde M15 cTrader, se cotejó C1 y C2 con barras M3 y recibos por bar de A R3. Se exige C2 bullish single-low-sweep: `C2.low < C1.low`, `C2.high <= C1.high`, `C1.low < C2.close < C1.high`, `C2.close > C2.open`. Sin leer ni sumar barras C3 posteriores a C3.open.

| Mercado | Casos R3 fuente | C2 sweep+cierre alcista físico | C1 no puede ser pivote central bullish M30 debido al C2 low | Pivote central C2 M30 necesita esperar a C3.close | C0 M30 disponible |
|---|---:|---:|---:|---:|---:|
| EURJPY | 538 | 538 | 538 | 538 | 538 |
| USDCHF | 518 | 518 | 518 | 518 | 518 |
| NZDUSD | 550 | 550 | 550 | 550 | 550 |
| CADJPY | 516 | 516 | 516 | 516 | 516 |
| USDCAD | 535 | 535 | 535 | 535 | 535 |
| **TOTAL** | **2.657** | **2.657** | **2.657** | **2.657** | **2.657** |

El segundo requisito de un pivote bullish de tres velas **centrado en C1** es `C2.low > C1.low`. Es **lógicamente incompatible** con `C2.low < C1.low` (sweep C2) en **todos** estos casos. Un pivote de tres M30 **centrado en C2** exige la derecha **C3**, que sólo estará completa al final C3, nunca al principio C3 donde la entrada positional se propone. Por tanto, una implementación que exija *ese* pivote M30 específico **antes** de un POS C3.open eliminaría toda la familia por una **confusión de escala temporal**; no es una falsación legítima del PS M3 dentro de C2, que puede tener su propia estructura y barras derechas M3 completas.

**El R13 tampoco valida automáticamente el PS M3**: el detector A observó 2.657 únicos *proxies*, cuyo criterio auténtico aún necesita opposing series, CISD real, protected low, EQ y POI source-reviewed por caso. Este es un control de falso-negativo de método, no un nuevo filtro de ingreso ni estrategia de resultados.

### Hashes canónicos de los cinco reportes fuente R13

- EURJPY: `65d5c33c4541ba98152a34e7b8cf871cef9e9c2fab349c28011100e5a12e1d89`.
- USDCHF: `254038381fedffb221cdad46d4861042f544b2b8c10abb9bdac59afc6383f918`.
- NZDUSD: `32cbc1d8f07b29bd0195750634e980a748109fca0dc1633f1e2badcc2c51432c`.
- CADJPY: `ea6f8a573806cd97759704e1458eeea0a6ddea3b5d554536598913f9f0547662`.
- USDCAD: `84eb2872c6ed75cc3deb8c203fed10070699beb4f0aac7bef783fe799de90d4e`.

**QA roja preservada:** el primer CI [#38796831030](https://github.com/mezas3238-hue/qore-core/actions/runs/38796831030) falló por fixture M15 de test con schema `bars` en vez de `periods.M15`; corregido respetando esquema cTrader. Segunda CI [#38796955588](https://github.com/mezas3238-hue/qore-core/actions/runs/38796955588) falló porque un test que modificó el M15 sin reemitir IDs recibos fue capturado **antes** de llegar al supuesto de discrepancia M3 vs M15. Se corrigió el **test** para recomputar recibos M15 consistentes con su propio feed sintético y aislar desacuerdo cross-feed, sin modificar verificadores; tercer CI #38797170701 **5/5 verde**.

## 3. Contrato de estados propuesto para adjudicación A/B

Los estados NO son señales. Requisito de fuente específica: 
- `C2_M30_SOURCE_SWEEP_CLOSE=PHYSICAL_PASS`, **no autoriza** `RELEVANT_SWING_A`.
- `M3_CISD_PROXY_FORMED_AT=<M3.close>`, `JOINT_C2_CLOSE_M3_CISD_KNOWN_AT=C3.open`; **validación auténtica CISD=UNADJUDICATED** hasta analizar opposing candles.
- `M30_C1_CENTER_THREE_BAR_BULL_PIVOT=PHYSICAL_FALSE` para los 2.657 casos; `M30_C2_CENTER_THREE_BAR_BULL_PIVOT_ASOF_C3_OPEN=NOT_YET_OBSERVABLE`.
- `M3_PROTECTED_SWING_AUTHENTIC`, `M30_RELEVANT_SWING_CONTEXT`, `VALID_SEPARATION`, `POI_REVERSED`, `EQ_BRANCH`, `BREAKER_REQUIRED_FOR_THIS_FAMILY`, `STOP_ID_AND_CONSTRAINTS`, `TARGET_HTF_UNTOUCHED_AND_TIEBREAK` = fuente D pendiente en los cases no adjudicados.
- Autoridad A/B deberá **firmar y revisar independientemente** valores/IDs/source refs antes de un manifest; cero promociones por el propio script. B exige 27 `CAUSAL_FIELDS` procedentes de fuentes reales, respetando `available_at <= C3.open`.
- **0** registros source-complete, **0** admisiones cognitivas, **0** fills; `profit_factor=null`. No pruebas económicas válidas, no sizing, holdout sellado intacto; ningún PR merge.

## 4. Siguientes acciones para A y B

**A metodológico:** congelar el contrato **M30 estructura + M3 CISD/Protected Swing + bias HTF**; separar explícitamente pivot HTF vs protected swing LTF; definir el **breaker** específicamente para el ejemplo elegido; dar fichas de autor por cada candidato pre-PnL, con source-relevance, opposing series, contexto POI, protected swing elegido y stops/target. No dar A a una interpretación derivada sin justificar.

**B cognitivo:** conectar R12 formación y joint-observable con R13 cierre C2 y contradicción pivote M30; rechazar cualquier situación que sostenga `M30_C1_THREE_BAR_PIVOT=true` en un caso de sweep o que adjudique un pivote C2 con barras de C3 posteriores; **nunca usar el falso veto como prueba contra Protected Swing M3**; luego los 27 campos originales probados individualmente.

**Estado:** fuente física auditada, interpretación de tercer auditor parcialmente incorporable, **VT08 NO CERTIFICADO**. Sin manipulaciones económicas.

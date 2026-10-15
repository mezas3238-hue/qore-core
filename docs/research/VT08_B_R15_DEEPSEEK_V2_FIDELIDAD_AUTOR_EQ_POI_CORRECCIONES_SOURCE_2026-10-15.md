# VT08 B R15 — Dictamen adversarial DeepSeek Contrato TTrades V2 y EQ/POI verificados
**Fecha:** 15-oct-2026. **Rama B:** `agent/vt08-5m-cognition-replay-20261010`. **B:** PR #764 DRAFT. **A:** PR #765 DRAFT. **Estatus:** `SOURCE_PHYSICAL_AND_RULE_TEXT_PASS / V2_AS_WRITTEN_REJECTED / RULE_COMPLETE_ZERO / NO_ECONOMIC_CERTIFICATION`.

## 1. Fuente independiente y errores materiales del contrato V2

Se revisó el texto recibido «Contrato VT08 TTrades V2» contra **fuentes primarias HTML reales**, no contra citas intermediarias; y se re-ejecutó prueba source-only original cTrader M3.

**CORRECCIÓN 1 — V2 declara la selección de POI enteramente D. FALSO como regla general.** El texto original [The Only Points of Interest That Actually Matter For Trading, 18-jul-2026, «Fair Value Gaps Come First», «If There Isn't a Fair Value Gap», «CISD Is the Final Point of Interest»](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/) **define explícitamente jerarquía condicional para CONTINUACIONES** desde protected swing hacia current range:

`FVG > SWING_HIGH_LOW > CISD_RETEST`.

Si un FVG existe **entre protected swing y current range**, el autor instruye elegir esa **categoría**, sin seguir buscando swing; si no hay, swings; si tampoco, retest CISD. **No significa** que cualquier FVG de la pantalla sea válido, ni desambigua **varios FVG de la misma categoría** ni determina protected swing inicial. Por eso hay contenido Clase A REAL para R09 POI category, pero la selección específica y el punto de inicio siguen D cuando hay múltiples objetos/discreción.

**CORRECCIÓN 2 — V2 ejemplo bullish EQ usa incorrectamente `(C2.close + C2.low)/2` para la C2 BULLISH congelada.** [How To Use Equilibrium (EQ) — TTrades Fractal Model, 10-oct-2026, «When Candle 2 Closes Against/With The Swing Point» y «The Mechanical Process»](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/) prescribe:
- **Bullish swing + C2 bullish body**: `EQ=(C2.high+C2.low)/2`, rango completo.
- **Bullish swing + C2 bearish body**: `EQ=(C2.close+C2.low)/2`, cierre→mínimo.
- **Bearish swing + C2 bullish body**: `EQ=(C2.close+C2.high)/2`, cierre→máximo.
- **C3 cierre**: rango completo.
- Sin conocer `source_author_validated_swing` NO corresponde elegir ninguna rama como `trade_EQ`. El primer texto de [Using EQ in Continuations (02-ago-2025)](https://ttrades.com/using-equilibrium-in-continuations/) dice generalmente wick high→wick low; el artículo de oct-2026 **especifica** la excepción cierre→extremo condicionada, no es licencia para ignorarla.

**CORRECCIÓN 3 — Protected Swing y posición C3 no se certifican por `pivote + sweep + CISD` aislados.** [Ideal Formation, 27-jun-2026, «The Ideal Candle 2 Formation» y «Why Point of Interest Matters»](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/) describe un *ideal* que simultáneamente cierra C2, crea protected swing y reacciona en POI **significativo**; además dice que C2 válida no necesariamente es *ideal*. [Positional Entries, 08-ago-2026, «The Fractal Model Comes First» y «The Protected Swing Determines the Stop Loss»](https://ttrades.com/positional-entries-enter-before-the-expansion/) exige fractal completo y protected swing **ya existente antes** del nuevo HTF open. R14 reconstruyó 2.657 M3 series/cierres geométricos independientes, **NO POI significativo ni protected swing autor-válido**.

**CORRECCIÓN 4 — V2 R05 breaker fijo M30 por una secuencia de 4 puntos no se sigue de la fuente para cada R3.** Fuente [Time Frame Alignment, 30-jul-2025, «Example 1 — 30M to 3M Intraday Reversal»](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) exige para ese **ejemplo específico** stop bajo EQ de M30 Y breaker low, y advierte **dejar espacio para FVG inferior**. El breaker **no es** requisito universal de todo POS; no hay justificación fuente para fijar el detector low→high→lower-low→higher-high como cuatro barras M30 adyacentes, ni el breaker low específico, y un proxy de cuatro M3 individuales no prueba swings válidos. El stop `SL < EQ` y `SL < breaker_low` es **relación necesaria dentro del ejemplo**, NO autorización suficiente si PS/POI/stop-invalidation/FVG/RR siguen desconocidos.

**CORRECCIÓN 5 — V2 R10 impone target disponible antes de C2.open como regla A universal. NO sustentado.** [How to Set Price Targets Using the Fractal Model, 23-may-2026](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/) exige previous swing highs y niveles HTF untouched; no establece **C2.open** como deadline universal. La restricción ineludible para entrada C3.open es disponibilidad causal `target.available_at <= C3.open` y determinación de no-tocado **hasta ese cutoff**, sin barras del futuro; exigir PRE-C2 sería una restricción conservadora no atribuible al autor salvo prueba fuente específica; no habilita otra metodología dentro de VT08. R9 halló 1.357 niveles H1 cuyo cierre fue DURANTE C2 y estaban físicamente disponibles al C3.open; **no etiquetarlos automáticamente INVALID author** ni elegirlos por PnL. Sigue D cuál objetivo de varios y si un H1 high recién confirmado es «previous HTF» apto.

**CORRECCIÓN 6 — V2 R12 describe calidad de CISD como obligación falsable en todas las entradas.** [CISD Confirms Swing Points, 10-ene-2026, «What a High-Quality CISD Looks Like»](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) presenta V-shape / strong displacement, decisive close y minimal consolidation con carácter de **«usually»**, NO umbral obligatorio. Separar `CISD_GEOMETRIC_CORE` de `CISD_QUALITATIVE_PREFERENCE`; un filtro fuerte formalizado por QORE sería Clase C, no nuevo criterio A numérico.

## 2. Nueva prueba B R15 — 5 mercados, todas las M3 nativas

Código: `src/qore/infrastructure/trader_lab/vt08_b_r15_v2_eq_poi_source_v1.py`  
Tests: `tests/infrastructure/trader_lab/test_vt08_b_r15_v2_eq_poi_source_v1.py`  
Workflow: `.github/workflows/vt08-b-r15-v2-source-eq-poi-audit.yml`

**[GitHub Actions R15 #38803620750](https://github.com/mezas3238-hue/qore-core/actions/runs/38803620750)**: **5/5 SUCCESS**, Ruff + **14 tests/job = 70 ejecuciones**, SHA-verified fuente A R3 `#38715560333` y original M3 cTrader `#35941643396`, 2.657/2.657 íntegros, sin PnL, sin futuro ni 7Y.

Recomputación de M30 C2 desde diez M3 RAW individuales con horarios y `source_bar_id` autentificados por R11 original B. Ambas fórmulas calculadas a partir de OHLC original para evaluar el error teórico de DeepSeek, **sin elegir `trade_EQ` porque ninguno tiene swing fuente adjudicado**:

| Mercado | C2 alcistas físicas | Rango entero ≠ (close+low)/2 | Numéricamente iguales |
|---|---:|---:|---:|
| EURJPY | 538 | 527 | 11 |
| USDCHF | 518 | 496 | 22 |
| NZDUSD | 550 | 533 | 17 |
| CADJPY | 516 | 504 | 12 |
| USDCAD | 535 | 516 | 19 |
| **TOTAL** | **2.657** | **2.576 (96,95%)** | **81 (3,05%)** |

La fórmula de V2 habría dado **un nivel diferente para 2.576 candidatos si esos candidatos tuvieran un swing genuino alcista**. Es una *diferencia de fórmulas*, **no trades, no ganadores, ni prueba de que 2.576 cuentan con swing válido**. Los 81 restantes cierran en el high de C2, lo cual hace coincidir full y close+low. Este análisis no recorta el denominador y es ciego al futuro.

**SHA256 canónico de la salida completa R15 (por mercado):**
- EURJPY: `b3eaca0d43baceede45f06197e5b30b42e796bc518486dccd268b6bf93440da5`
- USDCHF: `ceda2158d644905002e3bdbd8e8941f3d3d5414c731c45d383450233c55febc0`
- NZDUSD: `483fe30f47b08221e7802d1c1c0f214ae71bd760306c50137f512939a591c190`
- CADJPY: `220960c7bbd5e5c9b3c31e794f090afccf03dab6f6a21f948628b9e28e70acbc`
- USDCAD: `43d2f4537137045e2528d1222b64114357ea2f0711c85d60979ed1fd4777602d`

**POI pure contract** `continuation_poi_priority`: solo si `protected_swing_author_validated=True` se expone la **primera categoría no vacía** siguiendo FVG→SWING→CISD; si hay >1 objeto de esa categoría se marca `D_MULTIPLE_SAME_TIER_OBJECTS`; incluso un solo objeto categoría requiere source IDs/cutoff para seleccionar trading POI; siempre `chosen_poi=None`, para evitar prueba de fuente fabricada. Con PS no validado marca `D_PROTECTED_SWING_UNVERIFIED` aun si existen muchos FVG proxies.

**QA transparente**: runs iniciales [#38803481213](https://github.com/mezas3238-hue/qore-core/actions/runs/38803481213), [#38803548744](https://github.com/mezas3238-hue/qore-core/actions/runs/38803548744) y [#38803570110](https://github.com/mezas3238-hue/qore-core/actions/runs/38803570110) fallaron por import tipo Decimal con alias `D` prohibido por Ruff y corrección posterior de la prueba/semántica rama bearish; el final #38803620750 **5/5 verde**, sin suavizar verificador fuente.

## 3. Adjudicación de las 12 reglas V2 — qué queda realmente aprobable

| V2 ID | Dictamen source-first B R15 | Status |
|---|---|---|
| R01 C2 closure | Autor explícito barrido previa vela + cierre dentro. **La cohorte R3 tiene GEOMETRÍA, no prueba de sweep a un POI relevante ni bias.** | A regla, `GEOMETRIC_PHYSICAL_ONLY` por ID |
| R02 M3 CISD | Autor requiere importante nivel / POI, liquidez y cierre **a través** de las velas que crearon el extremo. R14 demuestra una serie bajista + cierre, **no el POI ni la validez del contexto**. | A patrón, D calidad/contexto por ID |
| R03 Protected Swing | La formación ideal requiere HTF closure, CISD de opposing candles, sweep de liquidez + POI significativo. **No toda recuperación geométrica = protected swing autenticado**. | A condiciones, D validación por caso |
| R04 EQ | **A fórmula condicional** tras swing validado. V2 bullish C2 contra swing usa incorrectamente close→low; con bullish swing/body se aplica full C2. | A fórmula; EQ actionable D |
| R05 Breaker | Autor lo describe, pero no otorga **cuatro velas M30 consecutivas** ni identifica qué breaker usar en todos los R3. | A estructura general, C proxy, D selección |
| R06 Stop | En Example1 específico: debajo de EQ **y** breaker, más protección del PS / margen FVG. `SL < min(EQ,breaker)` necesario pero insuficiente. | A ejemplo, D identidad/posicionamiento |
| R07 Buffer stop | Sin offset numérico universal. No inferir buffer desde PF ni admitir un buffer inventado como regla del programa VT08 actual. | D TTrades, **NO AUTORIZADO** hasta evidencia fuente/decisión de alcance del Owner |
| R08 PS entre múltiples | El más cercano no necesariamente es correcto; selección contextual por EQ/delivery sin tie universal. | D aún |
| R09 POI | **A JERARQUÍA DE CATEGORÍAS** FVG > swing H/L > CISD retest, de fuente 18-jul-2026; empate dentro de FVG/swing y start PS D. | A tier / D object |
| R10 HTF target | Tipos A: highs/lows untouched y previous HTF. **cutoff PRE-C2 no es A universal**; no usar futuro C3; al decidir C3.open, nivel debe estar confirmado y aún intacto. | A tipos / D selección y frontera específica |
| R11 Tie de targets | Múltiples niveles HTF y dealing ranges pueden coexistir; ninguna jerarquía universal demostrada. | D |
| R12 Calidad CISD | V-shape/displacement/minimal consolidation son **observaciones cualitativas «usually»**, no criterio cuantitativo binario obligatorio. | A preferencia descriptiva / D binarización sin fuente |

## 4. Rectificación vinculante de alcance: programa único VT08, sin QORE-alpha

**FE DE ERRATAS 15-oct-2026, por instrucción explícita del Owner.** La versión anterior de este informe propuso erróneamente dos vías, incluida una supuesta variante QORE-alpha. **ESA PROPUESTA QUEDA EXPRESAMENTE RETIRADA Y RECHAZADA.** QORE-alpha fue **excluido previamente del programa** y no es candidato de certificación, alternativa, subtipo, salvamento ni benchmark de VT08. No hay autorización para mezclar componentes, reglas C, señales, métricas, datasets, resultados o identidad metodológica de QORE-alpha con VT08. Mencionar aquí su nombre sirve solo para registrar la exclusión, nunca para rehabilitarlo.

**Única línea admitida: VT08 actual**, con metodología TTrades sometida a comprobación de autor, cognitiva correspondiente y Gates de rentabilidad **solo después** de superar la validación fuente A/B. El estudio físico de las 2.657 geometrías congeladas sigue siendo investigación de VT08, no una invitación a crear otro trader. Donde falte una regla original, dejar `D_PENDING_SOURCE_AUTHORITY` y `WAIT`, **sin inventar una variante nueva, filtros posthoc ni operar**. Nunca importar un modelo QORE-alpha, ni cambiar el objetivo de certificación sin nueva instrucción expresa de alcance del Owner.

**Instrucción para ambos arquitectos:** rechazar cualquier manifest o candidato que se anuncie como `VT08-QORE-ALPHA`, `QORE-alpha`, `QORE_ALPHA`, `QORE-alpha hybrid`, `alpha fork` o mezcle características identificadas como excluidas. La presencia de código compartido en el repositorio QORE CORE no otorga admisibilidad a una metodología excluida. Preservar el denominador de 2.657 y todas las evidencias R9–R15 únicamente como **VT08 source-only**. Esta rectificación prevalece sobre cualquier propuesta anterior en documentos o comentarios de esta rama que sugiera una segunda vía.

**Queda trabajo P0 A:** rater fuente real del contexto swing y su separación, identificar protected swing apropiado y POI con fuente hierarchy, breaker/stop bajo EQ correcta y target selecciones con IDs y clocks. **P0 B:** cotejar esos recibos con M3/M15 nativos, `CAUSAL_FIELDS` (27), WAL/manifest y firmantes auténticos; false SOURCE_COMPLETE abstiene.

**R15 Estado global:** `B_RULE_SOURCE_MISMATCH_REPAIRED`, `PHYSICAL_C2_EQ_CENSUS_PASS`, `POI_AUTHOR_TIER_DOCUMENTED`, `A+B_MANIFEST_NONE`, `AUTHOR_COMPLETE_0`, `COGNITIVE_ADMISSIONS_0`, `BROKER_FILLS_0`, `ECONOMIC_NOT_EVALUABLE`, `HOLDOUT_7Y_SEALED`, `SIZING_NOT_USED`, VT08 **NO CERTIFICADO**.

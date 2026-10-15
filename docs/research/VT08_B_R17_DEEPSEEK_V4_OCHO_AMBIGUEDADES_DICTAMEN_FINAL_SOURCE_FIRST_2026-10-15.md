# VT08 B R17 — Dictamen adversarial del último contrato DeepSeek sobre 8 ambigüedades

**Fecha:** 2026-10-15 · **Rama B:** `agent/vt08-5m-cognition-replay-20261010` · **A:** PR #765; **B:** PR #764; ambos DRAFT. **Estado:** `RULE_TEXT_SOURCE_ADJUDICATED / SETUP_SOURCE_AUTHORITY_NOT_GRANTED / AUTHOR_COMPLETE_0 / COGNITIVE_0 / NO_ECONOMIC_CERTIFICATION`.

**Gobernanza OWNER vinculante:** [VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md](VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md). Solo VT08 metodología TTrades/cognitiva propia. QORE-alpha excluido por completo; prohibido importar su lógica, optimizaciones o experimentos, así como inventar reglas bajo identidad del autor; no usar sizing ni holdout 7Y.

## 1. Dictamen de los ocho puntos contra páginas primarias del autor (revisadas 15-oct-2026)

### P0.1 Swing relevante — A definiciones, D selector

**A textual real:** [Relevant Swings (21-mar-2026)](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/), secciones `What Is a Swing Point` (pivote 3 barras con mayor low a ambos lados), `Failure Swings vs Relevant Swings`, `Understanding Valid Separation` (NO existe regla cuantitativa; autor dice `There is no strict numerical formula`), `The Fractal Lookback Window` (LOOKBACK tres velas HTF INCLUYENDO la actual). No equiparar `tres HTF incluyendo la actual` a `tres cierres HTF confirmados`. **El pivote confirmado de tres barras requiere el lado derecho ya conocido**, pero un extremo de ventana HTF en formación es solo observación live as-of, no un pivote validado por cierre.

**D:** quién selecciona el swing relevante entre varios, qué hacer con separación discrecional, qué HTF contextual gana entre M30/H1/H4. La frase `extreme of move` contextual NO define un desempate general. Una decisión `C2.open` no puede leer el futuro de C2; una `C3.open` puede ver la C2 final, siempre diferenciando `available_at`. Una POI previa al CISD se fija antes del CISD, pero el swing EQ y la entrada HTF no deben antedatar evidencia observada al cierre C2.

### P0.2 Protected Swing — A secuencia, D selección/POI y alcance

**A:** [Stop Loss Mastery (07-ago-2025)](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/) dos pasos: precio alcanza `important level` (sweep low/FVG) y cierra SOBRE serie de velas que originó el movimiento; [Let The Wick Form, Trade The Body (29-ago-2026)](https://ttrades.com/let-the-wick-form-trade-the-body-stop-getting-stopped-out/) aclara que barrido no confirma, cierre a través de la serie sí. [CISD Confirms (10-ene-2026)](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) exige un `important level` y cierre a través de las velas que crearon el extremo; HTF C2/C3 cierre también necesario para validar conjunto fractal. [Positional Entries (08-ago-2026)](https://ttrades.com/positional-entries-enter-before-the-expansion/) exige protected swing **ANTES de la apertura HTF siguiente** y fractal completo.

**NO APROBADO:** `sweep + cisd` genérico en 2.657 proxies no establece que el nivel haya sido `important`, que sea `the` series causal, ni qué PS seleccionar cuando hay varios. R14 auditó 2.657 geometrías y R12 2.657 cronologías, no 2.657 PS autor-signados. Distinción importante de [Ideal Formation (27-jun-2026)](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/): una formación IDEAL C2 simultáneamente confirma closure y PS; la mera observación intrabar de PS y C2 cierre posterior no prueba cada componente del ideal original. No imponer `pivote M30 de tres barras` como condición universal de cada PS M3.

### P0.3 POI significativo para REVERSIÓN — A categorías, D prioridad/objeto

[A CISD](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) permite important level FVG/high/low con CISD posterior; [Ideal Formation](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/) requiere reacción en POI para ideal. La [jerarquía FVG→swing H/L→CISD retest, 18-jul-2026](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/) está redactada para **CONTINUACIONES iniciadas desde un protected swing**, no una prioridad universal para **reversal C2 M30**. Una posición sin FVG puede buscar high/low válido, pero sin identidad/source IDs de ese POI no hay source-complete.

**Corrección al contrato DeepSeek:** `sin CISD` invalida la **confirmación de la entrada**, NO borra necesariamente un FVG/alto/bajo previamente existentes. No tratar `POI_EXISTS` = `POI_REACTION_CONFIRMED` = `POI_SELECTED_FOR_THIS_SETUP`. Tres evidencias distintas, sus timestamps y su procedencia deben separarse. `POI` marcado solo a posteriori tras éxito es circular y prohibido. Si POI existe antes CISD y este cierra, **todavía** queda identificar cuál POI produjo el cambio en la estructura.

### P1.4 EQ — A fórmula condicionada de C2, D swing seleccionado

[How To Use Equilibrium (EQ), publicado 10-oct-2026](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/) **sí existe y se leyó**. Si C2 cierra CON dirección del swing: `(C2.high + C2.low)/2`. Si C2 cierra CONTRA swing alcista (C2 bajista): `(C2.close+C2.low)/2`. Si contra swing bajista (C2 alcista): `(C2.close+C2.high)/2`. C3 **después de cerrar** full range. **No sustituir** por EQ general de dealing range de artículo distinto y no aplicar selectores sin swing autor adjudicado.

R15 [#38803620750](https://github.com/mezas3238-hue/qore-core/actions/runs/38803620750) 5/5 SUCCESS, 70 pruebas, **2.657 C2 bullish fuente original**; comparar full-high-low contra errónea close-low usada en V2 difiere **2.576/2.657**, aunque esto solo es contrafactual matemático **condicional**, no 2.576 setups genuinos. `TRADE_EQ_SELECTED=None` mientras `SWING_AUTHOR_VALIDATED=D`.

### P1.5 Breaker — A estructura, D identidad/timeframe/stop level

[Breaker Blocks Simplified (05-jul-2025)](https://ttrades.com/breaker-blocks-simplified/): bullish Low→High→Lower Low→Higher High, seleccionar **serie de up-close candles entre Low y High** de la estructura, no sustituir por los lows de cada una de cuatro velas M3/M30 consecutivas sin swing IDs. Exige HH antes de usar estructura completa. [Timeframe Alignment Example1 (30-jul-2025)](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) **sí** exige stop bajo breaker low EN ESE EJEMPLO M30→M3. Breaker genérico se puede formar en varios TF; la elección del breaker real/TF relevante al Example1 sigue D. El doc permite stops `just beyond breaker block` O swing que confirma breaker EN LA TÉCNICA GENERAL; no confundir ambos niveles. La ausencia de breaker bloquea la certificación de **este ejemplo específico**, no demuestra que toda entrada positional sin breaker sea imposible.

### P1.6 Stop — A condiciones específicas, D niveles exactos/buffer/FVG

[Timeframe Alignment Example1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/): STOP **estrictamente bajo EQ M30 Y bajo breaker low**, con espacio para operar hacia FVG inferior en su contexto. [Stop Loss Mastery](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/) establece PS low como invalidación general bullish; [Positional Entries](https://ttrades.com/positional-entries-enter-before-the-expansion/) lo vincula al positional. Numéricamente si los tres son aplicables y VALIDOS: `SL < EQ && SL < BREAKER_LOW && SL < PS_LOW` (equivale a < mínimo), pero esto es **combinación conservadora de contratos de artículos distintos** y **NO** una frase universal escrita por el autor. **No promover min() a señal source-complete**, ni afirmar que basta estar debajo sin controlar la zona FVG inferior, fuente de niveles y RR.

`buffer` positivo mínimo pips/ATR no publicado. No inventar distancia para obtener PF/DD; `SL < level` es relación matemática y por sí sola no define un precio stop reproducible, feed-dependent e íntegro. Un stop demasiado lejano para R:R puede descartar trade por criterio de ejecución aún sin umbral numérico A universal.

### P1.7 Target — A tipos y estado untouched, D jerarquía entre niveles

[How to Set Price Targets (23-may-2026)](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/): previous highs en long, `untouched` (ya tomado deja de ser objetivo), previous HTF highs/lows; ofrece `5M→H1` como **ejemplo**, NO prioridad vinculante `M3→H1` frente a H4/D1. Variantes de dealing range high contextual no implican un target único sin swing origen seleccionado. Timing obligatorio **como mínimo `target_qualified_at <= decision_at = C3.open`**, `untouched` comprobado hasta ese punto, sin precios de después. El artículo no fija si todo target tuvo que existir antes de C2.open. En A R6 2.437 casos tienen múltiples highs H1 reales → selector D.

### P1.8 CISD calidad — A cualidades, D obligatoriedad cuantitativa

[CISD Confirms (10-ene-2026)](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/): V-shape / displacement / decisive close / minimal sideways consolidation son ejemplos de `usually shows` para `high-quality`, no fórmula cuantificada universal. **CISD_CLOSED_THROUGH_OPPOSING_SERIES** sí es condición exigible. Rechazar por `no closes through` es válido; rechazar TODAS las continuaciones por `3 candles`, `n pips`, `ATR` inventados no es fiel al autor. Calidad puede anotarse ciegamente de forma descriptiva con `rater1/rater2` y disentimiento D, sin convertir anotación en nuevo filtro por PnL.

## 2. Matriz de dependencia: regla escrita vs prueba por candidato

| Regla | Regla A escrita | Evidencia física B | Autorización por caso | P0 |
|---|---|---|---|---|
| C2 sweep/close | Sí | 2.657 geometrías | NO: bias/relevant swing/POI D | Sí |
| M3 opposing-series CISD | Sí | 2.657 eventos R14 | NO: POI important/series causal D | Sí |
| Protected Swing | Sí (dos pasos) | proxies M3 | NO: protected swing contextual D / 476 multi-PS D | Sí |
| Swing relevante | Definición + ventana | pivots/fuentes disponibles | NO: separación/desempate D | Sí |
| POI reversal | Tipos FVG/high/low | no source POI completo | NO: validez/relevancia/selección D | Sí |
| EQ C2 | Fórmula condicional A | R15 2.657 ambos valores | NO: swing dirección validada D | Sí |
| Breaker | estructura A | formas proxy | NO: breaker source low D | Sí |
| Stop | relación ejemplo A | ninguna autorización ejecutable | NO: level ids/buffer/FVG D | Sí |
| Target | tipos untouched A | múltiples H1 R6 | NO: selección/tie D | Sí |
| CISD quality | preferencia descriptiva A | ningún rater completo | NO: no umbral de exclusión A | Secundario |

**Interpretación:** «Regla escrita A» NO equivale a «regla implementada/validada por 2.657 casos». El contrato DeepSeek revisado identifica correctamente A vs D en muchos lugares; la conclusión de que Protected Swing, Breaker, Stop y Target quedaron «resueltos definitivamente» debe quedar acotada SOLO a **definiciones**, no a selección ni a suscripción A/B por caso.

## 3. Nuevo plan operativo sin inventar TTrades, sin QORE-alpha

1. **Arquitecto A:** registrar fichas físicas por caso `reference_swing_candidates` con bar IDs, timeframe, `available_at`, `confirmed_pivot` vs `HTF_3BAR_WINDOW_LIVE` claramente distintos, `valid_separation` anotación no numérica; `POI_candidates` pre-CISD con IDs, tipos FVG/swing/high/low, zonas y clocks; `PS_causal_opposing_candles` y múltiple; `BREAKER_swing_sequence+up_close_candles`; target candidates untouched; `EQ_if` solo condicional, sin trade authority.
2. **Arquitecto B:** revisión ciega al resultado de muestras estratificadas (ambiguas y nítidas; no solo 52 limpios), doble rater1/rater2 y disensos firmados antes de PnL; full audit para toda afirmación positiva, independientes M3/M15 RAW original (sha, clock, market, cutoffs). No usar un `boolean approved` externo como fuente.
3. **A+B:** producir `author_rule_source_evidence` por campo, si decisión esencial sigue D, abstener. **No** reinterpretar muestreo visual como regla numérica A universal. Priorizar true swing+POI antes de intentar escoger EQ, PS, stop, breaker y target.
4. **Gobernanza:** solo VT08 TTrades/cognitiva; cero importaciones QORE-alpha (Owner R16 CI [#38805194446](https://github.com/mezas3238-hue/qore-core/actions/runs/38805194446) PASS 170 tests). Ningún sizing, holdout 7Y intacto, no LIVE/DEMO/VPS ni merge.
5. **Economía:** sin A+B semantic PASS ni 27 `CAUSAL_FIELDS` auténticos, las métricas PF/DD/Sharpe/Sortino siguen `NOT_EVALUABLE`; no estimar ganancias con geometría proxy.

## 4. Estado real y bloqueo remanente

- Fuente A autor (definiciones de 8 aspectos): mayormente aclarada / parcialmente fuente verdadera.
- 2.657/2.657 geometrías físicas M30/M3, no autor-entidades.
- `RULE_SELECTED_BY_SOURCE_PER_CASE = 0` · `AUTHOR_COMPLETE_ENTRIES = 0` · `REAL_COGNITIVE_ADMISSIONS = 0` · `BROKER_FILLS = 0` · `ECONOMIC_GATES = NOT_EVALUABLE`.
- `R17 = SOURCE_TEXT_ADJUDICATION_DOCUMENT`; **sin pretensión de pruebas adicionales ni certificación**. R13/R14/R15/R16 pasan su CI previo, mientras este R17 es dictamen de fuente y adjudicación humana.

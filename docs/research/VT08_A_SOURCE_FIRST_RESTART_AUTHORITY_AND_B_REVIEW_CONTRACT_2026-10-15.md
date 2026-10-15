# VT08 — Arquitecto A: reanudación SOURCE-FIRST y contrato de revisión B

**Fecha:** 2026-10-15 · **Proyecto:** QORE CORE · **Estado:** `METHODOLOGY_SOURCE_INCOMPLETE` · **PR:** #765 (draft) · **Issues:** #762 A / #763 B · **Fuente de continuidad:** handoff maestro 2026-10-14 en PR #764, commit `6c4fd6fbe5f4a38fac3d0dda457f190e018a8de1`.

## 1. Alcance y decisión de gobernanza

Esta entrega es una **revisión de especificación y barreras de certificación**, NO un replay, NO un ensayo de rentabilidad, NO un manifiesto A/B firmado y NO un permiso de ejecución. El Owner pide certificación de VT08 por **metodología TTrades original + cognitiva QORE**, además de Gates PF, DD, Sharpe, Sortino, OOS y robustez. Sizing, leverage, compounding y pesos de CIBO quedan prohibidos para obtener la certificación del Trader. Sin merge, sin VPS, DEMO, LIVE ni acceso al 7Y sellado.

**Identidad:** el ensayo FINAL1 #787 está cerrado/superado. Su prerregistro bullish M30→M3 sigue siendo un **modelo de referencia acotado**, no una validación económica nueva automáticamente autorizada. El antiguo prototipo QORE PS-only tuvo PF bruto <1; este resultado **no prueba** que el TTrades original carezca de edge. No fusionar VT08 con QORE-alpha #798 ni reoptimizar el prototipo falsado.

**Universo congelado de expansión:** EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD. Política Owner de anclas H4 NY 01/05/09 y máximo una entrada por mercado/día; los perfiles H4/M15/M5 y la familia de ejemplo M30/M3 **no son intercambiables**. Ninguna familia de ejemplo debe darse por aprobada para H4 sin su propia acta de traslación metodológica.

## 2. Adjudicación escrita A vs selector D: familia de EJEMPLO M30→M3

| ID | Regla verificable en fuente primaria | Parte que NO está resuelta / autoridad |
|---|---|---|
| A-01 | HTF bias → estructura CISD → trigger; ejemplo reversal bullish 30M→3M [Timeframe Alignment, 30-jul-2025, Three Layers / Example 1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) | **D** selector causal del bias direccional concreto, conflictos HTF, priorización; no sustituir por `daily_bias` del viejo B01 sin fuente |
| A-02 | Los swings relevantes requieren extreme/contexto/separación; [Relevant Swings, 21-mar-2026, Valid Separation / Fractal Lookback](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/) declara que **no existe separación numérica estricta universal** | **D** qué swing valida EQ ANTES de C2.open; pivot de 3 barras confirmado ≠ automatically relevant; no crear ATR/pips arbitrarios como SOURCE-A |
| A-03 | POI estructural: FVG, swing highs/lows, OB y retest pueden ser relevantes; [Timeframe Alignment, Aligning Structural Time Frame](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) y [POI](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/) | **D** selección/tiebreak y reacción de POI concreto PRE-C2; un FVG geométrico solo ≠ POI autenticado |
| A-04 | [EQ, 10-oct-2026, When C2 Closes Against/With Swing](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/) usa para C2 bullish swing: cierre a favor -> (H+L)/2; cierre en contra -> (close+low)/2 | **D** dirección del swing de referencia ya conocida antes de C2.open, etiqueta del régimen y disponibilidad de C2 OHLC solo al cierre; no dejar que un swing ex post decida la fórmula |
| A-05 | [Timeframe Alignment, Example 1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) indica bullish C2 closure tras sweep y CISD 3M, con estructura de continuación | **D** qué serie opuesta M3 y PS prevalecen cuando hay más de una; probar timestamps de M3 CLOSE <= C2.close, no inventar CISD después de abrir C3 |
| A-06 | [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/) describe estructura bullish; el stop del Example 1 está debajo de **EQ 30M Y breaker low** | **D** elegir low y vela(s) originarias correctas con `source_bar_id`; detector cuatro M3 de QORE = **C-PROXY**; stop concreto solo si EQ y breaker verdaderos ya verificados |
| A-07 | El mismo [Example 1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) añade que el stop deja espacio para visitar un FVG inferior si se forma continuación | **D** identidad/relevancia y cronología de ese FVG condicional; `SL < min(EQ, breaker)` es condición necesaria de niveles, **NO demostración suficiente** de fidelidad total al ejemplo |
| A-08 | [Price Targets, 23-may-2026, HTF Highs/Lows](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/) pide highs previos aún no barridos como objetivos long | **D** cuál target prevalece entre varios highs untouched, sin mirar TP posterior. Un 2R fijo QORE no equivale automáticamente a un objetivo TTrades |
| A-09 | [Positional Entries, 08-ago-2026, Fractal Model / Protected Swing](https://ttrades.com/positional-entries-enter-before-the-expansion/) autoriza entry al open HTF nuevo solo con modelo ya completo, LTF CISD/PS ya confirmado | **D** exacto PS significativo y ejecución BID/ASK as-of; nada de usar C3.high/low final para decidir entrada |
| Q-C | BID/ASK, ticks, comisiones, no-fill, salida/expiración, exact timestamps, stop ordering, validación económica | Reglas operativas **QORE-C**, no fuente textual TTrades A; sin broker proof => NO_EVALUABLE, no poner fee=0 por defecto |

**Equivalencia aritmética, NO validación de origen:** para long, el stop debe satisfacer `SL < min(EQ_M30, BREAKER_LOW)`. Con tick broker verificado `SL <= min(EQ, breaker) - tick` es una formalización conservadora QORE-C; no convertirlo en selector de breaker/POI auténtico.

**Atención a relojes:** los tres relojes de `swing/reference known pre-C2`, `M3 CISD/PS confirmed during C2`, y `entry decision at C3.open` son diferentes. Si el swing depende de high/low final de C2 o de una vela HTF actual todavía abierta, FAIL-CLOSED. La ventana de tres HTF velas del autor incluye la actual, pero los valores de una vela aún abierta **solo** pueden emplearse con snapshot parcial hasta `as_of`.

## 3. Contrato que A debe producir antes de entregar CandidateEvent a B

Cada nivel y estado relevante debe poder contrastarse sin ejecutar código productor A:

1. Identidad: `market`, `methodology_version`, `family`, `ltf_profile`, `anchor_hour_ny`, `scenario_id`, `source_rule_id`, autoridad `A/B/C/D/OWNER_POLICY`, `source_uri`, sección/fecha de artículo y versión congelada.
2. Tiempo/custodia: `source_bar_id`, `source_feed_sha256`, `source_bar_opened_at_utc`, `source_bar_closed_at_utc`, `available_at_utc`, `decision_at_utc`, `event_cutoff_utc`, `source_snapshot_sha256`, zona NY y fold DST, ausencia de lectura post-decisión.
3. Modelo causal: `reference_swing_id`, `reference_swing_right_closed_at`, `poi_id`, `poi_type`, `poi_qualified_at`, `bias_at`, `c2_id`, `c2_closed_at`, `cisd_opposing_series_ids`, `cisd_confirmed_at`, `protected_swing_id`, `protected_swing_validated_at`, `eq_regime`, `eq_basis_bars`, `breaker_origin_bar_ids`, `breaker_low`, `breaker_confirmed_at`.
4. Orden causal: `positional_open_at`, `entry_side`, `entry_quote_id`, `broker_bid_ask_sha256`, `stop_price`, `stop_tick_source`, `target_source_id`, `target_untouched_evidence_asof`, `expiry_rule_id`; llenar solo con hechos auténticos, nunca con proxy sintético.
5. Entrada a Situation cognitiva: mapear por campo los atributos de `Vt08ForexSituationModel` y `vt08_cognitive_5m_research_scope.py` contra los `source_bar_id / available_at / SHA` y `source_class`; `methodology_valid` y `source_identity_complete` **False** mientras exista D en precondición obligatoria. No fabricar valores solo para superar 27+ campos.

El verificador B deberá reproducir un **spec textual congelado primero**, no deducir verdad a partir del productor ni de flags, SHA con 64 caracteres o `reviewers_agree=True`. Juicio discrecional de dos evaluadores ciegos: herramienta QORE-C de reproducibilidad, NO transformación de una regla cualitativa del autor en algoritmo A.

## 4. Auditoría real realizada 15-Oct (sin backtest)

Rama A PR #765. Cambios:
- Commit `92c0aa59ac4d8b95b967ff73f4902fc7fdff8ba9`: el `RuleReceipt` exige **correspondencia exacta entre rule key y página TTrades autorizada**. Antes bastaba `https://ttrades.com/` aunque la página fuera irrelevante. La tabla `SOURCE_PAGES_BY_RULE` es control conservador, no afirmación de source completeness.
- Commit `1994e7a18ec04d316dd5ea1709becb8bb496090e`: adversarial tests de fuente equivocada/query/fragment, nonfinite Decimal y stop; rechazo de ledger económico incoherente donde `gross_profit - gross_loss != fills * expectancy_per_fill`; rechazo de bool en fills. `NaN` / `Infinity` no pueden conseguir GO.
- [CI A final1 #38706126841](https://github.com/mezas3238-hue/qore-core/actions/runs/38706126841): **SUCCESS, Ruff PASS, 28 pytest PASS** sobre contrato (no mercado).
- [CI A CandidateEvent #38706133196](https://github.com/mezas3238-hue/qore-core/actions/runs/38706133196): **SUCCESS**, sin afirmar que habilita órdenes.

**Resultado científico:** 0 nuevas entradas source-complete, 0 admisiones cognitivas, 0 fills de VT08 A+B, PF/DD/Sharpe/Sortino no medidos por esta actualización. `APPROVED_A_B_MANIFEST_SHA256=None` sigue vigente.

## 5. Bloqueos, prioridades y condición de parada

**P0 A (bloqueantes):** (a) relevant swing pre-C2 reproducible, (b) POI causal significativo y desempate, (c) breaker low exacto/FVG room, (d) HTF target untouched y selector, (e) CIN/CISD/PS fuente M3 por clocks y ejemplo; todo sin leer PnL. Si el criterio del autor solo es discrecional, registrar `AUTHOR_SELECTOR_UNSPECIFIED_D` y pedir al auditor B si esa familia es especificable sin una formalización QORE-C explícita, jamás forzar "A" por más tests.

**P1 B:** auditoría independiente del spec y de cada recepción física. Construcción de 27+ Situation fields con provenance real; ledger WAL e idempotencia son tareas B, NO completadas aquí. A/B deben acordar el schema y el hash antes de publicar manifest. Mantener `evaluate_provenanced()` fail closed.

**P2 Gobernanza:** los Gates VT08 antiguos (**PF >=1.80, DD <=6R, MC p95 DD <=15R y P(terminal > 0) >=0.90**) no se sustituyen automáticamente por el GO restringido del #787 (**PF>1.15, >=100 fills, expectancy>0**). El Owner aún no fijó vigencia/umbral nuevo de Sharpe, Sortino y densidad: `PENDING_OWNER_NUMERIC_FREEZE`. No importar gates de Alpha. Sharpe/Sortino requieren definir denominador, serie uniforme 1R, MAR, frecuencia de retorno, anualización, costos y tratamiento de periodos sin fills ANTES del OOS.

**P3 Datos/economía:** custodiar y re-verificar BID/ASK y comisión y checksum de M3/M15; reservar OOS genuinamente no visto. Evaluación pareada baseline metodología sola vs misma metodología + cognitiva, misma secuencia y fricción, sin sizing ni capital compuesto; DD R, PF net, Sharpe y Sortino reportados con intervalos y robustez. 7Y holdout sellado.

**STOP formal:** sin selector fuente repetible, sin manifest B, sin broker proof, sin thresholds versionados o sin OOS legitimado => `NOT_CERTIFIED / NO_EVALUABLE`. No publicar GO económico ni probar variantes para rescatar el PF.

## 6. Solicitud de réplica concreta a Arquitecto B (#763)

B debe revisar **por escrito**: 1) matriz `SOURCE_PAGES_BY_RULE` contra secciones primarias; 2) si cada uno de 9 recibos podría pasar con nombres/SHAs formalmente correctos pero sin mercados auténticos, clasificar límites de barrera; 3) propuesta de binding por campo `Vt08ForexSituationModel` source-id/SHA/as-of; 4) criterio de reviewer independiente para swing/POI/breaker/target y discrepancias; 5) compatibilidad con gateway `evaluate_provenanced()` y bloqueo de entradas en caso D. Responder en issue #763 y NO firmar manifiesto sin ejemplos de mercado validados.

---
**No se han leído outcomes ni liberado holdout; ningún CI de esta ronda representa rentabilidad.**

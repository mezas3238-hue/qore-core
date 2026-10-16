# QORE CORE — VT08 | HANDOFF MAESTRO R8: Arquitecto A → próximo arquitecto
## Metodología TTrades, colaboración cognitiva B, fuentes reales, pruebas, problemas y ruta de certificación
**Checkpoint oficial:** 15 de octubre de 2026 (America/Asuncion)
**Repositorio soberano:** https://github.com/mezas3238-hue/qore-core
**Naturaleza:** transferencia técnica exhaustiva y verificable; NO es certificado económico, permiso de trading, ni firma A/B.
**Continuidad anterior que NO DEBE PERDERSE:** [Handoff maestro 14-Oct](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_HANDOFF_MAESTRO_CERTIFICACION_METODOLOGICA_COGNITIVA_GATES_2026-10-14.md), 228 líneas, checkpoint histórico commit 6c4fd6fbe5f4a38fac3d0dda457f190e018a8de1.
**Este R8 actualiza ese corte con TODAS las rondas A/B verificables del 15-Oct hasta el CI #38765076497.** NO borrar el handoff anterior ni la historia negativa.

---

# 0. DICTAMEN EJECUTIVO Y ESTADO DE SEGURIDAD

**VT08 NO ESTÁ CERTIFICADO.** La certificación exigida por el Owner es integral: (1) metodología auténtica TTrades/adjudicada sin futuro; (2) cognitiva QORE con 27 campos reales verificables y consenso A/B; (3) economía con BID/ASK real, comisiones y ejecución/salida física; (4) Gates de Profit Factor, Drawdown, Sharpe, Sortino, expectativa, Monte Carlo, OOS y robustez, con umbrales congelados por identidad. No basta con que 5/5 jobs o pruebas unitarias sean verdes.

**Lo efectivamente logrado:** datos M3/M15 íntegros y auditados contra raws; universo de 93.230 ventanas C2, 2.657 precursores geométricos de una familia alcista, catálogos por mercado y auditor B independiente de 88.276 bar IDs; aritmética condicional EQ, niveles físicos H1 no tocados en segmentos observados, pivotes H1 básicos y unión final con 52 contextos de revisión prioritaria (NO 52 trades). B ya posee barreras por campo/mercado y runner geométrico indexado. **Cero** candidatos TTrades totalmente adjudicados, **cero** admisiones cognitivas de señal A-fiel, **cero** fills físico-económicos nuevos; PF/Drawdown/Sortino/Sharpe NET = NO MEDIDOS; APPROVED_A_B_MANIFEST_SHA256 = None.

**Prohibiciones heredadas y permanentes para la certificación:** SIZING variable, lotaje dinámico, apalancamiento, compounding, pesos de cartera o manipulación de riesgo para pasar PF/DD/Sortino: **PROHIBIDOS**. No abrir holdout **7Y sellado**, ni usar resultado futuro o PnL para elegir parámetros; no tocar VPS, producción, DEMO/LIVE, ni hacer MERGE automático. Los PR permanecen DRAFT. Respetar licencias de raws cTrader (GitHub Actions artifacts, NO subir ticks licenciados al repositorio público).

**Regla de veredicto:** si falta fuente auténtica, firmas independientes, datos de ejecución, trazabilidad causal o freeze previo de Gates => NO_EVALUABLE / NOT_CERTIFIED; jamás inventar resultado GO. El trabajo debe avanzar sobre bloqueos verificables, no sobre maquillaje de métricas.

---

# 1. IDENTIDADES, CONTROL DE VERSIONES Y HERRAMIENTAS

| Frente | Rama / PR | Commit verificado ANTES de este R8 | Estado |
|---|---|---|---|
| A metodológico | agent/vt08-5m-methodology-source-20261010 / [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765) | 362e1914469e6c3fac957b1708eb29f18d89445b | OPEN, DRAFT, unmerged |
| B cognitivo | agent/vt08-5m-cognition-replay-20261010 / [PR #764](https://github.com/mezas3238-hue/qore-core/pull/764) | 457cfcab81c048a0bd6c23f82dde4fc700a85f8c | OPEN, DRAFT, unmerged |
| Investigación principal legado | [PR #634](https://github.com/mezas3238-hue/qore-core/pull/634) | revisar head al reanudar | No fusionar automáticamente |
| A coordinación | [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762) | comentarios R0–R7 | revisar y responder |
| B revisión independiente | [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763) | último mensaje A R7 #6196475774; último dictamen B R7 #6194093685 | A espera revisión semántica del R7 |
| Final-one-family antiguo | [issue #787](https://github.com/mezas3238-hue/qore-core/issues/787) | CLOSED / SUPERSEDED | **NO reabrir como si el ensayo fuera virgen** |
| QORE-alpha diferente | [issue #798](https://github.com/mezas3238-hue/qore-core/issues/798) | identidad separada | No fusionar reglas ni resultados |

**Datos fuente persistentes por historial de acciones:**
- [M3 real cTrader DEMO](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396): por mercado qore-vt08-m3-fractal-{MARKET}-bc1379d7661aac202495ec67afdd3098473ba723, archivo m3-evidence.json.
- [M15 original 1.095 días](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907): qore-vt08-cognitive-5m-fresh-{MARKET}-b2d33e1b4829d8b4afc76983decca8a99131403c, archivo market-evidence-1095d.json.
- Mercados congelados: EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD. Tiempos UTC en datos; Owner anclas NY 01/05/09 para marco H4 y max 1 fill/mercado/día NY. El censo M30/C2 explora intervalos NY 01–13 cada media hora: **otra población**, no igual a anclas Owner puntuales; verificar compatibilidad formal antes de usar para certificado.
- M1 BID/ASK: fuentes parciales en [QORE Native PR #849](https://github.com/mezas3238-hue/qore-core/pull/849) y [#851](https://github.com/mezas3238-hue/qore-core/pull/851); tres ventanas de aprox. 10 min separadas en 2020/2023/2026, no histórica continua de entradas/salidas; NZDUSD piloto aparte. **Existe BID/ASK auténtico parcial**; NO decir que no existe nada; **NO** decir que cubre los fills completos de VT08.
- [QORE Research Ultra Fast Runner](https://github.com/mezas3238-hue/qore-core/tree/research/qore-accelerator-5layers-ultrafast-20261013/src/qore/infrastructure/research_accelerator) está orientado a otro simulador CE LIMIT; **NO equivale** a la entrada VT08 C3 POS. Usar **Trader Lab** indexado para geometría y as-of con paridad, NO cambiar familia de órdenes para que corra más rápido.

**Artefactos Actions tienen retención temporal (a menudo 30 días).** Siguiente arquitecto: comprobar expiración, descargar y conservar dentro de políticas/licencias, verificar SHA del JSON canónico y SHA bytes originales. RUN SUCCESS por sí solo NO garantiza disponibilidad perpetua de bytes. Si algún artifact falta, reconstruirlo del raw custodiado; jamás adivinarlo.

---

# 2. MANDATO METODOLÓGICO CONGELADO (Y SU COLISIÓN HISTÓRICA)

La intención actual del Owner es **certificar VT08 por su metodología TTrades y cognitiva**, además de Gates económicos. NO convertir VT08 en investigación cuantitativa QORE-alpha sin identificar el cambio.

**Familia aislada para reconstrucción, NO trading autorizado:** M30 C2 bullish reversal sobre low relevante, confirmación CISD/Protected Swing M3 DENTRO C2, entrada POS al open de C3; cinco mercados congelados y máximo 1 fill/mkt/day NY. Un submodelo de TTrades, no todas las familias H4/M15/M5. No añadir short, LIMIT, retest arbitrario, filtros de wick%, ATR, 2R, mercados escogidos por PnL. El preregistro histórico está [aquí](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_FINAL_ONE_FAMILY_AUTHOR_FIDELITY_FROZEN_TRIAL_PREREG_2026-10-11.md) pero su ISSUE #787 está cerrado/superado: un sucesor debe redactar **acta nueva de identidad/versiones y política de muestra independiente** antes de hacer un «ensayo final». El censo DEV 2023–2026 ya se usó intensamente y no es un holdout virgen.

**Autoridad de reglas:** A = escrita por fuente primaria; B = inferencia reproducible documentada; C = formalización QORE explícita, no fuente; D = discrecional/indeterminada. OWNER_POLICY es contractual pero NO fuente TTrades. No elevar C/PROXY a A por pasar pytest; no seleccionar una regla D mirando el resultado económico.

**Fuentes TTrades utilizadas (leer sección original, no solo título):**
1. [Timeframe Alignment / Example 1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/): bias HTF -> estructura CISD -> entry LTF; long M30->M3, stop bajo EQ y breaker.
2. [Relevant Swings / Valid Separation](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/): pivote básico y relevancia contextual, **sin umbral numérico universal**; no confundir tres H1 cerradas con lookback tres HTF incluyendo vela actual.
3. [How to Use Equilibrium](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/): EQ de C2 distinto si close WITH vs AGAINST swing válido; referencia swing debe conocerse PRE-C2; rango C2 completo solo al cerrar.
4. [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/): bullish LOW→HIGH→LOWER LOW→HIGHER HIGH y zona up-close original; un patrón 4 M3 consecutivas es proxy C.
5. [Trading Breaker Blocks for Continuations](https://ttrades.com/trading-breaker-blocks-for-continuations/): continuation/retest es otra configuración, no convertir la entrada C3 POS en LIMIT.
6. [Only POIs that Matter](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/): para CONTINUATIONS desde protected swing hacia rango actual, prioridad por CLASE FVG > swing H/L > CISD retest; múltiples POI del mismo tier siguen D; NO generalizar a reversals universalmente.
7. [Price Targets Using Fractal Model](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/): long a previous HTF highs untouched; **sin desempate total único** entre varios highs.
8. [Positional Entries](https://ttrades.com/positional-entries-enter-before-the-expansion/): C3 OPEN solo cuando modelo previo, CISD/PS y cronología completos.
9. [4 Hour Power of 3](https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/): identidad HTF no intercambiable automáticamente con ejemplo M30.

**STOP obligatorio (ejemplo long):** source-verified reference swing PRE-C2, POI significativo, confirmación CISD/PS M3 completa antes de C3.open, EQ correcto según swing, breaker real con bar IDs, STOP debajo de **AMBOS** EQ M30 y breaker low, espacio FVG inferior si corresponde, HTF target precedente untouched y concretamente adjudicado, disciplina de 1/día. Condición necesaria SL < min(EQ, breaker_low); no prueba suficiente por sí sola y no aporta tick buffer o fill broker. Ninguna señal es SOURCE_COMPLETE si falta siquiera un selector obligatorio D.

---

# 3. TRABAJO REALIZADO ANTES DE ESTE CORTE: HITOS 10–14 OCT

### 3.1 Auditoría B01 y fuente M15, no economía
- B01 histórico sobre 5 mercados/1.095d: 11.655 anclas H4 -> 488 candidates -> 457 terminales de REPLAY legado. B comprobó 488/488 linajes M15 originales. Los 488 **NO** son fills auténticos nuevos ni 488 señales TTrades.
- C3/C4 timing: 294/294 geometrías y snapshots C4 validados físicamente; 213 Owner/81 no Owner; subsets solapados.
- FVG/CISD/PS proxies: B reconstruyó 495/495 receipts FVG/shape M15 reales, no significancia POI de autor, no trade.
- Módulos Situation, razonamiento WAIT/ABSTAIN/EXECUTE, hipótesis, memoria, relojes UTC/DST, políticas one-shot, recovery WAL y calidad ingenieril pasaron tests; **no** implican datos cognitivos de source-complete. Detalle heredado en handoff 14-Oct.
- Prototipo QORE M30/M3 PS-only económicamente NO-GO **para ese PROTOTIPO**: [run #38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903), 3.561 madres OHLC hipotéticas; PF bruto POS **0,964184**, PF bruto LIMIT **0,894996**, sensibilidad 0,10R hipotética PF POS ~0,781; DD POS bruto ~102,62R. **No representa TTrades fiel**, no tiene fills broker y no autoriza reoptimizar según ese PnL.
- Contrato de tres veredictos GO/NO_GO/NO_EVALUABLE y preregistro específico: código A vt08_a_final1_three_verdict_author_fidelity_gate_v1.py, tests. Endurecimiento fuentes URL exactas, rechazo NaN/Infinity, coherencia gross/expectancy, cruce de RuleReceipts de mercado/escenario/clock, EQ no observable antes C2.close; **34/34 pytest** CI [#38706949054](https://github.com/mezas3238-hue/qore-core/actions/runs/38706949054). Es validación de CONTRATO, no fills ni edge.

### 3.2 Gobernanza del proyecto y B
- B audita de forma independiente, sin confiar en productor A: [R4 93.230](https://github.com/mezas3238-hue/qore-core/actions/runs/38716419342) y [R7 88.276](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948).
- B añadió barrera para source_raw_market_map: los hashes SHA sin nombre de mercado podían mezclar mercados; restauró fail-closed por market y bar.market; cambios B R5, CI [#38717559918](https://github.com/mezas3238-hue/qore-core/actions/runs/38717559918). **SHA formato correcto no implica firma/verdad de mercado** sin raws.
- B tiene 27 CAUSAL_FIELDS en Vt08ForexSituationModel y vt08_b_situation_field_source_audit_v1.py. Ruta evaluate_provenanced() debe rechazar sin campos reales y semántica independiente; suite B 234 PASS/3 skipped de investigación, WAL 13 PASS y field audit 14 PASS en [#38715753360](https://github.com/mezas3238-hue/qore-core/actions/runs/38715753360). WAL SQLite fixture-only/restart fail-closed NO equivale a rehidratación completa real.
- B implementó **indexed fast geometry runner** con identidad estricta al auditor físico para los 93.230 C2, [CI #38740153019](https://github.com/mezas3238-hue/qore-core/actions/runs/38740153019). Tiempos 8,906s geometría indexada vs 32,751s auditor de alcance mayor; **NO** afirmar 3,68× full-pipeline, son cargas distintas.
- Último B R7 [run #38748150948](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948): **88.276/88.276 unique bar IDs**, **10.628 source groups**, **2.656/2.657 H1 anteriores completos**, 5/5 market PASS, Ruff/Mypy y 14 adversariales, contra RAW M3/M15. Primer intento #38748007526 FAIL en expectativa de texto del test, corregido y luego PASS. Dictamen B: DATA CUSTODY VERIFIED, SOURCE SEMANTICS NOT CERTIFIED.

---

# 4. TRABAJO DE ESTE ARQUITECTO A EL 15-OCT: CRONOLOGÍA REPRODUCIBLE

**IMPORTANTE:** los números de cada etapa pertenecen a universos distintos. NO sumar 11.650 anclas, 93.230 ventanas, 2.657 eventos, 88.276 bar IDs, 2.437 highs, 537 pivotes como «número de trades». La única familia activa utiliza decisiones C3 POS; nada de lo siguiente representa fills.

| Fase A | Archivo principal / entregable | CI REAL | Resultado y estado |
|---|---|---|---|
| R0 | vt08_a_final1_three_verdict_author_fidelity_gate_v1.py + tests | [#38706949054](https://github.com/mezas3238-hue/qore-core/actions/runs/38706949054) | 34 tests PASS: reglas URL, no NaN, market/scenario/clock, condición Stop; 0 AUTHOR fills |
| R1 | vt08_a_m30m3_raw_bar_custody_v1.py; manifiesto [source R2](VT08_A_NATIVE_SOURCE_CUSTODY_MANIFEST_R2_2026-10-15.json) | [#38710113768](https://github.com/mezas3238-hue/qore-core/actions/runs/38710113768) | 11.650 anclas NY 01/05/09; 11.639 completas, 11 faltantes, 0 mismatch M3/M15 completos; 5/5 PASS |
| R2 | vt08_a_ttrades_continuation_poi_priority_v1.py | [#38710818860](https://github.com/mezas3238-hue/qore-core/actions/runs/38710818860) | 45 PASS junto a gate A; FVG > swing > CISD solo continuation, ties D |
| R3 | vt08_a_m30m3_frozen_family_source_funnel_v1.py, [ledger de conteos](VT08_A_FROZEN_M30M3_BULLISH_FIRST_FAIL_COUNTS_2026-10-15.json) | [#38714800333](https://github.com/mezas3238-hue/qore-core/actions/runs/38714800333) | 93.230 C2 de cinco mercados: 2.657 UNIQUE proxy PS, 4.702 sin PS, 476 PS múltiples, 85.312 no C2, 83 gaps, 0 source-complete. Tope cronológico 1.987 mkt-days, no fills |
| R3+ | Contexto 3 H1 PRE-C2 desde 12 M15 + C1/C2 physical bar IDs | [#38715560333](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333) | 2.656 de 2.657 con H1 completo; único CADJPY ausente |
| R4 | vt08_a_b_market_custody_catalog_v1.py + tests | [#38740699499](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499) | Catálogos 2.657 casos, 88.276 bar IDs distintos dentro de cada mercado; mercado/SHA/reloj per bar, B auditó independientemente |
| R5 | vt08_a_source_conditional_eq_review_v1.py | [#38747954308](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308) | 2.657 C2 EQ_FULL y EQ_CLOSE_LOW condicionales reconstruidas de M3/M15, 9 adversariales/job, sin seleccionar swing ni EQ real |
| R6-target | vt08_a_h1_untouched_high_source_witness_v1.py | [#38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669) | 2.657; 220 con 1 high H1 fuente observable, 2.437 múltiples; 1.202 gaps/reset conservador; 5×11 tests |
| R6-swing | vt08_a_pre_c2_h1_basic_swing_source_witness_v1.py | [#38764229960](https://github.com/mezas3238-hue/qore-core/actions/runs/38764229960) | 2.657; 537 pivotes low básicos, 607 high, 42 simultáneos, 1 H1 incompleta; 5×8 tests. Relevance D |
| R7-join | vt08_a_blind_three_source_review_join_v1.py | [#38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497) | EQ+targets+swings enlazados con C2/C3/market, 2.657/2.657 preservados: 52 unique-target+pivot, 485 multi-target+pivot, 2.119 sin pivot en tres H1 previas, 1 H1 incompleta; 5×8 tests |

**Censos desagregados R3 y RAW B:** por mercado 18.646 C2. 83 faltantes, 85.312 no bullish single-low-sweep, 7.835 con C2 geométrica bullish, subdivididas por A en 4.702 NO M3 PS shape, 476 MULTI PS D, 2.657 UNIQUE PS SHAPE. Revisor B autenticó raws de todos los 2.657 y primera geometría M30 pero **NO detector PS/CISD autor**. No afirmar «2.657 CISD TTrades».

**Ventanas exactas de ancla Owner R1:** EURJPY 2328 completas/2 incompletas, USDCHF 2328/2, NZDUSD 2327/3, CADJPY 2328/2, USDCAD 2328/2; 0 discrepancias OHLC entre ventanas íntegras. 11 incidencias en tres instantes: 2024-01-05 14:00Z (todos, M3 14:09 y 14:12 ausentes), 2024-03-29 13:00Z (NZDUSD M3 13:06), 2026-06-15 09:00Z (todos M3 09:15..09:27 y M15 09:15). Ver manifiesto R2; no imputar.

**A R7 clasificación íntegra, incluidas negativas/ambiguas:**
| Mercado | Total R3 | H1 ausente | Sin pivot-low en 3 H1 ya cerradas | Pivot-low + HIGHs múltiples | Pivot-low + HIGH único |
|---|---:|---:|---:|---:|---:|
| EURJPY | 538 | 0 | 417 | 109 | 12 |
| USDCHF | 518 | 0 | 410 | 93 | 15 |
| NZDUSD | 550 | 0 | 452 | 91 | 7 |
| CADJPY | 516 | 1 | 417 | 89 | 9 |
| USDCAD | 535 | 0 | 423 | 103 | 9 |
| TOTAL | 2657 | 1 | 2119 | 485 | 52 |

**Clave de interpretación:** los 52 son **casos prioritarios para inspección ciega**, NO 52 operaciones ni filtro aprobado. Los 2.119 sin pivot en solo esa ventana no se pueden descartar como NO-GO autor: la ventana de 3 H1 previas completas es una formalización conservadora QORE-C, mientras el artículo del autor menciona 3 HTF incluyendo vela actual y un rango contextual más amplio. Los 485 multi-target no se pueden resolver escogiendo el ganador futuro. Preservar población completa al auditar densidad.

---

# 5. INVENTARIO FÍSICO DE MÓDULOS (DÓNDE RETOMAR)

**Arquitecto A, todos en src/qore/infrastructure/trader_lab/:**
- vt08_a_final1_three_verdict_author_fidelity_gate_v1.py — gate de contrato, RuleReceipt para nueve componentes, GO/NO_GO/NO_EVALUABLE solo si se aporta prueba auténtica; no es detector de setups.
- vt08_a_m30m3_raw_bar_custody_v1.py — M30 desde diez M3 y dos M15, raw SHA, por-bar SHA, censo NY, reporte de gaps.
- vt08_a_ttrades_continuation_poi_priority_v1.py — prioridad de POI por clase restringida a continuation; empate sin regla D.
- vt08_a_m30m3_frozen_family_source_funnel_v1.py — primera falla, C1/C2 M30, M3 PS geometría proxy, todos los positivos antes de PnL, tres H1 PRE-C2; NO autor.
- vt08_a_b_market_custody_catalog_v1.py — catálogo canonical M3/M15 por mercado, 2.657 casos; checks raw SHA y bar ID, fields y clocks.
- vt08_a_source_conditional_eq_review_v1.py — EQ full vs EQ close→low condicional, con bar rehash; NO selecciona régimen.
- vt08_a_h1_untouched_high_source_witness_v1.py — máximos H1 fuente, touch vía high M15; cuarentena de gaps, no selector.
- vt08_a_pre_c2_h1_basic_swing_source_witness_v1.py — pivot H1 central estricto de 3 H1 PRE-C2; relevancia no definida.
- vt08_a_blind_three_source_review_join_v1.py — cruce total físico de EQ/target/pivot, B review classes; no metrics.

**Tests exactos:** tests/infrastructure/trader_lab/test_<nombre_módulo>.py para cada módulo, exceptuando correlación habitual. Ejecutar vía workflows homónimos enumerados en sección 4. NO correr órdenes ni leer el 7Y.

**Workflows A de esta ronda en .github/workflows/:**
- vt08-a-m30m3-native-raw-custody-source-only.yml
- vt08-a-frozen-m30m3-first-fail-source-census-v1.yml
- vt08-a-b-market-custody-catalog-v1.yml
- vt08-a-c2-conditional-eq-author-source-review-v1.yml
- vt08-a-h1-untouched-target-native-source-census.yml
- vt08-a-h1-basic-swing-source-witness-v1.yml
- vt08-a-blind-three-source-review-join-v1.yml
- vt08-final1-three-verdict-source-gate-v1.yml

**Arquitecto B, en su rama (NO aún integrados a A sin manifest):**
- vt08_b_r3_frozen_source_independent_v1.py — auditor independiente C2 M30.
- vt08_b_r3_indexed_ultrafast_runner_v1.py — geometría indexada, paridad con auditor.
- vt08_b_a_catalog_independent_verifier_v1.py — verificador RAW de 88.276 source bars.
- vt08_b_situation_field_source_audit_v1.py — 27 fields con reloj/custodia/source class.
- vt08_b_durable_cognitive_research_ledger_v1.py — SQLite WAL fixture/research, no rehidratación prod.
- vt08_cognitive_5m_consumed_gate_v1.py / vt08_5m_a_to_b_candidate_readiness_v1.py — fail closed y convenios de B01 vs M30.
- Vt08ForexSituationModel y vt08_cognitive_5m_research_scope.py — contrato Situation/cutoff.

**Documentos de este corte:** R0 [A source-first](VT08_A_SOURCE_FIRST_RESTART_AUTHORITY_AND_B_REVIEW_CONTRACT_2026-10-15.md), R2 [bar custody](VT08_A_NATIVE_M30M3_SOURCE_CUSTODY_AND_B_BLIND_ANNOTATION_R2_2026-10-15.md), R3 [funnel](VT08_A_R3_FROZEN_BULLISH_M30M3_FULL_SOURCE_CANDIDATE_CENSUS_AND_B_PROOF_PACKAGE_2026-10-15.md), R4 [catalog/UltraFast](VT08_A_R4_B_MARKET_CUSTODY_CATALOG_AND_ULTRAFAST_ROUTING_2026-10-15.md), R5 [EQ](VT08_A_R5_CONDITIONAL_EQ_REVIEW_AND_BREAKER_TARGET_SOURCE_ADJUDICATION_2026-10-15.md), R6 [targets](VT08_A_R6_H1_UNTOUCHED_TARGET_PHYSICAL_CENSUS_AND_B_BLIND_REVIEW_2026-10-15.md), R7 [blind join](VT08_A_R7_THREE_SOURCE_BLIND_REVIEW_52_PHYSICAL_UNIQUE_CONTEXTS_2026-10-15.md). Consultar cada SHA y artifacts desde esos informes.

---

# 6. REGISTRO DE PROBLEMAS REALES, GRAVEDAD Y SOLUCIÓN PROPUESTA

| ID | Sev | Fallo o ambigüedad comprobada | Qué se corrigió y QUÉ SIGUE FALTANDO |
|---|---|---|---|
| P0-01 | BLOCKER | **Swing RELEVANTE previo a C2 indeterminado.** Basic 3-H1 pivot ≠ valid separation contextual; el autor NO fija threshold. | A implementó geometría estricta, 537 low pivots; B debe revisar con texto/vídeo primario, contexto/liquidez y doble anotación independiente. Si no replicable => D_UNSPECIFIED/NO_ESPECIFICABLE, sin trade. |
| P0-02 | BLOCKER | **POI significativo no autenticado; 2+ FVG/OB/swing posibles.** Prioridad FVG>swing>CISD del artículo corresponde solo a continuation. | Código prioridad de clase fail closed. Falta regla de POI para ESTA reversal + elección causal + rechazo explícito de múltiples no resueltos, sin RR/pips heurísticos disfrazados de autor. |
| P0-03 | BLOCKER | **PS/CISD M3 es PROXY**: 2.657 únicos geométricos comprobados físicamente; B no ha auditado su identidad semántica TTrades. 476 múltiple PS D. | Reconstruir serie opuesta, CLOSED-over-OPEN, protected swing auténtico con IDs, confirmación <= C2.close y conducta ante múltiples. Revisión B desde raw M3, NO confiar en flags A. |
| P0-04 | BLOCKER | **Breaker bullish exacto sin identidad**. 4 velas consecutivas/PS-only son PROXY, no fuente. | Exigir LOW→HIGH→LOWER LOW→HIGHER HIGH con IDs y tiempos, zona velas up-close, confirmar higher high antes C3, escoger breaker low por regla escrita; sin ella STOP prohibido. |
| P0-05 | BLOCKER | **EQ condicionado a swing D**. Fórmulas verificables pero no elegibles aún; usar C2 final antes de cierre sería FUTURE. | R5 calcula ambas desde barras reales; B tiene que adjudicar swing PRE-C2 y regime WITH/AGAINST antes de fijar precio EQ; no seleccionar por PnL. |
| P0-06 | BLOCKER | **Target HTF untouched no tiene desempate.** 2.437 de 2.657 tienen varios H1 highs físicos aún no tocados en segmento; 220 uno. | R6 enumeró H1 y touch; B debe elegir pertinencia de high, fuente timeframe, swing/source history y tie-break del autor. Si no hay, D; NO nearest/2R/best TP posterior. |
| P0-07 | BLOCKER | **R7 52 casos review son selector C restringido** (3 H1 PRE-C2) y no equivalen a tres HTF con actual del autor; sesgo de muestra si se mide solo 52. | Usar 52 para revisión de claridad de fuente + negativos/ambiguos estratificados; conservar los 2.657 en censo y futuros denominadores, no optimizar. |
| P0-08 | BLOCKER | **Sin 27+ Situation fields auténticos**. Los bar IDs (88.276 verificados) no son valores semánticos. | Diseñar derivación por campo, bar lineage/raw SHA/market/cutoff A/B/C/D; B verify_all_field_receipts e evaluate_provenanced por ruta REAL; UNKNOWN/AMBIGUOUS=>WAIT/ABSTAIN. No autorizar con un booleano. |
| P0-09 | BLOCKER | **APPROVED_A_B_MANIFEST_SHA256=None**; no revisión fuente semántica A+B ni firma. | Publicar frozen text-first spec y matriz dual reviewer; B debe reconstruir independientemente con bytes/raw, resolver disenso y firmar SHA únicamente cuando todas las reglas obligatorias sean A o C explícita bajo acta distinta. |
| P0-10 | BLOCKER | **BID/ASK y fees temporales insuficientes**. QORE Native 3×10min piloto no cubre stops/TP/outcomes. | Homologar pair alias, time, timezone, broker, BID/ASK, commission/swap/slippage y full trade lifecycle. Sin cobertura => NO_EVALUABLE, nunca usar spread/fees cero ficticios. |
| P0-11 | BLOCKER | **Gates NO congelados**. Legados VT08 PF>=1.80, DD<=6R, MC p95 DD<=15R, MC P(positive)>=0.90, mean R>=0; FINAL1 #787 cerrado PF net>1.15/100 fills/positive expectancy; Sharpe/Sortino/densidad sin threshold actual aprobado. | Owner/gobernanza versionar umbrales completos PRE-OOS, definición DD R vs DD% sin sizing, MAR y retorno de referencia, annualización y calendario, no combinar criterios incompatibles sin acta. |
| P0-12 | BLOCKER | **No validación independiente OOS nueva** y 7Y sellado. DEV 2023–2026 consumido por C2/pivot/target. | Freeze modelo + A/B + Gates + datos + hash; obtención de muestra OOS no vista/autorizada; abrir 7Y SOLO con gobernanza formal futura, no durante desarrollo. |
| P0-13 | BLOCKER | **No fills económicos auténticos / stop-out lifecycle**. 0 signals fuente completas. | Integrar engine faithful C3 POS, bid/ask, simultaneidad, stop-first conservador con ticks auténticos, no-fill, TP/SL y expiry; Pareado A-only vs A+B mismos eventos/quotes/costes. |
| P1-01 | HIGH | **Gaps raw M3/M15 Owner**: 11 incompletas en 3 anclas; 1 CADJPY sin H1. | IDs y relojes exactos en manifiesto; investigar proveedor/calendar, no imputar. Auditar continuidad por mercado/huso/DST. |
| P1-02 | HIGH | **R6 untouched H1 resetea en cualquier gap M15, incluso cierres semanales**. La inferencia «untouched» vale solo por segmento. | Modelar calendarios FX/closure verificables, cuarentena de intervalos y cobertura por high origin; no ampliar historial a través de huecos suponiendo ausencia de operaciones. Conteo de 1.202 resets NO equivale a 1.202 errores de broker. |
| P1-03 | HIGH | **R6 registra H1 high completo hasta C3; puede incluir H1 formada DENTRO de C2**. Aunque nivel estaba as-of C3, eso NO lo hace automáticamente «previous higher-timeframe target» según la familia. | B exigir high origin H1 verdaderamente anterior al contexto definido del autor; diferenciar target qualified pre-C2 vs newly confirmed at C3; revisar H1 boundary y fair opportunity. Nunca seleccionar por éxito. |
| P1-04 | HIGH | **Tres H1 PRE-C2 cerradas es QORE-C conservador, no especificación exhaustiva del autor**. 2.119 «no pivot» pueden tener swing real a otra escala o actual parcial. | Diseñar as-of snapshots de H1 actual y lookback contextual SOURCE, probar ausencia de future y no reinterpretar geometría negativa como NO-GO. |
| P1-05 | HIGH | **Solo SOURCE OHLC M15/M3 de broker DEMO, tick/ASK y fees discontinuos**. La autenticidad del SHA source no acredita cuenta/contrato/spread futuro. | Contrato broker específico, revisiones quotes coherentes y cadena raw; no coberturas agregadas de otros mercados. |
| P1-06 | HIGH | **Engine UltraFast QORE Research simula CE LIMIT, no VT08 POS C3**, cambio silencioso de estrategia si se reutiliza. | Usar indexed Trader Lab para geometría; antes de mover simulator, prueba diferencial EXACTA trades/no-fills/stop order vs referencia fiel C3 POS, sin observar PnL para elegir. |
| P1-07 | HIGH | **Persistencia WAL B fixture-only** y rehidratación/kill state real pendiente. | Reproducción after restart, idempotencia, dedupe global fill_id en ruta authenticated real, degradar/ABSTAIN si WAL falla; separar permisos de ejecución. |
| P1-08 | HIGH | **Artifacts Actions caducan y raws licenciados no deben exponerse**. | Preservar SHA/pointers y ubicación autorizada, backup cifrado/legal, reproducibilidad en runners, no copiar material protegido al public git. |
| P1-09 | HIGH | **Cobertura de test NO equivale a cobertura de fuente**. Tests sintéticos pueden pasar con 0 entradas auténticas. | B evaluar tasa false-positive/false-negative de semántica contra anotación humana ciega y casos negativos, sin optimización PnL. |
| P1-10 | HIGH | **Historias B01 M15, H4 C3/C4, FINAL1 M30/M3 y QORE-alpha coexistentes**; riesgo de cruzar linajes/timestamps/código. | Source family_id + version + market + scenario + profile + source_clock, manifest per family y no merges accidentales. |
| P2-01 | MEDIUM | **Pruebas transitorias FAIL antes PASS** (lint E501, import unused, fixture close OHLC inválido; test B R7 assertion prematura). | Se corrigieron en nuevas CI verdes (A #38765076497; B #38748150948). Conservar enlaces a fails, repetir suites desde HEAD, no ocultar historial. |
| P2-02 | MEDIUM | **Métricas de velocidad comparadas en runners de distinto alcance**. | Reportar 8,906s indexado y 32,751s auditor amplio como tiempos de tareas distintas; benchmark same-output y same-hardware antes de reclamar factor speedup. |
| P2-03 | MEDIUM | **C2 single-low-sweep físico vs barrido low significativo**. En 93.230 C2, 7.835 shapes C2 -> no significa POI/liq relevante. | No usar forma low < previous C1.low como sustituto del swing/source target; inspección adversarial. |

**Notas de ingeniería de seguridad ya arregladas (no reabrir):** URLs TTrades incorrectas en RuleReceipt; SHA formal sin igualdad de escenario/mercado; NaN/Infinity/loss ledger falsamente GO; C2 EQ prematuro; cruzar feeds SHA de distintos símbolos; falso source_complete en B01; perfil H1_PRE_C2 sintético sin canonical M15; cache mutable cognitiva; TZ DST ambiguo; WAL commits fuera de orden. Mantener pruebas adversariales de regresión para todos ellos.

---

# 7. REPRODUCIBILIDAD: ORDEN DE EJECUCIÓN Y CONTRATOS

**Primeras lecturas** obligatorias del sucesor, SIN PnL:
1. Este R8 + handoff 14-Oct + A R7 y B R7.
2. Ramas A/B HEADs, PR #765/#764 e issues #762/#763 y sus comentarios después del corte. Confirmar si B hizo adjudicación del R7.
3. Fuente TTrades primaria ligada a cada regla y prerregistro del 11-Oct con etiqueta CLOSED/SUPERSEDED; no importar estrategia QORE-alpha.
4. Manifiesto raw [source R2](VT08_A_NATIVE_SOURCE_CUSTODY_MANIFEST_R2_2026-10-15.json) y ledger counts [C2 R3](VT08_A_FROZEN_M30M3_BULLISH_FIRST_FAIL_COUNTS_2026-10-15.json); SHA raw M3/M15 exactos.

**Secuencia de GitHub Actions, orden de dependencias (NO mezclar artifact-SHA de otro run):**
- Fuente native 1095d M3 #35941643396 / M15 #35934924907.
- Auditar anclas R2 #38710113768; primer filtro R3 #38714800333; R3+ H1 #38715560333.
- A market catalog #38740699499 -> B independent R7 #38748150948.
- A C2 EQ #38747954308 + A H1 target #38763309669 + A preC2 3-H1 pivot #38764229960 -> A triple-source join #38765076497. Usar exactamente JSON y SHA reportados en esos workflows; el join emite **los 2.657 casos**, y ellos sirven a B para revisión.
- B indexed geometry #38740153019 sirve al índice rápido de 93.230 C2, no reemplaza verificador raw; equivalencia exacta por stage es requisito.
- Registrar cualquier nueva variante SOURCE (si se autoriza) ANTES de mirar outcomes, pasar A/B independent field audit, luego economía.

**Cinco artefactos finales A R7 de 30 días** (JSON cross-source, NO datos de trading):
| Mercado | A R7 artifact ID | SHA256 sobre JSON canónico, no ZIP |
|---|---|---|
| EURJPY | [11987661905](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11987661905) | 65718734b9120ca6cefbf17800e0ecb5dcfc5a6c17421753f3879003314c6c69 |
| USDCHF | [11988466184](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11988466184) | ac9457ca757e9253ae8bff37a29ef1be7742e3797a19c00f613efe08ed24eb6d |
| NZDUSD | [11987477069](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11987477069) | 6bbd8e9e6947e8979d69aa3d078274dfda401f50e75f6fe64bd00c282eebaa4b |
| CADJPY | [11987711676](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11987711676) | db91a50305127ea9bcf88cd3e7bb178eb6d932e53b7c1f462fa56d734dfd7279 |
| USDCAD | [11985939734](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11985939734) | 7875e7f0a8ed27d1b969f5437938636522739946f7757f5b525328212116e58a |

**No confiar en número 88.276 como número de velas M15 únicas universales:** es la suma de bar IDs únicos *por mercado* pertenecientes a los 2.657 contextos, e incluye M3 y M15 con repeticiones entre casos correctamente deduplicadas por hash dentro de mercado. Más barras del corpus bruto total pueden existir.

---

# 8. PLAN DE TRABAJO EJECUTABLE PARA EL PRÓXIMO ARQUITECTO

## Paso 1 — Reconciliar identidad/preregistro y fuente textual ANTES de PnL [P0, A+Owner]
Construir acta versionada «VT08 metodología original / M30→M3 C2 LONG→C3 POS» con universo, fechas de datos DEV, HOLDOUT permitido y condiciones de parada. Registrar #787 CLOSED y PF bruto 0.964 del prototipo PS-only como negativos de otras implementaciones, jamás resucitar por tuning. Congelar source citation por regla y separar A/B/C/D.

**Done si:** spec describe causalmente WHAT, WHEN, WHO, SAME_EVIDENCE, y excluye filtros post-outcome. Si source relevante no se deja especificar => D/no-especificable; NO-GO epistemológico legítimo.

## Paso 2 — Resolver en serio relevant swing/POI y breaker/target [P0 A+B]
Usar 52 ejemplos ciegos para discutir estructura con pocos niveles, más muestras cronológicas estratificadas de 485 multi-target, 2.119 no-pivot y caso CADJPY incompleto; luego adjudicar la totalidad necesaria sin escoger ganadores. Exigir para swing: marco, bar IDs izquierda/centro/derecha, qualified_at pre-C2, separación, contextual liquidity, rater1/rater2/disenso. Para breaker: 4 hitos ordenados con bar IDs, up-close candle(s), breaker-low observable. Para POI: categoría, score de relevancia **si fuente lo autoriza**, conflict resolution y timestamp. Para target: source high original/untouched desde historia completa y tie-break explícito. Clasificar lo irresoluble AMBIGUOUS_D y STOP, no añadir 2R.

**Done si:** cada operador podría repetir selección ANTES de mirar C3 futuro en fuente y los revisores concuerdan, o se declara no-especificable.

## Paso 3 — PS/CISD, reloj y final1 source gate [P0 A]
B reimplementar independencia M3: opposing series, CLOSE cruza OPEN, PS protegido y temporalidad completa <= C3.open. El módulo A RuleReceipt debe recibir manifest físico auténtico, misma familia+mercado+escenario+C1/C2/C3/timestamps, y stop debajo EQ y breaker de identidad adjudicada. Prohibido mezclar recibos sintéticos de diferentes oportunidades. Prioridad de POI continuation NO reemplaza regla de reversal.

**Done si:** 100% candidate decisions de la cohorte congelada son reproducibles y su false-negative audit contiene los negativos; no simplemente «todos PASS» dentro de un subconjunto.

## Paso 4 — Conectar campo a campo la cognitiva B [P0 B]
Crear Situation de cada verdadera CandidateEvent validado con 27 CAUSAL_FIELDS, tipo, source SHA/market, bar_ids, qualified_at<=cutoff, Authority A/B/C/D, hipótesis y memoria UNKNOWN cuando corresponda. Ejecutar evaluate_provenanced() con B verificando independentemente; ABSTAIN/WAIT para ausencias y contradicciones. Verificar WAL con reinicios y kill real; A-only vs A+B deben operar **mismas señales y mismas fechas**.

**Done si:** manifest A+B legítimamente firmado, campo por campo B PASS y ninguna señal CON D entra a economía.

## Paso 5 — Fijar Gates y datos de broker [P0 Owner+Auditor de riesgos]
Owner debe versionar contrato de métricas PF net, R expectancy, DD R y si DD % medible con unidad homogénea (NO sizing dinámico), Sharpe, Sortino, MAR, anualización, densidad, MC p95 DD, P(beneficio), límites por mercado/mes/estacionalidad, costos, missing/no fills, holdout y STOP. Resolver explícitamente legado PF 1.80 vs FINAL1 #787 1.15 CERRADO antes de consultar OOS. Adquirir o identificar 3Y BID/ASK/fees pertinentes y verdaderamente independientes. No asumir que tres snapshots Native por año son histórico completo.

**Done si:** gate_manifest_sha versionado y PRICE/QUOTE manifest con fuente, cuenta, contrato, ticks completos de entry/SL/TP, coste y slippage preestablecidos.

## Paso 6 — Ejecutar economía fiel, compare A-only vs A+B [P0 Auditor económico]
En Trader Lab/runner con paridad exacta ejecutar C3 OPEN market order POS y no-fill, stop y target definidos pretrade, comisiones/ticks, 1R unitario fijo sin lotaje/apalancamiento variables. Para A-only y A+B misma calendarización, quotes, spread y slippage. Reportar TRADE LEDGER por mercado/fecha con source SHA, fecha, side, BID/ASK, stop/tgt, fill/exit, outcome R y razón de abstención. Exigir que el OOS no haya informado el desarrollo; cuando sea autorizado por gobernanza, UNA apertura del holdout sellado (no en esta etapa).

**Done si:** resultados numéricos NET reproducibles, intervalos incertidumbre, equity/R curve, PF/DD/Sortino/Sharpe y robustez MC, por mercado y global, prueba independiente de costes; luego PASS/FAIL/NO_EVALUABLE con firma real de auditor/Owner.

## Paso 7 — Habilitación solo tras certificación integral
No confundir GO de investigación con LIVE. El despliegue requerirá autoridad adicional y controles independientes de runtime/riesgo; no tocar CIBO sizing para certificación.

---

# 9. ENTREGABLES CONCRETOS ABIERTOS Y COMUNICACIÓN A/B

**Del Arquitecto A al B:** nuevo paquete R7 con 2.657 casos y claves market|C2.open|C3.open; 52 indicados para revisión cualitativa prioritaria, 485 multi high, 2.119 sin pivot en ventana QORE-C, 1 gap. Fuente TTrades e invariantes de reloj; UNKNOWN hasta revisión de relevancia. Está enviado a [issue B #763, comentario #6196475774](https://github.com/mezas3238-hue/qore-core/issues/763#issuecomment-6196475774). Los informes R4/R5/R6 previos también están en comentarios; responder con resultados que B pueda reproducir, no con «GO» sintético.

**Pendiente de B:** dictamen fuente semántica R5–R7 (no solo RAW), verificación independiente de EQ arithmetic vs selected regime, target high untouched y lookback, relevancia del swing, POI y breaker; matriz de 27 campos por cada Signal candidate autorizado, autenticación a la entrada cognitiva y recuperación WAL real. Esperar comentario y verificar HEAD B antes de nuevas decisiones; B R7 previo solo autorizó custodia física.

**Pendiente de gobernanza/Owner:** identidad de nuevo ensayo (tras #787 CLOSED) y umbrales numéricos firmados PRE-OOS, cobertura costo/feed histórico, control de acceso al 7Y sellado. Prohibición invariable de sizing.

**Pendiente de investigación:** si TTrades es demasiado discrecional y no especificable en esta familia, documentar frontera: IMPLEMENTACIÓN QORE-C explícita puede ser una estrategia DIFERENTE con prerregistro y test propio, **no** certificado de fidelidad TTrades. No «resolver» un D variando ATR/pips hasta que PF mejore.

---

# 10. GUÍA DE SEGURIDAD CONTRA ERRORES RECURRENTES

1. **CI PASS ≠ edge.** Un test de igualdad de barras no predice fill ni rentabilidad.
2. **88.276 bar IDs ≠ 88.276 trades; 2.657 geometrías ≠ fills; 52 casos contextuales ≠ estrategia rentable.**
3. **Fórmula EQ correcta ≠ régimen EQ autenticado.** Swing anterior y C2.close reloj separados.
4. **Un high H1 intacto en segmento sin huecos ≠ target relevante TTrades.** El origen H1 debe existir antes del instante que autorice su utilización; cuidado cuando H1 se cierra coincidiendo con C3.open.
5. **Un pivot H1 de tres H1 PRE-C2 ≠ Relevant Swing.** El autor permite contexto y separación discrecional.
6. **Stop < EQ y breaker ≠ stop fuente si breaker_low es proxy.**
7. **Ticks parciales BID/ASK ≠ todos los fills de 1.095 días.**
8. **QC cognitiva/SQLite WAL fixture ≠ SITUATION REAL ni durable production guarantee.**
9. **#787 CLOSED ≠ nueva autorización de un ensayo «final»; ni su PF 1.15 reemplaza a todos los Gates VT08.**
10. **Una rama GitHub actualizada no significa merge ni runtime modificado.**
11. **No usar sizing, capital compuesto, leverage ni riesgo variable para rescatar DD/Sharpe.**
12. **Nunca abrir 7Y sellado para depurar metodología, entrenar cognitiva, elegir mercado o mirar edge.**

---

# 11. CRITERIO PARA CONSIDERAR ESTE HANDOFF COMPLETO

Este documento es un corte verificable de continuidad: identifica los dos arquitectos, su HEAD, las fuentes originales, todos los nuevos módulos de A, trabajos B, dataset y artifacts, censo de calidad, TODOS los bloqueos P0/P1/P2 conocidos, resultados negativos auténticos y los pasos concretos antes de certificar.

**NO afirma certificación de VT08**. El siguiente arquitecto recibe suficiente contexto para seguir el trabajo desde la prioridad P0: adjudicar Relevant Swing pre-C2 / POI / PS-CISD / breaker / target y permitir que B valide la cognitiva de verdaderas señales. Solo posteriormente corresponde exigir los Gates económicos del Owner con datos BID/ASK reales y OOS gobernado. 

**Fin del checkpoint R8.**

---

## APÉNDICE OWNER — EXCLUSIÓN ABSOLUTA QORE-ALPHA (15-oct-2026; prevalece sobre propuestas anteriores)

**Instrucción explícita del Owner:** «Qore alpha quedó excluido del programa por ende no puede mezclarse con el vt08 actual».

- **ÚNICO PROGRAMA PERMITIDO: VT08 actual**, metodología TTrades adjudicada + cognitiva VT08 propia; no hay dos tracks autorizados, ni `VT08-QORE-ALPHA`, ni metodologías derivadas/importadas de QORE-alpha. Queda retirada cualquier sugerencia anterior de segunda vía, incluso la contenida en una versión antigua del informe B R15. **NO mezclar reglas, señales, POI, features cognitivas, resultados o estadísticas alpha con VT08.**
- **Contrato de alcance vigente en esta rama:** [VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md](VT08_OWNER_SCOPE_CURRENT_ONLY_NO_QORE_ALPHA_2026-10-15.md).
- **B corrigió su informe R15** y añadió auditoría [R16](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R16_OWNER_QORE_ALPHA_EXCLUSION_SOURCE_SCOPE_AUDIT_2026-10-15.md), [CI #38805194446](https://github.com/mezas3238-hue/qore-core/actions/runs/38805194446) **5/5 SUCCESS, 170 pruebas adversariales y los 2.657 candidatos originales VT08 source-only**. No equivale a certificar metodología, cognitiva, beneficios ni impedir automáticamente todas las importaciones futuras de software: integrar el guard R16 en los siguientes manifest/admissions antes de certificar sigue pendiente P0.
- **Cuando falte regla original:** `D_PENDING_SOURCE_AUTHORITY` / `WAIT` y no entrada; no introducir una ruta excluida para «salvar» un Gate. No sizing, no PnL selection, holdout sellado 7Y intacto, no VPS/LIVE/DEMO y sin merge.
- **Corte real:** 0 señales TTrades source-complete, 0 admisiones cognitivas auténticas, 0 fills; PF/DD/Sortino/Sharpe no evaluables y VT08 aún NO CERTIFICADO.

**Este apéndice prevalece sobre cualquier recomendación contradictoria histórica de investigación o DeepSeek y debe transmitirse textualmente al siguiente arquitecto.**


---

## APÉNDICE R17 — ÚLTIMO DICTAMEN DEEPSEEK (15-oct-2026)

**Fuente independiente B R17:** [Ocho ambigüedades, análisis textual y acciones A+B](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R17_DEEPSEEK_V4_OCHO_AMBIGUEDADES_DICTAMEN_FINAL_SOURCE_FIRST_2026-10-15.md); commit `2146c5748ade4ce1f42d4f1b8d88fcb6f533112e`. El texto completo contrasta páginas primarias del autor (Relevant Swings, EQ del 10-oct-2026, Protected Swing/CISD, Timeframe Alignment Example1 M30→M3, Breaker, POI para Continuations, Target).

**Correcciones innegociables:** una ventana de 3 HTF con vela actual NO equivale a pivote ya confirmado de tres cierres; POI que existe != POI con reacción CISD != POI elegido; FVG→swing→CISD documentado para continuaciones posteriores al Protected Swing NO es jerarquía universal para reversión previa; EQ C2 es condicional al swing de referencia real; breaker tiene swings y up-close source, NO 4 velas M3 consecutivas automáticamente; en Example1 el stop se ubica bajo EQ M30 Y breaker low, aunque PS sea la referencia estructural general de positional. Target untouched/jerarquía HTF, buffer y CISD cualitativo siguen sin regla decisora universal.

**P0 A:** producir fichas causales source para swing, POI pre-CISD, PS/serie opuesta, breaker high/low y objetivo HTF, con bar_ids, TF, hora de disponibilidad y ambigüedad D. **P0 B:** doble revisión independiente ciega pre-PnL sobre muestras realmente ambiguas, sellar el denominador 2.657, auditar toda futura señal positiva vs raw nativo; jamás convertir el 2.657 geométrico en 2.657 TTrades válidos por decreto.

**Owner R16:** QORE-alpha EXCLUIDO enteramente del programa VT08; no segundo track ni importaciones de esa estrategia. No sizing ni 7Y holdout ni operaciones ni merge.

`R17_DOCUMENTARY_SOURCE_ADJUDICATION_ONLY` · `AUTHOR_COMPLETE=0` · `COGNITIVE_REAL_ADMISSIONS=0` · `BROKER_FILLS=0` · `ECONOMIC_GATES=NOT_EVALUABLE` · VT08 **NO CERTIFICADO**.


---

## APÉNDICE R18/R19 — POI PRE-CISD ORIGINAL (16-oct-2026)

**Nuevo resultado B R18:** [informe fuente nativa de 2.657 eventos](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R18_PRE_CISD_H1_POI_NATIVE_CAUSAL_CENSUS_2026-10-16.md), [GitHub Actions #38902918264](https://github.com/mezas3238-hue/qore-core/actions/runs/38902918264) 5/5 GREEN, 80 tests, cTrader M15+M3 por ID y hora. Inventario cerrado de últimas **tres H1 totalmente cerradas ANTES de C2**. 574 FVG físicos H1 (290 bullish/284 bearish); 165 bullish FVG primer contacto **antes de la barra M3 CISD**; 4 primer contacto en esa barra sin ordenar ticks, 20 después, 382 no tocados. 1.694 con al menos un low previo H1 tocado pre-CISD; 1 CADJPY upstream H1 incompleta y en cuarentena. **Estos hechos NO autentican el POI significativo según autor.** Por caso hay source H1/M15 bar IDs y primer touchdown M3 `source_bar_id`, cutoff, fase y firmas de autor falsas explícitamente descartadas.

**Nuevo entregable B R19:** [107 fichas outcome-blind (A+B) por SHA](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_B_R19_PREREGISTERED_BLIND_POI_DUAL_REVIEW_QUEUE_2026-10-16.md), [GitHub Actions #38903529731](https://github.com/mezas3238-hue/qore-core/actions/runs/38903529731) 5/5 GREEN, 40 adversariales. Muestra determinista pre-PnL: 50 FVG bullish pre-CISD, 50 controles sin FVG de las últimas 3 H1, 4 primero en barra CISD, 3 FVG bearish antes CISD. **0 revisiones A firmadas, 0 B firmadas**, 0 fuente completa. Auditor A tiene que clasificar source swing/POI/PS verdaderos por caso; B debe revisar independientemente fuente raw y disenso; D=>WAIT. La muestra no es nuevo denominador económico: permanecen 2.657 físicos originales.

**Restricciones Owner ya vigentes**: VT08 actual EXCLUSIVO, QORE-alpha totalmente excluido, NO sizing, NO 7Y sellado, NO operaciones/merge; 27 `CAUSAL_FIELDS` sin semántica auténtica, `AUTHOR_COMPLETE=0`, `COGNITIVE_ADMISSIONS=0`, `BROKER_FILLS=0`, `GATES=NOT_EVALUABLE` y VT08 **NO CERTIFICADO**.

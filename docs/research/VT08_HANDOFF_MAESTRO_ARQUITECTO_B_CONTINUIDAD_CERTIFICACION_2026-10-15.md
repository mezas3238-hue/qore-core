# QORE CORE — VT08 | HANDOFF MAESTRO DEFINITIVO DE CONTINUIDAD (ARQUITECTO B)
**Corte investigado:** 15-oct-2026 · **Alcance:** Metodología TTrades original, cognitiva VT08 y Gates de certificación económica.  
**Propósito:** entregar TODO el contexto, código, resultados, problemas, decisiones irrevocables y pasos reproducibles al siguiente arquitecto.  
**Veredicto global al corte:** **VT08 NO CERTIFICADO**. Investigación de datos auténticos muy avanzada; semántica metodológica, admisión cognitiva genuina y resultados económicos siguen bloqueados.

## 0. Lee esto antes de cualquier prueba (restricciones Owner)
- Se certifica la **metodología VT08 y su cognitiva**, no una estrategia cuantitativa sustituta. Además debe aprobar PF, Drawdown, Sharpe, Sortino, expectativa, OOS, Monte Carlo, robustez y los demás Gates aplicables.
- **PROHIBIDO SIZING para certificar**: ni lotaje dinámico, ni leverage, ni compounding, ni ponderación de mercados o CIBO que transforme artificialmente PF/DD. Se pueden evaluar retornos homogéneos en unidades de **1R** definidas ex ante, nunca escalar el capital para rescatar resultados.
- **PROHIBIDO** usar VPS/LIVE/DEMO operativo/FundedNext, colocar órdenes, merge, abrir o reaprovechar el holdout de **7 años sellado**, modificar políticas de producción, inventar BID/ASK/fees/fills, seleccionar sólo ganadores o reabrir tests cerrados. Las credenciales DEMO cTrader que originaron los datos de histórico se utilizaron en adquisición histórica, **no** son permiso para operar.
- Cualquier D metodológica esencial que no se resuelva debe reportarse `NO_ESPECIFICABLE` o `NO_EVALUABLE`; no crear una regla nueva y llamarla TTrades. Code green no constituye licencia económica o de ejecución.
- **No extrapolar** los experimentos de VT31, CRT PURE, QORE Native ni QORE-alpha a VT08. Son identidades y ramas distintas. Ramas #764 y #765 siguen DRAFT y sin fusionar.

## 1. Repositorios, roles, versiones, fuentes de verdad
**Repositorio:** https://github.com/mezas3238-hue/qore-core

| Componente | Fuente concreta | Estado |
|---|---|---|
| **Arquitecto B**, cognitiva, verificaciones independientes, barreras | [PR #764](https://github.com/mezas3238-hue/qore-core/pull/764), rama `agent/vt08-5m-cognition-replay-20261010`, [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763) | DRAFT, source/economics fail-closed. HEAD antes de ESTE documento: `457cfcab81c048a0bd6c23f82dde4fc700a85f8c` |
| **Arquitecto A**, método, corpus TTrades, datos fuente y CandidateEvent | [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), rama `agent/vt08-5m-methodology-source-20261010`, [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762) | DRAFT. Último HEAD consultado: `362e1914469e6c3fac957b1708eb29f18d89445b`; volver a leer antes de desarrollar |
| Programa origen 5 mercados | [PR #634](https://github.com/mezas3238-hue/qore-core/pull/634) | otro frente de investigación, no merge automático |
| Ensayo final de una familia #787 | [issue #787](https://github.com/mezas3238-hue/qore-core/issues/787) | cerrado/superado; sus umbrales no reemplazan certificación global |
| QORE-alpha | [issue #798](https://github.com/mezas3238-hue/qore-core/issues/798) | otra identidad, sin traslado de Gates |
| Handoff histórico EXTENSO anterior | [VT08 handoff 14-oct, 38 KB](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_HANDOFF_MAESTRO_CERTIFICACION_METODOLOGICA_COGNITIVA_GATES_2026-10-14.md) | fuente retrospectiva de 488 B01, 294 C3, 495 FVG/CISD y auditorías cognitivas de principio de mes; ESTE handoff añade rondas R1–R8 |

**Alcance Owner actual:** 5 mercados EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD. Anclas H4 Owner 01/05/09 hora Nueva York; 13NY puede figurar en material de artículos, **no** es ancla Owner. Máximo una operación filled por mercado por día NY salvo nueva orden. Una ventana M30 C2 de 01:30–12:30 NY **no equivale a** una ancla H4 Owner 01/05/09: jamás mezclar los dos censos, ni inferir trades de C2.

### Fuente primaria metodológica
Referencias originales: TTrades *Relevant Swings* (21-mar-2026); *Equilibrium / Fractal Model* (10-oct-2026); *Timeframe Alignment* (30-jul-2025); *Breaker Blocks Simplified* (05-jul-2025); *Continuation Breaker* (03-ago-2025); *Price Targets* (23-may-2026); *Positional Entries*; *4 Hour Power of Three*. A mantiene matriz de URLs, apartados y citas breves. **No basta una URL o SHA en un JSON para demostrar relevancia correcta de un swing concreto.**

**Autoridad semántica por regla:** A = autor fuente primaria; B = inferencia documentada; C = formalización propia QORE, NO atribuible al autor; D = discrecionalidad/no resuelto. OWNER_POLICY distinto de SOURCE_A. Una estrategia inspirada en TTrades y llamada QORE-alpha exige identidad diferente y nuevo prerregistro, nunca falso PASS VT08.

## 2. Mapa de universos. No sumarlos ni llamarlos trades
| Universo | Conteo/evidencia | Qué ES | Qué NO ES |
|---|---:|---|---|
| B01 anterior H4/M15 | 11.655 anclas → 488 candidatos → 457 terminales en una implementación vieja | reconstrucción de aquella familia; CI B #38095654032 verificó 488 linajes | fills certificados del contrato nuevo |
| C3 y C4 pasado | 294 snapshots, 294/294 físicamente reconstruidos, CI B #38098119759 | evidencia física de geometría y relojes | 294 trades nuevos |
| Familia estrecha FVG/CISD M15 pasada | 495 recibos reconstruidos B, CI #38103539460 | source shape y proxies físicos | 495 setups autor válidos |
| Owner NY anclas exactas R2 | **11.650 observadas / 11.639 completas / 11 incompletas**; 0 OHLC mismatch | census RAW M3/M15 independiente B de anclas 01/05/09, [CI #38713809585](https://github.com/mezas3238-hue/qore-core/actions/runs/38713809585) 5/5 | fills, ni universo de 93.230 C2 |
| **Familia congelada M30 bullish C2→M3→C3 POS** | **93.230 ventanas C2**, [B R4 CI #38716419342](https://github.com/mezas3238-hue/qore-core/actions/runs/38716419342) 5/5 | 18.646 C2 de cada uno de cinco mercados, filtrado geométrico SIN PnL | 93.230 oportunidades ejecutables |
| Filtro bullish C2 | 83 incompletas, 0 mismatch, 85.312 sin geometría bullish single-low sweep, **7.835** geometría físicamente compatible | primer corte determinista; B recomputó del raw | validación PS/CISD original |
| Clasificación posterior de A | 4.702 sin forma PS, 476 múltiples PS proxy, **2.657** únicos PS proxy | clasificación A sobre los 7.835, positivos fuente físicamente revalidados B | B aún NO reimplementó independientemente el detector PS como semántica TTrades |
| Custodia física R7 | **88.276 source_bar_id** únicos dentro de mercado, **10.628 grupos C1/C2/H1** y **2.657** eventos positivos cotejados con A R3 | source OHLC/UTC/SHA comprobado B, [CI #38748150948](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948) 5/5 | decisiones cognitivas auténticas/fills |
| H1 precierre físico | 2.656 con 12×M15 PRE-C2; 1 CADJPY incompleto | contexto factual cerrado; no imputar faltante | swing relevante por definición del autor |
| EQ condicional B R8 | 2.657 `EQ_FULL=(H+L)/2` y 2.657 `EQ_CLOSE_LOW=(C+L)/2` matemáticamente verificados | ambos candidatos físicos; se auditaron offline ZIPs R4/R5 | selección de régimen EQ, target o stop |

**R8, matiz de evidencia:** auditoría **OFFLINE** B con [registro issue #763](https://github.com/mezas3238-hue/qore-core/issues/763#issuecomment-6196142170), entregables de esta conversación `VT08_B_R8_INDEPENDENT_EQ_AUDIT_2026-10-15.json` y `vt08_b_r8_independent_eq_audit.py` bajo `/mnt/data` (no alojados en GitHub al corte, retener/copiar por vía aprobada). Se cotejaron hashes JSON canónicos contra informe A; hubo **2.576** casos donde ambos EQ difieren numéricamente, **0** EQ autor seleccionados; una manipulación artificial de EQ se rechazó aun recalculando el SHA del reporte. **NO anunciar CI nueva o commit GitHub R8.**

## 3. Datos originales: localización y restaurabilidad
- cTrader 1.095d M15 por mercado: [Actions run #35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), patrón `qore-vt08-cognitive-5m-fresh-{MARKET}-b2d33e1b4829d8b4afc76983decca8a99131403c`, archivo `market-evidence-1095d.json`.
- cTrader 1.095d M3 por mercado: [run #35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396), patrón `qore-vt08-m3-fractal-{MARKET}-bc1379d7661aac202495ec67afdd3098473ba723`, `m3-evidence.json`.
- R3 source completo y recibos 2.657: [A Actions #38715560333](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333), SHA A `394116f13449fc310d7fbc5f0b5f60aa1bb247d4`, artefactos `vt08-a-frozen-m30m3-firstfail-{MARKET}-{SHA}`.
- R4 catálogo con IDs bar y market mapping: [A Actions #38740699499](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499), SHA A `f61b5e7a931e2c057a0660f4702f11d55ebc58af`, `vt08-a-b-market-catalog-{MARKET}-{SHA}`. 5 artifacts documentados por mercado en reporte A R4.
- EQ R5 (ambas ramas): [A Actions #38747954308](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308), artifacts `vt08-a-author-conditional-eq-{MARKET}-57a6fa70f8a14ff26a6249b39d1f3e4725aa0a4c`.
- **CUIDADO:** esos artefactos GH Actions tienen retención usual de 30 días (hasta ~14-nov-2026 los nuevos). Antes de expiración, asegurar backup/restaurabilidad con hash, bajo licencias del broker y acceso adecuado. NO commitear feeds privados al repo público, no alterar SHA ni consultar el holdout sellado.


## 4. Arquitecto B: trabajos implementados y pruebas técnicas verificadas

### 4.1 Metodología histórica, auditoría causales y prohibición de falso source
- Auditorías B antiguas 488 candidatos B01 M15; 294 C3/C4; 495 source geometrías FVG/CISD/PS, siempre comparadas con raws donde estuvieron disponibles. Véase **handoff maestro 14-Oct** sección 2 para la taxonomía exacta de los subconjuntos, pruebas M15, bloques PS y discrepancias metodológicas. No sumar esos universos entre sí ni a la familia congelada R3 M30/M3.
- Fuente TTrades C2 EQ: referencia swing válida **antes de C2.open**; C2 full-candle contra close-to-extremo depende de WITH/AGAINST. C3.full es conocible al C3.close, NO al comienzo. Antiguas pruebas de lectura causal B protegieron C3 in-progress, C4 primera barra y bloquearon uso de future high/low.
- `src/qore/infrastructure/trader_lab/vt08_5m_a_to_b_candidate_readiness_v1.py`: gate que inspecciona CandidateEvent de A, autoridad, SHA/identidad, reloj, perfil y cutoffs. Problema antiguo A: `H4_OPEN_EXACT_FILL_QORE_CONTAINMENT`, stop PS-only, TP fijo 2R y cierre next H4 se marcaban falsamente `SOURCE_COMPLETE_EXECUTABLE`. B lo bloqueó con `A_B:NON_SOURCE_CONTAINMENT_BUNDLE`; A corrigió productor en su rama para etiquetar `SOURCE_INCOMPLETE_QORE_CONTAINMENT`. Jamás quitar esta guardia por un hash de 64 caracteres.
- `src/qore/infrastructure/trader_lab/vt08_5m_b_methodology_spec_boundary_v1.py`: contrato independiente de especificación textual por familia/rol con reglas A/B/C/D, source URLs y cutoffs, además de preflight; no concede firma conjunta. Si existe una regla D decisiva para entry/stop/target, no hay `SOURCE_COMPLETE`.
- **Manifest:** `APPROVED_A_B_MANIFEST_SHA256 = None` **al corte** en readiness. Ningún SHA auto-declarado por A, B o tests reemplaza un acuerdo A+B formal e independiente.

### 4.2 Cognitiva y orquestación de cinco mercados
- `src/qore/infrastructure/traders/vt08_cognitive_5m_research_scope.py`: `Vt08FiveMarketResearchSituation` extiende `Vt08ForexSituationModel`, mantiene **exactamente 27 `CAUSAL_FIELDS`** de procedencia y timestamps individuales ordenados. Se obliga `latest_available_bar_close = max(feature_cutoffs)`, sin barras futuras, sin `terminal_pnl` ni etiquetas post-outcome. Cinco mercados y memoria `UNKNOWN_NOT_BOUND`; jamás reutilizar calibración de otro mercado o trader.
- `src/qore/infrastructure/traders/vt08_cognitive_orchestrator.py`, `vt08_cognitive_hypothesis.py`, `vt08_cognitive_position_intelligence.py` y contratos: razonamiento determinista/metacognición/adversarial, `WAIT/ABSTAIN/EXECUTE` en investigación y Journey/Position post-fill. Testing sintético no autoriza trades.
- `src/qore/infrastructure/trader_lab/vt08_cognitive_5m_consumed_gate_v1.py`: gate B sobrio, **`evaluate(situation)` fixture-only** exige `fixture_mode=True`. `evaluate_provenanced()` en modo normal exige CandidateEvent coherente, autoridad A/B, valores y tiempos, pruebas per-field; como aún falta semántica autenticada, **falla cerrado**. Fills, terminal y Position en modo normal están prohibidos hasta API de broker real verificada. No convertir `EXECUTE` de una fixture en orden.
- Freeze de identidad de evento y ciclo, no doble ejecución, timestamps monotónicos, caducidad H4, `ABSTAIN` killed, fill/terminal lineage. En posición, **SL/TP inicial congelado** al primer snapshot y stop observado jamás puede ampliarse long/short dentro de research; ese primer snapshot todavía NO prueba condiciones originales de broker.
- `src/qore/infrastructure/trader_lab/vt08_b_durable_cognitive_research_ledger_v1.py`: WAL SQLite transactional `BEGIN IMMEDIATE`, `synchronous=FULL`, cadena SHA, deduplicación idempotente, fill-id único, kills/terminal tombstone, source/time drifts y prueba de corrupción. **Integrado al gate solo en fixture mode**: commit al WAL antes de mutación de RAM, falla de escritura => no cambio de decisión. Tras restart los eventos previos **no se rearman**, pero todavía **NO existe rehidratación completa verificada del estado cognitivo**, ni WAL de fills reales. Hay que construirla antes de admitir actividad real.
- `src/qore/infrastructure/trader_lab/vt08_b_situation_field_source_audit_v1.py`: compara los 27 valores del Situation con SHA payload por campo, `source_bar_id`, `source_raw_sha256`, `source_raw_market_map`, OHLC, `available_at`, `feature_cutoffs`, perfiles y `market`. Rechaza mezcla de fuentes entre mercados. **Valida clocks y consistencia**, NO que el POI, swing o CISD TTrades interpretado sea correcto. El resultado `source_semantics_certified=False` impide bypass.

**CI cognitiva:**
- [#38714909676](https://github.com/mezas3238-hue/qore-core/actions/runs/38714909676): 13 tests WAL e integración, 234 tests generales PASS, 3 tests A congelados PASS, Ruff/Mypy. 3 saltos de la suite general están cubiertos separadamente por la integración A.
- [#38715753360](https://github.com/mezas3238-hue/qore-core/actions/runs/38715753360): 14 source-field adversariales, 13 WAL, 234 generales PASS/3 SKIP y 3 integración A PASS, Ruff/Mypy.
- R5 cross-market raw custody gate [#38717559918](https://github.com/mezas3238-hue/qore-core/actions/runs/38717559918) SUCCESS. Es una validación de límites, NO un fill.
- **Limitación:** los tres tests de integración A congelados se fijaron a una antigua base B01 M15; **no acreditan** la familia nueva R3 M30/M3. Revisar disparadores, branches y SHAs al sincronizar contrato.

### 4.3 Auditoría independiente de RAW y mejora Trader Lab
- `vt08_5m_b_independent_raw_receipts_v1.py`: algoritmo B separado del productor A, confirma barras físicas individuales y M30 agregado M3×10 vs M15×2; valida raw bytes, bar ID, OHLC, UTC `available_at`. Inicialmente **120 M30 windows** muestras, con 1.200 M3 +240 M15 fuente revalidadas; CI [#38710263808](https://github.com/mezas3238-hue/qore-core/actions/runs/38710263808) 5/5. Luego se extendió al censo de **11.650 anclas Owner** completas/incompletas, CI #38713809585.
- `vt08_b_r3_frozen_source_independent_v1.py`: **recuenta TODOS 93.230 C2**, exige primer filtro de geometría y reconstruye 2.657 recibos positivos C1/C2/H1 físicamente contra RAW, sin importar PS detector de A; run [#38716419342](https://github.com/mezas3238-hue/qore-core/actions/runs/38716419342) 5/5 SUCCESS.
- `vt08_b_r3_indexed_ultrafast_runner_v1.py`: acelerador específico VT08 en Trader Lab, indexa M30 causal y comparte caché entre ventanas, usa validación **diferencial EXACTA** contra verificador B R3. [CI #38740153019](https://github.com/mezas3238-hue/qore-core/actions/runs/38740153019) 5/5 PASS, 93.230 C2 igualdad sin desviación. Geometría indexada tomó por mercado ~1,5–2,0 s; auditor completo con recibos/H1 ~5,6–7,6 s. **No son workloads idénticos; prohibido anunciar aceleración global 3,68× sin benchmark justo.** No reutilizar el simulador CE LIMIT de QORE Accelerator como motor de órdenes C3 POS; sí aprovechar indexado/asof si conserva paridad.
- `vt08_b_a_catalog_independent_verifier_v1.py`: coteja catálogos A R4 **cada uno de 88.276 bar IDs** y **10.628 grupos** físicos contra fuentes RAW cTrader y los 2.657 eventos R3. Pruebas adversariales de SHA falso, mercado cruzado, grupos mezclados, C2 duplicado, H1 incorrecto, barras huérfanas y claims de profit. CI [#38748150948](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948) 5/5 PASS, Ruff/Mypy/14 tests por job; [reporte B R7](VT08_B_R7_INDEPENDENT_PHYSICAL_MARKET_CATALOG_88276_BAR_AUDIT_2026-10-15.md).
- Historia del fallo de QA R7: en run previo #38748007526 un test sintético esperaba `source_bar_id invalid`, pero la comprobación **anterior** de raw OHLC detectó correctamente la adulteración. Se cambió **solo** la aserción de error esperado; segunda ejecución verde. No esconder runs rojos intermedios y no relajar controles para conseguir verde.
- **R8 offline** en artefactos GitHub originales: comprobó 2.657/2.657 `EQ_FULL` y 2.657/2.657 `EQ_CLOSE_LOW`, M3/M15 coincidentes y 1 H1 incompleto. 2.576 precios de ramas distintos; hash-only no basta (tamper EQ detectado). No se generó commit/CI de R8 en GitHub; [issue #763 comentario](https://github.com/mezas3238-hue/qore-core/issues/763#issuecomment-6196142170) y JSON/script locales respaldan resultados.

### 4.4 Problemas corregidos en B, por tipo
| Defecto identificado | Corrección implementada | Riesgo que sigue |
|---|---|---|
| Fuente A B01 ocultaba `QORE_CONTAINMENT` bajo source-complete | rechazo en B, rectificación status de A | source nueva R3 sigue incompleta |
| Falsificar `evaluate()` con Situation sin raw | fixture explícito + normal exige `evaluate_provenanced()` | no stream verdadero source-complete |
| `side`, `NY date`, `anchor`, perfil y cutoffs no conciliados | envelope/Situation field binding + raw-market map | semántica fuente aún no justificada |
| WAV/WAL inexistente, crash y doble fill de tests | WAL idempotente/atómico, hash chain y guardias de restart | no rehidratación cognitiva completa ni validación de broker |
| SL o TP inicial podía cambiar durante Journey | freeze desde primer snapshot, stop monotónico | snapshot original no autentica terms externos |
| Proxy FVG/CISD/PS confundido con método autor | etiquetas de proxy, `source_semantics_certified=False` | source-author POI/swing/PS siguen D |
| Cruce de markets por conjunto de SHA global | `source_raw_market_map` y comprobación cruzada | falta validar feed de quotes de ejecución |
| El censo A podía muestrear sólo positivos favorables | B recuenta 93.230; compara 2.657 *TODOS* los positivos | negativos por detector PS A no reimplementados independientemente |
| Candidato tras C2 miraba H1 o C3 futuro | controles `C2.open`, `C3.open`, `closed_at/available_at` | author relevance exige juicio sobre barras permitidas |

## 5. Resultados de Arquitecto A que el sucesor debe considerar (no son firma B)
### A R3 — familia M30/M3 congelada (fuente geométrica)
[A R3](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R3_FROZEN_BULLISH_M30M3_FULL_SOURCE_CANDIDATE_CENSUS_AND_B_PROOF_PACKAGE_2026-10-15.md) / Actions #38715560333, full-census y 2.657 recibos. B revalidó geometría y todos positivos R4. El método NO es final: PS es C-QORE geometric precursor.

### A R4 — catálogo físico por mercado
[A R4](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R4_B_MARKET_CUSTODY_CATALOG_AND_ULTRAFAST_ROUTING_2026-10-15.md) / #38740699499 5/5. Canonical M3/M15 `source_bar_id`, market-specific raw SHA, grupos H1. **Fue verificado B R7**.

### A R5 — EQ condicional
[A R5](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R5_CONDITIONAL_EQ_REVIEW_AND_BREAKER_TARGET_SOURCE_ADJUDICATION_2026-10-15.md) / #38747954308 5/5. Ambas fórmulas de EQ verificadas **offline B R8**, sin selección por swing TTrades.

### A R6 — censo H1 TARGET «untouched», NUEVO posterior a B R8
[A R6](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R6_H1_UNTOUCHED_TARGET_PHYSICAL_CENSUS_AND_B_BLIND_REVIEW_2026-10-15.md) / [#38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669) 5/5 A. En 2.657 contextos, **220 con EXACTAMENTE un anterior H1 high físicamente no tocado, 2.437 con varios, 0 sin H1 highs** bajo el algoritmo de segmentos continuos; 1.202 discontinuidades M15 que causan reset prudente (pueden ser cierres del mercado normales). A reconstruyó H1 de 4×M15, desactiva high cuando posterior M15 `high >= level` antes de C3. **B aún NO ha auditado independientemente todos los highs/touches del run R6**. Incluso con high único no demuestra que sea HTF author target válido.

### A R7 — tres fuentes pre-PnL, pivotes H1 físicos y join
[A R7](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R7_THREE_SOURCE_BLIND_REVIEW_52_PHYSICAL_UNIQUE_CONTEXTS_2026-10-15.md), [Actions #38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497) 5/5 PASS **solo de A**. Integra R5 EQ, R6 H1 untouched highs y pivote H1 PRE-C2 [#38764229960](https://github.com/mezas3238-hue/qore-core/actions/runs/38764229960), sin salida ni PnL. 2.657/2.657 preservados:
| Mercado | H1 incompleto | Sin pivot LOW en 3 H1 cerradas | Pivot LOW + múltiples highs | Pivot LOW + único high | TOTAL |
|---|---:|---:|---:|---:|---:|
| EURJPY | 0 | 417 | 109 | 12 | 538 |
| USDCHF | 0 | 410 | 93 | 15 | 518 |
| NZDUSD | 0 | 452 | 91 | 7 | 550 |
| CADJPY | 1 | 417 | 89 | 9 | 516 |
| USDCAD | 0 | 423 | 103 | 9 | 535 |
| **Total** | **1** | **2.119** | **485** | **52** | **2.657** |

- Los **52** son geometría básica de H1 pivot-low + UN único high no tocado. **0 de ellos son trades**. La relevancia H1 TTrades del autor requiere **valid separation cualitativa**, no hay fórmula universal. El artículo original habla de tres HTF incluyendo vela actual, mientras A R7 usa tres H1 COMPLETAMENTE cerradas PRE-C2; no son ventanas equivalentes ni puede excluirse los 2.119 por falta de pivot en esta ventana.
- Los **485** tienen pivote LOW geométrico y MÁS DE UN high candidato; el desempate HTF sigue D. Los **2.119** sin pivot LOW básico no son author-invalid; hay que revisar jerarquías HTF/ventanas antes de clasificar.
- **R7 de A no tiene revalidación independiente B de su triple-join ni de los 220/2.437 highs** al momento de este handoff. No confundir run A verde con firma A+B.
- Cinco artefactos R7: EURJPY #11987661905, USDCHF #11988466184, NZDUSD #11987477069, CADJPY #11987711676, USDCAD #11985939734 en run #38765076497; los SHA JSON canónicos y expiry están en el informe A R7. No muestrear sólo los 52 para la economía y dejar fuera el resto de los 2.657 sin fallo/ambigüedad declarado.

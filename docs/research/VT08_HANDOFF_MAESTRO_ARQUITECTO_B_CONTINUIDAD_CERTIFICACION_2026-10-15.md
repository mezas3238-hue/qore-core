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


## 6. TODOS los problemas no resueltos y cómo resolverlos, por prioridad

### P0. Bloqueos de metodología, fuente y selección (Arquitecto A, verificación B)
1. **Swing relevante PRE-C2 sin definición causal reproducible.** No basta pivot-low central de tres H1 ni simple mínimo rolling. Según TTrades se requieren pivote y separación/relevancia contextual; no existe umbral numérico universal. A debe entregar `relevant_swing_id`, timeframe, extremos, barras izquierda/derecha YA CERRADAS, `qualified_at < C2.open`, explicación contextual y cita primaria. B debe verificar que no haya *future-bar/lookahead* y emitir `VALID/INVALID/AMBIGUOUS_D`. Si no es especificable y esencial, `NO_ESPECIFICABLE`.
2. **Desacople de ventanas H4 Owner vs M30 source.** H4 anchors NY 01/05/09 no equivalen automáticamente a C2 M30 NY 01–13. A debe demostrar pertenencia al H4 ciclo congelado y máximo un fill/día/mercado; no reinterpretar 93.230 C2 como 11.650 anclas ni saltar entre perfiles M3/M15 por PnL.
3. **Fidelidad CISD/PS M3.** Detector A clasifica 4.702 no shape, 476 múltiple, 2.657 único en los 7.835 bullish C2. B verificó físicamente los positivos, **no** semántica del detector ni falsos negativos. Exigir serie opuesta, cruce **OPEN** confirmado por cierre, protected swing PS y barra `confirmed_at <= C3.open`; documentar disputa frente a fuente autor. Probar negativos/adversariales, no solo 2.657.
4. **POI/tie-break author no documentado para esta familia bullish reversal.** Prioridad FVG > swings > CISD que el autor describe para **continuation** NO se aplica por defecto a **reversal**. Distinguir M30 C2 reversal, M3 CISD/PS y entrada positional C3.open de un retest breaker o CE LIMIT. Para dos POIs plausibles, no elegir mejor PnL; D hasta prueba primaria.
5. **EQ condicional correcto, selector ausente.** R8 demuestra ambas fórmulas pero no dirección WITH/AGAINST respecto a *swing previo autenticado*. Regla `EQ_FULL=(H+L)/2` si swing bullish válido y C2 cierra A FAVOR; `EQ_CLOSE_LOW=(C+L)/2` bajo rama CONTRA; no inferir WITH solo por cuerpo C2 bullish. Exigir `selected_eq` nulo hasta sentencia A+B. Revisar otros contextos bearish sólo con nueva familia prerregistrada.
6. **Breaker legítimo ausente.** Secuencia bullish LOW→HIGH→LOWER LOW→HIGHER HIGH, con zona up-close previa al lower low, orden real de bar IDs y confirmaciones antes C3.open; NO 4 velas M3 consecutivas imaginarias ni low del PS-only como sustituto. Varios breakers = D con casos adversariales.
7. **Stop de autor y costes del tick.** Stop long debe quedar estrictamente **bajo el EQ autenticado Y el breaker low**; FVG room y buffer si fuente lo exige. No firmar stop inexistente ni TP fijo 2R. El precio ejecutable ASK/BID y tamaño mínimo tick deben venir de especificación broker, no inferirse del OHLC mid. Sizing prohibido; SL es condición necesaria de método, no estrategia para arreglar DD.
8. **HTF target untouched no adjudicado.** A R6 da 220 únicos y 2.437 múltiples highs de H1 físicamente no tocados; no equivale a relevancia del autor ni target sell-side alcanzable. B debe recrear independently continuidad de M15, tocar `high >= level`, reset ante gaps, 4 M15 por H1, `known_at`, `untouched_as_of=C3.open`; revisar cada caso múltiple sin ordenar por `nearest/rr/reached_later` si la fuente no prescribe orden.
9. **Cierre de universo de reglas antes de PnL.** Prohibido ampliar familias, seleccionar anclas/pares, añadir confluencias o ajustar thresholds tras mirar ganancias. La vieja familia QORE M30/M3 fue falsada. Registrar nuevo `SOURCE_SPEC_VERSION` y universo congelado/fecha con aceptación de A+B y Owner antes de OOS legítimo.
10. **Autenticidad de referencia verbal/video del autor.** Cita primaria, URL, sección, fecha, screenshots/frames si preciso, procedencia del ejemplo, excepciones y no-equivalencia de reglas B/C. El código A no es validación independiente ni la coincidencia de un HASH prueba interpretación correcta.

### P0. Bloqueos cognitivos y seguridad de software (Arquitecto B)
11. **27 `CAUSAL_FIELDS` reales sin valores justificados.** Data catalog A contiene barras, no `bias_state`, `poi_state`, `cisd_state`, `scenario_state`, `exhaustion_state`, etc. reales. Por CADA field requerir `value`, `value_sha256`, `source_bar_ids`, `source_rule_ref`, `semantic_class A/B/C/D`, cutoff, market, M3/M15 raw SHA. Nunca pasar una Situation inventada con `methodology_valid=True`. Prueba adversarial futuro, drift, falsos PS, mezcla de par y fuente/valor.
12. **Firma conjunta inexistente.** `APPROVED_A_B_MANIFEST_SHA256=None`; además del SHA deben existir revisiones A y B independientes con versión de contrato/split, fuente de los campos y arbitraje de desacuerdos. Nunca cambiarlo a SHA de fixture ni decidir desde el código del productor. B no puede auto-firmarse por A o por el Owner.
13. **No hay CandidateEvent R3 source-complete en `evaluate_provenanced`.** La ruta B01 M15 legacy es otra familia. A debe construir envelopes M30/M3 POS autor fieles + los 27 campos; B debe validar identidades, secuencias WAIT/ABSTAIN/EXECUTE, reloj C2.close y expiración H4, en la misma población prerregistrada. Real EXECUTE autorizado actualmente = 0.
14. **WAL no restaura hipótesis ni memoria completa.** WAL está integrado en fixtures con fail-closed on restart; falta snapshot/replay de hashes de knowledge/adversarial/metacognition, posición, fill, terminal y market-day cap, más atomicidad multi-proceso, chequeo replay y firmas. No usar rearm en producción solo por disponer de una tabla SQLite.
15. **In-trade cognitiva no conectada a barras completas fuente y broker fills.** Journey/Position necesita actualización cada bar elegible posterior al fill, stop/TP congelados por broker, fill_id de BID/ASK y trazabilidad de propuestas vs acción externa realmente ejecutada. No confundir `EXIT` cognitivo con fill terminal.
16. **Autoridad Risk/CIBO/independent no delegada.** Los gates cognitivos no pueden conceder `broker_order_authorized=True`, demo o funded. Revisiones económicas y regulatorias externas solo después de evidencias completas y firma competente.

### P0. Bloqueos económicos, de muestras, robustez y gobernanza
17. **No hay trades económicos fuente-autorizados.** En la nueva familia R3 `source_complete=0`, `real_cognitive_admissions=0`, `verified_fills=0` y `PF/Sortino/Sharpe/Drawdown=NOT_MEASURED`. No sustituir por 2.657 precursores, por 52 casos físicos o por los 457 terminales legacy.
18. **BID/ASK, comisión, stop/target/entry y lifecycle no homologados.** Se necesitan quotes con timestamp/bar/tick/fuente/broker, matching a todos los eventos de entrada/sl/tp, fees y spread/slippage/swap verificables, tratamiento de no-fill, gap y stops; no interpolar a mano ni poner cost=0. Los manifiestos QORE Research CE LIMIT y USTEC partial no son el modelo VT08 positional C3 en 5 FX.
19. **PNL y metodología-only vs metodología+cognitiva A/B pareados.** Misma fuente, identidad de candidato, clock, lotaje conceptual 1R fijo, costes y reglas author; analizar rechazo cognitivo/WAIT, evitar selección por resultados posteriores, reportar efecto causal de cognitiva y densidad/turnover. No optimizar usando Sortino de muestras pseudo.
20. **Gates numéricos con historia conflictiva.** Certificación VT08 histórica PF≥1,80, MaxDD≤6R, mean R≥0, MC 95p DD≤15R, MC P(terminal positivo)≥0,90; trial cerrado #787 PF NET>1,15 con ≥100 fills (no es Gate general); QORE-alpha otra identidad. Sharpe, Sortino, DD%, densidad, definición de período no trade, split WFO y umbral estadístico requieren freeze versión Owner **antes de cualquier OOS**. No elegir los umbrales fáciles después de resultados.
21. **Densidad insuficiente/selección no legitimada.** Los 52 casos «pivot + single high» son una clase de revisión humana sugerida, NO una estrategia prefiltrada apta para certificar por sí sola. Conservar denominador 2.657, 485 ambiguos, 2.119 sin pivot de 3 H1, una falta CADJPY, y clasificar D excluido solo con criterio previo al outcome.
22. **Falsación económica de PROTOTIPO previo.** A QORE M30→M3 del 11-Oct: 3.561 candidatas, PF positional bruto **0,9642**, bajo coste hipotético 0,10R **0,7808**, PF limit CISD bruto **0,8950**, supuesto 0,10R **0,7729**, DD enorme; [run #38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903) y [reporte NO-GO](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_M30M3_ECONOMIC_FALSIFICATION_NO_GO_PROXY_REPORT_2026-10-11.md). **No rescatar/retunear** prototipo falsado. No prueba fracaso del TTrades original no reconstruido.
23. **OOS y holdout 7Y** sellado intocable. Necesidad de split genuinamente no visto, congelar reglas antes, auditoría de contaminación histórica, ventanas de stress y Monte Carlo dependiente. No asumir que el mismo histórico al que A/B ya miraron es OOS virgen.
24. **Conservación y licencia de datos:** GitHub Actions retiene artefactos temporalmente; se debe localizar almacenamiento canónico restaurable con hashes, contrato de licencia y control de acceso; no publicar ticks de broker privados en archivos Markdown/GitHub público. Los 1.202 resets del target son intervalos sin serie continua; muchos pueden ser fines de semana, no marcar automáticamente corrupción.
25. **Tres fases de evidencia distintas:** `SOURCE_RAW_VALID` (B R7 PASS), `SOURCE_METHOD_AUTHOR_VALID` (D), `ECONOMIC_PROFITABLE_AND_ROBUST` (NOT_EVALUABLE). Cambiar un status por otro es una falsificación de auditoría. Incorporar barreras de esquema/event contract y CI negativos.

## 7. Gate de certificación: criterios, umbrales y resultado real
**Pipeline canónico Trader Lab:** RESEARCH → REPLAY → FAST_FORWARD → OOS → STRESS → MONTE_CARLO → RISK_REVIEW → CIBO_REVIEW → INDEPENDENT_VALIDATION. Consulte [QORE-TRADER-LAB-001](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md); capacidad de lab/runner no equivale a autorización de broker.

| Gate | Requisito de entrada / aprobación | Estado al corte |
|---|---|---|
| DATOS - Original M3/M15 y mercado | Raw bytes SHA, perfiles cerrados, no future clocks, market binding, gaps explicitados | **PASS físico en la población R3**; B R7 |
| GEOMETRÍA / derivación EQ matemática | R4/ R8 data y formulas C2, solo algebra | **PASS parcial, no selección semántica** |
| M0 - Metodología autor | A/B texto y regla A real de swing, POI, EQ regime, PS, breaker, stop/target, journey, 1 fill/día | **BLOCKED** |
| C0 - Cognitiva fuente real | 27 field receipts genuinos, `evaluate_provenanced`, WAIT/ABSTAIN/EXECUTE+Journey, WAL recovery, fills/terminal auténticos, no leak | **RESEARCH FIXTURE CODE PASS / REAL BLOCKED** |
| X0 - Quotes/costes físicos | BID/ASK broker, fees, tick, fill/no-fill con chronology SL/TP, NET 1R | **NOT_EVALUABLE** |
| PF bruto y PF NET | fórmula suma ganancias / `abs(suma pérdidas)`; n=0 o denominador 0 no es infinito aprobado | **NOT_MEASURED** |
| Expectancy y riesgo | expectancy NET positiva; mean R>=0 según Gates históricos; serie 1R homogénea | **NOT_MEASURED** |
| DD observado R | DD <=6R legado; DD% si Owner define capital/curva nominal ex ante | **NOT_MEASURED** |
| MC DD y probabilidad beneficio | p95 DD <=15R; P(MC terminal positivo)>=0,90 en Gate legado, resample dependiente | **NOT_MEASURED** |
| Sharpe | returns periódicos netos, riesgo-free, frecuencia/anualización/vol0 y umbral Owner VERSIONADO | **NUMERIC_FREEZE_PENDING / NOT_MEASURED** |
| Sortino | returns periódicos vs MAR, down-deviation definida sobre períodos y 0down=undefined; threshold Owner | **NUMERIC_FREEZE_PENDING / NOT_MEASURED** |
| Densidad/power/WFO/OOS | total fills por market-NY-day/año, muestra eficaz, splits auténticos, robustez por era, mercados y anclas | **PENDING** |
| Risk/CIBO/Independent | firmas externas, sin lotaje adaptativo para certificar, autoridad fuera del gate B | **BLOCKED** |

**NO HAY PF/DRAWDOWN/SORTINO APROBADOS PARA VT08 R3.** En especial, no inferir rentabilidad de código PASS ni de datos correctos. La rentabilidad pasada bajo un prototipo irrelevante no acredita ni desacredita la implementación original aún incompleta.

## 8. Playbook del sucesor, secuencia óptima y condiciones de parada

### Fase 0 — Reanudar, sin perder estado ni repetir tests
1. Abrir ESTE handoff, el del 14-Oct y R7 B; verificar HEAD de ambos PR, conflictos, issues #762/#763; confirmar que #787 siga cerrado, #798 sea otra estrategia. Nunca usar SHA vieja como HEAD actual sin inspección.
2. Leer los resultados de CI B #38748150948 (catálogo físico), #38740153019 (runner), #38716419342 (source C2) y #38715753360 (cognitiva). Repetir solo cuando cambie código o fuente; respetar data hashes y retención.
3. Inspeccionar [A R7](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_R7_THREE_SOURCE_BLIND_REVIEW_52_PHYSICAL_UNIQUE_CONTEXTS_2026-10-15.md) y sus cinco artefactos [#38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497) (SHA canónico en informe). Comprobar que branch A no haya avanzado de nuevo.
4. Conservar evidencia nueva como comentario y documento con run_id, commit, parámetros, mercados, hashes y límites. Mantener PR en DRAFT.

### Fase 1 — Verificación B independiente de NUEVO aporte A R6 y R7
5. Descargar R6 A [#38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669): 5 artefactos completos y raw M15 auténtico. Programar **oráculo B de targets untouched** sin importar algoritmo A: H1 a partir de 4 M15 previas contiguas, alto conocido al cierre, touch si posterior M15 high>=H1 high, reset gap; reloj `<=C3.open`. Verificar 220 únicos y 2.437 múltiples, 0 sin candidates; añadir ataques high igual, gap fin de semana, minuto/H1 roto, cross-market, DST y futuro. Dejar source target NOT_SELECTED.
6. Descargar R7 A [#38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497): recomputar SHA y unir con R5 EQ y R6 high por llave market+C2.open+C3.open; verificar 2.657/2.657 y buckets 1/2.119/485/52, pivot-low básico de 3 H1 previamente cerradas, origen bar IDs y timestamps. **No importar código A**. Rechazar claims `AUTHOR_VALID` automáticos.
7. Publicar R9 B **source-audit-only** en GitHub y coordinar diferencia con A en #762. Si la prueba física falla, conservar FAIL con el ejemplo mínimo que permita reproducirlo y no admitir semántica.

### Fase 2 — Adjudicación autor A/B (EL CUELLO DE BOTELLA)
8. Solicitar A entrega congelada de texto/evidencia por los mismos 2.657 source IDs. Sin datos de futuro/outcome. Revisar *al menos* los 52 «pivote + único high» **como grupo de inspección**, más negativos/ambiguos estratificados de los 485 y 2.119, **sin quitar ninguno del denominador**. A y B revisan por separado antes de reconciliar; B no puede «inventar un segundo firmante».
9. Por evento fijar swing relevante PRE-C2, POI, breaker, CISD/PS, EQ con régimen, entry C3.open, stop debajo EQ/breaker y HTF target untouched; autor/source ID/available_at y razones A/B/C/D. Si D esencial no resoluble → `NO_ESPECIFICABLE` honesto, NO criar trades de QORE-C con nombre TTrades.
10. No mover a **P0 fuente aprobada** por más tests de geometría. El único avance real es completar semantic proof o cerrar científico por no especificabilidad.

### Fase 3 — Cognitiva 27 campos y estado persistente
11. Construir `Situation` real sobre fuente A/B adjudicada: 27 campos valor+semantic/status+IDs+SHA/time, misma market y ancla, `terminal_pnl=None`. Ejecutar `verify_all_situation_field_receipts()`; el diseño actual rechaza automáticamente si falta source semantics (intencional).
12. Versionar CandidateEvent author-complete con firma/contrato A+B verificable e independiente. Actualizar readiness del modelo M15 B01 al nuevo R3 **como versión nueva**, no quitar protección para que pase.
13. Implementar rehidratación WAL del estado entero con test reinicio/duplicados/concurrencia y per-bar Journey/Position, con fill/terminal externos solo después de entrada genuina. Comparar A-only vs A+B sobre la **misma base de candidatos**, registrando WAIT/ABSTAIN; sin leak futuro.

### Fase 4 — Costes y Gates (solo cuando fases anteriores PASS)
14. Mapear BID/ASK+ticks reales y fees roundtrip por mercado/instante y reglas exactas de no-fill/stop-first/target con fuente y SHA. `NO_EVALUABLE` si hay huecos materiales; no usar costes de conveniencia.
15. Congelar y documentar con Owner Gates vigentes **antes de OOS**: PF, DD-R, MC, Sharpe, Sortino, densidad, estabilidad, sample size, WFO y nominal si DD% se necesita. Resolver #787 heredado vs PF1.80 y nunca importar Alpha.
16. Ejecutar economía 1R homogénea y pair A-only/A+B, walk-forward legítimo no visto, stress/spread, MC dependencia y revisión independiente. NO abrir 7Y holdout sin permiso y diseño de una sola evaluación intacta.
17. Solo publicar **CERTIFIED** si M0+C0+X0+PF+DD+Sharpe+Sortino+MC+OOS+Risk+Independent están todos PASS verificables y versionados. De lo contrario `NO_SUPPORT/NO_EVALUABLE/FAIL` según evidencia. Cualquier resultado favorable puramente geométrico permanece NO_CERTIFIED.

## 9. Protocolos exactos de prueba, artefactos y CI
**Rutas B a leer primero:**  
`src/qore/infrastructure/trader_lab/vt08_5m_b_independent_raw_receipts_v1.py`;  
`vt08_b_r3_frozen_source_independent_v1.py`;  
`vt08_b_r3_indexed_ultrafast_runner_v1.py`;  
`vt08_b_a_catalog_independent_verifier_v1.py`;  
`vt08_b_situation_field_source_audit_v1.py`;  
`vt08_b_durable_cognitive_research_ledger_v1.py`;  
`vt08_cognitive_5m_consumed_gate_v1.py`;  
`vt08_5m_a_to_b_candidate_readiness_v1.py`;  
`vt08_5m_b_methodology_spec_boundary_v1.py`.

**Workflows B probados:**  
`.github/workflows/vt08-b-r7-independent-market-catalog-replay.yml` (último PASS #38748150948);  
`.github/workflows/vt08-b-r3-independent-frozen-source-review.yml` (con runner indexado; #38740153019);  
`.github/workflows/vt08-b-independent-native-raw-receipt-audit.yml` (#38713809585);  
`.github/workflows/vt08-cognitive-5m-research-bridge.yml` (#38715753360);  
`.github/workflows/vt08-b-r5-cross-market-provenance.yml` (#38717559918).

**Rutas A recientes:**  
`src/qore/infrastructure/trader_lab/vt08_a_m30m3_frozen_family_source_funnel_v1.py`;  
`vt08_a_b_market_custody_catalog_v1.py`;  
`vt08_a_source_conditional_eq_review_v1.py`;  
`vt08_a_h1_untouched_high_source_witness_v1.py`;  
`vt08_a_blind_three_source_review_join_v1.py`.  
Para nuevo R6/R7 estudiar sus tests, artefactos y reportes antes de escribir B oráculo. Los path A sólo existen en rama A hasta merge autorizado; runner B no los importa como verdad.

**Comandos locales típicos desde checkout correcto**, sin live:
```bash
python -m pip install -e ".[dev]"
ruff check src/qore/infrastructure/trader_lab/vt08_b_a_catalog_independent_verifier_v1.py
mypy src/qore/infrastructure/trader_lab/vt08_b_a_catalog_independent_verifier_v1.py
pytest -q tests/infrastructure/trader_lab/test_vt08_b_a_catalog_independent_verifier_v1.py
pytest -q tests/infrastructure/trader_lab/test_vt08_b_r3_indexed_ultrafast_runner_v1.py
pytest -q tests/infrastructure/trader_lab/test_vt08_b_durable_cognitive_research_ledger_v1.py
pytest -q tests/infrastructure/trader_lab/test_vt08_b_situation_field_source_audit_v1.py
```
En CI los workflows descargan artefactos **por run ID y SHA pins**, comparan JSON y raw y publican cinco reportes por mercado. Si un artifact expiró, detener (NO inventar dataset) y solicitar restauración bajo licencia. Prefiere workflows/Trader Lab ultrafast para CPU de indexado, **siempre** con prueba diferencial contra oráculo lento antes de emplear su salida.

### Campos mínimos de un recibo científico nuevo
`experiment_id, source_spec_version, family, source_market, market_source_sha, c2_opened_at_utc, c3_decision_utc, situation_27_provenance, source_rule_ref, semantic_class A/B/C/D, method_status, cognitive_status, original_broker_quotes_ref, costs_ref, risk_unit_definition, oos_partition, run_id, artifact_sha, reviewer_A, reviewer_B, verdict`. Valores desconocidos `null/UNKNOWN`, no booleanos falsos `verified=true`. El broker quote ref no debe ser obligatorio en auditoría **solo source**, pero sí indispensable para la economía.

## 10. Matriz de aceptación que determina el cierre de un traspaso
- **Datos físicos reproducibles:** SÍ para R3/R4 bajo B R7; R6/R7 NUEVOS de A aún exigen B fuente-only adicional.
- **Fidelidad al autor y SOURCE_COMPLETE:** NO; swing relevante/PS/POI/breaker/stop/target D.
- **Cognitiva lista por fuente REAL:** NO; 27 campos semánticos no derivados, contrato manifiesto no firmado, WAL real sin rehidratación y lifecycle broker ausente.
- **Ejecución económica auténtica:** NO; cero fills B/A auditados con BID/ASK+fees por toda vida de trade, Gate PF/DD/Sortino/Sharpe sin pruebas.
- **Rentabilidad robusta y validación final:** NO EVALUABLE; falta freeze Owner y OOS no visto; Risk/Independent sign-off ausente.
- **Autorización LIVE/DEMO/VPS/merge/sizing:** NO. Este handoff no modifica esa autoridad.

### Dónde continuar y cómo coordinar
Arquitecto A usa [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762) y PR #765. Arquitecto B usa [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763) y PR #764. Publicar enlace de ESTE documento en ambos issues y avisar cuándo se aborde R6/R7. No preguntar repetidamente al Owner lo que ya estableció: prioridad máxima es certificar por metodología/cognitiva con Gates reales, ejecutar pruebas seguidas y no usar sizing. Si un Gate carece de umbral o sign-off, actuar con pruebas seguras source-only y explicitar el bloqueo, sin declarar CERTIFIED.

**Conclusión inalterable:** la base física de VT08 está notablemente avanzada; queda por **demostrar una estrategia metodológica especificable con edge y cognitiva operativa**, no ganar por volumen de pruebas geométricas. Una certificación honesta puede concluir NO_EVALUABLE/FAIL mientras se resuelve la fuente, nunca «PASS» por 88.276 barras o 52 contextos preclasificados.

---
**Fin del handoff maestro — última actualización de contenido 15-oct-2026.** Este archivo es aditivo al handoff B de 14-oct y a los informes A/B citados. El SHA del COMMIT que contiene el documento se debe verificar en PR #764 y no escribirse como autocita dentro del texto antes de completar la subida.


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

## APÉNDICE DE CONTINUIDAD REAL R18–R21 — 16-oct-2026 (prevalece en lo nuevo)

**R18 frontera A→B corregida:** `inspect_architect_a_candidate` ahora invoca de forma real la exclusión del Owner QORE-alpha (incluso procedencias anidadas), no solamente el validador aislado R16. El puente está fijado a A commit `a60fee1b810b45d6067cd867ae557382135c8604` y verifica que la envoltura B01 A real sea `SOURCE_INCOMPLETE_QORE_CONTAINMENT`, jamás SOURCE_COMPLETE. [CI B R18 #38820178304](https://github.com/mezas3238-hue/qore-core/actions/runs/38820178304) **SUCCESS: 275 tests + 3 skipped, Ruff y Mypy.** NO significa que toda ruta de producción externa a ese ingress esté protegida.

**R19 46 dossiers para dos reviewers:** [informe R18/R19](VT08_B_R18_R19_AB_INGRESS_AND_46_BLIND_TTRADES_SEMANTIC_REVIEW_PACKETS_2026-10-15.md), [CI #38820822586](https://github.com/mezas3238-hue/qore-core/actions/runs/38820822586) **6/6 PASS**, 2.657/2.657 fuente R3+R7 por SHA/case ID, 46 archivos de revisión física (9+9+9+10+9) con originales bar IDs rehash; A/B reviewer answers **todavía NULL**. No alterar denominador por estrato de muestra o por estadísticas no observadas.

**R20 conclusión fuente primaria crucial:** [Informe 16-oct](VT08_B_R20_NATIVE_2657_C1_LOW_SWEEP_CISD_CAUSAL_ORDER_AND_TTRADES_INTRAC2_RULE_2026-10-16.md), [CI #38902326551](https://github.com/mezas3238-hue/qore-core/actions/runs/38902326551) **6/6 PASS + 14 adversariales**. TTrades [CISD](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) y [Playbook](https://ttrades.com/fractal-model-playbook-aligning-daily-hourly-and-5-minute-charts/) instruyen comprobar el CISD inferior **dentro** de HTF C2 al cierre de C2; **R11 2.504 CISD anteriores a C2.close son físicamente válidos para evaluación as-of C3**, sin inventar requisito `CISD.after(C2.close)`. B reconstruyó 2.657/2.657 secuencias físicas de M3 cTrader **C1.low swept y observable ANTES del cierre CISD dentro C2; ambos disponibles en C3.open**. No significa `important level` genuino, relevancia de swing, PS/POI/breaker/stop/target author completa. Addendum de corrección registrado también en documento R11.

**R21 nuevo diagnóstico de relevancia contextual, NO nuevo filtro TTrades:** [Informe 16-oct](VT08_B_R21_NY_DAY_TO_DATE_INTRADAY_LOW_SOURCE_CONTEXT_2657_CASES_2026-10-16.md), [CI #38903207496](https://github.com/mezas3238-hue/qore-core/actions/runs/38903207496) **6/6 PASS**. Fuente física NY-midnight→C2.open de M3 real: de 2.657 C2, **1.091** barrían también el mínimo ya observado NY-day-to-date, **1.555** barrían C1.low pero **NO** dicho mínimo contextual, **11** sin contexto íntegro. Este NY-00 lookback es **proxy físico QORE explícito, NO fuente/obligación del autor**; no seleccionar 1.091 como «tradables» ni descartar 1.555 como «invalid» sin prueba de POI original. Los 46 dossiers R19 ahora pueden cruzarse con R20/R21 por `case_id_sha256`.

**Ruta crítica ya más precisa:** el ORDEN causal fue comprobado físicamente y la supuesta objeción «CISD debe cerrarse después de la C2 que lo contiene» fue desmentida por fuente primaria. **El bloqueo genuino P0 es la IMPORTANCIA/SELECCIÓN del POI o intraday swing**: C1.low inmediato vs nivel realmente relevante. A #762 debe adjudicar por fuente/TF/contexto con nombre de source candle/level, available_at y cita exacta; B #763 debe auditar de manera independiente, sin false endorsements y conservando 2.657. Después swing válido, PS, breaker, EQ, stop, target, 27 Situations reales, contrato A/B, BID/ASK neto y Gates predefinidos, sin sizing.

**Estado 16-oct-2026:** `SOURCE_PHYSICAL_R20_R21_PASS`; `AUTHOR_SEMANTICS_0`; `COGNITIVE_ADMISSIONS_0`; `FILL_VERIFIED_0`; `PF_DD_SORTINO_NOT_EVALUABLE`; VT08 **NO CERTIFICADO**. QORE-alpha excluida, 7Y holdout sellado, 0 sizing, 0 órdenes LIVE/DEMO/VPS, PR A/B DRAFT, 0 merge.

# QORE CORE — VT08 CRT DE TRES FUENTES
# HANDOFF MAESTRO DE TRANSFERENCIA INTEGRAL — 15 OCTUBRE 2026

**DOCUMENTO DE RELEVO AUTÓNOMO.** La finalidad es que el próximo arquitecto pueda retomar el trabajo directamente desde GitHub sin reabrir debates, confundir candidatos con operaciones, volver a repetir ensayos falsados ni emitir certificaciones falsas.

- **Repositorio soberano:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core).
- **Rama de trabajo:** agent/vt08-crt-pure-source-identity-001.
- **PR:** [#626 — VT08 CRT PURE](https://github.com/mezas3238-hue/qore-core/pull/626), **OPEN / DRAFT / UNMERGED**; **base** agent/vt08-crt-cognitive-architecture-freeze-001 (**NO** asumir que la base es main).
- **HEAD verificado JUSTO ANTES de redactar:** df4e49455e87529d56d1f54d9de66ccd2d5e6bb7.
- **Evidencia CI final en ese HEAD:** [QORE VT08 CRT PURE Cognitive Gate #38763492695](https://github.com/mezas3238-hue/qore-core/actions/runs/38763492695) SUCCESS. Los ensayos económicos *no* están incluidos en este CI.
- **Último replay G-M4 completo sobre datos reales:** [Actions #38763192649](https://github.com/mezas3238-hue/qore-core/actions/runs/38763192649), commit c69f0b4dd716cc3ffd4bad8f7e2d88759e476971, **3/3 SUCCESS**.
- **Estudio:** AUDUSD y USDJPY, histórico Atlas original consumido. BTCUSD está **FROZEN**, no validado por los ensayos V1–V3.
- **ESTADO ÚNICO DEL TRADER:** G-M1, G-M2, G-M3, G-M4 = **PARTIAL**; G-M5 = **NOT ISSUED**; ECONÓMICO-GLOBAL = **NOT CERTIFIED**; operación/capital = **NO AUTORIZADO**.

> **ORDEN ACTUAL DEL OWNER QUE PREVALECE SOBRE DOCUMENTOS HISTÓRICOS:** No se necesita fidelidad exclusiva a RomeoTPT. Se permite desarrollar **CRT QORE compuesto a partir de RomeoTPT + SpeculatorFL + TraderFlameseN**, distinguiendo de modo auditable citas originales de decisiones de ingeniería QORE. Se exige certificación tanto de **metodología/cognitiva (G-M1…G-M5)** como de **economía global (Profit Factor, Drawdown, Sharpe, Sortino y demás Gates)**. Está **terminantemente prohibido usar sizing para certificar VT08**, incluso disfrazado de «1 lote», «R normalizada», «capital supuesto» o «unidad fija». **CIBO / QORE Risk** es dueño único de volumen, capital y DD patrimonial. **No merge, no órdenes, no demo/live, VPS, MT5 o producción**.

---

## 1. Dictamen ejecutivo — qué es verdad y qué no

**SÍ existe** un laboratorio original SHA-backed, modelado de fuente compuesta, generadores CRT V1/V2/V3 pre-registrados, cognitiva positiva sobre casos reales, protecciones contra futuro, y un flujo de G-M4 observacional que enlaza fuente → cognitiva → veto de autorización → invalidación/expiración. La calidad de sus últimas ejecuciones está verde.

**NO existe aún** una metodología compuesta con los **siete contratos operativos independientemente adjudicados**; tampoco existen firmas independientes verificadas de G-M1…G-M4, PF neto/fills BID-ASK ejecutables ni DD patrimonial certificado por Risk/CIBO, ni OOS genuinamente no consultado. V2 y V3 obtuvieron diagnósticos ADVERSOS de precio. **No se puede declarar rentable o certificado VT08.**

**Distinciones imprescindibles:**
1. Contexto H4 / barrido / confirmación geométrica **≠** trade ejecutado.
2. Alcanzar DOL por wick M5 **≠** fill ni operación rentable.
3. 139/139 confirmaciones reconocidas cognitivamente **≠** 139 pronósticos correctos.
4. 3/3 jobs GitHub SUCCESS **≠** G-M4 PASS.
5. Certificado metodológico G-M5 futuro **≠** certificado económico GLOBAL y **nunca** autoriza capital.
6. Tres fuentes para metodología QORE **≠** consenso universal de tres autores, especialmente porque los textos SpeculatorFL y TraderFlameseN son muy parecidos.

---

## 2. Fuentes autorizadas y cambio de autoridad

**Fuentes:**
- RomeoTPT: [video Model #1](https://www.youtube.com/watch?v=UUq_wKQ61Wo) y [post old CRTH](https://t.me/s/officialRomeotpt/6615). Es **inspiración/origen**, pero la falta de una regla *exclusivamente Romeo* que resuelva todos los old CRTH simultáneos **no es veto universal** del CRT QORE.
- SpeculatorFL: [thread CRT 28-APR-2024](https://threadreaderapp.com/thread/1784493604473618604.html) y [conformational/advanced 25-MAY-2024](https://threadreaderapp.com/scrolly/1794311615535518154). Ideas de HTF/LTF, confirmation, timing, PD array y modalidades.
- TraderFlameseN: [Choose best CRT candle 13-MAY-2024](https://threadreaderapp.com/thread/1790141530461622525.html). Ideación semejante, **no validación independiente de edge**.
- [Acta vinculante de cambio de Owner](VT08_CRT_OWNER_TRES_FUENTES_CAMBIO_MANDATO_2026-10-15.md).
- Registro corpus y referencias: src/qore/infrastructure/traders/crt_pure_source_corpus.py y crt_pure_source_registry.py. Mantener adjudicaciones Romeo históricas AMBIGUOUS cuando lo sean; no maquillarlas CANONICAL.

**Regla de gobernanza:** una regla puede ser SOURCE_SUPPORTED por una fuente permitida con concepto+URL exactos o explícitamente OWNER_APPROVED_QORE_ENGINEERING con motivación, Owner y revisor independiente auténticos. **No seleccionar según PnL futuro**. El permiso del Owner de combinar tres fuentes **no aprueba automáticamente los detalles V1, V2 o V3**.

**Código de autoridad ya migrado de Romeo-only:**
- src/qore/infrastructure/traders/crt_pure_three_source_methodology.py — contrato de tres fuentes y siete categorías.
- src/qore/infrastructure/traders/crt_pure_methodological_certification.py — G-M1…G-M5, no sizing.
- src/qore/infrastructure/traders/crt_pure_certification_readiness.py — readiness global, aún fail closed.
- src/qore/infrastructure/traders/crt_pure_r2_entry_router.py — router de familia, bloqueo por QORE composite sin adjudicar.
- src/qore/infrastructure/trader_lab/vt08_crt_pure_gm3_real_case_safety.py — casebook 48, rechazo causal/autoridad.

**LOS SIETE CONTRATOS SIGUEN OPEN:** reference_eligibility, multiple_reference_priority, parent_child_timeframe, entry_confirmation, invalidation_expiry, destination_lifecycle y conflict_and_rearm. Cerrar sus textos con verificaciones reales, no cambiando un booleano.

---

## 3. Datos originales, procedencia, cobertura y custodia P0

**Fuente exacta:** [GitHub Actions Atlas12 original #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), usado por src/qore/infrastructure/trader_lab/vt08_crt_pure_original_atlas_reader.py. Originales de investigación AUDUSD **148.171 M5** y USDJPY **148.201 M5**: **296.372 M5**. Velas relativas del proveedor con manifiestos, hashes y reloj UTC. Los 5.524 pares completos H4 son **2.738 AUDUSD y 2.786 USDJPY**, según el censo UTC completo de V1–V3.

**Limitaciones materiales:** M5 OHLC NO equivale a precio ejecutable BID/ASK, tick, order book, orden intrabar precisa ni coste neto; gaps causan UNKNOWN. El histórico septiembre 2024–septiembre 2026 fue visto durante V1, V2, V3 y antes: **TOTALMENTE CONSUMIDO como desarrollo; NO holdout virgen**. Las 48 fichas seleccionadas con buckets tampoco representan frecuencia general de señales.

**Otros repositorios/runs:** [New21 M5 #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) y datos de 33 activos de QORE Native no se convierten automáticamente en aprobación multi-mercado VT08; validación separada de proveedor, mercado, PIT/BID-ASK, clocks y autorización. No buscar Dukascopy por defecto: primero inventariar GitHub/Atlas existentes, sin confundir OHLC M5 con BID/ASK históricos.

**CRÍTICO #837:** [Data Vault: backup duradero + restore SHA](https://github.com/mezas3238-hue/qore-core/issues/837), aún OPEN a este checkpoint. El handoff histórico identifica el **vencimiento del Atlas12 original 2026-12-16 00:21:18 UTC**; verificar fecha real del artifact vía API, NO asumir retención permanente por CI GREEN. Obtener vault privado aprobado/licenciado, manifest run_id/artifact_id/source_sha/datasource/símbolo/timeframe/sha, prueba de restore independiente y control de acceso. **No copiar raw licenciados al repo público ni VPS, no activar pagos sin autorización**.

---

## 4. Qué se hizo antes del trabajo de tres fuentes: preservar y NO repetir

**Investigaciones históricas R1/R2/N:**
- [Handoff historia 13-OCT](VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md) y [handoff operativo 14-OCT](VT08_CRT_PURE_HANDOFF_MAESTRO_CERTIFICACION_CONTINUIDAD_2026-10-14.md): R1/R2 y variantes AO, BE, BM, CC, CD; densidades y PF exploratorios **no comparables** a V1/V2/V3 ni certificados.
- **Error grave R2-BM:** se priorizó TP antes de SL en la misma M15, inflando PF bruto (~1,119 vs ~1,019 corregido; con coste hipotético 0,02R ~0,976). Usar STOP_FIRST cuando no se conoce secuencia intrabar; idealmente pedir datos ejecutables, nunca proyectar el PF antiguo.
- R2-CC AUDUSD PF bruto exploratorio ~1,074; R2-CD USDJPY ~1,012; costes hipotéticos, hipótesis distintas, robustez insuficiente. **No presentarlos como edge CRT QORE certificado**.
- [Forense N1/N2/N3](VT08_CRT_PURE_HANDOFF_MAESTRO_INTEGRAL_DOBLE_CERTIFICACION_2026-10-14.md): 939 geometrías anidadas, 2.634 diagnósticos N3 y otros candidatos **no son fills/trades**; confusiones de duración de fuente, oposición H4/M15 y selección posterior permanecen identificadas.
- 48 casos G-M2 reales (24 AUDUSD y 24 USDJPY) sobre H4 C1/C2 + prefijo cerrado M15: [laboratorio #38622889457](https://github.com/mezas3238-hue/qore-core/actions/runs/38622889457). 96 posibles extremos H4 de dos velas, referencias «old CRT» NO homologadas por autor. En [G-M1 challenge #38650459457](https://github.com/mezas3238-hue/qore-core/actions/runs/38650459457) no surgió ninguna selección old-CRTH auténtica definitiva.
- 48/48 ABSTAIN/WAIT fail closed, G-M5 no emitido en [#38659571365](https://github.com/mezas3238-hue/qore-core/actions/runs/38659571365), prueba NEGATIVA de seguridad, NO precisión cognitiva en CRT.
- Los 48 paquetes [FIRST-LOOK NEUTRAL VISUAL #38706589343](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343): **48 fichas/96 SVG**, sin anotación direccional mecánica/futuro, 0 dictámenes humanos. [Informe blind G-M2](VT08_CRT_PURE_GM2_NEUTRAL_VISUAL_FIRSTLOOK_48_CASES_2026-10-15.md). Paquetes separados (FIRST LOOK, técnico posterior y futuro sellado) son **aislamiento por contenido, NO ACL real de acceso**; requieren revisión independiente antes de abrir C3 posterior.

---

## 5. Programa CRT de tres fuentes: V1 / V2 / V3 CONGELADAS

Los tres modelos son **síntesis de ingeniería QORE predefinidas**, no implementaciones «certificadas» de la estrategia de Romeo. Para evitar hindsight el sucesor debe conservar sus versiones y sus diagnósticos falsadores; un cambio posterior crea identidad NUEVA y exige protocolo y OOS diferentes.

| Experimento | Regla causal principal | Candidatos conceptuales | Experimento de precio posterior | Dictamen |
|---|---|---:|---|---|
| **V1** | H4 C1→C2 barrido unilateral/close dentro + **primer par M15** del C3 con confirmación restrictiva y midpoint H4 disponible | **54** = AUDUSD 31 + USDJPY 23 | No se debe suponer rentabilidad; primera prueba fue densidad | Filtro demasiado restrictivo para densidad perseguida; NO EDGE demostrado |
| **V2** | Mismo parent H4, micro-CRT en cualquiera de pares M15 durante C3, primer evento por parent y DOL no consumido | **745** = AUDUSD 353 + USDJPY 392 | **115** DOL primero, **538** invalidación primero, **2** ambos misma M5, **57** expire no-hit, **6** expire al cierre C3, **27** unknown | Trayectoria adversa, NO_SUPPORT para V2 como está definida |
| **V3** | H4 parent igual; *tercera vela M15* cerrada y **body-confirm** que supera apertura de source, no mecha; primera triple válida; invalidez en wick source; DOL midpoint H4 | **139** = AUDUSD 61 + USDJPY 78 | **23** DOL primero, **69** invalidación primero, **42** expire no-hit, **5** unknown | Trayectoria adversa V3, NO_SUPPORT para pretensión económica V3; no invalida universalmente CRT |

**Bajo V3**, del total original 5.524 H4, **1.734 padres H4** cumplen purga/reclaim estructural, pero **1.109** contextos ya habían consumido el destino al considerar confirmaciones. No convertir descartes en trades, ni exigir artificialmente todas las confluencias propuestas por autores sin pre-registro.

**Código exacto:**
- V1 src/qore/infrastructure/trader_lab/vt08_crt_three_source_candidate_v1.py y vt08_crt_three_source_v1_full_h4_census.py, tests homónimos. [Prereg V1](VT08_CRT_3_FUENTES_QORE_V1_PREREG_2026-10-15.md). [Lab V1 #38710923324](https://github.com/mezas3238-hue/qore-core/actions/runs/38710923324) 3/3 SUCCESS.
- V2 vt08_crt_three_source_v2_full_h4_census.py y vt08_crt_three_source_v2_price_lifecycle.py; [prereg V2](VT08_CRT_3_FUENTES_QORE_V2_PREREG_2026-10-15.md), [prereg PRICE-PATH](VT08_CRT_THREE_SOURCE_V2_LIFECYCLE_PREREG_2026-10-15.md), [V2 censo #38711787794](https://github.com/mezas3238-hue/qore-core/actions/runs/38711787794) y [outcomes #38713036976](https://github.com/mezas3238-hue/qore-core/actions/runs/38713036976), ambos 3/3 SUCCESS. [Informe falsación V2](VT08_CRT_THREE_SOURCE_V2_PRICE_LIFECYCLE_FALSATION_2026-10-15.md).
- V3 vt08_crt_three_source_v3_confirmed_h4_census.py y vt08_crt_three_source_v3_price_lifecycle.py; [prereg V3](VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE_PREREG_2026-10-15.md), [prereg V3 PRICE-PATH](VT08_CRT_THREE_SOURCE_V3_PRICE_LIFECYCLE_PREREG_2026-10-15.md), [V3 censo #38749028744](https://github.com/mezas3238-hue/qore-core/actions/runs/38749028744), [V3 price path #38749761117](https://github.com/mezas3238-hue/qore-core/actions/runs/38749761117), ambos 3/3 SUCCESS. [Falsación V3](VT08_CRT_THREE_SOURCE_V3_CONFIRMED_139_CAUSAL_FALSATION_2026-10-15.md).
- Tests y workflow: .github/workflows/vt08-crt-pure-gm2-blind-casebook.yml (V1/V2, blind), .github/workflows/vt08-crt-three-source-v3-third-candle.yml (V3 real original y price path), calidad Ruff/mypy/pytest en Actions.

**ADVERTENCIA:** V2 fue ideada después de conocer V1 y V3 después de V2, aunque cada versión se pre-registró **antes de su propio resultado**. Todo el histórico comparte información de desarrollo y no se convierte en OOS por usar nuevo nombre. La sucesión V1→V2→V3 NO justifica elegir retrospectivamente la mejor.

---

## 6. Estado G-M3: reconocimiento cognitivo sobre hechos positivos

**Módulos:** src/qore/infrastructure/traders/crt_pure_cognitive_state.py (Situation Model, ATTENTION, knowledge, metacognición, adversarial, `reason()`, transiciones), crt_pure_cognitive_contract.py, identidad de mercado. Fuente real V3 mediante src/qore/infrastructure/trader_lab/vt08_crt_three_source_v3_gm3_cognitive_replay.py y tests de anti-leak/revisor falso.

**Prueba [G-M3 #38750815066](https://github.com/mezas3238-hue/qore-core/actions/runs/38750815066):** quality + AUDUSD + USDJPY **3/3 SUCCESS**. 61/61 eventos source confirmados AUDUSD + 78/78 USDJPY = **139/139 RECONOCIDOS causalmente**; `supporting_evidence` incluye confirmación y DOL disponible a reloj; `reason()` produce **139/139 ABSTAIN** con `CRT_SOURCE_STRATEGY_NOT_CLOSED`, **0 EXECUTE**, por método triad QORE sin siete contratos aprobados. [Informe G-M3](VT08_CRT_THREE_SOURCE_V3_GM3_REAL_POSITIVES_139_2026-10-15.md). Artifacts AUDUSD **11980952529**, USDJPY **11981706027**, SHA internos verificados en la ronda.

**Lectura correcta:** reconoce lo que el generador V3 etiquetó como confirmación geométrica, pero eso **no es precisión frente a expertos independientes**, ni verifica meta-cognición «perfecta» ni edge; la respuesta ABSTAIN es legal. Falta contraposición con tesis/contratesis, source-ground truth de autor/QORE, conflictos, memoria/expiración con nuevos eventos y firma externa.

---

## 7. Estado G-M4: pipeline end-to-end causal, NO aprobado formalmente

**Nuevo protocolo pre-registrado:** [G-M4 V3](VT08_CRT_THREE_SOURCE_V3_GM4_CAUSAL_LIFECYCLE_PREREG_2026-10-15.md). Código src/qore/infrastructure/trader_lab/vt08_crt_three_source_v3_gm4_lifecycle.py; tests tests/infrastructure/trader_lab/test_vt08_crt_three_source_v3_gm4_lifecycle.py; workflow .github/workflows/vt08-crt-three-source-v3-gm4-lifecycle.yml.

**Último replay verdaderamente ejecutado:** [#38763192649](https://github.com/mezas3238-hue/qore-core/actions/runs/38763192649), SHA c69f0b4dd716cc3ffd4bad8f7e2d88759e476971, quality/AUDUSD/USDJPY **3/3 SUCCESS**, con guards de identidad source/clock/market/dirección, precio invalidante de M15 source idéntico en ambos ledgers, M5 temporal exacta, no future payload, no sizing y no rearm tras tesis terminada.

| Corte G-M4 original | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| V3 source→cognition→router reconciliado | 61 | 78 | **139** |
| Reconocidos, `ABSTAIN`, routing bloqueado | 61 | 78 | **139** |
| TERMINAL observado post-decisión (ya cerrado causalmente) | 59 | 75 | **134** |
| UNKNOWN por evidencia incompleta (sin terminal inventado) | 2 | 3 | **5** |
| DOL primero | 11 | 12 | **23** |
| Invalidez primero | 29 | 40 | **69** |
| Expiración sin toque | 19 | 23 | **42** |

**Mecanismo de estado:** OBSERVED_EVENT→HYPOTHESIS_FORMING→AWAITING_CONFIRMATION→CONFIRMED y, sólo después de M5 closed, INVALIDATED→KILLED o KILLED por destino/expiry; los UNKNOWN permanecen CONFIRMED en el ledger de investigación **sin representar una posición activa**. El estado cognitivo inicial y el WHY no utilizan precio M5 del futuro. **El pipeline representa el ciclo de observación de una hipótesis, NO un E2E con broker/Risk/CIBO real y no equivale a G-M4 PASS**.

**Evidencia:** [Informe final G-M4 139](VT08_CRT_THREE_SOURCE_V3_GM4_139_END_TO_END_INVARIANTS_2026-10-15.md). ZIP finales **AUDUSD 11986482995** y **USDJPY 11985714852** en [run #38763192649](https://github.com/mezas3238-hue/qore-core/actions/runs/38763192649). SHA256SUMS 3/3 por cada ZIP, descarga verificada durante ejecución anterior, comprobar de nuevo tras expiración nominal 2027-01-13. 134/139 TERMINAL probado; 5/139 CENSORED. G-M4 formal PARTIAL.

---

## 8. Matriz de Gates y definición concreta de qué queda por hacer

| Gate | Estado real | PASO BLOQUEANTE / evidencia faltante, no solo código |
|---|---|---|
| **G-M1 Fuente y método compuesto** | PARTIAL | Cerrar SIETE reglas CRT tri-source con fuente individual y/o ingeniería QORE marcada, operacional, sin futuro, firmada por Owner/revisor independiente; resolver jerarquía, DOL, timeframes, invalidación, timing, PD array y conflictos. No Romeo-only. |
| **G-M2 Percepción y dictamen externo** | PARTIAL | Revisor independiente realiza 48 FIRST-LOOK visuales sin scores, antes de abrir C3 sellado; labels de tesis, contra-tesis, nivel válido y motivo, disagreement, timestamp/fuente; cubrir también escenarios auténticos V3 positivos y rechazos no seleccionados. |
| **G-M3 Cognitiva y metacognitiva** | PARTIAL | Contrastar razón, incertidumbre y transición de `reason()` contra dictámenes externos y contraejemplos; corregir errores reales sin usar outcomes; memoria/event_generation/contradicciones/rearm y cancelación de fuente. 139 reconocidos ≠ 139 aciertos. |
| **G-M4 Recorrido causal completo** | PARTIAL | 139 eventos source→cognition→router→post-M5 probados; **5 UNKNOWN**. Falta cierre fuente-adjudicado y traspaso conceptual a soberanía CIBO/Risk, con pruebas sin broker/sizing; firmas independientes y fallas fail-safe. |
| **G-M5 Certificado método** | NOT ISSUED | Solo emitir cuando G-M1..G-M4 tengan prueba, Owner/reviewers autenticados y cuatro PASS genuinos. El certificado no autoriza operar ni volumen. |
| **GLOBAL económico** | NOT CERTIFIED | Candidato nuevo o válido método congelado; datos BID/ASK PIT + costs/fills, PF net, DD Risk/CIBO externo, Sharpe/Sortino, fresh OOS real, WFO, stress, MC, validación intermercado y revisión independiente. |
| **EXECUTION** | NOT AUTHORIZED | No broker/demo/live/production/VPS, PR no merged, CIBO sigue dueño soberano de capital. |

**FALLO ARQUITECTÓNICO ABIERTO P0:** `CrtPureMethodGateEvidence` actualmente acepta un string `independent_adjudicator`, booleano `no_future_leak_attested` y refs declaradas, pero **NO autentica por sí mismo la identidad o firma criptográfica del revisor**. `CrtThreeSourceRuleContract` acepta un `owner_approval_id` con cadena: **esa cadena por sí sola no prueba una aprobación**. Aunque source OPEN impida hoy falsa certificación, un cierre futuro basado solo en strings podría provocar AUTO-PASS sin evidencia. **Requerir un gate de evidencia verificada externa con blob SHA, principal autorizado, firma/acta y cadena de custodia antes de permitir cualquier certificación real.** No llenar el campo con "test review".

**FALLO DE ALCANCE ABIERTO P0:** `crt_pure_certification_readiness.py` todavía requiere `btcusd_history_verified` y `combined_three_market_validation_green`, mientras BTCUSD está **congelado** para VT08 actual. Esto no se resuelve poniendo flags falsos ni descongelando producción: **solicitar decisión del Owner del alcance GLOBAL AUDUSD/USDJPY o tres mercados**, versionar contrato y revisión Risk/CIBO. La semántica de certificación metodológica y global debe permanecer separada.

---

## 9. Economía GLOBAL: Gates E0–E11 siguen abiertos

**El Owner ratificó explícitamente Profit Factor, Drawdown, Sortino, Sharpe y demás Gates**; el método/cognitiva debe pasar G-M1…G-M5 antes de GLOBAL. No se permite certificar un modelo económicamente débil por «inteligente».

| ID | Entregable de la autoridad correspondiente | Estado |
|---|---|---|
| E0 Modelo/mercados/identity congelados | Código SHA, metodología aprobada, hipótesis identificada, reglas de ejecución neutrales a sizing, calendario PIT | OPEN |
| E1 Mercado ejecutable + costes | Históricos BID/ASK/quotes/ticks verificables, broker contract, comisión, slippage, spread, gaps y fill semantics | OPEN |
| E2 PF net / expectancy | Ledger REALIZABLE bruto/neto, nº trades verificables por mercado/año, muestra/IC, sin confundir wick-hit con fill | NOT EVALUATED |
| E3 Drawdown | **DD de cuenta patrimonial solo QORE Risk/CIBO**, no sizing propio ni simulado del Trader; definir autoridad y unidad | NOT EVALUATED |
| E4 Sharpe / Sortino | Frecuencia de retornos válida, downside benchmark/MAR, anualización, n suficiente, incertidumbre | NOT EVALUATED |
| E5 OOS genuinamente virgen | Datos posteriores/no vistos, acceso sellado y auditor independiente, sin usar Atlas 2024–2026 como OOS | OPEN |
| E6 Walk-forward / embargo | Folds chronology, purging, no leakage ni refit del test final | OPEN |
| E7 Stress & sensibilidad | Shocks de spreads/costes, gaps, DST/session, orden intrabar, regímenes y proveedores | OPEN |
| E8 Monte Carlo / dependencia | Bootstrap por bloques/regímenes, tail/quantiles/predefinidos y límites falsadores | OPEN |
| E9 Comparadores / multiplicidad | Baseline, incertidumbre, potencia, estabilidad temporal/mercados, correction for selection bias | OPEN |
| E10 CIBO / Risk / reviewer | Evidencia económica independiente y alcance, sin transferir capital authority a VT08 | OPEN |
| E11 GLOBAL CERTIFICATE | Todos E0–E10 y G-M5 PASS auténticos, código/global gate que NO sea configurable por flags falsos | NOT CERTIFIED |

**Umbrales numéricos CRT PURE** NO aparecen formalmente aprobados en el expediente: **NO COPIAR** los de [#762](https://github.com/mezas3238-hue/qore-core/issues/762) (VT08 5M TTrades, otra identidad) ni [#838](https://github.com/mezas3238-hue/qore-core/issues/838) (QORE-Alpha2). Pedir al Owner/Risk acta de alcance y umbrales PF/DD/Sharpe/Sortino y tolerancias ANTES de mirar el nuevo OOS; tampoco inventar 1 lote o 1R para poder calcular DD.

---

## 10. Registro de PROBLEMAS conocidos — responsables y salida exigible

| Problema | Causa raíz / evidencia | Severidad | Resolución mínima para sucesor |
|---|---|---|---|
| P-01 Romeo-only bloqueaba método sintético | Requería old CRTH única atribuida a Romeo aun con 3 fuentes permitidas | **CORREGIDO contrato** | Mantener política tri-source; preservar incertidumbre original sin veto exclusivo. |
| P-02 Siete reglas QORE abiertas | Fuente inspiracional ≠ semántica operativa completa/review | **P0 OPEN** | Contrato por regla con casos positivos, negativos y contraejemplo; aprobación Owner+auditor real. |
| P-03 Método V1 densidad baja | Primeras dos M15 rígidas, contexto HTF demasiado estrecho | **DIAGNOSTICADO** | Mantener V1 congelada; no tuning ex-post. |
| P-04 Método V2 trayectoria adversa | 745 conceptuales, DOL primero 115 vs invalidez 538 | **EVIDENCIA ADVERSA** | No usar V2 como estrategia rentable o retunear sus barreras in-sample. |
| P-05 Método V3 trayectoria adversa | 139 confirmadas, DOL primero 23 vs invalidez 69 | **EVIDENCIA ADVERSA** | No certificar V3 ni retunear contra resultados vistos. |
| P-06 Positivos cognitivos no adjudicados | 139/139 reconocidos, pero source-contract OPEN | **P0 OPEN** | Etiquetas independientes, precisión/falsación, source-aware cognitive policy. |
| P-07 G-M4 tiene 5 UNKNOWN | M5 missing o barrera al inicio no confiable, no podemos inventar terminal | **P1 OPEN** | Recuperar evidencia temporal original o censurar definitivamente y formalizar política de falta de datos. |
| P-08 Firma no autenticada | Campos string reviewer/Owner acceptance verifican no-vacío, no principal | **P0 OPEN** | Revisor y Owner autenticados, firma/commit/review auditada, protección anti self-attestation. |
| P-09 Blind y SEALED mismo dominio ACL | ZIP distintos; mismos permisos de repo/run potencialmente permiten leer futuro | **P0 OPEN** | Revisión externa con permisos/custodia y sellado verdadero antes de C3 future. |
| P-10 OOS contaminado | Iteración V1/V2/V3 y búsquedas previas sobre Atlas 2024–26 | **P0 OPEN** | Nuevo holdout realmente virgen, timing/control de acceso; no reutilizar fechas vistas. |
| P-11 No costes/fills BID-ASK | Solo source OHLC/provider relative y path first-touch | **P0 OPEN** | Broker original/time-aligned BID/ASK, costes PIT, fill rule, instrument mapping y auditoría. |
| P-12 R2-BM TP antes de SL | Orden intrabar desconocido; PF inflado | **CORREGIDO histórica** | Nunca reutilizar PF legacy defectuoso, STOP_FIRST / datos tick. |
| P-13 BTCUSD frozen vs Global 3-market | Readiness general exige 3 mercados sin política de alcance del Owner | **P0 OPEN** | Resolución alcance explícita, no false flags. |
| P-14 Artefactos no permanentes | Retention 90 días, riesgo Atlas12 #837 | **P0 OPEN** | Vault privado autorizado + restore SHA antes del vencimiento real. |
| P-15 CI GREEN ≠ metodología PASS | Tests invariantes internos no prueban fuentes/ejecución | **P0 DISCIPLINA** | No emitir G-M1..5 ni global por test verde; independencia real. |
| P-16 Sizing prohibido | Tentación de usar lotes, cash o 1R ficticia para DD/PF | **BLOQUEO PERMANENTE** | CIBO/Risk externo DD/capital, nada de tamaño en VT08. |
| P-17 No separación reaction/journey/confirmation | V1–V3 prueban subconjuntos de CRT anidado y destinos H4; otras familias no predefinidas | **P1 OPEN** | Especificar mecanismos causales separados antes de test NUEVO (no elegir por 2024–26). |
| P-18 Tiempo NY/DST / PD array / sesión | H4 censo UTC QORE, no validación de temporalidad/composición diaria del autor | **P1 OPEN** | Timestamps PIT, calendario NY-DST/market session, HTF key levels y fuente. |
| P-19 Datos source M1/ticks heterogéneos | No confundir otros datasets QORE Native con tick ejecutable del broker correcto | **P1 OPEN** | Inventario proveedor/símbolo/timeframe + permiso/contrato, no interpolar M1 desde M5. |

**Acciones NO autorizadas para «resolver» problemas:** liberar PR, fabricar señales con futuro, cambiar falsaciones, elegir niveles por PnL, cambiar alcance BTCUSD vía booleanos, copiar datos licenciados sin permiso, usar sizing dentro del Trader, activar cuentas/demo/live.

---

## 11. Procedimiento de takeover ejecutable — 12 pasos SIN perder contexto

1. **Verificar GitHub primero:** branch `agent/vt08-crt-pure-source-identity-001`, PR #626 DRAFT/unmerged, su base; consultar HEAD y registrar el nuevo HEAD antes de modificar. **No hacer merge**.
2. **Leer este handoff completo y sus fuentes enlazadas**: [maestro histórico integral 14-OCT](VT08_CRT_PURE_HANDOFF_MAESTRO_INTEGRAL_DOBLE_CERTIFICACION_2026-10-14.md), [directiva owner 15-OCT](VT08_CRT_OWNER_TRES_FUENTES_CAMBIO_MANDATO_2026-10-15.md), informes V2/V3/G-M3/G-M4 y preregistros. **Directiva nueva prevalece** sobre cualquier Romeo-only histórico.
3. **Custodia antes de perder M5:** atender [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837); mirar API `expires_at` Atlas12, inventario todos symbols+hashes, backup **privado licenciado aprobado**, restore independiente, sin VPS ni fugas de datos.
4. **Congelar línea falsada:** conservar V1/V2/V3 y sus hashes/outcomes como observaciones DEV, no candidates para retune. Respetar primero-no-mismo-M5 y último M15 C3 expirado.
5. **Cerrar fuente/ingeniería G-M1:** inventariar siete contratos y sus source locators; jerarquía de old key levels; clases **reaction/journey/confirmation**; política H4, M15, PD-array, expiración y tratamiento de conflictos. Pre-registrar especificaciones concretas QORE diferenciadas de autor, obtener Owner y revisor REAL verificable.
6. **Cerrar revisión ciega G-M2:** distribuir SOLO first-look sin etiquetas/resultados, documentar market UTC+NY DST y nivel/tesis/contra-tesis por case ID; doble revisión independiente y adjudicación de desacuerdos ANTES de revelar SEALED C3. Documentar accesos, no asumir ACL por ZIP.
7. **Auditar cognitiva G-M3:** incorporar etiquetas independientemente adjudicadas sin desenlace futuro, evaluar WAIT/ABSTAIN y «conceptual entry» legítimo por caso, WHY, incertidumbre, contradicciones/invalidación, generación nueva y precisión error class. 139/139 positive recognition solo baseline, no PASS.
8. **Cerrar G-M4 científico y Risk boundary:** usar flujo 139 real source→cognition→router→lifecycle, persistir los 5 UNKNOWN/censura y verificar hipotético handoff conceptual sin generar órdenes/volumen. Diseñar pruebas end-to-end con política y reviewer firmados, no sólo una colección de assertions.
9. **Corregir protocolo antifalsificación:** impedir que cadenas o booleans declaren source-approved/GM-PASS sin evidencia externa firmada y rastreable, sample SHA, identidad del reviewer diferente del implementador. Repetir tests self-attestation.
10. **Emitir G-M5 sólo cuando de verdad se cumpla**: cuatro PASS genuinos de G-M1–G-M4, acta firmada y hash de método; en caso contrario informar NOT_CERTIFIED, sin conceder operación.
11. **Carril GLOBAL económico:** resolución formal de BTCUSD congelado y alcance exacto; definición previa Owner/Risk de métricas y thresholds; datos BID/ASK PIT y costes/fills; hipótesis nueva con corpus OOS intacto, WFO, stress/MC e informe independiente Risk/CIBO sobre DD patrimonial, SIN sizing propio. Si no hay edge: NO_SUPPORT honesto, no regresión hasta pasar.
12. **Cierre de cada ronda:** actualizar este handoff o crear addendum con HEAD/código, Actions jobs, nombres de artifacts + SHA + retención, número de casos por mercado, nuevos problemas, estatus exacto de cada gate, revisión/firmas, Issue/PR comment. Mantener DRAFT, sin merge ni permisos de ejecución.

**Primer backlog ideal del sucesor:** (a) cerrar los 7 contratos y resolver autenticación de reviewer Owner; (b) resolver el alcance BTCUSD/global; (c) defender causalmente una nueva familia CRT y obtener realmente nuevo OOS antes de estudiar resultados; (d) custodiar urgentemente Atlas12 #837. **No** realizar otra búsqueda in-sample aleatoria para satisfacer deseo de certificación inmediata.

---

## 12. Anexo de rutas, CI, artifacts y documentación de lectura obligatoria

| Evidencia | URI / identificador |
|---|---|
| PR y coordinación | [PR #626](https://github.com/mezas3238-hue/qore-core/pull/626) |
| Fuente Owner 3 | [directiva y refactor](VT08_CRT_OWNER_TRES_FUENTES_CAMBIO_MANDATO_2026-10-15.md) |
| Documentación exhaustiva previa | [handoff integral 14-OCT](VT08_CRT_PURE_HANDOFF_MAESTRO_INTEGRAL_DOBLE_CERTIFICACION_2026-10-14.md) |
| Original Atlas12 M5 | [Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) |
| Custodia vault P0 | [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837) |
| 48 blind-neutral visual | [Actions #38706589343](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343), artifacts FIRST LOOK AUDUSD **11958423126**, USDJPY **11958537855** |
| Histórico G-M1 Model1 | [Actions #38650459457](https://github.com/mezas3238-hue/qore-core/actions/runs/38650459457) |
| V1 censo completo | [Actions #38710923324](https://github.com/mezas3238-hue/qore-core/actions/runs/38710923324) |
| V2 censo, 745 source | [Actions #38711787794](https://github.com/mezas3238-hue/qore-core/actions/runs/38711787794), artifacts AUDUSD **11960992041**, USDJPY **11961650358** |
| V2 745 price path | [Actions #38713036976](https://github.com/mezas3238-hue/qore-core/actions/runs/38713036976), artifacts AUDUSD **11961063948**, USDJPY **11961720910** |
| V3 censo, 139 source | [Actions #38749028744](https://github.com/mezas3238-hue/qore-core/actions/runs/38749028744), artifacts AUDUSD **11981125345**, USDJPY **11979094305** |
| V3 139 price path | [Actions #38749761117](https://github.com/mezas3238-hue/qore-core/actions/runs/38749761117), artifacts AUDUSD **11979699106**, USDJPY **11980476823** |
| V3 G-M3 cognitiva 139 | [Actions #38750815066](https://github.com/mezas3238-hue/qore-core/actions/runs/38750815066), artifacts AUDUSD **11980952529**, USDJPY **11981706027** |
| **V3 G-M4 end-to-end 139 / 134 / 5 FINAL** | [Actions #38763192649](https://github.com/mezas3238-hue/qore-core/actions/runs/38763192649), artifacts AUDUSD **11986482995**, USDJPY **11985714852** |
| Baseline gate última documentación/HEAD verificado | [Cognitive Gate #38763492695](https://github.com/mezas3238-hue/qore-core/actions/runs/38763492695) SUCCESS |
| Historial legacy con fallos BM y otros | [Handoff 13-OCT](VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md) |
| Generadores originales | src/qore/infrastructure/trader_lab/vt08_crt_three_source_v{1,2,3}_*.py, detalles arriba |
| Modelo cognitivo / autoridad | src/qore/infrastructure/traders/crt_pure_{cognitive_state,cognitive_contract,three_source_methodology,methodological_certification,certification_readiness}.py |
| Tests del método compuesto | tests/infrastructure/traders/test_crt_pure_three_source_methodology.py |
| Test G-M4 final | tests/infrastructure/trader_lab/test_vt08_crt_three_source_v3_gm4_lifecycle.py |
| Workflows vigentes | .github/workflows/vt08-crt-pure-cognitive-gate.yml; vt08-crt-pure-gm2-blind-casebook.yml; vt08-crt-three-source-v3-third-candle.yml; vt08-crt-three-source-v3-gm4-lifecycle.yml |

**Nota sobre artifacts:** los IDs citados se verificaron en rondas anteriores y tienen vencimiento temporal. **La mera existencia del enlace no es garantía de permanencia ni autorización externa de acceso.** Revalidar en GitHub, SHA y custodia; no guardar datasets licenciados junto con el markdown.

### Certificación / decisión de entrega

- **Methodology / cognition:** G-M1…G-M4 = PARTIAL; G-M5 NOT ISSUED.
- **Economic/GLOBAL:** no Profit Factor ni Sortino ni Drawdown patrimonial acreditados, no OOS intacto ni coste BID/ASK validado. GLOBAL NOT_CERTIFIED.
- **Research conclusion:** V1 densidad 54; V2 densidad 745 con observación de precio adversa; V3 tercera vela 139 con observación de precio adversa; G-M3 y G-M4 garantizan varias invariantes de no-leak/fail-closed, no edge económico.
- **Capital/operaciones:** ningún permiso, 0 sizing. PR #626 permanece DRAFT/unmerged.

**REGLA FINAL PARA EL PRÓXIMO ARQUITECTO:** No abandones CRT por un subconjunto V2/V3 adverso, pero tampoco transformes una hipótesis falsada en certificado porque sus tests pasan. Usa las tres fuentes, crea mecanismos CRT completos causalmente justificados, conserva el histórico de falsaciones, consigue evaluación realmente independiente y datos ejecutables OOS nuevos, y exige **TODOS** los Gates; sin sizing de VT08. CIBO/Risk es autoridad separada. Si no hay evidencia suficiente, el único dictamen aceptable es **NOT_CERTIFIED**.


---

## Addendum 15-OCT — hardening anti-self-attestation y dossier G-M1 del sucesor

**Nueva ronda después de takeover:** branch `agent/vt08-crt-pure-source-identity-001`, PR #626 permanece DRAFT, sin merge, sin órdenes ni sizing. Baseline inicial `a260abf13477a7a9e449c6088314e4f70da5e81c`. **Nueva evidencia de quality CI:** [run #38786465193](https://github.com/mezas3238-hue/qore-core/actions/runs/38786465193) **SUCCESS** sobre commit `839ba9d8687fa35eefdbc7f55dba8848fdce8f91` (Ruff/mypy/pytest de pipeline CRT). Los commits intermedios del primer intento fallaron Ruff por un docstring mal formateado, corregido en `cf97771a`; no atribuir sus fallos a error de estrategia.

**Hallazgo P0 ratificado:** `CrtThreeSourceRuleContract.independent_adjudication_id`, `owner_approval_id` y `CrtPureMethodGateEvidence.independent_adjudicator` son cadenas proporcionables por llamador; el atributo `no_future_leak_attested` es un booleano. La implementación previa permitía a una **tupla hipotética de siete reglas** obtener `methodology_closed=True` al llenar esas cadenas, aunque `current_three_source_methodology()` permanecía OPEN. El gate G-M5 seguía cerrado en estado corriente, pero el evaluador hipotético podía confundir "declaraciones" con "aprobaciones".

**Corrección implementada y auditada:**
- `crt_pure_three_source_methodology.py`: `proposal_complete` mide si se han presentado propuestas de las siete reglas; **nunca** lo equipara a `methodology_closed`. Agrega blocker `METHODOLOGY_INDEPENDENT_APPROVAL_UNVERIFIED` sin un verificador independiente confiable. Las siete políticas reales continúan OPEN.
- `crt_pure_methodological_certification.py`: todo PASS autodeclarado trae `G-Mx_PASS_ATTESTATION_UNVERIFIED`. Cuatro PASS sintéticos jamás emiten G-M5; no basta un ID/URL/booleano. **Esto es protección temporal fail-closed**, NO autenticación de review ya implementada.
- Tests negativos añadidos en `test_crt_pure_three_source_methodology.py` y `test_crt_pure_methodological_certification.py`, junto con actualización de expectativa de cierre hipotético. CI `#38786170231` y `#38786465193` SUCCESS.
- Nuevo [dossier G-M1 con siete reglas revisables](VT08_CRT_GM1_SEVEN_RULES_REVIEW_DOSSIER_2026-10-15.md): propuestas concretas y contrapruebas, con G2 multirreferencia y G7 rearm identificados como NO totalmente implementados/adjudicados. **Ninguna regla promovida a aprobada**; V3 adversa, no OOS.

**Atlas12 urgencia revalidada con GitHub API:** los 13 artefactos de [run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) aparecen `expired=false` con `expires_at=2026-12-16T00:21:18Z`, incluyendo originales AUDUSD `artifact_id=10475697610` y USDJPY `artifact_id=10475389415`. Existe **sólo retención temporal**; [issue #837](https://github.com/mezas3238-hue/qore-core/issues/837) OPEN. No exportación, vault o restore hecho en esta ronda. No copiar datos licenciados ni inventar backup.

**Nueva cola inmediata:** (1) construir verificador de review GitHub independiente realmente autenticado, SHA/contract-digest-bound, anti-self-approval y anti-replay; no insertar parámetro `verified=True` inyectable; (2) revisor externo adjudica semántica de G1–G7 y los contraejemplos; (3) G-M2 blind, G-M3 discrepancias y G-M4 revisión formal de 5 UNKNOWN; (4) custodia aprobada de Atlas12 antes de diciembre; (5) Gates globales sobre nueva hipótesis/fuente BID/ASK/fresh OOS, DD sólo CIBO/Risk. **G-M1..G-M4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED**. No sizing, órdenes, broker, PR merge ni promoción a producción.

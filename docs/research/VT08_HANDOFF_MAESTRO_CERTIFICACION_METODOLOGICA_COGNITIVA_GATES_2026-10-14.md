# QORE CORE — VT08: HANDOFF MAESTRO DE CONTINUIDAD Y CERTIFICACIÓN
## Corte 14-OCT-2026 — Metodología TTrades + Cognitiva propia + Gates PF / DD / Sharpe / Sortino

**MANDATO ACTUAL DEL OWNER (14 octubre 2026).** El nuevo objetivo es certificar VT08 POR SU METODOLOGÍA Y SU COGNITIVA, superando además TODOS los Gates económicos y de robustez (Profit Factor, Drawdown, Sharpe, Sortino, expectativa, estabilidad, OOS, estrés, etc.). No sustituir su metodología por una búsqueda cuantitativa ajena, ni declarar «certificación cognitiva» por el solo hecho de tener tests verdes. Este documento existe para que el arquitecto sucesor NO PIERDA CONTEXTO.

**REPOSITORIO FUENTE:** https://github.com/mezas3238-hue/qore-core

| Frente | Rama / evidencia soberana | Estado consultado 14-Oct |
|---|---|---|
| Arquitecto B, cognitiva y verificador | agent/vt08-5m-cognition-replay-20261010 / [PR #764](https://github.com/mezas3238-hue/qore-core/pull/764), [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763) | DRAFT, OPEN, UNMERGED; HEAD previo al handoff 6e2707c21dd8a49bf0ca21fe6112e13433b6e946 |
| Arquitecto A, metodología y fuentes | agent/vt08-5m-methodology-source-20261010 / [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762) | DRAFT, OPEN, UNMERGED; HEAD ca9181afff9512df5d31b8677ee00e1abcf25ed8 |
| Programa matriz | agent/vt08-cognitive-expansion-5m-v1-001 / [PR #634](https://github.com/mezas3238-hue/qore-core/pull/634) | DRAFT, OPEN, UNMERGED; HEAD e8c007aec382000f48fc4a9952864b15161d349f |
| Ensayo final específico 1 | [issue #787](https://github.com/mezas3238-hue/qore-core/issues/787), PR A #765 | CLOSED / SUPERSEDED, no prueba económica final física |
| QORE-alpha distinta identidad | [issue #798](https://github.com/mezas3238-hue/qore-core/issues/798), [PR #797](https://github.com/mezas3238-hue/qore-core/pull/797) | Investigación SEPARADA, no fusionar con VT08 |

**NO HACER:** merge automático; VPS, producción, DEMO, LIVE, FundedNext LIVE o ejecución con capital; abrir ni optimizar el histórico holdout 7Y sellado; falsear BID/ASK, rellenar comisiones ausentes con cero, convertir shape en trade, escoger ganadores por PnL posterior. **SIZING PROHIBIDO PARA CERTIFICAR EL TRADER:** sin lotaje variable, leverage, compounding, portfolio weight ni modos de CIBO para maquillar PF/DD/Sortino. La distancia de stop permite medir retornos normalizados en R; CIBO/QDLE conservan autoridad económica separada. No tocar el runtime de producción. El presente handoff ES documentación, no una nueva prueba de mercado.

---

# 0. VEREDICTO PRINCIPAL

**VT08 NO ESTÁ CERTIFICADO, NI EN METODOLOGÍA COMPLETA NI EN COGNITIVA CONECTADA A EJECUCIÓN ECONÓMICA REALISTA.** Se consiguió infraestructura cognitiva de investigación robusta y verificaciones físicas de origen M15, pero 0 entradas de los nuevos cinco mercados han recorrido una ruta completa fuente TTrades verificada → Situation REAL field-by-field → cognitiva → fill BID/ASK con costes físicos → posición/salida → PF/DD/Sortino certificables. La constante APPROVED_A_B_MANIFEST_SHA256 permanece None; ninguna decisión «EXECUTE» sintética equivale a entrada autorizada.

**EXISTE RESULTADO ECONÓMICO NEGATIVO MATERIAL:** el 11-Oct el Arquitecto A falsó un PROTOTIPO QORE M30→M3 distinto del método autor-fiel: 3561 madres, PF POS bruto 0,9642, PF POS con coste HIPOTÉTICO de 0,10R 0,7808; PF limit CISD bruto 0,8950, hipotético 0,7729; DD secuencial POS 102,62R bruto y 425,29R con coste supuesto; expectancy negativa. Run [#38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903), [informe detallado](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_M30M3_ECONOMIC_FALSIFICATION_NO_GO_PROXY_REPORT_2026-10-11.md). NO-GO permanente para ese prototipo; NO representa el TTrades ORIGINAL (POI/swing/EQ/breaker/stop/target reales NO estaban completos), y jamás debe retunarse usando esos resultados. Los fills eran OHLC hipotéticos y 0,10R era sensibilidad, no tarifas reales.

**COLISIÓN HISTÓRICA QUE NO PUEDE OCULTARSE:** después de ese NO-GO, el ensayo VT08 «final 1» de una única familia quedó [cerrado/superado en #787](https://github.com/mezas3238-hue/qore-core/issues/787) y el Owner abrió una identidad distinta llamada [QORE-alpha #798](https://github.com/mezas3238-hue/qore-core/issues/798) sin fidelidad TTrades. La nueva orden 14-Oct pide AHORA certificar VT08 mediante metodología+cognitiva. Interpretación conservadora: retomamos trabajo VT08 como NUEVA VERSIÓN/PERÍODO PROTEGIDO con acta explícita de identidad y Gates; NO reabrimos el antiguo único trial, NO alteramos su historial y NO mezclamos QORE-alpha. Ver sección 6 de reconciliación.

---

# 1. UNIVERSO, FUENTES Y ARQUITECTURA

**Cinco mercados expansión VT08:** EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD. Restricción Owner 01, 05 y 09 horas de Nueva York como anclas H4; 13NY puede figurar en material fuente pero NO es ancla Owner autorizada. Una operación rellenada máxima por mercado/día NY salvo autorización expresa. M15, M5 y M3 son perfiles SEPARADOS; posterior trabajo A estudió M30→M3; no combinar perfiles/mercados según cuáles ganan.

**Fuente TTrades primaria:** [4 Hour Power of Three](https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/), [EQ en Fractal Model](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/), [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/), [Timeframe Alignment ejemplo M30→M3](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/), [Breaker Blocks](https://ttrades.com/breaker-blocks-simplified/), [Positional Entries](https://ttrades.com/positional-entries-enter-before-the-expansion/), [Targets](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/); video original H4 youtube FAKWJ-1NlLE / PDF verificados solo hasta donde documentan informes A. Para promover A, A debe aportar enlace primaria, cita breve, sección, fecha, frame cuando procede, input cerrado y reloj. El blog ofrece ejemplos: no inventar umbrales ATR/pip/body%-wick o un FVG único obligatorio universal.

**Matriz de autoridad por regla** A=fuente primaria; B=inferencia documentada; C=formalización QORE separada; D=no resuelta / bloqueante de la entrada concreta. OWNER_POLICY es independiente de SOURCE_A. Exigir especificación por familia con roles REFERENCE_SWING, POI, EQ, CISD, PROTECTED_SWING, FAMILY_BOUNDARY, además de entry/stop/target/expiry/lifecycle. El verificador independiente B debe recibir primero TEXTO CONGELADO, nunca usar el código productor A como oráculo de metodología. Las auditorías históricas B fueron independientes en cálculo de fuentes raw, pero B ya había visto código A: NO llamarlas «revisión ciega integral».

**Corpus consumido M15 de los cinco mercados:** run original [#35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), 5 market-evidence-1095d.json, código origen SHA b2d33e1b4829d8b4afc76983decca8a99131403c. M3 cTrader DEMO nativo [#35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396). Artefactos Actions expiran: comprobar si hay backup físicamente restaurable, SHA, proveedor, zona horaria, licencias, meses faltantes y fuentes BID/ASK; run SUCCESS no equivale a conservación permanente. No abrir 7Y sellado.

---

# 2. TODOS LOS TRABAJOS YA HECHOS Y QUÉ PRUEBAN

## 2.1 Auditoría de densidad basal B01 y sus limitaciones

Funnel heredado de 1.095 días / 5 mercados: **11.655 anclas H4 observadas → 488 candidatos B01 → 457 terminales en el replay histórico de aquella versión**. Los 11.167 primeros descartes se reparten: 3.987 C2 cierre fuera de referencia; 2.071 daily bias unresolved; 1.347 doble barrido C2; 1.317 side/bias mismatch; 1.085 no reference sweep; 769 no Protected Swing; 406 H4 incompleta; 145 PS múltiples; 40 día fuente incompleto. Estos son motivos de descarte de una implementación, NO 11.167 trades latentes ni derecho a relajar filtros.

B verificó con serie M15 original **488/488 linajes B01**, mercados EURJPY 88, USDCHF 88, NZDUSD 126, CADJPY 88, USDCAD 98; [CI B #38095654032](https://github.com/mezas3238-hue/qore-core/actions/runs/38095654032), 13 tests adversariales, Ruff/Mypy. Los 488 son registros candidatos, NO fills del nuevo esquema. La base previa 457 terminales NO está conectada a cognitiva B. Hubo 30 conflictos market-day en la cohorte.

**Código B:** src/qore/infrastructure/trader_lab/vt08_5m_b_independent_real_lineage_audit_v1.py; test_vt08_5m_b_independent_real_lineage_audit_v1.py. [Informe](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_5M_B_INDEPENDENT_REAL_488_CANDIDATE_LINEAGE_AUDIT_2026-10-10.md). PR #634 conserva el antiguo análisis 161 trades/3Y y problemas reales de escasez, NO extrapolarlo al futuro.

## 2.2 EQ por fuente; C3 Completion / C4 dos relojes y clasificación estricta

Del [artículo EQ TTrades](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/), el rango EQ de C2 depende de cerrar a favor o contra swing válido: a favor usa rango completo, en contra el intervalo cierre-extremo; C3 tras cerrar usa rango entero. El **swing de referencia que CLASIFICA a C2 debe ser decidible antes de abrir C2**, diferente del swing final confirmado por el modelo a C2/C3 close. Si identifican swing usando extremo futuro de C2, LOOKAHEAD ESTRUCTURAL. Aún D hasta fuente y prueba independiente.

A emitió 294 C3 shape-only con 294 snapshots de primera M15 C4. B reconstruyó 294/294 y 294/294 físicamente, [CI #38098119759](https://github.com/mezas3238-hue/qore-core/actions/runs/38098119759), 8 tests. Subsets NO seriales: 213 dentro Owner, 81 fuera Owner (capability gap QORE), 105 double-sweep C2 D (80 entre los 213 Owner), 129 patrones CISD/PS M15 **PROXY FORMAL** (no predicen futura densidad fuente), 36 «envolvimientos fuertes» **geometría QORE C NO fuente**. No sumar buckets. No definir esas 36 como regla TTrades.

B escribió spec-consumer independiente A/B/C/D, protección de swing reference pre-C2 para régimen C2, y reloj propio C3 Continuation que NO puede usar C3 high/low H4 FINAL dentro de C3. Corrigió otra sobre-restricción: swing pre-C2 no es universal obligatorio de todas las familias C3 (cada una debe confirmar su propio antecedente causal). [CI #38103823100](https://github.com/mezas3238-hue/qore-core/actions/runs/38103823100), 21/21 adversariales, Ruff/Mypy. [Contrato auditor B](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_5M_B_AUDITOR_CLOSING_ROUND_SOURCE_FIRST_A_B_CONTRACT_2026-10-10.md). [Reporte taxonomía CI #38098820220](https://github.com/mezas3238-hue/qore-core/actions/runs/38098820220), 17/17 PASS. Las reglas SOURCE_COMPLETE no se concedieron por esas pruebas.

## 2.3 Reconstrucción independiente de 495 receipts FVG/CISD/PS

A publicó 237 estructuras C2 y 258 C3 intracycle bajo ruta estrecha «1 FVG» congelada, A software 5ea7d4ff2104200e99328bf57f6ee1aed447e028, [run #38098839670](https://github.com/mezas3238-hue/qore-core/actions/runs/38098839670). B creó verificador propio sobre artefactos originales A y 5 archivos M15 raw. Reconstruyó triple M15 FVG, momento de formación, toque posterior, serie opuesta, cruce de OPEN por close CISD, PS proxy, prefix de barras disponible, huellas event y SHA. Resultado **495/495 receipts físicos compatibles**, EURJPY 48+49; USDCHF 52+44; NZDUSD 48+49; CADJPY 42+63; USDCAD 47+53. Run [#38103539460](https://github.com/mezas3238-hue/qore-core/actions/runs/38103539460), SUCCESS 9 tests, Ruff/Mypy.

Eso NO prueba que la POI sea RELEVANTE para autor, ni que todos los positivos fueran detectados (false negatives), ni que sea posible comprar/vender y cerrar con costes reales. **488, 294 y 495 pertenecen a universos parcialmente solapados y NO se suman como operaciones**. [Reporte 495 + reloj C3](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_5M_B_INDEPENDENT_THREE_FAMILY_495_RECEIPTS_AND_INTRAC3_FUTURE_EQ_2026-10-10.md).

## 2.4 Hallazgos del arquitecto A posteriores al trabajo de B (11-Oct)

A investigó ejemplo del autor M30→M3: bullish C2 sweep/closure, M3 CISD+PS antes de nueva C3 y entrada posicional al OPEN de C3. **STOP long bajo EQ M30 Y breaker low**: SL menor que ambos niveles. Si el EQ o el breaker no son fuente causal validada, el stop PS-only de QORE NO es equivalente al autor. Referencia swing pre-C2, POI significativa, breaker exacto, target untouched y criterio de selección siguen D.

CI A [#38148776547](https://github.com/mezas3238-hue/qore-core/actions/runs/38148776547): 8.982 madres M30/M3, 8.979 casos de evidencia estructural y 3 incompletas, 4.406 bullish posibles según forma escrita, 921 pivot previos y 3.568 breaker-geometry PROXY C; subsets superpuestos, 0 source-complete. **NO REPRESENTAN 8.979 TRADES.**

**Ensayo QORE FALSADO** (ya descrito en sección 0): [#38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903), 3.561 madres, PF bruto <1, expectancy negativa. Repetirlo cambiando mercado/stop/filtro según los resultados anteriores violaría el preregistro. Guardar ese NO-GO permanente para el prototipo específico.

A preregistró un **único ensayo FINAL1 autor-fiel** de familia LONG M30 C2 reversal → M3 confirmación → open C3 positional. Exige swing relevant pre-C2, POI, EQ, breaker low, SL bajo ambos, target HTF high untouched conocido antes de entrada, BID/ASK real y manifest A+B; [prereg](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_FINAL_ONE_FAMILY_AUTHOR_FIDELITY_FROZEN_TRIAL_PREREG_2026-10-11.md). Gate de ESE ensayo: al menos 100 fills físicos, PF NET estrictamente >1,15, expectancy NET positiva, bajo un dataset independiente único. SI no completa fuente/fees/datos => NO_EVALUABLE; no inventar o repetir segundo holdout. A escribió barrera contractual de tres veredictos GO / NO_GO / NO_EVALUABLE, [CI #38164147226](https://github.com/mezas3238-hue/qore-core/actions/runs/38164147226) SUCCESS 17 tests, **sin prueba económica final ni manifiesto A+B firmado**. [Explicación de veredictos](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_FINAL1_AUDITOR_TRI_VERDICT_CAUSAL_GATE_AND_STOP_ORDER_2026-10-11.md).

## 2.5 Proyecto QORE-alpha no pertenece a esta certificación VT08

Owner mandó iniciar [QORE-alpha #798](https://github.com/mezas3238-hue/qore-core/issues/798) sobre features inspiradas en TTrades SIN fidelidad al autor: PR #797, 96 variantes PRECONGELADAS, sin resultados PnL bajo el nuevo protocolo debido a ausencia de M3 2022, source M3/M15 comienza ~24-Sep-2023; credencial cTrader DEMO invalid/refr. [Registro QORE-alpha #38170918767](https://github.com/mezas3238-hue/qore-core/actions/runs/38170918767) SUCCESS solo por registro, no economics. **NO confundir QORE-alpha / VT08 original, ni copiar al segundo Gates o winners del primero.** Issue #787 cerrado/superado, NO fue ensayo FINAL1 GO. La nueva petición de Owner 14-Oct necesita una acta de nueva versión VT08 que reconcilie esa historia sin reabrir OOS.

---

# 3. INVENTARIO COMPLETO DE COGNITIVA Y FALLAS CORREGIDAS

**Estado físico del código B:** [CI #38104698708](https://github.com/mezas3238-hue/qore-core/actions/runs/38104698708), código probado SHA 06fc55dd53299fcbc4c8b456a34394fed624a7d1: **196 PASS, 3 SKIPPED justificados en suite general**, Ruff PASS, Mypy PASS sobre 14 módulos, 3 tests de integración contra módulo A congelado PASS en job separado. Cobertura módulo gate de admisión/seguimiento 95% en regresión principal; NO cobertura total QORE. El código B HEAD posterior era documentación, NO nueva CI. [Reporte cognitivo profundo](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_5M_COGNITIVE_P0_HARDENING_QUALITY_GATE_2026-10-10.md).

| Capa | Función, evidencia y trabajos | Fallos identificados / solución / límites |
|---|---|---|
| Situation Model + scope | src/qore/infrastructure/traders/vt08_cognitive_situation_model.py y vt08_cognitive_5m_research_scope.py; cinco mercados RESEARCH, 27+ CAUSAL_FIELDS con cutoff. | BUG: cadenas truthy 'false' aceptadas como bool, bool True=1 como NY hora, precios no-Decimal, comparaciones DST fall-back; **corregido exact bool/Decimal + UTC instantes**. FALTA BAR_ID+SHA original por campo real. |
| Estrategia / memorias | vt08_cognitive_strategy_identity_memory.py, vt08_cognitive_memory.py, vt08_cognitive_cibo_market_memory.py, vt08_cognitive_trader_experience_memory.py | Las memorias de mercados nuevos son UNKNOWN, no importar retorno viejo ni auto-aprender PnL. BUG caché mutable en runtime_view permitía cambiar permisos y contenido sin cambiar hash; **deepcopy y test de ataque**, PASS. |
| Reasoning soberano | vt08_cognitive_reasoning.py, WAIT / ABSTAIN / EXECUTE, supportive evidence, contradicciones y market context. | BUG anterior: metacognitiva UNKNOWN sin soporte podía aparentar ejecutabilidad; controles de soporte explícito PASS. Aún no evalúa atributo de mercado REAL de fuente autenticada. |
| Meta + adversarial | states SUPPORTED/AMBIGUOUS/CONTRADICTED/UNKNOWN, ataques, reason_codes, fingerprints | UNKNOWN bloquea o espera, contradicción ABSTAIN; falta verificación independiente empírica de calidad de sus clasificaciones en trades físicos. |
| Hypothesis | vt08_cognitive_hypothesis.py, WAIT→EXECUTE, kill sin resurrection, una ejecución por source. | BUG CLOCK: Nueva York 01:45 fold0 y 01:15 fold1 pueden estar en orden UTC positivo pero Python comparaba hora local; **todos relojes event/fill/position/terminal/cutoff pasados a comparación UTC**, PASS DST. |
| A→B gateway | vt08_5m_a_to_b_candidate_readiness_v1.py y vt08_cognitive_5m_consumed_gate_v1.py | BUG: Situation construida con methodology_valid=True podría hacer EXECUTE sintético sin documento A completo. **API evaluate_provenanced() fail closed** comprueba CandidateEvent y manifest antes de razón real; evaluate() sigue para fixtures sintéticos, nunca orden. **Integración real aún no existe**; verificar que nadie use API lab fuera de tests. |
| Position | vt08_cognitive_position_intelligence.py y gate | BUG SL/TP DRIFT: el stop inicial, objetivo y current stop podían alterarse entre snapshots válidos aislados. **freeze desde primer snapshot, stop monotónico long y short**, y cada propuesta traza fill_id+fill SHA. AÚN NO se certificó que el primer SL/TP viniera de source/broker genuino. |
| Journey | vt08_cognitive_journey_intelligence.py, ADVANCING/STALLED/EXHAUSTED/INVALIDATED/REACHED | Propone HOLD/PROTECT/REDUCE/EXIT, no inventa cierre. Falta ejercicio contra cada M3 real desde fill a terminal, stop lifecycle y objetivos causal-authentic. |
| Fill/Terminal | Vt08ResearchFillEvidence, Vt08ResearchTerminalEvidence (en gate) | BUG GHOST POSITION: tras EXIT propuesto podía seguir evaluando abierto; ahora el terminal externo ligado a fill digest detiene continuidad. NO inferir fill de execute ni cierre de EXIT. **Ledger RAM, sin reinicios/idempotencia duradera**, SHA formal no autentica origen de broker. |

**Código puente central**:
- src/qore/infrastructure/trader_lab/vt08_cognitive_5m_consumed_gate_v1.py
- src/qore/infrastructure/trader_lab/vt08_5m_a_to_b_candidate_readiness_v1.py
- src/qore/infrastructure/trader_lab/vt08_5m_b_methodology_spec_boundary_v1.py
- src/qore/infrastructure/trader_lab/vt08_5m_b_independent_real_lineage_audit_v1.py
- src/qore/infrastructure/trader_lab/vt08_5m_b_independent_three_family_receipt_audit_v1.py
- src/qore/infrastructure/traders/vt08_cognitive_*.py

**Tests/workflows:** tests/infrastructure/trader_lab/test_vt08_cognitive_5m_consumed_gate_v1.py; tests/infrastructure/trader_lab/test_vt08_5m_a_to_b_candidate_readiness_v1.py; test_vt08_5m_b_methodology_spec_boundary_v1.py; tests/infrastructure/traders/test_vt08_cognitive_v1_*.py. Workflows .github/workflows/vt08-cognitive-5m-research-bridge.yml, vt08-b-independent-source-rule-spec-boundary.yml, vt08-b-independent-three-family-fvg-m15-receipts.yml, vt08-b-independent-c3c4-eq-asof-source-audit.yml, vt08-cognitive-5m-real-a-lineage-independent.yml. La suite general deja 3 SKIPPED cuando no existe VT08_ARCHITECT_A_FROZEN_MODULE; son precisamente los 3 tests que sí pasan en paso posterior de integración A atado a SHA. Verificar pinned SHA en workflow antes de ejecutar.

---

# 4. REGISTRO DE PROBLEMAS P0 QUE DEBE SOLUCIONAR EL SUCESOR

### Fuente / metodología (Arquitecto A, revisión independiente B)
1. **Referencia de swing EQ antes C2:** valid swing / relevante autor no se demuestra con pivot retrospectivo ni extremo final de C2. Adjuntar source_bar_id, sha256, closed_at y available_at anteriores a apertura C2 para la decisión WITH/AGAINST. Si imposible => D / NO_ESPECIFICABLE para esa familia.
2. **POI relevante por familia y prioridad:** FVG, high/low, OB/breaker, PS y CISD retest aparecen en fuentes, pero falta selector/tie-break EXACTO y observable ANTES de entrada. No FVG-only universal por comodidad; 129 proxy M15 no proyecta densidad real.
3. **CISD y PS reales:** serie de velas opuestas, primer OPEN, cierre beyond, protected swing, ventanas de cierre por familia. 495 receipts prueban geometría, NO la discrecional relevancia del autor; M3 vs M15 relojes independientes.
4. **Breaker low real y SL:** el ejemplo LONG pide stop debajo EQ 30M y breaker-low, SL < min(EQ, breaker_low), con tick/buffer broker justificado. Un patrón de cuatro velas M3 NO autentica breaker.
5. **Target HTF untouched:** múltiples highs/POI potenciales, prioridad no especificada, fuentes y clocks; no elegir el que alcanza TP tras mirar futuro ni imponer 2R siempre.
6. **Doble barrido C2:** 105 en censo H4 (80 dentro Owner) siguen D, exclusión QORE solo documentada; M30 dual aparte; no usar último CISD a posteriori.
7. **C3 intracycle:** no usar full-H4 C3 EQ antes del cierre; no sobrerregular familia C3 con swing PRE-C2 salvo que usa explícitamente dicho régimen.
8. **Source day NY / bias / 13NY / una operación:** auditar 3.987 C2, 2.071 bias, 1.347 dual y otros first-fail; restricciones SOURCE, OWNER y QORE diferentes. Timezone 17NY source-day y 01/05/09 Owner.
9. **Seis entry families, cinco stops, H4 lifecycle:** revisar 4H PO3 R3.2/R3.9, salida posición FILLED vs expiry orden pendiente, parcial/trailing si y solo si fuente; no abarcar variantes sin preregistro y evidencia A.
10. **Prueba final1 cerrada:** issue #787 CLOSED/SUPERSEDED; NO revivir el mismo test/cambiar mercados para salvarlo. Nueva versión requiere Owner y dataset legítimamente no visto.

### Cognitiva / calidad / persistencia (Arquitecto B)
11. **Faltan 27+ campos Situation físicos** con bar SHA/available_at/semantic status A/B/C/D; ahora gate real falla cerrado por falta de acuerdo. Un booleano formal y SHA 64 chars no autentican origen.
12. **APPROVED_A_B_MANIFEST_SHA256=None:** falta spec TEXTUAL autor, pruebas B independientes, hash inmutable y dos validadores distintos. A no puede escribir sus propios tests y aprobarlos como verificación independiente.
13. **Ingesta REAL obligatoria:** prohibir bypass de evaluate_provenanced() vía evaluate() sintético; recorrer módulos y jobs futuros, test negativo anti-bypass y exhaustividad.
14. **Ledger solo en RAM:** falta WAL/SQLite event source o equivalente, crash/restart, idempotencia fill/terminal, duplicados y race multi-market, orden absoluto, no resurrection ni doble fill en segunda sesión del proceso.
15. **Primer SL/TP no autentificado:** congelación B solo comprueba consistencia longitudinal, no el fill broker ni stop/target original. Verificar external source SHA y costes, qty no entra en certificación edge del Trader.
16. **Cobertura cognitiva real:** nunca se midió 100% real candidate decisions y 100% required in-trade assessments a cada snapshot; no sabemos número real de falsos ABSTAIN, WAIT expired, ganadoras bloqueadas, DD y PF cognitiva.
17. **Memoria y adversarial futuro:** fuzzing de errores de input, bar timing, cache poisoning, reordenamiento y corrupt hashes; CI positiva ≠ ausencia total de fallas ni confiabilidad de razonamiento a precio real.

### Datos / ejecución / ciencia (Arquitecto científico C)
18. **BID/ASK y comisiones históricas en ambos lados** de cada entrada, stop, TP: M3/M15 OHLC ≠ fills físicos; slippage/swap, broker symbol alias, tick, spread stale/crossed, STOP-FIRST bound honesto; tarifa ficticia 0,10R NO se presenta como NET físico.
19. **Custodia original 1095d/M3**: artifacts GitHub expiran; exigir backup, restore SHA, source provider, ventanas, clock. Holdout 7Y intacto: no tocar ni usar para tuning sin acta y autorización.
20. **No suficiente validación económica VT08+A+B:** el único PF calculado es del PROTOTIPO QORE fallido. Falta A/B pareado metodología-only vs metodología+cognitiva, mismos eventos, quotes y costos, frozen as-of, sin sizing.
21. **Gates numéricos en conflicto:** se hallaron umbrales históricos PF1.80/DD6R y ensayo final1 PF1.15/100 fills, y Alpha PF1.40/1.30/1.20. Resolver vigencia por identidad VERSIONADA y Owner ANTES de test nuevo, nunca escoger luego el fácil.
22. **Sharpe / Sortino no definidos numéricamente para nuevo VT08:** fijar frecuencia de returns, MAR/risk free, anualización, período sin trades, manejo denominator=0, confianza/error y umbral aprobados. No inventar Sortino>=1.5 o DD%<=20 si no existe acta VT08.
23. **No-sizing estricto:** PF, expectativa y DD del método se expresan en resultados por riesgo inicial 1R homogéneo; no variar peso por market/trade, no compounding, no portafolio para “rescatar” drawdown. DD% exige curva y nominal fijado ANTES, que se reporta como traducción diagnóstica, no lotaje trader.
24. **Robustez y potencia:** n fills reales por mercado/año, OOS, walk-forward, Monte Carlo/bootstrap por bloques, sensibilidad a spreads, subperiodos, ganadores extremos, PF/Sortino/Sharpe periódicos. Insuficiencia de fills/cobertura -> NO_EVALUABLE, no falso PASS.

---

# 5. GATES — FUENTES OFICIALES Y NUEVA MATRIZ PROPUESTA

**Trader Lab canónico** [QORE-TRADER-LAB-001](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md): RESEARCH → REPLAY → FAST_FORWARD → OOS → STRESS → MONTE_CARLO → RISK_REVIEW → CIBO_REVIEW → INDEPENDENT_VALIDATION; evidencia económica exacta obligatoria. CODE_GREEN != DEMO_ELIGIBLE, DEMO_ELIGIBLE != PROFITABLE. Risk/CIBO/independent evidence externas no se automintan.

**Valores HISTÓRICOS de VT08 [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762) + [handoff A 10-Oct](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-cognitive-expansion-5m-v1-001/docs/research/VT08_5M_ARCHITECT_A_METHODOLOGY_SOURCE_FIDELITY_DENSITY_MASTER_HANDOFF_2026-10-10.md)**: PF igual-riesgo >=1,80; DD observado <=6R; mean R>=0; Monte Carlo p95 DD <=15R; probabilidad MC terminal positiva >=0,90; estabilidad por temporalidad, mercados y anclas, stress. El Owner **RETIRÓ** mínimo 50 trades/2Y, exige nuevo criterio de densidad acordado ANTES de OOS.

**Gate ensayado FINAL1 #787** (otra configuración y alcance, cerrado): al menos 100 fills físicos; PF NET >1,15; expectancy NET positiva; fuente y tarifas reales A+B. Es GO de un test muy concreto, no certificación general ni sustituto del Gate PF1.80 legado. No abrir ese mismo holdout de nuevo.

**QORE-alpha #798 (otra identidad)**: PF Train>1,40 con >=50; Valid>1,30 con >=25; DD<20%; Test>=1,20; y paper 3m >1,20. NO IMPORTAR esos Gates a VT08 sin acta Owner. Tampoco se evaluó económicamente Alpha por cobertura/autenticación de datos.

**NUEVA DIRECTIVA OWNER 14-Oct** = VT08 requiere metodología+cognitiva, PF/DD/Sortino/Sharpe y Gates de Trader Lab. El umbral numérico NUEVO para Sharpe, Sortino, densidad y DD% **no fue acreditado en fuentes específicas de VT08 verificadas en este corte**. Dejar PENDING_OWNER_NUMERIC_FREEZE; si el sucesor encuentra norma posterior, deberá citar su archivo exacto, SHA/fecha, versión y resolver conflicto, no asumir universalidad de una cifra de otro trader.

| Gate nuevo VT08 | Requisito comprobable | Estado real |
|---|---|---|
| M0 Autor | regla A por familia POI/swing/EQ/CISD/PS/entry/SL/TP/lifecycle, ejemplos y as-of replicable B; D bloquea entrada afectada | BLOCKED |
| C0 Cognitiva | 100% real-source por evaluate_provenanced, memoria/meta/adversarial/hypothesis/journey/position y fill/terminal trazables, anti-leak/restart tests | RESEARCH CODE PASS / REAL BLOCKED |
| X0 Física | quote BID/ASK, comisiones, contratos, stop/target, fill vs no-fill, costo net realista sin inventos | NOT MEASURED |
| PF | PF BRUTO y NET, sum ganancias/abs suma pérdidas por fills auténticos; n=0, no-loss, no-win no se pasan como PF infinito; baseline A vs AB | NOT MEASURED en VT08 completo |
| DD | DD realizado en R de secuencia igual riesgo; DD% sólo con curva y nominal fijo previamente declarado; Monte Carlo p95 DD y worst era | NOT MEASURED en VT08 completo |
| Sharpe | returns netos PERIÓDICOS, frecuencia, risk-free, escala y manejo n insuficiente/vol=0, benchmark definido ANTES de OOS | THRESHOLD PENDING + NOT MEASURED |
| Sortino | returns netos PERIÓDICOS vs MAR previo, downside deviation incluyendo calendario/no-trade apropiado; downside cero = UNDEFINED, no certificación automática | THRESHOLD PENDING + NOT MEASURED |
| Expectancy / Win / Profitability | mean R, total R, net expectancy, payoff, WR, streak, concentration, source-causal ablations | NOT MEASURED nueva ruta |
| Densidad / estabilidad | filled trades market/year/Ny-day/anchor/side, n efectivo, tiempo y periodo OOS suficiente | NUMERIC PENDING |
| Stress/OOS/MC/WFO | congelación antes de mirar, OOS legítimamente sin consumir, broker cost stress, resampling dependiente, estabilidad mercado/periodos | BLOCKED |
| Lab Authorities | Risk + CIBO + Independent Validation, evidencias externas y permisos separados, no promoción automática por código | BLOCKED |

**VEREDICTO:** ningún ítem NOT_MEASURED/PENDING/UNDEFINED/FAIL se considera PASS. Un PF alto de OHLC/sizing no corrige D metodológico ni IA ficticia. La certificación completa exige pruebas económicas **y** cognitivas **y** fuente; jamás se reivindica rentabilidad garantizada.

---

# 6. PLAN DE EJECUCIÓN DEL ARQUITECTO ENTRANTE (ESTRICTO STOP/GO)

**P0-0 IDENTIDAD / GOBERNANZA / VERSION:** primero leer issues #762, #763, #787 CLOSED y #798 SEPARADO; verificar HEAD de ramas (nunca reusar SHAs viejos como current). Resolver con Owner en un acta VERSIONADA la nueva versión de VT08 autorizada, familia exacta y split independiente legítimo después de la prueba final1 cerrada, y los Gates únicos PF/DD/Sharpe/Sortino/densidad. No editar resultados históricos ni salvar prototipo M30M3. Se puede estudiar fuente y cognitiva sin esperar números, NO abrir OOS ni lanzar ensayo económico FINAL antes del freeze.

**P0-1 AUTOR/REGLAS (A):** preparar texto/fuentes A/B/C/D por familia, 3–5 ejemplos oficiales sin PnL ni años futuros, relevant swing anterior C2, POI, breaker, CISD/PS, EQ clock, target HTF untouched, SL bajo ambos, tiempo de entrada/orden/expiración. Source complete o NO_ESPECIFICABLE. No crear 10k shapes para esconder el bloqueo; no reoptimizar familiares/markets/sesiones por PF.

**P0-2 REVISIÓN VERDADERAMENTE INDEPENDIENTE (B):** congelar texto A y hashes originales antes de codificar tests; reconstruir desde raw M3/M15 sin llamar implementación A, incluir casos positivos/negativos y dos relojes C2/C3. Para SOURCE A, URL/cita/section/fuente primera y reviewer diferenciado; chequeos saltos DST, violaciones future, múltiples POI/swing y false negatives. Solo después revisar CandidateEvent y firma del contrato A+B (un hash no es una firma soberana).

**P0-3 COGNITIVA REAL (B):** construir 27+ CAUSAL_FIELDS con source_bar_id, SHA, as_of, available_at, market+NY, método versión, contradicciones; ingresar exclusivamente por evaluate_provenanced. Reproducir WAIT→EXECUTE, ABSTAIN→KILLED, no rearm, actual fill externo/no-fill, assessed every-bar Journey/Position, stop monotónico, terminal. Añadir WAL/ledger idempotente y test reinicio/concurrencia; no confundir TEST synthetic 196 PASS con edge.

**P0-4 FILL Y COSTES (C/Trader Lab):** elegir source BID/ASK con cobertura para instante real de entrada, SL y TP, cobrar comisiones roundtrip, slippage/swap/tick; rechazar data missing o spreads imposibles, stop-first si solo OHLC como sensibilidad no fill físico. Ejecutar **1R fijo por trade como unidad diagnóstica**, jamás sizing propio ni compounding; reconciliar cada orden/NO FILL/terminal.

**P0-5 CONTRAFACTUAL JUSTO:** mismo conjunto de CandidateEvents válidos, precios, costes y calendarios: A) metodología sola y B) metodología+cognitiva. Reportar n, WR, total R, net PF, DD R, Sharpe/Sortino períodos, leads/stalls, ganadores preservados, pérdidas evitadas y falsos bloqueos. Attribution causal, no seleção outcome-aware. No mezclar PnL de QORE-alpha o QORE PS-only con nuevo VT08.

**P1-6 ROBUSTEZ/GATES:** congelar reglas numéricas oficialmente con Owner; OOS nunca inspeccionado, WFO, stress de fees/spreads, Monte Carlo/bootstrap con bloque temporal, por mercado/época/año/ancla; no un único PF agregado como certificado. Si un gate no se puede computar, NO_EVALUABLE y documentar quién desbloquea; al fallar NO retunar mismo OOS.

**P1-7 REVISORES Y CIERRE:** A valida método, B cognitivas y fuente, C estadística/económica independiente; Trader Lab/Risk/CIBO/independent-gate autorizaciones EXTERNAS separadas. Solamente Owner orden explícita puede habilitar otra etapa; ESTE handoff no firma nada.

---

# 7. CHECKLIST DE ESTADO Y MAPA PARA NO PERDER UNA SOLA TAREA

- [x] Five FX research; 01/05/09 NY Owner; baseline 11.655/488/457 documentado.
- [x] B 488 recibos B01 autenticados por M15, 294 C3/C4 dos relojes y 495 FVG→PS receipts, universos NO sumables y aún sin fuente-candidate completo.
- [x] A/B/C/D contrato texto B, rechazo lookahead swing C2 y futuro C3; 21 adversariales PASS.
- [x] Cognitiva B robustecida y testeada: 196 PASS, 3 general SKIP justificados (los 3 A congelados PASS en job aparte); 95% coverage de módulo gate; Ruff/Mypy.
- [x] Test QORE proxy M30M3 negativo archivado, PF 0.964 y 0.895 bruto; no implicar TTrades.
- [x] Contrato FINAL1 una familia y veredictos, CI A GREEN; NO test físico final y #787 CLOSED/SUPERSEDED.
- [ ] Nueva identidad/autorización Owner VT08 fuente+cognitiva y reconciliación de Gates/cierre final1/QORE-alpha.
- [ ] Source POI/swing valid PRE-C2, EQ, breaker, target untouched, M3 CISD/PS autor por familia, bias, lifecycle y stop.
- [ ] A texto SPEC preregistrado, B aceptación independiente sin leer código A primero, 27+ atributos de Situation con raw provenance y manifest auténtico.
- [ ] Solo ruta real evaluate_provenanced, 100% cognition per entry y per in-trade snapshot y terminal físico; idempotencia/restauración/concurrencia.
- [ ] BID/ASK y comisión históricos en ambos lados, datos permanentes SHA restaurable, coste net verificado.
- [ ] Igual 1R, metodología-only vs metodología+cognitiva, PF y DD R, Sharpe/Sortino periódicos y thresholds Owner, sin sizing/leverage/compounding.
- [ ] OOS legítimamente independiente, WFO/bootstrap/MC/stress, estabilidad, sample y densidad suficiente; reviewer económico independiente.
- [ ] TODOS los Gates PASS y permisos externos de Lab/Risk/CIBO/Independent Validation, nada autorizado LIVE sin orden.

**Archivos/documentos de continuidad INDISPENSABLES:**
- [P0 Cognitiva 196 PASS y defectos corregidos](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_5M_COGNITIVE_P0_HARDENING_QUALITY_GATE_2026-10-10.md)
- [Auditor de fuente A/B/C/D y 129/36/105 proxies](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_5M_B_AUDITOR_CLOSING_ROUND_SOURCE_FIRST_A_B_CONTRACT_2026-10-10.md)
- [495 source-receipts y corrección EQ C3](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_5M_B_INDEPENDENT_THREE_FAMILY_495_RECEIPTS_AND_INTRAC3_FUTURE_EQ_2026-10-10.md)
- [Metodología y antiguo Gate VT08 PF1.80/DD6R](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-cognitive-expansion-5m-v1-001/docs/research/VT08_5M_ARCHITECT_A_METHODOLOGY_SOURCE_FIDELITY_DENSITY_MASTER_HANDOFF_2026-10-10.md)
- [A NO-GO prototipo con 3561 madres](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_M30M3_ECONOMIC_FALSIFICATION_NO_GO_PROXY_REPORT_2026-10-11.md)
- [A FINAL1 prereg y 3 veredictos](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-methodology-source-20261010/docs/research/VT08_A_FINAL1_AUDITOR_TRI_VERDICT_CAUSAL_GATE_AND_STOP_ORDER_2026-10-11.md)
- [Trader Lab canónico](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md)
- [Ci B cognitiva #38104698708](https://github.com/mezas3238-hue/qore-core/actions/runs/38104698708), [CI B regla #38103823100](https://github.com/mezas3238-hue/qore-core/actions/runs/38103823100), [CI B 495 #38103539460](https://github.com/mezas3238-hue/qore-core/actions/runs/38103539460), [CI A economía #38160918903](https://github.com/mezas3238-hue/qore-core/actions/runs/38160918903).

**MENSAJE AL ARQUITECTO A:** especifica fielmente lo que un humano TTrades sabría antes de cada acción; no generes señales sin swing/POI/breaker/target autor autentificados; el QORE proxy NO-GO queda frozen.

**MENSAJE AL ARQUITECTO B:** construye cognition TRUE-INPUT en todos los campos, ledger resiliente, no bypass ni PnL memoria, full causal post-entry y tests de recuperación; no llama certificado a CODE_GREEN.

**MENSAJE AL ARQUITECTO C:** económicamente cuantifica PF/DD/Sharpe/Sortino NET con misma exposición en R, quote/fees auténticos y OOS limpio; cero sizing; arbitra Gates POR VERSIÓN y nunca mezcla Alpha/FINAL1/B01/Proxy.

**PRINCIPIO RECTOR:** AUTENTICAR FUENTE → VERIFICAR COGNITIVA CON DATOS VERDADEROS → MEDIR ECONOMÍA SIN SIZING → GATES PRECONGELADOS + OOS → EVALUADOR INDEPENDIENTE → PROPONER CERTIFICACIÓN. No se promete rentabilidad; si fuente no es causalmente escribible o OOS insuficiente, documentar NO_EVALUABLE y preservar custodia. Ninguna afirmación de este handoff sustituye una ejecución económica nueva.

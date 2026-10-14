# QORE CORE — VT08 CRT PURE
# HANDOFF MAESTRO DE CONTINUIDAD Y CERTIFICACIÓN — 14 OCT 2026

## ORDEN VINCULANTE OWNER — CERTIFICACIÓN SIN SIZING (RATIFICADA 14-OCT-2026)

**ESTÁ ABSOLUTAMENTE PROHIBIDO USAR SIZING PARA CERTIFICAR VT08**, no solamente en producción sino en **todos los Gates de certificación G-M1, G-M2, G-M3, G-M4 y G-M5**. Esta ratificación prevalece sobre cualquier redacción ambigua de este handoff y del histórico.

- **NUNCA** introducir ni calcular en VT08 o en su prueba certificadora lotes, tamaño de posición, volumen, unidades de contrato, capital operativo, balance de cuenta, porcentaje de riesgo, apalancamiento, multiplicadores de capital, optimización de asignaciones o performance condicionada a sizing.
- La certificación propia del trader es **exclusivamente de metodología original documentada, interpretación cognitiva, causalidad, decisiones EXECUTE conceptual / WAIT / ABSTAIN, no leakage, robustez de su identidad y cumplimiento del contrato**. La métrica de acierto/edge **sin tamaño de posición**, si se investiga en otro expediente, tampoco sustituye ni desbloquea la certificación cognitiva.
- **CIBO/QORE Risk es el único soberano de sizing y volumen**; no trasvasar su cálculo al trader ni hacer de sus parámetros un criterio para declarar VT08 certificado. Las pruebas de integración G-M4 deben comprobar **ausencia de autoridad de sizing en VT08** y delegación efectiva al módulo soberano, no ejecutar o recomputar sizing para obtener PASS.
- Si un test, runner, certificador o propuesta exigiera sizing para aprobar al trader: **FAIL_CLOSED / TEST_INVALID**, registrar causa y reparar separación de responsabilidades. No ajustar la regla, no usar sizing simulado, no renombrarlo como capital normalizado o riesgo en R para eludir la prohibición.
- Los reportes históricos en **R** son caracterizaciones **legadas** de resultados brutos, no decisiones de tamaño ni parte de los Gates G-M1..G-M5. **No** efectuar nuevas simulaciones de riesgo monetario en el trabajo de certificación.
- La certificación global y cualquier validación económica **son expedientes separados**, pendientes de autorización; jamás exigir que VT08 mismo calcule lotes o riesgo. **Un PASS cognitivo no autoriza órdenes DEMO/LIVE.**

**En caso de conflicto entre metodologías, CI, documentación antigua y esta directiva del Owner, aplicar la prohibición y mantener VT08 NO CERTIFICADO hasta completar sus Gates sin sizing.**


**REPOSITORIO SOBERANO:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core)  
**PR #626:** [VT08 CRT PURE — source identity + hybrid cognitive foundation](https://github.com/mezas3238-hue/qore-core/pull/626)  
**RAMA:** agent/vt08-crt-pure-source-identity-001  
**HEAD inspeccionado antes de este documento:** c35efdac180fc78424d3fc7e1c34555e07d729ba  
**PR OPEN/DRAFT, SIN MERGE; DEPLOYMENT AUTHORITY NONE.**

**NOTA ESENCIAL:** este handoff es el índice actualizado y operativo. El [handoff histórico exhaustivo del 13 de octubre](VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md) tiene más de 50.000 caracteres y documenta R1 y todas las familias R2 hasta CD, resultados y scripts; conservarlo como volumen técnico, no sustituirlo. La [misión Owner de G-M1 a G-M5](VT08-CRT-PURE-OWNER-NONQUANTITATIVE-CERTIFICATION-MISSION-2026-10-13.md) tiene precedencia para la certificación metodológica/cognitiva. El Owner permitió posteriormente replays de investigación delimitados; NO autorizó nueva optimización libre ni órdenes.

## 0. ORDEN Y GOBERNANZA INALTERABLES

**OBJETIVO:** reconstruir metodología CRT auténtica de RomeoTPT, identificar qué reglas proceden de SpeculatorFL/TraderFlameseN frente a ingeniería QORE; certificar la cognición del trader sobre casos de mercado **reales, causales, positivos, negativos y ambiguos**, con capacidad auditable para EXECUTE conceptual, WAIT o ABSTAIN. Separar certificado metodológico de certificado GLOBAL rentable/operativo.

- **NO MERGE** sin autorización expresa. NO LIVE, DEMO, PRODUCTION, VPS, FUNDedNext LIVE, capital real, ejecución MT5 ni publicación de señales operativas.
- **PROHIBICIÓN ABSOLUTA DEL SIZING EN VT08:** el trader NO decide lotaje, tamaño, volumen, riesgo porcentual, capital, apalancamiento, presupuesto financiero ni multiplicadores. CIBO/QORE Risk gobierna exclusivamente capital y tamaño. Toda prueba permanece en unidades de observación, y la economía histórica solo como R/trade en investigación.
- NO hindsight, NO leakage M5/M15/H4, NO resurrección de la misma hipótesis KILLED, NO entrada fallback tras ABSTAIN y NO cambiar stop/TP para obtener mejor PF.
- BTCUSD conserva el freeze de nuevas investigaciones, aunque hay expedientes económicos históricos. No confundir certificación de investigación BTCUSD antigua con certificado global VT08.
- Las memorias de mercado AUDUSD, USDJPY y BTCUSD son independientes. No importar reglas o experiencia económica de un mercado al otro.
- **Regla de lenguaje:** patrón CRT observado ≠ candidato causal independiente ≠ operación económica ≠ edge ≠ certificado.

## 1. FUENTES, FIDELIDAD, Y BRECHA METODOLÓGICA

**Tier A: RomeoTPT, fuente original.** [Fundamentos](https://www.youtube.com/watch?v=UUq_wKQ61Wo), [Model #1/OTE](https://t.me/s/officialRomeotpt/6184), [old CRTH](https://t.me/s/officialRomeotpt/6615), [50% y CRT incompleto](https://t.me/s/officialRomeotpt/6455). [Acta de cierre Model #1](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md): la relación de investigación H4 CRT→M15 Model #1, un old high/low preexistente, barrido por vela fuente y confirmación de cierre corporal (mecha sola NO confirma), riesgo estructural extremo fuente. **La fuente A NO ha cerrado el selector entre varios old highs/lows, la edad/mitigación del nivel, el orden entre referencias, DOL definitivo, vencimiento universal ni el M5 trigger de nuevas familias**.

**Tier B: SpeculatorFL.** [CRT macro/micro](https://threadreaderapp.com/thread/1784493604473618604.html), [Conformational vs Advanced](https://threadreaderapp.com/scrolly/1794311615535518154); describe esperar confirmación tras segunda vela para estudiar tercera/posteriores y bajar otra temporalidad. Concepto inspirador, NO definición exacta atribuible a Romeo.

**Tier B dependiente: TraderFlameseN.** [Thread](https://threadreaderapp.com/thread/1790141530461622525.html); describe CRT anidados, pero coincide sustancialmente con SpeculatorFL y NO es segunda validación independiente.

**Problema P0 de software:** strategy_identity_ready()==True en la capa de estrategia general NO demuestra selección Model #1 fuente cerrada. En crt_pure_source_registry.py MODEL_1_REFERENCE_SELECTION permanece AMBIGUOUS y está fuera del conjunto CRT_PURE_CORE_EXECUTION_CONCEPTS de readiness general. No declarar G-M1 PASS ni cambiar silenciosamente la semántica del booleano heredado. Ver [auditoría G-M1](VT08-CRT-PURE-CERTIFICATION-PRIMARY-SOURCE-EXAM-GM1-2026-10-13.md).

**Línea fuente no equivalente:** N1 esperaba cierre de micro-C3 M15 y luego observar micro-C4 M15; el protocolo confirmacional de SpeculatorFL considera confirmación tras C2 y examina actividad en C3, eventualmente en TF inferior. [Acta de discrepancia](VT08_CRT_PURE_SOURCE_GM1_NESTED_C3_C4_AND_LOWER_TIMEFRAME_GAP_2026-10-14.md). N3/N3B estudian esa ventana M5 causalmente, NO prueban gatillo certificado.

## 2. DATOS HISTÓRICOS Y PROCEDENCIA: NO VOLVER A BUSCAR DUKASCOPY

El Owner tenía razón: QORE ya conserva millones de velas en **GitHub Actions artifacts**, no necesariamente en el árbol Git.

- **12 originales Atlas M5:** [Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), identidad CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1, productor ab782b8e9f890f86a2b6500070f0556b4b685e3d. AUDUSD artifact 10475697610; USDJPY 10475389415. Los manifests y SHA por año 2024, 2025, 2026 se verifican antes de procesar. El dataset termina 2026-09-17 excluyente, cuatro días antes del extremo del antiguo replay R2-C.
- **Ampliación 21 M5:** [Actions #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541). [Acta QORE Native G0 33](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-final33-tail-ready-g0-20261012/docs/research/QORE_NATIVE_FULL_33_MARKETS_G0_EXECUTED_FINAL_2026-10-12.md): 24.377.420 M5 entre 33 instrumentos, con posibles fuentes/brókers distintos; NO asumir que los 33 son el universo ya autorizado de VT08.
- **Corpus usado efectivamente en rondas recientes:** AUDUSD 148.171 + USDJPY 148.201 = **296.372 M5 originales**, aproximadamente 2024-09-20→2026-09-16, lecturas con SHA anual. **Esta época NO es holdout virgen.** No tiene cadena de fills BID/ASK históricos para asegurar PF neto broker real.
- Hay M1 AUDUSD y USDJPY en [Actions #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), pero NO fueron consumidas en N3/N3B; no atribuirles precisión que el replay M5 no posee.
- Lector exacto: src/qore/infrastructure/trader_lab/vt08_crt_pure_original_atlas_reader.py, bajo workflow .github/workflows/vt08-crt-pure-three-source-insidebar-replay.yml, descarga autorizada solo lectura de GitHub Actions, sin login de operaciones cTrader.
- **Issue de custodia [#837 Data Vault](https://github.com/mezas3238-hue/qore-core/issues/837)**: los artifacts expiran; verificar vencimientos y hacer respaldo duradero autorizado antes de que desaparezcan. No llenar commits con millones de barras.

## 3. ARQUITECTURA COGNITIVA EXISTENTE Y ERRORES YA CORREGIDOS

La rama contiene MASTER_BRAIN, GLOBAL_WORLD_MODEL, MARKET_BRAINS, DATA_PERCEPTION_INTEGRITY, CRT_STRATEGY_IDENTITY, CIBO_MARKET_MEMORY, CRT_EXPERIENCE_MEMORY, ATTENTION, CAUSAL_SITUATION_MODEL, HYPOTHESIS_LIFECYCLE, CROSS_MARKET_CAUSALITY, OPPORTUNITY_COMPETITION, UNCERTAINTY_METACOGNITION, ADVERSARIAL_REASONING, DECISION_SOVEREIGNTY, JOURNEY_DESTINATION_INTELLIGENCE, POSITION_INTELLIGENCE y COGNITIVE_AUDIT. Contratos centrales en src/qore/infrastructure/traders/crt_pure_cognitive_state.py, crt_pure_cognitive_contract.py, crt_pure_r2_entry_router.py, crt_pure_strategy_identity_memory.py, crt_pure_certification_readiness.py.

Las decisiones conceptuales EXECUTE/WAIT/ABSTAIN y el conocimiento KNOWN/PARTIAL/UNKNOWN/CONFLICTED NO deben producir probabilidad ficticia. QC-002 corrigió un caso en que PARTIAL podía tratarse como WELL_SUPPORTED/EXECUTE; debe permanecer WAIT. QC-003 agregó testigo causal, pero **es auxiliar**, no gate nuevo. [QC-002](VT08-CRT-PURE-QUALITATIVE-COGNITIVE-SOURCE-CODE-AUDIT-QC002-2026-10-13.md) y [QC-003](VT08-CRT-PURE-QUALITATIVE-CAUSAL-SOURCE-WITNESS-QC003-2026-10-13.md).

**Rondas históricas R1/R2-A…CD:** el [handoff completo anterior](VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md) contiene scripts, runs, cronología y resultados. No volver a experimentar filtros falsados sin nueva hipótesis de fuente:
- AUDUSD R2-AO tenía ~1.465 trades/6 años (~244/año), PF bruto ~0,999: **densidad sí, edge no**. R2-BE 15 años candidato overlap PF bruto ~1,0668, a costo 0,05R dejó de ser robusto.
- Error simulator R2-BM: la primera versión atribuía TP anterior a SL dentro misma M15, inflando PF ~1,1189; el runner corregido usa STOP_FIRST por misma M15. Run correcto 36055427737: PF bruto ~1,019, a costo 0,02R PF ~0,976; **nunca citar PF inválido**.
- BTCUSD histórico: familia intersectada tuvo reporte PF ~1,803 en 130 trades a lo largo de ~8 años, investigación de mercado solamente. Hoy mercado FROZEN: no reactivar sin orden.
- Cognitive Experience R2-BY/BZ demostró separación de ABSTAIN tóxico; WAIT tenía información útil. R2-CA/CB testearon el camino causal de la primera M15. R2-CC [run 36173116494]: AUDUSD ~1.067 trades, 97/año, PF bruto 1,07424, DD 17,01R; a supuesto costo 0,02R PF 1,01741. R2-CD [run 36173125334]: USDJPY 511 trades, ~63,875/año, PF bruto 1,01154 y DD 15,16R; a costo 0,02R PF 0,96054. **No representan rentabilidad robusta global ni deben confundirse con nuevos N3.**
- Falsaciones/insuficiencias históricas: rescate CISD/FVG/OTE ingenuo, RR universal, passive price como edge, segunda entrada terminal como remedio, filtros amplios DOA/Expected-R, selección retrospectiva de slots/ref/días y confundir crédito causal WAIT con reentrada rentable. No copiar economía AUDUSD a USDJPY.

## 4. ESTUDIOS RECIENTES, RESULTADOS VERIFICADOS Y LÍMITES

| Fase | Fuente de verdad / run | Hallazgos reales | Qué NO demuestra |
|---|---|---|---|
| R2-C + inside bars Level B | [CI #38546723415](https://github.com/mezas3238-hue/qore-core/actions/runs/38546723415), [acta](VT08_CRT_PURE_ORIGINAL_QORE_NATIVE_M5_INSIDE_BAR_REPLAY_RESULT_2026-10-14.md) | AUDUSD control 69 trades PF bruto ~1,025, inside 59 PF ~1,106. USDJPY control 64 PF ~0,864, inside 58 PF ~0,984. Histórico QORE de esta ventana, no igual a datasets viejos | No significa CRT solo produzca 30 trades/año, ni inside-bar regla Romeo |
| Auditoría densidad H4/M15 | [CI #38548265594](https://github.com/mezas3238-hue/qore-core/actions/runs/38548265594), [acta](VT08_CRT_PURE_DENSITY_RESTUDY_SOURCE_FIDELITY_AND_M5_CENSUS_2026-10-14.md) | 1.460 ventanas programadas/activo; AUDUSD 854 completas→287 parent TS→69 trades; USDJPY 877→265→64. FIRST_SOURCE_ONLY es QORE ingeniería restrictiva | No catálogo completo CRT; no convertir otras sources en trades |
| Forense 88 antiguos | [CI #38578534918](https://github.com/mezas3238-hue/qore-core/actions/runs/38578534918), [acta](VT08_CRT_PURE_88_CASES_REAL_M5_PREENTRY_FORENSIC_VERDICT_2026-10-14.md) | 47+41=88 padres descartados; 120 alternativas posteriores; 111 tenían cierre fuera lado barrido de C1 antiguo y 9 tenían midpoint antiguo tocado; flags QORE | 88 entradas recuperables ni veto original Romeo |
| N1 M15 anidado | [PREREG](VT08_CRT_PURE_NESTED_M15_SOURCE_PREREG_2026-10-14.md), [CI #38602113794](https://github.com/mezas3238-hue/qore-core/actions/runs/38602113794), [reporte](VT08_CRT_PURE_NESTED_N1_ORIGINAL_M5_REPLAY_RESULT_2026-10-14.md) | 939 patrones (521 AUDUSD/418 USDJPY), 479 parents H4 con alguno; 468 alineados/471 contrarios; análisis posterior 64 N1 en 57 H4 | No es Model #1 autentificado, no 939 trades |
| N2 caso-a-caso | [PREREG](VT08_CRT_PURE_N2_57_CASEBOOK_PRE_REGISTRATION_2026-10-14.md), [CI #38603974795](https://github.com/mezas3238-hue/qore-core/actions/runs/38603974795), [reporte](VT08_CRT_PURE_N2_57_CONTEXTS_CAUSAL_SOURCE_AND_OVERLAP_RESULT_2026-10-14.md) | 57 H4 y 64 patrones; 50 H4 con uno, 7 con 2 disjuntos, 37 H4 con señal N1 opuesta; todos los 64 cruzan midpoint propio al C3; 42 tocaron wick del far; 51 rebarrieron C1-H4 | No prueba independencia de tesis, destino intacto ni permiso entrada |
| N3 reloj C2 M15→M5 C3 | [PREREG N3](VT08_CRT_PURE_N3_C2_CLOSE_M5_CAUSAL_BRIDGE_PREREG_2026-10-14.md), [CI #38608270651](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651), [resultados](VT08_CRT_PURE_N3_N3B_M15_C2_TO_M5_C3_ORIGINAL_DATA_RESULTS_2026-10-14.md) | 2.634 C2 (1.374 AUDUSD/1.260 USDJPY) barrido unilateral+retorno; 1.314 aligned H4/1.320 opposite; N1 939 reconciliados; 1.109 M5 closes lado midpoint slot1/2 antes M15-C3 final; 540 C2 ya beyond; 422 mismo M5 wick-far + close-mid intrabar orden desconocido | Ningún C2 ni M5 es trigger source-approved/entrada |
| N3B nueva información PIT M5 | [PREREG N3B](VT08_CRT_PURE_N3B_NEW_INFORMATION_M5_PREREG_2026-10-14.md), [mismo run](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651) | 722 cierres M5 realmente nuevos respecto a C2, 541 sin extremo far tocado al cierre M5; intersección exploratoria alineación H4+target H4 intacto: 95 eventos en 83 H4. N3B prereg luego de observar N3 inicial | No OOS independiente, no 95 trades, no edge ni PF |

**ÚLTIMO LAB VERIFICADO:** [CI #38608270651](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651) HEAD 3aaeef4fcbd21ca74473ec274510b4657c14cd94; **quality + AUDUSD + USDJPY = SUCCESS**, Ruff/Mypy, **60/60 pytest**. Artifacts SHA: [AUDUSD #11917121744](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651/artifacts/11917121744) y [USDJPY #11916482628](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651/artifacts/11916482628) con n3-c2-m5-summary.json / n3-c2-m5-ledger.jsonl / SHA256SUMS.txt. HEAD antes del handoff c35efdac... tenía Cognitive Gate GREEN; commits más recientes deben reevaluarse.

**Código último:** src/qore/infrastructure/trader_lab/vt08_crt_pure_three_source_insidebar_replay.py, vt08_crt_pure_density_root_cause_audit.py, vt08_crt_pure_later_source_forensics.py, vt08_crt_pure_nested_m15_census.py, vt08_crt_pure_n2_57_casebook.py y vt08_crt_pure_n3_c2_m5_causal_clock.py, con tests homónimos en tests/infrastructure/trader_lab y workflow nombrado arriba.

## 5. TODOS LOS PROBLEMAS PENDIENTES Y CÓMO RESOLVERLOS

| ID | Problema verificable | Trabajo preciso / criterio de cierre |
|---|---|---|
| P0-01 | MODEL_1_REFERENCE_SELECTION aún AMBIGUOUS; old CRTH/CRTL no tiene selector autorizado | Leer videos originales Romeo y capturar minuto/ejemplo para selección entre varios niveles, edad, mitigación, ownership; separar AUTHOR_RULE de QORE_ENGINEERING; si fuente no resuelve, registrar UNKNOWN y pedir excepción **explícita Owner**, no usar PF |
| P0-02 | N1/N2 observa C3→C4; SpeculatorFL confirmational plantea cierre C2 y trading C3 o posterior | Cerrar equivalencia metodológica exacta por fuente y gráfico; nunca renombrar N1 Model #1 |
| P0-03 | N3/N3B muestra reloj M5 pero NO entrada M5 original | Especificar y justificar con fuente M5 trigger, cuerpo/cierre, estados WAIT y validez temporal, alternativa CSD/MSS solo si verdaderamente está en la familia elegida |
| P0-04 | DOL/target: 64/64 midpoint propio N2 ya consumido, 42 far wick tocado; N3B far untouched no es permiso | Localizar PD array, old level y destino con ownership; probar que objetivo sigue por delante en instante de decisión; no mover TP para inventar retorno |
| P0-05 | Contradicciones micro/macro y rearm: 37/57 H4 con opuestos; 88 padres no rehabilitables automáticamente | Arbitraje de prioridad y lifecycle por evidencia original; claves de hipótesis independientes; KILLED→terminal, hipótesis verdaderamente nueva solo con nuevo antecedente causal |
| P0-06 | Falta auditoría G-M2 real **vela por vela contra autor original**, aunque ya hay datasets y JSONL | Preparar expediente cronológico pre-resultados de casos positivos, negativos, agotados, múltiples y ambivalentes; chart M5/M15/H4 con SHA fuente + NY/DST; revisión ciega |
| P0-07 | Cognitiva G-M3 parcial: tests unitarios/sintéticos no prueban interpretación de casos reales | Comparar salida situation model, metacognición, adversarial y WAIT/ABSTAIN con veredicto metodológico por caso; registrar divergencias y causas |
| P0-08 | Integración G-M4 parcial: riesgo de fallback, old-level incorrecto, doble trade y sizing prohibido | Auditoría end-to-end de router, no C3-open fallback, no force rearm, C3 expiry, competencia de hipótesis, AISLAMIENTO mercados, no lotes/riesgo Trader, CIBO external |
| P0-09 | strategy_identity_ready TRUE no contempla todos los conceptos Model #1 | Diseñar source-family-specific readiness para G-M1/G-M5, sin alterar booleano global y tests legacy sin auditoría de impacto |
| P0-10 | Lookahead, OHLC intrabar ambiguo (422 casos N3 same M5) | Usar prefijos causales y M1/tick **solo si existe datos de fuente verificable y permiso**; donde no se conoce secuencia no inventar fill; STOP_FIRST en simulación conservadora |
| P1-11 | R2-C demasiado restrictivo, 2 triples H4 al día y first source only | Documentar horarios y familias con fuente original; no recuperar 88 por simple densidad ni extrapolar 69/64 a todo CRT |
| P1-12 | Edge global no demostrado, USDJPY costes negativos y AUDUSD estrecho, N3B exploratorio no OOS | Solo tras orden de fase económica y método congelado: candidato único, pre-reg, OOS limpio, BID/ASK/comisiones/fill, PF NETO, DD, stress, WFO, MC, slippage y capacidad |
| P1-13 | GitHub artifacts caducan; datos reales pueden perderse | Resolver issue #837 preservando fuente, manifest, hashes, versión y retención; NO VPS ni gastos o push masivo no autorizados |
| P1-14 | Alcance tres mercados con BTCUSD congelado y global certificate all_market_history_verified | Solicitar decisión Owner sobre alcance global si fuese necesario, no cambiar contrato ni declarar certificado por dos FX |
| P1-15 | Viejos resultados/pipelines fallidos y datos externos sustituidos | Mantener registro de correcciones: simulador STOP_FIRST; tests fixtures; acceso cTrader sin permisos; GetData abandonado; diferenciar historial 2011–2026 vs las 296.372 M5 originales, no mezclar PF |
| P1-16 | Investigación sobre conjuntos muy explorados puede dar ilusión de mejora y multiplicidad de patrones solapados | Declarar N3B segunda mirada exploratoria; construir muestreo ciego independiente, medir parents únicos y patrones sin solapamiento; no seleccionar por beneficios |

Los problemas P0 **no se dan por cerrados** con Ruff, Mypy o 60 pruebas GREEN: esos solo prueban contratos de programación y causalidad local, no fidelidad doctrinal, ventaja económica ni juicio cognitivo en gráficos reales.

## 6. GATES DE CERTIFICACIÓN: DOS CERTIFICADOS DIFERENTES

| Gate | Estado a este corte | Evidencia que falta para PASS |
|---|---|---|
| G-M1 original source/método | PARTIAL, old-level selection OPEN | Prueba primaria con localizador exacto, contratos C1/C2/C3 y Model #1, invalidación, ownership, DOL y excepción QORE rotulada por Owner |
| G-M2 reconocimiento visual real | OPEN (ledger disponible) | Casos de mercado auténticos revisitados **sin mirar futuro**, incl. falsos positivos y no trades, explicación de source y contradicciones |
| G-M3 cognición real | PARTIAL | Cada decisión EXECUTE/WAIT/ABSTAIN reconciliada con dictamen de auditoría sobre mismas velas y sin leakage |
| G-M4 integración y soberanía | PARTIAL | Flujo E2E fuente→cognitiva→router→QORE Risk con 0 capital authority en Trader, no fallback/rearm |
| G-M5 certificado metodología+cognición | NOT ISSUED | G-M1..G-M4 PASS, acta con commits, corpus, limitaciones y aprobación Owner; no autoriza LIVE |
| GLOBAL CrtPureCertificationStage.CERTIFIED | FALSE | Además de método: 3 mercados o alcance autorizado, historial verificado, deterministic replay, forensics, candidato congelado, WFO/MC/stress/slippage/robustness/fresh holdout/combined validation/full QORE |

Fuente código global: src/qore/infrastructure/traders/crt_pure_certification_readiness.py. No inventar umbrales PF/Sharpe/Sortino/DD ni bajarlos para certificar. El estado global incluso si fuese CERTIFIED no es autorización de despliegue.

## 7. SECUENCIA DE TRABAJO DEL SIGUIENTE ARQUITECTO

1. **RECIBIR:** leer este handoff, el de 13-OCT, misión Owner, Model #1 source closure, G-M1, resultado N3/N3B. Revalidar PR #626, último SHA, CI/artifacts y freezes. No merge.
2. **FUENTE ORIGINAL:** visionar videos Romeo y secundarios con minutaje; cerrar ownership old CRTH/CRTL, C2 vs C3, micro M5 trigger, invalidación, target y prioridad; producir matriz AUTHOR_RULE / SECONDARY_HYPOTHESIS / QORE_ENGINEERING / UNKNOWN. Presentar al Owner incertidumbres realmente no resolubles, sin asumir excepciones.
3. **CASOS REALES G-M2:** construir dossier OHLC de SHA originales pre-resultados con muestra previamente seleccionada de N3/N3B, 88 rechazados y N2; positivos, sin señal, opuestos, KILLED, target consumido, fuente duplicada, dos lados; registrar qué se sabía al cierre de cada vela.
4. **COGNICIÓN G-M3:** ejecutar reasoning/decision de VT08 sobre dichos prefijos, auditar porqué y contratesis vs experto fuente; reparar divergencias, no alterar metodología para obtener PF.
5. **INTEGRACIÓN G-M4:** probar router y source IDs, fail-closed, clocks NY, STOP_FIRST ambiguo, expiry, no rearm, no transferencias de memorias y prohibición de sizing; CIBO/QORE Risk sigue autoridad externa.
6. **ACTA G-M5** si y solo si G-M1..G-M4 PASS: emitir certificado estrictamente metodológico/cognitivo con versión, evidencia y aprobación Owner. De lo contrario mantener NOT_CERTIFIED_METHOD.
7. **ECONOMÍA SOLO POR ORDEN:** congelar nueva familia, datos costes originales, fresh OOS e integración completa de all gates sin mentir sobre PF; certificación GLOBAL separada y no LIVE automático.
8. **CUSTODIA:** resolver Issue #837, actualizar PR con hashes/runs/errores y este handoff tras cada etapa.

## 8. INVENTARIO DE REFERENCIAS OBLIGATORIAS

- [Handoff histórico extenso 13-OCT](VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md).
- [Misión metodológica G-M1…G-M5 Owner](VT08-CRT-PURE-OWNER-NONQUANTITATIVE-CERTIFICATION-MISSION-2026-10-13.md).
- [Model #1 Romeo original source closure](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md), [G-M1 examen fuente](VT08-CRT-PURE-CERTIFICATION-PRIMARY-SOURCE-EXAM-GM1-2026-10-13.md).
- [Comparación tres fuentes/insidebars](VT08-CRT-PURE-THREE-SOURCE-COMPARISON-REPLAY-2026-10-14.md).
- [Censo raíz baja densidad](VT08_CRT_PURE_DENSITY_RESTUDY_SOURCE_FIDELITY_AND_M5_CENSUS_2026-10-14.md).
- [88 casos rechazados](VT08_CRT_PURE_88_CASES_REAL_M5_PREENTRY_FORENSIC_VERDICT_2026-10-14.md).
- [N1 micro CRT](VT08_CRT_PURE_NESTED_N1_ORIGINAL_M5_REPLAY_RESULT_2026-10-14.md).
- [N2 57 H4](VT08_CRT_PURE_N2_57_CONTEXTS_CAUSAL_SOURCE_AND_OVERLAP_RESULT_2026-10-14.md).
- [Diferencia C3-C4 vs fuente CRT](VT08_CRT_PURE_SOURCE_GM1_NESTED_C3_C4_AND_LOWER_TIMEFRAME_GAP_2026-10-14.md).
- [N3/N3B report auditado](VT08_CRT_PURE_N3_N3B_M15_C2_TO_M5_C3_ORIGINAL_DATA_RESULTS_2026-10-14.md), [pre-reg N3](VT08_CRT_PURE_N3_C2_CLOSE_M5_CAUSAL_BRIDGE_PREREG_2026-10-14.md), [pre-reg N3B](VT08_CRT_PURE_N3B_NEW_INFORMATION_M5_PREREG_2026-10-14.md).
- [Source G-M1 cognitiva QC-002](VT08-CRT-PURE-QUALITATIVE-COGNITIVE-SOURCE-CODE-AUDIT-QC002-2026-10-13.md), [testigo QC-003](VT08-CRT-PURE-QUALITATIVE-CAUSAL-SOURCE-WITNESS-QC003-2026-10-13.md).
- [CI original N3/N3B](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651), artifacts [AUDUSD](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651/artifacts/11917121744), [USDJPY](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651/artifacts/11916482628).

**DICTAMEN CIERRE 14-OCT-2026:** VT08 CRT PURE permanece **NO CERTIFICADO**. Fase de reconstrucción fuente y cognición sin resolver, aunque infraestructura y datos M5 son suficientes para verificar situaciones reales. N3B=95 eventos/83 H4 es diagnóstico, NO nueva estrategia ni edge. **CERO nuevas órdenes y CERO sizing del Trader.** El próximo arquitecto debe cerrar el origen metodológico, juzgar las decisiones sobre casos reales y certificar G-M1…G-M4 antes de tocar economía o afirmar certificación.


## ADDENDUM DE EJECUCIÓN G-M2/G-M3/G-M4 — 14-OCT-2026 (arquitecto de continuidad)

**Ejecuciones y cambios comprobados (NO certificados de método):**

- [Auditoría completa 48 casos G-M2](VT08_CRT_PURE_GM2_48_REAL_BLIND_CASES_CAUSAL_AUDIT_2026-10-14.md), respaldada por [Actions #38617425240](https://github.com/mezas3238-hue/qore-core/actions/runs/38617425240), artifacts AUDUSD 11920048252 / USDJPY 11921035427. **48/48 prefijos M15 causalmente consistentes**, ambos ZIP verificaron todos los hashes internos. 24 casos por par, buckets: 14 HIGH_RETURN, 10 LOW_RETURN, 8 OUTSIDE_RANGE, 8 TWO_SIDED, 8 NO_SWEEP. Son observaciones QORE C2, NO autenticaciones Romeo/Model #1.
- **Barrera técnica reparada** en `crt_pure_strategy_identity_memory.py`: `MODEL1_SOURCE_CONCEPTS`, `unresolved_model1_source_concepts()`, `model1_source_ready()`. El booleano legacy `strategy_identity_ready()==True` sigue intacto, pero `model1_source_ready()==False` porque `MODEL_1_REFERENCE_SELECTION` permanece `AMBIGUOUS`. Pruebas añadidas para impedir falsa equivalencia.
- **Certificación vs laboratorio separadas** en `crt_pure_r2_entry_router.py`: `assess_model1_certification_entry_family()` impone `UNRESOLVED/WAIT` con old-level selector abierto. No se tocó la semántica del router histórico de investigación, que puede producir un `EXECUTE` SOLO conceptual. La nueva ruta nunca concede ejecución ni capital. Ante sesgo de Model #1 contrario a H4, conserva ABSTAIN. [Cognitive Gate #38621993347](https://github.com/mezas3238-hue/qore-core/actions/runs/38621993347) **SUCCESS** tras corrección de Ruff; otros runs iniciales que fallaron por import ordering no son resultado válido.
- **G-M3 y frontera G-M4 sobre velas reales:** módulo `vt08_crt_pure_gm3_real_case_safety.py` consume únicamente los 48 casos ciegos (ni ZIP sellado ni C3 futuro), alimenta `CrtPureSituationModel -> reason()` y verifica la ruta de certificación del router con contexto H4. **Última ejecución verificada [#38622889457](https://github.com/mezas3238-hue/qore-core/actions/runs/38622889457): quality + AUDUSD + USDJPY SUCCESS**. Artifacts AUDUSD **11922254406** y USDJPY **11921969429**, todos los hashes internos verificados. **Cognitiva: 48/48 ABSTAIN; router de certificación: 48/48 WAIT/UNRESOLVED; 0 autorización de ejecución y capital**. Ambos mercados reportan 24/24 en cada componente. Se probaron condiciones de no-futuro, fuente sin resolver, veto BTCUSD y clock causal.
- Los 48 ABSTAIN son **demostración de barrera de seguridad ante metodología sin cerrar**, NO que VT08 comprenda/identifique 48 Model #1 auténticos, ni prueba de precisión ni rentabilidad. Los 48 WAIT del router no representan operaciones pendientes listas ni un supuesto éxito de G-M4 completo.
- Fuente histórica usada: Atlas original AUDUSD 148.171 M5 y USDJPY 148.201 M5; el artefacto analizado es OHLC relativo, no histórico BID/ASK fill. Todos estos datos ya fueron consumidos antes, NO holdout virgen. Ningún estudio de PnL, riesgo R, DD, PF, capital o sizing fue ejecutado para certificación. **CIBO único gestor de lotaje y volumen**.
- Fuente original RomeoTPT sobre prioridades/ownership de old high-low, origen de DOL, caducidad y M5 trigger **sigue sin cierre primario**. Herramientas o resúmenes de terceros NO resuelven autoridad A; no promover indicaciones de SpeculatorFL o scripts externos como si fueran reglas Romeo.

**Estados de G-M1..G-M5 a este addendum:** `G-M1 PARTIAL`; `G-M2 PARTIAL` (corpus real auditado por geometría, pero sin adjudicación visual contra autor); `G-M3 PARTIAL` (fail-closed probado en mercado real, no reconocimiento original); `G-M4 PARTIAL` (barrera cognitiva/router probada, recorrido end-to-end completo pendiente); `G-M5 NOT_CERTIFIED`. `GLOBAL CERTIFIED=FALSE`.

**Ruta concreta siguiente sin perder contexto:** (1) visionado localizable de Romeo para selector old CRTH/CRTL, fuente de destino y expiración con minutaje/captura; si no hay regla, elevar excepción etiquetada QORE para orden explícita Owner; (2) seleccionar referencia de forma causal/independiente y sellar metodología SIN optimizar por PnL; (3) revisión ciega caso a caso de estos 48 frente a gráficas originales y dictamen fuente, distinguiendo familias; (4) reintroducir esa fuente cerrada en el motor para contrastar EXECUTE/WAIT/ABSTAIN real y reparar divergencias G-M3; (5) probar G-M4 completo incluyendo expiración, hipótesis muerta, aislamiento por mercado y delegación CIBO; (6) emitir G-M5 SOLO si los cuatro anteriores están PASS. Preservar todos los hashes. **NO MERGE, NO VPS, NO DEMO/LIVE, NO sizing del trader.**


## ADDENDUM G-M1 / G-M2 / G-M3 — anti-certificación falsa y doble custodia (14-OCT-2026)

**Cierre técnico de la ronda; fuente original pendiente, no certificar.**

- **P0 resuelto en código:** `evaluate_certification_readiness` antes podía entregar `CERTIFIED` con flags externos todos `True` aunque `MODEL_1_REFERENCE_SELECTION=AMBIGUOUS`. Ahora llama de manera independiente a `model1_source_ready()`. El veredicto continúa `SOURCE_OPEN` y agrega `MODEL_1_REFERENCE_AND_SOURCE_SELECTION_NOT_CLOSED`. Regresión `test_all_green_external_flags_cannot_fake_source_certification`. Commits `7882768302803783ab77906a084656b28580a155` y `54fd1130cbd659919ce7437d76879aaf4e272e2d`. [Cognitive Gate #38633022187](https://github.com/mezas3238-hue/qore-core/actions/runs/38633022187) **SUCCESS**.
- **Contaminación ciega corregida:** el flujo ya no sube C3 futuro al mismo ZIP del revisor; dos artifacts SHA independientes por mercado, accesibles a la misma audiencia del repo, sin fingir controles de permisos. [Lab #38633327900](https://github.com/mezas3238-hue/qore-core/actions/runs/38633327900): quality + ambos mercados **SUCCESS** y confirmación externa de cuatro ZIP, hashes verificados.
    - AUDUSD ciego artifact **11926643336**, futuro sellado **11926753073**; 24 casos / 24 ABSTAIN cognitiva / 24 WAIT router.
    - USDJPY ciego artifact **11927291468**, futuro sellado **11927026635**; 24 casos / 24 ABSTAIN cognitiva / 24 WAIT router.
    - Cada ZIP ciego carece totalmente de `gm2-sealed-c3-witness.jsonl`. Cada ZIP sellado carece de los casos ciegos y de la salida cognitiva. SHA256SUMS íntegros en los cuatro ZIP. Esta separación **NO convierte casos anteriores en holdout nuevo**.
- **Controles adversariales de G-M3 agregados:** `BLIND_ALLOWED_FIELDS` rechaza filtración de observaciones futuras u otro payload; valida continuidad H4 C1→C2→C3 y prefijo M15 dentro de H4, cierra contra OHLC booleano, falseo de fresh holdout y mercado BTCUSD congelado. Tests `test_vt08_crt_pure_gm3_real_case_safety.py` ampliados. [Lab #38633327900](https://github.com/mezas3238-hue/qore-core/actions/runs/38633327900) **SUCCESS**; [Cognitive Gate #38633328098](https://github.com/mezas3238-hue/qore-core/actions/runs/38633328098) **SUCCESS**.
- **Búsqueda fuente primara y protocolo de desbloqueo G-M1:** [expediente OLD CRTH/CRTL](VT08_CRT_PURE_GM1_OLD_LEVEL_SOURCE_DISPUTE_ADJUDICATION_2026-10-14.md) indexa Telegram Romeo oficial #6615/#6184 y videos originales a auditar. No se encontró selector canónico determinista de old highs/lows múltiples en las fuentes verificadas; seguir `AMBIGUOUS`. Los resúmenes de terceros son guías de ubicación, no autoridad. Solo tras dictamen Nivel A con minutaje y revisión ciega independiente se habilitaría G-M1.

**Pendientes esenciales:** G-M1 resolver propiedad/origen old levels y destino/caducidad sin reglas inventadas; G-M2 adjudicar la lectura del autor para 48 casos; G-M3 contrastar `reason()` con dictámenes reales originales; G-M4 demostrar lifecycle E2E completo sin ruta alternativa; G-M5 expedir únicamente con cuatro PASS. **No hay certificado ni permiso de trading.** PROHIBIDO sizing en Gates; lotaje y volumen exclusivamente CIBO. NO MERGE, NO DEMO/LIVE, NO VPS.


## ADDENDUM — 96 referencias H4 crudas y certificador G-M5 independiente (14-OCT-2026)

**Nueva evidencia real:** [Expediente G-M1 doble referencia + G-M5](VT08_CRT_PURE_GM1_DUAL_REFERENCE_CHALLENGE_AND_GM5_GUARD_2026-10-14.md). [Trader Lab #38650459457](https://github.com/mezas3238-hue/qore-core/actions/runs/38650459457) **3/3 SUCCESS** en calidad, AUDUSD y USDJPY; 48 expedientes históricos de G-M2 → **96 extremos H4 crudos causales**, dos por caso, 48/48 pares con precios distintos. **NO son CRTH/CRTL aprobados, entradas ni trades.** Registro de revisor AUDUSD artifact **11934262952** y USDJPY **11933349915**, descargados y SHA256 internos (7/7 cada ZIP) validados; contienen manifiesto de G-M1 y los casos históricos ciegos, nunca futuro C3 sellado. G-M1 todavía requiere validación con fuente original de qué nivel es legítimo, y si el autor define desempate.

**Seguridad G-M5 separada:** `src/qore/infrastructure/traders/crt_pure_methodological_certification.py`, con tests `test_crt_pure_methodological_certification.py`. Exige G-M1..G-M4 todos PASS con fuentes/segundo adjudicador/no-leakage y `model1_source_ready()` cerrado; frente a cuatro falsos PASS, mientras el concepto `MODEL_1_REFERENCE_SELECTION` siga AMBIGUOUS, **NO emite certificado**. [Cognitive Gate #38650560776](https://github.com/mezas3238-hue/qore-core/actions/runs/38650560776) **SUCCESS**. Esta ruta es 100% metodológica y cognitiva: sin sizing, sin PnL, sin DEMO/LIVE/capital. Es separada del certificador económico histórico.

**Pendientes activos:** localizar en la fuente original Romeo un selector old CRTH/CRTL multireferencia con minuto/fotograma/texto o reconocer discrecionalidad y pedir aprobación explícita Owner para política de ingeniería QORE. Posteriormente emitir dictámenes ciegos independientes (48 casos), cotejar la cognitiva y completar G-M4 E2E. Hasta entonces: `G-M1 PARTIAL; G-M2 PARTIAL; G-M3 PARTIAL; G-M4 PARTIAL; G-M5 NOT_CERTIFIED`. PR #626 DRAFT; NO MERGE; NO sizing (solo CIBO manda volumen).

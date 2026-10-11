# QORE CORE — SCALPER: HANDOFF MAESTRO DE CONTINUIDAD (A1 COGNITIVA + A2 METODOLOGÍA)
## Evidencia, código, resultados, fallos, reparaciones obligatorias, Master Frame real y certificación

**Fecha de corte:** 10 de octubre de 2026.
**Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core).
**Documento NUEVO y preferente para continuar A2:** rama agent/scalper-architect-b-methodology-20261010 / PR [#759](https://github.com/mezas3238-hue/qore-core/pull/759).
**Rama A1 cognitiva:** agent/scalper-architect-a-cognition-20261010 / PR [#758](https://github.com/mezas3238-hue/qore-core/pull/758).
**PR de programa / integración anterior:** [#623](https://github.com/mezas3238-hue/qore-core/pull/623).
**Issues de coordinación:** [#757 metodología](https://github.com/mezas3238-hue/qore-core/issues/757), [#756 cognitiva](https://github.com/mezas3238-hue/qore-core/issues/756).
**HEAD comprobado al preparar este cierre, ANTES del commit final de este documento:** B metodología 1d56044c030f372da2cdd32f8a7424e86499d0d4; A cognitiva e03f7330078725d4c5206a64ea0c5bde4efb0eac. El commit final de B es el registrado en GitHub para esta edición. Comprobar SHA en ambos PR antes de ejecutar workflows: A1 y B evolucionan en paralelo.
**Estado de todos los PR:** OPEN/DRAFT, sin merge. **Trader: NO CERTIFICADO. NINGUNA autorización VPS, LIVE, MT5 o real capital.**

> **ORDEN OPERATIVA DEL OWNER:** Ya NO desea otro panel pasivo ni un nuevo filtrado. Quiere los sensores alimentando la cognitiva potente REAL del Trader Scalper; el Master Frame debe razonar cada entrada y producir PASS/WAIT/ABSTAIN, el motor PAPER debe ejecutar sólo las entradas autorizadas y cuantificar SI mejora el drawdown, Profit Factor, expectativa, cantidad de operaciones y preservación de ganadores. Esta orden manda sobre una investigación cosmética adicional. Al mismo tiempo, la auditoría décima A1 ordenó congelar nuevas capas/modelos/filtros hasta cerrar fidelidad CISD, divergencias y Candle 3. Ambas exigencias se concilian **reutilizando la arquitectura cognitiva YA IMPLEMENTADA**, cerrando defectos de fuentes y construyendo evidencia histórica auténtica, sin inventar un nuevo score/política.


## ACTUALIZACIÓN DEFINITIVA — ESTADO REAL AL ENTREGAR AL SUCESOR

**Prioridad absoluta del Owner:** integrar sensores al CEREBRO Master Frame verdadero del Trader Scalper; este cerebro decide cada oportunidad ANTES de abrirla en PAPER; comparar su drawdown, PF, rentabilidad y preservación de ganadores con V49. **No volver a agregar un veto simple ni un panel meramente pasivo.**

**Hechos ya probados:** (1) la interfaz sensor→contexto Master Frame→PASS/WAIT/ABSTAIN→PAPER y memoria selected-and-settled-only funciona en tests con fixtures; (2) A1 construyó 2.822 barreras temporales reales en nueve mercados para 2.876 oportunidades V49, con 2.791 barreras 9/9 M1 exactas y 31 barreras de feed parcial; (3) 2.876 percepciones origen ascienden a DEGRADED y 22.522 permanecen BAD, 0 GOOD; (4) los regímenes permanecen UNRESOLVED, grafo causal UNKNOWN, spread/commission físico y World Model completo no están atestados; (5) **NO existe un replay histórico económico Full Master Frame de 2.876 decisiones con PF y DD calculados**. Es incorrecto asignar al cerebro los PF .664 de V49, 1.595 de V50-G reducido o .621 del veto de discrepancias.

**CI confirmada en commits exactos:** [B Methodology #38093821695](https://github.com/mezas3238-hue/qore-core/actions/runs/38093821695) y [B Cert V2 #38093824349](https://github.com/mezas3238-hue/qore-core/actions/runs/38093824349), SUCCESS en 1d56044; [A1 Cognition #38094209281](https://github.com/mezas3238-hue/qore-core/actions/runs/38094209281) y [A1 CISD outcome-blind nine-market #38094209262](https://github.com/mezas3238-hue/qore-core/actions/runs/38094209262), SUCCESS en e03f733. A1 tuvo fallos CI en SHA anteriores y fueron subsanados; no afirmar que calidad de CI demuestra rentabilidad.

**Congelación metodológica vigente:** [A1 Décima auditoría METHOD-FIRST](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/docs/research/QORE_SCALPER_A1_TENTH_AUDIT_METHOD_FIRST_FREEZE_2026-10-10.md) prohíbe nuevas políticas/regímenes/filtros mientras B completa fidelidad CISD/Candle3, resolver las 381 discrepancias por causa y testigos de H1/M15/M1. Esa congelación NO prohíbe cablear y comprobar las funciones Master Frame ya implementadas con hechos nativos; exige no fingir entradas o epistemología a partir de los resultados futuros. La prioridad es **terminar la integración REAL y el replay**, no crear nuevas capas teóricas.

---

# 0. INSTRUCCIONES DE ARRANQUE OBLIGATORIAS PARA EL SIGUIENTE ARQUITECTO

1. Revisar este documento, los dos PR y el estado GitHub Actions de sus **HEAD actuales**, no deducir resultados del código que sólo pasa tests con fixtures.
2. **NO VPS** ni siquiera de lectura; no desplegar; no LIVE/MT5; no fusionar ramas sin nueva autorización. GitHub, comentarios, commits y Actions/artifacts son el plano de trabajo.
3. Separar tres verdades: **(a) observación nativa**, **(b) cognición que realmente decide antes del trade**, **(c) economía de trades que realmente sobrevivieron**. Ninguna puede reemplazar a otra.
4. Mantener íntegro el control V49 y sus 2.876 source IDs. No convertir discrepancias, BAD/DEGRADED, TTL, ruido M1 ni incertidumbre en veto automático. Una señal sin evidencia debe quedar explicada con WHY y recuento, no desaparecer del denominador.
5. **P0 inmediato:** reconciliar las 381 señales CISD divergentes, probar contexto autor-fiel Candle 2/3→M15→M1, construir/alimentar en tiempo cronológico el verdadero Master Frame de nueve mercados, y pasar la batería PAPER comparativa con 2.876 decisiones. **No afirmar mejora de DD antes del reporte agregado medido.**
6. Comprobar el binario/algoritmo económico y criterio MAX3 del control en las nueve series. Prohibido seleccionar trades por retorno futuro, MFE/MAE, identidad de ganador o por resultados de los experimentos anteriores.
7. Identificar por commit y PR qué partes se importarán desde A1 a A2 o viceversa; A1 ya integró copias/interfaces de A2. Evitar dos selectores que decidan distinto o combinar accidentalmente una versión obsoleta del módulo de sensores.

---

# 1. IDENTIDAD DEL MODELO Y FUENTES PRIMARIAS TTRADES

**Modelo del autor:** TTrades, **TTrades Scalping Model / Fractal Model**, no confundir con un ICT Silver Bullet de otro Trader de QORE.

**Fuente general:** [TTrades Scalping Model — Simple Day Trading Strategy](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/), TTrades, 7 febrero 2026.
**Temporalidades:** contexto Daily según material del autor; **H1 sesgo y cierre Candle 2 / Candle 3**, **M15 estructura/swing protegido**, **M1 ejecución**. La ruta de investigación no impone automáticamente un cuarto filtro Daily/H4 obligatorio, ni una conjunción universal MSS+FVG+OB, ni 4–8R mínimos por mera ingeniería.
**Rutas que hay que preservar y verificar:**
- LIQUIDITY_SWEEP_CISD: barrido estructural en contexto, serie causal de velas que cierran en sentido contrario; **CISD válida exige cierre más allá de la apertura de la PRIMERA vela de la serie opuesta**. No basta mecha ni simplemente romper high/low del swing; CISD ≠ MSS.
- FVG_RETRACE_CISD: FVG M1 confirmado por tres velas, interacción/retracción posterior, pivot y CISD estructural. El pivot solo es PROTECTED después de cierre CISD, nunca porque retrospectivamente fue un extremo.
- Stop protegido M15 como esquema estructural observado V49; refinamiento M1 y veto 4–8× de ruido eran **QORE_ENGINEERING_RULE**, NO mandato universal TTrades. Stops M1, ruido, TTL y targets jerárquicos deben estudiarse como **ingeniería**, no presentar como fuente explícita sin cita.
- Objetivos: highs/lows de velas HTF previas y swings no barridos pueden representar liquidez externa; FVG puede ser liquidez interna. No hay jerarquía universal semanal→diario→H1→FVG obligatoria, ni regla de escoger siempre el objetivo más lejano.

**Fuentes directas de comprobación:**
- [TTrades — Understanding CISD](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/), 29 junio 2025.
- [TTrades — MSS vs CISD](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/).
- [TTrades — CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/), 10 enero 2026.
- [TTrades — Candle 3 Closure guide](https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/), 3 diciembre 2025.
- [TTrades — How to Set Price Targets Using the Fractal Model](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/).
- [TTrades — The Only Trading Strategy You Need for 2026](https://ttrades.com/the-only-trading-strategy-you-need-for-2026/).
**IMPORTANTE:** páginas primarias tienen descripciones potencialmente diferentes de C3: diciembre 2025 C3 cierra fuera del cuerpo de C2 **sin barrer rango C2**; enero 2026 puede describir cierre superando apertura Y rango de C2. No declarar una variante universal o introducirla en producción por cuál gana in-sample. Leer contexto y ejemplos concretos, preregistrar **dos universos A/B C3** independientes, no usar ganancias para resolver interpretación del autor. Fuente y efecto económico son preguntas distintas.
**Etiquetas del ledger metodológico:** SOURCE_EXPLICIT/MATCH, PARTIAL, SOURCE_AMBIGUITY, QORE_ENGINEERING_RULE, UNRESOLVED, CONFLICT. Toda diferencia debe enlazar detector/función, instante y testigo nativo, y párrafo fuente.

---

# 2. POBLACIÓN BASELINE INMUTABLE, DATOS Y REGLAS CAUSALES

**Periodo de desarrollo:** 2025-09-17 a 2026-09-17 (aprox. 12 meses). **NO existe aquí prueba de robustez 2023/2024 ni OOS sellado independiente.**
**Mercados:** AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, NAS100, USDCAD, USDJPY, XAUUSD.
**Fuente M1 original provider-native:** [Actions #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), commit 18c338aedd5013ce65a6cb6408ffbc2e904a6217; manifests provider_native_m1=true, synthetic_m1=false, interpolated_m1=false. Las velas faltantes nunca se fabrican.
**Libro V49 canónico:** [Actions #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), SHA e356e7a52541e99533b25ecfef0ab9c4e9ce03c0; [matriz artifact #11670728222](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695/artifacts/11670728222).
**Identity:** SHA-256 causal por source_opportunity_id; 2.876 oportunidades, unión 1:1 source/trade, 9/9 symbols, UTC y sesión NY/DST por fecha de operación.
**Sesión QORE operativa:** Asia 20:00–02:00 NY, London 02:00–08:30 NY, New York 08:30–16:00 NY, con DST y operating_date correctamente conciliados. **No confundir** con killzones ICT de un modelo distinto. MÁXIMO 3 oportunidades ejecutadas por sesión operativa/fecha a escala de cartera **entre TODOS los mercados**, por orden cronológico; no MAX3 individual por símbolo.
**Semántica económica del control:** precio al cierre M1 de confirmación, SL protected M15, target H1 witness disponible, STOP FIRST si STOP y TARGET tocados dentro de la misma M1, cierre al término de sesión. Ni BID/ASK tick físico, comisiones verificadas ni slippage están integrados en este resultado; por tanto **R brutos** y **DD medido en R, NO porcentaje de cuenta**.
**Métricas V49 confirmadas:** 2.876 antes MAX3, **2.020 ejecutadas**, 856 hipotéticas excluidas, 1.167 ganadoras, 852 perdedoras, 1 plana, PF **0.6644630742**, gross profit **+461.942761832R**, gross loss **−695.212088909R**, net **−233.269327076R**, maxDD **236.134284R**. Stop 609 × −1R, target 1.030 (media +0.392R), session_exit 381. Ganancia media por trade ganadora ~0.39584R vs pérdida media por perdedora ~−0.81598R.
**Límites de preservación OWNER:** mantener por **identidad original** al menos 80% de 1.167 ganadoras (**≥934 IDs**) y 90% de sus R originales (**≥415.74848565R** ≈415.75R), además de no perder densidad arbitrariamente. La masa R se mide sobre el **beneficio V49 original correspondiente a los source IDs aún ganadores**, nunca sobre el payoff superior de un nuevo stop/target que reescribió escala.
**Invariantes de anti-lookahead:** todas las decisiones con bars.closed_at <= decision_at, H1/M15 events confirmed_at <= decision_at, no leer h1_state_until calculado por la siguiente tesis futura como expiración sabida, no predecir próximo cierre M1, no usar trade.exit_reason/realized_r/MFE/MAE/future price ni la etiqueta winner original para aceptar entradas. La memoria se actualiza únicamente después de que una operación **elegida y ejecutada** cierre realmente, nunca con trades rechazos hipotéticos.

---

# 3. TRABAJOS COMPLETADOS POR B (METODOLOGÍA) — INVENTARIO POR CICLO

## 3.1 Auditoría fuente/ejecución original y base histórica

- Se rastreó el caller V49 y la arquitectura H1 bias C2/C3 → M15 protected → primer M1 Sweep+CISD o FVG+CISD → entry close → económico MAX3. Detectores en capitalizer_source_observation_detectors_v2.py, capitalizer_high_frequency_capacity_census_v49.py, capitalizer_ttrades_m1_cisd_observer_v48.py, capitalizer_ttrades_m1_fvg_cisd_continuation_v48.py. Se verificó que el nivel CISD Sweep es **series[0].open** (primera vela de cierres opuestos) y exige **CLOSE**. La estructura FVG pivot no se proclama protected prematuramente.
- Se corrigieron testigos causales de target y orden de velas (bisect al cierre de H1 y decisión), preservando igualdad del replay V49, evitando leer high/low de M1 futura abierta.
- Se establecieron lector de identidad/censo por fuente, workflows 9/9 y suite permanente Ruff/mypy/pytest. **El auditor de identidad es POST-REPLAY**, NO una regla de admisión: su invalidación obliga a rehacer evidencia, no filtra ganadoras de trading.

## 3.2 MAX3 / MFE-MAE / target / stops y filtros

- [MAX3 counterfactual #38056328467](https://github.com/mezas3238-hue/qore-core/actions/runs/38056328467): 2.020 seleccionadas PF0.66446, media −0.11548R; **856 excluidas hipotéticas** PF0.59831, media −0.12644R. No se demostró MAX3 como causa económica dominante. M1 hypothetical outcomes de excluidas NO son fills asegurados.
- [MFE/MAE #38057290884](https://github.com/mezas3238-hue/qore-core/actions/runs/38057290884), 11/11 PASS: entre 2.020 seleccionadas, **MFE preterminal media 0.34364R**, **MAE preterminal 0.46553R**. Se separó extremo M1 terminal observacional del recorrido intrabar realmente ejecutable; tres trades STOP/TARGET misma vela siguieron STOP-FIRST.
- [V50-G 9 mercados #38053723674](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674), plus [winner audit #38057558313](https://github.com/mezas3238-hue/qore-core/actions/runs/38057558313): Geometría 220 trades, PF 1.0959, DD 20.33R, 62/1.167 ganadoras originales preservadas y 23.625R masa original; “Cognitive Geometry” **94 trades**, PF 1.5949, DD 9R, sólo **37** ganadoras originales y **14.051R** masa original. **RECHAZADO.** Es PARTIAL_V50_BRIDGE_ONLY, NO ejecuta el verdadero full Master Frame; rendimiento in-sample de subpoblación diezma frecuencia, engañaría certificar por PF aislado.
- [Waterfall reason-code #38057731321](https://github.com/mezas3238-hue/qore-core/actions/runs/38057731321): 2.655 geometry rejects, de ellos **2.371 M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE**; 272 M1 invalidation missing, 10 demasiado amplio, 2 destinos H1. Otros 127 cognitivo puente (99 H1 stale, 23 M15 stale, 5 session runway). Son razones de ingeniería, no errores de autor demostrados, y **no generar gates nuevos**.
- [Factorial stop×noise](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_TARGET_GEOMETRY_AND_STOP_NOISE_FACTORIAL_2026-10-10.md): B M15/no veto=2020 PF.664 DD236.13R; C M15/veto=223 PF.869 DD12.69R; D M1/no veto=1934 PF.796 DD263.12R; A M1/veto=223 PF1.035 DD13.03R. El veto recorta ~89% de oportunidades y **no descubre robustez rentable**; no promover.
- [Target HTF as-of #38061448754](https://github.com/mezas3238-hue/qore-core/actions/runs/38061448754), 11/11: mismo 2.876 source /2.020 MAX3; reemplazo del extremo reciente H1 por swing externo confirmado subió mediana target planificado de ~0.443R a ~1.025R **pero** PF .664→.672, net −233.27→−277.61R, DD236.13→279.56R, target exits 1030→627; preservó 942 IDs pero solo **387.58R** masa original (<415.75R). **RECHAZADO**; “target H1 corto” no es causa raíz única.
- Tests de comparación de targets, stops, MFE, identity, MAX3 y ganador fuente con workflows individuales disponibles y CI metodología B actualizado. La prioridad siguiente NO es otro parámetro de stop/TP o veto.

## 3.3 Sesgo H1 / timing M1 / azar controlado

- [Joint diagnostic #38063930894](https://github.com/mezas3238-hue/qore-core/actions/runs/38063930894): original favorable H1 tras +15m **874/1975=44.25%**, +30m **839/1924=43.61%**, +60m **837/1824=45.89%**. Son cambios de precio retrospectivos y no porcentaje de winners ni PF. **66.2%** de entradas en último tercio de **precio de rango H1 parcial as-of** (NO último tercio horario). El favorable 30m por tercio precio primero 29.8%, último 47.2%, no el patrón inverso. Cuando runway <30m sólo 10/92 llegó al target, pero son subconjunto, no toda la causa.
- [Baseline aleatorio preregistrado #38067672878](https://github.com/mezas3238-hue/qore-core/actions/runs/38067672878), 11/11: 32 draws por ID misma dirección/tesis H1/sesión/mercado/operating day, otros 32 mismo tercio horario H1, y control coinflip. A +30m **V49 43.61% vs random mismo estado H1 54.90% vs reloj-ajustado 56.16%**, diferencia emparejada **−12.55 pp** IC95% bootstrapped por NY date **[−14.53,−10.37]pp**. A +15m 44.25 vs 53.20 ajustado, +60m 45.89 vs 58.61 ajustado. **NO demuestra** que un trade M1 aleatorio con stops/targets/costes sea rentable: el nulo no exige M15 POI ni CISD y no elimina confusores ni identifica una única pieza culpable.
- [Cadena M15→Sweep/FVG→CISD→entry #38068938682](https://github.com/mezas3238-hue/qore-core/actions/runs/38068938682), 11/11: 2.876 rutas originales reconstruidas con observadores reales; en Sweep n=900 pares completos +30m: **475 favorables en cierre Sweep, 362 en CISD, delta −12.56pp**; en FVG n=1.023: **506 favorables al formar FVG, 477 en CISD, delta −2.83pp**; pivote FVG posthoc **666/1036=64.3%** vs CISD **477/1023=46.6%** pero denominadores no idénticos y pivot aún NO protected. **CISD→entrada simulada=0 minutos** para las 2.020. Pérdida direccional localizada **en la cadena previa**, no por latencia pos-CISD. Un timestamp anterior es aún diagnóstico, no trade legal.
- El mercado V49 entero sigue bruto negativo; no hay certificado de ventaja TTrades autor ni sesgo H1 monetizable aislado.

## 3.4 Sensores al trader y ensayo PAPER real de ingeniería

**Se programó módulo as-of de >20 sensores** capitalizer_scalper_entry_timing_sensors_shadow_v1.py:
- H1_BIAS_DECLARED; H1_THESIS_AGE_MINUTES; H1_CURRENT_CLOCK_FRACTION; H1_ASOF_PARTIAL_PRICE_RANK.
- M15_PROTECTED_STOP_DECLARED; M15_TO_M1_ELAPSED_MINUTES; M15_ORIGINAL_RISK_PRICE_DISTANCE; ACTUAL_M15_STRUCTURE_REVALIDATION cuando realmente se ateste.
- NATIVE_M1_GAP_COUNT; M1_LOCAL_MEDIAN_BAR_RANGE; M1_LAST_BODY_DIRECTIONAL; SESSION_REMAINING_MINUTES.
- M1_SWEEP_OBSERVED; M1_OPPOSING_SERIES; M1_SWEEP_CISD_CLOSED; M1_FVG_FORMED; M1_FVG_RETRACE; M1_FVG_CISD_CLOSED; M1_PROTECTED_SWING_ATTESTATION.
- H1_TARGET_ROOM_R con testigo temporal; BROKER_BID_ASK_SPREAD; BROKER_COMMISSION_PER_LOT si hay datos reales; FULL_COGNITIVE_MASTER_FRAME; SOURCE_SIGNAL_OBSERVED.
Cada lectura es status OBSERVED / DEVELOPING / NOT_OBSERVED / NOT_AVAILABLE / CONTRADICTORY, con timestamp, valor, explicación y procedencia. **No inventa win-probability**, no autoriza ejecución ni reemplaza la cognitiva.
**Código de censo** capitalizer_scalper_entry_timing_sensors_census_v1.py, Actions [#38071138991](https://github.com/mezas3238-hue/qore-core/actions/runs/38071138991), 11/11: 2.876/2.876 source IDs instrumentados; **2.495 coinciden** con primer CISD V49, **381 difieren**. El primer control fail-closed abortó; se preservaron todas las 381 en el censo en vez de borrarlas, sin fabricar trades.
**Adaptador real a Master tipo QORE:** capitalizer_scalper_sensor_master_frame_bridge_v1.py produce CapitalizerCandidateCognitiveContext con observation tokens de sensores. **NO ejecuta solo** el mundo completo ni se inventa GOOD/M15 completo.
**Router PAPER A/B:** capitalizer_scalper_sensor_paper_decision_ab_v1.py acepta decisiones solo con Master Frame realmente atestado/WHY/ID/timestamp sin resultados futuros, selecciones cronológicas y MAX3. Simula únicamente los fills V49 originales en el mismo instante (WAIT/ABSTAIN no crean retiming). Reporta PF, DD R, winners de V49 preservados.
**[PAPER A/B #38071484777](https://github.com/mezas3238-hue/qore-core/actions/runs/38071484777):** V49 control 2020 PF0.664 DD236.13R; NOOP sensores idéntico; aplicar **rechazo binario a 381 discrepancias** produjo 1910 PF0.621 DD252.10R y sólo 385.08R masa original preservada. **RECHAZADO**. No es cognitiva A1 ni prueba de DD reducido; demuestra que el filtro automático **empeora** economía/densidad.
**ERROR/limitación:** lectura as-of del primer evento de ambos observers en snapshot truncado puede no ser el evento archivado por el V49 original, que vio su ventana de búsqueda completa; requiere causa/precedencia, no elegir ruta de mayor PF.

## 3.5 Novena auditoría: clasificación exacta 381 y MFE/MAE

**[CISD 381 forensic #38076268436](https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436)**, 11/11 GREEN; [artifact matriz #11679210450](https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436/artifacts/11679210450).
- **247 SENSOR_EARLIER_THAN_V49**: 171 original FVG→sensor Sweep anterior; 76 original Sweep→sensor FVG anterior.
- **134 SAME_TIME_DIFFERENT_FAMILY**: original Sweep→sensor FVG, exactamente misma vela y cierre.
- **0 later**, por diseño un panel que sólo ve hasta V49 original no puede observar el futuro; **0 missing**. **381/381 son conflictos de familia**, 247 además de minuto. **NO hay comparación de dirección contraria** porque el sensor hereda dirección H1: no aseverar que mercado no tuvo CISD opuesta.
- En 224 parejas completas de eventos **anteriores** a +30m, sensor 126/224=56.25% favorable vs V49 113/224=50.45%, **+5.804 pp**; a +15m empeora **−3.35pp**, a +60m empata. MFE temprano ~1.103R vs .793R en V49, MAE también sube ~.724R vs .580R, medias R con coberturas geométricas no idénticas. Mismo timestamp/diferente familia tiene exactamente idéntico precio y resultado posterior. **NO es nuevo edge operable**.
- El cierre CISD Sweep al opening de primera vela opuesta es fuente-MATCH básico. **La causa de las 381 se debe buscar en precedencia de rutas y ventanas H1/M15/futuro permitido, y asociación de la serie opuesta al swing/POI**, NO suponer CISD invertida.
- [Informe B novena auditoría](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_NINTH_CISD_381_SOURCE_AND_MFE_MAE_PREREG_2026-10-10.md) detalla por mercado/tipo/cobertura sin modificar operativa.

---

# 4. TRABAJOS COMPLETADOS POR A1 (COGNITIVA) — CÓDIGO REAL Y LÍMITES

**Rama A1:** agent/scalper-architect-a-cognition-20261010, consultar [PR #758](https://github.com/mezas3238-hue/qore-core/pull/758), commits y documentos antes de reutilizar código: A1 ha avanzado **después** de muchas observaciones B. No sustituir la rama A1 por el V50-G **PARTIAL_V50_BRIDGE_ONLY** que retenía 94 trades.

**Master Frame QORE REAL:** src/qore/infrastructure/trader_lab/capitalizer_master_cognitive_frame.py recibe el mundo, nueve percepciones y regímenes, grafo causal, candidate context, pressure, historial causal de decisiones y memoria. Su criterio de intervención depende de evidencia epistemológica, no sólo del nombre del indicador. Los componentes cognitivos ya existentes son parte del modelo: percepciones de mercado, estado/hipótesis de régimen, grafo intermercado, World Model/brains, memoria de pérdidas e interpretación de WHY/metacognición y presión; NO declararlos presentes en un replay simplemente porque el tipo Python existe.

**Rutas funcionales A1 con tests de integración, aún SIN outcome histórico nueve mercados:**
- capitalizer_a1_trader_cognition_port.py: empaquetar contexto candidato en interfaz de decisión.
- capitalizer_a1_multi_hypothesis_research.py: alternativas competidoras observadas en un mismo instante, no escoger trade por R futuro.
- capitalizer_a1_chronological_cognitive_replay.py: orden causal y memoria de resultados settled-only.
- capitalizer_a1_full_frame_research_adapter.py: investigación full frame desde world/evidencias **externamente proporcionadas**.
- capitalizer_a1_sensorized_paper_runtime_v1.py: asocia un EntrySensorInput M1 verdadero a candidato original y construye contexto sensor→hipótesis cognitiva.
- capitalizer_a1_master_frame_paper_trader_integration_v1.py::run_real_master_frame_paper_trader: invoca prepare_trader_cognition_packet → build_master_cognitive_frame → PASS/WAIT/ABSTAIN → selección PAPER MAX3 → economía R, DD, retención y memoria después de exit_at. Los tests con FIXTURES prueban que realmente cambia admisión; **no** equivalen a replay 2876 con mundo completo histórico.
- capitalizer_high_frequency_trader_v49.py::select_master_frame_trade_intents: otra ruta de intents con cognitiva. **P0 coherencia:** decidir UNA ruta canónica; no dejar dos motores dando permisos inconsistentes.
- capitalizer_a1_joint_competition_research.py / capitalizer_a1_m1_protected_route_forensics_v2.py / capitalizer_a1_m1_second_pivot_forensics_v3.py: diagnósticos para múltiples candidatos/swing; no establecer veto de autor por falta del segundo pivot.

**Datos físicos/sincronizados A1, VERIFICADOS:**
- [Native synchronized 9-market M1 #38080367716](https://github.com/mezas3238-hue/qore-core/actions/runs/38080367716) 11/11 PASS: 2.876 oportunidades original → **2.822 timestamps únicos**; 2.791 con vela M1 EXACTA 9/9, 24 con 8/9, 7 con 7/9. **31 instantes incompletos** se reportan, nunca backfill del futuro.
- [Censo de 9-market epistemic inputs #38091052695](https://github.com/mezas3238-hue/qore-core/actions/runs/38091052695) SUCCESS: **25.398 percepciones (2822×9)**, 25.398 hipótesis de régimen y **101.592 edges cross-market (2822×36)**: inicialmente todos los regímenes UNKNOWN/UNRESOLVED y edges UNKNOWN; no inventar causas por correlación. Los snapshots son tipos originales Master Frame.
- [Clock/source DST 2876](https://github.com/mezas3238-hue/qore-core/actions/runs/38091938032): los 2.876 buckets de sesión QORE NY/DST y source timestamps revalidados; no convertir una ventana ICT distinta en filtro.
- [Percepciones Clock-Bound V2 #38092434895](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434895) GREEN: **2.876 source-associated DEGRADED**, **22.522 BAD**, **0 GOOD** sobre 25.398. DEGRADED significa que hay OHLC M1 nativo y reloj QORE fuente conciliados, pero **quote_fresh=false** y **microstructure_complete=false**. BAD en ocho mercados sin testigo fuente de sesión individual NO significa precio M1 corrupto; no suprimir trades. 2.876 percepciones son instancias de fuentes, no 2.876 timestamps distintos; hay 2.822 timestamps. Regímenes y relación entre mercados siguen UNRESOLVED/UNKNOWN.
- 2.375/2.876 testigos M1 de estructura con primera/segunda ruta de pivot; **501 aún sin ese testigo independiente** (no equivale necesariamente a invalidez metodológica). **12 M15**, **124 H1** sin prueba independiente bajo el auditor A1; hacer adjudicación por caso, NO nuevo veto de 501+12+124.
- capitalizer_a1_native_nine_market_bar_witness_v1.py, capitalizer_a1_native_nine_market_epistemic_inputs_v1.py, capitalizer_a1_native_source_session_clock_attestation_v1.py, capitalizer_a1_native_clock_bound_perception_v2.py: herramientas auditadas y trazas nativas con reloj. Los estados 31 missing M1 y 25.398 percepciones no implican que World Model esté completo.

**Estatus del entorno histórico real:** todavía NO existe artifact reproducible de **2.822 barreras full Master Frame reales con 2.876 decisiones + outcome económico**, world, pressure, open_positions, selected settlements, régimen contrastado y grafo atestados por fuente. **PF/DD de Master Frame REAL sobre V49 = NO MEDIDOS**. La calidad de CI demuestra interfaces y observaciones, NO una reducción de drawdown. A1 congeló nuevas capas hasta cerrar metodología [décima auditoría](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/docs/research/QORE_SCALPER_A1_TENTH_AUDIT_METHOD_FIRST_FREEZE_2026-10-10.md).

---

# 5. REGISTRO DE ERRORES / DEFECTOS CON REPARACIÓN Y GATE POR PRIORIDAD

| Gravedad / código | Error, estado y evidencia | Reparación exigida al sucesor |
|---|---|---|
| **P0-01 CISD_381** | 381 first-CISD divergencias contra V49: 247 temprano otra ruta y 134 misma hora otra ruta. El veto redujo PF y empeoró DD. | A2 reconstruir exactamente los límites de búsqueda original V49 (próximo setup M15, frontera H1 as-of, deadline y preferencia de empate), frente a evaluación prefix-only en sensores. Emitir trace fuente→detectores→familia con los 381 IDs, causa y clasificación autor-fiel. No elegir detector según rendimiento. |
| **P0-02 CANDLE3_AMBIGUITY** | Diciembre 2025 vs enero 2026 describen C3 de modo diferente; actual detector C3 inside-range body. | Preregistrar A/B C3 y reconstruir universos de fuente diferentes, fidelidad y métricas 9 mercados, sin reescribir V49 ni elegir definición por PF IS. Resolver por contexto/documento primario o dejar SOURCE_AMBIGUITY. |
| **P0-03 H1_M15_M1_POI** | Nivel CISD básico coincide con source, pero serie opuesta puede no pertenecer al swing que creó barrido/POI; 501 M1, 12 M15, 124 H1 sin testigos independientes. | Ledger source_id por candle de H1 C2/C3, POI, M15 swing/protected, precio invalidación, M1 sweep/FVG, apertura primera candle opuesta, cierre CISD; source clip/time y FULL/PARTIAL/CONFLICT/UNKNOWN. Casos sin evidencia no son vetos por defecto. |
| **P0-04 NO_REAL_9MARKET_MASTER_REPLAY** | El Master Frame se invoca en tests con fixtures, NO en un replay completo con 2876 oportunidades fuente del mundo real. | A1+A2 implementar y ejecutar 2822 barreras de 9 mercados, 2876 decisiones Master reales previas a entrada, PASS/WAIT/ABSTAIN por ID, cartera cronológica MAX3 y memoria selected-settled-only; PF, DD y ganadores tras cierre. |
| **P0-05 EPISTEMIC_INPUT_GAPS** | 0 GOOD; 2876 DEGRADED/22522 BAD; quotes BID/ASK, microestructura/regímenes/cross-market WORLD incompletos. | A1 producir testigos as-of **reales** o mantener UNKNOWN/NOT_AVAILABLE; NO forzar GOOD, KNOWN ni WELL_SUPPORTED para pasar gates. Un reporte BLOCKED honesto no es PF. |
| **P0-06 NINE_MARKET_M1_GAPS** | 31 de 2822 instantes carecen de 9/9 M1 exacta (24 8/9, siete 7/9). | Reconstruir política explícita de percepción parcial, fuente native y event time; no backfill futuro, no borrar fuentes, marcar sensibilidad de DD/resultado a disponibilidad. |
| **P0-07 SENSOR_EVIDENCE_AUTHORITY** | >20 sensores ya existen, pero no son gates; adapter a contexto no prueba Full Frame. | A1 usar observaciones status/provenance para decidir WHY; no otorgar capital/size/risk por existir FVG o CISD; un solo selector maestro y QORE risk soberano fuera del scope. |
| **P0-08 TWO_COGNITIVE_EXECUTION_PATHS** | Runner PAPER A1 y select_master_frame_trade_intents coexisten. | Contrato único para orden de decisiones, MAX3, WAIT y settlements; tests diferenciales bit-a-bit sobre mismo caso; no doble selección/corrección en cartera. |
| **P0-09 DD_PF_UNMEASURED_FULL** | Control PF.664 DD236R; ensayo mismatch PF.621 DD252R. Ninguna de esas cifras representa inteligencia Master Frame. | Publicar scorecard solo tras ejecutarse la cognitiva histórica completa, con evidencia fuente/instantes/percepción y separación gross vs net; no reciclar V50-G parcial 94 trades. |
| **P0-10 NO_PHYSICAL_BROKER_COSTS** | No tick BID/ASK as-of, commission por símbolo/lot/side, slippage, spread, lotaje MIN/MAX/STEP MT5 conciliado. | Conseguir/articular evidencia physical reproducible o dejar NET metrics UNRESOLVED; no proclamar ejecución FundedNext solvente por replay OHLC. CIBO/QDLE fuera de esta rama hasta autorización e integración explícita. |
| **P0-11 SOURCE_H1_FUTURE_EXPIRY** | Riesgo de usar h1_state_until calculado con evento posterior como tiempo disponible ex ante; fue identificado/protegido en tests, riesgo de regresión al fusionar A1+A2. | Tests en todas las rutas reales que nieguen acceso futuro; sustituir vigencia de tesis por transiciones confirmadas **hasta** decision_at. |
| **P1-12 LOOKAHEAD_INTRABAR** | M1 simultáneamente toca STOP/TARGET; barras M1 no indican orden de ticks; MFE full terminal incluye posible high posterior al cierre. | Conservar STOP-FIRST y MFE preterminal separados; no convertir high/low posterior a stop en ganancia ejecutable. |
| **P1-13 PREVIEW_FVGSENSOR_NOT_EQUALS_SOURCE** | Primer FVG observado del prefijo puede diferir del primer FVG que finalmente genera CISD aceptada; explica parte de 381 conflictos. | Instrumentar ordinal de FVG, fecha de confirmación, retrace, pivot, deadline/next M15 y desempate; consistencia 2876 IDs, no lectura de vela futura. |
| **P1-14 HYPOTHESES_OVERFIT** | TTL H1, veto local noise, swing target más lejano, STOP refinado, early sensor timestamps mejoraban alguna métrica pero empeoraban otras; reutilización del mismo año como desarrollo. | Congelar hipótesis y reglas antes de OOS independiente, no elegir por mejor PF testado, no crear filtro para expirar H1 por cohortes posthoc. |
| **P1-15 TEST_FIXTURE_VS_REAL** | Tests Master Frame con World/perceptions sintéticos declarados; GH CI GREEN no certifica causalidad del mundo real. | E2E real 9 mercados, 2822 barreras + 2876 source decisions, full source witnesses, curvas de equity, errores e invariantes en CI. |
| **P1-16 RESOURCE_AND_BRANCH_DRIFT** | Nueve mercados y M1 pueden tardar mucho; branches A1/B con copias de sensores y rutinas de reloj divergentes; A1 HEAD puede cambiar. | Pin SHA por workflow, comparar archivos al merge, eliminar dependencia circular, priorizar determinismo y cache M1 no conductual. No afirmar PASS de una versión distinta de HEAD. |
| **P1-17 LONG_HISTORY_AND_HOLDOUT** | Solo un año de V49 nativo empleado; 2023/24 ausentes de validación; periodos diagnosticados quedan consumidos como research. | Buscar/validar datasets independientes reales, preregistrar OOS, split temporal o forward paper realmente futuro. Nunca reciclar años ya usados para tuneo como certificación sellada. |
| **P1-18 CERTIFICATION_METRIC_CONFUSION** | DD en R es distinto de % equity y PF bruto no es neto; win rate económico no es acierto sesgo; 2.876 oportunidades no son trades ejecutados. | Reportar denominadores/monedas y curvas exactas, Sharpe/Sortino bien anualizados sólo con retornos de capital/periodos adecuados, costes físicos y sample size. |

### Errores encontrados y ya reparados que NO hay que reintroducir
- Auditores/fixtures con M1 OHLC matemáticamente inconsistente; corregidos en GH CI antes de adjudicar resultados.
- Barra de sesión que cerraba exactamente a frontera NY Asia y no debía ser candidato aleatorio; se añadió regresión DST, sin mover trades V49.
- USDCAD con huecos nativos: forward +15/30/60 requieren barras contiguas, pero un target tocado en OHLC realmente observado no debe invalidar V49 por hueco previo del nuevo lector; separación entre observación y ejecución original.
- Fallos temporales Ruff/mypy por imports, shadowing y tipos al crear módulos; corregidos antes de runs GREEN. Ver commits B, no asumir que errores antiguos siguen.
- Intentos de censurar automáticamente discrepancias que habrían retenido solo 385.08R ganadoras: **rechazados** en papel.
- V50-G 90/94 y veto local noise que destruían densidad: **rechazados** y NO deben reaparecer como plan certificado.
- Inadmisible afirmar que el detector de identidad post-replay causaba rechazos de entrada; corrección conceptual documentada.
- No confundir hora operativa NY 08:30–16 con ICT killzones de otro modelo, ni M15 protected stop con supuesto stop M1 obligatorio.

---

# 6. ENTREGABLE P0 QUE EL OWNER EXIGE: FULL MASTER FRAME TOMANDO ENTRADAS Y DD REAL

## 6.1 Entradas, reloj, estados e invariantes

**Entrada por barrier real:** 2.822 unique decision instants ordenados cronológicamente y 9 mercado snapshots de M1 a cada instante; 2.876 source opportunities totales (algunas comparten barrera). Cada oportunidad contiene source_opportunity_id, market, NY session bucket y operating_date, H1 closure y sesgo con testigo, M15 swing/testigo y stop, ruta M1/confirmed_at, cierre físico M1 y sensores. Nunca confundir una percepción de origen con nueve percepciones GOOD.

**Brain real:** un CapitalizerGlobalWorldModel real (session brain, portfolio/open positions, session ledgers, journey/memory), nueve CapitalizerMarketPerceptionSnapshot, nueve CapitalizerRegimeHypothesis (UNKNOWN cuando no sustentados), CapitalizerCrossMarketCausalGraph (UNKNOWN no ≠ enlace inexistente), CapitalizerCognitivePressureFacts, hipótesis competidoras y CandidateContexts con tokens A2 as-of. Llamar build_master_cognitive_frame **de verdad** por candidato, guardando WHY y contadores de evidencia. La existencia del tipo no satisface el contrato histórico.

**Causalidad:** En una misma barrera se presentan alternativas sin saber quién será ganadora; resolver competencia conjunta antes de aplicar MAX3 portfolio; MEMORY recibe sólo operaciones elegidas que efectivamente liquidaron **antes** del siguiente instante; cierres de sesión, positions, margin/risk sólo según hechos a ese timestamp. Orden de operaciones con mismo closed_at debe ser estable y predefinido.

**Decisión observable:** por cada uno de los **2876** source IDs producir: brain/head SHA, timeline decision_at, source hash, sensor hash, barrier_id, market-world/perception/regime/graph evidence hashes, PASS/WAIT/ABSTAIN y WHY, epistemic flags, si fue elegido MAX3, motivo de no admisión, orden PAPER (solo si PASS y en slots) y fuente de SL/TP. **No inventar candidato posterior** a WAIT: esperar de verdad implica reevaluar en próxima vela y reconstruir oportunidad aún vigente si la fuente lo permite, con nuevo identity, precio y órdenes causales; la comparación inicial solo admite fills V49 originales para evitar falsa retemporización.

**Output portfolio:** todos los trades elegidos PAPER con entrada, SL, TP, exit y comisiones (si verificadas); seleccionar primero no por payoff, registrar tiempo de cierre, equity por R y por capital sólo si hay riesgo/dinero conciliado, PF (sum profit/sum losses), expectancy, DD peak-to-trough, win/loss, dirección H1 +15/30/60 **solo para diagnostics**. Conciliar baseline original 2020, 1167 wins, PF .664463, DD236.134R antes de comparar. La rama B preparada capitalizer_scalper_sensor_paper_decision_ab_v1.py exige decisiones A1 verdaderas o declara NO A1; **preferir ejecutor canónico A1** si provee todos los witnesses.

## 6.2 Comparación científica exigida

1. **CONTROL A = V49** 2876 candidatos / 2020 MAX3 / 1167 winners / -233.269R PF0.66446 DD236.13R.
2. **CONTROL NOOP = sensores observados sin influencia**, métricas bitwise iguales al A; si cambia, bug de integración.
3. **B REAL = Full Master Frame A1 + sensores**, cero veto de discrepancia/NOT_AVAILABLE por conveniencia; comparar número PASS/WAIT/ABSTAIN, source IDs, MAX3 ejecutadas, PF, DD, retención de ganadoras/massa R.
4. Si B PASS decisiones son todas WAIT por falta de regímenes/cuotas, no ocultar: **eso es bloqueo de evidencia**, NO éxito de reducción DD. Reportar 0 trades PF null y por qué, sin reemplazar por modelo heurístico.
5. **Ablation científica** sólo después del primer B real: sensores ON/OFF manteniendo mismo Full Master Frame y mundo, resultado por componente causal sin cambiar datos. Abrir registro ex-ante antes de mirar resultados.
6. **REPLAY físico posterior**: mantener 9 mercados, broker bid/ask, comisión de apertura/cierre, spreads, slippage, lotaje, simultaneidad, open risk; la evolución del equity depende del dinero real y settlements, no de sumar R independientes con tamaños constantes. No certificar con gross R.

**No hay disponible hoy un PF/DD del B REAL 2876/9/9**. Declararlo como resultado sería falsear la evidencia. El objetivo de reducir DD sigue **PENDIENTE DE MEDIR**, no logrado.

---

# 7. CRITERIOS DE CERTIFICACIÓN V2 — NO MODIFICAR POR RESULTADO IN-SAMPLE

La autoridad ejecutable es src/qore/infrastructure/trader_lab/capitalizer_scalper_certification_standard_v2.py. B Actions [cert standard CI #38076630610](https://github.com/mezas3238-hue/qore-core/actions/runs/38076630610) GREEN. Umbrales realmente definidos allí:

- **PF OOS cada era ≥1.50**, **PF OOS combinado ≥1.70**.
- **Expectativa OOS >0R** por trade; **Sharpe OOS ≥1.50**, **Sortino OOS ≥2.00**.
- **Drawdown OOS observado ≤10R** por era, y techo de aceptación **OWNER ≤6R**; el DD reportado del V49 236.13R es comparación en R, no porcentaje de equity.
- **Payoff medio ≥1.20**; **Monte Carlo probabilidad de beneficio ≥0.90**, **Monte Carlo p95 DD ≤15R**.
- Tras costes reales, **PF >1** y expectativa >0; esto NO reduce la exigencia de PF OOS 1.50/1.70. Winner retention obligatoria donde aplique **≥80% conteo y ≥90% masa R original** (934/415.748...).
- **Criterio de n:** en revisiones se solicitó n≥500 mínimo exploratorio e ideal n>1000; **no confundirlo con una constante de código V2 ya verificada si no aparece como gate**. La capacidad estadística, diversidad de sesiones/mercados, independencia OOS, R-multiple risk y estabilidad deben demostrarse, no asumirse por n solo.
- Missing mandatory evidence = MISSING/FAIL o INTERVENTION, jamás ACCEPTED. No certificar por CI verde, PF de 94 operaciones, simulated cost, o un año ya utilizado para diseño.

La certificación exige gobierno independiente del dataset y estrés multiera; reuso libre para investigar implica que el periodo queda **consumido** y no puede transformarse retroactivamente en holdout “virgen”.

---

# 8. PLAN DE EJECUCIÓN PARA EL SIGUIENTE ARQUITECTO — EN ORDEN, CON SALIDAS ACEPTABLES

**Fase 0 — fijar trazabilidad [P0]:** confirmar SHA A1/A2/parent, CI actual, archivar manifests de nueve M1, 2876 sources, 2822 timestamps y 2020 selected; fijar identidad y hash de cada artifact; test NOOP reproduce control. Abrir/actualizar issue P0 con enlaces de commits y gates. No empezar con optimización.

**Fase 1 — fidelidad de señal sin filtros [P0 B]:** reconstruir ruta V49 y sensor en ventana exacta desde setup M15 hasta próximo M15 y fin de tesis H1 sólo con eventos confirmados as-of; los 247 anticipados y 134 empates deben recibir **una causa individual** de discrepancia: distinta ventana, orden/tie-break, distinta primera FVG, distinta serie sweep, desincronía o bug reproducido. Auditar cierre de primera vela opuesta y estructura pertinente; crear fixtures SHORT/LONG y tests negativos. Emitir un ledger 381 MATCH/PARTIAL/CONFLICT con prueba de fidelidad primaria. **No tocar V49 histórico** durante esta fase.

**Fase 2 — Candle 3 source A/B [P0 B]:** preregistrar dos interpretaciones de C3, universos 9/9 sobre datos nativos, tasas 15/30/60 direccionales y cohortes temporales. No dejar que una definición “gane” por PF retrospectivo; si falta evidencia fuente, SOURCE_AMBIGUITY y no promover. Mantener M15/M1, stops, targets y MAX3 iguales para ensayo aislado. Pruebas as-of para pivot/right-H1 closure y POI.

**Fase 3 — mundo nueve mercados y epistemología [P0 A]:** consumir A1 [native witnesses #38080367716](https://github.com/mezas3238-hue/qore-core/actions/runs/38080367716), [inputs #38091052695](https://github.com/mezas3238-hue/qore-core/actions/runs/38091052695), [DST witness #38091938032](https://github.com/mezas3238-hue/qore-core/actions/runs/38091938032) y [DEGRADED #38092434895](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434895). Asociar 2822 barriers/2876 IDs con contexto H1/M15 probado y A2 sensores. 31 barreras incompletas se quedan visibles. No fabricar bid/ask, GOOD, régimen, world, graph, positions ni broker state. Si full no es posible, publicar inventario exacto de missing por candidato y bloquear PF cognitivo.

**Fase 4 — Full Master Frame PAPER [P0 A+A2]:** seleccionar una ruta canónica A1, ejecutar prepare_trader_cognition_packet→build_master_cognitive_frame→PASS/WAIT/ABSTAIN para cada fuente, actualizar chosen-settled-only, MAX3 cronológico y PAPER original fills. **La salida debe ser un artifact 2876 decisiones + trades + DD/PF completos** o un reporte BLOCKED con causas y cobertura, nunca un número inventado. Contrastar contra no-op y control. Medir por mercado, sesión, familia, H1 source, winner IDs y WINNER-R, información suficiente para adjudicar si **BAJÓ DD Y A QUÉ COSTE**.
**Fase 5 — adjudicación P0:** si PF sube pero pierde ganadoras o frecuencia, REJECT/INTERVENTION; si DD baja por dejar 0 trades, NO prueba de edge; si reporta DD sin costes reales, declarar gross/investigación. Sólo posterior a mundo completo y fuente reparada, estudiar ablación causal de sensores y mejoras de timing sin destruir edge.
**Fase 6 — robustez y certificación [P1]:** pruebas OOS por eras independientes, verdaderos BID/ASK y comisiones, multiasset open portfolio/exposición y drawdown monetario, Monte Carlo, Sharpe/Sortino, spread/slippage perturbations, test DST y missing-feed, suites de fuente y seguridad, threshold V2 completo y reviewer signoff. No VPS hasta autorización expresa.

### Gates por PR / Definition of Done

- **A2 método listo** sólo cuando el ledger 381 y C3 A/B y auditoría H1/M15/M1 tengan fuentes, fixtures y nueve mercados, sin desviaciones sin etiqueta y con CI verde.
- **A1 cognición integrada realmente** sólo cuando haya **2876 evaluaciones completas**, 2822 barreras, nueve percepciones por barrier y cerebro real invocado con WHY y cronología de memoria y selección MAX3; faltantes expuestos.
- **PAPER económicamente comparado** sólo cuando figuren PF/DD/retención/denominadores sobre mismo libro, control NOOP idéntico y coste/unknown declarado. **Nunca sustituir esta evidencia por 94 trades de V50-G o 1910 del veto de discrepancias**.
- **Certificación** sólo cuando estándares V2/OOS/costes/riesgo/robustez sean PASS; hasta entonces PRs DRAFT, no merge/LIVE.

---

# 9. LOCALIZACIÓN DE CÓDIGO, TESTS, WORKFLOWS Y REPORTES

## 9.1 B metodología: archivos centrales

Todo relativo a src/qore/infrastructure/trader_lab/ salvo cuando se indique:
- **capitalizer_high_frequency_capacity_census_v49.py:** generador 2876, H1/M15/M1 y primer disparador.
- **capitalizer_source_observation_detectors_v2.py**, **capitalizer_ttrades_m1_cisd_observer_v48.py**, **capitalizer_ttrades_m1_fvg_cisd_continuation_v48.py:** fuente y observadores CISD.
- **capitalizer_scalper_max3_counterfactual_audit_v1.py:** selección vs excluidas sin redefinir policy.
- **capitalizer_scalper_mfe_mae_v1.py:** MFE/MAE preterminal vs extremo OHLC terminal.
- **capitalizer_scalper_h1_liquidity_target_v1.py**, **capitalizer_scalper_h1_liquidity_paired_replay_v1.py**, **capitalizer_scalper_h1_target_asymmetry_audit_v1.py:** targets H1 causal y replay comparativo.
- **capitalizer_scalper_stop_noise_factorial_v1.py:** factorial de stop M15/M1 y veto noise.
- **capitalizer_scalper_h1_timing_session_diagnostic_v1.py:** dirección H1, edad, runway y rango parcial M1.
- **capitalizer_scalper_h1_direction_random_baseline_v1.py:** benchmark de reloj aleatorio, 32 draws/ID y coinflip.
- **capitalizer_scalper_m1_stage_chain_forensic_v1.py:** estudio de hitos M15→Sweep/FVG→CISD.
- **capitalizer_scalper_entry_timing_sensors_shadow_v1.py**, **capitalizer_scalper_entry_timing_sensors_census_v1.py:** sensores as-of/censo 9/9, primer-event discrepancy.
- **capitalizer_scalper_sensor_master_frame_bridge_v1.py** y **capitalizer_scalper_sensor_paper_decision_ab_v1.py:** contexto Master real tipo QORE y A/B PAPER de aceptación; atención: si A1 no tiene decision artifacts, son ONLY SENSOR/NOOP y no cognitivas.
- **capitalizer_scalper_cisd_381_discrepancy_forensic_v1.py:** forense 247+134, MFE/MAE emparejadas.
- **capitalizer_scalper_winner_retention_v1.py**, **capitalizer_scalper_v49_v50_g_waterfall_v1.py:** censos/retención ID y causa de densidad, lectores NO ejecutores.
- **capitalizer_scalper_certification_standard_v2.py**, **capitalizer_scalper_certification_metrics_v2.py:** límites y evaluación no transigible.
**Unit tests:** tests/infrastructure/trader_lab/test_capitalizer_scalper_*.py; testear as-of, LONG/SHORT, DST, gaps, misma barra stop/target, faltas de identidad, no-settlement leak.
**Workflows:** .github/workflows/qore-scalper-methodology-audit.yml, qore-capitalizer-scalper-certification-standard-v2.yml y los workflows qore-scalper-a2-* de nueve mercados.

## 9.2 A cognitiva: archivos centrales

- **capitalizer_master_cognitive_frame.py:** contrato Master Frame mundo, presión, percepción/régimen/graph y respuesta de intervención.
- **capitalizer_a1_trader_cognition_port.py**, **capitalizer_a1_multi_hypothesis_research.py**, **capitalizer_a1_chronological_cognitive_replay.py**, **capitalizer_a1_full_frame_research_adapter.py:** paquetes, competencia de oportunidades y memoria causal.
- **capitalizer_a1_sensorized_paper_runtime_v1.py**, **capitalizer_a1_master_frame_paper_trader_integration_v1.py:** cable sensor→Master real→decisión PAPER y economía.
- **capitalizer_a1_entry_timing_clock_v1.py**, **capitalizer_a1_native_nine_market_bar_witness_v1.py**, **capitalizer_a1_native_nine_market_epistemic_inputs_v1.py**, **capitalizer_a1_native_source_session_clock_attestation_v1.py**, **capitalizer_a1_native_clock_bound_perception_v2.py:** sincronización nativa, sesión y estados perceptivos.
- **capitalizer_a1_m1_protected_route_forensics_v2.py**, **capitalizer_a1_m1_second_pivot_forensics_v3.py**, **capitalizer_a1_source_sensor_independent_attestation_v1.py**, **capitalizer_a1_validated_sensor_overlay_v1.py:** testigos causales y nulas no-certificaciones.
- **capitalizer_a1_historical_full_frame_preflight_v1.py**: censo de faltantes world/attestation antes del replay, no inventar métricas si falla.
**Workflows:** .github/workflows/qore-scalper-cognition-audit.yml, qore-scalper-a1-real-nine-market-epistemic-inputs-v1.yml, qore-scalper-a1-real-native-clock-bound-perception-nine-markets-v2.yml (ver el nombre exacto en el branch actual), qore-scalper-a1-* forensics y research quality. **No dar nombres deducidos como rutas verificadas sin revisar árbol HEAD.**

## 9.3 Informes canónicos, evidencias y lectura antes de programar

1. **Este handoff maestro** (rama B PR #759), síntesis vigente de A1+A2, con prioridades y errores actuales.
2. [Master histórico del programa #623](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_CAPITALIZER_COGNITIVE_SCALPER_MASTER_HANDOFF_2026-10-10.md): 60k+ caracteres, historia y fuente; algunos NEXT ACTION anteriores están OBSOLETOS y este handoff tiene precedencia.
3. [B novena CISD 381 completa](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_NINTH_CISD_381_SOURCE_AND_MFE_MAE_PREREG_2026-10-10.md).
4. [B sensores + A/B PAPER](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_OWNER_SENSOR_TO_TRADER_PAPER_DECISION_AB_2026-10-10.md).
5. [B sesgo H1 random diagnostic](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_SIXTH_AUDIT_H1_RANDOM_BASELINE_AND_C3_FIDELITY_PREREG_2026-10-10.md).
6. [B M15/M1 stage ledger](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_SEVENTH_AUDIT_M1_CHAIN_SOURCE_STAGE_PREREG_2026-10-10.md).
7. [B V50-G real, nueve mercados y winner preservation](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_V50G_NINE_MARKET_VERDICT_AND_WINNER_AUDIT_2026-10-10.md).
8. [A1 actualización DÉCIMA: source-first freeze](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/docs/research/QORE_SCALPER_A1_TENTH_AUDIT_METHOD_FIRST_FREEZE_2026-10-10.md).
9. [A1 perceptions V2 realmente 2876 DEGRADED](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/docs/research/QORE_SCALPER_A1_REAL_2876_CLOCK_BOUND_PERCEPTIONS_V2_2026-10-10.md).
10. [A1 sensor→Master→PAPER real integration tests](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/docs/research/QORE_SCALPER_A1_A2_MASTER_FRAME_SENSOR_TO_PAPER_EXECUTION_INTEGRATION_2026-10-10.md).
11. [A1 world/M1 historical blocker report](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-a-cognition-20261010/docs/research/QORE_SCALPER_A1_HISTORICAL_MASTER_FRAME_NATIVE_M1_EXECUTION_FINDINGS_2026-10-10.md).
12. [Cert Standard V2 CI #38076630610](https://github.com/mezas3238-hue/qore-core/actions/runs/38076630610), [B methodology CI #38076627175](https://github.com/mezas3238-hue/qore-core/actions/runs/38076627175), [A perception V2 CI #38092434895](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434895).

---

# 10. CONTRATO DE HANDOFF / COMUNICACIÓN OBLIGATORIA ENTRE ARQUITECTOS

**A2 (siguiente responsable de metodología)** debe publicar issue #757 y avisar #756/PR #758: fuente exacta TTrades C2/C3/CISD, ledger de los 381 conflictos **por source ID**, denominador original 2876, prueba de bar-close nativa y sugerencia de corrección única con fixture; NO transferir MFE/MAE posthoc a features Master.

**A1 (responsable cognitivo)** debe publicar en issue #756 y avisar #757/PR #759: input/provenance/world por las 2822 barreras y 2876 candidatos, los 31 missing moments, clases epistémicas y WHY, versión exacta de motor y **evidencia de Master REAL invocado**. Resolver una ruta canónica para competir/autorizar PAPER y evidenciar memoria settled-only. Si no puede demostrar world completo, publicar formalmente cada BLOCKED y no fingir PF.

**Quien cierre el replay** debe depositar en un único artifact inmutable: (i) manifest SHA por símbolo/archivo; (ii) 2876 decision rows y causa de ausencia; (iii) trade-book elegidas ordenadas; (iv) matriz control/NOOP/cognitiva; (v) PF/DD bruto y, donde haya datos físicos, neto; (vi) retención por source winner ID y original winning-R; (vii) alertas de información futura, 381 discrepancias, 31 missing snapshots, 501/12/124 testigos pendientes; (viii) duraciones de sesión, máximos intrabar ambiguos, cambios por familia/sesión/mercado; (ix) todos los tests reproducibles Actions GREEN en SHA congelado y enlace PR.

**Si los resultados fueran malos:** no borrarlos ni reescribir este handoff; abrir una nueva hypothesis / prereg reproducible en rama de investigación, bajo las restricciones de fidelidad y preservación. No pasar a VPS.

---

# 11. FOTO EXACTA AL CIERRE DEL HANDOFF

| Hecho | Estado |
|---|---|
| V49 original 2876 source, 2020 MAX3, PF .664, DD236.13R | **CONFIRMADO ECONÓMICAMENTE NEGATIVO** |
| Censo de sensores 9/9 y anomalía 381 | **COMPLETADO, discrepancia no resuelta** |
| Caracterización 381: 247 temprano / 134 misma hora otra familia | **COMPLETADO; causa de ventanas/precedencia PENDIENTE** |
| CISD cierre sobre serie opuesta y no mera mecha | **MATCH básico; vínculo exacto de swing/POI parcial** |
| A/B Candle 3 entre fuentes diciembre y enero | **NO EJECUTADO / SOURCE_AMBIGUITY** |
| H1 target/swing y stop/noise factorial | **PROBADOS Y RECHAZADOS ECONÓMICAMENTE** |
| Benchmark aleatorio H1 y 15/30/60 | **COMPLETADO; penalización timing, no PF aleatorio** |
| M1 stage timing y cero delay after CISD | **COMPLETADO** |
| Sensores >20 y adaptador a CandidateContext Master | **CÓDIGO Y PRUEBAS COMPLETADOS; NO son autoridad** |
| A1 Master real con memoria settled-only | **CÓDIGO/TES­TS DE INTEGRACIÓN, no replay histórico completo** |
| Native synchronized 9 markets 2822 instantes | **CONSEGUIDO; 31 parcialmente incompletos** |
| 2876 percepciones fuente a DEGRADED, 22522 BAD | **EVIDENCIA REAL, 0 GOOD** |
| 501 M1, 12 M15, 124 H1 sin testigo estructural independiente del auditor | **PENDIENTE ADJUDICACIÓN, NO declarar todas inválidas** |
| Master Frame 2876 decisiones reales y resultado PF/DD | **BLOQUEANTE P0; NO EXISTE EL RESULTADO** |
| BID/ASK, comisión y costes físicos por operación | **PENDIENTE** |
| OOS multiera/certificación V2 | **NO EVALUADO, NO CERTIFICADO** |

**Éxito de sucesor = menos DD demostrable gracias al VERDADERO cerebro actuando sobre información causal, sin violar source TTrades ni diezmar ganadoras, con tiempo, identidad, riesgo, costes y OOS explicados.**

**FIN — CONTINUAR EN GITHUB, SIN VPS Y SIN LIVE.**

---

# 12. NOTA FINAL FIRMADA DE CONTINUIDAD — TRABAJO EXACTO DE LA PRÓXIMA MISIÓN

## 12.1 Estado económico congelado

V49 nueve mercados, datos provider-native M1, 2025-09-17 a 2026-09-17: 2.876 oportunidades únicas, 2.020 seleccionadas MAX3 portfolio, 1.167 ganadoras, 852 perdedoras y 1 plana, PF bruto 0.664463, neto −233.269R, drawdown máximo 236.134R, ganancias originales +461.943R. Los umbrales de conservación son **934 ganadoras originales** y **415.7485R de su masa original**; mantener frecuencia y n útil, además de PF OOS y drawdown. R no es porcentaje de equity; no se han aplicado BID/ASK, comisión y slippage físicos. Datos y fuente: [V49 nine market #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), M1 proveedor [#35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334). No cambiar el control.

Intentos anteriores descartados:
- V50-G Geometry 220 operaciones, PF 1.096 DD20.33R; V50-G llamada Cognition (puente PARTIAL, no Master Full) solo 94 operaciones PF1.595 DD9R y apenas 37 ganadoras originales. Fracaso por destrucción de población.
- Cambiar targets HTF más lejos preservó 942 winners pero 387.58R originales y empeoró DD 279.56R. Stops M1/M15 y veto de ruido no recuperaron edge.
- Baseline aleatorio misma tesis H1 a 30 minutos 54.9%-56.2% frente 43.6% del M1 real: evidencia de selección temporal desfavorable, NO PF de entradas aleatorias.
- Stage sweep→CISD −12.56 puntos de favorabilidad +30m, CISD→entry = cero delay; no promover una entrada en barrido antes de validación.
- Sensor con rechazo mecánico de discordancias 381: 1.910 trades, PF .62131, DD252.10R, 385.08R masa ganadora original: RECHAZADO. El Master Frame debe interpretar, no convertir estos sensores en hard gates.

## 12.2 Diferencias metodológicas y fuentes, sin confundirlas con PF

Origen general: [TTrades Scalping Model](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/) H1 tesis Candle2/3→M15 protected swing→M1 timing. [Understanding CISD](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/), [MSS versus CISD](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/) y [CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/): cierre por encima/debajo de la primera apertura de la serie de velas opuestas, vinculada al swing y al POI/HTF pertinentes. V49 cumple el nivel de cierre básico en Sweep (series[0].open), pero **no está certificada la identidad correcta de la serie/swing/POI**.

El censo 381 clasificado [#38076268436](https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436): **247 primeros eventos de otra familia antes de la entrada V49** (171 originales FVG frente sensor Sweep temprano, 76 originales Sweep frente sensor FVG temprano), **134 misma vela distinta familia** (original Sweep frente sensor FVG). No se observaron otras categorías en este panel: un registro as-of no puede ver una CISD posterior al momento original, y no hubo falta de observación. Los 381 tienen **familia distinta**, no prueba de signo CISD invertido; comprobar por source ID ventana hasta próximo setup M15/H1 as-of, POI y precedencia de evento, no por mejor retorno MFE. La ventaja temprana a +30m es +5.80 puntos en 224 pares, pero a +15m es −3.35 y +60m es 0; MAE aumenta. No constituye una entrada monetizable.

**Candle 3** sigue SOURCE_AMBIGUITY: lectura diciembre 2025 C3 dentro del rango C2 y cierre fuera de su cuerpo frente interpretación enero 2026 que cita cierre más allá de apertura/rango. B debe A/B separado autor-fiel con universos distintos, no escoger por PF in-sample. Contextos Asia/London/NY pueden tener rutas fuente Daily/H4 divergentes del genérico QORE; ver ledger autor en sección 1 y archivos adicionales listados en §9.

## 12.3 Lo construido en cognitiva REAL y funciones del cerebro

La rama A1 PR #758 conserva:
1. **Master Frame:** capitalizer_master_cognitive_frame.py; recibe el mundo y hipótesis, mercado/regímenes, grafo intermercado, evidencia candidata y presión. Evalúa estado epistemológico, incertidumbre y razonamiento WHY; la existencia de la API no significa que el mundo histórico esté construido.
2. **Entrada y sensorización:** capitalizer_a1_trader_cognition_port.py, capitalizer_scalper_entry_timing_sensors_shadow_v1.py, capitalizer_scalper_sensor_master_frame_bridge_v1.py y capitalizer_a1_sensorized_paper_runtime_v1.py. H1 sesgo/antigüedad, stop M15 declarado, M1 sweep/opposing series/FVG/retrace/CISD, rango H1 parcial, reloj NY, session runway, volatilidad, gaps, target y broker bid/ask si son reales. Cada sensor con status, reloj y procedencia, NO con winner-R futuro. Sin testigo causal real, estado NOT_AVAILABLE, nunca cero o GOOD inventados.
3. **Competición:** capitalizer_a1_multi_hypothesis_research.py, capitalizer_a1_joint_competition_research.py; estudiar oportunidades concurrentes a igual timestamp en nueve mercados. MAX3 aplica **a escala de portafolio por sesión/fecha**, no 3 por símbolo.
4. **Memoria temporal:** capitalizer_a1_chronological_cognitive_replay.py y cognitiva Master PAPER; solo outcomes efectivamente elegidos y settled antes del siguiente decision_at, no registrar ni aprender pérdidas de hipotéticos rechazados.
5. **Trader PAPER real con fixtures:** capitalizer_a1_master_frame_paper_trader_integration_v1.py::run_real_master_frame_paper_trader y capitalizer_high_frequency_trader_v49.py::select_master_frame_trade_intents. DEBEN reconciliarse en una ruta única, sin PASS simultáneos inconsistentes. En fixtures se prueban decisiones sobre datos sintéticos, **no existe resultado económico histórico real 2876**.
6. **Observación 9 mercados:** capitalizer_a1_native_nine_market_bar_witness_v1.py, capitalizer_a1_native_nine_market_epistemic_inputs_v1.py, capitalizer_a1_native_clock_bound_perception_v2.py, capitalizer_a1_native_source_session_clock_attestation_v1.py, protected pivot v2/v3 e independent attestation. 2.822 barreras, 2.876 IDs, 2.791 9/9 M1 exactas, 31 parciales, 2.876 DEGRADED, 22.522 BAD, 0 GOOD; 2.375 testigos protected swing M1 (1.885 iniciales +490 pivotes siguientes), 501 sin ese testigo; 12 M15 y 124 H1 sin prueba independiente; esto NO prueba que sean inválidas.
7. **Frontera contra futuro:** capitalizer_a1_cisd_outcome_blind_method_boundary_v1.py, CI A1 nine-market reciente SUCCESS, impide pasar MFE/MAE/retornos posteriores de la auditoría B a decisión Master. Mantener los tests causales y right-censorship de h1_state_until futuro.

## 12.4 Responsabilidades y Definition of Done inequívocas

**B metodología / PR #759, issue #757**: publicar por fuente la causa de **cada una de las 381 discrepancias** (ventana H1/M15/route priority/source swing y POI), resolver Candle 3 A/B con texto de fuente y pruebas causales, y reconciliar testigos H1/M15/M1. NO reescribir el libro V49 ni eliminar Sweep/FVG o introducir veto por inventario epistémico. Los defectos demostrados deben corregirse con prueba negativa y nueva comparación OOS congelada.

**A cognitiva / PR #758, issue #756**: sincronizar 2.822 barreras reales, nueve snapshots fuente por instante, regímenes y causal graph honestamente UNKNOWN si faltan hechos; construir World Model con sesiones NY/DST, posiciones open/settled, presupuesto/pressure y memoria elegida/settled-only. Aplicar los sensores A2 as-of y confirmar fuentes H1/M15/M1; ejecutar verdadero build_master_cognitive_frame por cada uno de los 2.876 IDs, publicar PASS/WAIT/ABSTAIN más WHY, hash de world/sensores/engine, fuente temporal, elegibilidad MAX3, orden PAPER, settlement y cambios de memoria. Si alguno falta, BLOCKED con conteos e IDs y PF cognitivo NULL, nunca un PF fingido.

**Comparación entregable**: A = V49 control 2.020 PF .66446 DD236.134R; A0 = NOOP sensores idéntico; B = Master FULL A1 y sensores, PF/DD por medir; C = veto 381 PF .62131 DD252.10R, rechazado. Para B exigir densidad, IDs ganadores originales preservados >=934, masa original >=415.7485R, PF bruto y —si existieran quotes/costes reales— neto, DD peak-to-trough en R, riesgo agregado, Sharpe/Sortino calculados sobre returns válidos, resultados por mercado/sesión/familia/fecha, y bootstrap/OOS multiera sin hindsight. Cero trades no se interpreta como DD exitoso.

**Gate de integración:** usar GitHub Actions pinned SHA, logs y artifact 9/9 más 2876 decisiones, conciliar ante cualquier mismatch. No modificar simultáneamente target, stop, C3 y CISD; no seleccionar configuración por PF in-sample. V50-G de 94 trades está rechazado y la certificación estándar V2 sigue bloqueada por PF OOS neto, DD, muestras, robustez y broker físico. Fuentes 2023/2024 OOS no atestadas; año V49 se considera desarrollo ya consumido.

**Cómo continuar desde GitHub:** leer este handoff → comprobar HEAD y CI de ambos PR → cargar artefactos V49 #38053946695, nativo #35548099334, M1 9mercados #38080367716, percepción #38092434895 y forensic CISD #38076268436 → cerrar fidelidad por source IDs y origen temporal → completar el World Model con evidencias realmente disponibles → ejecutar FULL Master PAPER no-lookahead con MAX3 portfolio y memoria settled-only → publicar matriz PF/DD y preservación por identidad o reporte BLOCKED con causas. Los PR continúan DRAFT, no hay autorización de merge, VPS, MT5 ni LIVE.

**Estado final y sucesor esperado:** infraestructura sensorial/cognitiva funcional en pruebas; causa CISD route precedence y definición C3 pendientes; entradas PAPER Master FULL 2876 sin medir, no hay PF/DD cognitivo; certificación NO. Handoff definitivo entregado por GitHub; siguiente trabajo empieza exactamente en B #759 / A #758, jamás desde resultados V50-G rechazados.


---

# 13. A2 SUCESOR — HALLAZGOS EJECUTADOS DESPUES DEL HANDOFF bbb4173 (2026-10-10)

Esta sección es posterior a la firma del handoff original. Se añaden evidencias sin reescribir los resultados históricos ni sustituir el baseline V49.

## 13.1 C3: dos lecturas fuente realmente parametrizadas y comparación H1 provider-native

Documentación/fuentes exactas y prereg: [QORE_SCALPER_A2_C3_SOURCE_VARIANTS_METHOD_FIRST_2026-10-10.md](QORE_SCALPER_A2_C3_SOURCE_VARIANTS_METHOD_FIRST_2026-10-10.md).
- Comparador sin autoridad de admisión: src/qore/infrastructure/trader_lab/capitalizer_scalper_c3_source_variants_v1.py. Diciembre 2025: C3 no barre C2 pero supera su cuerpo; enero 2026: hipótesis de ingeniería C3 cierra fuera del rango C2. NO establecer fidelidad exacta de segundo texto por sus resultados.
- Censo nativo src/qore/infrastructure/trader_lab/capitalizer_scalper_a2_c3_native_geometry_census_v1.py: [CI 9market #38095270532 SUCCESS, 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38095270532), [artifact matriz #11685698012](https://github.com/mezas3238-hue/qore-core/actions/runs/38095270532/artifacts/11685698012). 45086 tripletas H1 consecutivas con 60/60 M1 reales: DECEMBER_ONLY 2964, JANUARY_ONLY 21445, NEITHER 20677. 2876 fuente-IDs reconciliados, 238 CANDLE3 basis originales, 1460 linked native H1 C3 geometries exactas. 0 ejecución alterada.
- Lo anterior es GEOMETRIA, no POI/CISD autor atestados, y el gran tamaño de JANUARY no autoriza implantación ni demuestra alta densidad rentable.

## 13.2 Diagnóstico CISD 381 ahora cerrado COMO MECANISMO COMPUTACIONAL (no autor-fidelidad)

**[GitHub Actions source/native/full-prefix #38095562104 SUCCESS, 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38095562104)**, SHA de ejecución `a442a0d844b13cb4d013107b1b3721624abf574d`; [artifact aggregate #11685273575](https://github.com/mezas3238-hue/qore-core/actions/runs/38095562104/artifacts/11685273575). Programa src/qore/infrastructure/trader_lab/capitalizer_scalper_a2_cisd_prefix_causality_v1.py, workflow .github/workflows/qore-scalper-a2-cisd-window-nine-market.yml. Usa M1 provider-native nueve mercados y fuentes/sensores V49 congelados.

Se reconstruyó por cada uno de los 2876 source_opportunity_id el M15 parent y sus dos observadores V48:
- **FULL_WINDOW** desde M15 confirmado hasta siguiente M15/H1 boundary histórico: coincide con el ID, familia y close V49 original **2876/2876**.
- **ASOF_CLOSED_PREFIX** desde M15 confirmado hasta close original M1, no futuro: coincide con el ID, familia y close de shadow sensors **2876/2876**.
- **2495** MATCHED_BOTH_WINDOWS; **381** RECONSTRUCTED_FULL_VS_PREFIX_SELECTION. 0 M15_PARENT_NOT_RECONSTRUCTED, 0 fuentes ausentes, 0 nuevas órdenes. Ello **explica completamente por qué el mismo par de detectores QORE produce 381 familias/tiempos discordantes**, sin escoger ganador por MFE/MAE.
- Las 381 incluyen la clasificación previa 247 FIRST SENSOR EARLIER DIFFERENT FAMILY +134 SAME_CLOSE DIFFERENT_FAMILY; no prueban CISD direccional invertida (sensor hereda H1 direction).

**Riesgo P0 nuevo:** V49 seleccionó retroactivamente un primer evento con información de su ventana COMPLETA hasta un límite M15/H1 derivado del futuro. Un prefijo observado al momento de decisión puede escoger otro evento; por tanto el histórico V49 no tiene demostrada *prefix-invariance / online causal execution* en esos 381 IDs. No confundir la prueba del origen de discrepancia con determinar que el evento V49 sea falso según la fuente TTrades, ni suponer que la entrada sensor sea operable. El ledger full-window es un instrumento FORENSE EX-POST, nunca un feature cognitivo.

**Reparación exigida ANTES de nuevo PF/DD certificado:** preregistrar nuevo replay de observadores ONLINE cerrado por cada M1 y cada parent M15, con múltiples rutas/TTrades y POI, fijando evento de primera confirmación realmente disponible, y compararlo contra V49 preservado mediante IDs y matriz. No usar winner-label, MFE/MAE, P&L ni next M15/H1 futuro para admission. Sin gate universal 381 ni retiming arbitrario. Comprobar efectos en densidad, MAX3 portfolio y >=934 IDs vencedores y >=415.74848565R masa original; medir PF/DD sólo después de replay causal con entries reales, y OOS independiente. Escalar fuente autor CISD swing/POI y Candle 3 antes de ejecutar.

A1 sigue dueño del Master Frame y debe recibir únicamente testigos source-fieles confirmados <= decision_at; FULL_WINDOW/h1_state_until retrospectivo se mantiene fuera de cerebro. El PF/DD FULL Master sigue NO MEDIDO. Estado final: explicación técnica de 381 **CERRADA**; fidelidad semántica C3/POI/swing **PENDIENTE**; replay causal online corregido **PENDIENTE**; certificación NO, ningún VPS/LIVE/MERGE.

---

# 14. UNDÉCIMA AUDITORÍA — H17 CORREGIDA Y CISD PREFIX-INVARIANCE (10 OCT 2026)

**Leer primero el nuevo [informe rector metodológico del ciclo 11](QORE_SCALPER_A2_ELEVENTH_AUDIT_H1_C2_C3_AND_CISD_FIRST_SELECTION_2026-10-10.md).** Prioridad P0 es verificar el núcleo de V49; no añadir complejidad cognitiva o filtros hasta que fuente, testigo y causalidad se reconcilien.

**Censo histórico H1 ORIGINAL, [Actions #38096345552 SUCCESS 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38096345552), nueve mercados y 2876/2876 IDs:** 2638 (91.7%) etiquetados **CANDLE2_REVERSAL** y 238 (8.3%) **CANDLE3_CONFIRMATION**; 1604 sesiones con estado H1 heredado y 1272 con estado originado en evento H1. La frase de auditoría "solo 8,3% cumple la estructura de TTrades" es una inferencia NO sustentada: autor admite Candle2 **O** Candle3 en la fuente genérica. Tampoco afirmar fidelidad confirmada de los 2638: aún faltan POI, C2/C3 author closure, M15 swing, M1 real, estado heredado y prueba de la temporalidad. H17 es ahora investigación de fuente/POI y revalidación del H1, no un 91,7% de falla.

**381 discrepancias CISD:** run reproducido #38095562104 demuestra 381 diferencias de primera selección en ventana histórica V49 versus prefijo M1 sensor. NO demuestra per se ausencia del evento V49 en el conjunto de todos candidatos online. Nuevo ledger de comparación de primera coincidencia por ruta / tiempo `capitalizer_scalper_a2_eleventh_cisd_prefix_membership_v1.py`, GH Actions `qore-scalper-a2-eleventh-cisd-membership-nine-market.yml`; distinguir `future_dependent_offline_first_selection` de `original_absent_from_all_asof_candidates`, éste último UNKNOWN sin enumerador exhaustivo. No autorizar ningún veto 381.

**Reparación fuente previa a economía:** build causal online de candidatos CISD/timestamps, no leer ventana full o H1.state_until futura; una sola política de prioridad TTrades, POI/swing por evento, no vender un reemplazo PF ajustado. Recalcular diagnósticos H1 favorable/random, Sweep→CISD, MFE/MAE y target geometría estratificando los 2495 matched y 381 discordant sobre los 2876 IDs, y N real de ejecutados MAX3 por cada grupo (NO llamar 2495 trades). Sin PASS/ABSTAIN actuando ni PF/DD Master Full hasta certificado. Handoff actualizado pero PR #759 sigue DRAFT.


### 14.1 UNDÉCIMA cierre P0 CISD por ID (posterior al resumen del apartado 14)

[GitHub Actions #38096548896 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38096548896), [artifact #11686545003](https://github.com/mezas3238-hue/qore-core/actions/runs/38096548896/artifacts/11686545003): **2876/2876** eventos CISD V49 originales son observables al cierre de su M1 bajo el observador de SU PROPIA RUTA con datos prefijo. **2495** son ademas la primera seleccion global online; **381** difieren en primera selección global. No hay 381 eventos fisicamente no observables demostrados: el error confirmado es competencia/precedencia global no prefix-invariant. Resultado QORE interno, NO prueba POI/swing/serie original TTrades.

El ledger per-ID publica original_route_first_at_source_close y original_is_first_online_candidate. La enumeracion completamente independiente de todas candidatas por evento tiene estado no-finalizado y no justifica un "LOOKAHEAD_EVENT" binario imputado a 381. La corrección posterior debe emitir eventos M1 online sin conocer futuro y comparar densidad/ganadores/PF/DD bajo MAX3 solo una vez adjudicada fuente. Se conserva el baseline V49, 0 veto, DRAFT sin certificacion ni LIVE.

---

# 15. DECIMOTERCERA AUDITORÍA — H17 fuente, POI y selección causal-first (10 OCT 2026)

**Documento de trabajo:** [QORE_SCALPER_A2_THIRTEENTH_C2_POI_AND_FIRST_STREAM_ECONOMIC_2026-10-10.md](QORE_SCALPER_A2_THIRTEENTH_C2_POI_AND_FIRST_STREAM_ECONOMIC_2026-10-10.md).

El auditor acepta H17 fuerte RETIRADA: 2638/2876 H1 origen C2, 238/2876 origen C3; POI/swing autor pendientes. El rechazo blanket de las 381 sigue prohibido. 2876/2876 CID original existe por su propia ruta usando el prefijo al close; 381/2876 no coincide en primera selección GLOBAL online. No se ha demostrado todavía que las políticas produzcan los mismos retornos, ni que la primera familia offline sea un criterio ejecutable en línea. Los diagnósticos V49 anteriores son válidos como descripción **histórica** de su población fija, pero no son prueba económica de un nuevo portfolio causal-first.

**Nueva fuente TTrades fechada 15 NOV 2025:** https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/ exige barrido de extremo previo, cierre dentro del rango y POI HTF; admite FVG, swing y ocasionalmente vela contraria como POI. La generación QORE V49 usa solamente POIs tipo FVG H1 o swing H1; oposición de vela y HTF mayor no están atestadas. La función v48._aggregate(60) permite barras parciales **45/60** y su timestamp closed_at se deriva del último M1 observado, no necesariamente HH:00 real. Esto es un importante **supuesto estructural por auditar**, sin concluir que toda barra parcial es invalidación. Cada source-ID debe tener recibo exact 60/60 cuando exista, o UNKNOWN y por qué.

**Código/tests CI de verificación H1:** capitalizer_scalper_a2_thirteenth_h1_poi_native_audit_v1.py, test_capitalizer_scalper_a2_thirteenth_h1_poi_native_audit_v1.py, workflow qore-scalper-a2-thirteenth-h1-poi-nine-market.yml. Reconstruye cada origen de estado, incluyendo 1604 inherited, con H1 nativo, POI fechado al tercer cierre, interacción y cierre C2/C3; distingue `SOURCE_QORE_MATCH` de validación independiente de fuentes del autor; conserva 2876 IDs, cero vetos.

**Código/tests CI de equivalencia M1:** capitalizer_scalper_a2_thirteenth_cisd_stream_pairs_v1.py, test_capitalizer_scalper_a2_thirteenth_cisd_stream_pairs_v1.py, workflow qore-scalper-a2-thirteenth-online-paired-nine-market.yml. El recorrido online consulta ambas familias en cada prefijo M1 y **emite en primer instante de descubrimiento**, sin backdating de confirmación vista tarde ni H1.state_until futuro; preserva el censo 2876, los 381/2495 congelados, y estratifica MAX3 original 2020 y MAX3 contrafactual anclado. Calcula exclusivamente labels ex-post de retorno close+15/+30/+60 y máximos/minimos observados como MFE/MAE, con diferencia pareada normalizada por riesgo V49 original; NO es una ejecución de nuevas órdenes ni cálculo de PF/DD de sistema nuevo. No confundir sensor primera familia as-of-original con detector streaming primer descubrimiento.

**Bloqueos:** falta adjudicación POI del autor, confirmación H1 60/60, swing M15, M1 CISD route policy autor, comparación con costos físicos, y replay económico real universal MAX3 sin variar políticas post-outcome. Nueva cognitiva/World Model permanece congelada; PRs DRAFT, no VPS/MT5/live. No certificar por test de software GREEN.

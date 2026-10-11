# HANDOFF MAESTRO — QORE TRADER SCALPER | A1 cognitiva + B metodología

**Fecha de corte:** 10 de octubre de 2026. **Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core).  
**Propósito:** entregar al próximo arquitecto todo el contexto verificable de la reconstrucción del Trader Scalper, los trabajos A1 efectivamente realizados, hallazgos de B, riesgos sin resolver y ejecución PRIORITARIA.  
**Rama de ESTE handoff:** agent/scalper-architect-a-cognition-20261010; [PR A1 #758 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/758).  
**Rama del arquitecto de metodología:** agent/scalper-architect-b-methodology-20261010; [PR B #759 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/759).  
**PR programa original:** [#623 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/623). Issues: #756 cognitiva y #757 metodología.  
**Snapshot consultado al redactar:** A1 89932e6f9375fdc6e13cfdc2f06641d85b60c37d; B 88bf302174adc0a3df5a5d2cb6166725b32e394b. **Las ramas evolucionan en paralelo**: comprobar HEAD y Actions de nuevo; nunca suponer que estos son los HEAD definitivos de otro arquitecto.  
**Autoridad:** RESEARCH / PAPER, exclusiva de GitHub. **NO CERTIFICADO. NO MERGE, VPS, DEMO, MT5, LIVE, dinero real ni despliegue.** El hecho de pasar Ruff/Mypy/Pytest NO autoriza entradas.

---

## ACTUALIZACIÓN PRIORITARIA EN EL MOMENTO DE ENTREGA — Auditorías XIV y XV de B

**Esta sección SUPERA las cifras anteriores de las auditorías XII/XIII cuando entren en conflicto.** Se comprobó el trabajo del arquitecto B en su rama GitHub, incluidos los resultados nuevos **después** del snapshot inicial de este documento. El siguiente arquitecto DEBE tomar estas cifras como estado de investigación más reciente y volver a consultar el HEAD de B; la rama sigue en evolución.

### AUDITORÍA XIV — avance económico medido por primera vez, pero aún perdedor

[GitHub Actions #38102352779, 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38102352779) (código B SHA b4d35fe99b99a96dac3728610258fe5a4ab20c15). Primer **replay económico histórico source-anchored con elección M1 first-online**, stop M15 V49, target H1 recalculado al nuevo cierre as-of, STOP-FIRST, salida objetivo/sesión y portfolio MAX3 nueve mercados. Conserva el universo de **2876 fuentes V49 originales** como punto de partida; **NO** regenera los eventos H1/M15 desde el dato crudo para descubrir oportunidades fuera de esa población. **NO** es un full-brain/corredor BID-ASK físico, ni OOS autor-certificado.

| Medida bruta | V49 original | First-online source-anchored |
|---|---:|---:|
| Candidatas antes MAX3 | 2876 | 2816 válidas (36 geometrías SL M15 inválidas, 24 sin target H1) |
| Trades elegidos MAX3 | 2020 | **1997** |
| Wins | 1167 | **1154** |
| PF bruto | 0.6644630742 | **0.8425240505** |
| DD máximo bruto R | 236.134284 | **114.799099** |
| Resultado bruto R | −233.269327 | **−109.055389** |
| Beneficio bruto R | 461.942762 | 583.465531 |

**Conclusión:** PF **+26,8% relativo**, DD **−51,4%**, pero **PF < 1** y pérdida de **109,06R** incluso antes de broker BID/ASK/comisión. Es un progreso económico real y cuantificado, **NO cumple la misión de edge rentable**. La diferencia mezcla cambio de instante/familia, 60 fuentes no elegibles y selección MAX3; no atribuir toda la mejora a una sola regla. No construir World Model para encubrir esta pérdida.

**Ganadores por identidad:** [GH Actions #38102633581 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38102633581): conserva **1947** de los 2020 IDs ejecutados originales; 73 salen y 50 entran. De 1167 ganadoras originales, **1137 IDs** siguen seleccionados y representan **449.711269R/461.942762R = 97,35%** de la masa ganadora histórica identificada. **32/1137** cambian de ganadoras a perdedoras bajo el nuevo timing/target: conservar el ID NO equivale a conservar su beneficio realizado. El siguiente arquitecto debe medir retención tanto de ID como de win efectivo y R, por cartera y cohorte; las barreras Owner de 80% de IDs y 90% de R no garantizan rentabilidad.

### Auditoría XIV — CORRECCIÓN definitiva de los falsos 111 H1 sin POI

[GitHub Actions #38102351044 — 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38102351044), con lookback **exactamente 14 días** como el V49 original (antes un auditor reconstruía con 15 días): **2638/2638** C2 y **238/238** C3 H1/POI intrínseco vuelven a conciliar; **2876/2876** sesgos fuente reconstruidos. Los antiguos **111 sin reconstrucción** eran **artefacto de diferencia de lookback**, NO evidencia de POI ausente; queda explícitamente PROHIBIDO usarlos como diagnóstico vigente. **2372/2876** con las dos velas H1 60/60 físicas comprobadas, **504** sin doble cierre H1 íntegro (PARTIAL, NO veto).

[GitHub Actions #38102651079 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38102651079): **152** testigos H1 source off-clock (cierre registrado fuera de HH:00 UTC) con ese lookback, **CERO** M15 setups y **CERO** primeras órdenes M1 confirmados antes del verdadero cierre HH:00 de esas 152. **NO** se ha probado lookahead temporal de entrada por este problema, aunque aún falta verificar integridad OHLC de barras H1 parciales (45/60), POI HTF del autor, fuentes de swings y causalidad de la herencia H1. NO vender 8,3% C3 como falta de fidelidad: H1 admite C2 **o** C3. 

### AUDITORÍA XV — explicación de la pérdida residual, ahora con datos medidos

[GitHub Actions #38104619725 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38104619725), [artifact audit15](https://github.com/mezas3238-hue/qore-core/actions/runs/38104619725/artifacts/11689048493). Analizó 9 mercados, 2876 oportunidades, el mismo replay 1997 MAX3 y 2020 baseline; **no reajustó por outcomes**.

- Desglose de caída de fuentes: **36** INVALID_M15_STOP + **24** NO_H1_TARGET = 60 no elegibles antes MAX3; **73** IDs basales fuera del portfolio y **50** añadidos; **32** antiguas ganadoras seleccionadas pasan a perder tras el cambio.
- **32/32** ganadoras→perdedoras adelantaron su entrada; desplazamiento mediano **−33 minutos**; **25** pasan de TARGET a STOP, **4** TARGET→SESSION_EXIT, **2** SESSION_EXIT→STOP, **1** permanece SESSION_EXIT; **20/32** tienen target cambiado y **0/32** cambio en SL fuente. **17** pertenecían al antiguo subgrupo de 381 divergencias y **15** a otro grupo, lo que demuestra por qué 381 NO agota el problema online.
- En los **1997** nuevos trades, **935** tenían *target planificado inferior a 0,5R*; sólo **549** tenían target >=1R; target mediano **0.537R**, ganancia media de trade positivo **0.5056R** vs pérdida media por trade negativo **0.8234R**; **615** STOP, **1006** TARGET, **376** SESSION_EXIT. Este desequilibrio de payoff es P0 económico: no implica imponer RR mínimo ciego; comprobar **por qué** los objetivos HTF as-of tienen tan poco recorrido y el SL M15 es relativamente amplio. Segmentar por familia, mercado y sesión antes de hipótesis.
- PF 0.842524 y DD 114.799R son **brutos** y todavía malos; audit15 NO ha producido un Trader certificado ni una política alternativa con edge.

**B último código consultado:** auditor residual `src/qore/infrastructure/trader_lab/capitalizer_scalper_a2_audit15_residual_anatomy_v1.py` (localizar si cambia nombre por GitHub search), workflow `qore-scalper-a2-audit15-residual-anatomy-nine-market.yml` (comprobar filename exacto en HEAD B). Auditar logging, source IDs, hashes y artifact en la Action anterior. No confundir el informe PF source-anchored de B con **PF del verdadero Master Frame cognitivo A1**, que SIGUE SIN EJECUTARSE para nueve mercados históricos.

### ORDEN PRIORITARIO REVISADO PARA EL SUCESOR

**P0-A metodología:** resolver **primera selección CISD online NO prefix-stable**, **1090/2876** diferencias first-discovered en streaming contra V49, sin malinterpretar que 381 eventos estaban ausentes. Confirmar by-event as-of la relación swing/POI HTF TTrades; dejar regla de desempate multi-ruta como `QORE_ENGINEERING_RULE` si TTrades no la prescribe. Consulta DeepSeek para casos concretos de autor ambigüo, **verificar sus citas en TTrades**.

**P0-B densidad y nueva generación:** el replay XIV está *source-anchored*, NO descubre nuevas oportunidades de H1/M15 fuera de 2876; reconstruir H1→M15→M1 **bar-by-bar desde todas las fuentes nativas** con lookback exacto 14 días, C2/C3 originales y POI/HTF verificados. Mantener protocolo de primera confirmación real sin backdate ni conocer next-H1/next-M15.

**P0-C estructura económica:** explicar cuantitativamente los 935 targets <0,5R, payoffs y 32 flips, stop M15 vs target H1 as-of, selección MAX3 y winner-mass. Luego A/B pre-registrado de **una sola** corrección source-fiel cada vez, sin seleccionar por PF de ese mismo período de desarrollo. Asegurar costes reales BID/ASK/comisiones y prueba OOS congelada antes de certificación.

**P0-D C3:** finalizar adjudicación de lecturas de diciembre vs enero, universos e impactos; no trasplantar reglas de un contexto distinto ni inducir gates artificiales. H1 C2 2638 / C3 238 NO indica por sí mismo desviación del autor.

**P0-E A1:** mantener freeze de expansión World Model hasta raíz autor/causal resuelta; entonces conectar las nueve percepciones físicas, presión/portfolio/posiciones SETTLED ONLY, verdadera cognitiva Master Frame y PAPER, medir PF/DD reales del cerebro, no los del motor B.

**DeepSeek para ambigüedades:** el siguiente arquitecto está expresamente autorizado a CONSULTAR a DeepSeek para obtener hipótesis, lecturas alternativas, contraejemplos y sugerencias de tests sobre CISD, POI C2/C3, stops/targets y first-online; registrar pregunta y respuesta en GitHub; verificar citas **primarias** directamente y someter cada respuesta a prueba 9-market. DeepSeek es apoyo externo, NO verdad autoral ni certificador. No compartir secretos.

**Estado al publicar la actualización:** A1 #758 y B #759, así como #623, DRAFT/no merge; la prueba B XV tuvo inicialmente CI rojo y quedó **GREEN #38104619725**, por lo que no reproducir una falla transitoria como defecto pendiente. Auditoría completa de rama B puede tener nuevos runs posteriores; consultar HEAD y su estado actual. Sin VPS/MT5/LIVE. **Scalper sigue NO CERTIFICABLE.**

---

## 0. LECTURA OBLIGATORIA PARA EL SUCESOR

**No empezar desde cero ni ampliar el World Model todavía.** Antes, leer los documentos:

1. **ESTE handoff rector A1**, para la historia, prioridades y áreas de responsabilidad.
2. [Handoff maestro paralelo de B](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_MASTER_HANDOFF_A1_A2_COGNITION_METHOD_2026-10-10.md). Tiene detalle profundo del circuito de B y de los experimentos de la auditoría 13. Comprobar modificaciones posteriores en PR #759.
3. [Auditoría 13 de B: POI C2 / streaming CISD / 151 H1](https://github.com/mezas3238-hue/qore-core/blob/agent/scalper-architect-b-methodology-20261010/docs/research/QORE_SCALPER_A2_THIRTEENTH_C2_POI_AND_FIRST_STREAM_ECONOMIC_2026-10-10.md).
4. [A1 duodécima: pertenencia de evento al prefijo vs selección global](https://github.com/mezas3238-hue/qore-core/actions/runs/38098618743) y sus commits.
5. [Congelamiento METHOD-FIRST décima auditoría](QORE_SCALPER_A1_TENTH_AUDIT_METHOD_FIRST_FREEZE_2026-10-10.md), [cuarentena de outcomes](QORE_SCALPER_A1_TENTH_AUDIT_CISD_NO_HINDSIGHT_BOUNDARY_9MARKET_2026-10-10.md).
6. [Master antiguo histórico](QORE_CAPITALIZER_COGNITIVE_SCALPER_MASTER_HANDOFF_2026-10-10.md). **Histórico, NO asumir que sus tareas antiguas reflejan el estado de octubre final.**
7. [Estándar de certificación V2 congelado](QORE-CAPITALIZER-SCALPER-CERTIFICATION-STANDARD-V2.md). No sustituir estándares Owner con umbrales del autor.

**Cambio decisivo tras la auditoría 12:** hay que distinguir tres preguntas que no son sinónimos:
- ¿Existía la CISD elegida por V49, identificable en su propio detector y en el cierre original con M1 pasado? Evidencia B: **2876/2876 SÍ, como primer evento de su propia ruta QORE**.
- ¿Era esa CISD **el primer evento entre TODAS las rutas** emitidas realmente cada minuto? **NO coincide en 1090/2876** cuando se analiza streaming auténtico; 381/2876 discrepaban ya en FULL-vs-PREFIX estático.
- ¿Es la CISD **fiel al swing, POI, cierre HTF, serie opuesta y orden del autor TTrades**? **NO demostrado**. No convertir disponibilidad QORE en certificación del autor.

---

## 1. MISIÓN, UNIVERSO Y BASELINE FROZEN

**Trader:** QORE Capitalizer Cognitive Scalper V1, derivado de motor de investigación V48/V49. Horizonte operacional **H1 → M15 → M1**. H1 tesis y sesgo reutilizable; M15 confirma setup, protected/invalidation y POI; M1 confirma timing/sweep/FVG/CISD y ejecución. **Nueve activos:** USDJPY, AUDJPY, AUDUSD, GBPJPY, EURUSD, GBPUSD, XAUUSD, USDCAD, NAS100. Sesiones QORE operativas **Asia 20:00–02:00, Londres 02:00–08:30, Nueva York 08:30–16:00, hora America/New_York**, con DST y universos de mercados permitidos. MAX3 ejecuciones por sesión es techo, no cuota. No introducir Daily/H4 como gate universal del modelo genérico. No exigir MSS+FVG+OB como conjunción universal donde son **rutas alternativas**.

**Población original, control científico inmutable:** exactamente **2876 oportunidades fuente V49**, 9 mercados, M1 provider-native, intervalo de desarrollo aprox. septiembre 2025–septiembre 2026. En portafolio MAX3 original **2020 trades**, **1167 operaciones R positivas**, PF bruto **0,66446**, DD observado **236,13R**, P&L bruto aprox. **−233,269327R**. No confundir 2876 oportunidades con 2876 órdenes ejecutadas. Estos resultados NO son un replay físico bid/ask calibrado ni prueba live.

**Fuente física congelada:** [native M1 #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), SHA 18c338aedd5013ce65a6cb6408ffbc2e904a6217. **Fuente V49 y economía:** [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), SHA e356e7a52541e99533b25ecfef0ab9c4e9ce03c0. **Nunca reescribir fuente ni reemplazar un M1 real por OHLC generado, forward-filled o inventado.**

**Integridad ganadora:** un baseline históricamente negativo no autoriza destruir edge, volumen de ganadores o densidad útil. La norma exige informar de winner count preservation (mín. 80%), winner-R preservation (mín. 90%), pérdida evitada, PF/DD, calidad OOS y evolución por 9 activos. El propietario rechazó los 90 trades de V50-G como arquitectura final: PF 1,53459 y DD 9R en una selección escasa NO son un Scalper satisfactorio. El estándar actual prioriza **calidad robusta del edge** por encima de imponer una cuota arbitraria de trades.

---

## 2. MODELO OPERATIVO AUTOR TTRADES Y SUS INCERTIDUMBRES

**Fuente del AUTOR, no resumen de DeepSeek:** TTrades / TTrades Mentorship. Fuentes textuales a consultar en el momento de tomar cada decisión:

- [Understanding the Change in State of Delivery (CISD)](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/): cierre más allá de la **apertura de la primera vela de la secuencia de cierres opuestos**; la mecha aislada no basta.
- [Market Structure Shifts vs CISD](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): no confundir CISD con MSS/rutura de swing.
- [How Change in the State of Delivery Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/): el CISD protege el **swing pertinente**; debe relacionarse con las velas que formaron el extremo, POI y cierre HTF C2/C3.
- [Understanding Candle 2 Closures Within the Fractal Model, 15 nov 2025](https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/): barrido del extremo anterior, cierre dentro del rango anterior y reacción en POI HTF; POI swing, FVG y en ciertos contextos vela opuesta.
- [Candle 3 Closure, 3 dic 2025](https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/): cuando C2 no confirmó, posible C3 que no barre extremo C2 y cierra atravesando cuerpo C2, en el contexto especificado.
- [TTrades Scalping Model, 7 feb 2026](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/): sesgo H1 por Candle 2 **O** Candle 3, seguido de M15/M1, no solo C3.
- [The Only Trading Strategy You Need for 2026](https://ttrades.com/the-only-trading-strategy-you-need-for-2026/): contextualización de POI/estructura/confirmación.

**Ramas del origen:** H1 C2 reversal y C3 confirmation son alternativas/episodios distintos, no interpretar 8,3% C3 como “91,7% sin metodología autor”. La estructura C3 Closure→C4 no está certificada como segunda familia ejecutable universal; comprobar en el ledger del autor qué rutas funcionan y cuáles son observadores parciales. Mantener separados conceptos QORE-engineering y SOURCE_EXPLICIT; no trasplantar killzones ICT a Scalper TTrades.

**CISD V49 implementado:** capitalizer_ttrades_m1_cisd_observer_v48.py y capitalizer_ttrades_m1_fvg_cisd_continuation_v48.py; capitalizer_high_frequency_capacity_census_v49.py::_earliest_m1_trigger. En el nivel básico de cierre/primera vela opuesta existe **MATCH literal preliminar**. La exigencia de **serie que formó el swing/POI y auténtica cierre HTF**, las prioridades entre familias y la validación posterior en PAPER son **PARTIAL/UNRESOLVED**, no SOURCE_FAITHFUL.

**Dirección H1:** el sensor B conserva dirección H1 V49. *No instrumentó una búsqueda de CISD opuestas independiente*. Nunca reportar 0 “dirección contraria real” como hecho.

**Candle3 A/B:** diciembre (no barrido/extremos C2 + ruptura cuerpo) vs enero (formulación de cierre por apertura/rango C2 + LTF CISD, contextualizada). Registrar si son modalidades diferentes, no necesariamente contradicción universal. Prerregistro, causalidad, recuentos por rama, efecto sobre 9 mercados, outcomes +30m y reserva independiente. No elegir “definición correcta” solo por PF retrospectivo.

---

## 3. TRABAJO EFECTIVAMENTE REALIZADO POR A1 — CÓDIGO, RESULTADOS Y PRUEBAS

### A. Contratos y conexión de cognitiva con PAPER

Código A1 principal:
- **capitalizer_a1_master_frame_paper_trader_integration_v1.py:** toma alternativas, contexto cognitivo y fuentes, llama al Master Frame genuino antes de selección PAPER; conserva WHY/identidad de fuentes.
- **capitalizer_a1_multi_hypothesis_research.py:** barreras sincronizadas, hipótesis y alternativas, contratos H1/M15/M1 de cierre; no equivale a generar nueve percepciones reales.
- **capitalizer_a1_sensorized_paper_runtime_v1.py:** enlaza sensor M1 de B con contexto A1, más testigos independiente M15/H1, pivote M1, segundo pivote y reloj; aplica provenance/no-hard-veto; verifica identities, deadlines, monedas, precios, orden de acontecimientos; invoca el Master Frame genuino sobre **3 fixtures** de integración. **ATENCIÓN:** 3 fixtures no son los 2876 históricos ni prueban PF/DD de cerebro integrado.
- **capitalizer_scalper_sensor_master_frame_bridge_v1.py** / **capitalizer_a1_validated_sensor_overlay_v1.py:** contrato de atributos de sensor y estado observado/incompleto; no otorgar autoridad por tokens.

### B. Nueve mercados M1 nativos / prefijos temporales

- **capitalizer_a1_native_nine_market_bar_witness_v1.py:** conserva as-of 9 mercados a 2822 instantes distintos (2876 source IDs, hay timestamps con múltiples fuentes); **2791** instantes tienen M1 exacto cerrado 9/9, **31** no tienen exact 9/9. [Histórico nativo #38080367716](https://github.com/mezas3238-hue/qore-core/actions/runs/38080367716).
- **capitalizer_a1_native_nine_market_epistemic_inputs_v1.py:** transforma OHLC físicos en contratos reales CapitalizerMarketPerceptionSnapshot, CapitalizerRegimeHypothesis, CapitalizerCrossMarketCausalGraph: **25398 percepciones**, **25398 regímenes UNKNOWN/UNRESOLVED**, **101592 edges de pares cross MARKET UNKNOWN**, 2822 barreras. No inventa BID/ASK, sesión de fuente, microestructura ni causalidad dirigida. [#38091052695 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38091052695).
- **capitalizer_a1_native_source_session_clock_attestation_v1.py:** conciliación por 2876 source IDs del calendario QORE, operating-date y DST America/New_York (1913 EDT UTC−4, 963 EST UTC−5), cero contradicciones a bucket original. Ventana metodología ICT NO equivale a bucket QORE, así que NO vetar operaciones fuera de killzones ICT ajenas. [#38091938032 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38091938032).
- **capitalizer_a1_native_clock_bound_perception_v2.py:** join cada fuente y M1 exacto cerrado con su reloj independientemente validado: **2876 percepciones BAD→DEGRADED**, quedan **22522 BAD**, **0 GOOD** por BID/ASK y microestructura no probadas. Nueve mercados sin pérdida, cero vetos. [#38092434895 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434895).
- **Notas de límite:** DEGRADED es integridad incompleta de evidencia, NO mejoría estadística, quote/ejecución ni sesgo rentable.

### C. M1 protected swing, segundo pivote y otros testigos

- **capitalizer_a1_source_sensor_independent_attestation_v1.py:** cotejos fuente M1/M15/H1 sin sustituir sensor “UNKNOWN” por confirmación falsa.
- **capitalizer_a1_m1_protected_route_forensics_v2.py:** 9-M1 independiente por ID, **1885/2876** con pivote protegido/intacto que ese detector logra documentar (1244 primer pivote protegido más 641 previamente confirmado; 991 inicialmente sin esa prueba), bajo ventana as-of, no autor-fidelity. [#38083508578 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38083508578).
- **capitalizer_a1_m1_second_pivot_forensics_v3.py:** revisa pivotes causales POSTERIORES del mismo episodio, no se detiene en primer swing violado, nunca incluye vela futura. Añadió **490** segundos pivotes confirmados/intactos → **2375/2876 = 82,58%** con algún testigo estructural M1; **157** con pivote posterior pero precio vulnerado, **344** sin pivote posterior confirmado (**342 Sweep y 2 FVG**), total **501** sin esta prueba. [#38085489622 GREEN 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38085489622).
- La prueba de protected pivot QORE **NO** significa que los 501 sean entradas inválidas según TTrades; en Sweep, el autor puede exigir otra prueba. **No crear filtro de 501**. A1 conectó estas señales contextuales al runner PAPER de fixtures, sin nuevo veto. 12 M15 y 124 H1 quedaron sin cierto testigo independiente de rondas previas; requiere investigación por fuente, no negar el evento.
- [Handoff M1 V3 y cada mercado](QORE_SCALPER_A1_NATIVE_M1_SECOND_PIVOT_V3_HANDOFF_2026-10-10.md).

### D. Reloj operativo y frontera estricta de outcomes

- **capitalizer_a1_cisd_outcome_blind_method_boundary_v1.py:** 9 libros históricos fuente V49 y 9 libros originales A2 de la novena auditoría; valida **2876/2876** hashes originales, fuente M15/H1 y primer CISD de ambas familias. Emite SOLO A1CISDPredecisionMethodWitness, **nunca original_excur/sensor_excur con MFE/MAE 15/30/60**, ni PF futuro; test de canario futuro y schema más estricto. Consolida **2495 MATCHED /247 sensor anterior /134 misma hora-familia distinta**. Se mantiene cuarentenado y no se conecta al Master antes de adjudicación del autor. [#38094209281 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38094209281); full CI [#38094209262 Ruff / Mypy 1656 / 57 tests GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38094209262).
- **Causalidad A1 audit 12**, nuevo GH Action [#38098618743 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38098618743) y [Quality #38098741578 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38098741578): contrasta pertenencia de evento elegido a prefijo bajo misma ruta, primera selección ONLINE y H1 C2/C3, todo con source ID. Usar esta acción y la B #38096548896 para evitar interpretar que 381 eventos fuente estaban ausentes del prefijo. No confundir “own-route present” con “first global selected” ni con fidelidad POI del autor.
- Referencias A1: [Handoff clock](QORE_SCALPER_A1_NATIVE_SESSION_DST_SOURCE_PROOF_AND_MASTER_PAPER_LINK_2026-10-10.md), [Handoff percepción](QORE_SCALPER_A1_REAL_2876_CLOCK_BOUND_PERCEPTIONS_V2_2026-10-10.md), [A1 quarantine](QORE_SCALPER_A1_TENTH_AUDIT_CISD_NO_HINDSIGHT_BOUNDARY_9MARKET_2026-10-10.md), [Freeze METHOD-FIRST](QORE_SCALPER_A1_TENTH_AUDIT_METHOD_FIRST_FREEZE_2026-10-10.md).

### E. Quality y límites de los ensayos A1

- Se repararon fallos de fixtures/QA en pruebas de V51 preservación de masa ganadora y V54 OHLC synthetic stop/runner sin modificar la economía; ver [handoff de integración inicial](QORE_SCALPER_A1_FULL_FRAME_RESEARCH_BRIDGE_HANDOFF_2026-10-10.md).
- Reiteradas regresiones Ruff/Mypy y Pytest verificadas en GitHub. Los últimos SHA A1 antes de este handoff (89932e...) registran **CI #38098741578 SUCCESS**. Revalidar CI del SHA final del handoff, no citar pruebas antiguas como pruebas del último código B.
- **Prohibido afirmar:** “real nine-market FULL COGNITION reejecutada 2876” o PF/DD mejorado. Los tests end-to-end Master Frame usan **world fixture**, la evidencia de mercado histórica permite construir percepciones parciales, PERO faltan World Model, posiciones y regímenes físicamente verdaderos.

---

## 4. TRABAJO B YA COMPLETADO Y QUÉ DESCUBRIÓ (EXTERNO A A1, VERIFICAR SU BRANCH)

**Auditorías B disponibles en GitHub:**
- [CISD 381 tipología y excursiones #38076268436](https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436): 2495 coinciden; **247 first SENSOR earlier** (171 FVG→Sweep; 76 Sweep→FVG), **134 same-close-different-family** (Sweep→FVG). A +30m en 349 parejas sensor 189 favorable vs V49 176 (3.725 pp); *no* prueba edge o PF; a +15m early empeora y a +60m efecto desaparece, MAE anterior sube. NO seleccionar regla por etiqueta posterior.
- **B first-selection FULL vs M1 PREFIX #38095562104:** reproduce V49 con ventana completa 2876/2876, reproduce observador prefijo 2876/2876, primera global difiere **381**. Esto es un defecto de invariancia temporal en la selección de primera familia, NO prueba que evento original no existía.
- [B same-route prefix membership #38096548896 SUCCESS 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38096548896): 2876 eventos originales presentes como primer CISD de su PROPIA ruta al cierre real; **0** fuente ausentes bajo ese observador. Primera GLOBAL 2495 coincide, 381 cambia. “ALL candidate author-fidelity” NO se ha enumerado; etiqueta “lookahead confirmed EVENT ABSENT” no procede.
- [B H1 C2/C3 #38096345552 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38096345552): **2638 C2** y **238 C3**, no es 8,3% de fidelidad. **1604** H1 contextos heredados y 1272 directos; source label y POI real no son sinónimos.
- [B H1 native POI #38099880288 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38099880288): **2765/2876** eventos C2/C3 reproducidos con geometría+POI **interno QORE** (2538 C2, 227 C3); **111** no reconstruidos (100 C2,11 C3; 57 directos +54 heredados). **2267/2876** con dos H1 relevantes 60/60; **609** sin ese doble 60/60, de los cuales 498 reconstruidos con alguna vela parcial y 111 sin evento. FVG/swing H1 del detector QORE no demuestra POI “higher TF” autor; opción POI vela contraria contextual no implementada.
- [B incremental online #38099916845 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38099916845): **1786/2876** fuente V49 = primer descubrimiento streaming (misma familia/hora), **1090/2876** cambian cuando cada prefijo M1 se evalúa al cierre minuto por minuto. Las 381 estáticas NO agotan el desajuste. El experimento declara 0 discoveries backdated, 2020 original MAX3 y 2020 MAX3 **reordenado source-anchored**, intersección **1989 IDs** y 31 sustituciones. **No es nueva población fuente regenerada**, no valida stop/target/HTF del nuevo instante.
- [B bootstrap día-cluster #38100268079 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38100268079): 1000 resamples de 313 días operativos/9 mercados. Delta favorable CLOSE+30m **1090 diferentes online +9.4756 puntos** (95% CI **+6.8966,+12.1270**); CLOSE+15 +10.3036pp (CI +6.7753,+14.0304); CLOSE+60 +6.5559pp (CI +4.2991,+8.9317). **Son diferencias de cierre direccional posthoc, NO PF/WR de órdenes ejecutables**. En 381 la CI +30m [-1.5666,+8.6294] no confirma equivalencia ±5 pp.
- [B H1 no-horario #38100413220 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38100413220): 151 eventos origen H1 con etiqueta de cierre anterior a HH:00 pero **0/151 M15 y 0/151 M1 ocurrieron antes del verdadero cierre H1**. Hipótesis activación prematura en esas 151 **descartada**; sigue calidad 45/60 vs 60/60 y POI.
- [Veto sobre 381 #38071484777](https://github.com/mezas3238-hue/qore-core/actions/runs/38071484777): PF 0.664→0.621, DD 236.13→252.10R: **abstención ciega rechazada**.
- Otros ensayos previos: random same-H1 a 30m produjo señal V49 ~12.55 pp peor vs reloj aleatorio H1; el stage forensic Sweep→CISD ~−12.56pp favorable +30m en 900 pares; FVG formation→CISD ~−2.83pp en 1023 pares. **Estos son diagnósticos condicionados a un V49 cuyas reglas aún se auditan**, no explican por sí solos un bug TTrades, ni autorizan orden anticipada.
- **B trabajo más reciente en evolución:** capitalizer_scalper_a2_fourteenth_causal_first_economics_v1.py y workflows/commits de auditoría 14. Construye contrafactual económico source-anchored con M15 stop y objetivo observado, MAX3. **AL REDACTAR**, commit B observado 88bf302174adc..., había nuevos checks pending/queued; **NO DECLARAR RESULTADOS PF/DD ni “ejecutado” hasta verificar Action SUCCESS/artefacto agregado y población, fees BID/ASK y límites**. Aun si pasa, estudio source-anchored no es full source streaming independiente, ni broker live, ni Brain económico 9/9.

**Nota de nomenclatura:** B también ha consultado a DeepSeek en informes anteriores de reconstrucción de metodología; sus respuestas se conservan como **inferencia de experto externo**, NO se promueven a regla de TTrades sin referencia primaria.

---

## 5. INVENTARIO PRIORIZADO DE PROBLEMAS Y AMBIGÜEDADES QUE SIGUEN ABIERTOS

### P0-A | EVENTO CISD existente vs primera selección ejecutable: 1090 discrepancias

**Estado probado:** el evento de la MISMA RUTA original QORE es observable al cierre 2876/2876, pero el primer descubrimiento GLOBAL cronológico difiere para 1090 IDs. El constructor V49 de investigación analiza hasta siguiente M15 o final H1 reconstruido ex post; el primer evento de una función puede cambiar con nuevas velas, alterando la selección histórica. Una ruta puede tener evento disponible pero no ser primera. La decisión live causal debe fijar el primer evento cuando se DETECTA, sin volver a elegirlo después ni retrofechar.

**Exigir al sucesor:** traza por **los 2876 IDs y cada cierre M1** con H1/M15 parent ya confirmado, familia Sweep/FVG, timestamp real de detección, serie opuesta, boundary/close, no-repaint por extensión de prefijo, prioridad de familia en empate y estado del siguiente setup M15 conocido *sólo cuando haya cerrado*. Reproducibilidad independiente con shift/timezone y huecos M1. Clasificar 1090 por tipo/delta/mercado, reconciliar exactamente las 381 subset, permitir UNKNOWN si el POI no es demostrable. Distinguir **QORE_ENGINEERING_RULE de desempate** de textos de TTrades. No cambiar fuente baseline. Medir churn/winner mass y PF/DD **solo cuando haya fills físicos y stops recalculados**.

### P0-B | H1 C2/C3 + POI del AUTOR vs auto-coincidencia QORE

**Estado:** 2638 C2 +238 C3; 2765 internamente reproducibles, **111 sin testigo**. **609** sin doble H1 60/60; agregador actual permite **45/60** y fecha de cierre desde último M1 (potencial origen off-clock). **151** offclock no causaron M15/M1 prematuro, PERO el OHLC H1 parcial y el POI todavía pueden diferir. **1604** source rows tienen bias heredado: vigencia real en cada M15/M1 no certificada independientemente.

**Exigir:** para cada uno de 2876 IDs, el evento C2/C3 original y la pareja HTF previa con OHLC exacta, causa de POI (swing/FVG/vela opuesta), timeframe del POI HTF autor, instante en que el POI era conocido, verdadero sweep y cierre dentro del rango, comienzo/fin estado H1, ruta de herencia, consumo por M15/M1, y motivo de los 111 sin match; log separate UNKNOWN/UNAVAILABLE vs CONFLICT confirmado. Si falta 60/60 consultar agregación institucional/broker oficial, jamás rellenar silenciosamente. A/B C3 diciembre/enero en cohorts limpias y población completa por separado, no elegir ganador in-sample.

### P0-C | M15 y M1 protected swing / CISD ligados al verdadero swing

**Estado A1:** 2375 witness M1 protegidos por detector QORE (1885 iniciales+490 later) / 501 sin tal testigo (157 vulnerados +344 sin otro). **12 M15/124 H1** carecían prueba independiente en auditoría antigua, revisar artefactos posteriores B antes de conservar el diagnóstico. TTrades exige que CISD confirme el swing que generó extremo, no cualquier cruce de apertura. No imponer un triple pivot a todas las familias si autor no lo hace.

**Exigir:** reconstrucción POI/swing por cierre M1/M15/H1 y cronología, stop protegido, target HTF verdaderamente untouched, familia original; reconciliación del 157/344, especialmente 342 Sweep sin tripivot, sin mirar resultado futuro; confirmación que ninguna vela ulterior corrige un pivot declarado protegido retrospectivamente. No hard gate en ausencias de documentación.

### P0-D | C3 A/B fuente diciembre vs enero, aún sin economía certificable

Dos ramas PRE-REGISTRADAS, mismas series y estado H1/M15/M1, geometría, sesión y costos, outcomes separados, cohortes intersection/A-only/B-only, no más de un cambio simultáneo. Registrar exact N, favorable +15/30/60, coverage, estratos, CI day-cluster y OOS; luego SOURCE judgement y replay físico de decisión *as of*, sin elegir rama por PF in-sample. Si las descripciones TTrades son contextuales, el resultado adecuado puede ser **ambas válidas por estado, alcance pendiente**, NO establecer una regla universal ficticia.

### P0-E | Economía real de la primera detección vs V49 baseline

Ninguna mejora del 9.4756pp de retorno de cierre implica dinero. Lo pendiente es primer source H1/C2-C3 reproducido causalmente + primer M15 válido + primer CISD M1 a close + stop/target as-of + entrada/fill BID/ASK, comisión, spread, slippage, orden STOP-FIRST, cierre al fin de sesión, prioridad MAX3 **global** por 9 mercados, posiciones abiertas y pérdidas asentadas. Un cambio de hora altera SL/TP y puede invalidar target o geometría de riesgo. **NO reusar realized_R del trade V49** cuando cambia instante de entrada. Solo tras esto medir PF, expectancy, DD, Sharpe/Sortino y masa ganadora antes de valorar nueva cognitiva.

### P0-F | World Model cognitivo FULL nine-market, pausado por secuencia metodológica

Existe un contrato de Master Frame y test end-to-end de fixtures, además de 25398 percepciones reales parciales, pero falta un **CapitalizerGlobalWorldModel as-of** con estado verdadero de los nueve mercados, H1/M15 nativos, régimen causal confirmado, grafo cross-market justificado, contexto Shared si se conoce, cartera/posiciones abiertas, memoria pérdidas liquidadas, competencia MAX3 y pressure. Evidencia BID/ASK/microestructura no recibida no puede promover GOOD. **Congelar su ampliación** hasta corrección metódica P0-A/B/C/D; sólo entonces coordinar B→A1 y probar 2876 sobre 2822 barreras, con causalidad real y pruebas anti-lookahead.

### P1 | Estabilidad y certificación

Desarrollo ~1 año usado intensivamente, **no** nuevo OOS. OOS 2023/2024/2025 que ya influyó tuning está consumido. Reservar fuente prospectiva o independiente congelada ANTES de mirar outcomes, Monte Carlo dependiente, colas de pérdidas, bootstrap por day/market, comisiones reales, ejecución intrabar. No mezclar resultados de V49 desarrollo con reference V2 multi-era de otro segmento del repositorio. No fabricar Sharpe o drawdown porcentual a partir de unidades R ni convertir DD objetivo en hard gate in-sample por conveniencia.

---

## 6. COMPONENTES COGNITIVOS: FUNCIÓN, INPUT, RIESGO Y ESTADO REAL

Contratos en src/qore/infrastructure/trader_lab/; leer CapitalizerMasterCognitiveContract y CapitalizerMasterCognitiveFrame. El nombre de una clase o test de fixture NO significa disponibilidad de hechos históricos reales.

| Módulo | Trabajo / responsabilidad | Entrada indispensable y precaución |
|---|---|---|
| capitalizer_master_brain.py | síntesis global pre-estrategia de estado cognitivo | world completo, market context y hechos as-of |
| capitalizer_global_world_model.py | estado de los nueve mercados y memoria operativa transversal | eventos cronológicos, posiciones/ledger real, sin posiciones inventadas; **EXPANSIÓN PAUSADA** |
| capitalizer_market_brain_registry.py | nueve especialistas por símbolo | 9/9 físicos, no inferir mercado faltante |
| capitalizer_perception_integrity.py | calidad, frescura, sesiones, completitud M1/cotizaciones | BAD/DEGRADED/GOOD; reloj+M1 no equivale BID/ASK |
| capitalizer_regime_intelligence.py | hipótesis de régimen y resolución respaldada por evidencia | 25398 UNRESOLVED hasta pruebas reales; no clasificar solo por label |
| capitalizer_cross_market_causality.py | grafo de relaciones dirigidas entre pares | 101592 edges UNKNOWN históricos; simultaneidad no es causalidad |
| capitalizer_session_journey_intelligence.py | evolución sesión, límites y memoria causal | solo eventos y trades ya liquidados |
| capitalizer_attention.py | BACKGROUND / WATCH / FOCUSED / DECISION / POSITION | no confundir observación con permiso de entrada |
| capitalizer_opportunity_competition.py | ranking causal de oportunidades en misma sesión | MAX3 techo, no cuota; preservación de ganadoras |
| capitalizer_confidence.py | grado de certeza epistémico | UNKNOWN no se convierte en WELL_SUPPORTED por input fixture |
| capitalizer_metacognition_v2.py | incertidumbre y calidad del propio razonamiento | nunca consumir MFE/MAE futuro |
| capitalizer_adversarial_reasoning_v2.py | hipótesis contrarias y falsificación | debe usar evidencias observables en ese instante |
| capitalizer_decision_sovereignty.py | límites de autorización cognitiva/estrategia | Master pre-strategy no otorga capital ni orden |
| capitalizer_cognitive_pressure.py | cautela/selección/paro conforme circunstancias causales | no usar outcome etiquetado futuro; presión no inventada |
| capitalizer_portfolio_position_supervisor.py | posiciones abiertas, riesgo y solapamiento | holdings, fills y cierre temporal real |
| capitalizer_exposure_graph.py | exposición y concentración cross-market | instrumentos y cotizaciones físicas, no asumir correlación |
| capitalizer_memory.py / capitalizer_experience_memory.py | memoria de hechos y outcomes asentados | impedir leakage de trade rechazado o sin liquidación |
| capitalizer_master_cognitive_frame.py | coordina contextos, inteligencia, adversarial, metacognition, gate | construye PRE-STRATEGY frame; strategy_decision_allowed=False, outcome_visibility=False y grants_capital_authority=False |
| capitalizer_a1_multi_hypothesis_research.py | empaqueta hipótesis alternativas por barrier | se necesitan verdaderas 2822 barreras históricas y evidencias H1/M15/POI |
| capitalizer_a1_sensorized_paper_runtime_v1.py | inyecta witness de sensores al Full Frame y PAPER | test REAL DE CÓDIGO con 3 fuentes fixture, no full historical PF/DD |
| capitalizer_a1_cisd_outcome_blind_method_boundary_v1.py | cuarentena de resultados futuros del estudio B | entregas as-of por 2876 IDs; prohibida promoción metodológica |

**Boundaries QORE:** Trader debe poseer metodología y entradas; Shared provee contextos causalmente observables sin alterar tesis, CIBO capital/sizing/economía, QORE Risk es última autoridad financiera. Estos roles NO se simularon como mundo cognitivo full-nine histórico. No atribuir “razonamiento autónomo live” al trader por fixture unitario.

---

## 7. ESTÁNDAR DE CERTIFICACIÓN (NO CONFUNDIR CONTRACTS)

[Certification Standard V2 congelado](QORE-CAPITALIZER-SCALPER-CERTIFICATION-STANDARD-V2.md): **PF OOS >=1,50 en CADA era**, combinado **>=1,70** (deseado >=2); expectancy OOS **>0R/trade** (deseado >=0,15R), Sharpe anualizado OOS **>=1,50**, Sortino anualizado **>=2,00**, drawdown observado **<=10R** en estándar V2 (deseado 6–8R), MC positivo **>=90%**, MC p95 DD **<=15R**, payoff >=1,20 (o excepción estadística aprobada), costes netos PF >1 y expectancy >0. Preservación ganadores mínima 80% y winner-R 90% en estudios de cambios. Períodos de desarrollo pueden diagnosticar pero NO certificar. Finalmente Risk + CIBO + auditor independiente.

**Conflicto de exigencia a resolver, NO ocultar:** el MasterCognitiveContract además codifica objetivo DD 3–5R y absolute_max_drawdown_r=6; Standard V2 acepta <=10R y prefiere 6–8R. Son **contratos/niveles distintos**, no inventar que “6R para todas las operaciones” es idéntico al gate 10R del estándar o viceversa. Verificar gobernanza Owner aplicable al candidato antes de declararlo PASS. No eliminar filtros del sistema global a ciegas ni imponerlos a V49 retroactivamente. `Sharpe/Sortino` requieren definición exacta de frecuencia, coste, anualización, días sin trades y riesgo.

---

## 8. PROTOCOLO DE CONSULTA CON DEEPSEEK — APOYO EXTERNO PRIORITARIO

**INSTRUCCIÓN EXPLÍCITA PARA EL SIGUIENTE ARQUITECTO:** PUEDE Y DEBE CONSIDERAR **CONSULTAR CON DEEPSEEK** como segundo par de ojos cuando detecte una ambigüedad técnica o metodológica relevante. DeepSeek sirve de **apoyo externo de investigación, crítica, generación de hipótesis y búsqueda de contradicciones**, coordinado por GitHub con A1/B. No hay prohibición de usarlo. Este permiso es especialmente útil para las 1090 divergencias M1 online, elección de FIRST candidato, secuencia CISD opuesta/swing, POI H1 vs HTF real, Candle2/3 fuente contradictoria, H1 45/60 y economía con stop/target.

**JERARQUÍA de autoridad obligatoria:**
1. **Fuente primaria fechada del AUTOR TTrades** (texto literal, URL, contexto, captura/cita y fecha verificables).
2. Código fuente real V49/A1/B + dataset provider-native + sello as-of, id original y test determinista.
3. Prerregistro inmutable + GitHub Actions 9/9 mercados, output histórico + independencia/OOS.
4. Dictamen de auditor independiente.
5. **DeepSeek externo = hipótesis y crítica NO normativa**: sin fuente primaria ni pruebas no puede declarar SOURCE_FAITHFUL, ordenar veto ni garantizar PF/DD.

**Cómo pedir ayuda a DeepSeek, de forma operativa:**
- Crear un issue/comentario GitHub con ID de ambigüedad, p. ej. DS-CISD-ONLINE-001, DS-H1-POI-002, DS-C3-003, DS-H1-45of60-004, DS-BROKER-005.
- Entregar a DeepSeek **las dos descripciones exactas que se contradicen**, referencias URL TTrades, el fragmento mínimo del detector V49/B, timestamps H1/M15/M1 y **dos o más casos fuente ID anonimizados con OHLC as-of**, claramente sin resultados futuros.
- Solicitar (a) citas textuales primarias con fecha, (b) alternativas falsables, (c) contraejemplos de OHLC, (d) algoritmo causal bar-by-bar sin hindsight, (e) qué dato falta y (f) un test de rechazo que distinga ambas hipótesis. Preguntar explícitamente: “¿Qué parte es TTrades SOURCE_EXPLICIT y qué parte es QORE_ENGINEERING_RULE?”
- Registrar respuesta completa de DeepSeek en un documento GH como **EXTERNAL_EXPERT_UNVERIFIED**; adjudicar cada proposición como PRIMARY_MATCH / PARTIAL / CONFLICT / NO_SOURCE / TEST_PENDING. Si DeepSeek proporciona URL o cita, verificar directamente con fuente TTrades: los LLM pueden inventar fechas, frases y reglas.
- Nunca revelar secretos de GitHub, tokens, broker, capital, usuarios, credenciales, posiciones privadas o datos sensibles; usar OHLC públicos/de desarrollo anonimizados. La consulta **no** tiene acceso automático a repos privados sin autorización del Owner.
- Conservar desacuerdos y revisiones en el ledger, incluir SHA, acción GH y prueba que resolvió la duda; no borrar hipótesis perdedoras para acomodar el resultado.
- Si DeepSeek y fuente textual discrepan, manda **la fuente y el test causal**, nunca la autoridad del modelo.

**PREGUNTAS MODELO PARA DEEPSEEK (copiables/adaptables):**

**DS-CISD-ONLINE:** “En este escenario H1+M15+M1 con dos observadores Sweep+CISD y FVG_Retrace+CISD, V49 selecciona offline la primera señal mirando hasta el próximo setup M15/fin H1. Un observador streaming ejecutado en cada vela M1 completamente cerrada revela otra primera familia. Reconstruye TODOS los eventos observables a cada close, distingue first-detected vs first-confirmed, cero repaint y detalla si TTrades prescribe la prioridad, con URL exacta y cita; si no, marca QORE_ENGINEERING_RULE. Genera casos que falsan selección retrospectiva.”

**DS-C2-POI:** “El autor TTrades exige Candle2 sweep+cierre dentro de rango+POI superior y acepta swing/FVG/posible vela contraria. QORE usa FVG/swing H1, a veces 45/60 M1 en H1. Determina condiciones causales exactas para confirmar POI y swing sin usar velas futuras; distingue timeframe superior al H1 frente al mismo H1; no presupongas que 111 no reconstruidos son inválidos.”

**DS-C3-AB:** “Compara los artículos TTrades diciembre 2025 y enero 2026 sobre Candle3; identifica cuáles describen circunstancias diferentes y plantea A/B prereg causal, qué vela debe cerrar y qué observador protected swing sigue, con ejemplos LONG/SHORT de ruptura de body vs apertura de C2 y ausencia/presencia de sweep.”

**DS-BROKER-REPLAY:** “Revisa un replay con trade histórico source-anchored, entrada cambiada a primer evento detectado, stop M15 original y target H1 recalculado. Señala los casos en que el stop/objetivo dejan de ser as-of válidos, reglas STOP-FIRST en vela ambigua y qué BID/ASK/comisión son imprescindibles para calcular PF/DD reproducibles. Evita simular fills no observables.”

---

## 9. ORDEN EXACTO DE REANUDACIÓN PARA EL PRÓXIMO ARQUITECTO

**PRIMERO (P0 sin nuevas capas):**
1. Verificar HEAD de PR #758/#759/#623, leer docs A1/B y consultar runs pendientes B (incluida auditoría 14). Marcar qué está SUCCESS y qué no. Crear issue/checklist de P0 actual sin duplicar sensores.
2. Ejecutar/resumir por **2876 IDs** las pruebas ya existentes de source C2/C3, 111 sin origen, 609 sin 60/60, 1604 inherited y 151 offclock 0 prematuro. Para cada desviación, ¿es bug, fuente incompleta o regla QORE? Comparar TTrades literal.
3. Resolver el problema **1090 streaming** por ID, con verificador de primera detección real cada M1, membership de evento vs global-first y primer-CISD sin conocer siguiente M15 futuro. Comparar contra 381 estáticas sin tratarlas como población total.
4. Resolver POI/swing/HTF y la diferencia entre dos familias como SOURCE_RULE vs QORE_ENGINEERING_RULE; registrar casos TTrades explícitos/implícitos/desconocidos, consultar DeepSeek donde haya dudas y verificar después texto del autor.
5. Ejecutar Candle3 diciembre/enero A/B pre-registrado, con denoms, outcomes diagnósticos y OOS, sin retunear; adjudicar source o conservar ambas contextualmente.
6. Solo cuando el detector M1 y H1 sean causalmente firmes: construir **primer evento source FULL streaming** y ensayar economía PAPER de 9 mercados, idéntico modelo de costes, SL/TP as-of, MAX3 y sin outcome leakage. Estratificar 1090/1786 y 381/2495, por mercados/sesiones, medir win mass y comparar 2020 baseline.
7. Cuando (2–6) estén resueltos y documentados: habilitar expansión World Model y conectar todos los hechos físicamente verificables a Master Cognitive Frame y verdadero Trader PAPER histórico. Medir PF/DD cognitivo **nuevo** y todos gates; no declarar “mejora” antes de ello.
8. Finalmente multi-era, stress, OOS prospectivo/independiente congelado, Risk/CIBO/auditor y aprobación explícita Owner. Sin merge/VPS/LIVE automático.

**Pruebas adversariales obligatorias por cambio:** sin vela futura, sin H1.partial→close ficticio, mismo source hash, sin retrofechar primer descubrimiento, dos señales en misma vela, ruta SWEEP/FVG empatadas, M15 setup llega tarde, DST NY, 31 barreras incomplete 9/9, stops/targets invalidados por hora de entrada nueva, hueco de mercado M1, colisiones MAX3 entre mercados, pérdida asentada solo tras exit.

---

## 10. CHECKLIST DE ENTREGA, DOCUMENTOS Y CONTACTOS ENTRE ARQUITECTOS

**A1 sucesor** mantiene o corrige cognitiva sobre PR #758; **B** continúa o coordina metodología sobre PR #759; usar comentarios vinculados y no merges cruzados sin revisión. El siguiente arquitecto deberá:
- Publicar hoja de ruta y lista de fallos con estado, source-ID, impacto y autoridad de cada regla.
- Adjuntar workflow reproducible con artifacts JSONL por ID y resumen aggregate, pin a source run+SHA, pruebas falsas/sintéticas separadas de históricas.
- Adjuntar auditoría de fuente TTrades y responder dudas consultando DeepSeek cuando contribuya, sin transferirle autoridad de certificación.
- Reportar cambios de densidad 2876/2020, ganadoras y winner-R, PF/DD con costos reales, sin ocultar los fallos.
- Mantener V49 baseline intacto, World Model congelado hasta condición go, todos los PR en DRAFT y hardware/prod fuera del alcance.

**No hay trabajo asincrónico iniciado por este handoff.** Toda actividad futura requiere ejecución explícita del sucesor y pruebas nuevas GitHub. El documento sirve para continuidad operativa, **no** constituye certificación ni rendimiento nuevo.

**Veredicto final al corte: Trader Scalper NO CERTIFICABLE.** A1 consiguió integridad física, percepción parcial, pivot causal y aislamiento de datos futuros; B localizó el problema real de elección CISD primera ONLINE y la ambigüedad H1 POI/timeframe; el núcleo económico y full brain siguen pendientes. **Prioridad absoluta: resolver autor-fidelidad + política de primera detección causal, no construir más capas para esconder ese defecto.**

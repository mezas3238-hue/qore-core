# QORE / Scalper — PRERREGISTRO P0 de auditoría causal de dirección H1→M15→M1
**Fecha:** 2026-10-11 · **Estado:** PROTOCOLO CONGELADO PREVIO A EJECUCIÓN · **Tipo:** diagnóstico metodológico, no prueba de rentabilidad.
**Rama independiente:** `research/scalper-p0-h1-m15-m1-causal-direction-audit-20261011`. Nace del SHA A2 `bf8ce75faa6a94fbbc4c33ca74b9a15a2aa53c82`, **no** de un nuevo selector DCVC ni una estrategia contraria.
**Fuentes selladas:** V49 baseline [run 38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`; M1 native [run 35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`; test 1:1 [run 38109948508](https://github.com/mezas3238-hue/qore-core/actions/runs/38109948508) y posthoc [run 38110441161](https://github.com/mezas3238-hue/qore-core/actions/runs/38110441161), informe y código en [PR #771](https://github.com/mezas3238-hue/qore-core/pull/771). Datos septiembre 2025–septiembre 2026 **consumidos**, no OOS.
**Riesgo:** CERO cambios a producción/VPS/MT5, a V49 y a DCVC; sin merge/live/certificación ni señales inversas.

## 0. Qué está observado, sin exageración

- Universo fuente 2.876 oportunidades en 9 mercados; selección cronológica MAX3 A: 2.020 operaciones; V49 original PF bruto 0,664463; esperanza −0,11548R; 1.167 wins / 852 losses / 1 flat.
- Test 1:1 PURE: 1.735 resueltas (768 target, 967 stop), **285 right-censored** por gaps; 8 dual touch bajo STOP_FIRST; acierto **44,265% SOLO resueltas**; PF con coste supuesto 0,025R = 0,75547, esperanza −0,13970R/resuelta. SESSION_CAPPED: 2.010 resueltas + 10 censuradas; PF con coste supuesto 0,025R = 0,71580.
- Para espejo con mismas dos barreras ±1R: en 8 dual-touch ambas direcciones pierden con STOP_FIRST; por eso espejo PURE tiene 959 targets, **55,274%** entre 1.735 resueltas, no 55,73%. La aparente ventaja del espejo es principalmente algebraica de `opposite_R ≈ -original_R`, no segundo edge independiente. Random-sign control mantiene **instantes seleccionados por Scalper**, no tiempos aleatorios.
- 50% primer contacto es benchmark teórico solo bajo proceso martingala apropiado, barreras simétricas, sin censura/horarios, sin fricción ni sesgos de observación. **No** inferir literalmente que toda la muestra A sea “6 puntos peor que el azar” a partir de 44,27% de resueltas.
- No inferir ahora ventaja de reversión; la auditoría determina si existe **defecto causal, de signo, de temporalización, o discrepancia autoral**. La hipótesis de agotamiento del impulso es **hipótesis**, no hecho.

## 1. Hipótesis preregistradas

**H1a (timing/causalidad):** al menos parte de las señales usa H1/M15/M1 sin esperar confirmación disponible, hereda sesgo H1 obsoleto, o entra con demora causalmente cuantificable después de la confirmación pertinente. Una demora legítima no es por sí sola un *bug*; separar `LOOKAHEAD_VIOLATION`, `VALID_BUT_DELAYED`, `AUTHOR_TIMING_DIVERGENCE`, `UNRESOLVED`.

**H1b (semántica direccional):** la dirección V49 derivada de H1+M15+M1 no coincide con una regla de fuente TTrades explícita, o el code path que asigna sesgo invierte/omite requisitos causales; distinguir `AUTHOR_EXPLICIT`, `QORE_INTERPRETATION`, `SOURCE_AMBIGUOUS`. `h1_state_direction=BULLISH→LONG` por sí solo es consistente mecánicamente y no prueba error; validar la **semántica upstream**.

**H1c (first-online):** la secuencia histórica V49 difiere de un detector independiente procesando solo prefijos cronológicos de datos brutos. Distinguir discrepancia de identidad, timestamp, familia de trigger, swing, precio/SL y sesión; explicar cada divergencia antes de atribuir rentabilidad.

**H2 (alternativa estructural distinta):** aun sin problemas relevantes de H1a/b/c, las entradas pueden ubicarse al final de un impulso o en zonas de absorción/reversión. Esta hipótesis requiere **nuevo contrato** con definiciones causalmente medibles y no se eleva por el mero éxito algebraico del espejo.

No establecer a priori que H1 es “más probable” cuantitativamente sin evidencia de prevalencia; prioridad de **diagnóstico de implementación** por ser condición de validez.

## 2. Gate A — 20 trazas públicas replicables + censo automatizado

**Muestra de explicación**: exactamente **20 source-ID A** elegidos sin consultar resultados futuros; seed y regla SHA256 determinística sobre `source_opportunity_id` congelada en este contrato (usar orden ascendente del hash SHA256 de cadena `QORE_SCALPER_H1_M15_M1_AUDIT_20261011|` concatenada con source ID; elegir dentro de estratos no vacíos según **familia de trigger** `LIQUIDITY_SWEEP_CISD` vs `FVG_RETRACE_CISD`, **estado H1 fresh/inherited**, y balance aproximado de sesiones/mercados cuando sea factible). Si quedan cupos, completarlos por hash global. Publicar manifest con estrategia concreta de estratificación determinística **antes** de extraer payoffs para los 20; si estratos muy escasos, publicar motivo y no inventar balance.

**Trazas para cada source-ID**: fichero Markdown/JSON individual con: mercado/sesión/fecha, hashes de feed, origen H1 Candle2/Candle3 y POI, últimas H1 cerradas disponibles y timestamp, dirección H1 del evento original, frescura/edad real, posibles H1 opuestos; swing M15 (velas izquierda, pivote, derecha, timestamps de **disponibilidad**, serie contraria y cruce CISD); todas las M1 necesarias (sweep confirmado, serie, vela CISD/FVG, entrada), dirección V49, stops/targets antes de decisión, precio de entrada vs swing y distancia recorrida antes de entrada; opinión metodológica reconstruida con cita primaria TTrades, diferencias y etiqueta. Una segunda muestra **forense específica** de casos con anomalías puede añadirse, pero nunca usarse para inferir prevalencia.

**Censo completo**: sobre **2.020 A** y de forma separada **2.876 fuentes**, producir tabla automática de todas las invariantes causales, fuente→confirmación→entrada, tasa de evidencia ausente, fechas de origen de H1, casos heredados y edad, desviación M15→M1, símbolos/sesiones, y causas de discrepancia. Los **20 ejemplos no sustituyen la prevalencia**. Los hashes no deben incorporar realized_R ni future features para muestreo.

## 3. Gate B — prueba direccional H1 independente

- Reconstruir desde M1 bruto solo **barras H1 completamente cerradas antes del instante de decisión**. Definir **antes de examinar resultados** dos benchmarks descriptivos y no autorales: (i) señal neta de precio entre los últimos cinco cierres H1 completos (4 retornos), (ii) dirección del último evento H1 Candle2/Candle3 independientemente reconstruido y verdaderamente confirmado. Sin barrido retrospectivo de ventanas ni optimización.
- Comparar dirección LONG/SHORT V49 vs ambos baselines, `fresh` vs `session inherited`, familia M1, edad desde evento original, hora/sesión y cobertura. Reportar `MATCH`, `OPPOSE`, `FLAT`, `UNKNOWN`, todos con conteos denominador y posibles confusores. **Operar contra un trend de 4 barras no prueba bug**, porque la tesis puede ser reversión.
- Verificar `build_h1_context_states`: al heredar usa `prior[-1]` sin TTL máximo explícito y crea estado `confirmed_at=session_start`. Por ello `h1_state_from` heredado **NO** es edad real del evento. Resolver el último `prior` hacia atrás desde los eventos H1 originales, registrar `origin_h1_confirmed_at`, `real_h1_age_at_entry` y cobertura de lookback. Ninguna regla nueva de vencimiento puede derivarse de rentabilidad ex post.
- Añadir diagnóstico preregistrado de **late-entry**: `delta_m15_confirmed_to_m1_entry` en minutos/velas; `delta_origin_h1_to_entry`; desplazamiento *pre-entry* del precio desde el swing y desde inicio/fin de secuencia de impulso, normalizado por riesgo; orden exacto de pivot-right confirmation, CISD, primera vela susceptible de entrada y orden de ejecución. Atribuir timing tardío por reglas autorales, no porque el trade posteriormente pierda.

## 4. Gate C — motor first-online construido de forma independiente

- Procesar provider M1 en orden creciente, construir H1/M15 desde barras cerradas sin usar `V49Opportunity`, `_build_h1_bias_events`, `build_h1_context_states`, `observe_first_structural_cisd` ni `observe_first_m1_cisd` como **oráculo** para tomar decisiones del nuevo motor. Pueden usarse *solo como lado comparado*, nunca fuente de verdad de la reconstrucción. Definir en el nuevo motor especificación autoral/interpretativa congelada antes del replay; no reinterpretar por resultados económicos.
- En cada nuevo cierre registrar `available_at`, fuente de cada nivel, candle-right swing confirmation, persistencia/expiración H1, POI, trigger M1, entry, target/stop y motivo de rechazo. Pruebas `prefix invariance`: agregar velas futuras no cambia ninguna decisión pasada; no leer H1 abierto ni M15 que todavía no cerró.
- Alinear fuente y first-online con claves canónicas `symbol/session/operating_date/decision_at/trigger_family/direction/swing_price`. Producir `EXACT_MATCH`, `TIME_DRIFT`, `SIGN_MISMATCH`, `TRIGGER_FAMILY_DRIFT`, `SWING_MISMATCH`, `MISSING_IN_FIRST_ONLINE`, `NEW_IN_FIRST_ONLINE`, `UNRESOLVED`; si difiere una clave, mantener ambos IDs y trazas en lugar de reconciliar silenciosamente.
- No comenzar con PAYOFF 1:1 del motor nuevo; primero completar conciliación de **eventos** y conformidad autoral. Una reconstrucción independiente que difiere **no prueba automáticamente** bug de V49: adjudicar la diferencia contra regla fuente/timestamp y testigos.

## 5. Pruebas y decisión preregistrada

**Métrica primaria**: tasa de discrepancias **causales o semánticas adjudicadas**, separando defectos innegables de variantes metodológicas ambiguas, sobre el total evaluable A con denominadores y razón de no evaluabilidad. Secundarias: antigüedad de H1 heredado; delay M15→M1; concordancia de dirección con benchmarks; censo de divergencias first-online; cobertura por mercado/hora y consistencia entre periodos.

**STOP técnico inmediato** ante cualquier uso probado de información que aún no existía en `decision_at`, identidad no reconciliable o lectura futura de swing/vela. Congelar artefactos, registrar bug y caso mínimo; no ejecutar ensayo económico con señal causalmente rota.

**H1a/H1b apoyada** si las reglas/fuentes y timestamps prueban inequívocamente defectos de causalidad/dirección; cuantificar frecuencia sobre censo completo. **Sin bugs inequívocos** y con cobertura suficiente, etiquetar `NOT_SUPPORTED_UNDER_TESTED_CONTRACT` para mecanismos específicos, NO `UNIVERSALLY_REFUTED`. La demora sin violar reglas es propiedad temporal, no necesariamente implementación incorrecta. **H2 solo se abre** tras auditar H1 y con nueva hipótesis preregistrada.

**Corrección explícita al umbral propuesto:** que `>=14/20` trazas **no** exhiban timing/dirección incorrectos **NO refuta H1** (selección estratificada, muestra pequeña, posibles defectos parciales). Usar 20 para ejemplos y como gate de inspección, y el **censo 2.020** + evidencia autoral para adjudicación; publicar tasas/IC por día o mercado y sensibilidad a no-evaluables. No optimizar un umbral 70% según outcomes; si se mantiene como umbral de triage, nunca como prueba estadística de ausencia.

**Economía**: este gate **NO** busca mejorar PF ni propone invertir LONG/SHORT. Sin BID/ASK no hay neto físico y 1:1 no certifica entrada; sin OOS nuevo, hallazgos siguen diagnósticos. Concluir `CAUSAL_BUG_FOUND`, `METHOD_AMBIGUITY`, `NO_BUG_DETECTED_WITH_COVERAGE` o `INCONCLUSIVE` por mecanismo, sin fabricar ventaja económica.

## 6. Pruebas automatizadas mínimas

1. Agregar vela futura H1/M15/M1 no cambia evento anterior (prefix-invariance).
2. Pivot M15 no válido antes del cierre de su vela derecha; CISD no confirmado antes del cruce.
3. Contexto H1 heredado recupera `origin_h1_confirmed_at`, no lo confunde con `session_start`; probar evento muy antiguo y cambio opuesto.
4. En mercados/timestamps simultáneos, validar orden de cierres y empate; no usar interpolación sobre gaps.
5. Al alterar realized_R/históricos posteriores, IDs, muestras de 20 y pruebas causales no cambian.
6. Señal LONG de V49 no se invierte sin adjudicación semántica/fuente.
7. Todas las 2.876 fuentes y 2.020 A conservan identidad, y cada discrepancia entre motores es trazable.

## 7. Entregables y frontera de promoción

- Manifest JSONL de todos los casos (sin future outcome), 20 trazas individuales públicas, censo de 2.020/2.876, matriz **autor/regla/as-of**, comparaciones H1, diagnóstico de delay, resultado first-online independiente y diff por ID.
- Pruebas unitarias y CI reproducible 9 mercados + consolidación, copias/identificadores del feed, informes de cobertura y SHA, tabla de casos irresueltos y dictamen honesto.
- Solicitar revisión externa DeepSeek **solo para ambigüedades con evidencia primaria adjunta**, nunca como prueba ni reemplazo del autor.
- **NO LIVE / NO VPS / NO MT5 / NO PROD / NO MERGE / NO CERTIFICATION**. Mantener DCVC v0.1 STOP, y TTrades M30→M3 como investigación aparte [#768](https://github.com/mezas3238-hue/qore-core/issues/768); esta rama es solo auditoría de la implementación V49 H1/M15/M1.

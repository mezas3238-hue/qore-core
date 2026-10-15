# QORE CORE — VT31: mandato corregido de CERTIFICACIÓN METODOLÓGICA Y COGNITIVA

Fecha: 14 de octubre de 2026. **Directiva expresa del Owner:** «El problema es que tú estás tratando de certificar a VT31 de forma cuantitativa, pero VT31 será certificado por su metodología y su cognitiva». ESTE DOCUMENTO PREVALECE como prioridad de investigación de esta rama sobre tareas exploratorias adicionales de PnL, conteos de FVG, screening de retornos o optimización estadística. No reescribe contratos globales ni equivale a aprobación operativa.

## 1. Dos certificaciones DIFERENTES; no mezclar con Trader Lab económico

**Certificación de METODOLOGÍA de VT31:** demostrar que existe un método completo y no contradictorio, con identidad explícita por perfil, fuente autoral cuando se invoca ICT/TTrades, diferencias QORE transparentes, reglas de contexto, liquidez, giro de estructura, setup, invalidación, SL conceptual, DOL, salida, abstención y secuencia de reglas. Auditor COG distinto del autor de implementación revisa casos ejemplares positivos y negativos, y determina fidelidad o versión QORE original. No exigir PF, Sharpe, Sortino, DD, WR, rentabilidad ni masa mínima de trades para aprobar SOLO fidelidad/coherencia metodológica.

**Certificación de COGNITIVA de VT31:** demostrar que su MOTOR cognitivo real entiende la fuente disponible hasta cada instante, recuerda primeras condiciones, separa dos perfiles incompatibles, decide LONG/SHORT/WAIT/UNKNOWN/REJECT y justifica las decisiones con hechos contemporáneos y referencias exactas; no reescribe la historia cuando aparece el futuro, reconoce incertidumbre M1/quotes, evita sesgo retrospectivo y no inventa señal. Se observa el proceso del COG real **sin reemplazarlo por un testigo que ya sabe la respuesta**. Evaluación con escenarios semánticos y contrafactuales emparejados, y revisión independiente de trazas; sin cuantificar ganancias.

**Trader Lab L1–L10:** son Gates OFICIALES para eventual validación integral/DEMO del trader. Se mantienen vinculantes para `DEMO_ELIGIBLE` y operación económica, pero su L4 OOS, L6 MC, L7 metrics y L8/L9/L10 no deben confundirse con la pregunta delimitada **«¿metodología y cognitiva están certificadas?»**. Certificar una no autoriza DEMO/LIVE. A la inversa, no poder calcular PF todavía NO invalida un comportamiento cognitivo correctamente demostrado.

## 2. Identidad: nunca mezclar tres métodos

| Perfil | Regla de contexto | Enlace fuente y diferencia |
|---|---|---|
| ICT_GENERAL_2023 | Londres 03–04 NY, NY AM 10–11 y NY PM 14–15 con DOL contextual y M1 | https://www.youtube.com/watch?v=tRq1hyGGtl4 ; no imponer barrido H1 09h en Londres/PM |
| TTRADES_NY_AM_2025 | NY 10–11, H1 09–10 completo, sweep extremo alto/bajo, desplazamiento regreso al H1, destino extremo opuesto, familia displacement/FVG/OB/Breaker | https://ttrades.com/the-am-silver-bullet-strategy-on-nq/ ; diferencia con ICT general |
| QORE_G3_NYAM_RESEARCH_PROXY | pivote de 3 M1, cuerpo 1,25× mediana 5, primer FVG, 10 puntos desde MSS y stop C2 FULL WICK | Formalización QORE, **NO** coincidencia autoral acreditada (ver auditorías PR #943/#945) |

## 3. Gates cualitativos de aceptación (sin objetivos de trades ni rentabilidad)

| Subgate | Pregunta que debe responder un revisor independiente | Evidencia obligatoria | Resultado preliminar |
|---|---|---|---|
| M0 Identidad | ¿Qué metodología y qué sesión gobiernan ESTA decisión, sin préstamos encubiertos? | ID/version fuente, regla causal y diferencias QORE por cada decisión | PARCIAL |
| M1 Tiempo y memoria | ¿Se basa exclusivamente en hechos disponibles al cierre M1, UTC/NY y DST, sin usar el futuro? | Traza evento a evento, registros `available_at`, reinicio jornada y datos ausentes | PARCIAL |
| M2 Lectura de mercado | ¿Detecta H1 relevante, primer barrido, liquidez y DOL correcto; sabe abstenerse sin datos? | Escenarios espejo LONG/SHORT/WAIT, doble barrido, DOL incorrecto | PARCIAL |
| M3 Confirmación cognitiva | ¿Reconoce regreso, MSS, displacement y si la estructura es confirmada o indeterminada? | Niveles, pivote y `structure_break_confirmed_at` con causalidad, counterfactual solo cambia una vela | PARCIAL; proxy QORE no autor verificado |
| M4 Elección del setup | ¿Distingue FVG, OB, Breaker y displacement, sus zonas y prioridades, SIN confundir un pivote con breaker? | Casos fuente positivos/negativos; invalidación de zona; no duplicar 4 decisiones como 4 órdenes | PARCIAL; #906/#945 siguen proxies |
| M5 Plan conceptual | ¿Define SL conceptual, destino e invalidación consistente con el perfil, sin inventar swing o confundir C2? | Origen causal de stop, diferencia TTrades swing vs G3 C2, expiración/WAIT | PARCIAL; #943 conflicto sin resolver |
| M6 Autonomía y gobernanza | ¿COG genera su decisión autónoma y OPS comprueba sin redecidir, con auditores humanos independientes? | Traza del COG auténtico, falsaciones por tercero, firmas COG/OPS explícitas SHA | PENDIENTE; #897 |

**Dictamen exigido:** cada subgate informa `METODO_CONFORME`, `COG_CONFORME`, `NECESITA_CORRECCION`, `INDETERMINADO_POR_FUENTE` o `RECHAZADO` para cada caso. Una decisión `WAIT/UNKNOWN` puede ser CORRECTA y debe considerarse prueba de buen juicio cuando faltan datos, no falla por reducir frecuencia. `pass pytest` o total de casos examinado sólo respalda integridad de pruebas, **no certifica el método ni el juicio**.

## 4. Escenarios obligatorios e interrogatorio cognitivo (no backtest económico)

Para cada escenario guardar: perfil/version + SHA fuente, hora NY y UTC, hechos M1 visibles, qué hizo COG, qué habría hecho de cambiar UN solo hecho, explicación causal, qué sigue desconocido, juicio independiente y eventual conflicto con autor. Ningún caso puede tener una respuesta de oportunidad basada en ganancia posterior.

- Caso A: H1 09h completo; low sweep primero → retorno y MSS LONG verdadero; DOL HIGH 09; COG explica temporalidad.
- Caso B: espejo HIGH sweep → SHORT; mismo estándar de fuente y decisión.
- Caso C: no sweep H1 → WAIT, incluso si luego sube; abstención correcta.
- Caso D: dos extremos barridos en la MISMA M1 → UNKNOWN por orden intrabar; no elegir dirección.
- Caso E: 59/60 M1 de H1 09h o vela duplicada/stale → WAIT/UNKNOWN sin reconstrucción inventada.
- Caso F: MSS débil o pivote sin confirmación → WAIT, no invención; informe distingue proxy QORE versus autor.
- Caso G: DOL distinto del extremo opuesto → rechazar tesis TTrades NY AM, no invalida ICT_GENERAL por ello.
- Caso H: sesión Londres o NY PM → no aplicar requisito H1 09h de TTrades por traslado inapropiado.
- Caso I: primer retorno sin MSS y MSS sólo aparece DESPUÉS → no retrovalidar primera señal.
- Caso J: FVG con M1 C2 wick y stop proxy distinto de swing, o breaker con solo 1 pivote → `INDETERMINADO_POR_FUENTE`/no método autoral certificado.
- Caso K: CE tocada dentro de M1 sin orden/ACK → no crear conocimiento ficticio de fill. Esto es cognitiva sobre incertidumbre, **no prueba de PnL**.
- Caso L: observación futura cambia el desenlace del día → la decisión ya registrada NO cambia ni su explicación original.

## 5. Procedimiento de certificación real, no más selección por rendimiento

1. Congelar candidatos metodológicos separados y sus fuentes. Para perfil TTrades, resolver si el objetivo es reproducir autor exactamente o certificar una FORMALIZACIÓN ORIGINAL QORE (sin mentir). Definir qué incógnitas impiden tal decisión.
2. Entregar al COG auténtico escenarios **sin etiqueta de respuesta** y retener trazas inmutables. Después un revisor distinto compara con respuesta fuente; casos adversariales espejo y contrafactuales. El script testigo no es el COG.
3. Auditor independiente clasifica conducta e identifica causas raíz de cada divergencia; cambios de reglas generan versión nueva y misma suite más casos nuevos, sin optimizar por beneficio histórico.
4. Exigir documentos separados `CERTIFICADO_METODOLOGIA` y `CERTIFICADO_COGNITIVA` solo con todos los M0–M6 indispensables resueltos y aprobación humana auténtica del artefacto SHA. Si falta algo, emitir `PENDIENTE` claramente por dimensión, incluso con suite funcional verde.
5. **Después**, y solo como otro expediente para entrar en DEMO o LIVE (prohibido por Owner hoy), evaluar Trader Lab económico L1–L10, datos BID/ASK y riesgo CIBO. No bloquear auditoría doctrinal/cognitiva por falta de capital de mercado ni prometer rentabilidad.

## 6. Trabajos previos conservados, relegados a diagnóstico, NO certificación

- PR #937: paridad causal 1×/32×, soporte M1, no cognitiva aprobada.
- PR #939: identidad exacta y `TraderLabLifecycle.state=DRAFT`, no aprobación de L1.
- PR #943: 119 FVG, referencia C2 interior respecto extremo previo en 116, sin atribuir stops autorales.
- PR #945: 149 secuencias de cuatro piernas en proxy QORE, no equivalen a 149 breakers autorales ni acreditan cognitiva del productor.
- PR #906: cuatro detectores proxys, resultados históricos DESCRIPTIVOS no se usan para escoger qué metodología certificar.

## 7. Límites de autoridad

`CERTIFICADO_METODOLOGIA = PENDIENTE`, `CERTIFICADO_COGNITIVA = PENDIENTE`, `VT31_TRADER = NO_CERTIFICADO`, `DEMO_ELIGIBLE = NO`. Esta carta no inventa firmantes ni aprobación, no modifica COG/OPS originales, no hace merge ni operar, no da lotaje al trader (CIBO/CMA controla volumen), no FundedNext LIVE, VPS ni producción. Se coordina en Issue #727 y G3 #897.
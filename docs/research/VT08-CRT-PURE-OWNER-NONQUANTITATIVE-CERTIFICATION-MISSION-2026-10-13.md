# VT08 CRT PURE — MISIÓN DE CERTIFICACIÓN METODOLÓGICA Y COGNITIVA, SIN INVESTIGACIÓN CUANTITATIVA

**Fecha de orden:** 13-OCT-2026  
**PR:** #626 DRAFT · rama `agent/vt08-crt-pure-source-identity-001`  
**Prioridad:** OWNER DIRECTIVE — prevalece sobre los pendientes de testigos y optimizaciones de QC-002 / QC-003.

## 0. Qué pidió el Owner y qué debemos dejar de hacer

El Owner aclara que **no pide desarrollar más testigos ni otro laboratorio estadístico**: quiere **certificar al trader VT08 con investigación no cuantitativa**, regresando a la metodología original y a la cognición.

**Decisión efectiva:**

1. **MISIÓN PRINCIPAL = CERTIFICAR FIDELIDAD DE CRT + COGNICIÓN + DISCIPLINA OPERATIVA NO CAPITAL**, mediante evidencia de fuentes originales y lectura causal de situaciones del mercado, sin optimización estadística.
2. El testigo causal QC-003 queda **ARCHIVADO COMO INSTRUMENTO AUXILIAR**, no es gate, no se necesita ampliar para obtener esta certificación. No ejecutar más feature engineering de testigos por inercia.
3. **NO** hacer nuevas investigaciones de PF, Sharpe, DD, WFO, Monte Carlo, regresiones, filtros paramétricos, barridos de indicadores, modelos cuantitativos ni selección por el PnL.
4. **NO** convertir certificación metodológica en afirmación de rentabilidad ni confundirla con el estado global `CrtPureCertificationStage.CERTIFIED` que el código QORE reserva para TODOS los gates económicos/integración. Ese estado **no se falsifica ni se rebaja**.
5. Sin merge, DEMO/LIVE, VPS, producción ni capital. VT08 jamás asigna sizing, lote, volumen, apalancamiento o presupuesto de riesgo. CIBO/QORE Risk conserva soberanía.

## 1. Dos certificados diferentes, dos afirmaciones diferentes

| Reconocimiento | Evidencia admisible | Puede emitirse sin investigación cuantitativa nueva |
|---|---|---|
| **CERTIFICACIÓN METODOLÓGICA Y COGNITIVA CRT PURE** | Fuentes originales, coherencia vela a vela, razonamiento causal/adversarial verificable, respeto de invalidaciones y límites, criterios cualitativos aprobados | **SÍ, solo al demostrar todos los gates metodológicos aquí definidos** |
| **CERTIFICACIÓN GLOBAL DEL TRADER PARA OPERAR** (estado de código `CERTIFIED`) | Además de los anteriores, evidencia económica y gates de validación independientes del contrato QORE existente | **NO**, mientras esos gates estén pendientes y la investigación cuantitativa permanezca suspendida |

Esta separación preserva lo que el Owner pide ahora sin llamar rentable a una estrategia no demostrada ni activar trading. El certificado metodológico no es licencia operativa.

## 2. Gates exclusivamente cualitativos — ejecución guiada por evidencia

Cada gate se cierra **PASS** solo con evidencia directa identificable (fuente original con localizador, caso verificable o decisión de auditoría); **PARTIAL** si solo existe documentación genérica/pruebas sintéticas, **OPEN** si falta evidencia, **FAIL** ante divergencia real. Nunca subir un gate para mostrar progreso.

### G-M1 — Identidad CRT de fuente original

**Pregunta:** ¿la descripción de C1/C2/C3, old CRTH/CRTL, sweep, reclaim, breakout, Model #1, stop y destino coincide con RomeoTPT, distinguiendo original vs política de ingeniería?

- Material ya localizado: fuente fundamental RomeoTPT, ep. 1/2/5/7/8/9 y post de jerarquía temporal.
- Model #1 H4→M15, vela fuente y confirmación corporal figuran adjudicados en `VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md`.
- **Bloqueador real:** `MODEL_1_REFERENCE_SELECTION` sigue `AMBIGUOUS`, igual que varias cuestiones de expiración/competencia. No inventar prioridad de pivotes desde la ingeniería.
- **PASS requiere:** acta por cada ambigüedad de la metodología elegida, con fuente original exacta o una excepción de ingeniería claramente rotulada y autorizada por el Owner. Una excepción NO se publicita como "regla Romeo".

**Situación actual: PARTIAL.**

### G-M2 — Identificación visual en datos reales, sin desenlace a la vista

**Pregunta:** ¿un arquitecto puede reconocer cada etapa de H4 CRT→M15 Model #1 en ejemplos reales, sin mirar las velas del futuro ni elegir el caso por rentabilidad?

- Preparar un expediente de situaciones reales del repositorio, con mercado, timestamps con zona, origen del OHLC, H4 padre y todas las M15 pertinentes.
- A cada decisión mostrar **solo información disponible hasta ese cierre**. Registrar fuente y geometría de old level, sweep, confirmación por cuerpo, destino/MOB, tesis rival e invalidación.
- Incluir también casos con ausencia de señal, ruptura aceptada, referencia ambigua, contradicción, confirmación tardía y fallo. Las muestras no pueden estar compuestas solo por aciertos.
- La tarea es de **reconocimiento y explicación visual**, no de cálculo económico ni frecuencia/PF.

**Situación actual: OPEN.** QC-003 tuvo ejemplos **sintéticos**, explícitamente no registros visuales de mercado reales verificados. No se convierten en PASS.

### G-M3 — Cognitiva comprende, cuestiona y decide

**Pregunta:** ¿VT08 demuestra en esos casos reales el PORQUÉ de `EXECUTE / WAIT / ABSTAIN` y diferencia desconocimiento, espera, falsación, tesis invalidada y fuente genuinamente nueva?

- Evidencia: fichas antes-después con `Situation Model`, hipótesis y contra-hipótesis, razón adversarial, incertidumbre, circunstancias de fin de C3 y destino.
- Validar la prohibición de rearm de misma fuente después de ABSTAIN/THESIS_KILLED; explicar los únicos supuestos en los que un evento independiente crea nueva hipótesis.
- El algoritmo cognitivo no puede usar futuro, calcular confianza ficticia ni tomar autoridad de CIBO.
- Software ya reparado en QC-002: `PARTIAL` no se trata como `WELL_SUPPORTED`; pero esto **no cierra** la comprensión del método cuando recibe una afirmación upstream falsa de `KNOWN`.
- **PASS requiere:** reconciliación de decisiones de la cognitiva con decisiones de la auditoría metodológica sobre **casos reales** y con contradicciones documentadas y resueltas. No basta un test unitario sintético.

**Situación actual: PARTIAL.**

### G-M4 — Integración sin desviación metodológica ni capital

**Pregunta:** ¿detectores, router, hipótesis y cognitiva pueden funcionar con la metodología congelada sin una entrada alternativa silenciosa, contaminación de otros traders o tamaño de posición propio?

- Detectores/router Model #1 y contratos cognitivos existen; las pruebas de calidad de Foundation/Gate cubren invariantes locales.
- Confirmar en recorrido causal completo que `NO_C3_OPEN_FALLBACK`, stop estructural, C3 expiry, no resucitar fuente, destinos no disponibles, cadena de autorizaciones y autoridad exclusiva de QORE Risk se respetan sin esconder un veto/umbral que no pertenece a CRT.
- Comprobar separación de experiencia por mercado y ausencia absoluta de sizing/volumen/lotes/apalancamiento propio.
- **PASS requiere:** auditoría del recorrido real completo sobre la interfaz relevante, con acta por contrato y decisión. No es necesario PnL para auditar fidelidad.

**Situación actual: PARTIAL**, porque las pruebas de calidad y contratos locales no equivalen a un dictamen del flujo total usando casos reales.

### G-M5 — Acta de certificación metodológica

- Con G-M1 a G-M4 en **PASS**, emitir `VT08_CRT_PURE_METHODOLOGY_COGNITION_CERTIFICATE` con versión congelada, corpus fuente y casos auditados, expediente de contradicciones, límites de autoridad y firmas/identidades aprobadas por el Owner.
- Si algún gate está `OPEN`, `PARTIAL` o `FAIL`, la acta tiene estado `NOT_CERTIFIED_METHODOLOGICALLY`, no aprobado por proximidad.
- Certificado no autoriza merge, brokers ni despliegue.
- Si una ambigüedad se acepta como ingeniería QORE por mandato, identificar el alcance y evitar llamarlo "CRT puro fuente original" donde no corresponde.

**Situación actual: OPEN.**

## 3. Dictamen a 13-OCT-2026

- **Certificación metodológica/cognitiva:** **NO EMITIDA**, faltan pruebas primarias y examen completo de casos auténticos.
- **Certificación global / `CERTIFIED` de QORE:** **FALSE**; sus requisitos adicionales se mantienen intactos y suspendidos, nunca suplantados por narraciones.
- **Progreso válido:** contrato de origen/source, Model #1 de base, reparación del conocimiento `PARTIAL`, disciplina `WAIT/ABSTAIN` y testigos como herramientas **opcionales**.
- **Barreras concretas:** referencia OLD_HIGH/OLD_LOW no inequívocamente seleccionada por fuente; falta dossier de situaciones reales sin futuro; falta reconciliación cognitiva con casos reales; falta acta de auditoría de extremo a extremo.

## 4. Nueva orden de trabajo para el siguiente arquitecto

**No crear otro testigo. No iniciar otro backtest. No buscar mejores parámetros.**

1. Revisar específicamente videos originales de RomeoTPT y publicaciones del autor que sustentan old high/CRTH, Candle 3, invalidación y destino, y registrar citas breves con instante exacto y autoridad.
2. Resolver o exponer formalmente cada regla pendiente. Cuando el autor no la defina, elaborar una decisión explícita de ingeniería **solo si el Owner la autoriza**, sin inventarla por PnL.
3. Traer una secuencia real verificable H4/M15 y redactar expediente de **casos positivos, negativos y ambiguos**, cronológicamente. No utilizar rentabilidad final para aceptar/rechazar una lectura.
4. Auditar cómo razón y contrato QORE se comportan frente a cada caso real; registrar divergencias y corregir errores de fidelidad, **no optimizar**.
5. Pasar gates G-M1 a G-M4 con evidencia y solo entonces emitir el acta G-M5 (certificación **metodológica**).
6. Mantener resultado `global CERTIFIED=FALSE` hasta que el Owner vuelva a habilitar y completar todas las validaciones globales requeridas.

## 5. Documento de referencia y precedencia

- `VT08-CRT-PURE-OWNER-QUALITATIVE-RETURN-DIRECTIVE-2026-10-13.md`
- `VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md`
- `VT08-CRT-PURE-PRIMARY-SOURCE-ADJUDICATION-QUEUE-001.md`
- `VT08-CRT-PURE-QUALITATIVE-MODEL1-COGNITIVE-RESEARCH-001.md`
- `VT08-CRT-PURE-QUALITATIVE-COGNITIVE-SOURCE-CODE-AUDIT-QC002-2026-10-13.md`
- `VT08-CRT-PURE-QUALITATIVE-CAUSAL-SOURCE-WITNESS-QC003-2026-10-13.md`
- `src/qore/infrastructure/traders/crt_pure_certification_readiness.py`

**GOBERNANZA ACTIVA:** PR #626 DRAFT, sin merge, sin VPS, DEMO, LIVE, producción o capital; BTCUSD market-research freeze preservado; trader VT08 sin sizing/lotaje/volumen/apalancamiento. CIBO/QORE Risk es autoridad externa de capital.

# QORE CORE · VT31 · HANDOFF MAESTRO R3 — GATES DE METODOLOGÍA Y COGNITIVA
**Checkpoint:** 15-OCT-2026 · **Fuente de verdad:** `mezas3238-hue/qore-core` · **Línea de investigación:** PR #940 → #947 → #949 → #952 → #954 → #958 → #959 (todas DRAFT, ninguna fusionada).

## 0. Orden soberana del Owner, sin reinterpretaciones
**Certificar VT31 por su METODOLOGÍA y su COGNITIVA, NO mediante rentabilidad ni criterios cuantitativos de PF, Sharpe, Sortino, DD, densidad, nº de operaciones o sizing.** Evidencias estadísticas de pruebas y casos M1 son inventarios de trazabilidad y diagnóstico, **NO puntuación que otorgue certificados**. No se permite merge a `main` sin orden, LIVE/DEMO/VPS/FundedNext, paper económico/OMS ni lotaje VT31 (autoridad CIBO CMA).

El verdadero objetivo exige **dos certificados separados** de `CERTIFICADO_METODOLOGIA` y `CERTIFICADO_COGNITIVA` por **perfil/version/commit fuente y evidencia**, con revisión independiente (M6). No declarar método certificado solo porque hay pytest PASS; no sustituir doctrina de fuente con supuestos del arquitecto.

## 1. Fuente primaria y perfiles exclusivos: riesgo principal M0
**Fuentes:** [ICT Silver Bullet 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4); [TTrades AM Silver Bullet NQ — 19 Jun 2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) y [PDF oficial TTrades 6p](https://ttrades.com/wp-content/uploads/2026/01/Silver_Bullet_AM_Session_TTrades_PDF.pdf).

- `ICT_GENERAL_2023`: un VT31 con tres ventanas 03–04 London, 10–11 NY AM y 14–15 NY PM en reloj NY DST. H1 09h/raid opuesto **NO** es regla universal London/PM.
- `TTRADES_NY_AM_2025`: SOLO NY AM, H1 09–10 NY completa; primer raid H1 high ⇒ sesgo SHORT y target H1 low; low ⇒ LONG y target H1 high; esperar confirmación/desplazamiento dentro 10–11; autor menciona displacement, FVG, OB, breaker; stop tras swing **que causó** displacement.
- `QORE_G3_PROPUESTA`: reglas propias pivote3 + cuerpo 1,25×mediana5 y mínimo 10 puntos; selección FVG/CE y C2 full wick propias de QORE. **No son automáticamente autoría ICT/TTrades**.

**Conflicto real no escondido:** PR #950 y #955 demostraron con COG G3 ORIGINAL que NY AM puede emitir DOL de cash anterior 150/80 en lugar de opuesto H1 09 TTrades 110/90. Por tanto, **no certificar el COG G3 original como TTrades**. El **source-first research** PR #956 reconstruye DOL H1 autoral y preserva las anclas MSS originales, con WAIT si la distancia al objetivo fuente no cumple `MIN_INDEX_POINTS=10` G3, regla que TTrades **NO** prescribe. Es un nuevo productor de investigación, no integración ni certificación del trader original. Referencia issue [#957](https://github.com/mezas3238-hue/qore-core/issues/957).

## 2. Matriz de decisión REAL M0–M6 — sin conversiones a economía

| Gate | Evidencia/estado demostrado | Adjudicación de certificación |
| --- | --- | --- |
| **M0 identidad fuente** | G3 original vs TTrades NY AM divergencia probada (#950/#955); source-first research #956 es módulo separado | **BLOCKED** hasta selector de perfil causal/versión y decisión única de qué productor VT31 será certificado |
| **M1 reloj, M1 cerrado, DST/causalidad** | G3 OPS/COG, PR #949/954, testigos independientes, adversariales invierno/verano | **ENGINEERING VERIFIED IN SCOPE**, falta integración versionada de perfil único |
| **M2 primer raid, sentido, DOL** | TTrades research COG #949: primer raid H1 y target opuesto corroborados en contexto; source-first #956 resuelve parcialmente conflicto original | **CONTEXT CONFORMANT EN SUBPERFIL RESEARCH**, COG G3 ORIGINAL NY AM no certificado como TTrades |
| **M3 cognitiva MSS/desplazamiento/WAIT** | PR #952: 449/483 regresos sin MSS inicial muestran QORE proxy tardío; V2 #954 conserva WAIT/invalidación | **COG WAIT RESEARCH ENGINEERING VERIFIED**, displacement original del autor NO certificado y G3 original sin nueva política |
| **M4 cuatro familias/precedencia** | PR #958: 457/483 contextos con FVG 3-M1 geométrico QORE, 26 sin él; fuente TTrades nombra displacement/FVG/OB/Breaker sin desempate/algoritmo numérico fuente suficiente | **BLOCKED**, FVG geometría ≠ entry setup autoral, OB/Breaker source NOT_IMPLEMENTED |
| **M5 swing causante SL/invalidación** | PR #959: 189 sin pivote3 candidato, 88 con 1 no causalmente atribuido, 180 varios, 26 sin FVG; stops no inventados | **BLOCKED**, exige swing high/low que realmente causó displacement, no asumir C2 o sweep |
| **M6 frontera/sign-off** | [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) OPEN; API [PR #896 reviews](https://github.com/mezas3238-hue/qore-core/pull/896) devuelve **0 reviews**, sin dos firmantes COG/OPS independientes designados/validados | **BLOCKED**; una cuenta Owner no es dos firmantes; no falsificar atestaciones |

**CERTIFICADO_METODOLOGÍA = NO EMITIDO. CERTIFICADO_COGNITIVA = NO EMITIDO.** Esta es adjudicación de gobernanza factual, NO “falla económica”. El cumplimiento de M1 y la capacidad WAIT demuestran progreso real.

## 3. Evidencias recientes y reproducibles — nada sobre PnL
- [PR #947](https://github.com/mezas3238-hue/qore-core/pull/947) directiva OWNER primacía metodología/COG y evaluador semántico por decisión: CI #38659777717 **42 PASS**. Tests de contrato no equivalen a veredicto del trader.
- [PR #949](https://github.com/mezas3238-hue/qore-core/pull/949) COG TTrades **REAL #933** fuente #929/#926 y V2 #928, corpus 775 días: 128 contextos con DTO auténtico DOL H1 opuesto; 483 WAIT implícitos por QORE MSS primera M1, 92 sweep sin regreso, 65 sin sweep, 6 incompletos y 1 rechazo; CI #38671454652 **78 PASS**.
- [PR #952](https://github.com/mezas3238-hue/qore-core/pull/952) diagnostica cognitiva: **449** MSS QORE proxies después de primera M1 retorno entre **483** abstenciones, 34 sin aparición hasta 11:00; CI #38707327204 **79 PASS**. **449 NO son trades autorales**.
- [PR #954](https://github.com/mezas3238-hue/qore-core/pull/954) COG V2 WAIT persistente (read-only) y primera fuente inmutable: de 483, 449 QORE MSS posteriores y 34 expirados; **48 de 449 contextos se invalidan DESPUÉS** por raid opuesto; cierre 401 contextos proxy no contradichos + 48 invalidados + 34 expirados; CI #38708842316 **80 PASS**. V2 nunca construye `CognitiveDecision`, no emite orden.
- [PR #958](https://github.com/mezas3238-hue/qore-core/pull/958) source M4 FVG/4 familias: de mismos 483, **457 geometrías QORE** FVG M1 3 cierres en contexto y **26 sin**; 48 invalidaciones finales solapadas, CI #38710774260 **79 PASS**, artifact #11960700796 ZIP SHA256 `9ae5fac3ea01d07405d4d571d587b5e3f450e3d150fba77b39cfb7c6dad31804`. No FVG fill ni fuente author.
- [PR #959](https://github.com/mezas3238-hue/qore-core/pull/959) source M5 swing: 483 casos sin stop inventado, categorías **189/88/180/26**, CI #38711574019 **76 PASS**, artifact #11961370684 SHA256 `4d792d35bd6fabbdb61656ce70fe71bc702000b94f671d2d54df4e144a8f4c67`.
- En otros lanes: [#948](https://github.com/mezas3238-hue/qore-core/pull/948) COG G3 original LONG/WAIT/REJECT, [#950](https://github.com/mezas3238-hue/qore-core/pull/950) DOL original vs TTrades conflicto, [#951](https://github.com/mezas3238-hue/qore-core/pull/951) M0 perfil, [#953](https://github.com/mezas3238-hue/qore-core/pull/953) NY PM COG original, [#955](https://github.com/mezas3238-hue/qore-core/pull/955) COG ORIGINAL short 3 sesiones, [#956](https://github.com/mezas3238-hue/qore-core/pull/956) source-first DOL/H1 y conflicto QORE G3 mínimo 10. Integrar conclusiones SIN mezclar productores originales, research, ni múltiples firmas con mismo login.
- [#940 R2](https://github.com/mezas3238-hue/qore-core/pull/940) custodió el handoff anterior, [#941/#942/#944] investigaron M1 DOL/continuidad fuente (10 intervalos únicos). Estas pruebas son **diagnóstico** auxiliar, no criterios de certificado por trade count.

## 4. Bloqueos técnicos exactos, con prueba de resolución necesaria
**B0 — Identidad y selector cognitivo real (M0):** congelar un solo COG operativo de `ICT_GENERAL` y sus subperfiles, decidir cuál fuente manda cuando TTrades NYAM y G3 cash DOL discrepan. Demostrar cambio de perfil **antes de observar resultado** y que no se puede tomar una tesis de PM/London para NYAM TTrades. Diferenciar el nuevo #956 source-first del COG original: investigación ≠ integración.
 
**B1 — Displacement TTrades (M3):** recoger casos primarios autorales con timestamps positivos/negativos de desplazamiento posterior a sweep/return, swing relevante, con `WAIT` si no hay confirmación, y explicar regla sin convertir QORE pivot3×1.25 en texto del autor. El artículo y PDF no fijan ese número. Se intentó transcripción del video oficial enlazado, pero plugin conectado vidIQ **sin créditos** (no se consumieron; próximo reset 28-OCT-2026). NO inventar contenido de video ni afirmar que fue auditado.

**B2 — Las 4 familias M4:** fuente/conjunto de casos positivos, negativos y confusos para displacement, FVG en estructura, OB y breaker por separado; definir en el contrato del perfil si puede operar **sin** FVG cuando hay desplazamiento u OB/Breaker, cómo elegir ante simultaneidad, y cómo invalidar. Prioridad no especificada por artículo/PDF: `AUTHOR_AMBIGUITY` o especificación **QORE propia etiquetada**, nunca atribuir arbitrariamente al autor.

**B3 — Swing stop M5:** identificar **qué swing CAUSÓ desplazamiento**, no cualquier pivot3/cierre C2/sweep high. Resolver varias opciones plausibles en casos reales con anotación de metodología. No es tarea de lotaje del trader: solo determinar **límite estructural de invalidación**; autoridad de tamaño sigue CIBO CMA. Mientras testigo insuficiente ⇒ `WAIT/UNKNOWN`.

**B4 — Gobernanza M6 (dependencia externa real):** [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) solicita dos **identidades revisoras independientes**, COG y OPS, autorizadas y atestaciones ligadas a **DOC `a446afa17ed6e411b8f0b6fc182b103a78959a97` + CODE `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`** G3 r1.3, así como fuente/version método nuevo. API revisada 15-OCT: **0 reviews APPROVED** en [PR #896](https://github.com/mezas3238-hue/qore-core/pull/896). Aprobación Owner “revisar urgente” es administrativa, NO firma COG+OPS. No simular independencia desde una cuenta. Acción Owner: designar los dos revisores y sus permisos o modificar gobernanza con acto formal legítimo (no unilateral de un agente). Contrato original bloqueado hasta entonces.
 
**B5 — Certificación separada, sin LIVE:** cuando estén corregidos y contrastados B0–B4, ejecutar acta M0–M6 sobre código/version SHA congelados, fuente primaria testigos y negativas, primero `METHOD_CERTIFIED`, segundo `COGNITION_CERTIFIED`. Solo tras ambas y firmas genuinas sería permisible escribir CERTIFICACIÓN METODOLOGÍA/COG, **pero aún no operación/DEMO/LIVE**. Trader Lab L1–L10/economía permanecen expediente separado.

## 5. Protocolo de continuación sin pérdida de contexto
1. Inspeccionar GitHub PRs #940, #947, #949, #952, #954, #956, #958, #959 y issue #957/#897 antes de elegir archivos. Fuente de verdad es commit/CI/artefacto, NO afirmación narrativa.
2. Nuevo lane separado ADDITIVO; prereg PRE-code; no pisar G3 original. Mantener #959 y padres DRAFT, sin merge.
3. Ruta más corta de avance: adjudicar source authorial cuatro familias con testigos en M1 (positivos/negativos) y versionar COG V2 **de investigación** para que solo emita `CONTEXT_READY_PENDING_ENTRY_FAMILY` cuando se demuestre, no por QORE MSS/FVG proxy. Luego resolver M5 swing causante e identidad M0 y M6 firmas.
4. Ejecutar QA/CI por cada modificación, publicar hash y artifact, reportar cada caso crítico y decisión `WAIT/REJECT/UNKNOWN`. Cualquier afirmación no respaldada por fuente ⇒ no PASS.
5. No contar 483, 449, 457, 189, 88, 180 ni 26 como trades; ninguno es una métrica económica. No utilizar los datos 3Y ya vistos como OOS; no desarrollar a base de PnL.
6. Reabrir revisión M6 solo con firmantes genuinos; una única cuenta no crea dos personas. Ningún arquitecto declara `CERTIFIED` a partir de CI de investigación.

### Dictamen R3
**VT31 ESTÁ EN PROCESO ACTIVO DE CERTIFICACIÓN METODOLÓGICA Y COGNITIVA; NO ESTÁ CERTIFICADO TODAVÍA.** Hay evidencias fuertes de capacidad de espera/invalidez, primera fuente H1 TTrades en research y comportamiento causal M1. Hay **contradicción documentada en original G3 NY AM vs fuente TTrades**, M3 autoral no formalizado, M4 cuatro familias incompleto, M5 swing causante no validado y M6 sin firmas humanas distintas. **NO MERGE, NO LIVE, NO sizing propio.**

# QORE CORE — VT31 · HANDOFF MAESTRO DE CONTINUIDAD
## Certificación por metodología, cognitiva y evidencia causal · 14-OCT-2026

**Repositorio soberano:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core)  
**Owner:** titular y autoridad final del repositorio.  
**Rama de este handoff:** \`agent/vt31-master-handoff-method-cognition-certification-20261014\`  
**BASE inmutable de la rama de handoff:** \`54ed47d35db25df5c47115cac6888da4c58801d7\` (HEAD documental PR #929 en el momento de crearla).  
**Dictamen al corte:** \`METHODOLOGY_CERTIFICATION_PENDING\` · \`COGNITION_CERTIFICATION_PENDING\` · \`VT31_TRADER_NOT_CERTIFIED\` · \`ECONOMIC_EDGE_NOT_DEMONSTRATED\`.

> **ORDEN VIGENTE DEL OWNER:** No descartar VT31. La misión prioritaria cambia de perseguir profit factor o un filtro ganador a **certificar la fidelidad metodológica y la calidad de las decisiones cognitivas**. No declarar rentabilidad de una estrategia por aprobar tests metodológicos. El siguiente arquitecto debe trabajar sobre este plan, explicar toda discrepancia y preservar la gobernanza.

Este documento contiene todo lo verificado y lo todavía no resuelto; **no es firma ni autorización de operar**. Los resultados científicos del histórico siguen registrados y no se borran.

---

## 1. REGLAS SOBERANAS DE TRABAJO (NO NEGOCIABLES)

1. **GitHub es la única fuente de verdad.** No MERGE sin instrucción explícita del Owner. Todo trabajo nuevo en rama de investigación + PR DRAFT, con preregistro de expectativas, logs, hashes, pruebas adversariales y enlaces.
2. **NO LIVE**, NO FundedNext LIVE, NO producción, NO VPS, NO órdenes broker ni despliegue/paper conectado a OMS sin nueva autorización. El Owner autorizó la investigación y revisión, no la operativa.
3. **NUNCA sizing en el Trader.** CIBO/CMA gobierna el volumen y QDLE su factibilidad/costes. VT31 entrega intención/cognición y estructura; no calcula lotaje por sí solo.
4. **No fingir firma COG/OPS**: dos identidades independientes no se reemplazan por dos agentes usando una cuenta GitHub. Issue [#897](https://github.com/mezas3238-hue/qore-core/issues/897) continúa abierto. Si el Owner quiere modificar el protocolo de doble firma, debe registrarse como **cambio formal y versionado de gobernanza**, nunca como firmas que no existen.
5. **No usar el Fresh Holdout** para afinar patrones, modelos, regímenes, parámetros ni stops. El NAS100 3Y ya es desarrollo previamente observado.
6. Sólo datos disponibles **as-of**; NAS100 M1 con reloj \`America/New_York\` y DST real. No asumir el orden intrabar high→low usando OHLC; devolver \`UNKNOWN\` cuando falte secuencia.
7. **No equiparar un CI verde con trader certificado.** \`CONFIRMED\` en un testigo significa un hecho acotado de contexto; nunca implica \`TRADER_CERTIFIED\`, \`LIVE_AUTHORIZED\` ni \`EDGE_VERIFIED\`.
8. La metodología debe nombrarse y versionarse sin mezclar **ICT general 2023**, **TTrades NY AM 2025** y **formalizaciones QORE**. No copiar el filtro H1 09–10 de TTrades a Londres/NY PM de ICT por defecto.
9. No filtrar señales retrospectivamente para mejorar retorno, no optimizar parameters/umbrales por resultados, no escoger OB/Breaker porque su media sea positiva; distinguir \`NO_SUPPORT\`, \`UNDERPOWERED\` y \`BLOCKED/UNKNOWN\`.

## 2. DÓNDE ESTÁ CADA PIEZA: MAPA DE PRS, CÓDIGO Y EVIDENCIA

### 2.1 Cadena de certificación metodológica/cognitiva — **PRIORIDAD ACTUAL**

| PR y estado auditado | Contenido | Git HEAD consultado | Evidencia CI | Interpretación |
|---|---|---|---|---|
| [#896 — DRAFT](https://github.com/mezas3238-hue/qore-core/pull/896) | G3 r1.3, MSS/OPS; base contractual que NO se modifica | \`78d4cdac0e09d1a6eef37b99c505ffc5098031fc\` | [#38343414831](https://github.com/mezas3238-hue/qore-core/actions/runs/38343414831), 41/41 | \`G3_PENDING_DUAL_SIGNATURE\` |
| [#926 — DRAFT](https://github.com/mezas3238-hue/qore-core/pull/926) | M0–M3: identidad de fuentes y primer comprobador TTrades AM | \`82ea1ab802ede75d7fbd965ee42cce23e7ce1487\` | [#38546753088](https://github.com/mezas3238-hue/qore-core/actions/runs/38546753088), 62/62 | Testigo independiente de contexto |
| [#927 — DRAFT](https://github.com/mezas3238-hue/qore-core/pull/927) | MC-P1: productor **COG REAL** vs TTrades AM, falsación de discrepancia | \`5f08b1fb3a5ec3dfdc984ba49baeca904360ec3c\` | [#38579110581](https://github.com/mezas3238-hue/qore-core/actions/runs/38579110581), 69/69 | Contraejemplo doctrinal real del código con mercado sintético |
| [#928 — DRAFT](https://github.com/mezas3238-hue/qore-core/pull/928) | \`COG_EVIDENCE_V2\`: verifica independientemente MSS/pivote/M1 y origen DOL por perfil | \`90f2ce2a957823389fc5d999eedd198c3f20d55a\` | [#38594178014](https://github.com/mezas3238-hue/qore-core/actions/runs/38594178014), 80/80 | Atestación causal M0–M3, no trader |
| [#929 — DRAFT](https://github.com/mezas3238-hue/qore-core/pull/929) | MC-P2: testigo **nativo** TTrades H1 09:00, sweep, regreso y comparación con V2 | \`54ed47d35db25df5c47115cac6888da4c58801d7\` | [#38607626630](https://github.com/mezas3238-hue/qore-core/actions/runs/38607626630), 101/101 | Base principal de este handoff |

**Precisión sobre CI:** los HEAD de algunos PR incluyen documentación posterior al commit de código ejecutado. Para #929 el código CI fue \`d356e5fcd0d4fc364239ed4cfb1f4a71a0c94447\`; la versión documental HEAD es \`54ed47d35db25df5c47115cac6888da4c58801d7\`. Para #928 el código verificado fue \`150837fd1d84ef4a16b07ce03ebf5fcf5ee400d4\`. Para #927 \`755fff9e761f6bd5432e87df532a6872fbc6b1a1\`; para #926 \`0c3235b4d31880b9e0f8ac2d95b1bdc68916733e\`. Releer diffs antes de afirmar que la misma CI probó cambios posteriores.

**Genealogía:** #929 está apilado sobre #928, que deriva de #926; #927 es una **rama hermana** desde #926 y sus tests del COG genuino **no se deben perder** al consolidar. No cherry-pick/merge de PR DRAFT en main por comodidad.

### 2.2 Documentos ya publicados y útiles

- [Plan de certificación M0–M7](https://github.com/mezas3238-hue/qore-core/blob/4477540e928dc9ec3bdbe437e2bea7a01990c9c9/docs/research/VT31_METHOD_COG_CERTIFICATION_PLAN_PREREG_2026-10-14.md), registrado antes del código.
- [Informe inicial M0–M3 #926](https://github.com/mezas3238-hue/qore-core/blob/82ea1ab802ede75d7fbd965ee42cce23e7ce1487/docs/research/VT31_METHOD_COG_CERTIFICATION_FIRST_VERDICT_2026-10-14.md).
- [COG auténtico: falsación MC-P1 #927](https://github.com/mezas3238-hue/qore-core/blob/5f08b1fb3a5ec3dfdc984ba49baeca904360ec3c/docs/research/VT31_MC_P1_REAL_COG_COGNITION_METHOD_SOURCE_CERT_VERDICT_2026-10-14.md).
- [COG_EVIDENCE_V2 #928 — dictamen](https://github.com/mezas3238-hue/qore-core/blob/90f2ce2a957823389fc5d999eedd198c3f20d55a/docs/research/VT31_COG_EVIDENCE_V2_FIRST_VERDICT_2026-10-14.md).
- [MC-P2 #929 — testigo H1 nativo](https://github.com/mezas3238-hue/qore-core/blob/54ed47d35db25df5c47115cac6888da4c58801d7/docs/research/VT31_MC_P2_TTRADES_NATIVE_H1_SOURCE_CERTIFICATION_VERDICT_2026-10-14.md).
- [Issue #727](https://github.com/mezas3238-hue/qore-core/issues/727): muro de coordinación entre arquitectos; dejar nueva nota de continuidad al publicar este handoff.

### 2.3 Error de integración: rama experimental V2 **NO canónica**

Se detectó una versión paralela \`agent/vt31-cog-evidence-v2-p0-20261014\` que define \`CogEvidenceV2\` de manera distinta:
- [CI #38607867244](https://github.com/mezas3238-hue/qore-core/actions/runs/38607867244): FAIL por Ruff E501 inicialmente.
- [CI #38607963276](https://github.com/mezas3238-hue/qore-core/actions/runs/38607963276): FAIL tras primer fix; pruebas fallidas por discrepancia serialización \`Status(StrEnum)\` contra cadena y expectativas incongruentes de UNKNOWN/REJECTED en datos M1 con as-of inconsistente.
- **No equiparar su CI roja con la del PR #928**, cuya propia implementación y 80 pruebas están verificadas.
- **NO MERGE ni reemplazar el módulo canónico del #928 por el homónimo de esa rama.** Si se aprovecha su idea de hash de DTO, integrarla con nueva especificación y tests nuevos **encima de #929**; nunca modificar el viejo modelo G3 por conveniencia.

## 3. IDENTIDAD DEL TRADER Y EL PUNTO DOCTRINAL FUNDAMENTAL

**Un solo VT31 NAS100/NQ-context, múltiples perfiles investigados; no son cuatro traders distintos.** Operativa fuente M1, sin reemplazar con M5; no DAILY/H4 como capa de decisión de scalper. Las ventanas ICT del proyecto están en horario Nueva York:
- LONDON **03:00–04:00**;
- NEW YORK AM **10:00–11:00**;
- NEW YORK PM **14:00–15:00**.

**Perfil \`ICT_GENERAL_2023\`:** Silver Bullet original con FVG, estructura/objetivos DOL y contexto. Fuente: [vídeo ICT 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4). No se puede declarar que el H1 de 09:00–10:00 sea obligatorio a Londres y NY PM; necesita evidencia causal independiente de DOL prior NY cash/Asia/London para no dar por auténtico un pool que sólo declara COG.

**Perfil \`TTRADES_NY_AM_2025\`:** variante restringida 10:00–11:00 NY, fuente [TTrades AM Silver Bullet NQ (19 junio 2025)](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/):
- H1 09:00–10:00 cerrado completo;
- barrido del high o low de ese H1 **antes** de la reversión;
- HIGH barrido => SHORT hacia low H1; LOW barrido => LONG hacia high H1;
- desplazamiento/regreso **dentro** del rango con M1 ya cerrada, orden causal;
- entradas mencionadas: displacement, FVG, order block, breaker block;
- stop más allá del swing causante del desplazamiento; no sustituir por C2 stop QORE sin identificar divergencia.
- Falta especificación algorítmica textual completa de OB/Breaker, por lo que son **proxies QORE inspirados en TTrades**, no «ICT/TTrades exacto» por decreto.

**Perfil \`QORE_G3_MSS_CLOSE_V1_PROPOSED\`:** formalización propia: pivote M1 de 3 barras, MSS cuerpo \`>=1.25×median5\` de cuerpos previos, DOL elegible prior NY/Asia/London más cercano con distancia mínima de 10 puntos, FVG tres M1 y CE 50%, stop C2 + tick según propuesta. **Reglas QORE no iguales automáticamente a fuente original.**

## 4. QUÉ TRABAJOS SE HICIERON (PRUEBA, ALCANCE Y LÍMITES)

### 4.1 M0–M1 — Identidad, reloj, velas M1 y origen causal

**HECHO:** PR #926 introduce testigo separado de la COG con \`CognitiveDecision\` verdadero como contrato, ventanas NY DST, secuencias cerradas M1, 60 M1 previas 09–10 completas para TTrades y prefijo 10–11 disponible al instante \`as_of\`. Rechaza faltantes, doble barrido y datos futuros, verifica momento MSS y DOL opuesto exacto. [CI #38546753088](https://github.com/mezas3238-hue/qore-core/actions/runs/38546753088) **62/62 PASS** (13 del nuevo verificador +49 regresiones auténticas COG/OPS/M1/G3). Resultado positivo máximo \`CONTEXT_CONFORMANT_ONLY\`, sin orden.

**LÍMITE:** no es el COG runtime modificado ni mide totalidad de doctrina en mercado. Un testigo sintético aprobando ≠ trader certificado.

### 4.2 MC-P1 — Se probó COG REAL y se encontró una falta doctrinal

PR #927 no fabrica su objeto de decisión: alimenta el **productor auténtico** \`VT31CleanroomCognition\` con M1 de un **mercado artificial adversarial**:
- NY cash anterior high **150**.
- Rango H1 09–10 high **110**, low **90**.
- Caso sin raid 09–10 en 10AM pero con estructura MSS suficiente para el COG QORE.
- El COG genuino entrega **LONG hacia 150** (pool \`PRIOR_NY_CASH_SESSION_HIGH\`).
- La fuente TTrades AM exige barrido previo y, para LONG después de barrer low, target **110**. El comprobador devuelve **\`REJECTED:NO_PRE_SIGNAL_9AM_H1_SWEEP\`** y **\`REJECTED:DOL_NOT_OPPOSITE_9AM_H1_EXTREME\`**.
- [CI #38579110581](https://github.com/mezas3238-hue/qore-core/actions/runs/38579110581) **69/69 PASS** y artifact **11902302689**, luego de corregir un primer fallo F401 de import no usado en el test.

**INTERPRETACIÓN CORRECTA:** actual COG QORE **no reproduce nativamente TTrades AM** en ese caso. No significa que toda ICT sea inválida, ni que las oportunidades reales fallen con idéntica proporción, ni que los retornos económicos sean negativos.

### 4.3 COG_EVIDENCE_V2 — MSS/pivote y selectividad del conocimiento

PR #928, \`scripts/vt31_cog_evidence_v2_20261014.py\`, verifica de manera independiente:
- \`as_of\` externo; M1 cerradas y continuas, origen y edad de pruebas;
- vela de cierre MSS exacta, \`mss_anchor_close\` que coincida con M1 original, **no con un C3 posterior**;
- micropivote de tres velas, su nivel y confirmación por la vela derecha **antes de MSS**;
- ruptura direccional y desplazamiento del cuerpo \`>=1.25×median5\` como **proxy QORE**, no regla demostrada de ICT;
- DOL por perfil, contra evidencia externa cuando esté disponible;
- TTrades AM: sweep H1 previo / regreso / target opuesto;
- ICT general: \`UNKNOWN:ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED\` mientras no se reconstruya independientemente su pool de liquidez.
- Estados \`CONFIRMED/REJECTED/UNKNOWN\` **sólo para los hechos acotados M0–M3**; flags de certificación, live y sizing siempre denegados.

[CI #38594178014](https://github.com/mezas3238-hue/qore-core/actions/runs/38594178014) **80/80 PASS**, artifact **11908981245**. En otro escenario con raid low+MSS LONG, el productor real eligió previous cash high=150 y el testigo lo rechazó para TTrades high09=110; frente a ICT general quedó **UNKNOWN** por DOL no atestado, no automáticamente «falso».

### 4.4 MC-P2 — Testigo de contexto **nativo** TTrades AM

PR #929, \`scripts/vt31_mc_p2_ttrades_native_h1_evidence_20261014.py\`, analiza datos independientemente del COG:
- construye H1 09:00 a partir de 60 M1 cerradas;
- detecta PRIMER sweep 10AM de extremo alto/bajo, sello temporal y dirección;
- exige retorno **en una M1 cerrada posterior**, no acepta suponer high/low intrabar de la vela sweep;
- evita elegir a posteriori segundo sweep favorable; ambos extremos en una M1 → \`UNKNOWN\`, sweep contrario ulterior → \`REJECTED\`;
- coteja el testigo independiente con el DTO original COG y con #928 V2, sin alterar el generador de señales.
- salida máxima \`CONTEXT_ATTESTED_NOT_CERTIFIED\`. **M2 de contexto nativo sí verificable; M3 displacement total del autor sigue sin certificar**.

[CI #38607626630](https://github.com/mezas3238-hue/qore-core/actions/runs/38607626630) **101/101 PASS**, artifact **11916311533**, con casos LONG/SHORT, DST verano e invierno y antileakage. Los testigos «conformes» son sintéticos y **no** prueban tasa real de concordancia de la COG instalada sobre los 3Y.

### 4.5 Investigación de edge anterior — preservar pero NO mezclar con certificación cognitiva

| PR | Hallazgo / alcance exacto |
|---|---|
| [#902](https://github.com/mezas3238-hue/qore-core/pull/902) | 2.140 señales viejas, media bruta signed 15min **−1.919664 puntos**; 301 contactos con CE basados en OHLC futuros NO son 301 fills. Economía V1 CE/SL/DOL todavía no computada. |
| [#905](https://github.com/mezas3238-hue/qore-core/pull/905) | TTrades AM FVG-only reconstituido en 3Y M1: **205** candidatos de 775 días, gross 15m **−1.445951 pts**; IC incluye cero. |
| [#906](https://github.com/mezas3238-hue/qore-core/pull/906) | 4 familias source-only (212 DIRECT, 205 FVG, 116 OB, 84 BREAKER); OB gross +1.865948 y Breaker +1.661548 pts pero **IC cruza cero**. Proxies sin fills ni edge. |
| [#907](https://github.com/mezas3238-hue/qore-core/pull/907) | Solapamiento: **116/116 OB** y **84/84 Breaker** son subgrupos de día DIRECT, exclusivos 0; la comparación de ancla común cambia signo/escala y placebo tiene otro reloj. No escoger «ganador». |
| [#910](https://github.com/mezas3238-hue/qore-core/pull/910) | Puerta COG+OPS vs primer FVG crudo, 2.286 horas, 2.140 seleccionados: delta **−0.954117 pts**, IC95 [−2.692464;+0.840541]; **COG aislado NO IDENTIFICADO**, tiempos/lados distintos. |
| [#911](https://github.com/mezas3238-hue/qore-core/pull/911) | 4 regímenes PIT TREND/CHOP × alta/baja volatilidad, ninguno demuestra lift; TREND submuestras 41 y 46 = **UNDERPOWERED**. |
| [#912](https://github.com/mezas3238-hue/qore-core/pull/912) | Macro CPI/NFP/FOMC **PREREG SOLO**, sin dataset exhaustivo congelado y **sin resultado macro**. |

**IMPORTANTE:** los resultados de +15m desde OPEN después de un FVG o retest no son backtest económico de LIMIT CE+stop C2+TP DOL, ni WR, PF, DD, Sharpe ni Sortino del trader. Ninguna PR previa prueba rentabilidad neta o falsación de ICT universal.

## 5. MATRIZ DE CERTIFICACIÓN — LO APROBADO Y LO QUE FALTA

| Gate | Estado honesto al corte | Criterio mínimo para aprobar |
|---|---|---|
| **M0 – Identidad y fuente** | \`PARTIAL_SOURCE_PROFILES_SEPARATED\` | Selector por sesión y perfil versionado con fuente; ICT/TTrades/QORE explícitos; no reglas cruzadas. |
| **M1 – Datos, reloj, causalidad** | \`TEST_FIXTURES_PASS\` | Revalidar en muestras reales M1 por estación/DST, gaps, as-of; audit trail SHA y no futuro; 0 discrepancias causales críticas. |
| **M2 – Liquidez/sweep/DOL** | TTrades AM testigo independiente \`SOURCE_WITNESS_PASS\`; COG actual tiene \`SOURCE_MISMATCH\` | Nuevo productor COG específico de método debe emitir side/DOL congruentes con sweep, y testigo independiente atestarlo; para ICT, fuentes externas de DOL. |
| **M3 – MSS/desplazamiento** | V2 verifica pivot/MSS/QORE; \`AUTHOR_DISPLACEMENT_NOT_CERTIFIED\` | Reproducir una semántica causal revisada de MSS y displacement por perfil, con ejemplos positivos/negativos primarios y UNKNOWN en ambigüedad. |
| **M4 – Entradas** | \`NOT_CERTIFIED\`, research-only en #906 | Cada familia (desplazamiento directo/FVG/OB/Breaker) con definición autoral o etiqueta QORE_PROXY, trigger causal, zona, expiración, veto, no-trade, evidencia as-of; tests positivos y negativos. |
| **M5 – Invalidación, TP y salidas** | \`NOT_CERTIFIED\` | SL swing que causó displacement para TTrades vs C2 stop propuesto QORE, tick/buffer y target DOL, intrabar ambiguity/expiry definidos, sin sizing propio, sin órdenes aún. |
| **M6 – Gobernanza / operación** | \`BLOCKED_DUAL_SIGNATURE\` | Atestación real COG+OPS en SHAs congelados o cambio de gobernanza formal aprobado; pruebas de contrato OPS separadas de semántica COG. |
| **M7 – Economía / OOS** | \`BLOCKED_BROKER_DATA_AND_IMPLEMENTATION\` | Identidad contrato/broker, histórico BID/ASK/ticks suficiente, OMS/ACK, costes y simulación SL/TP, OOS auténtico, PF/DD/equity reproducibles; aprobación Owner para activar siguiente gate. |

**No existe hoy certificado global de VT31.** No aprobar M2 completo por construir un testigo de raid; no aprobar M3 autoral por hacer coherente un pivot QORE; no aprobar M4/M5 por tener códigos de detectores/source-only; no aprobar M6 con una cuenta.

## 6. PROBLEMAS P0 IDENTIFICADOS Y CORRECCIÓN CONCRETA

### P0-A — Confusión doctrinal entre ICT general y TTrades NY AM
**Causa:** la lógica vigente de DOL contextual (prior NY cash/Asia/London) no obliga a buscar high/low 09–10 ni a exigir sweep. **Prueba:** COG REAL produjo 150 vs H1 110 en escenarios MC-P1/V2; en uno tampoco hubo sweep.  
**Solución:** identidad de perfil explícita *antes de detectar*; dos atestadores fuente independientes por perfil. No introducir regla TTrades en London/PM. Si se crea COG NY AM TTrades, hacerlo como nueva versión en nueva rama, nunca reescribir G3 firmado-para-revisión.

### P0-B — Falta de fuente nativa de DOL ICT (pendiente principal en las 3 sesiones)
**Causa:** V2 puede verificar timestamps de un nivel declarado, pero sin reconstruir pools previos desde M1 independientes mantiene \`UNKNOWN:ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED\`.  
**Solución inmediata:** \`ICT_DOL_SOURCE_V1\`: construir prev NY cash / Asia / London H/L de M1 causales, exigir ventanas completas, marcadores de nivel barrido/no barrido según reglas declaradas, selección y vigencia, identidad de sesión y DST; comparar contra \`CognitiveDecision.draw_family/draw_target/draw_level_observed_at\`, sin readbacks del DTO para fabricar el nivel. Registrar \`CONFIRMED/REJECTED/UNKNOWN\`. Tests negativos: gap H1/M1, sesiones que cruzan medianoche, DST, duplicados, nivel inexistente, objetivo antiguo, rotación y fuente futura. **No afirmar que preferir el DOL más cercano sea regla original de ICT.**

### P0-C — El COG actual puede declarar un MSS coherente con reglas QORE, pero no probar la semántica ICT completa
**Causa:** micropivote 3M1 y cuerpo≥1.25×median5 son cuantificación QORE; no garantizan displacement/source qualitative.  
**Solución:** analizar referencias autorales explícitas y construir dos contratos: \`AUTHOR_WITNESS\` (evidencia fiel que sí puede formalizarse) y \`QORE_OPERATIONAL_PROXY\` (decisiones propias honestamente etiquetadas). Congelar casos positivos y **no-trade** negativos con timestamps as-of. No usar interpretación favorable del resultado del replay para «corregir» doctrinas.

### P0-D — M4: ninguna familia completa está certificada y faltan reglas autorales deterministas de OB/Breaker
**Causa:** #906 evalúa retestes de proxy OB y pivote breaker; no demuestra que esos niveles cumplan breaker block del autor ni que hayan sido órdenes que llenaron.  
**Solución:** cuatro contratos por perfil, input/output, zona/trigger/expiración/tie-break/counterexample; testigos manuales de fuente etiquetados por dos revisiones reproducibles, desacuerdos \`SOURCE_AMBIGUITY\`. Aplicar pruebas *por significado*, no sólo conteos de trades. No cambiar threshold para forzar CI.

### P0-E — M5: stop/target no unificados ni certificados
**Causa:** TTrades propone stop más allá del swing causante del desplazamiento; G3 define stop C2 wick+tick, no siempre mismo precio/estructura. Tampoco hay fill, BE/partials ni cierre económico completo.  
**Solución:** una política de invalidación por perfil, testigo de swing **as-of**, tick/contract específico, DOL anterior y cierre de ventana/15:55 según acta. Evaluar conflictos OHLC como \`AMBIGUOUS\` sin inventar orden intrabar. Entregar intención de stop/TP a OPS sin sizing ni órdenes hasta gates correspondientes.

### P0-F — M6 firmas duplicadas inexistentes
**Causa:** issue [#897](https://github.com/mezas3238-hue/qore-core/issues/897) sigue \`open\`; autorizaciones del Owner para investigar no prueban revisión independiente COG y OPS.  
**Solución:** Owner designa dos firmantes independientes con permiso real **o** ordena reemplazo del requisito mediante acto versionado explícito y nuevo contrato de governance. La revisión revisará el par exacto **DOC** \`a446afa17ed6e411b8f0b6fc182b103a78959a97\` y **CODE** \`78d4cdac0e09d1a6eef37b99c505ffc5098031fc\`, CI y responsabilidades; nunca declarar doble firma por un comentario de agentes usando el mismo login.

### P0-G — M7 historial exacto BID/ASK / identidad NAS100 broker NO verificada
**Causa:** [Issue #900](https://github.com/mezas3238-hue/qore-core/issues/900) muestra cuenta cTrader DEMO lectura que **no exponía el símbolo exacto NAS100**; no prueba inexistencia de datos en todo QORE Native. Usuario afirma tener datasets BID/ASK históricos: **buscar PRs, GitHub Actions artifacts y fuentes Native existentes antes de descargar o cobrar datos externos**. El M1 congelado NAS100 \`1,059,784\` barras SHA256 \`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa\` es OHLC y **NO** un stream de fills ejecutables.  
**Solución:** auditoría de inventario **dentro de GitHub** para mismo instrumento broker y tiempo exacto, fuente de BID/ASK/tick, spreads por vela, tick_size, comisiones/currency/contract. Sólo si existe el dato y cumplen contratos, ejecutar G5 y G6/G7 económicos con autorizaciones; no asumir que NAS100 CFD equivale al NQ de futuros. No gastar USD125 en datos sin orden expresa ni fondos.

### P1-H — Trabajos duplicados sin centralización
**Causa:** #927 rama hermana de #928; #929 sigue #928; hay rama V2 duplicada con 2 workflows fallidas; source-only #905–#907 usan identificadores parcialmente solapados.  
**Solución:** crear un **índice de identidad de contrato y PR** y mapa semántico de eventos (por perfil), mantener testigos fallidos como negativos, no sobrescribir module names ni fusionar branches no autorizadas, correr CI total de regresión de fuente+COG+OPS. Mantener un único expediente de certificación en este handoff y Issue #727.

### P1-I — Identificación cognitiva no aislada / selección sesgada
**Causa:** 2,140 fuente histórica ya pasó COG+OPS; compararla con primer FVG crudo modifica timestamp/lado. En Gate1 diferencia −0.954 pts IC cruza cero, no prueba que COG por sí sola no agrega inteligencia.  
**Solución:** si se reabre sólo para diagnóstico de metodología, registrar cada FVG fuente con \`COG_APPROVE/REJECT/UNKNOWN\` **antes de la salida de la vela siguiente**, explicar razón estructural y doble fuente. No confundir selección con rentabilidad ni intervenir filtros por resultados. Esta tarea no debe desplazar P0-A–E.

### P1-J — Calendarios macro y regímenes no sustituyen metodología
**Causa:** Gate2 TREND bajo poder; Gate3 macro calendario no ejecutado.  
**Solución:** conservar resultados y no mezclarlos con certificado de método. Sólo ejecutar Gate3 si el calendario PIT completo CPI/Employment Situation/FOMC queda congelado, fechas/horas oficiales y hash; hoy PR #912 solo preregistra. No perseguir combinaciones si no hay mecanismo.

### P1-K — M1 retest / instant intrabar ambiguo
**Causa:** OHLC de M1 no da secuencia exacta de tocar CE, stop, DOL; 301 CE touches no fills y 737 contactos ambiguos de fuente vieja.  
**Solución:** semántica explícita \`TOUCH_NOT_FILL\`, \`INTRABAR_UNKNOWN\`, \`REJECT\`; para economía necesitar BID/ASK/ticks mismo símbolo y OMS. Para método solo atestiguar fuente causal y rechazar fabricar una entrada.

## 7. CÓDIGO QUE DEBE REUSARSE O PRESERVARSE

**Biblioteca auténtica instalada G3, SOLO LEER (NO EDITAR EN ESTE HANDOFF):**
- \`src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py\` — productor \`VT31CleanroomCognition\` y evaluación \`CognitiveAssessment\`.
- \`src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py\` — frontera OPS, integridad M1 y evidencia.
- \`src/qore/infrastructure/traders/vt31_ict_cleanroom/contracts.py\` — \`CognitiveDecision\`, \`M1Bar\`, \`SessionId\`, \`Side\`.
- \`src/qore/infrastructure/traders/vt31_ict_cleanroom/m1_execution.py\` — ejecución de investigación de M1, **no** fills broker.
- \`tests/infrastructure/test_vt31_ict_cleanroom_cognition.py\`, \`test_vt31_ict_cleanroom_ops.py\`, \`test_vt31_ict_cleanroom_m1_execution.py\`, \`test_vt31_g3_mss_anchor_optin.py\`.

**Módulos RESEARCH verificadores de fuente:**
- #926: \`scripts/vt31_ttrades_am_cognitive_fidelity_witness_20261014.py\`; \`tests/infrastructure/test_vt31_methodology_cognitive_source_fidelity_20261014.py\`.
- #928: \`scripts/vt31_cog_evidence_v2_20261014.py\`; \`tests/infrastructure/test_vt31_cog_evidence_v2_20261014.py\`; workflow \`.github/workflows/vt31-cog-evidence-v2-semantic-gate.yml\`. **Esta es V2 CANÓNICA investigativa**, no la rama experimental de mismo nombre.
- #929: \`scripts/vt31_mc_p2_ttrades_native_h1_evidence_20261014.py\` y sus tests/workflow en ese PR. El comparador \`compare_native_with_existing_cog\` es testigo, no nuevo emisor.
- #927: revisar y recuperar pruebas del **COG REAL** no presentes en #929 (si aplica), sin realizar MERGE no autorizado.

**Integridad G3 a mantener:** \`cognition.py\` Git blob \`d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9\`, \`operations.py\` blob \`0ce9707314aecb71155de8b57044b6ec028847b2\`, acta metodológica blob \`e99c70b4e018d626fb620d9a21b9314a51abc36d\`. Estos son identificadores de blob Git, distintos de SHA de commits; verificar antes de modificar cualquier base.

## 8. PLAN DE EJECUCIÓN ORDENADO PARA EL SIGUIENTE ARQUITECTO

**P0 — Fase A · Asegurar custodia y herencia (PR nuevo; no merge):**
1. Leer este handoff, #926–#929, Issue #727, Issues #897 y #900, G3 #896.
2. Verificar HEAD, base de cada PR y CI verde del commit exacto; comparar blobs originales. Crear rama de investigación desde **HEAD verificado de #929**; no copiar la rama experimental V2 fallida.
3. Mantener matriz de versión/perfil/estado y registrar \`SOURCE_AMBIGUITY\` sin inventar reglas.

**P0 — Fase B · \`ICT_DOL_SOURCE_V1\` para 3 sesiones (mejor siguiente entregable):**
1. Preregistrar construcción **independiente** de pools prior NY cash / Asia / Londres, con intervalos y rollover NY documentados, estado de barrido y cronología del nivel; no confiar en el DOL suministrado por COG.
2. Escribir módulo + tests sintéticos LONG/SHORT, DST, corte de sesión, faltantes, input externo/intrabar, DOL sin existir, nivel ya consumido, timestamp posterior.
3. Comparar con DTO real y V2 por fuente/versión. Resultado \`DOL_PROVENANCE_CONFIRMED/REJECTED/UNKNOWN\`, nunca \`SOURCE_AUTHOR_TRADING_EDGE\`. Ejecutar regresiones existentes.
4. Publicar PR DRAFT, run CI verde, artifact con report hashes, comentario de coordinación #727.

**P0 — Fase C · Cognitiva nativa por perfil y M2/M3:**
1. Desarrollar una **nueva variante de COG por perfil**, con \`TTRADES_NY_AM_2025\` y \`ICT_GENERAL_2023\` separados en contrato; sin editar G3 original. Si se pretende preservar un único trader, que el perfil sea propiedad explícita de la decisión.
2. En TTrades AM, exigir del **testigo nativo** H1 cerrado, sweep, regreso, MSS coherente y objetivo H1 opuesto; COG no puede declararlos por confianza en sí mismo.
3. En ICT general, verificar origen de DOL independiente con el nuevo módulo; documentar qué elemento es doctrina ICT versus QORE operativo.
4. Mantener función de clasificación cognitiva: \`CONFIRMED\` solo con evidencia, \`REJECTED\` ante contradicción, \`UNKNOWN\` ante falta de prueba, **sin sacrificar precisión por densidad deseada**.
5. Ejecutar adversariales de no-trade, contradictorios y replays **metodológicos** sobre M1 existentes, con matriz de falsos positivos/no identificables; no medir/optimizar PnL para declarar conformidad.

**P0 — Fase D · M4 cuatro familias de entrada y M5 salidas:**
1. Para displacement, FVG, OB y breaker: formalización semántica por fuente, aristas causales, zona, entrada propuesta y caducidad; anotar por qué un patrón no constituye fuente; OB/Breaker proxies permanecerán etiquetados hasta revisión fuente.
2. Crear testigo de swing causante del desplazamiento y comparador con stop C2 QORE. Unificar según perfil **sin reescribir la fuente**. SL debe existir as-of, TP DOL trazable; no usar resultados históricos para escoger.
3. Agregar casos de prioridad de múltiples familias, nulo/no-trade, colisión, empate y resolución sin lookahead. Demostrar que **una sola decisión cognitiva** produce intención coherente y OPS evalúa integridad, no sizing.
4. Regresiones completas y informe de cobertura doctrinal con porcentaje de casos \`CONFIRMED/REJECTED/UNKNOWN\` y casos ejemplo, **sin seleccionar solo positivos**.

**P0 — Fase E · M6/M7 CERTIFICACIÓN FINAL SEPARADA:**
1. Elevar a revisión de gobernanza en Issue #897: autorización Owner no suple dos firmas independientes hasta cambio formal de política.
2. Investigar **primero en GitHub/QORE Native** los datos BID/ASK NAS100 broker/símbolo, contrato y fees, sin comprar dataset por defecto. Issue #900 para prueba de disponibilidad real.
3. Una vez método/COG/OPS aceptados y datos listos, construir motor íntegro CE-LIMIT/SL/TP-DOL con ACK, costes y timestamp causal; entonces OOS verdadero y controles de robustez de profit factor/DD, con CIBO/QDLE para lote.
4. Comunicar veredicto con estados \`PASS\`, \`FAIL\`, \`UNKNOWN/UNDERPOWERED\` o \`BLOCKED\`; no presentar certificación económica si M7 no existe.
5. Nunca desplegar ni hacer MERGE automático por concluir el handoff.

## 9. ENTREGABLES Y GATES DE ACEPTACIÓN EXIGIDOS AL PRÓXIMO ARQUITECTO

Antes de reclamar «VT31 certificado por metodología y cognitiva» se exigen todos:
- [ ] Matriz de fuentes y perfiles por las 3 ventanas sin contradicción ni herencia incorrecta de TTrades.
- [ ] \`ICT_DOL_SOURCE_V1\` con niveles causales y refutaciones en fixtures adversariales; origen DOL corroborado independientemente del COG.
- [ ] COG per-profile emisor real y \`COG_EVIDENCE_V2\` emisor/consumidor de testigos, no solo DTO sintéticos; registros as-of reproducibles en M1 reales disponibles.
- [ ] Contrato MSS/shift/displacement por perfil, testigos M1, ejemplos fuente positivos y negativos, \`UNKNOWN\` para ambigüedad que no pueda resolverse.
- [ ] M4 cobertura de displacement/FVG/OB/Breaker con etiquetas \`QORE_PROXY\` cuando corresponda y criterio explícito de no-trade.
- [ ] M5 swing stop/TP/expiración consistentes y separados del sizing CIBO.
- [ ] COG/OPS separados con evidencias/firma válida de acuerdo con gobernanza vigente, sin suplantar revisores.
- [ ] CI del commit exacto, cero lookahead/intrabar forgery críticos, informe de discrepancias semánticas completas (NO borrar los casos que fallen).
- [ ] **M7 se mantiene como certificado económico independiente**, que sólo se concederá con dato broker, fills y OOS; la aprobación M0–M6 no significa rentable.

**Entregables por PR:** prereg, código, tests, workflow verde, artefacto SHA256, matriz de casos clasificados con justificación/DTO/M1, informe M0–M7, comentario #727 y siguiente paso verificable. Nada queda sólo en una respuesta conversacional.

## 10. ESTADO FINAL Y PRÓXIMA ACCIÓN

**Este handoff deja trabajo real ya ejecutado y validado hasta MC-P2 en PR #929, y problemas concretos todavía abiertos.** El siguiente arquitecto debe empezar por **atestador independiente ICT de origen DOL para las tres sesiones**, no por cambiar umbrales para hallar edge, no por ampliar OHLC screens y no por afirmar que un testigo source-only certificó la metodología del autor.

**NO se declara:** VT31 rentable, certificado, con G3 dual signed, con G5 BID/ASK NAS100 exacto completo, con G6/G7 replay ejecutable u operable en LIVE.  
**SÍ se declara:** infraestructura verificable; contraejemplos reales del motor con M1 sintéticas que demuestran un desajuste doctrinal concreto para TTrades; COG_EVIDENCE_V2 e H1 source-native context testados; plan y gates para corregirlo sin contaminar ICT general.

**ORDEN FINAL DE CUSTODIA:** mantener PRs en DRAFT, la pareja G3 intacta, no modificar main, no órdenes, no lotaje propio, no leaks, no usar Fresh Holdout para calibración, publicar toda nueva evidencia en GitHub.

---
**Fin del HANDOFF MAESTRO · VT31 · 2026-10-14.**

# VT31 — Dictamen cognitivo y metodológico: DOL TTrades por fuente vs G3 MIN10

**2026-10-15. Owner: método y cognitiva, no trading cuantitativo.** Nuevo avance: en un módulo versionado de INVESTIGACIÓN, y SIN MODIFICAR COG original G3, el método TTrades NY AM ya puede definir causalmente DOL opuesto H1 09 tras un MSS auténtico de G3, verificarlo con testigo independiente V2 y abstenerse cuando conflicto de reglas G3 10 puntos imposibilita simultánea conformidad. Esto es un paso concreto hacia coherencia metodológica, no es certificación de trader.

## Fuente, prereg y evidencia
- Primaria [TTrades AM Silver Bullet NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/), 19-JUN-2025: 10–11 New York, H1 09–10, barrido/retorno/desplazamiento, target siempre lado opuesto 09h, cuatro familias entry (displacement, FVG, OB, breaker) y stop más allá swing causante. **No dice** que TTrades exija mínimo 10 pt; 10 pt es CONTRATO QORE G3.
- Prereg ANTES del código commit `39d64d80c9090dd2d1dd97be6003084b75f1eb1f`, documento `docs/research/VT31_PROFILE_TTRADES_SOURCE_FIRST_COG_ADAPTER_MIN10_PREREG_2026-10-15.md`.
- [PR #956 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/956), [CI #38709608789 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38709608789), commit EXACTO de código/todos los tests `668d492fb74f0625e15dd05a7069643a571a1a26`, **58/58 pytest PASS**, Ruff/Python compile/hash locks G3 PASS.
- [Artifact #11959393863](https://github.com/mezas3238-hue/qore-core/actions/runs/38709608789/artifacts/11959393863) ZIP SHA256 `05b834475801822e339d21665736f3f78a4e4dbf4c266f50be7ece3f8662dcbf` incluye 8 casos JSON source-first (EST/EDT), contrafactuales negativos, JUnit/tests/summary y SHA256SUMS.
- La primera CI #38709514179 falló solamente Ruff E501 un string, corregido sin alterar reglas ni velas. Original G3 COG `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, OPS `0ce9707314aecb71155de8b57044b6ec028847b2` y acta G3 `e99c70b4e018d626fb620d9a21b9314a51abc36d` intactos.

## La solución QUALITATIVA source-first en versión nueva
Función research `ttrades_source_first_g3_cognitive_proposal` con perfil declarado `TTRADES_NY_AM_2025`, hora NY_AM, todos los M1 cerrados al as-of, **y no se integra a OPS ni decide lotes**:
1. Testigo original TTrades H1 09 completo, primer raid válido 10–11 y regreso fuente as-of. Falta/barrido doble → WAIT, no inventar lado.
2. Ejecuta el **COG G3 ORIGINAL** con `G3_MSS_FRAMEWORK_POLICY`, preserva pivote MSS, as-of, lado, ancla y origen. Si falla MSS genuino o difiere de lado fuente → WAIT/REJECT.
3. Calcula SOLO DOL H1 opuesto de TTrades. Si distancia lado × (DOL_source − MSS_close) es menor a `MIN_INDEX_POINTS=10`, el contrato G3 no admite simultáneamente ese método: WAIT `G3_MIN10_AND_TTRADES_SOURCE_TARGET_CONFLICT_WAIT`. **No cambia DOL del autor ni elimina MIN10 para lograr aprobación.**
4. Si distancia alcanza 10 pt, genera un **NUEVO DTO de versión de investigación** con linaje `QORE_RESEARCH_TTRADES_AM_SOURCE_BOUND_09H_OPPOSITE|ORIGINAL_G3_MSS_PASSTHROUGH` y verifica con `inspect_cog_evidence(TTRADES_AM)`, que responde `CONFIRMED` solo al CONTEXTO M1 fuente. No representa salida literal del COG ORIGINAL, ni firma ni entrada/stop certificada.

## Escenarios espejo previamente fijados
| Dirección / estación | DOL H1 TTrades | MSS close | Distancia | Dictamen de método / G3 |
|---|---:|---:|---:|---|
| LONG enero y julio, H1 HIGH110 / G3 original cash HIGH150 | 110 | 105 | 5 pt | **WAIT por conflicto G3 MIN10** |
| LONG enero y julio, H1 HIGH120 / G3 original cash HIGH150 | 120 | 105 | 15 pt | **Propuesta research, fuente TTrades CONTEXT_CONFIRMADO** |
| SHORT enero y julio, H1 LOW90 / G3 original cash LOW80 | 90 | 94 | 4 pt | **WAIT por conflicto G3 MIN10** |
| SHORT enero y julio, H1 LOW80 / G3 original cash LOW60 | 80 | 94 | 14 pt | **Propuesta research, fuente TTrades CONTEXT_CONFIRMADO** |

**4 resultados CONTEXT_CONFORMANT (2 long/2 short)** + **4 decisiones justificadas WAIT por incompatibilidad de reglamento**, sin indicadores económicos. Adversariales: no barrido, barrido alto/bajo misma M1, H1 incompleto, MSS no confirmado, futuro en M1, perfil inválido, hora Londres. Todos cierran sin DTO fuente certificado cuando no corresponde.

## Evaluación por dimensión, la palabra CONFIRMED no significa CERTIFIED
- Metodología **M0 identidad TTrades + M2 DOL + M3 MSS proxy**: en este research, contrastada en escenarios M1 causales y V2 independiente; parcialmente conforme con fuente en cronología/target, no homologada en las cuatro familias OB/Breaker/FVG/desplazamiento ni swing stop.
- Cognitiva: COG original produce MSS válido en LONG/SHORT; el módulo externo READ-ONLY propone DOL autoral y se abstiene en conflicto. **La adaptación no es conducta NATIVA del COG G3 ORIGINAL**, ni tiene su firma. No atribuirle certificación cognitiva operativa.
- G3 MIN10 vs objetivo TTrades: **conflicto explícito NO RESUELTO para 4 casos**. No se puede certificar política única plena sin decidir regla de compatibilidad antes del procedimiento; la abstención es correcta bajo política mixta QORE.
- `CERTIFICADO_METODOLOGIA=PENDIENTE`, `CERTIFICADO_COGNITIVA=PENDIENTE`; validaciones humanas y dos firmantes COG/OPS independientes [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) SIGUEN AUSENTES al comprobar issue en esta ronda (open, una autorización administrativa, no firmas).
- `TraderLab L1–L10` economía para eventual DEMO sigue expediente distinto y no establece estos certificados de conocimiento. No derivar PnL de un source-context matched.

## Bloqueadores y siguiente acción, sin reensayar retornos
1. **Identidad final:** determinar formalmente perfil del VT31 NY AM en la metodología certificada (`ICT_GENERAL/QORE` o `TTRADES_NY_AM_2025`; si ambos, selector inequívoco previo a decisión). Un único VT31 puede incluir dos subperfiles, nunca atribuir fuente que no cumple.
2. **Compatibilidad del 10 pt QORE**: documentar si el perfil TTrades permite legítimamente WAIT cuando autor DOL <10 G3 sin modificar fuente; el objetivo TTrades sigue opuesto H1, nunca otra pool.
3. **M4/M5 autorales**: obtener ejemplos primarios para FVG/OB/Breaker y el swing del desplazamiento; codificar solo reglas definidas sin inferir autor a partir de pivote QORE, incluyendo orden intrabar incierto y zonas de invalidación. Fallas #943/#945 permanecen.
4. **Cognitiva nativa**: integrar solo con versión G3 revisada por arquitecto COG independiente y OPS distinto, firmada sobre SHAs exactos; mientras tanto investigación fuente-first desconectada de operativa, cero órdenes/OMS y cero lotaje propio Trader (CIBO CMA).

**No MERGE/main, no LIVE/producción, no FundedNext LIVE, no VPS, no permisos de ejecución.** Este informe posterior al commit de CI no reclama que el texto esté incluido en el SHA probado.
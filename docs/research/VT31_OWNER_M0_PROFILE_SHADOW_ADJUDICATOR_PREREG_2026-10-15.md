# VT31 — PRE-REGISTRO: frontera metodológica y cognitiva por perfil, COG G3 ORIGINAL

Fecha 15-OCT-2026. PRE-CÓDIGO / PRE-CI. Owner: VT31 se certifica por METODOLOGÍA y COGNITIVA, no por resultados económicos ni número de trades. Este trabajo aporta una **frontera de atribución de fuente** en una auditoría independiente, nunca modifica/admite operaciones desde G3 ni convierte la CI en certificado.

## Objetivo doctrinal
El PR #950 demostró en M1 sintético causal un COG original NY AM LONG→DOL 150 (prior NY CASH) mientras el perfil TTrades NY AM 2025 requiere DOL HIGH 09h=110 tras el low raid. El COG general no está necesariamente equivocado bajo ICT_GENERAL_2023; atribuirlo simultáneamente a TTrades sería equivocado. Esta prueba fija las responsabilidades del selector externo **antes** de observar resultado económico y prohíbe prestar una decisión de un perfil a otro.

## Contrato de sombra, NO autoridad de trading
Entrada (1) enum **perfil declarado** `ICT_GENERAL_2023` o `TTRADES_NY_AM_2025`, (2) `SessionId` explícita y horario cerrado M1 as-of, (3) historial M1 con cierra <= as_of, (4) `CognitiveAssessment` AUTÉNTICO de `VT31CleanroomCognition`, nunca DTO externo elegido por el auditor. Salida tiene `assessment_state`, `decision_as_of`, `observed_side/DOL/source`, `profile_fidelity` y razones, `allow_method_cognitive_certification=false`, `orders=0`, `sizing=0`.

**Reglas inmutables de clasificación**:
1. Perfil desconocido -> `ValueError`, perfil TTrades fuera de NY AM -> `PROFILE_SESSION_REJECTED`. La sesión Londres/NY PM bajo ICT_GENERAL NO requiere H1 09–10; tampoco se declara autoralmente certificada.
2. Sin `CognitiveDecision` auténtico -> `COG_ABSTAINED` (no inventar lado/DOL); `CognitiveAssessment.session/as_of` y bar cierre deben coincidir; información futura/orden fuera de rango causa `INPUT_INVALID_REJECTED` sin tocar el COG.
3. Bajo `ICT_GENERAL_2023` con COG real coherente temporalmente, el `inspect_cog_evidence(profile=ICT_GENERAL)` reporta `UNKNOWN` por `ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED`, por tanto `ICT_CONTEXT_WITNESS_UNDERDETERMINED`; nunca traducir ese UNKNOWN a pass TTrades, ni exigir TTrades 09h.
4. Bajo `TTRADES_NY_AM_2025`, usar `native_ttrades_am_context` del mismo H1 09 completo y 10 M1 cerrado al as-of, más `inspect_cog_evidence(TTRADES_AM)` independiente sobre mismo snapshot; si Rejected -> `TTRADES_PROFILE_SOURCE_REJECTED` con motivos; si UNKNOWN -> `TTRADES_PROFILE_SOURCE_UNKNOWN`; si CONFIRMED -> `TTRADES_CONTEXT_MATCH_ONLY`, no certificación total de OB/Breaker/swing fuente autoral.
5. Ninguna clasificación devuelve solicitud de orden, fake fill, sizing, riesgo o certificado. COG, G3 y OPS originales intocados y locked by Git blob; el nuevo script solo documenta divergencias por perfil. No es una función de habilitación operativa real.

## Casos registrados ex ante
- G3 original NY AM #950 con LOW sweep H1 09=90, HIGH H1 09=110, MSS cierre 105, COG elige 150: TTrades -> `TTRADES_PROFILE_SOURCE_REJECTED`, código `DOL_NOT_OPPOSITE_9AM_H1_EXTREME`; exactamente mismos hechos y COG declarado como ICT_GENERAL -> `ICT_CONTEXT_WITNESS_UNDERDETERMINED` sin veto 09h.
- G3 original London #948 con DOL previo 150 -> ICT_GENERAL `ICT_CONTEXT_WITNESS_UNDERDETERMINED` (bien que 09h no exista), TTrades -> `PROFILE_SESSION_REJECTED`.
- Fuente 09h incompleta / no sweep -> no elevar a TTrades si no hay testigo H1; citar rechazo o UNKNOWN según fuente independiente, no convertir `NO_PRIOR_9AM_H1_SWEEP` en LONG.
- COG `as_of` y source `history[-1].closed_at` discordantes -> rechazo, no inspección retrospectiva; `CognitiveDecision` de sesión distinta -> rechazo; política desconocida -> ValueError.
- Fuente TTrades validada por COG de investigación #946 NO es COG G3 original: es material de investigación distinto y no admite certificado de autonomía de COG real. Test de no certificación hasta firma humana.

## Límites
Sin PnL, PF/DD/Sharpe, real NAS100 3Y, BID/ASK, OOS, sizing trader, CIBO, OMS, LIVE, FundedNext LIVE, VPS o merge. M0–M6 auditables por juicio independiente, con metodología y cognitiva `PENDING`, y G3 #897 sin dos firmas. CI y logs son evidencia de consistencia del oráculo metodológico de sombra, no autocertificación.
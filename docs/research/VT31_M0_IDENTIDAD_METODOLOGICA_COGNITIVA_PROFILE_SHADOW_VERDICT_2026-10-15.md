# VT31 — Dictamen M0: identidad metodológica de COG original (ICT GENERAL ≠ TTrades AM)

**2026-10-15 · Auditoría cualitativa/criterio cognitivo, no evaluación cuantitativa.** Owner: certificar VT31 por metodología y cognitiva. No se revisó PnL, densidad de trades, DD, PF, Sharpe, Sortino ni OOS. El entregable es una **frontera de atribución de fuente RESEARCH READ-ONLY** y no un router operativo, condición de ejecución o certificado.

## Versiones y ejecución
- Repositorio soberano `mezas3238-hue/qore-core`, [PR #951 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/951), basado en PR #950 (hallazgo NY AM DOL).
- Pre-registro ANTERIOR al código y cualquier prueba: commit `9ca7c4a4dd1aa3180788a682b174aee605a2eda4`, documento `docs/research/VT31_OWNER_M0_PROFILE_SHADOW_ADJUDICATOR_PREREG_2026-10-15.md`.
- **[CI #38706697043 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38706697043)**, commit de código exacto `67299f24201a4930a37d1c2fb9888d4cc00e12c1`, **80/80 pytest PASS**, Ruff PASS, Python compile PASS, SHA-1 blobs originales COG/OPS/G3 PASS.
- [Artifact #11958388150](https://github.com/mezas3238-hue/qore-core/actions/runs/38706697043/artifacts/11958388150), ZIP SHA256 `78ad2ba7c53790a6c9119f4e831c6683f3f502aee10aa729dc800dd16784ca0e`, JSON de expediente, resumen, JUnit, SHA256SUMS.
- Código nuevo `scripts/vt31_m0_profile_shadow_attestation_20261015.py`, pruebas `tests/infrastructure/test_vt31_m0_profile_shadow_attestation_20261015.py`, CI `.github/workflows/vt31-m0-method-cog-profile-shadow.yml`. NO se editó `src/qore/infrastructure/traders/vt31_ict_cleanroom/{cognition,operations}.py` ni G3 acta.

## Acta de decisiones del COG ORIGINAL, mismos hechos y distinta doctrina
| Caso | Perfil declarado | Decisión de sombra | Causa o limitación |
|---|---|---|---|
| NY AM (M1 original sintético, DOL COG 150 / fuente TTrades H1 110) | TTRADES_NY_AM_2025 | **TTRADES_PROFILE_SOURCE_REJECTED** | `DOL_NOT_OPPOSITE_9AM_H1_EXTREME`: LONG de COG G3 no replica el objetivo prescrito por TTrades AM |
| Exactamente la MISMA salida de COG y cronología | ICT_GENERAL_2023 | **ICT_CONTEXT_WITNESS_UNDERDETERMINED** | No atribuir regla de 09h de TTrades a ICT general, pero falta testigo autónomo de procedencia contextual ICT completo |
| Original COG Londres LONG, DOL anterior 150 | ICT_GENERAL_2023 | **ICT_CONTEXT_WITNESS_UNDERDETERMINED** | H1 09h TTrades NO universal en Londres; falta revisión de fuente ICT |
| MISMA salida Londres clasificada como TTrades AM | TTRADES_NY_AM_2025 | **PROFILE_SESSION_REJECTED** | `TTRADES_ONLY_NY_AM` (Londres no es perfil AM NQ) |

El verificador V2 de ICT GENERAL actualmente etiqueta `ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED`; **ese UNKNOWN no es aprobación ni rechazo general**. Esta distinción es la principal barrera contra falsas certificaciones. Incluso una eventual coincidencia DOL=TTrades H1 sería únicamente `TTRADES_CONTEXT_MATCH_ONLY`, no certificado de FVG, OB, Breaker, stops ni COG integral.

## Juicios adversariales adicionales
- PERFIL NO declarado/mal escrito → excepción estricta; jamás elegir método por precio o resultado económico.
- COG que produce legítimo `WAIT` sin MSS → `COG_ABSTAINED`; no generar un LONG ficticio ni penalizar buena abstención.
- Manipular `as_of`, agregar M1 futura o presentar sesión distinta entre input y assessment → `INPUT_INVALID_REJECTED`, sin ejecutar una evaluación retroactiva.
- Mismo `CognitiveAssessment` AUTÉNTICO del COG original es juzgado una vez bajo cada perfil; la auditoría no crea su propio `CognitiveDecision` ni cambia código productor para satisfacer la fuente.
- `method_certified=false`, `cognition_certified=false`, `orders_or_sizing=0`, `live_authorized=false` en cada caso. Sin CIBO CMA, OMS, broker, QDLE ni cuentas.

## Certificados separados — situación real
**METODOLOGÍA PENDIENTE M0:** aún NO existe selector de perfil aprobado y conectado causalmente al COG original; el script es un CONTROL DE SOMBRA, no un veto de señales dentro de la app, y sin orden no debe convertirse en uno por su cuenta. Hay desacuerdo concreto en NY AM TTrades y falta definición verificable autoral de OB/Breaker/swing stop (PR #943/#945). Falta verificación fuente ICT GENERAL por sesión.
**COGNITIVA PENDIENTE:** COG G3 original mostró decisión/memoria/WAIT correctos en Londres #948 y en NY AM #950 mostró una LONG causal según QORE que NO correspondía al destino TTrades. Evaluar NY PM, escenarios espejo SHORT en COG original, transición de sesiones/identidad, cambio de única M1, razones `CognitiveTelemetry`, contradicciones y casos autorales positivos/negativos. CI verde demuestra únicamente que el adjudicador clasifica adecuadamente escenarios específicos.
**Gobernanza:** Issue #897 necesita firmas genuinas independientes de COG/OPS para acta y versión exacta; no construir una firma por un bot ni promover L1, M6, L2–L10, DEMO o LIVE.

## Handoff / tareas P0 concretas
1. Diseñar y preregistrar **M0 selector declarativo real de perfil** separado y explícito, con valor predeterminado de rechazo si no se decide perfil, SIN sustituir decisiones del COG ni permitir órdenes. Se requiere decisión Owner sobre identidad `ICT_GENERAL_2023/QORE` versus `TTRADES_NY_AM_2025`, o perfiles explícitos coexistentes de un mismo VT31 y sus contratos.
2. Para el COG G3 ORIGINAL, registrar NEW YORK PM as-of y contrafactuales LONG/SHORT (pruebas semánticas); no usar el detector de investigación `propose_ttrades_am_cognition` como si fuera runtime.
3. Definir fuentes y juicio cualitativo de MSS/OB/Breaker y SL swing vs C2 a partir de ejemplos primarios, revisar independiente por arquitecto metodológico y cognitivo.
4. Emitir dos dictámenes humanos por separado (METODOLOGÍA / COGNITIVA) con SHA y escenario firmado, nunca por PF/DD/Sharpe. La economía permanece en un expediente aparte de elegibilidad DEMO.

**Sin MERGE · sin operaciones · sin LIVE/PRODUCCIÓN · sin VPS/FundedNext LIVE · sin sizing propio del Trader (CIBO CMA autoridad).** Este documento se creó después del commit de código verificado por CI; la CI citada no equivale a afirmar ejecución de este nuevo texto.
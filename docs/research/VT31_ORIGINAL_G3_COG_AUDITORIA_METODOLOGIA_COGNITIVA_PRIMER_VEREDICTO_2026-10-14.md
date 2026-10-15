# VT31 — Dictamen cualitativo del COG ORIGINAL G3 (comportamiento, memoria y abstención)

**14-OCT-2026 / Evidencia técnica; no certificación definitiva.** Mandato Owner: **METODOLOGÍA + COGNITIVA**. PF, DD, Sharpe, Sortino, retornos, densidad y sizing están explícitamente fuera del criterio de aprobación de estas dos dimensiones. Código de referencia: `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py::VT31CleanroomCognition` ORIGINAL, no sustituto experimental TTrades.

## Evidencia realmente ejecutada
- PR #948 DRAFT: https://github.com/mezas3238-hue/qore-core/pull/948, desde #946. Prereg antes de código commit `d5a783d7bf4b7ffe4c91b9feffabdf53146a962c` archivo docs/research/VT31_ORIGINAL_G3_COG_QUALITATIVE_ADVERSARIAL_PREREG_2026-10-14.md.
- [CI SUCCESS #38671368366](https://github.com/mezas3238-hue/qore-core/actions/runs/38671368366), código/test exacto `274c4b2b29063d20e565f7f740e71887176f8fd9`, **66/66** pruebas pasadas, Ruff PASS, py_compile PASS, G3 COG/OPS/acta SHAs congelados y verificados. El intento previo #38671204732 falló solo Ruff import style; #38671260662 SUCCESS 65 pruebas; después se corrigió el metadato de horario de evaluación en dos abstenciones y se incorporó su test, **66/66 SUCCESS**. No se cambió ni una regla del COG original.
- [Artifact #11944328096](https://github.com/mezas3238-hue/qore-core/actions/runs/38671368366/artifacts/11944328096), SHA256 ZIP `05710d9ab11c598fbfc57718f6e5a7fe18ebcc02564443cd4831c0eef925a272`. JSON 10 escenarios con decisiones auténticas `CognitiveAssessment`/`CognitiveDecision` y `as_of` propio por escenario, JUnit, summary, scope, SHA256SUMS.
- Perfil evaluado: **ICT_GENERAL_2023 LONDON** con decisiones QORE G3, contextos M1 sintéticos controlados. **No se le impone requisito TTrades NY 09h**. NO 3Y mercado ni fresh holdout. NO órdenes, fills, balances, comisiones o datos económicos.

## Interrogatorio del COG original: acción observada y regla cognitiva
| Escenario original, entrada M1 cerrada | Acción del ORIGINAL COG | Evaluación del comportamiento, no del método autoral |
|---|---|---|
| Tesis Londres: DOL de NY cash anterior HIGH=150, swing MSS=105, cierre de desplazamiento=107 | **LONG** | Lectura causal y plan estructural confirmados en el escenario |
| Volver a pedir juicio al mismo `as_of` sin nueva vela | **LONG**, mismo destino | Memoria estable, no selección de un nuevo DOL por resultados |
| Eliminar NY cash anterior; pools contemporáneos ya consumidos | **WAIT** | No inventa liquidez y no emite tesis |
| Detener serie antes de la vela M1 que confirma MSS | **WAIT** | Pivote no roto, prudencia correcta |
| Preservar liquidez previa pero quitar HTF contemporáneo 00–03 NY | **WAIT** | No sustituye H1/M15 frescos por barras de viernes |
| Agregar M1 que toca HIGH=152 consumiendo DOL=150 | **WAIT** | Revoca tesis cuyo objetivo ya fue mitigado |
| Agregar M1 con cierre 102 bajo pivote confirmado 105 | **WAIT** | Revoca desplazamiento y tesis cognitiva persistida |
| Alimentar una vela adicional e intentar revaluar `as_of` anterior | **REJECT** | No acepta pedir pasado con conocimiento futuro |
| Mismo productor real con `G3_MSS_FRAMEWORK_POLICY` opt-in | **LONG**, ancla=107 | Valida que toma cierre exacto del MSS M1, no FVG C3 futuro |
| Primer caso Londres, clasificación de fuente | **LONG** | ICT GENERAL London ≠ prueba de fidelidad TTrades NY AM |

**Punto crítico:** El sistema responde a pruebas sintéticas que incluyen el nivel destino 150 y vela MSS 105 en su fuente M1, **no interpreta una descripción en lenguaje natural** ni prueba por sí solo comprensión ICT profunda. La etiqueta de COG autor-certificado y metodología autor-certificada permanece FALSE. Los tests validan juicio operacional implementado; falta criterio humano con fuentes originales y casos verdaderamente adversariales más completos.

## Diagnóstico de certificación separado

**METODOLOGÍA: PENDIENTE.** Identidad de perfiles ICT general vs TTrades 2025 debe ser objeto de una matriz de fuentes y correspondencia de setups. MSS 1.25x/mediana 5, selección automática de DOL más cercano, stop C2 en G3 y breaker proxy de cuatro piernas no tienen acreditación autoral universal. Probar si constituyen **formalización QORE coherente** sin mentir sobre fidelidad ICT/TTrades. M4 OB/Breaker, invalidación, plan SL/TP necesitan casos fuente positivos+negativos. PR #943 C2 vs swing y PR #945 4-leg sólo son pruebas de investigación.

**COGNITIVA: PENDIENTE, CON TESTIGOS DE ABSTENCIÓN APROBADOS PARA LONDRES.** El COG ORIGINAL demuestra memoria causal y WAIT en los casos enumerados; faltan escenarios del COG mismo para NY AM y NY PM, transición de sesiones, falsos MSS, DOL de origen conflictivo, vela de FVG ambigua, instrucción WAIT por falta de conocimiento, y explicación cognitiva de por qué se eligió cada fuente. Revisar trazas nativas `CognitiveTelemetry` además de DTO, no usar datos del futuro ni PnL.

**Gobernanza independiente:** Issue #897 sigue exigiendo 2 firmas reales COG/OPS sobre SHA de método y código exactos. CI automática no equivale a revisión humana. Registrar las firmas auténticas solo tras juicio de source/procedimiento; no promover a un estado de certificación formal ni activar órdenes.

**Trader Lab L1–L10 económico:** expediente separado para DEMO, ajeno al criterio de estos certificados de conocimiento, sin suprimir obligaciones futuras si se desea DEMO. La identidad DRAFT #939 no es la cognitiva certificada.

## Acciones precisas para siguiente arquitecto
1. Crear escenarios originales del **mismo `VT31CleanroomCognition`** NY AM y NY PM (no cambiarlo por `propose_ttrades_am_cognition`), probar la diferencia NY AM TTrades: high/low H1 09 y prioridad DOL. Probar la fuente ICT General en esas ventanas por separado.
2. Evaluar con evidencia exacta por qué el COG aceptó o negó cada caso. Contrafactual que cambie una sola M1, manteniendo todas las demás; exigir cambio de decisión sólo cuando cambia causa. Validar `CognitiveTelemetry` state as-of.
3. Preparar corpus autoral con casos positivos/negativos de MSS/FVG/OB/Breaker y SL conceptual; identificar formalizaciones QORE vs doctrina autoral. No usar métricas económicas ni densidad.
4. Pedir revisión humana independiente COG/OPS del SHA del expediente junto a G3 y emitir **dos actas separadas** CERTIFICADO_METODOLOGIA y CERTIFICADO_COGNITIVA solo tras cerrar M0–M6 sin falsedad.

**NO MERGE · NO LIVE/PRODUCCIÓN · NO VPS · NO FundedNext LIVE · NO broker órdenes/OMS · NO sizing del trader.** El documento de esta sección se publicó tras la CI; se identifica el SHA exacto ya probado en lugar de atribuir verde a un HEAD de documentación posterior.
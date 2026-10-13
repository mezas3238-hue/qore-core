# VT31 — G3 r1.2 dual MIN_INDEX_POINTS versioning: independent causal code gate (PRE-SIGNATURE)

**Fecha:** 2026-10-12 NY / 2026-10-13 UTC, **auditoría técnica de G3**. **Estado:** `CODE_REVIEW_DRAFT_UNSIGNED`. Fuente de doctrina revisada: [PR #881, acta G3 r1.2, commit b4042c568aac59e0e18bc2003d278a47612dce5a](https://github.com/mezas3238-hue/qore-core/blob/b4042c568aac59e0e18bc2003d278a47612dce5a/docs/research/VT31_G3_DECISION_METODOLOGICA_STOP_FRAMEWORK_FVG_EXIT_V1_2026-10-12.md).

**NO cambia estrategia LIVE ni habilita replay económico.** Esta rama deriva exactamente del commit G3 r1.2 y modifica sólo tres módulos source del **cleanroom en rama research**, fixture unitario, CI y este informe. No modifica `main`, PR #881, VPS, trader antiguo, historiales o Fresh Holdout. Los 2.140 A/B históricos y sus 51/619 UNKNOWN conservan identidad y resultados; los cambios no constituyen un backtest.

## Hallazgo verificado en código b4042c5

**Dos puertas de 10 puntos**: `cognition.py::VT31CleanroomCognition.assess` selecciona el DOL con `p.level >= last.close+10` (LONG) o `<= last.close−10` (SHORT). `operations.py::IctSilverBulletOperations.on_closed_m1` rechaza FVG si `DOL − current.close(C3) <10` direccional. La puerta en OPS consume una **ancla distinta de la convenida en G3**, alterando elegibilidad; cambiar OPS sin controlar COG haría insegura la identidad de la cohorte.

**Matiz demostrado por inspección de control de flujo:** COG sólo ejecuta su filtro de nuevos draws dentro de `if not missing and shift is not None`, donde `_index.shift()` fue confirmado sobre el *último* M1 cerrado; por tanto `last.close` allí **coincide de hecho con el cierre MSS en ese instante**, no con un C3 arbitrario. Su problema no es necesariamente un valor inicial incorrecto, sino que **el ancla no se versionaba ni se conservaba como testigo causal para COG→OPS en posteriores revalidaciones**. OPS sí usaba otro cierre: el de C3. No se infiere equivalencia si las M1 no están causalmente reconciliadas.

## Contrato codificado, activación sólo futura tras firma

`contracts.py` declara IDs inmutables `LEGACY_C3_CLOSE_SOURCE_V0` (valor por defecto) y `QORE_G3_MSS_CLOSE_V1_PROPOSED` (OPCIÓN DE INVESTIGACIÓN, **NO APROBADA**). En `CognitiveDecision` se adicionan de forma opcional `mss_anchor_close` y `framework_policy`. Instancias antiguas conservan el modo fuente por defecto; en G3 falta de `mss_anchor_close` hace FAIL. Se rechazan nombres de política no previstos y testigo G3 inyectado dentro del contrato legado.

`cognition.py` incorpora `framework_policy` opcional al constructor. Para un MSS recién probado, ancla `mss_anchor_close=last.close` **únicamente** si `last.closed_at == shift.break_confirmed_at`, emite versión cognitiva distinta y el ID de política; la distancia DOL se calcula contra **esa ancla explícita**. La continuación de la misma tesis en otro M1 con DOL/pivote todavía válidos preserva el precio MSS y el timestamp mediante `dataclasses.replace` del objeto original: **no cambia a last.close de la revalidación**. El modo anterior sigue siendo default.

`operations.py` incorpora `framework_policy` opcional al constructor. Observa y conserva los closes M1 realmente consumidos en esa ventana; cuando recibe la decisión V1 exige **mismo policy ID**, testigo de COG no nulo, registro exacto de `structure_break_confirmed_at` y coincidencia del valor `mss_anchor_close` contra SU PROPIO bar cerrado con ese timestamp. Si COG inventa un nivel, cita un MSS no observado o mezcla V1 con un OPS legado, la llamada falla `ValueError`, no se crea candidato. OPS G3 usa **DOL−MSS_close** (LONG) o **MSS_close−DOL** (SHORT) como única puerta de 10pt; mantiene por separado pruebas de dirección, geometría FVG/CE y DOL favorable. El modo anterior sigue evaluando contra `close(C3)`.

**Límite de esta validación:** la versión nueva conserva los requisitos causales de MSS que emite la cog original. OPS sólo contrasta el **precio y el tiempo** MSS con su propio registro M1; para certificar geometría estructural independiente deberá verificarse el breakout en el replay integrado. Tampoco añade política C2/limit/OMS: esos son otros gates G3 no firmados.

## CI verificable

- **[GitHub Actions #38327107567 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38327107567)**, HEAD code/test `5475b295b6865bf248e59271d5a1c16907fc6795`, **38/38 tests** (unidad nueva + test suites de COG/OPS anteriores), Ruff y `py_compile` PASS; artefacto **11780739795** (manifest SHA256 con acta origen y código testado).
- Run inicial **#38327065862 FAIL** sólo por orden de imports Ruff `I001` en archivos nuevos; corregido y repetido en el run verde, sin cambiar lógica de la puerta.
- Pruebas de frontera: LONG con C3 rechazado pero MSS aprobado; LONG con C3 aprobado pero MSS rechazado; SHORT MSS aprobado/C3 rechazado; testigo MSS adulterado; MSS timestamp sin M1 observable; COG V1 no alimenta OPS legacy ni viceversa; falta de mss_close; políticas inventadas; retención de cierre MSS tras COG revalidado con cierre posterior más cercano al DOL; MSS falso con timecode incongruente y checks legacy previos.
- **CERO casos del histórico V1/B recalculados**, ningún PF/DD/net expectancy, no broker fills, no tick Bid/Ask, Fresh Holdout SELLADO.

## Para obtener firmas sin confundir documento y código

| Pregunta | Prueba/decisión que debe firmarse | Responsable | Estado |
|---|---|---|---|
| ¿Correcto ancla `close(MSS_M1)` estrictamente as-of y revalidación sin sobreescritura? | Código COG, contrato DTO, test de cambio C3 vs MSS | **COG** | **PENDIENTE** |
| ¿OPS rechaza ancla falsa/ausente y usa MSS en ambas direcciones? | Código OPS y pruebas de discrepancia / falla cerrada | **OPS** | **PENDIENTE** |
| ¿Modelo C2+1 tick >=2 ticks, CE-limit, DOL, hora NY, primer FVG, vida de órdenes y 15:55 cumple G3? | **NO IMPLEMENTADO / NO AUTORIZADO por este commit**; el acta b4042c5 sí declara la intención metodológica | **Ambos** | **PENDIENTE** |
| ¿Contrato/broker/ticks/ACK y costes permiten PnL? | **NO**; fuente real no presente | **OPS+Datos** | **BLOQUEADO** |

**Firmas SHA específicas:** `b4042c568aac59e0e18bc2003d278a47612dce5a` es el texto normativo actual del acta G3 y sigue DRAFT. Este **nuevo PR** será el diff técnico a inspeccionar; **su propio HEAD SHA será distinto**. No se puede decir que dos firmas al SHA del texto certifiquen automáticamente el código construido después. Solicitar dos aprobaciones explícitas con referencias a **AMBOS SHA**, o una nueva acta/manifest firmado que contenga G3 SHA + commit del código congelado; cualquier cambio adicional de reglas después invalida esas firmas para la nueva versión. Comentarios de revisión sin `APROBAR` no equivalen a dos firmas. Mantener **`NO_MERGE_TO_MAIN` y `NO_REPLAY`** mientras cualquiera de estos gates siga pendiente.

**Siguiente arquitectura aprobable:** una vez firmada G3 r1.2, completar en carril separado integración opt-in COG/OPS a un runner científico V1 completo con políticas de C2, contrato broker, selección primer FVG, expiración y salida definida; alinear manifiesto de código/acta y repetir tests exhaustivos ANTES de cualquier fuente 3Y development, sin reutilizar los 2.140 IDs como cohorte de V1. Sólo con Bid/Ask y evidencia OMS, costes reales y protocolo económico podrá emitirse edge, jamás con esta prueba de contratos.

**Fuentes:** G3 [#881](https://github.com/mezas3238-hue/qore-core/pull/881), B histórico [#879](https://github.com/mezas3238-hue/qore-core/pull/879), Issue de coordinación [#727](https://github.com/mezas3238-hue/qore-core/issues/727).

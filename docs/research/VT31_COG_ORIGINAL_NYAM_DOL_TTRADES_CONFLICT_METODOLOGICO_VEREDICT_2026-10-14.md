# VT31 — DICTAMEN: COG G3 ORIGINAL contra metodología TTrades NY AM (DOL)

**14-OCT-2026 · METODOLOGÍA Y COGNITIVA, NO CUANTITATIVA.** Se demuestra una divergencia verificable de **identidad metodológica** del COG original de VT31 cuando se le atribuye el perfil TTrades NY AM 2025. La demostración NO descalifica por sí sola la metodología general ICT 2023 ni certifica trader/edge.

## Fuente primaria y caso preregistrado
- [TTrades AM Silver Bullet NQ, 19-JUN-2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) fija NY 10:00–11:00, rango 09h 09:00–10:00, primer barrido LOW ⇒ LONG al lado opuesto 09h HIGH y HIGH ⇒ SHORT al lado opuesto 09h LOW.
- [ICT Silver Bullet 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4) admite DOL contextual propio en varios horarios y **NO** prescribe como universal que todo NY AM deba tomar el lado opuesto del H1 09h. Diferenciar perfiles es obligatorio.
- Prereg ANTES del nuevo script/ensayo commit `6ed6fb5e43d86b1457766a701a49f07b4f06ea88`, doc docs/research/VT31_ORIGINAL_COG_TTRADES_NY_AM_DOL_SOURCE_CONFLICT_PREREG_2026-10-14.md.
- Caso **sintético, M1 cerrado, no PnL**. Viernes previo sesión NY cash completa: high 150. Lunes durante 09h 60 M1 rango high 110/low 90. Primera vela de barrido 10:01 alcanza 89; cierre 10:02 vuelve dentro del 09h con desplazamiento LONG y MSS proxy de pivote 104, referencia close 105, observado 10:03 NY. Todos los hechos están disponibles antes de cualquier decisión. No se inspeccionó 3Y real ni se buscaron ejemplos ganadores.

## Lo que hizo el COG ORIGINAL frente a fuente
| Decisión / fuente | Resultado |
|---|---|
| COG real `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py::VT31CleanroomCognition` en NY AM | `LONG`, DOL=**150**, familia `PRIOR_NY_CASH_SESSION_HIGH` |
| Testigo nativo independiente de fuente TTrades AM sobre **las mismas velas** | `LOW RAID -> LONG`, DOL opuesto H1 09h = **110** |
| Verificador independiente V2 de doctrina, con el verdadero `CognitiveDecision` producido por COG | `REJECTED`, razón `DOL_NOT_OPPOSITE_9AM_H1_EXTREME` |
| Veredicto de **perfil TTrades NY AM** | `TTRADES_NYAM_DOL_SOURCE_NONCONFORMANT` |
| Veredicto de perfil ICT GENERAL | **NO evaluado como erróneo por este caso**; puede elegir un DOL contextual distinto |

**Interpretación metodológica:** se prueba la incompatibilidad de atribuir indistintamente al **COG G3 actual** la decisión TTrades 09h opuesta. El COG fue coherente con **su propia regla QORE G3 de seleccionar DOL elegible más cercano de pools anteriores**, pero no es fiel por defecto al **perfil específico TTrades AM** en ese escenario. Un detector auxiliar conforme al artículo no reprograma mágicamente el COG auténtico; PR #946 y #948 mantuvieron explícita esa separación. No modificar el COG para dar `110` simplemente porque ahora se observa el caso; debe existir identidad y política de perfil gobernadas y un nuevo versionado metodológico.

## Evidencia comprobada
- [PR #950 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/950), hijos del PR #948 original.
- **[CI GitHub Actions #38671726622 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38671726622)**, HEAD de código/test ejecutado `16ce2884b0b9a40a7edb46bc43d2ef3244bd993a`, **73/73 pytest PASS**, Ruff + compilación PASS. Todos los blobs G3 COG/OPS/acta originales SHA inmutables.
- **[Artifact #11943793928](https://github.com/mezas3238-hue/qore-core/actions/runs/38671726622/artifacts/11943793928)**, ZIP SHA256 `bb5aef53f1db40f89683da9cb982ac51f4689abbd3a23ce044f958ff2527833f`. Incluye dictamen JSON exacto con `CognitiveDecision` original, comparación del testigo nativo, V2, causales, veredicto y pruebas JUnit.
- El corpus NAS100 3Y 1.059.784 M1 y los conteos FVG/breaker NO fueron consultados en este ensayo. Ningún PF/WR/DD/Sharpe/Sortino, riesgo, lotaje, fill, OOS, BID/ASK o PnL entró al juicio.

## Qué queda para CERTIFICAR metodología y cognitiva
**Metodología M0 (identidad) no resuelta:** el Owner debe poder distinguir dentro de VT31 el perfil ICT_GENERAL_2023 y el perfil TTRADES_NY_AM_2025, con un **selector gobernado antes del contexto**, diferencias doctrinales explícitas y pruebas de transición; no habilitar filtro TTrades 09h en Londres/NY PM.
**M2 lectura de liquidez:** COG original debe demostrar el DOL que prescribe la **metodología seleccionada** y rechazar DTO de una variante en la otra. El testigo nativo de TTrades ya existe y no debe sustituir al COG real.
**M3–M5:** pendiente demostración completa del MSS/desplazamiento autoral y elección de la familia de entrada; #943 encuentra divergencia de stop C2 respecto al proxy pre-MSS, #945 formaliza estructuras breaker cuatro piernas sin prueba de fidelidad autoral; OB/Breaker y swing del autor siguen desconocidos.
**Cognitiva:** PR #948 demuestra WAIT razonado, memoria e invalidación del COG G3 en Londres; el caso actual confirma que ese COG emite una tesis causal en NY AM pero su DOL no corresponde a TTrades cuando el método se presenta con ese perfil. Se requieren más contrafactuales NY AM/PM, razones de selección de cada DOL y un testigo de comportamiento auténtico sin etiquetas del resultado.
**Gobernanza M6:** no emitir certificado a través de CI. Issue #897 requiere firma COG+OPS independientes sobre el SHA EXACTO de metodología y código. Cuando método y cognitiva estén ambos completos, emitir DOS actas humanas, no un PF.

## Decisión de arquitectura que NO se debe forzar
- **Opción de método A:** certificar VT31 como ICT GENERAL/QORE G3 honesto, sin alegar fidelidad autoral completa TTrades. Antes de certificar hay que completar fuente ICT, variaciones QORE y el resto de reglas.
- **Opción de método B:** certificar subperfil **TTRADES_NY_AM_2025** con un **COG nativo que obligue primer barrido 09h, retorno/confirmación y DOL opuesto 09h**, y fuentes OB/Breaker/swing de parada. La rama de investigación TTrades NYAM ya produce DTO separado (#933), pero no se puede decir que sea el COG original ni activar sin nueva versión y revisión.
- **Opción combinada:** un VT31 con dos perfiles explícitos por sesión, un solo COG gobernado que elige perfil **antes de procesar las condiciones**, sin ranking retrospectivo por PF, y dos certificaciones doctrinales por perfil antes de certificado integral.

**Estado vigente:** `METODOLOGIA=PENDIENTE`, `COGNITIVA=PENDIENTE`, `TRADER=NO_CERTIFICADO`. NO MERGE, NO LIVE, NO PRODUCCIÓN, NO FundedNext LIVE, NO VPS, NO OMS, NO sizing trader. Se conserva CIBO CMA como autoridad exclusiva del volumen y todos los requisitos futuros de DEMO en expediente separado. El presente informe añadido tras CI no se hace pasar por parte del código exacto SHA ya ejecutado.
# VT08 CRT PURE — AUDITORÍA CUALITATIVA DE FIDELIDAD COGNITIVA Y MODELO #1 — QC-002

**13-OCT-2026 · PR #626 · Modo OWNER: SOURCE-FIRST / NO NUEVAS INVESTIGACIONES CUANTITATIVAS**  
**Estado:** inspección código + registro documental, corrección cognitiva limitada; NO certificación, NO entrada al mercado, NO replay económico.

## Pregunta

¿Puede una cognitiva que dice tener `PARTIAL` conocimiento de la fuente CRT terminar dando una decisión `EXECUTE` como si todo estuviera demostrado? ¿Quién suministra la evidencia de old-high/old-low y confirma que es anterior al evento?

## I. Hallazgo COG-01, bug reproducible de razonamiento

### Antes (código original al comenzar esta ronda)

En `src/qore/infrastructure/traders/crt_pure_cognitive_state.py::assess_metacognition`, el árbol distinguía `UNKNOWN` y `CONFLICTED`, pero **NO** distinguía `PARTIAL` de `KNOWN` cuando no existían tokens de `uncertainties`. Estado `PARTIAL` + listas vacías + flags de estrategia/confirmación/destino verdaderos -> `WELL_SUPPORTED`; `reason(...)` podía producir `EXECUTE`.

Este es un error de coherencia epistémica (el nombre `PARTIAL` se contradice con `WELL_SUPPORTED`), no un efecto deducido de ganancias históricas.

### Después: corrección acotada

- `PARTIAL` siempre produce `CONDITIONALLY_SUPPORTED`, con razón `KNOWLEDGE_STATE_PARTIAL`, incluso si quien construyó el Situation Model olvidó detallar `uncertainties`.
- `adversarial_assessment` incluye esa razón metacognitiva, no solo la etiqueta genérica `METACOGNITION_NOT_WELL_SUPPORTED`, en `challenge_findings` / `auditable_why`.
- `reason(...)` devuelve `WAIT` si la hipótesis está viva, confirmada formalmente pero su evidencia es `PARTIAL`; preserva `ABSTAIN` ante contradicciones o tesis muerta. `KNOWN` sin contradicción mantiene el contrato anterior de salida `EXECUTE` conceptual.
- No se inventa umbral, indicador, filtro de horario, entrada o regla de fuente. No cambia los campos de stop, destino, precio, tamaño ni se crea permiso de capital.
- Tests centrados en conocimiento parcial vacío, referencia ambigua explícita, tesis inválida y caso `KNOWN`. Tests son de semántica de software, **no cuantitativos de rentabilidad**.

**Archivos:** `src/qore/infrastructure/traders/crt_pure_cognitive_state.py`; `tests/infrastructure/traders/test_crt_pure_cognitive_architecture.py`. Esperar CI **Cognitive Foundation** + **Cognitive Gate**, no WFO. Los cambios de tests inicialmente expusieron que faltaba propagar el motivo hasta la salida de `reason` y se corrigió antes de aceptar resultados.

## II. Matriz de concordancia: autoridad metodológica vs ingeniería

| Paso | Autoridad existente en expediente | Implementación inspeccionada | Dictamen |
|---|---|---|---|
| `OLD_HIGH / OLD_LOW` previo | video fundamental RomeoTPT Model #1 registrado como CANONICAL para el concepto | `_confirmed_pivot` fabrica swings `strength=1` solo al cerrar la vela a la derecha | **Causalidad razonable; criterio strength=1 ENGINEERING, no regla del autor** |
| Nivel entre varios máximos/mínimos antiguos | `MODEL_1_REFERENCE_SELECTION = AMBIGUOUS` en `crt_pure_source_registry.py` | `build_close_unmitigated_breach_groups` reúne simultáneamente varios niveles penetrados en un `BreachGroup` | **No se elige nivel fuente del autor; agregación ENGINEERING** |
| Vida del nivel después del raid | fuente original no cierra política universal de mitigación/rearm | R2-C elimina nivel al primer evento calificado y ante un cierre estrictamente fuera de nivel, no por mecha suelta | **ENGINEERING no promovido** |
| Fuente Model #1 bearish | M15 `up-close` que penetra old high; bullish inverso | R2-C exige `up_close` en OLD_HIGH y `down_close` en OLD_LOW; grupo puede incluir varios old levels | **Compatible con resumen documental; identidad precisa del nivel sigue abierta** |
| Confirmación | posterior M15 `close` más allá del borde del cuerpo fuente (no solo wick) | `_confirmation` utiliza `source.open_price`: límite inferior de cuerpo de vela fuente alcista para bearish, superior de vela bajista para bullish | **Traducción coherente con la fuente documental** |
| Momento de entrada | solo después de confirmación; transporte próximo M15 open | `_confirmation` requiere siguiente vela M15 contigua para el evento de entrada | **ENGINEERING causal de simulación, no original del autor** |
| Competencia entre dos fuentes M15 | fuente canónica no ordena política de elección universal | R2-G `NEWEST_SUPERSEDES` y otros ensayos seleccionan un intento por C3 | **ENGINEERING; NO autoriza múltiples operaciones** |
| Cognitiva ante evidencia de selección ambigua | no fingir `KNOWN` ni confianza numérica | `Situation Model` solo tiene `knowledge_state`/tokens e indicadores booleanos; no incorpora un objeto fuertemente tipado `OldLevel` | **GAP DE INTERFAZ sin resolver: el adaptador debe representar propiedad del nivel y contradicciones, o puede mentir por omisión** |

### Matiz crucial

La presencia de `source_event_present=True` y `strategy_identity_ready=True` **no demuestra** que el nivel antiguo se haya identificado correctamente. Son indicadores entregados por otra capa. La corrección `PARTIAL -> WAIT` no resuelve el riesgo de un adaptador que falsamente afirme `KNOWN`; no puede proclamarse cognitiva óptima ni trader certificado.

## III. Nueva fuente de orientación atribuida al autor — NO promoción de reglas

Se encontró un hilo públicamente archivado atribuido a `@Romeotpt`, con contenido fechado a finales de febrero de 2023. En él el autor describe que no todos los máximos/mínimos son equivalentes, contrastando niveles defendidos por su contexto con otros atravesados fácilmente, y resalta la importancia de tiempo/contexto.

**Localizador de transporte:** https://threadreaderapp.com/thread/1630736059393798144.html (sección de hilo 26-Feb, atribución @Romeotpt).

**Clasificación:** `AUTHOR_ATTRIBUTED_MIRROR / NAVIGATION_ONLY` hasta verificar el post original exacto. Una copia de un hilo del autor NO equivale a evidencia canónica cerrada, ni especifica una fórmula para elegir un swing. **No autoriza** indicador de "institucional", strength=2, ranking monetario, veto de nivel, hora arbitraria, ni permiso de entrada. Su utilidad es una **pregunta cualitativa**: ¿qué evidencia previa vincula al nivel con el CRT H4 que el trader está estudiando?

## IV. Secuencia guiada de lectura, no gráfico real

Caso pedagógico deliberadamente **ESQUEMÁTICO** (no resultado de AUDUSD/USDJPY, no datos de broker):

1. **Antes** de la vela fuente: el observador conoce dos old highs previamente validados. `REFERENCE_OWNERSHIP = AMBIGUOUS`.
2. **Se cierra una vela M15 alcista** con mecha por encima de ambos old highs. En R2-C puede emitir una sola `BreachGroup` con dos `reference_ids`; la fuente temporal se conoce solo al cierre.
3. **La siguiente M15 toca por mecha** por debajo del cuerpo de la fuente pero cierra por encima de su borde inferior. Esto no satisface el Model #1 bearish confirmado.
4. **La siguiente vela M15 cierra por debajo del borde inferior del cuerpo fuente.** Hay confirmación de precio; **no** demuestra la propiedad unívoca del old high. El adaptador debe conservar `PARTIAL` y explicar la ambigüedad si no está resuelta.
5. **Cognitiva:** ante estado `PARTIAL`, la evaluación debe ser `WAIT` (o `ABSTAIN` ante invalidez/expiry/contradicción), NO `EXECUTE` por ausencia accidental de tokens `uncertainties`.
6. **Nueva fuente posterior:** requiere identidad de evento y referencia nueva; `ABSTAIN` de una fuente muerta no se vuelve a ejecutar; evidencia real se revisará vela a vela cuando esté disponible.

## V. Gobernanza de procesos automáticos

Se detectó que dos workflows heredados `R2-BY AUDUSD` y `R2-BZ USDJPY` tenían `push` escuchando cada cambio de `crt_pure_cognitive_state.py`, relanzando pruebas económicas antiguas y requiriendo credenciales cTrader aun bajo la nueva orden del Owner. Se quitó su `push` automático y se dejaron `workflow_dispatch` **solo manual**, con comentario explicativo. Esto preserva el archivo/replay histórico y no consume datos de mercado; su nueva ejecución queda pendiente de autorización explícita.

Antes de esta corrección de disparadores, un `push` de la corrección cognitiva activó los jobs de `R2-BY/R2-BZ` ya existentes; ambos fallaron en la fase de descubrimiento de cuenta DEMO. **NO** se tomaron sus métricas como investigación nueva, y no hubo órdenes DEMO/LIVE. Conservar los logs como traza de automatismo antiguo.

## VI. Dictamen y próximos pasos (100% no cuantitativos)

**Reparado:** `COGNITIVE_PARTIAL_MISCLASSIFIED_AS_WELL_SUPPORTED`; razón explícita preservada hasta `auditable_why`.

**Abierto:** `MODEL_1_REFERENCE_SELECTION` (jerarquía entre old levels), `M15_SOURCE_IDENTITY` cuando dos referencias pertenecen a una misma vela, `NEW_EVENT_VS_REARM`, y **`SITUATION_MODEL_SOURCE_EVIDENCE_SEAM`** (adapter no expresa old level con campos auditables independientes).

1. Revisar un video original concreto de RomeoTPT con timestamp/página para adjudicar o mantener `AMBIGUOUS` la propiedad del nivel, evitando adoptar frases de un mirror como fórmula.
2. Elegir **un caso real documentado** con H4 y velas M15 originales visibles antes de decisión; generar una ficha con OHLC, fuente verificable, niveles, invalidación y razón humana, sin analizar resultados económicos. Hasta disponer de ese caso: `VISUAL_CASE_NOT_YET_OBSERVED`.
3. Trazar qué productor crea `CrtPureSituationModel` y si conecta `reference_ids`, `source_event_id`, `knowledge_state`, `contradictions` de manera fiel; sin añadir filtros numéricos ni nuevos thresholds.
4. Documentar divergencias de fuente/código con `CANONICAL / QORE_ENGINEERING / AMBIGUOUS`, no con `PF`.
5. Mantener tests semánticos y auditoría de causalidad; no abrir nuevos backtests ni tareas WFO.

**CERTIFIED=FALSE**. **NO SIZING/LOT/VOLUME/CAPITAL/LEVERAGE INSIDE VT08**. CIBO/QORE Risk autoridad independiente. No merge, no VPS, no DEMO, no LIVE, no producción, no dinero real.

## VII. Trazabilidad de productores de Situation Model — observación QC-02 (cerrada documentalmente)

Se inspeccionaron los siguientes archivos de la rama del PR:

- `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2by_audusd_cognitive_experience_wf.py`, construcción alrededor de líneas 230–253.
- `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2bz_usdjpy_cognitive_experience_wf.py`, construcción alrededor de líneas 291–314.
- `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2cc_audusd_cognitive_wait_resolution_wf.py`, construcción alrededor de líneas 443–466.
- `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2cd_usdjpy_cognitive_wait_resolution_wf.py`, construcción alrededor de líneas 443–466.
- `src/qore/infrastructure/traders/crt_pure_model1.py`, `crt_pure_r2_entry_router.py` y `crt_pure_cross_market_cognition.py`; ninguno de estos tres archivos inspeccionados construye directamente `CrtPureSituationModel`.

En los **cuatro productores de laboratorio** mencionados, `source_event_present=True`, `confirmation_complete=True`, `destination_context_known=True`, `destination_available=True` y `execution_data_fresh=True` son valores entregados directamente al constructor en esa etapa, mientras que el grado de conocimiento `knowledge_state` y las `contradictions/uncertainties` se derivan del modelo cognitivo de investigación.

**Distinción obligatoria:** esos indicadores son aserciones del adaptador de investigación para un evento ya seleccionado; no constituyen pruebas autónomas, verificables y tipadas de que el old HIGH/LOW correcto exista, esté vigente y sea propietario de ese source event. Tampoco muestran un vínculo de evidencia `reference_ids`/nivel primario en `CrtPureSituationModel`, pese a que el ledger `BreachGroup` sí contiene referencias.

### Estado de los problemas tras la trazabilidad

- `QC-01` **REPARADO**: `PARTIAL` deja de transitar inadvertidamente a `WELL_SUPPORTED` y su incertidumbre es visible en el `WHY`.
- `QC-02` **CONFIRMADO / ABIERTO**: cadena de evidencia semántica hasta `Situation Model` insuficientemente explícita. Un booleano verdadero no equivale a prueba primaria. Para cerrar QC-02 se necesita contrato entre referencia causal y el modelo cognitivo con procedencia/identidad/frescura, sin inventar regla de prioridad de old-level.
- `QC-03` **ABIERTO**: `MODEL_1_REFERENCE_SELECTION` sigue `AMBIGUOUS` en source registry; ni `strength=1` ni `BreachGroup` son regla fuente.

Se mantiene la instrucción de **NO** activar nueva investigación cuantitativa, de **NO** ajustar esos productores de laboratorio por PF, y de **NO** alegar que esta evidencia prueba edge o un trader listo.


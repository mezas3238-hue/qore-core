# QORE CORE — HANDOFF MAESTRO ARQUITECTO A — VT08 5M
## Auditoría integral de fidelidad a TTrades, recuperación de densidad y ruta a certificación

**Fecha:** 2026-10-10  
**Estado:** MANDATO ACTUALIZADO POR EL OWNER / PRIORIDAD P0 DENSIDAD / INVESTIGACIÓN, NO CERTIFICADO  
**Repositorio:** `mezas3238-hue/qore-core`  
**PR padre:** [#634](https://github.com/mezas3238-hue/qore-core/pull/634)  
**Issue asignado a la especialidad:** [#762](https://github.com/mezas3238-hue/qore-core/issues/762)  
**Rama del Arquitecto A:** `agent/vt08-5m-methodology-source-20261010`  
**Arquitecto B cognitiva:** [#763](https://github.com/mezas3238-hue/qore-core/issues/763) / `agent/vt08-5m-cognition-replay-20261010`  
**Rama canónica del programa:** `agent/vt08-cognitive-expansion-5m-v1-001`  
**Fuentes de continuidad:** `VT08_COGNITIVE_EXPANSION_5M_MASTER_HANDOFF_2026-10-10.md`; `VT08_COGNITIVE_EXPANSION_5M_AUDIT_AND_TWO_ARCHITECT_CONTRACT_2026-10-10.md`.

> **ORDEN DE TRABAJO DEL OWNER:** el problema prioritario de VT08 es la **falta de densidad de operaciones**. El Arquitecto A tiene que auditar al trader íntegramente contra la fuente primaria del autor, corregir cualquier restricción artificial/omisión/interpretación errónea que esté suprimiendo entradas válidas, construir las variantes fieles que faltan y probar si recuperan densidad ejecutable **sin destruir los edges ni la robustez**. Debe continuar hasta dejar documentados todos los bloqueos de certificación y trabajar con el Arquitecto B hasta la validación conjunta. No podrá presentar un aumento de eventos estructurales como un aumento probado de trades rentables.

## A. Mandato explícito y prioridad sobre instrucciones previas

La instrucción anterior de «cerrar una única familia» era un **primer hito**, NO el alcance final. Queda supersedida como límite de la investigación. El Arquitecto A debe auditar la **totalidad** de la metodología y las **seis familias fuente**, priorizar las más prometedoras desde la **fuente y disponibilidad causal, no del PnL**, cerrar de forma incremental tantas familias justificadas como sea necesario para recuperar densidad legítima. Si alguna queda sin evidencia suficiente, mantenerla NO EJECUTABLE; registrar evidencia que falta. No hay autorización para inventar señales, relajar invalidaciones fuente o seleccionar winners con hindsight.

Orden de prioridades:
1. **P0-M0 FIDELIDAD:** verificar correspondencia real fuente primaria→contrato R3.2/R3.9→implementación→filtro del replay; catalogar desvíos y errores.
2. **P0-M1 DENSIDAD:** localizar TODA pérdida de oportunidad válida y corregir contenciones que sean artificiales previa adjudicación autor/Owner.
3. **P0-M2 EJECUCIÓN:** contratos completos y causales para familias de entrada, SL, TP y lifecycle; medición de trades verdaderamente ejecutables por mercado y año.
4. **P0-M3 INTEGRACIÓN:** producir CandidateEvent para el Arquitecto B y asegurar que cognitiva participe realmente en el replay y no suprima oportunidades por bloqueos ajenos a la fuente.
5. **P1-CERTIFICACIÓN:** medir densidad, raw PF, DD, comportamiento temporal y costes; preparar freeze + validación independiente y batería final con el Arquitecto B.

## B. Evidencia basal que debe reproducirse antes de cambiar metodología

1. Auditoría de funnel anterior sobre el MISMO corpus ~1095 días / cinco mercados / 01,05,09 NY: **11.655** H4-anchors observados; **488** candidatos mecánicos; **457** operaciones terminales. Conversión observados→terminal **3,92%**. De 488 a 457 se pierden **31**; la escasez está casi toda **antes** de construir un candidato.
2. Fallos de primera exclusión: C2-close-not-inside-reference **3.987**, bias-unresolved **2.071**, C2-both-side-sweep **1.347**, C2-side/bias-mismatch **1.317**, no-reference-sweep **1.085**, no-Protected-Swing **769**, incomplete-source-H4 **406**, multiple-PS **145**, incomplete-source-day **40**. Total exactamente 11.655 al sumar 488 mecánicos + primeros fallos. La clasificación es de la **implementación existente**: no significa que todos los descartes sean setups genuinos.
3. Línea M3 latest-confirmed PS ya rechazada por el Owner: por ~3Y EURJPY **161**, USDCHF **149**, NZDUSD **182**, CADJPY **161**, USDCAD **159** operaciones; insuficiente.
4. Censo M3 sin resultados posteriores de precio: estructuras CISD+PS por mercado ~2.042–2.340 eventos / ~3Y, pero **452–502 fechas NY únicas** / ~3Y, ~**301–335 fechas únicas / 2Y**. Posterior retest del nivel CISD: ~**291–318 fechas únicas/2Y**. Esto es **reservorio estructural** y cota de oportunidad por día, **NO** conteo de entradas admisibles, órdenes ejecutadas o edge.
5. Modelos anteriores de raw PF son mixtos/insuficientes en varios mercados; mejoras de Core Stack y DD no pueden confundirse con calidad de señal. Holdout EURJPY 5Y anterior rechazado por estabilidad temporal pese a cifras agregadas alentadoras.
6. Historial relevante: `docs/research/VT08_COGNITIVE_EXPANSION_5M_DENSITY_ROOT_CAUSE_AUDIT_V1.md`, `VT08_COGNITIVE_EXPANSION_5M_THREE_YEAR_OPPORTUNITY_CENSUS_MASTER_REPORT.md`, `VT08_COGNITIVE_EXPANSION_5M_M3_ENTRY_GEOMETRY_CENSUS_V1_FREEZE.md`, `VT08_COGNITIVE_EXPANSION_5M_SOURCE_AUTHORITY_DENSITY_RECOVERY_AUDIT_V1.md`.
7. Cinco mercados de investigación: **EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD**; Owner anchors de operación **01:00, 05:00, 09:00 Nueva York**. 13:00 NY figura en SOURCE_COMPLETE de R3.2 pero **NO** pertenece al subset vigente del Owner. No ampliar horas ni mercados operativos sin autoridad separada.

**Advertencia:** los datos anteriores provienen del handoff y ejecuciones históricas. El siguiente arquitecto debe verificar SHA/corpus/versión, regenerar el funnel reproducible y no declarar métricas nuevas sin ejecutar y archivar el replay.

## C. Auditoría total de fidelidad al autor: trabajo obligatorio, no optativo

Autor/metodología primaria: **TTrades — 4-Hour Power of Three**. Fuente primaria identificada en el contrato congelado: `youtube:FAKWJ-1NlLE`; activo histórico `1000854868.mp4`; SHA-256 declarado `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`. **Verificar acceso y huella del medio realmente disponible; no afirmar que se rehashó cuando no se ha hecho**. Revisar audio, transcripción comprobada, capturas/frames y ejemplos. Revisar aclaraciones posteriores OFICIALES del autor por separado y fecharlas. DeepSeek R3.2 es testigo/reconstrucción, no autoridad superior al autor.

Entregar una **matriz forense fuente→código** por cada regla. Campos obligatorios: `rule_id`, fuente primaria URL/archivo + minuto/segundo + frame, fragmento/acción observada (sin citas extensas), aclaración oficial si la hay, `SOURCE_EXPLICIT/SOURCE_INFERRED/QORE_CONTAINMENT/OWNER_POLICY/UNRESOLVED`, código y líneas, test asociado, regla programada, diferencias, efecto sobre densidad, propuesta de corrección y autoridad que la aprobaría. Si el autor no precisa una condición, no «inventar fidelidad».

Elementos mínimos de revisión:
- H4 PO3, OLHC/OHLC, manipulación/distribución, acumulación y sincronía de C1/C2/C3 con el reloj NY.
- Daily bias cuatro casos PDH/PDL; frontera del source-day (17:00 NY→17:00 NY es contención QORE, no regla universal fuente).
- C2 reversal frente a C3 continuation; diferencia cualitativa shallow/large/deep y cuánto rango queda; ningún umbral ATR/pips/body% puede presentarse como autor-explicit.
- CISD: vela opuesta primera, nivel **open**, close-through para confirmación, control wick-only; datos LTF con cierre real as-of.
- POI/liquidez/FVG: ¿FVG es requisito de esa familia o solo ejemplo contextual? ¿Reentrada/retest exige zona, qué confirmación y cuándo?
- Protected Swing: formación, nivel, multiplicidad y selección; cómo se resuelve PS que se forma después del open H4 sin reescribir la historia.
- Las **seis familias**: reversal-entry, continuation-entry, confident-entry, positional-entry, open-entry, POI-continuation-entry. Auditar primero todas; implementar variantes una por una con bundle completo, no exigir de todas el filtro FVG que solo pudiera corresponder a algunas.
- Las **cinco familias de SL**: swing protegido, 50% CISD/EQ, opposing-candle, FVG, body-low/body-high; compatibilidad real por entrada, distancia/offset de broker y causalidad.
- Objetivos CONTEXTUALES: liquidez estructural, 2R, -1 SD, daily open, extremos de sesión, cuando correspondan; 2R fijo actual = contención del replay, NO objetivo universal del autor.
- Modelo de salida y lifecycle H4 de órdenes pendientes y posiciones abiertas, stops, TP parcial/gestión; **resolver expresamente discrepancia** entre `VT08-R3-2-SOURCE-FREEZE.md` (afirma no sobrevivir al H4 actual) y `VT08-R3-9-FINAL-SOURCE-CONTRACT.md` (lifecycle de posición llena marcado unresolved y close-at-next-H4 = contención). Nunca ampliar/reducir lifecycle solo porque cambia PnL.
- M15_STANDARD / M5_FRACTAL / M3_FRACTAL independientes; timing SOURCE_COMPLETE vs OWNER_OPERATIONAL_SUBSET; DST, 01/05/09 NY; cardinalidad una operación filled por mercado/día es Owner policy, no TTrades universal.
- Filtros extra, selectores first/latest/only-PS, bias, same-bar assumptions, tolerance exacta, duplicados, prohibiciones no fuente y cualquier decisión oculta que suprima candidatos.

## D. Auditoría de causa raíz de densidad: demostrar dónde se pierden los trades

Reconstruir **un ledger por cada barra de anchor / evento causal**, no solo un resumen de trades. Cada fila debe retener:
`market`, `NY_date`, `anchor`, `ltf_profile`, `as_of`, `event_id`, `source_family`, `C2_C3`, `CISD`, `PS`, `POI/FVG`, `bias`, `source_authority`, `candidate_created`, `rejection_stage`, `first_failure`, `all_failure_reasons`, `QORE_only_restriction`, `causal_entry_possible`, `fill_possible`, `owner_daily_cap`, `evidence_hash`. Sin futuro/TP/SL realizado/PnL en admisión.

Separar al menos cuatro contadores por mercado/fecha:
1. Eventos fuente observables (sin derecho a operar).
2. Setups completos/justificados por fuente (antes de restricciones QORE).
3. Señales y órdenes **ejecutables** bajo contrato causal exacto.
4. Órdenes **rellenadas y cerradas** en replay con costes y daily limit.

Reportar densidad **por mercado/año**, operaciones cada 2Y equivalentes por mercado, por mes/trimestre/anchor/familia, días únicos, trade-rate por ventana observable, conversión etapa por etapa, causas exclusión y oportunidad recuperada marginal. **No sumar eventos duplicados** de varias temporalidades ni múltiples señales de un mismo día como operaciones cerradas. Entregar baseline versus metodología corregida con mismas barras/same broker assumptions.

Investigar prioritariamente, pero sin declararlos errores fuente de antemano:
- **3.987 C2 closes fuera de referencia**: distinguir una condición esencial del autor de una restricción muy estrecha del replay.
- **2.071 bias unresolved**: si el límite de día y los cuatro casos PDH/PDL tienen cobertura fuente/código correcta.
- **1.347 both-side-sweep y 1.317 side mismatch**: si fuente resuelve dirección y cuándo; no admitirlos por fuerza.
- **1.085 sin reference sweep**: qué nivel es válido, si actual referencia exclusiva es contención QORE.
- **769 no PS y 145 multiple-PS**: causalidad, fresh versus pre-anchor PS, selección fuente y geometría.
- **C2-only** vs C3 omitido; familias no posicionales no ejecutadas; 13:00 source complete solo diagnóstico por defecto.
- Comprobar que el censo M3 `CISD-level retest` realmente coincide con un **bundle de entrada** oficial; si no, seguirá siendo forma geométrica, NO fill.
- Cuantificar pérdidas atribuibles a **fidelidad**, **reglas Owner**, **restricción experimental**, **dato ausente**, **ejecución**, y **cognitiva** (para esta última pasar CandidateEvent al Arquitecto B).

**Prohibido:** afirmar que los 3.987/2.071/etc. son trades recuperables; las causas son clases de descartes, no PnL ni edge.

## E. Plan experimental obligatorio para recuperar densidad

**Etapa M0 — Verdad y reproducción.** Congelar SHA de referencia, auditoría documental de fuente, reproducir baseline de 457 trades y versión M3 más reciente en corpus consumido; manifest de evidencia y fingerprint. Registrar desviaciones antes de cambios.

**Etapa M1 — Matriz completa de fidelidad.** Publicar diferencias concretas entre fuente, R3.2, R3.9, B01 y todos los selectores de laboratorio. `P0_SOURCE_MISMATCH` requiere corrección y test; `P0_UNKNOWN` requiere evidencia/contención honesta. Revisar fuente completa, no solo fragmentos que apoyan más trades.

**Etapa M2 — Rediseño causal de admisión con densidad.** Mantener base mínima fuente y separar claramente source-valid / owner-policy / QORE-containment. Cerrar una primera familia de alta cobertura, **seguir con las demás justificadas**; cada una tendrá entry timestamp/precio/tipo de orden, SL, TP, cancelación, expiry y manejo de ambigüedad con fuente exacta. Contrato por familia pre-registrado **antes** de inspeccionar PnL; rechazo fail-closed si incompleto.

**Etapa M3 — Perfil independiente y atribución incremental.** Ejecutar M15, M5 y M3 **por separado**, idéntica evidencia y horarios/Owner policy; encontrar contribución marginal de cada variante fuente, sin combinarlas mirando qué ganó. Si se propone política de selección intradía o entre perfiles, formalización causal y aprobación Owner **previa** a un nuevo replay económico. No aumentar el tope one-fill/day implícitamente.

**Etapa M4 — Pruebas reproducibles de densidad ejecutable.** En evidencia **consumida** comparar baseline y cada bundle precongelado con listado trade por trade, first-failure y conteos exactos. Entregar: volumen de trades genuinos, PF raw equal-risk, total R, DD R, ratio edge/volumen, sensibilidad a spread, slippage/commission si inputs disponibles; no simular fills imposibles o spreads hipotéticos como reales. Reducir DD o subir PF sin densidad suficiente NO cierra la misión.

**Etapa M5 — Handoff al Arquitecto B.** Publicar `VT08_5M_CANDIDATE_EVENT_V1` versionado e inmutable: as_of, full source/bundle authority, event fingerprint, market/date/timezone, family, profile, C2/C3, PS/CISD/POI causal, entry/SL/TP/expiry y contradicciones/UNKNOWN. A no puede llamar `EXECUTE` si B da ABSTAIN; B no puede inventar o alterar fuente, SL, TP o fill. Comparar metodología-only vs cognitiva-on en los **mismos** source events.

**Etapa M6 — Congelación de candidato y certificación conjunta.** Definir con Owner un **nuevo umbral numérico de densidad**, aprobado **antes** de ver los resultados de validación. El antiguo mínimo 50 trades/2Y está retirado. La cifra de ~301–335 **días con estructura** es una cota observada, no un objetivo aprobado de trades: no inventar uno. Batería temporal, WFO, Monte Carlo/block bootstrap, años/mensuales, estrés de costes, independencia de top winners, causality leakage, per-market/anchor/side. Solo con candidate+gates congelados abrir validación 7Y más antigua; señales y salidas estrictamente antes de `2023-09-24T23:45:00Z`. Si falla, no retunar con ese holdout; retirar identidad e iniciar otra hipótesis en evidencia apta.

## F. Criterios de éxito/fracaso y reporte obligatorio

**No confundir cuatro distintos logros**:
- Más estructuras detectadas = descubrimiento; no rendimiento.
- Más señales completas = mejora de admisión; no necesariamente llenados.
- Más trades ejecutables reales = **recuperación de densidad** (principal KPI del Owner).
- Más trades + PF/DD/estabilidad aceptables con cognitiva y costes = candidato certificable, sujeto a validación independiente.

El reporte tiene que distinguir metodología sola, metodología+gestión, metodología+cognitiva, y capital-weighted; PF de la fuente se calcula en riesgo igual, no puede maquillarse asignando capital a los ganadores.

Umbrales económicos históricos de investigación vigentes salvo freeze explícito nuevo: PF >=1.80; DD observado <=6R; mean R >=0; MC p95 DD <=15R; MC probabilidad terminal positiva >=0.90; estabilidad de anchors, periodos y mercados; estrés. **No se declara certified** hasta satisfacer todos los gates precongelados y sin brechas cognitivas. No prometer esos valores; son criterios de aceptación, no previsiones.

**Cada entrega/PR debe incluir:**
- SHA exacto; pruebas realmente ejecutadas y resultados, sin confundir CI anterior con actual.
- Fuente con minutaje y comparación original vs código por familia.
- Tabla de restricciones removidas/retenidas con clasificación SOURCE/OWNER/QORE y prueba causal.
- Matriz por mercado: anchor events → structures → source-complete candidates → orders → fills → terminal, y diferencia vs baseline.
- Trades/año y por dos años equivalentes, con días únicos y calendario NY verificable.
- PF raw, R, DD, ratio PF marginal, estabilidad y costes en bases comparables.
- Attribution ledger de cada entrada nueva; motivos exactos de ABSTAIN/no-fill; contabilidad del daily cap.
- Contracto CandidateEvent/fingerprint para B y confirmación de revisión cruzada.
- Lista concreta de bloqueos restantes, decisiones Owner pendientes, resultados de holdout **solo cuando legítimamente unsealed**.

### Prohibiciones duras

No tocar VPS, producción, capital real ni lista runtime de mercados autorizados. No auto-fusionar PRs. No buscar densidad rompiendo fuente ni subiendo riesgo/lotaje; un trade no se vuelve rentable por mayor sizing. No usar métricas de Core Stack como PF de señal. No inventar un target universal 2R o permitir un Protected Swing aún no confirmado. No unir M3/M5/M15 después de resultados; no elegir año/mercado/anchor/dirección ganador a posteriori. No apertura de sealed 7Y durante tuning. No relabel `UNKNOWN` como `CONFIRMED`. No borrar historia de evidencia rechazada.

## G. Primeras acciones del siguiente Arquitecto A

1. Leer este handoff, master de PR #634, [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762), y el audit de dos arquitectos; leer [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763) para interfaz.
2. Inspeccionar video/framebook original y referencias de R3.2/R3.9; publicar **fidelity delta report** en su rama con evidencia suficiente y sin usar métricas para interpretar al autor.
3. Inspeccionar el funnel código; reproducir los 11.655/488/457 y la causa de los 3.987/2.071/1.347/... first failures sobre el mismo dataset y SHA, o documentar la imposibilidad de reproducirlos.
4. Clasificar exhaustivamente seis entry families en fuente→bundle; investigar qué permite entry intracycle y retest CISD/PS/POI; cada cierre de familia debe ser completo e implementable o permanecer shape-only.
5. Publicar propuesta versionada CandidateEvent + fixture causally available para B; solicitar aprobación cruzada antes de cambiar interfaz.
6. Solo entonces realizar primer replay de DENSIDAD + PF/DD en desarrollo consumido; iterar por nuevas hipótesis fuente y avanzar hasta candidato congelado y batería certificadora conjunta.

**Estado del handoff en esta fecha:** MISIÓN ASIGNADA Y DOCUMENTADA, NO SOLUCIONADA. El siguiente Arquitecto debe realizar la auditoría exhaustiva, código y nuevos replays; aquí no se afirma ejecución ni certificación.

**Principio rector:** CORREGIR FIDELIDAD → RECUPERAR TRADES LEGÍTIMOS → PROBAR EDGE → INTEGRAR COGNITIVA → VALIDAR SIN FUGAS → CERTIFICAR.

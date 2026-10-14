# ADR — QORE Native: decidir A / B / C después de veinte rondas; prohibir la alternativa D

**Fecha:** 2026-10-14 (America/Asuncion).
**Estado:** **PROPUESTA TÉCNICA PARA RATIFICACIÓN DEL OWNER; NO ORDEN DE MERGE, NO CIERRE IRREVERSIBLE DE REPOSITORIO**.
**Ámbito exclusivo:** programa **QORE Native, descubrimiento de alpha intradía FX/índices/metales CFD sobre M5** y sus modelos cuantitativos derivados.
**Repositorio soberano:** `mezas3238-hue/qore-core`. GitHub es fuente de verdad.
**NO comprende ni decide** VT08, VT31, CIBO, Traders existentes, Scalper, QORE Research general, Shared, Risk, QDLE ni ninguna certificación de otros programas.
**Coste adicional autorizado:** USD0. **No capital real, no DEMO operativa nueva, no VPS, no LIVE, no merges sin orden.**

## 1. Evidencia ya producida que sí autoriza una decisión

La discusión con el owner constató la necesidad de optar por infraestructura nueva (A), pivot a horizonte diario (B) o cierre de línea QORE Native (C); no seguir con hipótesis 21 sin decidir (D). Esta ADR registra una **recomendación arquitectónica**, no una prueba adicional de trading ni una atribución de causalidad a datos inexistentes.

1. **33 activos, 24.377.420 barras M5 verificadas en inventario**: [handoff maestro PR #855](https://github.com/mezas3238-hue/qore-core/pull/855). No son 24 millones de observaciones económicas independientes ni BID/ASK continuo 2016–26. Mezcla de orígenes originales CIBO y nuevas series IC Markets; contrato histórico económicamente EXACT aún sin probar para cohorte original.
2. **7 metodologías × 33 mercados = 231 celdas con resultados brutos sin hallazgo robusto replicado:** [E3 PR #836](https://github.com/mezas3238-hue/qore-core/pull/836), [Actions #38262585848](https://github.com/mezas3238-hue/qore-core/actions/runs/38262585848). **0/7** métodos con gross y delta positivos en DEV y DIAG bajo las sensibilidades. El método ya incluía `TREND_MULTI_DAY`; **reempacar el mismo método como momentum diario sería reciclar una línea fallida, no hipótesis nueva**. Su gross en DEV fue negativo, según #836.
3. **H-TOM-1 — examen preregistrado sobre SP500/US30/NAS100:** [PR #923](https://github.com/mezas3238-hue/qore-core/pull/923), [Actions #38502188181](https://github.com/mezas3238-hue/qore-core/actions/runs/38502188181). En DIAG los tres gross medios antes de costes son **−3.0884, −11.9489 y −0.2184 bps**; incluso NAS100, que supera control relativo, es negativo en términos absolutos. Para la **regla exacta long-only** y costes totales no negativos, neto medio no puede superar bruto negativo. `NO_SUPPORT_UNDER_PREREG`.
4. **CFTC H-COT-2:** [PR #921](https://github.com/mezas3238-hue/qore-core/pull/921), [Actions #38495515717](https://github.com/mezas3238-hue/qore-core/actions/runs/38495515717). WTI n7/n1, gas natural n5/n3 por split; faltó muestra independiente; es `CLOSED_INCONCLUSIVE_LOW_POWER`, **NO** prueba de retorno universal cero ni recuperación de un edge.
5. **Auditoría independiente de los tres expedientes originales firmados:** [PR #924](https://github.com/mezas3238-hue/qore-core/pull/924), [Actions #38504196569](https://github.com/mezas3238-hue/qore-core/actions/runs/38504196569), **SUCCESS 8/8** adversariales, sin nuevo PnL ni nuevas velas. Documento base [handoff económico de #924](https://github.com/mezas3238-hue/qore-core/blob/research/qore-alpha-discovery-economic-audit-20261013/docs/research/QORE_ALPHA_DISCOVERY_INDEPENDENT_ECONOMIC_TRIAGE_MASTER_HANDOFF_2026-10-13.md).

**Inferencia permitida:** en las estrategias y segmentos previamente analizados, QORE Native **NO ha documentado una señal bruta positiva, robusta, replicada y ejecutable**. **NO** concluir como teorema que todo `FX/CFD M5` es ineficiente o que ningún edge existe: la población de métodos examinados es finita, no abarca todos los mecanismos y hay sesgo de exploración. El problema observacional principal en dichas reglas es la evidencia bruta, **mientras** que el faltante de costes/fills sigue siendo bloqueo genuino para certificar métodos con gross positivo que pudieran aparecer.

## 2. Criba por pagador económico (no confundir motivación con alpha)

| Hipótesis de prima / flujo | Pagador posible | Observable con fuentes actuales | Estado de investigación |
|---|---|---|---|
| Roll yield / term structure | Coberturistas con obligación de rodar vencimientos; exposición curva | **NO**: sin precios contract-native por vencimiento y roll/expiry económica verificada | No elegible para inferir retornos |
| Prima de riesgo de volatilidad | Demanda de protección opcional; vendedores toman riesgo de cola | **NO**: sin series opciones, volatilidad implícita y primas/costes | No elegible para inferir retornos |
| Liquidez/impacto microestructural | Demandantes de ejecución inmediata | **NO** a profundidad necesaria: BID/ASK en ventanas cortas, no order book, agresores ni fills | No elegible para certificar |
| Rebalanceo forzoso de constituyentes de índice | Fondos replicadores | **PARCIAL**: M5 del índice pero sin universo histórico de constituyentes, anuncios point-in-time ni eventos ejecutables | No confundir con H-TOM-1; requiere fuente distinta |
| Momentum de horizonte diario | Underreaction/prima condicional por riesgo, pagador no siempre único | **M5→D1 técnicamente posible**; pero `TREND_MULTI_DAY` E1/E3 y persistencia anteriores sin respaldo, dividendos/swap CFD y OOS virgen no acreditados | **No autorizar automáticamente otra prueba** |
| FX carry / fixing London / turn-of-month | Coverers/balance sheets/calendar demand | Fuente parcial y resultados anteriores insuficientes o negativos | Familias ya cerradas en su alcance |
| CFTC posicionamiento extremo | Teoría contrarian a gestores posicionales, pagador no demostrado | Solo WTI/NG referencial EIA; pocos episodios efectivos | Cerrado inconcluso por muestra |

No atribuir un edge automáticamente a roll yield, VRP u order flow solo porque exista un participante que paga una prima. Datos superiores mejoran la posibilidad de contrastar mecanismos, **no garantizan ganancias**.

## 3. Las opciones reales — decisión recomendada

### A. Nueva infraestructura (futuros contract-native/options/order flow)

**Estado actual: `BLOCKED_NO_OWNER_BUDGET_OR_LICENSE`.** Si algún día se autoriza, exigir presupuesto por licencia/venue/histórico/almacenamiento, permiso de redistribución, custodia, contratos, cuotas recurrentes y un **solo mecanismo económico preregistrable** antes de comprar. No gastar USD125 ni iniciar descargas bajo la política USD0; no afirmar que A sea la **única** ruta teórica hacia un edge.

### B. Pivot con los M5 ya disponibles a horizonte diario

**Estado: `SEPARATE_PROPOSAL_NOT_AUTOMATIC_CONTINUATION`.** Técnicamente se pueden derivar barras D1 a partir de M5 sin inventar velas, sujeto a huso horario, sesiones, gaps, cash vs CFD, corporate actions, rollover, financiación y matching de bid/ask para valoración. Pero una nueva frecuencia por sí misma **NO** constituye causa económica nueva. Debe explicar exactamente por qué difiere de los `TREND_MULTI_DAY`, `PERSISTENCE_12H` y carry previamente fallidos; presupuestar muestra/efectos y fuente realmente nueva para validación. **No correr B ahora:** eso sería la hipótesis 21 bajo otro nombre. B puede ser **un nuevo programa**, solo por decisión expresa del owner, con prereg independiente y sin selección del mejor índice retroactiva.

### C. Cerrar la búsqueda de alpha M5 del QORE Native actual y conservar los activos

**RECOMENDACIÓN TÉCNICA: C.** Marcar `QORE_NATIVE_M5_ALPHA_DISCOVERY_FROZEN_RECOMMENDED_PENDING_OWNER_RATIFICATION`, preservando hallazgos negativos, G0/G1, Trader Lab y custodia por SHA. **No** borrar archivos, ramas, modelos antiguos, borrar PRs o congelar desarrollo de VT31/VT08/CIBO/Scalper/Shared. QORE Core continúa; se cierra **solo el modo de búsqueda automática de nuevas hipótesis en ese subprograma**.

### D. Seguir testando nuevas señales con el mismo M5 sin una decisión A/B/C

**RECHAZADA** por repetición de hipótesis, data mining y ausencia de señal bruta robusta en 20 rondas. No permitir duplicar H-TOM-1, extremismos CFTC, London fix, carry, E1 7×33, ni bajar umbrales ex post.

## 4. Condiciones de cambio de arquitectura que evitarán otra ronda sin dirección

- Cualquier nuevo estudio económico necesita autorización **específica**: no basta "avanza" para modificar el estado de un programa **científicamente congelado**.
- Entregar, **antes de outcomes**: `ACTOR_PAGADOR`, `RIESGO/FLUJO_TRANSFERIDO`, `PREVISIBILIDAD/INFO_ASOF`, `MERCADO/CONTRATO`, `REGLA_DIRECCIONAL`, `RENDIMIENTO_ABSOLUTO_MINIMO_NETO`, `COSTO_EJECUCION_RAZONABLE`, `N_EFECTIVO`, `OOS_REALMENTE_NUEVO`, `REGLA_STOP`. Si cualquiera es indeterminable con datos accesibles USD0: **NO_GO**, no otra auditoría preliminar vendida como descubrimiento de alpha.
- `2024-09-17+` Native y `2022+` CFTC siguen cerrados a inspección de retornos por impulso de resultados anteriores. No consumirlos para buscar la hipótesis que falta.
- Evidencia de source no es custodia permanente: archivos GitHub Actions pueden expirar. Conservar SHA/documentos y resolver archivo legal en un proyecto **de preservación**, si owner ordena, no para reabrir especulación.
- Un `NO_SUPPORT` significa falta de respaldo bajo la prueba. `INCONCLUSIVE` es falta de potencia o datos. `CLOSED` es decisión operativa sobre esas líneas, no una afirmación universal sobre la existencia de alfa.

## 5. Resolución, autoridad y siguiente trabajo

**Decisión arquitectónica recomendada (pendiente de ratificación):**
`RECOMMEND_C_FREEZE_QORE_NATIVE_INTRADAY_M5_ALPHA_SEARCH; KEEP_CORE_AND_ALL_OTHER_TRADERS_ACTIVE; A_BLOCKED_USD0; B_AVAILABLE_ONLY_BY_SEPARATE_EXPLICIT_MANDATE; NO_D`.

La presente ADR crea una salida clara y falsable para el programa. **No declara que el Owner ya decidió C**, no altera el estado técnico de producción, no aprueba nuevos recursos, no efectúa merges ni renombra productos, y no emite un certificado negativo universal. Cuando exista la ratificación explícita de C, se puede registrar en la misma PR; si el owner elige B, tramitar un **mandato nuevo**, no retunear el actual.

**Fin ADR. Evidencia disponible, limitaciones explícitas, NO nuevos tests/forecasts/PnL.**

# VT31 — preregistro M3 V6: geometría intermedia literal frente a filtro QORE estricto

**Fecha:** 2026-10-15. **Antecedente inmutable:** handoff R4 commit `037ae728ed2d7990998d837574099cb1d7e2f116`, V5 script blob `e6fd7de4997534426a024eb9689974c916b189a4`, PR #973. Este documento se confirma ANTES de agregar el testigo V6.

## Pregunta científica y fuente original

[TTrades, *Advanced Market Structure Simplified*, 11-Jul-2025](https://ttrades.com/advanced-market-structure-simplified-from-short-term-to-long-term-trends/) describe un swing intermedio como un short-term swing flanqueado por otros short-term swings del **mismo tipo**. La lectura original incluye además estructuras intermedias **rebalanced** vinculadas a FVG. **No** dice que para el *basic intermediate* el centro deba ser mayor (HIGH) o menor (LOW) que ambos vecinos: esa desigualdad está expresamente identificada por V5 como política QORE conservadora. V5 contó 24 geometrías únicas estrictas y 294 sin estricta entre los 318 contextos ambiguos V4; el cero estricto no es evidencia de ausencia de otros tipos válidos.

[TTrades, *Market Structure Shifts vs. Change in the State of Delivery*, 1-Jul-2025](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): un MSS exige **displacement + cierre más allá de swing**, a diferencia del CISD. Ni V5 ni este testigo pueden acreditar displacement/protected swing causal por sí mismos.

## Diseño fijado sin mirar nuevos resultados

- Mantener intactos V2/V3/V4/V5, COG G3 y OPS G3, NAS100 M1 histórico de desarrollo SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. Censo previo 775 días, cohorte 483 y categorías V4 `96/318/69` congeladas; V5 `24/294` no se reinterpretará a posteriori.
- En los **318** casos V4 ambiguos, usar **exactamente el primer as_of de ambigüedad V4**, el sesgo y retorno fuente validados previamente y las M1 cerradas hasta ese as_of. Calcular los swings short-term confirmados por tres velas consecutivas, mismo lado: HIGH si LONG, LOW si SHORT.
- Comparar triples sucesivos de ese mismo tipo `left,center,right` con tiempos confirmados estrictamente crecientes, `center.pivot_closed_at >= first_return_at` y `right.confirmed_at < as_of`. La geometría **literal** no aplica umbral de magnitud al centro. Exigir cierre M1 **nuevo** que atraviese el extremo del centro (LONG `previous.close <= level < current.close`, SHORT simétrico), no wick. Es un testigo QORE operacionalizado de geometría textual, **no certificación autoral**.
- Clasificar 0 / 1 / 2+ triples atravesados como `NO_LITERAL_INTERMEDIATE_BREAK`, `ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY`, `MULTIPLE_LITERAL_INTERMEDIATES_UNKNOWN`. No desempatar por precio, retorno, cercanía, dirección deseada ni PnL. Mantener estado de los otros 165 casos como `NOT_IN_318_AMBIGUOUS_SCOPE`.
- Auditoría sin selección posterior: contabilizar particiones entre V5 `STRICT_SINGLE` (24) y `STRICT_NONE` (294) con las 3 clases literales; **no se predice cuántos casos cambiarán**. Registrar cada uno de 483 por día, as_of y recuentos; comparar SHA256 del JSON completo scalar contra fork 2 procesos.
- Probar adversariales: LONG/SHORT, un triple literal no estricto, empate, ambigüedad múltiple, cierre wick-only, confirmación del vecino derecho demasiado tardía, reloj sin zona, hueco M1, as_of adelantado y ningún certificado/orden/sizing.
- Los 294 permanecen **sin resolver para certificación** incluso si aparecen triples literales: faltan rebalanced intermediate/FVG, HTF reaction, displacement y swing protegido/causante. Si hay resultados diferentes a V5, no reescribir V5 ni recontar como nuevos trades.
- Publicar script/test/workflow independientes, sin modificar producción ni merges. Probar sobre datos de desarrollo; no abrir holdout/OOS ni simular órdenes. **Método, cognitiva runtime y trader certificados = FALSE** siempre; no hay nuevos G3 firmantes humanos (#897).

## Criterios de falsación y cierre

La ronda fracasa si cambia cualquier conteo congelado V4/V5, si se presenta una M1 sin cierre causal o con gap, si se selecciona arbitrariamente uno entre múltiples candidatos, si desaparece la diferencia entre geometría literal y MSS certificado, si los JSON scalar/fork divergen o si se infiere autorización de trading. Con éxito de ingeniería el resultado será un **censo diagnóstico independiente del filtrado estricto QORE**, no un certificado M3/M7.
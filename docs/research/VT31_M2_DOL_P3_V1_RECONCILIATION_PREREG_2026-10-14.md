# VT31 — M2 ICT GENERAL | PR #930 vs PR #932 — PRERREGISTRO DE RECONCILIACIÓN
**Fecha:** 2026-10-14. **Base de trabajo:** #932 @ `e3f65b34599cc868d6cf1867dcc3df480e1e66d4`. **Verificador competidor:** #930 @ `1c820086339323f79d4ec1cb5954fb53841064b2`, módulo Git blob `bb11d965e99666957378e9748e710360dc5bb9ac`.
**Mandato:** M2/COG fuente de precios y causalidad, sin economía ni cambios de estrategia. El handoff R2 #940 define bloqueo B03.

## Hipótesis falsables
Los dos verificadores **NO deben presumirse equivalentes**. Antes de observar nuevos datos históricos, hay diferencias textuales que necesitan falsación:
1. **Cash anterior:** P3 busca hacia atrás el último cash COMPLETO presente en `history` (hasta 5 días), potencialmente salta un festivo o día incompleto; V1 exige weekday anterior exacto y no permite retroceder sin calendario. Caso crítico: weekday previo incompleto, anterior a ese completo.
2. **Sello de fuente:** P3 exige `draw_level_observed_at == source_confirmed_at`; V1 comprueba que no sea anterior al cierre ni posterior al as-of, lo que podría tolerar un timestamp tardío distinto.
3. **London pool en ventana LONDON:** P3 `REJECTED`; V1 pool `UNKNOWN` y, si DTO fue anunciado prematuramente, `REJECTED`. Diferenciar outcome por razón y precondición.
4. **M1 stale/futuros/consumo/lagunas:** cotejar estados normalizados pero conservar reasons textuales por módulo, NO etiquetar igualdad semántica por coincidencia de strings.
5. **Temporalidad DST:** observar períodos de verano/invierno y frontera exacta; no convertir una sola comparación sintética en prueba sobre mercado real.

## Diseño congelado antes de implementación
- Dos referencias de CÓDIGO congeladas arriba, nunca adoptar automáticamente una rama cambiante. Requerir hash del verificador P3 al traerlo de Git; V1 es exactamente el script del commit base.
- Construir fixture de cash con anterior exacto incompleto y un día aún más antiguo completo; DTO declarado explícitamente **PROBE sintetizado** (NO COG auténtico); comparar el par completo de estados.
- Construir fixture donde la fuente Asia tiene precio válido pero `draw_level_observed_at` es posterior al cierre: se espera **P3 REJECTED y V1 CONFIRMED** bajo cobertura continua. Es un testigo de diferencia de CONTRATO, no evidencia de mercado.
- Comparación con M1 histórica: fuente GitHub Actions artifact `11459859004`, miembro `NAS100/market-evidence.json`, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, 1.059.784 barras, development usado/no OOS. Fechas NY prefijadas: `2024-01-16,2024-04-16,2024-07-16,2024-10-15,2025-01-14,2025-04-15,2025-07-15,2025-10-14,2026-01-13,2026-04-14,2026-07-14,2026-09-15`. Observaciones 03:30, 10:30, 14:30 NY; side HIGH/LOW de cada una de 3 familias. Todos los casos, incluidos huecos, documentados, nunca filtrados por precio ni rendimiento.
- Cada fila histórica: `M1 source` real pero `COG DTO` de prueba, construido del pool V1 únicamente para **comparar contratos**; rotular `PROBE_NOT_NATIVE_COG`; NO acreditar validación cognitiva auténtica, operaciones, fills ni método ICT. No se optimiza ninguna regla. El verificador P3 no se modifica.
- Salida JSON incluye input sha, source sha, cantidad de samples, matriz pares P3/V1, casos discordantes (razones + fecha/sesión/familia/side), exclusión del gráfico económico; todos los flags de certificación **false**.
- **Expectativa:** diferencias genuinas podrán aparecer; reconciliar debe escoger luego una política conservadora sólo por fidelidad causal y calendario PIT, en un PR separado con versión propia; no inferir M2 CERTIFIED, no hacer cherry-pick de código ni alterar G3.
- QA: pruebas unitarias adversariales de las dos divergencias estructurales, source hash, GitHub Actions CI con artifact y SHA de reporte, pytest/ruff. Cualquier fuente expirada/error explícito -> RUN BLOCKED, nunca PASS.
- **Restricciones:** NO MERGE main, NO LIVE/DEMO, NO CIBO sizing dentro del trader, NO VPS, NO órdenes/ACK, NO PF/DD, NO lookahead, NO llamar a fresh holdout.

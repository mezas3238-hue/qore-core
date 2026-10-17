# VT08 B R5 — Blindaje de custodia por mercado (15-Oct-2026)

## Alcance
Continuidad de [B R4](VT08_B_R4_93230_C2_INDEPENDENT_AUDIT_COGNITIVE_WAL_FIELD_GATES_2026-10-15.md), PR #764 DRAFT, A #762 y B #763. Sin lectura de holdout 7Y, sin sizing, lotaje adaptativo, leverage, capitalización, VPS, DEMO, LIVE ni merge.

## Defecto de ingeniería observado y corrección
El verificador por campo de B R4 validaba `source_raw_sha256` contra un conjunto global de SHA sin exigir identidad de mercado. Un catálogo con barras físicas de otro mercado y una unión de hashes podía superar el cotejo de valor/tiempo. Esto NO había autorizado trading porque la certificación semántica seguía false, pero la etiqueta de trazabilidad causal podía inducir a error.

R5 requiere `source_raw_market_map` (SHA de feed -> mercado), identidad `bar_catalog[source_bar_id].market == situation.market` y rechaza incluso feeds extranjeros incluidos en `pinned_raw_shas`. El gateway `evaluate_provenanced` exige ese mapa antes de la ruta real. Tres pruebas adversariales aisladas documentan mezcla de feeds, barras cruzadas y custodia falsa. Los SHA del mapa requieren verificación externa contra manifiesto de fuente; la declaración del caller NO es firma científica ni acredita semántica TTrades. El catálogo de barras debe incluir `market`; productores previos sin ese campo fallan cerrados y requieren migración explícita.

## Evidencia y límites
La revisión B R4 verificó 93.230 C2 físicos y 2.657 recibos de PS geométrico de A, pero NO autenticó PS/CISD del autor ni produjo fills. A R3 reparó `SOURCE_COMPLETE_EXECUTABLE` falso del B01 M15 a `SOURCE_INCOMPLETE_QORE_CONTAINMENT`. Las capturas BID/ASK de QORE Native son ventanas cortas; falta historia completa alineada con entrada, SL/TP y comisiones. `APPROVED_A_B_MANIFEST_SHA256=None`. Ninguna medida de PF/DD/Sharpe/Sortino NET, OOS/MC o certificación integral es válida todavía.

## Próximos trabajos de A y B
A: semántica TTrades source-first para relevant swing PRE-C2, POI y empates, CISD/PS, breaker, EQ, SL y target untouched, con source_rule_id, bar SHA y as-of; evitar atribuir QORE-C al autor. B: validar de forma independiente el mapa SHA/mercado contra los manifests RAW, hacer revisión ciega de cada campo Situation, mantener rechazo de `evaluate_provenanced` hasta acta A/B auténtica; probar persistencia/rehidratación del WAL en ruta real y counterfactual A-only vs A+B. Owner: antes del holdout, fijar por acta los Gates económicos de VT08 y umbrales Sharpe/Sortino/densidad sin reutilizar #787 ni Alpha. OOS 7Y sigue sellado.

**Veredicto:** NOT_CERTIFIED. QA de código no equivale a edge, fills, autorización o firma. CI de R5 pendiente de verificar hasta recibir estado de Actions del nuevo commit.

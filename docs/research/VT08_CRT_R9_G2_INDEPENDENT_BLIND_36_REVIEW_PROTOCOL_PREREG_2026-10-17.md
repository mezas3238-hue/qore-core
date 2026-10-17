# VT08 CRT R9 — preregistro de caso G2 verdaderamente ciego (36 referencias competidoras)

2026-10-17. Antes de generar sobre Atlas SHA verificado, fijamos este protocolo. V1/V2/V3/G-M4 congelados y 36 conflictos C0/C1 preexistentes según R8. No performance/PnL, no operaciones, no sizing, no OOS virgin. PR #626 sigue DRAFT, sin revisión independiente GitHub comprobada.

## Defecto corregible sin alterar metodología
R5–R8 exportaba `g2-c0-c1-blind-predecision-cases.jsonl` que, aunque no mostraba C3 ni outcomes, expone `c0_direction`, `c1_direction` y `conflict_kind`. Esas etiquetas sesgan el resultado de un revisor que debe identificar el conflicto sin guía del implementador. Resolver creando un paquete **REVIEWER ONLY** y otra parte SEALED ENGINE LABELS, ambos con SHA; no mover C0/C1/ C2 ni tocar G2 WAIT original.

## Contrato de datos antes de ejecución
- Insumo: 36 objetos reales `G2_blind_predecision_case` desde replay original `real_atlas_g2_g7_bridge`, 16 AUDUSD + 20 USDJPY. Conservan exactamente C0/C1/C2 H4 cerrados, relojes, IDs; sin C3, path, terminal o PnL.
- `reviewer_only` debe contener únicamente identificador SHA-only estable por evento, market (para cotización), decision UTC, C0/C1/C2 OHLC originales y relojes H4, pregunta de método y conjunto de decisiones: `C0`, `C1`, `BOTH_AMBIGUOUS`, `NEITHER_VALID`, `INSUFFICIENT_SOURCE`. Sin `parent_id`, `source_event_id`, `parent_direction`, `reference_C0_rival_eligible`, `conflict_kind`, direcciones computadas, `G7` ni salida.
- `sealed_engine_labels` guarda solo case id, source event id, market, direcciones del motor, direcciones de conflicto, timestamps, mismo hash del payload de velas. **Sólo para verificación posterior del reviewer**; está prohibido entregar a revisor antes de dictamen.
- Orden de casos determinista pero barajado por SHA256 de case id, no por resultado. Precios, mercados y clocks siguen originales; no pretender anonimato perfecto contra búsquedas externas. Controles de ausencia de C3/labels, reloj H4 estricto, hash de evidencia, caso único, conservación 36, 14 direcciones opuestas/22 iguales solo en manifest sellado.
- Formato `reviewer_response_template.jsonl` con 36 filas vacías vinculadas a SHA por caso, sin adjudicaciones prellenadas, y preguntas de G2 y G7 firmadas separadamente. El script acepta más tarde respuestas pero no los acredita como aprobación sin revisar GitHub identity independiente, Owner, commit SHA y estado de review externo. No auto PASS bajo ningún valor del JSON.
- CI original: Ruff/mypy/pytest + AUDUSD/USDJPY, artifacts SHA, reviewer-only y sealed por separado; CI verify 0 fugas literales hacia reviewer-only, 36/36, 14+22. No publicar receptor review si no existe.

## G7: tema para firma anterior a nuevo OOS
Política A `GLOBAL_ALL_PRIOR_TERMINAL` (bloquea 108 casos desde 5 UNKNOWN) versus política B `SOURCE_LINEAGE_SCOPED` (solo eventos de cadena causal certificada). No elegir por densidad retrospectiva ni declarar B fuente-supported sin evidencia. El artículo G7 y política de venue/cierre requieren análisis metodológico independiente y consentimiento Owner PREVIO a OOS.

## Estado que debe conservarse
G-M1..4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED; 139 V3 original, 5 G-M4 UNKNOWN sin alterar, 108 G7 WAIT, G2 WAIT 139, 0 rearm, 0 broker orders, no sizing (ni 1R ni lotes). Certificación requiere revisión independiente real #976, 48 G-M2, OOS nuevo, Gates globales bajo CIBO Risk.

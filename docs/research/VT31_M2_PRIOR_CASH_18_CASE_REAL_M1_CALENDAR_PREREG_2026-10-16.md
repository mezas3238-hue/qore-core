# VT31 M2-PIT — Prerregistro del contrafactual de calendario cash en los 18 REJECTED (16-OCT-2026)

Origen de casos **sellados antes de este código**: PR #993 [GitHub Actions #38975891228 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38975891228), casebook JSON SHA256 `d74b24242c4b8c5656547727b88886ecd1a18243c362d9d366825880bddbfc21`; exactamente 18 con motivo `COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE` y todos `PRIOR_NY_CASH_SESSION_HIGH/LOW`. Tabla con 18 fechas, sesión NY, precio, origen original y cierre del rango nominal en `docs/research/VT31_M2_TRISESION_DOL_REAL_PROVENANCE_18_CONTRADICTIONS_2026-10-16.md` (commit `e2072645802cdb443f149478ec0b40e20c24b668`). No seleccionar fechas basadas en resultados de este nuevo experimento.

**Pregunta:** ¿G3 eligió una sesión cash anterior por falta de cobertura de la sesión nominal inmediata, o seleccionó una sesión antigua pese a haber cash completo más reciente? ¿El nivel marcado por G3 coincide literalmente con HIGH/LOW de las 390 M1 cash 09:30–16:00 de la fecha que marca `draw_level_observed_at`?

**Prereg**: usar original NAS100 1.059.784 M1 SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, NO broker tick bid/ask. Fijar 18 casos del CI anterior (NY fecha, ventana, DOL HIGH/LOW, precio, último cash elegido fechado por G3); alimentar lectura cronológica una vez y capturar **todos los días hábiles entre el día fuente G3 y la sesión actual**. Determinar para cada día cash nominal 390 velas consecutivas completas según reloj America/New_York y comparar extrema únicamente cuando la fuente esté completa. Nunca interpolar; `PARTIAL_OR_MISSING` NO prueba cierre del CFD ni imposibilidad de trading. Computar `most_recent_source_complete_cash_day` y `newer_complete_cash_days_than_G3` para evitar inferir que G3 eligió la última sesión válida sin evidencia.

Etiquetas predefinidas sin juicio económico:
- `OLDER_G3_CASH_SOURCE_COMPLETE_AND_PRICE_MATCH` si exactamente 390 M1 de su día y extrema HIGH/LOW coincide con el precio G3. No significa que haya sido la sesión metodológicamente correcta.
- `OLDER_G3_CASH_SOURCE_INCOMPLETE_UNKNOWN` si faltan velas, no atribuir precio por historia insuficiente.
- `OLDER_G3_CASH_SOURCE_PRICE_DISAGREES` si fuente completa pero price no coincide.
- `NOMINAL_PRIOR_WEEKDAY_FULL_M1` / `NOMINAL_PRIOR_WEEKDAY_M1_INCOMPLETE_UNKNOWN`.
- `NEWER_COMPLETE_CASH_DAY_EXISTS` cuantificado por fechas para casos en que G3 miró cash anterior aun existiendo día completo más nuevo. Sigue pendiente si selección intencional por DOL no consumido o bug.

Tests con EST/EDT, sesgo, 389/390 M1, falsificación de high/low, fechas fijas, no futuro, sin precios económicos. CI reproduce corpus, calcula SHA caso por caso y añade artefacto; no modifica G3 original, `vt31_ict_dol_source_v1_20261014.py`, OPS, trader nativo ni regla H1 solo NYAM. Si una fecha es conflicto STOP, no inventar calendario PIT ni cambiar regla G3.

**Dictamen posible:** `M2_CASH_CALENDAR_SOURCE_GAP_TRIAGE_RESEARCH_PASS`, no certificación ICT/TTrades. Se requieren documentos broker NAS100 PIT, adjudicación Owner policy de `prior cash`, M3–M5, firmas independientes humanas M6 #897, M7 tres certificados; 0 sizing/orders/PNL/DEMO/LIVE.
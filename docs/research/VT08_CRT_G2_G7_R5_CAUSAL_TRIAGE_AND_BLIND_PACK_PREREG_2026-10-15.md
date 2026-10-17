# VT08 CRT R5 — pre-registro de diagnóstico G7 WAIT y pack blind G2

**2026-10-15.** Registrado antes de ejecutar un nuevo análisis Atlas. R4 fuente congelada: run #38802320161 / commit 2c23ddd72df6238e2ca3331ed3350e131ae4a5bb, 139 V3, 36 referencias competidoras C0/C1, 108 G7 WAIT, 5 UNKNOWN G-M4. No introducir nuevo filtro de rentabilidad, no backtest nuevo, no modificar V3 o G-M4. No sizing, R simulado, lotes, capital, orders ni VPS.

## Hipótesis de fallo P0
La política G7 actual exige **terminal causal probado de todas las tesis históricas previas**. Un único registro anterior con terminal desconocido hace WAIT para cada fuente posterior de ese mercado hasta resolver dicho registro. El total 108 WAIT puede ser efecto de propagación de pocos UNKNOWN, y no significar 108 invalidaciones ni 108 señales sin dirección. Medir exposición y primer bloqueo en el punto de decisión; contrastar **después** contra el G-M4 ya observado, sin mezclar análisis ex-post con decisión causal.

## Métricas R5 preregistradas

Por cada fuente futura V3, sin usar C3 futuro: g7_prior_causal_terminal_missing_count, g7_first_prior_missing_source_id, g7_first_prior_missing_decision_clock, g7_pending_prior_count, g7_rearm_policy_verdict, g2_c0_competitor_present, g2_c0_opposes y snapshots SOLO de C0/C1/C2 H4 completos. No se incluirán outcomes de G-M4 en la bitácora de la decisión, solo si un terminal ya era observable antes de esa hora.

**Separado y etiquetado EX_POST_DIAGNOSTIC (nunca entrada):** usando G-M4 original ya congelado, clasificar cada G7 WAIT según cantidad de previos UNKNOWN definitivo vs previos con terminal conocido pero posterior al tiempo de esa decisión. Calcular el primer caso UNKNOWN que puede explicar WAIT permanente y los eventos sucesivos alcanzados por ese veto. No confundir fuente UNKNOWN con resultado económico, ni permitir retroactivamente entrada cuando conocemos algo después.

Para G2: generar **pack de adjudicación ciega** solo de conflictos C0 contra C1 (incluidos iguales/opuestos) con H4 C0/C1/C2 OHLC originales y reloj de cierre, ID y hash del evento. Sin C3, sin terminal, sin precio de resultado, sin información futura, sin profit/PnL, sin capital. Pack incluye controles de causalidad y manifest SHA256. Es un conjunto **acotado**: NO demostrar exhaustividad de old CRTH/CRTL. No pedir o fingir firma del evaluador.

## Aceptación técnica
- Reproducir exactamente 61 AUDUSD/78 USDJPY y 2+3 UNKNOWN, sin modificar V1/V2/V3 ni G-M4.
- Causal/puro: mutar los terminales actuales/futuros no puede cambiar decisiones G2/G7 previas; solo cambia el análisis EX_POST separado cuando corresponda. Referencias siempre cerradas antes de decisión.
- 108 WAIT deben conciliar con categorías causales y ex-post sin duplicación, y 36 competidoras deben generar el pack completo.
- Si la infraestructura CI o los originales Atlas fallan, reportar FAIL y corregir sin alterar resultados del generador.
- G-M1..G-M4 PARTIAL, G-M5 NOT ISSUED y Global NO CERTIFICADO, con independencia humana todavía ausente.

**Riesgo de interpretación:** La política ALL-PRIOR-TERMINAL es propuesta QORE, todavía no aprobada por las tres fuentes ni por auditor. Un bottleneck no autoriza relajarla por rendimiento. La resolución metodológica debe ser separada del reestudio de edge y fijarse antes de nuevo OOS.

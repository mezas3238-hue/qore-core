# VT08 CRT R10 — preregistro del validador de 36 dictámenes G2 y firma externa G-M1

**2026-10-18.** Alcance de investigación, **no certificado**. Los 36 expedientes reviewer-only R9 fueron precomputados sin etiquetas G2 ni C3 futuro: AUDUSD 16, USDJPY 20. El estado GitHub PR #626 al iniciar la ronda: **0 reviews nativas**, G-M1..4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED. Ya existe un validador externo R1 (`crt_pure_gm1_external_review.py`) que exige token y trusted IDs fuera del PR, valida approval/head/dossier SHA y **no emite G-M1 PASS**. R10 reutiliza ese concepto, NO crea otra firma ni aprueba por sí mismo.

## Defecto de flujo pendiente y aceptación pre-registrada

Las plantillas R9 contienen `human_choice=null` por diseño. Falta un contrato que compruebe que **todos** los 36 casos tengan elección, localizador tri-fuente y razón causal ligada al SHA de la vela original sin permitir sustitución, outcome-hindsight o auto certificación.

1. Leer **solo reviewer-only** y respuestas; **NO abrir sealed labels** antes de firma. Rechazar market contrario, SHA manipulado, reordenamiento silencioso, duplicado, falta de case o caso extra, `human_choice` fuera de C0/C1/BOTH_AMBIGUOUS/NEITHER_VALID/INSUFFICIENT_SOURCE, fuentes vacías, explicación insuficiente o afirmación de G-M1 PASS, owner/reviewer GH verified en JSON editable.
2. Versionar un resumen de **integridad SHA**, no interpretar la elección C0/C1 como validación de un old-CRT level. Si choice=INSUFFICIENT_SOURCE, permitir al revisor documentar insuficiencia explícita sin fabricar cita de autor, y contar por separado `INSUFFICIENT_SOURCE`. Una cita `QORE_ENGINEERING:<rule/version>` es propuesta, nunca fuente primaria.
3. El validador puede declarar `structurally_complete=true` SOLO si el contenido es íntegro y firmado por humanos después en GitHub; incluso entonces debe permanecer `methodology_independently_approved=false`, `G_M1_PASS=false`, `G_M5_ISSUED=false`. La autoridad de identidad sigue exclusivamente en R1 desde un entorno protegido. Nunca confundir tests sintéticos con personas reales.
4. Sobre el artefacto R9 real ejecutar **con respuestas NULL** para demostrar que la puerta responde `NOT_READY` con 36/36 pendientes; CI NO puede reclamar certificación si el baseline está vacío. Publicar solo conteos, SHA y blockers de no aprobación, nunca mezclar engine sealed en reviewer-only.
5. Mantener 139 V3/5 UNKNOWN/108 G7 WAIT y V1/V2/V3 intactos. Sin sizing de VT08 en ninguna forma, PnL, lotes ficticios, riesgo/capital, órdenes/demo/live/VPS/merge. CIBO Risk conserva DD/capital y los futuros Gates económicos.

## Definición de cierre R10
Tests adversariales + Ruff/mypy + 2 matrices originales Atlas sobre 36 expedientes, salida reproducible y SHA. Hasta completar review auténtica por Owner y tercero distinto, sigue G-M1..4 PARTIAL, G-M5 NOT ISSUED y global NOT CERTIFIED.

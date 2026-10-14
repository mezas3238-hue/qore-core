# VT31 — ICT_DOL_SOURCE_V1 · PRE-REGISTRO M2
Fecha: 2026-10-14. Base congelada: `54ed47d35db25df5c47115cac6888da4c58801d7` (PR #929). Handoff PR #931.
**Este documento se registra antes del código y de ejecutar pruebas del nuevo testigo.**

## Pregunta falsable
¿Podemos verificar **independientemente del `CognitiveDecision`** que el precio señalado por la COG procede de un extremo de un intervalo M1 completo, ya cerrado y aún no tocado con evidencia disponible, en LONDON 03–04 / NY AM 10–11 / NY PM 14–15?

## Alcance de la prueba
No es una afirmación de que ICT obligue a perseguir estos pools ni de que su alcance explique rentabilidad: `PRIOR_NY_CASH_SESSION`, `ASIA_NY_CLOCK` y `LONDON_NY_CLOCK` son **formalizaciones QORE** del mercado. Fuente M1 original, horario NY con DST, sólo barras cerradas `closed_at <= as_of`. La identidad del COG existente no cambia; se verifica externamente. TTrades NY AM 09 H1 opuesto tiene su testigo especializado #929 y no se sustituye.

## Definiciones congeladas (sin afinar por PnL)
- `PRIOR_NY_CASH_SESSION`: último **weekday anterior** (lunes→viernes anterior) NY 09:30–16:00, **390 M1 exactas**. No tenemos calendario de festivos/early-close PIT en este contrato: un día hábil sin 390 barras devuelve `UNKNOWN`, **NO** retroceder silenciosamente a un día favorable. Lunes→viernes precedente aunque medie fin de semana; feriados requieren calendario externo auditado.
- `ASIA_NY_CLOCK`: **día local actual** 00:00–03:00, 180 M1 exactas. `LONDON_NY_CLOCK`: día local actual 03:00–05:00, 120 M1 exactas, **sólo** si ese intervalo ya terminó (NY AM/PM); no emitir pool londinense completo para SB de 03–04.
- Cada intervalo produce `_HIGH` y `_LOW` con high/low M1 originales y `source_start/source_end`. Side LONG sólo puede usar HIGH y SHORT LOW de su familia declarada. El target del DTO debe coincidir *exactamente* con el extremo observado; un tick distinto es refutación, no redondeo a posteriori.
- `CONSUMED`: cualquier M1 cerrado después de la confirmación tocó el nivel (high >= nivel / low <= nivel). `UNCONSUMED`: ninguna M1 lo tocó y la cadena M1 desde cierre del pool hasta `as_of` es completa. `UNKNOWN`: huecos de cobertura, insuficiencia de M1, ausencia de historial, ventana todavía abierta, precios futuros o ambiguos (en este último caso rechazar input inválido), sin asumir ausencia de negociación. Las fechas de fuentes se calculan sin usar COG.
- Nunca completar huecos ni inferir orden intrabar de barridos; el contacto de un nivel aislado sí es observable en OHLC, pero simultaneidad de dos niveles **no define cuál ocurrió primero**.
- `CONFIRMED` es exclusivamente origen, nivel, cronología y no consumo **bajo cobertura disponible**. No acredita dirección ict autoral, MSS, desplazamiento, FVG, entrada, SL, PF ni trading. `REJECTED` sólo si contradice fuente reconstruida; `UNKNOWN` para pruebas insuficientes. Siempre `method_certified/cognition_certified/execution_authorized = false`.

## Diseño adversarial obligatorio (antes de ver respuestas)
1. LONG y SHORT para cada familia en los tres horarios elegibles; DST invierno/verano.
2. M1 incompleta, duplicada, sin orden, fuera de `as_of`, source aún abierto y deadline de ventana.
3. Cash previous weekday no presente/early close/festivo; lunes→viernes previo; no fallback a pools de otro día.
4. Nivel tocado tras formación: NO rehabilitarlo porque el precio regresó. Gaps tras fuente con ninguna observación de toque: UNKNOWN, NO declarar limpio.
5. COG genuino equivocado de familia, lado, nivel, timestamp y target consumido; expectativa REJECTED sin generar un DTO propio.
6. M2 no reetiqueta V2 como certificado ni modifica fuentes originales G3. Testimonio solo; regresión #926/#928/#929 + COG/OPS/M1/G3.
7. Registros en GitHub: prereg SHA, módulo, tests, workflow, CI exacta, hashes SHA256 y PR DRAFT. Si el CI falla, informar sin maquillar resultados.

## Criterio ex ante
**PASS técnico acotado** si todas las pruebas adversariales de M2 y regresiones corren en CI verde sobre mismo SHA, G3 blobs intactos. **PENDING método** hasta COG per-profile real, MSS/M4/M5, revisión M6 y evidencia M1 en muestra real; **economía M7 separada**. Sin MERGE, LIVE, VPS, sizing, broker/OMS, Fresh Holdout ni optimización por PnL.

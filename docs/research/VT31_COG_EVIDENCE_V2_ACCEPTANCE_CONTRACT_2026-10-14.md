# VT31 COG_EVIDENCE_V2 — aceptación metodológica, no trading

**14-OCT-2026 · Preregistro anterior al código V2 y pruebas.** Hereda [PR #926](https://github.com/mezas3238-hue/qore-core/pull/926), fuentes ICT 2023 / TTrades AM 2025 y G3 intacto.

## Objetivo concreto

Convertir la salida auténtica `CognitiveAssessment` + `CognitiveDecision` de `VT31CleanroomCognition.assess()` y el historial de M1 **cerradas en el mismo as-of** en un registro `COG_EVIDENCE_V2` trazable, versionado e inmutable por evento. La salida es una **evaluación de fidelidad cognitiva en investigación**, nunca una orden, permiso de sizing, G3 aprobado, rentabilidad ni certificación del trader.

La clasificación cerrada es `CONFIRMED`, `REJECTED`, `UNKNOWN`:
- **CONFIRMED** exclusivamente para `TTRADES_NY_AM_2025` si el `CognitiveDecision` y el comprobador de contexto de #926 satisfacen causalmente H1 09–10, sweep posterior, MSS posterior que vuelve al rango y DOL H1 opuesto. Confirmar contexto **no** certifica internamente pivote ICT auténtico, displacement discrecional de TTrades, familia/stop, ni edge.
- **REJECTED** cuando hay una contradicción verificable (ej. hora/perfil incorrecto, DOL incompatible, lado del sweep contradice señal, MSS antes de sweep, doble sweep, evidencia futura): la razón y testigos se guardan.
- **UNKNOWN** cuando faltan datos causales para pronunciarse (sin historia H1 completa, gaps M1, sin COG aprobado, COG no evaluable, MSS sin testigo, perfil ICT general aún no totalmente formalizado). No promover UNKNOWN a REJECTED mediante suposiciones ni a CONFIRMED mediante forward-fill.
- `ICT_GENERAL_2023` cubre Londres/NY AM/NY PM y **no hereda filtro H1 09–10** de TTrades; mientras no haya verificador autoral específico para cada ventana debe retornar `UNKNOWN_SOURCE_DOCTRINE_NOT_FORMALIZED` (sin falso juicio negativo).

## Evidencia inmutable y contrato

Un registro por estado de `CognitiveAssessment` contendrá: `schema`, `profile`, `status`, `reasons`, `assessment.as_of`, `session`, `COG.state`, `COG.decision.side`, `COG.shift/MSS timestamp`, `observed DOL/family`, `9AM high/low`, `first_sweep_close`, `target expected`, `last M1 close`, `source_bar_count`, `sha256` canónico **solo de hechos as-of presentes en el DTO y secuencia M1 cerrada**. No exponer decisiones ajenas al repositorio ni datos posteriores a as-of. Cualquier as-of incoherente/gap/duplicado es UNKNOWN o REJECTED según sea ausencia vs contradicción, nunca confirmar.

`CognitiveAssessment` real se consume sin alterar `cognition.py`, `contracts.py` o `operations.py`. Las pruebas incluirán DTO sintético factible, mutación de DOL/side, wick con dos sweeps, MSS previo, missing H1, future M1, G3 mss close si aplicable, ICT London/PM sin raid NY AM, decisión faltante, determinismo digest, y todos los flags de trading falsos. Una sombra evalúa resultados COG sin convertirse en filtro instalado.

## Gates explícitos

- **P0 testigo:** software QA adversarial exitoso, integridad SHA256/Git y regresión preexistente. `SOURCE_WITNESS_IMPLEMENTED` es admisible.
- **COG semánticamente certificado:** requiere testigos de MSS structural *independientes* al productor, casos positivos y negativos de fuente autoral ICT/TTrades (o definición explícita QORE), y perfiles finalizados. NO cumplido por P0.
- **Trader/economía certificado:** requiere G3 auténtico firmado, FVG/OB/Breaker confirmados, stop/target ejecutables, BID/ASK+ACK y replay económico/OOS. NO forma parte de V2.

**Controles soberanos:** NO MERGE, NO LIVE, NO VPS, no FundedNext LIVE, no QDLE/sizing, no uso del holdout. G3 acta `a446afa17ed6e411b8f0b6fc182b103a78959a97` y código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` son inmutables; dos firmas COG/OPS no se simulan.

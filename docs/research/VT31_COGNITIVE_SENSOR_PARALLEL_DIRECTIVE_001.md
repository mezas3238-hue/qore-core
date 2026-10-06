# VT31 — Directiva de sensores cognitivos paralelos

**Estado:** activa, solo diagnóstico.  
**Fresh Holdout:** sellado.  
**Autoridad económica:** ninguna.

El objetivo común es observar la cadena completa:

`INPUT -> COGNITION -> REASONING -> POSITION OUTPUT -> ACTUATION`.

## Arquitecto principal

Mantiene el esquema canónico de telemetría y los sensores generales:

- disponibilidad de inputs;
- estados UNWIRED / UNAVAILABLE / UNKNOWN / UNCALIBRATED;
- cobertura de dominios cognitivos;
- blockers de máxima inteligencia;
- acción de reasoning;
- salida completa HOLD / TRAIL / EXTEND / EXIT;
- estado de enrutamiento de esa salida.

## Arquitecto paralelo

Queda autorizado para colocar sensores complementarios, sin cambiar política
económica, específicamente alrededor de:

- `structure_invalidated`;
- `liquidity_failure_confirmed`;
- `regime_changed_against_thesis`;
- instante causal en que cada hecho se vuelve observable;
- número de llamadas al productor y al consumidor;
- valor que entra a MarketFacts / Situation;
- PositionAction que sale;
- comprobación de llegada al siguiente actuador M1 válido.

Debe reutilizar el vocabulario de
`vt31_nas100_cognitive_telemetry.py` y no crear un segundo motor de decisión.

## Clases mínimas de fallo

Los informes deben distinguir:

1. INPUT_MISSING_OR_UNWIRED
2. COGNITION_BLOCKED_OR_INCOMPLETE
3. OUTPUT_NOT_ROUTED
4. ROUTED_NOT_EXECUTED
5. ROUTED_AND_EXECUTED
6. ALIGNED_NO_ACTION

Los sensores son read-only. Pueden estudiar resultados terminales después del
trade para atribución, pero resultado, fecha o fold nunca pueden convertirse
en autoridad runtime.

Sin sizing, leverage, compounding, portfolio/capital weighting ni rescate CIBO.

VT31 sigue **NO CERTIFICADO** y Fresh Holdout permanece sellado.

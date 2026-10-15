# VT31 — PRE-REG M0-B: invocación COG genuina vs declaración optimista (15-Oct-2026)

**Base:** Handoff Maestro R5 #975, #971 router y PR #978 temporal. **Problema observado por inspección de código:** `scripts/vt31_m0_predecision_method_router_20261015.py` usa `emit(... original_cog_invoked=True)` de forma incondicional. Sin embargo, `ttrades_source_first_g3_cognitive_proposal` puede retornar `TTRADES_SOURCE_NOT_CONFIRMED_WAIT` o `TTRADES_SOURCE_UNKNOWN_WAIT` antes de construir `VT31CleanroomCognition`. Así un WAIT causa evidencia COG falsamente positiva. Este arreglo no altera metodología del autor ni la decisión de trading.

## Cambios preregistrados ANTES de código
1. El objeto `SourceFirstCogProposal` exportará booleano `original_cog_invoked` que solo será **true tras ejecutar `engine.assess()`**, y será false en cualquier retorno pre-COG. Congelar en dataclass inmutable y serialización de investigación.
2. El router #971 propagará `source.original_cog_invoked` en lugar de fijar true para TTrades. El camino ICT GENERAL que sí evalúa el COG conservará true, pero con `ICT_CONTEXT_WITNESS_UNDERDETERMINED` sin fuente homologada.
3. Contraprueba principal: NYAM H1 09 incompleta (una M1 del día removida) usando **router #971 directamente, sin puerta #978**, retorno WAIT sin invocación original. Capturar divergencia que puerta #978 bloquea por separado.
4. Contraprueba alternativa: NYAM H1 intacta pero MSS final ausente; si la fuente llegó a la evaluación, `original_cog_invoked=True` incluso si el COG devuelve `decision=None`, distinguiendo llamadas de LONG/SHORT.
5. Los 16 escenarios originales (4 compatibles TTrades, 4 WAIT MIN10, 8 ICT UNKNOWN) conservan estados y decisión exactamente iguales con bandera verdadera cuando COG se ejecutó.
6. Tests originales y nuevos en pytest-xdist + Ruff; hashes originales G3 COG/OPS y acta idénticos. No cambian certificados, perfiles, source authority, OOS, rentabilidad, sizing, órdenes ni autorización.

**Falsador:** cualquier retorno antes de `engine.assess` registrado como invocación true, o cualquier escenario válido que deje de invocar el COG, invalida la ronda. La ausencia de firma COG+OPS sigue impidiendo certificar.

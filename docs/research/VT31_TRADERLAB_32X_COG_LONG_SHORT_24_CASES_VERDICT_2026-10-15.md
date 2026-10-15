# VT31 — Dictamen TraderLab Fast Forward: 24 escenarios LONG/SHORT, COG ORIGINAL, 1× vs 32×

**15-OCT-2026.** Encargo Owner: agilizar pruebas con Trader Lab / QORE Research, certificando por metodología y cognitiva, **no por Profit Factor, Drawdown ni rentabilidad**. Se completó nueva ronda de CI reproduciendo COG G3 ORIGINAL sin modificar ni hacer backtest económico.

## Evidence y reproducibilidad
- [PR #967 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/967), rama `agent/vt31-traderlab-32x-bidirectional-cog-20261015`, apilada sobre PR #965.
- Prereg pre-código `38030ba2d8cabbf73fa1c2c2c5d3b7d7cf67961f`: archivo `docs/research/VT31_TRADERLAB_32X_COG_LONG_SHORT_PREREG_2026-10-15.md`.
- [GitHub Actions #38747782153 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38747782153), SHA de código y tests exacto **`87afbc7908555f51d0c343c4d3d51b8664111710`**, **69/69 pytest PASS**, Ruff y py_compile PASS, 3 blobs G3 COG/OPS/acta SHA protegidos PASS; 4 workers `pytest-xdist -n 4`.
- [Artifact #11979797382](https://github.com/mezas3238-hue/qore-core/actions/runs/38747782153/artifacts/11979797382), ZIP SHA256 **`a77be5d7c66a767a4f0724f2b981571f3972fc0eee992a2b9b2ea70c7ccad25b`**, contiene `VT31_TRADERLAB_NATIVE_32X_G3_COG_BIDIRECTIONAL_24_CASES.json`, `junit.xml`, `summary.json`, SHA256SUMS, commit exacto.
- Fallos previos: primera CI ni arrancó porque el nombre de step YAML tenía `:` sin comillas; segunda CI Ruff E741 variable ambigua `l` de espejo, corregidos sin cambiar ninguna vela, expectativa ni COG; tercera CI 69 PASS.

## Resultado estrictamente cognitivo
| Sesión COG auténtico | Temporada | LONG espejo MSS134→close136→DOL150 | SHORT MSS96→close94→DOL80 | Contrafactual cambiando SOLO último close |
|---|---|---|---|---|
| London | Enero EST | LONG igual en 1×/32× | SHORT igual en 1×/32× | LONG close133→WAIT, SHORT close97→WAIT |
| NY AM | Enero EST | LONG igual en 1×/32× | SHORT igual en 1×/32× | ambos WAIT |
| NY PM | Enero EST | LONG igual en 1×/32× | SHORT igual en 1×/32× | ambos WAIT |
| London | Julio EDT | LONG igual en 1×/32× | SHORT igual en 1×/32× | ambos WAIT |
| NY AM | Julio EDT | LONG igual en 1×/32× | SHORT igual en 1×/32× | ambos WAIT |
| NY PM | Julio EDT | LONG igual en 1×/32× | SHORT igual en 1×/32× | ambos WAIT |

**24/24 casos** se construyeron de 3 ventanas × 2 estaciones × 2 direcciones × MSS/WAIT; se ejecutaron dos instancias independientes originales de `VT31CleanroomCognition` por caso y se compararon source M1 SHA256, `CognitiveAssessment` completo (`state`, missing reasons, side, DOL, MSS timestamp/as-of y `source_provenance`), y hashes de traza. Todas las M1 fueron entregadas sólo al cierre y el constructor nativo `TraderLabFastForwardSchedule` visitó **exactamente** los mismos timestamps.

Los LONG no se eligieron mirando PnL: estaban prescritos antes del código como espejo geométrico de SHORT de PR #955 `p'=230-p`; cambio HIGH↔LOW respeta OHLC y timestamps, cash HIGH150 y pivote134/cierre136. Casos sin MSS sólo alteran último cierre LONG136→133 o SHORT94→97, sin modificar wick ni historia. El COG no anticipó ruptura en ninguno. Eso prueba una simetría funcional en este conjunto **SINTÉTICO**, no fidelidad autoral ICT/TTrades completa.

## ¿Qué permite acelerar? ¿Qué NO?
- **SÍ:** la infraestructura nativa de Trader Lab para 32× de calendario simulado sin lookahead, ejecución paralela `pytest-xdist` de pruebas, auditoría reproducible de LONG/SHORT/WAIT y diferencias de método sin consultar PnL.
- **NO:** afirmar 32× CPU real; calificar TraderLab L3 de VT31 sin candidate binding y cronología canónica M1 real; certificar fuente ICT general o TTrades por pasar sintéticos; invocar PF/DD/Sharpe como umbral de esta dimensión; abrir cuentas u operaciones.

## Estado de certificación / handoff de continuidad
`CERTIFICADO_METODOLOGIA=PENDIENTE`, `CERTIFICADO_COGNITIVA=PENDIENTE`, `TRADER=NO_CERTIFICADO` conforme al [tribunal #964](https://github.com/mezas3238-hue/qore-core/pull/964). La nueva paridad aumenta cobertura M1 funcional de cognitiva y no solventa requisitos M0 selector real de perfil, MSS de fuente, selección de familias OB/Breaker, swing stop causante, revisión autoral ciega y las dos firmas COG+OPS independientes [#897](https://github.com/mezas3238-hue/qore-core/issues/897). El Owner requiere continuar hasta certificar; no se deben inventar firmas ni declarar certificado por pasar una CI.

Sin MERGE, LIVE/PRODUCCIÓN, broker órdenes/fills, FundedNext LIVE, VPS ni lotaje propio de trader: CIBO CMA autoridad exclusiva. Este documento se añade después del commit de código CI probado; no declarar que texto posterior se ejecutó.
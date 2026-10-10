# QORE Scalper — A1 V3: segunda estructura CISD protegida M1 y llegada a Master Frame

**Fecha:** 2026-10-10 | Responsable: A1 Cognitiva | PR #758 | Revisión metodológica B: PR #759 | GitHub-only, investigación sin merge, VPS, QORE Risk authority, MT5 ni LIVE.

## Hallazgo verificado en histórico provider-native M1 9/9

[**Run #38085489622 — SUCCESS, 11/11 trabajos**](https://github.com/mezas3238-hue/qore-core/actions/runs/38085489622), con datos originales nativos M1 [#35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), los 2.876 `V49Opportunity` originales [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), y la taxonomía ya congelada V2 [#38083508578](https://github.com/mezas3238-hue/qore-core/actions/runs/38083508578). **Ninguna señal fuente se eliminó, modificó o seleccionó retrospectivamente.**

La V2 sólo clasificaba el **primer** CISD estructural observado tras la tesis M15, y por eso podía dejar como `PRIOR_CONFIRMED_BREACHED` un setup donde un *segundo* pivote posterior sí estaba protegido antes de entrada. La V3 enumera sucesivos pivotes por su instante de origen (`swing_occurred_at`), no salta por la fecha tardía de confirmación, y exige **que el precio no vuelva a tocar el swing desde el momento de ocurrencia hasta la entrada M1**, además de estar en el lado correcto del cierre original. No lee ninguna vela posterior al M1 source; tampoco emplea resultados de operaciones seleccionadas/rechazadas.

| Clase causal V3 | FVG_RETRACE_CISD | LIQUIDITY_SWEEP_CISD | Total |
|---|---:|---:|---:|
| Fuente ya tenía evidencia V2 de swing estructural intacto | 1.115 | 770 | **1.885** |
| **Segundo pivot o posterior confirmado e intacto** | **371** | **119** | **490** |
| Pivot confirmado, pero ninguno de los sucesivos estaba intacto | 23 | 134 | **157** |
| Ningún nuevo pivot estructural confirmado por detector base | 2 | 342 | **344** |
| **Total idéntico source-ID** | **1.511** | **1.365** | **2.876** |

**Nuevo total contextual de protected-swing evidence = 2.375 / 2.876 (82,58%).** Restan **501 (17,42%) sin esta evidencia estructural estricta**: 157 confirmados pero ya vulnerados; 344 sin pivote estructural de tres velas. **Es incorrecto presentar 501 como señales inválidas o un veto TTrades**: la ruta `LIQUIDITY_SWEEP_CISD` puede permitir un comportamiento que no sea el protected pivot del observador estructural, a determinar por B con fuente original.

| Mercado | IDs V49 | Ya probados V2 | Nuevos intactos V3 | Confirmados luego rotos | Sin segundo pivot |
|---|---:|---:|---:|---:|---:|
| AUDJPY | 282 | 191 | 42 | 15 | 34 |
| AUDUSD | 275 | 166 | 54 | 20 | 35 |
| EURUSD | 332 | 222 | 53 | 16 | 41 |
| GBPJPY | 300 | 185 | 54 | 16 | 45 |
| GBPUSD | 329 | 217 | 55 | 20 | 37 |
| NAS100 | 361 | 234 | 74 | 17 | 36 |
| USDCAD | 320 | 206 | 55 | 22 | 37 |
| USDJPY | 297 | 211 | 31 | 16 | 39 |
| XAUUSD | 380 | 253 | 72 | 15 | 40 |
| **TOTAL** | **2.876** | **1.885** | **490** | **157** | **344** |

**Limitación metodológica concreta**: se usa el detector estructural *ya presente* en QORE V48, **NO una verificación independiente del autor TTrades**. V49 reproduce sus 2.876 source routes con sus detectores; esa consistencia de código tampoco valida contra reglas/videos. Las **381 discrepancias CISD** del shadow A2 permanecen como evidencia adversarial; no son filtros. No se han tocado 12 casos M15 y 124 H1 aún sin prueba previa, ni demostrado `FULL_COGNITIVE_MASTER_FRAME` en histórico 9/9.

## Código, contratos y alcance cognitivo real

`src/qore/infrastructure/trader_lab/capitalizer_a1_m1_second_pivot_forensics_v3.py`: 
- El constructor `review_second_pivot(source,first,m1)` exige ID, símbolo, familia, tiempo M1 y precio del control V49 y cadena anterior V2. Rechaza M1 posterior a decisión. Examina desde el instante de la tesis M15; reobserva cada CISD `observe_first_structural_cisd` desplazando `after` según `pivot.closed_at`; conserva todos los testigos con `swing_at`, `confirmed_at`, precio y clasificación. Solo el mejor pivot aún intacto se identifica como testigo V3.
- `attest_market()` exige manifest provider-native solo lectura, los IDs exactos V2 por `source_opportunity_id` y el libro original V49. Da JSONL por operación y resumen por activo. `aggregate_nine_market()` comprueba que todos los nueve mercados coinciden, total 2876, previa V2=1885 y 0 cambios/vetos.
- Tests `test_capitalizer_a1_m1_second_pivot_forensics_v3.py` construyen dos pivotes M1 reales en fixture: primero vulnerado, segundo confirmado y preservado; también segundo vulnerado, source ajeno, vela futura y false authority. **Estos fixtures prueban invariantes, no resultados económicos históricos.**

`src/qore/infrastructure/trader_lab/capitalizer_a1_sensorized_paper_runtime_v1.py` ahora tiene `m1_secondary_reviews: Mapping[str, A1SecondPivotReview] | None` (opt-in). Si se suministra, requiere **todo** el ledger V2 y V3 por IDs fuente originales, confronta familia, tiempo, source ID y `previous_class`. V3 se añade como tokens de WHY/provenance **en `A1MultiHypothesisBarrier.alternatives[].context.observation_tokens` ANTES de la llamada al auténtico full Master Frame y Trader PAPER**. Contadores: `secondary_m1_route_reviews_received` y `newly_intact_second_m1_context_count`. No cambia `M1_PROTECTED_SWING_ATTESTATION` a OBSERVED automáticamente, no cambia la selección ni crea permiso de operación. Los testigos ya revalidados M15/H1 y M1 estricto siguen llegando por `independent_source_witnesses` opcional.

**Calidad de código tras integración en el HEAD**: [Repositorio Cognición audit #38085788648](https://github.com/mezas3238-hue/qore-core/actions/runs/38085788648) **Ruff PASS, Mypy 1.648 archivos PASS, 57 pruebas PASS**, y [Causal #38085788635](https://github.com/mezas3238-hue/qore-core/actions/runs/38085788635) **56 tests PASS**. Las pruebas de sensor A1 también prueban el puente enriquecido con V2+V3, con errores de fuente/tiempo. El workflow de atestación independiente [#38085788639](https://github.com/mezas3238-hue/qore-core/actions/runs/38085788639) pasó su gate de calidad (12 pruebas), trabajos históricos por mercado ejecutados de nuevo; consultar su estado final en GitHub.

## Tareas obligatorias antes de certificación y PF/DD del Master Frame

**A2 fuente TTrades** debe revisar los **501 casos**, prioritariamente los **342 SWEEP** sin protected CISD estructural, y resolver si la ruta del autor permite un extremo barrido/confirmación temprana sin el triple-pivot del detector QORE. Revisar 157 pivotes posteriores vulnerados y **490 pivotes nuevos** bajo fuente original, sin hindsight ni filtrar masa ganadora. Registrar diferencias con 381 CISD del observador shadow, no vetar discrepancias.

**A1 cognitiva** debe construir el verdadero histórico causal 9/9: percepciones M1 simultáneas, contextos H1/M15 atestados, régimen, correlaciones/cross-market, pressure, posiciones y presupuesto de cartera as-of; conectar al Master Frame y al runner PAPER/económico para todas las 2876 source ID. No deducir quotes BID/ASK o spreads de OHLC, no crear readiness `WELL_SUPPORTED` ficticia. Ejecutar A/B comparado V49 2020 trades PF ~0.664/DD ~236.13R (gross, ambos resultados V49 control), preservación de >=934 ganadores originales y >=415.748485649R positivos, con mercados 9/9, Sharpe/Sortino, DD y costes.

**Estado aprobado**: evidencia adicional de 490 pivotes físicos causales y conexión de sus tokens a la interfaz Master Frame PAPER validada en CI. **No aprobado**: fidelidad por autor, full historical nine-market Master Frame economic replay, nuevo PF/DD, certificación, merge o VPS/LIVE.

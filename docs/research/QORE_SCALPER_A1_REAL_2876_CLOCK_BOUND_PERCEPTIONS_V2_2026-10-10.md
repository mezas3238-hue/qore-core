# QORE Trader Scalper A1 — V2: 2.876 percepciones nativas avanzan BAD→DEGRADED con prueba real de horario

**Fecha:** 10 octubre 2026 | PR A1 #758 DRAFT, A2 #759 DRAFT | Solo GitHub, cero VPS/LIVE/merge.

## Resultado REAL 9 mercados / 2.822 instantes / 2.876 V49 originales

[**Run native clock-bound nine perceptions V2 #38092434895 — SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434895). Se juntan artefactos INMUTABLES independientes:

- 9/9 libros native closed M1 proveedor original, decisión global del evento +última vela cerrada de cada activo, [#38080367716](https://github.com/mezas3238-hue/qore-core/actions/runs/38080367716), commit `435e2369f1ed94d7130d328115d2402dcd4e5b84`.
- 2.876 testigos fuente por `source_opportunity_id` y reloj America/New_York DST, todos revalidados contra bucket y operating-date V49 [#38091938032](https://github.com/mezas3238-hue/qore-core/actions/runs/38091938032), commit `532f8a683a4181c85a07d071c7a2c22818d9b0aa`.
- Los originales V49 provienen de [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695); NINGÚN resultado de trade se utiliza para determinar la categoría perceptiva.

| Percepción tipada del verdadero contrato Master Frame | Anterior epistémico V1 | Con reloj nativo fuente V2 |
|---|---:|---:|
| `CapitalizerPerceptionStatus.DEGRADED` | 0 | **2.876** |
| `CapitalizerPerceptionStatus.BAD` | 25.398 | **22.522** |
| `CapitalizerPerceptionStatus.GOOD` | 0 | **0** |
| **Total 9×2.822** | **25.398** | **25.398** |

La **promoción no es heurística ni universal**: exige `source_opportunity_id` único, símbolo de la oportunidad original entre los nueve, instante de decisión fuente idéntico a cierre de vela M1 nativa, mismo `m1_opened_at`, bucket QORE original `QORE_BUCKET_RECONFIRMED` y `operating_date` revalidado. Si falta el ID, la vela, la hora o el mercado, el ensayo falla (integridad de datos), no vetamos silenciosamente una señal. Si un reloj contradice QORE pero está íntegramente presente, conserva estado BAD y la fuente no pierde elegibilidad.

En la percepción promovida `assess_perception_integrity` recibe exactamente `quote_fresh=False`, `microstructure_complete=False` y `session_clock_valid=True`, `bars_complete=True` sólo en el mercado fuente de ese instante. Resultado **DEGRADED** con `QUOTE_NOT_FRESH` y `MICROSTRUCTURE_INCOMPLETE`; **NO GOOD**. Los 8 mercados ajenos que no tienen oportunidad fuente concurrente permanecen BAD con session clock sin certificar a nivel de esa percepción. Se conservan las 31 barreras con al menos otro activo sin vela exacta, 2.791 tienen 9/9 vela exacta. El censo V2 demuestra 2.876 instancias asociadas a oportunidades (algunas de las 2.822 barreras contienen fuentes de más de un mercado).

El nuevo `src/qore/infrastructure/trader_lab/capitalizer_a1_native_clock_bound_perception_v2.py` construye **objetos reales** `CapitalizerMarketPerceptionSnapshot` y mantiene los originales `CapitalizerRegimeHypothesis` `UNRESOLVED` y `CapitalizerCrossMarketCausalGraph` con 36 pares `UNKNOWN`/barrier. La V2 emite JSONL por barrera para auditoría/joins posteriores y resumen [en artifact del run #38092434895](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434895). Ningún camino de código a broker/riesgo, ningún resultado P&L, ningún filtro.

### Enlace al Trader ya implementado, sin falsa afirmación de replay histórico

El paso anterior A1 `run_sensorized_master_frame_paper(... source_clock_witnesses=...)` comprueba 1:1 original ID+fecha+sesión+vela M1 y pasa tokens como procedencia al **verdadero** `A1MultiHypothesisBarrier.alternatives.context.observation_tokens` → Master Frame → PAPER Trader. Tests de integración con **fixtures artificiales del World Model** prueban paso de información y ningún veto. La V2 nueva es otro avance: **construye las percepciones históricas tipadas que ahora pueden consumirse dentro de un mundo nine-market completo**, no afirma por sí misma que el histórico haya ejecutado `build_master_cognitive_frame` real o seleccionado órdenes.

### Datos para certificación que faltan (nunca inventarlos)

1. Cotización física BID/ASK y trazabilidad temporal del spread, comisión, slippage, mercado, MT5 lot size y microestructura para fuente y nueve mercados; no elevar GOOD por OHLC nativo ni reloj válido.
2. `CapitalizerRegimeHypothesis` por nueve mercados deducida de series verdaderamente as-of H1/M15/M1 y validación adversarial; no transformar 25.398 `UNRESOLVED` en regímenes SUPPORTED por conveniencia.
3. `CapitalizerCrossMarketCausalGraph` con hechos causales por par no inferidos solo por correlación o cierres simultáneos.
4. `CapitalizerGlobalWorldModel` completo con Market Brains, Session Brain, `session_ledgers`, `journey`, `loss_memory`, `open_positions` y `CapitalizerCognitivePressureFacts` tal como eran en cada instante as-of; las pérdidas sólo entran tras asentamiento real de trades seleccionados.
5. Materialización 2.822 barreras multi-hypothesis con 2.876 source IDs + A2 sensores revalidados M15/M1/H1, reloj/NY as-of y 381 CISD discrepancias **sin hard veto**, invocar Master Frame → selección Trader PAPER económica, retención de ganadores y medición PF/DD.
6. A2 debe resolver contra las fuentes **originales de TTrades**, no el módulo ICT de otro modelo: 501 protected M1 pendientes, 12 M15, 124 H1, y si existe ventana TTrades autor-fiel distinta del QORE broad bucket. NO convertir 408 London/1061 New York fuera de killzone ICT en invalidaciones de TTrades.

**Evidencia calidad:** [V2 native perception #38092434895 GREEN — Ruff, Mypy y 4 pruebas causales](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434895), [auditoría repo #38092434918 GREEN](https://github.com/mezas3238-hue/qore-core/actions/runs/38092434918) Ruff/Mypy repositorio/57 tests. 0 operaciones fuente descartadas. 0 permiso LIVE, no certificar. V49 control original 2020 trades PF ~0.664 DD ~236.13R permanece SIN CAMBIO; **PF/DD del full Master Frame 9-market NO ha sido ejecutado**.

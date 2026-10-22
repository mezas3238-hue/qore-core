# VT08 — Arquitecto B R6: runner indexado en Trader Lab y validación diferencial real

Fecha: 2026-10-15. Repositorio `mezas3238-hue/qore-core`; rama B `agent/vt08-5m-cognition-replay-20261010`; PR #764 DRAFT. Este informe mantiene todos los bloqueos científicos y de autoridad de R5.

## Necesidad y solución
El Owner solicitó acelerar la validación mediante Trader Lab / QORE Research (Ultra Fast Runner). Se localizaron `src/qore/infrastructure/trader_lab/fast_forward.py` (acelera cronología SIMULADA, no es un segundo motor de backtest ni acelera necesariamente CPU) y `ict_turtle_soup_behavior_lab_fast_runner.py` (específico de ICT Turtle Soup; su metodología NO debe transferirse a VT08).

Se incorporó un **runner propio de VT08**, `src/qore/infrastructure/trader_lab/vt08_b_r3_indexed_ultrafast_runner_v1.py`, que **preindexa OHLC M30** a partir de raws M3/M15, cachea cada bloque cerrado por tiempo, y vuelve a computar los conteos de geometría C1/C2 sin ejecutar fuentes autor A o mirar salida/PnL.

Existe un segundo verificador B completo e independiente `vt08_b_r3_frozen_source_independent_v1.py`. La nueva función `compare_indexed_against_reference()` exige igualdad exacta de **mercado, ventanas C2, faltantes, discordantes, bullish negativos y bullish positivos**. Ante una sola diferencia, FAIL y sin aceptar ejecución ni certificación. A sigue proveyendo fuente M3/M15 auténtica y recibos R3; no se readmite método completo.

### Evidencia EJECUTADA
[GitHub Actions B #38740153019](https://github.com/mezas3238-hue/qore-core/actions/runs/38740153019): **cinco de cinco SUCCESS**, con Ruff, Mypy, prueba sintética diferencial/adversarial y verificación física por mercado. SHA de código de referencia `77b1cd046e159d67198b9ff8886535bd7d096e6c`.

| Mercado | C2 verificadas | Positivos geométricos R3 con recibos B | Runner indexado solo geometría | Auditor B referencia (incluye recibos/H1) | Conteos coinciden |
|---|---:|---:|---:|---:|---|
| EURJPY | 18.646 | 538 | 1,969 s | 7,469 s | SÍ |
| USDCHF | 18.646 | 518 | 1,513 s | 5,639 s | SÍ |
| NZDUSD | 18.646 | 550 | 1,506 s | 5,664 s | SÍ |
| CADJPY | 18.646 | 516 | 1,990 s | 7,584 s | SÍ |
| USDCAD | 18.646 | 535 | 1,928 s | 7,395 s | SÍ |
| **Total** | **93.230** | **2.657** | **8,906 s** | **32,751 s** | **SÍ 5/5** |

**Advertencia de benchmark:** las duraciones son observadas de un solo run de Actions en cada job. **NO es un benchmark equitativo del mismo trabajo**: el recorrido indexado recomputa solo geometría C1/C2, mientras la referencia además re-hashea/verifica **todos los 2.657 recibos C1/C2 y contexto H1 PRE-C2**. Es correcto decir «8,906 s para geometría indexada vs 32,751 s para un paquete más amplio», pero está **prohibido** afirmar mejora global 3,68× de igual evidencia. No se ha demostrado reducción de tiempo del pipeline completo, que también descarga raws y ejecuta tests.

## Matriz de permisos y alcances
- **Sí:** optimización de CPU mediante indexación con cálculo idéntico de los 93.230 C2, source windows faltantes, OHLC M3/M15 y primer filtro bullish. Difusión acelerada de auditorías P0 sin cambiar selección por PnL.
- **NO:** calificativo TTrades, selección de POI relevante, criterio semántico CISD/PS, relevant swing, breaker, EQ, stop/target, fills BID/ASK, fees o congnitiva postfill. El runner devuelve `author_semantics_certified=False`, `economic_gates_evaluated=False`, `orders_authorized=False`.
- **NO:** optimización de lotes/riesgo/sizing/apalancamiento/compounding para aprobar, merge, VPS/DEMO/LIVE, reutilización de trial #787 cerrado ni apertura de 7Y sealed OOS.
- **Acción siguiente:** mantener verificación física completa como oráculo de identidad/fuente; cuando A entregue reglas semánticas congeladas, mejorar ingesta/eventos de fuente REAL y medir A-only vs A+B en identidades iguales usando Trader Lab sin alterar pre-registro y sin certificar por conteos OHLC.

## Último dictamen
**Desarrollo técnico y aceleración de geometría PASS; certificación integral VT08 PENDING.** `APPROVED_A_B_MANIFEST_SHA256=None`. Falta source-author adjudicado, ruta cognitiva auténtica y economía con BID/ASK+fees y Gates Owner congelados. El trabajo está reproducible por las rutas del repo y el workflow `.github/workflows/vt08-b-r3-independent-frozen-source-review.yml`.

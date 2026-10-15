# VT08 B R9 — Auditoría independiente de origen temporal H1 (source-only)

**Fecha:** 15-oct-2026 · **Repositorio:** `mezas3238-hue/qore-core` · **Rama:** `agent/vt08-5m-cognition-replay-20261010` · **PR:** [#764](https://github.com/mezas3238-hue/qore-core/pull/764)

**Dictamen:** **SOURCE PHYSICAL + AS-OF VERIFIED** para la comparación A R6/R7 sobre sus 2.657 registros, **TTRADES TARGET SEMANTICS NOT CERTIFIED**. Investigación solamente, no trading.

## Evidencia reproducible exacta

- Auditor independiente B: `src/qore/infrastructure/trader_lab/vt08_b_r9_h1_target_independent_v1.py`. No importa generadores A.
- Pruebas: `tests/infrastructure/trader_lab/test_vt08_b_r9_h1_target_independent_v1.py`.
- [Workflow GitHub Actions #38787187066](https://github.com/mezas3238-hue/qore-core/actions/runs/38787187066) — **5/5 SUCCESS**, Ruff y **7/7 pytest por mercado**, cinco artefactos de resultado de B con retención temporal.
- Commit reproducido en CI `299aeae1c9ba96bc270e84d5d6fcd261e23cdb65`.
- Intento anterior [#38786993784](https://github.com/mezas3238-hue/qore-core/actions/runs/38786993784) falló por **un índice adicional en una aserción de test sintético del gap** (`result[0][0]` sobre un diccionario); se corrigió en el test SIN cambiar la lógica de auditoría de mercado. No ocultar ese rojo.
- Fuente original M15 DEMO por mercado [run #35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907). Insumos A R6 [#38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669) y A R7 [#38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497), artefactos con nombres SHA-pinned en el workflow B.
- Como antecedente de revisión paralela complementaria, B [CI #38786941777](https://github.com/mezas3238-hue/qore-core/actions/runs/38786941777) verificó fuente física R6/R7 con otro oráculo y 5/5 SUCCESS. Esta auditoría añade la **separación de disponibilidad PRE-C2 vs DURANTE C2**.

## Resultados realmente medidos en cinco mercados

| Mercado | Precursores auditados | H1-highs disponibles al inicio de C2 | H1-highs confirmados después de C2.open y hasta C3.open | Casos sin high conocido pre-C2 | Casos con un solo high pre-C2 |
|---|---:|---:|---:|---:|---:|
| EURJPY | 538 | 3.883 | 291 | 17 | 63 |
| USDCHF | 518 | 4.085 | 251 | 24 | 47 |
| NZDUSD | 550 | 4.567 | 277 | 9 | 53 |
| CADJPY | 516 | 3.812 | 278 | 18 | 57 |
| USDCAD | 535 | 4.215 | 260 | 8 | 58 |
| **TOTAL** | **2.657** | **20.562** | **1.357** | **76** | **278** |

**Invariante de conservación:** 20.562 + 1.357 = **21.919** high-level witnesses; conteos de **niveles**, no señales/operaciones, pueden repetirse entre C2 distintos. 76 / 278 son **contextos** distintos. No extrapolar conteos de 52 contextos A R7 ni descartar los 76 del denominador.

La reconstrucción B recorre ordenadamente las barras **M15 nativas originales** con SHA del archivo fuente, verifica identidad de origen de 4×M15, anula high ante touch posterior `>= high`, elimina estado previo en gaps y nunca lee más allá del `decision_at_utc = C3.open`. Compara cada candidato y `source_bar_id` con R6 y su réplica en R7. Los cinco jobs validaron igualdad exacta de inventario por registro; un SHA manipulado, high modificado o recibo de barras adulterado se rechaza.

**Interpretación crítica:** los 1.357 niveles nacidos durante C2 son observables al momento de abrir C3, pero NO estaban completamente confirmados al abrir C2. Esto importa para cualquier regla que exija un objetivo HTF `previous` **pre-C2** o para un selector de swing previo. El artículo del autor sobre targets habla de highs previos y untouched, pero **no resuelve aquí por sí solo** si el reloj autorizado es C2.open o C3.open para esta familia M30→M3. Por tanto **no eliminar automáticamente los 1.357 niveles ni seleccionar los 20.562 como targets TTrades**; solicitar una adjudicación A/B fuente-textual explícita y anterior a cualquier PnL. Un high físico tampoco significa relevante, alcanzable, superior al entry, único ni orden fillable.

## Pruebas adversariales incluidas

- Equal-price touch invalida nivel anterior; nuevo H1 se reconstruye por sus propios 4 M15.
- Ninguna barra que cierre después de C3.open afecta el reporte.
- Alteración del high incluso si A R6 y R7 se adulteran de forma coordinada: B rechaza por diferencia con M15 original.
- Alteración de un `origin_source_m15_bar_id`: B rechaza.
- A R6 y R7 con distinta cardinalidad: B rechaza.
- Falsificación de fills/economía o certificación: B rechaza.
- Hueco M15: reset de continuidad, no imputación de barras faltantes.

## Nueva decisión metodológica P0 a resolver

1. A debe exponer cita exacta de fuente `target_availability_clock` para la familia **M30 bullish C2 + M3 PS/CISD + C3 POS**. Distinción a adjudicar: `AVAILABLE_BEFORE_C2` vs `AVAILABLE_AT_C3`. Una categoría `UNRESOLVED_D` debe permanecer explícita. **No** inventar un cutoff a partir de beneficios.
2. A+B deben resolver relevant swing/valid separation, POI reversal, breaker con LOW→HIGH→LOWER LOW→HIGHER HIGH, PS/CISD M3, EQ WITH/AGAINST y desempate entre múltiples highs. El alta de 27 campos cognitivos solo puede hacerse con semántica/cutoffs fieles al autor, no flags de catálogo.
3. Preservar cohorte entera de 2.657 casos, revisar ciegamente positivos/negativos/ambiguos, fijar manifest dual `APPROVED_A_B_MANIFEST_SHA256` **solo tras validación conjunta**.
4. Posteriormente cotizaciones BID/ASK y fees reales para operaciones definidas antes del outcome, misma unidad 1R sin sizing, contratos PF/DD/Sharpe/Sortino/OOS/MC aprobados por Owner; el holdout 7Y sigue sellado.

## Restricciones de alcance / veredicto

`source_complete_entries=0`, `broker_fills=0`, `profit_factor=null`, `economic_gates_evaluated=false`, `ttrades_target_relevance_certified=false`, `cognitive_admission_authorized=false`, `holdout_7y_accessed=false`, `sizing_used=false`.

**No hubo merge, VPS, DEMO/LIVE, órdenes, operación ni apertura de holdout.** R9 es un avance de procedencia/causalidad; no es un certificado de método, cognitiva o rentabilidad.

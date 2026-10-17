# VT08 B R14 — CISD M3 serie bajista original, reconstrucción independiente 2.657/2.657

**Fecha:** 15-oct-2026 · **Arquitecto B:** PR [#764](https://github.com/mezas3238-hue/qore-core/pull/764) DRAFT · **Arquitecto A:** PR [#765](https://github.com/mezas3238-hue/qore-core/pull/765) DRAFT.

**Veredicto:** `NATIVE_M3_OPPOSING_SERIES_PHYSICAL_RECONSTRUCTION_PASS` · `TTRADES_CISD_QUALITY_AND_PROTECTED_SWING_SOURCE_D` · `COGNITIVE_0` · `ECONOMIC_NOT_EVALUABLE`. No sizing, no PnL, no holdout, no merge ni órdenes.

## Ejecución real

- [**GitHub Actions #38798284641**](https://github.com/mezas3238-hue/qore-core/actions/runs/38798284641): **5/5 SUCCESS**; Ruff + **11/11 pruebas adversariales por market** = **55 ejecuciones de test**; todos los 2.657 positivos congelados A R3 con 20 barras M3 originales (diez C1, diez C2) revalidados por B.
- Código B: `src/qore/infrastructure/trader_lab/vt08_b_r14_opposing_series_native_cisd_v1.py`.
- Tests: `tests/infrastructure/trader_lab/test_vt08_b_r14_opposing_series_native_cisd_v1.py`.
- Workflow: `.github/workflows/vt08-b-r14-native-m3-opposing-series.yml`.
- Commit código+tests aprobado: `bd945dd26d620b87d93f84ec8eb5dffbf2b01686`.
- Insumos inmutables fijados por run/artifact: [R3 original congelado #38715560333](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333); [M3 cTrader nativo #35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396). Fuentes SHA256 originales leídas del archivo real y comparadas a los recibos source por cada barra de cada evento. Ningún uso de código productor A para buscar posiciones.

## Condiciones físicas verificadas

El artículo primario [TTrades CISD Confirms Swing Points, «What Is CISD» y «How CISD Defines Trend Shifts»](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) describe que el precio llega a un nivel importante y **cierra a través de una serie de velas que produjo el movimiento**. El oráculo B R14 controla físicamente las condiciones siguientes, **sin declarar POI importante ni calidad autor-probada**:

1. Una sucesión contigua de velas M3 bajistas `close < open`, cuyo primer `open` establece `cisd_level_proxy`.
2. El menor `low` de esa sucesión está estrictamente por debajo de `low(C1)` M30, donde `C1` se reconstruye nuevamente desde sus diez M3 RAW.
3. La primera vela no bajista siguiente cierra `close > cisd_level_proxy`; una mecha/high por encima sin cierre **no es** CISD confirmado.
4. Hay **exactamente un** cruce de ese patrón en las diez M3 que componen C2 para cada caso congelado (no se seleccionan los favorables).
5. Los cuatro componentes A R3 `opposing_series_opened_at`, `cisd_confirmed_at`, `ps_proxy_price`, `cisd_level_proxy` coinciden exactamente con la reconstrucción independiente en el feed original.
6. Todos los cierres M3 tienen `available_at <= C3.open`. Se conservan por caso los IDs originales de barras que soportan la serie y el cierre.

| Mercado | Casos R3 | Secuencia opuesta y cierre M3 reconstruidos sin detector A | Proxies confirmados causalmente hasta C3 |
|---|---:|---:|---:|
| EURJPY | 538 | 538 | 538 |
| USDCHF | 518 | 518 | 518 |
| NZDUSD | 550 | 550 | 550 |
| CADJPY | 516 | 516 | 516 |
| USDCAD | 535 | 535 | 535 |
| **TOTAL** | **2.657** | **2.657** | **2.657** |

### Digests SHA256 completos por mercado (del JSON fuente R14)

- EURJPY: `83179600d482f1725f4fbd5bdbc0f77c488fdeb2c53d6493f8f9321efad4dc3a`.
- USDCHF: `8e536884be36647ddbefaf4801a751bde4a304fc37a450e2f75efd2d21bf4ebb`.
- NZDUSD: `bc90ca4dbdf8c3fa502b972a551d95fb21f630fa16fdb6649f9aade526a07d89`.
- CADJPY: `df535a7bd7aa16df82c2bd5bb3865f16dfd80b835b3e75b9f40103d87bb72019`.
- USDCAD: `e572eddcc35e781e6416944fd69383ec3aa0307d31f20a0ac6dfdc382ac99479`.

## Interpretación causal correcta y fronteras de inferencia

R11/R12 documentaron formación intrabar CISD previo al cierre C2 en 2.504 casos y simultáneo en 153; R14 por fin verifica también de modo totalmente independiente la **estructura elemental del patrón** detrás de esos timestamps. Esto respalda la propuesta metodológica de DeepSeek respecto a **disponibilidad causal** del CISD antes de C3.open.

**NO se ha demostrado**: que el low C1 barrido sea un *relevant swing* TTrades (R13 detectó que no es el pivot M30 bullish centrado en C1); que la serie opuesta haya nacido en un **POI significativo**; que el cierre sea «high-quality CISD» en términos de desplazamiento/V/rechazo vs consolidación; que el protected swing elegido sea correcto respecto a EQ/estructura y ya estuviese colocado; ni que exista breaker si el Example 1 específico exige stop bajo él; SL/target correctos ni un fill real. Una serie geométrica no certifica por sí sola autoría de un trade.

El auditor tercero **acierta** al señalar que el patrón debe tener un cierre real a través de las velas opuestas; **sobreinterpreta** al derivar de ese hecho `protected_swing_genuino=true` para todos los casos, o al dar por superados todos los requisitos del POS. R14 es un puente físico fuerte para adjudicación, no el manifiesto A/B.

## Calidad adversarial, fallos y resolución

[Primer run #38798211993](https://github.com/mezas3238-hue/qore-core/actions/runs/38798211993) **FAIL** exclusivamente por estilo N802: nombre del test con mayúscula `A`, corregido solo el nombre del test. [Run final #38798284641](https://github.com/mezas3238-hue/qore-core/actions/runs/38798284641) **5/5 SUCCESS**, 11 tests/job. Sin relajación del validador. Las 11 pruebas incluyen falso cierre a nivel/no sweep, wick sin cierre, huecos de minutos, source native alterado, cisd_proxy/precio A contradictorios, fuente SHA y falsificación de `A_rule_complete`.

## Siguiente bloqueo obligatorio por arquitecto (fuente y cognitiva)

**A metodológico #762:** Para los 2.657 IDs, usar los IDs físicos R14 para estudiar las series M3 reales **ciegamente** y adjudicar contra la fuente CISD *important level, displacement/strong close, consolidation*, valid closure M30, relevant swing y POI reversal. Definir reglas operativas y casos `D` (no especificables). Contrastar con R13 prohibición de reemplazar M3 protected swing por un M30 pivot centrado C1/C2. Resolver stop bajo EQ+breaker para la familia y target/tiebreak. No escoger ejemplos por PnL.

**B cognitivo #763:** Enlazar `case_id_sha256`, `source_bar_id[]`, `cisd_level_proxy`, `ps_low_proxy`, `source_m3_sha256`, `available_at`, fuente TTrades y signoffs a los 27 CAUSAL_FIELDS solo cuando A tenga resolución original real; no promover `physical_cisd_proxy_reconstructed` a `author_cisd_and_ps_validated` en ausencia de A+B reales.

**Estado:** ninguno de estos 2.657 es automáticamente `SOURCE_COMPLETE`; `COGNITIVE_ADMISSIONS=0`; `BROKER_FILLS=0`; PF/Drawdown/Sharpe/Sortino siguen **NOT_EVALUABLE**, holdout 7Y sellado, sizing prohibido, sin VPS/trading ni merge.

# VT08 B R21 — Contexto intradía físico C1.low vs mínimo NY day-to-date, 2.657 candidatos

**Fecha:** 16-oct-2026 · B PR #764 DRAFT · coordinación A #765. **Auditoría SOURCE-ONLY; NO rule/POI certified.** Única vía VT08 metodología actual TTrades y cognitiva VT08; **QORE-alpha excluida**.

## 1. ¿Por qué un segundo contraste después de R20?

El artículo original [Timeframe Alignment / Example 1: M30→M3 intraday reversal, 30-jul-2025](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) describe reversión M30 tras **barrer mínimos intradía**. A R3 seleccionó un caso C2 si barrió el mínimo de C1 M30 inmediatamente anterior y cumplió cuerpo + CISD/PS geométrico. B R20 demostró 2.657/2.657 secuencias físicas C1-low sweep anterior a CISD M3. **Eso no demuestra que el low de C1 sea el extremo intradía al que se refiere el autor.**

R21 hace una comparación puramente **física, no normativa**: reconstruye el mínimo M3 observado desde las **00:00 de NY del mismo día** hasta `C2.open`, estrictamente sin usar C2 o velas posteriores para determinar el low previo. Compara con `C2.low` real. La fecha NY y DST usan `America/New_York` y tránsito UTC. **El autor no prescribe NY-midnight day-to-date como selector universal de POI**, por lo que cualquier conclusión `not NY DTD low ⇒ no TTrades setup` es FALSA. Se registra la diferencia, no se elimina ninguna fila ni se elige un filtro según PnL.

## 2. Resultado REAL, cTrader M3 de origen, censo total sin PnL

[**CI B R21 #38903207496**](https://github.com/mezas3238-hue/qore-core/actions/runs/38903207496) **6/6 SUCCESS**, HEAD `8c24c425810cb960f7a3384809a1a50a2eeb6516`. Ruff, cinco tests adversariales sintéticos y cinco jobs con original A R3, A R7, M3 cTrader pinned. La función vuelve a correr B R20 con 20 barras por candidato y sus SHA de origen, luego verifica el contexto M3 PRE-C2 por secuencia cada 3 min. Cualquier barra faltante, hora inconsistente o discontinuidad => `INCOMPLETE_D`, nunca imputación.

| Mercado | Total | C2 barrió además low NY 00→C2.open | C2 barrió C1.low, no low NY 00→C2.open | Contexto incompleto |
|---|---:|---:|---:|---:|
| EURJPY | 538 | 185 | 351 | 2 |
| USDCHF | 518 | 217 | 300 | 1 |
| NZDUSD | 550 | 238 | 308 | 4 |
| CADJPY | 516 | 189 | 324 | 3 |
| USDCAD | 535 | 262 | 272 | 1 |
| **TOTAL** | **2.657** | **1.091** | **1.555** | **11** |

En los **2.646 contextos completos**, el C1.low original coincidía exactamente con el mínimo ya observado NY DTD en **842**, y estaba **por encima** del mínimo previo DTD en **1.804**; algunos de estos 1.804 todavía fueron barridos más profundamente por C2 y alcanzaron el mínimo DTD, de ahí la diferencia 842 vs 1.091.

**Denominador intocable:** 1.091 + 1.555 + 11 = **2.657**. Ni los 1.091 son automáticamente author-valid, ni los 1.555 son automáticamente author-invalid; estos no son 1.091 / 1.555 fills o firmas.

## 3. Qué se entrega a la revisión ciega A/B

Los 46 paquetes R19 quedan cruzables por exacto `case_id_sha256` con cinco nuevos artifacts R21 `vt08-b-r21-intraday-context-{MARKET}-{SHA}`. Cada row de los 2.657 registra C1.low, C2.low, mínimo anterior NY DTD o `None` por GAP, clasificación física, fuentes SHA, condición as-of y `important_level_ttrades_author_confirmed=False` por defecto. No se escribieron barras de proveedor ni precios licenciado en el repositorio público. Retención artifacts 30 días.

**Pregunta que deben responder dos reviewers independientes, con texto original+IDs:**
- ¿El `important level` del ejemplo es bajo C1 M30 (como under-reaction local), mínimo anterior NY, mínimo de otra sesión, pivot relevante HTF u otro POI? El artículo **no define una regla automática global de selección**; marcar `AUTHOR_P0_POI_SELECT_D` hasta establecerla por fuente/contexto.
- ¿El barrido fue del POI correcto *antes* del CISD que confirmó serie opuesta? R20 prueba la condición **orden físico** relativa a C1.low, R21 prueba una comparación adicional; **no** prueba significance causal.
- Si POI autor-relevante/HTF swing/PS/breaker/stop/target son adjudicados realmente, verificar 27 Situation fields con hashes/available_at y dos revisores antes de cualquier cognitiva, BID/ASK, PnL/OOS.

## 4. Artefactos exactos

`src/qore/infrastructure/trader_lab/vt08_b_r21_intraday_low_source_context_v1.py`

`tests/infrastructure/trader_lab/test_vt08_b_r21_intraday_low_source_context_v1.py`

`.github/workflows/vt08-b-r21-native-intraday-low-context-diagnostic.yml`

Complemento causal correcto: [VT08 B R20 2.657 C1-low pre-CISD y author intra-C2](VT08_B_R20_NATIVE_2657_C1_LOW_SWEEP_CISD_CAUSAL_ORDER_AND_TTRADES_INTRAC2_RULE_2026-10-16.md). Complemento de 46 packets: [VT08 B R18/R19](VT08_B_R18_R19_AB_INGRESS_AND_46_BLIND_TTRADES_SEMANTIC_REVIEW_PACKETS_2026-10-15.md).

**Estado real:** R20 causal physical PASS, R21 contextual physical PASS, 2.657 source geometric only; **0 fuente autor completa, 0 revisión dual completada, 0 cognitiva admitida, 0 fills**, PF/DD/Sharpe/Sortino NO_EVALUABLE. Sin sizing, sin QORE-alpha, sin 7Y, no VPS/DEMO/LIVE ni merges.

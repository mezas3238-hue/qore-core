# VT08 B R10 — Tres HTF incluyendo la actual: auditoría H1 causal independiente (15-oct-2026)

**Repositorio:** `mezas3238-hue/qore-core` · **PR B:** [#764](https://github.com/mezas3238-hue/qore-core/pull/764) · **Rama B:** `agent/vt08-5m-cognition-replay-20261010`  
**Dictamen:** **CAUSAL PHYSICAL WITNESSES VERIFIED**, **AUTHOR RELEVANT SWING/ENTRY NOT CERTIFIED**. No declaración económica ni autorización operativa.

## 1. Hallazgo semántico primario que originó la auditoría

Fuente primaria TTrades, [*Relevant Swings*, 21-mar-2026](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/), sección «The Fractal Lookback Window»: el autor pide mirar **tres velas HTF incluyendo la actual**, no siempre tres velas ya cerradas anteriores al evento. Sección «Valid Separation»: **no existe fórmula numérica universal** para esa separación. Una geometría simple de 3 H1 cerradas (A R7) es una ventana QORE-C conservadora, no selección automática de relevant swing original. La elección de H1 como HTF para este subtipo M30/M3 también exige su propia justificación de alineación de marcos, no deducirse solo del artículo.

TTrades [*Positional Entries*, 08-ago-2026](https://ttrades.com/positional-entries-enter-before-the-expansion/), secciones «The Fractal Model Comes First» y «The Protected Swing Determines the Stop Loss»: requiere un modelo fractal completo antes del nuevo HTF open y protected swing válido como referencia de stop, además de confirmación lower timeframe. El artículo **no demuestra por sí solo que todo trade POS deba tener un breaker obligatorio**. No eliminar ni imponer universalmente ese requisito sin reconciliar las fuentes de la familia congelada. Tampoco habilitar ejecución de trades por este informe.

## 2. Insumos y oráculo genuinamente independiente

- GitHub Actions [**#38789207167**](https://github.com/mezas3238-hue/qore-core/actions/runs/38789207167): **5/5 SUCCESS**, Ruff + 8 pruebas adversariales por mercado; 2.657 eventos source-only cotejados con RAW M15 cTrader, SHAs pinned exactos por mercado.
- Commit código+tests validado: **`5c601f324b12a2fca27bbf9b944ce136833dbc25`**; código `src/qore/infrastructure/trader_lab/vt08_b_r10_three_h1_current_asof_v1.py`; tests `tests/infrastructure/trader_lab/test_vt08_b_r10_three_h1_current_asof_v1.py`; workflow `.github/workflows/vt08-b-r10-current-h1-asof-three-candle.yml`.
- R7 source-only join A [#38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497), misma población congelada y validación de `case_id_sha256`, market y C2/C3, sin outcomes.
- Original M15 cTrader [#35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), verificado contra SHA a bytes (`PINNED_M15`), perfil/mercado/DST por el oráculo B `_raw_bars`.
- 3×H1 PRE-C2 completadas se verifican de nuevo contra RAW: **2.656 sí, 1 CADJPY no**. Dos H1 anteriores al H1 actual completas: **2.657 sí**. Nunca completar el H1 faltante por inferencia.
- Primer [run #38788793995](https://github.com/mezas3238-hue/qore-core/actions/runs/38788793995) **FAIL** por un `\\n` literal en Python al formatear una URL TTrades. Se arregló el código. [#38788924629](https://github.com/mezas3238-hue/qore-core/actions/runs/38788924629) PASS 5/5. R10 final añadió matriz de transición respecto a R7 y pasó [#38789207167](https://github.com/mezas3238-hue/qore-core/actions/runs/38789207167) PASS 5/5; dejar la historia roja visible.

**Método:** reconstruye `H1[-2]`, `H1[-1]` (dos H1 anteriores enteras) y `H1[0]` (actual, solo M15 realmente cerradas a C2.open o C3.open), además de la ventana alternativa previa A R7 `H1[-3:-1]`. Define únicamente basic geometric pivot del H1 medio; el H1 actual parcial no puede llamarse completado. Se prueba ausencia de lectura futura, fuente ausente, duplicados, mezcla de feed, SHA, origen y falsos claims de economía. Ningún recorte por PnL.

## 3. Resultados completos, sin mezclar ventanas

| Mercado | Eventos | Pivote básico ventana antigua 3 cerradas R7 | Pivote básico nueva 2 previas + actual as-of C3 | Nueva ventana con H1 actual cerrada | Nueva ventana con H1 actual parcial |
|---|---:|---:|---:|---:|---:|
| EURJPY | 538 | 121 | 57 | 42 | 15 |
| USDCHF | 518 | 108 | 50 | 34 | 16 |
| NZDUSD | 550 | 98 | 51 | 40 | 11 |
| CADJPY | 516 | 98 | 62 | 48 | 14 |
| USDCAD | 535 | 112 | 49 | 29 | 20 |
| **TOTAL** | **2.657** | **537** | **269** | **193** | **76** |

**Resultado esencial:** **0 superposiciones** entre las 537 geometrías centrales de A R7 y las 269 nuevas geometrías centrales R10, porque cambió cuál H1 es la vela central evaluada. Esto es una propiedad de **dos definiciones de pivote adyacentes** en este censo, NO es una prueba de que R7 perdiera 269 trades ni que 537 trades deban descartarse. Los **2.119 «sin pivote» de R7** eran negativos solamente dentro de la ventana antigua y no una exclusión source-author irrevocable. No elegir la nueva ventana por parecer producir más trades: de hecho reporta menos pivotes geométricos (269 vs 537), y ambos diagnósticos NO son densidad ejecutable.

**Transición intra-C2:** al inicio C2 había **288** pivotes básicos observables del tipo 2 previas + H1 actual parcial; **193** persistieron al abrir C3 y **95** dejaron de satisfacer geometría (la H1 actual completó una caída o rompió el pivote). Los 288 iniciales no son necesariamente confirmados porque la H1 actual sigue en formación. Es una prueba concreta del riesgo de promocionar un pivote observado temporalmente a «swing validado».

**Disponibilidad:** 1.357/2.657 casos tienen H1 actual cerrada completamente a C3.open; **1.300/2.657** solo dos barras M15 de la H1 actual (H1 parcial). En los 2.657 se verifican dos H1 anteriores cerrados. **0 huecos** en la H1 actual hasta su corte C3. La diferencia con 2.656/2.657 previo A R7 es la tercera H1 *más antigua*, no error de suma.

**Cohortes / denominadores:** A R7 52 casos «un high + pivot» son otra conjunción diagnóstica y no deben inferirse como intersección de R10 193/76. R9 21.919 testigos de H1 highs untouched tampoco son trades. No mostrar muestras favorables sin preservar la cohorte 2.657.

## 4. Qué se resolvió y qué NO

Resuelto:
1. Nueva reconstrucción independiente de ambas ventanas físicas a C2 y C3 y cuantificación de cambio de población por desplazamiento de la ventana; 5/5 cross-check SHA cTrader.
2. Distinción as-of `0/2/4` M15 cerradas dentro H1 actual: no rellenar minutos faltantes, no promover H1 incompleta a cerrada.
3. Detección causal de 95 pivotes provisionales que desaparecen entre C2 y C3, y clase de 76 pivotes aún provisionales a C3.
4. WITNESSES completo en artefactos con hash/pinned inputs para que A/B revisen sin ver futuros económicos.

**Pendiente — P0 real (no solved):**
1. A adjudicar evidencia autor de **marco HTF que corresponde usar** (H1 u otro) y la naturaleza y fecha de confirmación de un **Relevant Swing** con valid separation/failure swings y contexto (no solo strict pivot), con doble anotación independiente A/B sin PnL.
2. A separar `C2_OPEN_SOURCE_KNOWN`, `C3_OPEN_SOURCE_KNOWN_PARTIAL_H1`, `CURRENT_H1_FULLY_CLOSED` en el contrato; no exigir que H1 actual cierre como regla universal si autor usa vela en desarrollo, pero no alegar que aún incompleta es definitiva.
3. Resolver si breaker es requisito **para ESTA familia** según fuente original aplicable frente al artículo de positional entries que define protected swing y CISD, sin convertir un ejemplo de breaker en obligación universal, ni borrarlo caprichosamente para subir densidad.
4. Relevancia POI reversal, CISD/PS M3 auténtico, EQ condicionado, SL y target HTF untouched/empates; B debe derivar **27 CAUSAL_FIELDS reales**, producir `evaluate_provenanced()` con doble firma legítima cuando corresponda.
5. Economía solo si hay señal íntegra y pre-registro Owner: real BID/ASK+fees para el ciclo completo, paridad A-only vs A+B, restricciones de un fill por mercado/día NY, Gates PF/DD/Sharpe/Sortino/OOS/MC en R homogéneo y prohibición sizing. 7Y sellado hasta freeze formal.

**Dictamen verificable:** `source_complete_entries=0`; `broker_fills=0`; `profit_factor=null`; `author_relevant_swing_certified=false`; `cognitive_admission_authorized=false`; `sizing_used=false`; `holdout_7y_accessed=false`. R10 no es certificación metodológica, cognitiva o económica; ninguno de los PR se fusionó y no hubo VPS/LIVE/DEMO.

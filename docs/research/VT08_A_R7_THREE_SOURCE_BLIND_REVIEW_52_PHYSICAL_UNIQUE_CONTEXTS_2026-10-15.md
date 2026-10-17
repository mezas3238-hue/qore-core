# VT08 Arquitecto A — R7: unión causal de tres fuentes y paquete de adjudicación ciega

**Fecha:** 15-Oct-2026 · **PR A:** #765 DRAFT · **B:** PR #764 DRAFT · **B issue:** #763 · **Veredicto:** `AUTHOR_SEMANTIC_NOT_CERTIFIED`, 7Y sellado.

## 1. Resultado REAL ejecutado con GitHub/Trader Lab, no backtest de rentabilidad

[GitHub Actions **#38765076497**](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497): **5/5 SUCCESS**, 8 tests adversariales + Ruff PASS por job. Código `src/qore/infrastructure/trader_lab/vt08_a_blind_three_source_review_join_v1.py`, tests `tests/infrastructure/trader_lab/test_vt08_a_blind_three_source_review_join_v1.py`, workflow `.github/workflows/vt08-a-blind-three-source-review-join-v1.yml`, código HEAD `385e89cb769eef36f85ddca56f3f3dcaf1e0f863`.

Se consumen **tres artefactos de pruebas reales previamente congeladas por mercado**:
1. `R5 EQ`: [#38747954308](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308): 2.657 C2 físicas, EQ full y EQ close-to-low condicionales sin elegir régimen.
2. `R6 TARGET`: [#38763309669](https://github.com/mezas3238-hue/qore-core/actions/runs/38763309669): 2.657 contextos, máximos H1 «no tocados» en segmentos M15 observados sin huecos, **2.437 múltiples y 220 con uno**, cero sin niveles físicos.
3. `R7 SWING`: [#38764229960](https://github.com/mezas3238-hue/qore-core/actions/runs/38764229960): 2.657 contextos, **537 geometrías pivote H1 bullish (low central menor a ambas vecinas), 607 bearish, 42 simultáneas**, un H1 faltante. Se verifican 12 M15 previas cerradas y SHA; `VALID_SEPARATION` y `RELEVANT_SWING` autor continúan `D`.

Adicionalmente B R7 verificó independientemente los 88.276 `bar_catalog` recibos de los 2.657 contextos originales contra M3/M15 cTrader: [#38748150948](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948). La unión de A verifica `market, C2.open, C3.open`, universo de 2.657 casos, arithmetic EQ, identidad de los SHA raw por mercado y ausencia de claims de trade/Profit Factor. **No es una firma de B sobre estas tres nuevas semánticas ni un oráculo de relevancia TTrades.**

## 2. Censo de clases EXCLUYENTES, incluido TODO caso negativo o ambiguo

| Mercado | No H1 previa | No pivot low EN 3 H1 cerradas | Hay pivot low + múltiples highs | Hay pivot low + único high | Total |
|---|---:|---:|---:|---:|---:|
| EURJPY | 0 | 417 | 109 | 12 | 538 |
| USDCHF | 0 | 410 | 93 | 15 | 518 |
| NZDUSD | 0 | 452 | 91 | 7 | 550 |
| CADJPY | 1 | 417 | 89 | 9 | 516 |
| USDCAD | 0 | 423 | 103 | 9 | 535 |
| **TOTAL** | **1** | **2.119** | **485** | **52** | **2.657** |

Los **52** son **«basic H1 pivot observable + exactamente UN H1 high físico no tocado»** dentro de la ventana fija, sin selección de precio posterior. No son 52 setups TTrades, no entraron a cognitiva, no son fills ni un recorte legítimo para medir rentabilidad. Hay **537** pivotes low físicos con información H1; 52 únicos en targets y 485 con más de uno. Los 2.119 `NO_PIVOT` NO son negaciones de TTrades: revisar otra estructura superior/ventana y relevancia ex-ante antes de adjudicarlos. El artículo del autor menciona 3 HTF con vela actual, mientras este subensayo usó **3 H1 completamente cerradas antes de C2** para tener custodia causal fuerte. Ambas ventanas **NO son formalmente equivalentes** y no se debe imponer la segunda como criterio universal del autor.

**Fuente del autor:** [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/) define un pivot básico y exige un «relevant swing» separado y contextual SIN fórmula numérica estricta. [Price Targets](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/) establece anteriores highs HTF / untouched, pero no define una prioridad universal de múltiples highs. Los flags `basic_bullish_h1_pivot` y `source_unconsumed_h1_highs` son testigos físicos previos; `source_author_relevant_swing_verified=false`, `source_author_target_selected=false`, `eq_selection_authorized=false`.

## 3. Artefactos y SHA verificables para B

[Run #38765076497](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497) tiene un JSON por mercado con TODOS los casos, incluidos negativos, clases y enlaces `origin_source_m15_bar_ids` / `h1_source_bar_id_groups` / EQ condicionales. 
- EURJPY: artifact [11987661905](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11987661905); SHA256 JSON canónico `65718734b9120ca6cefbf17800e0ecb5dcfc5a6c17421753f3879003314c6c69`.
- USDCHF: artifact [11988466184](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11988466184); SHA256 `ac9457ca757e9253ae8bff37a29ef1be7742e3797a19c00f613efe08ed24eb6d`.
- NZDUSD: artifact [11987477069](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11987477069); SHA256 `6bbd8e9e6947e8979d69aa3d078274dfda401f50e75f6fe64bd00c282eebaa4b`.
- CADJPY: artifact [11987711676](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11987711676); SHA256 `db91a50305127ea9bcf88cd3e7bb178eb6d932e53b7c1f462fa56d734dfd7279`.
- USDCAD: artifact [11985939734](https://github.com/mezas3238-hue/qore-core/actions/runs/38765076497/artifacts/11985939734); SHA256 `7875e7f0a8ed27d1b969f5437938636522739946f7757f5b525328212116e58a`.

Artifact retention 30 días; prohibido volcar raws cTrader con licencia en público. El paquete de revisión no contiene PnL o desenlaces.

## 4. Contrato B de validación ciega para AL MENOS los 52 y controles

B debe verificar fuente física independientemente, hacer doble anotación o adjudicación de:
- **Grupos:** los 52 casos «fácil inspección» y muestra cronológica estratificada de los 485 múltiples y los 2.119 sin pivot H1 previo, sin consultar ni usar PnL. No descartar los otros 2.605 del análisis metodológico.
- **Swing:** relevante real pre-C2 / separación / reacción, fuente específica, identidad del swing, POI significativo, CISD/PS M3 causal y breaker origin correcto; distinguir A escrito, C-QORE heurístico y D indeterminado.
- **EQ y SL:** elegir régimen EQ SOLO después de swing A-válido; `SL < min(EQ,breaker_low)` y espacio FVG cuando se aplique. Ningún stop por PS-only, 2R ni buffer ajustado a resultados.
- **Targets:** para todos los high H1 candidatos, decidir por evidencia escrita si H1 es HTF apropiado para C3 M3 y si se requiere swing, cuál target untouched realmente es author valid; devolver AMBIGUOUS si no hay desempate source A. No usar nearest TP ni nivel que alcanzó el precio futuro.
- **Cognitiva 27 campos:** bar-ID/SHA/available_at por feature y ausencia causal. B manifest queda `None` hasta revisión y signoff independientes. Bloquear cualquier ruta `evaluate_provenanced` falsa.

## 5. Certificación

El estado permanece `NOT_CERTIFIED`. **0 source-author-complete, 0 cognitive admissions reales, 0 broker fills, PF/DD/Sharpe/Sortino netos NOT MEASURED, OOS 7Y sellado, sin sizing, leverage, compounding, VPS, DEMO/LIVE ni merge**. Una infraestructura más rápida no reemplaza la autenticidad de señal ni datos BID/ASK/fees del trade entero.

**Siguiente P0:** A/B adjudicar fuente efectiva de relevant swing / breaker / POI / target con fuentes originales y eventos físicos; solo después ejecutar certificación económica con runner fiel a C3 POS.

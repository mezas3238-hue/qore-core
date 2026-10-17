# VT08 B R23 — Dictamen operativo: 107 expedientes semánticos sin firmas falsas

**Fecha:** 2026-10-17 · **Proyecto:** exclusivamente VT08 actual, fuente metodológica TTrades + cognitiva VT08 propia · **Arquitecto B:** `agent/vt08-5m-cognition-replay-20261010`, PR #764 (DRAFT), Arquitecto A PR #765 DRAFT.

**Estado del Gate:** `R23_SOURCE_PHYSICAL_CROSS_AUDIT_PASS` / `AUTHENTIC_SEMANTIC_REVIEW_NOT_COMPLETED` / `SOURCE_COMPLETE=0` / `COGNITIVE_ADMITTED=0` / `BROKER_FILLS=0` / `ECONOMIC_GATES_NOT_EVALUABLE`.

## 1. Qué se ejecutó, por qué y qué NO significa

Después de los censos R18–R22, el bloqueo no es encontrar más geometrías de cierre CISD: es identificar **el swing TTrades correcto, el POI verdaderamente relevante y el Protected Swing relacionado causalmente con ese POI**; sin ellos no existe elección fuente legítima de EQ, breaker, stop ni target, y tampoco admission cognitiva real.

El **Gate R23** unió **dos revisiones físicas independientes ya congeladas** para cada uno de los 107 dossiers outcome-blind (50 FVG bullish PRE-CISD, 50 controles sin FVG H1 en la ventana de tres H1 anteriores, 4 primeros toques en barra CISD con orden intrabar desconocido, y 3 FVG bearish PRE-CISD controles negativos):

- **R20-POI-RUN**, [CI #38975212429](https://github.com/mezas3238-hue/qore-core/actions/runs/38975212429): reconstrucción de FVG H1 con M15, serie original bajista M3 y primer toque del POI por source-bar-ID; full original 2.657, 143 FVG bullish tocados durante bearish run, sin pretensión author-significant.
- **R22**, [CI #38975204483](https://github.com/mezas3238-hue/qore-core/actions/runs/38975204483): revisión independiente de candidatos múltiples de H1 lows, FVGs, y contexto NY day-to-date (proxy físico, **NO regla TTrades**). Sus 107 packets comparten la misma selección por SHA del R19, pero no importan ninguna nueva estrategia ni segundo programa.

**R23 comprueba que ambos expedientes coinciden en TODOS los 107 IDs, mercado, categoría original, rango temporal, semilla / rank congelado y source witnesses por caso.** Rechaza firmas falsas, señales económicas, referencias de POI/swing sin evidencia, contextos discordantes, duplicaciones, cambios de hash, alteración de denominador o procedencia fuera del único programa VT08. Cada `review_dossier` contiene el contexto concreto, prueba de la serie bearish, tipo de POI, nivel/touch y ocho preguntas metodológicas abiertas con URL primaria y espacio para dos revisores independientes. NUNCA rellena respuestas humanas por heurística. Se distingue **`AWAITING_REAL_REVIEW`** de `D_SOURCE_UNSPECIFIED` (esta última etiqueta solo puede justificarse al revisar fuentes y contraejemplos).

## 2. CI final y resultados reales

**[GitHub Actions R23 #39037632164](https://github.com/mezas3238-hue/qore-core/actions/runs/39037632164)**, **5/5 SUCCESS**, Ruff + **12 adversariales por mercado = 60 tests PASSED**, sin read PnL/7Y, sin sizing, fills ni operaciones. Archivos:

- `src/qore/infrastructure/trader_lab/vt08_b_r23_semantic_review_firstfail_ledger_v1.py`
- `tests/infrastructure/trader_lab/test_vt08_b_r23_semantic_review_firstfail_ledger_v1.py`
- `.github/workflows/vt08-b-r23-semantic-review-firstfail.yml`

| Mercado | Censo original preservado | Expedientes R23 | Estado |
|---|---:|---:|---|
| EURJPY | 538 | 21 | WAIT |
| USDCHF | 518 | 21 | WAIT |
| NZDUSD | 550 | 21 | WAIT |
| CADJPY | 516 | 21 | WAIT |
| USDCAD | 535 | 23 | WAIT |
| **TOTAL** | **2.657** | **107** | **0 A/B signoffs** |

**SHA256 reproducible de JSONs R23 finales:**
- EURJPY: `642751096ea272b327838aef6e1ed4665053901219b10b4ad1744619845a0c7c`
- USDCHF: `5af3eacb822456217d3a05e0e6d46dd015b445a168a43f64143e64ac1ca9c346`
- NZDUSD: `1d534eb82a45f6fae8386eb896d47ad2cdaf3d0fedc5b51fa3339124e683b3eb`
- CADJPY: `1ec64b4bff295b2b18d0e96010ddfc6943fadc0dd7336abc6347b05fd5627dd9`
- USDCAD: `31f8241ad67c1a1d3ddbb90efe47c89f524b4e769544abada2cc35c952b4647e`

**Estratos internos dentro de los 107:** 50 sin FVG H1 local (¡no necesariamente sin otro POI!), 4 primer contacto en la barra CISD (tick order desconocido); de los demás, **18** primer contacto FVG durante la serie bearish M3 y **35** antes de ella (incluye los tres controles FVG bearish). Estas son características físicas para ayudar a los revisores, NO casos certificados.

## 3. Las ocho exigencias por caso, no ocho reglas nuevas de trading

1. **Relevant Swing:** barra/timeframe del nivel, separación cualitativa, HTF 3-candle live window versus 3-bar confirmed pivot, competidores, instante as-of. Fuente: [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/).
2. **Important POI:** high/low/FVG previo, source IDs, elección entre candidatos realmente significativos, observabilidad antes CISD; no confundir contacto geométrico con relevancia. Fuente: [CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/).
3. **Protected Swing:** nivel barrido auténtico y serie de velas que lo creó, cierre sobre toda la opposing-series, POI al que reacciona, timestamps. Fuente: [Positional Entries](https://ttrades.com/positional-entries-enter-before-the-expansion/).
4. **EQ:** condicional C2 respecto al swing VERIFICADO, no confundir con dealing-range EQ. Fuente: [EQ (10-oct-2026)](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/).
5. **Breaker:** estructura Low→High→Lower Low→Higher High y velas originales, TF/breaker low, disponible para C3. Fuente: [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/).
6. **Stop:** en el Example1 M30→M3 por debajo de EQ y breaker-low; PS como referencia contextual, FVG inferior/ejecución y buffer no inventado. Fuente: [Timeframe Alignment](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/).
7. **Target:** highs HTF untouched, availability antes del nuevo entry open, competidores y selección fuente. Fuente: [Price Targets](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/).
8. **Cognitiva:** 27 `CAUSAL_FIELDS` reales, por caso y con evidencia independente B posterior al visto bueno metodológico. No igualar trazabilidad fixture a autorización real.

**Matiz esencial:** las ocho son obligaciones de **evidencia para la auditoría**, no requisitos cuantitativos artificiales, nuevos filters de rentabilidad ni respaldo del autor a una jerarquía universal para POI de reversal. Incluso 8/8 recibos físicos no prueban por sí solos que el autor especificó una regla de elección si continúa discrecional.

## 4. Acción inmediata asignable (A y B)

**Arquitecto A — primera revisión source-primary:** para los 107 `review_dossiers` entregados por R23, rellenar SIN PnL el `A_provenance_and_author_selection` de cada campo realmente auditable, citando URL/sección, source `bar_ids`/timeframe, nivel y `available_at`; cuando la elección sea discrecional, justificar `D_SOURCE_UNSPECIFIED` sin inventar umbral. Documentar `candidate_id`, todos los swings/POI competidores y motivo de no elegir. NO emitir `source_authenticity_accepted=true` sin revisión humana auténtica y B independiente.

**Arquitecto B — segunda revisión, realmente independiente:** contrastar cada afirmación de A con barras M3/M15 originales (no con los flags de A), validar clasificación TTrades, confrontar disensos, no asumir tick-order de misma M3, y jamás usar revisión ficticia para permitir cognitiva/órdenes. Hacer match al menos 107 IDs originales y revisar toda señal que aspire a author-complete, no sólo una muestra.

**Integración pendiente P0:** conectar el futuro resultado de adjudicación fuente/autenticidad a la frontera de admisión cognitiva verificada y a ejecución broker con autoría/firmas respaldadas por evidencia. **R23 es un gate de investigación por hoy, no un guard activo universal de todas las rutas LIVE.**

## 5. Límites invariantes del Owner

Solo **VT08 actual**. **QORE-alpha excluido completamente** del programa: no mezclas, forks, segunda vía ni estrategias derivadas importadas. Muestras R18–R23 permanecen source-only, 2.657 sin recorte económico. Holdout 7Y sellado, cero sizing, ningún LIVE/DEMO/VPS order/fill ni merge. **PF/DD/Sharpe/Sortino no evaluables mientras no haya señales autor-completas, cognitiva auténtica y bid/ask costes reales.**

**Dictamen:** `VT08_R23_PREPARACION_DE_ADJUDICACION_SOURCE_COMPLETE_INTEGRITY_PASS`, 0 operaciones certificadas. Nunca llamar «0 trades rentables» a «0 trades verificables».

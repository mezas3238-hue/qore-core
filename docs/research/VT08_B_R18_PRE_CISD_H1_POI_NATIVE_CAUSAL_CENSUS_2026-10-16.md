# VT08 B R18 — Inventario temporal real de POI H1 pre-CISD para 2.657 setups M30→M3

**Fecha:** 2026-10-16 · **Arquitecto B:** rama `agent/vt08-5m-cognition-replay-20261010`, PR #764 **DRAFT**. **Owner:** únicamente VT08 actual metodología TTrades+cognitiva; QORE-alpha **excluido**, R16 gobernanza probada. **Dictamen:** `PRE_CISD_HTF_POI_PHYSICAL_CUSTODY_PASS / AUTHENTIC_POI_SEMANTICS_STILL_D / VT08_NOT_CERTIFIED`.

## 1. Nuevo problema realmente atacado

R11–R14 ya habían demostrado 2.657 series opuestas / CISD **geométricos** originales dentro de C2. R17 identificó el P0 real: ni un nivel H1 relevante ni un FVG original estaba vinculado causalmente a la secuencia antes de CISD por caso. R18 no pretende resolver criterio subjetivo de relevance/selection, pero por **primera vez** adjunta un **inventario candidato temporal POI físico** con IDs de M15, H1 `available_at`, M3 touchdown `source_bar_id`, y fase PRE/INTRA/POST CISD.

**Fuentes primarias del autor:** [Relevant Swings (21-mar-2026)](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/) diferencia geometría de relevancia y declara sin fórmula numérica para separación; [Ideal Formation (27-jun-2026)](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/) espera reacción en POI + sweep + cierre C2 + PS, no equipara `found FVG` a señal. [CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) exige cerrar a través de velas que generaron nivel importante.

## 2. Implementación, controles de origen y cutoffs

- Código: `src/qore/infrastructure/trader_lab/vt08_b_r18_pre_cisd_h1_poi_native_timing_v1.py`
- Tests: `tests/infrastructure/trader_lab/test_vt08_b_r18_pre_cisd_h1_poi_native_timing_v1.py`, **16 adversariales**×5=**80**. Pruebas cubren M3 touch primero en barra anterior a CISD, CISD misma barra (orden intrabar **DESCONOCIDO**), posteriores, no-tocados, M3 discontinuos, relojes naive y H1 incompleta; reconstrucción sintética de gap bullish con doce M15, sin futuro.
- Workflow: `.github/workflows/vt08-b-r18-pre-cisd-h1-poi-native.yml`
- CI FINAL **[GitHub Actions #38902918264](https://github.com/mezas3238-hue/qore-core/actions/runs/38902918264)**, cinco mercados **SUCCESS**, Ruff+80/80 tests y todo censo original. La primera ejecución [#38902230164](https://github.com/mezas3238-hue/qore-core/actions/runs/38902230164) falló solo porque el test naive de reloj activaba ANTES una excepción de discontinuidad (fail-closed correcto); reparado test aislamiento en commit `50f3165810ca261ac71e467b7f21db0688c7963f`; inicial [#38902298416](https://github.com/mezas3238-hue/qore-core/actions/runs/38902298416) 5/5; se agregaron clasificación bullish/bearish y tres pruebas H1 reales sintéticas al final, sin alterar origen/datos.
- Fuentes originales **fijadas sin acceder al holdout**: A R3 GitHub Actions `#38715560333` `vt08-a-frozen-m30m3-firstfail-${market}-394116f13449fc310d7fbc5f0b5f60aa1bb247d4`; M3 cTrader `#35941643396`; M15 cTrader `#35934924907`. Se recalculan SHA M3/M15 originales, M15 contra `PINNED_M15`, se contrastan 10 receipts M3 C2 por caso con `source_bar_id`, precio y `available_at`, y se valida universo `audit_frozen_source_program_scope` R16 `VT08_CURRENT_ONLY_NO_QORE_ALPHA`.
- R18 toma **las últimas tres H1 completamente cerradas ANTES del inicio C2** (12 M15 raws; no la H1 parcial, ni H1 futura). Calcula 3 bajos H1 fuente; define posible **FVG bullish** solo si `H1_older.high < H1_newer.low` o **bearish** `H1_newer.high < H1_older.low`. Solo se etiqueta candidato geométrico, no FVG elegido ni POI significativo.
- Cada zona/nivel se cruza contra los 10 M3 originales C2. `TOUCHED_BEFORE_CISD_BAR` significa primera barra M3 **cerrada antes de que inicie la barra CISD** (sin lookahead), `TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN` prohíbe asumir secuencia de ticks dentro de M3, `TOUCHED_AFTER_CISD_CLOSE` no es POI observable previo, `NOT_TOUCHED_DURING_C2` no acredita interacción. **Una H1 incompleta CADJPY queda en cuarentena**, jamás rellenada o contada como FVG ausente.

## 3. Censo real (5 mercados, 2.657 fuentes originales)

| Mercado | R3 source | H1 completas | FVG H1 total | FVG bullish | Bullish FVG TOUCHED antes barra CISD | Todos FVG TOUCHED antes CISD | H1 low candidate tocado antes |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURJPY | 538 | 538 | 115 | 52 | 31 | 32 | 337 |
| USDCHF | 518 | 518 | 116 | 59 | 36 | 36 | 324 |
| NZDUSD | 550 | 550 | 106 | 59 | 33 | 33 | 362 |
| CADJPY | 516 | 515 | 110 | 59 | 33 | 33 | 326 |
| USDCAD | 535 | 535 | 127 | 61 | 32 | 34 | 345 |
| **TOTAL** | **2.657** | **2.656** | **574** | **290** | **165** | **168** | **1.694** |

**Interpretación cuantitativa:** 574 FVG H1 de tres velas previas (290 bullish, 284 bearish). De los 574, 168 primeros contactos M3 acabaron **antes del inicio de barra CISD** (**165 bullish y 3 bearish**), 4 contactos iniciales ocurrieron dentro de la barra CISD (secuencia física desconocida; **todos bullish**), 20 tuvieron contacto recién DESPUÉS del CISD, 382 nunca tocados en C2. La cifra **165** no equivale a 165 setups auténticos; no hay validación de swing, liquidez relevante, PS, elección de POI, EQ, breaker, stop, target ni cognitiva. El FVG puede ser un POI de continuación o reversión, y un gap sin historial anterior de touch no es automáticamente `untouched`.

Al menos uno de los 3 H1 lows previos tuvo contacto físico anterior a la barra CISD para 1.694 candidatos; **no** se ha demostrado que esos H1 lows sean swings relevantes ni POI elegidos. Los 165 con FVG bullish anterior NO deben **reemplazar** los 2.657 del denominador para el estudio: solo forman un estrato de revisión source-blind pre-PnL.

**SHA256 de reportes completos inmutables R18 CI FINAL:**
- EURJPY: `aa4e64613aad028548f1d07cf4ed8f4c4ae5a8aa3ebbd5454943e7e2ee2fd5b9`
- USDCHF: `f306859c13b3925b42f6c1b49f5eb62497d3c72235a4a49fbdb5979872f043f6`
- NZDUSD: `1bb8871d28fe2217b1d1e9187fd99e1b9260090258ab4f5995959cdcebb103f3`
- CADJPY: `f0e3d2dd7fb1cc73e4cb4d2a07c25fb93b76137e09ff0f1fdc607eba288a0dbc`
- USDCAD: `bec27d9651a65d85502dd62c319f258d540a56784c0b141efccdf973946332a6`

**Output report `all_pre_cisd_h1_poi_source_witnesses`:** market, `case_id_sha256`, `c2_opened_at`, `cisd_closed_at`, `c3_opened_at`; low kandidatos H1 con `source_h1_opened_at`, H1 `available_at`, 4 source M15 bar IDs y touch phase; FVG 3bar con lower/upper, H1 `available_at`, los ocho IDs del H1 older/newer, touch phase; false inmutables `author_relevant_swing_selected`, `author_poi_significant_and_selected`, `author_protected_swing_adjudicated`, `author_source_complete`, `cognitive_admission`, `broker_fill`.

## 4. Próxima fase P0 — resolver autoridad metodológica real, no acumular geometría

**Arquitecto A:** clasificar ciegamente casos estratificados SIN PnL, empezando por (i) 165 FVG bullish pre-CISD, (ii) 4 first-touch en barra CISD ambigua, (iii) 382 FVG no tocados, (iv) reversión con low H1 pero sin FVG, (v) CADJPY gap y casos multipoi. Para cada fila, dictaminar: `POI_exists_before_CISD`, `POI_significant_author`, `POI_swept_or_reacted_causally`, `selected_POI_ID`, `referenced_swing_ID`, `PS_opposing_series_origin_ID`, `level available_at`, reglas fuente A/B/D. Registrar **disentimiento**; jamás seleccionar por RR/PF.

**Arquitecto B:** verificación independiente de IDs, reloj y distinción de primera interacción **antes de cierre CISD vs en barra CISD**; controlar cuál H1 está completa y cuál provisional, evitar reconstruir gap a través de finde; revisar manual ciega con evaluadores independientes y métricas de desacuerdo. No etiquetar `H1_3BAR_FVG` como FVG realmente **relevante** por simple touch. Si ambigüedad D no resoluble por fuente, WAIT.

**Operacional:** firma dual manifest, 27 campos `CAUSAL_FIELDS` en `evaluate_provenanced`, stop bajo EQ & breaker de Example1 y PS fuente, target untouched source, bid/ask completos, costos y Gates económicas permanecen P0. Ningún derecho para LIVE/DEMO/VPS ni sizing/merge.

**Estatus:** R18 **5/5 SOURCE_POI_TIMING_PHYSICAL_PASS** · `SOURCE_COMPLETE_ENTRIES=0` · `REAL_COGNITIVE_ADMISSIONS=0` · `BROKER_FILLS=0` · `PF/DD/SORTINO=NOT_EVALUABLE` · `SEALED_7Y=UNTOUCHED` · `QORE_ALPHA=EXCLUDED` · VT08 **NO CERTIFICADO**.

**R18 fuente enriquecida (16-oct-2026):** commit `9349cc84ee245c68291db60b4613411453061c94` añadió `first_touch_m3_source_bar_id` original a cada H1 low/FVG tocado (incluyendo phase IN/POST), que se comprueba por receipts cTrader en toda la cohorte; reporte anterior y hashes iniciales quedan sustituidos por CI FINAL #38902918264 y los SHA anteriores. El censo, conteos y estado D permanecen iguales. Esta ampliación no firma la semántica TTrades.

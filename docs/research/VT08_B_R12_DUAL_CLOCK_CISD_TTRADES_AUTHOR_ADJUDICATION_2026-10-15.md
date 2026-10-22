# VT08 B R12 — Doble reloj de CISD y cierre HTF: prueba causal exhaustiva, sin promoción metodológica

**Corte:** 15-oct-2026 | **Rama:** `agent/vt08-5m-cognition-replay-20261010` | **PR:** [#764](https://github.com/mezas3238-hue/qore-core/pull/764) | **A:** [#765](https://github.com/mezas3238-hue/qore-core/pull/765)  
**Ejecución verificable:** [CI #38795035783](https://github.com/mezas3238-hue/qore-core/actions/runs/38795035783) (head de código y tests `47c1365ed7c3f2f73efb854159ee3f2368aa6ad9`), **5/5 SUCCESS, 7 pruebas adversariales por job = 35 ejecuciones y Ruff PASS**. Nada operativo ni económico.

## Hallazgo P0 del texto primario

[TTrades — How CISD Confirms Swing Points, 10-ene-2026](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) contiene **dos instrucciones de orden observacional que requieren interpretación conjunta, no citas aisladas**:
- «How I Use CISD With Swing Points» (párrafos tras definición): se obtiene un cierre HTF candle 2/3, luego se baja al LTF y se **comprueba el CISD dentro de esa vela HTF**.
- «The Fractal Nature of the Model»: enuncia HTF closure, luego LTF CISD, luego continuación.
- [TTrades — Positional Entries, 08-ago-2026](https://ttrades.com/positional-entries-enter-before-the-expansion/) «The Fractal Model Comes First» exige un modelo ya formado con cierre HTF válido y CISD LTF **antes** de considerar el nuevo HTF open.

Estas frases pueden leerse como (I) orden físico estricto `HTF.close < formación CISD LTF` o (II) secuencia de **validación retrospectiva**: CISD LTF se forma dentro del HTF y solo se determina que ambas condiciones se satisfacen cuando se cierra HTF; no son reglas equivalentes. La fuente **sí dice «inside that higher time frame candle»**, por lo que imponer automáticamente (I) como única interpretación contradice ese fragmento. Tampoco es lícito proclamar (II) «SOURCE_A aprobado para VT08» sin revisión A/B de ejemplos, identidad HTF y fuente/video. Este informe **no elige entre interpretaciones por PnL**; emite relojes separados y estado `D_UNADJUDICATED`.

## Implementación R12 independiente, source-only

- Código B: `src/qore/infrastructure/trader_lab/vt08_b_r12_dual_clock_cisd_source_v1.py`
- Pruebas: `tests/infrastructure/trader_lab/test_vt08_b_r12_dual_clock_cisd_source_v1.py`
- CI: `.github/workflows/vt08-b-r12-dual-clock-cisd-source.yml`
- Descarga R3 fuente congelada A [#38715560333](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333), y M3 cTrader real [#35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396), **run y nombres pinned**, no outcomes.
- Reutiliza la atestación B R11 para **recomputar** raw M3 SHA, all original `source_bar_id` para las diez M3 de C2, OHLC, `available_at`, mercado, timezones, `opposing_series_opened_at`, deduplicación y cierre M3 físico coincidente.
- Produce para **cada uno de los 2.657 eventos congelados** `case_id_sha256`, mercado, `c1_closed_at`, `c2_opened_at`, `c2_closed_at`, `m3_cisd_proxy_formed_at`, `earliest_jointly_observable_at = c2.close = C3.open`, dos flags de comparación y campo explícito `original_author_rule_status=D_UNADJUDICATED`. No produce selección de swing/POI/SL/TP/entrada/fill.
- Ataca falso signoff/fill, M3 futuro, RAW corrompido, duplicidad, falsas horas de disponibilidad. `APPROVED_A_B_MANIFEST_SHA256` permanece sin firma; ledger `sizing_used=false`, `holdout_7y_accessed=false`.

## Censo físico original completo

| Mercado | R3 M3 PS/CISD proxy únicos | Se formó ANTES de C2.close | MISMO instante C2.close | Se formó DESPUÉS | Ambas condiciones físicas consultables al C3.open |
|---|---:|---:|---:|---:|---:|
| EURJPY | 538 | 507 | 31 | 0 | 538 |
| USDCHF | 518 | 483 | 35 | 0 | 518 |
| NZDUSD | 550 | 519 | 31 | 0 | 550 |
| CADJPY | 516 | 481 | 35 | 0 | 516 |
| USDCAD | 535 | 514 | 21 | 0 | 535 |
| **TOTAL** | **2.657** | **2.504** | **153** | **0** | **2.657** |

SHA256 canónico por market de **los cinco reportes completos R12** (SHA del JSON, no necesariamente hash ZIP):
- EURJPY: `a05c7796c01c5fec3ca1dd82f55e9aea42921ec1363844eb6467963472e694a2`
- USDCHF: `52646fc70d2ebcbe8856a2343f0cde761be1834dea118f560926a2520d31070b`
- NZDUSD: `cf53a57e121133f4452e9bab506a4dd6b1dafd037b02dece9369052d870c9999`
- CADJPY: `8c70ac59e5aa6e79223ac4182bf259634f4c6115d7442d2b2abf2e1dd0c4c0a5`
- USDCAD: `d85c0b1d1410b632c425f62104393b44f97c47cff8da7549e1041b9164f47999`

**Importante:** estos 2.657 son precursores M3 proxy, NO 2.657 CISD TTrades realmente validados. «Ambas condiciones físicas consultables al C3.open» no equivale a existencia de cierre autor-válido, relevant swing, POI, protected swing real, breaker, EQ, SL, target o feed BID/ASK.

## R12 CI y correcciones transparentes

- [Run #38794839352](https://github.com/mezas3238-hue/qore-core/actions/runs/38794839352) FAIL por import `datetime` sin usar (Ruff); corregido removiendo exclusivamente import.
- [Run #38794909357](https://github.com/mezas3238-hue/qore-core/actions/runs/38794909357) FAIL por fixtures de test que omitían `semantics=OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE`, **correctamente rechazadas** por atestación B de fuente original. Se corrigieron únicamente los datos sintéticos de test; no se relajó validador.
- [Run #38795035783](https://github.com/mezas3238-hue/qore-core/actions/runs/38795035783) SUCCESS 5/5, Ruff + 7/7 por mercado y cinco artifacts de cronología con retención de 30 días.

## P0 siguiente — decisiones fuente que no pueden sustituirse por ingeniería

**Architect A (issue #762):**
1. Escribir la **especificación primaria** por evento de cierre HTF de confirmación: `C2 M30`, `C1 M30`, otro HTF u `UNRESOLVED_D`, con URL+sección+ejemplos fechados de texto/vídeo original. No llamar al mero `C1.close < CISD` validación fuente: C1 puede no ser un cierre candle2/3 correcto.
2. Determinar si el CISD retrospectivamente revisado al cerrar C2 es suficiente para esta familia de **entrada C3 POS**, o si la fuente exige otro modelo ya completo. Distinguir expresamente `formation_at`, `verification_as_of` y `entry_at`.
3. Exigir auténtico `relevant_swing`, separation, LTF opposing series, protected swing, POI reversal, EQ condicionado, SL, target HTF y condiciones breaker si aplican; marcar D todas las decisiones fuente irresueltas, no inferir de datos geométricos ni seleccionar 153 simultáneos por resultado económico.

**Architect B (issue #763):**
4. Cuando exista prueba A, validar `source-rule-ref`, `htf_confirming_candle_id`, `closed_at`, `m3_cisd_source_id`, `cognitive_cutoff`, fuente market SHA; rechazo de 27 CAUSAL_FIELDS con valores sintéticos. `evaluate_provenanced()` sigue fail-closed.
5. Después de doble revisión A/B independiente y preregistro Owner, recién pasar a operaciones broker BID/ASK+costes, comparativa homogénea A-only vs A+B, PF/DD/Sharpe/Sortino/MC/OOS con **sizing prohibido** y 7Y sellado hasta autorización formal.

**Veredicto:** `PHYSICAL_TEMPORAL_EVIDENCE_PASS`; `SOURCE_AUTHOR_TEMPORAL_SEMANTICS=D_UNADJUDICATED`; `COGNITIVE_REAL_ADMISSIONS=0`; `BROKER_FILLS=0`; `PF/DD/SORTINO/SHARPE=NOT_EVALUABLE`; VT08 **NO CERTIFICADO**. Ningún PR fusionado, no trading, sin override de holdout.

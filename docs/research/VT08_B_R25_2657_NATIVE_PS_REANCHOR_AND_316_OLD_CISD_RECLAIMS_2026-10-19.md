# VT08 B R25 — 2.657 mínimos reanclados as-of CISD, 316 breaches reales, 301 reclaman nivel, 15 sin recaptura

**19-oct-2026** · PR B #764 DRAFT, PR A #765 DRAFT · Mercado VT08 actual: EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD · **NO QORE-alpha** · No sizing, no 7Y holdout, no broker órdenes LIVE/DEMO/VPS.

## 1. Resultado de ejecución ORIGINAL, no estimación

**[GitHub Actions R25 #39338842612](https://github.com/mezas3238-hue/qore-core/actions/runs/39338842612)** — **6/6 SUCCESS** (Ruff, 20/20 tests adversariales más 5 jobs con RAW cTrader M3), commit ejecutado **`6409087eb359145f190db137d0a630ebe9386aaa`**. Cada mercado descarga los **artefactos originales fijos**, verifica `case_id_sha256`, SHA original R19 por mercado, M3 fuente cTrader ID/UTC/OHLC, y reconstruye independiente el `opposing series`+CISD original mediante B R14 SIN importar el detector A. **2.657 de 2.657** conservados y los **107/107** expedientes preregistrados preservados sin PnL.

**R24** había medido 809 casos con mínimo de serie original stale: 564 por mecha inferior en la propia barra de CISD y 348 por vela posterior más baja que el antiguo run-low, con 103 solapados. La pregunta **R25** es más estricta: `true_asof_first_CISD_closed_low=min(old_opposing_run_low, low_of_confirming_M3)`. Este mínimo provisional más conservador sí estaba observable al finalizar CISD. A continuación B busca cualquier vela M3 **completamente posterior** a la confirmación y anterior a abrir C3 cuyo `low<corrected_low`. Para el conjunto que lo atraviesa, clasifica si la vela del nuevo low cierra sobre el nivel inicial del CISD (apertura de la serie bearish anterior), si hay **un cierre posterior** recuperándolo, o si no se recupera hasta C3. Recalcula todas las barras y precios contra fuente, sin usar ticks imaginarios.

| Mercado | Censo | Antigua serie low reemplazada al cerrar CISD | M3 POST-CISD rompe mínimo **corregido** | Recupera nivel previo en **misma** vela del nuevo low | Recupera en **posterior** cierre M3 | No recupera por C3 | Sin nuevo low bajo el mínimo corregido |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURJPY | 538 | 116 | 74 | 10 | 61 | 3 | 464 |
| USDCHF | 518 | 105 | 60 | 10 | 46 | 4 | 458 |
| NZDUSD | 550 | 95 | 53 | 7 | 42 | 4 | 497 |
| CADJPY | 516 | 119 | 64 | 8 | 55 | 1 | 452 |
| USDCAD | 535 | 129 | 65 | 8 | 54 | 3 | 470 |
| **TOTAL** | **2.657** | **564** | **316** | **43** | **258** | **15** | **2.341** |

**Reconciliación:** `43+258+15=316`; `316+2341=2657`. La definición correcta evita considerar automáticamente que 348 rompieron el mínimo as-of confirmación: **32** rompieron el low antiguo de la serie, pero la barra confirmadora CISD ya había marcado un low aún más profundo que las velas posteriores. **Esta corrección es material**, no un cambio para mejorar resultados económicos.

Los **301** casos que cierran otra vez por encima del antiguo CISD (`43+258`) *no* se convierten en `author_confirmed_second_CISD`. **El nivel antiguo puede no ser la serie que creó el NUEVO low**, no sabemos qué POI era importante, y el requisito fuente de cierre sobre las velas **correctas** sigue sin resolver. Ninguno de los 2.341 casos sin nueva ruptura prueba source-valid PS: conservar nivel ≠ validación del autor.

**Base metodológica primaria original, comprobada 19-oct:** [Protected Swings](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/) exige barrido de low o llegada a FVG y cierre de la serie opuesta **que formó el low**, y espera que ese low permanezca intacto en continuación; [CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) exige el nivel importante y la serie **que produjo el movimiento hacia el nivel**, en convivencia con cierre C2 HTF. **R25 verifica solamente la historia física del low y la recuperación del nivel anterior, NO demuestra que exista la segunda confirmación válida de esa serie nueva**, ni inventa un selector universal.

## 2. Tres casos REALES preseleccionados ciegamente — dictamen negativo/positivo limitado a hechos

### Caso A: USDCHF 27-sep-2023, contradicción estructural posterior seguida de cierre tardío

- Identidad original ciega R19 `83c687ffa373093c3ea211eafdbb4f015f9068cfc8aa0fceb5f8184799bcb990`. C2 abre 13:00 UTC; primer CISD cierra 13:06; `old run-low=0.91758`; `confirming wick-low=0.91767` => `asof-CISD low=0.91758`; `old CISD breakout level=0.91782`.
- Primer M3 posterior que viola low corregido cierra 13:12 UTC, `low=0.91750` (bar SHA `3d2c6d8041545d87abd49fafc600c68e8da2f5dc21a26f7178bc9001302d456a`; R24 custodia original).
- R25 verifica que un **cierre M3 de 13:30 UTC** recupera `>0.91782`, exactamente a `C3.open`, fuente original en artifact R25 por `first_close_reclaiming_old_level_source_bar_id`. Esas barras eran observables **en el instante de decisión C3**, sin lookahead. Dictamen fuente físico: `LATER_M3_CLOSE_RECLAIMS_OLD_CISD_LEVEL`, pero reentrada por **serie que creó nuevo 0.91750** aún `D/WAIT`; no crear nueva PS ni trade.

### Caso B: USDCHF 07-nov-2023, nivel roto y recuperado antes de C3

- ID R19 `c463ba07bb354d4cd617f8d3c0d1a8073a9cd9b67c7c3f19af43b6321189dbae`. C2=12:00 UTC; primer CISD 12:09; old run-low=0.90072, confirming low=0.90077; level=0.90094.
- M3 12:15 hace `low=0.90069`, bar fuente R24 `00a27e66ca41b2da89410b6ce7b6ae011d6c750b91638cf24561014f993cae1a`; M3 **12:27** recupera el nivel anterior `>0.90094`, antes de C3=12:30. Mismo primer CISD viejo **no** autentica segunda serie y no demuestra el important POI. Se exige fuente original y selección A/B independiente.

### Caso C: NZDUSD 25-feb-2026, corrección que elimina una falsa «segunda ruptura»

- ID R19 `ab42c7b10290b2ab1af37cb9efc479fbc3366fb3f3a601f96810a95d510088d1`. C2=09:00 UTC; CISD=09:18; old bearish-run low=**0.59735**; barra M3 que **confirma CISD** marcó bajo **0.59723**, por lo que el low provisional observable al confirmarse es **0.59723**, no 0.59735.
- M3 de **09:21** marcó 0.59733, menor que antiguo 0.59735 pero **MAYOR** que 0.59723. Por eso R24 clasifica violación del proxy viejo, mientras R25 demuestra `NO_POST_CISD_NEW_LOW_BELOW_CISD_ANCHOR`. El PS autor sigue `D/WAIT` por falta de POI/serie exacta; prueba un **error de interpretación del origen mínimo** si se usara sólo el R24 proxy antiguo.

En cada caso la evidencia fuente contiene original cTrader M3 SHA/bar_id, RSI/PNL prohibidos, hashes de expediente R19 sin cambiar, y las 8 obligaciones R23 abiertas. **Estas son adjudicaciones de identidad/cronología física con pruebas (no dos opiniones A/B firmadas ni decisión author-semantic `SOURCE_COMPLETE`).**

## 3. Implementación entregada y archivo de resultados

- `src/qore/infrastructure/trader_lab/vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1.py` — verifica 10 barras M3 completas, primera serie bearish original y breakout level, reancla low de la barra CISD as-of y busca LOW+CLoses entre el CISD y C3. Todos los precios `Decimal`. Fuente RAW obtenida por `_raw_bars`, `_verify_bar`, IDs con SHA firmemente verificados. No A producer ni selección por PnL.
- `tests/infrastructure/trader_lab/test_vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1.py` — 20 PASS en CI: clases as-of, same-bar/next-bar reclaim, LOW ya corregido, veto de datos futuros, OHLC corrupto, falso precio del PS, falsa firma, R19 modificado, holdout tocado.
- `.github/workflows/vt08-b-r25-original-ps-reanchor-and-old-cisd-level-reclaim.yml` — **6/6 SUCCESS**, retención 30 días, cinco artifacts `vt08-b-r25-original-reanchor-reclaim-{MARKET}-{HEAD}`. `full_source_case_index` de todo el original 2.657, `same_107_r19_blind_source_review` de la misma muestra pre-PnL sin reelección.

## 4. Acción inmediata para desbloquear certificación REAL sin false positives

**Arquitecto A PR #765:** en los tres casos anteriores mostrar qué POI/swing relevante pre-CISD existía por TF, si los nuevos lows constituyeron cambio de PS que **realmente** fue confirmado por un segundo cierre sobre *la nueva serie de velas*; si no, dictaminar `D_SOURCE_UNSPECIFIABLE` y `WAIT`, no ocultar la imposibilidad bajo reanclaje numérico. Priorizar los **15** originales que no recuperaron el nivel al llegar a C3 (negativa física) y los **316** con low corregido roto; mantener los 2.657 intactos, no convertirlo en backtest de 301.

**Arquitecto B PR #764:** dar revisión realmente independiente sobre OHLC+bar IDs A (no autoproducir A/B firmas). Distinguir cierre sobre antigua serie de cierre sobre nueva serie. La confirmación correcta depende de fuente de autor y POI relevante, no de `post_break_old_cisd_level_reclaim`. El artículo no prescribió universalmente `reclaim(previous run.open)=new PS` — prohibido implementarlo como filtro source-grade sin A+B.

**Infra cognitiva y economía:** hasta disponer de dictámenes A/B reales sobre source-selected POI, protected swing, breaker, EQ/SL/target y todos los `27 CAUSAL_FIELDS`, `CandidateEvent SOURCE_COMPLETE=0`; `cognitive_admissions=0`; `broker_fills=0`; **PF/MaxDD/Sortino/Sharpe/OOS/MC NOT EVALUABLE**. Holdout 7Y sellado; sin sizing ni mezclas QORE-alpha. No LIVE/DEMO/VPS orders y PR A/B DRAFT.

**Estado final R25:** `NATIVE_PHYSICAL_CONTRADICTION_AND_RECLAIM_PASS`; `SOURCE_COMPLETE=0`; `COGNITIVE=0`; `ECONOMIC_GATES_NOT_EVALUABLE`; **VT08 NO CERTIFICADO**.

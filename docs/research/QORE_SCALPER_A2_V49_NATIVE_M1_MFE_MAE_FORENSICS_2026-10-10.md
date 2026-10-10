# QORE Scalper — MFE/MAE nativo M1 post-V49 y relectura DeepSeek Expert

**Fecha:** 2026-10-10; **arquitecto responsable:** B, metodología PR #759, issue #757; A1 Cognitiva PR #758, issue #756. Origen: PR #623. **Estado:** diagnóstico preregistrado / solo GitHub / sin órdenes ni VPS / sin certificación.

## Hechos congelados antes del nuevo diagnóstico

El control V49 de nueve mercados con M1 nativo de GitHub está publicado en [run #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), matriz [#11670728222](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695/artifacts/11670728222), datos originales M1 [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), origen SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. Ventana de desarrollo 2025-09-17 a 2026-09-17.

V49: 2,876 oportunidades simuladas antes de MAX3, 2,020 seleccionadas, 1,167 ganadoras, 852 perdedoras, una plana; ganancia +461.943R, pérdida -695.212R, PF 0.66446, DD 236.134R, beneficio medio +0.395838R por ganadora y -0.815977R por perdedora. La asimetría de resultados **no prueba** que el sesgo H1 sea bueno o malo. MAX3 censoring histórico [run #38056081811](https://github.com/mezas3238-hue/qore-core/actions/runs/38056081811) dejó 856 oportunidades hipotéticas excluidas, PF 0.5983, inferior al grupo seleccionado; ninguna política de admisión fue cambiada.

El informe independiente DeepSeek retractó correctamente dos inferencias: `win_rate != H1_direction_hit_rate`; la auditoría de identidad es post-ejecución y no puede filtrar señales. Concluye que **MFE/MAE nativos por operación son la prueba prioritaria**.

## Contrato causal MFE/MAE — preregistrado ANTES del resultado real

**Código:** `src/qore/infrastructure/trader_lab/capitalizer_scalper_mfe_mae_v1.py`.  
**Tests:** `tests/infrastructure/trader_lab/test_capitalizer_scalper_mfe_mae_v1.py`.  
**Workflow read-only:** [GitHub Actions #38057290884](https://github.com/mezas3238-hue/qore-core/actions/runs/38057290884), source code SHA `6ca33be13e23cdcb5288f40a5326955ab1274215`. Contract suite GREEN antes del procesamiento de nueve mercados.  
**Dataset:** exactamente nueve artefactos M1 nativos usados por V49 y nueve archivos económicos V49 congelados en [control #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695). Se descargan vía GitHub Actions en cada job, se verifican manifest/provider native/no synthetic/read_only y su símbolo.

Sea `entry` el precio M1 ya confirmado, `risk = abs(entry-stop_M15)`. Para LONG:
- `MFE_R = max(0, max_bar_high - entry)/risk`.
- `MAE_R = max(0, entry - min_bar_low)/risk`.
Para SHORT invertir highs y lows. Normalizar las dos medidas por el **riesgo inicial del modelo estructural V49**, NO por beneficio, variación porcentual o dinero de cuenta.

### Frontera temporal e incertidumbre intrabar

- Solo examinar barras M1 **después de la confirmación/entrada** y **hasta la última barra del replay (inclusive)**, nunca barras previas ni movimiento posterior a la salida. Reconciliar por mercado, `entry_at`, `exit_at`, `m1_bars_held`, STOP/TARGET testigo y fecha de sesión. Una falta de barras, ID duplicado, símbolo erróneo o STOP sin cruce de precio INVALIDA informe: **no descartar esa operación silenciosamente**.
- `mfe_preterminal_r` / `mae_preterminal_r`: máximos observados **en barras completamente anteriores** a la vela de salida, sin contar extremos de la vela de salida (conservador; puede subestimar excursion ejecutable antes del fill).
- `mfe_full_exitbar_upper_r` / `mae_full_exitbar_upper_r`: extremos de barras previas **más OHLC completo de la vela de salida**; solo *envolvente observacional*, **NO máximo ejecutable antes de la salida**, porque M1 no muestra la secuencia de ticks intrabar. En particular, si stop y target se tocan en la misma M1, el replay V49 adjudica **stop primero**. Un high favorable posterior dentro de la vela puede ser incompatible con una posición ya cerrada; no contarlo como edge realizable.
- No se alteran stop, target, parciales, trailing, salida forzada de sesión, MAX3 ni las familias Sweep+CISD/FVG+CISD. La prueba es observacional post hoc, sin autorizar estrategias.

### Preguntas falsables para H5/H6/H7

| Hipótesis | Señal favorable a la hipótesis | Falsador/cautela |
|---|---|---|
| H5 salida prematura | En SESSION_EXIT, ganadores pequeños y/o perdedores muestran MFE alto **preterminal** respecto a R realizado; si no hay terminal hit, un cambio de salida requiere replay contrafactual | Un high dentro de la M1 de salida **no prueba** que era alcanzable en orden causal; V49 no impone parciales ni break-even del tipo que DeepSeek sugirió, sino STOP/TARGET/SESSION_EXIT |
| H6 stop M15 grande | Existencia de señales con alta MFE y bajo MAE preterminal, pero posterior stop; revisar relación R con distancia stop/volatilidad local y proponer stop M1 sólo tras fuente confirmada | Las pérdidas STOP necesariamente alcanzan 1R MAE en algún punto; MAE bajo **antes** de la barra STOP no prueba que el stop pueda estrecharse sin aumentar stop-outs |
| H7 asimetría intrínseca | MFE preterminal sistemáticamente bajo, MAE alto, reward target mediano ~0.443R y -1R stop; desagregado por familia y sesión | La ausencia de ganancia en esta muestra no implica imposibilidad de edge bajo la fuente TTrades original ni aporta win-rate/R:R publicados del autor |

La evaluación cruzará `selected by MAX3` vs `excluded simulated counterfactual` manteniendo 2,020 + 856 = 2,876, además de MARKET, ASIA/LONDON/NEW_YORK, `FVG_RETRACE_CISD`, `LIQUIDITY_SWEEP_CISD`, `H1_state_basis`, y motivo de salida STOP/TARGET/SESSION_EXIT. Los outcomes no entran en el selector.

## Salidas archivables

**Por mercado:** `scalper-a2-mfe-mae-market.json` + `scalper-a2-mfe-mae-trades.jsonl` con valor MFE/MAE y banderas de incertidumbre por cada operación simulada. **Matriz 9 mercados:** `scalper-a2-mfe-mae-matrix.json`, solo si los 9 jobs pasan y la identidad/riesgo/denominadores se concilian. Se pueden usar conteos por exit reason, promedio R ganado/perdido, mean MFE/MAE y cuantiles; no presentar la media MFE como beneficio capturable.

**No deducir todavía:** bias H1 accuracy a partir del win rate, premium sobre M1 stop, óptimo target, profit real BID/ASK, comisión, Sharpe/Sortino, PF V50-G hasta que [su replay #38053723674](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674) complete nueve mercados; y tampoco si una reforma de salidas generaría ventaja OOS. DeepSeek tiene razón en priorizar diagnóstico sobre optimización. La clasificación H5/H6/H7 sigue `HYPOTHESIS` hasta evidencia agregada y prueba de estabilidad.

## Coordinación A1

A1 deberá enlazar `source_opportunity_id`, H1/M15 bias/POI confirmed_at, Master Frame ASOF, memoria prequential settled-only y decisión WHY sobre la misma población. El MFE/MAE **nunca** se incorpora en la decisión pre-entrada ni al entrenar/escoger en la misma muestra. Pueden preregistrarse ensayos posteriores de stop M1 vs swing M15 y exits alternativos, pero solo después del diagnóstico; preservar ganadores de V49 (mínimo 934 y 415.75R **baseline mass**) y medir rentabilidad neta y DD causal.

**Protecciones:** Research-only GitHub Actions; NO producción, no VPS, no LIVE, no merges de PR #759/#758/#623, no certificación parcial por métricas de desarrollo.

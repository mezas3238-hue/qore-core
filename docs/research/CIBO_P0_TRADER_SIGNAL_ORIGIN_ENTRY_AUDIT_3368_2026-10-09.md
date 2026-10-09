# CIBO P0 — Auditoría forense del origen y causalidad de las 3.368 señales Trader

**2026-10-09 · RESEARCH ONLY · PR #748 · sin VPS/LIVE**

## Hallazgo obligatorio: M5 del ejecutor no es M5 de la señal

Manifiesto sellado `walk-forward-manifest.json` del artifact original **11451743578**, hash canónico registrado `sha256:6cbb18f5b79e8fab99431d3dffd2ef6a711f663dd625752ac505d2bac73e0b6e`; último replay de la cohorte financieramente simulada: run **37976407778**. La fuente es `cibo_single_account_7trader_maximum_capability_manifest.py`, que une tres eras de trabajo histórico reutilizado. El propio manifiesto declara `governance.reused_burned_research_population: true`, `fresh_oos_claimed: false`, `certification_claimed: false`.

`scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py` utiliza Atlas **M5** para obtener precio sintético de entrada y comprobar SL/TP, con spread de screenshot de octubre 2026. **NO** genera en M5 toda la señal. El timestamp y la `decision_context` originales pertenecen a estos Traders:

| Trader | Familia/fuente | TF original de contexto | Fuente 3368 | PAPER open | PAPER settled | Win% settled | PF settled | Net USD |
|---|---|---|---:|---:|---:|---:|---:|---:|
| R42_AUDJPY | Turtle Soup ICT, barrido/reclaim, C2/CISD, protected swing, DOL | H1 455 / H4 176 | 631 | 200 | 199 | 43.22 | 0.9717 | -1.6867 |
| R43_GBPUSD | Turtle Soup ICT, mismo tronco de patrón, su propia cognitiva | H1 485 / H4 76 | 561 | 55 | 55 | 43.64 | 0.7048 | -4.9950 |
| R38_GBPJPY | Turtle Soup ICT + políticas especializadas | H1 437 / H4 106 | 543 | 87 | 86 | 37.21 | 0.6923 | -12.0973 |
| R38_EURUSD | Turtle Soup ICT + políticas especializadas | H1 418 / H4 77 | 495 | 93 | 93 | 41.94 | 0.6773 | -5.1500 |
| R34_XAUUSD | Turtle Soup ICT + políticas especializadas | H1 434 / H4 58 | 492 | 5 | 5 | 20.00 | 0.3610 | -0.7937 |
| VT31_NAS100 | NY AM Silver Bullet, barrido + confirmación estructural + FVG/PD array | M1 484 | 484 | 89 | 89 | 16.85 | 0.4501 | -24.7075 |
| VT08_FOREX | B01 H4 PO3, M15, horarios NY y giro/protected swing | M15 162 | 162 | 11 | 11 | 27.27 | 0.3234 | -1.7444 |
| **TOTAL** | **siete productores** | H1 2229 / H4 493 / M1 484 / M15 162 | **3368** | **540** | **538** | **37.17** | **0.7166** | **-51.1746** |

Fuentes de ingeniería verificables:
- `src/qore/infrastructure/trader_lab/turtle_soup_eurusd_r1.py`, `turtle_soup_audjpy_r1.py`, `turtle_soup_gbpjpy_r1.py`, `turtle_soup_gbpusd_r1.py`, `turtle_soup_xauusd_r1.py`: `exact_c2_side`, `_raid_at`, `causal_cisd`, `protected_swing`, `_target_untouched`, `_source_signals`. Los módulos de investigación superiores añaden memoria y contextos, y no todos reproducen idéntica regla en cada versión.
- `scripts/cibo_phase22_v4_turtle_window_replay.py`: congela payloads de geometría/trades precedentes por lane (`phase18-*geometry-trades.jsonl`); por tanto, ¡nunca atribuir la ejecución a la versión actual del Trader sin verificación de SHA y reglas congeladas!
- `src/qore/infrastructure/traders/vt31_silver_bullet_r2_2.py`, `scripts/vt31_nas100_r1_candidate.py`: New York AM Silver Bullet, fuente original r2.2 y políticas de entrada explícitamente separadas. `vt31_nas100_native_perception.py` reconstruye contexto causal M1.
- `src/qore/infrastructure/traders/vt08_b01_r3_8.py`: B01 H4 PO3 con ventanas 01:00/05:00/09:00 NY, source M15 y reglas de contingencia research-only.
- `scripts/cibo_single_account_7trader_maximum_capability_manifest.py` y `scripts/cibo_build_walk_forward_expectation_manifest.py`: poblaciones reutilizadas de tres eras, señales y outcomes históricamente adjuntos por separado, expectativas únicamente con asentamientos anteriores.

## Hallazgos por clasificación predecisión — NO filtros aprobados

- **VT31/NAS100 (M1) explica ≈48,3% del perjuicio total**: 89 cierres, -$24.7075, PF 0.4501. De ellos **59** muestran `cash_open_state=bullish`: 7 ganadores (11,86%) y -$23.74 de PnL; es la primera hipótesis a auditar, **no una orden para bloquear bullish**, porque se ha observado sobre la muestra quemada y puede haber confusión con la dirección/momento.
- **R38/GBPJPY** concentra -$12.0973, n86, PF 0.6923. Combinados con VT31 aportan aproximadamente **71,9%** de la pérdida observada. Prioridad segunda de dirección, entradas y stops.
- **R42/AUDJPY** n199, PF 0.9717, net -$1.69. No todos los Traders parecen igualmente deficientes; la muestra tampoco prueba edge positivo.
- **Por origen temporal en la cohorte 538:** H1 405 cierres, PF 0.79, net -$25.93; H4 **solo 33** cierres, PF 1.10 y net +$1.20; M1 89 cierres, PF 0.45, net -$24.71; M15 11 cierres, PF 0.32. H4 no está validado por n33; no repetir que «todos son M5» o que «pasar a H1/H4» resolverá el defecto.
- `reg_h4_range_state=expanded` tuvo n44, PF ≈1.58; y `ctx_cisd_progress_bucket=q2:<=0.50` n92 PF ≈1.07. **Subgrupos post-hoc no son permiso de operar ni resultado OOS**.
- El origen H1/H4 se combina con precios y stops originalizados al MID de Atlas M5 sintético. Es obligatorio probar equivalencia del instante, símbolo, bid/ask real, geometría y contrato del Trader. Un replay que no preserva exactamente el timing de su señal puede degradar artificialmente una estrategia válida.

## Protocolo vinculante de auditoría Trader

**A. Reconstrucción exacta de entradas desde el código congelado, ANTES de optimizar:** por cada señal y Trader guardar `trader_id,source_module,source_SHA,source_event_id,decision_at,signal_at,execution_at,reference_timeframe,side,raid_at,reclaim_at,C2_close,CISD_confirmed_at,protected_swing,DOL_target,original_entry,stop,tp`; para VT31 rastrear sesión NY, cash open, rango/sweep/fvg y familia de la zona; VT08 reconstruir vela H4 y los horarios. Verificar `<= decision_at` para cada evidencia. Crear tests que detecten un `source_event` posterior a la decisión.

**B. Separación de dirección y timing:** medir si el setup se mueve favorablemente después de la confirmación frente a una referencia emparejada de mismo instrumento/día/hora/regime. Contrastar entry EXACTA congelada vs 1 y 3 barras causales M5 posteriores, sin mirar mejores precios retrospectivamente. La inversión de dirección solo es **control diagnóstico** (geometría distinta con presupuesto/costes independientes), no recomendación de operar al revés.

**C. Filtros/régimen antes de exposición:** auditar CISD temprano/tardío, rechazo y profundidad del raid, alineación H1/H4, DOL disponible, rango/volatilidad, sesión, cash_open_state para VT31, y contexto predecisión; comparar NAV/stop geometry y coste/beneficio sin usar el resultado para construir features.

**D. Controles nulos:** dirección aleatoria emparejada por símbolo/sesión, momentos horarios emparejados y etiquetas permutadas en bloques temporales. Comprobar si la señal original supera el control tras fees y spread. No comparar costes históricos sin obtener bid/ask con marca temporal auténtica.

**E. Generalización sin data mining:** 2019-2022 es investigación quemada; NO se acepta calibrar con 2019-2021 y declarar 2022 (8 cierres) un holdout robusto. Congelar toda regla de entrada y filtro, adquirir partición temporal realmente nueva, evaluar >= tamaños informativos por Trader con IC por bloques temporales, sensibilidad de fricción y PF+expectativa neta con cobertura y DD MTM. No garantizar ganancias por cruzar 50% win rate.

**F. Qué no hacer:** no aumentar 1.096 entradas bajo PF actual, no recortar estratégicamente VT31 en LIVE solo por informe, no culpar automáticamente a CIBO/QDLE ni exonerar por definición, no atribuir a estrategia nativa actual un replay con lane de geometría congelada distinta, no seguir optimizando stops/parciales como sustituto de verificar la señal.

## Entregables ejecutables y decisión

La nueva tarea automática `scripts/cibo_trader_lab_source_signal_audit_3368.py` integra un manifiesto congelado con el resultado PAPER por fingerprint SIN pasar resultados históricos a variables explicativas. Debe emitir `cibo-p0-source-signal-audit-3368.json` e incluir desglose por Trader, familia, TF, dirección, año y 4 contextos, dejando `RESEARCH_ONLY_FROZEN_BURNED_NOT_OOS`. CI verifica 3368/540/538, siete emisores, frecuencias H1/H4/M1/M15, cero LIVE y `fresh_oos_claimed=false`.

**Veredicto actual:** `ENTRY_EDGE_NOT_CERTIFIED_IN_CURRENT_FUNDED_PAPER_SAMPLE`. No hay prueba de expectativa rentable de la muestra, pero tampoco sentencia universal de que la estrategia ICT Turtle Soup o VT31 nunca tiene edge. El paso siguiente es reproducir la decisión del Trader desde su código congelado y comparar timing/registro real antes de hacer filtros adicionales.

# QORE-TRADER-STORY-FORENSICS-001 — auditoría independiente

Estado científico: **COMPLETE FOR ADJUDICATION / NO AUTHORITY**. No concede DEMO_ELIGIBLE, DEMO, LIVE, Production, Risk, execution ni capital real.

## Baseline, independencia y witness

Primera pasada aislada: HEAD `18dc5736a28369ffb7bc1cfd0fccabb2334b208b`, TREE `4a897527d3d3250ddaaddf89009f04d18decae88`, antes de consumir conclusiones Harness/Expert/Architect. Witness run `34466491554`: Ruff PASS; Mypy PASS; Pytest `7 failed, 7213 passed, 8 warnings`; cobertura ~83%.

Clase causal reproducida: fixtures/callers antiguos entregaban `qore.trader_lab.eleven_market_trader_dossier.v1` al panel que exige `qore.trader_lab.eleven_market_trader_research_dossier.v1`. El validator profundo era correcto. Se conservó el boundary shallow y se migró la integración profunda sin relajar exceptions.

## Findings y reparaciones

| ID | Evidencia y mecanismo | Falsificador/contraejemplo | Reparación | Confianza |
|---|---|---|---|---|
| TSF-001 | Migración shallow→research incompleta. | Shallow sigue válido en su boundary. | Fix focal de PR #506 validado. | Alta |
| TSF-002 | Frames raw emitían MFE antes de MAE por append. | Permutar timestamps. | Orden canónico `(timestamp, prioridad, stage)`; monotonicidad fail-closed. | Alta |
| TSF-003 | `decision_time` aceptaba oracle fields. | Inyectar exit/MFE/MAE/return. | Validator compartido en Story, sesión, review, replay/filmstrip y visual. | Alta |
| TSF-004 | USTEC/US500 se confundían con NAS100/SP500. | Alias sin certificado, SHA/account/digest alterado. | Binding Stage 1 conserva provider y mercado económico. | Alta |
| TSF-005 | Digests derivados no ligaban seis fuentes raw. | Sustituir exactamente WF/failure/Characterization. | Seis digests por mercado, replicados por fila Trader. | Alta |
| TSF-006 | Dossier omitía hora, weekday, calendario y funnel. | Comparación raw→derivado. | Contrato profundo preserva Characterization sin segunda fuente. | Alta |
| TSF-007 | Story no tenía self-digest de todos sus bytes. | Mutar payload sin actualizar hash. | `market_forensics_payload_digest` verificado antes de thesis. | Alta |
| TSF-008 | Primer repair de alias aún comparaba pack provider contra top-level económico. | Ejecución NAS100 real. | Comparación pack→provider y top-level→economic; test alias. | Alta |

## Provenance empírica 11 mercados

Se materializaron y analizaron los 11 mercados × 5 Traders. Dossier fingerprint `ae5d64052a27185ad236938e1e892a06a90654f82a1a0b475cd640bdb611b19a`. Cuenta DEMO/read-only `d9a5f41beca4584a2dc7eccc17015f40a707b99c72f74790b01ccddd7a5e8999`. Cada ZIP, run, software SHA, seis source digests, identity binding, Story self-digest y los 55 digests están en el manifiesto.

| Mercado | Provider | Run:artifact (contenido) | Story payload | Thesis |
|---|---|---|---|---|
| EURUSD | EURUSD | 34410292913:10128482613 (retained-full) | `5b0f6fa8d7d44f202ef179add79e2252a268ffbea59e5856741908def16b144c` | `2ca70cfe787492c6781a092c8744db0d5434fb379ed1393ef1e65e2b167e0f33` |
| GBPUSD | GBPUSD | 34410292913:10128945460 (retained-full) | `752d6b30adda8b685ae1e66e4aa530361a60ae5ad1d916938f2ee66835015e33` | `7d316e9975eb223a822db2ce82721d7123acd3ff59cca0e65dfd8e5c8c193c44` |
| USDJPY | USDJPY | 34410292913:10128928165 (retained-full) | `89f1941f020497b534c683be8c6775d1b5770d3536c97ac5190767408c7d7ebf` | `a960eb9b5d27892949c3e7c01e376aff0b4492e7b60848a7e3b4f2d36496b1b7` |
| AUDUSD | AUDUSD | 34410292913:10128986108 (retained-full) | `d2900ef64a9acefcb541d487ee89eb8d5a11b39647e16315f65a15e90ad5d50c` | `a64e7d7347fb2c99f21a3e08de9a05a1132064a50a7e809364ee338f1bb1056b` |
| USDCAD | USDCAD | 34410292913:10128813867 (retained-full) | `6883f7578c8147a2f4f3ea4088d9bdd6fda3a9834180fd6058191ab14e4e9db9` | `0e99a1f2b8ea20aae3450a3c9875a0cf75ea9c14be655ea488cbc37f0462760e` |
| XAUUSD | XAUUSD | 34410292913:10128461139 (retained-full) | `05031d6f5af02390d9fd73e7c23409841bf8516b780a45443f321ab193fc9240` | `9cf3b29922dbcfbd4e30c6be3e6aab2a1a7a1b3fa26161ebf5947d83dccd6a05` |
| NAS100 | USTEC | 34410292913:10128644190 (source-except-stage4); 34376439792:10133837821 (stage4) | `adb8a56ab2087c7455101ca2636ae41a3289b7f7bda61ace4fb7bf448c271fb0` | `beea0beb70638139df827e07f03263a31aab62596518cd45537b391940211543` |
| SP500 | US500 | 34410292913:10128611130 (source-except-stage4); 34376439792:10135078991 (stage4) | `2e741abe1e51f654b3901c599afbd90893da0655237ed64d17d5b857ef27a354` | `ff125fcc59de76d374f7c59e93e34146bb99db06db6c6d64bc41ac1d449d86f3` |
| GBPJPY | GBPJPY | 34408479696:10126766969 (stage1); 34408479696:10127952856 (stage2); 34408479696:10131315152 (stage3); 34408479696:10133737547 (stage4); 34408479696:10131359215 (stage5) | `f485338ad421c9ad85924c66dfc2ea877818132515b0df89ef1b1dcce8140373` | `68bbf195387fc02ad7a7869d604fecd42c90ca20f8a295a04fcea498a3e8f378` |
| AUDJPY | AUDJPY | 34408479696:10126760296 (stage1); 34408479696:10128086239 (stage2); 34408479696:10131351447 (stage3); 34408479696:10135443014 (stage4); 34408479696:10131359014 (stage5) | `8da47af6af39c813aec101b3122410ad7e14312093ea9f59f561476fb03fe2ae` | `197b6a6a193d7962e0a87645163e896042cde174a7df0a297cf002d6c4440f21` |
| US30 | US30 | 34433561975:10135672548 (stage1); 34433561975:10136366351 (stage2); 34433561975:10138842023 (stage3); 34433561975:10142855889 (stage4); 34433561975:10138848594 (stage5) | `248de328b1abe7317f1ee8539a2c161e5c9c84851e614fbeb1f6855507ed6dad` | `74c7d61f8c2bc5517feab8758b48d254fdf02071f1801e0c97498ed2ab64cbe9` |

## Resultado transversal

| Trader | Setups/fills | Story | IS+ | OOS PASS | Stress PASS | Streak W/L | Veredicto |
|---|---:|---:|---:|---:|---:|---:|---|
| VT-01 | 100,609/41,462 | 15,554 | 0/11 | 0/11 | 0/11 | 7/28 | STRUCTURAL_WEAKNESS |
| VT-08 | 2,776/1,047 | 252 | 6/11 | 3/11 | 0/11 | 16/6 | INSUFFICIENT_EVIDENCE / SPECIALIST_CANDIDATE |
| VT-09 | 220,964/213,394 | 99,690 | 0/11 | 0/11 | 0/11 | 8/35 | STRUCTURAL_WEAKNESS |
| VT-17 | 44,914/43,233 | 32,798 | 1/11 | 0/11 | 0/11 | 7/37 | STRUCTURAL_WEAKNESS |
| VT-31 | 45,758/16,818 | 7,610 | 0/11 | 0/11 | 0/11 | 6/29 | STRUCTURAL_WEAKNESS |

Direct-stop y giveback son familias empíricamente distintas. El primero tiene MFE casi nulo; el segundo llegó ampliamente a beneficio antes de perderlo. Un trailing sólo puede abordar lifecycle/giveback y no repara selección/entrada direct-stop.

## Cinco tesis individuales

### VT-01 — STRUCTURAL_WEAKNESS

**Comportamiento central y alcance.** NY liquidity sweep + FVG + midpoint y 2R aparece en 11/11 como identidad estable, pero no como edge: expectancy IS positiva en 0/11.

**Contraejemplos.** USDCAD es el menos negativo; SP500 el peor. Ninguno supera OOS ni Stress.

**Dirección y sesión.** LONG/SHORT cambia de ranking por instrumento; no existe dirección universal. La sesión NY está fijada por metodología, no es un experimento entre sesiones. LONG supera SHORT en 4/11 mercados; SHORT en 7/11.

**Regímenes y tiempo.** Los mejores trend/volatility/hour/weekday cambian por mercado; cualquier filtro post hoc queda consumido.

**OOS/Stress.** OOS PASS: ninguno; Stress PASS: ninguno.

**Ganadores, pérdidas y lifecycle.** Los direct-stops dominan y tienen MFE casi nulo; los givebacks alcanzan MFE material. Son mecanismos separables: selección/entrada frente a lifecycle. Direct-stop=7,130 (MFE medio 0.023R); giveback=3,015 (3.088R).

**Streaks.** Losing streak máximo 28 vs winning 7; hay clustering descriptivo, sin prueba causal de régimen.

**Preservar / riesgo de degradación.** Preservar NY, sweep/FVG, geometría 2R y ganadores canónicos. Ampliar sesiones o trailing calibrado con MFE futuro puede destruir selectividad.

**Mecanismo propuesto.** Selección insuficiente antes que simple fill; fill ~41% y RR 2R no compensan el exceso de stops directos.

**Falsificador.** Holdout fresco pre-registrado con expectancy positiva y Stress PASS en varios mercados, sin selección ex post.

**Evidencia faltante.** Tick/M1 para orden intrabar y holdout no consumido.

**Confianza.** Alta para debilidad histórica; baja para mecanismo causal. Mejor/peor: USDCAD (-0.00001684) / SP500 (-0.00013685).

| Mercado | fills/fill% | mean/WR/var | OOS n/mean/P | Stress/P | L/S mean | mejor sesión; trend; vol | Story direct/giveback W/L | digest |
|---|---:|---:|---:|---:|---:|---|---:|---|
| EURUSD | 3,517/39.58% | -6.26e-05/26.70%/4.18e-07 | 392/-2.11e-05/False | -2.21e-04/False | -5.51e-05/-7.00e-05 | ny-am-session (n=3517, -6.26e-05); mixed (n=287, -3.74e-05); low (n=65, 3.35e-05) | 1,358 644/240 5/16 | `aa0e50bdb7db3db8965d349de72ddd5499dd3d9e098a6617022912e272e88941` |
| GBPUSD | 3,568/38.85% | -4.92e-05/27.47%/4.31e-07 | 411/-5.31e-05/False | -2.53e-04/False | -7.09e-05/-2.57e-05 | ny-am-session (n=3568, -4.92e-05); range (n=3266, -4.66e-05); low (n=64, 8.72e-05) | 1,332 600/266 5/18 | `f9bbe109d9f45643965608e4cbf3214c61eccbdc0d6562e49793cbff7bd9fe30` |
| USDJPY | 3,526/40.60% | -4.79e-05/27.65%/5.67e-07 | 408/-4.91e-05/False | -2.49e-04/False | -6.22e-05/-3.37e-05 | ny-am-session (n=3526, -4.79e-05); insufficient-history (n=18, 1.90e-04); insufficient-history (n=33, 1.10e-04) | 1,311 577/247 5/17 | `9fe1ec19c6491a4f9c3ca6cf8655b86c119613f199119d39ed5fa8dd25104c3f` |
| AUDUSD | 3,711/41.72% | -1.00e-04/26.14%/6.73e-07 | 413/-7.26e-05/False | -2.73e-04/False | -1.07e-04/-9.31e-05 | ny-am-session (n=3711, -1.00e-04); range (n=3417, -9.47e-05); low (n=97, 3.86e-05) | 1,412 639/262 5/16 | `0051a0623f0ba6226e21f2c887636bdadb3dffff1fc308b36425dc4c453bbf26` |
| USDCAD | 3,511/41.45% | -1.68e-05/28.68%/2.84e-07 | 356/1.15e-06/False | -1.99e-04/False | -8.61e-06/-2.44e-05 | ny-am-session (n=3511, -1.68e-05); trend (n=7, 2.47e-04); low (n=42, 2.04e-05) | 1,318 567/269 5/19 | `b89524b4f87d71e49a5ef9f7269dd93a665880c376cd565f41495e457bffe86e` |
| XAUUSD | 4,014/40.02% | -1.01e-04/29.22%/3.25e-06 | 410/-1.87e-04/False | -3.87e-04/False | -1.69e-04/-2.82e-05 | ny-am-session (n=4014, -1.01e-04); mixed (n=319, 9.62e-05); insufficient-history (n=10, -3.33e-06) | 1,425 614/265 7/14 | `36e08c2bbfaf585300e242da91442aae14b09a2cbd0e5e6ad555c00bee28c06f` |
| NAS100 | 3,980/42.64% | -9.66e-05/26.53%/4.26e-06 | 440/-1.44e-04/False | -3.44e-04/False | -1.18e-04/-7.37e-05 | ny-am-session (n=3980, -9.66e-05); mixed (n=288, -2.37e-05); insufficient-history (n=12, 9.45e-05) | 1,507 705/306 5/21 | `840f18344a1e08ae0ef8dc5cc144d65214c15f4d5674bcd39b741502d4b65f7e` |
| SP500 | 3,707/43.92% | -1.37e-04/24.49%/2.15e-06 | 429/-6.65e-05/False | -2.67e-04/False | -1.47e-04/-1.26e-04 | ny-am-session (n=3707, -1.37e-04); range (n=3449, -1.25e-04); insufficient-history (n=1, 1.16e-03) | 1,472 702/289 4/18 | `2418917f843205e74287eabdb1443a0606a89641e9f4adb858fcda0952227212` |
| GBPJPY | 3,991/39.91% | -1.03e-04/24.35%/4.80e-07 | 422/-1.14e-04/False | -3.14e-04/False | -8.11e-05/-1.24e-04 | ny-am-session (n=3991, -1.03e-04); trend (n=3, 8.51e-04); normal (n=3413, -8.82e-05) | 1,433 696/275 4/28 | `1501a3ccec8b21c2a0729217a4c4f446c7cc49872b8944388c57e0037f029464` |
| AUDJPY | 4,095/41.27% | -9.48e-05/24.27%/6.92e-07 | 454/-5.76e-05/False | -2.58e-04/False | -6.36e-05/-1.26e-04 | ny-am-session (n=4095, -9.48e-05); trend (n=2, 1.38e-03); high (n=570, -8.64e-05) | 1,496 709/300 5/17 | `7d076a5ac768e382b9377727dad8c910853ffa340b42f22217182993ae1c33e9` |
| US30 | 3,842/43.86% | -1.35e-04/27.43%/1.93e-06 | 402/9.57e-07/False | -1.99e-04/False | -1.91e-04/-7.87e-05 | ny-am-session (n=3842, -1.35e-04); range (n=3480, -1.26e-04); low (n=43, -3.29e-05) | 1,490 677/296 5/27 | `c6a0f8c2c12d68d8260b9af44b8c301e8cc26ed5eb5cea766d0ef2cb68675fb8` |

### VT-08 — INSUFFICIENT_EVIDENCE / SPECIALIST_CANDIDATE

**Comportamiento central y alcance.** H4 AMD + bias estructural + FVG M5 es muy selectivo: positivo IS en 6/11, pero sólo 252 episodios Story y todos los mercados <100.

**Contraejemplos.** USDCAD, SP500, GBPJPY y AUDJPY son negativos; AUDJPY es el peor. XAUUSD lidera con sólo 16 fills y OOS n=0.

**Dirección y sesión.** La ventaja aparente depende de instrumento/dirección; no hay dirección universal. H4 structural es parte de la metodología, no una sesión comparable. LONG supera SHORT en 6/11 mercados; SHORT en 5/11.

**Regímenes y tiempo.** La muestra no potencia una tesis estable por régimen; los buckets favorables son hipótesis exploratorias.

**OOS/Stress.** OOS PASS: GBPUSD, NAS100, US30; Stress PASS: ninguno.

**Ganadores, pérdidas y lifecycle.** Sólo 23 direct-stops y 4 givebacks: la separación existe, pero ambas familias están underpowered. Direct-stop=23 (MFE medio 0.024R); giveback=4 (2.095R).

**Streaks.** Winning streak 16 y losing 6 pueden ser varianza en una muestra minúscula, no cambio probado de régimen.

**Preservar / riesgo de degradación.** Preservar contexto H4, manipulación, FVG y baja frecuencia; relajar filtros para aumentar n puede eliminar su fortaleza plausible.

**Mecanismo propuesto.** Target estructural variable y selectividad pueden producir payoff condicionado, pero tamaño muestral explica igualmente el resultado.

**Falsificador.** Muestra fresca suficiente por mercado/dirección, expectancy estable y Stress PASS repetido; colapso al crecer n falsifica especialización.

**Evidencia faltante.** Más operaciones, OOS no vacío por mercado y Stress con potencia.

**Confianza.** Media para especialización; baja para edge robusto. Mejor/peor: XAUUSD (0.00099844) / AUDJPY (-0.00032169).

| Mercado | fills/fill% | mean/WR/var | OOS n/mean/P | Stress/P | L/S mean | mejor sesión; trend; vol | Story direct/giveback W/L | digest |
|---|---:|---:|---:|---:|---:|---|---:|---|
| EURUSD | 138/38.33% | 7.16e-06/71.74%/4.34e-07 | 3/1.79e-04/False | -2.07e-05/False | -3.30e-05/7.57e-05 | h4-structural (n=138, 7.16e-06); trend (n=2, 4.16e-04); normal (n=86, 1.10e-04) | 36 3/1 16/5 | `18d0866736bfafaa974f01332129ceeb99aaa71ebdd6944571f2006bbc8b980c` |
| GBPUSD | 60/27.65% | 7.04e-05/65.00%/1.82e-07 | 4/1.30e-04/True | -6.99e-05/False | 1.50e-04/-6.77e-05 | h4-structural (n=60, 7.04e-05); trend (n=4, 3.76e-04); normal (n=30, 1.80e-04) | 14 5/0 6/4 | `a8a00095af2953942e226277be2d6c7481e5d34380a4f56b858a7bdb1589f10a` |
| USDJPY | 33/41.25% | -1.77e-05/72.73%/2.55e-07 | 3/2.48e-04/False | 4.79e-05/False | 2.26e-04/-1.09e-04 | h4-structural (n=33, -1.77e-05); insufficient-history (n=9, 3.40e-04); insufficient-history (n=9, 3.40e-04) | 10 0/0 6/1 | `a15841a7760375075be5e292aad35379333f61f6fc05317fd822977120b88c11` |
| AUDUSD | 26/28.26% | 2.07e-04/84.62%/7.18e-07 | 7/-1.26e-04/False | -3.26e-04/False | 5.75e-04/1.19e-04 | h4-structural (n=26, 2.07e-04); mixed (n=13, 6.13e-04); high (n=9, 5.02e-04) | 8 1/0 5/2 | `3416f587844abf4fdd6fc1c07c10902cb31b3ac8ae8ab0957c26bcf265884934` |
| USDCAD | 72/28.80% | -2.29e-04/48.61%/3.42e-07 | 4/-2.25e-04/False | -4.25e-04/False | 2.39e-04/-4.78e-04 | h4-structural (n=72, -2.29e-04); trend (n=1, 1.70e-04); high (n=15, 2.11e-04) | 15 2/0 4/2 | `68f83d7558696cb51664177b20ffcd68d3c50ded201e170d769bdadd21c0f378` |
| XAUUSD | 16/23.53% | 9.98e-04/81.25%/1.25e-06 | 0/0.00e+00/False | 0.00e+00/False | 4.76e-04/1.24e-03 | h4-structural (n=16, 9.98e-04); mixed (n=3, 2.61e-03); insufficient-history (n=10, 1.44e-03) | 5 0/0 4/1 | `7c8e8d73c278d8d633c1d54146253e2a90418cb7e99019e199d3144f1531d725` |
| NAS100 | 239/47.23% | 4.71e-04/84.10%/7.82e-07 | 14/7.30e-05/True | -1.27e-04/False | 2.33e-04/6.03e-04 | h4-structural (n=239, 4.71e-04); trend (n=1, 2.69e-03); low (n=28, 5.27e-04) | 53 7/0 14/4 | `b7e6ea1baea9201d04d585457dbd768f70943b3d03e8185333d8111532afb361` |
| SP500 | 150/36.59% | -7.46e-05/64.67%/3.95e-06 | 9/2.84e-05/False | -1.72e-04/False | -5.09e-05/-9.04e-05 | h4-structural (n=150, -7.46e-05); trend (n=3, 5.80e-04); high (n=26, 7.47e-04) | 39 1/3 9/6 | `8de29dd86e8986cd33d81db4786e93dd39e68128399147a0ac67ff49d9770122` |
| GBPJPY | 41/22.65% | -7.61e-05/63.41%/5.99e-07 | 0/0.00e+00/False | 0.00e+00/False | -1.79e-04/1.45e-04 | h4-structural (n=41, -7.61e-05); range (n=30, 1.85e-04); low (n=15, 2.94e-04) | 11 2/0 3/3 | `d4cc9816caa7ff5e9844445c9c51376e7b8adbaf0a5a7cdc003658fcd18123d8` |
| AUDJPY | 24/32.00% | -3.22e-04/62.50%/1.32e-06 | 0/0.00e+00/False | 0.00e+00/False | 5.42e-04/-1.76e-03 | h4-structural (n=24, -3.22e-04); mixed (n=4, 5.56e-05); normal (n=13, -2.72e-04) | 3 1/0 2/1 | `259e2e88b936947f28a0935733871eae3075c824964193a470386f64da0f2abd` |
| US30 | 248/46.18% | 1.33e-04/68.95%/2.17e-06 | 28/6.08e-05/True | -1.39e-04/False | -2.52e-04/4.20e-04 | h4-structural (n=248, 1.33e-04); insufficient-history (n=2, 4.54e-04); insufficient-history (n=4, 4.54e-04) | 58 1/0 12/2 | `e6721c982f983d21c491f0b6914d094786a789cfbf64862bb8dcdad6fccbdaa3` |

### VT-09 — STRUCTURAL_WEAKNESS

**Comportamiento central y alcance.** Turtle Soup M15 continuo tiene fill ~96.6% y gran potencia, pero expectancy negativa 11/11, OOS 0/11 y Stress 0/11.

**Contraejemplos.** EURUSD es el menos negativo y NAS100 el peor; no hay mercado favorable que contradiga la debilidad.

**Dirección y sesión.** LONG/SHORT alterna por mercado; ningún lado rescata la tesis global. Continuous impide inferir efecto de otra sesión. LONG supera SHORT en 6/11 mercados; SHORT en 5/11.

**Regímenes y tiempo.** Ningún filtro trend/vol/hour/weekday es estable en los once; escogerlo ahora sería leakage de investigación.

**OOS/Stress.** OOS PASS: ninguno; Stress PASS: ninguno.

**Ganadores, pérdidas y lifecycle.** Direct-stops masivos y givebacks de MFE alto coexisten; entrada demasiado permisiva y lifecycle son fallas distintas. Direct-stop=48,859 (MFE medio 0.010R); giveback=22,697 (7.382R).

**Streaks.** Losing máximo 35 vs winning 8; secuencias extensas con gran n sostienen debilidad, no causalidad temporal.

**Preservar / riesgo de degradación.** Preservar falso-break Turtle Soup y ganadores canónicos; fill alto es fortaleza operativa, no edge.

**Mecanismo propuesto.** Selección de falsos breaks demasiado permisiva para 2R; win rate ~23–25% no cubre stops/costes.

**Falsificador.** Filtro decision-time pre-registrado que sobreviva holdout fresco y Stress sin elegir régimen/hora ex post.

**Evidencia faltante.** Resolución intrabar y validación prospectiva de filtros.

**Confianza.** Alta para debilidad histórica. Mejor/peor: EURUSD (-0.00001128) / NAS100 (-0.00006137).

| Mercado | fills/fill% | mean/WR/var | OOS n/mean/P | Stress/P | L/S mean | mejor sesión; trend; vol | Story direct/giveback W/L | digest |
|---|---:|---:|---:|---:|---:|---|---:|---|
| EURUSD | 20,697/96.68% | -1.13e-05/24.84%/2.22e-07 | 2947/-1.34e-05/False | -2.13e-04/False | -1.89e-05/-3.29e-06 | continuous (n=20697, -1.13e-05); trend (n=136, 5.64e-06); insufficient-history (n=1518, 1.02e-05) | 9,733 4739/2188 6/24 | `65f5f0629d1699ede6decbc40385da300c3a57652eceef2b594ddfd1d8c46a22` |
| GBPUSD | 21,592/96.78% | -1.87e-05/24.43%/2.31e-07 | 2995/-1.76e-05/False | -2.18e-04/False | -2.09e-05/-1.63e-05 | continuous (n=21592, -1.87e-05); mixed (n=3290, -1.60e-05); insufficient-history (n=1391, 6.13e-06) | 9,966 4923/2248 6/23 | `48bec811c32de8fbbcda49e89a575f769be668e44daaf2ad6ba3eb5dbdfac577` |
| USDJPY | 20,605/96.35% | -1.93e-05/24.84%/3.76e-07 | 2892/-2.16e-05/False | -2.22e-04/False | -1.48e-05/-2.40e-05 | continuous (n=20605, -1.93e-05); insufficient-history (n=247, 2.23e-05); insufficient-history (n=1442, 3.79e-06) | 9,392 4535/2169 7/28 | `0f6f6cfc0688d9fc30c0859bcd9d10f013895fadb17c2eaa027bf10c254feb21` |
| AUDUSD | 21,356/96.53% | -3.13e-05/24.15%/4.11e-07 | 3023/-2.00e-05/False | -2.20e-04/False | -3.51e-05/-2.72e-05 | continuous (n=21356, -3.13e-05); insufficient-history (n=269, -1.46e-05); insufficient-history (n=1501, -1.91e-05) | 9,859 4813/2320 7/32 | `a89e03e0539e3f4db0626a349d6f7304e1b0fb9ad5ae048f6f5712badeb6d892` |
| USDCAD | 21,409/96.48% | -1.64e-05/24.61%/1.34e-07 | 3008/-1.21e-05/False | -2.12e-04/False | -1.27e-05/-2.00e-05 | continuous (n=21409, -1.64e-05); mixed (n=3036, -1.49e-05); low (n=4248, -1.14e-05) | 9,928 4828/2258 8/28 | `76a2ab4101a1b617abccb72e1db3811f4ae19623cb0126a65aae3b02cb0b87bd` |
| XAUUSD | 16,314/96.41% | -5.16e-05/24.95%/1.96e-06 | 2366/-4.79e-05/False | -2.48e-04/False | -5.64e-05/-4.68e-05 | continuous (n=16314, -5.16e-05); insufficient-history (n=1059, -3.20e-05); low (n=1346, -8.80e-06) | 7,801 3747/1762 6/29 | `e63a0bc1479aa4c89cb238f40008bdcc24a73886ee8ba27a0a95aa96640396cf` |
| NAS100 | 16,131/96.55% | -6.14e-05/24.52%/2.30e-06 | 2331/-5.23e-05/False | -2.52e-04/False | -5.78e-05/-6.50e-05 | continuous (n=16131, -6.14e-05); insufficient-history (n=962, -3.10e-05); low (n=258, -2.91e-06) | 7,798 3802/1732 5/31 | `aec6b9dd9646e2fa3d3dc8afebcacbd81886cc8e84bd37c83b64a2d2321e5813` |
| SP500 | 14,829/96.45% | -5.11e-05/23.79%/1.48e-06 | 2288/-1.11e-05/False | -2.11e-04/False | -3.82e-05/-6.36e-05 | continuous (n=14829, -5.11e-05); insufficient-history (n=845, -2.77e-05); high (n=3928, -3.54e-05) | 7,410 3662/1659 6/23 | `3855eda2c08ca4911d2d101c890d7a2de93cf9c0fc8584c37e8ac2580558d6fc` |
| GBPJPY | 22,879/96.85% | -3.14e-05/23.23%/3.54e-07 | 3084/-3.67e-05/False | -2.37e-04/False | -2.88e-05/-3.40e-05 | continuous (n=22879, -3.14e-05); mixed (n=3471, -2.11e-05); high (n=2134, -1.61e-05) | 10,176 5087/2345 5/23 | `100de5f06b3c0144094a51d51cc1b1096be3726184fbeaa293d89fddbf200dfa` |
| AUDJPY | 22,050/96.80% | -3.27e-05/23.37%/5.42e-07 | 2969/-4.66e-05/False | -2.47e-04/False | -3.86e-05/-2.68e-05 | continuous (n=22050, -3.27e-05); insufficient-history (n=195, 2.76e-05); insufficient-history (n=1319, -1.09e-05) | 10,028 5030/2311 5/31 | `3d07c9a867ecb3d089944331629ada3694517878e18040e4eedb209e0e951dc4` |
| US30 | 15,532/96.22% | -3.19e-05/24.94%/1.24e-06 | 2306/-5.45e-05/False | -2.54e-04/False | -1.10e-05/-5.26e-05 | continuous (n=15532, -3.19e-05); mixed (n=2137, 3.17e-07); high (n=4158, -3.43e-06) | 7,599 3693/1705 6/35 | `23170429731cae55af39e175affdda3980057efc707a952743bce4b3f9f40ed4` |

### VT-17 — STRUCTURAL_WEAKNESS

**Comportamiento central y alcance.** Sweep del ciclo 90 minutos NY M5 llena ~96%, pero sólo USDJPY es marginalmente positivo IS y también falla OOS.

**Contraejemplos.** US30 es el peor; diez mercados negativos. OOS levemente positivos aislados no pasan gate y Stress es 0/11.

**Dirección y sesión.** Asimetrías LONG/SHORT no son invariantes. NY es parte congelada del método. LONG supera SHORT en 6/11 mercados; SHORT en 5/11.

**Regímenes y tiempo.** Buckets favorables rotan por mercado; no hay régimen generalizable observable.

**OOS/Stress.** OOS PASS: ninguno; Stress PASS: ninguno.

**Ganadores, pérdidas y lifecycle.** Direct-stops dominan; givebacks con MFE grande prueban una segunda familia de lifecycle. Direct-stop=15,647 (MFE medio 0.011R); giveback=7,420 (6.669R).

**Streaks.** Losing máximo 37 vs winning 7, consistente con baja discriminación de entrada.

**Preservar / riesgo de degradación.** Preservar ciclo y NY; no convertir la anomalía USDJPY ya consumida en autorización especialista.

**Mecanismo propuesto.** La construcción de ciclos genera entradas rápidas abundantes con poca discriminación de edge.

**Falsificador.** Holdout fresco que confirme un cluster con OOS+Stress PASS manteniendo config y metodología.

**Evidencia faltante.** Holdout prospectivo y datos intrabar.

**Confianza.** Alta para ausencia de robustez; media para mecanismo. Mejor/peor: USDJPY (0.00000155) / US30 (-0.00004357).

| Mercado | fills/fill% | mean/WR/var | OOS n/mean/P | Stress/P | L/S mean | mejor sesión; trend; vol | Story direct/giveback W/L | digest |
|---|---:|---:|---:|---:|---:|---|---:|---|
| EURUSD | 3,787/95.85% | -1.11e-05/26.14%/1.86e-07 | 868/5.36e-06/False | -1.95e-04/False | -1.69e-05/-5.04e-06 | ny-am-session (n=3787, -1.11e-05); insufficient-history (n=134, 2.23e-05); insufficient-history (n=173, 7.91e-06) | 2,877 1356/641 6/19 | `b8b98f60a8110954ae6142e20feecc0cbbfe9195ee20dd3ea9a89fd14a48b423` |
| GBPUSD | 3,907/96.26% | -2.12e-05/25.44%/1.64e-07 | 863/-1.46e-05/False | -2.15e-04/False | -2.72e-05/-1.49e-05 | ny-am-session (n=3907, -2.12e-05); range (n=2588, -1.91e-05); insufficient-history (n=19, 6.26e-05) | 2,978 1432/654 6/23 | `c64e1ece4bc3d7cbfde0b7b64e5bdc6cb696078615db5908075b0068137968fa` |
| USDJPY | 3,813/95.73% | 1.55e-06/26.28%/2.89e-07 | 825/-2.01e-06/False | -2.02e-04/False | 1.09e-05/-6.72e-06 | ny-am-session (n=3813, 1.55e-06); insufficient-history (n=133, 1.37e-04); insufficient-history (n=174, 1.43e-04) | 2,940 1381/649 6/25 | `81b70c5d3a4d4a90ce42423c314281bc57e8757e347a0f776881ebea89218071` |
| AUDUSD | 3,815/96.14% | -1.73e-05/25.77%/2.28e-07 | 818/-1.26e-05/False | -2.13e-04/False | -3.15e-05/-2.63e-06 | ny-am-session (n=3815, -1.73e-05); mixed (n=1080, 2.52e-05); low (n=88, 2.29e-06) | 2,937 1421/631 7/24 | `8e6073ace5ac00ab5d2a46ce1c781271eb21b134ffdde56367469994e6a0897e` |
| USDCAD | 3,924/96.01% | -5.94e-06/25.74%/1.04e-07 | 914/4.35e-06/False | -1.96e-04/False | -7.62e-06/-4.53e-06 | ny-am-session (n=3924, -5.94e-06); insufficient-history (n=1, 5.73e-05); normal (n=2631, -3.83e-06) | 3,006 1455/656 6/21 | `6854af2abea8252364653e8c5456d07ed28af7185f136d664a549afe9b73cb89` |
| XAUUSD | 4,195/96.35% | -6.56e-06/26.15%/1.44e-06 | 911/6.65e-05/False | -1.34e-04/False | -2.28e-05/8.47e-06 | ny-am-session (n=4195, -6.56e-06); mixed (n=1221, 1.94e-06); low (n=54, 6.37e-05) | 3,117 1472/672 4/18 | `e7cfd95eddb30c771beb91f1f6d78d3f2144197171c1126bfbc506a778f185f7` |
| NAS100 | 4,100/96.86% | -1.89e-05/25.34%/1.56e-06 | 905/-2.13e-05/False | -2.21e-04/False | 8.04e-06/-4.39e-05 | ny-am-session (n=4100, -1.89e-05); insufficient-history (n=5, 8.96e-05); insufficient-history (n=13, 9.72e-05) | 3,056 1443/712 5/20 | `015bfb7d0b1ab80de413175bde78a4190a70de3aea85661989efe98439835360` |
| SP500 | 3,587/96.58% | -3.16e-05/24.95%/7.91e-07 | 849/-6.77e-05/False | -2.68e-04/False | -9.39e-06/-5.28e-05 | ny-am-session (n=3587, -3.16e-05); insufficient-history (n=6, 8.06e-05); insufficient-history (n=12, 3.93e-04) | 2,810 1348/666 4/24 | `805af6cb81977b7f7e45712ad00d3c191173dd94cdd067d1bdea96b25f751b9a` |
| GBPJPY | 4,253/96.84% | -2.46e-05/24.81%/2.21e-07 | 964/-4.13e-05/False | -2.41e-04/False | -7.60e-06/-3.89e-05 | ny-am-session (n=4253, -2.46e-05); trend (n=166, -7.66e-06); insufficient-history (n=9, -6.67e-06) | 3,174 1539/727 7/27 | `9717705aff97490fd796ece6e56016c03d5928f771a6a9dc60095cc29834249a` |
| AUDJPY | 4,229/96.80% | -2.40e-05/25.02%/2.84e-07 | 909/-1.99e-05/False | -2.20e-04/False | -1.22e-05/-3.46e-05 | ny-am-session (n=4229, -2.40e-05); mixed (n=1204, -1.22e-05); insufficient-history (n=14, 8.51e-05) | 3,128 1524/711 4/23 | `f0f3301e05603a8096051b531b0bd9f55cb2671c9517594ff8e1b14116f75759` |
| US30 | 3,623/95.24% | -4.36e-05/24.26%/7.13e-07 | 834/-5.67e-05/False | -2.57e-04/False | -2.02e-05/-6.58e-05 | ny-am-session (n=3623, -4.36e-05); insufficient-history (n=8, 3.27e-04); insufficient-history (n=21, 1.59e-04) | 2,775 1276/701 5/37 | `f5cf68b35b9de172cdf46a1d80ff38b8ac7fdec5584cefdde8990b9e50f35d74` |

### VT-31 — STRUCTURAL_WEAKNESS

**Comportamiento central y alcance.** Silver Bullet mantiene selectividad (~36.8% fill) y 2R, pero expectancy negativa 11/11, OOS 0/11 y Stress 0/11.

**Contraejemplos.** USDJPY/USDCAD son menos negativos; US30/NAS100/SP500 contradicen especialización favorable en índices.

**Dirección y sesión.** LONG/SHORT cambia de signo por instrumento; no hay lado universal. La ventana es metodología, no comparación causal de sesiones. LONG supera SHORT en 6/11 mercados; SHORT en 5/11.

**Regímenes y tiempo.** No existe régimen trend/vol/hour estable entre mercados.

**OOS/Stress.** OOS PASS: ninguno; Stress PASS: ninguno.

**Ganadores, pérdidas y lifecycle.** Stops directos superan ampliamente givebacks; trailing sólo atacaría una minoría distinta. Direct-stop=3,513 (MFE medio 0.025R); giveback=1,398 (3.593R).

**Streaks.** Losing máximo 29 vs winning 6; clustering descriptivo compatible con debilidad y varianza.

**Preservar / riesgo de degradación.** Preservar ventana Silver Bullet y geometría; ampliar horario/mercados por P&L retrospectivo degradaría selectividad.

**Mecanismo propuesto.** La ventana filtra frecuencia, pero sweep+FVG aún admite demasiados stops directos.

**Falsificador.** Cambio decision-time pre-registrado, holdout nuevo multi-mercado positivo y Stress PASS.

**Evidencia faltante.** Resolución intrabar y holdout fresco.

**Confianza.** Alta para debilidad histórica. Mejor/peor: USDJPY (-0.00000716) / US30 (-0.00015176).

| Mercado | fills/fill% | mean/WR/var | OOS n/mean/P | Stress/P | L/S mean | mejor sesión; trend; vol | Story direct/giveback W/L | digest |
|---|---:|---:|---:|---:|---:|---|---:|---|
| EURUSD | 1,495/36.46% | -4.16e-05/27.09%/3.89e-07 | 216/-2.80e-05/False | -2.28e-04/False | -7.13e-05/-1.11e-05 | ny-silver-bullet (n=1495, -4.16e-05); range (n=1347, -3.47e-05); high (n=177, -2.04e-05) | 713 342/110 3/13 | `343bcbe1d23247d0caaf8f729e6e088fd296226c748ddfbde5f820f9c3249bfe` |
| GBPUSD | 1,534/36.53% | -2.70e-05/28.23%/3.96e-07 | 225/-5.70e-05/False | -2.57e-04/False | -5.76e-05/8.13e-06 | ny-silver-bullet (n=1534, -2.70e-05); range (n=1371, -1.70e-05); high (n=143, 2.22e-04) | 713 311/145 5/29 | `417e11c4e31aad8849bb5293af7b3a7e54b2c73eee11809051d11580ad81c269` |
| USDJPY | 1,454/35.97% | -7.16e-06/29.99%/4.83e-07 | 216/-4.47e-05/False | -2.45e-04/False | 9.74e-06/-2.30e-05 | ny-silver-bullet (n=1454, -7.16e-06); trend (n=1, 4.14e-04); insufficient-history (n=23, 2.28e-05) | 665 296/123 4/16 | `e95a1d89445e91bd97aae99ff0a3a37560d8f3b3e1d0ff2aed6fcb4db209f047` |
| AUDUSD | 1,491/38.93% | -9.39e-05/25.15%/6.89e-07 | 220/-1.02e-04/False | -3.02e-04/False | -1.35e-04/-4.75e-05 | ny-silver-bullet (n=1491, -9.39e-05); insufficient-history (n=10, 6.24e-05); insufficient-history (n=15, 1.01e-04) | 701 321/133 6/17 | `b5a13148f1238f4d593b8809d6d4272da1f0a6a3caad581cf612a74583bd9264` |
| USDCAD | 1,511/38.60% | -2.01e-05/28.26%/2.54e-07 | 224/-1.94e-05/False | -2.19e-04/False | -4.29e-06/-3.46e-05 | ny-silver-bullet (n=1511, -2.01e-05); trend (n=5, 4.93e-04); normal (n=858, -6.56e-06) | 692 299/138 6/14 | `368a74fb4fb6a610a7daf522d2313b3df251ae83fc6de9872931f2aa72fc9b75` |
| XAUUSD | 1,486/33.39% | -8.06e-05/30.15%/2.56e-06 | 184/-3.61e-04/False | -5.61e-04/False | -1.58e-04/4.00e-06 | ny-silver-bullet (n=1486, -8.06e-05); mixed (n=147, 6.86e-05); high (n=302, -6.73e-06) | 645 289/113 4/15 | `33e06ac0f40970c2a9d425d7476073bd85c8fbaf8fa0020d884bc7cf052b21cb` |
| NAS100 | 1,567/37.90% | -1.33e-04/27.89%/4.11e-06 | 213/-2.50e-04/False | -4.50e-04/False | -3.50e-05/-2.42e-04 | ny-silver-bullet (n=1567, -1.33e-04); mixed (n=103, -4.19e-05); normal (n=537, -5.46e-05) | 704 321/141 5/23 | `eeeb8a34ba3ce27211e24089c6f9092c7476967bd694ef11ea33f73bb5127af8` |
| SP500 | 1,430/36.48% | -9.91e-05/27.20%/2.64e-06 | 197/-1.05e-04/False | -3.05e-04/False | -3.41e-05/-1.65e-04 | ny-silver-bullet (n=1430, -9.91e-05); trend (n=4, 1.54e-04); normal (n=527, -6.91e-06) | 648 286/126 4/16 | `bc7e4e8370c7d8f882f4a78e71028f547b51cc87d1d77a6da086fc6ba1da1e02` |
| GBPJPY | 1,737/36.99% | -8.74e-05/25.16%/4.00e-07 | 226/-3.37e-05/False | -2.34e-04/False | -3.71e-05/-1.36e-04 | ny-silver-bullet (n=1737, -8.74e-05); trend (n=3, 2.78e-05); low (n=438, -2.43e-05) | 764 360/133 4/29 | `74ad08b9c3313b859778cb5923e724e5269e61d5cfb244355b8bd5ed60ff9ed2` |
| AUDJPY | 1,626/37.44% | -7.74e-05/24.23%/6.63e-07 | 238/-6.45e-05/False | -2.64e-04/False | -4.48e-05/-1.10e-04 | ny-silver-bullet (n=1626, -7.74e-05); range (n=1495, -7.24e-05); high (n=264, -5.31e-05) | 726 372/125 3/20 | `def9596f6c2914c3ddf700ec26dc49699b375a184ffefaf0fb0b25e2be7a62ce` |
| US30 | 1,487/36.03% | -1.52e-04/27.77%/2.48e-06 | 179/-1.76e-04/False | -3.76e-04/False | -2.14e-04/-8.50e-05 | ny-silver-bullet (n=1487, -1.52e-04); range (n=1362, -1.41e-04); low (n=221, -4.31e-05) | 639 316/111 4/19 | `7e8e9b6332786ab4bf334672528d1ebd6798dd88aaa6fe2ca835917b50cbcb6b` |

## Decision-time, oracle, cronología y visualización

En 155,904 episodios Story se observaron 0 oracle leaks en `decision_time` y 0 secuencias de frames no monotónicas. MFE/MAE/exit/return se usan sólo post-outcome. La evidencia OHLC M5/M15 no permite inferir orden intrabar; se conserva `closed-bar-path; no intrabar ordering inferred` y stop-first conservador. TradingView Lightweight Charts sólo renderiza evidencia QORE y no completa velas.

## Falsificación adversarial

Controles ejecutables cubren: permutación de mercados invariante; missing/duplicate; mercado sustituto; config/metodología/timeframe; source digest cross-market; Story payload y Characterization; oracle injection; frames desordenados/duplicados/desconocidos/ISO-unix incoherente; review lane/Human antes de cuatro machines y digest de mercado ajeno. Los controles benignos demuestran aceptación del paquete válido y aliases certificados.

## LSP semántico

Pyright language server real: hover, go-to-definition, find-references e incoming call hierarchy sobre backtest, Characterization, walk-forward, failure, hypothesis, Story, market Story, thesis evidence, ambos dossiers, thesis panel, session replay/intelligence, market board, review panel, Lightweight renderer, filmstrip y visual package. Characterization consume market+WF; Story liga market+backtest+Characterization; thesis conserva production-default y liga WF/failure; dossier exige 11×5; panel profundo no consume shallow.

## Limitaciones y holdout

- Los Story streaks pertenecen a la intersección trades↔setups production-default, no a todos los setups.
- VT-08 está underpowered; OOS PASS con n=4, 14 y 28 no es robustez.
- Sin tick/segundos/M1 no se resuelve intrabar; no se inventó cronología.
- Todo OOS observado quedó consumido. Cualquier cambio exige OBSERVE→DIAGNOSE→HYPOTHESIZE→PRE-REGISTER→MODIFY→FRESH HOLDOUT→FALSIFY→STRESS→AUTHORITY.
- Evidencia observacional histórica no identifica causalidad ni concede autoridad.

## Estado GitHub y QG

Issue #505 OPEN; PR #500 permanece DRAFT y no fue modificado; PR #506 permanece DRAFT; PR #507 es carrier CI y no fue mergeado. El candidato está en branch independiente `work/qore-trader-story-forensics-independent-001`.

Quality Gate completo ejecutado sobre el candidato sellado: `ruff check .` PASS; `mypy src tests` PASS (`978 source files`); `pytest --cov=src/qore --cov-report=term-missing` PASS (`7234 passed`, `8 warnings`, cobertura `83%`). Tras incorporar este registro documental se repitió el mismo gate sobre el HEAD final; el HEAD y TREE exactos se consignan en la entrega de adjudicación.

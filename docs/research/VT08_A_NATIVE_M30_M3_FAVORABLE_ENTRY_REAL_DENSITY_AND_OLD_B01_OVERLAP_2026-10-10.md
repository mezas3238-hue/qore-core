# QORE CORE VT08 — RECUPERACIÓN M3 REAL: FRACTAL 30M→3M, ENTRADA FAVORABLE Y NET DENSITY

**Fecha de investigación 2026-10-10 NY / cierre CI 2026-10-11 UTC.** Owner RECHAZÓ densidad insuficiente VT08: este informe **NO afirma levantar rechazo de certificación**, pero identifica rama legítima TTrades + cuantifica mejora estructural de volumen. Arquitecto A / PR #765, issues #762 / #763 / parent #634. Solo GitHub, no VPS, no cuenta/live, no 7Y holdout.

## 1. FUENTE TTRADES A: M3 realmente autorizado para 30M

TTrades public:
- [Time Frame Alignment — TTrades](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) sección **"Time Frame Pairings"**: Weekly→4H, Daily→1H, **4H→15M**, **1H→5M**, **30M→3M**, 15M→1M. Su Example 1 muestra 30M bullish reversal + CISD 3M y continuación/positional entry.
- [Fractal Model Indicator Full Guide](https://ttrades.com/ttrades-fractal-model-indicator-full-guide/), sección **"Template: 3 Minute"**: Daily+4H context y **3M–30M fractal**; overlay 15M–4H. Por ello M3 **NO** significa reemplazar 15M por 3M sin más sobre H4.
- [A Simple 3-Step Trading Model](https://ttrades.com/a-simple-3-step-trading-model-full-breakdown/): daily/HTF context, 7h profiles, H1/5M y 30M/3M alineados, intra-candle CISD.
- [Positional Entries](https://ttrades.com/positional-entries-enter-before-the-expansion/) 2026-08-08: al OPEN siguiente HTF si modelo + swing + PS ya confirmado, **no requiere segundo CISD en vela nueva**, stop debe proteger estructura/ EQ. Éste es método de ejecución alternativo; no genera una señal madre nueva por nombre.
- [TTrades 4H Power of Three](https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/): combinar **1H/5M o 30M/3M** con contexto 4H y daily para expansión.

**Corrección frente a DeepSeek / implementación anterior:** M3 deja de D, pero solo para **fractal 30M→3M fuente A**. No usar 4H→3M universal, y no permitir M3 sin POI, CISD, protected swing y alineación temporal/contextual.

## 2. Datos reales, no interpolados y fuente cruzada

**M3 NATIVO cTrader DEMO**, 5 FX, 1095d, run GitHub #35941643396, commit `bc1379d7661aac202495ec67afdd3098473ba723`, 5 artifacts vigentes/no expirados; `vt08_cognitive_m3_evidence_probe_v1.py` colecta nativas `period=3` de broker en modo read-only.

**M15 fuente congelada** mismo intervalo y pares, run #35934924907, commit `b2d33e1b4829d8b4afc76983decca8a99131403c`. Cada M30 estructural se reconstruyó con 10 M3 cerradas y se cruzó con 2 M15 cerradas independientes. **CERO** discrepancias OHLC en las M30 completas con doble evidencia. NO utilizar bid/ask sintético; estas velas OHLC NO prueban fills físicos.

**Prerregistro** antes de explorar resultados [VT08_A_NATIVE_M3_M30_FAVORABLE_ENTRY_PREREG_2026-10-10.md](VT08_A_NATIVE_M3_M30_FAVORABLE_ENTRY_PREREG_2026-10-10.md), SHA `e00bd98d09d6a4c94c4663822acf9073379629e3`. El análisis de solapamiento con 488 B01 es **POST-CENSO DESCRIPTIVO**, sin outcome PnL ni selección de reglas; no pretender que estuvo en el preregistro original.

**Código**:
- `src/qore/infrastructure/trader_lab/vt08_5m_a_native_m30_m3_favorable_entry_v1.py`
- `tests/infrastructure/trader_lab/test_vt08_5m_a_native_m30_m3_favorable_entry_v1.py`
- `.github/workflows/vt08-a-native-m30-m3-favorable-entry-1095d-v1.yml`
- GitHub Actions [#38104294081](https://github.com/mezas3238-hue/qore-core/actions/runs/38104294081) **SUCCESS 5/5** tests SHA `0d214b4a5973873ee0d92e2b59eb8773e2481829`. Ruff PASS, **12 pytest tests/mercado = 60 pruebas**, 5 x native M3/M15 source audits and trace artifacts.

## 3. Máquina causal de entrada favorable que se probó

**Un setup madre (M30 C1/C2) y DOS técnicas alternativas, no dos trades:**

1. **Antes de abrir C3:** C1 M30 cerrada; C2 M30 barre **un solo extremo** de C1, regresa dentro de C1 y cierra; dentro C2 se confirma serie opuesta CISD+PS por cierre **M3**. Invalidaciones as-of, no seleccionar PS si hay varios. **POI HTF fuente aún pendiente**: el actual detector con C1 high/low como boundary es sólo upper bound, no setup certified.
2. **Entrada A posicional:** en el OPEN M30 C3 usar primer **OPEN nativo M3**, stop beyond PS y objetivo liquidez del extremo opuesto C1. Computar RR geométrica `reward/risk` sobre esos niveles ya conocidos. Si geometría inválida => abstener. No usar OHLC del resto de C3 para justificar A.
3. **Entrada B precio favorable:** programar **antes de C3** un posible retesteo del nivel CISD ya confirmado en C2, siempre que esté estrictamente entre stop y precio de apertura C3 en lado que REDUCE distancia al stop. Monitorear **hasta cierre M30 C3**, evento de touch solo después de cerrar la M3 correspondiente. Si SL/TP alcanzado ANTES del touch, descartar; si mismo M3 toca limit+SL o limit+TP, `SAME_BAR_ORDER_SEQUENCE_AMBIGUOUS`. Un touch OHLC limpio **NO** es BID/ASK fill, **NO** demuestra por sí solo ejecución viable. Entrada a mitad C2 EQ no se probó: depende del contexto swing fuente validado.
4. **Un evento por NY día de mercado:** selección descriptiva del PRIMER retesteo observado al cierre M3 cronológico; desempate por `origin_id`, NO mayor RR ni ganancias ex post. Dato posterior nunca vuelve atrás a fecha apertura C3. Se registran oportunidades, NO fills.
5. **El RR 1,5:1** es un bucket diagnóstico QORE, no target/certificación TTrades. Objetivo usado = opuesto C1 high/low (liquidez conocida); hay que verificar disponibilidad/ relevancia real y costos.

## 4. RESULTADOS — 1095 días, cinco pares

| Mercado | Setups M30/M3 con PS único, stop/target geométricos | M3 CISD-level retest *clean OHLC touch* (TODOS eventos) | DÍAS con primer retest M3 (máximo 1/día) | Primer retest RR bruto ≥1,5 | Reducción MEDIANA bruta riesgo vs entrada positional |
|---|---:|---:|---:|---:|---:|
| EURJPY | 1.895 | 781 | 509 | 482 | 42,42% |
| USDCHF | 1.751 | 689 | 454 | 419 | 44,20% |
| NZDUSD | 1.794 | 689 | 461 | 432 | 44,00% |
| CADJPY | 1.790 | 695 | 465 | 439 | 45,33% |
| USDCAD | 1.752 | 688 | 470 | 440 | 44,50% |
| **TOTAL** | **8.982** | **3.542** | **2.359** | **2.212** | **42,4–45,3% por mercado** |

- Los 2.359 son **market-day slots** (un día por par), NO 2.359 trades. Pueden ser observaciones donde ninguno de los POI HTF/objetivos/targets cumple metodología, BID/ASK y/o filtro cognitivo. No interpretar este techo de fuente como expectativa de volumen autorizado.
- Para los primeros retesteos seleccionados por día, **RR geométrico bruto mediano** entre 1,43–1,69:1 si entrara posicional, frente a 3,71–3,94:1 a nivel CISD retestado. **Comparación condicionada a que RETEST ocurrió**, por lo que induce sesgo de selección de disponibilidad; NO prueba mejora neta de esperanza matemática, PF o DD.
- RR >=1,5 en **3.322** de los 3.542 touches generales, pero **2.212** tras selección máxima 1 market/day. **0 fills certificados**.
- 0 M30 OHLC cross-feed mismatch. M3 mismo intervalo que M15, no data sintetizada, no 7Y sealed.

## 5. Densidad incremental SIN DOBLE CUENTA respecto a B01 original

Para cada mercado se reconstruyó de nuevo `evaluate_expansion_at_entry_indexed` desde las M15 reales, con posterior selección cardinalidad EXACTAMENTE un candidato por NY day. Comparación **descriptiva** de la unión de días M30/M3 y B01 original, sin pretender unión de trades ejecutables.

| Mercado | B01 día seleccionable | Días M30/M3 primer touch | Días SOLAPADOS | Días M30/M3 SIN B01 | Unión de días estructurales |
|---|---:|---:|---:|---:|---:|
| EURJPY | 82 | 509 | 59 | 450 | 532 |
| USDCHF | 78 | 454 | 58 | 396 | 474 |
| NZDUSD | 114 | 461 | 67 | 394 | 508 |
| CADJPY | 86 | 465 | 52 | 413 | 499 |
| USDCAD | 98 | 470 | 58 | 412 | 510 |
| **TOTAL** | **458** | **2.359** | **294** | **2.065** | **2.523** |

**Conclusión diagnóstica:** La rama auténtica 30M→3M puede **encontrar geometrías en 2.065 market-day slots que el viejo B01 NO seleccionó**. Esto es un potencial de cobertura estructural, **no** +2.065 trades. El ratio hipotético de días estructurales unión/B01 (2523/458 ≈ 5,51×) **NO es ratio de señales validadas**, nunca presentarlo como producción real.

## 6. Seguridad/fidelidad/ambigüedades

- Todos los records M3 `source_poi_htf_confirmed=False`, `orders_authorized=False`, `cognitive_ready=False`, `bid_ask_fill_verified=False`, `pnl_evaluated=False`.
- RR basada en precio entrada OHLC sin broker spread/fees/slippage; el retoque intra M3 no provee secuencia tick, aunque bloqueamos same-bar touch+stop/target.
- Al esperar touch CISD M3, frecuencia "touched" es CONDICIONAL retrospectiva; la política ex ante debe registrar una orden limit teórica al C3 open que caduque al final de la ventana, sin usar outcome del día para elegir un setup. El "first clean" posterior es sólo respuesta de cobertura, no simulador físico.
- H4 y daily source bias aún en proceso; la prueba no admite automáticamente vieja etiqueta LONG/SHORT B01 ni añade 13NY Owner no autorizada. Owner 01/05/09 NY intactos, dentro intervalos H4 01–05,05–09,09–13 se cuentan intrasession M30.
- TTrades POI distinto de barrido mecánico de C1; es bloqueante para cognitiva y trades reales. Hay que integrar valid High/Low/FVG/OB y prioridad causal TTrades (no FVG único inventado).
- Sin implementación aquí de sizing QDLE, CIBO, riesgo de cuenta ni reportes PF/DD. Certificación requiere matching M3 bid/ask o tick histórico (no disponible en estos artefactos), comisiones, SL/TP físicos, selección ORDER state machine as-of, fuente POI y cognición 100% trazable.
- 105 C3 dual-sweep H4 anteriores siguen D, no mezclados con M30; otra familia diferente.

## 7. PRIORIDAD para siguiente arquitecto y B cognitiva

1. **P0 M3 AUTHOR SOURCE COMPLETE**: reconstruir POI HTF relevante as-of, H4/daily EQ valid swing and neutral/reversal/continuation bias, M30 fractal C1/C2 + M3 CISD exact, elegir PS estructural verdaderamente protector, registrar `poi_id`, `cisd_id`, `ps_id`, `origin_id`. No abstraer H4→M3 sin 30M.
2. **P0 PHYSICAL M3 EXECUTION**: conservar la elección de limit ex ante durante 30m, feed bid/ask y costes físicos, sin precio dentro del spread; no inferir fills solo de M3 low/high; registrar missing quotes, same-bar ambiguity, expiration, OCO y un trade/day NY.
3. **P0 A→B MANIFEST**: metadatos/valores causal source para todos los 27+ Situation features y hashes de mercado/timestamp, firmar bilateral. Hasta entonces B `APPROVED_A_B_MANIFEST_SHA256=None`, zero cognitively admitted, no aleatorizar PS.
4. **P1 ejecución A/B científica**: sobre el mismo universo M15+M3 prueba **positional open** vs **limit CISD retest** vs luego **M3 intracycle confirmation**, sólo tras fuente completa, bid/ask y POI. Objetivo mejorar PF/DD sin perder densidad; no vender hallazgos de geometría como edge.
5. **P1 certificación**: WFO/MC, evaluar trade physical density > viejo B01 458 selected days, PF/DD Sharpe Sortino costos, sellar parámetros antes de usar holdout final 7Y. **No VPS ni LIVE** hasta aprobación.

**Artefactos GitHub reproducibles del CI (cada ZIP full trace/summary; retención 30d):**
- EURJPY id `11688359687` sha256:009c1112d08252ad70a431e3b8a8058889cf1dd69c4ca195d506ee833ebeb1de
- USDCHF id `11689082918` sha256:377f630f3d1de29466e011fed62481ff59cb5616c25285dc4e4fa636f41f2ea0
- NZDUSD id `11689290212` sha256:015b057fcd79c96804a2ef42c44c65df58b9e4f5079161241f21d21db4d3775d
- CADJPY id `11688858241` sha256:8d8199e828286eadc215d75a493bb961b76c70fe05dcd4e2a23335a244d5ecd4
- USDCAD id `11688399578` sha256:4b1bdba78e471c0336021a7f5053abd367e22bce0c1a451c0fc2e3b88f8eceb1

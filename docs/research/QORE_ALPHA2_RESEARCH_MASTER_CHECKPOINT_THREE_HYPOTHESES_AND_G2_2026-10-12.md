# QORE-Alpha 2 — CHECKPOINT MAESTRO DE INVESTIGACIÓN Y GATES — 2026-10-12

**Repo:** `mezas3238-hue/qore-core`.
**Rama research exclusiva:** `research/qore-alpha2-original-intermarket-propagation-20261012`.
**PR [#840](https://github.com/mezas3238-hue/qore-core/pull/840)** permanece DRAFT/NO MAIN.
**Issues:** [#838 owner](https://github.com/mezas3238-hue/qore-core/issues/838), [#843 W2 source](https://github.com/mezas3238-hue/qore-core/issues/843), [#852 broker BIDASK/PIT](https://github.com/mezas3238-hue/qore-core/issues/852).

## Visión y objetivo

Trader cuantitativo **QORE-Alpha 2**, metodología diseñada aquí por hipótesis y evidencia, sin copiar modelos de los otros Traders ni prometer rentabilidad sin medir. La meta requiere demostración de beneficio NET replicable y Gates UTC-001 por año/fold. A día de este informe: **0 traders Alpha2 certificados, 0 señales autorizadas para PAPER/LIVE, 0 órdenes.** VPS, MT5, Shared, CIBO, QDLE y producción totalmente intactos. La computación ocurre en GitHub Trader Lab, procesamiento paralelo por 33 y motor vectorizado W1; el `trader_lab.fast_forward.py` original es un certificador de cronología, no confundirse con un ejecutor económico de órdenes.

## Los 33 mercados y artefactos fuente

Fuente original G0 33 SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. 3 índices, 2 metales, 7 pares mayores, 21 cruces. Cohortes 12 Atlas `run 35166210458` y 21 IC Markets `run 38193802541`, manifiesto firmado `run 38207337960`; origen RAW+QUALITY SHA para once particiones anuales antes de acceder a OHLC. Identidad entre cuentas broker de ambas cohortes todavía no probada. Los artefactos fuente alojados en Actions tienen retención/fecha de expiración: los originales Atlas observados hacia 2026-12-16 y ICMarkets hacia 2027-01-10; verificar de nuevo y archivar legalmente/reproducir testigos antes de expirar.

- **G0/W2 Source all33 [#38273144621](https://github.com/mezas3238-hue/qore-core/actions/runs/38273144621):** SUCCESS 35/35; **19.496.136/19.496.136** barras pre-embargo contienen entero positivo en campo `volume`. En el protocolo cTrader `ProtoOATrendbar.volume` está definido como *bar volume in ticks*, NO negociación ejecutada buy/sell: https://help.ctrader.com/open-api/model-messages/#protooatrendbar . Procedencia byte-a-byte del campo productor->RAW individual por auditar, identidad de cuenta por verificar.
- **Corte común:** desarrollo [2016-09-17,2022-09-17) UTC, diagnóstico temporal [2022-09-17,2024-09-17) UTC, **EMBARGO desde 2024-09-17** OHLC para el programa. Estos períodos NO constituyen OOS virgen debido a experimentos previos en QORE.

## W1 — PATR, transmisión asincrónica entre mercados, CERRADO

- PREREG `docs/research/QORE_ALPHA2_ORIGINAL_PATR_METHOD_AND_UTC001_PREREG_2026-10-12.md`.
- **Trader Lab 33 [#38268654596](https://github.com/mezas3238-hue/qore-core/actions/runs/38268654596):** 224 señales, 33/33 originales SHA con H4 completas; SIMD/incremental `O(T*N²)` y paridad con motor lento synthetic.
- GROSS `[#38270999595](https://github.com/mezas3238-hue/qore-core/actions/runs/38270999595)`: 176 pareadas (130 DEV, 46 DIAG), medias −0,16743bps y −3,42366bps; diferencia contra control −0,72876bps y 0,00000bps. Insuficiencia muestral; delta control algebraicamente no-discriminativo en mayoría de retornos no cero. 48 censuras trayectoria M5; [auditoría source-only #38272270791](https://github.com/mezas3238-hue/qore-core/actions/runs/38272270791). Estado `UNDERPOWERED_NO_SUPPORT`, NO net. No retunar PATR.

## W2 — PADE, tick-activity vs desplazamiento horario, CERRADO

- Prereg pre-outcome `docs/research/QORE_ALPHA2_W2_PADE_FIRST_ECONOMIC_PREREG_2026-10-12.md`, HEAD ancestral `43688569fa8d9c5ba93a127ff6ae66f9091aeede`.
- GROSS 33 [#38283326547](https://github.com/mezas3238-hue/qore-core/actions/runs/38283326547) SUCCESS 35/35: 265 señales, 265 pares, 134 direcciones de estrategia vs control diferentes. DEV n220 bruto −1,79805bps, delta −4,55863bps; DIAG n45 bruto +3,39427bps, delta −1,97277bps; Gate de potencia diagnóstico NO pasa. [Auditoría posthoc #38283910730](https://github.com/mezas3238-hue/qore-core/actions/runs/38283910730) muestra 6 activos 0 señal (3 índices, 2 metales y 1 adicional), y ausencia de 20 H1 continuas 204.203 casos; 0 índices/metales con trade, no interpretarlo como un fallo económico de su universo. IC95 semanal 4wk de delta DEV [−13,576;+1,641]bps y DIAG [−8,154;+2,487]bps, ambos cruzan cero. No retunar ratios de volumen, horarios, stops ni filtros después del resultado. Estado `UNDERPOWERED_NO_SUPPORT`.

## W3 — CMTRL, Bayesian online morphology, TERCERA Y ÚLTIMA exploración, CERRADO

- Prereg antes de outcomes `docs/research/QORE_ALPHA2_W3_CMTRL_LAST_EXPLORATORY_PREREG_2026-10-12.md`, HEAD ancestral `a18cb43a6fb69eab948d840c6e6101c6a7251906`.
- All33 Gross [#38284821503](https://github.com/mezas3238-hue/qore-core/actions/runs/38284821503) SUCCESS **35/35**: 24.487 señales, 24.399 pares, 88 censuras, 10.841 decisiones opuestas control, **0 mercados con cero señales**. DEV 18.266 trades, gross +0,18660bps y delta **−0,01516bps**; DIAG 6.133 trades, gross +0,06924bps y delta +0,53516bps. Muestra suficiente ambas eras, hipótesis relativa predeclara FAIL.
- Auditoría [#38285345503](https://github.com/mezas3238-hue/qore-core/actions/runs/38285345503) GOOD: 4wk IC95 delta DEV [−0,4443;+0,4252]bps, DIAG [−0,2418;+1,2782]bps; ambos cruzan cero. Clusters con pares DEV312/314, DIAG105/106. Por familia: índices 2.178 señales, metales 1.623, mayores 5.137, cruces 15.549, ningún símbolo seleccionado ex-post. `NO_SUPPORT_PREDECLARED_GROSS`.
- W3 logra densidad y amplía cobertura, pero **no gana evidencia incremental**, retorno bruto absolutamente pequeño y seguramente vulnerable a fricción (la fricción real está por medir, no declarar net negativo sin costes).

## G2 — quote BID/ASK as-of, INICIADO pero SOURCE REAL BLOQUEADO

- Contrato `src/qore/research/alpha2_g2_bidask_causal_contract.py`; tests `tests/research/test_alpha2_g2_bidask_causal_contract.py`.
- [GitHub Actions #38285672036](https://github.com/mezas3238-hue/qore-core/actions/runs/38285672036) PASS **7/7 pruebas sintéticas**: `available_at` causal, quotes freshness máximo 5 segundos para referencia, bid<=ask, fuente/cuenta/símbolo exactos, long entrada ASK/salida BID y short entrada BID/salida ASK. El control de esquema no es descarga ni ejecución, y los tests no prueban edge.
- Data actual: `NET_BLOCKED_NO_VERIFIED_BROKER_BIDASK_HISTORY_OR_PIT`. Faltan quotes históricos de la MISMA cuenta, cobertura completa, source SHA/identidad, calendario de sesiones, tamaño tick y contrato, comisiones/financiación/swap, slippage, gaps/rechazos, noticias publicadas conocidas-as-of, fills controlados y OOS genuinamente independiente. Issue [#852](https://github.com/mezas3238-hue/qore-core/issues/852).

## Reglas de parada y siguiente arquitecto

1. **NO ejecutar W4 sobre 2016–2024 consumido, ni barrer umbrales W1/W2/W3 para publicar un ganador**. Preservar estados y fracaso científico como testigo; evidencia negativa vale más que un PF fabricado.
2. Alta prioridad: construir fuente BID/ASK PIT read-only de broker y comprobar continuidad, latencia y costes y reales de cada símbolo/cohorte; nunca asignar coste 0 porque fuente no existe. Iniciar capturas prospectivas de quotes mediante autorización adecuada en entornos de investigación sin órdenes, reteniendo SHA original.
3. Resolver `source account mismatch` 12 vs21, semántica exacta de tick_volume productor y expiración de artefactos, condiciones de operación por familia, DST, especificaciones de CFD; estratificar antes de combinar.
4. Fijar nuevo registro independiente de datos (no declarar 2024+ virgin automáticamente), prereg método futuro solo sobre fuente temporal aún no explorada y con evidencia del tamaño de efecto mínimo detectable.
5. Certificación UTC-001: **cada año/fold** PF net ≥1,5, E net≥+0,15R, Sharpe net≥1,5, Sortino net≥2, payoff≥1,5, maxDD observado≤6R, MC p(ganancia)≥90%, p95 DD≤15R, suficientes operaciones y meses, integridad anti-lookahead, riesgos por cluster, winners preservation, MAE/MFE, paper independiente, CIBO+risk reviews. No compensar años malos promediando.
6. Mantener ramas investigación y PR draft, nada al VPS/Shared/CIBO/MT5/QDLE/LIVE hasta aprobación independiente explícita. A día de hoy **rentabilidad de QORE-Alpha 2 NO demostrada**.


## Addendum G2 REAL BID/ASK / SHA / quote quality — 2026-10-12

**PR #840 sigue DRAFT. Sin órdenes y sin NET.** La afirmación anterior de ausencia de todo BID/ASK original queda superada **únicamente en alcance SOURCE PARTIAL** por los nuevos testigos:
- Productor original 12 y nuevo21, campo native volume sin transformación directa, SHA/AST original fuente: Actions [#38287282241](https://github.com/mezas3238-hue/qore-core/actions/runs/38287282241) SUCCESS; no demuestra misma cuenta, volume como ticks y no volumen negociado.
- PR externos QORE Native [#849](https://github.com/mezas3238-hue/qore-core/pull/849), [#851](https://github.com/mezas3238-hue/qore-core/pull/851) comparten fuente histórica nativa ICMarkets DEMO. Alpha2 reaudita 29/29 símbolos originales con **37.430 BID y 37.342 ASK** en dos ventanas de 10min consumidas, **2020 y 2023**: Actions [#38288561813](https://github.com/mezas3238-hue/qore-core/actions/runs/38288561813) SUCCESS, 5/5 negative tests, SHA originales y codificación entero/decimal. Original 2026 (tercera ventana) **precios no abiertos**; NO cobertura de 10 años, NO homologación de 33 brokers, 0 NET.
- **Fuente-quality precongelada antes de medir spreads**, contract `docs/research/QORE_ALPHA2_G2_QUOTE_29_SECOND_GRID_SOURCE_QUALITY_PREREG_2026-10-12.md` commit `cfd82a0b0e7a36e2bd27181742123bcc137e5430`. [Actions #38289175880](https://github.com/mezas3238-hue/qore-core/actions/runs/38289175880) SUCCESS Ruff/14 tests; 29×2×600=**34.800 instantes** cada 1s, edad máxima lado 5s, 27.866 spread positivo, **4.297 spread cero en cuarentena**, 2.637 ausente/stale y cero crossed. **No inferir spread cero ejecutable gratis**. SHA JSON `1d2193c7238c48e106f979e9f2311be5129017d66c9f30e437f88fc096fd998b`; artifact #11764855653. Detalle `docs/research/QORE_ALPHA2_G2_REAL_BIDASK_29_SOURCE_SECOND_GRID_VERDICT_2026-10-12.md`.
- Piloto propio EURCHF de 1min con DEMO en Actions [#38287610751](https://github.com/mezas3238-hue/qore-core/actions/runs/38287610751) BLOCKED SOURCE (tras 14/14 synthetic PASS); sin quotes verificadas, sin órdenes/refresh; decoder corregido signed time AND price deltas. No confundir un test sintético de causalidad con la captura externa o primer momento `available_at`.
- **Bloqueos persistentes**: event timestamp histórico no prueba recepción real, falta toda secuencia BID/ASK en entrada+salida por año/fold, contratos y sesiones de broker, comisiones, swaps, slippage, macro PIT, fuente 33 original homologada, holdout independiente, y no soporte de edge en W1/W2/W3. SRC_INTEGRITY_PARTIAL_PASS no modifica NET_BLOCKED ni UTC001 0. No W4 oportunista.

Prioridad operativa ahora: probar contratos y disponibilidad real vía captura forward independiente de quotes con `available_at` real, y obtener cobertura histórica original suficiente por trayectoria sin liberar período reservado ni mandar órdenes; no usar muestras snapshot para convertir no-soporte en PF.

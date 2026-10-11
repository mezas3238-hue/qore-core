# QORE CORE VT08 — AUDITOR P0 M30→M3: CINCO FAMILIAS, SWING PRE-C2 Y POI SOURCE-ONLY REVERIFICADOS

**Fecha:** 2026-10-10 NY / 2026-10-11 UTC. Arquitecto A, PR #765, issues #762/#763. **Estado: RESEARCH ONLY / NO SOURCE_COMPLETE / NO CERTIFICACIÓN**. GitHub-only: 7Y sealed, VPS y cartera LIVE intactos.

## Decisiones de fuente y nivel de autoridad

**TTrades** 2025-07-30 [Timeframe Alignment](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) sección "Time Frame Pairings" y "Example 1 – 30M to 3M Intraday Reversal": 30M→3M y M3 CISD A. **Ejemplo de long:** stop bajo EQ M30 y bajo breaker low; nuestro antiguo stop exclusivamente PS era simplificación C, NO réplica fuente A. Sin swing-POI EQ M30 válido, no generar stop autor desde full-range midpoint.

**TTrades** 2026-08-22 [Internal & External Liquidity](https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/) sección "What Is External Liquidity": swing high externo tiene high mayor que high izquierdo y derecho; swing low externo low menor que low izquierda y derecha. Geometría A **confirmada al CIERRE DERECHO**; antes no es swing causal. NO igualar este pivot externo a "valid swing point" que activa C2 EQ del artículo [2026-10-10](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/). La correspondencia semántica entre externo/swing de reversión/C2 EQ sigue D. Si C2 mismo determina pivot luego, nunca usarlo para justificar un EQ que necesitaba estar activo ANTES de C2.

**TTrades** 2026-01-10 [How CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/): reversión necesita HTF Candle 2/3 closure más CISD LTF dentro de esa misma vela, fecha de confirmación `max(HTF.closed_at, CISD_M3.closed_at)`. C3 sin CISD interno NO se vuelve validada con un CISD futuro C4.

**TTrades** 2026-07-18 [POI priority](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/): FVG → relevante external swing high/low → CISD retest, entre PS y rango actual. El POI que aparece **no autoriza orden**.

**Especificación formal por familia** publicada antes de medir este censo: [VT08_A_AUDITOR_M30M3_FIVE_FAMILY_CAUSAL_SOURCE_SPEC_2026-10-10.md](VT08_A_AUDITOR_M30M3_FIVE_FAMILY_CAUSAL_SOURCE_SPEC_2026-10-10.md), M15 H4 C2 Closure→C3, H4 C3 Continuation, H4 C3 Closure→C4, M30→M3 C2 closure+positional, M30→M3 retest. Distintas etapas/timestamps y POI/familias, sin duplicar señales madres.

## Prerregistro y nueva implementación independiente

**Prerregistro ANTES de resultados:** [VT08_A_M30_M3_SWING_POI_SOURCE_CAUSAL_PREREG_2026-10-10.md](VT08_A_M30_M3_SWING_POI_SOURCE_CAUSAL_PREREG_2026-10-10.md), commit `d51a6c4ae40fec262dfeabef6a2af034da117d1e`.

**Código:** `src/qore/infrastructure/trader_lab/vt08_5m_a_m30m3_h1_liquidity_swing_asof_verifier_v1.py`. **Tests:** `tests/infrastructure/trader_lab/test_vt08_5m_a_m30m3_h1_liquidity_swing_asof_verifier_v1.py`. **CI:** `.github/workflows/vt08-a-m30m3-h1-liquidity-asof-reverify-v1.yml`.

- No confía en un `origin_id` del productor: reconstruye los 10 M3 C1, 10 M3 C2, correspondientes 2 M15 de cada M30 y verifica OHLC cross-feed.
- Reconstruye PS/CISD desde M3 originales y comprueba level CISD, PS-price, opposing-series opened_at y confirmed_at <=C2.closed_at. Comprueba SHA identidad madre recomputada. Sin source no autoriza.
- Reconstruye sensor **H1 = tres H1 cerradas antes de C2.open**, usando exactamente **12 M15 cerradas**, nunca posterior; un eventual 3-H1 external pivot se conoce solo al cierre de su right H1, no en su centro. FVG H1 también tiene formed_at previo a C2.open.
- Mide mera intersección entre rango wick H1 FVG y posterior OHLC C2 y si un pivot H1 externo relevant exists/swept. H1 SENSOR/selector "tres últimas H1" es **C-QORE** y NO certificación POI HTF TTrades. FVG/External pivot pueden solaparse, no constituyen bucket serial.
- Filtra de cifras "source-complete" todos los registros; `valid_EQ_C2_swing_definition_fully_adjudicated=False`; EQ contra swing bloqueado, no escoger full-range automáticamente. 105 dual H4 del censo C3 antiguo siguen D; nuevos M30 dual distintos.
- Cada M3 "favorable touch" original sigue **OHLC touch**, nunca BID/ASK fill ni permiso de abrir limit retrospectiva.

## GitHub CI sobre M3 NATIVO real + M15 1095d

[Actions run #38105786480](https://github.com/mezas3238-hue/qore-core/actions/runs/38105786480) **SUCCESS 5/5**, código probado SHA `790cc928e947c6c133a3492e3ed1b259e70acb25`. Ruff GREEN; **11 tests negativos/mercado ×5 = 55 PASS**, on-source independent rerun. M3 native DEMO source run #35941643396 SHA `bc1379d7661aac202495ec67afdd3098473ba723`; M15 from #35934924907 SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`. Sin resultados económicos.

| Mercado | M30→M3 geometrías anteriores | Reconciliadas con CISD/PS y H1 fuente previo | H1 faltante | FVG H1 previo tocado en C2 | Pivot H1 externo relevante confirmado previo | Ese pivot H1 barrido C2 | C2 close corporal a favor lado |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURJPY | 1.895 | 1.893 | 2 | 118 | 403 | 108 | 1.132 |
| USDCHF | 1.751 | 1.751 | 0 | 121 | 347 | 99 | 1.081 |
| NZDUSD | 1.794 | 1.794 | 0 | 111 | 366 | 112 | 1.115 |
| CADJPY | 1.790 | 1.789 | 1 | 122 | 347 | 91 | 1.066 |
| USDCAD | 1.752 | 1.752 | 0 | 128 | 351 | 102 | 1.076 |
| **TOTAL** | **8.982** | **8.979** | **3** | **600** | **1.814** | **512** | **5.470** |

**Interpretación:** 8.979 confirmadas son coincidencia mecánica revalidada con relojes y H1 sensor disponible, no metodología/source-author POI completa. Los 600 son un subconjunto *touched FVG H1 geometry*, NO señales potenciales A y NO estimación de trades; 1.814 pivotes H1 presentes, 512 realmente barridos posteriormente. Todos los conjuntos son **no mutuamente excluyentes**, no sumables ni "funnel validación" serial. 3 sin H1 íntegra conservan INCOMPLETE, nunca fabricated.

### Artefactos ZIP GitHub reproducibles (30 días)

- EURJPY `11689991124`, sha256 `877f6e6c1d7f59a7ba5fa8b18beec8d3c82b37b71f07be4baaa8368a347a8286`
- USDCHF `11690250812`, sha256 `c0dbed668706c53c6313f6a5c765f15f5c63bb9adf252acb8a5e4fd6add2de11`
- NZDUSD `11690170972`, sha256 `ca3c85315d3f8c8db8f7a8cdebf552e09e19ce26aea6cd71b334ab3fec5c72a2`
- CADJPY `11689841471`, sha256 `aaca70bdcbf5f49e43c6b4fc0526d233f74045c8f61a0f6af453926d333c2cff`
- USDCAD `11689706962`, sha256 `5612f8eee14f6ffc5ffd0737af31f987b8e98988beeb340a3e5e4475d33a78ac`

## Respuesta a seis riesgos señalados por el auditor

1. **Swing para EQ C2: D**: external pivot source A no equivale sin fuente al swing usado para EQ, deber POI HTF+timing+auth; no usar formula close→wick en producción sin ello.
2. **Doble barrido H4: D**: 105 siguen aisladas de métricas de certificación; prioridad entre dos sweeps sin autor resuelta. H4 105 no se confunden con nuevos M30 duals.
3. **36 engulf, 129 CISD/PS C3 proxies: C**; no se promueven.
4. **POI por familia: parcialmente fuente A categórica** (FVG, high/low, CISD retest), falta selección del primer POI en rango PS→current y validación de contexto HTF. Un único FVG no es condición universal.
5. **M30→M3 stop EQ+breaker low**: ejemplificado por el autor, pero el PS-only anterior NO basta. Requiere EQ source regime y breaker-low provenance. La comparación anterior del riesgo bruto 42–45% NO es comparación de stops autor-correctos.
6. **BID/ASK fills comisiones y cognitiva: 0**. La estrategia ejecutable y PF/DD permanecen NO CERTIFICABLES. El overlap 2065 market-days OHLC adicional NO significa 2065 señales admitidas.

## Siguiente ronda prioritaria — no ocultar el problema de densidad

**P0 A:** comprobar si el swing point previo que orienta EQ C2 procede de pivote externo/PS anterior bajo ejemplos reales de TTrades y sus timestamps; implementar selector POI FROM defended protected swing→current range usando source H1/H4/daily, FVG primero, swing high/low luego, CISD retest último, con explicita capacidad de varios POI/PS D. Debe haber autor-level examples + tests negativos antes de habilitar EQ o stop.
**P0 A/M30:** validar breaker low (opposing M3 candle series) y stop bajo EQ y breaker, buscando viable entrada favorable sin fijar 8 M3 CISD ni RR ex-post. **No bajar riesgo dejando stop sobre breaker/EQ a conveniencia de densidad**.
**P0 B #763:** revisar A source receipts, refutar o reproducir independientemente 8.982 identities, 8.979 h1-reviewed, 3 incomplete, 600/1814/512 overlaps, prohibir SOURCE_COMPLETE y no firmar A/B manifest hasta POI significativo, clock EQ, M3 BID/ASK/fees y Situation 27+ causal fields. 
**P1:** económico full-paper sólo después source POI+CISD+PS+stop+physical risk; no 7Y sealed, no VPS.

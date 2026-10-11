# QORE CORE — VT08 ARCHITECT A SOURCE CONTRACT POR FAMILIA (AUDITOR M30→M3)

**Version 2026-10-10 / actualización 2026-10-11 UTC.** Referencias: PR #765, A #762, B #763. Documentación fuente para verificador independiente. **No es permiso de trading, no es PR ready para producción**.

## Niveles de autoridad: A, C, D

A = el autor publica regla explícita; C = propuesta operativa parametrizable de QORE; D = sin fuente decidible, NO puede entrar en certificación. Una regla A textual NO vuelve automáticamente A su traducción algorítmica C.

Fuentes:
- [Time Frame Alignment (30-jul-2025)](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/), "Time Frame Pairings" y "Example 1 – 30M to 3M Intraday Reversal": 30M→3M A, CISD entry M3 A, positional A; stop below EQ 30M **Y breaker low** del ejemplo alcista. No extrapolar stop solo a PS.
- [Internal & External Liquidity (22-ago-2026)](https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/), "What Is External Liquidity?": external pivot high H[i]>H[i-1] y H[i]>H[i+1]; low L[i]<L[i±1]. Este swing externo se CONOCE al **CIERRE** de right candle, no en la central. Esto es A geometría externa.
- [CISD Confirms Swing Points (10-ene-2026)](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/): swing REVERSAL validado por HTF C2/C3 CLOSURE y LTF CISD confirmado DENTRO esa HTF. Un pivot externo no basta para autorizar la reversal.
- [POI priority (18-jul-2026)](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/): del protected swing al rango actual, FVG antes de structural high/low, CISD retest último; POI solo contexto.
- [EQ Candle 2/3 (10-oct-2026)](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/), sections "When Candle 2 Closes Against/With the Swing Point": C2 contra swing = (C2.close+C2.wickExtreme)/2, con swing=(C2.high+C2.low)/2, C3 full. **Selector del swing originario EQ D** hasta conexión de POI validada y fecha before-C2 sin usar C2 itself.
- [Positional Entries (8-ago-2026)](https://ttrades.com/positional-entries-enter-before-the-expansion/): opening de nueva vela HTF tras valid C2/C3 closure, LTF CISD y PS preexistente. "Closest protected swing" NO necesariamente elegido.

## Requisito común as-of

Cada señal madre debe tener:
market, family, c1/c2/c3 source H4/H1/M30 timeframe y OHLC SHA, prior pivot_id + pivot_right_closed_at, poi_id/poi_kind/poi_formed_at/poi_touched_at/poi_source_range_proven, cisd_id + opposing_series_started_at + M3/M5/M15 bar closed_at, ps_id + ps_confirmed_at + defended_price, htf_closure_closed_at, evaluation_at, market-source SHA, broker bid/ask-side price + costs, deterministic entry_id, reason_code y author-source vs QORE hypothesis tags. No número de OHLC derivado de futuro. Snapshot previo no debe incluir C3/C4 futuras. Duplicación mismo market NY day resuelta ex-ante, no mejor R/R futuro.

Definir relojes:
- Pivote EXTERNO (liquidez target) conocido desde cierre derecho de las 3 velas; no es automáticamente swing REVERSAL válido para EQ.
- Swing REVERSAL validado desde max(HTF-closure, LTF-CISD-closed, confirmed-POI-observation), **nunca retroactivo al sweep**.
- Para EQ C2 "closes against/with SWING", el **swing de referencia de C2** debe tener identificador y evidencia conocida antes del C2.open; si no se conoce, EQ intra-C2 queda D y NO se toma fórmula full universal ni close-wick inventada.
- Un swing creado/validado por la C2 recién cerrada puede usarse para nuevas decisiones C3; NO es por definición el swing previo contra el cual C2 cerró. **Son dos objetos distintos**.

## Matrix de familias

| Familia | Contexto POI | HTF closure y CISD/PS | Early decision | Estado fuente / bloqueantes |
|---|---|---|---|---|
| C2 Closure→C3 H4→M15 | FVG HTF, high/low, fallback CISD; todos known-before-touch, confirm at POI | C2 hace single sweep C1+close inside; CISD/PS M15 dentro C2, HTF closed antes apertura C3 | Positional open C3, PS protegido; no nuevo CISD en C3 | C2 geometría/CISD proxy sí; POI HTF/significancia y daily bias contexto D |
| C3 Continuation H4→M15 | Si valid C2 y contexto source, POI FVG/high/low/PS en C3, formed-before-touch | C2 H4 cerrada antes C3 open; CISD en M15 de C3 antes entry, sin C3 H4 final | Intracycle M15; alternative positional si ya había confirmación previa | POI no restringir FVG; selección multiple PS/FVG D |
| C3 Closure→C4 H4→M15 | C2 reversal FALLÓ, C3 valida body closure, POI antes de reacción | C3 H4 cerrada y su CISD interno <= C3.closed para validar swing C3; nuevo CISD C4 solo para timing propio | C4 open positional o M15 posterior, no usar futuro C4 H4 | 105 dual sweep en viejo censo siguen D, 36 engulf proxies C, 129 CISD proxies C |
| C2 Closure→C3 M30→M3 | 30M structure ALINEADA HTF/daily, POI FVG primero luego swing H/L/CISD último; no adoptar H1 sensor como autor-validado | M30 C2 sweep single, close dentro C1 y POI source; M3 CISD PS CLOSED dentro C2 | Positional en M30 C3 open (primera M3.open); comparar stop bajo EQ M30 Y breaker low del ejemplo bullish; PS no basta | 8.982 shapes/3.542 OHLC retest NO señales; EQ swing reference D, breaker provenance D, POI/fills D |
| M30→M3 Entry Refinement | Misma señal madre validada M30→M3 | CISD-level retest conocido antes de C3.open, nuevo retest sólo DESPUÉS M3 closes; no adivinar trayecto intrabar | Limit hipotético nivel CISD; caduca máximo al cierre C3 **C QORE**, no confundir con fuente A | BID/ASK, spread, comisiones, intrabar sl/limit/tp tick, ATR, PF/DD faltan; one trade/day |

### POI seleccionados / los que NO se deben filtrar

A: FVG prioridad; si no FVG en rango pertinente, high/low relevante; si ninguno, CISD retest. No convertir "no FVG" en "no trade" universal. FVG triple fuente cerrado; el selector "primero al recorrer desde PS" necesita rango espacial comprobado y posibles varios POI. Selección nearest PS, última señal CISD, 8 velas timeout, wick 50% threshold: **D/C NO autorizadas**.

### DUAL_SWEEP: fallo cerrado

- C2 H4 dual swept ambos C1 high/low: 105 geometrías detectadas en la cohorte C3 Closure→C4 anterior (80 dentro Owner). La fuente no decide qué lado manda. Status DUAL_SWEEP_D, sin abrir dirección por último CISD.
- C2 M30 dual swept ambos C1 extremos: mismo status D, pero **no son los 105 eventos H4**. Contar separado y prohibir suma entre horizontes.

### Stop y entrada favorable M30/M3

En el ejemplo alcista concreto: stop < EQ(M30) Y stop < breaker_low. Pero EQ(M30) no debe inferirse usando (H+L)/2 de manera universal; primer prerequisito EQ swing/POI source; segundo breaker low demostrado. Cualquier record sólo PS recibe STOP_GEOMETRY_C_ONLY y EQ_NOT_ATTESTED. En largos, una limit M3 más baja mejora riesgo nominal sólo si entry > protected stop; no demuestra que se puede llenar en bid/ask ni que ese target sea liquidez autor-validada. El "earliest clean touch after M3 close" posterior es una observación, NO autorización para enviar limit retrospectiva.

### Gates antes de entregar a B

1. Independiente verificador compara closed-M3 source con M15, cross-feed H1/M30 SHA; rechazo ante timestamp future, OHLC mismatch, missing POI o hash.
2. Todos 27+ CAUSAL_FIELDS cognición populated with provenance and known-at, no valor futuro; B firma A→B digest estable; APPPROVED_A_B_MANIFEST_SHA256=NULL hasta entonces.
3. Replay PAPER physical with bid/ask/fees; nominal 3.542 retesteos no se consideran fills. PF/DD sólo después de riesgo real y cognición completa. No VPS/7Y.

**VEREDICTO:** SOURCE COMPLETE = 0 hasta resolver selector swing-ref-before-C2/POI significance/PS/stop breaker, BIDASK y B certification. El hallazgo de densidad es útil pero sigue geométrico.

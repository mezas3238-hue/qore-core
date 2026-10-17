# VT08 P0 — PRERREGISTRO M30→M3 DE TTRADES: ENTRADA POSICIONAL VERSUS RETEST CISD

**Congelado antes del primer censo nuevo.** 2026-10-10 QORE Core Architect A; PR #765, A issue #762, coordinación B #763. Owner rechaza densidad de VT08 actual. Este es un ensayo **NUEVO fractal M30/3M**, no H4→3M inventado ni relajación arbitraria del setup.

## Fuente primaria y correspondencia explícita

- https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/ — TTrades Time Frame Pairings: **30M→3M**; example 1 30M bullish reversal and 3M CISD with continuation and **positional entry**. Otras parejas: 4H→15M, 1H→5M, 15M→1M. No claim H4→3M directa.
- https://ttrades.com/ttrades-fractal-model-indicator-full-guide/ — **3 Minute Template**: Daily/4H context, 3m-30m Fractal Model, 15m-4H overlay. Por ello no forzar B01 daily bias como universal; se medirá alineación/conflicto contextual.
- https://ttrades.com/a-simple-3-step-trading-model-full-breakdown/ — 30M→3M lower timeframe alignment and IC-CISD.
- https://ttrades.com/positional-entries-enter-before-the-expansion/ — new HTF open only after completed model+valid PS, evaluate stop relation and risk; cannot require new CISD in new HTF.
- https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/ — POI priority (FVG→valid swing high/low→CISD retest), **CISD retest limit** is a research execution option, not universal guarantee.
- https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/ — C2 EQ differs full vs close→extreme depending on VALID swing; do **NOT** invent M30 intra-C2 EQ if swing/POI not validated.

## Evidence read-only exactly same 1095d dates / markets

H4/daily M15 consumed historical original #35934924907, exact artifact SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`. **Native M3 cTrader DEMO artifacts** source run #35941643396, code SHA `bc1379d7661aac202495ec67afdd3098473ba723`. Five matched markets EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD; evidence native M3, **NEVER fake/interpolate from M15**. Must cross-check M30 native M3 aggregation vs two M15 actual candles (OHLC and completeness) when both available. If disagreement => bucket `CROSS_TF_OHLC_MISMATCH`, no source-verified signal.

## Source-object construction, as-of rule

- `M30_C1`: ten consecutive CLOSED M3 bars [t-60m,t-30m). `M30_C2`: ten consecutive CLOSED M3 [t-30m,t) with one-side sweep C1 + H/L close back inside C1. `t` is C3 opening, 30-min aligned, in a currently authorized Owner H4 interval 01/05/09 NY (separately count 13NY/etc outside Owner; don't alter current hours).
- `M3 CISD/PS`: `protected_swings_in_candle2(C2 10xM3)` with `important_level=C1 swept edge`; confirmation m3.close <=t; reject >1 PS as `MULTIPLE_PS_D`, double sweep `DUAL_SWEEP_D`, no PS as no setup. **This algorithm is QORE structural proxy** pending author examples/HTF POI; NEVER source trade-ready on proximity alone.
- `ENTRY_POSITIONAL_M30_OPEN`: price first native M3 OPEN at t, provided stop PS below (long) / above (short), target **opposite C1 liquidity** beyond entry, no future C3 features. Compare gross geometric RR `(target - entry)/(entry-stop)` (bear inverse).
- `ENTRY_CISD_RETEST_M3`: PRE-place level = prior confirmed CISD open-series level as of t (not C3 EQ and not hindsight), only if strictly between PS stop and C3 opening entry in more favorable direction. A hypothetical retest is counted after a native M3 CLOSED TOUCH **and only if no earlier stop/target hit before touch**. If touch and stop or target share same M3 bar, mark **intrabar sequence UNRESOLVED** (not clean fill). No spread/BID/ASK or SL/TP execution attribution. RR computed on the predeclared target and stop; successful/failing trades not inferred.
- `ENTRY_M3_CISD_NEW`: new 3M CISD formed in C3 after t, signal only after confirming 3M bar close, next 3M OPEN; **separate family execution alternative**, do not count as an independent mother setup until selection and source POI as-of.
- Published thresholds `RR>=1.0,>=1.5,>=2.0` are **C diagnostic bins** to see entry improvement; no profit optimization / certification threshold. Count by market and by year, daily distinct IDs, eligibility and median/percentile risk/target RR where viable, and unique day overlap with the H4 branch (no double count).
- No high/low wick future is allowed in initial positional price. For retest touch observations M3 OHLC can confirm *opportunity of touch* only after that M3 closes. No claims filled without BID+ASK and order sequencing. No PnL/PF/DD generated.

## Scope and honest boundary

Max 1 executed trade / market NY day remains QORE policy: count all geometric mother structures, distinct days and `FIRST_VALID_EVENT_ASOF` determinism, but no order execution. C3 Closure→C4 variant will require separate family and source POI, not port all 294 geometries. EQ daily continuation pending. No 7y holdout, VPS, live or cognitive approved manifest. Owner-requested density: numbers **measured**, not thresholds invented; outcome-blind prereg before measurement. 

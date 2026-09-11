# VT-08 CRT / H4 Power of Three V2 — source-fidelity freeze

## Status

The earlier VT-08 V2 campaigns are **falsified as faithful methodology reconstructions**.
Their artifacts remain historical engineering evidence only and MUST NOT be used as
CRT/4H-PO3 economic evidence. In particular, the old `13,468` entry count is invalid.

The later 11-market source-fidelity run that reported `16,351` mechanical candidates is
also **not final source-fidelity evidence**. The re-audit found that the scanner covered
only half of the source timing family and did not retain the source-required POI state.
Those candidates remain useful engineering evidence, but the count must be recomputed.

The current frozen research contract is:

`v2.4-source-fidelity-reaudit`

It is intentionally non-economic while source-authorized entry selection, target/lifecycle,
and the remaining qualitative judgments are unresolved.

See also `VT08-CRT-H4-AMD-V2-FIDELITY-REAUDIT-002.md`.

## Primary authority

Human Owner-provided copy of TTrades **Trading The 4 Hour Power Of Three - OHLC / OLHC**.

- local source file: `1000854868.mp4`
- SHA-256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`
- public identity: `youtube:FAKWJ-1NlLE`
- duration: about `21:16`

The same-author H4 PO3 lesson companion may clarify source slides/examples. The lesson
explicitly depends on TTrades Candle-2, Candle-3 and CISD/protected-swing concepts. Those
prerequisites may define required concepts but may not introduce a different strategy.

## Rule classification

Every mandatory rule is one of:

- `EXPLICITLY_STATED`;
- `VISUALLY_DEMONSTRATED`;
- `REQUIRES_FORMALIZATION / SOURCE_AMBIGUOUS`.

A source-ambiguous item MUST NOT silently become an automated trading rule.

## Video/source-to-code evidence map

| Source region | Directly supported fact | Code consequence |
| --- | --- | --- |
| ~00:30–01:10 | PO3 is Accumulation → Manipulation → Distribution/Expansion | preserve H4 PO3 causal sequence |
| ~01:30 | directional-candle OHLC/wick/body relationship | opposing wick/run precedes body expansion |
| ~01:50–02:30 | large/deep opposing run versus shallow opposing wick | retain qualitative `SHALLOW`, `LARGE`, `UNRESOLVED`; no invented ratio |
| ~02:50–03:10 | continuation-expansion case follows larger opposing run/reversal sequence | Candle-3 continuation is distinct |
| ~03:30 | reversal-expansion case shows wick forming and same-candle expansion | Candle-2 reversal-to-expansion is distinct |
| timing slide ~03:35–03:40 | complete repeating H4 opening families | scan all six anchors per family, DST-aware |
| ~03:50–04:11 | use H4 for bias/candle-closure context; let the wick form, trade the body | no anticipatory entry and no invented D1 formula |
| examples from ~04:11 onward | M15 is repeatedly paired with H4; objectives are contextual | preserve M15 confirmation; no universal TP |
| same-source lesson sequence | reach source-defined POI → CISD/protected swing → continuation entry | POI reach/provenance required before CISD; do not invent universal POI selection |

## Source-grounded rules

1. H4 PO3 is accumulation, manipulation, distribution/expansion.
2. Candle 2 can provide reversal-to-expansion when its opposing wick/run is **shallow**.
3. A **large/deep opposing run** in Candle 2 means do not force Candle-2 expansion; wait
   for Candle-3 continuation.
4. The source principle is **let the wick form, then trade the body**.
5. M15 is the demonstrated lower-timeframe confirmation for H4.
6. A source-defined point of interest must be reached before lower-timeframe continuation
   confirmation. The source does not prove one universal mechanical POI selector for all
   historical cases.
7. CISD/protected swing confirms that the opposing run formed a swing.
8. The protected-swing extreme is the structural invalidation reference. No arbitrary
   stop buffer may be invented.
9. Directional bias/context is required. The primary lesson does not provide one universal
   OHLC-only formula that can replace that judgment.
10. The complete source H4 opening families are:
    - Forex: `17:00 / 21:00 / 01:00 / 05:00 / 09:00 / 13:00` New York;
    - Futures: `18:00 / 22:00 / 02:00 / 06:00 / 10:00 / 14:00` New York.
    These are H4 anchors, not automatic trades.
11. CISD confirmation price is an observation. The source does **not** establish a
    universal rule that the exact CISD confirming close is always the executable entry.
12. Source context is causal: a bias/wick/POI annotation observed after confirmation may
    not authorize an earlier opportunity.

## Explicit non-rules — prohibited inventions

Unless the primary source or an explicitly required prerequisite states them
unambiguously, V2 MUST NOT add:

- a `50%` definition of shallow versus large wick;
- ATR, body/wick ratio, volatility percentile, or optimized wick thresholds;
- a mandatory two-D1-candle bias formula;
- a forced `1→5→9` or `2→6→10` sequence;
- a requirement that every H4 anchor creates a trade;
- a fixed maximum trades/day introduced to force plausible frequency;
- the VT-08 V1 FVG rule as a blanket V2 requirement;
- a universal POI-ranking/selection algorithm when multiple FVG/high/low candidates exist;
- universal previous-day-high/low take-profit;
- fixed-R target;
- automatic XAUUSD classification as Forex or Futures timing;
- universal market entry at the CISD confirming close.

## What raw OHLC can and cannot decide

Raw M15/H4 evidence can deterministically identify:

- source H4 timing anchors;
- previous H4 high/low runs;
- completed H4 reversal-closure structures;
- M15 CISD and protected-swing extreme;
- CISD confirmation price/time as an observation;
- descriptive post-confirmation MFE/MAE and H4-close path.

Raw OHLC from this lesson alone cannot faithfully decide:

- every correct source POI selection when several structures are available;
- a universal numerical shallow/deep cut-off;
- every directional-bias/context judgment;
- one universal executable entry price;
- one universal take-profit/lifecycle;
- the XAUUSD timing family.

Those unresolved judgments remain explicit evidence states. The implementation abstains
rather than inventing them.

## Trader Lab semantics

The unannotated >=730-day historical pass is a **source-fidelity audit**, not an economic
backtest. It may count mechanically observable candidates and characterize their paths,
but:

- candidate ≠ entry;
- unresolved POI/bias/wick judgment ≠ trade;
- CISD confirmation price ≠ automatically authorized execution price;
- favorable post-confirmation path ≠ win;
- adverse post-confirmation path ≠ loss without a source-authorized execution/lifecycle;
- Stress and Monte Carlo do not run without a source-authorized return series;
- `DEMO_ELIGIBLE` remains false.

The previous `16,351` candidate total must be recomputed using all source timing anchors.
The replacement audit must also mark POI selection as unresolved where it cannot be
source-bound. Neither correction authorizes economic trades.

Faithfulness to the Human Owner-provided source has priority over creating an apparently
complete but invented trading system.

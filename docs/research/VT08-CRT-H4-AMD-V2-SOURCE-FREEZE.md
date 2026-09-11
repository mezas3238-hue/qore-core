# VT-08 CRT / H4 Power of Three V2 — source-fidelity freeze

## Status

The earlier VT-08 V2 campaigns are **falsified as faithful methodology reconstructions**.
Their artifacts remain historical engineering evidence only and MUST NOT be used as
CRT/4H-PO3 economic evidence. In particular, the old `13,468` entry count is invalid.

The later 11-market source-fidelity run that reported `16,351` mechanical candidates is
also **not final source-fidelity evidence**. A subsequent video/PDF re-audit found that the
scanner covered only half of the source timing family. Those candidates remain useful
engineering evidence, but the count must be recomputed after the timing correction.

This freeze supersedes every earlier V2 operationalization that added a D1 formula, a
50% wick threshold, a universal take-profit, a fixed one-sequence-per-day assumption, or
any other rule not stated/demonstrated by the source.

See also `VT08-CRT-H4-AMD-V2-FIDELITY-REAUDIT-002.md`.

## Primary authority

Human Owner-provided copy of TTrades **Trading The 4 Hour Power Of Three - OHLC / OLHC**.

- local source file: `1000854868.mp4`
- SHA-256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`
- public identity: `youtube:FAKWJ-1NlLE`
- duration: about `21:16`

The same-author H4 PO3 PDF/blog released with the lesson may be used to read source
slides/examples that appear in the primary video. The video itself says Candle-2 and
Candle-3 lessons are prerequisite material. Those TTrades prerequisites, plus TTrades
CISD definition, may be used only to define concepts the primary lesson explicitly
depends on. They may **not** introduce a new strategy.

## Rule classification

Every mandatory rule must be classified as one of:

- `EXPLICITLY_STATED`;
- `VISUALLY_DEMONSTRATED`;
- `REQUIRES_FORMALIZATION / SOURCE_AMBIGUOUS`.

A source-ambiguous item MUST NOT silently become an automated trading rule.

## Video-to-code evidence map

| Video region | Directly supported rule | Code consequence |
| --- | --- | --- |
| ~00:30–01:10 | PO3 is Accumulation → Manipulation → Distribution; Candle 1 establishes accumulation/reference | V2 models H4 PO3 phases; no unrelated indicator is added |
| ~01:30 | Directional-candle OHLC/wick/body relationship | V2 waits for opposing wick/run before body expansion |
| ~01:50–02:30 | Two H4 types are contrasted visually: large/deep opposing run versus shallow opposing wick | V2 preserves `SHALLOW`, `LARGE`, `UNRESOLVED` as qualitative source states; it does **not** manufacture a ratio |
| ~02:50–03:10 | Continuation-expansion case follows the larger opposing run / reversal sequence | Candle-3 continuation is a distinct scenario |
| ~03:30 | Reversal-expansion case shows wick forming and same-candle expansion | Candle-2 reversal-to-expansion is a distinct scenario |
| ~03:50–04:11 | Summary: use H4 for bias/candle-closure context; “let the wick form, trade the body”; once expanding, entries become easier | Entry requires source context plus M15 protected-swing/CISD; no mandatory D1 formula is invented |
| examples from ~04:11 onward | M15 is repeatedly used with H4 examples; examples show contextual objectives rather than one universal exit | M15 is the decision/confirmation timeframe; no universal TP/fixed-R target is encoded |
| source timing slide | Full repeating H4 opening families are shown across the 24-hour cycle | Audit must cover all six H4 anchors per source family; an anchor is not an automatic trade |

## Source-grounded rules

1. H4 PO3 is accumulation, manipulation, distribution/expansion.
2. Candle 2 can provide reversal-to-expansion when its opposing wick/run is **shallow**.
3. A **large/deep opposing run** in Candle 2 means do not force Candle 2 expansion; wait
   for Candle 3 continuation.
4. The source entry principle is **let the wick form, then trade the body**.
5. M15 is the demonstrated lower-timeframe confirmation for H4.
6. CISD/protected swing is used to confirm that the opposing run has formed a swing.
7. The protected-swing extreme is the structural invalidation reference. No arbitrary
   stop buffer may be invented.
8. The source uses directional bias/context. The primary video does not give one universal
   OHLC formula that can replace that contextual judgment.
9. The complete source H4 opening families are:
   - Forex: `17:00 / 21:00 / 01:00 / 05:00 / 09:00 / 13:00` New York;
   - Futures: `18:00 / 22:00 / 02:00 / 06:00 / 10:00 / 14:00` New York.
   These are **H4 anchors**, not proof that every anchor must produce a setup or trade.
10. CISD confirms a protected swing, but the primary lesson does **not** establish a
    universal rule that the exact CISD confirming close is always the executable entry
    price. Confirmation price and execution price must remain separate unless the source
    authorizes an exact entry model.

## Explicit non-rules — prohibited inventions

The following are **not** allowed to become V2 rules unless the primary source or an
explicitly required prerequisite is later shown to state them unambiguously:

- no `50%` numerical definition of shallow versus large wick;
- no ATR, body/wick ratio, volatility percentile, or optimized wick threshold;
- no mandatory two-D1-candle bias formula;
- no rule that every day must produce exactly one `1→5→9` or `2→6→10` sequence;
- no rule that every H4 anchor must produce a trade;
- no fixed maximum trades/day introduced merely to force a plausible frequency;
- no FVG requirement imported from VT-08 V1;
- no universal previous-day-high/low take-profit;
- no fixed `R` target;
- no automatic classification of XAUUSD as forex or futures timing when the source does
  not specify that mapping;
- no universal market entry at the CISD confirming close.

## What software can and cannot decide from raw OHLC

Raw M15/H4 data can deterministically identify:

- source key-time H4 windows;
- previous H4 high/low runs;
- completed H4 reversal closure structures;
- M15 CISD and the protected-swing extreme;
- CISD confirmation price/time as an observation;
- post-signal MFE/MAE and H4-close path observations for research.

Raw OHLC **cannot faithfully decide** from this video alone:

- whether a wick is “shallow” or “large/deep” using a numerical cut-off;
- every instance of directional bias/context when the video relies on trader context;
- one universal executable entry price for every confirmed protected swing;
- a universal take-profit for every setup;
- the timing family for XAUUSD.

Those unresolved source judgments must remain explicit evidence states. The implementation
must abstain rather than invent them.

## Trader Lab semantics

The unannotated >=730-day historical pass is a **source-fidelity audit**, not an economic
backtest. It may count mechanically observable candidates and characterize their paths,
but:

- candidate ≠ entry;
- CISD confirmation price ≠ automatically authorized execution price;
- favorable H4-close path ≠ win;
- adverse H4-close path ≠ loss unless an actual source-authorized stop event exists;
- Stress/Monte Carlo are not run without a source-authorized return series;
- `DEMO_ELIGIBLE` remains false.

The previous `16,351` candidate total must be recomputed because its audit omitted source
H4 anchors. This correction does not authorize economic trades.

This is intentional. Faithfulness to the Human Owner-provided video has priority over
creating an apparently complete but invented trading system.

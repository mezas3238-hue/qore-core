# VT-08 CRT / H4 Power of Three V2 — reconstruction source freeze

## Status

The first VT-08 V2 campaign at SHA `5326d70e99c929fef6a2a0caef27ad5381b95e38`
is falsified as a methodology reconstruction. Its artifacts remain historical engineering
evidence only and MUST NOT be used as economic evidence for CRT/4H PO3.

## Primary source

Human Owner-provided copy of TTrades **Trading The 4 Hour Power Of Three - OHLC / OLHC**.

- source file SHA-256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`
- public source identity: `youtube:FAKWJ-1NlLE`

Corroborating TTrades material may clarify concepts explicitly referenced by the primary
lesson (daily bias, Candle 2/Candle 3 closures, CISD/protected swings and equilibrium),
but may not add an unrelated entry model.

## Falsified implementation findings

The first V2 implementation:

1. scanned six H4 windows across the entire day instead of the source's institutional
   session sequence;
2. did not provide D1 market evidence to the evaluator even though expansion is to be
   aligned with the daily candle;
3. treated any non-stopped H4-close mark as a terminal return and later counted positive
   marks as wins, even though the source objective had not necessarily been reached.

The old `13,468` result is therefore invalid for methodology/economic conclusions.

## Reconstructed deterministic contract

The research implementation freezes one institutional sequence per New-York day:

- FX/spot-FX pairs: H4 opens `01:00 -> 05:00 -> 09:00` NY.
- futures-style Core markets: `02:00 -> 06:00 -> 10:00` NY.
- XAUUSD is explicitly classified as futures-style for this V2 operationalization; this
  classification is versioned and falsifiable, not inferred from performance.

The two most recent fully closed provider D1 candles create a one-sided daily bias using
closure/range logic. Without a bias the intraday model abstains.

Candle 1 is reference/accumulation. Candle 2 must manipulate against the daily bias and
M15 must confirm a protected swing through CISD. A shallow manipulation may expand in
Candle 2. A deep Candle-2 opposing run is not traded immediately; a completed aligned
Candle-2 reversal is required before searching Candle 3 for a fresh protected swing.

The source uses equilibrium/50% to distinguish halves of a range. Because the primary
lesson describes wick size qualitatively rather than supplying an optimized numeric wick
parameter, V2 uses the 50% range split as an explicit **source operationalization**. It is
not tuned against results and must be falsified against source-labelled examples before
promotion.

Entry is the causal M15 CISD-confirming close. Stop is the protected-swing manipulation
extreme. The primary research objective is the prior completed daily directional extreme.
If neither target nor stop is reached before the source H4 candle closes, the observation
is **censored**. H4-close mark-to-market remains descriptive path evidence and is never a
win/loss label.

At most one V2 setup is retained per market per New-York day in this reconstruction.

## Governance

This is research-only. Quality gates, backtests, OOS, Stress and Monte Carlo do not grant
DEMO/LIVE/Risk/execution authority. Any post-OOS methodology change consumes the holdout
and requires preregistration plus fresh unseen evidence.

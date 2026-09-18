# TURTLE_SOUP_XAUUSD_R2 — CIBO FULL CONTEXT FREEZE

Identity: `TURTLE_SOUP_XAUUSD_R2_CIBO_FULL_CONTEXT`

Evidence: already-consumed CIBO XAUUSD M5 corpus, 2016-09-17 through 2026-09-17. This is not a fresh holdout.

## Temporal separation

- Model-development block: `[2016-09-17, 2022-09-17)`.
- Internal temporal validation block: `[2022-09-17, 2026-09-17)`.
- Validation labels may not fit, tune, rank, or threshold the R2 context model.
- Full 10Y replay is reported separately and remains consumed development evidence.

## Base Turtle Soup mechanics

Prior-candle meaningful liquidity boundary -> raid -> exact C2 reversal closure -> causal CISD inside C2 -> entry at next source open -> exact Protected Swing stop -> untouched C1 opposite boundary as structural DOL. H1 + H4, LONG + SHORT, single position, 24h maximum lifetime, STOP_FIRST for same-M5 stop/target ambiguity.

## CIBO context incorporated before entry

R2 consumes all currently formalized pre-entry context available from the CIBO/Behavior-Lab schema or deterministically derivable from the same M5 evidence:

- timeframe;
- side;
- raid session;
- weekday;
- prior-body alignment;
- FVG formed after raid but strictly before entry;
- exact equal-liquidity presence;
- raid depth normalized by preceding source ranges;
- reclaim latency;
- CISD latency normalized to source timeframe progress;
- Protected Swing risk distance normalized by source range;
- source-range state versus preceding source ranges;
- C2 body fraction;
- rejection-wick fraction;
- close location;
- projected structural R to the frozen DOL;
- target distance normalized by source range.

The development block fits transparent shrunk mean-R effects for predeclared feature buckets. The selection rule is frozen as `predicted_primary_r > 0` after 0.05R/trade friction. No session/side/timeframe is hard-coded as good or bad in advance.

## Explicit non-leakage rule

The following are never R2 model inputs because they are only knowable after entry: MFE, MAE, target hit, target time, exit reason, future price path. They may be reported only as diagnostics after the replay.

## Governance

This run cannot automatically promote, certify, enable DEMO, LIVE, real capital, or production. C3 remains unresolved and is not fabricated. Any future fresh holdout requires a separate frozen candidate and independent evidence window.

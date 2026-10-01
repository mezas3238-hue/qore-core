# CIBO Phase22 Historical Replay Economics Amendment V1

**Status:** PRE-OUTCOME GOVERNANCE CONTRACT — DOES NOT OPEN V2

## Problem resolved

The active V2 certification holdout is historical:

`2015-10-19T00:00:00Z -> 2016-04-19T00:00:00Z`.

A historical replay can produce causal Trader opportunities and structural
market outcomes, but it cannot truthfully produce cTrader DEMO order IDs, deal
IDs, position IDs or broker settlement events from 2015-2016.

The inherited Phase20 forward-outcome type requires actual provider
fill/settlement provenance. Applying that requirement literally to V2 makes the
historical holdout impossible to execute without fabricating broker facts.

Fabrication is forbidden.

## Amendment

This amendment changes **provenance semantics only** before any V2 outcome is
emitted. It does not change:

- the CIBO policy candidate;
- candidate parameters;
- Phase20D economic thresholds;
- Phase22 economic thresholds;
- temporal folds;
- population minimums;
- pass/fail hard gates;
- baseline policy;
- CE2I tool requirements.

The required execution-economics model is:

`EMPIRICALLY_CALIBRATED_COUNTERFACTUAL_HISTORICAL_REPLAY`.

Before V2 may open, a separate cTrader DEMO calibration population must be
sealed and READY with at least eight distinct minimum-volume entry executions
for each required symbol, causal quote reconstruction, empirical slippage
calibration and an execution model. All calibration positions must be closed.

Current DEMO calibration fills are evidence about current provider execution.
They are **never** relabeled as 2015-2016 fills.

## Required downstream implementation

A versioned historical-replay settlement adapter must be implemented before V2
outcomes are emitted. It must:

1. derive structural entry/exit outcome only from frozen Trader logic and V2
   source data;
2. apply only the pre-frozen empirically calibrated provider execution model;
3. label the resulting economics as counterfactual historical replay;
4. never emit broker order/deal/position identifiers for historical events;
5. preserve decision-before-outcome chronology and capital conservation;
6. use the same Phase20D economic thresholds without refit;
7. keep decision-time provider proxy diagnostics separate from settled replay
   economics so costs are not double-counted;
8. remain deterministic and replayable;
9. fail closed if the provider calibration is not READY;
10. grant no LIVE, FundedNext, VPS, production or real-capital authority.

V2 remains sealed until the provider-calibration receipt and replay-settlement
adapter are both terminally green.

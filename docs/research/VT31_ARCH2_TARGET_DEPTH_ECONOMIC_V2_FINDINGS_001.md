# VT31 NAS100 — Target-Depth Economic V2 Findings 001

**Owner:** Sergio Meza  
**Status:** NO SURVIVOR / W3-DOL2 MECHANISM RETAINED FOR RELOSS REPAIR  
**Workflow:** `37442469140` — SUCCESS  
**Head:** `c9e961939886693248184d82ac8a382d26b6e469`

## Result

The hardened finite-window V2 produced:

- no research survivor;
- no promotion-grade consumed witness.

All variants used the exact sovereign terminal population and no sizing,
leverage, compounding, capital weighting or volume adaptation.

## Strongest DOL2 family — 3-M1 acceptance window

`SOFT3_DOL2_ALL` improves PF and mean R in all four folds:

- R5 PF 1.9169 -> 2.0186; mean +0.7488R -> +0.8517R;
- R6 PF 2.3035 -> 2.4057; mean +1.1097R -> +1.1967R;
- R8 PF 2.6708 -> 2.9625; mean +1.3291R -> +1.5611R;
- consumed PF 1.0464 -> 1.1446; mean +0.0406R -> +0.1297R.

Winner-R is >=100% in R6/R8/consumed and 107.8% in R5, but one R5
baseline winner is not preserved as a winner.

The blocking defect is drawdown / sequence risk:

- consumed DD 13.834R -> 16.800R;
- consumed MC p95 DD 30.296R -> 32.550R;
- R5 MC positive probability also falls slightly.

Therefore the capacity is economically useful but the post-acceptance journey
needs protection.

## Full-cognition selector alone is insufficient

`SOFT3_DOL2_FULL_COGNITION` still raises consumed DD to 16.8R.

Entry/acceptance-time cognition alone cannot solve post-acceptance giveback.
The next decision must occur after the journey evolves.

## DOL3 clue

`SOFT1_DOL3_ALL` is also informative:

- consumed PF 1.0464 -> 1.2298;
- consumed mean +0.0406R -> +0.2011R;
- consumed MC p95 DD improves 30.296R -> 28.883R;
- winner count / winner-R = 100% / 117.5%.

But R6 PF and mean degrade slightly, so it is not cross-fold promotable.

## Next causal repair

The calibration plan already recorded whether price closes back inside DOL1
after acceptance. V3 will use that event causally.

The target remains W3 DOL2 because it showed PF/mean non-degradation 4/4.

After DOL1 acceptance and before DOL2:

- a fully closed M1 back inside DOL1 becomes a **reloss observation**;
- the control exits immediately at that close;
- the full-cognition variant rebuilds the live Situation Model and current
  position reasoning at that close;
- continuation is preserved only when full cognition still says EXECUTE and
  post-1R persistence remains PERSISTENT or RECOVERED;
- otherwise exit at the causal close.

No future DOL2 reach label is used.

No fresh holdout, freeze, promotion, merge, LIVE or real-capital authority.

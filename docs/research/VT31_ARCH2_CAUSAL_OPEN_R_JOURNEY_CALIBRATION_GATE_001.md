# VT31 NAS100 — Causal Open-R Journey Calibration Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / PURE-EDGE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Defect

The live Breaker cognition frontier proved that pre-DOL1 cognition is effectively
degenerate: almost every causal protective-swing observation is scored
SUPPORTIVE / LOW protection urgency even while maximum-intelligence blockers
remain active.

The missing causal input is the trade's current journey location relative to the
frozen initial risk. VT31 currently knows structure, regime, volatility,
liquidity, timing and path quality, but the Situation Model does not expose the
current open-R of the live trade.

That prevents the trader from distinguishing a healthy pullback from a position
that has materially deteriorated before DOL1.

## Sovereign interpretation

R is strategy-native geometry and is explicitly allowed during certification.

`current_open_r` is therefore permitted provided it is computed only from:

- frozen entry price;
- frozen initial structural stop / risk distance;
- current fully closed causal price;
- trade side.

It may not consume:

- position size;
- volume;
- account equity;
- monetary PnL;
- leverage;
- compounding;
- portfolio weighting;
- future bars;
- terminal trade result.

## Predeclared journey bands

These bands are fixed before the replay:

- `current_open_r <= -0.50R`: MATERIAL_ADVERSE, strong caution;
- `-0.50R < current_open_r < 0R`: ADVERSE, moderate caution;
- `0R <= current_open_r < +0.50R`: NEUTRAL;
- `+0.50R <= current_open_r < +1R`: FAVORABLE_PROGRESS, support;
- `current_open_r >= +1R`: STRONG_FAVORABLE_PROGRESS, stronger support.

The bands are universal journey semantics, not outcome-derived labels.

## Maximum-intelligence semantics

For a live post-entry observation:

- `current_open_r` must be available;
- its absence is a maximum-intelligence blocker;
- pre-DOL1 future continuation remains unknowable and must not be fabricated;
- however, the *current* journey is observable and must not be mislabeled as
  uncalibrated merely because future DOL persistence is unknown.

Target-depth knowledge is distinct from live journey state:

- DOL2 has calibrated economic capacity only when cognition selects it;
- DOL3 is rejected in the current architecture;
- neither fact predicts the future path of the current trade.

## Experiment governance

The next replay may compare the same fixed A+B candidate with and without
causal open-R cognition. Require cross-fold PF/mean/DD non-degradation,
winner-count >=80%, winner-R >=90%, temporal stability and the sovereign
observed-DD <=6R gate.

No sizing, dynamic sizing, leverage, compounding, capital weighting, fold
identity, outcome oracle or fresh holdout is permitted.

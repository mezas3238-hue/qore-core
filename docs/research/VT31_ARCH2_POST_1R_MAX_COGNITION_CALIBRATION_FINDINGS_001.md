# VT31 NAS100 — Post-1R Maximum Cognition Calibration Findings 001

**Owner:** Sergio Meza
**Status:** STABLE 5-M1 JOURNEY SEPARATION FOUND / ECONOMIC POLICY NOT YET PROMOTED
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Evidence

Workflow:
- run `37403585235`
- head `4567a7122780f43c9fb9206f364668d0b5aa8239`
- conclusion **SUCCESS**

Exact sovereign specialist populations:
- R5: 54 trades
- R6: 37
- R8: 33
- recent consumed 2Y: 48

Observed post-1R research rows:
- R5: 98
- R6: 46
- R8: 55
- consumed: 76

The horizons were predeclared at 2, 3, and 5 fully closed M1 bars after the first unambiguous +1R touch. Future journey class is research-only and never a runtime input.

## Stable mechanism at 5 closed M1

### PERSISTENT_1R_FLOOR

Eventual 3R+ rate:
- R5: 100% (11)
- R6: 100% (5)
- R8: 100% (7)
- consumed: 80% (10)

Giveback-after-1R:
- R5: 0%
- R6: 0%
- R8: 0%
- consumed: 20%

This is a strong continuation state. A generic BE rule should not cut it.

### RECOVERED_1R_FLOOR

Eventual 3R+:
- R5: 100% (10)
- R6: 80% (5)
- R8: 100% (4)
- consumed: 100% (3)

Giveback:
- R5: 0%
- R6: 20%
- R8: 0%
- consumed: 0%

Recovery back above the 1R floor is runner-supportive.

### POSITIVE_BELOW_1R

Giveback-after-1R:
- R5: 55.56% (9)
- R6: 33.33% (3)
- R8: 60% (5)
- consumed: 80% (10)

Eventual 3R+:
- R5: 33.33%
- R6: 66.67%
- R8: 40%
- consumed: 20%

This is a deterioration/caution state, but not deterministic failure. It requires an economic protection frontier rather than blind exit.

### ENTRY_OR_WORSE

Across all four partitions:
- sample: one observation per partition;
- eventual 3R+: 0% in 4/4;
- giveback-after-1R: 100% in 4/4.

The mechanism is consistent but sample is tiny. It is eligible only for conservative consumed-evidence testing.

## Architectural conclusion

Entry-time cognition alone is too coarse to decide protection. Maximum intelligence requires post-entry causal reassessment.

Next economic frontier at H5:
- PERSISTENT -> HOLD / preserve runner;
- RECOVERED -> HOLD / preserve runner;
- POSITIVE_BELOW_1R -> test BE/protection;
- ENTRY_OR_WORSE -> test causal close/protection.

No sizing, leverage, compounding, capital weighting, volume decision, fresh holdout, policy promotion, freeze, LIVE or real-capital authority.

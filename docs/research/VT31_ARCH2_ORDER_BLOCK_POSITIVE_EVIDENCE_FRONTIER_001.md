# VT31 NAS100 — Order Block Positive Evidence Frontier 001

**Owner:** Sergio Meza  
**Status:** CONSUMED-EVIDENCE DEVELOPMENT / NO PROMOTION  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Rationale

A full Order Block veto improves recent PF but destroys useful historical
trades and fails the predeclared 75% density floor in R6.

After the robust filters for expanded reference volatility and Order Block
entry age 0-2m, the remaining historical Order Block winners share a stronger
causal profile:

- SHORT;
- entry evidence approximately 14 minutes old;
- reference reclaim approximately 15 minutes old.

Recent remaining Order Blocks are losses and do not satisfy the same combined
profile.

## Predeclared development variants

All variants retain the expanded-reference ABSTAIN and then require one of:

1. Order Block must be SHORT;
2. Order Block entry-evidence age >= 11m;
3. Order Block must be SHORT and entry-evidence age >= 11m;
4. Order Block must be SHORT and reclaim age >= 15m.

These are positive-evidence requirements, not sizing or capital rules.

## Adjudication

Replay R5 / R6 / R8 / recent consumed with the B comparator fixed.

Require:

- PF non-degrading 4/4;
- mean-R non-degrading 4/4;
- DD non-degrading 4/4;
- density >=75% 4/4;
- winner floors;
- temporal stability;
- Monte Carlo;
- sovereign observed-DD direction toward <=6R.

Because the hypotheses were learned from consumed evidence, no survivor is
promotion evidence by itself.

Fresh holdout remains sealed.

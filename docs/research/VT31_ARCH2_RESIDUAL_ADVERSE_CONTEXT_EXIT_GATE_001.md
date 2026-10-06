# VT31 NAS100 — Residual Adverse Context Exit Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Fixed base

The current strongest development base is:

`COG_EXIT_CAUTION_OR_STALE_MIXED`

on top of:

- admission `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- H3;
- W5 soft-DOL1;
- full-cognition DOL2;
- post-acceptance PS2;
- live maximum-cognition reassessment;
- material-adverse state `current_open_r <= -0.50R`.

This base is a 4/4 development survivor with 100% winner/winner-R preservation.
Recent consumed reaches approximately PF 1.657 and observed DD 9.34R.

## Residual forensic findings

Outcome attribution remains observation-only and has zero runtime authority.

At the **first material-adverse observation**, after applying the current base:

### FVG + non-SHALLOW destination

Across R5/R6/R8/recent:

- R5: 7 losses / 0 winners;
- R6: 2 losses / 0 winners;
- R8: 2 losses / 0 winners;
- recent: 5 losses / 0 winners.

Total: **16 losses / 0 winners**.

The one R5 FVG recovery that reached the material-adverse state was
`destination_state=SHALLOW`, so SHALLOW is explicitly preserved.

### Normal reference + non-Order-Block

Across folds where this class occurs:

- R5: 3 losses / 0 winners;
- R8: 7 losses / 0 winners;
- recent: 5 losses / 0 winners;
- R6: no non-Order-Block member in this class.

The R6 material-adverse normal-reference winner is an Order Block and is
explicitly excluded from this hypothesis.

Total observed class: **15 losses / 0 winners**.

## Why these are development hypotheses, not promotion evidence

Both classes were discovered on consumed evidence.

No result from this frontier may be used as independent promotion evidence.
Fresh holdout remains sealed.

The states themselves are causal and pre-existing:

- entry evidence family;
- full-cognition destination state;
- reference volatility state;
- material adverse open-R;
- maximum cognition verification.

No new numeric threshold is introduced beyond the already-frozen -0.50R
material-adverse floor.

## Predeclared variants

1. `BASE_SAFE`
   - CAUTIOUS, or
   - MIXED + reclaim age 8..14m.

2. `BASE_PLUS_FVG_NONSHALLOW`
   - BASE_SAFE, or
   - entry family FVG + destination state != SHALLOW.

3. `BASE_PLUS_NONOB_NORMAL`
   - BASE_SAFE, or
   - frozen entry reference volatility = normal + entry family != Order Block.

4. `BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL`
   - union of all three causal conditions.

All additional exits still require:

- maximum cognition verified;
- current open-R <= -0.50R;
- fully closed causal M1;
- execution at the next M1 open;
- no DOL1 ownership conflict.

## Frozen adjudication

Across R5/R6/R8/recent:

- PF non-degrading 4/4;
- mean-R non-degrading 4/4;
- observed DD non-degrading 4/4;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrading.

Owner direction:

- combined/recent PF >=1.70 target;
- expectancy >=+0.15R;
- observed DD <=6R hard gate;
- MC positive >=90%;
- MC p95 DD <=15R.

No sizing, leverage, compounding, capital weighting, fresh holdout, candidate
freeze, LIVE, real capital or production authority.

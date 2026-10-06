# VT31 NAS100 — Live Cognitive Breaker Protection Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Problem

The current strongest A+B development stack is:

- admission: `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- H3 full-cognition post-1R management;
- W5 soft-DOL1;
- full-cognition DOL2;
- post-acceptance PS2.

Recent consumed economics are approximately PF 1.5537, mean +0.449R and
observed DD 10.57R. The sovereign certification gate is observed DD <=6R.

Universal Breaker PS1/PS2 is rejected. It can compress DD in some eras, but it
cuts too much winner-R and degrades recent Monte Carlo. Static entry-time M15
selection is a separate comparator, not the desired final architecture.

## Hypothesis

A protective swing should not itself force a stop move.

At the fully closed M1 where an improving Breaker protective swing becomes
eligible, VT31 must rebuild the live causal Situation, rerun `reason_position()`,
run the full cognitive synthesis, and let the existing market-native position
decision decide HOLD vs TRAIL.

The existing runtime already contains a winner-preservation veto:

- LOW protection urgency -> HOLD;
- MODERATE/HIGH urgency + causal momentum deterioration + improving structural
  swing -> TRAIL.

## Predeclared variants

- `CONTROL`: current A+B stack, no extra pre-DOL1 Breaker protection.
- `COG_SWING_PS1`: first improving closed-M1 Breaker swing becomes a
  protection opportunity; full live cognition decides HOLD/TRAIL.
- `COG_SWING_PS2`: same after two confirmed improving swings.
- `COG_WEAK_PATH_PS1`: PS1 plus market-native deterioration must be present
  using VT31's already-frozen weak-path definitions:
  - recent path efficiency <=0.30, or
  - recent overlap rate >=0.75.
- `COG_WEAK_PATH_PS2`: same after two confirmed improving swings.

The 0.30 / 0.75 thresholds are not newly outcome-tuned here; they already exist
inside VT31 full position cognition as weak-efficiency / high-overlap states.

## Causal reconstruction at every protection decision

Only information closed by the decision timestamp may be used:

- H4;
- H1;
- M15;
- premarket;
- cash open;
- path/range state;
- reference volatility;
- raid depth;
- recent path efficiency;
- recent overlap;
- reference reclaim state/age;
- latest structure event/age;
- frozen entry evidence and geometry;
- frozen strategy/CIBO/trader memories;
- current reasoning;
- full position cognition.

No future bar, terminal PnL, fold identity, date-specific outcome label, volume,
sizing, leverage, compounding, portfolio allocation or capital weighting may
authorize protection.

## Frozen adjudication

Across R5, R6, R8 and recent consumed require:

- PF non-degrading;
- mean-R non-degrading;
- observed DD non-degrading;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrading.

Recent owner-direction gates remain:

- PF >=1.50;
- mean >=+0.15R/trade;
- observed DD <=6R;
- MC positive terminal >=90%;
- MC p95 DD <=15R.

This is consumed-development evidence only. Even a survivor cannot open fresh
holdout or certify VT31. Any remaining maximum-intelligence blockers must be
closed causally before candidate freeze.

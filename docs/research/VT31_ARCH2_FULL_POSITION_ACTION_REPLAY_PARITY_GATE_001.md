# VT31 NAS100 — Full PositionAction Replay Parity Gate 001

**Status:** PREDECLARED SEMANTIC-PARITY REPAIR / ZERO ECONOMIC AUTHORITY  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Problem

The canonical post-entry runtime returns a full
`MarketNativePositionDecision` with the action surface:

- HOLD;
- TRAIL;
- EXTEND;
- EXIT.

The current research live-cognition adapter collapses that result to one
boolean:

`decision.position.action is PositionAction.TRAIL`.

That representation is sufficient for a trail-only caller but is not sufficient
for replay/runtime semantic parity. A runtime EXIT or EXTEND can be computed
correctly and still disappear before it reaches the research simulator.

## Repair allowed by this gate

Refactor the live-cognition adapter so it exposes the complete
`PostEntryCognitiveDecision` to research callers.

Keep the existing trail-only helper as a compatibility wrapper whose behaviour
is byte-for-byte equivalent in meaning:

- return true only for `PositionAction.TRAIL`;
- return false for HOLD / EXTEND / EXIT.

No market fact changes are authorized in this repair.

In particular, this gate does **not** authorize changing the current values of:

- `structure_invalidated`;
- `liquidity_failure_confirmed`;
- `regime_changed_against_thesis`;
- `momentum_deteriorated`.

## Required tests

1. The compatibility helper must still authorize TRAIL and only TRAIL.
2. The full-decision helper must preserve EXIT without converting it to a
   boolean.
3. The full-decision helper must preserve reason, next stop and next target.
4. Existing position-intelligence and post-entry-runtime tests must remain
   green.
5. No economic replay is needed to validate this refactor because the frozen
   Comparator-009 policy is unchanged.

## Governance

- semantic repair only;
- no outcome/fold/date authority;
- no new threshold;
- no sizing, leverage, compounding, portfolio or capital weighting;
- Fresh Holdout remains sealed;
- no policy promotion;
- no certification claim;
- no LIVE / real-capital / production authority.

# VT31 NAS100 — Full PositionAction Replay Parity Findings 001

**Status:** SEMANTIC INTERFACE REPAIR CLOSED / ECONOMIC POLICY UNCHANGED  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Repair

The research live-cognition adapter now exposes the complete
`PostEntryCognitiveDecision` returned by the canonical runtime.

The previous trail-only helper remains as a compatibility wrapper and still
returns true only when:

`decision.position.action is PositionAction.TRAIL`.

Therefore existing trail and adverse-exit policy semantics remain unchanged,
while future research callers can now observe the complete runtime decision
surface:

- HOLD;
- TRAIL;
- EXTEND;
- EXIT.

No market facts or trading thresholds were changed.

## Verification

Two workflows that consume the repaired adapter completed successfully:

- `37534189559` — QORE VT31 Live Cognitive Breaker Protection Frontier V1 —
  SUCCESS;
- `37534189523` — QORE VT31 Adverse Journey Cognitive Exit Frontier V1 —
  SUCCESS.

This closes the information-loss defect at the adapter interface.

## Remaining parity blocker

The full action can now be preserved, but three market-native runtime facts are
still hard-coded false in the research adapter:

- `structure_invalidated`;
- `liquidity_failure_confirmed`;
- `regime_changed_against_thesis`.

Those facts require separately predeclared causal constructors before they may
change economics.

A reusable post-entry fact ledger is being built in the independent GitHub
Trader Lab to evaluate those constructors without repeated M1 reconstruction.

## Governance

- semantic repair only;
- Comparator 009 economics unchanged;
- no sizing, leverage, compounding, portfolio or capital weighting;
- no Fresh Holdout access;
- no certification, LIVE, real-capital or production authorization.

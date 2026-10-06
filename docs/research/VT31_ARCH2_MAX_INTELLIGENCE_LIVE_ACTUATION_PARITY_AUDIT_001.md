# VT31 NAS100 — Maximum-Intelligence Live Actuation Parity Audit 001

**Status:** OPEN BLOCKER / OBSERVATION-ONLY AUDIT  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Purpose

Record a research/runtime parity blocker discovered while reconstructing the
stitched drawdown. This document grants no new trading authority and changes no
economic policy.

## Existing runtime capability

The production-side post-entry contract
`PostEntryMarketFacts` already exposes market-native facts for:

- `structure_invalidated`;
- `liquidity_failure_confirmed`;
- `momentum_deteriorated`;
- `regime_changed_against_thesis`.

`decide_market_native_position()` gives immediate position authority to
confirmed structural invalidation and other market-native failure states. The
runtime unit tests explicitly lock structural invalidation to
`PositionAction.EXIT` with reason
`STRUCTURAL_INVALIDATION_CONFIRMED`.

## Replay wiring gap

The research live-cognition adapter
`scripts/vt31_nas100_live_cognitive_breaker_protection_frontier_v1.py`
currently constructs `PostEntryMarketFacts` with:

- `structure_invalidated=False`;
- `liquidity_failure_confirmed=False`;
- `regime_changed_against_thesis=False`;

for every live post-entry reevaluation.

Only `momentum_deteriorated` is causally reconstructed there.

Therefore the research replay does not currently prove that the same
market-native facts available to the runtime contract are constructed and
actuated in replay.

## Action-shape gap

The same adapter reduces the complete market-native position decision to:

`authorized = decision.position.action is PositionAction.TRAIL`.

That boolean is suitable for a trail authorizer but is not a lossless
representation of the full `HOLD / TRAIL / EXTEND / EXIT` decision surface.

The separate adverse-exit research wrapper then re-authorizes EXIT using its
own Comparator-003/009 diagnostic predicates. Consequently:

> a future market-fact-driven `PositionAction.EXIT` from the shared runtime
> decision cannot be assumed to execute in the research composite merely
> because `reassess_and_decide_post_entry()` returned EXIT.

This must be closed before final replay/runtime semantic parity can pass.

## Reason-position observation

Across the currently retained Comparator-009 post-entry diagnostic traces,
`current_reasoning_action` remains `EXECUTE` throughout the recorded live
adverse reevaluations.

This is not sufficient evidence by itself that `reason_position()` is wrong.
Comparator 009 already has a separate H3 post-1R management path that computes
the calibrated persistence states:

- `PERSISTENT_1R_FLOOR`;
- `RECOVERED_1R_FLOOR`;
- `POSITIVE_BELOW_1R`;
- `ENTRY_OR_WORSE`.

The H3 path maps them to already-defined extension states including
`CALIBRATED_POST1R_CONTINUATION_DEPLETED`, which
`reason_position()` can treat as a position-authoritative contradiction.

Therefore the next parity repair must avoid double-applying H3. The problem is
not permission to add another H3 exit.

## Required closure before candidate freeze

1. Identify or implement canonical causal constructors for
   `structure_invalidated`, `liquidity_failure_confirmed`, and
   `regime_changed_against_thesis` using only fully closed market data.
2. Prove their timestamps do not use the same bar open after inspecting its
   close and do not use future bars.
3. Route the complete `PositionAction` result through the replay composite
   without collapsing it to a TRAIL-only boolean.
4. Preserve priority among already-authorized cognitive EXIT, structural stop,
   target, and protective actions.
5. Add integration tests showing one causal market-fact EXIT reaches execution
   at the next valid M1 open.
6. Prove research decision == runtime decision for identical causal input.
7. Re-run the frozen economic gates only after the parity semantics are
   predeclared; do not define market facts from known terminal losers.

## Non-permitted shortcut

Do not equate:

- initial stop touch with an earlier structural invalidation;
- terminal loss with liquidity failure;
- a known losing date with a regime change;
- a favorable counterfactual result with causal confirmation.

A canonical fact must exist before terminal outcome is known.

## Governance

- observation only;
- no new thresholds;
- no policy promotion;
- no sizing, leverage, compounding, portfolio or capital engineering;
- Fresh Holdout remains sealed;
- Comparator 009 remains the economic baseline until a separately
  predeclared successor passes all gates;
- VT31 remains not certified.

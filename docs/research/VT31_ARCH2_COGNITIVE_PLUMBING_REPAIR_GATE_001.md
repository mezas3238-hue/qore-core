# VT31 — Cognitive Plumbing Repair Gate 001

**Status:** PREDECLARED CONSUMED-EVIDENCE REPAIR  
**Baseline:** COMP009  
**Fresh Holdout:** SEALED

This gate repairs three sensor-confirmed plumbing defects without changing any
certification threshold.

## A. H4 readiness

H4 is a declared cognitive domain. When `h4_state == unavailable`,
maximum-intelligence readiness must expose:

`H4_CONTEXT_UNAVAILABLE`.

No market threshold is added. Because existing pretarget exits require
`maximum_cognition_verified`, the economic effect must be measured rather than
assumed.

## B. 10-minute liquidity count

`recent_liquidity_event_count_10m` is currently None on every observed call.

Populate it from the already-existing causal closed-M1 structure event stream.
Count only:

- `reference-liquidity-sweep`;
- `local-liquidity-sweep`;

with `observed_at` inside the existing trailing 10-minute field window ending
at the decision timestamp.

Use the same constructor at entry and post-entry. PD-array touches do not count
as liquidity sweeps.

## C. PositionAction parity

The sensor audit found canonical `PositionAction=HOLD` on every call while
the frozen COMP003/COMP009 pretarget policy routed 28 EXIT decisions.

Expose the already-frozen pretarget exit through one effective PositionAction
surface and prove trade-by-trade equality with the current control. This repair
may not broaden or narrow the frozen exit policy.

## Evaluation

Run only R5/R6/R8/recent consumed. Report changed decision/trade counts,
maximum-cognition counts, blockers, PositionAction distribution, routing
alignment, per-fold economics, stitched DD, frozen Sharpe/Sortino and winner
preservation.

Correctness is fail-closed: if truthful readiness changes economics, do not
restore the old result by weakening the audit.

The parallel architect owns sensors/constructors for
`structure_invalidated`, `liquidity_failure_confirmed` and
`regime_changed_against_thesis`.

No sizing, leverage, compounding, capital weighting, fold/date/outcome authority
or Fresh Holdout access.

VT31 remains **NOT CERTIFIED**.

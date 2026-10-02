# CIBO GENERAL CHAIN AUDIT & REPAIR V1

Checkpoint branch: `agent/cibo-integrator-ab-001`

Purpose: canonical running audit of critical CIBO chain defects, repairs and remaining certification blockers. This document grants no merge, LIVE, production, real-capital or certification authority.

## Severity P0

### P0-01 — DEMO broker mutation could bypass explicit QORE Risk authorization

Observed before repair:

`CTraderDemoFreeSink.submit(..., risk_authorization=None)` could continue through allocation-only fencing and reach `submit_authorized()`.

The operational cTrader DEMO runtime called `submit_demo_request(request)` without a RiskAuthorization and reported `account_wide_risk_active=False`.

Repair staged on #670:

- `CTraderDemoFreeSink.submit` now requires canonical `RiskAuthorization`.
- `submit_demo_request` now requires explicit `RiskAuthorization`.
- allocation-only fallback fence removed from the broker mutation path.
- runtime routes direct CIBO DEMO submissions through `authorize_phase20_demo_request`.
- runtime creates a current `AccountRiskSnapshot` from provider account equity/free margin plus registry-confirmed open and pending stop risk.
- telemetry now declares QORE Risk as `SOVEREIGN_HARD_GOVERNOR`.
- regression tests prove `risk_authorization=None` cannot stage or submit a broker mutation.

Scientific/operational law after repair:

`Trader opportunity -> CIBO sizing -> QORE Risk ALLOW/REDUCE/REJECT -> DEMO sink -> broker`.

No RiskAuthorization = no broker mutation.

### P0-02 — Phase22 V2 one-shot consumed but qualification INVALID

Canonical candidate:
`CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2`

Canonical truth:

- one-shot: `CONSUMED`
- outcomes_emitted: true
- qualification: `INVALID`
- fresh_oos_terminal_ready: false
- rerun_authorized: false
- selected: 0
- settled: 0

Forensics identify a Turtle fresh-window propagation defect in five lanes. The consumed V2 population may not be regenerated or replayed as fresh.

Repair/governance already present:

- consumed V2 remains immutable.
- no second V2 fresh execution is authorized.
- successor V3 is preregistered but NOT_READY pending new evidence and Owner authorization.

## Severity P1

### P1-01 — CI GREEN is not certification GREEN

At audited checkpoint the canonical ledger contains 64 mandatory workstreams:

- 16 COMPLETED_AND_PROVEN
- 3 FALSIFIED_AND_CLOSED
- 2 SUPERSEDED_WITH_PROVEN_LINEAGE
- 41 EXTERNAL_DEPENDENCY_BLOCKED
- 2 OPEN

The two OPEN workstreams are:

- FINAL_INTEGRATED_CIBO_EXAM
- WORLD_CUP_MAXIMUM_CAPABILITY_EXAM

All 41 EXTERNAL_DEPENDENCY_BLOCKED workstreams remain certification-blocking.

### P1-02 — Source-of-Truth reconciliation can lag live producer branches

The integrated acceptance checkpoint referenced producer heads older than live PR heads.

Observed live drift at audit time:

- Architect A #660: 67 commits ahead of the reconciled checkpoint.
- Architect B #661: 141 commits ahead of the reconciled checkpoint.

Repair staged:

`QORE CIBO Source of Truth Reconciliation` now queries the live PR heads for #660/#661 and fails on any unreconciled producer-head drift.

Updating only a SHA is forbidden. Child deltas must first be absorbed, deliberately overridden, superseded or otherwise accounted.

### P1-03 — terminal_count can overstate scientific closure

`EXTERNAL_DEPENDENCY_BLOCKED` is a terminal administrative disposition but remains certification-blocking. Therefore `terminal_count` must never be interpreted as certified/proven count.

### P1-04 — FRESH_OOS semantic distinction

Phase22 V2 FRESH_OOS is scientifically INVALID and non-terminal for qualification, while the master ledger administratively classifies it as EXTERNAL_DEPENDENCY_BLOCKED.

The certification gate remains blocked, but reporting must preserve the distinction:

`administratively classified != scientifically terminal qualification`.

## Positive controls verified

- Trader opportunity envelope carries no sizing authority.
- CIBO CMA owns requested volume.
- CMA-to-Risk request sets `strategy_requested_risk_usd=None`.
- QORE Risk remains independent ALLOW/REDUCE/REJECT governor.
- Integrated Capital Truth rejects cross-ledger double counting.
- consumed Phase22 V2 cannot be reopened by READY-era tests.
- no repair in this audit grants LIVE, FundedNext LIVE, production, real capital or merge authority.

## Next audit/repair fronts

1. Reconcile live A/B deltas against #670 without blind SHA promotion.
2. Audit VT31 execution path for identical sovereign Risk enforcement.
3. Audit Risk reservation lifecycle: reservation -> fill -> reconciliation -> release.
4. Audit T20 release lineage against real authoritative lifecycle.
5. Audit Phase20D population production versus the 41 external blockers.
6. Audit Compound/Integrated Capital Truth real-population bindings.
7. Audit PRE_EXAM/USD60 distinction between software-gate PASS and scientific readiness.
8. Audit Final Integrated Exam and World Cup receipt completeness.

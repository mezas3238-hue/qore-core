# VT31 NAS100 — Comparator 010 Neutral-Destination Adverse Exit Findings 001

**Status:** FALSIFIED BEFORE REPLAY / NO-OP AGAINST COMPARATOR 009  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Fresh Holdout:** SEALED

## Purpose

Audit the predeclared Comparator 010 hypothesis before spending a replay and
before adding any runtime authority.

The audit uses only the already-consumed Comparator-009 candidate rows and
their fully closed-M1 `cognitive_exit_evaluations` from the final pre-holdout
metric pack.

## Exact result

The proposed state was:

- entry family Breaker or FVG;
- maximum cognition verified;
- `current_open_r <= -0.50R`;
- `management_context == MIXED`;
- `destination_state == NEUTRAL`.

Across the current 109-trade Comparator-009 consumed population, there are
exactly 13 trades whose traces contain that state:

- Breaker: 8;
- FVG: 4;
- Order Block: 1.

The 12 Breaker/FVG trades are all losses, but every one of those 12 events
already has:

- `comp007_base_exit_authorized == true`;
- `cognitive_exit_authorized == true`.

Therefore the proposed Comparator-010 authorization adds **zero new
actuation**. It is already subsumed by the existing Comparator-003/007 adverse
exit stack carried into Comparator 009.

The thirteenth state is the excluded Order Block trade on 2018-12-20. It is a
large winner of approximately +5.8856R and correctly has the existing base
exit unauthorized.

## Adjudication

`BREAKER_FVG_NEUTRAL_DESTINATION_ADVERSE_EXIT` is rejected before replay as
a redundant no-op.

No workflow is warranted because a correctly implemented replay must reproduce
Comparator 009 exactly.

This result also corrects the discovery wording in the predeclaration: the
Breaker/FVG state was observable, but it was **not unused runtime authority**.
It was already being acted on by the frozen adverse-exit stack.

## Separate stitched-DD observation

An independent entry-only categorical counterfactual was also checked as
observation only:

1. Breaker LONG + bullish cash-open; or
2. Breaker + H4 bearish + H1 bearish.

The union removes 11 current losses and no current winners, but under the
already-frozen metric convention it still produces approximately:

- stitched DD: 6.0695R — FAIL;
- annualized Sharpe: 1.3403 — FAIL.

It is therefore not promoted and is not allowed to become Comparator 010/011
merely because it improves PF.

## Root-cause signal that remains live

Inside the exact stitched 2022-02-08 -> 2023-05-01 drawdown, multiple Breaker
losses first achieved material favorable excursion and then gave the progress
back before terminating negative. Examples from the fully causal
Comparator-009 trace include maximum observed open-R near:

- +1.96R on 2022-03-24;
- +5.07R on 2022-05-19;
- +1.85R on 2022-06-23;
- +1.26R on 2022-08-04;
- +2.27R on 2022-10-31;
- +5.26R on 2023-04-17.

This supports testing the already-existing Deep Giveback mechanism rather than
inventing another adverse-state exit.

## Governance

- consumed evidence only;
- dates are forensic labels only and never runtime authority;
- no outcome oracle may enter policy;
- no sizing, leverage, compounding, portfolio or capital weighting;
- no new numeric threshold created here;
- Fresh Holdout remains sealed;
- VT31 is not certified;
- no LIVE, real-capital or production authority.

# VT31 NAS100 — Target-Depth Economic Frontier Plan 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / DO NOT RUN UNTIL CALIBRATION WITNESS EXISTS  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Purpose

If the consumed target-depth calibration produces a valid DOL2 and/or DOL3
witness, test whether extending the sovereign VT31 winner actually improves
economic edge.

## Fixed population

Use the exact sovereign specialist admission and terminal population on:

- R5;
- R6;
- R8;
- recent consumed 2Y.

No admission, entry, initial invalidation, lifecycle, volume, sizing, leverage,
compounding or capital weighting changes.

## Causal extension decision

DOL1 touch is not enough.

Extension can become eligible only after:

1. DOL1 is touched;
2. a subsequent fully closed M1 closes beyond DOL1 in trade direction;
3. any required predeclared full-cognition state existed causally no later than
   that acceptance close.

No future DOL2/DOL3 reach label may select the runtime action.

## Soft-DOL1 acceptance windows

The calibration showed non-constant touch-to-acceptance latency. To avoid
post-hoc selection, test the following windows in parallel:

- 1 fully closed M1 after DOL1 touch;
- 3 fully closed M1 after DOL1 touch;
- 5 fully closed M1 after DOL1 touch.

Within a window:

- the original structural invalidation remains active;
- DOL1 is a soft checkpoint, not a hard TP;
- acceptance occurs only when a closed M1 finishes beyond DOL1;
- if the window expires without acceptance, exit at that causal close;
- if accepted, the extension target becomes active only from the next M1.

No post-acceptance target hit on the acceptance bar is credited.

## Economic variants

Always include:

- `DOL1_EXIT_BASELINE`

If DOL2 calibration passes, for each 1/3/5-M1 acceptance window:

- `ACCEPTED_DOL1_EXTEND_DOL2_ALL` control;
- `ACCEPTED_DOL1_EXTEND_DOL2_FULL_COGNITION`.

The full-cognition variant re-runs live-position reasoning at the accepted
close and extends only when the integrated cognition supports continuation.

If DOL3 calibration passes, for each 1/3/5-M1 acceptance window:

- `ACCEPTED_DOL1_EXTEND_DOL3_ALL` control;
- `ACCEPTED_DOL1_EXTEND_DOL3_DEEP_COGNITION`.

DOL3 cognition requires DOL1 acceptance plus a continuation-supportive live
journey state. It is research-only until cross-fold economics survive.

The whole position follows the selected market-management policy. The policy
must be executable independently of absolute volume.

## Protection

Structural-protection variants may use only information available after DOL1
acceptance:

- confirmed M1 protective swing;
- current full cognition;
- regime / volatility / H1 / M15 / M1 journey;
- strategy-native R if predeclared.

No outcome labels.

## Gates

A candidate extension must satisfy all of:

- identical terminal population;
- PF non-degrading in 4/4 preferred, minimum 3/4 only for further research;
- mean-R non-degrading in 4/4 preferred;
- DD non-degrading in at least 3/4;
- winner-count preservation >= 80% every fold;
- winner-R preservation >= 90% every fold;
- no negative half-year mean-R delta in R5/R6/R8 for promotion;
- Monte Carlo must not materially worsen;
- recent consumed 2Y must improve or remain non-degrading.

Passing consumed gates is research survival only. It does not open fresh
holdout or certify the candidate.

## Governance

R is allowed as trader logic. Sizing to obtain certification is forbidden.

No merge, fresh holdout, LIVE, real-capital or production authority.

# VT31 NAS100 — Target-Depth V2 Zero-Extension Supersession 001

**Owner:** Sergio Meza  
**Status:** FIRST V2 AGGREGATE SUPERSEDED AS TARGET-DEPTH EVIDENCE  
**Run:** `37441800341` — SUCCESS  
**Head:** `3bf320819f0dfa3bfde855af17422f4159c08973`

## Finding

The first economic V2 aggregate reported:

- `SOFT5_DOL2_FULL_COGNITION` as a research survivor;
- `SOFT5_DOL3_FULL_COGNITION` as a research survivor.

However both variants had:

- total DOL1 acceptances: 26;
- total cognition-declined acceptances: 26;
- **actual extension activations: 0**.

Therefore their economic improvement came from soft-DOL1 banking / timeout
behavior, not from DOL2 or DOL3 extension.

## Root cause

At DOL1 acceptance the research harness supplied
`dol1_acceptance_observed=True`, but the live Situation Model still carried
the old DOL1 state rather than an accepted/reached DOL1 state.

The target-intent engine correctly requires both:

- causal DOL1 reached/accepted state;
- acceptance observation.

Without both, `EXTEND_TO_DOL2` could not be emitted.

## Correction

The corrected harness:

1. replaces the causal current Situation state with
   `REACHED_ACCEPTED_CLOSED_M1` at the acceptance close;
2. reruns `reason_position()` on that exact state;
3. recomputes full position cognition;
4. allows target extension only from the next M1;
5. requires `extension_activated_total > 0` before any target-depth variant
   may be called a research survivor.

## Scientific treatment

Run `37441800341` remains useful evidence about soft-DOL1 management.

It is **not** evidence that full cognition successfully selected DOL2 or DOL3.

No runtime policy, candidate freeze, fresh holdout, merge, LIVE, or real-capital
authority follows from the superseded aggregate.

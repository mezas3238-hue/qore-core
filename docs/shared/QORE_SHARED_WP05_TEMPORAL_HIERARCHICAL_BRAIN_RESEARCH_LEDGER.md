# QORE Shared WP-05 — Temporal Hierarchical Brain Research Ledger

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**Primary PR:** #635  
**Work package:** #643 — WP-05 Temporal Hierarchical Brain  
**Status:** ACTIVE / consumed development  
**Fresh holdout:** CLOSED  
**Governance:** DRAFT / no LIVE / no production / no real-capital / no merge authority

## 1. Scientific question

WP-05 asks whether local adverse pressure is only a recoverable pullback or has
become a genuine higher-timeframe structural failure.

The frozen consumed-development gate is unchanged:

- false structural-failure declaration reduction >= 2000 bps;
- terminal detection preservation >= 9500 bps;
- BOTH R6 and R5 must pass;
- R8 may be used for discovery / fit / chronological calibration only;
- R6 and R5 are consumed falsification only;
- no fresh holdout may open before a frozen candidate passes both consumed gates.

## 2. Immutable experiment chain

### V1 — single-snapshot temporal hierarchy

Authoritative run: `36249925483`  
Git SHA: `f47f4e6079c0154e29b51e9f0bd5f16acd0dac2c`  
Status: `WP05_V1_HIERARCHY_FALSIFIED`

- R6: false reduction 443 bps; terminal preservation 9886 bps.
- R5: false reduction 420 bps; terminal preservation 9861 bps.

Interpretation: strong terminal preservation, insufficient discrimination of
recoverable adversity.

### V2 — temporal propagation

Authoritative run: `36251403048`  
Git SHA: `bc78d90f137cd1cfcb8c204ee1f7819ad3280365`  
Status: `WP05_V2_PROPAGATION_MODEL_FALSIFIED`

- R6: false reduction 270 bps; terminal preservation 9887 bps.
- R5: false reduction 277 bps; terminal preservation 9887 bps.

Mechanism: source-only t-60m -> t-30m -> t propagation / resilience model.

### V3 — semi-Markov hierarchy absorption

Authoritative run: `36255882478`  
Git SHA: `73717a5fad9ad03a9459169c80b305c184b71360`  
Status: `WP05_V3_ABSORPTION_MODEL_FALSIFIED`

- R6: false reduction 1119 bps; terminal preservation 9016 bps.
- R5: false reduction 1110 bps; terminal preservation 8871 bps.

Interpretation: materially more false-declaration reduction, but terminal recall
collapsed below the frozen 95% gate.

### V4 — terminal-safe recovery veto

Authoritative run: `36258021907`  
Git SHA: `25651b0f9017fc24a6b7f57023037424db8b9d64`  
Status: `WP05_V4_RECOVERY_VETO_FALSIFIED`

- R6: false reduction 102 bps; terminal preservation 9878 bps.
- R5: false reduction 115 bps; terminal preservation 9905 bps.

V1-V4 are immutable falsification history of the original M15-oriented terminal
proxy. They must not be retroactively relabeled as Target V2 evidence.

## 3. Target semantics audit

Authoritative activation audit: `36259738096`  
Git SHA: `d7b6830d957a6dee12959236b6cef42d3b162f96`  
Status: `WP05_TARGET_CONTRACT_DIRECTIONALLY_INCONSISTENT`

The old proxy was directionally inverted against the higher-timeframe
structural-failure question on the majority of identifiable baseline episodes:

- R8 inversion: 5452 bps.
- R6 inversion: 5432 bps.
- R5 inversion: 5419 bps.

Therefore the preregistered
`HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2` contract became active for new
experiments. V1-V4 remain untouched historical evidence.

Target V2 higher-timeframe anchor:

```text
sign(mean(H1.direction, H4.direction, D1.direction))
```

Target V2 structural frontier:

```text
prior 20 closed NAS100 M1 bars
```

The next 30 closed M1 bars may mature the historical label offline only. Future
market information is forbidden from runtime cognition.

### Neutral-anchor law

`anchor == 0` means directionally unidentifiable.

It must not be interpreted as recoverable, non-terminal or safe. New
recoverable-vs-terminal experiments must abstain/exclude those episodes from
their directionally identified universe and report the count.

## 4. Corrected-target experiments

### Target V2 Absorption V1

Authoritative run: `36262640528`  
Git SHA: `e82491b1f920c885e14e491aaa840abd5fda1047`  
Status: `WP05_TARGET_V2_ABSORPTION_V1_FALSIFIED`

- R6: false reduction 1271 bps; terminal preservation 9307 bps.
- R5: false reduction 1199 bps; terminal preservation 9286 bps.

This approached the discrimination requirement more closely than V1/V2 but
still failed both the 2000-bps reduction gate and the 9500-bps terminal
preservation gate.

### V5 — Target V2 terminal-safe recovery veto

Authoritative run: `36262494942`  
Git SHA: `1d62244a4ee974b06127bfa963d112ec454570bc`  
Status: `WP05_V5_STRUCTURAL_FAILURE_V2_FALSIFIED`

- R6: false reduction 25 bps; terminal preservation 9976 bps.
- R5: false reduction 27 bps; terminal preservation 9985 bps.

Interpretation: extremely terminal-safe, but nearly incapable of separating
recoverable adversity from structural failure.

## 5. V6 — Structural Frontier Survival

Scientific hypothesis:

A model that uses the exact Target V2 structural-price coordinate plus
source-time approach, rejection, adverse persistence, volatility, cross-market
confirmation and hierarchical survival may discriminate recoverable pullbacks
without paying the recall cost seen in V3.

### Pre-outcome corrections

The first V6 implementations produced no authoritative scientific payload due to
technical defects.

A later pre-outcome audit found two semantic implementation defects before any
V6 metric was accepted:

1. exact-neutral H1/H4/D1 anchors were raising an exception instead of
   abstaining;
2. hierarchy depth/recession inherited the V4 `recovery_motif_signature()`
   coordinate, which prioritizes D1 and therefore did not guarantee the same
   anchor as Target V2.

Those defects were corrected before accepting any V6 outcome.

The active representation is:

`STRUCTURAL_FRONTIER_SURVIVAL_V2_FIXED_ANCHOR`

Frozen geometry:

- source anchor = `sign(mean(H1,H4,D1))`;
- anchor zero => abstain;
- structural frontier = prior 20 closed M1 bars;
- one fixed source anchor interprets the entire pre-source causal hierarchy
  trajectory;
- distance / approach / rejection around the exact target frontier;
- local adverse-close persistence;
- 5m/20m volatility ratio;
- SP500 / US30 adverse confirmation at 5m and 15m;
- higher-timeframe resilience minus fragility;
- fixed-anchor hierarchy penetration depth;
- fixed-anchor recession versus advance;
- bounded second-order terms / interactions;
- R8 70% chronological discovery / 30% calibration;
- threshold frozen on R8 calibration with >=98% terminal-preservation buffer;
- R6/R5 no refit and no threshold retuning.

Authoritative fixed-anchor candidate:
- Git SHA: `52dc9b0f9c8747dc3969ab0ecddc7fbbbd91f799`;
- GitHub Actions run: `36273873969`.

Its result must be recorded here only after the workflow produces a
protocol-valid payload.

## 6. Scientific governance

No WP-05 experiment may:

- weaken the 2000/9500 gate to obtain a pass;
- use R6/R5 to refit or retune the current candidate;
- use future market data at runtime;
- use terminal outcome or PnL as a runtime feature;
- use trader identity, symbol identity or setup identity as a shortcut;
- open fresh holdout before consumed-development pass;
- self-promote research knowledge;
- obtain methodology, sizing, capital-allocation, Risk, order or Execution
  authority.

If V6 fails consumed development, its exact model is frozen as falsification
history and the next experiment must use a materially different structural
hypothesis with a new identity.

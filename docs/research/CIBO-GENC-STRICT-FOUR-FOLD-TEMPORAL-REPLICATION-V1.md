# CIBO GEN-C — STRICT FOUR-FOLD TEMPORAL REPLICATION V1

Status: **PREREGISTERED / ENGINE IMPLEMENTED / REAL EVIDENCE REQUIRED**

Identity:

`CIBO_GENC_STRICT_FOUR_FOLD_TEMPORAL_REPLICATION_V1`

## Scope

This contract covers the Architect-A workstreams whose existing economic gates
did not themselves prove independent four-fold replication:

- GEN-C7 Profit Preservation;
- GEN-C8 Adaptive Compound Speed;
- GEN-C11 Multi-Period MPC;
- GEN-C12 Crisis Capital Intelligence;
- GEN-C13 Meta-Capital Memory.

GEN-C3..GEN-C6 already enforce WF1..WF4 directly in their economic gate.
GEN-C9 already has its dedicated Compound temporal replication gate.

## Law

Each treatment must independently pass its unchanged frozen economic/utility
gate on four distinct temporal populations:

```text
WF1 PASS
WF2 PASS
WF3 PASS
WF4 PASS
---------
REPLICATED
```

The following are forbidden:

- pooled rescue;
- 3/4 rescue;
- weighted compensation;
- post-outcome winner selection;
- treatment identity drift;
- control identity drift;
- protocol retuning between folds.

## GEN-C7

The wrapper re-runs the canonical GEN-C7 causal economic gate independently per
fold. Every raw observation must bind exactly one fold. The treatment action is
required to remain unchanged across WF1..WF4.

## GEN-C8

The wrapper re-runs the canonical adaptive-speed economic gate independently
per fold. Every raw observation binds exactly one fold and the same treatment
identity is preserved across all four populations.

## GEN-C12

The wrapper re-runs the canonical crisis economic gate independently in each
fold. The frozen crisis-factor-set digest must remain identical across all four
folds; changing the stress definition after seeing outcomes is not replication.

## GEN-C11

Each fold reuses the already frozen GEN-C11/13 non-compensatory utility wrapper.
The same control, treatment, protocol binding and GEN-C10 transition-calibration
digest must survive all four folds.

## GEN-C13

Each fold reuses the same non-compensatory utility wrapper. The same control,
treatment, protocol binding and prospective memory-hypothesis digest must
survive all four folds. Retrospective memory cannot be upgraded into causal
evidence.

## Non-claims

This layer does not claim real OOS evidence, stress success, replication
success, production authority, governed DEMO authority, LIVE authority,
certification, or Owner review.

The sealed 2017H1 holdout remains untouched.

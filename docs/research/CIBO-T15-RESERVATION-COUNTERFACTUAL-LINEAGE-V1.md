# CIBO T15 Reservation Counterfactual Lineage V1

Status: **A1 PHASE22-NATIVE LINEAGE CONTRACT / NO COUNTERFACTUAL EFFECT CLAIM**

Identity:

`CIBO_T15_RESERVATION_COUNTERFACTUAL_LINEAGE_V1`

## Problem

The active V2 certification holdout is a historical replay. The pre-existing
Phase20 T15 reservation/realization consumers are intentionally restricted to
`FORWARD_OBSERVED` evidence.

Rewriting historical Phase22 decisions as forward evidence or manufacturing
historical broker execution identifiers would violate provenance.

## A1 solution

This consumer reads the canonical
`VersionedPhase22HistoricalReplayEvidenceBook` directly.

For T15 it verifies:

- known options existed at or before the reservation decision;
- the option was active and not already cancelled;
- the frozen policy record is digest-valid and bound to the exact origin;
- the MPC considered-option set matches the decision-time in-horizon option set;
- non-zero reservation exists whenever a known in-horizon option requires it;
- later option maturation is found only after the origin decision;
- materialization is matched by the sealed signal identity;
- replay outcomes are reconciled against the later sealed decision;
- current DEMO calibration is never relabelled as historical broker execution.

## Scientific boundary

Complete lineage is **not** proof that reservation was economically beneficial.

Even with `lineage_complete=true`, T15 remains scientifically open until the
frozen control/treatment utility comparison and strict WF1..WF4 replication
identify the counterfactual effect.

Mandatory remaining scientific blockers after lineage closure:

```text
COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED
T15_CAUSAL_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED
```

No productive, LIVE, real-capital, merge, PRE_EXAM or certification authority
is created by this contract.

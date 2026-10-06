# VT31 NAS100 — Causal H4 Carry-Forward Plumbing Gate 001

**Status:** PREDECLARED DATA-AVAILABILITY REPAIR  
**Fresh Holdout:** SEALED

## Defect

The post-entry adapter recomputes H4 only from the current-day causal slice.
Before a new complete H4 bucket is available, that reconstruction can return
`unavailable` even though the entry Situation Model already contains the last
fully closed H4 context that was valid at admission.

The sensor audit therefore reports H4 unavailable on many post-entry calls and,
correctly after the readiness repair, blocks maximum cognition.

## Repair

At each post-entry observation:

1. compute current H4 only from fully closed causal bars;
2. if that computation yields a valid current H4 state, use it;
3. if it yields `unavailable`, carry forward the frozen entry H4 state;
4. only remain `unavailable` if the frozen entry H4 itself was unavailable.

This is last-observation-carried-forward semantics, not imputation.

Once a new closed H4 observation exists, it supersedes the carried entry state.

## Constraints

- no future H4 bar;
- no partially formed H4 bar;
- no outcome/fold/date authority;
- no new trading threshold;
- no economic rule change;
- H4 unavailability must still block maximum cognition when neither a current
  nor frozen valid H4 state exists.

## Validation

The cognitive sensor audit must report:

- reduced/eliminated false H4-unavailable calls;
- no synthetic H4 values;
- PositionAction routing remains coherent;
- economic effects measured, not assumed.

Fresh Holdout remains sealed.

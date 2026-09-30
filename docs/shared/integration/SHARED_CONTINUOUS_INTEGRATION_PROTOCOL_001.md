# SHARED CONTINUOUS INTEGRATION PROTOCOL 001

## Authority

This document governs the integrator lane for PR #635 only.

- Architect A owns cognitive/scientific workstreams.
- Architect B owns global-world/perception workstreams.
- The Integrator owns convergence into `agent/qore-core-stack-v2-shared-001`.
- PR #635 remains DRAFT / UNMERGED until explicit Owner authority and all certification laws are satisfied.
- No LIVE, VPS, production, real-capital, Trader-authority, CIBO-authority, Risk-authority or execution authority is created here.

## Admission law

A child-lane workstream may enter the Shared master branch only when its claimed closure level is explicitly evidence-backed.

Required integration packet:

1. stable workstream identifier;
2. exact source branch and source SHA;
3. exact files admitted;
4. test/workflow evidence;
5. replay/OOS/stress/replication evidence when required by the workstream's own law;
6. provenance and anti-leakage status;
7. authority-isolation status;
8. explicit statement of remaining blockers;
9. terminal or closed-at-this-layer disposition.

`IMPLEMENTED` is not sufficient.
`CI_GREEN` is not sufficient when the workstream requires empirical/scientific evidence.
Partial or externally unresolved work remains in the owning child lane.

## Integration lifecycle

```text
CHILD WORK
-> EVIDENCE-BACKED CLOSURE
-> INTEGRATOR SLICE
-> CHILD EVIDENCE REVALIDATION
-> MERGE INTO SHARED MASTER
-> MASTER REGRESSION
-> INTEGRATION LEDGER UPDATE
-> INTEGRATED_AND_PROVEN
```

No second functional slice is merged while the previous master regression is unresolved.

## First admitted slice

Source lane: Architect B.
Source cut: `b498b4a340080c703dedee2fb5480946fa2afcc7`.

Admitted closed workstreams:

- B-02 Provider catalogue identity and drift freeze.
- B-03 Post-V14 cross-asset source availability.
- B-05 Global sensor registry discovery freeze.

Explicitly excluded from the slice:

- B-06 and later global-instrument/CNH work;
- every partial, in-progress, externally blocked or open B item.

The integration merge commit is:
`de96c6caa2a8a4ec001260675f03363d0eba8966`.

## Child-lane closure manifests

Architect A and Architect B must expose closure truth in machine-readable form before large-scale convergence.

The Integrator must not infer terminal closure merely from commit-message wording.

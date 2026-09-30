# CIBO Integrator Cross-Boundary Support Register V1

Date: 2026-09-30
Integrator PR: #670
Integrator branch: `agent/cibo-integrator-ab-001`

## Purpose

Track A↔B integration blockers, acceptance conditions and support actions without
mutating either architect's active branch.

## Architect A — current support item

Source HEAD reviewed:
`4b39952718640b1f723f03cd71a68c72afb3d76b`

### A-SUPPORT-001 — Final Integrated Exam evidence must not be self-attestable

Observed:
- P1-P8 are caller booleans with formatted SHA strings.
- E1-E10 use `passed: bool` plus formatted evidence SHA.
- Current gate validates shape, but does not prove that the referenced evidence
  exists, passed, belongs to the integrated HEAD, or is fresh/canonical.

Integrator acceptance condition:
- typed canonical receipts or a canonical recomputed evidence manifest;
- integrated-HEAD binding;
- stale/cross-head/cross-candidate rejection;
- adversarial test: dummy SHA + `passed=True` cannot PASS.

Integrator repair: receipt-bound Final Exam wrapper exists in #670 and requires canonical source-bound P1–P8/E1–E10 evidence tied to exact integrated HEAD/policy identity.\n\nStatus: STAGED_REPAIR_IN_670 / CI_PENDING / MIRROR_IN_A_REQUIRED.

### A-SUPPORT-002 — Mandatory workstream governance drift

Observed at A HEAD `4b39952718640b1f723f03cd71a68c72afb3d76b`:
- `WORLD_CUP_MAXIMUM_CAPABILITY_EXAM` was changed from mandatory/blocking to non-mandatory/non-blocking.
- A summary therefore moved from 64 mandatory to 63 mandatory workstreams.
- B and Integrator #670 remain on the common 64-mandatory closure law.

Integrator acceptance condition:
- restore the workstream to mandatory/blocking, or
- provide an explicit Owner-authorized canonical governance amendment that moves the World Cup exam outside ordinary CIBO certification.

Resolution implemented in #670: keep World Cup mandatory, let PRE_EXAM exclude both mandatory certification exams only for sequencing, then run Final Integrated Exam → World Cup Exam → STRICT zero-open. A must still reconcile its local protocol/ledger. Status: STAGED_REPAIR_IN_670 / CI_PENDING / MIRROR_IN_A_REQUIRED.

## Architect B — current support item

Source HEAD reviewed:
`3895af47c32c473682700d07435ea437110e5c3e`

### B-SUPPORT-001 — USD60 pre-exam prerequisites must not be self-attestable

Observed:
- `CiboUsd60PrerequisiteEvidence` accepts `passed=True` and arbitrary non-empty
  evidence refs.
- Seven self-attested prerequisite rows plus a ready forward manifest can make
  `ready_for_governed_exam=True` without proving the prerequisite receipts.

Integrator acceptance condition:
- typed canonical prerequisite receipts or validated manifest;
- binding to frozen USD60 protocol, Phase21 policy identity and integrated HEAD;
- stale/cross-head/cross-candidate rejection;
- adversarial test: dummy refs + `passed=True` cannot unlock readiness.

Integrator repair: receipt-bound USD60 readiness now derives the seven prerequisite PASS rows only after canonical receipt validation against the exact integrated HEAD and frozen policy identity. Forward scientific thresholds remain independently blocking.\n\nStatus: STAGED_REPAIR_IN_670 / CI_PENDING / MIRROR_IN_B_REQUIRED.

## Integration policy

A/B active heads remain moving work surfaces. PR #670 absorbs only frozen,
evidence-backed batches. Pending CI is not GREEN, and engineering GREEN is not
economic certification.

Current reconciled terminal ledger remains:
- mandatory: 64
- terminal: 13
- open: 51
- zero-open-work: false
- final certification candidate: false


### B-SUPPORT-002 — Risk handoff / canonical-ledger drift

Observed at B HEAD `41f0227e2136ac09c94bdd8187c2e6f5e625ee36`:
- B closure handoff recommends `RISK_INTEGRATION = COMPLETED_AND_PROVEN`.
- B canonical master ledger still leaves RISK_INTEGRATION open/partial.
- the mechanical test surface covers minimal-seed ALLOW, safe REDUCE and genuine minimum-fit REJECT semantics.
- current Risk workflow remains queued.

Integrator acceptance condition:
- Risk workflow SUCCESS on the accepted checkpoint;
- B handoff and canonical ledger reconciled in the same checkpoint;
- then #670 may import the terminal Risk closure.

Status: OPEN pending CI + B source-of-truth reconciliation.


### B-SUPPORT-004 — Provider geometry fixture breakage

Observed at B HEAD `2b13c4395e4bf8dc0d47118040a6915e3df5911c`:
- provider execution calibration test duplicated `provider_contract_size/tick_size/tick_value`
  keyword arguments and broke indentation;
- integrated-capital-forward-binding test still used the old manifest-row schema.

Integrator repair:
- `5331472d86023fe619ae6f6d650fcdf57c21c262`
- `bbb2415a16af9f3bffc42422632c36646759fffe`

Status: STAGED_REPAIR_IN_670 / CI_PENDING / MIRROR_IN_B_REQUIRED.

### B-SUPPORT-005 — T11 dedicated validation missing

Observed:
- B introduced `cibo_ce2i_t11_execution_cost_calibration.py` without a dedicated
  unit test/workflow proving provider-native tick-cost arithmetic and fail-closed
  policy readiness.

Integrator repair:
- `tests/infrastructure/test_cibo_ce2i_t11_execution_cost_calibration.py`
- `.github/workflows/cibo-t11-execution-cost-calibration.yml`

The Integrator test proves spread + commission + adverse-slippage cost arithmetic
and keeps gross-edge, market-impact and historical-2017 terms explicitly open.

Status: REPAIRED_IN_670 / MIRROR_IN_B_REQUIRED.

### Integrator trust hardening — receipt anti-laundering

The shared receipt artifact must now embed and cryptographically bind:
- `evidence_binding_id`;
- `evidence_kind`;
- producer identity;
- exact integrated Git HEAD;
- policy identity;
- PASS/failures/governance state.

A source artifact cannot be rebound as another P/E/Txx control or another evidence
kind without changing its canonical JSON and digest.

Status: STAGED_REPAIR_IN_670 / CI_PENDING.


### B-SUPPORT-003 — Calibration freeze evidence must not be self-attestable

Integrator repair:
- `cibo_receipt_bound_calibration_freeze.py` reconstructs the T01..T20 freeze only from canonical receipts tied to exact integrated HEAD/policy identity.
- `cibo_receipt_bound_pre_holdout.py` rebuilds readiness-critical provider objects before pre-holdout evaluation.

Status: STAGED_REPAIR_IN_670 / CI_PENDING / MIRROR_IN_B_REQUIRED.

### B-SUPPORT-006 — T16/T17 structural disablement requires typed provider status

Integrator repair:
- cTrader DEMO account-capability parser and typed capability registry are staged in #670;
- account mode `HEDGED` is not treated as proof of T16 economic hedge support;
- T16/T17 remain UNKNOWN/blocking until provider-verified support or provider-verified unavailable evidence exists.

Status: STAGED_REPAIR_IN_670 / CI_PENDING / REAL_PROVIDER_STATUS_STILL_REQUIRED.

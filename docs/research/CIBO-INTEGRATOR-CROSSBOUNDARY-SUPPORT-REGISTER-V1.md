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

Status: OPEN — returned to Architect A in PR #660.

### A-SUPPORT-002 — Mandatory workstream governance drift

Observed at A HEAD `4b39952718640b1f723f03cd71a68c72afb3d76b`:
- `WORLD_CUP_MAXIMUM_CAPABILITY_EXAM` was changed from mandatory/blocking to non-mandatory/non-blocking.
- A summary therefore moved from 64 mandatory to 63 mandatory workstreams.
- B and Integrator #670 remain on the common 64-mandatory closure law.

Integrator acceptance condition:
- restore the workstream to mandatory/blocking, or
- provide an explicit Owner-authorized canonical governance amendment that moves the World Cup exam outside ordinary CIBO certification.

Status: OPEN — A's 63-mandatory ledger is not accepted into #670.

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

Status: OPEN — returned to Architect B in PR #661.

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

# SHARED — INTEGRATOR 1 · A2 NATIVE LAB STAGED EXECUTION CONTRACT 001

**Owner:** Sergio Meza  
**Repository:** `mezas3238-hue/qore-core`  
**Integrator lane:** Integrator 1 — A1 + A2  
**Date:** 2026-10-04

## 1. Purpose

This contract prevents a mechanically GREEN A2 plugin graph from being confused with scientific closure.

The A2 lane cannot be executed truthfully as one homogeneous Shared Lab FULL run because its scientific stages require different sealed datasets/evidence families.

No producer threshold, hypothesis, target, holdout boundary or promotion rule is changed here.

## 2. Phase A — MC23 / MC24

Dataset identity:

- id: `shared-a2-consumed-r6-r5`
- version: `1`
- sha256: `15575cd662b92e736fe53f59fbad50c42d244e29180cfb10fa8b6c7a87c560d0`

Mandatory order:

`mc23-functional -> a2-capsule-self-test -> a2-mc23-one-shot-adaptation -> a2-mc24-regression -> a2-mc24-half-life`

Rules:

- capsule lineage must remain exact;
- R6 is fit/development; R5 is validation;
- no R5 refit or threshold rescue;
- if MC23 is falsified, the exact mechanism closes and MC24 cannot bind it;
- MC24 can advance only from a sealed MC23 PASS;
- no protected final Shared holdout is opened.

## 3. Phase B — MC25 same-lineage stress

Canonical consumed input lineage:

- freeze artifact `10906064254`
- HOLDOUT_E artifact `10908500161`
- REPLICATION_D artifact `10908077821`
- R8 artifact `10402199719`
- R6 artifact `10389112524`
- R5 artifact `10380044761`

Mandatory order:

`lineage integrity -> same-lineage performance stress`

The current `a2-mc25-performance` plugin validates mechanics only. It is NOT accepted by Integrator 1 as scientific performance-stress evidence.

A real MC25 performance result must have identity:

`QORE_SHARED_MC25_WP04_V3B_PERFORMANCE_STRESS_001`

and may advance only if all frozen scenarios pass on both HOLDOUT_E and REPLICATION_D without refit, representation refit, threshold retuning or target-aware stress selection.

## 4. Phase C — governed lifecycle

A performance-stress PASS does not complete MC25.

Mandatory non-skippable stages:

`FORMAL_STRESS -> SHADOW -> CERTIFICATION -> GOVERNED_PROMOTION`

The existing `mc25_governed_lifecycle.py` forbids stage skipping.

Governed promotion requires the producer's explicit owner-approval contract and still grants Shared no broker, sizing, QORE Risk, order, execution or productive trading authority.

## 5. Phase D — WP11

Run the real `shared_wp11_exact_blocker_audit.py` over sealed MC23, MC24 and MC25 evidence.

Terminal status required:

`WP11_GOVERNED_SELF_IMPROVEMENT_COMPLETED_AND_PROVEN`

with:

- blocker_count = 0
- zero_open_work = true
- wp11_completed_and_proven = true
- productive_authority = false
- protected_certification_holdout_opened = false

A pytest of WP11 mechanics is not terminal WP11 evidence.

## 6. Integrator 1 terminal guard

The combined A1+A2 gate now depends on:

`i1-a2-scientific-evidence`

This gate fails closed unless the exact target SHA contains sealed evidence for:

- MC23 validated adaptation;
- MC24 empirical half-life + non-degradation;
- MC25 lineage integrity;
- MC25 same-lineage performance stress;
- MC25 formal STRESS;
- MC25 SHADOW;
- MC25 CERTIFICATION;
- MC25 governed PROMOTION;
- WP11 zero-open-work terminal reconciliation.

Therefore unit/integration tests alone cannot manufacture an A1+A2 scientific PASS.

## 7. Shared Lab dependencies still open

PR #716 must repair:

1. external/versioned harness vs exact target SHA seam;
2. staged/multi-dataset execution semantics:
   - task-level dataset binding, or
   - explicit sub-DAG/task profile selection with sealed inter-run dependencies.

Relevant PR #716 comments:

- A1 exact-SHA seam: `5983660147`
- Integrator1 pair confirmation: `5983802293`
- Integrator1 multi-dataset seam: `5983850871`

Until those are repaired, native Shared Lab scientific execution is **BLOCKED**, not PASS.

## 8. Governance

- no merge of PR #635;
- no GitHub Actions validation fallback;
- no VPS;
- no LIVE / production / real capital;
- no broker mutation;
- no protected final holdout;
- no outcome-aware rescue;
- no scientific completion claim from mechanics-only GREEN.

# CIBO Architect 2 — Integrator Patch Request 014

Status: **FRESH_OOS CROSS-BOUNDARY BINDING REQUIRED / FAIL-CLOSED**

Architect-2 branch:

`agent/cibo-external-scientific-closure-001`

## Problem

Architect-2 is correctly forbidden to execute or independently inspect the
Phase22 V2 one-shot. Its terminal intake therefore depends entirely on an
Integrator-produced receipt.

The current pieces are individually strong but are not yet joined by one
canonical PASS/FAIL binding:

1. `Phase22ExecutionConsumptionReceipt` binds the durable one-shot claim and
   carries `execution_manifest_sha256` plus `outcome_bundle_sha256`.
2. `Phase22HoldoutQualificationReport` carries the economic qualification
   status and lineage assessment, but does not carry the outcome-bundle digest
   or the exact holdout evidence/policy store digests.
3. `Phase22QualificationReceipt` cryptographically binds the exact holdout
   evidence/policy store digests to a canonical qualification artifact, but its
   current contract is PASS-only.

Therefore Architect-2 cannot currently prove, for both terminal outcomes
PASS **and** FAIL, that the qualification being consumed was computed from the
same fresh one-shot outcome bundle named by the durable consumption receipt.

Accepting the two objects independently would permit an evidence-mixing class
of error even though each object is valid in isolation.

## Required Integrator receipt

Before FRESH_OOS can terminalize, Integrator must emit a canonical immutable
binding that validates and carries, at minimum:

- exact Phase22 V2 `candidate_id`;
- exact `execution_manifest_sha256`;
- durable claim run id / attempt / claim HEAD;
- exact `outcome_bundle_sha256`;
- exact `holdout_evidence_store_sha256`;
- exact `holdout_policy_store_sha256`;
- exact Phase22 qualification plan SHA;
- canonical qualification artifact SHA and canonical artifact payload;
- terminal qualification status: `PASS` or `FAIL`;
- lineage validity;
- proof that the qualification artifact's evidence/policy stores were
  materialized from that exact outcome bundle;
- no rerun / no holdout mining / no outcome-aware refit;
- `productive_authority=false`.

The binding must derive PASS/FAIL from the canonical qualification artifact,
not from caller booleans.

## Architect-2 acceptance law

- PASS + valid exact bundle/store/qualification lineage
  -> `COMPLETED_AND_PROVEN`.
- FAIL + valid exact bundle/store/qualification lineage
  -> `FALSIFIED_AND_CLOSED`.
- missing/mismatched binding
  -> remain `WAITING_ON_INTEGRATOR_RECEIPT`.
- NOT_READY/INVALID
  -> non-terminal; no rescue or rerun is authorized.

## Existing reusable infrastructure

Integrator already contains strong patterns that should be reused rather than
inventing a weaker trust model:

- `cibo_phase22_consumption_ledger.py`;
- `cibo_ce2i_final_certification.py::Phase22QualificationReceipt`;
- `cibo_crossboundary_evidence_receipt.py`.

The new binding may reuse/extend these patterns, but must support both terminal
PASS and terminal FAIL without weakening the one-shot rules.

## Governance

- Phase22 V2 outcomes consumed by Architect-2: **false**;
- Phase22 V2 executed by Architect-2: **false**;
- canonical ledger modified: **false**;
- Integrator branch modified directly: **false**;
- holdout outcomes inspected by Architect-2: **false**;
- rerun authorized: **false**;
- productive authority: **false**.

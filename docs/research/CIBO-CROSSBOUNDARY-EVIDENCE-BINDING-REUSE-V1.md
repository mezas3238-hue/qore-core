# CIBO Cross-Boundary Evidence Binding Reuse V1

Date: 2026-09-30
Integrator PR: #670

## Decision

Architect A Final Integrated Exam and Architect B USD60 Pre-Exam Readiness must
reuse the existing self-validating evidence pattern already implemented by
`Phase22QualificationReceipt` in
`src/qore/infrastructure/cibo_ce2i_final_certification.py`.

Do not introduce a second weaker trust model based on caller booleans plus
canonical-looking SHA strings.

## Canonical pattern to preserve

The existing Phase22 receipt demonstrates the required shape:

1. frozen candidate / plan identity is checked against canonical constants;
2. SHA-256 and Git SHA syntax is validated;
3. canonical JSON is parsed and re-serialized;
4. the artifact digest is recomputed from the actual canonical JSON;
5. artifact fields are checked against receipt fields;
6. lineage/population thresholds are verified;
7. economic hard gates are recomputed from artifact metrics;
8. governance contamination flags are fail-closed;
9. productive authority remains false.

## Architect A application

P1-P8 and E1-E10 must not remain caller-controlled `passed: bool` assertions.
Each certification-critical item must resolve to a canonical typed receipt or
canonical artifact whose digest and identity are verified by the exam gate.

At minimum bind:
- integrated HEAD SHA;
- producer gate / artifact identity;
- candidate / policy identity where applicable;
- canonical artifact JSON or equivalent immutable receipt payload;
- recomputed SHA-256;
- PASS semantics derived from that payload, not supplied independently.

## Architect B application

USD60 pre-exam prerequisites must not remain caller-controlled
`passed=True` plus arbitrary non-empty evidence refs.

Each prerequisite must bind to a canonical typed receipt/artifact and the
frozen USD60 protocol / Phase21 identity as applicable. Readiness must be
derived from verified receipts.

## Integrator acceptance law

A batch that preserves self-attested certification-critical booleans is not
eligible for integration as a trusted certification/readiness gate.

This contract does not grant holdout access, DEMO, LIVE, production,
real-capital, Risk, execution or merge authority.

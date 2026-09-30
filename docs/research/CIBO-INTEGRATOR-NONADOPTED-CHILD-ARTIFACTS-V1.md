# CIBO Integrator — Deliberately Non-Adopted Child-Branch Artifacts V1

Date: 2026-09-30
Integrator PR: #670

## Purpose

A file present in Architect A or B but not copied byte-for-byte into #670 is not
automatically forgotten work. Some child-branch files are deliberately not
adopted because the Integrator owns the reconciled equivalent or because the
child copy contains stale/conflicting global state.

This register prevents silent omissions while preserving one canonical truth.

## Architect A

### `.github/workflows/cibo-zero-open-work-gate.yml`

Disposition: **DO NOT COPY CHILD VERSION**

Reason:
#670 owns the reconciled Zero Open Work topology, including:
- 64 mandatory workstreams;
- mandatory Final Integrated Exam;
- mandatory World Cup Maximum-Capability Exam;
- PRE_EXAM exclusion of only those two exams;
- STRICT inclusion of every mandatory workstream;
- union of A/B/Integrator inventory classifiers.

Canonical replacement:
- `scripts/cibo_zero_open_work_gate.py`
- `tests/infrastructure/test_cibo_zero_open_work_gate.py`
- the #670 zero-open workflow.

### A branch Roadmap V3 / World Cup Gap Matrix delta

Disposition: **DO NOT COPY CHILD VERSION BYTE-FOR-BYTE**

Reason:
the A delta described World Cup as post-certification/non-mandatory in the
ordinary closure topology. That conflicts with the standing Owner absolute
closure law.

Canonical resolution in #670:
- Roadmap V3 reconciled to Final Integrated Exam → World Cup → STRICT zero-open;
- Gap Matrix reconciled to the same sequence;
- `CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md`;
- `CIBO-ABSOLUTE-CLOSURE-AMENDMENT-V1.md`.

### `docs/research/CIBO-ARCH-A-CROSSBOUNDARY-REQUEST-001.md`

Disposition: **ADOPTED AS REQUEST/PROVENANCE**

Its requested evidence bridge is being implemented by the Integrator through:
- `cibo_arch_a_capital_state_delivery.py`;
- `cibo_arch_a_forward_compound_delivery.py`;
- `cibo_compound_path_history.py`;
- `cibo_arch_a_path_evidence_delivery.py`.

## Architect B

### `docs/research/CIBO-ARCH-B-CLOSURE-HANDOFF-V1.json`
### `docs/research/CIBO-ARCH-B-CLOSURE-HANDOFF-V1.md`

Disposition: **DO NOT USE AS CANONICAL INTEGRATED STATE**

Reason:
these are branch-local handoff snapshots. They may contain terminal
recommendations that are ahead of the B canonical ledger or whose workflows are
still pending.

Canonical integrated state:
- `CIBO-AB-INTEGRATION-ACCEPTANCE-V1.json`;
- `CIBO-MASTER-OPEN-WORK-LEDGER-V1.json`;
- `CIBO-AB-INTEGRATED-EVIDENCE-REGISTER-V1.json`;
- `CIBO-INTEGRATOR-CROSSBOUNDARY-SUPPORT-REGISTER-V1.md`.

### B Cross-Boundary Request 001 / 002

Disposition: **ADOPTED AS REQUEST/PROVENANCE**

The requested Zero Open Work ownership mappings are implemented and tested in
the Integrator classifier.

## Rule

No child handoff, roadmap or workflow may overwrite global certification law,
terminal union, mandatory counts or shared inventory ownership by simple file
copy. Those surfaces require explicit Integrator reconciliation.

This register grants no merge, holdout, LIVE, production, execution, Risk or
real-capital authority.

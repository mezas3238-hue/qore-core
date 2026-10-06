# CIBO A+B Shared Governance Surface V1

Date: 2026-09-30
Integrator PR: #670

## Purpose

Architect A and Architect B may continue independently, but global CIBO
governance must no longer be resolved independently in both child branches.

## Integrator-owned reconciliation surfaces

The only A/B file overlap currently observed is:

1. `docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json`
2. `scripts/cibo_zero_open_work_gate.py`

These are global state/governance surfaces. PR #670 is the canonical
reconciliation surface for combining changes to them.

Architects may still modify their local copies when needed to express the
state of their own work, but those edits are proposals until reconciled by the
Integrator. A child-branch edit cannot independently change global
certification law, mandatory-work counts, terminality, or cross-project
inventory classification.

## Reconciliation law

For the master ledger:
- terminality requires evidence-backed closure;
- mandatory/blocking changes require canonical governance authority;
- A terminal closure proven by A cannot be reopened by B merely because B's
  local ledger is stale, and vice versa;
- open-work maturity improvements may be integrated without granting terminality;
- summary counts are recomputed from the reconciled rows.

For the zero-open-work gate:
- the Integrator takes the union of valid A and B inventory classifiers and
  hardening invariants;
- no architect-specific classifier may be silently lost;
- stricter fail-closed invariants dominate weaker duplicates;
- pre-exam exceptions cannot redefine Owner-mandated closure scope without an
  explicit governance amendment.

## Current measured boundary

At this checkpoint:
- Architect A changed files: 74
- Architect B changed files: 53
- A↔B overlap: 2 files
- overlap is limited to the two reconciliation surfaces above.

## Authority

This coordination contract grants no merge, LIVE, production, Risk,
execution, DEMO, real-capital or holdout-access authority.

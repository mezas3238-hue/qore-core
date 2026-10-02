# CIBO Architect A1 Integrator Handoff V1

Status: **A1 TERMINAL HANDOFF CONTRACT / INTEGRATOR OWNS RECONCILIATION**

Identity:

`QORE_CIBO_ARCH_A1_INTEGRATOR_HANDOFF_V1`

## Purpose

When A1 science is terminal, the Integrator must receive one immutable receipt
instead of reconstructing state from individual commits.

The handoff binds:

- exact A1 branch and HEAD;
- original Architect-A split base SHA;
- canonical Phase22 scientific manifest SHA256;
- A1 scientific-consumption manifest SHA256;
- canonical A1↔Phase22 bridge SHA256;
- complete disposition-package SHA256;
- canonical Phase22 scientific-closure packet SHA256;
- exact completed/falsified partition across the 18 A1 workstreams.

The local A1 disposition package and the canonical Phase22 closure packet must
agree exactly on manifest identity, completed/falsified partition and terminal
count.

## Readiness rule

`ready_for_integrator=true` only when:

- A1 Internal Readiness is green;
- the scientific package is marked complete;
- exactly 18 terminal A1 dispositions exist;
- package branch equals the isolated A1 branch;
- package HEAD equals the handoff HEAD.

A falsified workstream is still terminal scientific evidence and is preserved as
`FALSIFIED_AND_CLOSED`; it is never rewritten into PASS.

## Governance

The receipt grants no:

- Master Ledger update authority;
- merge authority;
- productive/LIVE authority;
- CIBO certification claim.

The Integrator consumes the receipt and owns all global reconciliation.

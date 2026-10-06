# CIBO Integrated Certification Sequence Amendment V1

Date: 2026-09-30
Authority surface: Integrator PR #670
Status: INTEGRATION GOVERNANCE / NO CERTIFICATION CLAIM

## Problem resolved

The Architect-A draft final-exam topology makes
`WORLD_CUP_MAXIMUM_CAPABILITY_EXAM` non-mandatory and post-certification.

That conflicts with the standing CIBO absolute-closure rule used by the
Integrator: no material CIBO work may remain pending at certification.

Keeping World Cup mandatory while excluding only the final integrated exam
from PRE_EXAM would create a circular dependency, because World Cup is intended
to run only after ordinary scientific/integration closure.

## Non-circular mandatory sequence

Both certification exams remain:

- `mandatory=true`
- `certification_blocking=true`

The required sequence is:

```text
ZERO-OPEN AUDITOR IMPLEMENTATION PROVEN
        ↓
ALL NON-EXAM MANDATORY WORK TERMINAL
        ↓
PRE_EXAM PASS
(excludes FINAL_INTEGRATED_CIBO_EXAM
 and WORLD_CUP_MAXIMUM_CAPABILITY_EXAM only)
        ↓
PHASE21 / PHASE22 ECONOMIC RECEIPT AVAILABLE
        ↓
FINAL INTEGRATED CIBO EXAM
P1-P8 + E1-E10
        ↓
FINAL_INTEGRATED_CIBO_EXAM TERMINAL
        ↓
WORLD CUP MAXIMUM CAPABILITY EXAM
under its separately frozen protocol/evidence
        ↓
WORLD_CUP_MAXIMUM_CAPABILITY_EXAM TERMINAL
        ↓
STRICT ZERO-OPEN PASS
        ↓
FINAL CIBO CERTIFICATION CANDIDATE
```

## Meaning of PRE_EXAM

PRE_EXAM is a sequencing scope, not a certification waiver.

It may exclude only the two mandatory certification exams so that they can be
executed in their defined order. It cannot exclude scientific, provider, Risk,
CMA, forward, Compound, OOS, stress, replication, source-of-truth, inventory,
or other mandatory work.

## Meaning of STRICT

STRICT includes all mandatory workstreams, including both exams.

Therefore CIBO cannot become a final certification candidate until:
- the final integrated exam is terminal;
- the World Cup maximum-capability exam is terminal;
- every other mandatory row is terminal;
- no certification-critical external blocker remains.

## Authority

This amendment grants no holdout access, DEMO, LIVE, production, execution,
Risk, real-capital or merge authority.

# CIBO CE2I — OOS MECHANISM STRESS ADMISSION V1

Status: **PREREGISTERED / ENGINE IMPLEMENTED / REAL STRESS EVIDENCE REQUIRED**

Identity:

`CIBO_CE2I_OOS_MECHANISM_STRESS_ADMISSION_V1`

## Scope

This adapter covers CE2I workstreams whose frozen utility contracts expose
canonical fresh-OOS reports rather than a shared economic status enum:

- T08 Portfolio Netting;
- T09 Opportunity Competition;
- T12 Regime Tool Eligibility;
- T13 Drawdown Reserve;
- T18 Cross-Trader Allocation.

The adapter consumes the real report object type for each workstream. It does
not translate arbitrary strings into PASS.

## Stress law

For every workstream, all seven already-frozen `CompoundStressKind` scenarios
must be present, preregistered before outcomes, non-improving, use distinct
stressed population digests, and share the same protocol-binding digest.

Missing scenarios or protocol drift are invalid evidence.

## T08

A stressed T08 scenario passes only when the canonical
`T08NettingOosAblationReport` still demonstrates fresh-OOS utility, preserves
pathwise risk authorization, and retains exactly four folds.

Independent factor-risk/correlation certification remains a separate blocker.

## T12 / T13

A stressed scenario passes only when the canonical utility report still has:

- `fresh_oos_utility_demonstrated = true`;
- no blockers;
- no runtime authority.

## T09 / T18

Stress admission is deliberately conjunctive.

For the same stressed scenario:

1. the canonical scarcity utility scope must demonstrate fresh-OOS utility with
   no blockers; **and**
2. the canonical scarcity safety gate must return the named treatment as
   `ELIGIBLE_FOR_FURTHER_RESEARCH` in WF1..WF4 with no failed dimensions.

T18 continues to inherit Trader-sovereignty enforcement from the underlying
scarcity safety gate.

## Verdict

Every frozen stress kind must pass. One failed scenario produces
`FALSIFIED`. There is no weighted or cross-scenario compensation.

## Non-claims

The adapter does not create stressed outcomes, claim market probabilities,
authorize runtime allocation/netting, certify CIBO, merge code, or touch LIVE.

The sealed 2017H1 holdout remains untouched.

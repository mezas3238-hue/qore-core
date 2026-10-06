# CIBO Final Integrated Certification Exam Protocol V1

Status: **PREREGISTERED / EXECUTION BLOCKED UNTIL ALL PREREQUISITES PASS**

Identity:

`CIBO_FINAL_INTEGRATED_CERTIFICATION_EXAM_V1`

This protocol does not open the sealed 2017H1 holdout and grants no MERGE,
LIVE, PRODUCTION, REAL-CAPITAL or broker-mutation authority.

## Purpose

The final exam answers one question:

> Does the complete integrated CIBO system satisfy its frozen authority,
> accounting, provider, causal, survival and economic contracts with no material
> open work and no evidence contamination?

Return alone cannot pass the exam.

## Entry prerequisites

The exam may not execute until all of the following are true.

### P1 — source of truth reconciled

PR body, code, tests, workflows, ADRs, roadmaps, artifacts and the canonical
master ledger agree on the integrated A+B HEAD.

### P2 — zero open work

`CIBO_ZERO_OPEN_WORK_GATE` in enforcement mode must report:

`pass = true`

Every mandatory workstream must have exactly one legal terminal disposition.

A certification-critical `EXTERNAL_DEPENDENCY_BLOCKED` row keeps this
prerequisite false.

### P3 — no unexplained red CI

Every certification-relevant workflow must either:

- be GREEN on the integrated evidence HEAD; or
- have a documented terminal scientific disposition that does not hide an
  engineering defect.

A red engineering workflow cannot be compensated by return.

### P4 — provider / Risk / CMA / forward truth

The integrated evidence package must prove:

- provider-valid economics;
- account identity;
- requested -> authorized -> executed lineage;
- CMA reservation/allocation/release lineage;
- terminal settlement uniqueness;
- no fabricated USD economics;
- no fabricated hedge/netting credit;
- no missing critical provider assumptions promoted as support.

### P5 — frozen forward qualification

The frozen Phase20D thresholds must pass without reduction:

- decision epochs >= 80;
- candidate outcomes >= 200;
- selected outcomes >= 60;
- calendar span >= 28 days;
- trading days >= 20;
- represented lineages >= 7;
- outcomes/lineage >= 8;
- four contiguous folds;
- candidate coverage >= 95%;
- selected coverage = 100%;
- baseline-selected coverage = 100%;
- pre-freeze decisions = 0.

### P6 — policy / calibration freeze

All policies, calibration artifacts, comparison identities and causal gates used
for certification must be frozen before the outcomes they evaluate.

### P7 — scientific closure

Applicable CE2I and GEN-C mechanisms must already have their terminal
scientific dispositions from:

- equal-population causal comparison;
- non-compensatory economic evaluation;
- fresh OOS;
- required adversarial stress;
- temporal replication.

### P8 — Compound closure

The complete chronological Compound cycle must already prove:

- accounting integrity;
- provenance;
- no double counting;
- no unexplained creation/destruction;
- capital generations;
- protected-floor semantics;
- profit graduation;
- Internal Capital Market;
- reservation/release/recycling;
- dependency-aware path Monte Carlo;
- adversarial stress;
- temporal replication.

## Sealed holdout law

Protected identity:

`CIBO_USD60_6M_HOLDOUT_2017H1_V1`

Window:

`2017-01-01 inclusive -> 2017-07-01 exclusive`

The exam protocol itself does not authorize opening it.

The holdout may be consumed only through the already-governed Phase21/Phase22
chain after all holdout-opening prerequisites pass.

Once opened:

1. the frozen policy cannot be changed;
2. calibration cannot be changed;
3. gates cannot be relaxed;
4. failed results cannot trigger same-holdout retuning;
5. every access/result must be sealed with immutable provenance.

A failed holdout is a scientific result, not permission to tune.

## Integrated exam assertions

Once entry is legal, the exam must verify the integrated system end to end.

### E1 — authority

```text
TRADER owns methodology
CIBO owns capital
RISK owns hard survivability boundaries
EXECUTION owns broker mutation
```

No layer steals another layer's authority.

### E2 — capital conservation

At every integrated checkpoint:

`ACCOUNTING RESIDUAL = 0`

No phantom capital, double spend, lost capital or duplicate settlement is
allowed.

### E3 — realized-capital law

Floating PnL is never realized funding.

Loss is never a reason for more capital.

Protection classifications remain distinct from broker guarantees.

### E4 — provider truth

All provider-sensitive decisions use evidence valid for that account,
instrument and timestamp.

UNKNOWN remains fail-closed where support is required.

### E5 — Risk precedence

CIBO may optimize only inside the Risk-authorized feasible set.

No CIBO economic objective can waive a Risk rejection.

### E6 — chronology / leakage

No future outcome, future opportunity identity, future provider state, or
post-outcome memory may influence an earlier decision.

### E7 — economic non-compensation

No upside metric can compensate:

- higher ruin;
- worse tail/max drawdown;
- higher plausible loss;
- lower minimum capital;
- worse recovery/underwater duration;
- capital-conservation breach;
- provider/Risk violation.

### E8 — stress integrity

Impossible or fragile paths remain visible.

The system may not silently remap dependency breaches or repair impossible
capital histories to manufacture a pass.

### E9 — temporal replication

Where economic replication is required, the same frozen gate must pass
independently in `WF1/WF2/WF3/WF4`.

No pooled rescue is allowed.

### E10 — deterministic replay

The complete evidence package must be replayable from immutable identities and
hashes to the same certification verdict.

## Pass law

The ordinary CIBO certification exam passes only if:

```text
ALL ENTRY PREREQUISITES PASS
AND
ALL INTEGRATED ASSERTIONS PASS
AND
ZERO CERTIFICATION-CRITICAL EXTERNAL BLOCKERS
AND
ZERO MATERIAL OPEN WORK
```

There is no weighted score and no compensatory return threshold.

## Fail law

Any failed mandatory assertion yields a non-pass.

The root cause must be assigned to one of:

- engineering defect to correct and revalidate;
- scientific falsification;
- superseded lineage with proven replacement;
- real external dependency.

The exam must not rewrite history to obtain a green verdict.

## Closure topology — no circular certification

The executable closure order is:

```text
ZERO-OPEN AUDITOR IMPLEMENTATION PROVEN
        ↓
PHASE21 / PHASE22 GOVERNED HOLDOUT CHAIN COMPLETE
        ↓
ALL OTHER ORDINARY MANDATORY WORK EXCEPT FINAL_EXAM TERMINAL
        ↓
PRE-EXAM ZERO-OPEN PASS
        ↓
FINAL INTEGRATED EXAM P1-P8 + E1-E10
        ↓
FINAL_INTEGRATED_CIBO_EXAM TERMINAL
        ↓
STRICT ZERO-OPEN PASS
        ↓
ORDINARY CIBO FINAL CERTIFICATION CANDIDATE
```

`PRE_EXAM` excludes only `FINAL_INTEGRATED_CIBO_EXAM` from the mandatory
closure set. It does not exclude scientific, provider, Risk, CMA, forward,
Compound, OOS, stress, replication or governance work.

The Zero Open Work auditor itself is normal mandatory infrastructure and must
already have a terminal engineering disposition before PRE_EXAM can pass.

The post-ordinary `WORLD_CUP_MAXIMUM_CAPABILITY_EXAM` is tracked in the
ledger but is not part of the ordinary-certification mandatory count. Its
preparation may not leave orphan work, and its exam cannot run before ordinary
certification.

The Phase22 economic receipt must already exist before PRE_EXAM can pass because FORWARD_QUALIFICATION is itself ordinary mandatory work. That receipt remains necessary but is not sufficient for global CIBO certification. Global certification additionally requires this integrated exam and the final strict zero-open verdict.

## World Cup separation

Passing this ordinary exam does **not** imply World Cup maximum-capability
certification.

`WORLD_CUP_MAXIMUM_CAPABILITY_EXAM`

remains a separate post-ordinary-certification program under its own future
frozen protocol and evidence.

## Non-claim

This document freezes the exam law only.

The exam is not currently eligible to run because mandatory CIBO work remains
open.

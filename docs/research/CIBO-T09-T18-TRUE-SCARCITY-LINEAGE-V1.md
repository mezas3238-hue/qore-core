# CIBO T09/T18 True Scarcity Lineage V1

Status: **A1 PHASE22-NATIVE POPULATION CONTRACT / NO UTILITY CLAIM**

Identity:

`CIBO_T09_T18_TRUE_SCARCITY_LINEAGE_V1`

## Purpose

The original T09/T18 scarcity-readiness consumer accepts only
`FORWARD_OBSERVED` evidence. Phase22 V2 is a historical replay and exposes
`HISTORICAL_REPLAY_OBSERVED` decisions.

A1 therefore consumes the canonical historical replay book directly instead of
rewriting evidence kind or fabricating forward/provider provenance.

## What this contract proves

For the exact Phase22 replay population it identifies, at decision time:

- epochs with at least two simultaneous valid candidates;
- true capital scarcity from stop-risk headroom, margin headroom or frozen
  concentration limits;
- cross-Trader scarcity for T18;
- exact selected-policy binding;
- candidate and selected outcome coverage;
- contiguous WF1..WF4 coverage;
- immutable source/policy population digests.

The same minimum robust competition population and frozen Phase20D coverage
requirements remain in force.

## What it does not prove

The lineage reader never inspects PnL magnitudes and cannot claim economic
utility.

A ready T09 or T18 population means only that the frozen utility/safety gate can
legally consume the evidence.

It does not produce:

- `COMPLETED_AND_PROVEN`;
- `FALSIFIED_AND_CLOSED`;
- runtime allocation authority;
- certification;
- LIVE or real-capital authority.

T09 and T18 still require independent utility dispositions even though they
share the scarcity lineage.

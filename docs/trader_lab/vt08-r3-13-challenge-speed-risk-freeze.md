# VT-08 R3.13 — Challenge-Speed Adaptive Risk Freeze

Status: **CONSUMED-DATA RESEARCH ONLY**

Parent: PR #528 / R3.12 exact green HEAD `6a09be314a5c8b6a17822ea141a41d521aaf8655`.

## Frozen objective

R3.13 searches Risk policy only. Trader, methodology, source contract and frozen portfolio identities remain unchanged.

Primary challenge objective for a USD 100,000 account:

`P(+10% before prop-firm breach and on/before trading day 30)`.

Secondary objectives are P(+5%), P(+8%), time to target, maximum drawdown, daily/max-loss breach, ruin, Risk dynamics, heat/concurrency, cost robustness and provider portability.

## Safety acceptance contract

A policy is considered **safe-candidate** only when all of the following hold in the official paired Monte Carlo at the primary modeled cost:

- any prop-firm breach probability <= 1.00%;
- maximum drawdown p99 <= 6.00%;
- ruin probability == 0;
- slow-up / fast-down is true;
- provider hard rules, internal drawdown/daily guards, heat, sleeve and correlation caps remain sovereign;
- broker-valid sizing remains fail-closed.

Among safe candidates, selection maximizes P(+10% before breach within 30 trading days). Tie-breaks prefer lower breach probability, lower p99 drawdown, then lower base Risk.

If no candidate is safe, R3.13 must conclude `NO_SAFE_30D_SOLUTION`; it must not weaken the safety contract to manufacture a passing result.

## Research surface

The pre-registered discovery surface spans materially higher adaptive Risk than R3.12 while retaining fast-down containment. Candidate base Risk levels cover approximately 0.30% through 2.00% per trade, with correspondingly bounded ceilings, floors, portfolio/sleeve/correlation heat and internal guards. Exact candidate definitions are versioned in code and included in the official artifact.

Discovery uses a deterministic paired moving-block bootstrap over consumed evidence only. The final selected candidate is rerun at 10,000 paired paths for both versioned provider profiles and A CORE / GBPJPY RETURN ENHANCER / B COMBINED.

## Governance

- `HOLDOUT_NOT_ACCESSED = true`.
- Protected holdout `[2020-07-01, 2022-07-01)` remains untouched.
- Existing R3.12 remains the capital-preservation / funded-mode baseline.
- R3.13 Challenge Mode is not DEMO_ELIGIBLE and grants no LIVE or real-capital authority.
- PR must remain DRAFT. Do not merge or mark ready.
- Search multiplicity is explicit: all candidates and their results must be retained in the artifact.
- Primary modeled transaction cost remains 0.50 bp with robustness at 0.00 / 0.25 / 0.50 / 1.00 bp.

## Gate repair checkpoint

The first official R3.13 quality run passed Ruff and exposed three Mypy narrowing errors in optional target-day handling. One-shot repair run `34734882391` corrected that typing path and passed Ruff, Mypy, and the focused R3.13 test file before committing the repair. This documentation commit retriggers the full official gate from the repaired HEAD without changing the frozen research objective or search surface.

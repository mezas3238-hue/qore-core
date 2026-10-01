# CIBO Provider Economics — Stress-Bound Execution Model V1

Status: **OWNER-AUTHORIZED / PRE-HOLDOUT EXECUTION MODEL**

The current cTrader DEMO native provider terms are frozen exactly as observed.
The account does not yet contain a large enough QORE-labelled fill population
to claim empirical slippage calibration.

Certification therefore uses a separate `STRESS_BOUND` execution-model lane.
It must never be described as observed slippage.

Four scenarios are frozen before the fresh 2017H1 holdout is opened:

1. NATIVE_BASE
2. MODERATE_DEGRADATION
3. SEVERE_DEGRADATION
4. EXTREME_DEGRADATION

The scenarios monotonically degrade spread, adverse-slippage allowance,
commission and margin assumptions.  The final USD60 examination must report
sensitivity across the frozen surface.

This policy does not claim historical 2017 broker terms, does not use holdout
outcomes, does not mutate cTrader and grants no productive authority.

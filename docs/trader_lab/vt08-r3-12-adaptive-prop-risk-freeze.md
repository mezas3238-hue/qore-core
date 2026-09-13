# VT-08 R3.12 — Adaptive Prop-Firm Risk + Monthly Growth

Research-only child of VT-08 R3.11.

## Frozen parent

- Parent PR: #527
- Parent branch: `agent/vt08-r3-11-profitability-forensics-001`
- Parent HEAD at branch creation: `8dbf32f9163e75bbe98b0ca205f02266c947b272`
- Source/methodology/Trader semantics: frozen; no R3.12 mutation authorized.

## Research boundary

R3.12 may use consumed evidence only. The proposed fresh holdout `[2020-07-01, 2022-07-01)` remains protected and MUST NOT be downloaded, previewed, replayed, sampled, or used for parameter selection during this workstream.

`HOLDOUT_NOT_ACCESSED = true`

## Frozen portfolio identities

- A CORE = AUDJPY SHORT + GBPUSD SHORT.
- GBPJPY RETURN ENHANCER = GBPJPY LONG + GBPJPY SHORT.
- B COMBINED = A CORE + GBPJPY RETURN ENHANCER.

## Mission

Implement a sovereign Risk authority that recalculates authorized Risk before every entry from current account state, with slow-up profit-cushion scaling, faster drawdown contraction, hysteresis, daily/max-loss headroom, open bounded loss, portfolio heat, sleeve budgets, provider profile rules, and broker-valid quantity constraints. Produce paired consumed-evidence Monte Carlo, complete monthly compounding/growth distributions, prop-firm breach probabilities, cost sensitivity, static R3.11 comparison, and frozen preregistration evidence before any fresh holdout access.

No DEMO_ELIGIBLE, no LIVE, no real capital, no merge, no ready-for-review authority.

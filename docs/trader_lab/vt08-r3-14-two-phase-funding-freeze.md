# VT-08 R3.14 — Two-Phase Funding Qualification Freeze

Status: **CONSUMED-DATA RESEARCH ONLY**

Parent: PR #529 / R3.13 exact green HEAD `f88769f2d5c0f356b875e8788fcf56dc37c7c9ab`.

## Frozen objective

R3.14 models the way Challenge Mode is actually intended to be used. Aggressive adaptive Risk is temporary and exists only to qualify a two-phase funding evaluation. It is not the funded-account policy and it is not a monthly return target.

For a USD 100,000 evaluation account the fixed objective is:

1. **Phase 1:** reach +10% without provider breach.
2. Reset evaluation state for the new Phase 2 account.
3. **Phase 2:** reach +5% without provider breach.
4. Complete both phases within **60 total trading days**.
5. Immediately transition to the conservative R3.12 funded-mode Risk policy after Phase 2 completion.

The primary metric is:

`P(Phase1 +10% -> Phase2 +5% completed within 60 trading days, before any breach)`.

The two phases have independent Risk memory and independent account/equity/peak/daily-loss state. The Phase 2 clock begins on the trading day after Phase 1 completion. Provider minimum-trading-day requirements are enforced. A target hit before the provider minimum does not complete the phase; a breach before minimum-day completion is a failed phase.

## Safety acceptance contract

A Phase 1 / Phase 2 Risk pair is a **safe candidate** only if all of the following hold at the primary modeled cost:

- combined modeled provider breach probability <= 1.00%;
- challenge maximum-drawdown p99 <= 6.00%;
- ruin probability == 0;
- slow-up / fast-down is true in both phases;
- provider hard loss rules, internal daily/DD guards, portfolio heat, sleeve heat, correlation caps and broker-valid quantity remain sovereign;
- Phase 2 Risk is lower than or equal to Phase 1 base Risk;
- no safety threshold may be relaxed because a higher-risk pair reaches the target faster.

Among safe candidates, selection maximizes two-phase completion probability within 60 days. Tie-breaks prefer lower breach probability, lower p99 drawdown, faster successful completion, then lower combined base Risk.

If no pair is safe, R3.14 must conclude `NO_SAFE_TWO_PHASE_SOLUTION`; it must not manufacture qualification by weakening containment.

## Pre-registered Risk surface

Phase 1 adaptive base Risk candidates cover approximately:

- 1.50%
- 2.00%
- 2.25%
- 2.50%

Phase 2 adaptive base Risk candidates cover approximately:

- 0.75%
- 1.00%
- 1.25%
- 1.50%

This yields 16 pre-registered Phase 1 x Phase 2 pairs. All pairs use fast-down / slow-up adaptation. Discovery uses 10,000 deterministic paired moving-block-bootstrap paths per pair at the primary 0.50 bp cost. The selected pair is then evaluated against both versioned provider risk profiles and cost sensitivity at 0.00 / 0.25 / 0.50 / 1.00 bp.

## Required adjudication metrics

The artifact must report at least:

- P(Phase 1 pass) and Phase 1 completion-day distribution;
- P(Phase 2 pass | Phase 1 passed) and Phase 2 completion-day distribution;
- P(two-phase pass <=30 / <=45 / <=60 total trading days);
- median and p95 total days when both phases pass;
- expected attempts implied by the modeled completion probability;
- combined / per-phase breach probability and cause;
- challenge DD p95 / p99 and ruin;
- ALLOW / REDUCE / REJECT and containment interactions through the underlying Risk engine;
- transaction-cost sensitivity;
- provider portability;
- exact selected Phase 1 and Phase 2 policy fingerprints;
- explicit post-qualification transition to R3.12 funded-mode policy.

## Funded-mode transition

After successful Phase 2 qualification, Challenge Mode Risk is discarded. The funded account starts with fresh Risk state under the existing R3.12 capital-preservation policy (`balanced-adaptive-v1`, approximately A 0.25% / GBPJPY 0.20% base Risk), subject to the same sovereign Risk and broker constraints. R3.14 does not authorize production or real-capital execution.

## Governance

- `HOLDOUT_NOT_ACCESSED = true`.
- Protected holdout `[2020-07-01, 2022-07-01)` remains untouched.
- Trader, source contract, methodology and frozen A / GBPJPY / B portfolio identities remain unchanged.
- Search multiplicity is retained in the artifact.
- Costs remain research proxies; actual cTrader transaction costs are not demonstrated by this study.
- `DEMO_ELIGIBLE = false`.
- `LIVE_AUTHORIZED = false`.
- PR remains DRAFT. Do not merge or mark ready.

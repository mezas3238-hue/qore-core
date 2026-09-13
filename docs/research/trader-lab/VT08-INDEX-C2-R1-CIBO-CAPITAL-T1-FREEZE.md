# VT-08 Index C2 R1 — CIBO Capital T1 pre-economic freeze

Checkpoint: 2026-09-13

Status: RESEARCH ONLY / CONSUMED EVIDENCE / NO PROMOTION AUTHORITY

## Immutable parent evidence

This study consumes the exact official CIBO stop-protection artifact from PR #537:

- parent R1 HEAD: `5232540cdb444473ddf0bfae01beb2e672cea344`
- parent R1 artifact: `10323025742`
- CIBO stop-transfer HEAD: `9c072a582d11943dc2c32c77627f1aa96ea32a52`
- CIBO stop-transfer run: `34773753125`
- CIBO stop-transfer artifact: `10322827806`
- CIBO stop-transfer GitHub digest: `sha256:aa497744bb988ac64acd34dd9191e26d764d620ddc7c1058e6e369b4b451e707`
- exact signal count: 152
- signal identity SHA-256: `f29bb0c1877b38f535671730c34623df9210465ae7743b640dac2c2d2c8e7d7d`

No Trader entry, market, anchor, side, target or stop-transfer threshold may change in this study.

## Scientific question

Can CIBO improve the account-level behavior of the same 152 VT-08 Index R1 signals by managing capital posture and requesting bounded Risk envelopes, while Risk remains sovereign over actual exposure?

The experiment measures account management only. It does not create, filter, cancel, redirect or reverse Trader signals.

## Frozen intratrade arms

All four already-observed stop families from R3.16 / PR #537 remain in scope, unchanged:

1. `off`
2. `soft`: +0.75R -> -0.50R; +1.25R -> 0R; +1.60R -> +0.50R
3. `be050-lock050-at100`: +0.50R -> 0R; +1.00R -> +0.50R
4. `aggressive`: +0.50R -> 0R; +1.00R -> +0.50R; +1.50R -> +1.00R

No stop family will be selected from the consumed result as an execution policy.

## Frozen account-level Risk envelopes

Transferred unchanged from the already-existing VT-08 R3.17 chronology policy, using the former A-risk dimension as the generic per-index-signal request:

- BASE per-signal requested risk: 1.00% of current equity
- BASE heat ceiling per simultaneous day+anchor group: 2.50%
- ATTACK per-signal requested risk: 2.00% of current equity
- ATTACK heat ceiling per simultaneous day+anchor group: 4.50%

This transfer is a research hypothesis. It is not a TTrades source rule and is not DEMO authorization.

## Frozen BANK policy

Transferred unchanged from R3.17 `bank25-t2`:

- profit trigger: +2.00% peak equity
- bank fraction: 25% of peak profit above starting equity
- minimum free cushion for ATTACK: 0.50% of current equity
- banked capital may ratchet upward only; it may never be silently unbanked

## Frozen Risk sovereignty ceilings

Transferred unchanged from R3.17:

- internal daily drawdown ceiling: 4.75%
- internal capital drawdown ceiling: 4.95%
- provider-style 5.00% daily/capital boundaries must never be touched
- Risk computes worst-case group loss before execution
- Risk may ALLOW, REDUCE or REJECT a CIBO request
- `CIBO request != RiskAuthorization`

## Frozen CIBO arms

For every stop family, evaluate all three account controllers. No controller may be selected for execution from this consumed study.

### A — RISK_ONLY_R100

- request BASE 1.00% per signal
- 2.50% heat ceiling
- no CIBO bank or attack
- same internal daily/capital Risk ceilings

### B — CIBO_BANK_ATTACK_R317_TRANSFER

CIBO posture is derived only from information available before the current day+anchor group:

- `BUILD`: equity <= starting equity and no banked profit
- `PROTECT`: equity > starting equity but ATTACK is not available
- `BANK`: protected bank floor ratchets higher and there is not yet enough free cushion to ATTACK
- `ATTACK`: banked profit exists and free cushion >= 0.50%
- `SUSPEND`: no permissible Risk headroom remains

CIBO emits BASE or ATTACK requests; Risk applies heat, daily floor, capital floor and bank floor and may reduce/reject.

### C — CIBO_FULL_GUARD_T1

This arm uses the same BANK/ATTACK contract and adds only the pre-existing R3.16 drawdown-reduction schedule from `bank50-ddlate`; no new index-derived threshold is introduced:

- capital drawdown >= 3.50% -> requested risk multiplier <= 0.75
- capital drawdown >= 4.25% -> requested risk multiplier <= 0.50
- capital drawdown >= 4.75% -> requested risk multiplier <= 0.25
- zero permissible headroom -> `SUSPEND`

`REDUCE` is a CIBO request posture only. Risk remains free to reduce further or reject.

## Frozen chronological replay

- starting equity: 1.000000
- source window: retained 2024-08-13 through 2026-09-11 evidence
- group signals by New-York trading date and anchor
- preserve all simultaneous cross-market signals within a group
- apply one capital observation before each group
- PnL = current equity * Risk-authorized fraction * observed trade R
- no compounding lookahead
- no outcome may affect the Risk request for its own group

## Frozen Monte Carlo

A deterministic 60-trading-day moving-block bootstrap is pre-registered before any account-level outcome is opened:

- source calendar: weekdays from 2024-08-13 through 2026-09-11 inclusive
- block length: 5 trading days
- paths: 10,000 per stop-family x controller arm
- seed: 2026091318
- preserve all within-day and within-anchor cross-market groups
- preserve no-trade weekdays

Report at minimum:

- terminal return P5 / median / mean / P95
- probability terminal return > 0
- probability of touching +5% and +10% during 60 days
- median / P95 / P99 maximum capital drawdown
- maximum observed daily drawdown
- maximum observed capital drawdown
- provider-boundary breaches (must be zero)
- Risk reductions and rejections
- CIBO BANK / ATTACK / REDUCE / SUSPEND counts

No Monte Carlo threshold determines CI success.

## Governance

- consumed evidence only
- no independent validation
- no retrospective market/anchor/side selection
- no stop-policy selection from these results
- no capital-controller selection from these results
- any changed threshold requires a distinct T2 identity and a new pre-economic freeze
- fresh unseen validation is mandatory before promotion
- DEMO_ELIGIBLE=false
- LIVE_AUTHORIZED=false
- PRODUCTION_AUTHORIZED=false
- keep DRAFT
- no merge
- no READY

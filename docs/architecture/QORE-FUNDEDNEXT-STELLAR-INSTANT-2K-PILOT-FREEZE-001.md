# QORE FundedNext Stellar Instant $2K Pilot Freeze 001

Verified against current FundedNext official surfaces and QORE frozen portfolio identities: 2026-09-13.

Status: IMPLEMENTATION / PRE-ACCOUNT / PRE-ORDER FREEZE.

This document authorizes implementation, tests, read-only integration and shadow execution only. It does not purchase an account, store credentials, submit an order, authorize real capital, merge a PR, or mark a PR ready.

## Constitutional topology

Provider rules constrain one sovereign account-wide Risk engine. They do not sit inside Trader methodology and CIBO does not issue capital authority.

Signal flow:

`VT08 -> CIBO REQUEST -> ACCOUNT-WIDE RISK -> RiskAuthorization -> MT5 EXECUTION`

Two independent Trader/CIBO lineages share the same account budget:

- `VT08_FOREX -> CIBO_FOREX -> ACCOUNT_WIDE_RISK`
- `VT08_INDEX -> CIBO_INDEX -> ACCOUNT_WIDE_RISK`

There is no independent Forex Risk budget plus independent Index Risk budget. Atomic reservation is mandatory so concurrent requests cannot spend the same provider/QORE headroom twice.

## Frozen pilot universe

Trader A — `VT08_FOREX`:

- AUDJPY -> AUDJPY
- GBPUSD -> GBPUSD
- GBPJPY -> GBPJPY

Trader B — `VT08_INDEX`:

- NAS100 -> NDX100
- SP500 -> SPX500
- US30 -> US30

The index aliases are provider routing identities and do not assert futures equivalence to NQ/ES/YM.

No other market is authorized for this pilot. In particular AUDUSD, EURUSD, USDCAD and USDJPY are out of scope even if FundedNext offers them.

## Trader certification boundary

Owner-side audit status at this implementation checkpoint:

- `VT08_FOREX_DEMO_APPROVED=true` for frozen B COMBINED only.
- official certification run: `34772576642`.
- official certification artifact: `10322482424`.
- certificate JSON SHA-256: `a4eb567592cedb4e92926881fb7a859c7b455329f00a4227d6886bbb1a33cf98`.
- `VT08_INDEX_DEMO_APPROVED=false`.
- post-certification Forex CIBO R3.17 research is NOT silently promoted.
- Index CIBO research #537-#539 is consumed evidence and does NOT promote an operating policy.

## Frozen product identity

- provider: FundedNext CFD
- product: Stellar Instant
- pilot nominal starting balance: USD 2,000
- target platform: MT5
- no Challenge / Evaluation phase
- no profit target prerequisite
- no Daily Loss Limit
- Maximum Loss Limit: 6% trailing
- fixed $2K initial MLL distance: $120
- initial provider floor: $1,880
- MLL rises with new closed-balance highs
- MLL never falls after losses
- MLL is capped at starting balance
- Performance Reward / payout does not reset the MLL lower
- equity below active MLL is a provider hard breach

Local verification recurrence:

`candidate_floor = highest_closed_balance - 0.06 * initial_balance`

`reconstructed_mll = min(initial_balance, max(previous_active_mll, candidate_floor))`

Provider-reported state is reconciled against this invariant. A provider value that would create more budget than the invariant is treated as a state conflict and fails closed; QORE may impose stricter limits but never widen provider budget.

## Current 3% maximum-risk rule

The current official Stellar Instant product page publishes `Max Risk 3% At any time`.

For the $2K pilot the implementation treats this conservatively as a maximum aggregate simultaneous stop-risk envelope of $60 until activation-time verification establishes a more precise provider interpretation. This is a QORE containment; it must never be used to enlarge the 6% MLL headroom.

## Current leverage conflict — fail closed

Two current official FundedNext surfaces conflict:

- Help Center Stellar Instant leverage: Forex 1:30, Indices 1:5, Commodities 1:7.5.
- Stellar Instant product page: Forex 1:30, Indices 1:10, Commodities 1:15.

QORE therefore MUST NOT size orders from either documentation leverage value.

Execution truth is fresh MT5 SymbolInfo/Specification for the exact purchased account and symbol. Until that exists, leverage-dependent order feasibility is unresolved and live submission remains disabled.

## Automation / EA rule

Current official Stellar Instant guidance permits Expert Advisors and Trading Bots on MT4/MT5 subject to provider conditions, including an additional EA usage fee/add-on where applicable, customization/strategy-uniqueness requirements, and prohibited-tool restrictions.

Any QORE automation that submits trades or only modifies SL/TP/lot size must be treated as EA/bot usage.

Before account activation, reverify the exact purchased product, region, MT5 availability, EA eligibility, EA add-on/fee state, prohibited strategies, VPS/IP rules and current Terms. Missing, stale or conflicting verification fails closed.

## Current costs frozen as mutable provider facts

Current official reference:

- Forex commission: USD 7 per lot, charged on opening.
- Indices commission: USD 0.

These values belong to provider/execution economics, not immutable TTrades methodology, and must be reverified before activation.

## Contract-size and live-symbol evidence

Static documentation is not sufficient for safe order sizing. Before every order, or after specification refresh, the MT5 boundary must obtain fresh execution facts for the exact provider symbol, including at minimum:

- bid / ask / spread;
- digits / point;
- contract size;
- tick size / tick value;
- minimum / maximum volume;
- volume step;
- minimum stop distance;
- freeze level where applicable;
- margin requirement/effective leverage;
- trade mode / session state;
- observation timestamp.

Missing/stale SymbolInfo fails closed.

## Account-wide shared Risk

Risk must consume simultaneously:

- current equity and balance;
- active MLL;
- open Forex stop risk;
- open Index stop risk;
- pending broker risk;
- QORE in-flight reservations;
- floating loss;
- margin/free margin;
- QORE internal reserve;
- CIBO requested envelope.

Every authorization is serialized/atomically reserved. A first request changes the headroom visible to a same-timestamp second request.

Risk can `ALLOW`, `REDUCE` or `REJECT`. CIBO can request posture/exposure but cannot mint a `RiskAuthorization`.

## Payout-aware budget

`CIBO BANK != provider floor mutation`.

Withdrawn profit is not available cushion. After any Performance Reward/payout, QORE must ingest actual account/provider state and recompute headroom before any BASE/REDUCED/ATTACK request is authorized.

## MT5 boundary

The repository contains a provider-scoped MT5 boundary with an injected gateway protocol. Credentials remain outside repository configuration.

Current implementation supports:

- account read;
- fresh SymbolInfo read;
- six-symbol normalization;
- broker-valid volume/SL/TP prechecks;
- deterministic idempotency;
- READ_ONLY and SHADOW suppression;
- explicit live-submission runtime gate;
- unknown-submit -> reconciliation-required suspension;
- duplicate-submit blocking.

A concrete secret-bearing MT5 gateway and actual account binding are NOT present yet. Therefore `MT5_ADAPTER_READY=false` for operational use even though the fail-closed boundary exists.

## Dry-run / shadow / order governance

Required progression:

`READ_ONLY -> SHADOW -> OPERATIONAL READINESS -> explicit Owner authorization -> naturally occurring certified setup`

READ_ONLY and SHADOW never submit provider orders.

No synthetic/random trade is permitted merely to test execution.

## Current official source references

FundedNext official Help Center / product surfaces used at this checkpoint:

- https://help.fundednext.com/en/articles/11641161-how-much-does-each-stellar-instant-account-cost
- https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/12439744-what-will-happen-to-the-maximum-loss-limit-after-a-trader-withdraws-from-a-stellar-instant-account
- https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant
- https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account
- https://help.fundednext.com/en/articles/8224087-fundednext-tradable-assets-what-can-i-trade-on-fundednext-cfd-accounts
- https://fundednext.com/usa/cfds/stellar-instant

Source conflicts are retained, not averaged away.

## Governance flags

- `VT08_FOREX_DEMO_APPROVED=true`
- `VT08_INDEX_DEMO_APPROVED=false`
- `FUNDEDNEXT_STELLAR_INSTANT_ADAPTER_READY=false`
- `SHARED_RISK_IMPLEMENTED=true`
- `CONCRETE_MT5_GATEWAY_BOUND=false`
- `ACTUAL_ACCOUNT_BOUND=false`
- `DRY_RUN_PASSED=false`
- `SHADOW_MODE_PASSED=false`
- `ACCOUNT_PURCHASE_AUTHORIZED=false`
- `ORDER_SUBMISSION_AUTHORIZED=false`
- `REAL_CAPITAL_AUTHORIZED=false`
- `LIVE_AUTHORIZED=false`
- `PRODUCTION_AUTHORIZED=false`
- keep PR DRAFT
- do not merge or mark ready

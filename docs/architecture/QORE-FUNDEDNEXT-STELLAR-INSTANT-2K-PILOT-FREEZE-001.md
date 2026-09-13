# QORE FundedNext Stellar Instant $2K Pilot Freeze 001

Verified against FundedNext official Help Center and QORE frozen portfolio identities: 2026-09-13

Status: PRE-IMPLEMENTATION / PRE-REPLAY COMPLIANCE FREEZE

This freeze authorizes implementation and research replay only. It does not purchase an account, store credentials, submit an order, authorize LIVE capital, merge a PR, or mark a PR ready.

## Mission

Prepare QORE to connect a FundedNext **Stellar Instant $2,000** MT5 account as a small-cost operational pilot for VT-08 + CIBO + sovereign Risk.

Constitutional chain:

`FundedNext product rules -> StellarInstantRiskBudget -> QORE Risk policy -> CIBO request -> RiskAuthorization -> MT5 execution adapter`

CIBO may request BUILD / PROTECT / BANK / REDUCE / ATTACK. CIBO never creates loss budget and never issues RiskAuthorization. Risk remains sovereign.

## Frozen product identity

- provider: FundedNext CFD
- product: Stellar Instant
- pilot initial balance: USD 2,000
- platform target: MT5
- no Challenge / Evaluation phase
- no profit target prerequisite
- no Daily Loss Limit
- Maximum Loss Limit (MLL): 6% of initial account balance
- fixed $2K MLL distance: **$120**
- initial MLL floor: **$1,880**
- MLL trails upward with new closed-balance highs
- MLL never moves downward after losses
- MLL is capped at the initial account balance
- after withdrawals / Performance Rewards, MLL does not reset lower
- equity below active MLL is a provider hard breach

Frozen replay recurrence:

`candidate_floor = highest_closed_balance - 0.06 * initial_balance`

`active_mll = min(initial_balance, max(previous_active_mll, candidate_floor))`

Provider-reported MLL is sovereign when available; local reconstruction is verification only.

## Leverage frozen for Stellar Instant

- Forex: 1:30
- Indices: 1:5
- Commodities: 1:7.5
- Crypto: 1:1
- Stock CFDs: 1:2

## Automation / platform rule

Current Stellar Instant product guidance permits customized EAs/indicators subject to provider rules. This pilot may expose an MT5 automated-capable route only after activation-time re-verification of the exact purchased product and EA fee/option state. Any mismatch fails closed.

## Recovered QORE portfolio identities

GitHub PR #528 and its committed R3.12 freeze are authoritative for the already-frozen portfolio identities:

- **A CORE = AUDJPY SHORT + GBPUSD SHORT**
- **GBPJPY RETURN ENHANCER = GBPJPY LONG + GBPJPY SHORT**
- **B COMBINED = A CORE + GBPJPY RETURN ENHANCER**

This is identity recovery from existing QORE governance, not a new market selection and not post-hoc tuning.

## Owner-authorized Stellar Instant pilot universe

The pilot MUST NOT introduce the full historical VT-08 universe. The only Forex instruments needed to preserve A / GBPJPY / B are:

- AUDJPY -> AUDJPY
- GBPUSD -> GBPUSD
- GBPJPY -> GBPJPY

The Owner additionally authorizes the existing index research set:

- NAS100 -> NDX100
- SP500 -> SPX500
- US30 -> US30

Therefore the exact unique six-symbol pilot universe is:

`AUDJPY, GBPUSD, GBPJPY, NAS100, SP500, US30`

Portfolio semantics remain frozen:

- A CORE executes only its existing AUDJPY SHORT and GBPUSD SHORT sleeves;
- GBPJPY RETURN ENHANCER preserves both existing GBPJPY LONG and SHORT sleeves;
- B COMBINED is the combination of A CORE plus the GBPJPY RETURN ENHANCER;
- the three index instruments remain a separate VT-08 index research/execution lineage and are not silently redefined as components of A or B.

No other Forex pair or index is authorized for this pilot. AUDUSD, EURUSD, USDCAD and USDJPY are explicitly out of scope for now even if FundedNext offers them.

`NAS100 -> NDX100` and `SP500 -> SPX500` are provider routing mappings and do not assert exact exchange-futures equivalence.

## Contract-size and live-symbol evidence

Current public FundedNext guidance reports Forex contract size 100,000 and indices contract size 10. Static public documentation does not establish every live MT5 value required for safe order sizing.

Before any order, the MT5 adapter MUST provide fresh SymbolInfo/Specification for the exact provider symbol, including:

- bid / ask / spread;
- contract size;
- minimum and maximum volume;
- volume step;
- tick size;
- tick value in account currency or verified conversion path;
- leverage / margin requirement;
- minimum stop distance where applicable.

QORE MUST NOT invent `0.01` lot, tick value, margin or any other broker parameter. Missing/stale fields fail closed.

## $2K pilot order-feasibility contract

For every proposed order Risk must additionally know entry, stop, target, current equity, balance, provider-reported MLL and aggregate open-position worst-case loss.

Risk must calculate:

1. provider headroom = `equity - active_mll`;
2. QORE authorizable headroom after internal reserve;
3. monetary stop loss at broker-valid rounded volume;
4. post-order worst-case equity across all open positions;
5. required/free margin;
6. whether the CIBO BASE / REDUCED / ATTACK request fits.

Risk rejects when volume rounding raises loss above budget, post-order worst-case equity reaches the MLL, margin is insufficient, or required market/account data is missing/stale.

## CIBO semantics for Stellar Instant

`BANK != provider floor mutation`.

The provider MLL is sovereign and already trails upward. CIBO must not invent another provider MLL. Any retained-profit or payout reserve has `QORE_POLICY` provenance only.

ATTACK is permitted only when Risk can authorize the full requested envelope after considering active MLL, current/open risk, QORE reserve, margin, broker-valid minimum volume and payout-retention policy.

After a payout, CIBO must not assume withdrawn profit restores loss budget. Risk recomputes from actual equity minus active MLL.

## Replay governance

The first replay may consume previously used evidence to validate mechanics, but cannot use P&L to change Trader rules, portfolio identity, market universe, anchors, direction, stop policy or CIBO thresholds.

Replay and future adapter work MUST be restricted to the six-symbol allowlist and frozen portfolio semantics above.

Any economic replay must disclose all pre-existing CIBO/stop-policy arms rather than cherry-pick a consumed-sample winner. Fresh unseen validation is required before promotion.

## Official sources frozen

FundedNext Help Center:

- https://help.fundednext.com/en/articles/11641117-what-are-the-available-account-sizes-for-the-stellar-instant-account
- https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/12439744-what-will-happen-to-the-maximum-loss-limit-after-a-trader-withdraws-from-a-stellar-instant-account
- https://help.fundednext.com/en/articles/11641614-what-rules-do-i-need-to-follow-in-the-stellar-instant-account
- https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/8224087-fundednext-tradable-assets-what-can-i-trade-on-fundednext-cfd-accounts
- https://help.fundednext.com/en/articles/8020350-what-is-the-contract-size-of-the-instruments
- https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext

QORE identity evidence:

- PR #528 — VT-08 R3.12 adaptive prop-firm risk and monthly growth Monte Carlo
- `docs/trader_lab/vt08-r3-12-adaptive-prop-risk-freeze.md` at R3.12 HEAD

## Governance

- account_purchase_authorized: false
- credentials_present: false
- orders_submitted: false
- trader_methodology_mutation: false
- portfolio_identity_mutation: false
- provider_selected_by_backtest_result: false
- market_universe_expansion_authorized: false
- A_CORE_identity_recovered: true
- GBPJPY_RETURN_ENHANCER_identity_recovered: true
- B_COMBINED_identity_recovered: true
- pilot_unique_market_count: 6
- DEMO_ELIGIBLE: false
- LIVE_AUTHORIZED: false
- PRODUCTION_AUTHORIZED: false
- keep PR DRAFT
- do not merge or mark ready

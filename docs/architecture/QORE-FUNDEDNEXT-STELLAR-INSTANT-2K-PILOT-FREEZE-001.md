# QORE FundedNext Stellar Instant $2K Pilot Freeze 001

Verified against FundedNext official Help Center: 2026-09-13

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
- account sizes currently published: 2,000 / 5,000 / 10,000 / 20,000 USD
- no Challenge / Evaluation phase
- no profit target prerequisite
- no Daily Loss Limit
- Maximum Loss Limit (MLL): 6% of the initial account balance
- for the $2,000 pilot, fixed MLL distance = **$120**
- initial MLL floor = **$1,880**
- MLL trails upward when closed balance makes a new high
- MLL never moves downward after losses
- MLL is capped at the initial account balance
- after withdrawals / Performance Rewards, the MLL does not reset lower
- account is hard breached if equity falls below the active MLL

Frozen MLL recurrence for QORE replay:

`candidate_floor = highest_closed_balance - 0.06 * initial_balance`

`active_mll = min(initial_balance, max(previous_active_mll, candidate_floor))`

The initial active MLL is `initial_balance * 0.94`.

QORE MUST preserve provider-reported MLL when the live adapter supplies it; locally reconstructed MLL is a verification calculation, not authority to override the provider.

## Leverage frozen for Stellar Instant

- Forex: 1:30
- Indices: 1:5
- Commodities: 1:7.5
- Crypto: 1:1
- Stock CFDs: 1:2

## Automation / platform rule

Current FundedNext Stellar Instant product guidance explicitly permits customized EAs and indicators subject to provider rules. Current generic FundedNext automation guidance permits EAs/bots on MT4/MT5 for accounts below $50,000 and forbids automation on cTrader / Match-Trader.

Therefore this pilot may expose an **MT5 automated-capable route** only after activation-time re-verification of the exact purchased product and EA fee/option state. Any mismatch fails closed.

## Owner-authorized VT-08 pilot market universe

The pilot MUST NOT introduce the full historical VT-08 universe. Only markets explicitly retained by the Owner because they have worked so far are permitted.

Frozen allowlist for this pilot:

- owner alias `A` — exact canonical symbol unresolved in this freeze; FAIL CLOSED until explicitly bound;
- GBPJPY -> GBPJPY;
- owner alias `B` — exact canonical symbol unresolved in this freeze; FAIL CLOSED until explicitly bound;
- NAS100 -> NDX100;
- SP500 -> SPX500;
- US30 -> US30.

No other Forex pair or index is authorized for this Stellar Instant pilot. In particular, AUDJPY, AUDUSD, EURUSD, GBPUSD, USDCAD and USDJPY MUST NOT be added merely because FundedNext offers them.

`A` and `B` are Owner labels, not inferred symbols. QORE MUST NOT guess their identity. Until the Owner binds each alias to an exact QORE canonical symbol and FundedNext MT5 symbol, they are non-executable and excluded from replay/order routing.

The index mapping is identity/proxy routing only. `NAS100 -> NDX100` and `SP500 -> SPX500` do not assert exact exchange-futures equivalence.

## Contract-size evidence

Current FundedNext contract-size guidance states:

- Forex contract size: 100,000
- Indices contract size: 10

These values are reported as applying to all FundedNext accounts.

However, static public documentation does **not** establish the exact live MT5 values needed for safe order sizing for every symbol: minimum volume, volume step, tick size, tick value, spread, margin currency/conversion and broker-side minimum stop distance.

Therefore the execution feasibility gate MUST ingest the live MT5 SymbolInfo/Specification before authorizing any order. QORE MUST NOT invent `0.01` lot or any other minimum volume.

## $2K pilot order-feasibility contract

For each proposed order Risk must have, from the live provider adapter:

- canonical QORE symbol and provider symbol;
- bid / ask / spread;
- contract size;
- minimum volume;
- maximum volume;
- volume step;
- tick size;
- tick value in account currency or a verified conversion path;
- leverage / margin requirement;
- entry, stop and target;
- current equity, balance and provider-reported MLL;
- current open-position worst-case loss.

Risk must calculate:

1. provider headroom = `equity - active_mll`;
2. QORE authorizable headroom after internal safety reserve;
3. monetary stop loss at broker-valid rounded volume;
4. post-order worst-case equity including all open positions;
5. required margin and free margin;
6. whether CIBO BASE / REDUCED / ATTACK requested exposure fits.

Risk rejects when any required symbol specification is absent or stale, when volume rounding raises loss above budget, when post-order worst-case equity reaches the MLL, or when margin is insufficient.

## CIBO semantics for Stellar Instant

`BANK != provider floor mutation`.

The provider MLL is sovereign and already trails upward. CIBO must not invent another trailing provider floor. CIBO can maintain a separate strategic retained-profit / payout reserve, but it has `QORE_POLICY` provenance only.

ATTACK is permitted only when Risk can authorize the requested envelope after considering:

- active provider MLL;
- floating/open-position worst-case loss;
- QORE safety reserve;
- margin headroom;
- broker minimum volume;
- any payout-retention reserve.

After a payout, because provider MLL does not reset downward, CIBO must not assume that withdrawn profit restores loss budget. Risk must recompute from actual equity minus active MLL.

## Replay governance

The first replay may consume previously used VT-08 evidence to validate mechanics, but is research-only. It cannot select a new Trader rule, market, anchor, direction, stop policy, or CIBO threshold from P&L.

Replay and future adapter work MUST be restricted to the Owner-authorized pilot allowlist above. No market may be added because it exists at FundedNext or because it performed well in a post-hoc scan.

Any economic replay must report all pre-existing CIBO/stop-policy arms rather than cherry-pick the best consumed-sample arm.

Fresh unseen validation is required before any promotion.

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

## Governance

- account_purchase_authorized: false
- credentials_present: false
- orders_submitted: false
- trader_methodology_mutation: false
- provider_selected_by_backtest_result: false
- market_universe_expansion_authorized: false
- owner_alias_A_bound: false
- owner_alias_B_bound: false
- DEMO_ELIGIBLE: false
- LIVE_AUTHORIZED: false
- PRODUCTION_AUTHORIZED: false
- keep PR DRAFT
- do not merge or mark ready

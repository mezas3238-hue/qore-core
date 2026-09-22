# QORE Provider Contract Freeze 001

## FTMO + FundedNext Challenge operating contracts

Verified: 2026-09-13

Status: PRE-EXECUTION COMPLIANCE FREEZE

This document freezes QORE's provider-facing rule model before any provider-specific
economic replay. It is a compliance contract, not Trader methodology and not a CIBO
optimization.

## Constitutional boundary

The authority chain is:

`Provider rules -> ProviderRiskBudget -> QORE Risk policy -> CIBO request -> RiskAuthorization -> Execution`

Provider rules are external hard constraints. QORE internal reserves are separate,
more-conservative policy and MUST NOT be labelled as provider rules. CIBO may request
BASE/REDUCED/ATTACK but cannot create provider loss budget and cannot issue a
RiskAuthorization.

## Frozen Challenge profiles

### FTMO Challenge: 1-Step

- profit target: 10% of initial simulated capital;
- maximum daily loss amount: 3% of initial simulated capital;
- daily floor: balance recorded at 00:00 CE(S)T minus that fixed 3% amount;
- maximum loss amount: 10% of initial simulated capital;
- maximum-loss floor: end-of-day trailing, based on the highest balance recorded at
  00:00 CE(S)T of any preceding trading day or initial capital, whichever is higher,
  minus the fixed 10% amount;
- the maximum-loss floor may increase but not decrease;
- Best Day Rule: best profitable day must be <= 50% of Positive Days' Profit for
  challenge completion; exceeding it is not itself a hard loss breach;
- unlimited trading period;
- automated/algo/EA trading is provider-supported subject to FTMO forbidden-practice,
  server-activity and replicability requirements.

### FTMO Challenge: 2-Step

Phase 1:
- profit target: 10%;
- maximum daily loss amount: 5%;
- maximum loss: 10% static from initial simulated capital;
- minimum trading days: 4.

Phase 2 / Verification:
- profit target: 5%;
- maximum daily loss amount: 5%;
- maximum loss: 10% static from initial simulated capital;
- minimum trading days: 4.

For both phases the daily floor is the balance recorded at 00:00 CE(S)T minus the
fixed 5% of initial capital. The overall floor does not move upward with profits.
The trading period is unlimited.

### FundedNext Stellar 1-Step Challenge

- profit target: 10%;
- daily loss amount: 3% of initial balance;
- maximum loss: 6% of initial balance, static floor at 94% of initial balance;
- minimum trading days: 2 separate trading days;
- daily loss resets at 00:00 FundedNext server time;
- FundedNext CFD server time is GMT+3 during daylight-saving operation and GMT+2
  otherwise;
- daily loss includes closed results plus running/floating loss and applicable swaps,
  commissions and fees;
- intraday profit increases the loss room available during that same provider day,
  while the fixed daily-loss amount resets on the next server day;
- no time limit for the profit target.

### FundedNext Stellar 2-Step Challenge

Phase 1:
- profit target: 8%;
- daily loss amount: 5% of initial balance;
- maximum loss: 10% of initial balance, static floor at 90% of initial balance;
- minimum trading days: 5 separate trading days.

Phase 2:
- profit target: 5%;
- daily loss amount: 5%;
- maximum loss: 10% static from initial balance;
- minimum trading days: 5 separate trading days.

Daily reset and P/L inclusion semantics are the same FundedNext CFD semantics stated
above. The trading period is unlimited.

## Execution capability contract

Execution capability is a tuple of provider + exact product/ruleset + program +
platform + account size + account options. It is not inferred from provider name alone.

FTMO:
- algorithmic trading and EAs are allowed when the strategy is legitimate,
  market-replicable and compliant with FTMO forbidden practices;
- FTMO currently offers MT4, MT5 and cTrader among supported platforms and cTrader
  exposes algorithmic/Open API capability;
- QORE freezes automated routing only for cTrader, MT4 and MT5 in this contract;
  any platform not explicitly frozen fails closed until a separate adapter is
  verified at activation.

FundedNext source conflict adjudication:
- the current general FundedNext EA article states that MT4/MT5 accounts below
  USD 50,000 may use EAs/bots with the relevant paid option and conditions, while
  accounts at USD 50,000 or above are manual-only;
- the current product-specific `FundedNext CFD — Stellar 1-Step` rule page states
  that EAs and third-party indicators are not permitted;
- current cTrader and Match-Trader guidance independently prohibits automated/algo
  trading regardless of account size;
- because generic and product-specific official documents diverge, QORE MUST NOT
  infer automated authority for a FundedNext account from the generic EA article;
- until the exact purchased product/account rules are re-verified and represented by
  an explicit product-scoped execution contract, every FundedNext MT4/MT5 binding is
  routed as `MANUAL_HANDOFF`, even when an EA add-on is present;
- FundedNext cTrader/Match-Trader bindings below USD 100,000 are also
  `MANUAL_HANDOFF`; automated submission remains prohibited;
- current provider platform guidance states that USD 100,000 and USD 200,000
  accounts are not available for purchase/reset/top-up on cTrader or Match-Trader
  (with a U.S.-specific Match-Trader exception that is not generalized here), so
  QORE rejects those bindings rather than silently switching platforms;
- unknown combinations fail closed.

A manual-handoff capability may still permit QORE to calculate a setup, CIBO posture
and Risk decision, but the execution adapter must not submit the order automatically.

## Provider budget semantics

Every provider budget evaluation MUST expose at least:

- provider hard daily floor;
- provider hard overall floor;
- daily headroom;
- overall headroom;
- effective provider headroom = minimum of daily and overall headroom;
- hard-breach state;
- stage progress: profit target and minimum trading days;
- execution automation capability.

For static-overall-loss profiles, profits create genuine additional distance from the
provider overall floor. QORE MUST NOT turn that into a new trailing provider floor.

For FTMO 1-Step, intraday peaks MUST NOT trail the maximum-loss floor. Only the
provider's 00:00 CE(S)T end-of-day balance checkpoints may advance the stored high
used by the trailing overall-loss rule.

## QORE internal policy separation

Values such as the R3.17 research ceilings 4.75% / 4.95% are QORE research/internal
policy. They are not FTMO or FundedNext rules. If retained as a safety overlay they
must have `QORE_POLICY` provenance and be evaluated after provider headroom is known.
They may make Risk more conservative but can never enlarge provider budget.

## Activation fail-closed rules

Before a Challenge account adapter is enabled, QORE must re-verify the provider
profile against current official terms and bind:

- exact provider;
- exact product/ruleset;
- exact program/model;
- exact phase;
- exact account initial balance;
- exact platform;
- automation/add-on capability;
- provider/server timezone;
- profile version and source evidence.

Provider documentation can change and product-specific help pages can diverge. The
activation check therefore re-verifies the exact purchased account/program instead of
assuming that this 2026-09-13 freeze is eternally valid.

Any unknown or mismatched value means automated execution is not authorized.

## Official source inventory

FTMO:
- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/
- https://ftmo.com/en/faq/which-platforms-can-i-use-for-trading/
- https://ftmo.com/en/trading-platforms/
- https://ftmo.com/en/forbidden-trading-practices/

FundedNext:
- https://help.fundednext.com/en/articles/8021061-what-are-the-rules-for-the-stellar-1-step-challenge-at-fundednext
- https://help.fundednext.com/en/articles/12673301-what-rules-do-i-need-to-follow-in-the-stellar-1-step-challenge-at-fundednext-cfd
- https://help.fundednext.com/en/articles/8021076-what-rules-do-i-need-to-follow-in-the-stellar-2-step-challenge
- https://help.fundednext.com/en/articles/8030875-what-is-the-profit-target-of-the-stellar-1-step-challenge
- https://help.fundednext.com/en/articles/8021071-what-is-the-profit-target-of-the-stellar-2-step-challenge
- https://help.fundednext.com/en/articles/8019811-how-can-i-calculate-the-daily-loss-limit
- https://help.fundednext.com/en/articles/8019812-how-can-i-calculate-the-maximum-loss-limit
- https://help.fundednext.com/en/articles/8394309-when-does-the-daily-loss-limit-reset-with-fundednext-cfd
- https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext
- https://help.fundednext.com/en/articles/8019808-which-platforms-can-i-use-for-trading-at-fundednext

## Governance

This freeze authorizes implementation and tests only. It does not select FTMO over
FundedNext, does not alter VT-08 methodology, does not authorize real-capital trading,
and does not confer DEMO/LIVE/PRODUCTION authority.

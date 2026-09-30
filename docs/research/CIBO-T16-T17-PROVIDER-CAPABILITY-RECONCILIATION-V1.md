# CIBO Architect B — T16/T17 Provider Capability Reconciliation V1

Observed: 2026-09-30  
Status: **PROVIDER-POLICY RECONCILED / ACCOUNT-SPECIFIC CAPABILITY STILL FAIL-CLOSED**

This note narrows T16/T17 without fabricating account capabilities.

## Official sources

1. cTrader — Trading accounts  
   https://help.ctrader.com/ctrader/trading-accounts/

   Current documentation states that cTrader supports both hedging and netting
   account types. A hedging account can hold long and short positions on the
   same symbol simultaneously. The same page explicitly warns that not all
   brokers support different account types.

2. FundedNext — Restricted/prohibited strategies  
   https://help.fundednext.com/en/articles/8020351-what-are-the-restricted-prohibited-trading-strategies

   Current policy permits hedging only within the same FundedNext account and
   prohibits cross-account hedging.

3. FundedNext — Tradable assets for CFD accounts  
   https://help.fundednext.com/en/articles/8224087-fundednext-tradable-assets-what-can-i-trade-on-fundednext-cfd-accounts

   The current page describes its list as the comprehensive CFD symbol list and
   enumerates Forex, indices/commodities, crypto and stocks. It does not expose
   an option/defined-risk-spread instrument class.

## T16 interpretation — Hedged Exposure / Risk Transfer

T16 requires more than the ability to hold opposite same-symbol positions.
Its registry contract requires:

- a hedge instrument;
- measurable basis risk;
- hedge cost;
- correlation stability;
- provider-valid execution support;
- net economic benefit.

Therefore:

- cTrader platform documentation establishes that a hedging account type
  exists, but **does not certify the actual connected DEMO account** or any
  cross-instrument hedge relationship;
- FundedNext policy establishes that same-account hedging is permitted, but
  does **not** prove basis-risk, cost, correlation or economic benefit.

T16 remains fail-closed until the actual account/provider catalog and economics
are observed and bound.

## T17 interpretation — Convex / Limited-Downside Exposure

For the FundedNext CFD program, the official comprehensive asset list contains
no option/defined-risk-spread instrument class. The program is therefore
provider-policy **UNAVAILABLE for option structures** unless FundedNext later
changes the account-specific instrument universe.

This conclusion is intentionally scoped to FundedNext CFDs. It is not a global
claim about cTrader. The actual cTrader DEMO broker/account symbol catalog must
still be observed; cTrader is a platform and broker capabilities vary.

## Required machine evidence before closure

The existing `ProviderInstrumentCapabilityRegistry` must receive account-bound
evidence with:

- provider key and opaque account reference;
- exact environment/program;
- observed account type;
- observed symbol/instrument catalog;
- observation timestamp;
- immutable source hash;
- capability status `SUPPORTED`, `CONDITIONALLY_SUPPORTED`,
  `UNAVAILABLE` or `UNKNOWN`;
- explicit conditions when conditional.

No missing capability is converted into support. No cTrader platform feature is
silently treated as broker/account support.

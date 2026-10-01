# CIBO Architect B — T16/T17 Provider Capability Reconciliation V1

Observed: 2026-09-30  
Status: **ACCOUNT-BOUND PROVIDER EVIDENCE SEALED / T17 STRUCTURAL DISPOSITION READY / T16 ECONOMIC HEDGE STILL OPEN**

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


## Machine-readable account taxonomy bridge

Architect B now has an additional provider-native evidence surface:

`cibo_ctrader_demo_instrument_taxonomy.py`

It binds the observed DEMO account catalog to cTrader's account-scoped symbol
categories and asset classes. The binding is deterministic, hashed and
read-only. Consumers recompute enabled-symbol coverage before trusting the
taxonomy-complete flag.

This narrows T17 but deliberately does not promote it:

- taxonomy incomplete -> `T17_ACCOUNT_TAXONOMY_BINDING_INCOMPLETE`;
- explicit option taxonomy candidate -> further instrument/execution proof is
  still required;
- no explicit option taxonomy candidate -> T17 remains fail-closed rather than
  treating symbol-name absence as universal proof.

T16 is unchanged: account mode and taxonomy do not establish economic hedge
utility. Basis risk, cost, correlation, execution feasibility and fresh OOS
utility remain mandatory.


## Limited-Risk / Guaranteed Stop Loss equivalent candidate

The current cTrader Open API also exposes a provider-native limited-downside
mechanism that must be evaluated before T17 can be falsified solely from the
absence of options:

- `ProtoOATrader.isLimitedRisk`;
- `ProtoOATrader.limitedRiskMarginCalculationStrategy`;
- `ProtoOASymbol.guaranteedStopLoss`;
- `ProtoOASymbol.gslDistance`;
- `ProtoOASymbol.gslCharge`.

Architect B now captures these fields read-only and produces a sanitized,
account-fingerprint-bound assessment:

`qore.cibo.t17.limited_risk_capability.v1`

This assessment may identify a **provider-native GSL candidate** when the
connected account is Limited Risk and the observed QORE provider universe has
complete GSL support.

That is not terminal T17 proof. The assessment hard-codes:

- `option_structure_proven=false`;
- `defined_risk_spread_proven=false`;
- `gsl_execution_economics_proven=false`;
- `fresh_oos_utility_demonstrated=false`;
- `t17_policy_ready=false`;
- `productive_authority=false`.

If a GSL candidate exists, B still needs empirical execution/cost evidence and
fresh OOS economic utility before it can become a terminal T17 disposition.


## Structural-disable rule

The Calibration Freeze permits T16/T17 to be `STRUCTURALLY_DISABLED`, but B must
not derive that disposition from silence. In particular, none of the following is
sufficient by itself:

- a NETTED account type;
- absence of an `Option` token in broker-defined taxonomy labels;
- absence of option-looking symbol names;
- `isLimitedRisk=false` without instrument-level GSL evidence;
- incomplete or unknown GSL fields.

A structural-disable handoff requires explicit account/provider-bound evidence that
all admissible capability paths are unavailable for the governed CIBO universe. If
that evidence is incomplete, the disposition remains fail-closed/open rather than
being converted into provider unavailability.


## 2026-10-01 account-bound disposition

GitHub Actions run `36806511867` completed successfully at HEAD
`6dc4a22dac0a54368917bb9308d04dd83eec079f` and sealed current cTrader DEMO provider/account evidence.

The durable sanitized snapshot is:

`docs/research/CIBO-B-CTRADER-DEMO-PROVIDER-EVIDENCE-2026-10-01.json`

Observed facts:

- the account type is `HEDGED`;
- the complete account catalog contains 352 symbols;
- taxonomy binding is complete across 11 provider asset classes;
- no explicit option taxonomy candidate exists;
- `isLimitedRisk=false`;
- all six governed CIBO symbols have explicit
  `guaranteedStopLoss=false`;
- GSL coverage has no unknown rows;
- no Limited-Risk/GSL candidate exists.

The earlier structural-disable rule required the combination of complete
taxonomy plus explicit instrument-level Limited-Risk/GSL evidence. That
condition is now satisfied for cTrader DEMO rather than inferred from silence.

For FundedNext Stellar Instant CFDs, the official current comprehensive symbol
policy enumerates Forex, indices, commodities, crypto and stocks and does not
list an option/defined-risk instrument class.

Therefore Architect B emits:

`docs/research/CIBO-B-T17-STRUCTURAL-DISPOSITION-V1.json`

with recommended calibration-freeze disposition
`STRUCTURALLY_DISABLED` and recommended master-ledger disposition
`FALSIFIED_AND_CLOSED`.

This disposition is scoped to the current governed provider universe. It is
not a claim that T17 is impossible in global markets. It must be reopened if
cTrader or FundedNext later exposes an admissible option, defined-risk, Limited
Risk or Guaranteed Stop Loss path.

T16 does **not** receive the same disposition. The observed cTrader account is
HEDGED, so structural unavailability is false. T16 remains open for actual
hedge-instrument basis risk, cost, correlation, execution and fresh OOS
economic utility.


## T16 anti-selection preregistration

A T16 hedge pair must be declared before the first return window consumed by
the audit. The declaration fixes provider, target symbol and hedge symbol.
Choosing the pair after observing correlation, basis residual or costs is
rejected as causal contamination. This requirement is independent from the
later fresh-OOS utility gate.

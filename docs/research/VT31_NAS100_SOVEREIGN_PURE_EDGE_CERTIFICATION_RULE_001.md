# VT31 NAS100 — Sovereign Pure-Edge Certification Rule 001

**Owner:** Sergio Meza  
**Authority:** Owner sovereign directive  
**Source of truth:** GitHub `mezas3238-hue/qore-core`

## Certification identity

VT31 may certify only through:

`ENTRY EDGE + EXIT EDGE + WINNER PRESERVATION`

Capital engineering is outside the trader certification exam.

## Forbidden certification mechanisms

VT31 certification may not improve results through:

- sizing;
- dynamic position sizing;
- leverage;
- compounding;
- CIBO capital rescue;
- risk-based volume reduction;
- loss-compensating volume increases;
- risk budgeting;
- portfolio allocation;
- route-dependent capital weighting;
- any rule deciding how much to trade from R.

## Sovereign role of R

R is an **evaluation metric only**.

R may be computed after or alongside replay for:

- expectancy;
- drawdown;
- payoff;
- MAE;
- MFE;
- profit;
- loss;
- stability;
- Monte Carlo;
- cost stress;
- winner preservation.

R may **not** govern runtime:

- admission;
- entry price;
- entry timing;
- invalidation;
- stop movement;
- breakeven;
- target selection;
- exit;
- trailing;
- partials;
- volume.

Canonical rule:

> R IS AN EVALUATION METRIC, NOT AN ENTRY, EXIT OR VOLUME ENGINE.

## Universal volume invariance

VT31 market decisions are independent of absolute volume.

The same market opportunity must produce the same:

- admission decision;
- entry;
- invalidation;
- target;
- management;
- exit;

whether the provider executes 0.01, 0.02, 0.05, 0.10, 1.00 or any other
provider-permitted amount.

Provider lot minimums, maximums, steps and rounding belong only to the provider
adapter.

VT31 produces the trade. Volume scales only the economic amount of that same
trade.

## Entry repair principle

If an entry requires an impractically wide stop, the repair must be inside the
trader:

- better structure reading;
- better liquidity reading;
- better context;
- better regime interpretation;
- better volatility interpretation;
- better H1/M15/M1 alignment;
- better confirmation;
- better M1 location;
- better timing;
- better invalidation;
- rejection of aged opportunity.

The defect may not be hidden by reducing position size.

## Exit repair principle

Artificial R caps such as +0.50R, +0.75R or +1.00R are not valid runtime
solutions.

VT31 exits must come from market-native causes:

- structural target;
- liquidity destination;
- exhaustion;
- regime change;
- invalidation;
- momentum deterioration;
- loss of structure;
- structural trailing;
- target intelligence.

Any exit rule that destroys winner-R fails the certification objective.

## Legacy incompatibility

Any legacy VT31 simulator or candidate using a runtime rule such as
`3R -> breakeven` is **not certification-authoritative** under this rule.

Legacy code may remain for provenance and comparison, but the pure-edge
certification path must not use it as runtime authority.

## Final principle

> DO NOT ADAPT CAPITAL TO SAVE THE TRADE.
>
> ADAPT TRADER INTELLIGENCE TO PRODUCE A BETTER TRADE.

No merge, LIVE, real-capital or production authority is granted by this rule.

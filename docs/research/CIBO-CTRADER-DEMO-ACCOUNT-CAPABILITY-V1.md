# CIBO cTrader DEMO Account Capability Observation V1

Status: **READ-ONLY CONTRACT IMPLEMENTED / REAL ACCOUNT OBSERVATION REQUIRED**

Architect B now has a read-only collector for the two provider facts required
before T16/T17 can be reasoned about safely:

1. `ProtoOATraderReq -> ProtoOATrader.accountType`;
2. `ProtoOASymbolsListReq -> complete non-archived account symbol catalog`.

The official cTrader Open API model defines `accountType` as HEDGED, NETTED
or SPREAD_BETTING and the symbols-list response as the list of symbols available
to that trader account.

## Critical non-inference rule

`accountType=HEDGED` means only that the account can hold opposite
same-symbol positions. It is **not** CE2I T16 certification.

The collector therefore hard-codes:

- `t16_hedge_instrument_certified=false`;
- `t17_option_structure_certified=false`;
- `productive_authority=false`.

T16 still requires an identified hedge instrument plus basis risk, hedge cost,
correlation stability, execution support and fresh OOS economics.

T17 still requires account-bound provider evidence for an option or other
explicitly limited-downside structure. Symbol-name guessing is prohibited.

## Determinism

The complete account catalog is normalized and hashed. Missing optional
`accountType` stays `UNKNOWN`; protobuf default zero is never silently
interpreted as HEDGED when field presence is absent.

## Governance

The collector sends no new/amend/cancel/close order request and grants no
DEMO/LIVE/real-capital authority. It is an observation primitive for B's
provider-capability closure only.

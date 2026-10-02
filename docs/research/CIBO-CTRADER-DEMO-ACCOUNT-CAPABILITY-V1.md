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


## Account-bound instrument taxonomy

The read-only provider observation now also resolves the account's native
instrument taxonomy through:

- `ProtoOAAssetClassListReq`;
- `ProtoOASymbolCategoryListReq`.

The symbol catalog's `symbolCategoryId` values are reconciled against the
provider-returned category and asset-class graph. The taxonomy receives its own
SHA-256 and is accepted as complete only when every enabled account symbol is
bound through:

`symbol -> symbol category -> asset class`.

Consumer boundaries recompute this coverage instead of trusting a serialized
`catalog_binding_complete` flag.

An explicit provider taxonomy label containing `option/options` is only a
candidate for further inspection. It does **not** certify T17. T17 still needs
account-bound instrument, execution and economic evidence. Absence of such a
label is likewise not silently upgraded into a universal platform claim.

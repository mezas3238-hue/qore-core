# QORE-UMI14-CRYPTO-STAKING-TOKENIZATION-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — LANE 8 / UMI13-UNR-010 — PREPARATORY CORRECTION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracker: #390  
Parent audit: #363  
Starting certified baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`

This artifact closes only the bounded static D04 representation gap identified for
staking/yield-bearing/tokenized products. It does not certify a provider, blockchain,
validator, wallet, custody path, legal status, settlement path, execution path,
Production environment or real capital.

## 1. Evidence boundary

Exact QORE evidence at the opening baseline:

- UMI-08 source: `src/qore/infrastructure/crypto_perpetual_funding_semantics.py`;
- UMI-08 source blob: `f459f73bf5d5eb2556e207b3ebfdf591edde79d8`;
- UMI-08 architecture blob: `bba67cc77d9332ef45cfa231856d04508c11e02d`;
- UMI-13 architecture blob: `ec51c900c2701f885053141601a7792cdf74856e`.

UMI-13 retains:

`UMI13-UNR-010 — crypto-digital-assets — staking/yield-bearing/tokenized products`

and explicitly records:

`funding observation != staking; tokenized security crosses domains`.

External product/standard evidence used for the financial falsification:

- Ethereum Proof-of-Stake documentation distinguishes deposited stake, validator
  participation, rewards, penalties/slashing and withdrawals;
- ERC-4626 defines tokenized-vault shares over an underlying token and explicit
  share/asset conversion semantics;
- ERC-3643 defines security-token identity/compliance interfaces.

These sources prove material product distinctions. They do not prove QORE provider,
execution, legal or operational support.

## 2. Adjudication

`VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`

UMI-08 remains sovereign for crypto perpetual/funding/network qualification and is
reused rather than modified.

The surviving collisions are:

1. perpetual funding convention != staking arrangement;
2. staked/principal asset != optional staking receipt/liquid token;
3. static exit convention != current withdrawal queue or availability;
4. yield-bearing token/share != underlying identity;
5. yield mechanism != current APR, reward amount or exchange ratio;
6. native on-chain security issuance != tokenized representation of an existing
   security identity;
7. tokenized-security qualification != legal/compliance determination.

## 3. Candidate inventory

The candidate adds:

- `CryptoStakingModeCode`;
- `CryptoStakingExitScheduleCode`;
- `CryptoStakingPenaltyPolicyCode`;
- `CryptoYieldMechanismCode`;
- `CryptoRepresentationRoleCode`;
- `CryptoStakingExitMode`;
- `CryptoTokenizedSecurityForm`;
- `CryptoStakingExitTerms`;
- `CryptoRepresentationBinding`;
- `CryptoStakingTerms`;
- `CryptoYieldBearingTokenTerms`;
- `CryptoTokenizedSecurityQualificationTerms`.

It reuses UMI-08 `CryptoTermsId`, `CryptoEvidenceRef` and
`CryptoNetworkBindingTerms`, and UMI-02 `EconomicIdentityId` plus exact
`IdentityRelationship`.

## 4. Staking arrangement semantics

`CryptoStakingTerms` retains static contractual material only:

- staked/principal economic identity;
- reward economic identity;
- extensible staking-mode code;
- explicit exit convention;
- optional penalty/slashing-policy code;
- optional exact staking-receipt relationship;
- optional existing UMI-08 network binding;
- evidence reference.

Reward identity may equal the staked asset identity. QORE therefore does not invent a
universal separate reward currency.

An optional receipt relationship must target the staked asset. Its source is the
receipt/liquid-token identity and remains a distinct UMI-02 economic identity by the
UMI-02 relationship invariant.

No stake balance, accrued reward, APR, validator status, current exit queue, slashing
amount or observed network state is retained.

## 5. Exit/unbonding boundary

The static exit vocabulary distinguishes:

- `IMMEDIATE`;
- `FIXED_DELAY` with strict positive integer seconds;
- `GOVERNED_SCHEDULE` with typed schedule code;
- `NETWORK_GOVERNED` with no invented current delay.

`NETWORK_GOVERNED` deliberately preserves the fact that exit timing is controlled by
network rules/state without pretending the current queue or completion time is known.

`EXIT CONVENTION != CURRENT EXIT AVAILABILITY`

D06 owns current clock/schedule resolution. D05 owns observed network state.

## 6. Exact representation binding

`CryptoRepresentationBinding` retains the exact UMI-02 `IdentityRelationship`, an
owner-local typed role code and evidence reference.

The role code must equal the exact UMI-02 relationship code. Therefore a relationship
with unrelated semantics cannot be laundered into staking/yield/tokenization merely
because its endpoints happen to fit.

The candidate does not create a second identity graph, choose the current relationship
revision, or infer cross-revision precedence.

## 7. Yield-bearing token semantics

`CryptoYieldBearingTokenTerms` retains:

- token/share economic identity;
- underlying economic identity;
- exact representation relationship binding;
- extensible yield/accrual mechanism code;
- optional network binding;
- evidence reference.

Token and underlying identities must differ. Relationship source must be the token and
target must be the underlying.

No current exchange ratio, NAV, reward amount, APR/APY, price or valuation value is
stored or calculated. An ERC-4626-style share/asset relationship can therefore be
represented without turning D04 into a valuation engine.

## 8. Tokenized-security qualification

`CryptoTokenizedSecurityQualificationTerms` distinguishes two static forms:

- `NATIVE_ONCHAIN_ISSUANCE` — the security identity is natively represented on-chain;
  no fake second represented-underlying security is allowed;
- `TOKENIZED_REPRESENTATION` — token identity and represented security identity are
  distinct and an exact UMI-02 representation relationship is mandatory.

This contract is a D04 structural qualification only.

It does not decide whether an instrument is legally a security, whether an investor is
eligible, whether transfer restrictions are satisfied, or whether a token transfer is
permitted. D22 retains those determinations. Underlying equity/fund/fixed-income or
other economics remain with their existing family owners.

`TOKENIZED SECURITY TERMS != LEGAL SECURITY DETERMINATION`

## 9. Authority map

| Material | Authority |
|---|---|
| Economic identity / relationship / lifecycle | UMI-02 / D04 |
| Underlying equity/fund/security economics | existing D04 family owner |
| Perpetual/funding/network qualification | UMI-08 |
| Staking/yield/tokenization static qualification | this bounded UMI-14 owner |
| Observed validator/network/on-chain state | D05 |
| Current clocks/queue/schedule resolution | D06 |
| Reward/APR/exchange-ratio/valuation observations | D07 / UMI-10 |
| Current balances/holdings/stake positions | D08 |
| Slashing/risk/exposure/capacity assessment | D09 |
| Execution/submission | D10 / D18 |
| Custody/deposit/withdrawal/settlement mutation | D11 |
| Legal/compliance/eligibility/transfer policy | D22 |

## 10. Fail-closed invariants

- exact typed wrappers; raw UUID/string laundering rejected;
- canonical lowercase bounded code syntax;
- strict bool/int distinction for fixed delay;
- mutually exclusive exit-mode payloads;
- exact representation role/relationship-code equality;
- yield token != underlying;
- yield relationship source/target bound exactly;
- native on-chain issuance forbids a fake represented underlying;
- tokenized representation requires distinct underlying + exact binding;
- staking receipt relation must target the staked asset;
- immutable frozen/slotted values;
- deterministic `logical_values()`;
- no implicit UUID, wall clock, random, mutable global state or secret material.

## 11. Negative space

The candidate implements no:

- provider SDK or provider capability claim;
- RPC/network call, wallet, key or signing operation;
- validator operation;
- deposit/withdrawal/custody/bridge/settlement mutation;
- current balance/current stake/current reward;
- current APR/APY/current exchange ratio;
- valuation/reward/risk/slashing calculation;
- oracle or market-data observation;
- legal/compliance eligibility engine;
- order/route/execution operation;
- retry, sleep, thread or scheduler;
- productive Cloud or real-capital authority.

## 12. Gate discipline

This lane is preparatory because Lane 3 / PR #376 remains the integration-order gate.

Required before eventual integration:

`CURRENT PREPARATORY CANDIDATE -> EXACT-HEAD CI -> FREEZE -> WAIT FOR PRECEDING LANES -> SYNC TO NEW CERTIFIED MAIN -> NEW EXACT SHA -> FULL CI -> INDEPENDENT REVIEW -> INTEGRATION GATE -> EXPECTED-HEAD MERGE -> POST-MERGE CERTIFICATION`

`CI GREEN != ENGINEERING APPROVAL`

`TYPE EXISTS != OPERATIONAL SUPPORT`

`NO INDEPENDENT EXACT-HEAD REVIEW -> NO MERGE`

`NO LANE-ORDER BYPASS`

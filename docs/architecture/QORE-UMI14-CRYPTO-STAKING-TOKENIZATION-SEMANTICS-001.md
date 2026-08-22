# QORE-UMI14-CRYPTO-STAKING-TOKENIZATION-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — LANE 8 / UMI13-UNR-010 — GATE-B CURRENT-BASELINE RECERTIFICATION CANDIDATE — NOT GATE-C CERTIFIED**

Tracker: #390  
Parent audit: #363  
Historical preparatory PR: #391 — provenance only  
Current certified serial baseline: `d901653ef9c4b643262391e71940e2e80a30c385`  
Current baseline tree: `dcc95d16a3af04f17bb9a6c828f9ea88faf114c3`

This artifact covers only the bounded static D04 representation gap for crypto staking,
yield-bearing token/share relationships, and tokenized-security qualification. It does
not certify any provider, blockchain, validator, wallet, custody path, legal status,
settlement path, execution path, Production environment, or real capital.

## 1. Current-baseline reconstruction

The serial predecessor UNR-009 is sealed on current `main` at
`d901653ef9c4b643262391e71940e2e80a30c385`.

The next open serial blocker is tracker #390 / `UMI13-UNR-010`.

Historical preparatory PR #391 was constructed from stale baseline
`39e1598e91c912f473f9628c3aab30fe7b9cc034` and is not current Gate-C authority.
Its exact preparatory identity is retained only as provenance:

- base: `39e1598e91c912f473f9628c3aab30fe7b9cc034`;
- head: `9be3e2f9e024ce512690ef3bbf0a599e9cc51e96`;
- head tree: `db194a39bd98945f0d991d727e621f3bf063c518`;
- source blob: `85f0d70c8276f1422d7e3b9cc13d63aba7d61f33`;
- primary-test blob: `e0482c912ca57f00596c934def98f1ebf9912e7a`;
- architecture blob: `7124d5d5f99f328d398eba1c49d536f4fcabb0c1`.

Its historical CI/reviews remain provenance only and cannot certify a candidate built
from the current serial baseline.

## 2. Existing-owner compatibility

UMI-08 remains sovereign for crypto perpetual/funding/network qualification:

`src/qore/infrastructure/crypto_perpetual_funding_semantics.py`

The UMI-08 source changed after the historical preparatory baseline:

- historical opening-baseline blob: `f459f73bf5d5eb2556e207b3ebfdf591edde79d8`;
- current sealed-main blob: `3ac35bb0265af38bbf37c4984a694eb8ba057c6e`.

Therefore this recertification makes **no byte-identity claim** for the UMI-08 owner.
Compatibility was re-proved against the current owner instead.

The public contracts composed by this lane remain compatible:

- `CryptoTermsId` retains explicit UUID-backed local artifact identity;
- `CryptoEvidenceRef` retains explicit UUID-backed evidence reference;
- `CryptoNetworkBindingTerms` retains typed terms identity, UMI-02 relationship ID,
  role, optional network-native identifier, evidence, and deterministic logical material.

UMI-02 identity/relationship authority is also current-baseline compatible:

`src/qore/infrastructure/universal_instrument_identity.py`

current blob: `c39a77c621f9a6a524751d4e2983e71c36400a0f`.

`IdentityRelationship` includes explicit `ordinal: int | None` in its exact field and
logical surface. The fresh Gate-B oracle exercises a non-`None` ordinal so this composed
material cannot disappear unnoticed.

## 3. Authorized additive surface

Gate B is additive and touches exactly four new paths on the current baseline:

1. `src/qore/infrastructure/crypto_staking_tokenization_semantics.py`
2. `tests/infrastructure/test_crypto_staking_tokenization_semantics.py`
3. `tests/infrastructure/test_crypto_staking_tokenization_semantics_logical_identity.py`
4. `docs/architecture/QORE-UMI14-CRYPTO-STAKING-TOKENIZATION-SEMANTICS-001.md`

No pre-existing certified source, test, document, workflow, policy, or configuration is
modified or deleted.

The source and primary-test payloads reuse the historical preparatory blobs only after
current-baseline compatibility reconstruction. The logical-identity oracle and this
architecture artifact are fresh Gate-B material.

## 4. Bounded static semantics

### 4.1 Staking

`CryptoStakingTerms` preserves:

- explicit local terms identity;
- staked/principal economic identity;
- reward economic identity;
- extensible typed staking mode;
- explicit static exit/unbonding convention;
- optional static penalty/slashing-policy qualification;
- optional exact UMI-02 receipt-token representation relationship;
- optional reuse of UMI-08 network binding;
- opaque evidence reference.

A staking receipt relationship must target the staked asset. The relationship source
remains the receipt/liquid-staking representation identity and is not collapsed into the
staked asset.

### 4.2 Exit/unbonding

`CryptoStakingExitTerms` distinguishes:

- immediate;
- fixed positive integer delay;
- governed schedule code;
- network-governed timing.

The contract stores only static convention. It does not resolve current queue state,
current withdrawal availability, current epochs, or current network timing.

### 4.3 Yield-bearing token/share

`CryptoYieldBearingTokenTerms` preserves:

- token/share identity;
- distinct underlying identity;
- exact UMI-02 source/target relationship binding;
- extensible yield/accrual mechanism code;
- optional UMI-08 network binding;
- evidence.

It contains no current APR, NAV, conversion ratio, exchange rate, reward amount, accrued
balance, or valuation.

### 4.4 Tokenized-security qualification

`CryptoTokenizedSecurityQualificationTerms` distinguishes:

- native on-chain issuance, with no invented represented underlying; and
- tokenized representation of an existing security identity, which requires a distinct
  represented-underlying identity plus an exact UMI-02 relationship binding.

This is product/representation qualification only. It is not a legal-security decision,
compliance decision, transfer-eligibility decision, custody instruction, settlement
instruction, or execution authority.

## 5. Semantic collision laws

The following distinctions are mandatory:

`PERPETUAL FUNDING CONVENTION != STAKING PARTICIPATION / REWARD ARRANGEMENT`

`DIRECTLY STAKED ASSET != OPTIONAL RECEIPT / LIQUID-STAKING TOKEN`

`STAKING TERMS != CURRENT STAKING POSITION`

`REWARD IDENTITY != REWARD OBSERVATION`

`EXIT CONVENTION != CURRENT WITHDRAWAL QUEUE / NETWORK STATE`

`YIELD-BEARING TOKEN / SHARE != UNDERLYING ASSET IDENTITY`

`YIELD-BEARING TOKEN != CURRENT EXCHANGE / CONVERSION RATE`

`NATIVE ON-CHAIN SECURITY ISSUANCE != TOKENIZED REPRESENTATION OF EXISTING SECURITY`

`TOKENIZED SECURITY TERMS != LEGAL SECURITY DETERMINATION`

`NETWORK BINDING != WALLET / RPC / CUSTODY SUPPORT`

`STATIC D04 TERMS != CURRENT MARKET / VALIDATOR / ON-CHAIN OBSERVATION`

`STATIC D04 TERMS != VALUATION / RISK / EXECUTION / SETTLEMENT MUTATION`

## 6. Authority boundaries

- UMI-02 / D04 owns canonical identity and relationship semantics.
- UMI-06 and other family owners remain sovereign for underlying security/fund/equity economics.
- UMI-08 remains sovereign for perpetual/funding/network qualification.
- D05 owns observed validator/network/on-chain state.
- D06 owns current clocks, queue timing, epoch/schedule resolution.
- D07 / UMI-10 owns observed reward/APR/exchange-rate/valuation values and methodologies.
- D08 owns balances, holdings, and current stake positions.
- D09 owns slashing/risk/exposure/capacity assessment.
- D10 / D18 owns execution/submission.
- D11 owns custody, deposits/withdrawals, cash/position/settlement mutation.
- D22 owns legal/compliance eligibility, transfer restrictions, and regulatory determinations.

## 7. Negative space

This lane must not contain or infer:

- provider SDKs or provider symbols;
- blockchain RPC/client calls;
- wallet/private-key/signing capability;
- validator operation;
- deposit/withdrawal transactions;
- custody or bridge operations;
- oracle/current market observation;
- current balance/current stake/current APR/current yield;
- current exchange/conversion ratio;
- reward calculation;
- slashing/risk calculation;
- legal/compliance engine authority;
- settlement mutation;
- order/execution authority;
- retry loops, sleep, threads, scheduler, implicit wall clock, implicit UUID, random;
- Production enablement or real-capital authority.

## 8. Determinism and type discipline

All new semantic values are frozen/slotted dataclasses or typed enums/codes. IDs and
evidence are explicit. Fixed delay uses exact `int` semantics so `bool` is rejected.
Logical material is tuple-based and deterministic. No implicit clock, UUID, random,
network, file, process, thread, or scheduler authority is introduced.

## 9. Independent logical oracle

The fresh oracle
`tests/infrastructure/test_crypto_staking_tokenization_semantics_logical_identity.py`
uses `dataclasses.fields` only for structural field-surface assertions and manually
reconstructs expected logical tuples from primitive fixture values.

Expected values do **not** call the SUT `.logical_values()` implementation and do not
use production serializer/sort/fingerprint/projection helpers. The oracle also includes
a non-`None` UMI-02 `IdentityRelationship.ordinal` to bind the current relationship
projection surface.

## 10. Gate discipline

This document is Gate-B evidence only.

`GATE-B CANDIDATE != GATE-C CERTIFIED`

`CI GREEN != INDEPENDENT CERTIFICATION`

A future Gate C requires fresh authorization and must independently freeze the exact
base SHA/tree, head SHA/tree, all candidate blobs, exact diff, synthetic merge, fresh
QORE CI, DeepSeek Expert offline audit, DeepSeek Coder offline audit, Claude independent
audit, and IA falsification.

Any candidate HEAD mutation after a Gate-C freeze invalidates SHA-bound evidence and
requires Gate C to be repeated from the new exact HEAD.

No statement here authorizes Draft-to-Ready, merge, tracker closure, UMI-14 closure,
Production, productive credentials, or real capital.

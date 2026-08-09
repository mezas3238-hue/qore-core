# QORE-CLIENT-DECISION-SECURITY-001 — Cryptographic Core Decision Security

## Status

**IMPLEMENTED — NON-PRODUCTION SECURITY CONTRACTS/ORCHESTRATION; PRODUCTIVE CRYPTO CLOSED**

Opening baseline:

```text
main @ b2efb31f7eef11003eeaa27923f1e169994a864f
```

MISSION-07 Delivery 5 defines the canonical security boundary required to transport a Core Decision to one client execution account without exposing a reusable plaintext trading command.

## Maximum authority invariant

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Cryptographic verification protects Core authority; it does not create strategy.

A copied Client Execution Agent without a valid protected Core Decision remains unable to obtain new-trade authority.

## Security objective

A protected client decision must fail closed when it is:

- modified;
- replayed;
- expired;
- issued in the future;
- addressed to another account;
- addressed to another runtime;
- bound to another entitlement;
- protected with an unsupported protocol/profile;
- signed/encrypted under a revoked, unknown, not-yet-effective or expired key;
- decrypted to a different Core Decision identity/expiry;
- associated with inconsistent replay evidence.

## Existing boundaries reused

This delivery deliberately composes existing repository doctrine rather than creating parallel security systems.

It reuses:

- canonical `DecisionId` and `CoreTradeDecision`;
- `TradingAccountId`, `ExecutionRuntimeReference`, `ProductEntitlementReference` and `ClientTradingAccountBinding`;
- Delivery 4 `DecisionSecurityAttestation` consumed by the Client Agent;
- the existing `SecretRef` boundary so key material is referenced opaquely and never stored in the decision contract;
- MISSION-04 replay doctrine: deterministic fingerprint + one atomic durable claim + fail-closed duplicate/conflict handling;
- MISSION-04 transport doctrine: explicit IDs, schema/protocol identity, sent/expiry time and authenticated routing identity concepts.

The new client security types are account-trading specific, but the safety invariants are not reimplemented inconsistently.

## No productive cryptographic dependency added

The repository does not currently declare a productive cryptography package.

This delivery therefore does **not** pretend that hashing or a deterministic fake is a signature/cipher implementation.

Instead it defines:

```text
DecisionCryptoVerifier (Protocol)
```

A productive adapter behind this port must perform the real algorithm suite, including signature/authentication verification and decryption, using approved key-management infrastructure.

Unit-test fakes prove orchestration, binding, replay and fail-closed semantics only. They are not evidence of cryptographic strength or Production readiness.

## Protected external envelope

The external `ClientDecisionEnvelope` carries only routing/security metadata plus opaque protected bytes:

```text
envelope_id
protocol_version
protection_profile
decision_id
account_id
runtime_ref
entitlement_ref
issued_at
expires_at
nonce
key_id
key_version
protected_payload
```

The v1 accepted protection profile is:

```text
SIGNED_ENCRYPTED
```

The envelope does **not** carry plaintext fields such as:

```text
instrument
side
BUY / SELL
quantity
lot size
Stop Loss
Take Profit
trailing instructions
```

Those trading semantics exist only after successful verification/decryption inside the authorized boundary.

Therefore a captured transport object is not a reusable plaintext trading command.

## ProtectedDecisionPayload

`ProtectedDecisionPayload` contains opaque:

```text
ciphertext
authentication_tag
signature
```

Its `repr()` redacts every protected byte sequence.

Its deterministic logical representation contains only lengths and SHA-256 digests, never raw ciphertext/tag/signature bytes.

SHA-256 here is used only for deterministic evidence/fingerprint identity. It is not represented as the encryption/signature mechanism.

## Protocol version

The current accepted protocol is exactly:

```text
qore.client-decision.v1
```

Unknown protocol versions fail closed before key resolution or cryptographic processing.

Protocol evolution must occur through an explicit future delivery rather than permissive fallback parsing.

## Account / runtime / entitlement binding

Before resolving key metadata or invoking cryptography, the verifier requires:

```text
envelope.account_id == binding.account_id
envelope.runtime_ref == binding.runtime_ref
envelope.entitlement_ref == binding.product_entitlement_ref
```

A decision captured for Account A therefore cannot be used for Account B.

A copied Agent instance with another runtime binding also cannot consume the envelope.

A commercial entitlement reference cannot be substituted without invalidating the binding.

These routing/binding checks do not replace cryptographic authentication. They are an additional fail-closed layer.

## Freshness / expiry

The envelope has explicit timezone-aware:

```text
issued_at
expires_at
```

Rules:

```text
issued_at <= evaluated_at < expires_at
expires_at > issued_at
```

Future-dated or expired envelopes fail before key/crypto/replay processing.

The decrypted `CoreTradeDecision.expires_at` must exactly equal the authenticated envelope expiry, and its strategic decision timestamp cannot be after envelope issuance.

## Nonce

`DecisionNonce` is an explicit public 16–64 byte nonce.

It contributes to the replay fingerprint and prevents identical protected-envelope material from sharing an indistinguishable transport identity.

Nonce presence alone is not replay protection; durable atomic replay state remains mandatory.

## Key identity / version / rotation / revocation

Every envelope binds:

```text
DecisionKeyId
DecisionKeyVersion
```

`DecisionKeySnapshot` provides non-secret lifecycle metadata:

```text
ACTIVE
VERIFY_ONLY
REVOKED
UNKNOWN
```

and:

```text
material_ref: SecretRef
```

Accepted verification states:

```text
ACTIVE
VERIFY_ONLY
```

`VERIFY_ONLY` allows safe key rotation: an old key may continue verifying already-issued valid envelopes without being authorized as the current publishing key.

Rejected states:

```text
REVOKED
UNKNOWN
```

Key metadata also has explicit effective/expiry times.

This delivery never carries private key bytes, bearer tokens or resolved `SecretMaterial` inside the envelope/key snapshot.

## Secret boundary

The verifier receives a `DecisionKeySnapshot` containing only an existing canonical `SecretRef`.

Actual key-material resolution belongs to the concrete `DecisionCryptoVerifier` adapter/key-management implementation.

This keeps key values outside strategic Core and outside ordinary audit/logical values.

## Cryptographic verifier port

```text
DecisionCryptoVerifier.verify_and_decrypt(
    envelope,
    key_snapshot,
)
    -> DecisionCryptographicVerification
```

A successful productive implementation must mean:

- the authenticated envelope/header and protected payload are acceptable under the configured suite;
- signature/authenticity verification succeeded;
- integrity/authentication verification succeeded;
- decryption succeeded;
- the returned plaintext maps to a valid canonical `CoreTradeDecision`.

The orchestrator performs no fallback verifier and no retry.

The returned verification includes the protected-payload digest; it must equal the digest independently derived from the envelope to bind the crypto result to exactly the protected material that was received.

## Decrypted decision binding

After successful crypto verification, the orchestrator still requires:

```text
decrypted DecisionId == envelope DecisionId
decrypted expiry == envelope expiry
decision timestamp <= envelope issued_at
```

A crypto adapter cannot accidentally return a different valid Core Decision and have it inherit another envelope's routing/replay authority.

## Replay key

Replay identity is account-scoped:

```text
ClientDecisionReplayKey
    = (TradingAccountId, DecisionId)
```

This is deliberate.

One Core Decision may fan out legitimately to multiple independent accounts:

```text
Decision D + Account A
Decision D + Account B
```

but Account A may not execute Decision D twice merely because the attacker changes nonce, encryption randomness or the protected bytes.

## Replay fingerprint

The replay fingerprint is a SHA-256 digest over canonical secret-free envelope identity including:

- envelope/protocol/profile IDs;
- decision/account/runtime/entitlement binding;
- issued/expiry times;
- nonce;
- key ID/version;
- digest of protected payload metadata.

It never embeds raw ciphertext, tag, signature or secret key material.

Changing nonce or protected material changes the fingerprint.

## Atomic replay claim

The client replay port mirrors the established MISSION-04 fail-closed pattern:

```text
ClientDecisionReplayClaimPort.claim(key, fingerprint)
```

Possible results:

```text
ACQUIRED
DUPLICATE
CONFLICT
```

Only:

```text
ACQUIRED
```

may lead to a VERIFIED client decision.

Both duplicate and conflict are rejected for new trading.

Unlike an executive query/idempotent request, a captured trading decision is never re-dispatched automatically because a duplicate was seen.

There is:

- exactly one claim call after successful crypto verification;
- no release;
- no retry;
- no automatic redispatch.

## Claim occurs after cryptographic verification

Replay reservation is intentionally attempted only after:

- routing/binding checks;
- time checks;
- key lifecycle checks;
- cryptographic verification/decryption;
- decrypted decision identity/expiry checks.

This prevents invalid unauthenticated packets from reserving durable replay identities for legitimate Core Decisions.

A valid captured replay still fails at the atomic claim.

## VerifiedClientDecision

Only the successful orchestration result returns:

```text
VerifiedClientDecision
    decision: CoreTradeDecision
    attestation: DecisionSecurityAttestation(VERIFIED)
    envelope_id
    replay_fingerprint
```

The attestation exactly binds:

```text
decision_id
account_id
runtime_ref
VERIFIED
evidence_ref
verified_at
```

This is the canonical object Delivery 4 can feed into `evaluate_client_execution(...)`.

A verification failure does not manufacture a VERIFIED attestation.

## Security evidence reference

`DecisionSecurityEvidenceReference` remains opaque.

A future audit/evidence implementation may bind this reference to richer durable evidence such as:

- verifier implementation/version;
- algorithm-suite policy identity;
- key ID/version;
- replay claim receipt;
- authenticated envelope digest;
- verification timestamp.

The evidence store must not log raw secret key values or decrypted strategy payload unnecessarily.

## Copied Agent / antipiracy property

A copied EA/Client Agent binary alone is intentionally insufficient.

For a new trade it still needs all of the following:

```text
valid Core Decision
signed+encrypted envelope
exact account binding
exact runtime binding
exact entitlement binding
current authorized key
successful cryptographic verification
unexpired envelope
successful anti-replay claim
later Agent/account/risk/policy gates
```

Therefore:

```text
COPIED AGENT WITHOUT VALID CORE AUTHORITY -> NO NEW TRADING
```

The Agent also does not contain Core strategy logic.

This is architectural antipiracy through absence of distributed strategic authority, not a claim that client-side software can be made impossible to reverse engineer.

## Verification sequence

`verify_client_decision_envelope(...)` executes this deterministic sequence:

```text
1. validate input types / evaluated_at
2. require supported protocol/profile
3. require exact account/runtime/entitlement binding
4. require current envelope time window
5. resolve exact key ID/version once
6. require ACTIVE or VERIFY_ONLY current key
7. call crypto verifier exactly once
8. bind crypto result to protected-payload digest
9. require decrypted DecisionId/expiry/timestamp consistency
10. derive account-scoped replay key + canonical fingerprint
11. atomically claim replay once
12. reject DUPLICATE / CONFLICT
13. emit VERIFIED attestation + VerifiedClientDecision
```

No step falls through after failure.

## No broker/execution authority

This module has no:

```text
submit_order
execute
broker client
provider credential
lot sizing
SL/TP calculation
position mutation
```

Security verification proves that a Core Decision came through the authorized protected-decision boundary for one account/runtime/entitlement and is not replayed.

It still does not bypass Delivery 4 account/policy/risk/entitlement evaluation or the repository's existing pre-trade/execution safety gates.

## Determinism and typing

The delivery preserves:

- frozen/slotted immutable contracts;
- caller-supplied UUID identities;
- caller-supplied timezone-aware timestamps;
- no hidden clock;
- no implicit nonce/UUID generation;
- typed key/replay states;
- typed `Result / Success / Failure`;
- deterministic logical values/fingerprints;
- one explicit replay claim;
- no network IO;
- no background thread/scheduler;
- no automatic retry;
- no `type: ignore`;
- no cast workaround;
- no suppression.

## Test evidence

`tests/infrastructure/test_client_decision_security.py` proves orchestration semantics including:

- external envelope has no plaintext trading fields;
- protected bytes are redacted and logical evidence uses digests;
- fingerprints are deterministic and change with nonce/protected material;
- valid envelope produces exact VERIFIED attestation;
- wrong account/runtime/entitlement fails before key/crypto/replay;
- expired/future envelopes fail closed;
- unsupported protocol fails closed;
- revoked/unknown keys fail before crypto;
- VERIFY_ONLY supports rotation verification;
- key material remains an opaque `SecretRef`;
- crypto/signature failure performs no replay claim;
- protected-payload digest mismatch performs no replay claim;
- decrypted decision ID/expiry mismatch performs no replay claim;
- duplicate/conflicting replay both fail closed;
- replay claim occurs exactly once with no release/retry;
- one Core Decision may fan out to independent account replay keys;
- Account A envelope cannot authorize Account B;
- security contracts expose no broker/order execution method.

The fakes do not claim to test or certify a real cryptographic algorithm.

## Explicitly not implemented

This delivery does not implement or authorize:

- productive signing private keys;
- productive encryption/decryption keys;
- KMS/HSM integration;
- a concrete signature algorithm adapter;
- a concrete encryption/AEAD adapter;
- network decision distribution;
- public signal service;
- durable replay database implementation;
- productive evidence database;
- broker/MT5/FCM connectivity;
- live execution;
- position lifecycle/trailing actions;
- Billing/Payments;
- Widget;
- Managed Hosting;
- Futures;
- Production;
- MISSION-06 activation;
- MISSION-03 Gate #5 closure.

## Acceptance result

This delivery is complete only after the exact PR head passes the unchanged QORE Quality Gate and merges with only the intended architecture, contracts and tests.

After merge, the next authorized MISSION-07 delivery is:

```text
QORE-CLIENT-POSITION-LIFECYCLE-001
```

That delivery must extend the causal chain from a verified/authorized execution plan through execution/position/protection/trailing/exit/result evidence without automatic redispatch or orphan actions.

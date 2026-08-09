# QORE-EXECUTIVE-REPLAY-IDEMPOTENCY-001 — Fail-Closed Replay Claim Boundary

Status: **MISSION-04 DELIVERY 9 — OFFLINE CONTROL-PLANE PROTECTION**

## Purpose

Prevent an already-authorized executive control request from being dispatched twice and prevent one
Governance mutation identity from being reused with conflicting content.

This delivery is transport-neutral and persistence-neutral. It defines the claim contract used
before protected downstream activity; it does not choose a database, lock implementation, message
transport, or runtime scheduler.

## Required ordering

```text
authorized control intent / governance mutation request
        -> deterministic replay claim
        -> authoritative claim boundary
        -> ACQUIRED only
        -> protected downstream action
```

`DUPLICATE`, `CONFLICT`, boundary failure, malformed receipt, or mismatched receipt means:

```text
NO DISPATCH / NO MUTATION
```

There is no automatic retry.

## Replay keys

The protected identities are explicit existing domain identities:

- control dispatch -> `ExecutiveIntentId`;
- Governance mutation -> `ExecutiveGovernanceMutationId`.

No hidden UUID generation is introduced.

## Deterministic fingerprints

A replay key is paired with a secret-free fingerprint derived only from protected typed fields.

Control fingerprints bind:

- intent ID;
- principal;
- action;
- target when present;
- authority version;
- correlation ID.

Mutation fingerprints additionally bind:

- mutation ID;
- source control receipt ID;
- expected snapshot/version;
- requested snapshot/version.

Free-text intent/grant reasons are intentionally excluded.

## Claim semantics

`ExecutiveReplayClaimStatus` is closed:

```text
ACQUIRED
DUPLICATE
CONFLICT
```

`ACQUIRED` means the identity/fingerprint pair was newly reserved and downstream execution may
continue exactly once.

`DUPLICATE` means the same identity and same fingerprint already exists. It is blocked rather than
silently re-dispatched.

`CONFLICT` means the identity already exists with a different fingerprint. It is fail-closed.

The receipt proves the exact requested and observed fingerprint. A conflict cannot report identical
fingerprints; acquired/duplicate cannot report different fingerprints.

## Boundary

`ExecutiveReplayClaimPort` is a `Protocol`:

```text
claim(ExecutiveReplayClaimRequest)
  -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]
```

`ExecutiveReplayProtector` makes exactly one claim call. It returns success only for `ACQUIRED`.
Arbitrary downstream error text is converted into a closed sanitized block reason.

## Ambiguous outcomes

Once a claim is acquired, this contract does not release it automatically if a later stage becomes
ambiguous or fails. Reusing the same identity would risk double execution. Recovery therefore
requires a new explicit identity or a later governed recovery/re-read policy; Delivery 12 will
address resilience semantics without automatic duplicate dispatch.

## Safety

The delivery introduces no:

- Production activation;
- broker/provider dependency;
- OANDA dependency;
- real capital;
- order execution;
- Risk bypass;
- retry loop;
- sleep;
- scheduler;
- thread;
- implicit clock;
- implicit identity generation.

MISSION-03 Gate #5 remains unchanged and blocked pending authorized OANDA Practice secret
provisioning.

## Secret discipline

Fingerprints accept only canonical components and reject secret-like material. Passwords, bearer
headers, access tokens, client secrets, credentials, private keys, free-text reasons, provider
payloads, and private reasoning do not belong in replay state or `logical_values()`.

## Tests

Contract tests prove:

- exact control identity/fingerprint binding;
- mutation-ID reuse with changed state produces a different fingerprint;
- explicit timezone-aware chronology;
- secret-like fingerprint data rejected;
- only newly acquired claims pass the protector;
- duplicate/conflict fail closed;
- boundary failures are sanitized and never retried;
- mismatched receipts fail closed;
- structural Protocol substitution.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppressions or gate weakening are permitted.

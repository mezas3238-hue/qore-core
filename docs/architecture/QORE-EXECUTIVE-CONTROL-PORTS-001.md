# QORE-EXECUTIVE-CONTROL-PORTS-001 — Command, Query & Audit Receipt Contracts

Status: **PREPARATION READY — TRANSPORT AND MOBILE ACTIVATION REMAIN CLOSED**

## Purpose

Define the transport-neutral ports and deterministic audit receipts that sit immediately after the authorization contracts introduced by `QORE-EXECUTIVE-CONTROL-PLANE-001`.

This delivery still does not implement HTTP, WebSocket, mobile transport, a backend service, a broker connection, a database, or direct Core access.

## Required flow

The future executive path is deliberately staged:

```text
CEO Desktop / iOS / Android
        │
        ▼
Authentication boundary
        │
        ▼
ExecutiveAuthorityGrant
        │
        ▼
ExecutiveControlIntent / ExecutiveReadRequest
        │
        ▼
authorize_executive_*
        │
        ▼
AuthorizedExecutiveControlIntent
or AuthorizedExecutiveReadRequest
        │
        ▼
transport-neutral executive port
        │
        ▼
downstream governance/read adapter
        │
        ▼
Executive*Receipt
        │
        ▼
audit evidence
```

An unauthorized request cannot be represented as input to these ports without violating their type contract.

## Ports

Two separate Protocol boundaries are introduced.

### `ExecutiveControlCommandPort`

Consumes only:

```text
AuthorizedExecutiveControlIntent
```

and returns:

```text
Result[ExecutiveControlReceipt, ExecutivePortError]
```

The protocol exposes only `apply()`.

It does not expose order submission, cancellation, broker access, credential access, Risk bypass, or trading-strategy calls.

### `ExecutiveReadQueryPort`

Consumes only:

```text
AuthorizedExecutiveReadRequest
```

and returns:

```text
Result[ExecutiveReadReceipt, ExecutivePortError]
```

The protocol exposes only `read()`.

The read receipt is audit metadata. It is deliberately not the business read-model payload itself.

This keeps authorization/audit semantics independent from how future read models are serialized or transported.

## Why command and query are separate

QORE must not infer control authority from read access.

A principal may be allowed to inspect:

```text
system-health
risk
ceo-accounts
corporate-profit-vault
```

without automatically receiving authority to pause, restrict, resume, or change policies.

Likewise, authorization for one governance command does not imply unrestricted access to all read surfaces.

The ports preserve that distinction at the type level.

## Audit receipt identity

Every receipt has an explicit `ExecutiveReceiptId` supplied by the caller/runtime boundary.

There is no hidden `uuid4()` generation.

Receipt construction derives protected identity directly from the already-authorized request:

- intent/request identity;
- executive principal;
- action or read scope;
- exact authority version;
- QORE correlation identity.

The caller cannot provide replacement values for those protected fields through the receipt builder.

This reduces the chance of producing audit evidence for a different authority or principal than the request actually used.

## Receipt chronology

Receipt builders require explicit timezone-aware timestamps.

The following chronology is mandatory:

```text
authorized_at
    <= received_at
    <= completed_at
```

A port cannot claim to have received a request before authorization occurred.

A receipt cannot claim completion before receipt.

No implicit runtime clock is used by the contract.

## Control receipt statuses

`ExecutiveControlReceiptStatus` is a closed enum:

```text
applied
no-change
blocked
failed
```

These states describe the downstream governance result after authorization.

`applied` does not mean a broker order was sent. It means the requested executive governance action was applied by the future downstream governance adapter.

For example, `halt-new-trading` may be applied while existing position protection remains active.

`blocked` allows downstream governance to reject an already-authorized executive request when another invariant prevents it.

Authorization therefore remains necessary but not sufficient for every downstream state transition.

## Read receipt statuses

`ExecutiveReadReceiptStatus` is:

```text
served
blocked
failed
```

A served receipt proves that an authorized read request crossed the query boundary successfully.

It does not embed the read payload.

## Evidence references

Receipts can contain a tuple of `ExecutiveEvidenceRef` values.

Evidence refs are:

- opaque;
- canonical lowercase references;
- sanitized;
- deterministic;
- sorted into stable order;
- duplicate-free.

They may reference future audit/evidence storage, but the receipt does not assume a database or storage technology.

Example conceptual values:

```text
audit:control/001
audit:read/002
```

They are references, not secret-bearing URLs or tokens.

## Reason codes

Receipts use a canonical `reason_code` rather than arbitrary narrative text.

Examples:

```text
governance.applied
governance.no_change
read.served
```

The syntax is intentionally restrictive and cannot carry bearer tokens, API keys, passwords or free-form confidential material.

A future human explanation can exist in a separate sanitized evidence record referenced by `ExecutiveEvidenceRef`.

## Reason-for-Action alignment

The executive audit chain is now capable of preserving:

```text
ExecutivePrincipalId
    ↓
ExecutiveAuthorityVersion
    ↓
ExecutiveAuthorityGrant
    ↓
ExecutiveControlIntent / ExecutiveReadRequest
    ↓
Authorized request
    ↓
Executive port
    ↓
Executive receipt
    ↓
Evidence refs
```

This is still not the final corporate audit store, but it establishes deterministic reconstruction boundaries.

## Capital-preservation boundary

Nothing in these ports creates a trading-order command.

The control port consumes the governance allowlist already closed by `QORE-EXECUTIVE-CONTROL-PLANE-001`.

Therefore the port cannot receive:

```text
buy
sell
submit-order
cancel-order
force-trade
close-position
bypass-risk
```

without a prior explicit architectural change to the repository.

The intended rule remains:

```text
CEO governance authority
    may stop or reduce trading authority

CEO governance authority
    must not bypass Risk / Capital Protection
```

## Corporate Profit Vault boundary

A future read request for `corporate-profit-vault` may pass through an implementation of `ExecutiveReadQueryPort` backed by a Corporate Plane adapter.

A future read request for `ceo-accounts` may be backed by a separate proprietary-operations read adapter.

The shared executive port contract does not connect those underlying domains to each other.

This remains forbidden:

```text
QORE Core ↔ Client Profit Vault
```

The CEO Command Center may render separately authorized read models from both domains without creating a Core/Vault dependency.

## No business payload in receipts

Receipts deliberately contain no:

- balance;
- equity;
- account number;
- client identity;
- order;
- position;
- broker payload;
- Profit Vault settlement payload;
- payment data.

This keeps receipts small, audit-focused and safe to correlate.

Business read-model contracts will be defined separately.

## No transport assumptions

The ports do not know whether future transport is:

- local IPC;
- HTTPS;
- WebSocket;
- gRPC;
- message transport;
- another controlled mechanism.

Likewise they do not know whether the caller UI is Desktop, iOS or Android.

Transport adapters must be implemented outside these governance contracts.

## No hidden runtime behavior

This deliverable introduces no:

- network I/O;
- retry;
- reconnect;
- polling;
- `sleep`;
- scheduler;
- thread;
- process manager;
- mutable singleton;
- implicit clock;
- implicit identity generation.

## Tests

The tests verify:

- receipt identity is derived from the authorized request;
- authority version and correlation are preserved;
- receipt chronology fails closed;
- evidence references are sorted and duplicate-free;
- reason codes cannot become secret-bearing free text;
- read receipts preserve exact scope and authority;
- receipts contain audit metadata rather than business payloads;
- structural Protocol implementations expose only command/read surfaces;
- no order submit/cancel surface is introduced;
- logical values are deterministic.

## Mission boundary

MISSION-03 remains unchanged and active.

This work is preparatory for:

```text
MISSION-04 — QORE Control Plane & Executive Governance
MISSION-05 — QORE Mobile & CEO Command Center
```

It does not operationally start either mission.

It does not activate:

- CEO Desktop;
- iOS;
- Android;
- CIBO Widget;
- public networking;
- Production trading;
- real capital;
- productive credentials;
- Client Profit Vault runtime;
- billing/payment integration.

## Quality gate

The unchanged repository quality gate remains mandatory:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

## Next boundary

After integration, the next controlled deliverable should define **executive read-model contracts** for system health, CIBO state, proprietary CEO accounts and the isolated corporate Profit Vault without yet implementing mobile transport or coupling those data domains.

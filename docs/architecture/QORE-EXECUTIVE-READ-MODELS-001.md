# QORE-EXECUTIVE-READ-MODELS-001 — Executive Read Model Contracts

Status: **PREPARATION READY — TRANSPORT AND MOBILE ACTIVATION REMAIN CLOSED**

## Verified base

This delivery starts from:

```text
main @ fb62f22014b7e18504ff28a30f707a69867689ec
```

At branch creation there were no open pull requests and no later commit changing the
executive-control direction.

## Purpose

Define the first explicit business projections that may later be consumed by the QORE CEO
Command Center without exposing internal Core/domain objects to Desktop, iOS, or Android.

The canonical flow remains:

```text
Internal domain/runtime state
        ↓
executive projection adapter
        ↓
Executive*ReadModel
        ↓
AuthorizedExecutiveReadRequest
        ↓
ExecutiveReadQueryPort
        ↓
ExecutiveReadReceipt + separately transported authorized projection
        ↓
CEO Command Center
```

This delivery does not create another authorization path or another query boundary.
`ExecutiveReadQueryPort` and its receipt remain the canonical audit boundary established by
`QORE-EXECUTIVE-CONTROL-PORTS-001`. The read model is deliberately separate from the receipt,
matching the existing repository decision that receipts are audit metadata rather than business
payloads.

## Scope decomposition

The executive read surface is intentionally split into narrow auditable deliveries.

### This delivery

```text
COMMON PROJECTION PROVENANCE
SYSTEM_HEALTH
CIBO_STATE
```

### Follow-up operational projections

```text
MARKETS
TRADERS
VALIDATION_LAB
TRADE_FORENSICS
AUDIT
GOVERNANCE
```

### Follow-up proprietary-capital projections

```text
CAPITAL_STATE
RISK
PORTFOLIO
CEO_ACCOUNTS
```

These represent CEO proprietary operations only.

### Follow-up isolated corporate projection

```text
CORPORATE_PROFIT_VAULT
```

This must remain a separate corporate read surface and must never be merged into a generic
financial overview with CEO proprietary accounts.

## Shared projection provenance

Every projection carries explicit immutable metadata:

- `ExecutiveProjectionId`;
- `ExecutiveProjectionVersion`;
- exact `ExecutiveReadScope`;
- explicit timezone-aware source observation time;
- explicit timezone-aware projection time;
- explicit freshness state;
- stable sanitized `ExecutiveEvidenceRef` values;
- stable sanitized policy-version references.

No projection creates its own clock, UUID, secret access, provider access, or mutable state.

Chronology is fail-closed:

```text
source_observed_at <= projected_at
```

Evidence and policy references are duplicate-free and deterministically ordered.

## SYSTEM_HEALTH

`ExecutiveSystemHealthReadModel` is a public executive projection rather than an exported
`RuntimeSnapshot` or `RuntimeHealthSnapshot`.

It exposes only stable executive semantics:

- aggregate health;
- readiness;
- attention level;
- canonical reason codes;
- explicit component health projections;
- common provenance/evidence metadata.

The Command Center therefore does not depend on internal runtime object layout.

The contract does not expose:

- `RuntimeContext`;
- internal runtime graph objects;
- provider sessions;
- credentials;
- broker objects;
- execution gateways.

## CIBO_STATE

`ExecutiveCiboReadModel` is intentionally evidence-backed and does not contain private
chain-of-thought.

It may expose:

- operational state;
- judgment;
- confidence representation;
- uncertainty state;
- executive attention level;
- authorization state;
- structured reason codes;
- supporting evidence references;
- counter-evidence references;
- structured risk-factor codes;
- recommendation code.

For every non-unknown CIBO judgment the contract requires both structured reason codes and
supporting evidence references.

Supporting and counter-evidence references must be distinct.

The contract deliberately provides no field for:

```text
chain_of_thought
private_reasoning
hidden_prompt
scratchpad
```

The intended rule remains:

```text
conversation -> structured reason/evidence
```

never:

```text
conversation -> trust me
```

## Attention model

The first stable executive attention levels are:

```text
information
attention
important
decision-required
critical
```

They are descriptive read-model states only. This delivery does not implement notification
thresholds, push notifications, interruption scheduling, or autonomous command execution.

## Freshness

Freshness is explicit:

```text
fresh
stale
unknown
```

The producer must supply it. The contract does not call `datetime.now()` or infer wall-clock age.

This makes stale or uncertain executive data visible rather than silently presenting it as current.

## Secret and privacy boundary

Public projection identifiers, reason codes, recommendation codes, policy versions, and component
identifiers use restrictive canonical syntax.

Evidence is represented by opaque `ExecutiveEvidenceRef` values.

The projection contracts do not contain:

- tokens;
- passwords;
- API keys;
- authorization headers;
- provider credentials;
- broker sessions;
- client names;
- client account numbers;
- private chain-of-thought.

## Proprietary vs Corporate economics

The repository direction is preserved:

```text
CEO proprietary operations  X  Client Profit Vault
```

This delivery intentionally does not introduce a generic `financial_overview`.

Future `CEO_ACCOUNTS`, `CAPITAL_STATE`, `RISK`, and `PORTFOLIO` projections will model only
proprietary operations.

Future `CORPORATE_PROFIT_VAULT` projections will model client-service economics behind a separate
Corporate Plane adapter using opaque ledger identities.

Core and Profit Vault remain unaware of each other.

## Read-scope binding

Each concrete read model must carry the exact scope it represents.

For example:

```text
ExecutiveSystemHealthReadModel -> SYSTEM_HEALTH
ExecutiveCiboReadModel         -> CIBO_STATE
```

A model built with the wrong scope fails closed.

This prevents a payload projected for one authorized surface from being mislabeled as another.

## Determinism

All value contracts are immutable `dataclass(frozen=True, slots=True)` values.

`logical_values()`:

- use explicit values only;
- preserve normalized deterministic ordering;
- contain no generated identity;
- contain no implicit time;
- contain no secret-bearing free text.

## No transport or runtime activation

This delivery introduces no:

- HTTP;
- WebSocket;
- gRPC;
- mobile backend;
- database;
- broker/provider adapter;
- direct Core access from a UI;
- retry/reconnect loop;
- polling loop;
- sleep;
- scheduler;
- thread;
- Production account;
- real-capital authority;
- Profit Vault runtime.

MISSION-03 remains active and unchanged.

The work is preparatory for future MISSION-04/05 boundaries only and does not operationally open
those missions.

## Quality gate

The official repository gate remains unchanged:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or weakening of Ruff, Mypy, Pytest, or coverage is authorized.

## Next controlled deliverable

After this contract foundation is merged, the next narrow delivery should define the operational
executive projections for:

```text
MARKETS
TRADERS
VALIDATION_LAB
TRADE_FORENSICS
AUDIT
GOVERNANCE
```

while retaining the same projection provenance and canonical authorized read boundary.

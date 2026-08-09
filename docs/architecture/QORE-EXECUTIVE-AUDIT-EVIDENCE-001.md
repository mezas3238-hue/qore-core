# QORE-EXECUTIVE-AUDIT-EVIDENCE-001 — Durable Executive Audit Evidence Boundary

Status: **MISSION-04 DELIVERY 8 — PERSISTENCE-NEUTRAL AUDIT APPEND CONTRACT**

## Purpose

Define the durable, append-oriented boundary that preserves secret-free evidence for the executive
control-plane chain without choosing a database, transport, provider, or storage technology.

This delivery complements existing contracts rather than replacing them:

- `ExecutiveAuditReadModel` remains the governed read projection;
- `ExecutiveEvidenceRef` remains the opaque evidence reference carried by receipts;
- command/query receipts remain the canonical downstream result metadata;
- current authority remains sourced from `ExecutiveAuthorityStateSource`;
- governance state mutation remains `ExecutiveGovernanceMutationPort.compare_and_set()`.

The new boundary is only the durable audit write contract.

## Required chain

The evidence model can preserve references across:

```text
AuthenticatedExecutivePrincipal
  -> current authority request / observation
  -> authorized control or read request
  -> command receipt or read delivery
  -> governance mutation request / mutation receipt when applicable
  -> durable executive audit evidence
```

A blocked, failed, conflict, or no-action outcome remains auditable. Audit evidence never upgrades a
failed stage into authorization and never reconstructs current authority from historical records.

## Durable boundary

`ExecutiveAuditEvidencePort` is a structural `Protocol` exposing one operation:

```text
append(ExecutiveAuditEvidenceRecord)
  -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]
```

The contract does not define SQL, Redis, object storage, filesystem persistence, transactions,
locks, retention jobs, retries, or a concrete audit backend.

A concrete adapter may return `ExecutiveAuditEvidenceUnavailableError`; it must not fabricate a
successful append.

## Audit evidence record

`ExecutiveAuditEvidenceRecord` is immutable and contains only audit-safe correlation material:

- explicit record identity;
- lifecycle stage;
- closed outcome;
- executive principal;
- QORE correlation ID;
- optional exact authority version;
- explicit timezone-aware occurrence timestamp;
- canonical reason code;
- deterministic typed source references;
- deterministic existing `ExecutiveEvidenceRef` values.

It intentionally contains no arbitrary metadata dictionary and no raw payload field.

## Stages

The closed stage set is:

```text
authentication
authority
authorization
command-dispatch
query-dispatch
governance-mutation
```

The `authorization` stage is available for explicit fail-closed guard evidence even when no
authorized object exists. Successful command/read records bind the already-authorized object
through their typed source reference.

## Outcomes

The closed outcome set is:

```text
succeeded
no-action
blocked
failed
```

For control receipts, the mapping is deterministic:

```text
APPLIED   -> succeeded
NO_CHANGE -> no-action
BLOCKED   -> blocked
FAILED    -> failed
```

For Governance mutation receipts:

```text
APPLIED  -> succeeded
CONFLICT -> blocked
```

A command/read/mutation record without its expected downstream result can only be `blocked` or
`failed`. The builder cannot represent missing result evidence as success.

## Existing-contract binding

Dedicated builders bind existing objects rather than accepting caller-rewritten identities:

- authentication builder derives assertion/principal/correlation;
- authority builder derives request identity and current-state evidence reference;
- command-dispatch builder derives intent, authority version, correlation, receipt ID and receipt
  evidence;
- query-dispatch builder derives request, authority version, correlation, delivery/receipt identity
  and receipt evidence;
- Governance mutation builder derives mutation ID, source command receipt, expected/requested/
  observed snapshots, authority version and mutation outcome.

Mismatched principal, correlation, authority, receipt identity, request identity, mutation identity,
or chronology fails closed.

## Evidence references, not payloads

The durable record stores typed references to source objects, not those objects themselves.

It does not retain:

- authentication credentials or biometric material;
- authority grant reason narrative;
- control-intent free text;
- projection payloads;
- raw downstream exceptions;
- broker/provider payloads;
- arbitrary upstream error text;
- private reasoning.

Existing receipt evidence references are preserved as opaque sanitized references.

## Secret discipline

Canonical source references, reason codes, and evidence references reject secret-like material.

The boundary must never contain passwords, bearer headers, access tokens, client secrets, private
keys, credentials, raw provider credentials, or equivalent secret material in `repr`, evidence, or
`logical_values()`.

## Determinism and chronology

- all values are immutable `dataclass(frozen=True, slots=True)` objects;
- record IDs are explicit UUID values supplied by the caller;
- all timestamps are explicit and timezone-aware;
- no implicit wall clock is consulted;
- source and evidence references are sorted deterministically;
- duplicate references are rejected or deterministically coalesced only when combining already
  validated evidence sets from the same chain;
- `logical_values()` is deterministic;
- no hidden retry, sleep, scheduler, thread, or identity generation is introduced.

## Relationship to existing audit surfaces

`ExecutiveAuditReadModel` is a client-facing governed projection. This delivery does not turn that
read model into a persistence model.

`OperationsAuditBoundary` remains the infrastructure/operations audit boundary. This delivery does
not couple executive governance to that infrastructure-specific model and does not duplicate its
concrete in-memory sink.

The executive audit contract is a governance boundary whose concrete persistence adapter belongs
outside QORE Core's object graph.

## Provider independence

No OANDA, broker, provider, mobile, HTTP, database, or platform dependency is introduced.

MISSION-03 Gate #5 remains operationally blocked until OANDA Practice credentials are provisioned
through an authorized secret boundary. Nothing in this delivery changes that state.

## Safety

This delivery does not authorize or implement:

- Production;
- real capital;
- productive credentials;
- order submission/cancellation;
- autonomous real-money trading;
- Risk bypass;
- corrective trading;
- provider connectivity.

Audit persistence is evidence only. It confers no authority.

## Tests

Contract tests cover:

- immutable/deterministic records;
- secret-like and ambiguous values rejected;
- authentication and current-authority binding;
- exact authority version and correlation binding;
- all control receipt outcomes including `NO_ACTION`;
- fail-closed missing command/read results;
- query delivery linkage without persisting projection payloads;
- Governance mutation request/receipt/snapshot linkage;
- conflict auditability;
- structural `ExecutiveAuditEvidencePort` substitution.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or quality-gate weakening is permitted.

## Next delivery

After merge, verify the repository and continue with the next real gap for MISSION-04:

```text
QORE-EXECUTIVE-REPLAY-IDEMPOTENCY-001
```

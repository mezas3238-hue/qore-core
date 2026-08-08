# QORE-EXECUTIVE-GOVERNANCE-READ-MODEL-001 — Governance Executive Projection

Status: **PREPARATION READY — MATERIALIZED GOVERNANCE STATE REMAINS A FUTURE BOUNDARY**

## Verified base

```text
main @ 32714e6c1b60c687986b5a446c0734bb77e31935
```

This delivery starts only after `ExecutiveReadScope.GOVERNANCE` was explicitly authorized and
merged as a separate scope gate.

## Purpose

Define the first stable Governance projection for the future CEO Command Center without exposing
internal `ExecutiveAuthorityGrant` or `ExecutiveControlReceipt` objects directly to
Desktop/iOS/Android.

The canonical path remains:

```text
executive authority / control receipt state
        ↓
Governance projection adapter
        ↓
ExecutiveGovernanceReadModel
        ↓
AuthorizedExecutiveReadRequest(scope=GOVERNANCE)
        ↓
ExecutiveReadQueryPort
        ↓
CEO Command Center
```

No second authorization or query system is introduced.

## Repository-grounded scope

Current `main` has two canonical evidence sources suitable for this first Governance surface:

1. `ExecutiveAuthorityGrant` — exact executive authority/capability grant;
2. `ExecutiveControlReceipt` — audit receipt for an authorized governance command.

The repository does **not** yet contain a single canonical materialized state object for:

- active market restrictions;
- active account restrictions;
- current system pause state;
- current `halt new trading` state.

This delivery therefore does not reconstruct or invent those states from receipt history.

That follows QORE's fail-closed rule:

```text
no canonical materialized source
        ↓
no fabricated executive state
```

## Authority summaries

`ExecutiveGovernanceAuthoritySummary` is an explicit projection of authority evidence. It contains:

- opaque grant reference;
- stable executive principal reference;
- authority version;
- explicit timezone-aware issue/expiry timestamps;
- projected allowed governance action codes;
- projected allowed read-scope codes;
- structured reason codes;
- evidence references.

The summary must expose at least one capability.

Capabilities are immutable, duplicate-free and deterministically ordered.

The projection does not expose the internal grant object or free-form grant reason directly.

## Governance receipt summaries

`ExecutiveGovernanceControlReceiptSummary` represents the auditable result of one governance
command. It contains:

- opaque receipt identity;
- opaque source intent identity;
- principal reference;
- governance action code;
- exact authority-version reference;
- correlation reference;
- explicit received/completed timestamps;
- receipt status code;
- structured reason codes;
- evidence references.

Chronology is fail-closed:

```text
received_at <= completed_at
```

Receipt and intent identities must differ.

The model is intentionally audit-backed: it shows what was authorized and what command result was
recorded, not a reconstructed speculative current state.

## Projection-specific value objects

The Governance read surface defines its own projection identifiers and capability/status codes.

It does not return these internal control-plane objects directly:

- `ExecutiveGrantId`;
- `ExecutivePrincipalId`;
- `ExecutiveAuthorityVersion`;
- `ExecutiveControlAction`;
- `ExecutiveReadScope` as business payload;
- `ExecutiveControlReceipt`.

`ExecutiveReadScope.GOVERNANCE` is used only to bind the projection to the canonical authorized read
scope.

This preserves UI/API stability if internal governance contracts evolve.

## Evidence and privacy

Authority and receipt summaries require `ExecutiveEvidenceRef` values.

Public capability/status/reason values use restrictive canonical syntax rather than arbitrary
free-form text.

The read model contains no:

- credentials;
- secrets;
- authorization headers;
- private chain-of-thought;
- raw policy implementation;
- provider objects;
- broker objects;
- client identity;
- Profit Vault payload.

## No inferred restriction state

The Command Center architecture eventually needs direct visibility such as:

```text
system paused / active
new trading halted / permitted
active market restrictions
active account restrictions
```

Those fields are deliberately absent from this delivery because receipts alone are historical
results, not a canonical materialized governance-state boundary.

A future narrow contract may introduce that state only after the repository defines a deterministic
source-of-truth model with explicit identity, version, timestamps, evidence and restoration
semantics.

## No command expansion

This read model adds no `ExecutiveControlAction` and changes no command authorization.

The existing allowlist remains the authority surface for governance commands.

No read-model field can invoke:

- buy/sell;
- submit/cancel order;
- close position;
- force trade;
- Risk bypass;
- capital-protection bypass.

## Determinism

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit UUID identities;
- explicit timezone-aware timestamps;
- deterministic authority ordering by grant identity;
- deterministic receipt ordering by completion time and receipt identity;
- deterministic capability/reason/evidence ordering;
- duplicate grant/receipt/capability/evidence references rejected;
- deterministic `logical_values()`;
- no implicit current time or UUID generation.

## Scope binding

```text
ExecutiveGovernanceReadModel -> ExecutiveReadScope.GOVERNANCE
```

Any other scope fails closed.

## Safety / mission status

This is read-only preparatory contract work. It introduces no transport, Mobile activation,
provider/broker access, Profit Vault dependency, Production authorization, productive credentials,
real capital, scheduler, retry loop, thread, or deployment.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is authorized.

## Next controlled boundary

After this read model is merged, every executive surface currently approved in the CEO Command
Center map has a canonical authorization/read-model foundation.

The next work should therefore be selected from repository truth rather than adding more speculative
UI payloads. A likely architectural prerequisite for richer Governance visibility is a canonical
materialized governance-state contract for current pause/halt/restriction state, but it must be
introduced only if the current repository/roadmap confirms it is the next controlled deliverable.

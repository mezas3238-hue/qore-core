# QORE-EXECUTIVE-GOVERNANCE-MUTATION-001 — Governance State Mutation Boundary

Status: **MISSION-04 DELIVERY 7 — PERSISTENCE-NEUTRAL COMPARE-AND-SET**

## Purpose

Define the explicit downstream mutation boundary for the already-established materialized executive Governance state.

This delivery does not choose a database and does not add a second current-state model.

## Source and mutation separation

The repository already exposes `ExecutiveGovernanceStateSource.read_current_state()` for current reads.

Delivery 7 adds the complementary write contract:

```text
ExecutiveGovernanceMutationPort.compare_and_set(request)
    → Result[ExecutiveGovernanceMutationReceipt, ExecutiveGovernanceMutationError]
```

The mutation contract is compare-and-set: it carries the complete expected state and the complete requested next state. A concrete persistence implementation must compare the current persisted snapshot/version to that expectation before replacing it.

## Mutation request

`ExecutiveGovernanceMutationRequest` binds:

- explicit mutation UUID;
- exact `AuthorizedExecutiveControlIntent`;
- expected current materialized state;
- requested next materialized state;
- explicit `source_receipt_id` reserved for the canonical command receipt;
- caller-supplied timezone-aware mutation timestamp.

The request must produce a new snapshot identity and a new state version and cannot predate executive authorization.

## Action semantics

Only actions represented by the current materialized state may mutate it.

### PAUSE_SYSTEM

Must transition a non-paused system to `PAUSED`, preserve new-trading state and preserve restrictions.

Already-paused state is a `NO_CHANGE` command outcome, not a state mutation.

### RESUME_SYSTEM

Must transition a non-active system to `ACTIVE`, preserve new-trading state and preserve restrictions.

Already-active state is a `NO_CHANGE` command outcome.

### HALT_NEW_TRADING

Must transition a non-halted new-trading state to `HALTED`, preserving system run state and restrictions.

Already-halted state is a `NO_CHANGE` command outcome.

### RESTRICT_MARKET / RESTRICT_ACCOUNT

Must add exactly one immutable active restriction matching the authorized target. The new restriction must cite the exact `source_receipt_id` reserved by the mutation request.

No unrelated restriction may be removed or rewritten.

### RESTORE_RESTRICTION

Must remove exactly one active restriction whose restriction UUID text matches the authorized restriction target. No new restriction may be added.

### UPDATE_GOVERNANCE_POLICY / ACKNOWLEDGE_INCIDENT

These actions are intentionally rejected by this materialized-state mutation contract because the current snapshot does not model policy content or incident acknowledgement state.

A command handler must route those actions to their proper governed boundaries rather than fabricating state in this snapshot.

## Immutable restriction history

If a restriction ID exists in both expected and next state, its complete value must remain identical.

A mutation may add or remove restrictions according to the authorized action, but it may not silently rewrite the provenance of an already-active restriction.

The mutation's `source_receipt_id` also cannot reuse the receipt provenance of an active restriction in the expected state.

## Receipt contract

`ExecutiveGovernanceMutationReceipt` reports either:

- `APPLIED`; or
- `CONFLICT`.

An applied receipt must observe exactly the requested snapshot ID/version.

A conflict receipt must demonstrate that the observed current snapshot/version differs from the expectation.

`build_executive_governance_mutation_receipt()` derives the expected/requested identities from the exact mutation request and rejects completion timestamps before the request.

Concrete infrastructure unavailability remains a typed `Failure`, not a fabricated conflict or applied receipt.

## Relationship to command receipts

The explicit mutation `source_receipt_id` allows a concrete command-port implementation to reserve the final `ExecutiveControlReceipt` identity before compare-and-set.

A newly-created active restriction can therefore cite that same command receipt ID, preserving:

```text
AuthorizedExecutiveControlIntent
  → mutation request
  → materialized state
  → ExecutiveControlReceipt
  → restriction provenance
```

No implicit ID generation occurs inside governance.

## No persistence implementation

This delivery does not introduce SQL, Redis, filesystem, cloud storage, transactions or locks.

Those are infrastructure choices behind `ExecutiveGovernanceMutationPort`.

## Provider independence

No OANDA/broker/provider dependency is introduced. MISSION-03 remains operationally blocked at Gate #5 pending OANDA Practice provisioning.

## Safety

No trading order semantics, Production authority, real capital, credential, provider client, hidden retry, scheduler/thread or implicit clock is introduced.

## Tests

The delivery verifies pause semantics, exact market restriction provenance, exact restriction restoration, rejection of non-materialized actions, new snapshot/version requirements, no-change rejection, receipt chronology, conflict semantics and structural Protocol substitution.

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or weakened gate is permitted.

## Next delivery

After merge, continue directly with:

```text
QORE-EXECUTIVE-AUDIT-EVIDENCE-001
```

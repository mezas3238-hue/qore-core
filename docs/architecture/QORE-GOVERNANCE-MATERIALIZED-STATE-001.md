# QORE-GOVERNANCE-MATERIALIZED-STATE-001

## Purpose

Define one explicit canonical boundary for current Executive Governance state so readers do not infer pause, halt, or active restriction state from historical receipts.

## Why this contract is required

The executive control plane already has auditable command receipts and, after `QORE-EXECUTIVE-CONTROL-TARGETS-001`, scoped restriction commands carry exact target identity. Receipts remain historical outcomes, however; they are not themselves a canonical current-state store.

A reader that replays receipts independently could diverge from another reader, mishandle restoration, or silently invent current state. This contract forbids that ambiguity.

## Canonical snapshot

`ExecutiveGovernanceStateSnapshot` contains:

- explicit snapshot UUID;
- explicit state schema/version;
- timezone-aware `observed_at`;
- current system run state: `active`, `paused`, or `unknown`;
- current new-trading state: `permitted`, `halted`, or `unknown`;
- active market restrictions;
- active account restrictions.

`unknown` is first-class and preserves fail-closed semantics when a source cannot truthfully establish current state.

## Active restriction provenance

Every active restriction carries:

- opaque restriction UUID;
- exact market/account `ExecutiveControlTarget`;
- timezone-aware application time;
- exact source `ExecutiveReceiptId`;
- explicit governance policy version;
- canonical reason codes;
- non-empty structured evidence references.

Restriction targets are partitioned exactly: market restrictions contain only market targets and account restrictions only account targets. A restriction-target identity is not a valid active market/account restriction target.

The snapshot rejects duplicate active targets, duplicate restriction identities, duplicate source receipts, and restrictions applied after the snapshot observation time.

## Source boundary

`ExecutiveGovernanceStateSource` is a `Protocol` that returns `Result[ExecutiveGovernanceStateSnapshot, ExecutiveGovernanceStateError]` for an explicit `ExecutiveGovernanceStateRequest`.

The source contract receives no receipt history and exposes no replay/reducer API. How a concrete implementation persists or materializes state remains outside this contract, but every consumer reads the same already-materialized canonical state.

## Deliberate non-goals

This delivery does not:

- implement persistence;
- replay control receipts;
- mutate state;
- dispatch executive commands;
- expose the state directly to Mobile/Desktop;
- authorize Production or real capital;
- introduce broker/provider connectivity;
- perform corrective trading.

A separate executive projection may map this canonical state into the authorized `GOVERNANCE` read model without leaking internal state-source objects.

## Quality gate

The unchanged QORE gate applies:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is permitted.

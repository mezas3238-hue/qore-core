# QORE-EXECUTIVE-GOVERNANCE-CURRENT-STATE-001

## Purpose

Project canonical materialized Executive Governance state into the stable authorized `GOVERNANCE` read surface without exposing state-source internals or reconstructing state from control receipts.

## Dependency

`QORE-GOVERNANCE-MATERIALIZED-STATE-001` established the canonical source-side snapshot. This delivery consumes only that validated snapshot contract.

Historical authority and control-receipt summaries remain useful evidence, but they are not used to infer current pause, halt, or restriction state.

## Projection boundary

`project_executive_governance_current_state(snapshot)` is a pure mapping from `ExecutiveGovernanceStateSnapshot` into projection-specific immutable types.

The projection contains:

- opaque snapshot identity;
- state version;
- timezone-aware observation time;
- system run state: active, paused, or unknown;
- new-trading state: permitted, halted, or unknown;
- active market restriction summaries;
- active account restriction summaries.

Each projected restriction retains opaque identity, target kind/reference, application time, source receipt identity, governance policy version, reason codes, and evidence references.

## No internal leakage

The executive projection does not expose:

- `ExecutiveGovernanceStateSource`;
- source-side `ExecutiveActiveRestriction` objects;
- `ExecutiveControlTarget` objects;
- receipt histories;
- replay/reducer APIs;
- provider or broker objects.

Projection-specific values preserve the public boundary.

## Explicit absence

`ExecutiveGovernanceReadModel.current_state` is optional.

- `current_state is None` means no canonical materialized snapshot was supplied to the projection;
- it must not be interpreted as active, paused, permitted, halted, or unrestricted;
- readers must not derive a substitute state from `control_receipts`.

When present, the current-state observation may not postdate the executive projection timestamp.

## Compatibility

Existing authority/receipt projection behavior remains intact. The Governance read model gains a nested current-state block rather than adding convenience booleans such as `system_paused` or `new_trading_halted`, avoiding lossy or inferred semantics.

This delivery also exposes the Governance read-model contracts from the package root so the public Governance surface is complete and consistent with other executive projections.

## Safety

No command dispatch, state mutation, persistence, trading action, order surface, Risk bypass, broker/provider access, credentials, Production authorization, real capital, retry loop, scheduler, thread, or automatic corrective behavior is introduced.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is permitted.

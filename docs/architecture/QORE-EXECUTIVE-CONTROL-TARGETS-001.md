# QORE-EXECUTIVE-CONTROL-TARGETS-001

## Purpose

Make scoped executive governance actions reconstructible and auditable by binding each such action to one explicit opaque target identity.

## Problem closed

The existing executive allowlist contained `restrict-market`, `restrict-account`, and `restore-restriction`, but `ExecutiveControlIntent` and `ExecutiveControlReceipt` did not carry the subject of those actions. Authorization could therefore prove that an action was allowed without proving which market, account, or prior restriction it concerned.

That ambiguity is now closed at the contract boundary.

## Target contract

`ExecutiveControlTarget` is immutable and contains:

- `kind`: one of `market`, `account`, or `restriction`;
- `value`: an opaque canonical lowercase reference.

The value is a QORE governance reference. It is not a broker account number, credential, token, provider object, or unrestricted free-form payload.

## Exact action binding

The following bindings are mandatory and fail closed:

- `restrict-market` requires a `market` target;
- `restrict-account` requires an `account` target;
- `restore-restriction` requires a `restriction` target.

All other executive control actions are global at this contract level and must not carry a target.

A missing target, wrong target kind, secret-like value, non-canonical value, or target attached to a global action is invalid before authorization or dispatch.

## Audit continuity

`ExecutiveControlReceipt` now carries the exact target from the already-authorized intent. `build_executive_control_receipt` does not accept an independent caller-supplied target and therefore cannot silently change the subject between authorization and receipt construction.

The target is also present in deterministic `logical_values()` for both the intent and receipt.

## Architectural consequence

This delivery provides the identity prerequisite for a later canonical materialized Governance state. It does not itself derive active restrictions from receipt history and does not create a hidden reducer. A materialized-state source remains a separate explicit contract.

## Safety

This change introduces no trading action, order submission, close/cancel capability, Risk bypass, provider/broker access, transport, credentials, Production authorization, real capital, scheduler, retry loop, or automatic corrective behavior.

MISSION-03 remains active and unchanged.

## Quality gate

The unchanged repository gate applies:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is permitted.

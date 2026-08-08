# QORE-EXECUTIVE-GOVERNANCE-READ-SCOPE-001 — Explicit Governance Read Authority

Status: **AUTHORIZATION CONTRACT PREPARATION — GOVERNANCE READ MODEL NOT YET IMPLEMENTED**

## Verified base

```text
main @ 448ec13bd3dddf0866bd7f3de1f47df83b137e22
```

At branch creation there were no open pull requests and no later `main` change altering the CEO
Command Center direction.

## Why this change is separate

The approved CEO Command Center architecture includes a Governance product surface, but the
canonical `ExecutiveReadScope` allowlist previously had no `GOVERNANCE` member.

Earlier executive read-model deliveries therefore correctly failed closed rather than inventing a
scope outside the authorization contract.

This delivery performs the missing authority step explicitly:

```text
ExecutiveReadScope.GOVERNANCE = "governance"
```

Only after this gate is merged may a Governance read model be added.

## Authorization semantics

Governance remains a **read scope**, not a new executive command action.

The existing canonical authorization path is unchanged:

```text
ExecutiveReadRequest(scope=GOVERNANCE)
        ↓
ExecutiveAuthorityGrant.allowed_read_scopes
        ↓
authorize_executive_read_request(...)
        ↓
AUTHORIZED or FAIL-CLOSED
```

A Governance read request succeeds only when the exact authority grant includes
`ExecutiveReadScope.GOVERNANCE`.

If the scope is absent from the grant:

```text
NO DATA ACCESS
```

## No authority expansion by implication

Adding the enum value does not automatically add it to any existing grant.

Existing grants remain exactly as restrictive as before because authorization is capability-based
and each grant contains an explicit immutable tuple of allowed read scopes.

No wildcard or "all scopes" behavior is introduced.

## Control actions remain unchanged

This delivery does not add any `ExecutiveControlAction`.

In particular, it adds no:

- buy;
- sell;
- submit-order;
- cancel-order;
- force-trade;
- close-position;
- Risk bypass;
- capital-protection bypass.

The existing governed command surface remains separate from the Governance read surface.

## Determinism

`GOVERNANCE` participates in the existing deterministic read-scope sorting used by
`ExecutiveAuthorityGrant` and therefore in deterministic `logical_values()` evidence.

No clock, identity, provider, network, retry, scheduler, or mutable state is introduced.

## What this delivery does not implement

This scope gate deliberately does not define the Governance business payload.

A subsequent narrow delivery must define the explicit executive projection, such as stable
structures for:

- active governance policy versions;
- restrictions;
- system pause/halt state;
- executive authority summary;
- unresolved governance incidents/acknowledgements where canonically available;
- evidence references;
- source freshness and projection version.

That later projection must not expose internal policy/domain objects directly to Desktop/iOS/Android
and must reuse `ExecutiveProjectionMetadata` and `ExecutiveReadQueryPort`.

## Safety / mission status

This change creates no transport, application backend, Mobile activation, provider access, broker
access, Profit Vault dependency, Production account, productive credential, real capital, or
trading execution.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or weakening of the repository quality gate is authorized.

## Next controlled delivery

After this explicit scope authorization is merged, the next logical deliverable is:

```text
QORE-EXECUTIVE-GOVERNANCE-READ-MODEL-001
```

It may define the Governance executive projection only against the now-canonical `GOVERNANCE`
scope and existing authorized read boundary.

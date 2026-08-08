# QORE-EXECUTIVE-CONTROL-PLANE-001 — Executive Control Plane Governance Contracts

Status: **PREPARATION READY — MOBILE/CONTROL-PLANE ACTIVATION REMAINS CLOSED**

## Purpose

Define the first executable governance contracts that future QORE CEO Desktop, iOS and Android experiences must use before any executive request can reach a downstream QORE governance surface.

This deliverable implements only deterministic contracts and authorization evaluation. It does not deploy a Control Plane service, activate QORE Mobile, connect a CEO device to Core, expose a broker surface, or authorize Production trading.

## Architectural position

The target architecture remains:

```text
CEO Desktop / iOS / Android
            │
            ▼
Executive Control Plane
            │
            ├── identity/authentication boundary
            ├── authority evaluation
            ├── command/query governance
            ├── audit/evidence
            └── downstream adapters
                    │
                    ▼
             governed QORE surfaces
```

The prohibited architecture remains:

```text
CEO App ─────────────► Core internals
CEO App ─────────────► broker/provider
CEO App ─────────────► execution gateway
CEO App ─────────────► credentials
```

The contracts in `qore.governance.executive_control` are provider-free and transport-free. They do not contain HTTP, mobile, broker, database, scheduler, retry, thread, or network behavior.

## Reused QORE governance principles

The implementation follows existing repository patterns already used by supervised CIBO and market-test governance:

- explicit immutable identities;
- `dataclass(frozen=True, slots=True)`;
- explicit timezone-aware timestamps;
- expiring authorization;
- deterministic `logical_values()`;
- `Result / Success / Failure`;
- typed fail-closed errors;
- no implicit `datetime.now()`;
- no implicit `uuid4()`;
- no secret material in reason/evidence values;
- stable capability ordering.

## Executive identity

`ExecutivePrincipalId` is an opaque canonical principal identifier. It is not a password, session token, device identifier, biometric, email address, or secret.

Authentication itself belongs to a future external identity boundary. These contracts consume only the authenticated principal identity resulting from that boundary.

## Authority versioning

Every grant includes an explicit `ExecutiveAuthorityVersion`.

The system must therefore be able to reconstruct which authority policy was in force when an executive action or read request was authorized.

No authorization may rely on an invisible global role or an unversioned boolean such as `is_admin=True`.

## Executive authority grant

`ExecutiveAuthorityGrant` binds:

- grant identity;
- executive principal;
- authority version;
- allowed governance actions;
- allowed read scopes;
- issue time;
- expiry time;
- explicit safe reason.

The grant is immutable and expiring.

At least one capability must be authorized. Duplicate capabilities are invalid. Capabilities are normalized into stable deterministic order for evidence and audit.

## Closed governance action allowlist

`ExecutiveControlAction` deliberately exposes only governance actions:

```text
pause-system
resume-system
halt-new-trading
restrict-market
restrict-account
restore-restriction
update-governance-policy
acknowledge-incident
```

This allowlist deliberately does **not** include:

```text
buy
sell
submit-order
cancel-order
force-trade
close-position
change-stop-loss
change-take-profit
bypass-risk
```

The absence of these values is architectural, not merely a UI choice.

A future CEO application therefore cannot manufacture a direct trading command by choosing a hidden endpoint. Any new executive action requires an explicit repository change, tests, review and CI.

## CEO authority versus CIBO/Risk authority

The CEO may govern QORE, reduce authority, pause the system, halt new trading, restrict markets/accounts and change governance policies through future authorized downstream implementations.

This contract does not allow the CEO to force CIBO to accept a trade, create an order, bypass Portfolio/Risk/Capital Protection, or convert a blocked trading decision into an execution.

The governance rule remains:

```text
CEO may reduce or stop operational authority
              !=
CEO may bypass trading governance
```

## Control intent

`ExecutiveControlIntent` contains:

- explicit intent identity;
- principal identity;
- one allowlisted action;
- explicit request timestamp;
- existing QORE `CorrelationId`;
- safe reason.

The correlation identifier permits a future Control Plane to connect authentication evidence, authorization evaluation, downstream governance result and audit evidence without inventing a second tracing model.

## Fail-closed authorization

`authorize_executive_control_intent()` returns authorization only when all mandatory conditions hold:

1. request and grant are valid contract types;
2. timestamps are timezone-aware;
3. principal matches the grant;
4. action appears in the explicit allowlist of that grant;
5. request does not predate the grant;
6. authorization evaluation does not predate the request;
7. grant has not expired.

Any uncertainty produces `Failure` and no downstream dispatch occurs in this layer.

This deliverable intentionally contains no command dispatcher.

## Executive read surfaces

Control and observation are distinct capabilities.

`ExecutiveReadScope` currently defines:

```text
system-health
cibo-state
capital-state
portfolio
risk
markets
traders
validation-lab
trade-forensics
audit
ceo-accounts
corporate-profit-vault
```

A read grant does not imply control authority, and a control grant does not imply every read scope.

`ExecutiveReadRequest` is explicitly read-only and is authorized independently through `authorize_executive_read_request()`.

## Proprietary CEO accounts and Client Profit Vault remain distinct

The scopes:

```text
ceo-accounts
corporate-profit-vault
```

are intentionally separate values.

`ceo-accounts` represents proprietary/CEO-controlled account information.

`corporate-profit-vault` represents the isolated corporate client-service settlement read model defined by `QORE-CLIENT-PROFIT-VAULT-ARCH-001`.

Their coexistence in an executive navigation model does not connect their underlying data domains and does not create:

```text
Core ↔ Profit Vault
```

A future CEO Command Center may query separate adapters behind the Executive Control Plane and render both to the authenticated CEO while preserving domain isolation.

## Reason-for-Action alignment

Every control intent requires a reason.

The contract rejects empty reasons and obvious secret-bearing fragments including token/password/bearer/API-key forms.

This reason is not private chain-of-thought. It is structured operational evidence describing why the executive governance request exists.

Future downstream evidence should preserve the chain:

```text
Principal
  → Authority Version
  → Grant
  → Control Intent / Read Request
  → Authorization Evaluation
  → Downstream Governance Action or Read
  → Result
  → Audit Evidence
```

## Security boundary

This deliverable deliberately does not define:

- password storage;
- access tokens;
- biometric material;
- mobile session secrets;
- private signing keys;
- provider credentials;
- account credentials;
- payment credentials.

Those belong to external secret/authentication boundaries.

Secret material must never be placed in `reason`, `logical_values()`, audit metadata, logs, telemetry, or public evidence.

## No direct mobile authority

Desktop, iOS and Android are presentation surfaces only.

A future application must not convert possession of a device into operational authority. The Control Plane must independently resolve authenticated identity and current authority before evaluating each protected request.

A stolen/unlocked device must therefore not be modeled as equivalent to an unexpired executive grant.

## Emergency controls

`HALT_NEW_TRADING` is intentionally different from an instruction to close positions.

The executive control contract may stop new trading authority without becoming an order-management surface. Existing position protection, Risk and Capital Protection remain separate responsibilities.

Future emergency-close semantics, if ever required, must be defined through an explicit governed risk/capital-preservation architecture rather than adding `close-position` to the CEO UI contract.

## Determinism and auditability

All public value contracts are immutable.

Authorization uses caller-supplied explicit timestamps.

No runtime clock or random identity source is hidden inside the authorization functions.

`logical_values()` provides deterministic values that can participate in future evidence hashing/signing without embedding credentials.

## Tests

The test suite verifies at least:

- an allowlisted governance action succeeds;
- a non-granted action fails closed;
- principal mismatch fails closed;
- expired grants fail closed;
- requests cannot predate authority;
- direct trading actions are absent from the action enum;
- capability ordering is deterministic;
- duplicate capabilities fail validation;
- secret-like reasons fail validation;
- naive datetimes fail validation;
- allowed reads succeed;
- non-granted reads fail closed;
- CEO account and corporate Profit Vault scopes remain distinct;
- evidence values remain deterministic.

## Mission boundary

MISSION-03 remains the active operational mission and its provider TEST/DEMO sequence is unchanged.

This deliverable does not claim that MISSION-04 has started operationally.

It is preparatory architecture and contract implementation for the future:

```text
MISSION-04 — QORE Control Plane & Executive Governance
MISSION-05 — QORE Mobile & CEO Command Center
```

Nothing in this deliverable authorizes:

- QORE Mobile activation;
- CEO Widget activation;
- a public API;
- Production accounts;
- productive credentials;
- real capital;
- autonomous real-money execution;
- direct CEO order submission;
- Risk bypass;
- direct Profit Vault/Core connectivity.

## Quality gate

This functional contract delivery must pass the unchanged repository gates:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No lint, typing or coverage requirement may be weakened to merge this work.

## Next boundary

After this contract is integrated, the next Executive Control Plane work should add **transport-neutral command/query port contracts and deterministic audit receipts**, still without creating an HTTP/mobile server or connecting the CEO application directly to Core.

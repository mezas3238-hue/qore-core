# QORE-EXECUTIVE-AUTHENTICATED-PRINCIPAL-001 — Authenticated Principal Assertion

Status: **MISSION-04 DELIVERY 2 — TRANSPORT-NEUTRAL CONTRACT**

## Purpose

Define the secret-free identity assertion that the Executive Control Plane may consume after an external authentication boundary has already authenticated an executive principal.

This delivery does not implement login, password verification, passkey verification, OAuth/OIDC, biometrics, mobile sessions, token validation, HTTP or any identity-provider integration.

## Architectural position

```text
Credential / Passkey / External IdP
              │
              ▼
   Secret-aware authentication boundary
              │
              ▼
AuthenticatedExecutivePrincipal
              │
              ▼
      Executive Control Plane
```

QORE receives only the assertion on the right side of the authentication boundary. It never receives the credential material used to produce it.

## Reused identity

The assertion reuses the canonical `ExecutivePrincipalId` from `executive_control.py`.

No second CEO/user identity model is introduced.

The assertion also reuses the existing domain `CorrelationId`, preserving one tracing model across authentication, authority evaluation, dispatch and audit.

## Contracts

### ExecutiveAuthenticationAssertionId

Explicit UUID identity of one authentication assertion. No implicit identity generation occurs.

### ExecutiveAuthenticationMethodCode

Provider-neutral, sanitized classification of the authentication method. Examples may include safe codes such as `passkey` or `sso`; this value is descriptive evidence, not credential material.

### ExecutiveAuthenticationContextCode

Provider-neutral, sanitized assurance/authentication context classification supplied by the external identity boundary.

QORE deliberately does not infer privileges from this field. Governance authority remains separately evaluated from current authority state.

### ExecutiveIdentityBoundaryRef

Opaque canonical reference to the external boundary that produced the assertion. It is not a URL containing credentials, a bearer token, session secret or API key.

### AuthenticatedExecutivePrincipal

Immutable assertion containing only:

- assertion identity;
- existing executive principal identity;
- authentication method code;
- authentication context code;
- external identity-boundary reference;
- explicit issue timestamp;
- explicit expiry timestamp;
- existing QORE correlation identity.

The assertion contains no password, token, credential, private key or biometric field.

## Temporal semantics

The assertion requires timezone-aware `issued_at` and `expires_at`, with expiry strictly after issue.

`evaluate_authenticated_executive_principal()` receives an explicit caller-supplied `evaluated_at` and returns:

- `Success(assertion)` when `issued_at <= evaluated_at <= expires_at`;
- typed `Failure` when the assertion is not yet valid or has expired;
- typed validation failure for malformed evaluation input.

No runtime clock is consulted.

The inclusive expiry convention matches the already-established Executive Authority Grant evaluation convention; a later mission-wide temporal-policy change would require an explicit repository change rather than silent divergence.

## Secret boundary

Public method/context/boundary codes reject obvious secret-bearing fragments including:

- `authorization:`;
- `bearer `;
- `client_secret`;
- `password`;
- `private_key`;
- `secret`;
- `token`.

Secret material must never appear in assertion `repr`, `logical_values()`, audit metadata, telemetry or logs.

## Authority separation

A valid authentication assertion proves only that an external identity boundary asserted a principal for a bounded time window.

It does **not** prove that the principal currently has authority to pause QORE, change governance policy, read executive data or perform any other action.

MISSION-04 therefore preserves the chain:

```text
Authenticated Principal
  → Current Authority State
  → Request Authorization
  → Replay / Idempotency Evaluation
  → Governed Dispatch
```

Delivery 3 will define the canonical current authority/revocation source. Delivery 4 will bind authentication, current authority and a concrete request.

## No device authority

The contract contains no device identifier and does not treat possession of Desktop/iOS/Android as authority.

A future presentation client must obtain a fresh assertion from an external authentication boundary; the Control Plane must still independently evaluate current governance authority for every protected operation.

## No provider dependency

This delivery is independent of OANDA and all broker/provider integrations.

MISSION-03 remains operationally blocked at Gate #5 until the OANDA Practice account and token exist. This contract does not change that state and cannot supply MISSION-03 operational evidence.

## Safety

This delivery introduces no:

- provider/broker access;
- trading execution;
- buy/sell/order command;
- Risk bypass;
- Production authority;
- productive credentials;
- real capital;
- mobile/public network service;
- hidden retry, scheduler, thread or clock.

## Determinism

All values are immutable and use deterministic `logical_values()`.

Identity and timestamps are supplied explicitly by callers. No `uuid4()` or `datetime.now()` is embedded.

## Tests

The delivery verifies:

- current assertion succeeds;
- exact issue/expiry boundaries follow existing executive temporal convention;
- future and expired assertions fail closed;
- naive timestamps fail validation;
- invalid chronology fails validation;
- secret-like public codes fail validation;
- runtime type coercion is rejected;
- values are immutable;
- no password/token/credential/biometric field exists;
- logical values are deterministic and secret-free.

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or weakened check is permitted.

## Next delivery

After merge, continue directly with:

```text
QORE-EXECUTIVE-AUTHORITY-STATE-001
```

That delivery will define the canonical current grant/revocation/supersession/expiry source-of-truth boundary without replaying incomplete audit history.
